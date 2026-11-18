"""xfund_eea_fwd (R509): R508's carry book (Kraken + Hyperliquid, L14d th5% K20) forward on paper, as set out in
experiments/xfund_eea_fwd/PREREG.md. Paper only: nothing here can place an order.

The lane is lab.carrylane's (R278's rule and accounting on any venues; what a tick does is in its docstring), with a
"kraken" venue registered at run time by lab.kraken (lab/carrylane.py is pinned by frozen lanes and is not edited).
After each tick, every new on-time ticket gets a book record: both venues' live books are walked for a market order of
$1,000 and $2,500 on the side the ticket trades, into journal/book_fills.csv. R508 found its return on thin Kraken
books, so the decided series charges these measured costs (PREREG).

Its data lives in data/xfund_eea_fwd/, its journal in experiments/xfund_eea_fwd/journal/.

usage: python scripts/forward_xfund_eea.py [--no-fetch]
"""
import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import carrylane, kraken, prereg  # noqa: E402

kraken.register()
LANE = carrylane.Lane(
    name="xfund_eea_fwd", rid="R509", folder=ROOT / "experiments" / "xfund_eea_fwd",
    symbols=ROOT / "experiments" / "xfund_eea_v1" / "symbols.csv",
    books={"A": ("kraken+hyperliquid", 14, 0.05, 20, "R508's primary book (PASS, NW t 7.39)")},
    venues=["kraken", "hyperliquid"],
    warm="2026-10-01", on_time="2026-11-19")
FIXED = {"lab/xfund.py": "d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d",
         "experiments/xfund_eea_v1/symbols.csv": "cf942d8f7e9235e5af3956b627d3edf06633f29f57c184a02670510b751975c0"}
SIZES = (1000, 2500)
FILL_COLS = ["run", "day", "book", "action", "coin", "venue", "symbol", "side", "utc", "mid",
             *[f"{k}_{s}" for s in SIZES for k in ("fill", "cost_bp")]]


def record_books(lane=LANE, books=None, now=None):
    """Book records for on-time tickets that have none yet; returns how many rows were appended."""
    books = books or kraken.BOOKS
    _, tk, _ = lane.journal()                  # tickets of completed runs only
    tickets = [r for r in tk if r["kind"] == "ontime"]
    done = {(r["run"], r["book"], r["action"], r["coin"]) for r in lane.rows("book_fills.csv")}
    table = lane.table().set_index("key")
    rows = []
    for t in tickets:
        if (t["run"], t["book"], t["action"], t["coin"]) in done:
            continue
        for venue, side in kraken.sides(t["action"], t["long"], t["short"]).items():
            sym = table.loc[t["coin"], venue]
            rec = {"run": t["run"], "day": t["day"], "book": t["book"], "action": t["action"], "coin": t["coin"],
                   "venue": venue, "symbol": sym, "side": side,
                   "utc": now or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "mid": ""}
            try:
                bids, asks = books[venue](sym)
            except Exception as e:             # noqa: BLE001 - a failed book is recorded as missing (PREREG: 3x cost)
                carrylane.log(f"{venue} book {sym} failed", e)
                bids, asks = [], []
            for s in SIZES:
                mid, px, cost = kraken.side_fill(bids, asks, side, s)
                rec["mid"] = "" if mid is None else f"{mid:.10g}"
                rec[f"fill_{s}"] = "" if px is None else f"{px:.10g}"
                rec[f"cost_bp_{s}"] = "" if cost is None else f"{cost:.4f}"
            rows.append(rec)
    if rows:
        lane.append("book_fills.csv", FILL_COLS, rows)
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-fetch", action="store_true", help="use the forward root as it is (dry runs)")
    a = ap.parse_args()
    carrylane.log("prereg sha", prereg.verify(LANE.folder / "PREREG.md")[:12])
    bad = [f for f, h in FIXED.items() if prereg.sha256_file(ROOT / f) != h]
    if bad:
        raise SystemExit(f"fixed inputs changed since the freeze: {bad}")
    LANE.tick(fetch=not a.no_fetch)
    carrylane.log("book records", record_books())


if __name__ == "__main__":
    main()
