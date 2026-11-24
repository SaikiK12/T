"""R528 closing_momentum_v1: intraday momentum into the US cash close on E-mini S&P 500 futures, as set out in
experiments/closing_momentum_v1/PREREG.md. Paper only.

The payer (Baltussen, Da, Lammers and Martens, JFE 2021): leveraged ETFs and short-gamma option dealers must trade in
the direction of the day's move near the close, so the day's move predicts the last part of the session. Gao, Han, Li
and Zhou (JFE 2018) found the first half hour (previous close to 10:00 ET) predicts the last half hour.

Data: Databento GLBX.MDP3 ohlcv-1h for ES.v.0 (the volume-leading contract), 2010-06-06..2026-11-20, in
data/databento/es_1h/. Bars are labelled by their open time (UTC); New York hours are whole UTC hours, so the bar
opening at 15:00 New York time closes at 16:00, the cash close.

Per New York trading day d, from closes C at 10:00, 15:00 and 16:00 New York time, and the previous trading day's 16:00:
- **A (Gao):** s = sign(ln C10/C16_prev), held from 15:00 to 16:00;
- **B (Baltussen):** s = sign(ln C15/C16_prev), held from 15:00 to 16:00;
- **Trade return:** s ln(C16/C15) minus the round-trip cost, on notional.
- A day counts only if the four bars exist and carry the same instrument_id (no roll inside the signal or the hold).
  A zero signal is flat.

usage: python scripts/run_closing_momentum.py run
"""
import json
import math
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab.stats import newey_west_t  # noqa: E402

LANE = ROOT / "experiments" / "closing_momentum_v1"
DATA = ROOT / "data" / "databento" / "es_1h"
NY = ZoneInfo("America/New_York")
COSTS = (0.0001, 0.0002, 0.0003)        # round trip on notional: MES fees and one tick, 1x/2x/3x
SPLIT = pd.Timestamp("2018-01-01")      # decided period from here (after Gao et al.'s publication)
T_MIN = 2.8


def load(folder=DATA):
    import pyarrow.csv as pc
    import pyarrow as pa
    parts = []
    for p in sorted(folder.glob("*ohlcv-1h*.csv.zst")):
        parts.append(pc.read_csv(pa.input_stream(str(p), compression="zstd")).to_pandas())
    if not parts:
        raise SystemExit(f"no ohlcv-1h files in {folder}")
    df = pd.concat(parts, ignore_index=True)
    df["ts"] = pd.to_datetime(df["ts_event"], utc=True)
    return df[["ts", "instrument_id", "close"]].drop_duplicates("ts").sort_values("ts", ignore_index=True)


def closes(bars):
    """One row per New York date: (instrument_id, close) at 10:00, 15:00 and 16:00 New York time (bar close)."""
    t = bars.ts + pd.Timedelta(hours=1)                    # bar close time
    ny = t.dt.tz_convert(NY)
    out = pd.DataFrame({"date": ny.dt.date, "hour": ny.dt.hour, "minute": ny.dt.minute,
                        "inst": bars.instrument_id, "close": bars.close})
    out = out[(out.minute == 0) & out.hour.isin([10, 15, 16])]
    wide = out.pivot_table(index="date", columns="hour", values=["close", "inst"], aggfunc="last")
    wide.columns = [f"{a}{b}" for a, b in wide.columns]
    return wide.sort_index()


def trades(wide, cost):
    """Per day: the two rules' net returns and the target return, on days where all four bars share one contract."""
    w = wide.copy()
    w["close16_prev"], w["inst16_prev"] = w.close16.shift(1), w.inst16.shift(1)
    ok = w[["close10", "close15", "close16", "close16_prev"]].notna().all(axis=1)
    ok &= (w.inst10 == w.inst16_prev) & (w.inst15 == w.inst16_prev) & (w.inst16 == w.inst16_prev)
    w = w[ok]
    target = np.log(w.close16 / w.close15)
    sa = np.sign(np.log(w.close10 / w.close16_prev))
    sb = np.sign(np.log(w.close15 / w.close16_prev))
    return pd.DataFrame({"target": target, "A": sa * target - cost * (sa != 0), "B": sb * target - cost * (sb != 0),
                         "sA": sa, "sB": sb}).set_axis(pd.DatetimeIndex(pd.to_datetime(w.index.astype(str))))


def stats(x):
    x = np.asarray(x, float)
    n = len(x)
    if n < 20:
        return {"n": n}
    return {"n": n, "mean_bp": float(x.mean() * 1e4), "ann_pct_on_notional": float(x.mean() * 252 * 100),
            "nw_t": float(newey_west_t(x, 5)[2]), "hit": float((x > 0).mean()),
            "sharpe_ann": float(x.mean() / x.std() * math.sqrt(252)) if x.std() > 0 else None}


def decide(oos1, oos2, halves):
    """A rule PASSES if, on 2018-01..2026-11 at 1x cost, NW t >= 2.8, the 2x-cost mean > 0 and both halves > 0."""
    checks = {"t_ge_2.8": (oos1.get("nw_t") or 0) >= T_MIN, "mean_2x_pos": (oos2.get("mean_bp") or 0) > 0,
              "both_halves_pos": min(halves) > 0}
    return ("PASS" if all(checks.values()) else "FAIL"), checks


def run(lane=LANE):
    from lab.prereg import verify
    from scripts import run_xfund_bfx as base   # its check_inputs
    verify(lane / "PREREG.md")
    base.check_inputs(lane / "PREREG.md")
    res = lane / "results"
    if (res / "report.json").exists():
        raise SystemExit("results exist: this lane is read once")
    wide = closes(load())
    rep = {"days_with_bars": int(len(wide)), "rules": {}}
    tr = {c: trades(wide, c) for c in COSTS}
    t1 = tr[COSTS[0]]
    rep["days_scored"] = int(len(t1))
    rep["target_sd_bp"] = float(t1.target.std() * 1e4)
    for rule in ("A", "B"):
        r = {}
        for name, lo, hi in (("discovery_2010_2017", None, SPLIT), ("decided_2018_2026", SPLIT, None)):
            seg = {}
            for c in COSTS:
                x = tr[c][rule]
                x = x[(x.index >= lo) if lo is not None else slice(None)]
                x = x[(x.index < hi)] if hi is not None else x
                seg[f"{round(c * 1e4)}bp"] = stats(x)
            r[name] = seg
        o = tr[COSTS[0]][rule]
        o = o[o.index >= SPLIT]
        h = len(o) // 2
        halves = [float(o.iloc[:h].mean() * 1e4), float(o.iloc[h:].mean() * 1e4)]
        r["decided_halves_mean_bp"] = halves
        r["by_year_mean_bp_1x"] = {int(y): float(g.mean() * 1e4) for y, g in tr[COSTS[0]][rule].groupby(
            tr[COSTS[0]][rule].index.year)}
        r["corr_signal_target"] = float(np.corrcoef(t1["s" + rule], t1.target)[0, 1])
        r["verdict"], r["checks"] = decide(r["decided_2018_2026"]["1bp"], r["decided_2018_2026"]["2bp"], halves)
        rep["rules"][rule] = r
    res.mkdir(parents=True, exist_ok=True)
    t1.to_csv(res / "daily_1bp.csv")
    (res / "report.json").write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps({k: {"verdict": v["verdict"], "checks": v["checks"],
                          "decided_1bp": v["decided_2018_2026"]["1bp"], "by_year": v["by_year_mean_bp_1x"]}
                      for k, v in rep["rules"].items()}, indent=1, default=str))
    return rep


if __name__ == "__main__":
    if sys.argv[1:] != ["run"]:
        raise SystemExit("usage: python scripts/run_closing_momentum.py run")
    run()
