"""xfund_bfx_fwd (R524): R507's carry book on Binance + Bitfinex (L14d th5% K20) forward on paper, as set out in
experiments/xfund_bfx_fwd/PREREG.md. Paper only: nothing here can place an order.

The lane is lab.carrylane's, with a "bitfinex" venue (lab.bitfinex, R507's frozen client) registered at run time.
After each tick every new on-time ticket gets a book record for both legs ($1,000 and $2,500 walks), by R509's recorder.

usage: python scripts/forward_xfund_bfx.py [--no-fetch]
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import bitfinex, carrylane, live, prereg  # noqa: E402
from scripts import forward_xfund_eea as r509  # noqa: E402  (its book recorder)

bitfinex.register()


def binance_book(sym):
    d = live.get(f"fapi/v1/depth?symbol={sym}&limit=100")
    return ([[float(p), float(q)] for p, q in d.get("bids", [])], [[float(p), float(q)] for p, q in d.get("asks", [])])


LANE = carrylane.Lane(
    name="xfund_bfx_fwd", rid="R524", folder=ROOT / "experiments" / "xfund_bfx_fwd",
    symbols=ROOT / "experiments" / "xfund_bfx_fwd" / "symbols.csv",
    books={"A": ("binance+bitfinex", 14, 0.05, 20, "R507's book (+5.21%/yr, NW t 11.94, 2,078 days)")},
    venues=["binance", "bitfinex"],
    warm="2026-10-01", on_time="2026-11-25")
BOOKS = {"binance": binance_book, "bitfinex": bitfinex.book}
FIXED = {"lab/xfund.py": "d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-fetch", action="store_true", help="use the forward root as it is (dry runs)")
    a = ap.parse_args()
    carrylane.log("prereg sha", prereg.verify(LANE.folder / "PREREG.md")[:12])
    bad = [f for f, h in FIXED.items() if prereg.sha256_file(ROOT / f) != h]
    if bad:
        raise SystemExit(f"fixed inputs changed since the freeze: {bad}")
    LANE.tick(fetch=not a.no_fetch)
    carrylane.log("book records", r509.record_books(LANE, BOOKS))


if __name__ == "__main__":
    main()
