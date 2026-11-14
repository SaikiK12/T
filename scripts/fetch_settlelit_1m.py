"""R363's Lighter minutes around R354's settlement hops: Lighter 1-minute candles from T - 10 min to T + 10 min.

- Lighter: the public 1-minute candles (carrylane's client and its machine-wide lock), one call a hop, fields as
  scripts/fetch_venue_history.py maps them (o/h/l/c, volume v, quote volume V). Only bars that had closed when they
  were fetched are kept. data/settlelit_1m/lighter/<symbol>/<T ms>.parquet.
- docs/provenance/settlelit_1m.json: the source, the script, the time, and every file's sha256.

The hops are R354's frozen Binance + Lighter θ 0.3% book (experiments/settlehop_pred_v1/results/hops.csv.gz), which
holds all 87 hops of its primary θ 0.5% book. The script prints counts only; it computes no price change.
usage: python -I scripts/fetch_settlelit_1m.py [--plumbing]
"""
import argparse
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import carrylane  # noqa: E402

MIN = 60_000
HOPS = ROOT / "experiments" / "settlehop_pred_v1" / "results" / "hops.csv.gz"
BOOK = "binance+lighter th0.3%"
SYMBOLS = ROOT / "experiments" / "settlehop_v1" / "symbols.csv"
LIGHTER_IDS = ROOT / "data" / "lighter_hist" / "contracts.csv"
OUT = ROOT / "data" / "settlelit_1m"
PROV = ROOT / "docs" / "provenance" / "settlelit_1m.json"
BEFORE, AFTER = 10 * MIN, 10 * MIN               # bars opening in [T - 10 min, T + 10 min)
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def hops():
    """R354's θ 0.3% hops: [(Binance symbol, Lighter symbol, Lighter market id, T ms)] in T order."""
    h = pd.read_csv(HOPS)
    h = h[h.book == BOOK].sort_values(["T", "coin"])
    lt = {r["key"]: r["lighter"] for r in csv.DictReader(open(SYMBOLS, newline=""))}
    ids = {r["symbol"]: int(r["market_id"]) for r in csv.DictReader(open(LIGHTER_IDS, newline=""))}
    return [(c, lt[c], ids[lt[c]], int(t)) for c, t in zip(h.coin, h["T"])]


def lighter_window(mid, T, now):
    rows = carrylane._lighter("candles", market_id=mid, resolution="1m", start_timestamp=T - BEFORE,
                              end_timestamp=T + AFTER, count_back=0).get("c") or []
    df = pd.DataFrame({"t": [int(r["t"]) for r in rows],
                       **{k: [float(r.get(c, 0.0)) for r in rows] for k, c in (("open", "o"), ("high", "h"),
                                                                                ("low", "l"), ("close", "c"),
                                                                                ("volume", "v"),
                                                                                ("quote_volume", "V"))}})
    df = df[(df.t >= T - BEFORE) & (df.t < T + AFTER) & (df.t + MIN <= now)]
    return df.drop_duplicates("t").sort_values("t", ignore_index=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true", help="count the windows and bars on disk; fetch nothing")
    a = ap.parse_args(argv)
    hs = hops()
    log(f"{len(hs)} hops on {len({h[0] for h in hs})} coins")
    if a.plumbing:
        return plumbing(hs)
    now = int(time.time() * 1000)
    new = 0
    for _, lsym, mid, T in hs:
        p = OUT / "lighter" / lsym / f"{T}.parquet"
        if p.exists():
            continue
        df = lighter_window(mid, T, now)
        p.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(p, index=False)
        new += 1
    files = sorted(OUT.rglob("*.parquet"))
    PROV.write_text(json.dumps({
        "folder": "data/settlelit_1m",
        "source": "https://mainnet.zklighter.elliot.ai/api/v1/candles resolution 1m (lab.carrylane)",
        "script": "python -I scripts/fetch_settlelit_1m.py",
        "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hops": f"{HOPS.relative_to(ROOT).as_posix()} book {BOOK!r}: {len(hs)} hops",
        "window": "Lighter 1-minute bars opening in [T - 10 min, T + 10 min), closed when fetched",
        "files": len(files), "bytes": sum(f.stat().st_size for f in files),
        "file_hashes": [{"path": f.relative_to(ROOT).as_posix(), "sha256": sha(f)} for f in files],
    }, indent=1) + "\n")
    log(f"{new} new windows; wrote {PROV.relative_to(ROOT)}: {len(files)} files")
    return plumbing(hs)


def plumbing(hs):
    """Counts only: windows on disk, bars per window, and untraded bars at the minutes around T."""
    n, missing, short, untraded = 0, 0, 0, {k: 0 for k in (-6, -1, 0, 1, 4)}
    for _, lsym, _, T in hs:
        p = OUT / "lighter" / lsym / f"{T}.parquet"
        if not p.exists():
            missing += 1
            continue
        n += 1
        df = pd.read_parquet(p, columns=["t", "close", "volume"])
        short += int(len(df) < (BEFORE + AFTER) // MIN)
        traded = set(df.t[(df.close > 0) & (df.volume > 0)])
        for k in untraded:                   # the bar opening at T + k min
            untraded[k] += int(T + k * MIN not in traded)
    log(f"windows on disk {n}, missing {missing}, with fewer than {(BEFORE + AFTER) // MIN} bars {short}; "
        f"untraded bar by its open minute after T: {untraded}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
