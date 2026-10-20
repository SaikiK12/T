"""Coin Metrics community API (free, no key): daily market caps and on-chain metrics for every asset it serves free.

- **Market caps:** estimated market cap (`CapMrktEstUSD`, about 850 assets) and, where Coin Metrics has the supply
  on chain, the current market cap (`CapMrktCurUSD`, about 135). These give the size factor (and volume / cap turnover)
  over the full archive, where CoinGecko's free API keeps 365 days only.
- **On-chain, where served free:** active addresses, transactions, supply, MVRV, adjusted NVT, fees, transfer value,
  hash rate, and exchange in/outflows and exchange supply (BTC, ETH).

Each asset's free metrics come from the community catalog (`/v4/catalog-v2/asset-metrics`), so nothing is requested
that the free tier refuses. A row's `t` is the start of Coin Metrics' UTC day: the value is known only after the day
ends (`t + 1 day`), and exchange flows can be revised after their first ("flash") print, so the panel lags them.

Rows before 2021-01-01 go to `reserved/` (the reserved 2020 window, docs/GATES.md). Saved in
data/coinmetrics/{open,reserved}/<asset>.parquet (t in ms, one column per metric) with `catalog.json` and
`manifest.json`. An asset whose file exists is skipped, so it resumes. Data collection only.

usage: python scripts/fetch_coinmetrics.py [--pause 0.65] [--only btc,eth]
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402
from scripts.fetch_venue_history import OPEN_FROM_MS, ms  # noqa: E402

API = "https://community-api.coinmetrics.io/v4"
OUT = data.ROOT / "coinmetrics"
WANT = ("CapMrktEstUSD", "CapMrktCurUSD", "CapMrktFFUSD", "PriceUSD", "volume_reported_spot_usd_1d", "AdrActCnt",
        "TxCnt", "SplyCur", "SplyFF", "CapMVRVCur", "NVTAdj", "FeeTotUSD", "TxTfrValAdjUSD", "HashRate",
        "FlowInExUSD", "FlowOutExUSD", "SplyExNtv")
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def get(url, tries=8):
    delay = 3.0
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8.5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except (OSError, ValueError) as e:              # 429 and 5xx included: back off
            err = e
            time.sleep(delay)
            delay = min(delay * 2, 60)
    raise RuntimeError(f"{url}: {err}")


def catalog(pause):
    """{asset: [free daily metrics we want]} from the community catalog."""
    out = {}
    for m in WANT:
        url = f"{API}/catalog-v2/asset-metrics?{urllib.parse.urlencode({'metrics': m, 'page_size': 1000})}"
        while url:
            d = get(url)
            time.sleep(pause)
            for a in d.get("data", []):
                if any(f["frequency"] == "1d" for x in a["metrics"] if x["metric"] == m for f in x["frequencies"]):
                    out.setdefault(a["asset"], []).append(m)
            url = d.get("next_page_url")
    return {a: sorted(set(v)) for a, v in sorted(out.items())}


def series(asset, metrics, pause):
    rows, url = [], f"{API}/timeseries/asset-metrics?" + urllib.parse.urlencode(
        {"assets": asset, "metrics": ",".join(metrics), "frequency": "1d", "page_size": 10000,
         "ignore_forbidden_errors": "true", "ignore_unsupported_errors": "true"})
    while url:
        d = get(url)
        time.sleep(pause)
        rows += d.get("data", [])
        url = d.get("next_page_url")
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["t"] = [ms(x) for x in df.time]
    cols = [m for m in metrics if m in df.columns]
    df = df[["t", *cols]]
    df[cols] = df[cols].apply(pd.to_numeric, errors="coerce")
    return df.astype({"t": "int64"}).drop_duplicates("t").sort_values("t", ignore_index=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pause", type=float, default=0.65)   # the free tier allows about 10 requests per 6 s
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    cat_path = OUT / "catalog.json"
    if cat_path.exists():
        cat = json.loads(cat_path.read_text())
    else:
        cat = catalog(a.pause)
        cat_path.write_text(json.dumps(cat, indent=1))
    only = set(filter(None, a.only.split(",")))
    # assets with a market cap or on-chain data; the rest serve only a reference price
    keep = {"CapMrktEstUSD", "CapMrktCurUSD", "AdrActCnt"}
    assets = [x for x in cat if (not only and keep & set(cat[x])) or x in only]
    log(f"{len(assets)} assets, {sum(len(v) for v in cat.values())} asset-metrics in the free catalog")
    status = {}
    for i, asset in enumerate(assets, 1):
        if (OUT / "open" / f"{asset}.parquet").exists() or (OUT / "reserved" / f"{asset}.parquet").exists():
            status[asset] = "skip"
            continue
        try:
            df = series(asset, cat[asset], a.pause)
        except RuntimeError as e:
            status[asset] = f"error {e}"
            continue
        for where, part in (("open", df[df.t >= OPEN_FROM_MS]), ("reserved", df[df.t < OPEN_FROM_MS])) if len(df) else ():
            if len(part):
                (OUT / where).mkdir(exist_ok=True)
                part.to_parquet(OUT / where / f"{asset}.parquet", index=False)
        status[asset] = len(df)
        if i % 50 == 0 or i == len(assets):
            log(f"{i}/{len(assets)} {asset}: {len(df)} days")
    if not only:
        (OUT / "reserved" / "README.md").parent.mkdir(exist_ok=True)
        (OUT / "reserved" / "README.md").write_text(
            "Reserved 2020 window (docs/GATES.md). Do not read: only a frozen batch PREREG declaring "
            "RESERVED-2020-READ may.\n")
        (OUT / "manifest.json").write_text(json.dumps({
            "source": API, "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "errors": {k: v for k, v in status.items() if str(v).startswith("error")}, "assets": status}, indent=1))
    log("done")


if __name__ == "__main__":
    main()
