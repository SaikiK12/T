"""Venue-neutral carry books (M468): R275's rule with the three accounting fixes of the 2026-11-04 audit.

`lab/xfund.py` (the frozen twin of `engine/src/spread.rs`) is not changed. This module reuses its funding windows,
identity guard, pair choice and entry rule, and changes only what the audit found wrong
(docs/reviews/hidden_edge_audit_20261104.md):

1. **Freshness (H1).** A venue is fresh on day d when at least one bar with volume ended in (day d - 1, day d], whatever
   the bar length. The frozen rule needed a bar ending exactly at 00:00, so an hourly venue needed a trade in the
   23:00 hour while a daily venue needed one trade in the day.
2. **Fixed-quantity marks (H2).** A pair holds q = 1 / entry price of each leg (one unit of entry notional per leg)
   until it exits. Price P&L is q x the price change; funding is paid on the leg's current notional. The frozen rule
   re-based both legs to equal notional every day.
3. **Valuation and dead legs (F4).** Legs are valued at the venue's mark price where one is held, else at the last
   trade. On an interval where a leg did not trade, the pair is credited no price gain (a loss is kept): a stale
   print is not a fill. A pair whose legs' price ratio moves more than BLOWOUT from its entry ratio exits that day
   (`blowout`), and such exits are reported apart so a result cannot rest on them.

Engineering only: no data, no decision. A test of a book on this engine is a registered lane (M469).
"""
import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from lab import xfund as v1

DAY, H = v1.DAY, v1.H
BLOWOUT = 0.20


def daily_prices(t, close, vol, bar_ms, t0, nd):
    """(close carried forward, fresh) per day. The close is v1's (last traded close at or before day d's instant);
    fresh[d] is true when any traded bar ended in (day d - 1, day d]."""
    close_d, _ = v1.daily_prices(t, close, vol, bar_ms, t0, nd)
    t, close, vol = (np.asarray(x, np.float64) for x in (t, close, vol))
    ok = np.isfinite(t) & np.isfinite(close) & (close > 0) & np.isfinite(vol) & (vol > 0)
    ti = np.where(np.isfinite(t), t, 0).astype(np.int64)
    end = ti + bar_ms
    ok &= ti >= t0
    d = (end - t0 + DAY - 1) // DAY
    ok &= (d >= 0) & (d < nd)
    fresh = np.zeros(nd, bool)
    fresh[d[ok]] = True
    return close_d, fresh


def daily_marks(t, mark, bar_ms, t0, nd):
    """The last mark close at or before each day's instant, carried forward; NaN before the first."""
    t, mark = np.asarray(t, np.float64), np.asarray(mark, np.float64)
    ok = np.isfinite(t) & np.isfinite(mark) & (mark > 0)
    ti = np.where(ok, t, 0).astype(np.int64)
    end = ti + bar_ms
    d = (end - t0 + DAY - 1) // DAY
    ok &= (ti >= t0) & (d >= 0) & (d < nd)
    out = np.full(nd, np.nan)
    if ok.any():
        frame = pd.DataFrame({"d": d[ok], "ti": ti[ok], "m": mark[ok]}).sort_values(["d", "ti"]).drop_duplicates(
            "d", keep="last")
        out[frame.d.to_numpy()] = frame.m.to_numpy()
    return pd.Series(out).ffill().to_numpy()


@dataclass
class Daily(v1.Daily):
    val: np.ndarray = None            # valuation price: mark where held, else the last trade

    @classmethod
    def build(cls, close, fresh, f, n, mark=None):
        base = v1.Daily.build(close, fresh, f, n)
        val = np.asarray(close, np.float64).copy()
        if mark is not None:
            mark = np.asarray(mark, np.float64)
            val = np.where(np.isfinite(mark), mark, val)
        return cls(base.close, base.fresh, base.cumf, base.cumn, base.first_fund, base.last_fresh, val)


def load_daily(prices, funding, vol_col, bar_h, t0, nd, marks=None, mark_bar_h=1):
    """A Daily from a price parquet (t, close, vol_col), a funding parquet (t, rate) and optionally a mark parquet
    (t, close), or None if prices or funding are missing."""
    try:
        p = pd.read_parquet(prices, columns=["t", "close", vol_col])
        g = pd.read_parquet(funding, columns=["t", "rate"])
    except (FileNotFoundError, OSError):
        return None
    f64 = lambda s: s.to_numpy(np.float64)
    close, fresh = daily_prices(f64(p.t), f64(p.close), f64(p[vol_col]), bar_h * H, t0, nd)
    f, n = v1.daily_funding(f64(g.t), f64(g.rate), t0, nd)
    mark = None
    if marks is not None:
        try:
            m = pd.read_parquet(marks, columns=["t", "close"])
            mark = daily_marks(f64(m.t), f64(m.close), mark_bar_h * H, t0, nd)
        except (FileNotFoundError, OSError):
            mark = None
    return Daily.build(close, fresh, f, n, mark)


@dataclass
class Position(v1.Position):
    pl_e: float = math.nan           # long leg's valuation price at entry
    ph_e: float = math.nan           # short leg's
    price_pnl: float = 0.0
    funding_pnl: float = 0.0
    unobserved: int = 0              # intervals on which a leg did not trade


def ratio_move(a, h, p, d):
    """|log| of the legs' price ratio on day d relative to its entry value."""
    x = (a.val[d] / p.pl_e) / (h.val[d] / p.ph_e)
    return abs(math.log(x)) if math.isfinite(x) and x > 0 else math.inf


@dataclass
class Book(v1.Book):
    blowout: float = BLOWOUT

    def exits(self, u, d, forced_fn=None):
        """Exit decisions on day d: [(position, reason)], reason in {"spread", "dead", "blowout"}."""
        out, keep = [], []
        for p in self.open:
            a, h = u.series[p.coin][p.lo], u.series[p.coin][p.hi]
            reason = None
            if (forced_fn(p, d) if forced_fn else (a.last_fresh < d or h.last_fresh < d)):
                reason = "dead"
            elif ratio_move(a, h, p, d) > math.log1p(self.blowout):
                reason = "blowout"
            elif a.fresh[d] and h.fresh[d]:
                fa, fh = a.window(d, self.lookback), h.window(d, self.lookback)
                w = (fh - fa) * 365.0 / self.lookback if fa is not None and fh is not None else None
                if w is None or w < self.threshold / 2.0:
                    reason = "spread"
            (out.append((p, reason)) if reason else keep.append(p))
        self.open = keep
        return out

    def entries(self, u, d):
        if len(self.open) >= self.slots:
            return []
        held = {p.coin for p in self.open}
        cs = []
        for c in range(len(u.keys)):
            if c in held:
                continue
            x = u.candidate(c, self.vset, d, self.lookback)
            if x is None or x.spread < self.threshold:
                continue
            a, h = u.series[c][x.lo], u.series[c][x.hi]
            if math.isfinite(a.val[d]) and math.isfinite(h.val[d]) and a.val[d] > 0 and h.val[d] > 0:
                cs.append((c, x))
        cs.sort(key=lambda z: (-z[1].spread, z[0]))
        new = []
        for c, x in cs[: self.slots - len(self.open)]:
            a, h = u.series[c][x.lo], u.series[c][x.hi]
            new.append(Position(c, x.lo, x.hi, d, x.spread, pl_e=float(a.val[d]), ph_e=float(h.val[d])))
        self.open.extend(new)
        return new

    def interval(self, u, d):
        """(gross, funding, unobserved pairs) over day d -> d + 1, per unit of one leg's entry notional."""
        gross = fund = 0.0
        unobserved = 0
        for p in self.open:
            a, h = u.series[p.coin][p.lo], u.series[p.coin][p.hi]
            ql, qh = 1.0 / p.pl_e, 1.0 / p.ph_e
            price = ql * (a.val[d + 1] - a.val[d]) - qh * (h.val[d + 1] - h.val[d])
            if not math.isfinite(price):
                price = 0.0
            if not (a.fresh[d + 1] and h.fresh[d + 1]):
                price = min(price, 0.0)
                p.unobserved += 1
                unobserved += 1
            f = qh * h.val[d] * h.fund_on(d + 1) - ql * a.val[d] * a.fund_on(d + 1)
            f = f if math.isfinite(f) else 0.0
            p.price_pnl += price
            p.funding_pnl += f
            gross += price + f
            fund += f
        return gross, fund, unobserved


def replay(u, book, w0):
    """Run a book over days [w0, nd - 1): per day (gross, funding, legs, held, unobserved) and one row per trade."""
    rows, trades, idx = [], [], {}

    def close(p, d, reason):
        trades[idx.pop(id(p))].update(exit_day=d, reason=reason, price_pnl=p.price_pnl, funding_pnl=p.funding_pnl,
                                      unobserved=p.unobserved)

    for d in range(w0, u.nd - 1):
        legs = 0.0
        for p, reason in book.exits(u, d):
            legs += 2.0
            close(p, d, reason)
        for p in book.entries(u, d):
            legs += 2.0
            idx[id(p)] = len(trades)
            trades.append({"coin": u.keys[p.coin], "long": u.names[p.lo], "short": u.names[p.hi], "entry_day": d,
                           "exit_day": None, "spread_in": p.spread_in, "reason": None})
        g, f, n_unobs = book.interval(u, d)
        rows.append({"day": d, "gross": g, "funding": f, "legs": legs, "held": len(book.open),
                     "unobserved": n_unobs})
    if rows:
        rows[-1]["legs"] += 2.0 * len(book.open)
        for p in list(book.open):
            close(p, u.nd - 1, "end")
    return pd.DataFrame(rows), trades


def window_start(u, vset, l):
    return v1.window_start(u, vset, l)


def net(rows, slots, cost):
    return v1.net(rows, slots, cost)
