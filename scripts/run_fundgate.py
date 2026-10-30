"""fundgate_v1 (R297): does the market's funding response to up days time the crypto market? As set out in
experiments/fundgate_v1/PREREG.md (M295, from a Bankless guest's remark, docs/COMMENT_DIG.md).

The guest read 2026 as a bear structure because "funding rates on positive days so far this year have been lower than
funding rates on positive days in 2022". Two daily measures of that, on the 50 most traded Binance perps:
- slope: the trailing 30-day OLS slope of the day's funding on the day's return (how far funding rises per up move);
- up-day funding: the trailing 30-day mean funding over up days only (the guest's own words).
Each is scored against its own trailing year (a z-score) and read against the equal-weight basket's next 7 and 30
days. The guest's sign is positive (a weak response, a weak market). The crowding reading is negative. Both count.

Timing (lab/daily.py): row D is the decision at 00:00 UTC of day D and holds day D-1's return and funding. The signal
on row D uses rows up to D. The basket held over day D is the TOP perps of row D, and its return is on row D+1.

usage: python scripts/run_fundgate.py [--plumbing]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sps

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import daily, prereg, stats  # noqa: E402
from scripts.run_clockflow import check_inputs  # noqa: E402

LANE = ROOT / "experiments" / "fundgate_v1"
TOP, NEED_COINS, TRIM = 50, 30, 0.10        # the 50 most traded perps (rank_qvol30); 10% trimmed means
LOOK, NEED_LOOK, UP_NEED = 30, 25, 8        # trailing 30 rows: 25 for the slope, 8 up days for up-day funding
ZLOOK, ZNEED, ZCLIP = 365, 180, 3.0         # z against the previous 365 rows (180 needed), clipped at +-3
HORIZONS = (7, 30)
MEASURES = ("slope", "upfund")
TRIAL_LIST = [(m, h) for m in MEASURES for h in HORIZONS]
TRIALS = len(TRIAL_LIST)
T_MIN = 2.50                                # Bonferroni over 4 trials, two-sided 5%
NW_MULT, RULE_LAG = 2, 5                    # NW lag 2h for overlapping h-day targets; 5 days for daily rule series
COST, API = 3e-4, 8.5e-4                    # per side: manual web at 1x (BTC); API (the basket is API only)
DISC = ("2021-04-01", "2023-12-31")
VALID = ("2024-01-01", "2026-09-30")
WINDOWS = {"disc": DISC, "valid": VALID}
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


# ----------------------------------------------------------------------------------------------------------- market
def _trim(v):
    v = np.asarray(v, float)
    return float(sps.trim_mean(v, TRIM)) if len(v) >= NEED_COINS else np.nan


def market(df):
    """One row per calendar day D (a complete index, gaps NaN):
    - F, R: 10% trimmed means of funding and return over the TOP perps of row D, n: their count (NaN under NEED_COINS);
    - B, Bf: the basket's return and funding paid on row D, equal weight over the TOP perps of row D-1 (the basket
      held over day D-1) that have a return on row D; nb: their count;
    - btc, btc_f: BTCUSDT's return and funding on row D."""
    df = df.assign(day=pd.to_datetime(df.day), perp=df.perp.astype(str))
    for c in ("ret", "fund"):
        df[c] = df[c].astype(np.float64)
    idx = pd.date_range(df.day.min(), df.day.max(), freq="D")
    top = df[df.rank_qvol30 <= TOP]
    g = top.dropna(subset=["ret", "fund"]).groupby("day")
    out = pd.DataFrame({"F": g.fund.agg(_trim), "R": g.ret.agg(_trim), "n": g.size()}).reindex(idx)
    held = top[["day", "perp"]].assign(day=top.day + pd.Timedelta(days=1))
    b = df.merge(held, on=["day", "perp"])
    b = b[b.ret.notna()]
    gb = b.groupby("day")
    out["nb"] = gb.size().reindex(idx)
    out["B"] = gb.ret.mean().reindex(idx).where(out.nb >= NEED_COINS)
    out["Bf"] = gb.fund.apply(lambda v: v.fillna(0.0).mean()).reindex(idx).where(out.nb >= NEED_COINS)
    btc = df[df.perp == "BTCUSDT"].set_index("day")
    out["btc"], out["btc_f"] = btc.ret.reindex(idx), btc.fund.reindex(idx).fillna(0.0)
    out.index.name = "day"
    return out


# ---------------------------------------------------------------------------------------------------------- signals
def rolling_slope(F, R, look=LOOK, need=NEED_LOOK):
    """OLS slope of F on R over the trailing `look` rows (this one included), from rows with both, at least `need`."""
    ok = F.notna() & R.notna()
    f, r = F.where(ok), R.where(ok)
    roll = lambda s: s.rolling(look, min_periods=need).mean()
    var = roll(r * r) - roll(r) ** 2
    return ((roll(f * r) - roll(f) * roll(r)) / var).where(var > 0)


def upday_funding(F, R, look=LOOK, need=UP_NEED):
    """Mean F over the rows of the trailing `look` (this one included) where R > 0, at least `need` of them."""
    return F.where(R > 0).rolling(look, min_periods=need).mean()


def trailing_z(m, look=ZLOOK, need=ZNEED, clip=ZCLIP):
    """(m - mean) / sd of the previous `look` rows (not this one), at least `need`, clipped at +-clip."""
    prev = m.shift(1).rolling(look, min_periods=need)
    return ((m - prev.mean()) / prev.std()).clip(-clip, clip)


def forward(r, h):
    """Y[D] = sum of log(1 + r) over rows D+1..D+h; NaN when one of them is missing."""
    return np.log1p(r).rolling(h, min_periods=h).sum().shift(-h)


def window_of(index):
    w = pd.Series(None, index=index, dtype=object)
    for name, (a, b) in WINDOWS.items():
        w[(index >= a) & (index <= b)] = name
    return w


def table(mk):
    """The signals and targets per decision row. A target counts only when its last row is inside the decision's
    window (no discovery target reads validation days)."""
    t = pd.DataFrame(index=mk.index)
    t["F"], t["R"] = mk.F, mk.R
    t["slope"] = rolling_slope(mk.F, mk.R)
    t["upfund"] = upday_funding(mk.F, mk.R)
    t["level"] = mk.F.rolling(LOOK, min_periods=NEED_LOOK).mean()          # descriptive: plain funding level
    t["mom30"] = np.log1p(mk.B).rolling(LOOK, min_periods=NEED_LOOK).sum()   # reported: the basket's last 30 rows
    for m in (*MEASURES, "level"):
        t[f"x_{m}"] = trailing_z(t[m])
    t["win"] = window_of(t.index)
    for h in HORIZONS:
        end = t.index + pd.Timedelta(days=h)
        inside = pd.Series(False, index=t.index)
        for name, (a, b) in WINDOWS.items():
            inside |= (t.win == name) & (end <= pd.Timestamp(b))
        t[f"y{h}"] = forward(mk.B, h).where(inside)
        t[f"b{h}"] = forward(mk.btc, h).where(inside)
    return t


# ------------------------------------------------------------------------------------------------------------ tests
def slope_test(x, y, lag):
    """Demean x and y within the rows given; NW t (calendar lag) of the mean of their product, the slope and the
    correlation, and a t from every lag/NW_MULT-th row only (non-overlapping targets)."""
    ok = x.notna() & y.notna()
    if ok.sum() < 10:
        return {"n": int(ok.sum())}
    xx = (x - x[ok].mean()).where(ok)
    yy = (y - y[ok].mean()).where(ok)
    u = (xx * yy).loc[ok.idxmax():ok[::-1].idxmax()]
    n, mu, t = stats.newey_west_t(u.to_numpy(), lag)
    step = max(lag // NW_MULT, 1)
    xs, ys = x[ok].iloc[::step], y[ok].iloc[::step]
    r = float(np.corrcoef(xs, ys)[0, 1]) if len(xs) > 3 else np.nan
    t_no = r * np.sqrt((len(xs) - 2) / (1 - r * r)) if np.isfinite(r) and abs(r) < 1 else np.nan
    return {"n": int(n), "t": float(t) if np.isfinite(t) else None,
            "beta": float((xx * yy).sum() / (xx * xx).sum()), "corr": float(np.corrcoef(x[ok], y[ok])[0, 1]),
            "n_nonoverlap": int(len(xs)), "t_nonoverlap": float(t_no) if np.isfinite(t_no) else None}


def residual(x, z):
    """x less its OLS fit on z and a constant, over the rows with both (NaN elsewhere)."""
    ok = x.notna() & z.notna()
    b = np.polyfit(z[ok], x[ok], 1)
    return (x - np.polyval(b, z)).where(ok)


def trial(t, m, h):
    x, lag = t[f"x_{m}"], NW_MULT * h
    res = {"trial": f"{m} h{h}"}
    for w in WINDOWS:
        sel = t.win == w
        res[w] = slope_test(x[sel], t[f"y{h}"][sel], lag)
        res[f"{w}_btc"] = slope_test(x[sel], t[f"b{h}"][sel], lag)
        res[f"{w}_given_mom"] = slope_test(residual(x[sel], t.mom30[sel]), t[f"y{h}"][sel], lag)   # reported only
    sel = t.win == "valid"
    res["valid_by_year"] = {str(y): slope_test(x[sel & (t.index.year == y)], t[f"y{h}"][sel & (t.index.year == y)],
                                               lag).get("t") for y in sorted(set(t.index[sel].year))}
    td, tv = res["disc"].get("t"), res["valid"].get("t")
    res["pass"] = bool(td is not None and tv is not None and np.sign(td) == np.sign(tv) and abs(tv) >= T_MIN)
    res["direction"] = None if tv is None else ("claim" if tv > 0 else "crowding")
    return res


# ------------------------------------------------------------------------------------------------------------ rules
def rule_days(x, r, f, side, cost):
    """Daily net of a long/flat gate: long over day D when x on row D is >= 0 (side "claim") or < 0 ("crowding"),
    earning row D+1's return less the funding longs paid, and paying `cost` per side on each switch. Flat when x is
    NaN. Index: the decision row."""
    on = (x >= 0) if side == "claim" else (x < 0)
    p = on.astype(float).where(x.notna(), 0.0)
    gross = p * (r.shift(-1) - f.shift(-1))
    sw = (p - p.shift(1).fillna(0.0)).abs()
    return gross - cost * sw, p, sw


def book_stats(net, p, sw, base, days):
    """Annualized stats of a daily net series over `days` (index), against always long (`base`)."""
    net, p, sw, base = (s.reindex(days) for s in (net, p, sw, base))
    ok = net.notna() & base.notna()
    if ok.sum() < 30:
        return {"days": int(ok.sum())}
    n, b = net[ok], base[ok]
    yrs = ok.sum() / 365.25
    eq = n.cumsum()
    _, _, t = stats.newey_west_t((n - b).to_numpy(), RULE_LAG)
    return {"days": int(ok.sum()), "ann": float(n.mean() * 365), "vol": float(n.std() * np.sqrt(365)),
            "sharpe": float(n.mean() / n.std() * np.sqrt(365)) if n.std() > 0 else None,
            "maxdd": float((eq - eq.cummax()).min()), "in_market": float(p[ok].mean()),
            "switches_per_year": float(sw[ok].sum() / yrs), "base_ann": float(b.mean() * 365),
            "base_sharpe": float(b.mean() / b.std() * np.sqrt(365)), "base_maxdd": float((b.cumsum() -
                                                                                          b.cumsum().cummax()).min()),
            "excess_ann": float((n - b).mean() * 365), "excess_t": float(t) if np.isfinite(t) else None}


def rules(t, mk):
    """Per measure and side: the gate on the basket (API: 8.5 bp per side at 1x, then 2x and 3x) and on BTC (manual
    web 3 / 6 / 9 bp, and API), against always long the same asset. Basket rebalancing is not costed (either book)."""
    out = {}
    assets = {"basket": (mk.B, mk.Bf, (API, 2 * API, 3 * API), None),
              "btc": (mk.btc, mk.btc_f, (COST, 2 * COST, 3 * COST), API)}
    for m in MEASURES:
        x = t[f"x_{m}"]
        for side in ("claim", "crowding"):
            for a, (r, f, costs, api) in assets.items():
                base = (r.shift(-1) - f.shift(-1))
                rep = {}
                for w, (lo, hi) in WINDOWS.items():
                    days = t.index[(t.index >= lo) & (t.index < pd.Timestamp(hi))]   # row D+1 inside the window
                    rep[w] = {}
                    for k, c in zip(("1x", "2x", "3x"), costs):
                        rep[w][k] = book_stats(*rule_days(x, r, f, side, c), base, days)
                    if api is not None:
                        rep[w]["api"] = book_stats(*rule_days(x, r, f, side, api), base, days)
                out[f"{m} {side} {a}"] = rep
    return out


# ----------------------------------------------------------------------------------------------------- descriptives
def descriptives(t):
    """By calendar year (the guest compared 2026 with 2022): funding per day, funding on up days, the share of up
    days and the year's own slope of F on R, plus how the two measures relate to the plain funding level and to the
    basket's last 30 days."""
    years = {}
    for y, d in t.groupby(t.index.year):
        d = d[d.F.notna() & d.R.notna()]
        if len(d) < 30:
            continue
        up = d.R > 0
        years[str(y)] = {"days": int(len(d)), "fund_day_bp": float(d.F.mean() * 1e4),
                         "fund_upday_bp": float(d.F[up].mean() * 1e4), "fund_downday_bp": float(d.F[~up].mean() * 1e4),
                         "up_share": float(up.mean()), "slope_year": float(np.polyfit(d.R, d.F, 1)[0])}
    ok = t[[f"x_{m}" for m in (*MEASURES, "level")] + ["mom30"]].dropna()
    return {"by_year": years, "x_corr": ok.corr().round(3).to_dict(), "x_rows": int(len(ok))}


# ------------------------------------------------------------------------------------------------------------- main
def build(df):
    mk = market(df)
    return mk, table(mk)


def plumbing(mk, t):
    """Counts only: no statistic of a target, and a power table from the counts."""
    out = {"days": int(len(mk)), "first": str(mk.index[0].date()), "last": str(mk.index[-1].date()),
           "days_F": int(mk.F.notna().sum()), "days_B": int(mk.B.notna().sum()), "days_btc": int(mk.btc.notna().sum()),
           "median_top_coins": float(mk.n.median()), "median_basket_coins": float(mk.nb.median())}
    for m in (*MEASURES, "level"):
        s = t[f"x_{m}"].dropna()
        out[f"first_x_{m}"] = str(s.index[0].date()) if len(s) else None
    rows = {}
    for m, h in TRIAL_LIST:
        for w in WINDOWS:
            ok = t[f"x_{m}"].notna() & t[f"y{h}"].notna() & (t.win == w)
            rows[f"{m} h{h} {w}"] = int(ok.sum())
    out["rows"] = rows
    power = {}
    for h in HORIZONS:
        n = rows[f"slope h{h} valid"] / h
        power[f"h{h}"] = {"n_eff": round(n, 1), **{f"rho {r}": round(float(sps.norm.cdf(r * np.sqrt(n) /
                                                                                          np.sqrt(1 - r * r) - T_MIN)), 3)
                                                    for r in (0.1, 0.2, 0.3, 0.4, 0.5)}}
    out["power_normal_approx"] = power
    return out


def analyze(t, mk):
    tests = [trial(t, m, h) for m, h in TRIAL_LIST]
    passes = [r["trial"] for r in tests if r["pass"]]
    return {"tests": tests, "passes": passes, "verdict": "PARTIAL" if passes else "NULL", "rules": rules(t, mk),
            "descriptives": descriptives(t)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true", help="counts only, no statistic (before the freeze)")
    a = ap.parse_args()
    if a.plumbing:
        mk, t = build(daily.load(columns=["ret", "fund", "rank_qvol30"]))
        print(json.dumps(plumbing(mk, t), indent=1))
        return
    sha = prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    mk, t = build(daily.load(columns=["ret", "fund", "rank_qvol30"]))
    log(f"{len(mk)} days, F on {int(mk.F.notna().sum())}, basket on {int(mk.B.notna().sum())}")
    res = analyze(t, mk)
    for r in res["tests"]:
        log(f"{r['trial']}: disc t {r['disc'].get('t')}, valid t {r['valid'].get('t')} (BTC {r['valid_btc'].get('t')})"
            f", pass {r['pass']}")
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    t.drop(columns=["win"]).join(mk[["B", "Bf", "btc", "btc_f", "n", "nb"]]).to_csv(out / "daily.csv",
                                                                                   float_format="%.8g")
    summary = {"rid": "R297", "verdict": res["verdict"], "trials": TRIALS, "prereg_sha256": sha, "inputs": shas, **res}
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    log(f"verdict {res['verdict']}; passes {res['passes']}")
    return summary


if __name__ == "__main__":
    main()
