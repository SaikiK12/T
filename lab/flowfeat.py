"""Order-flow features from the hourly metrics and bookDepth tables written by lab/flow.py, binned the same way as
lab/features.py (cross-sectional rank buckets, trailing 30-day z-score buckets, or fixed edges).

Row t aggregates what was published during the hour [t, t + 1 h), so like a kline it is known at the bar close.

metrics: oi_chg[n] log change of open interest over n hours; oi_price[n] quadrant of (price change, OI change) over
  n hours: 0 price down + OI down (longs closing), 1 down + up (new shorts), 2 up + down (shorts covering),
  3 up + up (new longs); crowd_ls log all-account long/short ratio; top_ls log top-trader position ratio;
  top_vs_crowd their difference (top traders against the crowd); taker[n] mean log taker buy/sell volume ratio
  over n hours; oi_turnover log(OI value / trailing 24 h quote volume), a leverage-crowding gauge.
bookDepth (30 most liquid symbols, from 2023): imb[k] (bid - ask) / (bid + ask) notional within k% of mid;
  imb_dev imb[1] minus its trailing 24 h mean; liq log(depth within 1% / trailing mean hourly quote volume);
  shape log(b1/b5) - log(a1/a5), whether liquidity near mid leans to the bid or the ask.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from . import data
from .features import bins_fixed, bins_xs, bins_z, roll
from .panel import HOUR, load_panel

METRIC_COLS = ("oi", "oi_value", "top_ls_sum", "ls_count", "taker_ls_vol")
BOOK_COLS = tuple(f"{s}{i}" for s in "ba" for i in range(1, 6))
IMB_EDGES = (-0.5, -0.3, -0.15, -0.05, 0.05, 0.15, 0.3, 0.5)
Z30 = ("z", 720)
XS8 = ("xs", 8)


def load(kind, t, symbols, cols, root=None):
    root = Path(root or data.ROOT) / f"{kind}_1h"
    out = {c: np.full((len(t), len(symbols)), np.nan, np.float32) for c in cols}
    for j, s in enumerate(symbols):
        p = root / f"{s}.parquet"
        if not p.exists():
            continue
        df = pd.read_parquet(p)
        i = (df["t"].values - t[0]) // HOUR
        ok = (i >= 0) & (i < len(t))
        for c in cols:
            out[c][i[ok], j] = df[c].values[ok]
    return out


def _log(x):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(x > 0, np.log(np.where(x > 0, x, 1)), np.nan).astype(np.float32)


def _chg(x, n):
    out = np.full_like(x, np.nan)
    out[n:] = x[n:] - x[:-n]
    return out


def raw_features(m, b, close, qvol):
    """Name -> [T, S] float32 raw feature."""
    f = {}
    loi, lc = _log(m["oi"]), _log(close)
    for n in (4, 24, 72):
        f[f"oi_chg[{n}]"] = _chg(loi, n)
    for n in (4, 24):
        dp, do = _chg(lc, n), _chg(loi, n)
        q = (dp > 0) * 2 + (do > 0)
        f[f"oi_price[{n}]"] = np.where(np.isfinite(dp) & np.isfinite(do), q, np.nan).astype(np.float32)
    f["crowd_ls"] = _log(m["ls_count"])
    f["top_ls"] = _log(m["top_ls_sum"])
    f["top_vs_crowd"] = f["top_ls"] - f["crowd_ls"]
    lt = _log(m["taker_ls_vol"])
    for n in (1, 4, 24):
        f[f"taker[{n}]"] = lt if n == 1 else roll(lt, n, "mean")
    vol24 = roll(np.nan_to_num(qvol), 24, "sum")
    f["oi_turnover"] = _log(m["oi_value"] / np.where(vol24 > 0, vol24, np.nan))
    if b is not None:
        for k in (1, 2, 5):
            bb, aa = b[f"b{k}"], b[f"a{k}"]
            f[f"imb[{k}]"] = ((bb - aa) / (bb + aa)).astype(np.float32)
        f["imb_dev"] = f["imb[1]"] - roll(f["imb[1]"], 24, "mean", 12)
        f["liq"] = _log((b["b1"] + b["a1"]) / roll(np.nan_to_num(qvol), 24, "mean"))
        f["shape"] = (_log(b["b1"] / b["b5"]) - _log(b["a1"] / b["a5"])).astype(np.float32)
    return f


def specs():
    """(feature name, norm) pairs in a fixed order."""
    S = []
    for n in (4, 24, 72):
        S += [(f"oi_chg[{n}]", XS8), (f"oi_chg[{n}]", Z30)]
    for n in (4, 24):
        S.append((f"oi_price[{n}]", ("fix", (1, 2, 3))))
    for name in ("crowd_ls", "top_ls", "top_vs_crowd"):
        S += [(name, XS8), (name, Z30)]
    for n in (1, 4, 24):
        S += [(f"taker[{n}]", XS8), (f"taker[{n}]", Z30)]
    S += [("oi_turnover", XS8), ("oi_turnover", Z30)]
    for k in (1, 2, 5):
        S += [(f"imb[{k}]", ("fix", IMB_EDGES)), (f"imb[{k}]", XS8), (f"imb[{k}]", Z30)]
    for name in ("imb_dev", "liq", "shape"):
        S += [(name, XS8), (name, Z30)]
    return S


def spec_name(name, norm):
    return f"flow:{name}/{norm[0]}" + (str(norm[1]) if norm[0] != "fix" else "")


def binned(x, norm, elig):
    if norm[0] == "xs":
        return bins_xs(x, elig, norm[1])
    if norm[0] == "z":
        return bins_z(x, norm[1])
    return bins_fixed(x, norm[1])


def build(t, symbols, elig, spec_list, out, log=print, root=None):
    p = load_panel(symbols, root=root)
    assert np.array_equal(p.t[: len(t)], t), "panel clock differs from the research clock"
    m = load("metrics", t, symbols, METRIC_COLS, root)
    have_book = (Path(root or data.ROOT) / "bookDepth_1h").exists()
    b = load("bookDepth", t, symbols, BOOK_COLS, root) if have_book else None
    log("loaded: metrics cover", f"{np.isfinite(m['oi']).mean():.2f}", "of cells;",
        "book", f"{np.isfinite(b['b1']).mean():.3f}" if b is not None else "missing")
    f = raw_features(m, b, p["close"][: len(t)], p["quote_volume"][: len(t)])
    names = []
    for i, (name, norm) in enumerate(spec_list):
        x = f.get(name)
        out[i] = -1 if x is None else binned(x, norm, elig)
        names.append(spec_name(name, norm))
        log(" ", names[-1], "cells with a value:", f"{(np.asarray(out[i]) >= 0)[elig].mean():.2f}")
    return names
