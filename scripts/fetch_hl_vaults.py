"""Hyperliquid user-vault histories for M466 (vault persistence; edge map family F4). Public data, no key, no order.

1. The vault list (stats-data.hyperliquid.xyz/Mainnet/vaults, about 14 MB, closed vaults included) is read from
   data/hyperliquid/vaults/list_<date>.json (fetched once with --list).
2. Each vault's vaultDetails (POST api.hyperliquid.xyz/info) is appended as one JSON line to
   data/hyperliquid/vaults/details_<date>.jsonl.gz. The followers list is replaced by its count to keep the file
   small; everything else is kept as received, with the UTC fetch time.

Resumable: addresses already in the output are skipped. Paced at one request per PAUSE seconds (Hyperliquid allows
1,200 weight a minute per IP), doubling the wait after an error. Stops when free disk falls below MIN_FREE_GB.
This is a measurement download approved under the owner's delegation of 2026-11-04 (about 80 MB compressed).

usage: python -I scripts/fetch_hl_vaults.py --list            fetch today's vault list
       python -I scripts/fetch_hl_vaults.py --date 2026-11-04 fetch details for that list
"""
import argparse
import gzip
import json
import shutil
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "hyperliquid" / "vaults"
LIST_URL = "https://stats-data.hyperliquid.xyz/Mainnet/vaults"
INFO_URL = "https://api.hyperliquid.xyz/info"
PAUSE = 1.1
MIN_FREE_GB = 2.0
log = lambda *a: print(time.strftime("%H:%M:%S", time.gmtime()), *a, flush=True)


def slim(details, fetched):
    """The record kept per vault: the answer as received, followers replaced by their count."""
    out = dict(details)
    followers = out.pop("followers", None)
    out["followers_n"] = len(followers) if isinstance(followers, list) else followers
    out["fetched_utc"] = fetched
    return out


def good_lines(path):
    """The complete JSON lines of a gzip file, and whether its end was cut (a run killed mid-write)."""
    lines, cut = [], False
    try:
        with gzip.open(path, "rt") as f:
            for line in f:
                lines.append(line)
    except (EOFError, gzip.BadGzipFile, OSError):
        cut = True
    ok = []
    for line in lines:
        try:
            json.loads(line)["vaultAddress"]
            ok.append(line if line.endswith("\n") else line + "\n")
        except (ValueError, KeyError, TypeError):
            cut = True                # a torn last line is dropped and refetched
    return ok, cut


def done_addresses(path):
    """Addresses already saved. A file cut by an interrupted run is first rewritten with its complete lines only,
    so later appends stay readable."""
    if not path.exists():
        return set()
    ok, cut = good_lines(path)
    if cut:
        tmp = path.with_suffix(".tmp")
        with gzip.open(tmp, "wt") as f:
            f.writelines(ok)
        tmp.replace(path)
        log(f"recovered {len(ok)} complete lines from a cut file")
    return {json.loads(line)["vaultAddress"].lower() for line in ok}


def addresses(list_path):
    rows = json.loads(list_path.read_text())
    return [r["summary"]["vaultAddress"].lower() for r in rows]


def post(body, timeout=30):
    req = urllib.request.Request(INFO_URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def run(date, pause=PAUSE, fetch=post, free_gb=lambda: shutil.disk_usage(OUT).free / 1e9, limit=None):
    list_path = OUT / f"list_{date}.json"
    out_path = OUT / f"details_{date}.jsonl.gz"
    done = done_addresses(out_path)
    todo = [a for a in addresses(list_path) if a not in done]
    log(f"{len(todo)} vaults to fetch -> {out_path.name}")
    wait, n = pause, 0
    with gzip.open(out_path, "at") as f:
        for a in todo[:limit]:
            if free_gb() < MIN_FREE_GB:
                log("stop: free disk below", MIN_FREE_GB, "GB")
                break
            while True:
                try:
                    d = fetch({"type": "vaultDetails", "vaultAddress": a})
                    break
                except OSError as e:
                    wait = min(wait * 2, 120)
                    log("error", a, e, "waiting", wait)
                    time.sleep(wait)
            if d is not None:
                d.setdefault("vaultAddress", a)
                f.write(json.dumps(slim(d, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))) + "\n")
                f.flush()
            n += 1
            if n % 500 == 0:
                log(n, "fetched")
            wait = pause
            time.sleep(pause)
    log("done", n)
    return n


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--list", action="store_true")
    p.add_argument("--date", default=time.strftime("%Y-%m-%d", time.gmtime()))
    a = p.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    if a.list:
        with urllib.request.urlopen(LIST_URL, timeout=120) as r:
            (OUT / f"list_{a.date}.json").write_bytes(r.read())
        log("list saved")
        return 0
    run(a.date)
    return 0


if __name__ == "__main__":
    sys.exit(main())
