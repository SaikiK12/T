"""How much edge does a prop challenge need? Synthetic map for queue M211, from lab/propfirm presets.

For each firm preset and each annual Sharpe ratio, a 20-year synthetic daily return stream (normal, or Student t with
4 degrees of freedom for fat tails; daily volatility 1% at scale 1) is bootstrapped through the challenge and the
funded phase by lab.propfirm.optimize, which picks the size with the best expected value. No market data is read, so
this is a model, not a trial. Output: experiments/propsim_v1/edge_map.csv and a printed table.

usage: python scripts/prop_edge_map.py
"""
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import propfirm  # noqa: E402

OUT = ROOT / "experiments" / "propsim_v1"
SHARPES = (-1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0, 3.0)
# fees from docs/PROP_FIRMS.md where the preset has none: HyroTrader 2-step USD 579 (refunded at the first payout);
# HyroTrader 1-step USD 749; CFT and Breakout prices were not captured, so their break-even fee is reported instead
FEES = {"hyro_2step": 579.0, "hyro_1step": 749.0}
PRESETS = ("hyro_2step", "hyro_1step", "ftmo_2step", "breakout_pro", "cft_2phase", "topstep_50k")


def stream(sharpe, tails, days=5040, seed=0):
    rng = np.random.default_rng(seed)
    z = rng.standard_normal(days) if tails == "normal" else rng.standard_t(4, days) / np.sqrt(2.0)
    return 0.01 * z + 0.01 * sharpe / np.sqrt(252)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for name in PRESETS:
        rules = propfirm.PRESETS[name]
        if name in FEES:
            rules = replace(rules, fee=FEES[name])
        for tails in ("normal", "t4"):
            for sr in SHARPES:
                r = stream(sr, tails)
                _, best = propfirm.optimize(r, rules, scales=(0.25, 0.5, 0.75, 1, 1.5, 2, 3), n=2000)
                rows.append({"preset": name, "fee": rules.fee, "tails": tails, "sharpe": sr, **best})
                print(name, tails, sr, {k: round(v, 3) if isinstance(v, float) else v for k, v in best.items()},
                      flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "edge_map.csv", index=False)
    pd.set_option("display.width", 250)
    cols = ["preset", "tails", "sharpe", "scale", "p_pass", "p_paid", "days_to_pass", "exp_payout", "ev", "breakeven_fee"]
    print(df[cols].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
