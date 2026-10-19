"""Binance public-archive fetcher (data.binance.vision). The trading API is geo-blocked here; the archive is not.

Monthly archives are used where they exist, daily ones only for months after the last monthly archive. Every download
is verified (zip CRC by default, the published SHA-256 with strict=True) and cached, so a run resumes where it stopped.
"""
import hashlib
import io
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

BASE = "https://data.binance.vision"
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
UM = "data/futures/um"
ROOT = Path(__file__).resolve().parent.parent / "data"
END = "2026-09-30"  # last day of the research window (the original universe ended here)

KLINE_COLS = ("t", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "count",
              "taker_buy_volume", "taker_buy_quote_volume", "ignore")
KLINE_KEEP = ("t", "open", "high", "low", "close", "volume", "quote_volume", "count",
              "taker_buy_volume", "taker_buy_quote_volume")
METRIC_COLS = ("t", "symbol", "oi", "oi_value", "top_ls_count", "top_ls_sum", "ls_count", "taker_ls_vol")
FUNDING_COLS = ("t", "interval_h", "rate")
KINDS = {  # kind -> (has interval, column names, kept columns)
    "klines": (True, KLINE_COLS, KLINE_KEEP),
    "markPriceKlines": (True, KLINE_COLS, KLINE_KEEP),
    "premiumIndexKlines": (True, KLINE_COLS, KLINE_KEEP),
    "metrics": (False, METRIC_COLS, ("t",) + METRIC_COLS[2:]),
    "fundingRate": (False, FUNDING_COLS, FUNDING_COLS),
}


class FetchError(Exception):
    pass


def _get(url, tries=5, timeout=60):
    delay = 1.0
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise
            err = e
        except OSError as e:
            err = e
        if attempt < tries - 1:
            time.sleep(delay)
            delay *= 2
    raise FetchError(f"{url}: {err}")


def _list(prefix, delimiter="/", marker=""):
    """All keys and common prefixes under prefix, following S3 pagination."""
    keys, prefixes = [], []
    while True:
        q = {"prefix": prefix}
        if delimiter:
            q["delimiter"] = delimiter
        if marker:
            q["marker"] = marker
        root = ET.fromstring(_get(S3 + "?" + urllib.parse.urlencode(q)))
        ns = {"s": root.tag.split("}")[0][1:]}
        page_keys = [e.text for e in root.findall("s:Contents/s:Key", ns)]
        page_prefixes = [e.text for e in root.findall("s:CommonPrefixes/s:Prefix", ns)]
        keys += page_keys
        prefixes += page_prefixes
        if root.findtext("s:IsTruncated", namespaces=ns) != "true":
            return keys, prefixes
        marker = root.findtext("s:NextMarker", namespaces=ns) or (page_keys or page_prefixes)[-1]


def list_zips(prefix, marker=""):
    return [k for k in _list(prefix, delimiter="", marker=marker)[0] if k.endswith(".zip")]


def universe():
    """USDT-quoted perpetuals in the archive, delisted ones included (quarterly contracts carry a date suffix)."""
    _, prefixes = _list(f"{UM}/monthly/klines/")
    names = (p.rstrip("/").rsplit("/", 1)[1] for p in prefixes)
    return sorted(n for n in names if n.endswith("USDT"))


_DATE = re.compile(r"-(\d{4}-\d{2})(-\d{2})?\.zip$")


def plan_files(symbol, kind, interval="", list_fn=list_zips, end=END):
    """Archive keys covering a symbol: every monthly file, plus daily files after the last monthly month."""
    stem = f"{UM}/%s/{kind}/{symbol}/" + (f"{interval}/" if interval else "")
    monthly = list_fn(stem % "monthly")
    last = max((_DATE.search(k).group(1) for k in monthly), default="")
    daily = []
    if kind != "fundingRate":  # funding is published monthly only
        name = f"{symbol}-{interval}-" if interval else f"{symbol}-{kind}-"
        marker = f"{stem % 'daily'}{name}{last}-99.zip" if last else ""
        daily = list_fn(stem % "daily", marker=marker)
    keys = monthly + daily
    return [k for k in keys if _DATE.search(k).group(1) + (_DATE.search(k).group(2) or "-01") <= end]


def fetch(key, raw=None, strict=False):
    """Download one archive file into the cache; None when the archive does not have it."""
    dest = Path(raw or ROOT / "raw") / key
    quoted = urllib.parse.quote(key)
    if dest.exists():
        if strict:
            want = _published_sha256(key, quoted)
            got = hashlib.sha256(dest.read_bytes()).hexdigest()
            if got != want:
                raise FetchError(f"{key}: cached SHA-256 mismatch")
        else:
            _verify_zip(dest.read_bytes(), key)
        return dest
    try:
        blob = _get(f"{BASE}/{quoted}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    if strict:
        want = _published_sha256(key, quoted)
        if hashlib.sha256(blob).hexdigest() != want:
            raise FetchError(f"{key}: SHA-256 mismatch")
    else:
        _verify_zip(blob, key)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    tmp.write_bytes(blob)
    tmp.replace(dest)
    return dest


def _published_sha256(key, quoted=None):
    """Fetch the archive's published checksum; strict mode never trusts an unverified cache."""
    quoted = quoted or urllib.parse.quote(key)
    fields = _get(f"{BASE}/{quoted}.CHECKSUM").split()
    if not fields:
        raise FetchError(f"{key}: empty published checksum")
    try:
        digest = fields[0].decode("ascii").lower()
    except UnicodeDecodeError as e:
        raise FetchError(f"{key}: invalid published checksum") from e
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise FetchError(f"{key}: invalid published SHA-256")
    return digest


def _verify_zip(blob, key):
    """Verify a cached or freshly downloaded archive's ZIP CRC without contacting the source."""
    try:
        bad = zipfile.ZipFile(io.BytesIO(blob)).testzip()
    except (OSError, zipfile.BadZipFile) as e:
        raise FetchError(f"{key}: invalid zip") from e
    if bad is not None:
        raise FetchError(f"{key}: corrupt zip ({bad})")


def parse(path, kind):
    """One archive file to a frame with t in epoch milliseconds."""
    _, names, keep = KINDS[kind]
    with zipfile.ZipFile(path) as z:
        raw = z.read(z.namelist()[0])
    skip = 1 if raw[:1].isalpha() else 0  # older kline files have no header row
    df = pd.read_csv(io.BytesIO(raw), header=None, names=list(names), skiprows=skip, usecols=range(len(names)))
    if kind == "metrics":
        stamp = pd.to_datetime(df["t"], utc=True)
        df["t"] = (stamp - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(milliseconds=1)
    elif df["t"].iloc[0] > 10**14:  # microsecond timestamps
        df["t"] = df["t"] // 1000
    return df[list(keep)]


def build(kind, interval="", symbols=None, workers=32, strict=False, end=END, root=None, log=print):
    """Fetch and assemble one dataset into <root>/<kind>[_<interval>]/<SYMBOL>.parquet plus a manifest."""
    has_interval = KINDS[kind][0]
    if has_interval and not interval:
        raise ValueError(f"{kind} needs an interval")
    root = Path(root or ROOT)
    out = root / (f"{kind}_{interval}" if has_interval else kind)
    out.mkdir(parents=True, exist_ok=True)
    symbols = list(symbols or universe())
    end_ms = int((pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)).timestamp() * 1000)
    with ThreadPoolExecutor(workers) as ex:
        plans = dict(zip(symbols, ex.map(lambda s: plan_files(s, kind, interval if has_interval else "", end=end), symbols)))
        jobs = [(s, k) for s, keys in plans.items() for k in keys]
        log(f"{kind} {interval}: {len(symbols)} symbols, {len(jobs)} files to fetch")
        done = ex.map(lambda sk: fetch(sk[1], root / "raw", strict), jobs)
        paths = {}
        for i, ((s, k), p) in enumerate(zip(jobs, done), 1):
            if p is not None:
                paths.setdefault(s, []).append(p)
            if i % 5000 == 0:
                log(f"  fetched {i}/{len(jobs)}")
    manifest = {}
    for s, ps in paths.items():
        df = pd.concat([parse(p, kind) for p in ps], ignore_index=True)
        df = df[df["t"] < end_ms].drop_duplicates("t", keep="last").sort_values("t").reset_index(drop=True)
        if df.empty:
            continue
        df.to_parquet(out / f"{s}.parquet", index=False)
        manifest[s] = {"rows": len(df), "first": int(df["t"].iloc[0]), "last": int(df["t"].iloc[-1]),
                       "sha256": hashlib.sha256((out / f"{s}.parquet").read_bytes()).hexdigest()}
    body = {"kind": kind, "interval": interval, "end": end, "symbols": manifest}
    body["sha256"] = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    (out / "manifest.json").write_text(json.dumps(body, indent=1, sort_keys=True))
    log(f"{kind} {interval}: {len(manifest)} symbols written, manifest sha {body['sha256'][:12]}")
    return body


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["universe", "build"])
    ap.add_argument("kind", nargs="?", default="klines")
    ap.add_argument("interval", nargs="?", default="")
    ap.add_argument("--symbols", help="comma separated; default is the whole universe")
    ap.add_argument("--limit", type=int, help="first N symbols only")
    ap.add_argument("--workers", type=int, default=32)
    ap.add_argument("--strict", action="store_true", help="verify the published SHA-256 of every file")
    a = ap.parse_args()
    if a.cmd == "universe":
        u = universe()
        ROOT.mkdir(exist_ok=True)
        (ROOT / "universe.json").write_text(json.dumps(u))
        print(len(u), "USDT perpetuals;", hashlib.sha256("\n".join(u).encode()).hexdigest()[:16])
    else:
        syms = a.symbols.split(",") if a.symbols else (json.loads((ROOT / "universe.json").read_text()) if (ROOT / "universe.json").exists() else None)
        build(a.kind, a.interval, syms[: a.limit] if (syms and a.limit) else syms, a.workers, a.strict)
