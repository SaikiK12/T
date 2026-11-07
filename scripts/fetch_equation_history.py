"""Bounded public input restoration for equations_v1. No strategy/return calculation.

Only the already frozen R288 MEXC/Lighter/Binance-overlap table is admissible.
Pages are immutable, resumable, hashed public responses; no account endpoints.
Historical coverage and historical contract-rule availability are NOT certified.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sys
import threading
import time
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab.carrylane import _lighter_lock  # noqa: E402

H = 3_600_000
START = int(pd.Timestamp("2025-04-27", tz="UTC").timestamp() * 1000)
END = int(pd.Timestamp("2026-10-01", tz="UTC").timestamp() * 1000)
TABLE = ROOT / "experiments/xfund_lt_v1/symbols.csv"
MEXC = "https://contract.mexc.com/api/v1/contract"
LIGHTER = "https://mainnet.zklighter.elliot.ai/api/v1"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pairs(table=TABLE):
    with open(table, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r.get("mexc") and r.get("lighter")]
    if not rows or len({r["key"] for r in rows}) != len(rows):
        raise ValueError("empty or duplicate frozen pair universe")
    if any(not r.get("binance") for r in rows):
        raise ValueError("reserved/non-Binance market in proposed input universe")
    return rows


class BudgetStop(RuntimeError):
    pass


class PublicPages:
    def __init__(self, out, max_requests=8000, max_bytes=250 * 1024**2):
        self.out = Path(out)
        self.max_requests, self.max_bytes = max_requests, max_bytes
        self.lock = threading.RLock()
        self.path = self.out / "acquisition_status.json"
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {
            "requests": 0, "wire_bytes": 0, "complete": False, "errors": {}, "completed": []}
        self.out.mkdir(parents=True, exist_ok=True)

    def save(self):
        with self.lock:
            p = self.path.with_suffix(".tmp")
            p.write_text(json.dumps(self.state, sort_keys=True, indent=2) + "\n")
            p.replace(self.path)

    def get(self, base, path, params=None, lighter=False):
        url = base + "/" + path + ("?" + urllib.parse.urlencode(params) if params else "")
        cache = self.out / "raw" / (hashlib.sha256(url.encode()).hexdigest() + ".json.gz")
        if cache.exists():
            return json.loads(gzip.decompress(cache.read_bytes()))
        err = None
        for attempt in range(3):
            try:
                with self.lock:
                    if self.state["requests"] >= self.max_requests or self.state["wire_bytes"] >= self.max_bytes:
                        raise BudgetStop("registered public-request/250 MiB wire budget exhausted")
                    self.state["requests"] += 1
                    self.save()
                req = urllib.request.Request(url, headers={"User-Agent": "quant-lab-public-inputs/1",
                                                           "Accept-Encoding": "gzip"})
                def read():
                    with urllib.request.urlopen(req, timeout=30) as response:
                        with self.lock:
                            limit = min(12 * 1024**2, self.max_bytes - self.state["wire_bytes"])
                            body = response.read(limit)
                            self.state["wire_bytes"] += len(body)
                            self.save()
                        if len(body) >= limit:
                            raise BudgetStop("public response reached remaining wire/per-response budget")
                        return gzip.decompress(body) if response.headers.get("Content-Encoding") == "gzip" else body
                if lighter:
                    with _lighter_lock():
                        try:
                            raw = read()
                        finally:
                            time.sleep(1.1)
                else:
                    raw = read()
                    time.sleep(.15)
                data = json.loads(raw)
                if lighter and data.get("code") != 200:
                    raise ValueError("Lighter public response code is not 200")
                if not lighter and data.get("success") is not True:
                    raise ValueError("MEXC public response success is not true")
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_bytes(gzip.compress(raw, mtime=0))
                with self.lock:
                    with (self.out / "public_receipts.jsonl").open("a") as f:
                        f.write(json.dumps({"url": url, "received_utc": pd.Timestamp.now(tz="UTC").isoformat(),
                                            "raw_sha256": hashlib.sha256(raw).hexdigest(),
                                            "cache": str(cache.relative_to(self.out))}, sort_keys=True) + "\n")
                return data
            except BudgetStop:
                raise
            except Exception as exc:
                err = exc
                if attempt < 2:
                    time.sleep(2**attempt)
        raise RuntimeError(f"public fetch failed: {path}: {err}")


def unique(frame):
    if len(frame):
        dup = frame[frame.duplicated("t", keep=False)]
        if len(dup) and any(len(g.drop_duplicates()) > 1 for _, g in dup.groupby("t")):
            raise ValueError("conflicting duplicate public rows")
        frame = frame.drop_duplicates("t").sort_values("t").reset_index(drop=True)
    return frame


def lighter_rows(client, market, kind, start=START, end=END):
    frames = []
    step = (480 if kind == "prices" else 700) * H
    for s in range(start, end + (H if kind == "funding" else 0), step):
        e = min(end + (H if kind == "funding" else 0), s + step)
        q = {"market_id": market, "resolution": "1h", "start_timestamp": s if kind == "prices" else s // 1000,
             "end_timestamp": e if kind == "prices" else e // 1000, "count_back": 0}
        d = client.get(LIGHTER, "candles" if kind == "prices" else "fundings", q, lighter=True)
        for r in d.get("c" if kind == "prices" else "fundings", []):
            if kind == "prices":
                t = int(r["t"])
                if not start <= t < end:
                    continue
                frames.append({"t": t, "close": float(r["c"]), "volume": float(r.get("v", 0)),
                               "amount": float(r.get("V", 0))})
            else:
                t = int(r["timestamp"]) * 1000
                if not start <= t <= end:
                    continue
                if r["direction"] not in ("long", "short") or float(r["rate"]) < 0:
                    raise ValueError("unknown Lighter direction/negative unsigned rate")
                sign = 1 if r["direction"] == "long" else -1
                frames.append({"t": t, "rate": sign * float(r["rate"]) / 100,
                               "cycle_h": 1., "raw_value_uninterpreted": str(r.get("value", ""))})
    cols = ["t", "close", "volume", "amount"] if kind == "prices" else ["t", "rate", "cycle_h", "raw_value_uninterpreted"]
    return unique(pd.DataFrame(frames, columns=cols))


def mexc_rows(client, symbol, kind, start=START, end=END):
    rows = []
    if kind == "prices":
        for s in range(start, end, 2000 * H):
            e = min(end, s + 2000 * H)
            d = client.get(MEXC, "kline/" + symbol, {"interval": "Min60", "start": s // 1000,
                                                     "end": (e - H) // 1000})["data"]
            if not d or not d.get("time"):
                continue
            for i, t in enumerate(d["time"]):
                t = int(t) * 1000
                if start <= t < end:
                    rows.append({"t": t, "close": float(d["close"][i]), "vol": float(d["vol"][i]),
                                 "amount": float(d["amount"][i])})
    else:
        page = 1
        previous_oldest = None
        while page <= 30:
            d = client.get(MEXC, "funding_rate/history", {"symbol": symbol, "page_num": page,
                                                         "page_size": 1000})["data"]
            if int(d["currentPage"]) != page:
                raise ValueError("MEXC funding page identity mismatch")
            items = d["resultList"]
            if not items:
                if page != 1 or int(d["totalPage"]) > 1:
                    raise ValueError("empty nonterminal MEXC funding page")
                break
            oldest = min(int(x["settleTime"]) for x in items)
            if previous_oldest is not None and oldest >= previous_oldest:
                raise ValueError("MEXC funding pagination stalled")
            previous_oldest = oldest
            for r in items:
                t = int(r["settleTime"])
                if start <= t <= end:
                    if r.get("symbol", symbol) != symbol:
                        raise ValueError("MEXC funding symbol mismatch")
                    rows.append({"t": t, "rate": float(r["fundingRate"]),
                                 "cycle_h": float(r["collectCycle"]) if r.get("collectCycle") else np.nan})
            if oldest <= start or page >= int(d["totalPage"]):
                break
            page += 1
        else:
            raise ValueError("MEXC funding page safety cap")
    cols = ["t", "close", "vol", "amount"] if kind == "prices" else ["t", "rate", "cycle_h"]
    return unique(pd.DataFrame(rows, columns=cols))


def collect(out):
    client = PublicPages(out)
    acquisition = {"version": 1, "start_ms": START, "end_price_exclusive_ms": END,
                   "end_funding_inclusive_ms": END, "symbol_table_sha256": sha(TABLE),
                   "collector_sha256": sha(__file__), "max_requests": client.max_requests,
                   "max_wire_bytes": client.max_bytes, "coverage_certified": False,
                   "scope": "R288 frozen current-survivor table; open Binance-overlap only; historical rule vintages unknown"}
    p = Path(out) / "acquisition.json"
    if p.exists() and json.loads(p.read_text()) != acquisition:
        raise ValueError("resume specification or collector changed")
    p.write_text(json.dumps(acquisition, sort_keys=True, indent=2) + "\n")
    table = pairs()
    mexc_meta = client.get(MEXC, "detail")["data"]
    lighter_meta = client.get(LIGHTER, "orderBookDetails", {"filter": "perp"}, lighter=True)["order_book_details"]
    for venue, meta in (("mexc", mexc_meta), ("lighter", lighter_meta)):
        (Path(out) / (venue + "_contracts_current.json")).write_text(json.dumps(meta, sort_keys=True) + "\n")
    ids = {x["symbol"]: int(x["market_id"]) for x in lighter_meta}

    def venue_work(venue):
        for n, row in enumerate(table, 1):
            for kind in ("prices", "funding"):
                symbol = row[venue]
                dest = Path(out) / venue / kind / (symbol + ".parquet")
                key = str(dest.relative_to(out))
                if key in client.state["completed"]:
                    continue
                try:
                    df = (lighter_rows(client, ids[symbol], kind) if venue == "lighter" else
                          mexc_rows(client, symbol, kind))
                    numeric = [c for c in df.columns if c not in ("cycle_h", "raw_value_uninterpreted")]
                    if len(df) and not np.isfinite(df[numeric].to_numpy(float)).all():
                        raise ValueError("nonfinite public input")
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    temp = dest.with_suffix(".tmp.parquet")
                    df.to_parquet(temp, index=False)
                    temp.replace(dest)
                    with client.lock:
                        client.state["completed"].append(key)
                        client.state["errors"].pop(key, None)
                        client.save()
                except Exception as exc:
                    with client.lock:
                        client.state["errors"][key] = f"{type(exc).__name__}: {exc}"
                        client.save()
                    if isinstance(exc, BudgetStop):
                        return
            print(time.strftime("%H:%M:%S"), venue, f"{n}/{len(table)}", row["key"],
                  "requests", client.state["requests"], flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(venue_work, ("mexc", "lighter")))
    client.state["complete"] = len(client.state["completed"]) == len(table) * 4 and not client.state["errors"]
    client.save()
    return 0 if client.state["complete"] else 1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=ROOT / "data/equations_v1")
    a = p.parse_args()
    return collect(a.out)


if __name__ == "__main__":
    raise SystemExit(main())
