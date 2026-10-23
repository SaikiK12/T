"""mexc_costs (R224): what a taker order costs on MEXC for the coins the forward books trade, measured from the public
order book, as set out in experiments/mexc_costs/PREREG.md. Reads R200's journal (never writes it); appends to its own.
Paper only: reads depth, places nothing.

usage: python scripts/record_mexc_depth.py   (one snapshot, then status.json; after scripts/forward_mexc.py)
"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import forward_tick as ft  # noqa: E402
from lab import engine, live, mexc, prereg  # noqa: E402

LANE = ROOT / "experiments" / "mexc_costs"
J = LANE / "journal"
TRADFI = set(json.loads((ROOT / "experiments" / "venue_gap_v1" / "results" / "tradfi_symbols.json").read_text()))
SIZES = (1_000, 10_000, 50_000)
BAND, API_TAKER, LEVELS = 0.005, 0.0008, 50
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def walk(levels, cs, notional, mid):
    """Impact in bp: the VWAP distance from mid to fill `notional` USDT against [[price, contracts, orders], ...];
    NaN when the levels shown are too thin."""
    left, cost = float(notional), 0.0
    for p, v, *_ in levels:
        take = min(left, p * v * cs)
        cost += take * abs(p / mid - 1)
        left -= take
        if left <= 0:
            return cost / notional * 1e4
    return np.nan


def side(levels, cs, mid):
    """USDT within BAND of mid, and how far (bp) the levels shown reach."""
    near = sum(p * v * cs for p, v, *_ in levels if abs(p / mid - 1) <= BAND)
    return near, abs(levels[-1][0] / mid - 1) * 1e4


def snapshot(c, cs):
    d = mexc.get(f"depth/{c}", {"limit": LEVELS})
    asks, bids = d["asks"], d["bids"]
    bid, ask = bids[0][0], asks[0][0]
    mid = (bid + ask) / 2
    row = {"t": int(d["timestamp"]), "bid": bid, "ask": ask, "half_spread_bp": (ask - bid) / 2 / mid * 1e4}
    for n in SIZES:
        row[f"buy_{n // 1000}k"], row[f"sell_{n // 1000}k"] = walk(asks, cs, n, mid), walk(bids, cs, n, mid)
    (row["bid_depth_05"], row["bid_reach_bp"]), (row["ask_depth_05"], row["ask_reach_bp"]) = side(bids, cs, mid), \
        side(asks, cs, mid)
    return row


def record():
    sig = ft.read("signals.csv")
    last = int(sig.t.max())
    now = sig[sig.t == last].set_index("symbol")["rank"]
    table = mexc.contracts()
    mp = mexc.map_symbols(list(now.index), table)
    for s in (TRADFI | live.tradfi()) & set(mp):
        mp[s] = None
    info = table.set_index("symbol")

    def one(s):
        try:
            return s, snapshot(mp[s], float(info.contract_size[mp[s]]))
        except (mexc.MexcError, IndexError, KeyError, ZeroDivisionError) as e:
            log("depth failed", s, mp[s], e)
            return s, None

    with ThreadPoolExecutor(4) as ex:
        got = list(ex.map(one, [s for s in now.index if mp[s]]))
    run_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rows = [{"run_at": run_at, "symbol": s, "contract": mp[s], "signal_hour": last, "rank": float(now[s]),
             "fee_taker": float(info.taker[mp[s]]), "fee_maker": float(info.maker[mp[s]]), **r}
            for s, r in got if r is not None]
    J.mkdir(parents=True, exist_ok=True)
    p = J / "depth.csv"
    pd.DataFrame(rows).to_csv(p, mode="a", header=not p.exists() or p.stat().st_size == 0, index=False)
    log(f"recorded {len(rows)} of {sum(1 for s in now.index if mp[s])} contracts; "
        f"unmapped or TradFi: {sorted(s for s in now.index if not mp[s])}")


def status():
    x = pd.read_csv(J / "depth.csv")
    for n in SIZES:
        k = f"{n // 1000}k"
        x[f"impact_{k}"] = (x[f"buy_{k}"] + x[f"sell_{k}"]) / 2
        x[f"web_{k}"] = x.fee_taker * 1e4 + x[f"impact_{k}"]
        x[f"api_{k}"] = API_TAKER * 1e4 + x[f"impact_{k}"]
    cols = ["half_spread_bp", "impact_1k", "impact_10k", "impact_50k", "web_10k", "api_10k", "web_50k", "api_50k",
            "bid_depth_05", "ask_depth_05"]
    g = x.groupby("symbol")
    per = g[cols].median()
    per["rank"] = g["rank"].median()
    per["assumed_bp"] = engine.cost_matrix(per["rank"].to_numpy()) * 1e4
    per["snapshots"] = g.size()
    per["unfilled_50k_share"] = g["impact_50k"].apply(lambda v: float(v.isna().mean()))
    out = {"snapshots": int(x.run_at.nunique()), "first": x.run_at.min(), "last": x.run_at.max(),
           "coins": int(len(per)), "report_from": "2026-11-03",
           "median_over_coins": {c: float(per[c].median()) for c in cols + ["assumed_bp"]},
           "share_web_10k_above_assumed": float((per.web_10k > per.assumed_bp).mean()),
           "share_api_10k_above_assumed": float((per.api_10k > per.assumed_bp).mean()),
           "coins_50k_unfilled_most_snapshots": sorted(per.index[per.unfilled_50k_share > 0.5]),
           "per_coin": per.round(3).reset_index().to_dict("records")}
    (J / "status.json").write_text(json.dumps(out, indent=1, default=float))
    m = out["median_over_coins"]
    log(f"{out['snapshots']} snapshots, {out['coins']} coins: median half-spread {m['half_spread_bp']:.2f} bp, "
        f"web $10k {m['web_10k']:.2f} bp, API $10k {m['api_10k']:.2f} bp, assumed {m['assumed_bp']:.1f} bp")


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    record()
    status()


if __name__ == "__main__":
    main()
