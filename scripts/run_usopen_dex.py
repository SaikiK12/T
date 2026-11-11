"""usopen_dex_fwd (R457): R371's US-open picks traded on Lighter (book L, decides) and Hyperliquid (book H, reported),
the two perp venues the lab found open to a French resident, at each venue's own minute prices, funding and measured
book cost. The rule is frozen in experiments/usopen_dex_fwd/PREREG.md.

R371 (scripts/forward_usopen.py) writes, within two minutes of 10:00 New York (D) on each NYSE day, the 50 most traded
Binance USDT perps with their move since 00:00 UTC. This lane keeps the names that trade on the venue (a mapped symbol
with a one-minute bar in the hour before D whose close is within 10% of Binance's close at D), needs 30 of them, and
picks the 3 strongest long and the 3 weakest short with R371's own `pick`. Fills are the open of the venue's first
one-minute bar at or after D + 3 minutes and 24:00 UTC + 3 minutes, each within 5 minutes; funding is the venue's
hourly settlements after the entry minute up to the exit minute. Hyperliquid's book H uses its main dex for crypto
and R451's xyz (HIP-3) coins for stocks, indices and commodities. Each fill pays the venue's taker fee (Lighter's
Standard account 0; Hyperliquid tier 0 4.5 bp on the main dex, R453's HIP-3 fee on xyz) plus the cost of a $1k
market order on its side in the venue's book snapshot nearest the fill within 90 minutes (claude/xyz-books-data:
lighter/books; main/books and books), else R371's 10 bp fallback, flagged. Nothing is chosen after D: the picks
come from R371's ticket and bars before D.

Single writer of experiments/usopen_dex_fwd/journal/. A day is scored once, at the first run at least 3 hours after its
exit; a fetch error leaves it for the next run, a missing price makes it "unpriced" for good. Paper only: public
endpoints, no key, no order.

usage: python scripts/run_usopen_dex.py --snapshots DIR [--status]
"""
import argparse
import csv
import importlib.util
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import carrylane, prereg  # noqa: E402



def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rule = _load("usopen_rule")              # R371's frozen rule: pick, costs, decision
hs = _load("run_flow_hlstock")           # R451's Binance TradFi symbol -> xyz coin
mc = _load("run_flow_hlstock_mc")        # R453's HIP-3 taker fee from xyz's markets/ files

LANE = ROOT / "experiments" / "usopen_dex_fwd"
J = LANE / "journal"
PARENT = ROOT / "experiments" / "usopen_fwd" / "journal"
MIN, H, DAY = rule.MIN, rule.H, rule.DAY
FWD_START = int(pd.Timestamp("2026-11-12", tz="UTC").value // 10**6)
BOOKS = ("L", "H")                          # L decides, H is reported
FEE_L, FEE_HL_MAIN = 0.0, 4.5e-4           # taker fee per fill: Lighter Standard account, Hyperliquid tier 0 main dex
BOOK_DIR = {"L": (("lighter/books",), "symbol", "1k", "10k"), "H": (("main/books", "books"), "coin", "1000", "10000")}
LIGHTER_ALIAS = {"CL": "WTI", "BZ": "BRENTOIL"}
FILL_WINDOW_MIN = 5                         # a fill is the first bar within 5 minutes of the target minute (R371)
MAX_GAP_MIN = 90                            # nearest book snapshot within 90 minutes of the fill
MAX_PX_GAP = 0.10                           # venue close before D within 10% of Binance's close at D
SCORE_AFTER = 3 * H                         # score at the first run at least 3 h after the exit
PREFIXES = ("1000000", "1000")
SCORED_COLS = ["ticket", "book", "day_ms", "d_ms", "status", "eligible", "longs", "shorts", "price", "funding",
               "gross", "cost_1x", "net_1x", "net_2x", "net_3x", "cost_10k", "net_10k_1x", "fallback_fills",
               "scored_at"]
LEG_COLS = ["ticket", "book", "side", "symbol", "venue_symbol", "rank", "sig", "entry_t", "entry_px", "exit_t",
            "exit_px", "ret", "fund", "cost_in", "cost_out", "cost_in_10k", "cost_out_10k"]


def log(*a):
    print(time.strftime("%H:%M:%S", time.gmtime()), *a, flush=True)


def day_label(t):
    return pd.Timestamp(int(t), unit="ms", tz="UTC").strftime("%Y-%m-%d")


def check_inputs(prereg_path):
    """Every file in the PREREG's inputs block still hashes to its frozen sha256."""
    block = re.search(r"```inputs\n(.*?)```", Path(prereg_path).read_text(), re.S).group(1)
    for line in block.strip().splitlines():
        want, rel = line.split()
        got = prereg.sha256_file(ROOT / rel)
        if got != want:
            raise prereg.PreregError(f"{rel}: sha256 {got} != frozen {want}")


# ---------------------------------------------------------------- pure parts (tests/test_run_usopen_dex.py)
def venue_symbol(book, symbol, names):
    """The venue's perp for a Binance USDT symbol, None if none is listed.
    Lighter: the base, its alias (CL -> WTI, BZ -> BRENTOIL), the base without a 1000/1000000 prefix, or with 1000.
    Hyperliquid: the main-dex base, or the prefix as Hyperliquid's k; else R451's xyz coin (`xyz:<base or alias>`)."""
    if not symbol.endswith("USDT"):
        return None
    base = symbol[:-4]
    cands = [base]
    if book == "L" and base in LIGHTER_ALIAS:
        cands.append(LIGHTER_ALIAS[base])
    for p in PREFIXES:
        if base.startswith(p):
            cands += ["k" + base[len(p):]] if book == "H" else [base[len(p):]]
    if book == "L":
        cands.append("1000" + base)
    hit = next((c for c in cands if c in names), None)
    return hit if hit or book == "L" else hs.xyz_coin(symbol, names)


def fee_of(book, vsym, fees, day):
    """Taker fee of one fill: 0 on Lighter, 4.5 bp on Hyperliquid's main dex, R453's HIP-3 fee on xyz (9 bp when the
    markets/ files list none for that day)."""
    if book == "L":
        return FEE_L
    return mc.fee_at(fees or {}, vsym, day) if vsym.startswith("xyz:") else FEE_HL_MAIN


def close_before(bars, t):
    """Close of the last one-minute bar that opened in [t - 60 min, t), or None."""
    w = bars[(bars.t >= t - 60 * MIN) & (bars.t < t) & (bars.close > 0)]
    return float(w.close.iloc[-1]) if len(w) else None


def fill_open(bars, t):
    """Open of the first one-minute bar that opened in [t, t + 5 min], or None."""
    w = bars[(bars.t >= t) & (bars.t <= t + FILL_WINDOW_MIN * MIN) & (bars.open > 0)]
    return float(w.open.iloc[0]) if len(w) else None


def funding_sum(fund, entry_t, exit_t):
    """Settlements whose hour is after the entry minute and not after the exit minute (positive = longs pay)."""
    if fund is None or fund.empty:
        return 0.0
    hour = fund.t.to_numpy(np.int64) // H * H
    return float(fund.rate.to_numpy(float)[(hour > entry_t) & (hour <= exit_t)].sum())


def fill_cost(books, coin_col, coin, t, col):
    """bp/1e4 of a market order on `col` in the coin's snapshot nearest t within 90 minutes; None if none or blank."""
    if books is None or books.empty or col not in books:
        return None
    b = books[books[coin_col] == coin]
    if b.empty:
        return None
    gap = np.abs(b.ts.to_numpy(np.int64) - int(t))
    i = int(np.argmin(gap))
    if gap[i] > MAX_GAP_MIN * MIN:
        return None
    v = b[col].iloc[i]
    return max(float(v), 0.0) / 1e4 if pd.notna(v) else None


def leg_costs(book, books, vsym, side, entry_t, exit_t, fee):
    """(entry, exit, entry at $10k, exit at $10k, fallbacks used): the fee plus the book cost of the side traded, a long
    buying in and selling out, a short the reverse; R371's 10 bp fallback for a missing snapshot or a thin book."""
    _, coin_col, k1, k10 = BOOK_DIR[book]
    sides = ("buy", "sell") if side == "long" else ("sell", "buy")
    out, fb = [], 0
    for size in (k1, k10):
        for s, t in zip(sides, (entry_t, exit_t)):
            c = fill_cost(books, coin_col, vsym, t, f"{s}_{size}_bp")
            if c is None:
                c = rule.SPREAD_FALLBACK
                fb += size == k1
            out.append(fee + c)
    return out[0], out[1], out[2], out[3], fb


# ---------------------------------------------------------------- venue clients (public, paced in lab/carrylane)
def _frame(rows):
    if not rows:
        return pd.DataFrame(columns=["t", "open", "close"])
    df = pd.DataFrame({"t": [int(r["t"]) for r in rows], "open": [float(r["o"]) for r in rows],
                       "close": [float(r["c"]) for r in rows]})
    return df.drop_duplicates("t", keep="last").sort_values("t", ignore_index=True)


class Lighter:
    def names(self):
        return {d["symbol"] for d in carrylane._lighter_details()}

    def minutes(self, sym, start, end):
        return _frame(carrylane._lighter("candles", market_id=carrylane._lighter_id(sym), resolution="1m",
                                         start_timestamp=int(start), end_timestamp=int(end), count_back=0).get("c"))

    def funding(self, sym, start, end):
        return carrylane.lighter_funding(sym, start, end)


class Hyperliquid:
    def names(self):
        return {u["name"] for dex in ("", "xyz")
                for u in carrylane._json(carrylane.HL, {"type": "meta", "dex": dex})["universe"]}

    def minutes(self, sym, start, end):
        time.sleep(1.1)                 # candleSnapshot weighs about 21 of the 1,200 a minute per IP
        return _frame(carrylane._json(carrylane.HL, {"type": "candleSnapshot", "req": {
            "coin": sym, "interval": "1m", "startTime": int(start), "endTime": int(end)}}))

    def funding(self, sym, start, end):
        return carrylane.hl_funding(sym, start, end)


VENUES = {"L": Lighter, "H": Hyperliquid}


# ---------------------------------------------------------------- one day
def score_day(book, tk, sig, venue, names, books, fees=None):
    """(scored row, leg rows) for one R371 ticket on one venue. Raises on a fetch error (the day is retried)."""
    D, day = int(tk["d_ms"]), int(tk["day_ms"])
    entry_t, exit_t = D + rule.ENTRY_LAG_MIN * MIN, day + DAY + rule.EXIT_LAG_MIN * MIN
    row = {"ticket": tk["ticket"], "book": book, "day_ms": day, "d_ms": D}
    rows, bars = [], {}
    for r in sig.itertuples(index=False):
        v = venue_symbol(book, r.symbol, names)
        if v is None:
            continue
        b = venue.minutes(v, D - 60 * MIN, entry_t + FILL_WINDOW_MIN * MIN)
        px = close_before(b, D)
        if px is None or not np.isfinite(r.c_e) or abs(px / float(r.c_e) - 1) > MAX_PX_GAP:
            continue
        bars[r.symbol] = (v, b)
        rows.append({"symbol": r.symbol, "rank": int(r.rank), "sig": float(r.sig)})
    cs = pd.DataFrame(rows, columns=["symbol", "rank", "sig"])
    row["eligible"] = int(cs.sig.notna().sum())
    picked = rule.pick(cs) if len(cs) else None
    if picked is None:
        return {**row, "status": "no_book"}, []
    longs, shorts, _ = picked
    row.update(longs="|".join(longs), shorts="|".join(shorts))
    legs, fb = [], 0
    for side, syms in (("long", longs), ("short", shorts)):
        for s in syms:
            v, b = bars[s]
            entry = fill_open(b, entry_t)
            exit_ = fill_open(venue.minutes(v, exit_t, exit_t + FILL_WINDOW_MIN * MIN), exit_t)
            if entry is None or exit_ is None:
                return {**row, "status": "unpriced"}, []
            fund = funding_sum(venue.funding(v, entry_t - H, exit_t + H), entry_t, exit_t)
            ci, co, ci10, co10, f = leg_costs(book, books, v, side, entry_t, exit_t, fee_of(book, v, fees,
                                                                                            day_label(D)))
            fb += f
            g = cs[cs.symbol == s].iloc[0]
            legs.append({"ticket": tk["ticket"], "book": book, "side": side, "symbol": s, "venue_symbol": v,
                         "rank": int(g["rank"]), "sig": float(g.sig), "entry_t": entry_t, "entry_px": entry,
                         "exit_t": exit_t, "exit_px": exit_, "ret": exit_ / entry - 1, "fund": fund, "cost_in": ci,
                         "cost_out": co, "cost_in_10k": ci10, "cost_out_10k": co10})
    lo = [x for x in legs if x["side"] == "long"]
    sh = [x for x in legs if x["side"] == "short"]
    price, funding = rule.book_return(lo, sh)
    cost = rule.web_cost([x["cost_in"] + x["cost_out"] for x in lo], [x["cost_in"] + x["cost_out"] for x in sh])
    cost10 = rule.web_cost([x["cost_in_10k"] + x["cost_out_10k"] for x in lo],
                           [x["cost_in_10k"] + x["cost_out_10k"] for x in sh])
    gross = price + funding
    row.update(status="ok", price=price, funding=funding, gross=gross, cost_1x=cost,
               **{f"net_{k}x": gross - k * cost for k in (1, 2, 3)}, cost_10k=cost10, net_10k_1x=gross - cost10,
               fallback_fills=fb)
    return row, legs


# ---------------------------------------------------------------- journal
def read_csv(p):
    return pd.read_csv(p) if Path(p).exists() and Path(p).stat().st_size else pd.DataFrame()


def append(p, rows, cols):
    if not rows:
        return
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    new = not p.exists() or p.stat().st_size == 0
    with open(p, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore", lineterminator="\n")
        if new:
            w.writeheader()
        w.writerows(rows)


def read_days(snap_dir, subs, days):
    fs = [Path(snap_dir) / sub / f"{d}.csv" for sub in subs for d in sorted(days)]
    fs = [f for f in fs if f.exists()]
    return pd.concat([pd.read_csv(f) for f in fs], ignore_index=True) if fs else pd.DataFrame()


def read_fees(snap_dir, day):
    """R453's {xyz coin: [(day, fee)]} from xyz's markets/ files up to `day`."""
    fs = sorted(f for f in (Path(snap_dir) / "markets").glob("*.csv") if f.stem <= day)
    return mc.fee_lookup(pd.concat([pd.read_csv(f) for f in fs], ignore_index=True)) if fs else {}


def due(now_ms):
    """R371 tickets from FWD_START whose exit is at least SCORE_AFTER old: [(ticket row, its 50-name table)]."""
    tk, sg = read_csv(PARENT / "tickets.csv"), read_csv(PARENT / "signals.csv")
    if tk.empty:
        return []
    tk = tk[(tk.status == "ok") & (tk.day_ms >= FWD_START)]
    out = []
    for r in tk.to_dict("records"):
        exit_t = int(r["day_ms"]) + DAY + rule.EXIT_LAG_MIN * MIN
        if now_ms >= exit_t + SCORE_AFTER:
            out.append((r, sg[sg.ticket == r["ticket"]]))
    return out


def forward(snap_dir, status_only=False, now_ms=None, venues=None):
    now_ms = now_ms or int(time.time() * 1000)
    venues = venues or {b: VENUES[b]() for b in BOOKS}
    if not status_only:
        done = read_csv(J / "scored.csv")
        seen = set(zip(done.ticket, done.book)) if len(done) else set()
        for book in BOOKS:
            todo = [(t, s) for t, s in due(now_ms) if (t["ticket"], book) not in seen]
            if not todo:
                continue
            try:
                names = venues[book].names()
            except Exception as e:                      # noqa: BLE001 - the venue is down: next run
                log(book, "listing failed, retried next run:", type(e).__name__)
                continue
            for tk, sig in todo:
                days = {day_label(int(tk["d_ms"]) + k * H) for k in range(-2, 13)}
                days |= {day_label(int(tk["day_ms"]) + DAY + k * H) for k in (-2, 0, 2)}
                try:
                    books = read_days(snap_dir, BOOK_DIR[book][0], days)
                    fees = read_fees(snap_dir, day_label(int(tk["d_ms"]))) if book == "H" else None
                    row, legs = score_day(book, tk, sig, venues[book], names, books, fees)
                except Exception as e:                  # noqa: BLE001 - a fetch error: the day is retried
                    log(book, tk["ticket"], "fetch failed, retried next run:", type(e).__name__, str(e)[:120])
                    continue
                row["scored_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                append(J / "scored.csv", [row], SCORED_COLS)
                append(J / "legs.csv", legs, LEG_COLS)
                log(book, tk["ticket"], row["status"], "eligible", row.get("eligible"))
    return write_status(now_ms)


def write_status(now_ms):
    df = read_csv(J / "scored.csv")
    st = {"registry": "R457", "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_ms / 1000))}
    for book in BOOKS:
        d = df[df.book == book] if len(df) else df
        ok = d[d.status == "ok"] if len(d) else d
        if len(ok):
            s, v = rule.decision(ok.day_ms.to_numpy(np.int64), ok.net_1x.to_numpy(float), ok.net_2x.to_numpy(float))
            s["mean_3x"] = float(ok.net_3x.mean())
            s["mean_10k_1x"] = float(ok.net_10k_1x.mean())
            s["mean_cost"] = float(ok.cost_1x.mean())
            s["fallback_fill_share"] = float(ok.fallback_fills.sum() / (12 * len(ok)))
        else:
            s, v = rule.summarize([], []), f"pending (0 of {rule.N_DECIDE} scored)"
        st[book] = {"decision": v if book == "L" else f"reported only ({v})", "summary": s,
                    "no_book": int((d.status == "no_book").sum()) if len(d) else 0,
                    "unpriced": int((d.status == "unpriced").sum()) if len(d) else 0}
    J.mkdir(parents=True, exist_ok=True)
    (J / "status.json").write_text(json.dumps(st, indent=1, default=float) + "\n")
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshots", required=True, help="checkout of claude/xyz-books-data")
    ap.add_argument("--status", action="store_true", help="rewrite status.json from the journal, no fetch")
    a = ap.parse_args()
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    check_inputs(LANE / "PREREG.md")
    st = forward(a.snapshots, a.status)
    log({b: (st[b]["decision"], st[b]["summary"]["n"], st[b]["no_book"], st[b]["unpriced"]) for b in BOOKS})


if __name__ == "__main__":
    main()
