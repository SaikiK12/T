"""lab.xfund (the Python twin of qx spread) against R275's frozen engine output on the archive.

For each forward book of R278, replays the book over R275's window with lab.xfund and compares, against
experiments/xfund_v1/results/{trades,daily}.csv (R275's own output; hashes in results/hashes.json):
- the trade list (coin, long venue, entry day, exit day), which must be identical;
- the daily 1x net, which must agree within 1e-9.

usage: python scripts/xfund_parity.py        (about 1 minute; prints one line per book, exits 1 on a mismatch)
"""
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
from scripts.forward_xfund import BOOKS  # noqa: E402

LANE = ROOT / "experiments" / "xfund_v1"


def main():
    spec = tomllib.loads((LANE / "spec.toml").read_text())
    t0 = int(pd.Timestamp(spec["start"], tz="UTC").value // 10**6)
    nd = int((pd.Timestamp(spec["end"], tz="UTC").value // 10**6 + xfund.DAY - t0) // xfund.DAY + 1)
    sym = pd.read_csv(ROOT / spec["symbols"], dtype=str).fillna("")
    venues = spec["venues"]
    names = [v["name"] for v in venues]
    need = {v for b in BOOKS.values() for v in b[0].split("+")}

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
    trades_eng = pd.read_csv(LANE / "results" / "trades.csv")
    daily_eng = pd.read_csv(LANE / "results" / "daily.csv")
    day = lambda d: str((pd.Timestamp(spec["start"]) + pd.Timedelta(days=int(d))).date())
    ok = True
    for s, l, th, k, _ in BOOKS.values():
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
