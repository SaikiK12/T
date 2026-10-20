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


def funding_history(symbol, start, end, *, max_pages=1000):
    """Settled funding in [start, end), preserving the legacy hourly timestamp convention.

    Validate public pagination rather than silently treating missing metadata or stalled pages as complete history.
    Documentation: https://mexcdevelop.github.io/apidocs/contract_v1_en/#get-contract-funding-rate-history
    Valid page retrieval does not prove all expected settlements exist. No cache is read or rewritten here.
    """
    if isinstance(max_pages, bool) or not isinstance(max_pages, int) or max_pages < 1:
        raise ValueError("max_pages must be a positive integer")
    empty = lambda: pd.DataFrame(columns=["t", "rate", "cycle_h"])
    if start >= end:
        return empty()
    out, page, seen, oldest = [], 1, {}, None
    while True:
        if page > max_pages:
            raise MexcError(f"{symbol}: funding pagination exceeded max_pages={max_pages}")
        d = get("funding_rate/history", {"symbol": symbol, "page_num": page, "page_size": 1000})
        try:
            if not isinstance(d, dict) or not isinstance(d.get("resultList"), list):
                raise ValueError("missing resultList")
            # Require the documented page identity; do not default missing metadata to a one-page history.
            current, total = d["currentPage"], d["totalPage"]
            if any(isinstance(v, bool) or str(v) != str(int(v)) for v in (current, total)):
                raise ValueError("non-integer pagination")
            current, total = int(current), int(total)
            rows = d["resultList"]
            if current != page or total < 0 or (rows and total < page):
                raise ValueError("inconsistent page identity")
            if not rows:
                if page != 1 or total > 1:
                    raise ValueError("empty page contradicts pagination")
                break
            times, new = [], []
            for row in rows:
                if row.get("symbol", symbol) != symbol:
                    raise ValueError("settlement symbol mismatch")
                raw_t = row["settleTime"]
                if isinstance(raw_t, bool) or str(raw_t) != str(int(raw_t)) or int(raw_t) < 0:
                    raise ValueError("invalid settlement timestamp")
                t, rate, cycle = int(raw_t), float(row["fundingRate"]), row.get("collectCycle")
                if isinstance(row["fundingRate"], bool) or not np.isfinite(rate):
                    raise ValueError("nonfinite funding rate")
                if cycle is not None and (isinstance(cycle, bool) or not np.isfinite(float(cycle)) or float(cycle) <= 0):
                    raise ValueError("invalid settlement cycle")
                value = (rate, cycle)
                if t in seen:
                    if seen[t] != value:
                        raise ValueError("conflicting duplicate settlement")
                else:
                    if oldest is not None and t > oldest:
                        raise ValueError("page moves forward in time")
                    seen[t] = value
                    new.append(row)
                times.append(t)
            if any(a < b for a, b in zip(times, times[1:])):
                raise ValueError("settlements not in descending time order")
            if not new:
                raise ValueError("pagination repeated without progress")
        except (KeyError, TypeError, ValueError, AttributeError, OverflowError) as e:
            raise MexcError(f"{symbol}: invalid funding page {page}: {e}") from e
        out += new
        oldest = min(times)
        if page == total or oldest < start:
            break
        page += 1
    if not out:
        return empty()
    df = pd.DataFrame({"t": np.asarray([r["settleTime"] for r in out], np.int64) // HOUR * HOUR,
                       "rate": [float(r["fundingRate"]) for r in out],
                       "cycle_h": [r.get("collectCycle") for r in out]})
    if df.t.duplicated().any():
        raise MexcError(f"{symbol}: distinct settlements collapse into the same legacy hourly timestamp")
    return df[(df.t >= start) & (df.t < end)].sort_values("t").reset_index(drop=True)


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
