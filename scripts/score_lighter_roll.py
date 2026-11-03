"""R389 lighter_roll_fwd: does Lighter's BRENTOIL book lag the documented index roll steps? (M462, SRC1103-014)

Lighter's BRENTOIL index moves from the front to the next ICE month in five 20% steps, one on each of London business
days 5-9, at 23:59 London (the docs table says 7:00 PM ET, one minute later). Each step day's window opens at
23:29 UTC and closes at 00:30 UTC the next day: both stamps fall inside it, in November-March, when London is UTC and
New York is UTC-5.

Per month:
1. **Step 1 sets the direction.** d = sign of the jump in (index - mid) across step 1: the median over
   [23:50, 23:58] UTC against the median over [00:02, 00:10] UTC. Step 1 itself is never traded.
2. **Steps 2-5 are paper trades** in direction d.
   - Entry: the touch at 23:29 UTC (the ask for a long, the bid for a short), from the last market_stats row at or
     before it.
   - Exit: the touch at 00:30 UTC.
   - Funding: -d x Lighter's hourly settlement at 00:00 UTC. Lighter reports it in percent.
   - Gross, funding, cost and net are reported in bp of the entry mid.
3. **Stale data is missing, never filled.** A missing row, or a row older than STALE_S at an instant, makes that step
   missing. It is reported and not scored.

Paper only. This reads `data/lighter_index` (scripts/record_lighter_index.py) and places nothing.
usage: python scripts/score_lighter_roll.py [--through YYYY-MM-DD]
"""
import argparse
import datetime as dt
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402
from scripts import record_lighter_index as rec  # noqa: E402

LANE = ROOT / "experiments/lighter_roll_fwd"
SYMBOL = "BRENTOIL"
CONTROL = "WTI"
FIRST_MONTH = (2026, 11)
LAST_MONTH = (2027, 5)
# England and Wales bank holidays in the lane's calendar (gov.uk)
UK_HOLIDAYS = {dt.date(2026, 12, 25), dt.date(2026, 12, 28), dt.date(2027, 1, 1), dt.date(2027, 3, 26),
               dt.date(2027, 3, 29), dt.date(2027, 5, 3), dt.date(2027, 5, 31)}
STALE_S = 60
MIN_STEPS = 20
T_BAR = 2.0
MINUTE = 60_000_000  # microseconds


def business_days(year, month):
    d, out = dt.date(year, month, 1), []
    while d.month == month:
        if d.weekday() < 5 and d not in UK_HOLIDAYS:
            out.append(d)
        d += dt.timedelta(days=1)
    return out


def step_days(year, month):
    """London business days 5-9 of the month."""
    return business_days(year, month)[4:9]


def months(first=FIRST_MONTH, last=LAST_MONTH):
    y, m = first
    while (y, m) <= last:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def us(day, hh, mm):
    return int(dt.datetime(day.year, day.month, day.day, hh, mm, tzinfo=dt.timezone.utc).timestamp() * 1e6)


def rows(sym, day, out=rec.OUT):
    """Recorder rows of `day` and the next UTC day, in receive order."""
    parts = [rec.load(sym, str(d), out) for d in (day, day + dt.timedelta(days=1))]
    parts = [p for p in parts if p is not None and len(p)]
    if not parts:
        return None
    return pd.concat(parts, ignore_index=True).sort_values("t", kind="stable").reset_index(drop=True)


def at(df, t_us):
    """The last row at or before t_us that is no older than STALE_S, or None."""
    if df is None:
        return None
    i = int(np.searchsorted(df["t"].to_numpy(), t_us, side="right")) - 1
    if i < 0 or t_us - int(df["t"].iloc[i]) > STALE_S * 1_000_000:
        return None
    return df.iloc[i]


def basis_median(df, lo, hi):
    w = df[(df["t"] >= lo) & (df["t"] <= hi)] if df is not None else None
    if w is None or len(w) < 60:
        return math.nan
    b = (w["index"] - w["mid"]).to_numpy(dtype=float)
    b = b[np.isfinite(b)]
    return float(np.median(b)) if len(b) >= 60 else math.nan


def step_jump(df, day):
    """Change in (index - mid) across the step day's window: median [00:02, 00:10] next day minus [23:50, 23:58]."""
    nxt = day + dt.timedelta(days=1)
    before = basis_median(df, us(day, 23, 50), us(day, 23, 58))
    after = basis_median(df, us(nxt, 0, 2), us(nxt, 0, 10))
    return after - before


def settlement(df, t_us):
    """Lighter's settlement stamped at t_us (00:00 UTC), as a fraction, from the first row after it carrying it."""
    if df is None:
        return math.nan
    w = df[(df["t"] >= t_us) & (df["t"] <= t_us + 10 * MINUTE)]
    hit = w[w["funding_ts"] // 1000 == t_us // 1_000_000]
    return float(hit["funding_rate"].iloc[0]) / 100 if len(hit) else math.nan


def trade(df, day, d, m):
    """One paper trade of the step on `day` in direction d. Returns a dict, or None when an instant is stale."""
    nxt = day + dt.timedelta(days=1)
    t_in, t_out, t_pre, t_fund = us(day, 23, 29), us(nxt, 0, 30), us(day, 23, 58), us(nxt, 0, 0)
    a, b, p = at(df, t_in), at(df, t_out), at(df, t_pre)
    if a is None or b is None or p is None:
        return None
    vals = [a["bid"], a["ask"], b["bid"], b["ask"], p["mid"]]
    if not all(np.isfinite(vals)) or min(vals) <= 0:
        return None
    mid_in, mid_out = (a["bid"] + a["ask"]) / 2, (b["bid"] + b["ask"]) / 2
    half = ((a["ask"] - a["bid"]) / 2 / mid_in + (b["ask"] - b["bid"]) / 2 / mid_in) * 1e4
    gross = d * (mid_out - mid_in) / mid_in * 1e4
    rate = settlement(df, t_fund)
    fund = -d * rate * 1e4 if np.isfinite(rate) else 0.0
    return dict(day=str(day), d=d, gross_bp=gross, pre_bp=d * (p["mid"] - mid_in) / mid_in * 1e4,
                cost_side_bp=half / 2, funding_bp=fund, funding_known=bool(np.isfinite(rate)),
                net_bp=gross + fund - m * half, jump=step_jump(df, day))


def score(through, out=rec.OUT):
    """All months whose step 5 window has closed by `through` (a date)."""
    steps, missing, months_out = [], [], []
    for y, mo in months():
        days = step_days(y, mo)
        if days[-1] + dt.timedelta(days=1) > through:
            break
        frames = {day: rows(SYMBOL, day, out) for day in days}
        j1 = step_jump(frames[days[0]], days[0])
        jumps = [step_jump(frames[day], day) for day in days]
        d = int(np.sign(j1)) if np.isfinite(j1) and j1 != 0 else 0
        months_out.append(dict(month=f"{y}-{mo:02d}", step_days=[str(x) for x in days], d=d,
                               jumps=[None if not np.isfinite(x) else x for x in jumps]))
        if d == 0:
            missing += [dict(day=str(x), why="no step-1 direction") for x in days[1:]]
            continue
        for day in days[1:]:
            t1 = trade(frames[day], day, d, 1)
            if t1 is None:
                missing.append(dict(day=str(day), why="stale or missing touch"))
                continue
            t1["month"] = f"{y}-{mo:02d}"
            steps.append(t1)
    return steps, missing, months_out


def decide(steps, months_out):
    """Mechanism stop on the first month, then the 20-step decision."""
    first = months_out[0] if months_out else None
    if first is not None:
        signs = {int(np.sign(x)) for x in first["jumps"] if x is not None and x != 0}
        if len([x for x in first["jumps"] if x is not None]) == 5 and len(signs) > 1:
            return "NULL", "the first month's five index-minus-mid jumps do not share one sign: no documented step"
    if len(steps) < MIN_STEPS:
        return "PENDING", f"{len(steps)} of {MIN_STEPS} traded steps"
    s = steps[:MIN_STEPS]
    net = np.array([x["net_bp"] for x in s])
    half = np.array([x["cost_side_bp"] * 2 for x in s])
    gross = np.array([x["gross_bp"] for x in s])
    pre = np.array([x["pre_bp"] for x in s])
    t = net.mean() / (net.std(ddof=1) / math.sqrt(len(net))) if net.std(ddof=1) > 0 else 0.0
    checks = {"t_1x": t >= T_BAR, "mean_2x": (net - half).mean() > 0,
              "book_not_early": gross.mean() > 0 and pre.mean() < 0.5 * gross.mean()}
    return ("PASS" if all(checks.values()) else "NULL"), json.dumps({k: bool(v) for k, v in checks.items()})


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--through", default=None, help="score months whose steps closed by this date (default today)")
    a = p.parse_args()
    prereg.verify(LANE / "PREREG.md")
    through = dt.date.fromisoformat(a.through) if a.through else dt.datetime.now(dt.timezone.utc).date()
    steps, missing, months_out = score(through)
    verdict, why = decide(steps, months_out)
    net = [x["net_bp"] for x in steps]
    summary = dict(verdict=verdict, why=why, traded=len(steps), missing=missing, months=months_out,
                   mean_net_bp={f"{m}x": (float(np.mean([x["gross_bp"] + x["funding_bp"] - m * 2 * x["cost_side_bp"]
                                                           for x in steps])) if steps else None) for m in (1, 2, 3)},
                   mean_net_1x_bp=float(np.mean(net)) if net else None)
    (LANE / "results").mkdir(parents=True, exist_ok=True)
    pd.DataFrame(steps).to_csv(LANE / "results/steps.csv", index=False)
    (LANE / "results/summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n")
    print(json.dumps(dict(verdict=verdict, why=why, traded=len(steps), missing=len(missing))))


if __name__ == "__main__":
    main()
