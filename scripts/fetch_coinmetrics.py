"""Coin Metrics community API (free, no key): daily market caps and on-chain metrics for every asset it serves free.

- **Market caps:** estimated market cap (`CapMrktEstUSD`, about 850 assets) and, where Coin Metrics has the supply
  on chain, the current market cap (`CapMrktCurUSD`, about 135). These give the size factor (and volume / cap turnover)
  over the full archive, where CoinGecko's free API keeps 365 days only.
- **On-chain, where served free:** active addresses, transactions, supply, MVRV, adjusted NVT, fees, transfer value,
  hash rate, and exchange in/outflows and exchange supply (BTC, ETH).

Each asset's requested metrics come from the community catalog (`/v4/catalog-v2/asset-metrics`). UpperCamelCase
metrics use beginning-of-interval labels: `t + 1 day` is only their interval-end floor, not publication time.
Other metrics retain their provider-defined clock; this collector imposes no shared availability rule. Publication
can be later and historical values can be revised. This latest-vintage collection is not point-in-time data.

Rows before 2021-01-01 go to `reserved/` (the reserved 2020 window, docs/GATES.md). Saved in
data/coinmetrics/{open,reserved}/<asset>.parquet (t in ms, one column per metric) with `catalog.json` and
`manifest.json`. An immutable `completion/<asset>.json` receipt records the request and each partition's row count
and hash after all nonempty shards are published. Only a verified receipt permits skipping an asset. Legacy or
interrupted caches are preserved and refused; use a fresh `--out` directory. A receipt proves local publication
completeness, not historical availability or source coverage. Data collection only.

usage: python scripts/fetch_coinmetrics.py [--pause 0.65] [--only btc,eth] [--out PATH]
"""
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
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
PARTITIONS = ("open", "reserved")


class CacheError(RuntimeError):
    pass


def _sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _publish(path, write):
    """Stage and durably publish one new file; preserve partial writes for inspection."""
    path.parent.mkdir(parents=True, exist_ok=True)
    _sync_dir(path.parent.parent)
    if path.exists():
        raise CacheError(f"Refusing to overwrite {path}; use a fresh --out directory")
    with path.with_name(path.name + ".part").open("xb") as f:
        write(f)
        f.flush()
        os.fsync(f.fileno())
    path.with_name(path.name + ".part").replace(path)
    _sync_dir(path.parent)


def _sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _request(asset, metrics):
    return {"schema_version": 1, "source": API, "asset": asset, "metrics": sorted(set(metrics)),
            "frequency": "1d", "open_from_ms": OPEN_FROM_MS}


def completed(out, asset, metrics):
    """Return a verified local completion receipt, or None for an untouched asset."""
    receipt = out / "completion" / f"{asset}.json"
    shards = {where: out / where / f"{asset}.parquet" for where in PARTITIONS}

    def fail(reason):
        raise CacheError(f"{asset}: {reason}; cache preserved at {out}. Use a fresh --out directory")

    if any(p.with_name(p.name + ".part").exists() for p in (receipt, *shards.values())):
        fail("interrupted staging file")
    if not receipt.exists():
        if any(p.exists() for p in shards.values()):
            fail("existing shard has no completion receipt")
        return None
    try:
        d = json.loads(receipt.read_text())
        if not isinstance(d, dict) or any(d.get(k) != v for k, v in _request(asset, metrics).items()):
            fail("completion receipt does not match the request")
        datetime.strptime(d["captured_utc"], "%Y-%m-%dT%H:%M:%SZ")
        if set(d["partitions"]) != set(PARTITIONS):
            fail("completion receipt must declare both partitions")
        for where, path in shards.items():
            part = d["partitions"][where]
            rows = part["rows"]
            if type(rows) is not int or rows < 0 or part["path"] != f"{where}/{asset}.parquet":
                fail("invalid partition declaration")
            if rows == 0:
                if part["sha256"] is not None or path.exists():
                    fail(f"unexpected {where} shard for an empty partition")
            elif not path.is_file() or _sha256(path) != part["sha256"]:
                fail(f"missing or changed {where} shard")
    except (OSError, ValueError, KeyError, TypeError) as e:
        fail(f"invalid completion receipt ({e})")
    return d


def publish_asset(out, asset, metrics, df):
    """Publish new shards, then the immutable receipt; never adopt or repair old files."""
    if completed(out, asset, metrics) is not None:
        raise CacheError(f"{asset}: already complete; use a fresh --out directory")
    receipt = {**_request(asset, metrics),
               "captured_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "partitions": {}}
    for where in PARTITIONS:
        part = df
        if len(df):
            part = df[df.t >= OPEN_FROM_MS] if where == "open" else df[df.t < OPEN_FROM_MS]
        path = out / where / f"{asset}.parquet"
        if len(part):
            _publish(path, lambda f: part.to_parquet(f, index=False))
        receipt["partitions"][where] = {"path": f"{where}/{asset}.parquet", "rows": len(part),
                                          "sha256": _sha256(path) if len(part) else None}
    _publish(out / "completion" / f"{asset}.json",
             lambda f: f.write(json.dumps(receipt, indent=1).encode()))
    return receipt


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
        if not isinstance(d, dict) or not isinstance(d.get("data"), list):
            raise RuntimeError(f"{asset}: invalid series response: expected a data list")
        rows += d["data"]
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
    ap.add_argument("--out", type=Path, default=OUT, help="isolated output directory (legacy caches are not adopted)")
    a = ap.parse_args()
    out = a.out
    out.mkdir(parents=True, exist_ok=True)
    cat_path = out / "catalog.json"
    if cat_path.exists():
        cat = json.loads(cat_path.read_text())
    else:
        cat = catalog(a.pause)
        _publish(cat_path, lambda f: f.write(json.dumps(cat, indent=1).encode()))
    only = set(filter(None, a.only.split(",")))
    if only - set(cat):
        ap.error(f"assets absent from cached catalog: {', '.join(sorted(only - set(cat)))}")
    # assets with a market cap or on-chain data; the rest serve only a reference price
    keep = {"CapMrktEstUSD", "CapMrktCurUSD", "AdrActCnt"}
    assets = [x for x in cat if (not only and keep & set(cat[x])) or x in only]
    try:
        receipts = {asset: completed(out, asset, cat[asset]) for asset in assets}
    except CacheError as e:
        ap.error(str(e))
    log(f"{len(assets)} assets, {sum(len(v) for v in cat.values())} asset-metrics in the free catalog")
    status = {}
    for i, asset in enumerate(assets, 1):
        if receipts[asset] is not None:
            status[asset] = "skip"
            continue
        try:
            df = series(asset, cat[asset], a.pause)
        except RuntimeError as e:
            status[asset] = f"error {e}"
            continue
        publish_asset(out, asset, cat[asset], df)
        status[asset] = len(df)
        if i % 50 == 0 or i == len(assets):
            log(f"{i}/{len(assets)} {asset}: {len(df)} days")
    if not only:
        (out / "reserved" / "README.md").parent.mkdir(exist_ok=True)
        (out / "reserved" / "README.md").write_text(
            "Reserved 2020 window (docs/GATES.md). Do not read: only a frozen batch PREREG declaring "
            "RESERVED-2020-READ may.\n")
        (out / "manifest.json").write_text(json.dumps({
            "source": API, "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "errors": {k: v for k, v in status.items() if str(v).startswith("error")}, "assets": status}, indent=1))
    log("done")


if __name__ == "__main__":
    main()
