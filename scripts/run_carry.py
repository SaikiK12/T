"""carry_v1 (R190): hedged funding carry, as set out in experiments/carry_v1/PREREG.md."""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import carry, data, engine, events, panel, prereg, research  # noqa: E402

LANE = ROOT / "experiments" / "carry_v1"
SPLITS = {"discovery": ("2021-01-01", "2024-01-01"), "validation": ("2024-01-01", "2025-07-01")}
THETA, SPOT_COST, CMULT = (0.10, 0.20, 0.40), (0.0010, 0.0005), (1.0, 2.0)
PRIMARY = (0.20, 0.0010, 1.0)
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    p = panel.load_panel()
    keep = np.flatnonzero(np.isfinite(p["close"]).any(axis=0))
    p = p.columns(keep)
    rank = panel.liquidity_rank(p, 24 * 30)
    elig = rank <= 50
    cost = engine.cost_matrix(rank).astype(np.float64)
    fund = p["fund_event"].astype(np.float64)
    basis = p["premium"].astype(np.float64)
    apr = carry.trailing_apr(fund, 72)
    pairs = json.loads((data.ROOT / "spot_pairs.json").read_text())
    month = pd.to_datetime(p.t, unit="ms", utc=True).strftime("%Y-%m").values
    has = np.zeros(elig.shape, bool)
    for j, s in enumerate(p.symbols):
        m = pairs.get(s, {}).get("months")
        if m:
            has[:, j] = (month >= m[0]) & (month <= m[1])
    log(f"tradable with spot: median {int(np.median((elig & has).sum(1)))} of 50 per hour")
    rows, keep_series = [], {}
    for split, (a, b) in SPLITS.items():
        t0, t1 = research.row_of(p, a), research.row_of(p, b)
        years = pd.to_datetime(p.t[t0:t1:24], unit="ms", utc=True).year.values
        for th in THETA:
            for sc in SPOT_COST:
                for cm in CMULT:
                    o = carry.run(apr, fund, basis, elig, has, cost * cm, sc * cm, th, th / 2, t0, t1)
                    D = len(o) // 24
                    day = o[: D * 24].reshape(D, 24, 5)
                    net = day[..., 0].sum(1)
                    r = {"split": split, "theta_in": th, "spot_cost_bp": sc * 1e4, "cmult": cm,
                         "funding_ann": day[..., 1].sum(1).mean() * 365, "basis_ann": day[..., 2].sum(1).mean() * 365,
                         "cost_ann": day[..., 3].sum(1).mean() * 365, "avg_open": day[..., 4].mean(),
                         "invested": float((day[..., 4].mean(1) > 0).mean()), **events.summary(net)}
                    for y in np.unique(years):
                        r[f"y{y}"] = float(net[years[:D] == y].sum())
                    rows.append(r)
                    if (th, sc, cm) == PRIMARY:
                        keep_series[split] = net
    df = pd.DataFrame(rows)
    df.to_csv(out / "configs.csv", index=False)
    np.savez_compressed(out / "primary_daily.npz", **keep_series)
    pr = df[(df.theta_in == PRIMARY[0]) & (df.spot_cost_bp == PRIMARY[1] * 1e4) & (df.cmult == PRIMARY[2])]
    log("primary:\n" + pr.round(4).to_string(index=False))
    log("done")


if __name__ == "__main__":
    main()
