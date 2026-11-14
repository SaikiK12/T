"""xfund5_fwd (R440): R439's five-venue carry book forward on paper, as set out in experiments/xfund5_fwd/PREREG.md.
Paper only: nothing here can place an order.

The lane is lab.carrylane's (R278's rule and accounting on any venues; what a tick does is in its docstring), run on
R439's five venues in R439's spec order. Its data lives in data/xfund5_fwd/, its journal in
experiments/xfund5_fwd/journal/.

usage: python scripts/forward_xfund5.py [--no-fetch]
       (expectations of this book on the archive: python experiments/xfund5_fwd/plumbing/expect.py)
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import carrylane, prereg  # noqa: E402

LANE = carrylane.Lane(
    name="xfund5_fwd", rid="R440", folder=ROOT / "experiments" / "xfund5_fwd",
    symbols=ROOT / "experiments" / "carry5_v1" / "symbols.csv",
    books={"A": ("binance+gate+hyperliquid+mexc+kucoin", 14, 0.10, 20,
                 "R439: R275's all-four rule over five venues, CONFIRMED on M468 (NW t 8.71)")},
    venues=["binance", "gate", "hyperliquid", "mexc", "kucoin"],   # R439's spec order (ties)
    warm="2026-08-01", on_time="2026-11-11")
# fixed at the freeze (PREREG): the rule's code and the frozen universe. lab/carrylane.py may change for data plumbing.
FIXED = {"lab/xfund.py": "d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d",
         "experiments/carry5_v1/symbols.csv": "22a91dc96cd04a4ac9dce5914d5fba5485f754088acef74f7efe03f10e8e0328"}


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
