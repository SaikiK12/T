"""Hourly snapshot of the live funding rate of every USDT perp on six more venues: Gate, Hyperliquid, OKX, Bitget,
KuCoin and dYdX (MEXC is recorded by record_mexc_ticker.py; Binance and Bybit refuse this container). One public bulk
request per venue (two for Bitget). None of these venues publishes the history of its displayed (next) rate, and OKX
keeps only 3 months of settled rates, so recording is the only way to get a cross-venue, point-in-time funding panel.

Each row is normalized: venue, symbol, base (multiplier prefixes 1000 / 1000000 / k stripped, XBT -> BTC), rate (as
published, per settlement), interval_h, rate_8h (rate x 8 / interval_h), next_ms (next settlement), mark price, open
interest in the venue's units, and the venue's predicted or last-settled rate where it gives one (`alt_rate`).

One file per UTC hour, data/recorders/funding_board/<YYYY-MM-DD>/<HH>.parquet (gitignored); a second run in the same
hour writes nothing. New rows carry the local request start and the venue's response-completion bound; older
files used recv_ms for the start of the whole snapshot and do not provide a receipt bound.
A venue that fails is skipped and named in the log; the others are still written. Data
collection only. `board()` turns a snapshot into the cross-venue spread table shown on the control room.

usage: python scripts/record_funding_board.py
"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402

OUT = data.ROOT / "recorders" / "funding_board"
COLS = ["venue", "symbol", "base", "rate", "interval_h", "rate_8h", "next_ms", "mark", "oi", "alt_rate"]
URLS = {
    "gate": "https://api.gateio.ws/api/v4/futures/usdt/contracts",
    "hyperliquid": "https://api.hyperliquid.xyz/info",
    "okx": "https://www.okx.com/api/v5/public/funding-rate?instId=ANY",
    "okx_mark": "https://www.okx.com/api/v5/public/mark-price?instType=SWAP",
    "bitget": "https://api.bitget.com/api/v2/mix/market/current-fund-rate?productType=usdt-futures",
    "bitget_tickers": "https://api.bitget.com/api/v2/mix/market/tickers?productType=usdt-futures",
    "kucoin": "https://api-futures.kucoin.com/api/v1/contracts/active",
    "dydx": "https://indexer.dydx.trade/v4/perpetualMarkets",
}
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def http(name, body=None):
    req = urllib.request.Request(URLS[name], json.dumps(body).encode() if body else None,
                                 {"Content-Type": "application/json", "User-Agent": "lab/1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def base_of(raw):
    b = raw.upper() if not raw.startswith("k") else raw[1:]
    b = re.sub(r"^(1000000|1000)(?=[A-Z])", "", b)
    return "BTC" if b == "XBT" else b


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def gate(get):
    out = []
    for c in get("gate"):
        if c.get("status") not in (None, "trading") or not c["name"].endswith("_USDT"):
            continue
        h = (c.get("funding_interval") or 28800) / 3600
        out.append(("gate", c["name"], base_of(c["name"][:-5]), f(c.get("funding_rate")), h,
                    int(c["funding_next_apply"]) * 1000 if c.get("funding_next_apply") else None,
                    f(c.get("mark_price")), f(c.get("position_size")), f(c.get("funding_rate_indicative"))))
    return out


def hyperliquid(get):
    meta, ctxs = get("hyperliquid", {"type": "metaAndAssetCtxs"})
    out = []
    for u, c in zip(meta["universe"], ctxs):
        if u.get("isDelisted"):
            continue
        out.append(("hyperliquid", u["name"], base_of(u["name"]), f(c.get("funding")), 1.0, None,
                    f(c.get("markPx")), f(c.get("openInterest")), None))
    return out


def okx(get):
    marks = {m["instId"]: f(m.get("markPx")) for m in get("okx_mark").get("data", [])}
    out = []
    for c in get("okx").get("data", []):
        if not c["instId"].endswith("-USDT-SWAP"):
            continue
        t0, t1 = f(c.get("fundingTime")), f(c.get("nextFundingTime"))
        h = (t1 - t0) / 3_600_000 if t0 and t1 and t1 > t0 else 8.0
        out.append(("okx", c["instId"], base_of(c["instId"].split("-")[0]), f(c.get("fundingRate")), h,
                    int(t0) if t0 else None, marks.get(c["instId"]), None, f(c.get("settFundingRate"))))
    return out


def bitget(get):
    tick = {t["symbol"]: t for t in get("bitget_tickers").get("data", [])}
    out = []
    for c in get("bitget").get("data", []):
        if not c["symbol"].endswith("USDT"):
            continue
        t = tick.get(c["symbol"], {})
        out.append(("bitget", c["symbol"], base_of(c["symbol"][:-4]), f(c.get("fundingRate")),
                    f(c.get("fundingRateInterval")) or 8.0, int(c["nextUpdate"]) if c.get("nextUpdate") else None,
                    f(t.get("markPrice")), f(t.get("holdingAmount")), None))
    return out


def kucoin(get):
    out = []
    for c in get("kucoin").get("data", []):
        if c.get("quoteCurrency") != "USDT" or c.get("expireDate") or c.get("status") != "Open":
            continue
        g = c.get("currentFundingRateGranularity") or c.get("fundingRateGranularity") or 28_800_000
        out.append(("kucoin", c["symbol"], base_of(c["baseCurrency"]), f(c.get("fundingFeeRate")), g / 3_600_000,
                    c.get("nextFundingRateDateTime"), f(c.get("markPrice")), f(c.get("openInterest")),
                    f(c.get("predictedFundingFeeRate"))))
    return out


def dydx(get):
    out = []
    for name, c in get("dydx").get("markets", {}).items():
        if c.get("status") != "ACTIVE":
            continue
        out.append(("dydx", name, base_of(name.split("-")[0]), f(c.get("nextFundingRate")), 1.0, None,
                    f(c.get("oraclePrice")), f(c.get("openInterest")), None))
    return out


VENUES = {"gate": gate, "hyperliquid": hyperliquid, "okx": okx, "bitget": bitget, "kucoin": kucoin, "dydx": dydx}


def wall_ms():
    return time.time_ns() // 1_000_000


def snapshot(get=http, now_ms=None, *, clock_ms=wall_ms):
    """(frame, failed venues). Rows from every venue that answered."""
    start = clock_ms() if now_ms is None else now_ms
    previous = start
    rows, failed = [], []
    for name, parse in VENUES.items():
        venue_start = clock_ms()
        if venue_start < previous:
            raise ValueError("Local wall clock moved backwards during snapshot")
        try:
            venue_rows = parse(get)
        except Exception as e:                     # one venue down must not lose the others' hour
            failed.append(f"{name}: {type(e).__name__}: {str(e)[:120]}")
            venue_rows = []
        recv = clock_ms()
        if recv < venue_start:
            raise ValueError("Local wall clock moved backwards during snapshot")
        rows.extend((start, venue_start, recv, *row) for row in venue_rows)
        previous = recv
    df = pd.DataFrame(rows, columns=["request_start_ms", "venue_start_ms", "recv_ms", "venue", "symbol", "base",
                                     "rate", "interval_h", "next_ms", "mark", "oi", "alt_rate"])
    df["rate_8h"] = df["rate"] * 8 / df["interval_h"]
    df = df[["recv_ms", "request_start_ms", "venue_start_ms", *COLS]]
    return df, failed


def record(get=http, now_ms=None, out=OUT, *, clock_ms=wall_ms):
    now_ms = clock_ms() if now_ms is None else now_ms
    stamp = pd.Timestamp(now_ms, unit="ms", tz="UTC")
    path = Path(out) / stamp.strftime("%Y-%m-%d") / f"{stamp:%H}.parquet"
    if path.exists():
        return path, 0, []
    df, failed = snapshot(get, now_ms, clock_ms=clock_ms)
    if df.empty:
        return path, 0, failed
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    df.to_parquet(tmp, index=False)
    tmp.replace(path)
    return path, len(df), failed


def board(snap, mexc=None, top=None):
    """Cross-venue table, one row per base listed on 2+ venues: each venue's 8h-equivalent rate, the spread (max -
    min), which venues hold the max and the min, and the spread annualized at 3 settlements a day. Descriptive only:
    a spread is not an edge until a frozen lane prices it net of basis moves and costs."""
    frames = [snap[["venue", "base", "rate_8h"]]]
    if mexc is not None and len(mexc):
        m = mexc.dropna(subset=["f_fundingRate"])
        cyc = m["f_collectCycle"].astype(float).where(m["f_collectCycle"].astype(float) > 0, 8.0)
        frames.append(pd.DataFrame({"venue": "mexc", "base": [base_of(s[:-5]) for s in m["symbol"]],
                                    "rate_8h": m["f_fundingRate"].astype(float) * 8 / cyc}))
    long = pd.concat(frames, ignore_index=True).dropna(subset=["rate_8h"])
    long = long.groupby(["base", "venue"], as_index=False)["rate_8h"].mean()
    wide = long.pivot(index="base", columns="venue", values="rate_8h")
    wide = wide[wide.notna().sum(axis=1) >= 2]
    out = pd.DataFrame({"base": wide.index, "venues": wide.notna().sum(axis=1).values,
                        "max_venue": wide.idxmax(axis=1).values, "min_venue": wide.idxmin(axis=1).values,
                        "spread_8h": (wide.max(axis=1) - wide.min(axis=1)).values})
    out["spread_ann"] = out["spread_8h"] * 3 * 365
    out = out.join(wide.reset_index(drop=True).add_prefix("r8h_"))
    out = out.sort_values("spread_8h", ascending=False, ignore_index=True)
    return out.head(top) if top else out


def main():
    path, n, failed = record()
    for msg in failed:
        log("venue failed:", msg)
    log(f"funding board: {n} rows -> {path}" if n else f"funding board: nothing written ({path})")


if __name__ == "__main__":
    main()
