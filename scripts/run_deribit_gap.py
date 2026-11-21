"""R519 deribitgap_v1: the funding-design gap between Deribit's linear USDC perps and Hyperliquid, held statically.

- **Design.** Hyperliquid's funding is the premium plus a clamp toward 0.01%/8 h (10.95%/yr), so when the premium is
  small its longs pay the floor. Deribit's is max(0.025%, P) + min(-0.025%, P) per 8 h: zero inside a ±0.025% dead
  zone, with no interest term. So on the same coin, a long on Deribit and a short on Hyperliquid collect about the
  floor. This is R507/R508's gap on liquid coins.
- **Primary book (fit to a constant gap, lesson L009).** `StaticBook`, R275's engine (`lab.xfund_v2`) with:
  - lookback 30 days, entry at a spread of at least 0 (the paying side shorted), 20 slots, widest first;
  - no exit on the spread. Exits only on a dead leg or a 20% ratio blowout.
  So a pair is entered once and held.
- **Secondary (reported):** R275's book unchanged (L14d th5% K20) on the same pair.
- **Data.** Deribit fetched after the freeze (`scripts/fetch_deribit_perps.py`, verified against its manifest);
  Hyperliquid held (`data/hyperliquid`, rebuilt 2026-11-18). Bases are matched by name; HL's k-coins (kPEPE) match
  Deribit's 1000-prefixed names (1000PEPE).

usage: python scripts/run_deribit_gap.py run
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import xfund as v1  # noqa: E402
from lab import xfund_v2 as v2  # noqa: E402
from scripts import run_xfund_bfx as base  # noqa: E402  (frozen R507 runner: decide, check_inputs)
from scripts import run_xfund_listing as lst  # noqa: E402  (frozen R516 runner: report, COSTS)

LANE = ROOT / "experiments" / "deribitgap_v1"
DER = ROOT / "data" / "deribit_perps"
HL = ROOT / "data" / "hyperliquid"
START, END = "2023-05-01", "2026-11-17"
PRIMARY = (30, 0.0, 20)
SECONDARY = (14, 0.05, 20)


class StaticBook(v2.Book):
    def exits(self, u, d, forced_fn=None):
        out, keep = [], []
        for p in self.open:
            a, h = u.series[p.coin][p.lo], u.series[p.coin][p.hi]
            reason = None
            if a.last_fresh < d or h.last_fresh < d:
                reason = "dead"
            elif v2.ratio_move(a, h, p, d) > math.log1p(self.blowout):
                reason = "blowout"
            (out.append((p, reason)) if reason else keep.append(p))
        self.open = keep
        return out


def hl_name(base_):
    return "k" + base_[4:] if base_.startswith("1000") and len(base_) > 4 else base_


def table(der=None, hl=None):
    der, hl = Path(der or DER), Path(hl or HL)
    have = {p.stem for p in (hl / "funding").glob("*.parquet")} & {p.stem for p in (hl / "candles_1d").glob("*.parquet")}
    rows = []
    for p in sorted((der / "funding").glob("*.parquet")):
        h = hl_name(p.stem)
        if h in have and (der / "prices" / p.name).exists():
            rows.append({"key": p.stem, "deribit": p.stem, "hyperliquid": h})
    return pd.DataFrame(rows, columns=["key", "deribit", "hyperliquid"])


def universe(der=None, hl=None, start=START, end=END):
    der, hl = Path(der or DER), Path(hl or HL)
    t0 = int(pd.Timestamp(start, tz="UTC").value // 10**6)
    nd = int((pd.Timestamp(end, tz="UTC").value // 10**6 - t0) // v1.DAY + 1)
    sym = table(der, hl)
    series = [[v2.load_daily(der / "prices" / f"{r.deribit}.parquet", der / "funding" / f"{r.deribit}.parquet",
                             "volume", 24, t0, nd),
               v2.load_daily(hl / "candles_1d" / f"{r.hyperliquid}.parquet", hl / "funding" / f"{r.hyperliquid}.parquet",
                             "volume", 24, t0, nd)] for r in sym.itertuples()]
    return v1.Universe(sym.key.tolist(), ["deribit", "hyperliquid"], series, t0, nd), sym


def book(u, l, th, k, static):
    vset = [0, 1]
    b = (StaticBook if static else v2.Book)(vset, l, th, k)
    rows, trades = v2.replay(u, b, v2.window_start(u, vset, l))
    tr = pd.DataFrame(trades)
    if len(tr):
        tr["gross"] = tr.price_pnl + tr.funding_pnl
        tr["funding"] = tr.funding_pnl
    else:
        tr = pd.DataFrame(columns=["coin", "long", "short", "gross", "funding", "reason", "entry_day", "exit_day"])
    return rows, tr


def check_data(der=None):
    der = Path(der or DER)
    m = json.loads((der / "manifest.json").read_text())["files"]
    bad = [p for p, h in m.items() if hashlib.sha256((der / p).read_bytes()).hexdigest() != h]
    if bad:
        raise SystemExit(f"{len(bad)} data files differ from the manifest, e.g. {bad[:3]}")
    return len(m)


def check_hl(lane):
    m = json.loads((lane / "hl_manifest.json").read_text())["files"]
    bad = [p for p, h in m.items() if hashlib.sha256((ROOT / "data" / p).read_bytes()).hexdigest() != h]
    if bad:
        raise SystemExit(f"{len(bad)} Hyperliquid files differ from hl_manifest.json, e.g. {bad[:3]}")
    return len(m)


def run(lane=None):
    from lab.prereg import verify
    lane = Path(lane or LANE)
    verify(lane / "PREREG.md")
    base.check_inputs(lane / "PREREG.md")
    n = check_data()
    n_hl = check_hl(lane)
    res = lane / "results"
    if (res / "report.json").exists():
        raise SystemExit("results exist: this lane is read once")
    u, sym = universe()
    rows, tr = book(u, *PRIMARY, static=True)
    rep = {"window": [START, END], "deribit_files_verified": n, "hl_files_verified": n_hl, "coins": len(sym)}
    rep["primary"] = lst.report(rows, tr, PRIMARY[2], u.t0)
    if len(rows):
        rep["primary"]["first_date"] = str(pd.Timestamp(u.t0 + int(rows.day.iloc[0]) * v1.DAY, unit="ms").date())
    rep["verdict"], rep["checks"] = base.decide(rep["primary"])
    r2, t2 = book(u, *SECONDARY, static=False)
    rep["secondary_r275"] = lst.report(r2, t2, SECONDARY[2], u.t0)
    res.mkdir(parents=True, exist_ok=True)
    sym.to_csv(res / "symbols.csv", index=False)
    pd.DataFrame({"day": rows.day, "date": pd.to_datetime(u.t0 + rows.day * v1.DAY, unit="ms").dt.date,
                  **{f"net_{m}x": v2.net(rows, PRIMARY[2], c) for m, c in zip((1, 2, 3), lst.COSTS)},
                  "gross": rows.gross, "funding": rows.funding, "legs": rows.legs, "held": rows.held}
                 ).to_csv(res / "daily.csv", index=False)
    tr.to_csv(res / "trades.csv", index=False)
    (res / "report.json").write_text(json.dumps(rep, indent=1, default=str))
    p = rep["primary"]
    print(json.dumps({"verdict": rep["verdict"], "checks": rep["checks"],
                      **{x: p.get(x) for x in ("n", "ann_1x_pct", "ann_2x_pct", "ann_3x_pct", "t_nw_1x", "trades",
                                               "avg_held", "calendar_ann_pct", "by_year_1x_calendar")}}, default=str))
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("run",))
    ap.parse_args(argv)
    run()


if __name__ == "__main__":
    main()
