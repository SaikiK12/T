"""xyzbal_fwd (R530): the balanced (market-neutral) weekend fade of trade.xyz US-stock perps, tested forward on fresh
weekends from Friday 2026-12-04, as set out in experiments/xyzbal_fwd/PREREG.md. Paper only: public endpoints, no
key, no order.

Rule (frozen): for each plain weekend (scripts/xyzwknd_rule.py: R = Friday 20:00, E = Sunday 19:00, X1 = Sunday
22:00 New York) and each of R462's 76 markets listed at least 7 days before R, W is the perp's move from R to E on
the close of the last hourly candle before each instant (rule.event_row). With at least 5 priced markets,
rel W = W - the weekend's median W. Buy every market with rel W <= -50 bp, sell every market with rel W >= +50 bp,
equal notional on each side, from E to X1; a weekend trades only if both sides hold a market.
- Per trade: g = side x (price move + funding), net = g - (two taker fees from that day's markets file + the recorded
  $1k book cost on the side traded at E and at X1, nearest snapshot within 90 minutes, else 10 bp, counted).
- Weekend net (decides) = (mean net of the long side + mean net of the short side) / 2.

R463's helpers are imported, never edited (their sha256 is pinned in the PREREG). Writes journal/trades.csv and
journal/weekends.csv (append-only) and journal/status.json.

usage: python scripts/run_xyzbal_fwd.py score --snapshots DIR [--status]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
import xyzwknd_rule as rule  # noqa: E402
import run_xyzwknd_fwd as base  # noqa: E402

LANE = ROOT / "experiments" / "xyzbal_fwd"
J = LANE / "journal"
# ---- the frozen rule (PREREG "Rule"); tests/test_xyzbal_fwd.py checks these against the PREREG text
FIRST_FRIDAY = date(2026, 12, 4)
THETA_BP = 50.0
MIN_MARKETS = 5
FUTILITY_N, INTERIM_N, FINAL_N = 15, 20, 30      # traded weekends
ALPHA_INTERIM, ALPHA_FINAL = 0.01, 0.04
N_BOOT, SEED, TOP_K = 10_000, 530, 3
PROXY = ("MSTR", "COIN", "HOOD", "CRCL", "BMNR", "STRC", "IREN")   # reported only (cycle 5's prediction 6b)
T_COLS = ["friday", "coin", "status", "w_bp", "rel_bp", "side", "raw_side", "price_bp", "funding_bp", "gross_bp",
          "fee_bp", "book_bp", "fallback_fills", "fee_fallback", "net_1x", "book5k_bp", "net5k_1x"]
W_COLS = ["friday", "status", "markets", "median_w_bp", "n_long", "n_short", "gross_bp", "cost_bp", "net_1x",
          "net_2x", "net_3x", "net5k_1x", "common_move_bp", "proxy_trades"]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------- pure parts
def market_row(u, w, k, f):
    """W, raw fade side s and the raw side's E->X1 returns for one market (status 'priced' when usable)."""
    row = {"friday": str(w["friday"]), "coin": u["coin"]}
    t = k.t.to_numpy("int64") if len(k) else np.array([], "int64")
    if not len(t) or t[0] > w["R"] - base.LISTED_MS:
        return dict(row, status="not_listed")
    if u.get("ipo_424b4") and w["F"] <= u["ipo_424b4"]:
        return dict(row, status="pre_ipo")
    x = rule.event_row(t, k.c.to_numpy("float64"), f.time.to_numpy("int64"), f.rate.to_numpy("float64"), w)
    if x["s"] == 0 or not math.isfinite(x["g_x1"]):
        return dict(row, status="unpriced", w_bp=x["W"] if math.isfinite(x["W"]) else None)
    return dict(row, status="priced", w_bp=x["W"], raw_side=x["s"], c_x1=x["c_x1"], f_x1=x["f_x1"], g_x1=x["g_x1"])


def assign_sides(rows, theta=THETA_BP, min_markets=MIN_MARKETS):
    """Adds rel_bp and side (+1 buy, -1 sell, 0 none) to the priced rows; returns the weekend's median W or None."""
    pr = [r for r in rows if r["status"] == "priced"]
    if len(pr) < min_markets:
        return None
    med = float(np.median([r["w_bp"] for r in pr]))
    for r in pr:
        r["rel_bp"] = r["w_bp"] - med
        r["side"] = 1 if r["rel_bp"] <= -theta else (-1 if r["rel_bp"] >= theta else 0)
    return med


def trade_costs(r, w, books, mk_e, mk_x, uni_row):
    """Fees and recorded book costs of one trade (side b), R463's conventions."""
    name, b = "xyz:" + r["coin"], r["side"]
    fee_e, fb_e = base.fee_of(mk_e, name, uni_row)
    fee_x, fb_x = base.fee_of(mk_x, name, uni_row)
    side_in, side_out = ("buy", "sell") if b > 0 else ("sell", "buy")
    book, book5, fb = 0.0, 0.0, 0
    for t_, sd in ((w["E"], side_in), (w["X1"], side_out)):
        c = base.nearest(books, name, t_, f"{sd}_{base.SIZE_USD}_bp")
        if c is None:
            c, fb = base.FALLBACK_BP, fb + 1
        book += c
        c5 = base.nearest(books, name, t_, f"{sd}_{base.SIZE_REPORT}_bp")
        book5 = None if (book5 is None or c5 is None) else book5 + c5
    return fee_e + fee_x, book, book5, fb, fb_e + fb_x


def weekend_rows(rows, w, books, mk_e, mk_x, uni_by_coin):
    """(trade rows, weekend row) for one weekend from its market rows."""
    med = assign_sides(rows)
    fr = str(w["friday"])
    trades = []
    for r in rows:
        if r["status"] != "priced" or r.get("side", 0) == 0:
            continue
        b, s = r["side"], r["raw_side"]
        g = b * s * r["g_x1"]                      # the return of side b: raw side s's return times b*s (= +-1)
        fee, book, book5, fb, ffb = trade_costs(r, w, books, mk_e, mk_x, uni_by_coin[r["coin"]])
        trades.append({"friday": fr, "coin": r["coin"], "status": "ok", "w_bp": r["w_bp"], "rel_bp": r["rel_bp"],
                       "side": b, "raw_side": s, "price_bp": b * s * r["c_x1"], "funding_bp": b * s * r["f_x1"],
                       "gross_bp": g, "fee_bp": fee, "book_bp": book, "fallback_fills": fb, "fee_fallback": ffb,
                       "net_1x": g - (fee + book), "book5k_bp": book5,
                       "net5k_1x": None if book5 is None else g - (fee + book5)})
    priced = [r for r in rows if r["status"] == "priced"]
    wk = dict.fromkeys(W_COLS)
    wk.update(friday=fr, markets=len(priced), median_w_bp=med)
    lo = [t for t in trades if t["side"] > 0]
    sh = [t for t in trades if t["side"] < 0]
    wk.update(n_long=len(lo), n_short=len(sh))
    if med is None:
        wk["status"] = "too_few_markets"
        return trades, wk
    if not lo or not sh:
        wk["status"] = "one_sided"
        return trades, wk
    half = lambda key, side: float(np.mean([t[key] for t in side]))  # noqa: E731
    gross = 0.5 * half("gross_bp", lo) + 0.5 * half("gross_bp", sh)
    net = 0.5 * half("net_1x", lo) + 0.5 * half("net_1x", sh)
    cost = gross - net
    n5 = None
    if all(t["net5k_1x"] is not None for t in trades):
        n5 = 0.5 * half("net5k_1x", lo) + 0.5 * half("net5k_1x", sh)
    moves = [r["c_x1"] * r["raw_side"] for r in priced]      # the unfaded E->X1 move of each market
    wk.update(status="ok", gross_bp=gross, cost_bp=cost, net_1x=net, net_2x=gross - 2 * cost,
              net_3x=gross - 3 * cost, net5k_1x=n5, common_move_bp=float(np.median(moves)),
              proxy_trades=sum(1 for t in trades if t["coin"] in PROXY))
    return trades, wk


def boot_p(x, n_boot=N_BOOT, seed=SEED):
    """One-sided p: the share of resampled means (whole weekends, with replacement) at or below 0."""
    x = np.asarray(x, float)
    rng = np.random.default_rng(seed)
    m = x[rng.integers(0, len(x), size=(n_boot, len(x)))].mean(1)
    return float((m <= 0).mean())


def decision(weekends):
    """The frozen Decision on traded weekends in calendar order."""
    ok = weekends[weekends.status == "ok"].copy() if len(weekends) else weekends
    n = int(len(ok))
    out = {"traded_weekends": n, "state": "PENDING"}
    if not n:
        return out
    ok = ok.sort_values("friday")
    v1 = pd.to_numeric(ok.net_1x).to_numpy(float)
    v2 = pd.to_numeric(ok.net_2x).to_numpy(float)
    if n >= FUTILITY_N and v1[:FUTILITY_N].mean() <= 0:
        out.update(state="NULL", reason=f"futility: mean of the first {FUTILITY_N} traded weekends <= 0")
        return out
    for look, alpha in ((INTERIM_N, ALPHA_INTERIM), (FINAL_N, ALPHA_FINAL)):
        if n < look:
            break
        x, x2 = v1[:look], v2[:look]
        p = boot_p(x)
        trim = np.sort(x)[:-TOP_K].mean()
        out[f"look_{look}"] = {"mean_1x": float(x.mean()), "p": p, "mean_2x": float(x2.mean()),
                               "mean_without_best_3": float(trim)}
        if p < alpha and x2.mean() > 0 and trim > 0:
            out.update(state="PASS", reason=f"passes at {look} traded weekends")
            return out
    if n >= FINAL_N:
        out.update(state="NULL", reason=f"no pass by {FINAL_N} traded weekends")
    return out


# ---------------------------------------------------------------- driver
def score(snap_dir, status_only=False, now_ms=None, venue=None, journal=J, universe=None):
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    venue = venue or base.Venue()
    uni = universe if universe is not None else base.load_universe()
    uni_by_coin = {u["coin"]: u for u in uni}
    wk = base.read_csv(journal / "weekends.csv", W_COLS)
    done = set(wk.friday.astype(str)) if len(wk) else set()
    for w in ([] if status_only else base.due_weekends(now_ms, first=FIRST_FRIDAY)):
        fr = w["F"]
        if fr in done:
            continue
        w = dict(w, friday=fr)
        days = sorted({base.utc_day(t) for t in (w["E"] - 2 * base.H, w["E"] + 2 * base.H,
                                                 w["X1"] - 2 * base.H, w["X1"] + 2 * base.H)})
        books = base.read_days(snap_dir, "books", days)
        last = int(pd.to_numeric(books.ts).max()) if len(books) else 0
        if last < w["X1"] + base.MAX_GAP_MS and now_ms < w["X1"] + base.WAIT_BOOKS:
            log(fr, "waiting for the book recorder to pass X1 + 90 min")
            continue
        mk_e = base.read_days(snap_dir, "markets", [base.utc_day(w["E"])])
        mk_x = base.read_days(snap_dir, "markets", [base.utc_day(w["X1"])])
        rows, failed = [], False
        for u in uni:
            try:
                k = venue.candles(u["coin"], w["R"] - base.LISTED_MS - base.DAY, w["X1"] + base.H)
                f = venue.funding(u["coin"], w["E"] - base.H, w["X1"] + base.H)
            except Exception as e:                       # noqa: BLE001 - the whole weekend is retried next run
                log(fr, u["coin"], "fetch failed, weekend retried next run:", type(e).__name__, str(e)[:80])
                failed = True
                break
            rows.append(market_row(u, w, k, f))
        if failed:
            continue
        trades, wrow = weekend_rows(rows, w, books, mk_e, mk_x, uni_by_coin)
        base.append(journal / "trades.csv", trades, T_COLS)
        base.append(journal / "weekends.csv", [wrow], W_COLS)
        done.add(fr)
        log(fr, wrow["status"], "long", wrow["n_long"], "short", wrow["n_short"])
    wk = base.read_csv(journal / "weekends.csv", W_COLS)
    st = decision(wk)
    st.update({"weekends_rows": int(len(wk)),
               "by_status": {k: int(v) for k, v in wk.status.value_counts().items()} if len(wk) else {},
               "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    journal.mkdir(parents=True, exist_ok=True)
    (journal / "status.json").write_text(json.dumps(st, indent=1, default=float) + "\n")
    return st


def check_inputs(prereg_path):
    text = Path(prereg_path).read_text()
    lines = text.split("```inputs\n", 1)[1].split("```", 1)[0].splitlines()
    for line in lines:
        sha, rel = line.split()
        if hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != sha:
            raise SystemExit(f"input changed since the freeze: {rel}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("score", help="score due weekends and rewrite status.json")
    sc.add_argument("--snapshots", required=True, help="checkout of the data branch claude/xyz-books-data")
    sc.add_argument("--status", action="store_true", help="rewrite status.json from the journal, no fetch")
    a = ap.parse_args()
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    check_inputs(LANE / "PREREG.md")
    log(score(a.snapshots, a.status))


if __name__ == "__main__":
    main()
