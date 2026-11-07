"""xfund_lt_fwd (R294): R288's mexc+lighter carry book forward on paper, as set out in
experiments/xfund_lt_fwd/PREREG.md. Paper only: nothing here can place an order.

The lane is lab.carrylane's (R278's rule and accounting on any venues; what a tick does is in its docstring). Its data
lives in data/xfund_lt_fwd/, its journal in experiments/xfund_lt_fwd/journal/. Lighter's requests take the machine-wide
Lighter lock, shared with the book recorder, so a full refresh takes several minutes.

usage: python scripts/forward_xfund_lt.py [--no-fetch]
       (parity of this book with R288's engine output: python scripts/xfund_parity.py --lane xfund_lt_v1)
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import carrylane, prereg  # noqa: E402

LANE = carrylane.Lane(
    name="xfund_lt_fwd", rid="R294", folder=ROOT / "experiments" / "xfund_lt_fwd",
    symbols=ROOT / "experiments" / "xfund_lt_v1" / "symbols.csv",
    books={"A": ("mexc+lighter", 14, 0.05, 20, "R288's Lighter set with the highest 1x net (6.20%/yr, NW t 6.77)")},
    venues=["mexc", "lighter"],                        # R288's spec order, the two venues of the book
    warm="2026-08-01", on_time="2026-10-23", costs=(0.00055, 0.0011, 0.00165))
# fixed at the freeze (PREREG): the rule's code and the frozen universe. lab/carrylane.py may change for data plumbing.
FIXED = {"lab/xfund.py": "d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d",
         "experiments/xfund_lt_v1/symbols.csv": "e5a689a3bce5f16759104ab7dac945be2ad617317099b124b2137ef308fff1b1"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-fetch", action="store_true", help="use the forward root as it is (dry runs)")
    a = ap.parse_args()
    carrylane.log("prereg sha", prereg.verify(LANE.folder / "PREREG.md")[:12])
    bad = [f for f, h in FIXED.items() if prereg.sha256_file(ROOT / f) != h]
    if bad:
        raise SystemExit(f"fixed inputs changed since the freeze: {bad}")
    LANE.tick(fetch=not a.no_fetch)


if __name__ == "__main__":
    main()
