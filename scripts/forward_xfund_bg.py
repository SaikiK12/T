"""xfund_bg_fwd (R390): the binance+gate cross-venue carry book that passed reserved batch 1 (R286 C14), forward on
paper, as set out in experiments/xfund_bg_fwd/PREREG.md. Paper only: nothing here can place an order.

The lane is lab.carrylane's (R278's rule and accounting on any venues; what a tick does is in its docstring). Its data
lives in data/xfund_bg_fwd/, its journal in experiments/xfund_bg_fwd/journal/.

usage: python scripts/forward_xfund_bg.py [--no-fetch]
       (parity of this book with R275's engine output: python scripts/xfund_parity.py --lane xfund_v1 --forward xfund_bg)
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import carrylane, prereg  # noqa: E402

LANE = carrylane.Lane(
    name="xfund_bg_fwd", rid="R390", folder=ROOT / "experiments" / "xfund_bg_fwd",
    symbols=ROOT / "experiments" / "xfund_v1" / "symbols.csv",
    books={"A": ("binance+gate", 14, 0.10, 20, "R286 C14: R275's binance+gate book, gate-1 PASS on 2020 (NW t 4.03)")},
    venues=["binance", "gate"],                       # R275's spec order, the two venues of the book
    warm="2026-08-01", on_time="2026-11-04")
# fixed at the freeze (PREREG): the rule's code and the frozen universe. lab/carrylane.py may change for data plumbing.
FIXED = {"lab/xfund.py": "d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d",
         "experiments/xfund_v1/symbols.csv": "78201a341b9fc498b67f4893f1dd30d67d790d94ca8257a4b1a2ce8f569ab8e0"}


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
