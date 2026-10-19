"""One hourly clock for every symbol, and higher timeframes that only become visible once their bar has closed.

Row i is the hour bar [t_i, t_i + 1h). A signal at row i may use data through the end of bar i and acts on the return of
bar i + 1 (close_i to close_{i+1}). Higher-timeframe values are placed on the last hour of their bar and carried forward,
so a 4h or daily feature is never read before it is final.
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from . import data

START = "2021-01-01"
HOUR = 3_600_000
FIELDS = ("open", "high", "low", "close", "volume", "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume")


def ms(day: str) -> int:
    return int(pd.Timestamp(day, tz="UTC").timestamp() * 1000)


@dataclass
class Panel:
    t: np.ndarray            # [T] epoch ms of each hour open
    symbols: list
    f: dict                  # field name -> float32 [T, S], NaN where the symbol is not trading

    def __getitem__(self, k):
        return self.f[k]

    @property
    def T(self):
        return len(self.t)

    @property
    def S(self):
        return len(self.symbols)

    def columns(self, idx):
        idx = np.asarray(idx)
        return Panel(self.t, [self.symbols[i] for i in idx], {k: v[:, idx] for k, v in self.f.items()})

    def head(self, n):
        return Panel(self.t[:n], self.symbols, {k: v[:n] for k, v in self.f.items()})


def ffill(x):
    """Carry the last valid value forward down the time axis (axis 0); leading gaps stay NaN."""
    idx = np.where(~np.isnan(x), np.arange(len(x))[:, None], 0)
    np.maximum.accumulate(idx, axis=0, out=idx)
    return np.take_along_axis(x, idx, axis=0)


def load_panel(symbols=None, root=None, start=START, end=data.END):
    root = Path(root or data.ROOT)
    t0 = ms(start)
    t = np.arange(t0, ms(end) + 24 * HOUR, HOUR)
    symbols = list(symbols or sorted(p.stem for p in (root / "klines_1h").glob("*.parquet")))
    f = {k: np.full((len(t), len(symbols)), np.nan, np.float32) for k in FIELDS}
    f["premium"] = np.full((len(t), len(symbols)), np.nan, np.float32)
    f["funding"] = np.full((len(t), len(symbols)), np.nan, np.float32)
    f["fund_event"] = np.full((len(t), len(symbols)), np.nan, np.float32)  # the rate on the bar where it settles
    for j, s in enumerate(symbols):
        df = pd.read_parquet(root / "klines_1h" / f"{s}.parquet")
        i = (df["t"].values - t0) // HOUR
        ok = (i >= 0) & (i < len(t))
        for k in FIELDS:
            f[k][i[ok], j] = df[k].values[ok]
        for name, folder, col in (("premium", "premiumIndexKlines_1h", "close"), ("funding", "fundingRate", "rate")):
            path = root / folder / f"{s}.parquet"
            if path.exists():
                d = pd.read_parquet(path)
                i = (d["t"].values - t0) // HOUR
                ok = (i >= 0) & (i < len(t))
                f[name][i[ok], j] = d[col].values[ok]
                if name == "funding":
                    f["fund_event"][i[ok], j] = d[col].values[ok]
    f["funding"] = ffill(f["funding"])  # the rate is public at settlement and holds until the next one
    return Panel(t, symbols, f)


def liquidity_rank(p, window=24 * 30):
    """Rank (1 = most liquid) by trailing mean quote volume, using bars through row i only. NaN when not trading."""
    qv = pd.DataFrame(np.nan_to_num(p["quote_volume"])).rolling(window, min_periods=window // 4).mean().values
    qv = np.where(np.isnan(p["close"]), -np.inf, np.nan_to_num(qv, nan=-np.inf))
    rank = (-qv).argsort(axis=1).argsort(axis=1).astype(np.float32) + 1
    rank[np.isneginf(qv)] = np.nan
    return rank


def _first_valid(r):
    i = np.argmax(~np.isnan(r), axis=1)
    return np.take_along_axis(r, i[:, None, :], axis=1)[:, 0]


def resample(p, k):
    """Aggregate complete k-hour bars on the UTC-day clock.

    A partial block is marked missing instead of being presented as a full
    bar. ``coverage`` exposes the number of finite hourly closes in each block
    for diagnostics.
    """
    assert p.T % k == 0 and 24 % k == 0
    n = p.T // k
    r = {name: x.reshape(n, k, -1) for name, x in p.f.items()}
    price_complete = (np.isfinite(r["open"]) & np.isfinite(r["high"]) &
                      np.isfinite(r["low"]) & np.isfinite(r["close"])).all(axis=1)
    out = {
        "open": np.where(price_complete, _first_valid(r["open"]), np.nan),
        "high": np.where(price_complete, np.fmax.reduce(r["high"], axis=1), np.nan),
        "low": np.where(price_complete, np.fmin.reduce(r["low"], axis=1), np.nan),
        "close": np.where(price_complete, _first_valid(r["close"][:, ::-1]), np.nan),
        "coverage": np.isfinite(r["close"]).sum(axis=1).astype(np.int16),
    }
    for name in ("volume", "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume"):
        complete = np.isfinite(r[name]).all(axis=1)
        summed = np.sum(np.where(np.isfinite(r[name]), r[name], 0.0), axis=1)
        out[name] = np.where(complete, summed, np.nan).astype(np.float32)
    for name in ("premium", "funding"):
        if name in r:
            out[name] = _first_valid(r[name][:, ::-1])
    return {name: (x.astype(np.float32) if name != "coverage" else x) for name, x in out.items()}


def align(x, k):
    """Put k-hour values on the hourly clock: each is placed on its bar's last hour, then carried forward."""
    out = np.full((len(x) * k,) + x.shape[1:], np.nan, np.float32)
    out[k - 1::k] = x
    return ffill(out)
