"""Inputs for R473 tlteom_v1 (the end-of-month Treasury rally on TLT, Hartley and Schwarz). Public and keyless.

etfs -> data/tlteom/yahoo/<TICKER>.json (raw chart response) and <TICKER>.parquet (date in New York, open, high, low,
        close, adjclose, volume) for TLT and IEF, from Yahoo's public chart endpoint through the frozen parser of R471
        (scripts/fetch_cryptomon.py), paced 3 s apart with a generic client name.
data/tlteom/manifest.json lists every file's sha256.

usage: python scripts/fetch_tlteom.py --start 2002-06-01 --end 2026-11-12
"""
import argparse
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from fetch_cryptomon import CHART, UA, epoch, parse_chart  # noqa: E402  (frozen in R471)

OUT = ROOT / "data" / "tlteom"
TICKERS = ("TLT", "IEF")


def fetch(start, end, out=OUT):
    (out / "yahoo").mkdir(parents=True, exist_ok=True)
    man = {"source": "query1.finance.yahoo.com/v8/finance/chart (public, no key)", "start": start, "end": end,
           "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": {}}
    for t in TICKERS:
        req = urllib.request.Request(CHART.format(t=t, a=epoch(start), b=epoch(end)), headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
        (out / "yahoo" / f"{t}.json").write_bytes(raw)
        df = parse_chart(json.loads(raw))
        df.to_parquet(out / "yahoo" / f"{t}.parquet", index=False)
        man["files"][f"yahoo/{t}.parquet"] = {"rows": len(df)}
        print(t, len(df), flush=True)
        time.sleep(3)
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            rel = str(p.relative_to(out))
            man["files"].setdefault(rel, {})["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
    (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2002-06-01")
    ap.add_argument("--end", required=True)
    a = ap.parse_args()
    fetch(a.start, a.end)


if __name__ == "__main__":
    main()
