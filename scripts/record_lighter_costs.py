"""Hourly book costs on every active Lighter perp, on GitHub: what a market order costs, for measured-cost reads of
lanes traded on Lighter (R455 llpinv_v1 at 9 bp; any later Lighter lane). Public data, no key, no order. Stdlib only.

Why: Lighter's Standard accounts pay no fee, so the spread and the book are the whole cost of a taker order. The lab's
earlier recorder (scripts/record_lighter_book.py) ran on a container that is gone and needs pandas; this one runs in
`.github/workflows/claude-xyz-books.yml` with the same arithmetic: a market order of $1k and $10k walked through the
first 100 orders shown on each side, in bp from the mid.

Writes OUT/lighter/books/YYYY-MM-DD.csv (merged by [ts, market_id], so a re-run is idempotent): ts (the run's time,
ms), market_id, symbol, bid, ask, half_spread_bp, buy_1k_bp, sell_1k_bp, buy_10k_bp, sell_10k_bp, bid_usd_shown,
ask_usd_shown. An empty cell means the shown book was too thin for that size. Requests are paced at 1.1 s (Lighter
allows 60 a minute per IP), so about 210 books take about 4 minutes. Logs counts only.

usage: python scripts/record_lighter_costs.py --out DIR
"""
import argparse
import importlib.util
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("record_llp_positions", ROOT / "scripts" / "record_llp_positions.py")
lp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lp)             # Lighter's API root and its retried GET; the OKX recorder's file helpers
okx = lp.okx
log = lp.log

SIZES = (1_000, 10_000)
DEPTH = 100                              # orders read per side, as record_lighter_book.py
PACE_S = 1.1
COLS = ["ts", "market_id", "symbol", "bid", "ask", "half_spread_bp", "buy_1k_bp", "sell_1k_bp", "buy_10k_bp",
        "sell_10k_bp", "bid_usd_shown", "ask_usd_shown"]


def levels(orders):
    return [(float(o["price"]), float(o["remaining_base_amount"])) for o in orders or []]


def impact(side, usd, mid):
    """bp between the mid and the average fill of a market order of `usd` walked through `side` [(price, base), ...]
    best first; None when the shown book is too thin."""
    left, paid, qty = float(usd), 0.0, 0.0
    for p, q in side:
        take = min(left, p * q)
        paid += take
        qty += take / p
        left -= take
        if left <= 1e-9:
            return abs(paid / qty / mid - 1) * 1e4
    return None


def book_row(ts, market, book):
    a, b = levels(book.get("asks")), levels(book.get("bids"))
    if not a or not b:
        return None
    ask, bid = a[0][0], b[0][0]
    mid = (ask + bid) / 2
    out = {"ts": ts, "market_id": int(market["market_id"]), "symbol": market["symbol"], "bid": bid, "ask": ask,
           "half_spread_bp": (ask - bid) / mid / 2 * 1e4,
           "bid_usd_shown": sum(p * q for p, q in b), "ask_usd_shown": sum(p * q for p, q in a)}
    for usd in SIZES:
        k = f"{usd // 1000}k"
        out[f"buy_{k}_bp"] = impact(a, usd, mid)
        out[f"sell_{k}_bp"] = impact(b, usd, mid)
    return out


def record(out, now_ms=None, get=None, pace=PACE_S, sleep=time.sleep, clock=time.monotonic):
    """One snapshot of every active perp's book. Returns (books written, markets that failed)."""
    get = get or lp.get
    ts = now_ms or int(time.time() * 1000)
    markets = [m for m in get("orderBookDetails").get("order_book_details", []) if m.get("status") == "active"]
    rows, failed, last = [], 0, clock()
    for m in markets:
        sleep(max(0.0, pace - (clock() - last)))
        last = clock()
        try:
            r = book_row(ts, m, get(f"orderBookOrders?market_id={int(m['market_id'])}&limit={DEPTH}", tries=2))
        except Exception:               # noqa: BLE001 - one market failing does not stop the snapshot
            failed += 1
            continue
        if r:
            rows.append(r)
    for d, rs in okx.by_day(rows, "ts").items():
        okx.merge_rows(Path(out) / "lighter" / "books" / f"{d}.csv", rs, COLS, ["ts", "market_id"])
    return len(rows), failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    n, failed = record(a.out)
    log(f"Lighter books {n}, failed {failed}")
    if n == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
