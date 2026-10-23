"""xfund_kc_fwd (R279): R277's two replicating KuCoin carry books forward on paper, as set out in
experiments/xfund_kc_fwd/PREREG.md. Paper only: nothing here can place an order.

The lane is lab.carrylane's (R278's rule and accounting on any venues; what a tick does is in its docstring). Its data
lives in data/xfund_kc_fwd/, its journal in experiments/xfund_kc_fwd/journal/.

usage: python scripts/forward_xfund_kc.py [--no-fetch]
       (parity of these books with R277's engine output: python scripts/xfund_parity.py --lane xfund_kd_v1)
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import carrylane, prereg  # noqa: E402

LANE = carrylane.Lane(
    name="xfund_kc_fwd", rid="R279", folder=ROOT / "experiments" / "xfund_kc_fwd",
    symbols=ROOT / "experiments" / "xfund_kd_v1" / "symbols.csv",
    books={"A": ("gate+kucoin", 14, 0.05, 20, "R277's replicating set with the higher NW t (11.41)"),
           "B": ("binance+kucoin", 14, 0.05, 20, "R277's other replicating set (NW t 11.17)")},
    venues=["binance", "gate", "kucoin"],              # R277's spec order, without dYdX
    warm="2026-08-01", on_time="2026-10-22")
# fixed at the freeze (PREREG): the rule's code and the frozen universe. lab/carrylane.py may change for data plumbing.
FIXED = {"lab/xfund.py": "d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d",
         "experiments/xfund_kd_v1/symbols.csv": "15c8054f7e10f921bd9a797fbf2b9ac927c99fdfbc2388a54199be0cace6fb3b"}


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
