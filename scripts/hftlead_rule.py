"""R367 hftlead_v1 rule: does a cross-venue lead make a passive quote on Binance's USDC perp worth posting?

Pure functions over 100 ms grids built from the daily files of scripts/record_hft.py; the runner
(scripts/run_hftlead.py) loads the files and calls these. Everything is in the local-receive clock of the recorder:
a row of bucket k is known at the end of bucket k, a decision made then reaches the exchange L buckets later, and a
trade is placed in the bucket in which this container received it.

The question: when the Binance USDT (or Bybit) mid has moved away from the USDC mid by more than it usually does, is a
passive quote on the side the lead favours, left for one second, worth more than nothing after the fills this data
can be sure of? A quote is a bid when the USDC mid sits below the lead (the lead says up), an ask when above.
- **Signal:** x = 1e4 * (ln mid_lead - ln mid_usdc) minus its median over the last 60 s. The median removes the quote
  asset basis and venue offset that persist; what is left is the part that moved.
- **Candidates:** buckets with |x| at or above the q-th percentile (95 or 99) of |x| over the six hours before the
  bucket's UTC hour (no quotes in an hour with fewer than MIN_HIST valid points before it).
- **Quote:** at the best bid (ask) known at the decision, live from the start of bucket k + 1 + L for QLIFE buckets.
- **Strict fill:** a sell (buy) aggressor traded strictly below (above) the quote in a live bucket: the price moved
  through it, so a queue of any length was cleared. **Touch fill:** at the quote or through it: every fill the data
  allows, with an unknown queue. The true fills lie between the two sets.
- **Markout:** the USDC mid MARK buckets after the fill bucket, against the quote price, in bp (positive is a gain).
  No fee (the maker promotion), no exit.
- **One quote at a time:** after a decision no new one until the fill's markout bucket, or the quote's expiry.
The control is the same machinery on every bucket, bid and ask, whatever the signal says.
"""
import math

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
from scipy import stats

BUCKET_MS = 100
DAY_BUCKETS = 864_000
HOUR_BUCKETS = 36_000
MAX_AGE = 10                    # a quote older than 1 s (10 buckets) is no quote
MED_WIN, MED_MIN = 600, 300     # the signal's trailing median: 60 s, at least 30 s of points
HIST_HOURS = 6                  # the threshold's history
MIN_HIST = 18_000               # valid points (30 min) in that history for an hour to be quoted
QLIFE = 10                      # quote life, buckets
MARK = 10                       # markout horizon after the fill bucket, buckets
LAGS = (2, 5)                   # buckets from the end of the decision bucket to the order being live: 200, 500 ms
PCTS = (95, 99)
COINS = ("BTC", "ETH")
LEADS = ("binance_usdt", "bybit")
UNIT_COST_BP = 0.1              # one cost unit a fill, for 1x, 2x, 3x
COST_MULTS = (1, 2, 3)
MIN_FILLS = 300                 # strict fills for a rule to be scored
MIN_DAY_COVERAGE = 0.80         # share of a day's buckets with a USDC, Binance USDT and Bybit mid, for a coin
MIN_DAYS = 3
ALPHA = 0.05                    # one-sided, Holm over the rules
RULES = [(c, v, L, q) for c in COINS for v in LEADS for L in LAGS for q in PCTS]
TRIALS = len(RULES)


# ------------------------------------------------------------------------------------------------------------ series
DAY_MS = 86_400_000


def to_index(t, first_day_ms):
    """Grid index of rows with bucket starts t (ms): whole UTC days from first_day_ms laid end to end, DAY_BUCKETS
    buckets each. Rows past a day's DAY_BUCKETS (only in a shrunken test grid) get -1."""
    rel = np.asarray(t, dtype="int64") - first_day_ms
    off = (rel % DAY_MS) // BUCKET_MS
    idx = (rel // DAY_MS) * DAY_BUCKETS + off
    return np.where((rel >= 0) & (off < DAY_BUCKETS), idx, -1)


def ffill_mid(idx, bid, ask, n):
    """Mid, bid and ask on a grid of n buckets: the last row at or before each bucket, NaN when it is older than
    MAX_AGE buckets. idx, bid and ask are the rows of one (venue, symbol)."""
    keep = (idx >= 0) & (idx < n)
    out = []
    for v in (bid, ask):
        a = np.full(n, np.nan)
        a[idx[keep]] = np.asarray(v, dtype="float64")[keep]
        out.append(pd.Series(a).ffill(limit=MAX_AGE).to_numpy())
    return (out[0] + out[1]) / 2, out[0], out[1]


def trade_extremes(idx, ls, hb, n):
    """Per bucket the lowest sell-aggressor and the highest buy-aggressor price (NaN where none traded)."""
    keep = (idx >= 0) & (idx < n)
    out = []
    for v in (ls, hb):
        a = np.full(n, np.nan)
        a[idx[keep]] = np.asarray(v, dtype="float64")[keep]
        out.append(a)
    return out[0], out[1]


def signal(mid_lead, mid_usdc):
    """x in bp: the lead's log distance above the USDC mid, less its median over the trailing MED_WIN buckets."""
    d = 1e4 * (np.log(mid_lead) - np.log(mid_usdc))
    med = pd.Series(d).rolling(MED_WIN, min_periods=MED_MIN).median().to_numpy()
    return d - med


def thresholds(x, pct, hist_hours=HIST_HOURS):
    """Per bucket, the pct-th percentile of |x| over the hist_hours UTC hours before the bucket's hour (the grid starts
    at an hour boundary); NaN for an hour with fewer than MIN_HIST valid points before it."""
    n = len(x)
    ax = np.abs(x)
    out = np.full(n, np.nan)
    for h in range(0, (n + HOUR_BUCKETS - 1) // HOUR_BUCKETS):
        a = ax[max(0, (h - hist_hours) * HOUR_BUCKETS):h * HOUR_BUCKETS]
        a = a[np.isfinite(a)]
        if len(a) >= MIN_HIST:
            out[h * HOUR_BUCKETS:(h + 1) * HOUR_BUCKETS] = np.percentile(a, pct)
    return out


# ------------------------------------------------------------------------------------------------------------ fills
def outcomes(bid, ask, mid, ls, hb, lag):
    """For a quote decided in every bucket k, the strict and touch outcomes of a bid at bid[k] and an ask at ask[k].

    Returns a dict of arrays over k: "<side>_<kind>_j" the fill bucket (-1 when none) and "<side>_<kind>_m" the
    markout in bp (NaN when none or when the mid at the markout bucket is stale). Side is bid or ask, kind strict or
    touch. The quote is live in buckets k + 1 + lag ... k + lag + QLIFE; only the first fill is taken."""
    n = len(bid)
    pad = 1 + lag + QLIFE + MARK + 1
    ls_p = np.concatenate([ls, np.full(pad, np.nan)])
    hb_p = np.concatenate([hb, np.full(pad, np.nan)])
    mid_p = np.concatenate([mid, np.full(pad, np.nan)])
    ls_w = sliding_window_view(ls_p, QLIFE)[1 + lag:1 + lag + n]
    hb_w = sliding_window_view(hb_p, QLIFE)[1 + lag:1 + lag + n]
    out = {}
    with np.errstate(invalid="ignore"):
        conds = {("bid", "strict"): ls_w < bid[:, None], ("bid", "touch"): ls_w <= bid[:, None],
                 ("ask", "strict"): hb_w > ask[:, None], ("ask", "touch"): hb_w >= ask[:, None]}
    k = np.arange(n)
    for (side, kind), c in conds.items():
        has = c.any(axis=1)
        j = np.where(has, k + 1 + lag + c.argmax(axis=1), -1)
        mm = mid_p[np.where(has, j, 0) + MARK]
        price = bid if side == "bid" else ask
        sign = 1.0 if side == "bid" else -1.0
        with np.errstate(invalid="ignore", divide="ignore"):
            m = np.where(has, sign * 1e4 * (mm - price) / price, np.nan)
        out[f"{side}_{kind}_j"] = j
        out[f"{side}_{kind}_m"] = m
    return out


def serialize(cand, j, lag):
    """The decisions kept, one quote at a time: walk the candidate buckets in order; after a decision at k the next
    must come after the fill's markout bucket (j + MARK) or, with no fill, after the quote's expiry (k + lag + QLIFE).
    Returns the indices of the kept candidates in `cand`."""
    keep, free = [], -1
    for i, k in enumerate(cand.tolist()):
        if k <= free:
            continue
        keep.append(i)
        jk = int(j[k])
        free = jk + MARK if jk >= 0 else k + lag + QLIFE
    return np.asarray(keep, dtype="int64")


def rule_fills(cand, x, out, lag, kind):
    """One rule's quotes: a bid where x > 0 and an ask where x < 0 for each candidate bucket in `cand`, one at a time.
    Returns (decision buckets kept, decision buckets of the quotes that filled and have a markout, their fill buckets,
    their markouts)."""
    up = x > 0
    j = np.where(up, out[f"bid_{kind}_j"], out[f"ask_{kind}_j"])
    m = np.where(up, out[f"bid_{kind}_m"], out[f"ask_{kind}_m"])
    ks = cand[serialize(cand, j, lag)]
    ok = np.isfinite(m[ks])
    return ks, ks[ok], j[ks][ok], m[ks][ok]


def control_fills(valid, side, out, lag, kind):
    """The unconditional quote: every bucket in `valid` is a candidate, always on one side."""
    j, m = out[f"{side}_{kind}_j"], out[f"{side}_{kind}_m"]
    ks = valid[serialize(valid, j, lag)]
    ok = np.isfinite(m[ks])
    return ks, ks[ok], j[ks][ok], m[ks][ok]


# ------------------------------------------------------------------------------------------------------------ stats
def block_stat(blocks, vals):
    """Mean of vals and its t over whole blocks (UTC hours): the ratio estimator sum(v) / sum(n) with the blocks'
    residuals as the sampling unit. Returns (mean, se, t, n, blocks used)."""
    blocks, vals = np.asarray(blocks), np.asarray(vals, dtype="float64")
    n = len(vals)
    if n == 0:
        return math.nan, math.nan, math.nan, 0, 0
    ub, inv = np.unique(blocks, return_inverse=True)
    cnt = np.bincount(inv).astype("float64")
    tot = np.bincount(inv, weights=vals)
    mean = tot.sum() / cnt.sum()
    h = len(ub)
    if h < 2:
        return float(mean), math.nan, math.nan, n, h
    resid = tot - mean * cnt
    se = math.sqrt(h / (h - 1) * float((resid ** 2).sum())) / cnt.sum()
    return float(mean), se, float(mean / se) if se > 0 else math.nan, n, h


def p_one_sided(t, h):
    return float(stats.t.sf(t, max(h - 1, 1))) if math.isfinite(t) else 1.0


def holm(p, alpha=ALPHA):
    """Holm-Bonferroni step-down adjusted p-values (monotone, capped at 1); nan counts as 1."""
    p = np.where(np.isfinite(p), p, 1.0)
    order = np.argsort(p)
    adj = np.empty(len(p))
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (len(p) - rank) * p[i]))
        adj[i] = run
    return adj


def verdict(rows, usable_days):
    """(state, text) from the scored rules. Each row: strict mean, touch mean, n strict fills, holm-adjusted p.
    PASS when a rule with at least MIN_FILLS strict fills has a positive strict mean after 2 cost units, a positive
    touch mean and a Holm-adjusted p at most ALPHA; INCONCLUSIVE when fewer than MIN_DAYS usable days or fewer than
    three quarters of the rules reach MIN_FILLS; else NULL."""
    if usable_days < MIN_DAYS:
        return "INCONCLUSIVE", f"{usable_days} usable days, {MIN_DAYS} needed"
    scored = [r for r in rows if r["n_strict"] >= MIN_FILLS]
    if len(scored) < 0.75 * len(rows):
        return "INCONCLUSIVE", f"{len(scored)} of {len(rows)} rules reach {MIN_FILLS} strict fills"
    passes = [r for r in scored if r["mean_strict"] - 2 * UNIT_COST_BP > 0 and r["mean_touch"] > 0
              and r["p_holm"] <= ALPHA]
    if passes:
        best = max(passes, key=lambda r: r["mean_strict"])
        return "PASS", (f"{len(passes)} of {len(rows)} rules pass; best {best['rule']}: strict "
                        f"{best['mean_strict']:+.3f} bp a fill over {best['n_strict']} fills "
                        f"(Holm p {best['p_holm']:.3g})")
    best = max(scored, key=lambda r: r["mean_strict"])
    return "NULL", (f"no rule passes; highest strict mean {best['mean_strict']:+.3f} bp ({best['rule']}, "
                    f"{best['n_strict']} fills)")
