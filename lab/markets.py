"""Daily bars for markets beyond crypto perps (indices, index futures, forex, commodities, rates, volatility), from
Yahoo Finance's public chart endpoint, cached under data/markets/yahoo/. Small: one request per symbol, a few MB in
all. Prices are the venue's daily bars in its own time zone; `adjclose` includes dividends and splits where Yahoo has
them. Yahoo keeps only symbols that trade today, so a stock universe built from it is survivorship-biased: use it
for indices, futures and forex, not for single-stock cross-sections.
"""
import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

from . import data

ROOT = data.ROOT / "markets" / "yahoo"
URL = "https://query2.finance.yahoo.com/v8/finance/chart/{sym}?period1={a}&period2={b}&interval=1d&events=div%2Csplit"
UNIVERSE = {
    "us_index": ["^NDX", "^GSPC", "^DJI", "^RUT", "QQQ", "SPY", "IWM", "DIA"],
    "index_future": ["NQ=F", "ES=F", "YM=F", "RTY=F"],
    "forex": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X", "NZDUSD=X", "EURJPY=X",
              "GBPJPY=X", "EURGBP=X", "AUDJPY=X", "USDMXN=X", "USDZAR=X", "USDTRY=X"],
    "commodity": ["GC=F", "SI=F", "CL=F", "NG=F", "HG=F", "ZC=F", "ZW=F"],
    "rates": ["ZN=F", "ZB=F", "^TNX", "^IRX"],
    "volatility": ["^VIX", "^VXN", "^VIX3M", "SVXY", "VXX"],
    "dollar": ["DX-Y.NYB"],
    "crypto_spot": ["BTC-USD", "ETH-USD"],
}


class MarketError(RuntimeError):
    pass


def parse(payload):
    """Yahoo chart JSON -> DataFrame indexed by the bar's UTC timestamp, columns open/high/low/close/adjclose/volume."""
    res = (payload.get("chart") or {}).get("result")
    if not res:
        raise MarketError(f"no result: {(payload.get('chart') or {}).get('error')}")
    r = res[0]
    ts = r.get("timestamp") or []
    q = r["indicators"]["quote"][0]
    df = pd.DataFrame({k: q.get(k) for k in ("open", "high", "low", "close", "volume")},
                      index=pd.to_datetime(ts, unit="s", utc=True))
    adj = r["indicators"].get("adjclose")
    df["adjclose"] = adj[0]["adjclose"] if adj else df["close"]
    df.index.name = "t"
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df.attrs.update(symbol=r["meta"].get("symbol"), currency=r["meta"].get("currency"),
                    tz=r["meta"].get("exchangeTimezoneName"))
    return df.dropna(subset=["close"])


def fetch(sym, start="2000-01-01", end=None, refresh=False, pause=1.5):
    """Daily bars for one symbol, from the cache unless refresh."""
    p = ROOT / f"{sym.replace('^', '_').replace('=', '_')}.parquet"
    if p.exists() and not refresh:
        return pd.read_parquet(p)
    a = int(pd.Timestamp(start, tz="UTC").timestamp())
    b = int((pd.Timestamp(end, tz="UTC") if end else pd.Timestamp.now(tz="UTC")).timestamp())
    req = urllib.request.Request(URL.format(sym=urllib.request.quote(sym), a=a, b=b),
                                 headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                df = parse(json.loads(r.read()))
            break
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 3:
                raise MarketError(f"{sym}: HTTP {e.code}") from e
            time.sleep(pause * 2 ** (attempt + 1))
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(p)
    time.sleep(pause)
    return df


def fetch_all(groups=None, **kw):
    """{symbol: DataFrame} for the named groups of UNIVERSE (all by default); failures are reported, not raised."""
    out, failed = {}, {}
    for g in groups or UNIVERSE:
        for s in UNIVERSE[g]:
            try:
                out[s] = fetch(s, **kw)
            except MarketError as e:
                failed[s] = str(e)
    return out, failed
