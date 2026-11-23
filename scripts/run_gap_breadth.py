"""R525 gap_breadth_v1: R275's carry book on every floorless x floor venue pair the lab holds, and the equal-weight
portfolio of all of them, as set out in experiments/gap_breadth_v1/PREREG.md.

- **Floorless** (no interest term): Kraken, Bitfinex, Deribit.
- **Floor** (0.01%/8 h interest term): Binance, Gate, Hyperliquid, KuCoin.
- **12 pairs.** Kraken+Hyperliquid, Bitfinex+Binance and Deribit+Hyperliquid were tested before (R508, R507, R519)
  and are recomputed here for the portfolio. The other 9 are new trials.
- **Engine:** R275's book (L14d th5% K20, correlation guard 30 d >= 0.9 on 20 obs) on `lab.xfund_v2`. Costs
  7/14/21 bp a leg. R437's frozen loader.
- **Portfolio.** Per day, the mean 1x net over the pairs live that day (equal weight). Also reported: three sleeves,
  one per floorless venue, each the mean of its pairs, then their mean.

usage: python scripts/run_gap_breadth.py run
"""
import json
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import xfund as v1  # noqa: E402
from lab import xfund_v2 as v2  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402
from scripts import run_carry_v2_audit as loader  # noqa: E402  (frozen R437 loader)
from scripts import run_xfund_bfx as base  # noqa: E402  (frozen R507: summarize, decide, check_inputs)

LANE = ROOT / "experiments" / "gap_breadth_v1"
FLOORLESS = ("kraken", "bitfinex", "deribit")
FLOOR = ("binance", "gate", "hyperliquid", "kucoin")
KNOWN = {("kraken", "hyperliquid"), ("bitfinex", "binance"), ("deribit", "hyperliquid")}
BOOK = (14, 0.05, 20)
COSTS = (0.0007, 0.0014, 0.0021)


def pair_book(u, a, b):
    vset = [u.names.index(a), u.names.index(b)]
    rows, trades = v2.replay(u, v2.Book(vset, *BOOK), v2.window_start(u, vset, BOOK[0]))
    tr = pd.DataFrame(trades)
    if len(tr):
        tr["gross"] = tr.price_pnl + tr.funding_pnl
        tr["funding"] = tr.funding_pnl
    else:
        tr = pd.DataFrame(columns=["coin", "long", "short", "gross", "funding"])
    return rows, tr


def stats(x):
    x = np.asarray(x, float)
    n = len(x)
    if n < 10:
        return {"days": n}
    cum = np.cumsum(x)
    h = n // 2
    return {"days": n, "ann_pct": float(x.mean() * 365 * 100), "sharpe": float(x.mean() / x.std() * np.sqrt(365)),
            "nw_t": float(newey_west_t(x, 10)[2]), "max_dd_pct": float((cum - np.maximum.accumulate(cum)).min() * 100),
            "halves_ann_pct": [float(x[:h].mean() * 36500), float(x[h:].mean() * 36500)]}


def run(lane=LANE):
    from lab.prereg import verify
    verify(lane / "PREREG.md")
    base.check_inputs(lane / "PREREG.md")
    res = lane / "results"
    if (res / "report.json").exists():
        raise SystemExit("results exist: this lane is read once")
    sp = tomllib.loads((lane / "spec.toml").read_text())
    u = loader.load(sp, v2, set(FLOORLESS + FLOOR))
    rep, nets = {"pairs": {}}, {}
    for a in FLOORLESS:
        for b in FLOOR:
            rows, tr = pair_book(u, a, b)
            name = f"{a}+{b}"
            if not len(rows):
                rep["pairs"][name] = {"verdict": "UNREADABLE", "days": 0, "new": (a, b) not in KNOWN}
                continue
            r, _ = base.summarize(rows, tr, BOOK[2], COSTS[0])
            verdict, checks = base.decide(r)
            dates = pd.to_datetime(u.t0 + rows.day * v1.DAY, unit="ms").dt.normalize()
            nets[name] = pd.Series(v2.net(rows, BOOK[2], COSTS[0]).to_numpy(float), index=dates)
            nets[name + "@2x"] = pd.Series(v2.net(rows, BOOK[2], COSTS[1]).to_numpy(float), index=dates)
            rep["pairs"][name] = {"new": (a, b) not in KNOWN, "verdict": verdict, "checks": checks,
                                  **{k: r.get(k) for k in ("n", "ann_1x_pct", "ann_2x_pct", "ann_3x_pct", "t_nw_1x",
                                                           "max_dd_pct", "trades", "first_day")},
                                  "first_date": str(dates.iloc[0].date())}
    one = {k: v for k, v in nets.items() if not k.endswith("@2x")}
    df = pd.concat(one, axis=1, sort=True)
    df2 = pd.concat({k[:-3]: v for k, v in nets.items() if k.endswith("@2x")}, axis=1, sort=True)
    port, port2 = df.mean(axis=1, skipna=True).dropna(), df2.mean(axis=1, skipna=True).dropna()
    sleeves = pd.concat({f: df[[c for c in df.columns if c.startswith(f + "+")]].mean(axis=1, skipna=True)
                         for f in FLOORLESS}, axis=1, sort=True).mean(axis=1, skipna=True).dropna()
    rep["portfolio_equal_pairs"] = {**stats(port), "ann_2x_pct": float(port2.mean() * 36500),
                                    "by_year_ann_pct": {int(y): float(g.mean() * 36500)
                                                        for y, g in port.groupby(port.index.year)},
                                    "pairs_live_mean": float(df.notna().sum(axis=1).mean())}
    rep["portfolio_floorless_sleeves"] = stats(sleeves)
    rep["corr_overlap"] = df.dropna().corr().round(3).to_dict() if len(df.dropna()) >= 30 else "too few common days"
    p = rep["portfolio_equal_pairs"]
    checks = {"nw_t_ge_3": p.get("nw_t", 0) >= 3.0, "positive_at_2x": p["ann_2x_pct"] > 0,
              "both_halves_pos": min(p.get("halves_ann_pct", [-1])) > 0}
    rep["verdict"] = "PASS" if all(checks.values()) else "FAIL"
    rep["checks"] = {k: bool(v) for k, v in checks.items()}
    res.mkdir(parents=True, exist_ok=True)
    df.to_csv(res / "pair_daily_net_1x.csv")
    (res / "report.json").write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps({"verdict": rep["verdict"], "checks": rep["checks"], "portfolio": p,
                      "pairs": {k: (v["verdict"], round(v.get("ann_1x_pct") or 0, 2), round(v.get("t_nw_1x") or 0, 2))
                                for k, v in rep["pairs"].items()}}, default=str, indent=1))
    return rep


if __name__ == "__main__":
    if sys.argv[1:] != ["run"]:
        raise SystemExit("usage: python scripts/run_gap_breadth.py run")
    run()
