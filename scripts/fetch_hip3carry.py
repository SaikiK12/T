"""Inputs for R479 hip3carry_fwd (forward reads of R475-R477's funding carry). Keyless, public, run inside each read.

stocks/ - every HIP-3 dex in Hyperliquid's perpDexs (xyz, Paragon, EntropyIO and any other at fetch time), delisted
          markets included. A market stays if Yahoo's chart metadata calls its ticker an EQUITY quoted in USD on a US
          exchange (R475's filter, `fetch_hip3stock.US`). For each (names <DEX>_<TICKER>):
          xyz/<DEX>_<TICKER>_funding.csv - hourly funding (R475's `fetch_hip3stock.funding`), from `fund_from`;
          xyz/<DEX>_<TICKER>_1h.csv     - 1-hour candles (the venue keeps the latest 5,000), from `candle_from`;
          yahoo/<TICKER>.json and .parquet (date, close, adjclose) once per stock, plus IRX (^IRX).
          universe.csv: coin, ticker, dex, stock, equity, delisted, growth, fee_scale, max_lev, y_type, y_exchange.
twin/   - R477's pairs and layout, by R477's frozen fetcher (`fetch_xyztwin.fetch`, from `twin_from`).
<out>/manifest.json lists every file's sha256 (twin/ keeps its own manifest too). Paced, retried on HTTP 429.

usage: python scripts/fetch_hip3carry.py --end 2027-02-13 --out data/hip3carry_fwd/futility
"""
import argparse
import hashlib
import http.client
import json
import sys
import time
import urllib.error
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_hip3stock as fs  # noqa: E402  (frozen in R475)
import fetch_xyztwin as fx  # noqa: E402  (frozen in R477)
from fetch_cryptomon import CHART, epoch, parse_chart  # noqa: E402  (frozen in R471)

FUND_FROM, CANDLE_FROM, YAHOO_FROM, TWIN_FROM = "2026-10-12", "2026-10-01", "2026-07-01", "2026-08-01"
COLS = ["open_ms", "open", "high", "low", "close", "volume"]
TRIES, WAIT_S = 5, 15


def retry(fn, *args, tries=TRIES, wait=WAIT_S):
    """Call fn again, same client and request, after a dropped connection or a server error (5xx); R475's client
    already waits out HTTP 429 and returns None on 404. A whole call is repeated, so a paged fetch restarts."""
    for k in range(tries):
        try:
            return fn(*args)
        except urllib.error.HTTPError as e:
            if e.code < 500 or k == tries - 1:
                raise
        except (urllib.error.URLError, http.client.HTTPException, ConnectionError, TimeoutError) as e:
            if k == tries - 1:
                raise
            print(f"retry {k + 1}/{tries - 1} after {type(e).__name__}: {e}", flush=True)
        time.sleep(wait * (k + 1))


def candles_1h(coin, start_ms, end_ms):
    """1-hour candles in [start, end), paged like R475's 4-hour fetcher."""
    rows, t = [], start_ms
    while t < end_ms:
        page = fs.post({"type": "candleSnapshot", "req": {"coin": coin, "interval": "1h", "startTime": t,
                                                          "endTime": end_ms}}) or []
        rows += page
        if len(page) < 5000:
            break
        t = int(page[-1]["t"]) + 1
        time.sleep(1.5)
    df = pd.DataFrame(rows)
    if not len(df):
        return pd.DataFrame(columns=COLS)
    df = df.rename(columns={"t": "open_ms", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
    return df[COLS].drop_duplicates("open_ms").sort_values("open_ms")


def universe():
    """Every market of every HIP-3 dex, with R475's equity filter from Yahoo's metadata (cached per ticker)."""
    dexes = [d["name"] for d in retry(fs.post, {"type": "perpDexs"}) if d]
    seen, rows = {}, []
    for dex in dexes:
        time.sleep(1.5)
        for u in retry(fs.post, {"type": "meta", "dex": dex})["universe"]:
            stock = u["name"].split(":", 1)[1]
            if stock not in seen:
                seen[stock] = retry(fs.yahoo_meta, stock)
                time.sleep(1.0)
            m = seen[stock]
            ok = m.get("instrumentType") == "EQUITY" and m.get("currency") == "USD" and m.get("exchangeName") in fs.US
            rows.append({"coin": u["name"], "ticker": f"{dex}_{stock}", "dex": dex, "stock": stock, "equity": int(ok),
                         "delisted": int(bool(u.get("isDelisted"))), "growth": u.get("growthMode") or "",
                         "fee_scale": u.get("deployerFeeScale") if u.get("deployerFeeScale") not in (None, "") else 1.0,
                         "max_lev": u.get("maxLeverage"), "y_type": m.get("instrumentType") or "",
                         "y_exchange": m.get("exchangeName") or ""})
    return pd.DataFrame(rows)


def yahoo(sym, start, end, out, name):
    raw = retry(fs.request, CHART.format(t=sym, a=epoch(start), b=epoch(end)))
    (out / f"{name}.json").write_bytes(raw)
    parse_chart(json.loads(raw))[["date", "close", "adjclose"]].to_parquet(out / f"{name}.parquet", index=False)
    time.sleep(2)


def fetch(end, out, uni=None):
    out = Path(out)
    st = out / "stocks"
    for sub in ("xyz", "yahoo"):
        (st / sub).mkdir(parents=True, exist_ok=True)
    man = {"source": "api.hyperliquid.xyz/info (perpDexs, meta, fundingHistory, candleSnapshot 1h and 4h; every HIP-3 "
                     "dex) and query1.finance.yahoo.com/v8/finance/chart (public, no key)",
           "end": end, "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": {}}
    uni = universe() if uni is None else uni
    b = fs.ms(end)
    for _, r in uni[uni["equity"] == 1].iterrows():
        retry(fs.funding, r["coin"], fs.ms(FUND_FROM), b).to_csv(st / "xyz" / f"{r['ticker']}_funding.csv", index=False)
        time.sleep(1.5)
        retry(candles_1h, r["coin"], fs.ms(CANDLE_FROM), b).to_csv(st / "xyz" / f"{r['ticker']}_1h.csv", index=False)
        time.sleep(1.5)
    for stock in sorted(set(uni.loc[uni["equity"] == 1, "stock"])):
        yahoo(stock, YAHOO_FROM, end, st / "yahoo", stock)
    yahoo("%5EIRX", YAHOO_FROM, end, st / "yahoo", "IRX")
    uni.to_csv(st / "universe.csv", index=False)
    retry(fx.fetch, TWIN_FROM, end, out / "twin")
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.relative_to(out) != Path("manifest.json"):
            man["files"][str(p.relative_to(out))] = {"sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print("stock listings", int(uni["equity"].sum()), "files", len(man["files"]), flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    fetch(a.end, a.out)


if __name__ == "__main__":
    main()
