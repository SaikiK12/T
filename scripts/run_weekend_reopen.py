"""R432 weekend_reopen_v1 (M321 + M188): do Binance's 24/7 TradFi perps continue or reverse their weekend move when
the CME Globex week reopens on Sunday at 18:00 New York? Gate 0, files only, no orders.

Every weekend is anchored in New York local time (DST-aware):
  F       Friday 17:00 ET, the CME Globex close (equity index, metals and energy futures share the Sunday 18:00 to
          Friday 17:00 week; Brent's ICE week is the same in New York time)
  S       Sunday 18:00 ET, the reopen
  E_pre   S - 5 min: enter before the reopen, so the trade holds through the re-anchoring itself
  E_post  S + 1 min: enter just after the reopen
  X15/X60 S + 15 / 60 min; Xcash Monday 09:30 ET (the US cash open)
The price at an instant tau is the close of the last 1-minute bar with trades that ends at or before tau (opens at
tau - 1 min at the latest), at most STALE_MIN minutes earlier; a missing anchor drops that asset's weekend.
Signal W = 1e4 ln(P(E)/P(F)) for E_pre and 1e4 ln(P(S)/P(F)) for E_post. A trade is taken when |W| >= theta; the fade
earns -sign(W) * 1e4 ln(P(X)/P(E)), the follow its negative. One cost unit (12 bp a round trip: a 5 bp taker fee a side
plus 2 bp of spread and slippage, as in R368) is charged at 1x, 2x and 3x. Weekends whose Friday or Monday is an NYSE
holiday are dropped. Every dependent statistic resamples whole weekends.

usage: python scripts/run_weekend_reopen.py --plumbing   counts, anchor coverage, staleness and the signal's own
                                                          distribution; reads no price after any entry time
       python scripts/run_weekend_reopen.py              the frozen run (verifies the PREREG and every input first)
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
from lab.sessions import NYSEHolidays  # noqa: E402

LANE = ROOT / "experiments" / "weekend_reopen_v1"
DATA = ROOT / "data" / "tradfi_perps" / "klines_1m"
NY = "America/New_York"
MIN = 60_000
GROUPS = {"QQQUSDT": "equity", "SPYUSDT": "equity", "XAUUSDT": "metals", "XAGUSDT": "metals",
          "CLUSDT": "energy", "BZUSDT": "energy", "NATGASUSDT": "energy"}
GROUP_CELLS = ("all", "equity", "metals", "energy")
ENTRIES = ("pre", "post")
EXITS = ("x15", "x60", "cash")
THETAS = (0.0, 50.0, 100.0)            # bp of |W|
DIRS = ("fade", "follow")
PRIMARY = dict(entry="pre", exit="x15", theta=50.0, group="all", dir="fade")
COST_BP = 12.0                         # one cost unit: a round trip (5 bp taker a side + 2 bp spread/slippage), R368
COST_MULTS = (1, 2, 3)
STALE_MIN = 60                         # an anchor price may be at most this many minutes old
FIRST_FRIDAY = "2025-12-12"            # first Friday on or after the earliest listing (XAUUSDT 2025-12-11)
LAST_FRIDAY = "2026-10-23"             # its Monday cash open (10-26) is inside the archive (to 2026-10-27 23:59 UTC)
EWMA_FRIDAY = "2026-05-08"             # commodity off-hours mark moved to an order-book EWMA (news, date unverified)
PLACEBO_SHIFT_H = -24                  # placebo: the same clock one day earlier (Saturday 18:00 ET), nothing reopens
BOOT = 10_000
SEED = 432
MIN_TRADES, MIN_WEEKENDS, MIN_GROUP = 30, 12, 5
TRIALS = (len(ENTRIES) * len(EXITS) * len(THETAS) * len(GROUP_CELLS) * len(DIRS)   # 144 book cells
          + 2 * 2                                                                  # commodity regime split, fade/follow
          + len(ENTRIES) * len(EXITS) * len(GROUP_CELLS)                           # 24 slope cells
          + 2)                                                                     # placebo, fade/follow
LOG = []


def log(msg):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    LOG.append(line)
    print(line, flush=True)


# ---------------------------------------------------------------- clocks and prices

def ny_ms(day, hh, mm=0):
    """Epoch ms of a New York wall-clock time on a calendar day (DST-aware)."""
    ts = pd.Timestamp(f"{pd.Timestamp(day).date()} {hh:02d}:{mm:02d}", tz=NY)
    return int(ts.tz_convert("UTC").value // 10**6)


def weekends(first=FIRST_FRIDAY, last=LAST_FRIDAY, shift_h=0):
    """One row per Friday: anchor times (epoch ms) and whether a NYSE holiday touches the weekend."""
    fridays = pd.date_range(first, last, freq="W-FRI")
    hol = set(NYSEHolidays().holidays(pd.Timestamp(first) - pd.Timedelta(days=3),
                                      pd.Timestamp(last) + pd.Timedelta(days=4)).date)
    out = []
    for f in fridays:
        mon = (f + pd.Timedelta(days=3)).date()
        S = ny_ms(f + pd.Timedelta(days=2), 18) + shift_h * 3_600_000
        out.append(dict(friday=str(f.date()), F=ny_ms(f, 17), S=S, E_pre=S - 5 * MIN, E_post=S + MIN,
                        x15=S + 15 * MIN, x60=S + 60 * MIN, cash=ny_ms(mon, 9, 30),
                        holiday=bool(f.date() in hol or mon in hol)))
    return pd.DataFrame(out)


def load(sym, data=None):
    k = pd.read_parquet(Path(DATA if data is None else data) / f"{sym}.parquet", columns=["t", "close", "count"])
    k = k[(k["count"] > 0) & (k.close > 0)].drop_duplicates("t").sort_values("t")
    return k.t.to_numpy(np.int64), k.close.to_numpy(float)


def price_at(t, c, tau, stale_min=STALE_MIN):
    """Close of the last traded bar ending at or before tau (bar open <= tau - 1 min), and its age in minutes."""
    tau = np.asarray(tau, np.int64)
    i = np.searchsorted(t, tau - MIN, side="right") - 1
    ok = i >= 0
    age = np.where(ok, (tau - MIN - t[np.maximum(i, 0)]) / MIN, np.inf)
    p = np.where(ok & (age <= stale_min), c[np.maximum(i, 0)], np.nan)
    return p, age


def legs(t, c, wk, sym):
    """Per weekend for one asset: W for each entry and the entry-to-exit log return for each exit, in bp."""
    P = {k: price_at(t, c, wk[k].to_numpy())[0] for k in ("F", "S", "E_pre", "E_post", "x15", "x60", "cash")}
    first = t[0]
    rows = pd.DataFrame(dict(friday=wk.friday, sym=sym, group=GROUPS[sym], holiday=wk.holiday))
    listed = wk.F.to_numpy() - MIN >= first
    for e in ENTRIES:
        E = P["E_pre"] if e == "pre" else P["E_post"]
        ref = P["E_pre"] if e == "pre" else P["S"]
        rows[f"W_{e}"] = 1e4 * np.log(ref / P["F"])
        for x in EXITS:
            rows[f"R_{e}_{x}"] = 1e4 * np.log(P[x] / E)
    rows["valid"] = listed & ~rows.holiday.to_numpy() & np.all(np.isfinite(np.vstack(list(P.values()))), axis=0)
    return rows


def build(data=None, shift_h=0):
    wk = weekends(shift_h=shift_h)
    return pd.concat([legs(*load(s, data), wk, s) for s in GROUPS], ignore_index=True)


# ---------------------------------------------------------------- statistics

def block_boot(values, blocks, rng, boot=BOOT):
    """Mean, 95% percentile interval and one-sided p (share of resampled means <= 0), resampling whole weekends."""
    v = np.asarray(values, float)
    ok = np.isfinite(v)
    v, blocks = v[ok], np.asarray(blocks)[ok]
    if len(v) == 0:
        return dict(n=0, mean=None, lo=None, hi=None, p_le0=None, blocks=0)
    u, inv = np.unique(blocks, return_inverse=True)
    s, c = np.bincount(inv, v, len(u)), np.bincount(inv, None, len(u))
    pick = rng.integers(0, len(u), (boot, len(u)))
    means = s[pick].sum(1) / np.maximum(c[pick].sum(1), 1)
    return dict(n=int(len(v)), mean=float(v.mean()), lo=float(np.percentile(means, 2.5)),
                hi=float(np.percentile(means, 97.5)), p_le0=float((means <= 0).mean()), blocks=int(len(u)))


def slope_boot(x, y, blocks, rng, boot=BOOT):
    """OLS slope of y on x with a weekend-block bootstrap 95% interval."""
    x, y, blocks = np.asarray(x, float), np.asarray(y, float), np.asarray(blocks)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y, blocks = x[ok], y[ok], blocks[ok]
    if len(x) < 3 or np.var(x) == 0:
        return dict(n=int(len(x)), b=None, lo=None, hi=None)
    u, inv = np.unique(blocks, return_inverse=True)
    sx, sy = np.bincount(inv, x, len(u)), np.bincount(inv, y, len(u))
    sxx, sxy, n = np.bincount(inv, x * x, len(u)), np.bincount(inv, x * y, len(u)), np.bincount(inv, None, len(u))
    pick = rng.integers(0, len(u), (boot, len(u)))
    N, X, Y, XX, XY = (a[pick].sum(1) for a in (n, sx, sy, sxx, sxy))
    den = XX - X * X / N
    b = np.where(den > 0, (XY - X * Y / N) / np.where(den > 0, den, 1), np.nan)
    b0 = np.polyfit(x, y, 1)[0]
    return dict(n=int(len(x)), b=float(b0), lo=float(np.nanpercentile(b, 2.5)), hi=float(np.nanpercentile(b, 97.5)))


def trades(df, entry, exit_, theta, group, direction):
    """Gross bp per trade of one book cell, with its weekend and asset group."""
    d = df[df.valid]
    if group != "all":
        d = d[d.group == group]
    W, R = d[f"W_{entry}"].to_numpy(), d[f"R_{entry}_{exit_}"].to_numpy()
    take = (np.abs(W) >= theta) & (W != 0) & np.isfinite(R)
    sign = -1.0 if direction == "fade" else 1.0
    g = sign * np.sign(W[take]) * R[take]
    return g, d.friday.to_numpy()[take], d.group.to_numpy()[take], d.sym.to_numpy()[take]


def verdict(gross, weekends_, groups, ci1):
    """PASS needs >= MIN_TRADES trades on >= MIN_WEEKENDS weekends, mean net > 0 at 1x and 2x, the 1x weekend-bootstrap
    lower bound > 0, and a positive gross mean in every group with >= MIN_GROUP trades. PARTIAL: mean net 1x > 0 and
    one-sided bootstrap p < 0.10, but not PASS. Fewer trades or weekends: INCONCLUSIVE. Otherwise NULL."""
    gross = np.asarray(gross, float)
    if len(gross) < MIN_TRADES or len(np.unique(weekends_)) < MIN_WEEKENDS:
        return "INCONCLUSIVE"
    groups = np.asarray(groups)
    by = {g: gross[groups == g] for g in np.unique(groups)}
    groups_ok = all(x.mean() > 0 for x in by.values() if len(x) >= MIN_GROUP)
    m1, m2 = gross.mean() - COST_BP, gross.mean() - 2 * COST_BP
    if m1 > 0 and m2 > 0 and ci1["lo"] > 0 and groups_ok:
        return "PASS"
    if m1 > 0 and ci1["p_le0"] < 0.10:
        return "PARTIAL"
    return "NULL"


def power(sd_bp, n_weekends, per_weekend):
    """Minimum detectable mean (80% power, one-sided 5%) for weekend-clustered trades, ignoring within-weekend
    correlation beyond counting each weekend's mean as one draw (conservative when assets co-move)."""
    return float(2.49 * sd_bp / np.sqrt(max(n_weekends * min(per_weekend, 1.0), 1)))


# ---------------------------------------------------------------- plumbing (no outcome)

def plumbing(data=None):
    wk = weekends()
    out = dict(fridays=len(wk), holiday_weekends=int(wk.holiday.sum()),
               holiday_fridays=wk.friday[wk.holiday].tolist(), assets={})
    for s in GROUPS:
        t, c = load(s, data)
        listed = wk.F.to_numpy() - MIN >= t[0]
        ages = {k: price_at(t, c, wk[k].to_numpy())[1] for k in ("F", "E_pre", "S", "E_post", "x15", "x60", "cash")}
        ok = listed & ~wk.holiday.to_numpy() & np.all(np.vstack([a <= STALE_MIN for a in ages.values()]), axis=0)
        p_f = price_at(t, c, wk.F.to_numpy())[0]
        p_e = price_at(t, c, wk.E_pre.to_numpy())[0]
        W = np.abs(1e4 * np.log(p_e / p_f))[ok]
        out["assets"][s] = dict(
            group=GROUPS[s], first_bar=str(pd.Timestamp(t[0], unit="ms", tz="UTC")), listed_weekends=int(listed.sum()),
            valid_weekends=int(ok.sum()),
            anchor_age_min={k: dict(median=float(np.median(v[listed])), p95=float(np.percentile(v[listed], 95)),
                                    max=float(np.max(v[listed]))) for k, v in ages.items()},
            absW_pre_quantiles_bp={q: float(np.percentile(W, q)) for q in (25, 50, 75, 90)} if len(W) else {},
            n_absW_pre_ge={str(int(th)): int((W >= th).sum()) for th in THETAS})
    out["valid_asset_weekends"] = sum(a["valid_weekends"] for a in out["assets"].values())
    out["primary_eligible_trades"] = sum(a["n_absW_pre_ge"]["50"] for a in out["assets"].values())
    out["trials"] = TRIALS
    return out


# ---------------------------------------------------------------- run

def cells(df, rng):
    rows = []
    for e in ENTRIES:
        for x in EXITS:
            for th in THETAS:
                for g in GROUP_CELLS:
                    for d in DIRS:
                        gross, wks, grp, _ = trades(df, e, x, th, g, d)
                        ci = block_boot(gross - COST_BP, wks, rng)
                        rows.append(dict(entry=e, exit=x, theta=th, group=g, dir=d, n=len(gross),
                                         weekends=len(np.unique(wks)),
                                         gross=float(gross.mean()) if len(gross) else None,
                                         net1=ci["mean"], lo1=ci["lo"], hi1=ci["hi"], p_le0=ci["p_le0"],
                                         net2=float(gross.mean() - 2 * COST_BP) if len(gross) else None,
                                         net3=float(gross.mean() - 3 * COST_BP) if len(gross) else None))
    return pd.DataFrame(rows)


def slopes(df, rng):
    rows = []
    d = df[df.valid]
    for e in ENTRIES:
        for x in EXITS:
            for g in GROUP_CELLS:
                s = d if g == "all" else d[d.group == g]
                r = slope_boot(s[f"W_{e}"], s[f"R_{e}_{x}"], s.friday, rng)
                rows.append(dict(entry=e, exit=x, group=g, **r))
    return pd.DataFrame(rows)


def run():
    sha = prereg.verify(LANE / "PREREG.md")
    from scripts.run_clockflow import check_inputs
    log(f"PREREG verified {sha[:12]}; {len(check_inputs(LANE / 'PREREG.md'))} inputs match; trials {TRIALS}")
    rng = np.random.default_rng(SEED)
    df = build()
    log(f"asset-weekends {len(df)}, valid {int(df.valid.sum())}")
    res = LANE / "results"
    res.mkdir(exist_ok=True)

    p = PRIMARY
    gross, wks, grp, sym = trades(df, p["entry"], p["exit"], p["theta"], p["group"], p["dir"])
    ci = {k: block_boot(gross - k * COST_BP, wks, rng) for k in COST_MULTS}
    v = verdict(gross, wks, grp, ci[1])
    pd.DataFrame(dict(friday=wks, group=grp, sym=sym, gross_bp=gross)).to_csv(res / "trades_primary.csv", index=False)
    by_group = {g: dict(n=int((grp == g).sum()), gross=float(gross[grp == g].mean()) if (grp == g).any() else None)
                for g in ("equity", "metals", "energy")}
    by_sym = {s: dict(n=int((sym == s).sum()), gross=float(gross[sym == s].mean()) if (sym == s).any() else None)
              for s in GROUPS}
    log(f"primary {p}: n {len(gross)} on {len(np.unique(wks))} weekends, gross {gross.mean():+.2f} bp, "
        f"net 1x {ci[1]['mean']:+.2f} [{ci[1]['lo']:+.2f}, {ci[1]['hi']:+.2f}], verdict {v}")

    # commodity regime split (primary spec, metals + energy, before/after the EWMA Friday)
    d = df[df.valid & df.group.isin(["metals", "energy"])]
    split = {}
    for name, m in (("before", d.friday < EWMA_FRIDAY), ("after", d.friday >= EWMA_FRIDAY)):
        for dr in DIRS:
            g_, w_, _, _ = trades(d[m], p["entry"], p["exit"], p["theta"], "all", dr)
            split[f"{name}_{dr}"] = block_boot(g_ - COST_BP, w_, rng)

    # placebo: the same clock one day earlier (Saturday 18:00 ET), when nothing reopens
    pl = build(shift_h=PLACEBO_SHIFT_H)
    placebo = {}
    for dr in DIRS:
        g_, w_, _, _ = trades(pl, p["entry"], p["exit"], p["theta"], p["group"], dr)
        placebo[dr] = block_boot(g_ - COST_BP, w_, rng)

    tab = cells(df, rng)
    tab.to_csv(res / "cells.csv", index=False)
    sl = slopes(df, rng)
    sl.to_csv(res / "slopes.csv", index=False)
    sd = float(np.std(gross)) if len(gross) > 1 else None
    summary = dict(
        round="R432", prereg_sha=sha, trials=TRIALS, primary=p, verdict=v, cost_bp_per_unit=COST_BP,
        primary_n=int(len(gross)), primary_weekends=int(len(np.unique(wks))),
        primary_gross=float(gross.mean()) if len(gross) else None, primary_gross_sd=sd,
        primary_net={str(k): ci[k] for k in COST_MULTS}, primary_by_group=by_group, primary_by_sym=by_sym,
        mde80_bp=power(sd, len(np.unique(wks)), 1.0) if sd else None,
        regime_split=split, placebo=placebo,
        slopes_primary_entry=sl[(sl.entry == p["entry"]) & (sl.exit == p["exit"])].to_dict("records"),
        best_cell_net1=tab.sort_values("net1", ascending=False).head(5).to_dict("records"),
        valid_asset_weekends=int(df.valid.sum()))
    (res / "summary.json").write_text(json.dumps(summary, indent=1, default=float) + "\n")
    (LANE / "run.log").write_text("\n".join(LOG) + "\n")
    log("wrote results/summary.json, cells.csv, slopes.csv, trades_primary.csv")
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plumbing", action="store_true")
    a = ap.parse_args(argv)
    if a.plumbing:
        out = plumbing()
        (LANE / "plumbing.json").write_text(json.dumps(out, indent=1) + "\n")
        print(json.dumps({k: v for k, v in out.items() if k != "assets"}, indent=1))
        for s, v in out["assets"].items():
            print(s, v["valid_weekends"], v["n_absW_pre_ge"], v["absW_pre_quantiles_bp"])
        return 0
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
