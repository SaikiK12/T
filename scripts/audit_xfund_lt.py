"""R288 xfund_lt_v1 audit, as committed in its PREREG before the result: Lighter's funding sign and units against
Binance's, funding recomputed from the raw files for 2 random trades per set, concentration per set, the 2025-10-10
crash days (post hoc), each set at R275's uniform 7 / 14 / 21 bp per leg, and each set's net by year. Reads the engine's own output
(experiments/xfund_lt_v1/results) and the raw funding files; decides nothing on its own.

usage: python scripts/audit_xfund_lt.py
"""
import csv
import json
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, stats  # noqa: E402

LANE = ROOT / "experiments" / "xfund_lt_v1"
DAY, H = 86_400_000, 3_600_000
SEED = 288
CRASH = ("2025-10-10", "2025-10-12")
R275_COST = (0.0007, 0.0014, 0.0021)


def ms(day):
    return int(pd.Timestamp(day, tz="UTC").value // 10**6)


def funding(venue_dir, sym):
    f = pd.read_parquet(data.ROOT / venue_dir / f"{sym}.parquet", columns=["t", "rate"])
    f = f[np.isfinite(f.t) & np.isfinite(f.rate)]
    return (f.t.values.astype(np.int64) // H) * H, f.rate.values.astype(float)


def units(spec, sym):
    """BTC's 2025 funding per venue: median per settlement, settlements, and the year's sum (its annual carry)."""
    out = {}
    lo, hi = ms("2025-01-01"), ms("2026-01-01")
    for v in spec["venues"]:
        if v["name"] not in sym or not sym[v["name"]]:
            continue
        try:
            t, r = funding(v["funding"], sym[v["name"]])
        except FileNotFoundError:
            continue
        m = (t >= lo) & (t < hi)
        out[v["name"]] = {"median": float(np.median(r[m])), "n": int(m.sum()), "sum_2025_pct": float(r[m].sum() * 100)}
    return out


def recompute(trade, spec, syms, last_day):
    """A trade's funding: the short venue's settlements minus the long venue's, over days entry + 1 .. exit, a
    settlement (floored to the hour) at s belonging to day ceil((s - t0) / DAY). A trade still open at the end runs
    to the book's last daily row (`daily.csv` labels each interval by its end day, as the engine books it)."""
    vdir = {v["name"]: v["funding"] for v in spec["venues"]}
    a, b = ms(trade["entry"]), ms(trade["exit"] if isinstance(trade["exit"], str) else last_day)
    total = 0.0
    for venue, sign in ((trade["short"], 1.0), (trade["long"], -1.0)):
        t, r = funding(vdir[venue], syms[trade["coin"]][venue])
        total += sign * r[(t > a) & (t <= b)].sum()
    return total


def book_line(net):
    return {"ann_pct": float(np.mean(net) * 365 * 100), "nw_t": float(stats.newey_west_t(net, 10)[2]), "days": len(net)}


def main():
    spec = tomllib.loads((LANE / "spec.toml").read_text())
    syms = {r["key"]: r for r in csv.DictReader(open(ROOT / spec["symbols"]))}
    tr = pd.read_csv(LANE / "results" / "trades.csv")
    dl = pd.read_csv(LANE / "results" / "daily.csv")
    K = spec["slots"][0]
    out = {"units_btc_2025": units(spec, syms["BTCUSDT"]), "units_eth_2025": units(spec, syms["ETHUSDT"])}

    rng = np.random.default_rng(SEED)
    checks = []
    for s, g in tr.groupby("strategy"):
        for i in rng.choice(len(g), size=min(2, len(g)), replace=False):
            t = g.iloc[i]
            mine = recompute(t, spec, syms, dl[dl.strategy == s].date.max())
            checks.append({"strategy": s, "coin": t.coin, "entry": t.entry, "exit": t.exit if isinstance(t.exit, str) else "open",
                           "engine": float(t.funding_pnl), "recomputed": mine, "diff": abs(mine - float(t.funding_pnl))})
    out["funding_recompute"] = checks
    out["funding_recompute_max_diff"] = max(c["diff"] for c in checks)

    conc = {}
    for s, g in tr.groupby("strategy"):
        pnl = (g.price_pnl + g.funding_pnl).groupby(g.coin).sum().sort_values(ascending=False)
        tot = float(pnl.sum())
        conc[s] = {"coins": int(g.coin.nunique()), "trades": len(g),
                   "top5_share": float(pnl.iloc[:5].sum() / tot) if tot else None,
                   "top10_share": float(pnl.iloc[:10].sum() / tot) if tot else None,
                   "lighter_long_share": float((g.long == "lighter").mean()),
                   "funding_share": float(g.funding_pnl.sum() / (g.funding_pnl.sum() + g.price_pnl.sum()))}
    out["concentration"] = conc

    one = dl[dl.cost_multiple == 1]
    crash = {}
    uniform = {}
    for s, g in one.groupby("strategy"):
        g = g.sort_values("date")
        keep = ~g.date.between(*CRASH)
        crash[s] = {"all": book_line(g.net.values), "without_crash_days": book_line(g.net.values[keep.values]),
                    "crash_days_net_pct": [round(float(x) * 100, 3) for x in g.net.values[~keep.values]]}
        uniform[s] = {f"{m}x": book_line((g.gross - c * g.legs / (2 * K)).values)
                      for m, c in zip((1, 2, 3), R275_COST)}
    out["crash_post_hoc"] = crash
    out["at_r275_costs"] = uniform
    out["by_year_pct"] = {s: {str(y): {f"{m}x": round(float(gy.net.mean() * 365 * 100), 2) for m, gy in gm.groupby("cost_multiple")}
                              for y, gm in g.groupby(g.date.str[:4])} for s, g in dl.groupby("strategy")}
    (LANE / "results" / "audit.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
