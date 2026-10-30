"""R332 mlrank_v3: R304's ranker family again, on the daily panel rebuilt with complete Binance metrics.

R304 (`scripts/run_mlrank2.py`, frozen) passed its rule with a weekly GBM ranker, and R305 could not explain it. Its
panel (data/daily/panel.parquet) took the metrics columns (oi_usd, top_ls_pos, top_ls_acc, ls_acc, taker_ls) from
data/metrics_1h, which lab/flow.py fetched only for days when the coin was in the old research set's top 100 by volume
at some hour in that day or the next 35 days. So, in R304's universe, a row with metrics says the coin will be among
the most traded within 35 days. data/daily_v2/panel.parquet (scripts/build_daily_v2.py) is the same build with the
metrics fetched for every day a universe row reads (scripts/fetch_metrics_full.py).

The family: R304's six books (ridge, ic, gbm x hold 1, 7 days, on its 24 clean features), same code and decision rule,
on the v2 panel. Reported and counted: the presence book on the v1 panel, which ranks the universe only by whether a
row has metrics (long the rows with, short the rows without; ties in a seeded random order). Also reported: which
panel columns differ between v1 and v2.

Everything except the panel path and the presence book comes unchanged from `scripts/run_mlrank.py` and
`scripts/run_mlrank2.py`.

usage: python scripts/run_mlrank3.py [--plumbing]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402
from scripts.run_clockflow import check_inputs  # noqa: E402
from scripts.run_mlrank import (COLS, FIRST_PRED, WINDOWS, book, daily_ic, decide, legs, prepare,  # noqa: E402
                                rank_target, report, targets)
from scripts.run_mlrank2 import STRATS, analyze, build, label  # noqa: E402

LANE = ROOT / "experiments" / "mlrank_v3"
PANEL1 = ROOT / "data" / "daily" / "panel.parquet"
PANEL2 = ROOT / "data" / "daily_v2" / "panel.parquet"
METRIC_COLS = ["oi_usd", "top_ls_pos", "top_ls_acc", "ls_acc", "taker_ls"]
PRESENCE = ("presence", 7, "v1")
TRIALS = len(STRATS) + 1                                              # 7
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def load(path):
    return pd.read_parquet(path, columns=["day", "perp", *COLS])


def presence_pred(w, uni, first=FIRST_PRED):
    """(day, perp) -> 1.0 when row D has oi_usd, else 0.0, for universe rows from `first` on. Row D only."""
    has = w["oi_usd"].notna().astype(float).where(uni)
    s = has.stack(future_stack=True).dropna()
    return s[s.index.get_level_values(0) >= pd.Timestamp(first)]


def presence_book(df1, hold=7):
    w, _, uni = prepare(df1)
    pred = presence_pred(w, uni)
    ret, fund = targets(w, hold)
    y = rank_target(ret - fund, uni).stack(future_stack=True).reindex(pred.index)
    rows = book(legs(pred, hold), ret, fund)
    return rows, daily_ic(pred, y)


def column_check(df1, df2):
    """Per panel column: rows in both panels whose values differ (NaN-aware), and rows only in one panel."""
    key = ["day", "perp"]
    a = df1.assign(perp=df1.perp.astype(str)).set_index(key)
    b = df2.assign(perp=df2.perp.astype(str)).set_index(key)
    both = a.index.intersection(b.index)
    out = {"rows_v1": len(a), "rows_v2": len(b), "rows_both": len(both), "differ": {}}
    a, b = a.loc[both], b.loc[both]
    for c in a.columns:
        if c not in b:
            continue
        x, y = a[c].to_numpy(np.float64), b[c].to_numpy(np.float64)
        out["differ"][c] = int((~((x == y) | (np.isnan(x) & np.isnan(y)))).sum())
    return out


def coverage(df, top=150):
    """Share of top-`top` rows with oi_usd, by year and rank band."""
    d = df[df.rank_qvol30 <= top]
    band = pd.cut(d.rank_qvol30, [0, 50, 100, 150]).astype(str)
    g = d.oi_usd.notna().groupby([pd.to_datetime(d.day).dt.year, band], observed=True).mean()
    return {f"{y} {b}": round(float(v), 3) for (y, b), v in g.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true", help="column check and coverage only, no return read")
    a = ap.parse_args()
    if a.plumbing:
        df1, df2 = load(PANEL1), load(PANEL2)
        print(json.dumps({"columns": column_check(df1, df2), "coverage_v1": coverage(df1),
                          "coverage_v2": coverage(df2)}, indent=1))
        return
    sha = prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    df1, df2 = load(PANEL1), load(PANEL2)
    cols = column_check(df1, df2)
    log(f"columns that differ v1/v2: { {k: v for k, v in cols['differ'].items() if v} }")
    w, res, ics = build(df2, keys=STRATS)
    out = analyze(w, res, ics)
    for k, v in out["strategies"].items():
        d, va = v["disc"]["1x"], v["valid"]["1x"]
        log(f"{k}: disc net {d.get('bp_day', float('nan')):+.2f} bp/day t {d.get('t')}, valid net "
            f"{va.get('bp_day', float('nan')):+.2f} t {va.get('t')}")
    log(f"pick {out['pick']}, passes {out['pick_passes']} {out['checks']}; verdict {out['verdict']}")
    prow, pic = presence_book(df1)
    prep = report(prow, 7, pic)[0]
    for win in WINDOWS:
        log(f"presence v1 {win}: net {prep[win]['1x'].get('bp_day')} bp/day t {prep[win]['1x'].get('t')}, long "
            f"{prep[win]['long_bp']} short {prep[win]['short_bp']} bp/period")
    res_dir = LANE / "results"
    res_dir.mkdir(parents=True, exist_ok=True)
    allres = {**res, PRESENCE: prow}
    rows = [{"strategy": label(k), "t": r["t"], "gross": r["gross"], "long": r["long"], "short": r["short"],
             "n_long": r["n_long"], "n_short": r["n_short"]} for k, rs in allres.items() for r in rs]
    pd.DataFrame(rows).to_csv(res_dir / "periods.csv", index=False, float_format="%.8g")
    pd.DataFrame({label(k): v for k, v in {**ics, PRESENCE: pic}.items()}).to_csv(res_dir / "rank_ic.csv",
                                                                                   float_format="%.5f")
    import sklearn
    summary = {"rid": "R332", "verdict": out["verdict"], "trials": TRIALS, "prereg_sha256": sha, "inputs": shas,
               "sklearn": sklearn.__version__, **out, "presence_v1": prep, "columns": cols,
               "coverage_v1": coverage(df1), "coverage_v2": coverage(df2)}
    (res_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    return summary


if __name__ == "__main__":
    main()
