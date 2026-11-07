"""R362's ticks around R354's settlement hops: Binance USD-M trades from T - 10 min to T + 15 min.

- Source: the public daily aggTrades files of data.binance.vision, each zip checked against its published sha256
  (.CHECKSUM), for every UTC day a window touches. The zips stream through memory; only the windows are kept.
- data/settle_ticks/binance/<symbol>/<T ms>.parquet: one row per aggregated trade in [T - 10 min, T + 15 min), with
  t (transact time, ms), price, qty, buyer_maker (True when the seller took liquidity) and agg_id.
- docs/provenance/settle_ticks.json: sources, the script, the time, each zip's published sha256 and size, and every
  kept file's sha256.

The hops are R354's frozen Binance + Lighter θ 0.3% book (experiments/settlehop_pred_v1/results/hops.csv.gz), which
holds all 87 hops of its primary θ 0.5% book. The script prints counts only; it computes no price change.
usage: python -I scripts/fetch_settle_ticks.py [--plan | --plumbing]
"""
import argparse
import hashlib
import io
import json
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MIN, DAY = 60_000, 86_400_000
HOPS = ROOT / "experiments" / "settlehop_pred_v1" / "results" / "hops.csv.gz"
BOOK = "binance+lighter th0.3%"
OUT = ROOT / "data" / "settle_ticks"
PROV = ROOT / "docs" / "provenance" / "settle_ticks.json"
BV = "https://data.binance.vision/data/futures/um/daily/aggTrades/{s}/{s}-aggTrades-{d}.zip"
BEFORE, AFTER = 10 * MIN, 15 * MIN               # the window around T: [T - 10 min, T + 15 min)
ACOLS = ["agg_id", "price", "qty", "first_id", "last_id", "t", "buyer_maker"]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def hops():
    """R354's θ 0.3% Binance + Lighter hops: [(Binance symbol, T ms)], one per settlement and coin."""
    h = pd.read_csv(HOPS)
    h = h[h.book == BOOK]
    return sorted({(c, int(t)) for c, t in zip(h.coin, h["T"])}, key=lambda x: (x[1], x[0]))


def day(ms):
    return time.strftime("%Y-%m-%d", time.gmtime(ms / 1000))


def days_of(T):
    """The UTC days that [T - BEFORE, T + AFTER) touches."""
    return sorted({day(T - BEFORE), day(T + AFTER - 1)})


def get(url, tries=4, method="GET"):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, method=method)
            with urllib.request.urlopen(req, timeout=120) as r:
                return r if method == "HEAD" else r.read()
        except Exception:  # noqa: BLE001
            if k == tries - 1:
                raise
            time.sleep(2 ** (k + 1))


def parse(blob):
    """An aggTrades zip's CSV, with or without its header row: DataFrame of t, price, qty, buyer_maker, agg_id."""
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        (name,) = z.namelist()
        raw = z.read(name)
    first = raw[:raw.find(b"\n")].decode()
    header = not first.split(",")[0].strip().isdigit()
    df = pd.read_csv(io.BytesIO(raw), header=0 if header else None, names=None if header else ACOLS,
                     dtype=str)
    df.columns = ACOLS[:len(df.columns)]
    out = pd.DataFrame({"t": df.t.astype("int64"), "price": df.price.astype(float), "qty": df.qty.astype(float),
                        "buyer_maker": df.buyer_maker.str.strip().str.lower().eq("true"),
                        "agg_id": df.agg_id.astype("int64")})
    if len(out) and out.t.iloc[0] > 10 ** 14:                             # microseconds -> ms
        out["t"] = out.t // 1000
    return out


def binance_day(sym, d):
    """One day's aggregated trades, checked against the published sha256: (DataFrame, sha256, zip bytes)."""
    url = BV.format(s=sym, d=d)
    blob = get(url)
    want = get(url + ".CHECKSUM").decode().split()[0]
    got = hashlib.sha256(blob).hexdigest()
    if got != want:
        raise ValueError(f"{url}: sha256 {got} != published {want}")
    return parse(blob), want, len(blob)


def window(df, T):
    w = df[(df.t >= T - BEFORE) & (df.t < T + AFTER)]
    return w.drop_duplicates("agg_id").sort_values(["t", "agg_id"], ignore_index=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def plan(hs):
    """HEAD every zip the windows need: their count and total size; nothing is downloaded."""
    need = sorted({(s, d) for s, T in hs for d in days_of(T)})
    sizes = {}
    for s, d in need:
        r = get(BV.format(s=s, d=d), method="HEAD")
        sizes[(s, d)] = int(r.headers.get("Content-Length", 0))
    tot = sum(sizes.values())
    big = sorted(sizes.items(), key=lambda kv: -kv[1])[:5]
    log(f"{len(hs)} hops on {len({s for s, _ in hs})} coins need {len(need)} coin-days: "
        f"{tot / 1e9:.2f} GB of zips; largest {[(f'{s} {d}', round(b / 1e6, 1)) for (s, d), b in big]} MB")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true", help="size the zips with HEAD requests; fetch nothing")
    ap.add_argument("--plumbing", action="store_true", help="count the windows and trades on disk; fetch nothing")
    a = ap.parse_args(argv)
    hs = hops()
    if a.plan:
        return plan(hs)
    if a.plumbing:
        return plumbing(hs)
    by_sym = {}
    for s, T in hs:
        by_sym.setdefault(s, []).append(T)
    old = json.loads(PROV.read_text()) if PROV.exists() else {}
    zips = dict(old.get("binance_zips", {}))
    for s in sorted(by_sym):
        todo = [T for T in by_sym[s] if not (OUT / "binance" / s / f"{T}.parquet").exists()]
        parts = {T: [] for T in todo}
        for d in sorted({d for T in todo for d in days_of(T)}):
            df, want, nbytes = binance_day(s, d)
            zips[f"{s}/{d}"] = {"sha256": want, "bytes": nbytes}
            for T in todo:
                if d in days_of(T):
                    parts[T].append(window(df, T))
            del df
        for T in todo:
            w = window(pd.concat(parts[T], ignore_index=True), T)
            p = OUT / "binance" / s / f"{T}.parquet"
            p.parent.mkdir(parents=True, exist_ok=True)
            w.to_parquet(p, index=False)
        if todo:
            log(f"{s}: {len(todo)} windows")
    files = sorted(OUT.rglob("*.parquet"))
    PROV.write_text(json.dumps({
        "folder": "data/settle_ticks",
        "source": "https://data.binance.vision USD-M daily aggTrades (each zip checked against its .CHECKSUM sha256; "
                  "the zips are not kept)",
        "script": "python -I scripts/fetch_settle_ticks.py",
        "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hops": f"{HOPS.relative_to(ROOT).as_posix()} book {BOOK!r}: {len(hs)} hops",
        "window": "[T - 10 min, T + 15 min) of each hop's settlement T",
        "zips": len(zips), "zip_bytes": sum(z["bytes"] for z in zips.values()),
        "binance_zips": dict(sorted(zips.items())),
        "files": len(files), "bytes": sum(f.stat().st_size for f in files),
        "file_hashes": [{"path": f.relative_to(ROOT).as_posix(), "sha256": sha(f)} for f in files],
    }, indent=1) + "\n")
    log(f"wrote {PROV.relative_to(ROOT)}: {len(files)} files from {len(zips)} zips")
    return plumbing(hs)


def plumbing(hs):
    """Counts only: windows on disk, trades per window, and the longest trade-free gap around T."""
    n, missing, rows, empty_after, gaps = 0, 0, [], 0, []
    for s, T in hs:
        p = OUT / "binance" / s / f"{T}.parquet"
        if not p.exists():
            missing += 1
            continue
        n += 1
        t = pd.read_parquet(p, columns=["t"]).t.to_numpy()
        rows.append(len(t))
        after = t[(t >= T) & (t < T + 5 * MIN)]
        empty_after += int(len(after) == 0)
        near = np.concatenate([[T - MIN], t[(t >= T - MIN) & (t < T + 5 * MIN)], [T + 5 * MIN]])
        gaps.append(int(np.diff(near).max()))
    if rows:
        r, g = np.array(rows), np.array(gaps) / 1000
        log(f"windows on disk {n}, missing {missing}; trades a window min {r.min()} median {int(np.median(r))} "
            f"max {r.max()}; windows without a trade in [T, T + 5 min): {empty_after}")
        log(f"longest trade-free gap in [T - 1 min, T + 5 min), seconds: median {np.median(g):.1f}, "
            f"90th pct {np.percentile(g, 90):.1f}, max {g.max():.1f}")
    else:
        log(f"windows on disk 0, missing {missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
