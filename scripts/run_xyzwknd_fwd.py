"""xyzwknd_fwd (R463): R462's weekend fade of trade.xyz US-stock perps, tested forward on fresh weekends from
2026-11-13, as set out in experiments/xyzwknd_fwd/PREREG.md. Paper only: public endpoints, no key, no order.

The rule is R462's, frozen in scripts/xyzwknd_rule.py: W is the perp's move from Friday 20:00 (R) to Sunday 19:00 (E)
New York; when |W| >= 50 bp, fade it from E to Sunday 22:00 (X1). The universe is R462's (experiments/xyzwknd_v1/
universe.csv, 76 markets), a market listed at least 7 days before R. Two measures of that rule:
- A (decides): R462's own prices (the close of the last hourly candle before each instant, rule.price_at) and hourly
  funding, each fill charged that day's taker fee (claude/xyz-books-data markets/) plus the cost of a $1k market order
  on the side traded in the coin's recorded book snapshot nearest the instant (books/, within 90 minutes), else 10 bp,
  counted.
- B (tickets, must agree for a PASS): `tick`, run by a timed workflow, decides at E from the candles then available
  and walks the live order book for a $1k market order on the fade side (entry); at X1 it walks the book again on the
  other side (exit). The fee is the one listed at the tick. An exit not ticketed is priced at the first recorded
  snapshot after X1 (within 6 h), flagged.
Writes journal/tickets.csv (tick), journal/a_trades.csv, journal/b_trades.csv and journal/status.json (score), all
append-only except status.json.

usage:
  python scripts/run_xyzwknd_fwd.py tick                         take this weekend's due tickets (sleeps until E or X1)
  python scripts/run_xyzwknd_fwd.py score --snapshots DIR [--status]   score due weekends, rewrite status.json
"""
import argparse
import csv
import hashlib
import json
import math
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
import xyzwknd_rule as rule  # noqa: E402

LANE = ROOT / "experiments" / "xyzwknd_fwd"
J = LANE / "journal"
UNIVERSE = ROOT / "experiments" / "xyzwknd_v1" / "universe.csv"
INFO = "https://api.hyperliquid.xyz/info"
UA = "lab-research-fetch/1.0"
MIN, H, DAY = 60_000, rule.HOUR_MS, 86_400_000
# ---- the frozen rule (PREREG "Rule"); tests/test_xyzwknd_fwd.py checks these against the PREREG text
FIRST_FRIDAY = date(2026, 11, 13)
THETA_BP = 50.0
SIZE_USD, SIZE_REPORT = 1_000, 5_000
MAX_GAP_MS = 90 * MIN                 # a recorded snapshot prices a fill if it is this close to the instant
FALLBACK_BP = 10.0                    # cost of a fill with no usable snapshot (R457's and R459's)
BASE_TAKER_BP = 4.5                   # Hyperliquid tier-0 perp taker fee, one way, before the HIP-3 scale
LISTED_MS = 7 * DAY
SCORE_AFTER = 3 * H                   # a weekend is scored at least this long after X1 ...
WAIT_BOOKS = 48 * H                   # ... once the recorder has passed X1 + 90 min, or this long after X1 regardless
EARLY_MS, LATE_MS = 70 * MIN, 30 * MIN      # a tick run this early sleeps to the instant; entries end at E + 30 min
EXIT_LATE_MS = 6 * H                  # an exit is ticketed, or priced from a recorded snapshot, by X1 + 6 h
FUTILITY_N, INTERIM_N, FINAL_N = 15, 20, 30  # traded weekends
ALPHA_INTERIM, ALPHA_FINAL = 0.01, 0.04
B_COVERAGE = 2 / 3                    # share of A's read weekends that B must have ticketed
N_BOOT, SEED, TOP_K = 10_000, 463, 3
PACE_S = 1.5                          # between info requests (candleSnapshot weighs 20+ of 1,200 a minute)
TICK_COLS = ["friday", "phase", "coin", "status", "w_bp", "side", "tick_ts", "wall_ms", "bid", "ask", "mid",
             "cost_bp", "cost5k_bp", "growth", "fee_scale", "fee_bp"]
A_COLS = ["friday", "coin", "status", "w_bp", "side", "price_bp", "funding_bp", "gross_bp", "fee_bp", "book_bp",
          "fallback_fills", "fee_fallback", "net_1x", "net_2x", "net_3x", "book5k_bp", "net5k_1x"]
B_COLS = ["friday", "coin", "status", "w_bp", "side", "entry_ts", "entry_mid", "entry_cost_bp", "exit_ts", "exit_mid",
          "exit_cost_bp", "exit_src", "price_bp", "funding_bp", "fee_bp", "book_bp", "net_1x", "net_2x", "net_3x",
          "a_status"]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------- pure parts
def taker_fee_bp(growth, fee_scale):
    """One-way taker fee in bp of a HIP-3 perp at tier 0 (Hyperliquid's scaleIfHip3 and growth-mode scale)."""
    try:
        s = float(fee_scale)
    except (TypeError, ValueError):
        s = 1.0
    if not math.isfinite(s):
        s = 1.0
    scale = s + 1 if s < 1 else 2 * s
    return BASE_TAKER_BP * scale * (0.1 if str(growth).strip().lower() == "enabled" else 1.0)


def book_fill(book, side, sizes=(SIZE_USD, SIZE_REPORT)):
    """From an l2Book response, (bid, ask, mid, {size: cost bp of a market order on `side`}) or None if a side is empty.
    side is 'buy' or 'sell'; cost is the VWAP's distance from mid in bp, None if the 20 levels are too thin."""
    bids = [(float(x["px"]), float(x["sz"])) for x in book["levels"][0]]
    asks = [(float(x["px"]), float(x["sz"])) for x in book["levels"][1]]
    if not bids or not asks:
        return None
    bid, ask = bids[0][0], asks[0][0]
    mid = (bid + ask) / 2
    lv = asks if side == "buy" else bids
    out = {}
    for n in sizes:
        left, cost = float(n), 0.0
        for px, sz in lv:
            take = min(left, px * sz)
            cost += take * (px / mid - 1) * (1 if side == "buy" else -1)
            left -= take
            if left <= 1e-9:
                break
        out[n] = round(cost / n * 1e4, 3) if left <= 1e-9 else None
    return bid, ask, mid, out


def weekend_of(now_ms):
    """The weekend (rule.weekend dict, with 'friday' a date) whose Friday is the latest New York Friday at or before
    now; None if it is not a plain weekend."""
    d = datetime.fromtimestamp(now_ms / 1000, rule.NY).date()
    f = d - timedelta(days=(d.weekday() - 4) % 7)
    w = rule.weekend(f)
    return dict(w, friday=f) if w else None


def due_weekends(now_ms, first=FIRST_FRIDAY):
    """Weekends from `first` whose X1 is at least SCORE_AFTER before now."""
    last = datetime.fromtimestamp(now_ms / 1000, rule.NY).date()
    return [w for w in rule.fridays(first, last) if now_ms >= w["X1"] + SCORE_AFTER]


def nearest(books, coin, t, col, gap=MAX_GAP_MS):
    """books[col] (bp) of the coin's snapshot nearest t within `gap`; None if none or blank."""
    if books is None or not len(books) or col not in books:
        return None
    b = books[books.coin == coin]
    if not len(b):
        return None
    d = np.abs(b.ts.to_numpy(np.int64) - int(t))
    i = int(np.argmin(d))
    if d[i] > gap:
        return None
    v = pd.to_numeric(b[col], errors="coerce").iloc[i]
    return max(float(v), 0.0) if pd.notna(v) else None


def fee_of(markets, coin, uni_row):
    """(one-way taker fee bp, fell back): from that day's markets file, else the universe's settings."""
    if markets is not None and len(markets):
        m = markets[markets.coin == coin]
        if len(m):
            return taker_fee_bp(m.growthMode.iloc[-1], m.deployerFeeScale.iloc[-1]), 0
    return taker_fee_bp(uni_row["growth"], uni_row["fee_scale"]), 1


def score_a(u, w, k, f, books, mk_e, mk_x):
    """Measure A's row for one market and weekend. k: hourly candles (t, c); f: funding (time, rate)."""
    row = dict.fromkeys(A_COLS)
    row.update(friday=str(w["friday"]), coin=u["coin"])
    t = k.t.to_numpy("int64") if len(k) else np.array([], "int64")
    if not len(t) or t[0] > w["R"] - LISTED_MS:
        row["status"] = "not_listed"
        return row
    if u.get("ipo_424b4") and w["F"] <= u["ipo_424b4"]:
        row["status"] = "pre_ipo"
        return row
    x = rule.event_row(t, k.c.to_numpy("float64"), f.time.to_numpy("int64"), f.rate.to_numpy("float64"), w)
    if x["s"] == 0 or not math.isfinite(x["g_x1"]):
        row.update(status="unpriced", w_bp=x["W"] if math.isfinite(x["W"]) else None)
        return row
    row.update(w_bp=x["W"])
    if abs(x["W"]) < THETA_BP:
        row["status"] = "no_trade"
        return row
    s, name = x["s"], "xyz:" + u["coin"]
    fee_e, fb_e = fee_of(mk_e, name, u)
    fee_x, fb_x = fee_of(mk_x, name, u)
    side_in, side_out = ("buy", "sell") if s > 0 else ("sell", "buy")
    book, book5, fb = 0.0, 0.0, 0
    for t_, sd in ((w["E"], side_in), (w["X1"], side_out)):
        c = nearest(books, name, t_, f"{sd}_{SIZE_USD}_bp")
        if c is None:
            c, fb = FALLBACK_BP, fb + 1
        book += c
        c5 = nearest(books, name, t_, f"{sd}_{SIZE_REPORT}_bp")
        book5 = None if (book5 is None or c5 is None) else book5 + c5
    fee = fee_e + fee_x
    g = x["g_x1"]
    row.update(status="ok", side=s, price_bp=x["c_x1"], funding_bp=x["f_x1"], gross_bp=g, fee_bp=fee, book_bp=book,
               fallback_fills=fb, fee_fallback=fb_e + fb_x, net_1x=g - (fee + book), net_2x=g - 2 * (fee + book),
               net_3x=g - 3 * (fee + book), book5k_bp=book5,
               net5k_1x=None if book5 is None else g - (fee + book5))
    return row


def score_b(w, tickets, f_by_coin, books, a_rows):
    """Measure B's rows for one weekend from its tickets; exits not ticketed are priced from the recorder."""
    fr = str(w["friday"])
    tk = tickets[tickets.friday.astype(str) == fr] if len(tickets) else tickets
    ent = tk[(tk.phase == "entry") & (tk.status == "ok")] if len(tk) else tk
    ext = tk[(tk.phase == "exit") & (tk.status == "ok")] if len(tk) else tk
    a_st = {r["coin"]: r["status"] for r in a_rows}
    rows = []
    for _, e in ent.iterrows():
        coin = str(e.coin)
        row = dict.fromkeys(B_COLS)
        s = int(e.side)
        row.update(friday=fr, coin=coin, w_bp=float(e.w_bp), side=s, entry_ts=int(e.tick_ts),
                   entry_mid=float(e.mid), entry_cost_bp=float(e.cost_bp), a_status=a_st.get(coin))
        x = ext[ext.coin.astype(str) == coin]
        if len(x):
            x = x.iloc[0]
            xt, xmid, xcost, src, xfee = int(x.tick_ts), float(x.mid), float(x.cost_bp), "tick", float(x.fee_bp)
        else:
            xt, xmid, xcost, src, xfee = recorder_exit(books, "xyz:" + coin, w["X1"], "sell" if s > 0 else "buy")
            xfee = float(e.fee_bp) if xfee is None else xfee
        if xmid is None or xcost is None or not (xmid > 0 and float(e.mid) > 0):
            row.update(status="unpriced", exit_src=src)
            rows.append(row)
            continue
        f = f_by_coin.get(coin)
        fund = 0.0 if f is None or not len(f) else rule.funding_sum(
            f.time.to_numpy("int64"), f.rate.to_numpy("float64"), int(e.tick_ts), xt)
        price = s * 1e4 * math.log(xmid / float(e.mid))
        funding = -s * 1e4 * fund
        fee = float(e.fee_bp) + xfee
        book = float(e.cost_bp) + xcost
        g = price + funding
        row.update(status="ok", exit_ts=xt, exit_mid=xmid, exit_cost_bp=xcost, exit_src=src, price_bp=price,
                   funding_bp=funding, fee_bp=fee, book_bp=book, net_1x=g - (fee + book),
                   net_2x=g - 2 * (fee + book), net_3x=g - 3 * (fee + book))
        rows.append(row)
    return rows


def recorder_exit(books, coin, x1, side):
    """(ts, mid, cost bp, 'recorder', None) of the coin's first recorded snapshot in [X1, X1 + EXIT_LATE_MS]."""
    col = f"{side}_{SIZE_USD}_bp"
    if books is None or not len(books) or col not in books:
        return None, None, None, "none", None
    b = books[(books.coin == coin) & (books.ts >= x1) & (books.ts <= x1 + EXIT_LATE_MS)].sort_values("ts")
    for _, r in b.iterrows():
        c = pd.to_numeric(pd.Series([r[col]]), errors="coerce").iloc[0]
        bid, ask = float(r.bid), float(r.ask)
        if pd.notna(c) and bid > 0 and ask > 0:
            return int(r.ts), (bid + ask) / 2, max(float(c), 0.0), "recorder", None
    return None, None, None, "none", None


def weekly(tr, col="net_1x"):
    """One value per traded weekend (the mean over its markets with status ok), in calendar order."""
    if not len(tr):
        return pd.Series(dtype=float)
    ok = tr[tr.status == "ok"].copy()
    ok[col] = pd.to_numeric(ok[col], errors="coerce")
    return ok.groupby(ok.friday.astype(str))[col].mean().sort_index() if len(ok) else pd.Series(dtype=float)


def boot_p(x, n_boot=N_BOOT, seed=SEED):
    """One-sided p: the share of resampled means (whole weekends, with replacement) at or below 0."""
    x = np.asarray(x, float)
    rng = np.random.default_rng(seed)
    m = x[rng.integers(0, len(x), size=(n_boot, len(x)))].mean(1)
    return float((m <= 0).mean())


def decision(a, b):
    """The registered decision on A's weekend nets, with B's tickets as a fidelity condition."""
    x1 = weekly(a, "net_1x")
    n = len(x1)
    s = {"traded_weekends": n}
    for k in (1, 2, 3):
        x = weekly(a, f"net_{k}x")
        s[f"a_mean_{k}x_bp"] = float(x.mean()) if n else None
    if n >= FUTILITY_N and x1.iloc[:FUTILITY_N].mean() <= 0:
        s["decision"] = f"NULL (futility at {FUTILITY_N} traded weekends)"
        return s
    for look, alpha in ((INTERIM_N, ALPHA_INTERIM), (FINAL_N, ALPHA_FINAL)):
        if n < look:
            break
        a1 = x1.iloc[:look]
        a2 = weekly(a, "net_2x").reindex(a1.index)
        p = boot_p(a1.to_numpy())
        trim = float(np.sort(a1.to_numpy())[:-TOP_K].mean())
        bw = weekly(b, "net_1x")
        bw = bw[bw.index.isin(a1.index)]
        cover = len(bw) / look
        ok_a = a1.mean() > 0 and p < alpha and a2.mean() > 0 and trim > 0
        s.update({f"p_at_{look}": p, f"mean_without_best3_at_{look}_bp": trim, f"b_weekends_at_{look}": len(bw),
                  f"b_mean_1x_at_{look}_bp": float(bw.mean()) if len(bw) else None})
        if ok_a and cover >= B_COVERAGE and bw.mean() > 0:
            s["decision"] = f"PASS at {look} traded weekends (p {p:.4f}; tickets agree on {len(bw)} weekends)"
            return s
        if look == FINAL_N:
            if not ok_a:
                s["decision"] = f"NULL at {FINAL_N} traded weekends (p {p:.4f})"
            elif cover < B_COVERAGE:
                s["decision"] = (f"PARTIAL at {FINAL_N}: A passes (p {p:.4f}) but tickets cover only {len(bw)} "
                                 f"of {look} weekends")
            else:
                s["decision"] = f"NULL at {FINAL_N}: A passes (p {p:.4f}) but the ticketed fills lose"
            return s
    s["decision"] = (f"pending ({n} traded weekends; futility read at {FUTILITY_N}, interim at {INTERIM_N}, "
                     f"final at {FINAL_N})")
    return s


# ---------------------------------------------------------------- venue
class Venue:
    """Hyperliquid's public info endpoint (no key), paced."""

    def __init__(self, pace=PACE_S):
        self.pace = pace

    def post(self, body, tries=5):
        delay, err = 2.0, None
        for _ in range(tries):
            try:
                req = urllib.request.Request(INFO, json.dumps(body).encode(),
                                             {"Content-Type": "application/json", "User-Agent": UA})
                with urllib.request.urlopen(req, timeout=30) as r:
                    d = json.loads(r.read())
                time.sleep(self.pace)
                return d
            except urllib.error.HTTPError as e:
                err = e
                if e.code in (400, 404):
                    break
            except (OSError, ValueError) as e:
                err = e
            time.sleep(delay)
            delay *= 2
        raise RuntimeError(f"{body.get('type')}: {err}")

    def candles(self, coin, start, end):
        k = self.post({"type": "candleSnapshot", "req": {"coin": "xyz:" + coin, "interval": "1h",
                                                         "startTime": int(start), "endTime": int(end)}})
        d = pd.DataFrame([{"t": int(x["t"]), "c": float(x["c"])} for x in k], columns=["t", "c"])
        return d.drop_duplicates("t").sort_values("t").reset_index(drop=True)

    def funding(self, coin, start, end):
        out, s = [], int(start)
        while s < end:
            page = self.post({"type": "fundingHistory", "coin": "xyz:" + coin, "startTime": s, "endTime": int(end)})
            if not page:
                break
            out += [{"time": int(x["time"]), "rate": float(x["fundingRate"])} for x in page]
            s = int(page[-1]["time"]) + 1
            if len(page) < 500:
                break
        return pd.DataFrame(out, columns=["time", "rate"]).drop_duplicates("time").sort_values("time")

    def book(self, coin):
        return self.post({"type": "l2Book", "coin": "xyz:" + coin})

    def fees(self):
        """{coin without prefix: (growthMode, deployerFeeScale)} as listed now."""
        meta = self.post({"type": "meta", "dex": "xyz"})
        return {u["name"].split(":", 1)[-1]: (u.get("growthMode", ""), u.get("deployerFeeScale", ""))
                for u in meta["universe"]}


# ---------------------------------------------------------------- journal
def read_csv(p, cols):
    p = Path(p)
    return pd.read_csv(p) if p.exists() and p.stat().st_size else pd.DataFrame(columns=cols)


def append(p, rows, cols):
    if not rows:
        return
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=cols).to_csv(p, mode="a", header=not p.exists(), index=False, lineterminator="\n")


def load_universe(path=UNIVERSE):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------- tick (measure B)
def tick(venue=None, now=None, sleep=None, journal=J, universe=None):
    """Take this weekend's due tickets: the entry at E, else the exit at X1. Returns the phase done or a reason."""
    venue = venue or Venue()
    now = now or (lambda: int(time.time() * 1000))
    sleep = sleep or time.sleep
    uni = universe if universe is not None else load_universe()
    w = weekend_of(now())
    if w is None or w["friday"] < FIRST_FRIDAY:
        return "no weekend"
    fr = str(w["friday"])
    tk = read_csv(journal / "tickets.csv", TICK_COLS)
    tk = tk[tk.friday.astype(str) == fr] if len(tk) else tk
    live = tk[tk.status != "fetch_failed"] if len(tk) else tk      # a run whose every fetch failed is retried
    has_entry = bool(len(live)) and (live.phase == "entry").any()
    has_exit = bool(len(live)) and (live.phase == "exit").any()
    if not has_entry:
        if now() > w["E"] + LATE_MS:
            return "entry missed"
        phase, t0 = "entry", w["E"]
    elif not has_exit:
        if now() > w["X1"] + EXIT_LATE_MS:
            return "exit missed"
        phase, t0 = "exit", w["X1"]
    else:
        return "done"
    if now() < t0 - EARLY_MS:
        return f"{phase} not due"
    while now() < t0:
        sleep(min(60.0, (t0 - now()) / 1000 + 0.5))
    fees = venue.fees()
    rows = []
    if phase == "entry":
        for u in uni:
            rows.append(entry_ticket(venue, u, w, fees, now))
    else:
        for _, e in tk[(tk.phase == "entry") & (tk.status == "ok")].iterrows():
            rows.append(exit_ticket(venue, e, fr, fees, now))
        if not rows:
            rows.append(dict(dict.fromkeys(TICK_COLS), friday=fr, phase="exit", coin="", status="no_entry"))
    append(journal / "tickets.csv", rows, TICK_COLS)
    log(fr, phase, pd.Series([r["status"] for r in rows]).value_counts().to_dict())
    return phase


def entry_ticket(venue, u, w, fees, now):
    row = dict.fromkeys(TICK_COLS)
    row.update(friday=str(w["friday"]), phase="entry", coin=u["coin"])
    try:
        k = venue.candles(u["coin"], w["R"] - LISTED_MS - DAY, now())
    except Exception as e:                              # noqa: BLE001 - one market's failure is that market's
        row["status"] = "fetch_failed"
        log(u["coin"], "candles failed:", type(e).__name__, str(e)[:80])
        return row
    t = k.t.to_numpy("int64") if len(k) else np.array([], "int64")
    if not len(t) or t[0] > w["R"] - LISTED_MS:
        row["status"] = "not_listed"
        return row
    if u.get("ipo_424b4") and w["F"] <= u["ipo_424b4"]:
        row["status"] = "pre_ipo"
        return row
    c = k.c.to_numpy("float64")
    pr, pe = rule.price_at(t, c, w["R"]), rule.price_at(t, c, w["E"])
    if not (pr > 0 and pe > 0) or pe == pr:
        row["status"] = "unpriced"
        return row
    W = 1e4 * math.log(pe / pr)
    row["w_bp"] = W
    if abs(W) < THETA_BP:
        row["status"] = "no_trade"
        return row
    s = -1 if W > 0 else 1
    return fill_ticket(venue, row, u["coin"], s, "buy" if s > 0 else "sell", fees, now)


def exit_ticket(venue, e, fr, fees, now):
    row = dict.fromkeys(TICK_COLS)
    s = int(e.side)
    row.update(friday=fr, phase="exit", coin=str(e.coin), w_bp=float(e.w_bp))
    return fill_ticket(venue, row, str(e.coin), s, "sell" if s > 0 else "buy", fees, now)


def fill_ticket(venue, row, coin, s, side, fees, now):
    row["side"] = s
    try:
        bk = venue.book(coin)
        wall = now()
        got = book_fill(bk, side)
    except Exception as e:                              # noqa: BLE001
        row["status"] = "fetch_failed"
        log(coin, "book failed:", type(e).__name__, str(e)[:80])
        return row
    if got is None or got[3][SIZE_USD] is None:
        row["status"] = "thin_book"
        return row
    bid, ask, mid, cost = got
    g, sc = fees.get(coin, ("", ""))
    row.update(status="ok", tick_ts=int(bk.get("time", wall)), wall_ms=int(wall), bid=bid, ask=ask, mid=mid,
               cost_bp=cost[SIZE_USD], cost5k_bp=cost[SIZE_REPORT], growth=g, fee_scale=sc,
               fee_bp=taker_fee_bp(g, sc))
    return row


# ---------------------------------------------------------------- score (measures A and B)
def read_days(snap_dir, sub, days, dex="xyz"):
    got = [pd.read_csv(p) for p in (Path(snap_dir) / sub / f"{d}.csv" for d in days) if p.exists()]
    d = pd.concat(got, ignore_index=True) if got else pd.DataFrame(columns=["dex", "coin", "ts"])
    return d[d.dex.astype(str) == dex].reset_index(drop=True) if len(d) else d


def utc_day(ms):
    return pd.Timestamp(int(ms), unit="ms").strftime("%Y-%m-%d")


def score(snap_dir, status_only=False, now_ms=None, venue=None, journal=J, universe=None):
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    venue = venue or Venue()
    uni = universe if universe is not None else load_universe()
    a = read_csv(journal / "a_trades.csv", A_COLS)
    done = set(a.friday.astype(str)) if len(a) else set()
    tickets = read_csv(journal / "tickets.csv", TICK_COLS)
    for w in ([] if status_only else due_weekends(now_ms)):
        fr = w["F"]
        if fr in done:
            continue
        w = dict(w, friday=fr)
        days = sorted({utc_day(t) for t in (w["E"] - 2 * H, w["E"] + 2 * H, w["X1"] - 2 * H,
                                            w["X1"] + EXIT_LATE_MS)})
        books = read_days(snap_dir, "books", days)
        last = int(pd.to_numeric(books.ts).max()) if len(books) else 0
        if last < w["X1"] + MAX_GAP_MS and now_ms < w["X1"] + WAIT_BOOKS:
            log(fr, "waiting for the book recorder to pass X1 + 90 min")
            continue
        mk_e = read_days(snap_dir, "markets", [utc_day(w["E"])])
        mk_x = read_days(snap_dir, "markets", [utc_day(w["X1"])])
        a_rows, f_by_coin, failed = [], {}, False
        for u in uni:
            try:
                k = venue.candles(u["coin"], w["R"] - LISTED_MS - DAY, w["X1"] + H)
                f = venue.funding(u["coin"], w["E"] - H, w["X1"] + EXIT_LATE_MS)
            except Exception as e:                      # noqa: BLE001 - the whole weekend is retried next run
                log(fr, u["coin"], "fetch failed, weekend retried next run:", type(e).__name__, str(e)[:80])
                failed = True
                break
            f_by_coin[u["coin"]] = f
            a_rows.append(score_a(u, w, k, f, books, mk_e, mk_x))
        if failed:
            continue
        b_rows = score_b(w, tickets, f_by_coin, books, a_rows)
        append(journal / "a_trades.csv", a_rows, A_COLS)
        append(journal / "b_trades.csv", b_rows, B_COLS)
        done.add(fr)
        log(fr, "A", pd.Series([r["status"] for r in a_rows]).value_counts().to_dict(), "B", len(b_rows))
    a = read_csv(journal / "a_trades.csv", A_COLS)
    b = read_csv(journal / "b_trades.csv", B_COLS)
    st = decision(a, b)
    st.update(summary(a, b, tickets))
    journal.mkdir(parents=True, exist_ok=True)
    (journal / "status.json").write_text(json.dumps(st, indent=1, default=float) + "\n")
    return st


def summary(a, b, tickets):
    """Reported only: counts, fallbacks, B's own means, the A-B gap on common trades, capacity at $5k, tick latency."""
    num = lambda d, c: pd.to_numeric(d[c], errors="coerce") if len(d) else pd.Series(dtype=float)  # noqa: E731
    s = {"a_rows": int(len(a)), "a_by_status": {k: int(v) for k, v in a.status.value_counts().items()} if len(a)
         else {}, "a_fallback_fills": int(num(a, "fallback_fills").fillna(0).sum()),
         "a_fee_fallbacks": int(num(a, "fee_fallback").fillna(0).sum())}
    ok = a[a.status == "ok"] if len(a) else a
    s["a_trades"] = int(len(ok))
    s["a_mean_1x_bp_per_trade"] = float(num(ok, "net_1x").mean()) if len(ok) else None
    s["a_mean_5k_1x_bp_per_trade"] = float(num(ok, "net5k_1x").mean()) if len(ok) else None
    bok = b[b.status == "ok"] if len(b) else b
    s["b_rows"], s["b_trades"] = int(len(b)), int(len(bok))
    s["b_exits_from_recorder"] = int((bok.exit_src == "recorder").sum()) if len(bok) else 0
    bw = weekly(b, "net_1x")
    s["b_weekends"] = int(len(bw))
    for k in (1, 2, 3):
        s[f"b_mean_{k}x_bp"] = float(weekly(b, f"net_{k}x").mean()) if len(bw) else None
    if len(bok) and len(ok):
        m = bok.merge(ok, on=["friday", "coin"], suffixes=("_b", "_a"))
        s["common_trades"] = int(len(m))
        if len(m):
            s["gap_a_minus_b_1x_bp"] = float((num(m, "net_1x_a") - num(m, "net_1x_b")).mean())
    if len(tickets):
        e = tickets[(tickets.phase == "entry") & (tickets.status == "ok")]
        if len(e):
            fr = pd.to_datetime(e.friday.astype(str)).dt.date
            lag = [(int(t) - rule.weekend(f)["E"]) / 1000 for t, f in zip(e.tick_ts, fr) if rule.weekend(f)]
            s["entry_lag_s_median"] = float(np.median(lag)) if lag else None
            s["entry_lag_s_max"] = float(np.max(lag)) if lag else None
    return s


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
    sub.add_parser("tick", help="take this weekend's due tickets")
    sc = sub.add_parser("score", help="score due weekends and rewrite status.json")
    sc.add_argument("--snapshots", required=True, help="checkout of the data branch claude/xyz-books-data")
    sc.add_argument("--status", action="store_true", help="rewrite status.json from the journal, no fetch")
    a = ap.parse_args()
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    check_inputs(LANE / "PREREG.md")
    if a.cmd == "tick":
        log(tick())
    else:
        log(score(a.snapshots, a.status))


if __name__ == "__main__":
    main()
