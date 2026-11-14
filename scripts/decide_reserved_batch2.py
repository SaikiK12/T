"""R391 reserved batch 2: the decision on qx spread's tables (experiments/reserved_batch2/PREREG.md).

Batch 1's rule (scripts/run_reserved_batch.py `carry_stats` and `decide`), for the one candidate of this batch. It is
UNREADABLE below 60 book days. Otherwise it PASSES when all of these hold:
- the one-sided p of the Newey-West t (lag 10) at 1x is <= ALPHA;
- the 2x mean daily net is > 0;
- the 10% trimmed mean of the 1x daily net is > 0;
- the 1x mean without the two coins whose trades added most is > 0.
A coin's share of the daily sum is (price_pnl + funding_pnl - 4 x the 1x leg cost) / (2K).

usage: python -I scripts/decide_reserved_batch2.py   (after scripts/qx_run_verified.py experiments/reserved_batch2)
"""
import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path

import pandas as pd
import scipy.stats as sps

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402

LANE = ROOT / "experiments" / "reserved_batch2"
LABEL = "kucoin+dydx+lighter+mexc L14d th5% K20"
ALPHA = 0.05
N_MIN = 60
TRIM = 0.10


def stats(res, cost, slots, label=LABEL):
    st = pd.read_csv(res / "strategies.csv").set_index("label").loc[label]
    d = pd.read_csv(res / "daily.csv")
    d = d[d.strategy == label]
    x = d[d.cost_multiple == 1].net.to_numpy(float)
    out = {"n": int(len(x)), "days": int(st.days), "window_from": str(st.window_from),
           "ann_1x_pct": float(st.ann_1x_pct), "ann_2x_pct": float(st.ann_2x_pct), "ann_3x_pct": float(st.ann_3x_pct),
           "t_nw_1x": float(st.t_nw_1x), "avg_held": float(st.avg_held), "trades": int(st.trades),
           "half_bp": [float(st.half1_bp), float(st.half2_bp)], "max_dd_pct": float(st.max_dd_pct),
           "top10_share": float(st.top10_share), "funding_share": float(st.funding_share)}
    if len(x) < 3:
        return out
    out.update({"mean_1x_bp": float(x.mean() * 1e4), "p_one_sided": float(sps.norm.sf(st.t_nw_1x)),
                "trimmed_mean_bp": float(sps.trim_mean(x, TRIM) * 1e4)})
    for m in (2, 3):
        out[f"mean_{m}x_bp"] = float(d[d.cost_multiple == m].net.mean() * 1e4)
    tr = pd.read_csv(res / "trades.csv")
    tr = tr[tr.strategy == label]
    by = ((tr.price_pnl + tr.funding_pnl - 4 * cost) / (2 * slots)).groupby(tr.coin).sum().sort_values()
    top = by.index[::-1][:2].tolist()
    out["by_coin_bp_per_day"] = {c: float(v / len(x) * 1e4) for c, v in by.items()}
    out["by_long_venue_trades"] = {k: int(v) for k, v in tr.long.value_counts().items()}
    out["by_short_venue_trades"] = {k: int(v) for k, v in tr.short.value_counts().items()}
    out["l2co_dropped"] = top
    out["l2co_mean_bp"] = float((x.sum() - by[top].sum()) / len(x) * 1e4)
    return out


def decide(r, alpha=ALPHA):
    if r.get("n", 0) < N_MIN or "p_one_sided" not in r:
        return "UNREADABLE", {}
    checks = {"p_le_alpha": r["p_one_sided"] <= alpha, "mean_2x_pos": r["mean_2x_bp"] > 0,
              "trimmed_pos": r["trimmed_mean_bp"] > 0, "l2co_pos": r["l2co_mean_bp"] > 0}
    checks = {k: bool(v) for k, v in checks.items()}
    return ("PASS" if all(checks.values()) else "FAIL"), checks


def main():
    sha = prereg.verify(LANE / "PREREG.md")
    text = (LANE / "PREREG.md").read_text()
    block = re.search(r"```inputs\n(.*?)```", text, re.S).group(1)
    for line in block.splitlines():                     # qx_run's format: `path sha256`, `#` comments
        line = line.split("#")[0].strip()
        if not line or line.startswith("rebuild:"):
            continue
        rel, want = line.split()
        if hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != want:
            raise prereg.PreregError("frozen input changed: " + rel)
    spec = tomllib.loads((LANE / "spec.toml").read_text())
    r = stats(ROOT / spec["out"], spec["costs"][0], spec["slots"][0])
    verdict, checks = decide(r)
    out = {"round": "R391", "prereg_sha256": sha, "candidate": LABEL, "alpha": ALPHA, "verdict": verdict,
           "checks": checks, **r}
    (LANE / "results" / "decision.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("verdict", "checks") if k in out} |
                     {k: r.get(k) for k in ("days", "ann_1x_pct", "ann_2x_pct", "ann_3x_pct", "t_nw_1x",
                                            "trimmed_mean_bp", "l2co_mean_bp")}))


if __name__ == "__main__":
    main()
