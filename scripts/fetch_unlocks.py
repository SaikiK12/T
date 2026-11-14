"""DefiLlama token-unlock schedules (the old session's E01 source), from the free dataset mirror: the protocol list,
the emissions index, and one schedule file per protocol (documented unlock events with category, cliff/linear type
and token counts, plus max supply). Saved gzipped under data/unlocks/<UTC date>/ with a manifest of URLs, sizes and
SHA-256. Resumable: a protocol whose file exists in today's folder is skipped. Data collection only.

This is today's calendar, revised after the fact. A later lane must treat it as such (the old session warned that
corrections can flatter the edge); scripts/record_unlocks.py keeps dated snapshots from now on.

usage: python scripts/fetch_unlocks.py [--workers 4]
"""
import argparse
import gzip
import hashlib
import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402

BASE = "https://defillama-datasets.llama.fi"
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def get_bytes(url, tries=4):
    delay = 2.0
    for _ in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "lab/1"}), timeout=60) as r:
                return r.read()
        except OSError as e:
            err = e
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"{url}: {err}")


def save(path, raw):
    path.write_bytes(gzip.compress(raw))
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    out = data.ROOT / "unlocks" / time.strftime("%Y-%m-%d", time.gmtime())
    (out / "protocols").mkdir(parents=True, exist_ok=True)
    manifest = {"source": BASE, "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": {}}
    raw = get_bytes(f"{BASE}/emissionsProtocolsList")
    manifest["files"]["emissionsProtocolsList.json.gz"] = save(out / "emissionsProtocolsList.json.gz", raw)
    slugs = json.loads(raw)
    manifest["expected_protocols"] = len(slugs)
    raw = get_bytes(f"{BASE}/emissionsIndex")
    manifest["files"]["emissionsIndex.json.gz"] = save(out / "emissionsIndex.json.gz", raw)
    log(f"{len(slugs)} protocols")

    def one(slug):
        path = out / "protocols" / f"{slug}.json.gz"
        if path.exists():
            raw = gzip.decompress(path.read_bytes())
            return slug, {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        try:
            return slug, save(path, get_bytes(f"{BASE}/emissions/{slug}"))
        except RuntimeError as e:
            return slug, {"error": str(e)}

    with ThreadPoolExecutor(a.workers) as ex:
        for i, (slug, info) in enumerate(ex.map(one, slugs), 1):
            manifest["files"][f"protocols/{slug}.json.gz"] = info
            if i % 50 == 0:
                log(f"{i}/{len(slugs)}")
    errors = [k for k, v in manifest["files"].items() if "error" in v]
    manifest["got_protocols"] = len(slugs) - len(errors)
    manifest["errors"] = errors
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    log(f"done: {manifest['got_protocols']}/{len(slugs)} protocols, {len(errors)} errors -> {out}")


if __name__ == "__main__":
    main()
