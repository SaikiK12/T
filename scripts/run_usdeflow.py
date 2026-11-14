"""usdeflow_v1 (R488, M535): does the weekly change in USDe circulating supply rank-correlate with the next week's
change in Hyperliquid BTC and ETH funding, beyond a circular-shift null? Gate 0 on history, as set out in
experiments/usdeflow_v1/PREREG.md. A predictor test, not a book; the six forward carry books' week-ahead net is
reported as the spread proxy.

Verifies the PREREG, its inputs block and raw/manifest.json (every body's sha256), then reads raw/ only.

usage: python scripts/run_usdeflow.py
"""
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

LANE = ROOT / "experiments" / "usdeflow_v1"
RAW = LANE / "raw"
LLAMA_FILE = "llama/stablecoin_146.json"
COINS = ("BTC", "ETH")               # both decide
MIN_SUPPLY = 1e8                     # first sample week t: supply at the end of week t-1 > $100m
LAST_TARGET_END = "2026-11-08"       # last day (Sunday) of the last target week t+1
CUT = "2026-11-09"                   # nothing stamped at or after 00:00 UTC of this day is read
MIN_HOURS = 150                      # of 168 hourly settlements, else the week's mean funding is missing
MIN_SHIFT = 5                        # circular shifts k in [5, n - 5]: shifts within +/-4 weeks excluded
DAY = 86_400_000
WEEK = 7 * DAY
COSTS = (1, 2, 3)
BOOKS = {"R278 A": "gate+hyperliquid L14d th5% K20", "R278 B": "binance+mexc L14d th10% K20",
         "R278 C": "gate+mexc L7d th10% K20", "R390 A": "binance+gate L14d th10% K20",
         "R279 A": "gate+kucoin L14d th5% K20", "R279 B": "binance+kucoin L14d th5% K20"}
DAILY = ("experiments/carry_v2_audit_v1/results/daily.csv", "experiments/carry_v2_audit_kc_v1/results/daily.csv")
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def ms(day):
    return int(pd.Timestamp(day, tz="UTC").value // 10**6)


def day_label(t):
    return str(pd.Timestamp(int(t), unit="ms", tz="UTC").date())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------- inputs
def check_inputs(prereg_path):
    """Every file in the PREREG's inputs block hashes to its frozen sha256."""
    block = re.search(r"```inputs\n(.*?)```", Path(prereg_path).read_text(), re.S).group(1)
    n = 0
    for line in block.strip().splitlines():
        want, rel = line.split()
        got = sha(ROOT / rel)
        if got != want:
            raise SystemExit(f"{rel}: sha256 {got} != frozen {want}")
        n += 1
    return n


def check_manifest(raw=RAW):
    man = json.loads((Path(raw) / "manifest.json").read_text())
    for rel, want in man["files"].items():
        if sha(Path(raw) / rel) != want:
            raise SystemExit(f"raw/{rel}: sha256 differs from raw/manifest.json")
    return man


# ---------------------------------------------------------------- loaders
def parse_supply(body, cut=CUT):
    """DefiLlama /stablecoin/{id}: daily points {date (s, 00:00 UTC), circulating: {peggedUSD}} under `tokens`
    (summed over chains by DefiLlama); the documented `totalCirculating` list is used only if `tokens` is absent.
    Returns (Series of USD by UTC day, field used). Points stamped at or after the cut are dropped."""
    if "tokens" in body:
        pts = {day_label(int(p["date"]) * 1000): p.get("circulating", {}).get("peggedUSD") for p in body["tokens"]}
        field = "tokens[].circulating.peggedUSD"
    else:
        pts = {day_label(int(p["date"]) * 1000): p.get("totalCirculating") for p in body["totalCirculating"]}
        field = "totalCirculating[].totalCirculating"
    s = pd.Series(pts, dtype=float).sort_index()
    s = s[(s.index < cut) & s.notna() & (s > 0)]
    return s, field


def parse_funding(bodies, coin, cut=CUT):
    """Hyperliquid fundingHistory rows {coin, fundingRate, premium, time (ms)} -> DataFrame time, rate (fraction
    of notional per hour, + when longs pay), deduplicated, cut before 00:00 UTC of the cut day."""
    rows = [r for b in bodies for r in b]
    if any(r["coin"] != coin for r in rows):
        raise ValueError(f"{coin}: a row for another coin")
    f = pd.DataFrame({"time": [int(r["time"]) for r in rows], "rate": [float(r["fundingRate"]) for r in rows]})
    f = f.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    return f[f.time < ms(cut)].reset_index(drop=True)


def load_raw(raw=RAW):
    raw = Path(raw)
    supply, field = parse_supply(json.loads((raw / LLAMA_FILE).read_text()))
    fund = {}
    for coin in COINS:
        files = sorted((raw / "hl").glob(f"{coin}_funding_*.json"))
        fund[coin] = parse_funding([json.loads(p.read_text()) for p in files], coin)
    return supply, field, fund


def load_daily(paths=DAILY):
    d = pd.concat([pd.read_csv(ROOT / p) for p in paths], ignore_index=True)
    return d[(d.engine == "v2") & d.book.isin(BOOKS.values())].reset_index(drop=True)


# ---------------------------------------------------------------- weekly series
def monday(day):
    """ISO week label: the Monday (UTC) that starts the week holding day."""
    t = pd.Timestamp(day)
    return str((t - pd.Timedelta(days=t.weekday())).date())


def add_days(day, n):
    return day_label(ms(day) + n * DAY)


def mondays(first, last):
    return [day_label(t) for t in range(ms(monday(first)), ms(monday(last)) + 1, WEEK)]


def weekly_supply(supply, stamp="monday"):
    """For the week starting Monday m: S_end(m) = supply stamped on m + 7 (00:00 UTC of the next Monday, the week's
    end; 'monday', decides) or on m + 6 (the Sunday, 'sunday', reported). w(m) = log S_end(m) - log S_end(m - 7)."""
    off = 7 if stamp == "monday" else 6
    weeks = mondays(supply.index[0], supply.index[-1])
    end = pd.Series({m: supply.get(add_days(m, off), np.nan) for m in weeks}, dtype=float)
    prev = end.shift(1)
    return pd.DataFrame({"s_end": end, "s_prev": prev, "w": np.log(end) - np.log(prev)})


def weekly_funding(f, min_hours=MIN_HOURS):
    """Mean hourly funding rate of rows stamped in [Monday 00:00, next Monday 00:00) UTC; NaN under min_hours."""
    wk = [monday(day_label(t)) for t in f.time]
    g = f.assign(week=wk).groupby("week").rate.agg(["mean", "size"])
    return g["mean"].where(g["size"] >= min_hours), g["size"]


def weekly_proxy(daily):
    """Per day, the mean v2 net over the forward books with a row that day; per week, the mean over its 7 days
    (NaN unless all 7 days are present). Fraction of book capital per day, at 1x/2x/3x."""
    by_day = daily.groupby("date").agg(**{f"net_{c}x": (f"net_{c}x", "mean") for c in COSTS},
                                       books=("book", "nunique"))
    by_day = by_day.assign(week=[monday(d) for d in by_day.index])
    g = by_day.groupby("week")
    out = g[[f"net_{c}x" for c in COSTS]].mean()
    out["days"] = g.size()
    out["books_min"] = g.books.min()
    for c in COSTS:
        out[f"net_{c}x"] = out[f"net_{c}x"].where(out.days == 7)
    return out


def panel(w, fund_weekly, proxy=None, last_target_end=LAST_TARGET_END, min_supply=MIN_SUPPLY):
    """Rows t (Monday labels) from the first week with S_end(t - 1) > min_supply to the last t whose week t + 1 ends
    on or before last_target_end. Per coin: f(t), f(t + 1), d(t) = f(t + 1) - f(t). Proxy at t + 1."""
    ok = w.index[w.s_prev > min_supply]
    if not len(ok):
        raise ValueError("no week with supply above the threshold")
    last_t = add_days(monday(add_days(last_target_end, -6)), -7)
    weeks = [m for m in w.index if ok[0] <= m <= last_t]
    p = pd.DataFrame(index=weeks)
    p["w"] = w.w.reindex(weeks)
    nxt = [add_days(m, 7) for m in weeks]
    for coin, fw in fund_weekly.items():
        p[f"f_{coin}"] = fw.reindex(weeks).to_numpy()
        p[f"f_next_{coin}"] = fw.reindex(nxt).to_numpy()
        p[f"d_{coin}"] = p[f"f_next_{coin}"] - p[f"f_{coin}"]
    if proxy is not None:
        for c in COSTS:
            p[f"proxy_next_{c}x"] = proxy[f"net_{c}x"].reindex(nxt).to_numpy()
    return p


# ---------------------------------------------------------------- statistics
def ranks(x):
    return pd.Series(x).rank(method="average").to_numpy(float)


def spearman(x, y):
    return float(np.corrcoef(ranks(x), ranks(y))[0, 1])


def circular_null(x, y, min_shift=MIN_SHIFT):
    """Spearman rho of x against y and of x circularly shifted by every k in [min_shift, n - min_shift].
    p_one = share of rho_k >= rho; p_neg = share of rho_k <= rho; p_two = share of |rho_k| >= |rho|."""
    rx, ry = ranks(x), ranks(y)
    rho = float(np.corrcoef(rx, ry)[0, 1])
    n = len(rx)
    ks = np.arange(min_shift, n - min_shift + 1)
    null = np.array([np.corrcoef(np.roll(rx, k), ry)[0, 1] for k in ks])
    has = len(ks) > 0
    return {"n": int(n), "rho": rho, "shifts": int(len(ks)),
            "p_one": float((null >= rho).mean()) if has else None,
            "p_neg": float((null <= rho).mean()) if has else None,
            "p_two": float((np.abs(null) >= abs(rho)).mean()) if has else None,
            "null_mean": float(null.mean()) if has else None}


def pairs(p, col):
    ok = p.w.notna() & p[col].notna() & np.isfinite(p.w) & np.isfinite(p[col])
    return p.w[ok].to_numpy(float), p[col][ok].to_numpy(float), list(p.index[ok])


def halves(x, y):
    """Spearman rho of the first n // 2 pairs and of the rest, in time order."""
    h = len(x) // 2
    return {"first_n": int(h), "first_rho": spearman(x[:h], y[:h]),
            "second_n": int(len(x) - h), "second_rho": spearman(x[h:], y[h:])}


def test_coin(p, coin):
    x, y, used = pairs(p, f"d_{coin}")
    c = circular_null(x, y)
    c.update(halves(x, y))
    c.update(first=used[0], last=used[-1])
    return c


def gates(res):
    g1 = all(res[c]["rho"] > 0 and res[c]["p_one"] is not None and res[c]["p_one"] < 0.05 for c in COINS)
    g2 = all(res[c]["first_rho"] > 0 and res[c]["second_rho"] > 0 for c in COINS)
    return {"G1_rho_gt_0_and_p_one_lt_0.05_BTC_and_ETH": bool(g1), "G2_both_halves_positive_BTC_and_ETH": bool(g2)}


def verdict(g):
    return "SIGNAL" if all(g.values()) else "NULL"


def proxy_report(p):
    out = {}
    for c in COSTS:
        col = f"proxy_next_{c}x"
        x, y, used = pairs(p, col)
        if len(x) < 2 * MIN_SHIFT + 2:
            out[f"{c}x"] = {"n": int(len(x))}
            continue
        r = circular_null(x, y)
        r.update(first=used[0], last=used[-1], mean_daily_pct=float(y.mean() * 100),
                 ann_pct=float(y.mean() * 365 * 100),
                 mean_daily_pct_w_pos=float(y[x > 0].mean() * 100) if (x > 0).any() else None,
                 mean_daily_pct_w_nonpos=float(y[x <= 0].mean() * 100) if (x <= 0).any() else None,
                 weeks_w_pos=int((x > 0).sum()))
        out[f"{c}x"] = r
    return out


def main():
    from lab import prereg
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    log(f"inputs: {check_inputs(LANE / 'PREREG.md')} files match the PREREG")
    man = check_manifest()
    log(f"raw: {len(man['files'])} bodies match raw/manifest.json (fetched {man['fetched_utc']})")
    supply, field, fund = load_raw()
    log(f"supply {supply.index[0]}..{supply.index[-1]} ({len(supply)} days, field {field})")
    fw, hours = {}, {}
    for coin in COINS:
        f = fund[coin]
        fw[coin], hours[coin] = weekly_funding(f)
        log(f"{coin} funding {day_label(f.time.iloc[0])}..{day_label(f.time.iloc[-1])} ({len(f)} hours)")
    proxy = weekly_proxy(load_daily())
    w = weekly_supply(supply, "monday")
    p = panel(w, fw, proxy)
    res = {c: test_coin(p, c) for c in COINS}
    g = gates(res)
    rep = {"prereg_sha": prereg.sha256_file(LANE / "PREREG.md"), "manifest_fetched_utc": man["fetched_utc"],
           "supply_field": field, "sample_weeks": {"first": p.index[0], "last": p.index[-1], "rows": int(len(p))},
           "target_change": res, "gates": g, "verdict": verdict(g), "trials": 2}
    lev = {}
    for coin in COINS:
        x, y, used = pairs(p, f"f_next_{coin}")
        lev[coin] = circular_null(x, y)
    ws = weekly_supply(supply, "sunday")
    ps = panel(ws, fw, None)
    sun = {c: test_coin(ps, c) for c in COINS}
    wk_hours = {c: {"min": int(hours[c].reindex(p.index).min()), "weeks_below_min": int(
        (hours[c].reindex(list(p.index) + [add_days(p.index[-1], 7)]).fillna(0) < MIN_HOURS).sum())} for c in COINS}
    rep["reported"] = {"level_next_week": lev, "sunday_stamp": sun, "carry_proxy_next_week": proxy_report(p),
                       "funding_hours": wk_hours,
                       "w_pct": {"median": float(np.nanmedian(p.w) * 100), "p10": float(np.nanpercentile(p.w, 10) * 100),
                                 "p90": float(np.nanpercentile(p.w, 90) * 100)},
                       "supply_usd_first_week_end_prev": float(w.s_prev[p.index[0]])}
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    p.rename_axis("week").to_csv(out / "weekly.csv", float_format="%.10g", lineterminator="\n")
    (out / "report.json").write_text(json.dumps(rep, indent=1, default=float) + "\n")
    for k in ("sample_weeks", "target_change", "gates", "reported"):
        log(k, json.dumps(rep[k], default=float))
    log("verdict", rep["verdict"])


if __name__ == "__main__":
    main()
