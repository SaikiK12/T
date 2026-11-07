"""R388 forcedswitch_v1: Binance's forced hourly switch as a natural experiment (M461, web-deep SRC1103-010).

Since 2025-05-02 08:00 UTC Binance moves a perp to hourly settlement after a print at its cap or floor, so the side
that pays keeps paying every hour. The question: is the move after a post-rule switch print (the payer squeezed
hourly) stronger than after a pre-rule print of the same size (no switch)?

Events, from data/fundingRate only (rows stamped in [2022-10-01, 2026-10-01), filtered on load; no 2020 row is read):
- a settlement T that closes an interval of 4 h or more (the gap from the previous settlement) with |rate| >= 1.99%;
- **pre-rule:** T before 2025-05-02 08:00 UTC;
- **post-rule switched:** T after it, and the next settlement is at T + 1 h;
- **post-rule not switched:** the same print with a longer next gap, reported only;
- **one episode per symbol per 24 h:** the first such print opens it.

Trade (direction d = -sign(rate): a floor print is a long, a cap print a short):
- **Entry:** the open of the data/klines_1h bar opening at T + 1 h.
- **Exit:** the open of the bar at entry + h, for h in {4, 8, 24}. If that bar is missing, the close of the bar before
  it is used.
- **Funding:** each settlement of the symbol stamped in (entry, exit], -d x rate.
- **Net:** gross + funding - m x 40 bp round trip (R273's cost on these coins), for m = 1, 2, 3.

usage: python -I scripts/run_forcedswitch.py --plumbing   (counts only, no price read)
       python -I scripts/run_forcedswitch.py              (the scored run; verifies the frozen PREREG and inputs)
"""
import argparse
import gzip
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
import settlehop_rule as rule  # noqa: E402  decide_stats-style clustering, trimmed, leave_two_coins_out

LANE = ROOT / "experiments/forcedswitch_v1"
FUND = ROOT / "data/fundingRate"
BARS = ROOT / "data/klines_1h"
H = 3_600_000
DAY = 24 * H
T0 = 1664582400000      # 2022-10-01
T1 = 1790812800000      # 2026-10-01
RULE = 1746172800000    # 2025-05-02 08:00 UTC
THETA = 0.0199
HORIZONS = (4, 8, 24)
PRIMARY = 8
COST_RT = 0.0040        # R273: 40 / 80 / 120 bp round trip at 1x / 2x / 3x


def symbols():
    return sorted(p.stem for p in FUND.glob("*.parquet") if (BARS / p.name).exists())


def settlements(sym):
    t = pq.read_table(FUND / f"{sym}.parquet", columns=["t", "rate"],
                      filters=[("t", ">=", T0 - 2 * DAY), ("t", "<", T1)]).to_pandas()
    t["T"] = (t.t + H // 2) // H * H
    t = t.drop_duplicates("T").sort_values("T", ignore_index=True)
    return t["T"].to_numpy(np.int64), t.rate.to_numpy(float)


def events(sym):
    """Episode-opening prints of one symbol: (T, rate, era, next_gap_h)."""
    T, r = settlements(sym)
    out, last = [], -10 * DAY
    for i in range(1, len(T) - 1):
        if T[i] < T0 or T[i] + H + 25 * H >= T1:
            continue
        gap, nxt = (T[i] - T[i - 1]) // H, (T[i + 1] - T[i]) // H
        if gap < 4 or abs(r[i]) < THETA or T[i] - last < DAY:
            continue
        last = T[i]
        era = "pre" if T[i] < RULE else ("post_switched" if nxt == 1 else "post_not_switched")
        out.append((int(T[i]), float(r[i]), era, int(nxt)))
    return out


def bars(sym):
    b = pq.read_table(BARS / f"{sym}.parquet", columns=["t", "open", "close"],
                      filters=[("t", ">=", T0), ("t", "<", T1)]).to_pandas()
    return b.drop_duplicates("t").set_index("t")


def price_at(b, t):
    if t in b.index:
        return float(b.at[t, "open"])
    if t - H in b.index:
        return float(b.at[t - H, "close"])
    return math.nan


def score_event(sym, T, rate, b, fT, fr):
    d = -1 if rate > 0 else 1
    entry = T + H
    p0 = price_at(b, entry)
    row = dict(symbol=sym, T=T, rate=rate, d=d)
    for h in HORIZONS:
        p1 = price_at(b, entry + h * H)
        gross = d * (p1 / p0 - 1) if p0 > 0 and np.isfinite(p0) and np.isfinite(p1) else math.nan
        m = (fT > entry) & (fT <= entry + h * H)
        fund = float(-d * fr[m].sum())
        row[f"gross_{h}"] = gross
        row[f"fund_{h}"] = fund
        for k in (1, 2, 3):
            row[f"net{k}_{h}"] = gross + fund - k * COST_RT if np.isfinite(gross) else math.nan
    return row


def cluster_se(x, keys):
    x = np.asarray(x, float)
    n = len(x)
    if n < 2:
        return math.nan
    u = x - x.mean()
    g = {}
    for k, v in zip(keys, u):
        g[k] = g.get(k, 0.0) + v
    if len(g) < 2:
        return math.nan
    return math.sqrt(sum(v * v for v in g.values()) / n ** 2 * len(g) / (len(g) - 1))


def describe(df, h):
    out = {}
    for era, x in df.groupby("era"):
        x = x[np.isfinite(x[f"gross_{h}"])]
        keys = (x.symbol + ":" + (x["T"] // DAY).astype(str)).tolist()
        out[era] = dict(n=len(x), coins=int(x.symbol.nunique()),
                        gross_bp=float(x[f"gross_{h}"].mean() * 1e4) if len(x) else None,
                        fund_bp=float(x[f"fund_{h}"].mean() * 1e4) if len(x) else None,
                        **{f"net{k}_bp": (float(x[f"net{k}_{h}"].mean() * 1e4) if len(x) else None) for k in (1, 2, 3)},
                        se_gross_bp=cluster_se(x[f"gross_{h}"], keys) * 1e4,
                        hit_net1=float((x[f"net1_{h}"] > 0).mean()) if len(x) else None)
    return out


def decide(df, h=PRIMARY):
    pre = df[(df.era == "pre") & np.isfinite(df[f"gross_{h}"])]
    post = df[(df.era == "post_switched") & np.isfinite(df[f"gross_{h}"])]
    k = lambda x: (x.symbol + ":" + (x["T"] // DAY).astype(str)).tolist()
    diff = post[f"gross_{h}"].mean() - pre[f"gross_{h}"].mean()
    se = math.hypot(cluster_se(post[f"gross_{h}"], k(post)), cluster_se(pre[f"gross_{h}"], k(pre)))
    t = diff / se if se > 0 else math.nan
    n1 = post[f"net1_{h}"].to_numpy()
    half = post.sort_values("T")
    a, b = half.iloc[: len(half) // 2], half.iloc[len(half) // 2:]
    checks = {"diff_t_ge_2": bool(diff > 0 and np.isfinite(t) and t >= 2.0),
              "post_net2_pos": bool(post[f"net2_{h}"].mean() > 0),
              "post_net3_pos": bool(post[f"net3_{h}"].mean() > 0),
              "halves_net1_pos": bool(a[f"net1_{h}"].mean() > 0 and b[f"net1_{h}"].mean() > 0),
              "trimmed_pos": bool(np.isfinite(rule.trimmed(n1)) and rule.trimmed(n1) > 0),
              "l2co_pos": bool(np.isfinite(rule.leave_two_coins_out(n1, post.symbol.tolist()))
                               and rule.leave_two_coins_out(n1, post.symbol.tolist()) > 0)}
    stats = dict(diff_gross_bp=diff * 1e4, diff_t=t, n_pre=len(pre), n_post=len(post),
                 trim10_net1_bp=rule.trimmed(n1) * 1e4, l2co_net1_bp=rule.leave_two_coins_out(n1, post.symbol.tolist()) * 1e4,
                 halves_net1_bp=[float(a[f"net1_{h}"].mean() * 1e4), float(b[f"net1_{h}"].mean() * 1e4)])
    return ("PASS" if all(checks.values()) else "NULL"), checks, stats


def verify_inputs():
    sha = prereg.verify(LANE / "PREREG.md")
    block = re.search(r"```inputs\n(.*?)```", (LANE / "PREREG.md").read_text(), re.S)
    for line in block.group(1).strip().splitlines():
        want, rel = line.split()
        if hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != want:
            raise prereg.PreregError("frozen input changed: " + rel)
    return sha


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--plumbing", action="store_true", help="event counts only; no price is read")
    a = p.parse_args()
    ev = [(s, *e) for s in symbols() for e in events(s)]
    evdf = pd.DataFrame(ev, columns=["symbol", "T", "rate", "era", "next_gap_h"])
    if a.plumbing:
        c = {era: dict(n=int(len(x)), coins=int(x.symbol.nunique()), floor=int((x.rate < 0).sum()),
                       cap=int((x.rate > 0).sum()), first=str(pd.to_datetime(x["T"].min(), unit="ms")),
                       last=str(pd.to_datetime(x["T"].max(), unit="ms")))
             for era, x in evdf.groupby("era")}
        print(json.dumps(c, indent=1))
        return
    sha = verify_inputs()
    rows = []
    for sym, x in evdf.groupby("symbol"):
        b = bars(sym)
        fT, fr = settlements(sym)
        for e in x.itertuples():
            rows.append(dict(score_event(sym, e.T, e.rate, b, fT, fr), era=e.era, next_gap_h=e.next_gap_h))
    df = pd.DataFrame(rows)
    verdict, checks, stats = decide(df)
    res = LANE / "results"
    res.mkdir(parents=True, exist_ok=True)
    with gzip.open(res / "events.csv.gz", "wt") as f:
        df.to_csv(f, index=False)
    summary = dict(round="R388", prereg_sha256=sha, verdict=verdict, primary_h=PRIMARY, checks=checks, stats=stats,
                   by_horizon={h: describe(df, h) for h in HORIZONS},
                   missing_prices=int((~np.isfinite(df[f"gross_{PRIMARY}"])).sum()))
    (res / "summary.json").write_text(json.dumps(summary, indent=1, default=float) + "\n")
    print(json.dumps(dict(verdict=verdict, checks=checks, stats=stats), default=float))


if __name__ == "__main__":
    main()
