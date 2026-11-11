"""Earnings-release filings (8-K with Item 2.02, "Results of Operations and Financial Condition") from SEC EDGAR, timed
by EDGAR's acceptance time, for the US single stocks that have a MEXC TradFi perpetual in data/mexc_tradfi/klines_1h.
For M513 (earnings reaction on 24/7 stock perps).

Writes data/edgar_earnings/events.csv (ticker, cik, form, items, acceptance_utc, filing_date, accession) and
data/edgar_earnings/manifest.json (tickers asked, mapped, unmapped, row counts, sha256). data/ is gitignored; record the
folder with scripts/data_provenance.py afterwards.

Sources (public, no key; a generic client name in the User-Agent, at most about 6 requests a second):
- https://www.sec.gov/files/company_tickers.json   ticker -> CIK
- https://data.sec.gov/submissions/CIK##########.json   each company's filing index ("recent", plus the older pages
  it lists when the recent block does not reach back to --start)
Only original 8-K forms whose items include 2.02 are kept (no 8-K/A). Foreign issuers (6-K) are not covered and are
counted as unmapped or empty. EDGAR's acceptanceDateTime is in UTC (checked on Apple: 16:30 New York in both summer
and winter time).

usage: python scripts/fetch_edgar_earnings.py [--start 2025-06-01]
"""
import argparse
import csv
import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "edgar_earnings"
PERPS = ROOT / "data" / "mexc_tradfi" / "klines_1h"
UA = {"User-Agent": "lab-research-fetch/1.0", "Accept": "application/json"}
# MEXC single-stock perps whose symbol is not "<TICKER>STOCK"
NAMED = {"NVIDIA": "NVDA", "TESLA": "TSLA", "COINBASE": "COIN", "ROBINHOOD": "HOOD"}


def get_json(url, tries=5):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if k == tries - 1:
                raise
            time.sleep(2 ** (k + 1))
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(2 ** (k + 1))


def perp_tickers():
    out = {}
    for f in sorted(os.listdir(PERPS)):
        base = f.replace("_USDT.parquet", "")
        if base.endswith("STOCK"):
            out[base[:-5]] = base
        elif base in NAMED:
            out[NAMED[base]] = base
    return out


def rows_of(block, ticker, cik, start):
    out = []
    for i, form in enumerate(block.get("form", [])):
        if form != "8-K" or "2.02" not in (block["items"][i] or ""):
            continue
        if block["filingDate"][i] < start:
            continue
        out.append({"ticker": ticker, "cik": cik, "form": form, "items": block["items"][i],
                    "acceptance_utc": block["acceptanceDateTime"][i], "filing_date": block["filingDate"][i],
                    "accession": block["accessionNumber"][i]})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-06-01")
    a = ap.parse_args()
    perps = perp_tickers()
    tick = get_json("https://www.sec.gov/files/company_tickers.json")
    cik_of = {v["ticker"].upper().replace("-", "."): int(v["cik_str"]) for v in tick.values()}
    rows, unmapped, empty = [], [], []
    for n, (t, mexc) in enumerate(sorted(perps.items())):
        cik = cik_of.get(t) or cik_of.get(t.replace(".", "-"))
        if cik is None:
            unmapped.append(t)
            continue
        sub = get_json(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
        time.sleep(0.17)
        if sub is None:
            empty.append(t)
            continue
        recent = sub["filings"]["recent"]
        got = rows_of(recent, t, cik, a.start)
        oldest = min(recent["filingDate"]) if recent.get("filingDate") else "9999"
        if oldest > a.start:
            for page in sub["filings"].get("files", []):
                if page.get("filingTo", "") < a.start:
                    continue
                more = get_json("https://data.sec.gov/submissions/" + page["name"])
                time.sleep(0.17)
                if more:
                    got += rows_of(more, t, cik, a.start)
        if not got:
            empty.append(t)
        rows += got
        if n % 50 == 0:
            print(f"{n}/{len(perps)} {t}: {len(got)}", flush=True)
    rows.sort(key=lambda r: (r["acceptance_utc"], r["ticker"]))
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "events.csv"
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["ticker"], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    man = {"kind": "edgar_8k_item_2_02", "start": a.start, "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                                                         time.gmtime()),
           "tickers_asked": len(perps), "unmapped": unmapped, "no_8k_202": empty, "rows": len(rows),
           "events_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
           "sources": ["https://www.sec.gov/files/company_tickers.json",
                       "https://data.sec.gov/submissions/CIK##########.json"]}
    (OUT / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps({k: man[k] for k in ("tickers_asked", "rows", "events_sha256")}),
          "unmapped", len(unmapped), "empty", len(empty))


if __name__ == "__main__":
    main()
