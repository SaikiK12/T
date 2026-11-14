"""Inputs for R468 asiaclose_v1 (Asian single-stock perps across the daily local closure, on trade.xyz and Lighter).
Public and keyless, with a generic client name; Lighter through lab/carrylane.py's paced client.

universe  -> experiments/asiaclose_v1/universe.csv (run before the freeze; names, ids and fees only, no price)
    - MEMBERS below: the single-stock perps whose reference listing is on KRX, TSE, HKEX or the Shanghai exchange,
      from trade.xyz's documentation (docs.trade.xyz llms-full.txt) and Lighter's market table (docs.lighter.xyz
      llms-full.txt), live on 2026-11-11. Each row gets the venue's id, growth mode and fee scale (xyz meta) or
      market id, listing time and fees (Lighter orderBookDetails).
bars      -> data/asiaclose/ (run after the freeze; gitignored, recorded with scripts/data_provenance.py)
    - <venue>/klines_1h/<COIN>.parquet: 1 h candles (t open ms, close, volume) over [--start, --end)
    - <venue>/funding/<COIN>.parquet: hourly funding (t ms, rate signed + when longs pay)
    - receipts.jsonl (one sha256 per xyz response) and manifest.json (per-file sha256)

usage: python scripts/fetch_asiaclose.py universe
       python scripts/fetch_asiaclose.py bars --start 2026-04-01T00:00:00Z --end 2026-11-11T00:00:00Z
"""
import argparse
import csv
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import carrylane  # noqa: E402

LANE = ROOT / "experiments" / "asiaclose_v1"
OUT = ROOT / "data" / "asiaclose"
INFO = "https://api.hyperliquid.xyz/info"
UA = "lab-research-fetch/1.0"
H = 3_600_000
PAGE_H = 720                      # xyz candles per request (30 days)
# (venue, coin, exchange, local listing): xyz SKHY (two SK hynix markets on xyz) and Lighter SKHY (the US ADR) are left
# out, as are indices (KR200, JP225, NIFTY: external futures quotes overnight), pre-IPO perps and RELIANCE (listed
# 2026-10-26, too few days).
MEMBERS = [
    ("xyz", "SKHX", "KRX", "000660"), ("xyz", "SMSN", "KRX", "005930"), ("xyz", "HYUNDAI", "KRX", "005380"),
    ("xyz", "SOFTBANK", "TSE", "9984"), ("xyz", "KIOXIA", "TSE", "285A"),
    ("xyz", "MINIMAX", "HKEX", "0100"), ("xyz", "ZHIPU", "HKEX", "2513"),
    ("xyz", "GIGADEV", "SSE", "603986"), ("xyz", "CAMBRICON", "SSE", "688256"),
    ("lighter", "SKHYNIXUSD", "KRX", "000660"), ("lighter", "SAMSUNGUSD", "KRX", "005930"),
    ("lighter", "HYUNDAIUSD", "KRX", "005380"), ("lighter", "KIOXIA", "TSE", "285A"),
    ("lighter", "MINIMAX", "HKEX", "0100"), ("lighter", "ZHIPU", "HKEX", "2513"),
    ("lighter", "TENCENT", "HKEX", "0700"), ("lighter", "XIAOMI", "HKEX", "1810"),
    ("lighter", "SMIC", "HKEX", "0981"),
]
COLS = ["venue", "coin", "exchange", "local", "market_id", "created_at", "growth", "fee_scale", "taker_fee",
        "maker_fee", "status"]


def http(data, tries=5):
    head = {"User-Agent": UA, "Accept": "application/json", "Content-Type": "application/json"}
    for k in range(tries):
        try:
            req = urllib.request.Request(INFO, data=json.dumps(data).encode(), headers=head)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except (urllib.error.URLError, TimeoutError):
            if k == tries - 1:
                raise
        time.sleep(2 ** (k + 1))


def universe():
    meta = json.loads(http({"type": "meta", "dex": "xyz"}))
    xyz = {u["name"].split(":", 1)[1]: u for u in meta["universe"] if not u.get("isDelisted")}
    lt = {d["symbol"]: d for d in carrylane._lighter_details()}
    out = []
    for venue, coin, exch, local in MEMBERS:
        row = {"venue": venue, "coin": coin, "exchange": exch, "local": local}
        if venue == "xyz":
            u = xyz[coin]
            row.update(growth=u.get("growthMode", ""), fee_scale=u.get("deployerFeeScale", ""), status="active")
        else:
            d = lt[coin]
            row.update(market_id=int(d["market_id"]), created_at=int(d["created_at"]), status=d.get("status", ""),
                       taker_fee=d.get("taker_fee", ""), maker_fee=d.get("maker_fee", ""))
        out.append(row)
    LANE.mkdir(parents=True, exist_ok=True)
    with open(LANE / "universe.csv", "w", newline="") as f:
        w = csv.DictWriter(f, COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    print(len(out), "markets")


def epoch_ms(s):
    return int(datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp() * 1000)


def post(body, rec):
    raw = http(body)
    rec.write(json.dumps({"body": body, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                          "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n")
    time.sleep(0.3)
    return json.loads(raw)


def xyz_bars(coin, s0, s1, rec):
    name, rows, s = "xyz:" + coin, [], s0
    while s < s1:
        e = min(s1, s + PAGE_H * H)
        k = post({"type": "candleSnapshot", "req": {"coin": name, "interval": "1h", "startTime": s,
                                                    "endTime": e - 1}}, rec)
        rows += [{"t": int(x["t"]), "close": float(x["c"]), "volume": float(x["v"])} for x in k
                 if s0 <= int(x["t"]) < s1]
        s = e
    kd = pd.DataFrame(rows, columns=["t", "close", "volume"]).drop_duplicates("t").sort_values("t")
    fr, s = [], s0
    while s < s1:
        page = post({"type": "fundingHistory", "coin": name, "startTime": s, "endTime": s1}, rec)
        if not page:
            break
        fr += [{"t": int(x["time"]), "rate": float(x["fundingRate"])} for x in page if int(x["time"]) < s1]
        s = int(page[-1]["time"]) + 1
        if len(page) < 500:
            break
    fd = pd.DataFrame(fr, columns=["t", "rate"]).drop_duplicates("t").sort_values("t")
    return kd.reset_index(drop=True), fd.reset_index(drop=True)


def lighter_bars(coin, s0, s1):
    k = carrylane.lighter_prices(coin, s0, s1)
    k = k[(k.t >= s0) & (k.t < s1)].reset_index(drop=True)
    f = carrylane.lighter_funding(coin, s0, s1)
    f = f[(f.t > s0) & (f.t <= s1)].drop_duplicates("t").sort_values("t").reset_index(drop=True)
    return k, f


def bars(start, end):
    with open(LANE / "universe.csv", newline="") as f:
        members = [(r["venue"], r["coin"]) for r in csv.DictReader(f)]
    s0, s1 = epoch_ms(start), epoch_ms(end)
    man = {"kind": "asiaclose_1h_and_funding", "start": start, "end_exclusive": end, "files": {},
           "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "receipts.jsonl", "a") as rec:
        for venue, coin in members:
            k, fd = xyz_bars(coin, s0, s1, rec) if venue == "xyz" else lighter_bars(coin, s0, s1)
            for sub, df in (("klines_1h", k), ("funding", fd)):
                p = OUT / venue / sub / f"{coin}.parquet"
                p.parent.mkdir(parents=True, exist_ok=True)
                df.to_parquet(p, index=False)
                man["files"][f"{venue}/{sub}/{coin}.parquet"] = {
                    "rows": len(df), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            print(venue, coin, len(k), "candles", len(fd), "funding", flush=True)
    (OUT / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print(len(members), "markets")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("universe")
    b = sub.add_parser("bars")
    b.add_argument("--start", required=True)
    b.add_argument("--end", required=True)
    a = ap.parse_args()
    if a.cmd == "universe":
        universe()
    else:
        bars(a.start, a.end)


if __name__ == "__main__":
    main()
