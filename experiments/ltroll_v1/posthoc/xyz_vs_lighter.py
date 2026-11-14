"""Post hoc for R481 (decides nothing): the same roll cycles on trade.xyz (R478's post hoc) and on Lighter (R481).

Both oracles referenced the same contracts on the same business days 5-9 until Lighter moved WTI, NATGAS and XCU to
RedStone on 2026-10-22, and both rolls are measured against the same Yahoo front at 20:00 UTC. So, per cycle (business
day 10 to 10, % of notional):
    roll_xyz vs roll_lighter       should agree within the two perps' premia (a check of the measure)
    funding_xyz - funding_lighter  what a short xyz / long Lighter pair would have kept, with the roll netting out
Inputs: experiments/rollcarry_v1/posthoc/front_roll_months.csv and front_roll_cycles.csv (xyz), and
experiments/ltroll_v1/results/cycles.csv (Lighter). xyz's CL is Lighter's WTI. Cycles whose start differs (listing
weeks) are marked. Output: xyz_vs_lighter.csv next to this file.

usage: .venv/bin/python experiments/ltroll_v1/posthoc/xyz_vs_lighter.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PAIR = {"NATGAS": "NATGAS", "CL": "WTI", "BRENTOIL": "BRENTOIL"}


def main():
    xm = pd.read_csv(ROOT / "experiments/rollcarry_v1/posthoc/front_roll_months.csv")
    xc = pd.read_csv(ROOT / "experiments/rollcarry_v1/posthoc/front_roll_cycles.csv")
    lt = pd.read_csv(ROOT / "experiments/ltroll_v1/results/cycles.csv")
    out = []
    for xp, lp in PAIR.items():
        for _, r in lt[lt["market"] == lp].iterrows():
            m = xm[(xm["pair"] == xp) & (xm["month"] == r["month"])]
            c = xc[(xc["pair"] == xp) & (xc["to"] == r["end"])]
            if not len(m) or not len(c):
                continue
            out.append({"market": lp, "month": r["month"], "xyz_from": c["from"].iloc[0], "lighter_from": r["start"][:10],
                        "roll_xyz": m["roll"].iloc[0], "roll_lighter": r["roll"],
                        "fund_xyz": c["funding"].iloc[0], "fund_lighter": r["fund"],
                        "fund_diff": c["funding"].iloc[0] - r["fund"],
                        "same_start": c["from"].iloc[0] == r["start"][:10]})
    df = pd.DataFrame(out)
    df.to_csv(HERE / "xyz_vs_lighter.csv", index=False, float_format="%.6f")
    pd.set_option("display.width", 200)
    show = df.copy()
    for k in ("roll_xyz", "roll_lighter", "fund_xyz", "fund_lighter", "fund_diff"):
        show[k] = (show[k] * 100).round(2)
    print("per cycle, % of notional")
    print(show.to_string(index=False))
    for lp, g in df.groupby("market", sort=False):
        f = g[g["same_start"]]
        print(f"{lp}: {len(f)} full cycles; roll xyz - lighter mean {100 * (f['roll_xyz'] - f['roll_lighter']).mean():+.2f} "
              f"(max abs {100 * (f['roll_xyz'] - f['roll_lighter']).abs().max():.2f}); funding xyz - lighter mean "
              f"{100 * f['fund_diff'].mean():+.2f} sd {100 * f['fund_diff'].std():.2f}, > 0 in "
              f"{int((f['fund_diff'] > 0).sum())} of {len(f)}")


if __name__ == "__main__":
    main()
