"""Print the M479 anytime-valid monitor for every live forward paper series (read-only).

Operational companion to lane R489 (`experiments/anytime_monitor_v1`). It reads the unified daily
books from `lab.operations.forward_days` and, for each series and cost level, prints the e-process
value and whether it rejects H0: mean <= 0. Because an e-process is valid at every stopping time
(Ville's inequality), this table may be read on any day without inflating the type-I error - unlike
the lanes' own fixed interim/final reads. It changes no frozen lane, writes nothing, and places no
order.

The bound is declared here, not estimated: lo/hi default to +/-0.30 (a 30% single-day move). The
dependence-robust `block` mode is shown alongside the raw `bet` mode; a `bet`-only crossing is
reported but not treated as a rejection.

usage: python scripts/forward_monitor.py [--alpha 0.05] [--lo -0.30] [--hi 0.30] [--block 5]
"""
import argparse
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab.operations import forward_days  # noqa: E402
from lab.sequential import lane_monitor  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--lo", type=float, default=-0.30)
    ap.add_argument("--hi", type=float, default=0.30)
    ap.add_argument("--block", type=int, default=5)
    args = ap.parse_args()

    rows = forward_days(ROOT)
    series = defaultdict(list)
    for r in rows:
        series[r["series"]].append(r)

    print(f"M479 anytime monitor | alpha={args.alpha} threshold={1/args.alpha:.0f} | "
          f"bounds=[{args.lo}, {args.hi}] | block={args.block}")
    print(f"{'series':32s} {'cost':6s} {'n':>4s} {'bet_e':>9s} {'block_e':>9s} {'state':>16s}")
    n_reject = 0
    for name in sorted(series):
        sub = sorted(series[name], key=lambda r: r["day"])
        for cost in ("net", "net_2x", "net_3x"):
            x = np.array([r[cost] for r in sub if r.get(cost) is not None], dtype=float)
            if x.size == 0 or not np.isfinite(x).any():
                continue
            if np.any(np.isfinite(x) & ((x < args.lo) | (x > args.hi))):
                print(f"{name[:32]:32s} {cost:6s} {x.size:4d} {'-':>9s} {'-':>9s} {'OUT_OF_BOUND':>16s}")
                continue
            bet = lane_monitor(x, args.lo, args.hi, alpha=args.alpha, mode="bet")
            blk = lane_monitor(x, args.lo, args.hi, alpha=args.alpha, mode="block", block=args.block)
            if blk["reject"]:
                state = "REJECTS"
                n_reject += 1
            elif bet["reject"]:
                state = "bet-only(not-evidence)"
            else:
                state = "null"
            print(f"{name[:32]:32s} {cost:6s} {x.size:4d} {bet['e_value']:9.2f} {blk['e_value']:9.2f} {state:>16s}")
    print(f"\n{n_reject} series-cost cell(s) reject in the dependence-robust block mode.")
    print("A rejection says the realised net mean is positive at level alpha, not that the book is "
          "profitable net of live fills. No order, no money.")


if __name__ == "__main__":
    main()
