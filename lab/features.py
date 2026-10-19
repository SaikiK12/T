"""Feature library. Every feature is a causal [T, S] float32 array on the hourly clock of a Panel.

A family is built on its own timeframe (k hours per bar), then aligned so a value is visible only after its bar closes.
`Spec` names a feature plus how it is binned for the search; `views` turns specs into int8 bins (-1 = no value).
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import ict
from .panel import HOUR, align, ffill, resample

TFS = (1, 4, 24)  # hours per bar: 1h, 4h, daily


def _df(x):
    return pd.DataFrame(x)


def roll(x, w, how, minp=None):
    r = _df(x).rolling(w, min_periods=minp or w)
    return getattr(r, how)().values.astype(np.float32)


def ema(x, n):
    return _df(x).ewm(span=n, adjust=False, min_periods=n).mean().values.astype(np.float32)


def shift(x, n):
    out = np.full_like(x, np.nan)
    out[n:] = x[:-n]
    return out


def prev_bar(x, k):
    """Value of each k-hour bar becomes visible for all hours of the NEXT bar (previous-day style levels)."""
    out = np.full((len(x) * k,) + x.shape[1:], np.nan, np.float32)
    out[k:] = np.repeat(x, k, axis=0)[:-k]
    return out


class Bank:
    """Builds and caches features for one panel."""

    def __init__(self, panel):
        self.p = panel
        self._bars, self._raw, self._cache = {}, {}, {}
        sym = np.array(panel.symbols)
        self.btc = int(np.flatnonzero(sym == "BTCUSDT")[0]) if "BTCUSDT" in sym else None

    def bars(self, k):
        if k not in self._bars:
            self._bars[k] = self.p.f if k == 1 else resample(self.p, k)
        return self._bars[k]

    def raw(self, key, fn):
        if key not in self._raw:
            self._raw[key] = fn()
        return self._raw[key]

    def atr(self, k, n=14):
        def build():
            b = self.bars(k)
            pc = shift(b["close"], 1)
            tr = np.fmax(np.fmax(b["high"] - b["low"], np.abs(b["high"] - pc)), np.abs(b["low"] - pc))
            return _df(tr).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean().values.astype(np.float32)
        return self.raw(("atr", k, n), build)

    def trim(self, spec=None):
        """Free memory: drop cached float features, and ICT detector outputs that the next spec will not reuse."""
        self._cache.clear()
        for key in [k for k in self._raw if k[0] in ("fvg", "ob", "sweep", "struct")]:
            if spec is None or not (key[0] == spec.family and key[1] == spec.k and spec.args and key[2] == spec.args[0]):
                del self._raw[key]

    def get(self, family, k, args=()):
        key = (family, k, tuple(args))
        if key not in self._cache:
            x = FAMILIES[family](self, k, *args)
            self._cache[key] = x if (k == 1 or family in HOURLY) else align(x, k)
        return self._cache[key]


# ---- families: f(bank, k, *args) -> [T/k, S] on the k-hour clock (hourly families return [T, S]) ----------------------

def f_ret(B, k, n):
    c = B.bars(k)["close"]
    return np.log(c / shift(c, n))


def f_ema_ratio(B, k, n):
    c = B.bars(k)["close"]
    return c / ema(c, n) - 1


def f_ema_cross(B, k, a, b):
    c = B.bars(k)["close"]
    return ema(c, a) / ema(c, b) - 1


def f_ribbon(B, k, base):
    c = B.bars(k)["close"]
    e = [ema(c, base * m) for m in (1, 2, 3, 4, 5)]
    return sum(np.sign(e[i] - e[i + 1]) for i in range(4)).astype(np.float32)


def f_rsi(B, k, n):
    c = B.bars(k)["close"]
    d = c - shift(c, 1)
    up = _df(np.maximum(d, 0)).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean().values
    dn = _df(np.maximum(-d, 0)).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean().values
    return (100 - 100 / (1 + up / np.where(dn == 0, np.nan, dn))).astype(np.float32)


def f_bbz(B, k, n):
    c = B.bars(k)["close"]
    return (c - roll(c, n, "mean")) / roll(c, n, "std")


def f_donch(B, k, n):
    b = B.bars(k)
    lo, hi = roll(b["low"], n, "min"), roll(b["high"], n, "max")
    return (b["close"] - lo) / (hi - lo)


def f_atrp(B, k, n):
    return B.atr(k, n) / B.bars(k)["close"]


def f_volz(B, k, n):
    qv = B.bars(k)["quote_volume"]
    return np.log1p(qv) - np.log1p(roll(qv, n, "mean"))


def f_tbi(B, k, n):
    b = B.bars(k)
    return roll(2 * b["taker_buy_volume"] - b["volume"], n, "sum") / roll(b["volume"], n, "sum")


def f_clv(B, k):
    b = B.bars(k)
    return ((b["close"] - b["low"]) - (b["high"] - b["close"])) / (b["high"] - b["low"])


def f_rng(B, k, n):
    b = B.bars(k)
    return roll((b["high"] - b["low"]) / b["close"], n, "mean")


def f_prem(B, k, n):
    x = B.bars(k)["premium"]
    return x if n == 0 else (x - roll(x, n, "mean")) / roll(x, n, "std")


def f_fund(B, k, n):
    x = B.bars(k)["funding"]
    return x if n == 0 else (x - roll(x, n, "mean")) / roll(x, n, "std")


def f_fvg(B, k, gap, side, what):
    def build():
        b = B.bars(k)
        return ict.fvg(b["high"], b["low"], b["close"], B.atr(k), gap)
    bd, ba, sd, sa = B.raw(("fvg", k, gap), build)
    return {("bull", "dist"): bd, ("bull", "age"): ba, ("bear", "dist"): sd, ("bear", "age"): sa}[(side, what)]


def f_ob(B, k, impulse, side):
    def build():
        b = B.bars(k)
        return ict.order_block(b["open"], b["high"], b["low"], b["close"], B.atr(k), impulse, 5)
    return B.raw(("ob", k, impulse), build)[0 if side == "bull" else 1]


def f_sweep(B, k, n, side):
    def build():
        b = B.bars(k)
        return ict.sweep(b["high"], b["low"], b["close"], n)
    return B.raw(("sweep", k, n), build)[0 if side == "bull" else 1]


def f_struct(B, k, fractal, what):
    def build():
        b = B.bars(k)
        return ict.structure(b["high"], b["low"], b["close"], fractal)
    return B.raw(("struct", k, fractal), build)[("state", "since", "pd", "ote").index(what)]


def _hour_of_day(B):
    return ((B.p.t // HOUR) % 24).astype(np.float32)


def _bcast(B, v):
    return np.repeat(v[:, None], B.p.S, axis=1).astype(np.float32)


def f_hour(B, k):
    return _bcast(B, _hour_of_day(B))


def f_dow(B, k):
    return _bcast(B, (((B.p.t // HOUR) // 24 + 3) % 7).astype(np.float32))  # Monday = 0


def f_session(B, k):
    h = _hour_of_day(B)  # 0 Asia 00-07, 1 London 07-12, 2 New York 12-21, 3 late 21-24 (UTC)
    return _bcast(B, np.select([h < 7, h < 12, h < 21], [0, 1, 2], 3).astype(np.float32))


def f_funding_clock(B, k):
    return _bcast(B, (_hour_of_day(B) % 8).astype(np.float32))  # hours since the last 8h funding time


def f_dayopen(B, k):
    p = B.p
    d = p["open"].reshape(p.T // 24, 24, -1)
    i = np.argmax(~np.isnan(d), axis=1)
    first = np.take_along_axis(d, i[:, None, :], axis=1)
    return (p["close"] / np.repeat(first[:, 0], 24, axis=0)) - 1


def f_prevday(B, k, what):
    b = B.bars(24)
    level = {"high": b["high"], "low": b["low"], "close": b["close"]}[what]
    return (B.p["close"] - prev_bar(level, 24)) / np.maximum(prev_bar(B.atr(24), 24), 1e-12)  # prior day's ATR


def f_prevday_raid(B, k, side):
    p, b = B.p, B.bars(24)
    pdh, pdl = prev_bar(b["high"], 24), prev_bar(b["low"], 24)
    if side == "high":  # high takes out the previous day's high, close back below it
        out, level = ((p["high"] > pdh) & (p["close"] < pdh)).astype(np.float32), pdh
    else:
        out, level = ((p["low"] < pdl) & (p["close"] > pdl)).astype(np.float32), pdl
    out[np.isnan(level) | np.isnan(p["close"])] = np.nan
    return out


def f_asia(B, k):
    p = B.p
    hh = p["high"].reshape(p.T // 24, 24, -1)[:, :8]
    ll = p["low"].reshape(p.T // 24, 24, -1)[:, :8]
    hi, lo = np.fmax.reduce(hh, axis=1), np.fmin.reduce(ll, axis=1)
    rows = np.tile(np.arange(24) >= 8, p.T // 24)[:, None]  # the range is final from hour 8 on
    hi, lo = np.repeat(hi, 24, axis=0), np.repeat(lo, 24, axis=0)
    out = (p["close"] - lo) / (hi - lo)
    return np.where(rows, out, np.nan).astype(np.float32)


def _market(B, x):
    return np.repeat(x[:, None], B.p.S, axis=1).astype(np.float32)


def f_btc_ret(B, k, n):
    c = B.bars(k)["close"]
    ref = c[:, B.btc] if B.btc is not None else np.nanmedian(c, axis=1)
    return _market(B, np.log(ref / shift(ref, n)))


def f_breadth(B, k, n):
    c = B.bars(k)["close"]
    live = ~np.isnan(c) & ~np.isnan(ema(c, n))
    return _market(B, np.where(live.sum(1) > 0, ((c > ema(c, n)) & live).sum(1) / np.maximum(live.sum(1), 1), np.nan))


def f_disp(B, k, n):
    c = B.bars(k)["close"]
    r = np.log(c / shift(c, 1))
    s = _df(r).std(axis=1).values  # NaN-aware, NaN when fewer than two symbols trade
    return _market(B, roll(s[:, None], n, "mean")[:, 0])


FAMILIES = {n[2:]: f for n, f in globals().items() if n.startswith("f_")}
HOURLY = {"hour", "dow", "session", "funding_clock", "dayopen", "prevday", "prevday_raid", "asia"}  # already hourly


# ---- binning -------------------------------------------------------------------------------------------------------

def bins_fixed(x, edges):
    out = np.digitize(x, edges).astype(np.int8)
    out[~np.isfinite(x)] = -1
    return out


def bins_xs(x, elig, nb=8):
    """Cross-sectional rank bucket among eligible symbols at each time. Uses row i only, so it is causal."""
    v = np.where(elig & np.isfinite(x), x, np.nan)
    r = _df(v).rank(axis=1, pct=True).values
    out = np.clip(np.ceil(r * nb) - 1, 0, nb - 1)  # pct rank k/n falls in bucket ceil(k*nb/n) - 1
    return np.where(np.isnan(r), -1, out).astype(np.int8)


Z_EDGES = (-1.5, -0.75, -0.25, 0.25, 0.75, 1.5)


def bins_z(x, w):
    """Trailing z-score of a feature against its own last w bars, in fixed buckets."""
    z = (x - roll(x, w, "mean", w // 2)) / roll(x, w, "std", w // 2)
    return bins_fixed(z, Z_EDGES)


@dataclass(frozen=True)
class Spec:
    family: str
    k: int
    args: tuple
    norm: tuple  # ("xs", nb) | ("z", w) | ("fix", edges)

    @property
    def name(self):
        a = ",".join(str(x) for x in self.args)
        n = self.norm[0] + (str(self.norm[1]) if self.norm[0] != "fix" else "")
        return f"{self.family}[{a}]@{self.k}h/{n}"


def view(bank, spec, elig):
    x = bank.get(spec.family, spec.k, spec.args)
    kind = spec.norm[0]
    if kind == "xs":
        return bins_xs(x, elig, spec.norm[1])
    if kind == "z":
        return bins_z(x, spec.norm[1])
    return bins_fixed(x, spec.norm[1])


def default_specs():
    """The feature grid of the first battery. Edges for bounded features are fixed in advance, never fitted."""
    S = []
    add = lambda fam, k, args, norm: S.append(Spec(fam, k, tuple(args), norm))
    z30 = lambda k: ("z", 30 * 24 // k)
    for k, ns in ((1, (1, 3, 6, 12, 24, 72, 168)), (4, (1, 3, 6, 12, 30)), (24, (1, 3, 7, 14, 30, 60, 90))):
        for n in ns:
            add("ret", k, (n,), ("xs", 8)); add("ret", k, (n,), z30(k))
    for k in TFS:
        for n in (8, 21, 55, 144):
            add("ema_ratio", k, (n,), ("xs", 8)); add("ema_ratio", k, (n,), z30(k))
        for a, b in ((8, 21), (21, 55), (55, 144), (12, 26)):
            add("ema_cross", k, (a, b), ("xs", 8)); add("ema_cross", k, (a, b), z30(k))
        for base in (5, 8, 13):
            add("ribbon", k, (base,), ("fix", (-3.5, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3.5)))
        for n in (7, 14, 28):
            add("rsi", k, (n,), ("fix", (20, 30, 40, 50, 60, 70, 80)))
        for n in (20, 50):
            add("bbz", k, (n,), ("fix", (-2, -1, -0.5, 0, 0.5, 1, 2)))
        for n in (20, 50, 100):
            add("donch", k, (n,), ("fix", (0.05, 0.2, 0.4, 0.6, 0.8, 0.95)))
        add("atrp", k, (14,), ("xs", 8)); add("atrp", k, (14,), z30(k))
        for n in (6, 24, 72):
            add("volz", k, (n,), ("xs", 8)); add("volz", k, (n,), z30(k))
            add("tbi", k, (n,), ("xs", 8)); add("tbi", k, (n,), z30(k))
        add("clv", k, (), ("fix", (-0.6, -0.2, 0.2, 0.6)))
        add("prem", k, (0,), ("xs", 8)); add("prem", k, (0,), z30(k))
        add("fund", k, (0,), ("xs", 8)); add("fund", k, (0,), z30(k))
        for gap in (0.0, 0.5):
            for side in ("bull", "bear"):
                add("fvg", k, (gap, side, "dist"), ("fix", (0.0, 0.25, 0.5, 1, 2, 4)))
                add("fvg", k, (gap, side, "age"), ("fix", (0, 2, 5, 10, 20, 50)))
        for imp in (1.5, 2.5):
            for side in ("bull", "bear"):
                add("ob", k, (imp, side), ("fix", (0.0, 0.25, 0.5, 1, 2, 4)))
        for n in (10, 20, 50):
            for side in ("bull", "bear"):
                add("sweep", k, (n, side), ("fix", (0, 1, 2, 4, 8, 16, 48)))
        for fr in (2, 5):
            add("struct", k, (fr, "state"), ("fix", (0,)))
            add("struct", k, (fr, "since"), ("fix", (0, 2, 5, 10, 25, 60)))
            add("struct", k, (fr, "pd"), ("fix", (0.0, 0.2, 0.382, 0.5, 0.618, 0.786, 1.0)))
    add("hour", 1, (), ("fix", tuple(range(1, 24))))
    add("dow", 1, (), ("fix", tuple(range(1, 7))))
    add("session", 1, (), ("fix", (1, 2, 3)))
    add("funding_clock", 1, (), ("fix", tuple(range(1, 8))))
    add("dayopen", 1, (), ("xs", 8)); add("dayopen", 1, (), ("z", 30 * 24))
    for what in ("high", "low", "close"):
        add("prevday", 1, (what,), ("fix", (-4, -2, -1, -0.5, 0, 0.5, 1, 2, 4)))
    add("prevday_raid", 1, ("high",), ("fix", (0.5,))); add("prevday_raid", 1, ("low",), ("fix", (0.5,)))
    add("asia", 1, (), ("fix", (-0.5, 0, 0.25, 0.5, 0.75, 1, 1.5)))
    for k, ns in ((1, (24, 72, 168)), (4, (6, 18, 42)), (24, (3, 7, 14))):
        for n in ns:
            add("btc_ret", k, (n,), ("z", 30 * 24)); add("disp", k, (n,), ("z", 30 * 24))
    for k in TFS:
        for n in (21, 55):
            add("breadth", k, (n,), ("fix", (0.2, 0.35, 0.5, 0.65, 0.8)))
    return S


def views(bank, specs, elig, log=None, out=None):
    """int8 [V, T, S] bins for the given specs, plus the spec names. Pass `out` (e.g. a disk-backed memmap) to avoid
    holding the whole tensor in memory."""
    if out is None:
        out = np.empty((len(specs), bank.p.T, bank.p.S), np.int8)
    for i, sp in enumerate(specs):
        out[i] = view(bank, sp, elig)
        bank.trim(sp)
        if log and (i + 1) % 25 == 0:
            log(f"  views {i + 1}/{len(specs)}")
    bank.trim()
    return out, [sp.name for sp in specs]


def check_causal(panel, specs, cuts):
    """Names of specs whose value at any row <= cut changes when every bar after the cut is wiped out. Must be empty."""
    full = Bank(panel)
    bad = []
    for cut in cuts:
        wiped = type(panel)(panel.t, panel.symbols, {k: v.copy() for k, v in panel.f.items()})
        for v in wiped.f.values():
            v[cut + 1:] = np.nan
        part = Bank(wiped)
        for sp in specs:
            a, b = full.get(sp.family, sp.k, sp.args)[: cut + 1], part.get(sp.family, sp.k, sp.args)[: cut + 1]
            if not np.allclose(a, b, rtol=1e-4, atol=1e-6, equal_nan=True) and sp.name not in bad:
                bad.append(sp.name)
    return bad
