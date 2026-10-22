"""Order flow from bars that carry the taker-buy volume (Binance klines): delta, cumulative volume delta (CVD), the
delta profile, and two patterns traders name, absorption and exhaustion (docs/AUCTION_AND_FLOW.md).

A Binance kline gives the bar's volume v and the part bought by takers b (market orders lifting the ask). The rest,
v - b, was sold by takers, so delta = b - (v - b) = 2b - v, positive when aggressive buyers outweigh aggressive
sellers. That is the exchange's own trade sides, not a guess from the bar's shape (the tick rule or bulk-volume
classification equity bars need), but it is a bar total: the order of trades inside the bar is lost.

The patterns are discretionary; these are mechanical readings of them, one of several possible:
- absorption: heavy one-sided aggression that does not move price, read as a passive player (a large resting order)
  taking the other side. A bar is flagged when its |delta| is at least `k` times the trailing median |delta| and its
  |return| at most `m` times the trailing median |return|. The flag is the side that was absorbed: +1 buyers (a
  bearish read), -1 sellers (a bullish read).
- exhaustion: price makes a new extreme on weaker aggression, read as the move running out of buyers (sellers).
  A bar whose high is above every high of the previous `window` bars while the running delta sum is below its own
  maximum over those bars is flagged -1 (buyers exhausted, a bearish read); the mirror at lows is +1.
Trailing statistics use the bars before the current one only, so a flag is known at the bar's close.
"""
import numpy as np
import pandas as pd

from lab.auction import spread


def delta(volume, taker_buy_volume):
    """Taker buy volume minus taker sell volume of each bar: 2 b - v."""
    return 2 * np.asarray(taker_buy_volume, float) - np.asarray(volume, float)


def cvd(d, session=None):
    """Cumulative delta, reset at each new session id (lab.auction.session_ids); one running sum without `session`."""
    d = np.nan_to_num(np.asarray(d, float))
    if session is None:
        return np.cumsum(d)
    return pd.Series(d).groupby(np.asarray(session)).cumsum().values


def delta_profile(high, low, d, tick):
    """Delta at each price bin, each bar's delta spread evenly over the bins between its low and high (the volume
    profile's construction with a signed weight). Bins where buyers or sellers were the aggressors on net."""
    n = np.floor(np.asarray(high, float) / tick) - np.floor(np.asarray(low, float) / tick) + 1
    with np.errstate(invalid="ignore", divide="ignore"):
        return spread(low, high, np.asarray(d, float) / n, tick)


def _trailing_median(x, window):
    return pd.Series(x).shift(1).rolling(window, min_periods=window).median().values


def absorption(d, ret, window=60, k=3.0, m=0.5):
    """+1 where buyers were absorbed, -1 where sellers were, 0 otherwise (see the module note). `ret` is the bar's
    return (close / open - 1 or a log return); the first `window` bars are 0."""
    d, r = np.asarray(d, float), np.asarray(ret, float)
    big = np.abs(d) >= k * _trailing_median(np.abs(d), window)
    still = np.abs(r) <= m * _trailing_median(np.abs(r), window)
    return np.where(big & still, np.sign(d), 0.0).astype(np.int8)


def exhaustion(high, low, d, window=60):
    """-1 at a new `window`-bar high made while the running delta sum is below its maximum over the previous
    `window` bars, +1 at a new low while it is above its minimum, 0 otherwise. The running sum is not reset, so its
    change between two bars is the net aggression between them."""
    hi, lo = pd.Series(np.asarray(high, float)), pd.Series(np.asarray(low, float))
    c = pd.Series(cvd(d))
    prev = lambda x, f: getattr(x.shift(1).rolling(window, min_periods=window), f)()
    top = (hi > prev(hi, "max")) & (c < prev(c, "max"))
    bottom = (lo < prev(lo, "min")) & (c > prev(c, "min"))
    return (bottom.astype(np.int8) - top.astype(np.int8)).values


def volume_buckets(volume, buy, size):
    """Equal-volume buckets, the volume clock of Easley, López de Prado and O'Hara. Bar i counts v_i / size_i
    buckets, so the size may change over time (a point-in-time size per bar), and a bar is spread evenly over the
    buckets it straddles. Bars with no volume, or no valid size, count nothing.

    Returns (end, share): for each completed bucket, the index of the bar in which it filled (it is known at that
    bar's close) and the share of its volume bought by takers."""
    v = np.nan_to_num(np.asarray(volume, float))
    b = np.nan_to_num(np.asarray(buy, float))
    s = np.broadcast_to(np.asarray(size, float), v.shape)
    ok = (v > 0) & np.isfinite(s) & (s > 0)
    with np.errstate(invalid="ignore", divide="ignore"):
        u = np.concatenate([[0.0], np.cumsum(np.where(ok, v / s, 0.0))])
        q = np.concatenate([[0.0], np.cumsum(np.where(ok, b / s, 0.0))])
    k = np.arange(1, int(np.floor(u[-1] + 1e-9)) + 1, dtype=float)
    share = np.diff(np.concatenate([[0.0], np.interp(k, u, q)]))
    end = np.searchsorted(u, k - 1e-9, side="left") - 1
    return end, share


def vpin(share, n=50):
    """Volume-synchronized probability of informed trading: the mean of |buy - sell| / volume over the last `n`
    buckets, from `volume_buckets`' shares. NaN until `n` buckets exist."""
    imb = np.abs(2 * np.asarray(share, float) - 1)
    return pd.Series(imb).rolling(n, min_periods=n).mean().values


def bvc_buy(volume, ret, sigma):
    """Bulk volume classification: the buy part of each bar's volume guessed from its price change alone,
    v * Phi(ret / sigma). It is what VPIN was built on where trade sides are unknown."""
    from scipy.special import ndtr
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.asarray(volume, float) * ndtr(np.asarray(ret, float) / np.asarray(sigma, float))
