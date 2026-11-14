"""R460 usdtmint_v1 rule, frozen in experiments/usdtmint_v1/PREREG.md: after Tether mints USDT on Tron or Ethereum (an
Issue event of the token contract), does BTC rise over the next 4 or 24 hours by more than it does at random times,
and by more than a Hyperliquid taker round trip plus funding?

Pure functions over 1-minute bars (labelled by bar open time, epoch ms) and funding settlements. Nothing here reads a
file; scripts/run_usdtmint.py feeds it.

One trade:
- event       block timestamp ts of an Issue event of at least MIN_MINT USDT
- entry       E = ts + 120 s rounded up to the next minute; price = open of the first bar in [E, E + 5 min)
- exit        X = E + H hours; price = open of the first bar in [X, X + 5 min)
- return      r = 1e4 ln(exit / entry), bp, long
- funding     f = 1e4 * sum of the funding rates settled in (E, X] (a long pays a positive rate)
- net at k x  r - k * UNIT_COST_BP - f
Events are taken in time order and an event whose entry falls inside the previous taken trade's hold is skipped, so
the trades of one cell never overlap.
"""
import math

import numpy as np

MINUTE_MS = 60_000
HOUR_MS = 3_600_000
DAY_MS = 86_400_000
LAG_MS = 120_000             # entry no earlier than two minutes after the block
FILL_WINDOW_MS = 5 * MINUTE_MS
MIN_MINT = 1e8               # USDT
BIG_MINT = 1e9
HORIZONS_H = (1, 4, 24)
ASSETS = ("BTCUSDT", "ETHUSDT")
SUBSETS = ("all", "big", "tron", "ethereum", "down")
DECISIONS = (("BTCUSDT", "all", 24), ("BTCUSDT", "all", 4))
UNIT_COST_BP = 10.0          # Hyperliquid tier-0 taker 4.5 bp each way + 1 bp slippage for the round trip
COST_MULTS = (1, 2, 3)
MIN_TRADES = 40
ALPHA = 0.05
DRAWS = 2000
SEED = 460
SHIFT_MIN_MS = 7 * DAY_MS    # a placebo shift is at least a week either way around the circle
Z_MDE = 2.8                  # z(0.975) + z(0.80)


def entry_time(ts_ms):
    """Entry instant (a bar open time) for a block timestamp."""
    ts = np.asarray(ts_ms, dtype="int64") + LAG_MS
    return -(-ts // MINUTE_MS) * MINUTE_MS


def price_at(t_bars, open_bars, times):
    """Open of the first bar with open time in [time, time + 5 min); NaN when there is none or it is not positive."""
    times = np.asarray(times, dtype="int64")
    ix = np.searchsorted(t_bars, times)
    ixc = np.clip(ix, 0, len(t_bars) - 1)
    ok = (ix < len(t_bars)) & (t_bars[ixc] < times + FILL_WINDOW_MS) & (t_bars[ixc] >= times)
    p = np.where(ok, open_bars[ixc], np.nan)
    return np.where(p > 0, p, np.nan)


def log_return_bp(t_bars, open_bars, starts, hold_ms):
    a = price_at(t_bars, open_bars, starts)
    b = price_at(t_bars, open_bars, np.asarray(starts, dtype="int64") + hold_ms)
    with np.errstate(invalid="ignore", divide="ignore"):
        return 1e4 * np.log(b / a)


def funding_bp(fund_t, fund_rate, starts, hold_ms):
    """Sum of the rates settled in (start, start + hold], in bp; `fund_t` sorted."""
    starts = np.asarray(starts, dtype="int64")
    cum = np.concatenate([[0.0], np.cumsum(fund_rate)])
    lo = np.searchsorted(fund_t, starts, side="right")
    hi = np.searchsorted(fund_t, starts + hold_ms, side="right")
    return 1e4 * (cum[hi] - cum[lo])


def non_overlapping(entries, hold_ms):
    """Indices of the entries taken in time order, skipping any entry before the previous taken one's exit."""
    order = np.argsort(entries, kind="stable")
    taken, free_at = [], -np.inf
    for i in order:
        if entries[i] >= free_at:
            taken.append(i)
            free_at = entries[i] + hold_ms
    return np.array(taken, dtype=int)


def circle_shift(starts, lo, hi, offset):
    """Move every start by `offset` around the circle [lo, hi), keeping it on the minute grid."""
    span = hi - lo
    s = lo + (np.asarray(starts, dtype="int64") - lo + int(offset)) % span
    return s // MINUTE_MS * MINUTE_MS


def shift_p(t_bars, open_bars, starts, hold_ms, lo, hi, rng, draws=DRAWS):
    """One-sided p of 'the mean return of these starts is above the mean at the same starts shifted at random around
    the circle [lo, hi)': (1 + #{placebo mean >= observed}) / (1 + draws). Also returns the placebo mean."""
    obs = np.nanmean(log_return_bp(t_bars, open_bars, starts, hold_ms))
    span = hi - lo
    offs = rng.integers(SHIFT_MIN_MS // MINUTE_MS, (span - SHIFT_MIN_MS) // MINUTE_MS, size=draws) * MINUTE_MS
    plac = np.empty(draws)
    for j, d in enumerate(offs):
        plac[j] = np.nanmean(log_return_bp(t_bars, open_bars, circle_shift(starts, lo, hi, d), hold_ms))
    p = (1 + int(np.sum(plac >= obs))) / (1 + draws)
    return float(p), float(np.mean(plac)), float(obs)


def holm(p):
    p = np.asarray(p, dtype=float)
    order = np.argsort(p)
    out = np.empty_like(p)
    run = 0.0
    m = len(p)
    for k, i in enumerate(order):
        run = max(run, min(1.0, (m - k) * p[i]))
        out[i] = run
    return out


def mde80(sd, n):
    return Z_MDE * sd / math.sqrt(n) if n > 1 and np.isfinite(sd) else math.nan


def verdict(decisions):
    """decisions: dicts with n, p_holm, excess_disc, excess_val, excess_hold, net_1x, net_2x. Returns (state, text)."""
    states = []
    for d in decisions:
        signs = [d[f"excess_{s}"] > 0 for s in ("disc", "val", "hold")]
        enough = d["n"] >= MIN_TRADES
        if enough and d["p_holm"] <= ALPHA and all(signs) and d["net_2x"] > 0:
            states.append("PASS")
        elif enough and d["p_holm"] <= ALPHA and sum(signs) >= 2 and d["net_1x"] > 0:
            states.append("PARTIAL")
        elif not enough:
            states.append("INCONCLUSIVE")
        else:
            states.append("NULL")
    rank = {"PASS": 3, "PARTIAL": 2, "NULL": 1, "INCONCLUSIVE": 0}
    best = max(states, key=lambda s: rank[s]) if states else "INCONCLUSIVE"
    text = "; ".join(f"{a} {s} {h}h: {st}" for (a, s, h), st in zip(DECISIONS, states))
    return best, text
