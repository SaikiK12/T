"""Cross-venue funding carry books (R275's rule) one day at a time, for forward paper.

A line-for-line Python twin of `engine/src/spread.rs` (qx spread): the same daily axis, closes, freshness, funding
windows, identity guard, widest-pair choice, entries, exits and daily net. The engine replays a whole history at once.
Here `Book.exits`, `Book.entries` and `Book.interval` advance one day from a state the caller keeps (a forward lane's
journal), so a paper book's holdings come from its own tickets.

Parity: `replay` runs a book over a whole history with this code. tests/test_forward_xfund.py checks its trades against
qx on a synthetic root; scripts/xfund_parity.py checks trades and daily net against R275's frozen output on the archive.

Day d is the instant t0 + d days, 00:00 UTC. A venue's close on day d is its last traded close at or before that
instant; it is fresh when the bar ending at that instant traded. Funding settled in (day d - 1, day d] belongs to day d.
"""
import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

DAY = 86_400_000
H = 3_600_000


def daily_prices(t, close, vol, bar_ms, t0, nd):
    """(close carried forward, fresh) per day from bars whose `t` is the bar open. On a tie in bar open time the first
    row in file order marks the day, as in the engine."""
    t, close, vol = (np.asarray(x, np.float64) for x in (t, close, vol))
    ok = np.isfinite(t) & np.isfinite(close) & (close > 0) & np.isfinite(vol) & (vol > 0)
    ti = np.where(np.isfinite(t), t, 0).astype(np.int64)
    ok &= ti >= t0
    end = ti + bar_ms
    d = (end - t0 + DAY - 1) // DAY
    ok &= (d >= 0) & (d < nd)
    rows = np.flatnonzero(ok)
    day_close = np.full(nd, np.nan)
    fresh = np.zeros(nd, bool)
    if len(rows):
        frame = pd.DataFrame({"d": d[rows], "ti": ti[rows], "c": close[rows], "i": rows})
        # the last bar open per day; the first such row in file order
        top = frame.sort_values(["d", "ti", "i"], ascending=[True, False, True]).drop_duplicates("d")
        day_close[top.d.to_numpy()] = top.c.to_numpy()
        on = rows[end[rows] == t0 + d[rows] * DAY]
        fresh[d[on]] = True
    return pd.Series(day_close).ffill().to_numpy(), fresh


def daily_funding(t, rate, t0, nd):
    """(sum, count) of settlements per day; a settlement at s (floored to the hour) belongs to day ceil((s - t0) / DAY).
    Sums run in file order, as in the engine."""
    t, rate = np.asarray(t, np.float64), np.asarray(rate, np.float64)
    ok = np.isfinite(t) & np.isfinite(rate)
    ti = np.where(ok, t, 0).astype(np.int64)
    ok &= ti >= t0
    th = ti - ti % H
    d = (th - t0 + DAY - 1) // DAY
    ok &= (d >= 1) & (d < nd)
    f = np.bincount(d[ok], weights=rate[ok], minlength=nd).astype(np.float64)
    n = np.bincount(d[ok], minlength=nd).astype(np.int64)
    return f, n


@dataclass
class Daily:
    close: np.ndarray
    fresh: np.ndarray
    cumf: np.ndarray
    cumn: np.ndarray
    first_fund: int
    last_fresh: int

    @classmethod
    def build(cls, close, fresh, f, n):
        nd = len(close)
        f = np.asarray(f, np.float64).copy()
        f[0] = 0.0
        cumf = np.cumsum(f)                         # sequential accumulation, as the engine sums
        cumn = np.cumsum(np.asarray(n, np.int64) * (np.arange(nd) > 0))
        nz = np.flatnonzero(n[1:] > 0)
        first = int(nz[0]) + 1 if len(nz) else 2**62
        fr = np.flatnonzero(fresh)
        return cls(close, fresh, cumf, cumn, first, int(fr[-1]) if len(fr) else -1)

    def window(self, d, l):
        """Settled funding over (day d - l, day d], if the history covers the whole window, else None."""
        if d < l or self.first_fund > d + 1 - l or self.cumn[d] == self.cumn[d - l]:
            return None
        return self.cumf[d] - self.cumf[d - l]

    def fund_on(self, d):
        return self.cumf[d] - self.cumf[d - 1]

    def ret(self, d):
        a, b = self.close[d], self.close[d + 1]
        return b / a - 1.0 if math.isfinite(a) and math.isfinite(b) and a > 0 else 0.0


def load_daily(prices, funding, vol_col, bar_h, t0, nd):
    """A Daily from a price parquet (t, close, vol_col) and a funding parquet (t, rate), or None if either is missing."""
    try:
        p = pd.read_parquet(prices, columns=["t", "close", vol_col])
        g = pd.read_parquet(funding, columns=["t", "rate"])
    except (FileNotFoundError, OSError):
        return None
    f64 = lambda s: s.to_numpy(np.float64)
    close, fresh = daily_prices(f64(p.t), f64(p.close), f64(p[vol_col]), bar_h * H, t0, nd)
    f, n = daily_funding(f64(g.t), f64(g.rate), t0, nd)
    return Daily.build(close, fresh, f, n)


def pair_corr(a, b, d, days, min_obs):
    """Pearson correlation of the two venues' fresh daily log returns over (d - days, d], if at least min_obs days."""
    lo = max(d + 1 - days, 1)
    x, y = [], []
    for k in range(lo, d + 1):
        if a.fresh[k] and a.fresh[k - 1] and b.fresh[k] and b.fresh[k - 1]:
            x.append(math.log(a.close[k] / a.close[k - 1]))
            y.append(math.log(b.close[k] / b.close[k - 1]))
    if len(x) < max(min_obs, 3):
        return None
    mx, my = sum(x) / len(x), sum(y) / len(y)
    sxy = sxx = syy = 0.0
    for i in range(len(x)):                         # the engine's accumulation order
        sxy += (x[i] - mx) * (y[i] - my)
        sxx += (x[i] - mx) * (x[i] - mx)
        syy += (y[i] - my) * (y[i] - my)
    return sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else None


@dataclass
class Cand:
    lo: int
    hi: int
    spread: float


class Universe:
    """series[coin][venue] = Daily or None, venues in the order of `names`."""

    def __init__(self, keys, names, series, t0, nd, corr_days=30, corr_min=0.9, corr_obs=20):
        self.keys, self.names, self.series, self.t0, self.nd = keys, names, series, t0, nd
        self.corr_days, self.corr_min, self.corr_obs = corr_days, corr_min, corr_obs
        self._ok = {}

    def corr_ok(self, c, a, b, d):
        a, b = min(a, b), max(a, b)
        k = (c, a, b, d)
        if k not in self._ok:
            r = pair_corr(self.series[c][a], self.series[c][b], d, self.corr_days, self.corr_obs)
            self._ok[k] = r is not None and r >= self.corr_min
        return self._ok[k]

    def candidate(self, c, vset, d, l):
        """The widest eligible pair of venue indices `vset` for coin c on day d, or None."""
        sv, best = self.series[c], None
        for i, a in enumerate(vset):
            sa = sv[a]
            if sa is None or not sa.fresh[d]:
                continue
            fa = sa.window(d, l)
            if fa is None:
                continue
            for b in vset[i + 1:]:
                sb = sv[b]
                if sb is None or not sb.fresh[d]:
                    continue
                fb = sb.window(d, l)
                if fb is None:
                    continue
                lo, hi, w = (a, b, fb - fa) if fa <= fb else (b, a, fa - fb)
                s = w * 365.0 / l
                if (best is None or s > best.spread) and self.corr_ok(c, a, b, d):
                    best = Cand(lo, hi, s)
        return best


@dataclass
class Position:
    coin: int
    lo: int          # long venue (pays the lower funding)
    hi: int          # short venue
    entry_day: int
    spread_in: float


@dataclass
class Book:
    vset: list
    lookback: int
    threshold: float
    slots: int
    open: list = field(default_factory=list)

    def exits(self, u, d, forced_fn=None):
        """Exit decisions on day d: [(position, forced)]. forced_fn(pos, d) overrides the engine's delisting rule."""
        out, keep = [], []
        for p in self.open:
            a, h = u.series[p.coin][p.lo], u.series[p.coin][p.hi]
            forced = forced_fn(p, d) if forced_fn else (a.last_fresh < d or h.last_fresh < d)
            ex = forced
            if not forced and a.fresh[d] and h.fresh[d]:
                fa, fh = a.window(d, self.lookback), h.window(d, self.lookback)
                w = (fh - fa) * 365.0 / self.lookback if fa is not None and fh is not None else None
                ex = w is None or w < self.threshold / 2.0
            (out.append((p, forced)) if ex else keep.append(p))
        self.open = keep
        return out

    def entries(self, u, d):
        """Entry decisions on day d (after exits), widest first, ties by table order."""
        if len(self.open) >= self.slots:
            return []
        held = {p.coin for p in self.open}
        cs = []
        for c in range(len(u.keys)):
            if c in held:
                continue
            x = u.candidate(c, self.vset, d, self.lookback)
            if x is not None and x.spread >= self.threshold:
                cs.append((c, x))
        cs.sort(key=lambda z: (-z[1].spread, z[0]))
        new = [Position(c, x.lo, x.hi, d, x.spread) for c, x in cs[: self.slots - len(self.open)]]
        self.open.extend(new)
        return new

    def interval(self, u, d):
        """(gross, funding) of the open pairs over day d -> d + 1, per unit of one leg's notional (sum over pairs)."""
        gross = fund = 0.0
        for p in self.open:
            a, h = u.series[p.coin][p.lo], u.series[p.coin][p.hi]
            price = a.ret(d) - h.ret(d)
            f = h.fund_on(d + 1) - a.fund_on(d + 1)
            gross += price + f
            fund += f
        return gross, fund


def replay(u, book, w0):
    """Run a book over days [w0, nd - 1) as the engine's `simulate` does: per day (gross, funding, legs, held) and trades."""
    rows, trades = [], []
    idx = {}
    for d in range(w0, u.nd - 1):
        legs = 0.0
        for p, forced in book.exits(u, d):
            legs += 2.0
            trades[idx.pop(id(p))].update(exit_day=d, forced=forced)
        for p in book.entries(u, d):
            legs += 2.0
            idx[id(p)] = len(trades)
            trades.append({"coin": u.keys[p.coin], "long": u.names[p.lo], "short": u.names[p.hi], "entry_day": d,
                           "exit_day": None, "spread_in": p.spread_in, "forced": False})
        g, f = book.interval(u, d)
        rows.append({"day": d, "gross": g, "funding": f, "legs": legs, "held": len(book.open)})
    if rows:
        rows[-1]["legs"] += 2.0 * len(book.open)
    return pd.DataFrame(rows), trades


def window_start(u, vset, l):
    """The engine's w0: the first day on which any coin has an eligible pair in this set at this lookback."""
    for d in range(u.nd):
        if any(u.candidate(c, vset, d, l) is not None for c in range(len(u.keys))):
            return d
    return u.nd - 1


def net(rows, slots, cost):
    return (rows.gross - cost * rows.legs) / (2.0 * slots)
