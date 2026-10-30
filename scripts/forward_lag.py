"""Processing lag of the forward lanes: how long after each hour's bar closed R200 computed its signal, and which
on-time days were scored from hours computed late (a backfill after the container or session was down).

The frozen lanes label a day "ontime" by its date alone (ON_TIME = 2026-10-20). A live trader needs the signal
within minutes of the close. This report keeps both: every lane's frozen decision is unchanged, and FINDINGS report
the strict subset (no hour computed more than LATE_MIN after its close) beside it. Derived from R200's append-only
ticks.csv (one row per hour, `run_at` written once), so it is rewritten whole on every tick; it is not a journal.

Also checks that each day-ticket lane appended its days in order without gaps, so derived rows (R221, R225) that
read them in day order cannot have been computed before an earlier day arrived.

usage: python scripts/forward_lag.py   (last step of scripts/forward_all.sh)
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import panel  # noqa: E402

OUT = ROOT / "experiments" / "forward_lag"
TICKS = ROOT / "experiments" / "flow72_fwd2" / "journal" / "ticks.csv"
DAY_LANES = {"flow72_fwd2": "tickets.csv", "flow72_fwd3": "tickets.csv", "mexc_fwd": "tickets.csv",
             "mexc_fwd_sq": "tickets.csv", "carry_fwd": "tickets.csv", "vt_fwd": "days.csv"}
ON_TIME = panel.ms("2026-10-20")
LATE_MIN = 60
H = 3_600_000
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def hour_lags(ticks):
    """Minutes from each hour's bar close (t + 1 h) to the run that first computed it."""
    run_at = (pd.to_datetime(ticks.run_at, utc=True) - pd.Timestamp(0, tz="UTC")) // pd.Timedelta(milliseconds=1)
    return (run_at.to_numpy(np.int64) - (ticks.t.to_numpy(np.int64) + H)) / 60_000


def by_day(ticks):
    t = ticks.assign(lag_min=hour_lags(ticks), day=pd.to_datetime(ticks.t, unit="ms", utc=True).dt.strftime("%Y-%m-%d"))
    g = t.groupby("day")
    d = pd.DataFrame({"hours": g.size(), "median_lag_min": g.lag_min.median(), "max_lag_min": g.lag_min.max(),
                      "hours_late": g.lag_min.apply(lambda x: int((x > LATE_MIN).sum()))}).reset_index()
    d["kind"] = np.where(pd.to_datetime(d.day, utc=True) >= pd.Timestamp(ON_TIME, unit="ms", tz="UTC"),
                         "ontime", "replay")
    d["strict_ontime"] = (d.kind == "ontime") & (d.hours == 24) & (d.hours_late == 0)
    return d


def order_check(path):
    """Per book: days appended in increasing order with no missing calendar day in between."""
    tk = pd.read_csv(path)
    bad = {}
    for book, x in tk.groupby("book", sort=False):
        days = pd.to_datetime(x.day, utc=True)
        steps = days.diff().dropna()
        out_of_order = int((steps <= pd.Timedelta(0)).sum())
        gaps = int((steps > pd.Timedelta(days=1)).sum())
        if out_of_order or gaps:
            bad[str(book)] = {"out_of_order": out_of_order, "gaps": gaps}
    return {"rows": int(len(tk)), "problems": bad}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ticks = pd.read_csv(TICKS)
    d = by_day(ticks)
    d.to_csv(OUT / "lag_by_day.csv", index=False)
    on = d[d.kind == "ontime"]
    lag = hour_lags(ticks)
    recent = lag[ticks.t.to_numpy() >= ON_TIME]
    status = {"late_threshold_min": LATE_MIN, "hours": int(len(ticks)),
              "ontime_days": int(len(on)), "strict_ontime_days": int(on.strict_ontime.sum()),
              "ontime_days_with_late_hours": on[on.hours_late > 0].day.tolist(),
              "ontime_hour_lag_min": {"n": int(len(recent)),
                                      **({"median": float(np.median(recent)), "p90": float(np.quantile(recent, 0.9)),
                                          "max": float(recent.max())} if len(recent) else {})},
              "order": {lane: order_check(ROOT / "experiments" / lane / "journal" / f)
                        for lane, f in DAY_LANES.items() if (ROOT / "experiments" / lane / "journal" / f).exists()}}
    (OUT / "status.json").write_text(json.dumps(status, indent=1))
    log(f"on-time days {status['ontime_days']}, strict {status['strict_ontime_days']}; hour lag",
        status["ontime_hour_lag_min"], "order problems:",
        {k: v["problems"] for k, v in status["order"].items() if v["problems"]} or "none")


if __name__ == "__main__":
    main()
