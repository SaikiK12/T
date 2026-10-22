"""Which daily-panel columns leak survival through their coverage (found in R299's audit).

The KuCoin, Kraken, MEXC, Hyperliquid, Upbit and Bithumb histories behind `data/daily/panel.parquet` were fetched for
the markets those venues listed at download time. A coin Binance later delisted therefore has almost none of their
columns, and whether a row has them tells a model which coins will die. Binance, Gate and dYdX include delisted
contracts. `lab/daily.py` labels every column `pit`, which is about timing only; that file is a frozen input of
several lanes, so the coverage label lives here. See docs/FEATURE_VINTAGE_INTEGRITY.md.
"""
import pandas as pd

SURVIVOR_VENUES = ("kucoin", "kraken", "mexc", "hyperliquid", "upbit", "bithumb")
FULL_VENUES = ("binance", "gate", "dydx")
DERIVED = ("n_venues",)          # counts venues, survivor-only ones included


def survivor_columns(columns):
    """The columns, in order, whose coverage depends on survival: any column of a survivor-only venue, and the
    derived ones over all venues. A lane's own mean over venues must be checked by the lane."""
    return [c for c in columns if c.split("_")[0] in SURVIVOR_VENUES or c in DERIVED]


def clean_columns(columns):
    """`columns` without the survivor-only ones."""
    bad = set(survivor_columns(columns))
    return [c for c in columns if c not in bad]


def dead_perps(close, margin=30):
    """Perps whose last close (a day x perp frame) is more than `margin` days before the frame's last day."""
    last = close.apply(lambda s: s.last_valid_index())
    return set(last[last < close.index.max() - pd.Timedelta(days=margin)].index)


def coverage_by_survival(df, columns, margin=30, universe=None):
    """Per column and calendar year: the share of rows with a value, for perps that survive and for perps that later
    stop trading. `df` is the long panel (day, perp, close, columns...). Rows need a close; `universe`, a day x perp
    boolean frame, restricts them further. Reads no return."""
    w = df.assign(day=pd.to_datetime(df.day))
    close = w.pivot(index="day", columns="perp", values="close")
    dead = dead_perps(close, margin)
    uni = close.notna()
    if universe is not None:
        uni &= universe.reindex_like(close).fillna(False).astype(bool)
    is_dead = pd.DataFrame({p: p in dead for p in close.columns}, index=close.index)
    years = close.index.year
    out = {}
    for c in columns:
        has = w.pivot(index="day", columns="perp", values=c).reindex_like(close).notna()
        out[c] = {}
        for y in sorted(set(years)):
            r = years == y
            live, gone = (uni & ~is_dead)[r], (uni & is_dead)[r]
            out[c][int(y)] = (float(has[r][live].sum().sum() / max(int(live.sum().sum()), 1)),
                              float(has[r][gone].sum().sum() / max(int(gone.sum().sum()), 1)))
    return out
