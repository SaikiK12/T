"""R519's read with Deribit prices from hourly bars (closes at 00:00 UTC), everything else from the frozen
`run_deribit_gap.py`. See experiments/deribitgap_v1/DEVIATIONS.md.

usage: python scripts/run_deribit_gap_h1.py run
"""
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import xfund as v1  # noqa: E402
from lab import xfund_v2 as v2  # noqa: E402
from scripts import run_deribit_gap as g  # noqa: E402  (frozen R519 runner)
from scripts import run_xfund_bfx as base  # noqa: E402
from scripts import run_xfund_listing as lst  # noqa: E402


def universe(der=None, hl=None, start=g.START, end=g.END):
    der, hl = Path(der or g.DER), Path(hl or g.HL)
    t0 = int(pd.Timestamp(start, tz="UTC").value // 10**6)
    nd = int((pd.Timestamp(end, tz="UTC").value // 10**6 - t0) // v1.DAY + 1)
    sym = g.table(der, hl)
    sym = sym[[(der / "prices_1h" / f"{k}.parquet").exists() for k in sym.deribit]].reset_index(drop=True)
    series = [[v2.load_daily(der / "prices_1h" / f"{r.deribit}.parquet", der / "funding" / f"{r.deribit}.parquet",
                             "volume", 1, t0, nd),
               v2.load_daily(hl / "candles_1d" / f"{r.hyperliquid}.parquet", hl / "funding" / f"{r.hyperliquid}.parquet",
                             "volume", 24, t0, nd)] for r in sym.itertuples()]
    return v1.Universe(sym.key.tolist(), ["deribit", "hyperliquid"], series, t0, nd), sym


def check_h1(der=None):
    out = Path(der or g.DER) / "prices_1h"
    m = json.loads((out / "manifest.json").read_text())["files"]
    bad = [p for p, h in m.items() if hashlib.sha256((out / p).read_bytes()).hexdigest() != h]
    if bad:
        raise SystemExit(f"{len(bad)} hourly files differ from their manifest")
    return len(m)


def run():
    from lab.prereg import verify
    lane = g.LANE
    verify(lane / "PREREG.md")
    base.check_inputs(lane / "PREREG.md")
    n, n_hl, n_h1 = g.check_data(), g.check_hl(lane), check_h1()
    res = lane / "results"
    if (res / "report.json").exists():
        raise SystemExit("results exist: this lane is read once")
    u, sym = universe()
    rows, tr = g.book(u, *g.PRIMARY, static=True)
    rep = {"window": [g.START, g.END], "deribit_files_verified": n, "hl_files_verified": n_hl,
           "deribit_hourly_files_verified": n_h1, "coins": len(sym), "loader": "run_deribit_gap_h1 (DEVIATIONS)"}
    rep["primary"] = lst.report(rows, tr, g.PRIMARY[2], u.t0)
    if len(rows):
        rep["primary"]["first_date"] = str(pd.Timestamp(u.t0 + int(rows.day.iloc[0]) * v1.DAY, unit="ms").date())
    rep["verdict"], rep["checks"] = base.decide(rep["primary"])
    r2, t2 = g.book(u, *g.SECONDARY, static=False)
    rep["secondary_r275"] = lst.report(r2, t2, g.SECONDARY[2], u.t0)
    res.mkdir(parents=True, exist_ok=True)
    sym.to_csv(res / "symbols.csv", index=False)
    pd.DataFrame({"day": rows.day, "date": pd.to_datetime(u.t0 + rows.day * v1.DAY, unit="ms").dt.date,
                  **{f"net_{m}x": v2.net(rows, g.PRIMARY[2], c) for m, c in zip((1, 2, 3), lst.COSTS)},
                  "gross": rows.gross, "funding": rows.funding, "legs": rows.legs, "held": rows.held}
                 ).to_csv(res / "daily.csv", index=False)
    tr.to_csv(res / "trades.csv", index=False)
    t2.to_csv(res / "trades_secondary.csv", index=False)
    (res / "report.json").write_text(json.dumps(rep, indent=1, default=str))
    p = rep["primary"]
    print(json.dumps({"verdict": rep["verdict"], "checks": rep["checks"],
                      **{x: p.get(x) for x in ("n", "ann_1x_pct", "ann_2x_pct", "ann_3x_pct", "t_nw_1x", "trades",
                                               "avg_held", "calendar_ann_pct", "by_year_1x_calendar")}}, default=str))
    return rep


if __name__ == "__main__":
    if sys.argv[1:] != ["run"]:
        raise SystemExit("usage: python scripts/run_deribit_gap_h1.py run")
    run()
