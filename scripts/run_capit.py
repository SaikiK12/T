"""capit_v1 (R303): buying capitulation on Binance perps. As set out in experiments/capit_v1/PREREG.md.

Two queued methods, one family:
- M302 (Takashi Kotegawa, "BNF"): buy a perp whose close sits at least X% below its 25-day average. Here the dip
  coins are bought against a short in the top-50 basket, so the book is the coin's rebound, not the market's.
- M302's market variant and M286 (a liquidation cascade): buy the top-50 basket on days when many coins are far below
  their average, or when open interest and prices fall together. These books are judged against holding the basket
  on every day of the window.

The family: dip {20, 30, 40% below the average} x hold {1, 5 days} + trigger {breadth, cascade} x hold {2, 5 days}
= 10 books. The best discovery book (2021-01..2023-12) by net t goes to validation (2024-01..2026-09), once.

Timing: row D of data/daily/panel.parquet is the decision at 00:00 UTC of day D. Signals use rows up to D; entry is
row D's close; a hold of h days exits at the last close in rows D+1..D+h and pays the funding settled in those rows
(R299's `targets`). The panel holds no row before 2021-01-02 or after 2026-09-30 (reserved).

usage: python scripts/run_capit.py [--plumbing]
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
from lab import inference, prereg, stats  # noqa: E402
from scripts.run_clockflow import check_inputs  # noqa: E402
from scripts.run_lotcap import weekly_grid  # noqa: E402
from scripts.run_mlrank import targets  # noqa: E402
from scripts.run_qbasis import window_mask  # noqa: E402

LANE = ROOT / "experiments" / "capit_v1"
PANEL = ROOT / "data" / "daily" / "panel.parquet"
DAY = 86_400_000
XS = (0.20, 0.30, 0.40)                          # dip depth below the 25-day average
DIP_HOLDS = (1, 5)                               # days
TRIGGERS = ("breadth", "cascade")
TRIGGER_HOLDS = (2, 5)                           # days
STRATS = ([("dip", x, h) for x in XS for h in DIP_HOLDS]
          + [(t, None, h) for t in TRIGGERS for h in TRIGGER_HOLDS])
TRIALS = len(STRATS)
TOP, BASKET, MIN_BASKET = 150, 50, 30
MA = 25                                          # days in the average, all with a close
BREADTH_X, BREADTH_Q, BREADTH_FLOOR = 0.20, 0.95, 0.10   # M302 says the top 2%; that leaves 7 discovery days
BREADTH_LOOK, BREADTH_MIN_LOOK = 365, 180        # prior days for the percentile
OI_DROP, MED_RET = -0.08, -0.05                  # cascade: top-50 open interest and median return on day D
COST = 8.5e-4                                    # API, per side, 1x
T_MIN, BEST_DROP = 2.0, 10
WINDOWS = {"disc": ("2021-01-01", "2023-12-31"), "valid": ("2024-01-01", "2026-09-30")}   # R301's (window_mask)
SPA_BOOT, SPA_BLOCK, SEED = 2000, 4, 303
COLS = ["close", "ret", "fund", "oi_usd", "rank_qvol30"]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------------------------------------------------- panel
def wide(df):
    """{column: DataFrame day x perp} on a full calendar of days."""
    days = pd.date_range(df.day.min(), df.day.max(), freq="D")
    perps = sorted(df.perp.unique())
    df = df.assign(day=pd.to_datetime(df.day))
    return {c: df.pivot(index="day", columns="perp", values=c).reindex(index=days, columns=perps) for c in COLS}


def universe(w, top):
    return (w["rank_qvol30"] <= top) & w["close"].notna()


def ma_gap(w):
    """Row D's close over the mean of the closes on rows D-24..D, minus 1; NaN unless all 25 rows have a close."""
    c = w["close"]
    return c / c.rolling(MA, min_periods=MA).mean() - 1.0


def no_exit(w, h):
    """True where the perp trades on row D but has no close in rows D+1..D+h (R299's `targets` books 0 there)."""
    c = w["close"]
    later = sum(c.shift(-k).notna().astype(int) for k in range(1, h + 1))
    return c.notna() & (later == 0)


def basket(w, h):
    """The equal-weight top-50 basket's h-day return net of the funding a long pays, per decision day (NaN with fewer
    than 30 names)."""
    ret, fund = targets(w, h)
    uni = universe(w, BASKET) & ret.notna()
    x = (ret - fund).where(uni)
    return x.mean(axis=1).where(uni.sum(axis=1) >= MIN_BASKET)


# ---------------------------------------------------------------------------------------------------------- signals
def dips(w, x):
    """Row D's top-150 perps whose close is at least x below their 25-day average."""
    return (ma_gap(w) <= -x) & universe(w, TOP)


def breadth(w):
    """(share, trigger): the share of top-150 perps (with an average) at least 20% below it, and the days where that
    share is at or above its 95th percentile over the previous 365 days (at least 180 of them) and at least 10%."""
    g = ma_gap(w)
    have = universe(w, TOP) & g.notna()
    share = ((g <= -BREADTH_X) & have).sum(axis=1) / have.sum(axis=1).where(have.sum(axis=1) > 0)
    q = share.shift(1).rolling(BREADTH_LOOK, min_periods=BREADTH_MIN_LOOK).quantile(BREADTH_Q)
    return share, (share >= q) & (share >= BREADTH_FLOOR)


def cascade(w):
    """(oi_change, median_return, trigger): on row D, the top-50 perps' summed open interest against the same perps'
    on row D-1, and their median daily return. A trigger needs both at or below the thresholds, on 30+ perps."""
    oi, r = w["oi_usd"], w["ret"]
    top = universe(w, BASKET)
    both = top & oi.notna() & oi.shift(1).notna()
    chg = oi.where(both).sum(axis=1) / oi.shift(1).where(both).sum(axis=1) - 1.0
    chg = chg.where(both.sum(axis=1) >= MIN_BASKET)
    med = r.where(top).median(axis=1)
    return chg, med, (chg <= OI_DROP) & (med <= MED_RET)


# ------------------------------------------------------------------------------------------------------------ books
def dip_rows(w, x, h):
    """One row per decision day with dips: long the dip perps (equal weight), short the top-50 basket, held h days.
    gross = mean dip (return - funding) - basket (return - funding). Costs: 2 sides on each leg."""
    ret, fund = targets(w, h)
    ev = dips(w, x)
    bk = basket(w, h)
    nx = no_exit(w, h)
    rows = []
    for d in ev.index[ev.any(axis=1)]:
        coins = ev.columns[ev.loc[d].to_numpy()]
        r = (ret.loc[d, coins] - fund.loc[d, coins]).dropna()
        if r.empty or np.isnan(bk.loc[d]):
            continue
        rows.append({"t": int(d.value // 10**6), "long": float(r.mean()), "hedge": float(bk.loc[d]),
                     "gross": float(r.mean() - bk.loc[d]), "n": int(len(r)), "no_exit": int(nx.loc[d, coins].sum()),
                     "coins": "|".join(r.index)})
    return rows


def trigger_rows(w, trig, h):
    """One row per trigger day: long the top-50 basket for h days. gross = the basket's (return - funding)."""
    bk = basket(w, h)
    rows = []
    for d in trig.index[trig.fillna(False).to_numpy()]:
        if np.isnan(bk.loc[d]):
            continue
        rows.append({"t": int(d.value // 10**6), "long": float(bk.loc[d]), "hedge": 0.0, "gross": float(bk.loc[d]),
                     "n": 1, "no_exit": 0, "coins": "basket"})
    return rows


def decision(rows, kind, h, m, drift):
    """The decided series at m times the cost. dip: the hedged net (4 sides). Triggers: the net (2 sides) minus the
    window's buy-and-hold drift, the basket's mean h-day return over every day of the window."""
    g = np.array([r["gross"] for r in rows])
    if kind == "dip":
        return g - 4 * m * COST
    return g - 2 * m * COST - drift


# ------------------------------------------------------------------------------------------------------------ stats
def event_stats(x, ts, h):
    """Per-event stats of x at decision times ts. The t is Newey-West on a calendar grid of days (no event: a gap),
    lag max(5, 2h). bp_day divides the per-event mean by the hold."""
    x, ts = np.asarray(x, float), np.asarray(ts, np.int64)
    if len(x) < 10:
        return {"events": int(len(x)), "mean_bp": float(x.mean() * 1e4) if len(x) else None}
    grid = np.full(int((ts[-1] - ts[0]) // DAY) + 1, np.nan)
    grid[(ts - ts[0]) // DAY] = x
    _, _, t = stats.newey_west_t(grid, max(5, 2 * h))
    best = np.sort(x)[::-1]
    return {"events": int(len(x)), "mean_bp": float(x.mean() * 1e4), "bp_day": float(x.mean() / h * 1e4),
            "t": float(t) if np.isfinite(t) else None, "median_bp": float(np.median(x) * 1e4),
            "hit": float((x > 0).mean()), "mean_wo_best_bp": float(best[BEST_DROP:].mean() * 1e4),
            "best_share": float(best[:BEST_DROP].sum() / x.sum()) if x.sum() > 0 else None}


def drifts(w, h):
    """Per window: the basket's mean h-day return (net of funding) over every decision day in it."""
    bk = basket(w, h).dropna()
    ts = np.array([d.value // 10**6 for d in bk.index], np.int64)
    return {win: float(bk.to_numpy()[window_mask(ts, h, win)].mean()) for win in WINDOWS}


def report(rows, kind, h, drift):
    ts = np.array([r["t"] for r in rows], np.int64)
    rep = {}
    for win in WINDOWS:
        m = window_mask(ts, h, win)
        sel = [r for r, k in zip(rows, m) if k]
        if not sel:
            rep[win] = {"1x": {"events": 0}}
            continue
        out = {f"{k}x": event_stats(decision(sel, kind, h, k, drift[win]), ts[m], h) for k in (1, 2, 3)}
        out["gross"] = event_stats([r["gross"] for r in sel], ts[m], h)
        out["long_only_1x"] = event_stats([r["long"] - 2 * COST for r in sel], ts[m], h)
        out["hedge_bp"] = float(np.mean([r["hedge"] for r in sel]) * 1e4)
        out["perp_events"] = int(sum(r["n"] for r in sel))
        out["no_exit"] = int(sum(r["no_exit"] for r in sel))
        out["drift_bp"] = float(drift[win] * 1e4) if kind != "dip" else None
        rep[win] = out
    return rep, ts


def decide(reports):
    """The discovery pick (highest decided 1x t with a positive mean) and its validation verdict."""
    cand = [(k, r["disc"]["1x"]) for k, r in reports.items() if r["disc"]["1x"].get("t") is not None
            and r["disc"]["1x"]["mean_bp"] > 0]
    if not cand:
        return None, False, {}
    pick = max(cand, key=lambda z: z[1]["t"])[0]
    v = reports[pick]["valid"]
    checks = {"t_1x": (v["1x"].get("t") or -np.inf) >= T_MIN, "mean_2x": (v.get("2x", {}).get("mean_bp") or -1) > 0,
              "wo_best": (v["1x"].get("mean_wo_best_bp") or -1) > 0}
    return pick, all(checks.values()), checks


def label(k):
    kind, x, h = k
    return f"dip{int(round(x * 100))} h{h}" if kind == "dip" else f"{kind} h{h}"


def years(rows, kind, h, drift_all):
    """Per calendar year: events and the decided net 1x per event (bp); triggers use the all-period drift."""
    if not rows:
        return {}
    x = decision(rows, kind, h, 1, drift_all)
    y = pd.to_datetime([r["t"] for r in rows], unit="ms").year
    df = pd.DataFrame({"y": y, "x": x})
    return {int(k): {"events": int(len(v)), "net1x_bp": float(v.x.mean() * 1e4)} for k, v in df.groupby("y")}


# ------------------------------------------------------------------------------------------------------------- main
def build(w):
    res = {}
    trig = {"breadth": breadth(w)[1], "cascade": cascade(w)[2]}
    for k in STRATS:
        kind, x, h = k
        res[k] = dip_rows(w, x, h) if kind == "dip" else trigger_rows(w, trig[kind], h)
    return res, trig


def analyze(w, res, trig):
    dr = {h: drifts(w, h) for h in sorted(set(DIP_HOLDS) | set(TRIGGER_HOLDS))}
    dr_all = {h: float(basket(w, h).dropna().mean()) for h in dr}
    reports, series = {}, {}
    for k, rows in res.items():
        kind, _, h = k
        reports[k], ts = report(rows, kind, h, dr[h])
        series[k] = ts
    pick, ok, checks = decide(reports)
    first = w["close"].index[0].value // 10**6
    anchors = np.arange(first, w["close"].index[-1].value // 10**6 + 1, 7 * DAY, dtype=np.int64)
    spa = {}
    for win in WINDOWS:
        an = anchors[window_mask(anchors, 7, win)]
        cols = []
        for k in STRATS:
            kind, _, h = k
            ts = series[k]
            m = window_mask(ts, h, win)
            sel = [r for r, z in zip(res[k], m) if z]
            x = decision(sel, kind, h, 1, dr[h][win]) if sel else np.array([])
            cols.append(weekly_grid(ts[m], x, an))
        r = inference.spa(np.column_stack(cols), n_boot=SPA_BOOT, block=SPA_BLOCK, rng=np.random.default_rng(SEED))
        r["best"] = label(STRATS[r["best"]])
        r["weeks"] = int(len(an))
        spa[win] = r
    # how many dip days are also market-trigger days
    dip_days = {k: {r["t"] for r in res[k]} for k in STRATS if k[0] == "dip" and k[2] == 1}
    trig_days = {t: {int(d.value // 10**6) for d in v.index[v.fillna(False).to_numpy()]} for t, v in trig.items()}
    overlap = {label(k): {t: len(s & td) for t, td in trig_days.items()} | {"days": len(s)}
               for k, s in dip_days.items()}
    return {"strategies": {label(k): v for k, v in reports.items()}, "pick": label(pick) if pick else None,
            "pick_passes": bool(ok), "checks": checks, "verdict": "PARTIAL" if ok else "NULL", "spa": spa,
            "drift_bp": {h: {k: v * 1e4 for k, v in d.items()} for h, d in dr.items()},
            "years": {label(k): years(res[k], k[0], k[2], dr_all[k[2]]) for k in STRATS},
            "trigger_days": {t: sorted(pd.to_datetime(sorted(v), unit="ms").strftime("%Y-%m-%d").tolist())
                             for t, v in trig_days.items()},
            "dip_trigger_overlap": overlap}


def load_panel():
    return pd.read_parquet(PANEL, columns=["day", "perp", *COLS])


def plumbing(df):
    """Counts only: dip events, trigger days and open-interest coverage per window. No return is read after a
    decision day: the signals use rows up to D, the counts read no exit."""
    w = wide(df)
    out = {"panel_days": int(len(w["close"]))}
    for x in XS:
        ev = dips(w, x)
        days = ev.index[ev.any(axis=1)]
        ts = np.array([d.value // 10**6 for d in days], np.int64)
        n = ev.sum(axis=1)
        out[f"dip{int(round(x * 100))}"] = {
            "perp_events": int(n.sum()), "days": int(len(days)),
            **{wn: {"days": int(window_mask(ts, 1, wn).sum()),
                    "perp_events": int(n.loc[days][window_mask(ts, 1, wn)].sum())} for wn in WINDOWS}}
    for name, trig in (("breadth", breadth(w)[1]), ("cascade", cascade(w)[2])):
        days = trig.index[trig.fillna(False).to_numpy()]
        ts = np.array([d.value // 10**6 for d in days], np.int64)
        out[name] = {"days": int(len(days)), **{wn: int(window_mask(ts, 1, wn).sum()) for wn in WINDOWS}}
    chg = cascade(w)[0]
    out["oi_coverage_first_day"] = str(chg.first_valid_index().date()) if chg.notna().any() else None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true", help="counts only, no return read (before the freeze)")
    a = ap.parse_args()
    if a.plumbing:
        print(json.dumps(plumbing(load_panel()), indent=1))
        return
    sha = prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    w = wide(load_panel())
    res, trig = build(w)
    out = analyze(w, res, trig)
    for k, v in out["strategies"].items():
        d, va = v["disc"]["1x"], v["valid"]["1x"]
        log(f"{k}: disc {d.get('events')} events net {d.get('mean_bp')} bp t {d.get('t')}, valid "
            f"{va.get('events')} events net {va.get('mean_bp')} bp t {va.get('t')}")
    log(f"pick {out['pick']}, passes {out['pick_passes']} {out['checks']}; verdict {out['verdict']}")
    res_dir = LANE / "results"
    res_dir.mkdir(parents=True, exist_ok=True)
    rows = [{"strategy": label(k), **r} for k in STRATS for r in res[k]]
    pd.DataFrame(rows).to_csv(res_dir / "events.csv", index=False, float_format="%.8g")
    summary = {"rid": "R303", "verdict": out["verdict"], "trials": TRIALS, "prereg_sha256": sha, "inputs": shas, **out}
    (res_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    return summary


if __name__ == "__main__":
    main()
