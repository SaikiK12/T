"""How much trading can a book afford inside a prop firm? Synthetic map for queue M211, next to prop_edge_map.py.

A firm charges a commission per side and often a daily swap (docs/PROP_FIRMS.md: Breakout 4 bp per side and 3.3 bp a
day). For a gross synthetic daily stream (normal, daily volatility 1% at scale 1) at a few annual Sharpe ratios, each
firm preset is evaluated with lab.propfirm.optimize after charging a cost per side and a swap for a range of daily
turnovers (sides traded per day per unit of book: 0.1 is a slow carry book, 2 a book that opens and closes every
day). No market data is read, so this is a model, not a trial.

The same arithmetic decides a venue (docs/VENUE_STRUCTURE.md): at 2 sides a day, every bp per side costs 5% a year.

Output: experiments/propsim_v1/cost_map.csv and a printed table.

usage: python scripts/prop_cost_map.py
"""
import sys
from dataclasses import replace
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import propfirm  # noqa: E402
from scripts.prop_edge_map import FEES, stream  # noqa: E402

OUT = ROOT / "experiments" / "propsim_v1"
PRESETS = ("hyro_2step", "ftmo_2step", "breakout_pro")
SHARPES = (1.0, 2.0)
COSTS_BP = (0.0, 2.0, 4.0, 8.0)                    # per side
TURNOVER = (0.1, 0.5, 1.0, 2.0)                    # sides per day per unit of book
SWAP_BP = 3.3                                      # per day on the notional held (Breakout's, applied to all)
SCALES = (0.5, 1, 1.5, 2)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for name in PRESETS:
        base = propfirm.PRESETS[name]
        if name in FEES:
            base = replace(base, fee=FEES[name])
        for sr in SHARPES:
            r = stream(sr, "normal")
            for swap in (0.0, SWAP_BP):
                for c in COSTS_BP:
                    for k in TURNOVER:
                        rules = replace(base, cost_side=c / 1e4, swap_day=swap / 1e4)
                        _, best = propfirm.optimize(r, rules, scales=SCALES, n=1500, turnover=k, exposure=1.0)
                        rows.append({"preset": name, "sharpe_gross": sr, "cost_bp_side": c, "swap_bp_day": swap,
                                     "turnover_day": k, "drag_pct_year_at_scale1": (k * c + swap) * 252 / 100,
                                     **best})
            print(name, sr, "done", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "cost_map.csv", index=False)
    key = df.assign(value=df.ev.where(df.ev.notna(), df.breakeven_fee))
    pd.set_option("display.width", 250)
    for (name, swap), g in key.groupby(["preset", "swap_bp_day"]):
        print(f"\n{name}, swap {swap} bp/day: expected value per attempt in USD (break-even fee where the fee is "
              f"unknown), rows cost bp per side, columns turnover per day")
        print(g.pivot_table(index=["sharpe_gross", "cost_bp_side"], columns="turnover_day", values="value")
              .round(0).to_string())


if __name__ == "__main__":
    main()
