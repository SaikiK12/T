"""R336 levels_mexc0_v1: R333's level model on MEXC's zero-fee perps, at the measured MEXC spread (gate 0).

The owner wants short-hold futures edges only. R333's break-or-rebound model (hourly decisions, exits at +/- sigma12
or after 12 h) earned +30 bp gross per trade but did not pay the lab's API fees. MEXC lists perps with zero maker and
zero taker fees; on those the cost of a trade is the spread. This lane reads R333's saved V0 out-of-sample trades
(2022-01..2026-09, Binance closes and funding) on the coins whose MEXC perp was 0/0 on every one of the five contract
snapshots, charges each coin its median quoted MEXC half-spread (floor 1 bp) on entry and exit, and asks whether a
constant-size book of those trades pays. It places no orders.

usage: python scripts/run_levels_mexc0.py --run      # verifies the frozen PREREG and its inputs, then runs
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

LANE = ROOT / "experiments" / "levels_mexc0_v1"
EVENTS = "experiments/level_probability_v2/results/v0_oos_events.csv.gz"
SNAPSHOTS = tuple(f"data/mexc/contracts/2026-10-{d}.json" for d in ("19", "20", "21", "22", "26"))
H = 3_600_000
DAY = 24 * H
GRID0 = 1609459200000          # R333's hourly grid starts 2021-01-01 00:00 UTC: an exit row x closes at GRID0 + (x+1)H
HORIZON = 12                   # R333's V0 horizon in hours
D0, D1 = 18993, 20727          # 2022-01-01 .. 2026-10-01 (exclusive), in days since the epoch, as in R333
HALF = 19723                   # 2024-01-01: the second half starts here
FLOOR_BP = 1.0                 # the one-way cost is the median quoted half-spread, at least 1 bp
MULTS = (1, 2, 3)
CAP = 7                        # the manual book: the first 7 trades of each UTC day
TRIALS = 6                     # PZ day-sum, PZ day-mean, PZ capped, P1 trades, THROUGH, AWAY
SEED = 336
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def zero_fee_core(snapshots):
    """Contracts listed as trading (state 0) with zero maker and zero taker fees on every snapshot, and each one's
    base coin."""
    core, base = None, {}
    for rows in snapshots:
        z = {r["symbol"] for r in rows if r.get("state") == 0 and r.get("takerFeeRate") == 0
             and r.get("makerFeeRate") == 0}
        core = z if core is None else core & z
        base.update({r["symbol"]: r["baseCoin"] for r in rows})
    return core, {s: base[s] for s in core}


def half_spreads(ticks):
    """Median quoted half-spread in bp per contract, from (symbol, bid, ask) rows with a valid two-sided quote."""
    ok = (ticks.t_bid1 > 0) & (ticks.t_ask1 >= ticks.t_bid1)
    q = ticks[ok]
    hs = (q.t_ask1 - q.t_bid1) / (q.t_ask1 + q.t_bid1) * 1e4
    return hs.groupby(q.symbol).median()


def coin_costs(core_base, med, floor_bp=FLOOR_BP):
    """Binance symbol (base + USDT) -> (cheapest zero-fee contract, its median half-spread in bp, one-way cost as a
    fraction). A coin with several zero-fee contracts takes the one with the lowest median half-spread."""
    out = {}
    for sym in sorted(core_base):
        if sym not in med.index:
            continue
        key = core_base[sym] + "USDT"
        hs = float(med[sym])
        if key not in out or hs < out[key][1]:
            out[key] = (sym, hs, max(floor_bp, hs) / 1e4)
    return out


def exit_close_ms(exit_row):
    return GRID0 + (np.asarray(exit_row, np.int64) + 1) * H


def check_grid(ev):
    """Structural check of the saved events (no outcome is read): the exit row sits 1..12 hours after the decision row
    on the 2021-01-01 grid, and each coin has at most one open event at a time."""
    row = (ev.t.values - GRID0) // H
    if ((ev.t.values - GRID0) % H != 0).any():
        raise ValueError("a decision time is off the hourly grid")
    gap = ev.exit.values - row
    if (gap < 1).any() or (gap > HORIZON).any():
        raise ValueError("an exit row is not 1..12 h after its decision row")
    for _, g in ev.groupby("symbol"):
        o = g.sort_values("t")
        if (o.t.values[1:] < exit_close_ms(o.exit.values[:-1])).any():
            raise ValueError("overlapping events on one coin")


def policy(ev, mult=4.0):
    """+1 through the level, -1 away, 0 abstain: trade when |expected return| > mult x the one-way cost (4 x = twice
    the round trip)."""
    edge = ev.E_sigma.values * ev.sig.values
    with np.errstate(invalid="ignore"):
        take = np.isfinite(edge) & (np.abs(edge) > mult * ev.c.values)
    return np.where(take, np.sign(edge), 0).astype(int)


def manual_cap(ev, sides, cap=CAP):
    """Keep the first `cap` trades of each UTC day by decision time; equal times go to the larger |expected|."""
    on = np.flatnonzero(sides != 0)
    if len(on) == 0:
        return sides.copy()
    f = pd.DataFrame({"k": on, "day": ev.t.values[on] // DAY, "t": ev.t.values[on],
                      "e": -np.abs(ev.E_sigma.values[on] * ev.sig.values[on])}).sort_values(["day", "t", "e"])
    keep = f.groupby("day").head(cap).k.values
    out = np.zeros_like(sides)
    out[keep] = sides[keep]
    return out


def trades(ev, sides, mult, one_way=None):
    """Net return of each trade at mult x the one-way cost on entry and exit, its entry day and its symbol."""
    on = sides != 0
    c = ev.c.values[on] if one_way is None else np.full(int(on.sum()), one_way)
    net = sides[on] * ev.g.values[on] - 2 * mult * c
    return net, ev.t.values[on] // DAY, ev.symbol.values[on]


def day_sums(net, day, d0=D0, d1=D1):
    """The constant-size book: each calendar day's summed net (0 on a day with no trade), in per-trade notional."""
    s = pd.Series(net).groupby(day).sum()
    full = pd.Series(0.0, index=np.arange(d0, d1))
    s = s[(s.index >= d0) & (s.index < d1)]
    full.loc[s.index] = s.values
    return full


def drawdown(x):
    c = np.cumsum(x)
    return float((np.maximum.accumulate(np.concatenate([[0.0], c]))[1:] - c).max())


def sum_stats(net, day, sym, d0=D0, d1=D1, best=10):
    """The decided day-sum statistics plus what is reported with them."""
    sel = (day >= d0) & (day < d1)
    net, day, sym = net[sel], day[sel], sym[sel]
    if len(net) == 0:
        return {"trades": 0}
    full = day_sums(net, day, d0, d1)
    n, mu, t = newey_west_t(full.values, 3)
    wo = full.drop(full.nlargest(best).index)
    first, second = full[full.index < HALF], full[full.index >= HALF]
    by_coin = pd.Series(net).groupby(sym).sum()
    top = by_coin.idxmax()
    full_wo_top = day_sums(net[sym != top], day[sym != top], d0, d1)
    tpd = pd.Series(1, index=day).groupby(level=0).sum().reindex(full.index, fill_value=0)
    yr = pd.to_datetime(day * DAY, unit="ms").year
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
            "bp_per_trade_by_year": {int(k): round(1e4 * float(v), 2) for k, v in pd.Series(net).groupby(yr).mean().items()},
            "max_drawdown_trade_units": round(drawdown(full.values), 3),
            "worst_day_trade_units": round(float(full.min()), 3),
            "trade_bp_quantiles": {str(q): round(1e4 * float(np.quantile(net, q)), 1)
                                   for q in (0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99)}}


def mean_stats(net, day, d0=D0, d1=D1):
    """R333's convention, reported beside the decided series: each day's mean net per trade, days with no trade missing."""
    sel = (day >= d0) & (day < d1)
    s = pd.Series(net[sel]).groupby(day[sel]).mean()
    full = pd.Series(np.nan, index=np.arange(d0, d1))
    full.loc[s.index] = s.values
    n, mu, t = newey_west_t(full.values, 3)
    return {"days": int(n), "bp_per_day": round(1e4 * mu, 2), "t": None if np.isnan(t) else round(float(t), 2)}


def concurrency(ev, sides):
    """Open trades at each hour: a trade is open from its decision close to its exit close."""
    on = sides != 0
    a = (ev.t.values[on] + H) // H
    z = exit_close_ms(ev.exit.values[on]) // H
    if len(a) == 0:
        return {"max": 0, "p95": 0.0}
    lo = int(a.min())
    d = np.zeros(int(z.max()) - lo + 2, np.int64)
    np.add.at(d, a - lo, 1)
    np.add.at(d, z - lo, -1)
    open_ = np.cumsum(d)[:-1]
    return {"max": int(open_.max()), "p95": float(np.percentile(open_, 95))}


def decide(primary):
    """PARTIAL (gate 0) only if all five hold on the primary book; else NULL."""
    p1, p2 = primary["1x"], primary["2x"]
    checks = {"t_1x_ge_2": (p1.get("t") or -99) >= 2.0,
              "mean_2x_gt_0": p2["bp_per_day"] > 0,
              "wo_best10_1x_gt_0": p1["bp_per_day_wo_best10"] > 0,
              "both_halves_1x_gt_0": p1["bp_per_day_first_half"] > 0 and p1["bp_per_day_second_half"] > 0,
              "wo_best_coin_1x_gt_0": p1["bp_per_day_wo_best_coin"] > 0}
    return ("PARTIAL" if all(checks.values()) else "NULL"), checks


def frozen_ticker_files(prereg_path):
    """The MEXC ticker snapshots named in the PREREG's inputs block, and only those: the recorder keeps adding files."""
    block = re.search(r"```inputs\n(.*?)```", Path(prereg_path).read_text(), re.S).group(1)
    return [line.split()[1] for line in block.strip().splitlines() if "data/recorders/mexc_ticker/" in line]


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
    core, core_base = zero_fee_core([json.loads((ROOT / p).read_text()) for p in SNAPSHOTS])
    files = frozen_ticker_files(LANE / "PREREG.md")
    ticks = pd.concat([pd.read_parquet(ROOT / f, columns=["symbol", "t_bid1", "t_ask1"]) for f in files])
    costs = coin_costs(core_base, half_spreads(ticks[ticks.symbol.isin(core)]))
    ev = pd.read_csv(ROOT / EVENTS)
    ev = ev[ev.symbol.isin(costs)].reset_index(drop=True)
    ev["c"] = ev.symbol.map(lambda s: costs[s][2])
    check_grid(ev)
    log(f"zero-fee contracts {len(core)}, coins with events {ev.symbol.nunique()}, events {len(ev)}")
    pz = policy(ev)
    books = {"PZ_SUM": pz, "PZ_CAP7": manual_cap(ev, pz), "P1_TRADES": ev.side_P1.values.astype(int)}
    res = {"lane": "levels_mexc0_v1", "registry": "R336", "trials": TRIALS, "books": {}, "controls": {},
           "costs": {k: {"contract": v[0], "median_half_spread_bp": round(v[1], 3), "one_way_bp": round(1e4 * v[2], 3)}
                     for k, v in sorted(costs.items())},
           "ticker_snapshots": len(files), "zero_fee_contracts": sorted(core), "inputs": shas}
    for key, sides in books.items():
        b = {f"{m}x": sum_stats(*trades(ev, sides, m)) for m in MULTS}
        b["gross"] = sum_stats(*trades(ev, sides, 0))
        on = sides != 0
        b["break_even_bp_one_way"] = round(1e4 * float(np.mean(sides[on] * ev.g.values[on])) / 2, 2) if on.any() else None
        b["day_mean_convention"] = {f"{m}x": mean_stats(*trades(ev, sides, m)[:2]) for m in MULTS}
        b["concurrency"] = concurrency(ev, sides)
        res["books"][key] = b
        log(key, json.dumps({m: {k: b[m].get(k) for k in ("trades", "bp_per_day", "t", "bp_per_trade")}
                             for m in ("gross", "1x", "2x", "3x")}))
    for key, sides in (("THROUGH", np.ones(len(ev), int)), ("AWAY", -np.ones(len(ev), int))):
        res["controls"][key] = {f"{m}x": sum_stats(*trades(ev, sides, m)) for m in (0, 1)}
    on = pz != 0
    g, c = ev.g.values[on], ev.c.values[on]
    actual = float(np.mean(pz[on] * g - 2 * c))
    rng = np.random.default_rng(SEED)
    draws = np.array([np.mean(rng.choice((-1, 1), size=on.sum()) * g - 2 * c) for _ in range(1000)])
    res["controls"]["RANDOM_SIDES"] = {"actual_bp_per_trade_1x": round(1e4 * actual, 2),
                                       "placebo_mean_bp": round(1e4 * float(draws.mean()), 2),
                                       "p_placebo_ge_actual": float((draws >= actual).mean())}
    net, day, sym = trades(ev, pz, 1)
    coin = pd.DataFrame({"sym": sym, "net": net}).groupby("sym").net.agg(["size", "mean", "sum"])
    coin["share"] = coin["sum"] / coin["sum"].sum()
    res["by_coin_1x"] = {s: {"trades": int(r["size"]), "bp_per_trade": round(1e4 * r["mean"], 2),
                             "share_of_net": round(float(r["share"]), 3)}
                         for s, r in coin.sort_values("sum", ascending=False).iterrows()}
    verdict, checks = decide(res["books"]["PZ_SUM"])
    res["verdict"], res["checks"] = verdict, checks
    out = LANE / "results"
    out.mkdir(exist_ok=True)
    (out / "summary.json").write_text(json.dumps(res, indent=1) + "\n")
    log("verdict", verdict, json.dumps(checks))


if __name__ == "__main__":
    main()
