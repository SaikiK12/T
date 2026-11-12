"""R473 tlteom_v1, frozen in experiments/tlteom_v1/PREREG.md: the end-of-month Treasury rally (Hartley and Schwarz,
"Predictable End-of-Month Treasury Returns", 2019) as a long TLT position over the last T trading days of each month,
priced for trade.xyz's TLT perp. Gate 0 on held history.

Each complete month: buy at the close T trading days before the month's last trading day, sell at that last close.
The return is TLT's close-to-close price change (what a perp on TLT's price earns; Yahoo's close is not adjusted for
dividends). Net = gross - k x one round trip (2 x 2.9 bp) - funding paid by the long (5.5%/yr over the calendar days
held).

R (month-ends 2002-08 .. 2018-12, inside the paper's 1990-2018 sample) checks that TLT carries the effect; U
(2019-01 .. 2026-10, after it) decides. Paper only.

usage: python scripts/run_tlteom.py      the frozen run (verifies the PREREG, every input it lists and the data)
"""
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
from run_xyzwknd import frozen_inputs  # noqa: E402  (frozen in R462)

LANE = ROOT / "experiments" / "tlteom_v1"
DATA = ROOT / "data" / "tlteom"
REGISTRY = "R473"
TICKER = "TLT"
T_DAYS = 3                                          # deciding window: the last 3 trading days' returns
REPORT_T = (1, 2, 3, 5)
LEG_BP = 2.9                                        # one leg: xyz growth-mode taker 0.9 bp + 2 bp slippage
TRIP_BP = 2 * LEG_BP                                # one round trip: 5.8 bp
FUND_PCT = 5.5                                      # %/yr paid by the long (xyz stock-perp median, R470)
FUND_ALT = (0.0, 11.0)
SPANS = {"R": ("2002-08", "2018-12"), "U": ("2019-01", "2026-10")}
MIN_U = 80
T_REP = 2.0                                         # R: gross mean > 0 at t >= 2.0
T_PASS = 1.0                                        # U: 1x net mean > 0 at t >= 1.0, and 2x net mean > 0
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


def month_ends(dates):
    """Positions of each complete month's last trading day; the final month in the data counts as unfinished."""
    m = pd.to_datetime(pd.Series(dates)).dt.to_period("M").values
    last = np.r_[m[1:] != m[:-1], False]
    return np.flatnonzero(last)


def events(px, t_days=T_DAYS, col="close"):
    """One row per complete month: entry at the close t_days trading days before the last trading day, exit at it."""
    idx = month_ends(px["date"])
    idx = idx[idx - t_days >= 0]
    d = pd.to_datetime(px["date"]).values
    c = px[col].to_numpy(float)
    return pd.DataFrame({"month": pd.to_datetime(d[idx]).strftime("%Y-%m"),
                         "entry": px["date"].values[idx - t_days], "exit": px["date"].values[idx],
                         "gross": c[idx] / c[idx - t_days] - 1,
                         "cal_days": (d[idx] - d[idx - t_days]) / np.timedelta64(1, "D")})


def net(ev, k=1, fund=FUND_PCT):
    return ev["gross"] - k * TRIP_BP / 1e4 - fund / 100 * ev["cal_days"] / 365


def outside(px, t_days=T_DAYS):
    """Dividend-adjusted return from the previous month's last close to this month's entry close (the rest of the
    month), one row per complete month after the first."""
    idx = month_ends(px["date"])
    a = px["adjclose"].to_numpy(float)
    rows = [(px["date"].values[j][:7], a[j - t_days] / a[i] - 1) for i, j in zip(idx[:-1], idx[1:])]
    return pd.DataFrame(rows, columns=["month", "ret"])


def stats(x):
    x = np.asarray(x, float)
    n = len(x)
    if n < 2:
        return {"n": n, "mean_bp": math.nan, "t": math.nan}
    mu, sd = float(x.mean()), float(x.std(ddof=1))
    return {"n": n, "mean_bp": mu * 1e4, "sd_bp": sd * 1e4, "t": mu / (sd / math.sqrt(n)) if sd > 0 else math.nan,
            "sharpe_ann": mu / sd * math.sqrt(12) if sd > 0 else math.nan, "hit": float((x > 0).mean()),
            "min_bp": float(x.min()) * 1e4, "max_bp": float(x.max()) * 1e4}


def within(df, name):
    lo, hi = SPANS[name]
    return df[(df["month"] >= lo) & (df["month"] <= hi)]


def sample_stats(px, ief, name):
    ev = within(events(px), name)
    out = {"events": int(len(ev)), "mean_cal_days": float(ev["cal_days"].mean()) if len(ev) else math.nan,
           "gross": stats(ev["gross"])}
    for k in (1, 2, 3):
        out[f"net_{k}x"] = stats(net(ev, k))
    for f in FUND_ALT:
        out[f"net_1x_fund{f:g}"] = stats(net(ev, 1, f))
    out["gross_adjclose"] = stats(within(events(px, col="adjclose"), name)["gross"])
    out["windows"] = {str(t): {"gross": stats(within(events(px, t), name)["gross"]),
                               "net_1x": stats(net(within(events(px, t), name)))} for t in REPORT_T}
    e2 = within(events(ief), name)
    out["ief"] = {"gross": stats(e2["gross"]), "net_1x": stats(net(e2))}
    out["rest_of_month_adj"] = stats(within(outside(px), name)["ret"])
    ev = ev.assign(year=ev["month"].str[:4])
    out["by_year_gross_bp"] = {y: {"n": int(len(g)), "mean_bp": float(g["gross"].mean() * 1e4)}
                               for y, g in ev.groupby("year")}
    return out


def verdict(st):
    rep, u = st["R"]["gross"], st["U"]
    one, two = u["net_1x"], u["net_2x"]
    text = (f"R gross {rep['mean_bp']:+.1f} bp (t {rep['t']:.2f}, n {rep['n']}); U gross {u['gross']['mean_bp']:+.1f} "
            f"bp, net 1x {one['mean_bp']:+.1f} bp (t {one['t']:.2f}, n {one['n']}), 2x {two['mean_bp']:+.1f}")
    if u["events"] < MIN_U:
        return "INCONCLUSIVE", text
    if not (rep["mean_bp"] > 0 and rep["t"] >= T_REP):
        return "NULL", "not replicated in R: " + text
    if one["mean_bp"] > 0 and one["t"] >= T_PASS and two["mean_bp"] > 0:
        return "PASS", text
    if one["mean_bp"] > 0:
        return "PARTIAL", text
    return "NULL", text


def verify_data(data):
    man = json.loads((data / "manifest.json").read_text())
    for rel, meta in man["files"].items():
        if prereg.sha256_file(data / rel) != meta["sha256"]:
            raise SystemExit(f"manifest mismatch: {rel}")
    return len(man["files"])


def load(data, ticker):
    df = pd.read_parquet(data / "yahoo" / f"{ticker}.parquet")[["date", "close", "adjclose"]]
    return df.sort_values("date").reset_index(drop=True)


def run(lane=LANE, data=DATA, check=True):
    if check:
        digest = prereg.verify(lane / "PREREG.md")
        log(f"PREREG verified {digest[:12]}; {len(frozen_inputs(lane / 'PREREG.md'))} inputs match")
        log(f"data files verified: {verify_data(data)}")
    px, ief = load(data, TICKER), load(data, "IEF")
    st = {k: sample_stats(px, ief, k) for k in SPANS}
    state, text = verdict(st)
    res = lane / "results"
    res.mkdir(parents=True, exist_ok=True)
    ev = events(px)
    ev.assign(net_1x=net(ev), net_2x=net(ev, 2), net_3x=net(ev, 3)).to_csv(res / "events.csv", index=False)
    summary = {"registry": REGISTRY, "state": state, "text": text, "t_days": T_DAYS, "trip_bp": TRIP_BP,
               "fund_pct": FUND_PCT, "samples": st}
    (res / "summary.json").write_text(json.dumps(summary, indent=1, default=float) + "\n")
    log(state, text)
    return state


if __name__ == "__main__":
    run()
