"""R517 hip3list_v1: R516's listing-phase carry rule, unchanged, between HIP-3 dexes that list the same ticker.

- **Venues.** Every HIP-3 dex (trade.xyz, Felix, Kinetiq, Dreamcash, EntropyIO, Paragon, ...) is a venue. Both legs
  sit on Hyperliquid, under one wallet, with no broker.
- **Book.** R516's `ListingBook` and its constants, with one change, `LAUNCH_GAP` = 0.
  - On Binance + Hyperliquid, a venue's first funding day was its data start, not a listing.
  - A HIP-3 dex's launch day opens real new books, so its first markets count as listings.
- **Data.** `scripts/fetch_hip3list.py` output in `data/hip3list`, verified against its manifest before the run.
  Daily closes from 4-hour candles; hourly funding.

usage: python scripts/run_hip3list.py events | run
- events: before the freeze. Counts eligible events from funding ages only; prints nothing computed from a rate or
  a price.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import xfund as v1  # noqa: E402
from lab import xfund_v2 as v2  # noqa: E402
from scripts import run_xfund_bfx as base  # noqa: E402  (frozen R507 runner: summarize, decide, by_year, check_inputs)
from scripts import run_xfund_listing as lst  # noqa: E402  (frozen R516 runner: ListingBook, events, report)

LANE = ROOT / "experiments" / "hip3list_v1"
DATA = ROOT / "data" / "hip3list"
START, BOOK_START = "2025-10-01", "2025-11-15"
PRIMARY = (0.20, 10)
BAR_H = 4


def table(data=None):
    u = pd.read_csv(Path(data or DATA) / "universe.csv", dtype=str).fillna("")
    dexes = sorted(u.dex.unique())
    bases = sorted(u.base.unique())
    return u, dexes, bases


def universe(end, data=None):
    data = Path(data or DATA)
    u, dexes, bases = table(data)
    t0 = int(pd.Timestamp(START, tz="UTC").value // 10**6)
    nd = int((pd.Timestamp(end, tz="UTC").value // 10**6 - t0) // v1.DAY + 1)
    have = {(r.dex, r.base) for r in u.itertuples()}
    series = []
    for b in bases:
        row = []
        for d in dexes:
            if (d, b) not in have:
                row.append(None)
                continue
            row.append(v2.load_daily(data / "prices" / f"{d}_{b}.parquet", data / "funding" / f"{d}_{b}.parquet",
                                     "volume", BAR_H, t0, nd))
        series.append(row)
    return v1.Universe(bases, dexes, series, t0, nd)


def pairs_events(u, launch):
    """lst.events for every venue pair, one row per (coin, younger venue)."""
    out = []
    for i in range(len(u.names)):
        for j in range(i + 1, len(u.names)):
            e = lst.events(u, [i, j], launch)
            if len(e):
                out.append(e)
    ev = pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=["coin", "young", "listed"])
    return ev.drop_duplicates(["coin", "young"]).reset_index(drop=True)


def check_data(data=None):
    data = Path(data or DATA)
    m = json.loads((data / "manifest.json").read_text())["files"]
    bad = [p for p, h in m.items() if hashlib.sha256((data / p).read_bytes()).hexdigest() != h]
    if bad:
        raise SystemExit(f"{len(bad)} data files differ from the manifest, e.g. {bad[:3]}")
    return len(m), json.loads((data / "manifest.json").read_text())["end"]


def setup(end, data=None):
    lst.LAUNCH_GAP = 0                      # a HIP-3 dex launch opens real new books (the PREREG's one change)
    u = universe(end, data)
    vset = list(range(len(u.names)))
    return u, vset, lst.launches(u, vset)


def run(lane=None, data=None):
    from lab.prereg import verify
    lane = Path(lane or LANE)
    verify(lane / "PREREG.md")
    base.check_inputs(lane / "PREREG.md")
    n_files, end = check_data(data)
    res = lane / "results"
    if (res / "report.json").exists():
        raise SystemExit("results exist: this lane is read once")
    u, vset, launch = setup(end, data)
    ev = pairs_events(u, launch)
    w0 = int((pd.Timestamp(BOOK_START, tz="UTC").value // 10**6 - u.t0) // v1.DAY)
    rows, tr = lst.run_book(u, vset, launch, *PRIMARY, w0)
    rep = {"window": [BOOK_START, end], "data_files_verified": n_files, "venues": u.names, "bases": len(u.keys),
           "events": int(len(ev)), "events_by_young": {str(a): int(b) for a, b in ev.young.value_counts().items()}}
    rep["primary"] = lst.report(rows, tr, PRIMARY[1], u.t0)
    rep["verdict"], rep["checks"] = base.decide(rep["primary"])
    res.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"day": rows.day, "date": pd.to_datetime(u.t0 + rows.day * v1.DAY, unit="ms").dt.date,
                  **{f"net_{m}x": v2.net(rows, PRIMARY[1], c) for m, c in zip((1, 2, 3), lst.COSTS)},
                  "gross": rows.gross, "funding": rows.funding, "legs": rows.legs, "held": rows.held}
                 ).to_csv(res / "daily.csv", index=False)
    tr.to_csv(res / "trades.csv", index=False)
    ev.to_csv(res / "events.csv", index=False)
    (res / "report.json").write_text(json.dumps(rep, indent=1, default=str))
    p = rep["primary"]
    print(json.dumps({"verdict": rep["verdict"], "checks": rep["checks"],
                      **{x: p.get(x) for x in ("n", "ann_1x_pct", "ann_2x_pct", "ann_3x_pct", "t_nw_1x", "trades",
                                               "ann_on_deployed_1x_pct", "exit_reasons")}}, default=str))
    return rep


def count(end, data=None):
    u, vset, launch = setup(end, data)
    ev = pairs_events(u, launch)
    ev["month"] = ev.listed.str[:7]
    print(ev.groupby("month").size().to_string())
    print(json.dumps({"events": len(ev), "by_young": ev.young.value_counts().to_dict()}))
    return ev


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("events", "run"))
    ap.add_argument("--end", default="2026-11-20")
    a = ap.parse_args(argv)
    count(a.end) if a.cmd == "events" else run()


if __name__ == "__main__":
    main()
