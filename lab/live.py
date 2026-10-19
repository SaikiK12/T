"""Public live data from Binance USD-M futures, for paper trading only: no keys, no orders, nothing private.

fapi.binance.com is geo-blocked from here (451); the same public endpoints answer on www.binance.com.

klines      /fapi/v1/klines, full history, 1500 rows a request.
funding     /fapi/v1/fundingRate, full history.
ratios      /futures/data/{topLongShortPositionRatio, globalLongShortAccountRatio, takerlongshortRatio,
            openInterestHist}, 5-minute rows for about the last 28 days only, 500 rows a request. These are the live
            versions of the archive's metrics columns, reduced to hours exactly as lab/flow.reduce_metrics does: ratios
            averaged over the hour, OI at the last row of the hour, keyed by the hour that contains the row, after
            moving the live stamps onto the archive's clock (ARCHIVE_SHIFTS).

Everything fetched is cached under data/live/ (gitignored) and merged on the next call, so an hourly tick only
downloads what is new.
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from . import data

BASE = "https://www.binance.com"
HOUR = 3_600_000
FIVE = 300_000
ROOT = data.ROOT / "live"
KLINE_COLS = ("t", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "count",
              "taker_buy_volume", "taker_buy_quote_volume", "ignore")
# live endpoint -> (archive metrics column, field in the JSON rows)
RATIOS = {"topLongShortPositionRatio": ("top_ls_sum", "longShortRatio"),
          "globalLongShortAccountRatio": ("ls_count", "longShortRatio"),
          "takerlongshortRatio": ("taker_ls_vol", "buySellRatio"),
          "topLongShortAccountRatio": ("top_ls_count", "longShortRatio")}
OI = "openInterestHist"


class LiveError(Exception):
    pass


_weight = {"used": 0, "last_data": 0.0}
DATA_GAP = 0.3     # seconds between /futures/data calls (their limit is 1000 requests per 5 minutes per IP)


def get(path, params=None, tries=5, timeout=30):
    """GET a public endpoint and parse the JSON, with retries and backoff; slows down when the weight runs high."""
    url = f"{BASE}/{path}" + ("?" + urllib.parse.urlencode(params) if params else "")
    delay = 1.0
    err = None
    for attempt in range(tries):
        if path.startswith("futures/data"):
            wait = _weight["last_data"] + DATA_GAP - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            _weight["last_data"] = time.monotonic()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "lab-paper/1"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                w = r.headers.get("x-mbx-used-weight-1m")
                if w is not None:
                    _weight["used"] = int(w)
                    if int(w) > 1800:
                        time.sleep(15)
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            err = e
            if e.code in (400, 404, 451):
                break
            if e.code in (418, 429):
                delay = max(delay, float(e.headers.get("Retry-After") or 30))
        except (OSError, ValueError) as e:
            err = e
        if attempt < tries - 1:
            time.sleep(delay)
            delay *= 2
    raise LiveError(f"{url}: {err}")


def perpetuals(quote="USDT", statuses=("TRADING",)):
    """USDT-margined perpetuals with the given statuses, crypto and TradFi (commodities, equities): the archive holds
    both. SETTLING = being delisted, still in the archive while it traded."""
    info = get("fapi/v1/exchangeInfo")
    return sorted(s["symbol"] for s in info["symbols"] if s.get("contractType") in ("PERPETUAL", "TRADIFI_PERPETUAL")
                  and s.get("quoteAsset") == quote and s.get("status") in statuses)


def tradfi():
    """Binance USD-M contracts that are not crypto, as R216 defines them: contractType TRADIFI_PERPETUAL or an
    underlyingType other than COIN and PREMARKET (stocks, commodities, indices)."""
    info = get("fapi/v1/exchangeInfo")
    return {s["symbol"] for s in info["symbols"] if s.get("contractType") == "TRADIFI_PERPETUAL"
            or s.get("underlyingType") not in ("COIN", "PREMARKET", None)}


def parse_klines(rows):
    df = pd.DataFrame(rows, columns=KLINE_COLS).drop(columns=["ignore", "close_time"])
    for c in df.columns:
        df[c] = pd.to_numeric(df[c])
    df["t"] = df["t"].astype(np.int64)
    return df


def fetch_klines(symbol, start, end, interval="1h", path="fapi/v1/klines"):
    """Closed and open 1 h bars with open time in [start, end) ms. path="fapi/v1/premiumIndexKlines" gives the
    premium index bars (the archive's premium column is their close)."""
    out, s = [], start
    while s < end:
        limit = int(min(1500, (end - s) // HOUR + 1))     # the request weight grows with the limit asked, not returned
        rows = get(path, {"symbol": symbol, "interval": interval, "startTime": s, "endTime": end - 1, "limit": limit})
        if not rows:
            break
        out.append(parse_klines(rows))
        s = int(rows[-1][0]) + HOUR
        if len(rows) < limit:
            break
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=KLINE_COLS[:6])


def fetch_ratio(endpoint, symbol, start, end):
    """5-minute rows with timestamp in [start, end) ms as a DataFrame (timestamp, value[, oi_value])."""
    out, s = [], start
    while s < end:
        e = min(end, s + 500 * FIVE) - 1
        rows = get(f"futures/data/{endpoint}", {"symbol": symbol, "period": "5m", "limit": 500, "startTime": s,
                                                 "endTime": e})
        if rows:
            out.extend(rows)
        s = e + 1
    if not out:
        return pd.DataFrame(columns=["timestamp", "value"])
    df = pd.DataFrame(out).drop_duplicates("timestamp")
    if endpoint == OI:
        df = pd.DataFrame({"timestamp": df["timestamp"], "oi": pd.to_numeric(df["sumOpenInterest"]),
                           "oi_value": pd.to_numeric(df["sumOpenInterestValue"])})
    else:
        df = pd.DataFrame({"timestamp": df["timestamp"], "value": pd.to_numeric(df[RATIOS[endpoint][1]])})
    df["timestamp"] = df["timestamp"].astype(np.int64)
    return df.sort_values("timestamp").reset_index(drop=True)


# Live timestamp + shift = the archive's create_time for the same row (checked by scripts/live_parity.py on BTCUSDT
# 2026-09-26: snapshots match exactly 5 minutes earlier, taker windows at the same stamp).
ARCHIVE_SHIFTS = {"topLongShortPositionRatio": -FIVE, "globalLongShortAccountRatio": -FIVE,
                  "topLongShortAccountRatio": -FIVE, OI: -FIVE, "takerlongshortRatio": 0}


def hourly_metrics(frames, shifts=None):
    """Reduce 5-minute rows {endpoint: df} to the archive's hourly metrics columns. shifts {endpoint: ms} are added to
    the rows' timestamps first, to put them on the archive's clock (default: none)."""
    shifts = shifts or {}
    cols = []
    for ep, df in frames.items():
        if df is None or df.empty:
            continue
        ts = df["timestamp"].values + int(shifts.get(ep, 0))
        h = (ts // HOUR) * HOUR
        if ep == OI:
            cols.append(df.assign(t=h).groupby("t")[["oi", "oi_value"]].last())
        else:
            cols.append(df.assign(t=h).groupby("t")["value"].mean().rename(RATIOS[ep][0]))
    if not cols:
        return pd.DataFrame(columns=["t"])
    return pd.concat(cols, axis=1).reset_index().rename(columns={"index": "t"})


def _merge_cache(path, new, key):
    if path.exists():
        old = pd.read_parquet(path)
        new = pd.concat([old, new], ignore_index=True)
    new = new.drop_duplicates(key, keep="last").sort_values(key).reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    new.to_parquet(path, index=False)
    return new


def _covered_from(path, first):
    """The earliest time a fetch into this cache started from: rows before the first cached one do not exist (a coin
    listed later), so the cache is complete from there."""
    side = path.with_suffix(".from")
    return min(int(first), int(side.read_text())) if side.exists() else int(first)


def _note_from(path, start):
    side = path.with_suffix(".from")
    if path.exists() and (not side.exists() or int(side.read_text()) > start):
        side.write_text(str(int(start)))


def klines_cached(symbol, start, end, root=None):
    """1 h klines for [start, end), fetching only the hours missing from the cache. The last cached bar is always
    refetched (it may have been open when cached)."""
    path = Path(root or ROOT) / "klines_1h" / f"{symbol}.parquet"
    have = pd.read_parquet(path) if path.exists() else None
    s = start
    if have is not None and len(have) and _covered_from(path, have["t"].min()) <= start:
        s = max(start, int(have["t"].max()))
    new = fetch_klines(symbol, s, end) if s < end else None
    df = have if new is None or new.empty else _merge_cache(path, new, "t")
    _note_from(path, s)
    if df is None:
        return pd.DataFrame(columns=KLINE_COLS[:6])
    return df[(df["t"] >= start) & (df["t"] < end)].reset_index(drop=True)


def ratios_cached(symbol, start, end, endpoints=("topLongShortPositionRatio", "globalLongShortAccountRatio",
                                                 "takerlongshortRatio", OI), root=None):
    """{endpoint: 5-minute rows in [start, end)}, cached per endpoint; refetches from the last cached row on."""
    out = {}
    for ep in endpoints:
        path = Path(root or ROOT) / "ratios_5m" / ep / f"{symbol}.parquet"
        have = pd.read_parquet(path) if path.exists() else None
        s = start
        if have is not None and len(have) and _covered_from(path, have["timestamp"].min()) <= start + FIVE:
            s = max(start, int(have["timestamp"].max()))
        new = fetch_ratio(ep, symbol, s, end) if s < end else None
        df = have if new is None or new.empty else _merge_cache(path, new, "timestamp")
        _note_from(path, s)
        out[ep] = None if df is None else df[(df["timestamp"] >= start) & (df["timestamp"] < end)]
    return out


def spot_usdt():
    """Binance spot USDT pairs trading today, snapshotted daily to data/live/spot/{date}.json."""
    day = time.strftime("%Y-%m-%d", time.gmtime())
    p = ROOT / "spot" / f"{day}.json"
    if not p.exists():
        info = get("api/v3/exchangeInfo", {"permissions": "SPOT"})
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(sorted(x["symbol"] for x in info["symbols"]
                                       if x.get("quoteAsset") == "USDT" and x.get("status") == "TRADING")))
    return set(json.loads(p.read_text()))


def funding_history(symbol, start, end):
    """Funding settlements in [start, end): DataFrame (t = settlement time floored to the hour, rate)."""
    out, s = [], start
    while s < end:
        rows = get("fapi/v1/fundingRate", {"symbol": symbol, "startTime": s, "endTime": end - 1, "limit": 1000})
        if not rows:
            break
        out.extend(rows)
        s = int(rows[-1]["fundingTime"]) + 1
        if len(rows) < 1000:
            break
    if not out:
        return pd.DataFrame(columns=["t", "rate"])
    df = pd.DataFrame(out)
    return pd.DataFrame({"t": (df["fundingTime"].astype(np.int64) // HOUR) * HOUR,
                         "rate": pd.to_numeric(df["fundingRate"])}).drop_duplicates("t", keep="last")


def grid(frames, t, col):
    """Stack per-symbol frames {symbol: df with t, col} onto the hour grid t -> [T, S] float32."""
    syms = list(frames)
    out = np.full((len(t), len(syms)), np.nan, np.float32)
    for j, s in enumerate(syms):
        df = frames[s]
        if df is None or df.empty or col not in df:
            continue
        i = (df["t"].values.astype(np.int64) - t[0]) // HOUR
        ok = (i >= 0) & (i < len(t))
        out[i[ok], j] = df[col].values[ok]
    return out


def liquidity_rank(qvol, close, window=24 * 30):
    """Rank by trailing quote volume as lab/panel.liquidity_rank, on a live grid. The archive panel has rows before a
    listing (filled with 0 there), so its rolling mean is the window sum / window once the grid is long enough;
    the live grid starts recently, so the same sum / window is used here with min_periods=1."""
    qv = pd.DataFrame(np.nan_to_num(qvol)).rolling(window, min_periods=1).sum().values / window
    qv = np.where(np.isnan(close), -np.inf, qv)
    rank = (-qv).argsort(axis=1).argsort(axis=1).astype(np.float32) + 1
    rank[np.isneginf(qv)] = np.nan
    return rank
