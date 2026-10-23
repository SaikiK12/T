"""carry_holdout (R191): one-shot holdout of the R190 primary, as set out in experiments/carry_holdout/PREREG.md."""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import carry, data, engine, events, panel, prereg, research  # noqa: E402

LANE = ROOT / "experiments" / "carry_holdout"
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
    t0, t1 = research.row_of(p, research.HOLDOUT), p.T
    res = {}
    for name, (sc, cm) in {"primary": (0.0010, 1.0), "costs_2x": (0.0010, 2.0), "spot_5bp": (0.0005, 1.0)}.items():
        o = carry.run(apr, fund, basis, elig, has, cost * cm, sc * cm, 0.20, 0.10, t0, t1)
        D = len(o) // 24
        day = o[: D * 24].reshape(D, 24, 5)
        net = day[..., 0].sum(1)
        res[name] = {"days": D, "net_total": float(net.sum()), **events.summary(net),
                     "funding_total": float(day[..., 1].sum()), "basis_total": float(day[..., 2].sum()),
                     "cost_total": float(day[..., 3].sum()), "avg_open": float(day[..., 4].mean()),
                     "invested": float((day[..., 4].mean(1) > 0).mean())}
    with np.errstate(invalid="ignore"):
        mkt_apr = np.nanmean(np.where(elig[t0:t1], apr[t0:t1], np.nan))
    res["context_mean_trailing_funding_apr_top50"] = float(mkt_apr)
    pr = res["primary"]
    res["verdict"] = "CONFIRMED" if pr["net_total"] > 0 and pr.get("t_nw", 0) >= 2 else "NOT CONFIRMED"
    (out / "holdout.json").write_text(json.dumps(res, indent=1, default=float))
    log(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
