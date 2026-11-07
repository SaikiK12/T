"""Funding and candle history from two more perp venues, public APIs, no keys:

| venue | contracts | funding | candles |
|---|---|---|---|
| kucoin | USDT perps live today (`/api/v1/contracts/active`) | every settlement since listing (8 h, some 4 h / 1 h), 100 per call | daily, 200 per call |
| dydx | every v4 market, settled (delisted) ones included (`/v4/perpetualMarkets`) | hourly since 2023-10, 1,000 per call | daily and hourly with open interest, 1,000 per call |
| lighter | every Lighter perp in `/orderBookDetails` (inactive ones included; equity, index and commodity perps too) | hourly since listing (launch 2025-01-17), 700 h per call | daily and hourly, 480 per call |
| kraken | Kraken Futures linear perps live today (`PF_*`, `/derivatives/api/v3/instruments`) | hourly, the last year only (the API's limit), one call | daily since 2022-03, one call |
| upbit | KRW spot markets live today (`/v1/market/all`) | (spot) | daily, the day ending 00:00 UTC (09:00 KST), 200 per call |
| bithumb | KRW spot markets live today (`/v1/market/all`, Upbit-style API) | (spot) | daily, the day ending 15:00 UTC (00:00 KST), 200 per call |

The two Korean spot venues give each coin's Korean price, for the Korean premium against Binance (KRW per USD from
FRED or Upbit's KRW-USDT, or coin over BTC on the same venue, which needs no exchange rate).

Rows are routed by the reserved-sample rules (docs/GATES.md), as `fetch_gate_history.py` does:
- `open/`: contracts whose base has a Binance perp (R274's `binance_perp` name rule), rows from 2021-01-01;
- `reserved/`: everything else, i.e. 2020 rows and all rows of contracts with no Binance perp. Nothing in the lab
  may read `reserved/` except a frozen batch PREREG that declares RESERVED-VENUE-READ.

Saved in data/<venue>_hist/{open,reserved}/<kind>/<SYMBOL>.parquet with `contracts.csv` (route, Binance perp,
multiplier = Binance price / venue price) and the raw contract list. A contract whose file exists is skipped, so it
resumes. Data collection only.

Lighter allows 60 requests a minute per IP and the hourly book recorder uses most of that, so Lighter requests take the
recorder's lock (scripts/record_lighter_book.py) one at a time: run it with --workers 1 --pause 2.

usage: python scripts/fetch_venue_history.py {kucoin,dydx,kraken,lighter,upbit,bithumb} [--pause 0.15] [--workers 4]
       [--only SYM,SYM]
"""
import argparse
import concurrent.futures
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402
from scripts.record_lighter_book import BASE as LIGHTER, api_lock  # noqa: E402
from scripts.squeeze_events import binance_perp  # noqa: E402

OPEN_FROM_MS = 1_609_459_200_000           # 2021-01-01: earlier rows are the reserved 2020 window
DAY, HOUR = 86_400_000, 3_600_000
KUCOIN = "https://api-futures.kucoin.com"
KRAKEN = "https://futures.kraken.com"
KOREA = {"upbit": "https://api.upbit.com/v1", "bithumb": "https://api.bithumb.com/v1"}
DYDX = "https://indexer.dydx.trade/v4"
ALIASES = {"XBT": "BTC"}                   # KuCoin's name for bitcoin
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def get(url, tries=6):
    delay = 2.0
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8.5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except (OSError, ValueError) as e:
            err = e
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"{url}: {err}")


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def ms(s):
    return int(datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp() * 1000)


# ---- KuCoin ----

def kucoin_contracts():
    raw = get(f"{KUCOIN}/api/v1/contracts/active")["data"]
    rows = [{"symbol": c["symbol"], "base": ALIASES.get(c["baseCurrency"], c["baseCurrency"]),
             "multiplier_contract": c["multiplier"], "listed_ms": c.get("firstOpenDate") or 0,
             "funding_ms": c.get("fundingRateGranularity"), "status": c["status"]}
            for c in raw if c["quoteCurrency"] == "USDT" and c.get("type") == "FFWCSX"]
    return raw, rows


def kucoin_funding(sym, now, pause):
    """Every settlement, paged backwards from now (the API returns the newest 100 in a range)."""
    out, to = [], now
    while True:
        q = urllib.parse.urlencode({"symbol": sym, "from": 0, "to": to})
        d = get(f"{KUCOIN}/api/v1/contract/funding-rates?{q}").get("data") or []
        time.sleep(pause)
        if not d:
            break
        out += d
        first = min(int(x["timepoint"]) for x in d)
        if first >= to or len(d) < 100:
            break
        to = first - 1
    df = pd.DataFrame(out)
    if df.empty:
        return pd.DataFrame({"t": pd.Series(dtype="int64"), "rate": pd.Series(dtype=float)})
    df = df.rename(columns={"timepoint": "t", "fundingRate": "rate"})[["t", "rate"]]
    return df.astype({"t": "int64", "rate": float}).drop_duplicates("t").sort_values("t", ignore_index=True)


def kucoin_candles(sym, start, now, pause):
    """Daily bars (t = open, UTC), paged forwards (the API returns the first 200 from `from`)."""
    out, s = [], start
    while s < now:
        q = urllib.parse.urlencode({"symbol": sym, "granularity": 1440, "from": s, "to": now})
        d = get(f"{KUCOIN}/api/v1/kline/query?{q}").get("data") or []
        time.sleep(pause)
        if not d:
            break
        out += d
        last = int(d[-1][0])
        if last < s or len(d) < 200:
            break
        s = last + DAY
    cols = ["t", "open", "high", "low", "close", "volume", "turnover"]
    df = pd.DataFrame(out, columns=cols)
    df = df[df.t + DAY <= now]                     # finished bars only
    return df.astype({"t": "int64", **{c: float for c in cols[1:]}}).drop_duplicates("t").sort_values(
        "t", ignore_index=True)


# ---- dYdX v4 ----

def dydx_contracts():
    raw = get(f"{DYDX}/perpetualMarkets")["markets"]
    rows = [{"symbol": t, "base": t.rsplit("-", 1)[0], "multiplier_contract": 1, "listed_ms": 0, "funding_ms": HOUR,
             "status": m["status"]} for t, m in sorted(raw.items())]
    return raw, rows


def dydx_paged(path, key, field, now, pause, **params):
    """Rows newest first, paged backwards with the `before` field the endpoint takes."""
    out, before = [], iso(now)
    while True:
        q = urllib.parse.urlencode({**params, "limit": 1000, field: before})
        d = get(f"{DYDX}/{path}?{q}").get(key) or []
        time.sleep(pause)
        if not d:
            break
        out += d
        first = d[-1]["effectiveAt" if key == "historicalFunding" else "startedAt"]
        if len(d) < 1000:
            break
        before = iso(ms(first) - 1000)
    return out


def dydx_funding(sym, now, pause):
    d = dydx_paged(f"historicalFunding/{sym}", "historicalFunding", "effectiveBeforeOrAt", now, pause)
    df = pd.DataFrame({"t": [ms(x["effectiveAt"]) for x in d], "rate": [float(x["rate"]) for x in d],
                       "oracle": [float(x["price"]) for x in d]})
    return df.astype({"t": "int64"}).drop_duplicates("t").sort_values("t", ignore_index=True)


def dydx_candles(sym, res, now, pause):
    d = dydx_paged(f"candles/perpetualMarkets/{sym}", "candles", "toISO", now, pause, resolution=res)
    df = pd.DataFrame({"t": [ms(x["startedAt"]) for x in d],
                       **{c: [float(x[c]) for x in d] for c in ("open", "high", "low", "close")},
                       "volume": [float(x["baseTokenVolume"]) for x in d],
                       "usd_volume": [float(x["usdVolume"]) for x in d],
                       "trades": [int(x["trades"]) for x in d],
                       "open_interest": [float(x["startingOpenInterest"]) for x in d]})
    df = df[df.t + (DAY if res == "1DAY" else HOUR) <= now]      # finished bars only
    return df.astype({"t": "int64"}).drop_duplicates("t").sort_values("t", ignore_index=True)


# ---- Kraken Futures ----

def kraken_contracts():
    raw = [i for i in get(f"{KRAKEN}/derivatives/api/v3/instruments")["instruments"]
           if i.get("type") == "flexible_futures" and i["symbol"].startswith("PF_")]
    rows = []
    for i in raw:
        base = i["symbol"][3:].rsplit("USD", 1)[0]
        rows.append({"symbol": i["symbol"], "base": ALIASES.get(base, base), "multiplier_contract": i.get("contractSize"),
                     "listed_ms": ms(i["openingDate"]) if i.get("openingDate") else 0, "funding_ms": HOUR,
                     "status": "tradeable" if i.get("tradeable") else "halted"})
    return raw, rows


def kraken_funding(sym, now, pause):
    """Hourly relative funding rate (a fraction of notional per hour, as the venue settles it)."""
    d = get(f"{KRAKEN}/derivatives/api/v4/historicalfundingrates?symbol={sym}").get("rates") or []
    time.sleep(pause)
    df = pd.DataFrame({"t": [ms(x["timestamp"]) for x in d], "rate": [float(x["relativeFundingRate"]) for x in d],
                       "rate_usd": [float(x["fundingRate"]) for x in d]})
    return df[df.t <= now].astype({"t": "int64"}).drop_duplicates("t").sort_values("t", ignore_index=True)


def kraken_candles(sym, start, now, pause):
    d = get(f"{KRAKEN}/api/charts/v1/trade/{sym}/1d?from={start // 1000}").get("candles") or []
    time.sleep(pause)
    df = pd.DataFrame({"t": [int(x["time"]) for x in d],
                       **{c: [float(x[c]) for x in d] for c in ("open", "high", "low", "close", "volume")}})
    df = df[df.t + DAY <= now]                     # finished bars only
    return df.astype({"t": "int64"}).drop_duplicates("t").sort_values("t", ignore_index=True)


# ---- Upbit / Bithumb (same API shape) ----

def korea_contracts(venue):
    raw = get(f"{KOREA[venue]}/market/all")
    rows = [{"symbol": m["market"], "base": m["market"].split("-", 1)[1], "multiplier_contract": 1, "listed_ms": 0,
             "funding_ms": "", "status": "live"} for m in raw if m["market"].startswith("KRW-")]
    return raw, rows


def korea_candles(venue, market, now, pause):
    """Daily bars (t = open, UTC), paged backwards with `to` (the API returns the newest 200 before it)."""
    out, to = [], iso(now)
    while True:
        q = urllib.parse.urlencode({"market": market, "count": 200, "to": to[:19]})
        d = get(f"{KOREA[venue]}/candles/days?{q}")
        time.sleep(pause)
        if not isinstance(d, list) or not d:
            break
        out += d
        first = ms(d[-1]["candle_date_time_utc"])
        if len(d) < 200:
            break
        to = iso(first)
    df = pd.DataFrame({"t": [ms(x["candle_date_time_utc"]) for x in out],
                       **{c: [float(x[k]) for x in out] for c, k in (("open", "opening_price"), ("high", "high_price"),
                                                                      ("low", "low_price"), ("close", "trade_price"),
                                                                      ("volume", "candle_acc_trade_volume"),
                                                                      ("turnover_krw", "candle_acc_trade_price"))}})
    df = df[df.t + DAY <= now]                     # finished bars only
    return df.astype({"t": "int64"}).drop_duplicates("t").sort_values("t", ignore_index=True)


# ---- Lighter (zero-fee perp DEX, docs/VENUE_STRUCTURE.md) ----

LIGHTER_START_MS = 1_735_689_600_000       # 2025-01-01, before Lighter's first market
_lighter_listed = {}


def lighter_get(path, **params):
    with api_lock():
        return get(f"{LIGHTER}/{path}?{urllib.parse.urlencode(params)}")


def lighter_contracts():
    raw = lighter_get("orderBookDetails", filter="perp")["order_book_details"]
    rows = [{"symbol": d["symbol"], "base": d["symbol"], "market_id": int(d["market_id"]), "multiplier_contract": 1,
             "listed_ms": 0, "funding_ms": HOUR, "status": d.get("status")} for d in raw]
    return raw, rows


def lighter_windows(mid, step, now, pause):
    """[start, stop) windows of `step` ms from the market's first daily candle (looked up once) to now."""
    if mid not in _lighter_listed:
        first = [c["t"] for c in lighter_candle_rows(mid, "1d", LIGHTER_START_MS, now, 480 * DAY, pause)[:1]]
        _lighter_listed[mid] = first[0] if first else now
    t = _lighter_listed[mid]
    while t < now:
        yield t, min(t + step, now)
        t += step


def lighter_candle_rows(mid, res, start, now, step, pause):
    out, t = [], start
    while t < now:
        stop = min(t + step, now)
        out += lighter_get("candles", market_id=mid, resolution=res, start_timestamp=t, end_timestamp=stop,
                           count_back=0).get("c") or []
        time.sleep(pause)
        t = stop
    return out


def lighter_candles(mid, res, now, pause):
    """Finished bars; `V` is quote volume, `i` the last trade id Lighter reports for the bar."""
    size = DAY if res == "1d" else HOUR
    rows = [r for a, b in lighter_windows(mid, 480 * size, now, pause)
            for r in lighter_candle_rows(mid, res, a, b, 480 * size, pause)]
    df = pd.DataFrame({"t": [int(r["t"]) for r in rows],
                       **{k: [float(r.get(c, 0.0)) for r in rows] for k, c in (("open", "o"), ("high", "h"),
                                                                                ("low", "l"), ("close", "c"),
                                                                                ("volume", "v"),
                                                                                ("quote_volume", "V"))}})
    df = df[df.t + size <= now]
    return df.astype({"t": "int64"}).drop_duplicates("t").sort_values("t", ignore_index=True)


def lighter_funding(mid, now, pause):
    """Hourly settlements. The API gives an unsigned percent `rate` and the `direction`; Lighter's docs say longs pay
    when the rate is positive, so `rate` here is +rate/100 when direction is 'long' and -rate/100 otherwise (an
    interpretation, kept with the raw fields). `value` is the payment per unit of base, about rate x mark price."""
    rows = []
    for a, b in lighter_windows(mid, 700 * HOUR, now, pause):
        rows += lighter_get("fundings", market_id=mid, resolution="1h", start_timestamp=a // 1000,
                            end_timestamp=b // 1000, count_back=0).get("fundings") or []
        time.sleep(pause)
    df = pd.DataFrame({"t": [int(r["timestamp"]) * 1000 for r in rows],
                       "rate_pct": [float(r["rate"]) for r in rows], "value": [float(r["value"]) for r in rows],
                       "direction": [r["direction"] for r in rows]})
    df["rate"] = df.rate_pct.where(df.direction == "long", -df.rate_pct) / 100
    return df.astype({"t": "int64"}).drop_duplicates("t").sort_values("t", ignore_index=True)


VENUES = {
    "kucoin": (kucoin_contracts, lambda c, now, p: {
        "funding": lambda: kucoin_funding(c["symbol"], now, p),
        "candles_1d": lambda: kucoin_candles(c["symbol"], max(c["listed_ms"] - DAY, 0) // DAY * DAY, now, p)}),
    "dydx": (dydx_contracts, lambda c, now, p: {
        "funding": lambda: dydx_funding(c["symbol"], now, p),
        "candles_1d": lambda: dydx_candles(c["symbol"], "1DAY", now, p),
        "candles_1h": lambda: dydx_candles(c["symbol"], "1HOUR", now, p)}),
    "lighter": (lighter_contracts, lambda c, now, p: {
        "candles_1d": lambda: lighter_candles(c["market_id"], "1d", now, p),
        "candles_1h": lambda: lighter_candles(c["market_id"], "1h", now, p),
        "funding": lambda: lighter_funding(c["market_id"], now, p)}),
    "kraken": (kraken_contracts, lambda c, now, p: {
        "funding": lambda: kraken_funding(c["symbol"], now, p),
        "candles_1d": lambda: kraken_candles(c["symbol"], max(c["listed_ms"] - DAY, 0) // DAY * DAY, now, p)}),
    **{v: (lambda v=v: korea_contracts(v), lambda c, now, p, v=v: {
        "candles_1d": lambda: korea_candles(v, c["symbol"], now, p)}) for v in KOREA},
}


def route(base, perps):
    """('open', Binance perp, multiplier) when the base has a Binance perp, else ('reserved', '', '')."""
    hit = binance_perp(base, perps)
    return ("open", hit[0], hit[1]) if hit else ("reserved", "", "")


def save(out, kind, sym, dest, df):
    """Write the open part (2021+) or the whole frame to reserved/; 2020 rows of an open contract go to reserved/."""
    parts = {"reserved": df} if dest == "reserved" else {"open": df[df.t >= OPEN_FROM_MS],
                                                         "reserved": df[df.t < OPEN_FROM_MS]}
    for where, part in parts.items():
        if where == dest or len(part):
            p = out / where / kind / f"{sym}.parquet"
            p.parent.mkdir(parents=True, exist_ok=True)
            part.to_parquet(p, index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("venue", choices=sorted(VENUES))
    ap.add_argument("--pause", type=float, default=0.15)
    ap.add_argument("--only", default="")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    out = data.ROOT / f"{a.venue}_hist"
    contracts, kinds = VENUES[a.venue]
    now = int(time.time() * 1000) // HOUR * HOUR
    raw, rows = contracts()
    (out / "raw").mkdir(parents=True, exist_ok=True)
    (out / "raw" / "contracts.json").write_text(json.dumps(raw, indent=1, sort_keys=True))
    perps = {p.stem for p in (data.ROOT / "klines_1h").glob("*.parquet")}
    only = set(filter(None, a.only.split(",")))
    for r in rows:
        r["route"], r["binance_perp"], r["multiplier"] = route(r["base"], perps)
    rows = [r for r in rows if not only or r["symbol"] in only]
    log(f"{a.venue}: {len(rows)} contracts, {sum(r['route'] == 'open' for r in rows)} with a Binance perp")

    def one(r):
        sym, st = r["symbol"], {}
        for kind, fn in kinds(r, now, a.pause).items():
            if (out / r["route"] / kind / f"{sym}.parquet").exists():
                st[kind] = "skip"
                continue
            try:
                df = fn()
            except RuntimeError as e:
                st[kind] = f"error {e}"
                continue
            save(out, kind, sym, r["route"], df)
            st[kind] = len(df)
        return sym, st

    status = {}
    with concurrent.futures.ThreadPoolExecutor(a.workers) as ex:
        for i, (sym, st) in enumerate(ex.map(one, rows), 1):
            status[sym] = st
            if i % 25 == 0 or i == len(rows):
                log(f"{i}/{len(rows)} {sym}: {st}")
    if not only:
        pd.DataFrame(rows).to_csv(out / "contracts.csv", index=False)
        (out / "reserved" / "README.md").parent.mkdir(parents=True, exist_ok=True)
        (out / "reserved" / "README.md").write_text(
            "Reserved sample (docs/GATES.md). Do not read: only a frozen batch PREREG declaring RESERVED-VENUE-READ "
            "may.\n")
        (out / "manifest.json").write_text(json.dumps({
            "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "until_ms": now,
            "errors": {s: v for s, st in status.items() for k, v in st.items() if str(v).startswith("error")},
            "contracts": status}, indent=1))
    log("done")


if __name__ == "__main__":
    main()
