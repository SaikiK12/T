"""Public MEXC USDT-M futures data (no keys, no orders): contract metadata, hourly klines, funding settlements, and the
map from Binance USD-M symbols to MEXC crypto contracts. Cached under data/mexc/.

Klines are keyed by open time (seconds in the API, ms here) like Binance's, so close[t] is the price at t + 1 h. A kline
request returns at most 2000 bars; a longer range comes back truncated to its last 2000, so ranges are paged forward.
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from lab import data

BASE = "https://contract.mexc.com/api/v1/contract"
HOUR = 3_600_000
ROOT = data.ROOT / "mexc"
ALIAS = {"FIL": "FILECOIN", "PUMP": "PUMPFUN", "TRUMP": "TRUMPOFFICIAL"}     # Binance base -> MEXC base
PREFIXES = ("1000000", "1000")


class MexcError(RuntimeError):
    pass


def get(path, params=None, tries=5, timeout=30):
    url = f"{BASE}/{path}" + ("?" + urllib.parse.urlencode(params) if params else "")
    delay, err = 1.0, None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "lab-paper/1"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = json.loads(r.read())
            if not body.get("success", False):
                raise MexcError(f"{path}: {body.get('code')} {body.get('message')}")
            return body["data"]
        except MexcError:
            raise
        except Exception as e:             # network errors and 5xx: back off and retry
            err = e
            time.sleep(delay)
            delay *= 2
    raise MexcError(f"{path}: {err}")


def contracts(refresh=False):
    """USDT-settled perpetual contracts: DataFrame with symbol, base, type (1 crypto, 2 stock/TradFi), contract size,
    fee rates and state. Snapshotted daily to data/mexc/contracts/{date}.json."""
    day = time.strftime("%Y-%m-%d", time.gmtime())
    p = ROOT / "contracts" / f"{day}.json"
    if refresh or not p.exists():
        rows = get("detail")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rows))
    rows = json.loads(p.read_text())
    df = pd.DataFrame([{"symbol": r["symbol"], "base": r.get("baseCoin"), "type": r.get("type"),
                        "contract_size": r.get("contractSize"), "taker": r.get("takerFeeRate"),
                        "maker": r.get("makerFeeRate"), "state": r.get("state"), "settle": r.get("settleCoin")}
                       for r in rows])
    return df[df.settle == "USDT"].reset_index(drop=True)


def map_symbols(binance_symbols, table):
    """{binance symbol: MEXC crypto contract or None}. Only type-1 (crypto) USDT contracts are matched."""
    crypto = set(table.symbol[table.type == 1])
    out = {}
    for s in binance_symbols:
        base = s[:-4] if s.endswith("USDT") else s
        cands = [base] + [base[len(p):] for p in PREFIXES if base.startswith(p)]
        cands += [ALIAS[c] for c in cands if c in ALIAS]
        out[s] = next((c + "_USDT" for c in cands if c + "_USDT" in crypto), None)
    return out


def require_unique_mapping(mapping):
    """Reject two source contracts mapped onto the same venue instrument.

    The source signals cannot be treated as independent positions or basket
    members until an explicit lineage/aggregation rule has been registered.
    """
    reverse = {}
    for source, target in mapping.items():
        if target is not None:
            reverse.setdefault(target, []).append(source)
    collisions = {target: sorted(sources) for target, sources in reverse.items() if len(sources) > 1}
    if collisions:
        detail = "; ".join(f"{target}: {', '.join(sources)}" for target, sources in sorted(collisions.items()))
        raise MexcError(f"ambiguous source-to-MEXC contract mapping ({detail})")


def fetch_klines(symbol, start, end, kind=""):
    """Hourly bars with open time in [start, end) (ms): DataFrame t, open, high, low, close, vol, amount. kind
    "index_price" gives the index price bars instead of the contract's last price."""
    out, s = [], start
    while s < end:
        e = min(end, s + 2000 * HOUR)
        d = get(f"kline/{kind + '/' if kind else ''}{symbol}", {"interval": "Min60", "start": s // 1000,
                                                                "end": (e - HOUR) // 1000})
        if d and d.get("time"):
            out.append(pd.DataFrame({"t": np.asarray(d["time"], np.int64) * 1000,
                                     **{k: np.asarray(d[k], np.float64)
                                        for k in ("open", "high", "low", "close", "vol", "amount")}}))
        s = e
    if not out:
        return pd.DataFrame(columns=["t", "open", "high", "low", "close", "vol", "amount"])
    df = pd.concat(out).drop_duplicates("t", keep="last").sort_values("t")
    return df[(df.t >= start) & (df.t < end)].reset_index(drop=True)


def klines_cached(symbol, start, end, kind=""):
    """As fetch_klines, refetching from the last cached bar (it may have been open when cached)."""
    p = ROOT / (f"{kind}_1h" if kind else "klines_1h") / f"{symbol}.parquet"
    have = pd.read_parquet(p) if p.exists() else None
    s = start
    if have is not None and len(have) and int(have.t.min()) <= start:
        s = max(start, int(have.t.max()))
    new = fetch_klines(symbol, s, end, kind) if s < end else None
    if new is not None and len(new):
        df = new if have is None else pd.concat([have, new]).drop_duplicates("t", keep="last").sort_values("t")
        p.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(p, index=False)
        have = df
    if have is None:
        return pd.DataFrame(columns=["t", "close"])
    return have[(have.t >= start) & (have.t < end)].reset_index(drop=True)


def funding_history(symbol, start, end):
    """Settled funding in [start, end): DataFrame t (settlement time floored to the hour, ms), rate, cycle_h."""
    out, page = [], 1
    while True:
        d = get("funding_rate/history", {"symbol": symbol, "page_num": page, "page_size": 1000})
        rows = d.get("resultList") or []
        out += rows
        if not rows or page >= int(d.get("totalPage", 1)) or int(rows[-1]["settleTime"]) < start:
            break
        page += 1
    if not out:
        return pd.DataFrame(columns=["t", "rate", "cycle_h"])
    df = pd.DataFrame({"t": np.asarray([r["settleTime"] for r in out], np.int64) // HOUR * HOUR,
                       "rate": [float(r["fundingRate"]) for r in out],
                       "cycle_h": [r.get("collectCycle") for r in out]})
    return df[(df.t >= start) & (df.t < end)].drop_duplicates("t").sort_values("t").reset_index(drop=True)


def spot_usdt():
    """MEXC spot USDT pairs open for trading today {symbol: taker fee}, snapshotted daily to data/mexc/spot/{date}.json.
    The spot API lives on its own host."""
    day = time.strftime("%Y-%m-%d", time.gmtime())
    p = ROOT / "spot" / f"{day}.json"
    if not p.exists():
        req = urllib.request.Request("https://api.mexc.com/api/v3/exchangeInfo", headers={"User-Agent": "lab-paper/1"})
        with urllib.request.urlopen(req, timeout=60) as r:
            rows = json.loads(r.read())["symbols"]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({x["symbol"]: float(x.get("takerCommission") or "nan") for x in rows
                                 if x.get("quoteAsset") == "USDT" and x.get("status") == "1"
                                 and x.get("isSpotTradingAllowed")}))
    return json.loads(p.read_text())
