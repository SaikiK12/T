"""Build the daily point-in-time panel (lab/daily.py): one row per (day, Binance perp) from every source the lab holds,
plus the market-wide series, into data/daily/.

Writes panel.parquet, market.parquet, columns.csv (each column's source, definition and whether it is point in time)
and manifest.json (rows, perps, coverage per column, the lab/daily.py sha256, and the combined sha256 of every input
folder that has a provenance record in docs/provenance/). It reads no reserved row (2020, long tails, MEXC-only coins)
and computes no statistic on returns.

usage: nice python scripts/build_daily.py [--end 2026-09-30] [--workers 8]
"""
import argparse
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import daily, data, panel  # noqa: E402

log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)
INPUTS = ("klines_1h", "fundingRate", "premiumIndexKlines_1h", "markPriceKlines_1h", "metrics_1h", "bookDepth_1h",
          "spot_1h", "coinm_1h", "gate_hist", "mexc_hist", "dydx_hist", "hyperliquid", "kucoin_hist", "kraken_hist",
          "upbit_hist", "bithumb_hist", "coinmetrics", "defillama", "macro")


def provenance():
    """{folder: combined sha256} from docs/provenance/, for the folders the panel reads."""
    out = {}
    for p in sorted((ROOT / "docs" / "provenance").glob("*.json")):
        rec = json.loads(p.read_text())
        name = Path(rec.get("folder", "")).name
        if name in INPUTS or p.stem in INPUTS:
            out[rec.get("folder", p.stem)] = rec.get("combined_sha256", "")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--end", default=data.END)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    df, mk, notes = daily.build(end=a.end, workers=a.workers, log=log)
    out = daily.OUT
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / "panel.parquet", index=False)
    mk.to_parquet(out / "market.parquet", index=False)
    with open(out / "columns.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["column", "source", "definition", "kind"])
        w.writerows(daily.columns())
    cover = {c: round(float(df[c].notna().mean()), 4) for c in df.columns[2:]}
    man = {
        "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "first_row": str(df.day.min()), "last_row": str(df.day.max()), "rows": len(df),
        "perps": int(df.perp.nunique()), "market_series": list(mk.columns[1:]),
        "panel_start": panel.START, "end": a.end,
        "lab_daily_sha256": hashlib.sha256((ROOT / "lab" / "daily.py").read_bytes()).hexdigest(),
        "panel_sha256": hashlib.sha256((out / "panel.parquet").read_bytes()).hexdigest(),
        "market_sha256": hashlib.sha256((out / "market.parquet").read_bytes()).hexdigest(),
        "inputs": provenance(), "coverage": cover, "venue_map_notes": notes,
    }
    (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    log(f"wrote {out}: {len(df):,} rows, {df.perp.nunique()} perps, {df.day.min()}..{df.day.max()}, "
        f"{(out / 'panel.parquet').stat().st_size / 1e6:.0f} MB")


if __name__ == "__main__":
    main()
