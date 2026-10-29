"""Bounded, public, exclusive raw acquisition for the frozen ORB pilot.

No prices, returns, signals or performance statistics are inspected here.
Each request body is retained; 8 MB total and 1 MB/body, one fixed symbol.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://contract.mexc.com/api/v1/contract/"
SYMBOL = "NAS100_USDT"
LIMIT = 8_000_000


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(calendar_path, out, manifest_path):
    calendar = json.loads(calendar_path.read_text())
    out.mkdir(parents=True, exist_ok=False)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    if manifest_path.exists():
        raise ValueError("provenance destination already exists")
    receipts, total = [], 0

    def get(name, endpoint, params):
        nonlocal total
        url = BASE + endpoint + "?" + urlencode(params)
        started = time.time_ns()
        with urlopen(Request(url, headers={"User-Agent": "lab-paper/1"}), timeout=25) as response:
            raw = response.read(min(1_000_001, LIMIT - total + 1))
        if len(raw) > 1_000_000 or total + len(raw) > LIMIT:
            raise ValueError("acquisition budget exceeded")
        p = out / name
        with p.open("xb") as f:
            f.write(raw)
        total += len(raw)
        receipts.append(dict(path=name, url=url, started_ns=started, received_ns=time.time_ns(),
                             bytes=len(raw), sha256=digest(p)))
        body = json.loads(raw)
        if body.get("success") is not True:
            raise ValueError("provider request failed: " + name)
        print(name, len(raw), "bytes received", flush=True)
        time.sleep(.12)
        return body["data"]

    detail = get("contract.json", "detail", {"symbol": SYMBOL})
    if isinstance(detail, list):
        detail = next(r for r in detail if r["symbol"] == SYMBOL)
    if detail["symbol"] != SYMBOL or detail.get("type") != 2:
        raise ValueError("wrong contract identity/type")
    for s in calendar["sessions"]:
        for kind, prefix in (("last", ""), ("fair", "fair_price/")):
            get(f'{s["day"]}_{kind}.json', f"kline/{prefix}{SYMBOL}",
                dict(interval="Min1", start=s["open_ms"] // 1000,
                     end=(s["close_ms"] + 60_000) // 1000))
    first = min(s["open_ms"] for s in calendar["sessions"])
    older, seen_times = None, set()
    for page in range(1, 5):
        data = get(f"funding_{page:04d}.json", "funding_rate/history",
                   dict(symbol=SYMBOL, page_num=page, page_size=1000))
        if type(data.get("currentPage")) is not int or data["currentPage"] != page:
            raise ValueError("funding page identity missing/mismatched")
        if type(data.get("totalPage")) is not int or data["totalPage"] < page:
            raise ValueError("funding page count invalid")
        rows = data.get("resultList")
        if not isinstance(rows, list) or not rows:
            raise ValueError("funding history empty/incomplete")
        times = [r["settleTime"] for r in rows]
        if any(type(t) is not int for t in times) or any(a <= b for a, b in zip(times, times[1:])):
            raise ValueError("funding timestamps not strict descending integers")
        if any(r.get("symbol") != SYMBOL for r in rows) or seen_times.intersection(times):
            raise ValueError("funding identity/duplicate failure")
        if older is not None and times[0] >= older:
            raise ValueError("funding pagination did not move backwards")
        seen_times.update(times)
        older = times[-1]
        if older < first:
            break
        if page == data["totalPage"]:
            raise ValueError("funding history does not bracket requested start")
    else:
        raise ValueError("funding page budget exceeded")
    p = out / "receipts.json"
    with p.open("x") as f:
        json.dump(dict(symbol=SYMBOL, receipts=receipts, bytes=total,
                       historical_membership_verified=False, historical_contract_units_verified=False,
                       funding_scope="all provider-reported rows through a page older than requested start; not independent completeness proof",
                       collector_sha256=digest(Path(__file__))), f, indent=2)
        f.write("\n")
    files = [dict(path=p.relative_to(out).as_posix(), bytes=p.stat().st_size, sha256=digest(p))
             for p in sorted(out.iterdir())]
    payload = dict(folder=out.relative_to(ROOT).as_posix(), source=BASE, symbol=SYMBOL,
                   scope="latest-vintage raw last/fair minute bars and reported exact funding events",
                   source_authentication="TLS public endpoint and local byte hashes; no historical publication proof",
                   file_hashes=files, files=len(files), bytes=sum(r["bytes"] for r in files),
                   collector_sha256=digest(Path(__file__)))
    with manifest_path.open("x") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    print("Raw acquisition sealed; no market statistics computed.", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--calendar", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    a = ap.parse_args()
    fetch(a.calendar.resolve(), a.out.resolve(), a.manifest.resolve())


if __name__ == "__main__":
    main()
