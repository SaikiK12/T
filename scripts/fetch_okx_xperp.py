"""OKX Europe X-Perps (MiFID, 5-year expiry crypto contracts with 8-hourly funding; M484): public data, no key.

Each run:
- writes the list of live crypto X-Perps to data/okx_xperp/instruments.json;
- merges every funding print the public API still serves (about 3 months) into data/okx_xperp/funding.parquet. Rows
  are deduplicated by (instId, fundingTime), so a daily run keeps the history that the API drops;
- merges daily mark-price candles of the X-Perps in MARK_COINS, and daily index candles of their underlyings, into
  mark_1d.parquet and index_1d.parquet.

A run that already merged funding today does nothing, unless --force is given. Data collection only. Paper only: no
account, no order.

usage: python scripts/fetch_okx_xperp.py [--force]
"""
import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402

OUT = data.ROOT / "okx_xperp"
API = "https://eea.okx.com/api/v5/"
MARK_COINS = ("BTC", "ETH", "SOL", "XRP", "DOGE")
PAUSE = 0.25
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def get(path):
    req = urllib.request.Request(API + path, headers={"User-Agent": "lab-research/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    if d.get("code") != "0":
        raise RuntimeError(f"{path}: code {d.get('code')} {d.get('msg')}")
    time.sleep(PAUSE)
    return d["data"]


def crypto_xperps(instruments):
    return [i for i in instruments if "_UM_XPERP-" in i["instId"] and str(i.get("instCategory")) == "1"]


def pages(path, key, first_field=0, max_pages=50):
    """Every row of a paginated history endpoint, newest first, walking `after` back until it is empty."""
    rows, after = [], ""
    for _ in range(max_pages):
        d = get(path + (f"&after={after}" if after else ""))
        if not d:
            break
        rows += d
        after = d[-1][key] if isinstance(d[-1], dict) else d[-1][first_field]
    return rows


def merge(path, new, keys):
    if path.exists():
        new = pd.concat([pd.read_parquet(path), new])
    new = new.drop_duplicates(keys, keep="last").sort_values(keys).reset_index(drop=True)
    tmp = path.with_suffix(".tmp")
    new.to_parquet(tmp, index=False)
    tmp.rename(path)
    return new


def funding_frame(rows):
    f = pd.DataFrame(rows)
    out = pd.DataFrame({"instId": f.instId, "fundingTime": f.fundingTime.astype("int64"),
                        "fundingRate": pd.to_numeric(f.fundingRate, errors="coerce"),
                        "realizedRate": pd.to_numeric(f.get("realizedRate"), errors="coerce"),
                        "method": f.get("method"), "formulaType": f.get("formulaType")})
    return out


def candle_frame(rows, inst):
    c = pd.DataFrame([r[:5] for r in rows], columns=["ts", "o", "h", "l", "c"])
    c["ts"] = c.ts.astype("int64")
    for k in ("o", "h", "l", "c"):
        c[k] = pd.to_numeric(c[k])
    c.insert(0, "instId", inst)
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = OUT / "last_run.txt"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not a.force and stamp.exists() and stamp.read_text().strip() == today:
        log("already merged today")
        return
    inst = crypto_xperps(get("public/instruments?instType=FUTURES"))
    (OUT / "instruments.json").write_text(json.dumps({"fetched_utc": datetime.now(timezone.utc).isoformat(),
                                                      "instruments": inst}, indent=0) + "\n")
    rows, failed = [], []
    for i in inst:
        try:
            rows += pages(f"public/funding-rate-history?instId={i['instId']}&limit=100", "fundingTime")
        except Exception as e:  # noqa: BLE001 - one instrument must not stop the others
            failed.append(i["instId"])
            log(f"{i['instId']}: {type(e).__name__}: {e}")
    f = merge(OUT / "funding.parquet", funding_frame(rows), ["instId", "fundingTime"]) if rows else None
    marks, idx = [], []
    for coin in MARK_COINS:
        try:
            for x in [i["instId"] for i in inst if i["instId"].startswith(coin + "-USD_UM_XPERP-")]:
                marks.append(candle_frame(pages(f"market/history-mark-price-candles?instId={x}&bar=1D&limit=100",
                                                None, 0, 10), x))
            idx.append(candle_frame(pages(f"market/history-index-candles?instId={coin}-USD&bar=1D&limit=100",
                                          None, 0, 10), f"{coin}-USD"))
        except Exception as e:  # noqa: BLE001 - one coin must not stop the others
            failed.append(coin + " candles")
            log(f"{coin} candles: {type(e).__name__}: {e}")
    if marks:
        merge(OUT / "mark_1d.parquet", pd.concat(marks), ["instId", "ts"])
    if idx:
        merge(OUT / "index_1d.parquet", pd.concat(idx), ["instId", "ts"])
    stamp.write_text(today + "\n")
    log(f"{len(inst)} crypto X-Perps; funding rows held {0 if f is None else len(f)}; failed {failed}")


if __name__ == "__main__":
    main()
