"""Build the daily panel again with the complete Binance metrics (data/metrics_full/metrics_1h, from
scripts/fetch_metrics_full.py) in place of data/metrics_1h, into data/daily_v2/. Same code (lab/daily.py `build`),
same sources otherwise: a shadow root in data/daily_v2_src/ links every folder of data/ except metrics_1h, which links
to the complete one. data/daily/ and data/metrics_1h stay as they are (frozen inputs of earlier lanes).

Writes panel.parquet, market.parquet, columns.csv and manifest.json as scripts/build_daily.py does, plus in the
manifest the metrics folder used. It computes no statistic on returns.

usage: nice python scripts/build_daily_v2.py [--workers 8]
"""
import argparse
import csv
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import daily, data, panel  # noqa: E402
from scripts.build_daily import provenance  # noqa: E402

SRC = data.ROOT / "daily_v2_src"
OUT = data.ROOT / "daily_v2"
METRICS = data.ROOT / "metrics_full" / "metrics_1h"
SKIP = {"metrics_1h", "daily", "daily_v2", "daily_v2_src", "raw", "live"}
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def shadow(src=SRC, base=data.ROOT, metrics=METRICS):
    """The shadow root: a link per entry of `base` (except SKIP) and metrics_1h -> `metrics`. Rebuilt each run."""
    src.mkdir(parents=True, exist_ok=True)
    for p in src.iterdir():
        if p.is_symlink():
            p.unlink()
    for p in sorted(base.iterdir()):
        if p.name not in SKIP and not p.name.startswith("."):
            os.symlink(p.resolve(), src / p.name)
    os.symlink(Path(metrics).resolve(), src / "metrics_1h")
    return src


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    root = shadow()
    df, mk, notes = daily.build(root=root, workers=a.workers, log=log)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT / "panel.parquet", index=False)
    mk.to_parquet(OUT / "market.parquet", index=False)
    with open(OUT / "columns.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["column", "source", "definition", "kind"])
        w.writerows(daily.columns())
    man = {
        "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "first_row": str(df.day.min()), "last_row": str(df.day.max()), "rows": len(df),
        "perps": int(df.perp.nunique()), "market_series": list(mk.columns[1:]),
        "panel_start": panel.START, "end": data.END, "metrics_folder": str(METRICS.relative_to(ROOT)),
        "metrics_manifest_sha256": hashlib.sha256((METRICS / "manifest.json").read_bytes()).hexdigest(),
        "lab_daily_sha256": hashlib.sha256((ROOT / "lab" / "daily.py").read_bytes()).hexdigest(),
        "panel_sha256": hashlib.sha256((OUT / "panel.parquet").read_bytes()).hexdigest(),
        "market_sha256": hashlib.sha256((OUT / "market.parquet").read_bytes()).hexdigest(),
        "inputs": provenance(), "coverage": {c: round(float(df[c].notna().mean()), 4) for c in df.columns[2:]},
        "venue_map_notes": notes,
    }
    (OUT / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    log(f"wrote {OUT}: {len(df):,} rows, {df.perp.nunique()} perps, {df.day.min()}..{df.day.max()}")


if __name__ == "__main__":
    main()
