"""R349 minflow_v1: minute-scale order flow and overreaction on the BTC, ETH and SOL perps (M426, M306), priced at
Lighter's zero-fee book cost.

The question: do the most extreme minutes (in price, in signed taker volume, in absorbed or exhausted aggression, or
in BTC's move when ETH or SOL has not followed) predict the next 5 to 60 minutes by more than a round trip on a
zero-fee venue? A taker on Lighter pays no fee and about 0.25 bp a side to fill $1k on these three coins (R348), so a
rule needs only about half a basis point a trade, where Binance's or MEXC's API needs 15-17.

Every rule fires at a bar's close, enters at the next bar's open (the Lighter API fills in under a second; R348 found
Lighter's quote level with Binance's within one second) and exits h minutes later, one position per coin at a time.
Prices are Binance's 1-minute trade prints, moved half a tick against the trade on entry and exit. The family is
decided by a studentized reality check on 2021-04..2023 and the selected rule's read on 2024-01..2026-09, as in R289.

usage: python scripts/run_minflow.py    (verifies the frozen PREREG and every input hash first)
"""
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import inference, orderflow, prereg, stats  # noqa: E402

LANE = ROOT / "experiments" / "minflow_v1"
REGISTRY = "R349"
COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
ALTS = ("ETHUSDT", "SOLUSDT")
MIN, HOUR, DAY = 60_000, 3_600_000, 86_400_000


def ms(day):
    return int(pd.Timestamp(day, tz="UTC").value // 10**6)


T0, T1 = ms("2021-01-01"), ms("2026-10-01")       # 2020 is reserved (docs/GATES.md): never loaded
DISC = ("2021-04-01", "2023-12-31")
VALID = ("2024-01-01", "2026-09-30")
HALVES = (("2024-01-01", "2025-06-30"), ("2025-07-01", "2026-09-30"))
KS = (1, 5, 15)                                   # look-back of the statistic, minutes
HOLDS = (5, 15, 60)                               # minutes
Q, QWIN_H, QMIN = 0.995, 168, 5 * 1440            # threshold: 99.5th percentile of |stat| over the previous 7 days
ABS_WINDOW, ABS_K, ABS_M = 60, 3.0, 0.5           # lab.orderflow.absorption's defaults
EXH_WINDOW = 60                                   # lab.orderflow.exhaustion's default
WALK_BP = {"BTCUSDT": 0.27, "ETHUSDT": 0.23, "SOLUSDT": 0.30}   # Lighter $1k book walk a side, R348 (run.log)
WEB_BP, API_BP = 3.0, 8.5                         # MEXC web and API cost a side, reported only (as R289)
RC_B, RC_BLOCK, SEED = 2000, 10, 349
NW_LAG, RC_ALPHA, T_BAR = 10, 0.05, 2.0


def log(msg):
    line = f"{time.strftime('%H:%M:%S', time.gmtime())} {msg}"
    print(line, flush=True)
    with open(LANE / "run.log", "a") as f:
        f.write(line + "\n")


def frozen_inputs(prereg_path, root=ROOT):
    """Every file in the PREREG's inputs block must still hash to its frozen sha256."""
    block = re.search(r"```inputs\n(.*?)```", Path(prereg_path).read_text(), re.S).group(1)
    shas = {}
    for line in block.strip().splitlines():
        want, rel = line.split()
        got = prereg.sha256_file(root / rel)
        if got != want:
            raise prereg.PreregError(f"{rel}: sha256 {got} != frozen {want}")
        shas[rel] = got
    return shas


# ------------------------------------------------------------------------------------------------------------- data
def load_bars(path, t0=T0, t1=T1):
    """The bars opening in [t0, t1) on a full minute grid; NaN where a bar is missing or invalid (count 0, close 0).
    Rows outside [t0, t1) are filtered by the reader and never reach this code."""
    cols = ["t", "open", "high", "low", "close", "volume", "count", "taker_buy_volume"]
    k = pq.read_table(path, columns=cols, filters=[("t", ">=", t0), ("t", "<", t1)]).to_pandas()
    k = k.drop_duplicates("t")
    k = k[(k["count"] > 0) & (k.close > 0) & (k.open > 0)]
    n = (t1 - t0) // MIN
    out = {c: np.full(n, np.nan) for c in ("open", "high", "low", "close", "volume", "tbv")}
    i = ((k.t.values - t0) // MIN).astype(np.int64)
    for c, src in (("open", "open"), ("high", "high"), ("low", "low"), ("close", "close"), ("volume", "volume"),
                   ("tbv", "taker_buy_volume")):
        out[c][i] = k[src].values.astype(float)
    return out


def load_funding(path, t0=T0, t1=T1):
    """Settlement times (rounded to the minute) and rates inside [t0, t1)."""
    f = pq.read_table(path, columns=["t", "rate"], filters=[("t", ">=", t0), ("t", "<", t1)]).to_pandas()
    f = f.sort_values("t")
    return np.rint(f.t.values / MIN).astype(np.int64) * MIN, f.rate.values.astype(float)


def month_ticks(bars, t0=T0):
    """Per bar, the price tick of its calendar month: the smallest positive gap between two distinct prices printed
    in that month (open, high, low or close), rounded to 6 significant digits."""
    n = len(bars["close"])
    month = pd.to_datetime(t0 + np.arange(n, dtype=np.int64) * MIN, unit="ms").to_period("M").asi8
    out = np.full(n, np.nan)
    px = np.column_stack([bars[c] for c in ("open", "high", "low", "close")])
    for m in np.unique(month):
        sel = month == m
        p = px[sel].ravel()
        p = np.unique(np.round(p[np.isfinite(p)], 8))
        if len(p) < 2:
            continue
        g = np.diff(p)
        g = g[g > p[:-1] * 1e-12]
        if len(g):
            out[sel] = float(f"{g.min():.6g}")
    return out


# ------------------------------------------------------------------------------------------------------- statistics
def kret(close, k):
    """ln(C[i] / C[i-k]); NaN when either bar is missing."""
    r = np.full(len(close), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        r[k:] = np.log(close[k:] / close[:-k])
    return r


def kflow(d, k):
    """Signed taker volume (2 b - v) summed over the last k bars; NaN when any of them is missing."""
    return pd.Series(d).rolling(k, min_periods=k).sum().values


def hourly_quantile(a, q=Q, win_h=QWIN_H, min_n=QMIN):
    """For each hour h (bars 60h..60h+59), the q-quantile of |a| over the bars of the previous win_h hours, NaN when
    fewer than min_n of them are finite. Only bars before the hour enter its threshold."""
    x = np.abs(np.asarray(a, float))
    n_h = len(x) // 60
    out = np.full(n_h, np.nan)
    for h in range(n_h):
        w = x[max(0, (h - win_h) * 60): h * 60]
        w = w[np.isfinite(w)]
        if len(w) >= min_n:
            j = int(np.floor(q * (len(w) - 1)))
            out[h] = np.partition(w, j)[j]
    return out


def per_bar(hourly, n):
    """Expand an hourly array to bars."""
    out = np.full(n, np.nan)
    m = min(n, 60 * len(hourly))
    out[:m] = np.repeat(hourly, 60)[:m]
    return out


def hourly_beta(x, y, win_h=QWIN_H, min_n=QMIN):
    """OLS slope of y on x over the previous win_h hours of bars where both are finite, per hour."""
    ok = np.isfinite(x) & np.isfinite(y)
    xs, ys = np.where(ok, x, 0.0), np.where(ok, y, 0.0)
    c = lambda v: np.concatenate([[0.0], np.cumsum(v)])
    N, SX, SY, SXX, SXY = c(ok.astype(float)), c(xs), c(ys), c(xs * xs), c(xs * ys)
    n_h = len(x) // 60
    hi = np.arange(n_h) * 60
    lo = np.maximum(0, hi - win_h * 60)
    n = N[hi] - N[lo]
    sx, sy, sxx, sxy = SX[hi] - SX[lo], SY[hi] - SY[lo], SXX[hi] - SXX[lo], SXY[hi] - SXY[lo]
    with np.errstate(invalid="ignore", divide="ignore"):
        b = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    return np.where(n >= min_n, b, np.nan)


def fire(stat, thr):
    """+1 or -1 (the sign of stat) where |stat| reaches its threshold, else 0."""
    with np.errstate(invalid="ignore"):
        hit = np.isfinite(stat) & np.isfinite(thr) & (np.abs(stat) >= thr) & (stat != 0)
    return np.where(hit, np.sign(stat), 0).astype(np.int8)


def variant_names():
    names = []
    for fam in ("ret", "flow"):
        for side in ("fade", "follow"):
            names += [f"{fam}_{side}_k{k}_h{h}" for k in KS for h in HOLDS]
    for fam in ("absorb", "exhaust"):
        names += [f"{fam}_{side}_h{h}" for side in ("book", "anti") for h in HOLDS]
    names += [f"lead_k{k}_h{h}" for k in KS for h in HOLDS]
    return names


TRIALS = len(variant_names())                      # 57


def coin_signals(bars, btc=None):
    """Signal arrays of one coin keyed by the variant's name without its hold (the hold does not change the signal).
    `btc` holds BTC's k-minute returns and their hourly thresholds, for the lead rule on ETH and SOL."""
    n = len(bars["close"])
    d = orderflow.delta(bars["volume"], bars["tbv"])
    sig = {}
    for k in KS:
        r = kret(bars["close"], k)
        f = fire(r, per_bar(hourly_quantile(r), n))
        sig[f"ret_follow_k{k}"], sig[f"ret_fade_k{k}"] = f, -f
        s = kflow(d, k)
        f = fire(s, per_bar(hourly_quantile(s), n))
        sig[f"flow_follow_k{k}"], sig[f"flow_fade_k{k}"] = f, -f
    with np.errstate(invalid="ignore", divide="ignore"):
        bar_ret = np.log(bars["close"] / bars["open"])
    a = orderflow.absorption(d, bar_ret, ABS_WINDOW, ABS_K, ABS_M)
    sig["absorb_book"], sig["absorb_anti"] = (-a).astype(np.int8), a.astype(np.int8)
    e = orderflow.exhaustion(bars["high"], bars["low"], d, EXH_WINDOW)
    sig["exhaust_book"], sig["exhaust_anti"] = e.astype(np.int8), (-e).astype(np.int8)
    if btc is not None:
        beta = per_bar(hourly_beta(kret(btc["close"], 1), kret(bars["close"], 1)), n)
        for k in KS:
            rb, ra = btc["r"][k], kret(bars["close"], k)
            fb = fire(rb, per_bar(btc["thr"][k], n))
            with np.errstate(invalid="ignore"):
                lag = np.isfinite(ra) & np.isfinite(beta) & (np.sign(ra - beta * rb) == -np.sign(rb))
            sig[f"lead_k{k}"] = np.where(lag, fb, 0).astype(np.int8)
    return sig


# ----------------------------------------------------------------------------------------------------------- trades
def take(sig, entry_px, exit_px, h, delay):
    """The signal bars that trade, one position at a time. A signal at bar i enters at bar e = i + 1 and exits at the
    close of bar x = i + delay + h. It is skipped when either price is missing, and then blocks nothing. Once a trade
    is taken, the next one needs a signal at bar x or later (decided at or after the exit)."""
    n = len(sig)
    out, nxt = [], 0
    for i in np.flatnonzero(sig):
        if i < nxt:
            continue
        e, x = i + 1, i + delay + h
        if x >= n or not (np.isfinite(entry_px[e]) and np.isfinite(exit_px[x])):
            continue
        out.append(i)
        nxt = x
    return np.asarray(out, dtype=np.int64)


def funding_paid(F, rate, side, entry, exit_):
    """side x the rates settled at F with entry < F <= exit, per trade (a long pays a positive rate)."""
    lo = np.searchsorted(F, entry, side="right")
    hi = np.searchsorted(F, exit_, side="right")
    c = np.concatenate([[0.0], np.cumsum(rate)])
    return side * (c[hi] - c[lo])


def trades(bars, tick, F, rate, sig, h, delay=0, t0=T0):
    """One row per trade. delay 0 enters at the open of the bar after the signal; delay 1 at that bar's close (one
    minute late, reported only). Entry and exit prices are moved half a tick against the trade."""
    entry_px = bars["open"] if delay == 0 else bars["close"]
    i = take(sig, entry_px, bars["close"], h, delay)
    e, x = i + 1, i + delay + h
    s = sig[i].astype(float)
    tick = np.nan_to_num(tick)                     # a month with fewer than two distinct prices has no tick
    pe = entry_px[e] + s * tick[e] / 2
    px = bars["close"][x] - s * tick[x] / 2
    te = t0 + (e + delay) * MIN
    tx = t0 + (x + 1) * MIN
    gross = s * (px / pe - 1)
    fund = funding_paid(F, rate, s, te, tx) if len(i) else np.zeros(0)
    return pd.DataFrame({"i": i, "side": s.astype(np.int8), "te": te, "tx": tx, "pe": pe, "px": px,
                         "gross": gross, "fund": fund, "day": (te - t0) // DAY})


def net(t, cost_bp, mult=1.0):
    """Net return of each trade at `mult` times the coin's cost a side (bp)."""
    return t.gross.values - t.fund.values - 2 * mult * cost_bp / 1e4


def book(per_coin, n_days, mult=1.0, cost=None):
    """Daily net of the book: each coin holds a third of capital and trades it in sequence. per_coin maps a coin to
    its trade table; `cost` overrides the coin's Lighter walk (bp a side) for the web and API columns."""
    x = np.zeros(n_days)
    for coin, t in per_coin.items():
        if len(t):
            np.add.at(x, t.day.values, net(t, WALK_BP[coin] if cost is None else cost, mult) / 3)
    return x


# ------------------------------------------------------------------------------------------------------------ tests
def window(n_days, a, b, t0=T0):
    d = np.arange(n_days)
    return (d >= (ms(a) - t0) // DAY) & (d <= (ms(b) - t0) // DAY)


def stationary_idx(rng, n, block, B):
    idx = np.empty((B, n), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, B)
    jump = rng.random((B, n)) < 1.0 / block
    fresh = rng.integers(0, n, (B, n))
    for t in range(1, n):
        idx[:, t] = np.where(jump[:, t], fresh[:, t], (idx[:, t - 1] + 1) % n)
    return idx


def reality_check(X, rng, B=RC_B, block=RC_BLOCK):
    """White's reality check, studentized, as in R263, R287 and R289: X is (variants, days)."""
    n = X.shape[1]
    sd = X.std(axis=1)
    sd = np.where(sd > 0, sd, np.inf)
    stat = np.sqrt(n) * X.mean(axis=1) / sd
    Xd = X - X.mean(axis=1, keepdims=True)
    mx = np.array([np.max(np.sqrt(n) * Xd[:, b].mean(axis=1) / sd) for b in stationary_idx(rng, n, block, B)])
    return stat, float((mx >= stat.max()).mean()), float(np.percentile(mx, 95))


def decide(names, books1, books2, n_days, seed=SEED):
    """Reality check over the discovery series at 1x, the selected rule j* and its validation tests."""
    disc, val = window(n_days, *DISC), window(n_days, *VALID)
    X = np.array([books1[v][disc] for v in names])
    stat, rc_p, p95 = reality_check(X, np.random.default_rng(seed))
    j = int(np.argmax(stat))
    b1, b2 = books1[names[j]], books2[names[j]]
    tv = float(stats.newey_west_t(b1[val], NW_LAG)[2])
    halves = [float(b1[window(n_days, *hh)].mean()) for hh in HALVES]
    passed = bool(rc_p < RC_ALPHA and tv >= T_BAR and b2[val].mean() > 0 and min(halves) > 0)
    return {"rc_p": rc_p, "rc_null_p95": p95, "best": names[j], "best_disc_stat": float(stat[j]),
            "best_disc_net1_bp": float(X[j].mean() * 1e4), "valid_t1": tv, "valid_net1_bp": float(b1[val].mean() * 1e4),
            "valid_net2_bp": float(b2[val].mean() * 1e4), "valid_halves_net1_bp": [h * 1e4 for h in halves],
            "pass": passed, "disc_stats": {v: float(s) for v, s in zip(names, stat)}}


def describe(name, per_coin, n_days, wname, sel, late=None):
    """One reported row: trades, hit rate, gross and net per trade, daily net at 1x/2x/3x, web and API, t, Sharpe."""
    days = np.flatnonzero(sel)
    t = pd.concat([tt.assign(coin=c) for c, tt in per_coin.items()], ignore_index=True)
    t = t[np.isin(t.day.values, days)]
    b = {m: book(per_coin, n_days, m)[sel] for m in (1, 2, 3)}
    web, api = book(per_coin, n_days, cost=WEB_BP)[sel], book(per_coin, n_days, cost=API_BP)[sel]
    _, mu, tt = stats.newey_west_t(b[1], NW_LAG)
    cost = t.coin.map(WALK_BP).values / 1e4 if len(t) else np.zeros(0)
    row = {"variant": name, "window": wname, "days": int(sel.sum()), "trades": int(len(t)),
           "trades_per_day": len(t) / max(1, int(sel.sum())),
           "hit": float((t.gross > 0).mean()) if len(t) else np.nan,
           "gross_trade_bp": float(t.gross.mean() * 1e4) if len(t) else np.nan,
           "net1_trade_bp": float((t.gross - t.fund - 2 * cost).mean() * 1e4) if len(t) else np.nan,
           "net1_day_bp": mu * 1e4, "net2_day_bp": float(b[2].mean() * 1e4), "net3_day_bp": float(b[3].mean() * 1e4),
           "web_day_bp": float(web.mean() * 1e4), "api_day_bp": float(api.mean() * 1e4), "nw_t1": tt,
           "sharpe1": float(b[1].mean() / b[1].std() * np.sqrt(365)) if b[1].std() > 0 else np.nan,
           "breakeven_bp_side": float((t.gross - t.fund).mean() / 2 * 1e4) if len(t) else np.nan}
    if late is not None:
        tl = pd.concat([tt.assign(coin=c) for c, tt in late.items()], ignore_index=True)
        tl = tl[np.isin(tl.day.values, days)]
        row["late_gross_trade_bp"] = float(tl.gross.mean() * 1e4) if len(tl) else np.nan
        row["late_net1_day_bp"] = float(book(late, n_days, 1)[sel].mean() * 1e4)
    return row


def detail(name, per_coin, n_days):
    """For j*: net at 1x per calendar year and coin, the 10 best days' share, the mean without them, and a 5% trimmed
    mean of the days with a trade, in the validation window."""
    val = window(n_days, *VALID)
    b = book(per_coin, n_days, 1)
    days = pd.to_datetime(T0 + np.arange(n_days, dtype=np.int64) * DAY, unit="ms")
    out = {"net1_day_bp_by_year": {int(y): float(b[days.year == y].mean() * 1e4) for y in np.unique(days.year)}}
    out["valid_net1_day_bp_by_coin"] = {c: float(book({c: t}, n_days, 1)[val].mean() * 1e4) for c, t in per_coin.items()}
    v = b[val]
    top = np.sort(v)[::-1][:10]
    out["valid_best10_share"] = float(top.sum() / v.sum()) if v.sum() != 0 else np.nan
    out["valid_without_best10_bp"] = float((v.sum() - top.sum()) / (len(v) - 10) * 1e4)
    traded = v[v != 0]
    if len(traded) >= 20:
        lo, hi = np.quantile(traded, [0.05, 0.95])
        out["valid_trimmed5_traded_day_bp"] = float(traded[(traded >= lo) & (traded <= hi)].mean() * 1e4)
    return out


# ------------------------------------------------------------------------------------------------------------- main
def simulate_all(bars, ticks, funding, holds=HOLDS):
    """Trade tables for every variant, coin and delay: {delay: {variant: {coin: table}}}."""
    out = {0: {}, 1: {}}
    btc = None
    for coin in COINS:
        b = bars[coin]
        if coin == "BTCUSDT":
            r = {k: kret(b["close"], k) for k in KS}
            btc = {"close": b["close"], "r": r, "thr": {k: hourly_quantile(r[k]) for k in KS}}
        sig = coin_signals(b, btc if coin in ALTS else None)
        F, rate = funding[coin]
        for base, s in sig.items():
            for h in holds:
                name = f"{base}_h{h}"
                for delay in (0, 1):
                    out[delay].setdefault(name, {})[coin] = trades(b, ticks[coin], F, rate, s, h, delay)
        log(f"{coin}: {len(sig)} signals x {len(holds)} holds simulated")
    return out


def main():
    sha = prereg.verify(LANE / "PREREG.md")
    shas = frozen_inputs(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    bars = {c: load_bars(ROOT / "data" / "klines_1m" / f"{c}.parquet") for c in COINS}
    funding = {c: load_funding(ROOT / "data" / "fundingRate" / f"{c}.parquet") for c in COINS}
    ticks = {c: month_ticks(bars[c]) for c in COINS}
    log("bars, funding and ticks loaded: " + ", ".join(
        f"{c} {int(np.isfinite(bars[c]['close']).sum())} bars" for c in COINS))
    sims = simulate_all(bars, ticks, funding)
    names = variant_names()
    assert set(names) == set(sims[0]), "variant set mismatch"
    n_days = (T1 - T0) // DAY
    books1 = {v: book(sims[0][v], n_days, 1) for v in names}
    books2 = {v: book(sims[0][v], n_days, 2) for v in names}
    dec = decide(names, books1, books2, n_days)
    disc = window(n_days, *DISC)
    spa = inference.spa(np.array([books1[v][disc] for v in names]).T, n_boot=RC_B, block=RC_BLOCK,
                        rng=np.random.default_rng(SEED + 1))
    sub = {}
    for fam in ("ret", "flow", "absorb", "exhaust", "lead"):
        fn = [v for v in names if v.startswith(fam + "_")]
        X = np.array([books1[v][disc] for v in fn])
        st, p, _ = reality_check(X, np.random.default_rng(SEED + 2))
        sub[fam] = {"rc_p": p, "best": fn[int(np.argmax(st))], "best_stat": float(st.max()), "variants": len(fn)}
    rows = []
    wins = {"discovery": window(n_days, *DISC), "validation": window(n_days, *VALID),
            "valid_h1": window(n_days, *HALVES[0]), "valid_h2": window(n_days, *HALVES[1])}
    for v in names:
        for wname, sel in wins.items():
            rows.append(describe(v, sims[0][v], n_days, wname, sel, late=sims[1][v]))
    res = LANE / "results"
    res.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(res / "variants.csv", index=False, float_format="%.6g")
    daily = pd.DataFrame({v: books1[v] for v in names})
    daily.insert(0, "day", pd.to_datetime(T0 + np.arange(n_days, dtype=np.int64) * DAY, unit="ms").date)
    daily.to_csv(res / "daily.csv.gz", index=False, float_format="%.6g")
    best = dec["best"]
    pd.concat([t.assign(coin=c) for c, t in sims[0][best].items()]).to_csv(res / "trades_best.csv.gz", index=False)
    summary = {"lane": LANE.name, "registry": REGISTRY, "trials": TRIALS, "verdict": "PASS" if dec["pass"] else "NULL",
               "decision": dec, "spa_disc": spa, "subfamilies": sub, "best_detail": detail(best, sims[0][best], n_days),
               "walk_bp": WALK_BP, "inputs": shas}
    (res / "summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n")
    log(f"verdict {summary['verdict']}; rc_p {dec['rc_p']:.3f}; best {best} disc stat {dec['best_disc_stat']:.2f}; "
        f"validation net1 {dec['valid_net1_bp']:.2f} bp/day, t {dec['valid_t1']:.2f}")


if __name__ == "__main__":
    main()
