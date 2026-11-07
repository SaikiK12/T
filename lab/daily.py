"""Daily point-in-time panel: one row per (day, Binance USD-M perp) with what every source the lab holds had said
about that coin by 00:00 UTC of that day, plus one row per day of market-wide series.

**Timing.** Row D is a decision at 00:00 UTC on day D. Each observation goes on the first row at or after the moment it
is known:
- an hourly bar opening at t goes on row ceil((t + 1 h) / 1 day), so row D holds the 24 bars of day D - 1;
- a daily candle goes on the row of its close. Bithumb's candles close at 15:00 UTC, so they wait for the next row;
- a funding settlement at s goes on row ceil(s / 1 day), with s rounded to the minute, so a settlement at 00:00
  belongs to the day it ends;
- a series published `lag` days after its date goes on row date + lag (`SOURCE_LAGS`, `MARKET_LAGS`).

A row exists only when the perp traded in those 24 hours. Bars without a trade are dropped on every venue: after a
delisting, Binance's archive keeps writing them at a frozen close (8.75% of all hourly bars since 2021, 95% of them
in the dead tails of 148 delisted perps).

Sums (volume, funding) cover the 24 hours that end at 00:00 of row D. Levels are the last value known by then. Nothing
on row D uses anything later (tests/test_daily.py changes the future and checks).

**Reserved rows.** Nothing before `panel.START` (2021-01-01) is read: the first row is START + 1 day, and coins
listed before START have no age. Only the other venues' `open/` folders are read, through `lab.venues`, and only
coins with a Binance perp are listed. So the long tails, the MEXC-only coins and every 2020 row stay unread
(docs/GATES.md).

**Identity.** The same ticker is not proof of the same coin. A venue's columns on row D are kept only when the median
absolute log gap between its price and Binance's, at the same moment, over the last `IDENT_DAYS` rows, is at most
`IDENT_MAX`. It needs at least `IDENT_MIN` observations and uses rows up to D only.

**Not point in time.** Coin Metrics, DefiLlama and the macro series serve their latest vintage, so past values may
have been revised. `COLUMNS` marks them `vintage`. Everything else is `pit`: archives of what traded and settled.

usage: python scripts/build_daily.py (writes data/daily/), then `daily.load(columns=[...])`.
"""
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from . import data, panel, venues

DAY, H, MIN = 86_400_000, 3_600_000, 60_000
OUT = data.ROOT / "daily"
IDENT_DAYS, IDENT_MIN, IDENT_MAX = 30, 5, 0.10
SOURCE_LAGS = {"coinmetrics": 2, "defillama": 2}   # value dated X on row X + lag (end of day X, published after)
# market-wide series (data/macro): rows after the series' own date before the value is public
MARKET_LAGS = {
    "fng": 1,                                                                  # alternative.me, set at 00:00 UTC
    "sp500": 1, "nasdaq": 1, "vix": 1,                                         # US close, public the same evening
    "ust_3m": 2, "ust_2y": 2, "ust_10y": 2, "curve_10y2y": 2, "fed_funds": 2,  # H.15 / FRED, next business day
    "breakeven_10y": 2, "ust_real_10y": 2, "hy_spread": 2, "rrp": 2,
    "fed_assets": 2, "tga": 2,                                                 # H.4.1, Wednesday level, out Thursday
    "nfci": 6, "stl_fsi": 7,                                                   # weekly, out the next Wed / Thu
    "usd_broad": 8, "krw_usd": 8, "cny_usd": 8, "wti": 8,                      # H.10 and EIA, weekly releases
    "m2": 60,                                                                  # monthly H.6, about 4 weeks later
    "stable_total": 1, "stable_usdt": 1, "stable_usdc": 1, "defi_tvl": 1,      # DefiLlama daily snapshots
    "dex_volume": 1, "defi_fees": 1, "options_volume": 1,
    "btc_hashrate": 2, "btc_tx": 2, "btc_addresses": 2, "btc_miner_rev": 2, "btc_fees_usd": 2, "btc_mempool": 2,
}
MARKET_LAG_DEFAULT = 8
# (venue, price folder, price is hourly, USD volume rule, funding folder); paths under data/
VENUES = {
    "gate": ("gate_hist/open/candlesticks_1h", True, "gate", "gate_hist/open/funding_applies"),
    "mexc": ("mexc_hist/klines_1h", True, "amount", "mexc_hist/funding"),
    "dydx": ("dydx_hist/open/candles_1h", True, "usd_volume", "dydx_hist/open/funding"),
    "hyperliquid": ("hyperliquid/candles_1d", False, "coin", "hyperliquid/funding"),
    "kucoin": ("kucoin_hist/open/candles_1d", False, "turnover", "kucoin_hist/open/funding"),
    "kraken": ("kraken_hist/open/candles_1d", False, "coin", "kraken_hist/open/funding"),
}
KOREAN = {"upbit": "upbit_hist/open/candles_1d", "bithumb": "bithumb_hist/open/candles_1d"}

# (column, source, definition, pit | vintage); {v} = each venue in VENUES, {k} = upbit / bithumb
COLUMNS = [
    ("close", "binance", "last traded close of the 24 h (perp, USDT)", "pit"),
    ("ret", "binance", "close / previous row's close - 1 (NaN after a missing row)", "pit"),
    ("range", "binance", "24 h high / low - 1", "pit"),
    ("qvol", "binance", "24 h quote volume, USDT", "pit"),
    ("trades", "binance", "24 h trade count", "pit"),
    ("taker_buy", "binance", "taker-buy share of the 24 h quote volume", "pit"),
    ("bars", "binance", "hourly bars present in the 24 h (24 = complete)", "pit"),
    ("fund", "binance", "sum of funding rates settled in the 24 h (paid by longs)", "pit"),
    ("fund_n", "binance", "number of funding settlements in the 24 h", "pit"),
    ("premium", "binance", "premium index close at the last hour", "pit"),
    ("mark_gap", "binance", "close / mark-price close - 1, last hour with both", "pit"),
    ("wick_up", "binance", "max over the 24 h of hourly high / mark high - 1 (a traded print above the mark)", "pit"),
    ("wick_dn", "binance", "min over the 24 h of hourly low / mark low - 1", "pit"),
    ("oi_usd", "binance metrics", "open interest value at the last hour", "pit"),
    ("top_ls_pos", "binance metrics", "top-trader long/short position ratio, last hour", "pit"),
    ("top_ls_acc", "binance metrics", "top-trader long/short account ratio, last hour", "pit"),
    ("ls_acc", "binance metrics", "all-account long/short ratio, last hour", "pit"),
    ("taker_ls", "binance metrics", "taker buy/sell volume ratio, last hour", "pit"),
    ("depth1_usd", "binance bookDepth", "mean notional within 1% of mid, bid + ask, over the 24 h (30 coins)", "pit"),
    ("spot_qvol", "binance spot", "24 h spot quote volume, USDT", "pit"),
    ("basis", "binance spot", "perp close / spot close - 1, last hour with both", "pit"),
    ("qtr_basis_ann", "binance coin-m", "nearest quarterly (7+ days left) / COIN-M perp - 1, annualized", "pit"),
    ("qtr_days", "binance coin-m", "days to that quarterly's expiry", "pit"),
    ("{v}_gap", "{v}", "venue price (in Binance units) / Binance close at the same moment - 1", "pit"),
    ("{v}_fund", "{v}", "sum of the venue's funding rates settled in the 24 h", "pit"),
    ("{v}_fund_gap", "{v}", "{v}_fund - fund: positive when the venue's longs pay more than Binance's", "pit"),
    ("{v}_qvol", "{v}", "venue 24 h volume in USD (not kraken)", "pit"),
    ("mexc_premium", "mexc", "MEXC close / MEXC index price - 1, last hour with both", "pit"),
    ("{k}_rel", "{k}", "KRW price relative to BTC on the venue / the same ratio on Binance - 1 (the coin's kimchi "
     "premium over BTC's; no FX needed)", "pit"),
    ("{k}_qvol", "{k}", "KRW turnover in USDT at the venue's own BTC rate", "pit"),
    ("n_venues", "derived", "venues whose price passes the identity check on the row", "pit"),
    ("age_days", "derived", "days since the first Binance bar (NaN for coins already trading at the panel start)",
     "pit"),
    ("rank_qvol30", "derived", "rank of the trailing 30-row mean qvol among perps on the row (1 = most traded)", "pit"),
    ("mcap", "coinmetrics", "CapMrktCurUSD, the day 2 rows back", "vintage"),
    ("mcap_est", "coinmetrics", "CapMrktEstUSD (estimated free float)", "vintage"),
    ("supply", "coinmetrics", "SplyCur", "vintage"),
    ("active_addr", "coinmetrics", "AdrActCnt", "vintage"),
    ("tx_count", "coinmetrics", "TxCnt", "vintage"),
    ("ex_netflow_usd", "coinmetrics", "FlowInExUSD - FlowOutExUSD (into exchanges)", "vintage"),
    ("mvrv", "coinmetrics", "CapMVRVCur", "vintage"),
    ("tvl", "defillama", "protocol TVL, USD, the day 2 rows back", "vintage"),
    ("fees", "defillama", "protocol fees, USD", "vintage"),
    ("revenue", "defillama", "protocol revenue, USD", "vintage"),
]
CM_COLS = {"mcap": "CapMrktCurUSD", "mcap_est": "CapMrktEstUSD", "supply": "SplyCur", "active_addr": "AdrActCnt",
           "tx_count": "TxCnt", "mvrv": "CapMVRVCur"}


def columns():
    """COLUMNS with {v} and {k} expanded, in panel order."""
    out = []
    for c, s, d, kind in COLUMNS:
        names = VENUES if "{v}" in c else KOREAN if "{k}" in c else [None]
        for n in names:
            if n is None:
                out.append((c, s, d, kind))
            elif not (c == "{v}_qvol" and n == "kraken"):
                out.append((c.format(v=n, k=n), s.format(v=n, k=n), d.format(v=n, k=n), kind))
    return out


def row_of(ms):
    """Index (epoch days) of the first 00:00 UTC at or after `ms`."""
    return -(-np.asarray(ms, np.int64) // DAY)


def settle_row(ms):
    """Row of a settlement time, rounded to the minute first (Binance stamps 00:00:00.002)."""
    return row_of((np.asarray(ms, np.int64) + MIN // 2) // MIN * MIN)


def _read(path, cols=None):
    try:
        return pd.read_parquet(path, columns=cols)
    except (FileNotFoundError, OSError, KeyError, ValueError):
        return None


def _bars(path, cols, t_lo, t_hi):
    """Bars (index t = open, ms) in [t_lo, t_hi), sorted, one per t."""
    d = _read(path, ["t", *cols])
    if d is None or not len(d):
        return None
    d = d.assign(t=d.t.astype("int64"))
    d = d[(d.t >= t_lo) & (d.t < t_hi)].sort_values("t").drop_duplicates("t", keep="last")
    return d.set_index("t") if len(d) else None


def _rows(d, bar_ms, last=(), total=(), high=(), low=(), mean=()):
    """Bars reduced to rows by the row of each bar's end."""
    g = d.groupby(row_of(d.index.to_numpy(np.int64) + bar_ms))
    parts = []
    if last:
        parts.append(g[list(last)].last())
    if total:
        parts.append(g[list(total)].sum(min_count=1))
    if high:
        parts.append(g[list(high)].max())
    if low:
        parts.append(g[list(low)].min())
    if mean:
        parts.append(g[list(mean)].mean())
    return pd.concat(parts, axis=1)


def _funding(path, t_lo, t_hi, col="rate"):
    """(sum, count) of settled rates per row, for settlements in (t_lo, t_hi] (times rounded to the minute)."""
    d = _read(path, ["t", col])
    if d is None or not len(d):
        return None
    t = (d.t.astype("int64") + MIN // 2) // MIN * MIN
    d = d[(t > t_lo) & (t <= t_hi)]
    if not len(d):
        return None
    g = d[col].groupby(settle_row(d.t.astype("int64")))
    return pd.DataFrame({"sum": g.sum(min_count=1), "n": g.count()})


def _last_with(a, b, bar_ms, fn):
    """fn(a, b) on the hours both series hold, then the last value per row."""
    j = pd.concat([a.rename("a"), b.rename("b")], axis=1, join="inner").dropna()
    if not len(j):
        return pd.Series(dtype=np.float64)
    return pd.Series(fn(j.a, j.b).to_numpy(), index=j.index).groupby(row_of(j.index.to_numpy(np.int64) + bar_ms)).last()


def _identity(gap, idx):
    """Mask (True = keep) for a venue's gap series on rows idx: trailing median |log(1 + gap)| <= IDENT_MAX."""
    g = np.log1p(gap.reindex(idx)).abs()
    med = g.rolling(IDENT_DAYS, min_periods=IDENT_MIN).median()
    return (med <= IDENT_MAX).to_numpy()


def _mult_spot(perp, spot):
    hit = venues.binance_perp(spot[:-4], {perp}) if spot.endswith("USDT") else None
    return hit[1] if hit else 1.0


class Sources:
    """What a build reads besides each perp's own files: the venue map, spot pairs, COIN-M files, Korean BTC."""

    def __init__(self, root, t_lo, t_hi):
        self.root, self.t_lo, self.t_hi = Path(root), t_lo, t_hi
        self.map, self.notes = venues.table(root)
        sp = self.root / "spot_pairs.json"
        self.spot = json.loads(sp.read_text()) if sp.exists() else {}
        self.gate_quanto = {}
        gc = self.root / "gate_hist" / "contracts.csv"
        if gc.exists():
            g = pd.read_csv(gc, dtype=str)
            self.gate_quanto = dict(zip(g.name, pd.to_numeric(g.quanto_multiplier, errors="coerce")))
        self.coinm = {}
        perps = venues.binance_perps(root)
        for p in sorted((self.root / "coinm_1h").glob("*USD_*.parquet")):
            base, kind = p.stem.split("USD_", 1)
            hit = venues.binance_perp(base, perps)
            if hit and hit[1] == 1:
                self.coinm.setdefault(hit[0], {})[kind] = p
        self.korean_btc = {}
        for k, folder in KOREAN.items():
            d = _bars(self.root / folder / "KRW-BTC.parquet", ["close"], t_lo, t_hi)
            if d is not None:
                self.korean_btc[k] = d.close
        b = _bars(self.root / "klines_1h" / "BTCUSDT.parquet", ["close"], t_lo, t_hi)
        self.btc_end = pd.Series(b.close.to_numpy(), index=b.index + H) if b is not None else pd.Series(dtype=float)


def perp_frame(src, perp, r_lo, r_hi):
    """All columns for one perp on rows [r_lo, r_hi), or None when it has no Binance bar there."""
    root, t_lo, t_hi = src.root, src.t_lo, src.t_hi
    k = _bars(root / "klines_1h" / f"{perp}.parquet",
              ["high", "low", "close", "quote_volume", "count", "taker_buy_quote_volume"], t_lo, t_hi)
    if k is not None:
        k = k[k["count"] > 0]          # after a delisting the archive keeps writing no-trade bars at a frozen close
    if k is None or not len(k):
        return None
    rows = _rows(k, H, last=["close"], total=["quote_volume", "count", "taker_buy_quote_volume"], high=["high"],
                 low=["low"])
    first, last = int(rows.index.min()), int(rows.index.max())
    idx = pd.RangeIndex(max(first, r_lo), min(last + 1, r_hi))
    if not len(idx):
        return None
    rows = rows.reindex(idx)
    f = pd.DataFrame(index=idx)
    f["close"] = rows.close
    f["ret"] = rows.close / rows.close.shift(1) - 1
    f["range"] = rows.high / rows.low - 1
    f["qvol"] = rows.quote_volume
    f["trades"] = rows["count"]
    f["taker_buy"] = rows.taker_buy_quote_volume / rows.quote_volume
    f["bars"] = k.close.groupby(row_of(k.index.to_numpy(np.int64) + H)).count().reindex(idx)
    fu = _funding(root / "fundingRate" / f"{perp}.parquet", t_lo, t_hi)
    if fu is not None:
        f["fund"], f["fund_n"] = fu["sum"].reindex(idx), fu["n"].reindex(idx)
    pr = _bars(root / "premiumIndexKlines_1h" / f"{perp}.parquet", ["close"], t_lo, t_hi)
    if pr is not None:
        f["premium"] = _rows(pr, H, last=["close"]).close.reindex(idx)
    mk = _bars(root / "markPriceKlines_1h" / f"{perp}.parquet", ["high", "low", "close"], t_lo, t_hi)
    if mk is not None:
        f["mark_gap"] = _last_with(k.close, mk.close, H, lambda a, b: a / b - 1).reindex(idx)
        j = k[["high", "low"]].join(mk[["high", "low"]], rsuffix="_m", how="inner")
        r = row_of(j.index.to_numpy(np.int64) + H)
        f["wick_up"] = (j.high / j.high_m - 1).groupby(r).max().reindex(idx)
        f["wick_dn"] = (j.low / j.low_m - 1).groupby(r).min().reindex(idx)
    me = _bars(root / "metrics_1h" / f"{perp}.parquet", ["oi_value", "top_ls_sum", "top_ls_count", "ls_count",
                                                          "taker_ls_vol"], t_lo, t_hi)
    if me is not None:
        m = _rows(me, H, last=list(me.columns)).reindex(idx)
        f["oi_usd"], f["top_ls_pos"], f["top_ls_acc"] = m.oi_value, m.top_ls_sum, m.top_ls_count
        f["ls_acc"], f["taker_ls"] = m.ls_count, m.taker_ls_vol
    bd = _bars(root / "bookDepth_1h" / f"{perp}.parquet", ["b1", "a1"], t_lo, t_hi)
    if bd is not None:
        f["depth1_usd"] = _rows(bd.assign(d=bd.b1 + bd.a1), H, mean=["d"]).d.reindex(idx)
    if perp in src.spot:
        sp = _bars(root / "spot_1h" / f"{perp}.parquet", ["close", "quote_volume", "count"], t_lo, t_hi)
        sp = sp[sp["count"] > 0] if sp is not None else None
        if sp is not None and len(sp):
            mult = _mult_spot(perp, src.spot[perp]["spot"])
            f["spot_qvol"] = _rows(sp, H, total=["quote_volume"]).quote_volume.reindex(idx)
            f["basis"] = _last_with(k.close, sp.close * mult, H, lambda a, b: a / b - 1).reindex(idx)
    if perp in src.coinm:
        f = f.join(_quarterly(src.coinm[perp], t_lo, t_hi, idx))
    b_end = pd.Series(k.close.to_numpy(), index=k.index + H)        # Binance close by the moment it is final
    kept = []
    for v, (folder, hourly, vol, ffolder) in VENUES.items():
        key, mult = src.map.get(perp, {}).get(v, ("", ""))
        if not key:
            continue
        mult = float(mult)
        vcol = {"gate": "vol_contracts", "coin": "volume"}.get(vol, vol)
        vb = _bars(root / folder / f"{key}.parquet", ["close", vcol], t_lo, t_hi)
        vb = vb[vb[vcol] > 0] if vb is not None else None          # a bar without volume has a stale close
        if vb is None or not len(vb):
            continue
        bar = H if hourly else DAY
        px = vb.close * mult
        gap = _last_with(px.set_axis(vb.index + bar), b_end, 0, lambda a, b: a / b - 1)
        keep = _identity(gap, idx)
        f[f"{v}_gap"] = np.where(keep, gap.reindex(idx), np.nan)
        fu = _funding(root / ffolder / f"{key}.parquet", t_lo, t_hi)
        if fu is not None:
            f[f"{v}_fund"] = np.where(keep, fu["sum"].reindex(idx), np.nan)
            f[f"{v}_fund_gap"] = f[f"{v}_fund"] - f.get("fund", np.nan)
        if v != "kraken":
            usd = (vb[vcol] * src.gate_quanto.get(key, np.nan) * vb.close if vol == "gate"
                   else vb[vcol] * vb.close if vol == "coin" else vb[vcol])
            q = usd.groupby(row_of(vb.index.to_numpy(np.int64) + bar)).sum(min_count=1).reindex(idx)
            f[f"{v}_qvol"] = np.where(keep, q, np.nan)
        if v == "mexc":
            ix = _bars(root / "mexc_hist" / "index_price_1h" / f"{key}.parquet", ["close"], t_lo, t_hi)
            if ix is not None:
                f["mexc_premium"] = np.where(keep, _last_with(vb.close, ix.close, H, lambda a, b: a / b - 1)
                                             .reindex(idx), np.nan)
        kept.append(keep)
    for kv, folder in KOREAN.items():
        key = src.map.get(perp, {}).get(kv, ("", ""))[0]
        if not key or kv not in src.korean_btc:
            continue
        kb = _bars(root / folder / f"{key}.parquet", ["close", "turnover_krw"], t_lo, t_hi)
        if kb is None:
            continue
        end = kb.index + DAY
        j = pd.DataFrame({"x": kb.close.to_numpy(), "turn": kb.turnover_krw.to_numpy(),
                          "xb": src.korean_btc[kv].reindex(kb.index).to_numpy(),
                          "b": b_end.reindex(end).to_numpy(), "bb": src.btc_end.reindex(end).to_numpy()},
                         index=end)
        rel = ((j.x / j.xb) / (j.b / j.bb) - 1).dropna()
        r = pd.Series(rel.to_numpy(), index=row_of(rel.index.to_numpy(np.int64))).groupby(level=0).last()
        keep = _identity(r, idx)
        f[f"{kv}_rel"] = np.where(keep, r.reindex(idx), np.nan)
        usd = (j.turn / (j.xb / j.bb)).dropna()
        u = pd.Series(usd.to_numpy(), index=row_of(usd.index.to_numpy(np.int64))).groupby(level=0).last()
        f[f"{kv}_qvol"] = np.where(keep, u.reindex(idx), np.nan)
    f["n_venues"] = np.sum(kept, axis=0) if kept else 0
    f["age_days"] = (idx - first).astype(np.float64) if k.index.min() > t_lo else np.nan
    for name, (folder, cols) in {"coinmetrics": ("coinmetrics/open", CM_COLS),
                                 "defillama": ("defillama/open", {c: c for c in ("tvl", "fees", "revenue")})}.items():
        key = src.map.get(perp, {}).get(name, ("", ""))[0]
        if not key:
            continue
        d = _read(root / folder / f"{key}.parquet")
        if d is None:
            continue
        d = d[(d.t.astype("int64") >= t_lo) & (d.t.astype("int64") < t_hi)]
        r = d.t.astype("int64").to_numpy() // DAY + SOURCE_LAGS[name]
        for out, col in cols.items():
            if col in d:
                f[out] = pd.Series(d[col].to_numpy(np.float64), index=r).groupby(level=0).last().reindex(idx)
        if name == "coinmetrics" and {"FlowInExUSD", "FlowOutExUSD"} <= set(d.columns):
            flow = d.FlowInExUSD.to_numpy(np.float64) - d.FlowOutExUSD.to_numpy(np.float64)
            f["ex_netflow_usd"] = pd.Series(flow, index=r).groupby(level=0).last().reindex(idx)
    return f


def _quarterly(files, t_lo, t_hi, idx):
    """qtr_basis_ann and qtr_days per row, from the nearest COIN-M quarterly with 7 or more days left."""
    out = pd.DataFrame(index=idx, columns=["qtr_basis_ann", "qtr_days"], dtype=np.float64)
    perp = files.get("PERP")
    pp = _bars(perp, ["close"], t_lo, t_hi) if perp else None
    if pp is None:
        return out
    best = {}
    for kind, path in files.items():
        if not kind.isdigit():
            continue
        expiry = pd.Timestamp(f"20{kind[:2]}-{kind[2:4]}-{kind[4:]} 08:00", tz="UTC").value // 10**6
        q = _bars(path, ["close"], t_lo, t_hi)
        if q is None:
            continue
        b = _last_with(q.close, pp.close, H, lambda a, b: a / b - 1)
        for r, val in b.items():
            days = (expiry - r * DAY) / DAY
            if days >= 7 and (r not in best or days < best[r][1]):
                best[r] = (val, days)
    for r, (val, days) in best.items():
        if r in out.index:
            out.loc[r] = (val * 365.0 / days, days)
    return out


def market(root, t_lo, t_hi, r_lo, r_hi):
    """One row per day: every series in data/macro on its public row (MARKET_LAGS), carried forward."""
    root = Path(root)
    idx = pd.RangeIndex(r_lo, r_hi)
    out = pd.DataFrame(index=idx)
    for p in sorted((root / "macro").glob("*.parquet")):
        d = _read(p, ["t", "value"])
        if d is None:
            continue
        t = d.t.astype("int64")
        lag = MARKET_LAGS.get(p.stem, MARKET_LAG_DEFAULT)
        # the series may start before t_lo; only its value on rows >= r_lo is kept (macro data is not reserved)
        s = pd.Series(d.value.to_numpy(np.float64), index=t.to_numpy() // DAY + lag).groupby(level=0).last()
        s = s[s.index < r_hi]
        out[p.stem] = s.reindex(s.index.union(idx)).ffill().reindex(idx)
    return out


def build(root=None, start=panel.START, end=data.END, perps=None, workers=8, log=print):
    """(panel, market, notes) on rows from start + 1 day through end. Row `end` holds day end - 1; day `end` itself is
    read but not placed, because its 00:00 settlement and some sources' last values fall after the archive ends."""
    panel.check_reserved(start)
    root = Path(root or data.ROOT)
    t_lo, t_hi = panel.ms(start), panel.ms(end) + DAY
    r_lo, r_hi = t_lo // DAY + 1, t_hi // DAY
    src = Sources(root, t_lo, t_hi)
    perps = sorted(perps or venues.binance_perps(root))
    t0 = time.time()
    with ThreadPoolExecutor(workers) as ex:
        frames = list(ex.map(lambda p: perp_frame(src, p, r_lo, r_hi), perps))
    log(f"daily: {sum(f is not None for f in frames)} of {len(perps)} perps read in {time.time() - t0:.0f}s")
    cols = [c for c, *_ in columns()]
    parts = []
    for p, f in zip(perps, frames):
        if f is None:
            continue
        f = f.reindex(columns=cols)
        f.insert(0, "perp", p)
        f.insert(0, "row", f.index.to_numpy())
        parts.append(f)
    df = pd.concat(parts, ignore_index=True)
    df = df[df.close.notna()].sort_values(["row", "perp"], ignore_index=True)    # rows with a trade only
    trail = df.groupby("perp").qvol.transform(lambda s: s.rolling(30, min_periods=7).mean())
    df["rank_qvol30"] = trail.groupby(df.row).rank(ascending=False, method="min")
    df.insert(0, "day", pd.to_datetime(df.pop("row") * DAY, unit="ms").dt.date)
    df["perp"] = df.perp.astype("category")
    floats = df.columns[2:]
    df[floats] = df[floats].astype(np.float32)
    mk = market(root, t_lo, t_hi, r_lo, r_hi)
    mk.insert(0, "day", pd.to_datetime(mk.index.to_numpy() * DAY, unit="ms").date)
    return df, mk.reset_index(drop=True), src.notes


def load(columns=None, start=None, end=None, root=None, perps=None):
    """The built panel (data/daily/panel.parquet) as a DataFrame, optionally limited to columns, rows and perps."""
    root = Path(root or OUT)
    if start is not None:
        panel.check_reserved(str(start))
    cols = None if columns is None else ["day", "perp", *[c for c in columns if c not in ("day", "perp")]]
    df = pd.read_parquet(root / "panel.parquet", columns=cols)
    if start is not None:
        df = df[df.day >= pd.Timestamp(start).date()]
    if end is not None:
        df = df[df.day <= pd.Timestamp(end).date()]
    if perps is not None:
        df = df[df.perp.isin(perps)]
    return df.reset_index(drop=True)


def load_market(root=None):
    return pd.read_parquet(Path(root or OUT) / "market.parquet")
