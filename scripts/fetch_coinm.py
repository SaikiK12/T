"""Binance COIN-M hourly klines from data.binance.vision for every contract in the archive (272: perpetuals and
dated quarterlies of about 10 coins, 2020 onward): the dated-futures basis term structure (M170, C09). Raw zips are
cached under data/raw/ (CRC-checked by lab.data.fetch); future exports go to data/coinm_1h_v2/, t in epoch ms.
COIN-M fields7/10 are base-asset volumes, not quote volumes. Generic volume/taker_buy_volume units are not inferred.
Schema/hash completion receipts gate resume. Existing coinm_1h files and frozen consumers retain their provenance;
future panels must explicitly adopt v2. Monthly files through data.END. This command acquires data when invoked.

Source: binance/binance-public-data README, commit d571690eb66760763b0bd6e27e8cd35603c7e244, lines57-61.

usage: python scripts/fetch_coinm.py [--workers 16] [--out data/coinm_1h_v2]
"""
import argparse
import csv
import hashlib
import json
import os
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402

CM = "data/futures/cm/monthly/klines/"
OUT = data.ROOT / "coinm_1h_v2"
SCHEMA_VERSION = "coinm_klines_v2"
RENAMES = {"quote_volume": "base_asset_volume", "taker_buy_quote_volume": "taker_buy_base_asset_volume"}
COLUMNS = tuple(RENAMES.get(name, name) for name in data.KLINE_KEEP)
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


class CacheError(RuntimeError):
    pass


def parse_coinm(path):
    """Keep values/price/time behavior; name only the two established base-volume fields."""
    with zipfile.ZipFile(path) as z:
        with z.open(z.namelist()[0]) as f:
            first = f.readline().decode("utf-8-sig").strip()
    if first and first[0].isalpha():
        header = next(csv.reader([first]))
        normal = ["".join(c for c in name.lower() if c.isalnum()) for name in header]
        if (len(normal) != 12 or normal[7] not in {"basevolume", "baseassetvolume"}
                or normal[10] not in {"takerbuybasevolume", "takerbuybaseassetvolume"}):
            raise ValueError("COIN-M header must declare base-asset volume at fields7/10")
    return data.parse(path, "klines").rename(columns=RENAMES, errors="raise")


def _schema():
    return {"schema_version": SCHEMA_VERSION, "source": data.BASE + "/" + CM,
            "interval": "1h", "end": data.END, "columns": list(COLUMNS)}


def _request(contract):
    return {**_schema(), "contract": contract}


def _destination():
    legacy = (data.ROOT / "coinm_1h").resolve()
    target = OUT.resolve()
    if target == legacy or legacy in target.parents:
        raise CacheError("Refusing legacy coinm_1h destination; use a fresh versioned namespace")
    if OUT.is_symlink() or (OUT / "completion").is_symlink():
        raise CacheError("Refusing symlinked output/completion directory")


def _sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def completed(contract):
    """Check local completion before acquisition; preserve inconsistent outputs for inspection."""
    _destination()
    path, receipt = OUT / f"{contract}.parquet", OUT / "completion" / f"{contract}.json"

    def fail(reason):
        raise CacheError(f"{contract}: {reason}; cache preserved at {OUT}; use a fresh v2 directory")

    if any(p.with_name(p.name + ".part").exists() for p in (path, receipt)):
        fail("interrupted staging file")
    if path.is_symlink() or receipt.is_symlink():
        fail("symlinked output/receipt")
    if not path.exists() and not receipt.exists():
        return False
    if not path.is_file() or not receipt.is_file():
        fail("output and completion receipt must both exist")
    try:
        d = json.loads(receipt.read_text())
        if not isinstance(d, dict) or any(d.get(k) != v for k, v in _request(contract).items()):
            fail("schema/source request mismatch")
        if type(d["rows"]) is not int or d["rows"] <= 0 or _sha256(path) != d["sha256"]:
            fail("row declaration or output hash mismatch")
        from pyarrow import parquet
        if parquet.read_schema(path).names != list(COLUMNS) or parquet.read_metadata(path).num_rows != d["rows"]:
            fail("Parquet schema/row count mismatch")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        fail(f"invalid completion receipt/output ({exc})")
    return True


def preflight():
    """Reject inconsistent local artifacts before even listing the remote archive."""
    _destination()
    summary = OUT / "manifest.json"
    if summary.with_name(summary.name + ".part").exists():
        raise CacheError("Interrupted manifest; output preserved, use a fresh v2 directory")
    if summary.exists():
        try:
            d = json.loads(summary.read_text())
            if not isinstance(d, dict) or any(d.get(k) != v for k, v in _schema().items()):
                raise ValueError("schema/source request mismatch")
        except (OSError, ValueError) as exc:
            raise CacheError(f"Invalid v2 manifest; output preserved ({exc})") from exc
    contracts = {p.name.removesuffix(".part").removesuffix(".parquet")
                 for pattern in ("*.parquet", "*.parquet.part") for p in OUT.glob(pattern)}
    contracts |= {p.name.removesuffix(".part").removesuffix(".json")
                  for pattern in ("*.json", "*.json.part") for p in (OUT / "completion").glob(pattern)}
    for contract in sorted(contracts):
        completed(contract)


def _publish(path, write, *, summary=False):
    _destination()
    if path.is_symlink():
        raise CacheError(f"Refusing symlinked publication target {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not summary:
        raise CacheError(f"Refusing to overwrite {path}")
    part = path.with_name(path.name + ".part")
    with part.open("xb") as f:
        write(f)
        f.flush()
        os.fsync(f.fileno())
    if summary:
        part.replace(path)
    else:
        # link is atomic and refuses a destination created after the preflight.
        os.link(part, path)
        part.unlink()
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def one(contract):
    path = OUT / f"{contract}.parquet"
    if completed(contract):
        return contract, "skip"
    keys = [k for k in data.list_zips(f"{CM}{contract}/1h/") if data._DATE.search(k).group(1) <= data.END[:7]]
    frames = []
    for key in keys:
        archive = data.fetch(key, data.ROOT / "raw")
        if archive is None:
            raise CacheError(f"{contract}: listed archive disappeared: {key}; no completion published")
        frames.append(parse_coinm(archive))
    if not frames:
        return contract, "none"
    df = pd.concat(frames).drop_duplicates("t").sort_values("t").reset_index(drop=True)
    _publish(path, lambda f: df.to_parquet(f, index=False))
    receipt = {**_request(contract), "rows": len(df), "sha256": _sha256(path), "archives": keys}
    _publish(OUT / "completion" / f"{contract}.json",
             lambda f: f.write(json.dumps(receipt, indent=1).encode()))
    return contract, f"{len(df)} bars"


def main():
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--out", type=Path, default=OUT, help="Fresh versioned output; legacy coinm_1h is refused")
    a = ap.parse_args()
    OUT = a.out
    preflight()
    OUT.mkdir(parents=True, exist_ok=True)
    _, prefixes = data._list(CM)
    contracts = sorted(p.rstrip("/").rsplit("/", 1)[1] for p in prefixes)
    log(f"{len(contracts)} COIN-M contracts")
    status = {}
    with ThreadPoolExecutor(a.workers) as ex:
        for c, msg in ex.map(one, contracts):
            status[c] = msg
    manifest = {**_schema(), "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "contracts": status}
    _publish(OUT / "manifest.json", lambda f: f.write(json.dumps(manifest, indent=1).encode()), summary=True)
    log(f"done: {sum(v != 'none' for v in status.values())} of {len(contracts)} with data")


if __name__ == "__main__":
    main()
