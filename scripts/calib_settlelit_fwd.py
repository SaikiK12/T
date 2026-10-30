"""R364 settlelit_fwd: the look bounds' size and power, from R363's frozen hops, before the freeze.

R363 (gate 0) priced R354's 221 θ 0.3% hops on Lighter's minute closes. Its primary nets (enter at the last trade
before T, exit at the last trade before T + 1 min, Lighter's settlement at T, R354's band cost) are the only
distribution of this trade the lab holds. This script resamples them in whole settlements and runs
`settlelit_fwd_rule.verdict()` on the draws:
- **size:** the nets with their mean removed, the 2x condition switched off (applied, it can only lower the PASS
  rate). The bounds start at the normal-theory O'Brien-Fleming pair for two equal looks (2.80, 1.98) and are raised in
  steps of 0.02 on the final (the interim stays at sqrt 2 times it) until the size is at most 2.5%; never lowered;
- **power:** the nets shifted to each mean, with the 2x net charged R354's cost once more.
It reads only R363's results/hops.csv.gz, whose sha256 it checks. No forward data exists when it runs.

usage: python scripts/calib_settlelit_fwd.py [--draws 12000] [--seed 364]
"""
import argparse
import hashlib
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import settlelit_fwd_rule as rule  # noqa: E402

HOPS = ROOT / "experiments" / "settlelit_v1" / "results" / "hops.csv.gz"
NOMINAL = 1.98                           # O'Brien-Fleming, two equal looks, one-sided 2.5%: 2.80 then 1.98


def load(path=HOPS):
    """R363's primary trial: one row per hop with T, the 1x net and the 1x round-trip cost (fractions)."""
    h = pd.read_csv(path)
    p = h[h.trial == "in0_out1"].sort_values(["T", "coin"], ignore_index=True)
    cost = 2 * p.cost_h_bp.to_numpy(float) / 1e4
    return p["T"].to_numpy("int64"), p.price.to_numpy(float) + p.fund.to_numpy(float) - cost, cost


def draw(rng, groups, n):
    """Whole settlements drawn with replacement, in the order drawn, until n hops: (hop indices, cluster keys). Each
    draw is its own cluster, so a settlement drawn twice counts as two."""
    idx, keys, g = [], [], 0
    while len(idx) < n:
        members = groups[rng.integers(len(groups))]
        idx.extend(members)
        keys.extend([g] * len(members))
        g += 1
    return idx[:n], keys[:n]


def run(T, net1, net2, n, draws, seed, bounds):
    """PASS rate and interim PASS rate of verdict() on `draws` resampled books of n hops (n < 80: the end date)."""
    rng = np.random.default_rng(seed)
    groups = [np.flatnonzero(T == t).tolist() for t in np.unique(T)]
    now = rule.END_MS if n < rule.FINAL else 0
    p = i = 0
    for _ in range(draws):
        idx, keys = draw(rng, groups, n)
        rows = [{"net1": net1[k], "net2": net2[k], "T": g} for k, g in zip(idx, keys)]
        state, text = rule.verdict(rows, now, bounds)
        if state == "PASS":
            p += 1
            i += text.startswith("interim")
    return p / draws, i / draws


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=12_000)
    ap.add_argument("--seed", type=int, default=364)
    a = ap.parse_args()
    print("R363 hops.csv.gz sha256", hashlib.sha256(HOPS.read_bytes()).hexdigest())
    T, net, cost = load()
    print(f"{len(net)} hops at {len(np.unique(T))} settlements: mean {net.mean() * 1e4:+.1f} bp, "
          f"SD {net.std(ddof=1) * 1e4:.1f} bp, 1x round trip {cost.mean() * 1e4:.2f} bp")
    null = net - net.mean()
    off = null + 1.0                                     # the 2x condition switched off for the size
    c2 = NOMINAL                                         # never below the normal-theory bounds
    while True:
        bounds = (round(math.sqrt(2) * c2, 2), round(c2, 2))
        size, interim = run(T, null, off, rule.FINAL, a.draws, a.seed, bounds)
        print(f"bounds {bounds}: size {size:.2%} (interim {interim:.2%})")
        if size <= 0.025:
            break
        c2 += 0.02
    print("size at the end date with 60 hops:", "{:.2%} (interim {:.2%})".format(
        *run(T, null, off, 60, a.draws, a.seed, bounds)))
    for mu in (10, 15, 20, 23.4, 30, 41.7):
        x1 = null + mu / 1e4
        x2 = x1 - cost
        p80, i80 = run(T, x1, x2, rule.FINAL, a.draws // 3, a.seed + 1, bounds)
        p60, _ = run(T, x1, x2, 60, a.draws // 3, a.seed + 2, bounds)
        print(f"mean {mu:+5.1f} bp: PASS {p80:.0%} with 80 hops (interim {i80:.0%}), {p60:.0%} with 60 by the end")


if __name__ == "__main__":
    main()
