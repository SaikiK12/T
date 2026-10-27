"""R335 locked_carry_v1: the guarantee engine, a coin-margined cash-and-carry locked to expiry (measurement).

A coin-margined (inverse) quarterly lets a holder of B coins lock a dollar amount. Short Q = B x F0 dollars of the
quarterly at F0; at expiry the short has earned Q x (1/F_T - 1/F0) coins, so the account holds B x F0 / F_T coins,
worth exactly B x F0 dollars at the settlement price F_T, whatever F_T is. The equity always equals the short's notional
(one times), so the short cannot be liquidated. Bought at spot S0, the locked return is F0/S0 - 1 before costs, and it
is known at entry. Risks that remain: the venue itself, USDT against the dollar, and the settlement index.

This lane measures, on seen hours 2021-01..2026-09, how often and by how much that locked return beat the 3-month
T-bill on Binance's BTC and ETH quarterlies, and what an engine that locks only when it beats the T-bill by a hurdle
would have earned. It places no orders and predicts nothing: each lock's return is fixed at its entry.

usage: python scripts/run_locked_carry.py --run      # verifies the frozen PREREG and its inputs, then runs
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402

LANE = ROOT / "experiments" / "locked_carry_v1"
H = 3_600_000
DAY = 24 * H
T0 = 1609459200000            # 2021-01-01 00:00 UTC: first bar read; nothing earlier is loaded
T1 = 1790812800000            # 2026-10-01 00:00 UTC: end of the window (last bar opens 2026-09-30 23:00)
COINS = ("BTC", "ETH")
TAU_MIN, TAU_MAX = 14.0, 200.0  # days to expiry a lock may have at entry
COST = 0.0025                 # 1x round trip: spot taker 10 bp in and out, futures taker 5 bp
MULTS = (1, 2, 3)
HURDLES = (0.0, 0.03, 0.06)   # lock when the 1x locked yield beats the T-bill by this much a year
TBILL_LAG = 2 * DAY           # a FRED observation dated d is used from d + 2 days on
MIN_TRADES = 10               # a futures bar counts only with at least this many trades (spot files carry no count)
LEVELS = (0.0, 0.03, 0.06, 0.10)
PRIMARY = ("BTC", 0.03)
TRIALS = 6                    # 2 coins x 3 hurdles
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def expiry_ms(name):
    """'BTCUSD_210326' -> 2021-03-26 08:00 UTC in ms, when Binance settles its coin-margined quarterlies."""
    d = datetime.strptime(name.split("_")[1], "%y%m%d").replace(hour=8, tzinfo=timezone.utc)
    return int(d.timestamp() * 1000)


def inverse_short_coins(q_usd, f0, ft):
    """Coins earned by a short of q_usd dollars of an inverse contract opened at f0 and settled at ft."""
    return q_usd * (1.0 / ft - 1.0 / f0)


def locked_value_usd(b, f0, ft):
    """Dollar value at settlement of b coins plus a short of b x f0 dollars opened at f0: b x f0 for every ft."""
    return (b + inverse_short_coins(b * f0, f0, ft)) * ft


def load_close(path, t0=T0, t1=T1):
    """Hourly closes on the grid t0..t1 (NaN where the bar is missing or thin). Rows before t0 are never read."""
    k = pd.read_parquet(path, filters=[("t", ">=", t0), ("t", "<", t1)])
    if len(k) and k.t.min() < t0:
        raise ValueError(f"{path}: a row before {t0} was loaded")
    ok = (k.close > 0) & (k.volume > 0)
    if "count" in k:
        ok &= k["count"] >= MIN_TRADES
    k = k[ok].drop_duplicates("t")
    out = np.full((t1 - t0) // H, np.nan)
    out[(k.t.values - t0) // H] = k.close.values
    return out


def tbill_asof(grid, obs_t, obs_pct, lag=TBILL_LAG):
    """Annual T-bill yield (a fraction) known at each bar's close: the latest observation dated at least `lag` earlier."""
    order = np.argsort(obs_t)
    obs_t, obs_v = np.asarray(obs_t)[order], np.asarray(obs_pct, float)[order] / 100.0
    pos = np.searchsorted(obs_t + lag, grid + H, side="right") - 1
    return np.where(pos >= 0, obs_v[np.maximum(pos, 0)], np.nan)


def best_lock(i, grid, fut, spot, r, cost=COST):
    """At bar i's close: the eligible contract with the highest locked yield over the T-bill (1x), or None."""
    t_close, best = grid[i] + H, None
    if not np.isfinite(spot[i]) or not np.isfinite(r[i]):
        return None
    for name, (exp, f) in fut.items():
        tau = (exp - t_close) / DAY
        if not (TAU_MIN <= tau <= TAU_MAX) or not np.isfinite(f[i]):
            continue
        g = f[i] / spot[i] - 1.0
        e = (g - cost) * 365.0 / tau - r[i]
        if best is None or e > best["excess"]:
            best = dict(contract=name, i=i, expiry=exp, tau=tau, f=f[i], s=spot[i], gross=g, tbill=r[i], excess=e)
    return best


def engine(grid, fut, spot, r, hurdle, cost=COST, mults=MULTS):
    """Lock when the best 1x excess >= hurdle, hold to expiry, then cash at the T-bill; returns locks and hourly logs.

    Bar i's slot is the hour (grid[i], grid[i] + H]. A lock decided at bar i's close holds slots i+1 .. j-1, where
    grid[j] is the expiry; slot j is cash and the next decision is at bar j's close. Cash earns r / 8760 an hour; a
    lock's log return log(1 + gross - m x cost) is spread evenly over its slots. Slots past the window are cut.
    """
    n = len(grid)
    logs = {m: np.zeros(n) for m in mults}
    locked = np.zeros(n, bool)
    locks, i = [], 0
    while i < n:
        b = best_lock(i, grid, fut, spot, r, cost)
        if b is not None and b["excess"] >= hurdle:
            j = int((b["expiry"] - grid[0]) // H)
            slots = j - i - 1
            for m in mults:
                rate = np.log1p(b["gross"] - m * cost) / slots
                logs[m][i + 1:min(j, n)] = rate
            locked[i + 1:min(j, n)] = True
            if np.isfinite(r[i]):
                for m in mults:
                    logs[m][i] = np.log1p(r[i]) / 8760.0
            locks.append(b | {"slots": slots, "in_window": min(j, n) - (i + 1)})
            i = j
            continue
        if np.isfinite(r[i]):
            for m in mults:
                logs[m][i] = np.log1p(r[i]) / 8760.0
        i += 1
    return locks, logs, locked


def cash_logs(r):
    return np.where(np.isfinite(r), np.log1p(np.nan_to_num(r)) / 8760.0, 0.0)


def per_year(grid, logs):
    yr = pd.to_datetime(grid, unit="ms").year
    return pd.Series(logs).groupby(yr).sum()


def annualize(total_log, hours):
    return float(np.expm1(total_log * 8760.0 / hours))


def lock_vs_tbill(locks, r_path, grid, mult, cost=COST):
    """Each lock's return minus what the T-bill actually paid over the same slots (rates can rise after entry)."""
    out = []
    for b in locks:
        a, z = b["i"] + 1, min(b["i"] + 1 + b["slots"], len(grid))
        paid = float(np.expm1(cash_logs(r_path[a:z]).sum()))
        out.append(b["gross"] - mult * cost - paid * (b["slots"] / max(z - a, 1)))
    return np.array(out)


def calendar(grid, fut, spot, r):
    """The best 1x excess on offer at every bar close (NaN when no contract is eligible), plus its gross annualized yield."""
    best = np.full(len(grid), np.nan)
    gross = np.full(len(grid), np.nan)
    for i in range(len(grid)):
        b = best_lock(i, grid, fut, spot, r)
        if b is not None:
            best[i], gross[i] = b["excess"], b["gross"] * 365.0 / b["tau"]
    return best, gross


def summarize(coin, src, grid, fut, spot, r):
    years = pd.to_datetime(grid, unit="ms").year
    best, gross = calendar(grid, fut, spot, r)
    cal = []
    for y in sorted(set(years)):
        sel = (years == y) & np.isfinite(best)
        e = best[sel]
        row = dict(coin=coin, spot=src, year=int(y), hours=int(sel.sum()),
                   gross_ann_mean=round(float(np.nanmean(gross[sel])) * 100, 2),
                   excess_p10=round(float(np.percentile(e, 10)) * 100, 2),
                   excess_p50=round(float(np.percentile(e, 50)) * 100, 2),
                   excess_p90=round(float(np.percentile(e, 90)) * 100, 2))
        for lv in LEVELS:
            row[f"share_ge_{int(lv * 100)}"] = round(float((e >= lv).mean()), 3)
        cal.append(row)
    cash = cash_logs(r)
    hours = len(grid)
    tb_ann = annualize(cash.sum(), hours)
    rules = []
    for h in HURDLES:
        locks, logs, locked = engine(grid, fut, spot, r, h)
        row = dict(coin=coin, spot=src, hurdle=h, locks=len(locks), share_locked=round(float(locked.mean()), 3),
                   tbill_ann=round(tb_ann * 100, 2))
        for m in MULTS:
            ann = annualize(logs[m].sum(), hours)
            row[f"ann_{m}x"] = round(ann * 100, 2)
            row[f"excess_{m}x"] = round((ann - tb_ann) * 100, 2)
            ex_y = per_year(grid, logs[m]).apply(np.expm1) - per_year(grid, cash).apply(np.expm1)
            row[f"years_pos_{m}x"] = int((ex_y > 0).sum())
            row[f"by_year_{m}x"] = {int(k): round(float(v) * 100, 2) for k, v in ex_y.items()}
            vs = lock_vs_tbill(locks, r, grid, m)
            row[f"locks_below_tbill_{m}x"] = int((vs < 0).sum())
        if locks:
            row["entry_excess_mean"] = round(float(np.mean([b["excess"] for b in locks])) * 100, 2)
            row["entry_excess_max"] = round(float(np.max([b["excess"] for b in locks])) * 100, 2)
            row["tau_mean"] = round(float(np.mean([b["tau"] for b in locks])), 1)
        rules.append((row, locks))
    return cal, rules


def verdict(rules):
    """USEFUL when the primary rule beats the T-bill by >= 1%/yr at 2x and is ahead in >= 3 of the 6 years at 2x."""
    p = next(row for row, _ in rules if (row["coin"], row["hurdle"]) == PRIMARY and row["spot"] == "binance")
    ok = p["excess_2x"] >= 1.0 and p["years_pos_2x"] >= 3
    return ("USEFUL" if ok else "NOT_USEFUL"), p


def load_coin(coin, spot_path):
    grid = np.arange(T0, T1, H, dtype=np.int64)
    fut = {}
    for path in sorted((ROOT / "data" / "coinm_1h").glob(f"{coin}USD_2[1-6]*.parquet")):
        exp = expiry_ms(path.stem)
        if exp <= T0:
            continue
        fut[path.stem] = (exp, load_close(path))
    return grid, fut, load_close(spot_path)


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
    tb = pd.read_parquet(ROOT / "data" / "macro" / "ust_3m.parquet")
    tb = tb[(tb.t >= T0 - 60 * DAY) & (tb.t < T1) & tb.value.notna()]
    usdt = load_close(ROOT / "data" / "coinbase" / "USDT-USD.parquet")
    res = LANE / "results"
    res.mkdir(exist_ok=True)
    cals, rows, lock_rows = [], [], []
    for coin in COINS:
        for src, sp in (("binance", ROOT / "data" / "binance_spot" / f"{coin}USDT.parquet"),
                        ("coinbase_usd", ROOT / "data" / "coinbase" / f"{coin}-USD.parquet")):
            grid, fut, spot = load_coin(coin, sp)
            r = tbill_asof(grid, tb.t.values, tb.value.values)
            log(coin, src, "contracts", len(fut), "spot hours", int(np.isfinite(spot).sum()))
            cal, rules = summarize(coin, src, grid, fut, spot, r)
            cals += cal
            for row, locks in rules:
                log(json.dumps({k: v for k, v in row.items() if not k.startswith("by_year")}))
                rows.append(row)
                for b in locks:
                    lock_rows.append(dict(coin=coin, spot=src, hurdle=row["hurdle"], contract=b["contract"],
                                          entry_utc=str(pd.to_datetime(grid[b["i"]] + H, unit="ms")),
                                          tau=round(b["tau"], 2), gross=round(b["gross"] * 100, 3),
                                          tbill=round(b["tbill"] * 100, 2), excess_ann=round(b["excess"] * 100, 2),
                                          slots=b["slots"], in_window=b["in_window"]))
    v, p = verdict([(row, None) for row in rows])
    ok = np.isfinite(usdt)
    summary = dict(lane="locked_carry_v1", registry="R335", verdict=v, primary=p, trials=TRIALS, cost_1x=COST,
                   usdt_usd=dict(hours=int(ok.sum()), p01=round(float(np.percentile(usdt[ok], 1)), 4),
                                 p50=round(float(np.percentile(usdt[ok], 50)), 4),
                                 p99=round(float(np.percentile(usdt[ok], 99)), 4)),
                   rules=rows, calendar=cals, inputs=shas)
    (res / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    pd.DataFrame(lock_rows).to_csv(res / "locks.csv", index=False)
    pd.DataFrame(cals).to_csv(res / "calendar.csv", index=False)
    log("verdict", v, json.dumps({k: p[k] for k in ("excess_1x", "excess_2x", "excess_3x", "years_pos_2x")}))


if __name__ == "__main__":
    main()
