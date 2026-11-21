"""xfund_dhl_fwd (R520): R275's carry book on Deribit + Hyperliquid (L14d th5% K20) forward on paper, as set out in
experiments/xfund_dhl_fwd/PREREG.md. Paper only: nothing here can place an order.

The lane is lab.carrylane's, with a "deribit" venue (lab.deribit) registered at run time. After each tick every new
on-time ticket gets a book record for both legs ($1,000 and $2,500 walks), by R509's recorder.

Data lives in data/xfund_dhl_fwd/, the journal in experiments/xfund_dhl_fwd/journal/.

usage: python scripts/forward_xfund_dhl.py [--no-fetch]
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import carrylane, deribit, kraken, prereg  # noqa: E402
from scripts import forward_xfund_eea as r509  # noqa: E402  (its book recorder)

deribit.register()
LANE = carrylane.Lane(
    name="xfund_dhl_fwd", rid="R520", folder=ROOT / "experiments" / "xfund_dhl_fwd",
    symbols=ROOT / "experiments" / "xfund_dhl_fwd" / "symbols.csv",
    books={"A": ("deribit+hyperliquid", 14, 0.05, 20, "R519's reported R275 book (+4.52%/yr, NW t 7.02)")},
    venues=["deribit", "hyperliquid"],
    warm="2026-10-01", on_time="2026-11-22")
BOOKS = {"deribit": deribit.book, "hyperliquid": kraken.hl_book}
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
