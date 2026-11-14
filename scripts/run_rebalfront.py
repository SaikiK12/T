"""R472 rebalfront_v1, frozen in experiments/rebalfront_v1/PREREG.md: front-running balanced-fund rebalancing
(Harvey, Mazzoleni and Melone, NBER w33554), rebuilt on public ETF closes. Gate 0 on held history.

A simulated 60/40 stock/bond portfolio drifts with SPY's and IEF's daily total returns.
- Threshold signal: the mean over bands d = 0.0%, 0.1%, ..., 2.5% of the drifted equity weight minus 60%, where the
  d-portfolio resets to 60% once its weight is d or more away from it (Appendix B, eq. B.1).
- Calendar signal: the same drift for a portfolio that resets on the last trading day of each month (eq. B.2).
- Strategy (Section 4, Table 6): position w_t = mean(-Threshold_t / 1.5%, CalMod_t) in (stocks minus bonds), held
  from close t to close t + 1. CalMod_t = sign(-Calendar_t) on the last five trading days of a month,
  sign(Calendar on the month's 4th-last trading day) on the next month's first trading day, else 0.

R (2002-09-03 .. 2023-03-17, the paper's published span) checks the construction; U (2023-03-20 .. 2026-11-11, after
it) decides. Paper only.

usage: python scripts/run_rebalfront.py      the frozen run (verifies the PREREG, every input it lists and the data)
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
from lab.stats import newey_west_t  # noqa: E402
from run_xyzwknd import frozen_inputs  # noqa: E402  (frozen in R462)

LANE = ROOT / "experiments" / "rebalfront_v1"
DATA = ROOT / "data" / "rebalfront"
REGISTRY = "R472"
TARGET = 0.60
DELTAS = tuple(i / 1000 for i in range(26))       # 0.0% .. 2.5%
THR_SCALE = 0.015                                  # the paper's rescaling of the Threshold signal
WEEK4 = 5                                          # last five trading days of a month
DAY_M4 = 4                                         # the 4th-last trading day, read on the next month's first day
LEG_BP = 2.9                                       # one leg, one unit of notional traded: 0.9 bp fee + 2 bp slippage
BOND_RATIO = 0.45                                  # TLT notional per unit of IEF exposure (duration ~7.3 / ~16.5)
UNIT_BP = LEG_BP * (1 + BOND_RATIO)                # cost of one unit of |change in w| on both legs: 4.2 bp
NW_LAG = 5
SPANS = {"R": ("2002-09-03", "2023-03-17"), "U": ("2023-03-20", "2026-11-11"), "U2026": ("2026-01-02", "2026-11-11")}
MIN_U_DAYS = 800
T_REP = -2.0                                       # replication: both signal slopes at t <= -2.0 in R
T_PASS = 1.0                                       # U: one-sided t of the 1x net mean
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


class Signals:
    """Incremental Threshold and Calendar signals; step() takes one day's stock and bond returns."""

    def __init__(self):
        self.wt = np.full(len(DELTAS), TARGET)
        self.wc = TARGET

    @staticmethod
    def drift(w, rs, rb):
        a = w * (1 + rs)
        return a / (a + (1 - w) * (1 + rb))

    def step(self, rs, rb, month_end):
        """Signals at today's close (pre-reset drift), then the resets that today's close triggers."""
        dt = self.drift(self.wt, rs, rb)
        thr = float(np.mean(dt - TARGET))
        self.wt = np.where(np.abs(dt - TARGET) >= np.array(DELTAS) - 1e-15, TARGET, dt)
        dc = self.drift(self.wc, rs, rb)
        cal = float(dc - TARGET)
        self.wc = TARGET if month_end else dc
        return thr, cal


def calendar(dates):
    """Trading days left in each date's month, counting itself (1 = the month's last trading day)."""
    m = pd.to_datetime(pd.Series(dates)).dt.to_period("M").values
    left = np.zeros(len(dates), int)
    run = 0
    for i in range(len(dates) - 1, -1, -1):
        run = run + 1 if i + 1 < len(dates) and m[i + 1] == m[i] else 1
        left[i] = run
    first = np.r_[True, m[1:] != m[:-1]]
    return left, first


def build(frame):
    """frame: date, rs, rb (daily total returns), rf (daily T-bill). Adds thr, cal, calmod, w."""
    df = frame.reset_index(drop=True).copy()
    n = len(df)
    left, first = calendar(df["date"])
    # A month counts only once a later month is in the data; the last, unfinished month has no month end or week4.
    complete = np.arange(n) + left < n
    month_end, week4 = (left == 1) & complete, (left <= WEEK4) & complete
    sig = Signals()
    thr, cal = np.zeros(n), np.zeros(n)
    for i, (rs, rb) in enumerate(zip(df["rs"].values, df["rb"].values)):
        thr[i], cal[i] = sig.step(rs, rb, month_end[i])
    calmod = np.zeros(n)
    m4 = np.nan
    for i in range(n):
        if first[i] and i > 0 and np.isfinite(m4):
            calmod[i] = np.sign(m4)
            m4 = np.nan
        if week4[i]:
            calmod[i] = np.sign(-cal[i])
        if left[i] == DAY_M4 and complete[i]:
            m4 = cal[i]
    df["thr"], df["cal"], df["calmod"], df["left"], df["first"] = thr, cal, calmod, left, first
    df["week4"] = week4.astype(float)
    df["w"] = 0.5 * (-df["thr"] / THR_SCALE + df["calmod"])
    return df


def returns(df):
    """Next-day outcomes aligned on the signal day t: x = stocks minus bonds from t to t + 1."""
    out = df.copy()
    out["x_next"] = (df["rs"] - df["rb"]).shift(-1)
    out["e_next"] = (df["rs"] - df["rf"]).shift(-1)
    dw = df["w"].diff().abs()
    dw.iloc[0] = abs(df["w"].iloc[0])
    out["turn"] = dw
    out["gross"] = df["w"] * out["x_next"]
    out["eq_gross"] = df["w"] * out["e_next"]
    for k in (1, 2, 3):
        out[f"net_{k}x"] = out["gross"] - k * UNIT_BP / 1e4 * dw
        out[f"eq_net_{k}x"] = out["eq_gross"] - k * LEG_BP / 1e4 * dw
    return out.iloc[:-1]


def ols(y, X):
    """OLS with an intercept and HC1 standard errors. Returns slopes, se and t for the columns of X."""
    y = np.asarray(y, float)
    X = np.column_stack([np.ones(len(y)), np.asarray(X, float)])
    n, k = X.shape
    xtx = np.linalg.inv(X.T @ X)
    b = xtx @ X.T @ y
    e = y - X @ b
    meat = (X * e[:, None] ** 2).T @ X
    se = np.sqrt(np.diag(xtx @ meat @ xtx) * n / (n - k))
    return {"n": int(n), "b": b[1:].tolist(), "se": se[1:].tolist(), "t": (b[1:] / se[1:]).tolist()}


def perf(x):
    x = np.asarray(x, float)
    n, mu, t = newey_west_t(x, NW_LAG)
    sd = float(np.std(x, ddof=1)) if n > 1 else math.nan
    eq = np.cumsum(x)
    return {"days": n, "mean_bp": mu * 1e4, "nw_t": t, "ann_pct": mu * 252 * 100,
            "sharpe": mu / sd * math.sqrt(252) if sd > 0 else math.nan,
            "max_dd_pct": float(np.max(np.maximum.accumulate(eq) - eq)) * 100 if n else math.nan}


def span(df, name):
    lo, hi = SPANS[name]
    return df[(df["date"] >= lo) & (df["date"] <= hi)]


def sample_stats(r):
    reg_t = ols(r["x_next"], r[["thr"]])
    reg_c = ols(r["x_next"], np.column_stack([r["cal"], r["week4"], r["cal"] * r["week4"]]))
    thr_only = -r["thr"] / THR_SCALE
    return {"days": int(len(r)),
            "threshold_slope": {"b": reg_t["b"][0], "se": reg_t["se"][0], "t": reg_t["t"][0]},
            "calendar_week4_slope": {"b": reg_c["b"][2], "se": reg_c["se"][2], "t": reg_c["t"][2]},
            "calendar_slope": {"b": reg_c["b"][0], "t": reg_c["t"][0]},
            "two_leg": {k: perf(r[c]) for k, c in (("gross", "gross"), ("1x", "net_1x"), ("2x", "net_2x"),
                                                    ("3x", "net_3x"))},
            "equity_only": {k: perf(r[c]) for k, c in (("gross", "eq_gross"), ("1x", "eq_net_1x"),
                                                        ("2x", "eq_net_2x"), ("3x", "eq_net_3x"))},
            "threshold_leg_gross": perf(thr_only * r["x_next"]),
            "calendar_leg_gross": perf(r["calmod"] * r["x_next"]),
            "turnover_per_day": float(r["turn"].mean()), "mean_abs_w": float(r["w"].abs().mean()),
            "max_abs_w": float(r["w"].abs().max()), "mean_w": float(r["w"].mean())}


def verdict(st):
    rep, u = st["R"], st["U"]
    tt, tc = rep["threshold_slope"]["t"], rep["calendar_week4_slope"]["t"]
    one, two = u["two_leg"]["1x"], u["two_leg"]["2x"]
    text = (f"R slopes t {tt:.2f} (Threshold), {tc:.2f} (Calendar x week4); U two-leg 1x {one['mean_bp']:+.2f} bp/day "
            f"(NW t {one['nw_t']:.2f}, Sharpe {one['sharpe']:.2f}, {one['days']} days), 2x {two['mean_bp']:+.2f}")
    if u["days"] < MIN_U_DAYS:
        return "INCONCLUSIVE", text
    if not (tt <= T_REP and tc <= T_REP):
        return "NULL", "not replicated in R: " + text
    if one["mean_bp"] > 0 and one["nw_t"] >= T_PASS and two["mean_bp"] > 0:
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


def load(data):
    px = {t: pd.read_parquet(data / "yahoo" / f"{t}.parquet")[["date", "adjclose"]].set_index("date")["adjclose"]
          for t in ("SPY", "IEF")}
    both = pd.concat(px, axis=1, join="inner").sort_index()
    ret = both.pct_change().iloc[1:]
    fred = pd.read_csv(data / "fred" / "DTB3.csv")
    fred.columns = ["date", "rate"]
    fred["rate"] = pd.to_numeric(fred["rate"], errors="coerce")
    rate = fred.set_index("date")["rate"].reindex(ret.index).ffill().fillna(0.0)
    return pd.DataFrame({"date": ret.index, "rs": ret["SPY"].values, "rb": ret["IEF"].values,
                         "rf": rate.values / 100 / 252})


def run(lane=LANE, data=DATA, check=True):
    if check:
        digest = prereg.verify(lane / "PREREG.md")
        log(f"PREREG verified {digest[:12]}; {len(frozen_inputs(lane / 'PREREG.md'))} inputs match")
        log(f"data files verified: {verify_data(data)}")
    df = returns(build(load(data)))
    st = {k: sample_stats(span(df, k)) for k in SPANS}
    state, text = verdict(st)
    res = lane / "results"
    res.mkdir(parents=True, exist_ok=True)
    df.to_csv(res / "daily.csv", index=False)
    summary = {"registry": REGISTRY, "state": state, "text": text, "unit_bp": UNIT_BP, "leg_bp": LEG_BP,
               "samples": st}
    (res / "summary.json").write_text(json.dumps(summary, indent=1, default=float) + "\n")
    log(state, text)
    return state


if __name__ == "__main__":
    run()
