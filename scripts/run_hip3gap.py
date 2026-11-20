"""R518 hip3gap_v1: R275's cross-venue carry book between HIP-3 dexes that list the same ticker, where the dexes'
funding designs differ.

Each HIP-3 deployer sets, per asset, a funding multiplier (0-10), an 8-hour interest rate and a clamp (docs, "HIP-3
deployer actions"). On 2026-11-20, perpDexs listed these designs:
- trade.xyz: multiplier 0.5;
- Felix: 0;
- Dreamcash: 0.000001;
- Kinetiq: default multiplier with about 5%/yr interest;
- mkts: the default (about 11%/yr);
- Paragon: 0.6;
- EntropyIO: 0.5 or 1.

So the same stock can cost a long nothing on one dex and the full interest floor on another. That is R507/R508's
design gap inside one Hyperliquid wallet.

- **Book.** R275's rule on `lab.xfund_v2` (the venue-neutral engine), unchanged: lookback 14 days, entry 5%/yr,
  20 slots, correlation guard 30 days >= 0.9 on 20 observations, costs 7/14/21 bp a leg. Every HIP-3 dex is a venue.
- **Data.** R517's fetch (`data/hip3list`, verified against its manifest), loaded by R517's frozen loader.

usage: python scripts/run_hip3gap.py run
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import xfund as v1  # noqa: E402
from lab import xfund_v2 as v2  # noqa: E402
from scripts import run_hip3list as h3  # noqa: E402  (frozen R517 runner: universe, check_data)
from scripts import run_xfund_bfx as base  # noqa: E402  (frozen R507 runner: decide, check_inputs)
from scripts import run_xfund_listing as lst  # noqa: E402  (frozen R516 runner: report, COSTS)

LANE = ROOT / "experiments" / "hip3gap_v1"
PRIMARY = (14, 0.05, 20)


def book(u, l, th, k):
    vset = list(range(len(u.names)))
    rows, trades = v2.replay(u, v2.Book(vset, l, th, k), v2.window_start(u, vset, l))
    tr = pd.DataFrame(trades)
    if len(tr):
        tr["gross"] = tr.price_pnl + tr.funding_pnl
        tr["funding"] = tr.funding_pnl
    else:
        tr = pd.DataFrame(columns=["coin", "long", "short", "gross", "funding", "reason", "entry_day", "exit_day"])
    return rows, tr


def run(lane=None, data=None):
    from lab.prereg import verify
    lane = Path(lane or LANE)
    verify(lane / "PREREG.md")
    base.check_inputs(lane / "PREREG.md")
    n_files, end = h3.check_data(data)
    res = lane / "results"
    if (res / "report.json").exists():
        raise SystemExit("results exist: this lane is read once")
    u = h3.universe(end, data)
    rows, tr = book(u, *PRIMARY)
    rep = {"window_end": end, "data_files_verified": n_files, "venues": u.names, "bases": len(u.keys)}
    rep["primary"] = lst.report(rows, tr, PRIMARY[2], u.t0)
    if len(rows):
        rep["primary"]["first_date"] = str(pd.Timestamp(u.t0 + int(rows.day.iloc[0]) * v1.DAY, unit="ms").date())
    rep["verdict"], rep["checks"] = base.decide(rep["primary"])
    if len(tr):
        pair = tr.long + ">" + tr.short
        rep["by_pair_net_1x_pct"] = {k: float(((g.gross - 4 * lst.COSTS[0]) * 100).sum())
                                     for k, g in tr.groupby(pair)}
    res.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"day": rows.day, "date": pd.to_datetime(u.t0 + rows.day * v1.DAY, unit="ms").dt.date,
                  **{f"net_{m}x": v2.net(rows, PRIMARY[2], c) for m, c in zip((1, 2, 3), lst.COSTS)},
                  "gross": rows.gross, "funding": rows.funding, "legs": rows.legs, "held": rows.held}
                 ).to_csv(res / "daily.csv", index=False)
    tr.to_csv(res / "trades.csv", index=False)
    (res / "report.json").write_text(json.dumps(rep, indent=1, default=str))
    p = rep["primary"]
    print(json.dumps({"verdict": rep["verdict"], "checks": rep["checks"],
                      **{x: p.get(x) for x in ("n", "ann_1x_pct", "ann_2x_pct", "ann_3x_pct", "t_nw_1x", "trades",
                                               "avg_held", "calendar_ann_pct")}}, default=str))
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("run",))
    ap.parse_args(argv)
    run()


if __name__ == "__main__":
    main()
