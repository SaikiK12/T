"""xfund_eea3_fwd (R512): R511's three-venue carry book (Kraken + Hyperliquid + Aster, L14d th5% K20) forward on paper,
as set out in experiments/xfund_eea3_fwd/PREREG.md. Paper only: nothing here can place an order.

The lane is lab.carrylane's, with "kraken" (lab.kraken) and "aster" (lab.aster) venues registered at run time. After
each tick every new on-time ticket gets a book record for both legs ($1,000 and $2,500 walks), by R509's recorder.

Its data lives in data/xfund_eea3_fwd/, its journal in experiments/xfund_eea3_fwd/journal/.

usage: python scripts/forward_xfund_eea3.py [--no-fetch]
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import aster, carrylane, kraken, prereg  # noqa: E402
from scripts import forward_xfund_eea as r509  # noqa: E402  (its book recorder)

kraken.register()
aster.register()
LANE = carrylane.Lane(
    name="xfund_eea3_fwd", rid="R512", folder=ROOT / "experiments" / "xfund_eea3_fwd",
    symbols=ROOT / "experiments" / "xfund_kaster_v1" / "symbols.csv",
    books={"A": ("kraken+hyperliquid+aster", 14, 0.05, 20, "R511's three-venue book (+25.04%/yr, NW t 6.23)")},
    venues=["kraken", "hyperliquid", "aster"],
    warm="2026-10-01", on_time="2026-11-20")
BOOKS = {"kraken": kraken.kraken_book, "hyperliquid": kraken.hl_book, "aster": aster.book}
FIXED = {"lab/xfund.py": "d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d",
         "experiments/xfund_kaster_v1/symbols.csv": "c0d111aff76f6591f1e20af728a64347bb8e0e0adf75e3abce15ac198c6f10c7"}


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
