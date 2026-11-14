"""levcarry_v1 (R280): leverage and liquidation on the forward carry books, as set out in
experiments/levcarry_v1/PREREG.md. A measurement: it chooses nothing and counts no trials.

For each forward book (R278's A, B, C on R275's archive; R279's A, B on R277's), each leverage L, each margin policy and
each maintenance margin, replays the book over its engine run's window with lab.levcarry and writes, to
experiments/levcarry_v1/results/:
- summary.csv: per run, the annual net on capital at 1x / 2x / 3x cost, t, NW t, max drawdown, worst day,
  liquidated legs, pairs closed by a liquidation, and the share of held leg-days whose intraday range was unknown;
- events.csv: every liquidated leg;
- moves.csv: per book, quantiles of each held leg's worst adverse price move of the day (funding not included).

Parity guard, before any number is written: at L = 1 with no liquidation possible (mm = -1e9), each book's daily net
at 1x cost must equal its engine run's own daily net (results/daily.csv) within 1e-9. The run aborts otherwise.

usage: nice python scripts/run_levcarry.py
"""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import levcarry, prereg, xfund  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402
from scripts.qx_run import inputs, sha  # noqa: E402
from scripts.xfund_parity import books, load  # noqa: E402

LANE = ROOT / "experiments" / "levcarry_v1"
OUT = LANE / "results"
RUNS = {"xfund_v1": "R278", "xfund_kd_v1": "R279"}       # engine run -> the forward lane whose books it holds
LEVERAGE = (1, 2, 3, 5, 10)
MM = (0.01, 0.05)
QUANTILES = (0.5, 0.9, 0.99, 0.999, 1.0)
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def ranges_for(spec, u, need):
    """ranges[c][v] = (high, low) per day from each venue's price file (bars ending in the day), None where absent."""
    sym = pd.read_csv(ROOT / spec["symbols"], dtype=str).fillna("")
    out = []
    for _, row in sym.iterrows():
        per = []
        for v in spec["venues"]:
            s = row[v["name"]].strip()
            p = ROOT / "data" / v["prices"] / f"{s}.parquet"
            if not s or v["name"] not in need or not p.exists():
                per.append(None)
                continue
            df = pd.read_parquet(p, columns=["t", "high", "low"])
            per.append(levcarry.daily_range(df.t, df.high, df.low, v.get("bar_h", 1) * xfund.H, u.t0, u.nd))
        out.append(per)
    return out


def summarize(days, events, k, lev):
    r = {}
    for m, c in zip((1, 2, 3), (0.0007, 0.0014, 0.0021)):
        n = levcarry.net(days, k, c, lev).to_numpy()
        r[f"ann_{m}x_pct"] = 365 * n.mean() * 100
        if m == 1:
            cum = np.concatenate([[0.0], np.cumsum(n)])
            r["t"] = n.mean() / n.std(ddof=1) * np.sqrt(len(n)) if n.std(ddof=1) > 0 else np.nan
            r["t_nw"] = newey_west_t(n, 10)[2]
            r["max_dd_pct"] = (cum - np.maximum.accumulate(cum)).min() * 100
            r["worst_day_pct"] = n.min() * 100
    r["liquidated_legs"] = len(events)
    r["pairs_closed"] = len({(e["day"], e["coin"]) for e in events})
    r["days"] = len(days)
    r["unknown_range_share"] = float(days.unknown.sum() / days.exposed.sum()) if days.exposed.sum() else np.nan
    return r


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    files, _ = inputs((LANE / "PREREG.md").read_text())
    bad = [f for f, h in files.items() if sha(ROOT / f) != h]
    if bad:
        raise SystemExit(f"inputs changed since the freeze: {bad}")
    log(f"{len(files)} inputs match the frozen hashes")
    OUT.mkdir(parents=True, exist_ok=True)
    summary, all_events, moves_rows = [], [], []
    for run_name, rid in RUNS.items():
        run_dir = ROOT / "experiments" / run_name
        bks = books(run_name)
        need = {v for b in bks.values() for v in b[0].split("+")}
        spec, u = load(run_dir, need)
        rng = ranges_for(spec, u, need)
        daily_eng = pd.read_csv(run_dir / "results" / "daily.csv")
        log(f"{run_name}: loaded {len(u.keys)} coins, {u.nd} days")
        for b, (s, l, th, k, _) in bks.items():
            vset = [u.names.index(v) for v in s.split("+")]
            w0 = xfund.window_start(u, vset, l)
            label = f"{s} L{l}d th{round(th * 100)}% K{k}"
            # parity guard: no liquidation at 1x is the engine's own book
            moves = []
            days, ev = levcarry.run(u, rng, xfund.Book(vset, l, th, k), w0, 1, "iso_daily", mm=-1e9, moves=moves)
            eng = daily_eng[(daily_eng.strategy == label) & (daily_eng.cost_multiple == 1)].net.to_numpy()
            mine = levcarry.net(days, k, spec["costs"][0], 1).to_numpy()
            if ev or len(mine) != len(eng) or np.abs(mine - eng).max() > 1e-9:
                raise SystemExit(f"parity guard failed on {label}: events {len(ev)}, days {len(mine)} vs {len(eng)}")
            log(f"{rid} {b} {label}: parity OK over {len(mine)} days")
            mv = np.array(moves)
            for leg, col in (("long", 0), ("short", 1)):
                q = np.quantile(mv[:, col], QUANTILES)
                moves_rows.append({"lane": rid, "book": b, "set": s, "leg": leg, "leg_days": len(mv),
                                   **{f"q{x:g}": v for x, v in zip(QUANTILES, q)}})
            for lev in LEVERAGE:
                for policy in levcarry.POLICIES:
                    for mm in MM:
                        days, ev = levcarry.run(u, rng, xfund.Book(vset, l, th, k), w0, lev, policy, mm=mm)
                        summary.append({"lane": rid, "book": b, "set": s, "strategy": label, "leverage": lev,
                                        "policy": policy, "mm": mm, **summarize(days, ev, k, lev)})
                        all_events += [{"lane": rid, "book": b, "set": s, "leverage": lev, "policy": policy, "mm": mm,
                                        "date": str((pd.Timestamp(spec["start"]) + pd.Timedelta(days=e["day"])).date()),
                                        **{x: e[x] for x in ("coin", "venue", "leg", "adverse", "account")}}
                                       for e in ev]
                log(f"{rid} {b} L{lev}: " + ", ".join(
                    f"{x['policy']}/{x['mm']}: {x['ann_1x_pct']:+.2f}% liq {x['liquidated_legs']}"
                    for x in summary[-len(levcarry.POLICIES) * len(MM):]))
    pd.DataFrame(summary).to_csv(OUT / "summary.csv", index=False, float_format="%.6g")
    cols = ["lane", "book", "set", "leverage", "policy", "mm", "date", "coin", "venue", "leg", "adverse", "account"]
    pd.DataFrame(all_events, columns=cols).to_csv(OUT / "events.csv", index=False, float_format="%.6g")
    pd.DataFrame(moves_rows).to_csv(OUT / "moves.csv", index=False, float_format="%.6g")
    log(f"wrote {len(summary)} runs, {len(all_events)} liquidated legs")


if __name__ == "__main__":
    main()
