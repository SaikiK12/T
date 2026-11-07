"""Every Deribit BTC and ETH option trade, from Deribit's public history server, reduced to signed hourly flow per
option plus every block trade kept whole (docs/AUCTION_AND_FLOW.md).

Why: open interest says how many options exist, not who holds them, so dealer gamma (M300) has had to assume a sign.
Each Deribit trade carries `direction`, the taker's side. Summed over an option's life, taker buys minus taker sells
is the takers' net position in it, and the makers hold the opposite. If makers are mostly dealers and takers mostly
customers (the usual reading, not a fact), that is an estimate of dealer positioning by strike, from the data. Block
trades (`block_trade_id`) are negotiated off the order book and printed afterwards, the closest crypto thing to a
dark-pool print.

Source: https://history.deribit.com/api/v2/public/get_last_trades_by_currency_and_time (no key; checked 2026-10-21:
trades back to 2019 with direction, iv, index_price, amount in coins). Pages of 1,000 trades in time order; a page
boundary inside one millisecond is handled by restarting at that millisecond and dropping trade ids already seen.

Files (gitignored):
- data/deribit_trades/<CUR>/flow/<YYYY-MM>.parquet: one row per (hour t, instrument) with taker buy and sell amounts
  and counts, block amounts by side, the amount-weighted IV, premium paid in coins and the last index price;
  instrument parsed into expiry (08:00 UTC), strike and cp.
- data/deribit_trades/<CUR>/blocks/<YYYY-MM>.parquet: every block trade, all fields.
- data/deribit_trades/provenance.json: rows, trades and requests per month.
Only whole months before the current one; a month whose file exists is skipped. Data collection only.

usage: python scripts/fetch_deribit_trades.py [--currencies BTC,ETH] [--start 2019-01] [--workers 4]
"""
import argparse
import json
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402

OUT = data.ROOT / "deribit_trades"
URL = ("https://history.deribit.com/api/v2/public/get_last_trades_by_currency_and_time?currency={cur}&kind=option"
       "&start_timestamp={a}&end_timestamp={b}&count=1000&sorting=asc")
FLOW_COLS = ["t", "instrument", "expiry_ms", "strike", "cp", "buy", "sell", "n_buy", "n_sell", "block_buy",
             "block_sell", "iv", "premium", "index_price"]
MONTHS = {m: i for i, m in enumerate(["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV",
                                      "DEC"], 1)}
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)
_lock = threading.Lock()


def http(url, tries=6):
    delay = 2.0
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "lab/1", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())["result"]
        except Exception:  # noqa: BLE001 - retried, then raised
            if i == tries - 1:
                raise
            time.sleep(delay)
            delay *= 2


def trades(cur, a, b, get=http):
    """Every trade with a <= timestamp <= b, in time order, each once; and the number of requests made."""
    out, seen, start, n = [], set(), a, 0
    while True:
        r = get(URL.format(cur=cur, a=start, b=b))
        n += 1
        page = [x for x in r["trades"] if x["trade_id"] not in seen]
        out += page
        seen.update(x["trade_id"] for x in page)
        if not r.get("has_more") or not r["trades"]:
            return out, n
        last = r["trades"][-1]["timestamp"]
        if not page and last == start:
            raise RuntimeError(f"{cur}: more than one page of trades in millisecond {start}")
        start = last                       # restart inside the last millisecond; seen ids are dropped


def parse_instrument(name):
    """'BTC-8JAN21-24000-P' -> (expiry ms at 08:00 UTC, strike, 'P')."""
    _, day, strike, cp = name.split("-")
    d = pd.Timestamp(year=2000 + int(day[-2:]), month=MONTHS[day[-5:-2]], day=int(day[:-5]), hour=8)
    return int(d.value // 1_000_000), float(strike.replace("d", ".")), cp


def flow(rows):
    """Hourly signed flow per instrument from raw trades (see the module note)."""
    if not rows:
        return pd.DataFrame(columns=FLOW_COLS)
    df = pd.DataFrame(rows)
    df["t"] = df.timestamp // 3_600_000 * 3_600_000
    buy = df.direction == "buy"
    block = df["block_trade_id"].notna() if "block_trade_id" in df else pd.Series(False, index=df.index)
    a = df.amount.astype(float)
    df = df.assign(buy=a.where(buy, 0.0), sell=a.where(~buy, 0.0), n_buy=buy.astype(int), n_sell=(~buy).astype(int),
                   block_buy=a.where(buy & block, 0.0), block_sell=a.where(~buy & block, 0.0),
                   ivw=df.iv.astype(float) * a, premium=df.price.astype(float) * a, amt=a)
    g = df.sort_values("timestamp").groupby(["t", "instrument_name"], sort=True)
    out = g[["buy", "sell", "n_buy", "n_sell", "block_buy", "block_sell", "ivw", "premium", "amt"]].sum()
    out["index_price"] = g.index_price.last()
    out = out.reset_index().rename(columns={"instrument_name": "instrument"})
    with np.errstate(invalid="ignore", divide="ignore"):
        out["iv"] = out.ivw / out.amt
    parsed = [parse_instrument(i) for i in out.instrument]
    out["expiry_ms"] = [p[0] for p in parsed]
    out["strike"] = [p[1] for p in parsed]
    out["cp"] = [p[2] for p in parsed]
    return out[FLOW_COLS]


def write(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    df.to_parquet(tmp, index=False)
    tmp.replace(path)


def month(cur, ym, out=OUT, get=http):
    path = out / cur / "flow" / f"{ym}.parquet"
    if path.exists():
        return None
    a = pd.Timestamp(ym + "-01")
    b = a + pd.offsets.MonthBegin(1)
    rows, n = trades(cur, int(a.value // 1_000_000), int(b.value // 1_000_000) - 1, get)
    blocks = pd.DataFrame([r for r in rows if "block_trade_id" in r])
    write(blocks, out / cur / "blocks" / f"{ym}.parquet")
    f = flow(rows)
    write(f, path)
    return {"trades": len(rows), "blocks": len(blocks), "rows": len(f), "requests": n}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--currencies", default="BTC,ETH")
    ap.add_argument("--start", default="2019-01")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(argv)
    last = (pd.Timestamp.utcnow().tz_localize(None).to_period("M") - 1)
    months = [str(p) for p in pd.period_range(a.start, last, freq="M")]
    jobs = [(c, m) for c in a.currencies.split(",") for m in months]
    prov_path = OUT / "provenance.json"
    prov = json.loads(prov_path.read_text()) if prov_path.exists() else {}

    def one(job):
        cur, ym = job
        try:
            info = month(cur, ym)
        except Exception as e:  # noqa: BLE001 - logged; the month is retried on the next run
            log(f"{cur} {ym}: failed: {type(e).__name__}: {e}")
            return
        if info is None:
            return
        log(f"{cur} {ym}: {info['trades']} trades, {info['blocks']} blocks, {info['rows']} rows, "
            f"{info['requests']} requests")
        with _lock:
            prov[f"{cur}/{ym}"] = info | {"fetched_utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime()),
                                         "source": "https://history.deribit.com/api/v2/public/"
                                                   "get_last_trades_by_currency_and_time"}
            OUT.mkdir(parents=True, exist_ok=True)
            prov_path.write_text(json.dumps(dict(sorted(prov.items())), indent=1))

    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(one, jobs))


if __name__ == "__main__":
    main()
