"""Register S1 (docs/reviews/open_questions.md, committed fc0d571f before this read): at 3x costs, does R275's book
with entry 10%/yr (exit 5%) beat entry 5% (exit 2.5%) on R525's 12 pairs over 2024-01..2026-09? A measurement on held
data, both rules in sample; 1 trial. Prints the equal-weight portfolio for each rule at 1x/2x/3x and the difference.

usage: python scripts/measure_threshold_s1.py
"""
import json
import sys
import tomllib
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import xfund as v1  # noqa: E402
from lab import xfund_v2 as v2  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402
from scripts import run_carry_v2_audit as loader  # noqa: E402
from scripts.run_carry_meta import SPEC, FLOORLESS, FLOOR, COSTS, pairs  # noqa: E402

START = pd.Timestamp("2024-01-01")


def port(u, th, cost):
    nets = {}
    for a, b in pairs():
        vset = [u.names.index(a), u.names.index(b)]
        rows, _ = v2.replay(u, v2.Book(vset, 14, th, 20), v2.window_start(u, vset, 14))
        if not len(rows):
            continue
        dates = pd.to_datetime(u.t0 + rows.day * v1.DAY, unit="ms").dt.normalize()
        nets[f"{a}+{b}"] = pd.Series(v2.net(rows, 20, cost).to_numpy(float), index=dates)
    p = pd.concat(nets, axis=1, sort=True).mean(axis=1, skipna=True).dropna()
    return p[(p.index >= START) & (p.index <= pd.Timestamp("2026-09-30"))]


def main():
    u = loader.load(tomllib.loads(SPEC.read_text()), v2, set(FLOORLESS + FLOOR))
    out = {}
    for k, cost in zip(("1x", "2x", "3x"), COSTS):
        p5, p10 = port(u, 0.05, cost), port(u, 0.10, cost)
        j = pd.concat([p5.rename("th5"), p10.rename("th10")], axis=1, sort=True).dropna()
        d = j.th10 - j.th5
        out[k] = {"days": len(j), "th5_ann_pct": float(j.th5.mean() * 36500), "th10_ann_pct": float(j.th10.mean() * 36500),
                  "diff_ann_pct": float(d.mean() * 36500), "diff_nw_t": float(newey_west_t(d.to_numpy(), 10)[2]),
                  "diff_by_year": {int(y): float(g.mean() * 36500) for y, g in d.groupby(d.index.year)}}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
