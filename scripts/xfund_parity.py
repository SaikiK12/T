"""lab.xfund (the Python twin of qx spread) against a frozen engine run's output on the archive.

For each book of the forward lane built on that run, replays the book over the run's window with lab.xfund and
compares, against experiments/<run>/results/{trades,daily}.csv (the engine's own output):
- the trade list (coin, long venue, entry day, exit day), which must be identical;
- the daily 1x net, which must agree within 1e-9.

Runs and their forward lanes: xfund_v1 (R275) -> R278 xfund_fwd; xfund_kd_v1 (R277) -> R279 xfund_kc_fwd.

usage: python scripts/xfund_parity.py [--lane xfund_kd_v1]
       (about 1 minute; prints one line per book, exits 1 on a mismatch)
"""
import argparse
import sys
import time
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import xfund  # noqa: E402


def books(run):
    """The forward books built on an engine run: {book: (set, lookback, threshold, slots, why)}."""
    if run == "xfund_v1":
        from scripts.forward_xfund import BOOKS
        return BOOKS
    if run == "xfund_kd_v1":
        from scripts.forward_xfund_kc import LANE
        return LANE.books
    raise SystemExit(f"no forward lane is built on {run}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane", default="xfund_v1", help="the engine run (experiments/<lane>)")
    a = ap.parse_args()
    run = ROOT / "experiments" / a.lane
    bks = books(a.lane)
    spec = tomllib.loads((run / "spec.toml").read_text())
    t0 = int(pd.Timestamp(spec["start"], tz="UTC").value // 10**6)
    nd = int((pd.Timestamp(spec["end"], tz="UTC").value // 10**6 + xfund.DAY - t0) // xfund.DAY + 1)
    sym = pd.read_csv(ROOT / spec["symbols"], dtype=str).fillna("")
    venues = spec["venues"]
    names = [v["name"] for v in venues]
    need = {v for b in bks.values() for v in b[0].split("+")}

    def load(row):
        out = []
        for v in venues:
            s = row[v["name"]].strip()
            if not s or v["name"] not in need:
                out.append(None)
                continue
            out.append(xfund.load_daily(ROOT / "data" / v["prices"] / f"{s}.parquet",
                                        ROOT / "data" / v["funding"] / f"{s}.parquet", v["vol"], v.get("bar_h", 1),
                                        t0, nd))
        return out

    with ThreadPoolExecutor(8) as ex:
        series = list(ex.map(load, [r for _, r in sym.iterrows()]))
    u = xfund.Universe(sym.key.tolist(), names, series, t0, nd, spec["corr_days"], spec["corr_min"], spec["corr_obs"])
    trades_eng = pd.read_csv(run / "results" / "trades.csv")
    daily_eng = pd.read_csv(run / "results" / "daily.csv")
    day = lambda d: str((pd.Timestamp(spec["start"]) + pd.Timedelta(days=int(d))).date())
    ok = True
    for s, l, th, k, _ in bks.values():
        start = time.time()
        vset = [names.index(v) for v in s.split("+")]
        rows, trades = xfund.replay(u, xfund.Book(vset, l, th, k), xfund.window_start(u, vset, l))
        label = f"{s} L{l}d th{round(th * 100)}% K{k}"
        e = trades_eng[trades_eng.strategy == label]
        mine = [(x["coin"], x["long"], day(x["entry_day"]), "" if x["exit_day"] is None else day(x["exit_day"]))
                for x in trades]
        theirs = list(zip(e.coin, e.long, e.entry, e["exit"].fillna("")))
        net = xfund.net(rows, k, spec["costs"][0]).to_numpy()
        eng = daily_eng[(daily_eng.strategy == label) & (daily_eng.cost_multiple == 1)].net.to_numpy()
        diff = float(np.abs(net - eng).max()) if len(net) == len(eng) else float("inf")
        same = mine == theirs and diff < 1e-9
        ok &= same
        print(f"{label}: trades {len(mine)} vs {len(theirs)}, identical {mine == theirs}; days {len(net)} vs "
              f"{len(eng)}, max |net diff| {diff:.1e}; {'OK' if same else 'MISMATCH'} ({time.time() - start:.0f}s)",
              flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
