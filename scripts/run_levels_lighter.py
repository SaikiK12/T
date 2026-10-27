"""R337 levels_lighter_v1: R333's level trades on Lighter's own hourly prices, at Lighter's measured book cost (gate 0).

R336 found R333's break-or-rebound trades pay on MEXC's zero-fee perps at the quoted spread. But MEXC's zero fees hold
for web orders only: its API orders pay 6 bp maker and 8 bp taker since 2026-06-01 (docs/MEXC_EDGES.md), and the full
book needs about 9 orders at each hourly close, which is API work. Lighter's default account pays 0 maker and 0 taker,
API orders included (docs/VENUE_STRUCTURE.md). This lane reads R333's saved V0 out-of-sample events (2025-02..2026-09)
on the coins with an open-route Lighter perp, keeps the events Lighter covers (a traded bar in each of the 72 hours to
the decision, a close at every hour of the hold), re-prices each one on Lighter's hourly closes and hourly funding,
charges each coin the median measured cost of a $1k market order on Lighter's book (floor 1 bp) on entry and exit, and
asks whether a constant-size book of the policy's trades pays. It places no orders.

usage: python scripts/run_levels_lighter.py --run      # verifies the frozen PREREG and its inputs, then runs
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402
from scripts import run_levels_mexc0 as lm  # noqa: E402

LANE = ROOT / "experiments" / "levels_lighter_v1"
EVENTS = lm.EVENTS
CONTRACTS = "data/lighter_hist/contracts.csv"
CANDLES = "data/lighter_hist/open/candles_1h"
FUNDING = "data/lighter_hist/open/funding"
BOOKS = "data/recorders/lighter_book/"
H, DAY, GRID0 = lm.H, lm.DAY, lm.GRID0
D0, D1 = 20120, 20727          # 2025-02-01 .. 2026-10-01 (exclusive), in days since the epoch
HALF = 20423                   # 2025-12-01: the second half starts here
VOL_N = 72                     # R333's candidate rule: positive quote volume in each of the last 72 hours
FLOOR_BP = 1.0
MULTS = (1, 2, 3)
TRIALS = 6                     # LZ day-sum, LZ day-mean, LP1 trades, LZ on Binance prices, THROUGH, AWAY
SEED = 337
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def lighter_map(contracts):
    """Binance perp -> Lighter symbol, for the open route only: the reserved route (no Binance perp) is never read."""
    o = contracts[contracts.route == "open"]
    return dict(zip(o.binance_perp, o.symbol))


def book_costs(rows, symbols, floor_bp=FLOOR_BP):
    """Lighter symbol -> one-way cost as a fraction: the median over the snapshots of the mean cost of a $1k market buy
    and sell walked through the shown book (bp from the mid), at least floor_bp. Rows of other symbols are dropped
    before anything is computed."""
    r = rows[rows.symbol.isin(symbols)]
    c = ((r.buy_1k_bp + r.sell_1k_bp) / 2).groupby(r.symbol).median().dropna()
    return {s: max(floor_bp, float(v)) / 1e4 for s, v in c.items()}


def coin_grid(candles, funding):
    """A coin's full hourly grid from its first to its last bar (t = bar open): the close (NaN where none), whether the
    72 hours to each bar all traded, and the funding a long pays at a settlement inside each bar (0 where none)."""
    t0, t1 = int(candles.t.min()), int(candles.t.max())
    n = (t1 - t0) // H + 1
    k = ((candles.t.values.astype(np.int64) - t0) // H)
    close = np.full(n, np.nan)
    close[k] = np.where(candles.close.values > 0, candles.close.values, np.nan)
    traded = np.zeros(n)
    traded[k] = (np.nan_to_num(candles.quote_volume.values) > 0).astype(float)
    vol_ok = pd.Series(traded).rolling(VOL_N, min_periods=VOL_N).min().values == 1
    fund = np.zeros(n)
    if len(funding):
        j = (funding.t.values.astype(np.int64) // H * H - t0) // H
        ok = (j >= 0) & (j < n)
        np.add.at(fund, j[ok], np.nan_to_num(funding.rate.values[ok]))
    return t0, close, vol_ok, fund


def price(t, exit_row, side, t0, close, vol_ok, fund):
    """R333's through-direction return on this venue: side x the sum of the next-bar returns, net of the funding a long
    pays, from the decision close to the exit close (engine.forward_returns' convention). Returns (g, status): 0 priced,
    1 the 72 hours to the decision did not all trade, 2 a close is missing on the path, 3 outside the venue's bars."""
    i = (int(t) - t0) // H
    x = (GRID0 + int(exit_row) * H - t0) // H
    if i < 0 or x >= len(close) or x <= i:
        return np.nan, 3
    if not vol_ok[i]:
        return np.nan, 1
    c = close[i:x + 1]
    if not np.isfinite(c).all():
        return np.nan, 2
    r = c[1:] / c[:-1] - 1 - fund[i + 1:x + 1]
    return float(side * r.sum()), 0


def sum_stats(net, day, sym, d0=D0, d1=D1, half=HALF, best=10):
    """R336's day-sum statistics on this lane's window and halves."""
    sel = (day >= d0) & (day < d1)
    net, day, sym = net[sel], day[sel], sym[sel]
    if len(net) == 0:
        return {"trades": 0}
    full = lm.day_sums(net, day, d0, d1)
    n, mu, t = newey_west_t(full.values, 3)
    wo = full.drop(full.nlargest(best).index)
    first, second = full[full.index < half], full[full.index >= half]
    by_coin = pd.Series(net).groupby(sym).sum()
    top = by_coin.idxmax()
    full_wo_top = lm.day_sums(net[sym != top], day[sym != top], d0, d1)
    tpd = pd.Series(1, index=day).groupby(level=0).sum().reindex(full.index, fill_value=0)
    dt = pd.to_datetime(day * DAY, unit="ms")
    quarter = dt.year.astype(str) + "Q" + dt.quarter.astype(str)
    return {"trades": int(len(net)), "days": int(n),
            "trades_per_day": {"mean": round(float(tpd.mean()), 2), "median": float(tpd.median()),
                               "p90": float(tpd.quantile(0.9)), "max": int(tpd.max())},
            "bp_per_day": round(1e4 * mu, 2), "t": None if np.isnan(t) else round(float(t), 2),
            "bp_per_trade": round(1e4 * float(net.mean()), 2), "hit": round(float((net > 0).mean()), 4),
            "bp_per_day_wo_best10": round(1e4 * float(wo.mean()), 2),
            "bp_per_day_first_half": round(1e4 * float(first.mean()), 2),
            "bp_per_day_second_half": round(1e4 * float(second.mean()), 2),
            "best_coin": str(top), "best_coin_share_of_net": round(float(by_coin[top] / net.sum()), 3)
            if net.sum() != 0 else None,
            "bp_per_day_wo_best_coin": round(1e4 * float(full_wo_top.mean()), 2),
            "bp_per_trade_by_quarter": {k: round(1e4 * float(v), 2)
                                        for k, v in pd.Series(net).groupby(np.asarray(quarter)).mean().items()},
            "max_drawdown_trade_units": round(lm.drawdown(full.values), 3),
            "worst_day_trade_units": round(float(full.min()), 3),
            "trade_bp_quantiles": {str(q): round(1e4 * float(np.quantile(net, q)), 1)
                                   for q in (0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99)}}


def frozen_files(prereg_path, prefix):
    """The inputs named in the PREREG's inputs block under a folder, and only those: recorders keep adding files."""
    block = re.search(r"```inputs\n(.*?)```", Path(prereg_path).read_text(), re.S).group(1)
    return [line.split()[1] for line in block.strip().splitlines() if line.split()[1].startswith(prefix)]


def book(ev, sides):
    b = {f"{m}x": sum_stats(*lm.trades(ev, sides, m)) for m in MULTS}
    b["gross"] = sum_stats(*lm.trades(ev, sides, 0))
    on = sides != 0
    b["break_even_bp_one_way"] = round(1e4 * float(np.mean(sides[on] * ev.g.values[on])) / 2, 2) if on.any() else None
    b["day_mean_convention"] = {f"{m}x": lm.mean_stats(*lm.trades(ev, sides, m)[:2], D0, D1) for m in MULTS}
    b["concurrency"] = lm.concurrency(ev, sides)
    return b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if not a.run:
        ap.error("use --run (the PREREG must be frozen first)")
    from scripts.run_clockflow import check_inputs
    prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    log(f"PREREG verified; {len(shas)} inputs match")
    lmap = lighter_map(pd.read_csv(ROOT / CONTRACTS))
    snaps = frozen_files(LANE / "PREREG.md", BOOKS)
    rows = pd.concat([pd.read_parquet(ROOT / f, columns=["symbol", "buy_1k_bp", "sell_1k_bp"]) for f in snaps])
    costs = book_costs(rows, set(lmap.values()))
    ev = pd.read_csv(ROOT / EVENTS)
    ev = ev[ev.symbol.isin(lmap) & (ev.t // DAY >= D0) & (ev.t // DAY < D1)].reset_index(drop=True)
    lm.check_grid(ev)
    counts = {"events_on_lighter_coins": int(len(ev))}
    g = np.full(len(ev), np.nan)
    status = np.full(len(ev), 4)              # 4: no Lighter bars held for the coin
    for sym, idx in ev.groupby("symbol").groups.items():
        f = ROOT / CANDLES / f"{lmap[sym]}.parquet"
        if not f.exists():
            continue
        cd = pd.read_parquet(f, columns=["t", "close", "quote_volume"])
        if cd.empty:
            continue
        fu = ROOT / FUNDING / f"{lmap[sym]}.parquet"
        fd = pd.read_parquet(fu, columns=["t", "rate"]) if fu.exists() else pd.DataFrame(columns=["t", "rate"])
        grid = coin_grid(cd, fd)
        for k in idx:
            g[k], status[k] = price(ev.t[k], ev.exit[k], ev.side[k], *grid)
    counts.update({name: int((status == s).sum()) for s, name in
                   ((0, "priced"), (1, "dropped_untraded_72h"), (2, "dropped_missing_close"),
                    (3, "dropped_outside_bars"), (4, "dropped_no_bars"))})
    ev["g_bin"], ev["g"] = ev.g, g
    ev["lsym"] = ev.symbol.map(lmap)
    priced = ev[status == 0]
    counts["priced_on_coins_without_a_cost"] = int((~priced.lsym.isin(costs)).sum())
    counts["coins_without_a_cost"] = sorted(priced.lsym[~priced.lsym.isin(costs)].unique().tolist())
    ev = priced[priced.lsym.isin(costs)].reset_index(drop=True)
    ev["c"] = ev.lsym.map(costs)
    counts.update({"events": int(len(ev)), "coins": int(ev.symbol.nunique())})
    log(json.dumps(counts))
    lz = lm.policy(ev)
    res = {"lane": "levels_lighter_v1", "registry": "R337", "trials": TRIALS, "counts": counts, "books": {},
           "controls": {}, "costs_bp_one_way": {s: round(1e4 * costs[lmap[s]], 3) for s in sorted(ev.symbol.unique())},
           "book_snapshots": len(snaps), "inputs": len(shas)}
    for key, frame, sides in (("LZ_SUM", ev, lz), ("LP1_TRADES", ev, ev.side_P1.values.astype(int)),
                              ("LZ_BINANCE", ev.assign(g=ev.g_bin), lz)):
        res["books"][key] = book(frame, sides)
        b = res["books"][key]
        log(key, json.dumps({m: {k: b[m].get(k) for k in ("trades", "bp_per_day", "t", "bp_per_trade")}
                             for m in ("gross", "1x", "2x", "3x")}))
    for key, sides in (("THROUGH", np.ones(len(ev), int)), ("AWAY", -np.ones(len(ev), int))):
        res["controls"][key] = {f"{m}x": sum_stats(*lm.trades(ev, sides, m)) for m in (0, 1)}
    on = lz != 0
    gl, c = ev.g.values[on], ev.c.values[on]
    actual = float(np.mean(lz[on] * gl - 2 * c))
    rng = np.random.default_rng(SEED)
    draws = np.array([np.mean(rng.choice((-1, 1), size=on.sum()) * gl - 2 * c) for _ in range(1000)])
    res["controls"]["RANDOM_SIDES"] = {"actual_bp_per_trade_1x": round(1e4 * actual, 2),
                                       "placebo_mean_bp": round(1e4 * float(draws.mean()), 2),
                                       "p_placebo_ge_actual": float((draws >= actual).mean())}
    gap = lz[on] * (ev.g.values[on] - ev.g_bin.values[on])
    res["venue_gap"] = {"corr_g_lighter_binance": round(float(np.corrcoef(ev.g, ev.g_bin)[0, 1]), 4),
                        "lz_mean_bp_lighter_minus_binance": round(1e4 * float(gap.mean()), 2),
                        "lz_median_abs_bp": round(1e4 * float(np.median(np.abs(gap))), 2)}
    net, day, sym = lm.trades(ev, lz, 1)
    coin = pd.DataFrame({"sym": sym, "net": net}).groupby("sym").net.agg(["size", "mean", "sum"])
    coin["share"] = coin["sum"] / coin["sum"].sum()
    res["by_coin_1x"] = {s: {"trades": int(r["size"]), "bp_per_trade": round(1e4 * r["mean"], 2),
                             "share_of_net": round(float(r["share"]), 3), "cost_bp": res["costs_bp_one_way"][s]}
                         for s, r in coin.sort_values("sum", ascending=False).iterrows()}
    verdict, checks = lm.decide(res["books"]["LZ_SUM"])
    res["verdict"], res["checks"] = verdict, checks
    out = LANE / "results"
    out.mkdir(exist_ok=True)
    (out / "summary.json").write_text(json.dumps(res, indent=1) + "\n")
    log("verdict", verdict, json.dumps(checks))


if __name__ == "__main__":
    main()
