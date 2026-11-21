"""R519's fetch, run through the frozen `fetch_deribit_perps` functions, skipping instruments that Deribit's
funding endpoint calls "not open".

Deribit's `get_instruments` (expired=false) lists some perps, such as ANTH_USDC-PERPETUAL, whose
`get_funding_rate_history` answers error -32602 "instrument is not open". The frozen fetch stops there after five
retries (2026-11-21). This wrapper:
- probes each instrument once;
- skips and records only that exact error;
- otherwise calls the frozen `funding`, `candles` and manifest layout unchanged.
See `experiments/deribitgap_v1/DEVIATIONS.md`.

usage: python scripts/fetch_deribit_perps_open.py --start 2022-03-01 --end 2026-11-19 --out data/deribit_perps
"""
import argparse
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_deribit_perps as f  # noqa: E402  (frozen in R519)


def not_open(name, start_ms):
    url = f.API + "get_funding_rate_history?" + urllib.parse.urlencode(
        {"instrument_name": name, "start_timestamp": start_ms, "end_timestamp": start_ms + f.DAY})
    req = urllib.request.Request(url, headers={"User-Agent": "research-client"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = json.loads(e.read() or b"{}")
    return (body.get("error") or {}).get("data", {}).get("reason") == "instrument is not open"


def fetch(start, end, out):
    out = Path(out)
    for sub in ("funding", "prices"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    raw = f.get("get_instruments", currency="any", kind="future", expired="false")
    (out / "instruments.json").write_text(json.dumps(raw, indent=1))
    a, b = f.ms(start), f.ms(end)
    skipped = []
    for name, base in f.perps(raw):
        created = int(next(x["creation_timestamp"] for x in raw if x["instrument_name"] == name))
        s = max(a, created)
        if not_open(name, s):
            skipped.append(name)
            continue
        f.funding(name, s, b).to_parquet(out / "funding" / f"{base}.parquet", index=False)
        f.candles(name, s, b).to_parquet(out / "prices" / f"{base}.parquet", index=False)
    (out / "skipped_not_open.json").write_text(json.dumps(skipped, indent=1))
    man = {"source": "www.deribit.com/api/v2/public (get_instruments, get_funding_rate_history, "
                     "get_tradingview_chart_data 1D)", "start": start, "end": end,
           "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "skipped_not_open": skipped, "files": {}}
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            man["files"][str(p.relative_to(out))] = hashlib.sha256(p.read_bytes()).hexdigest()
    (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps({"perps": len(f.perps(raw)), "skipped_not_open": len(skipped), "files": len(man["files"])}),
          flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2022-03-01")
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", default="data/deribit_perps")
    a = ap.parse_args()
    fetch(a.start, a.end, a.out)


if __name__ == "__main__":
    main()
