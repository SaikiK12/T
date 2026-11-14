"""charm_expiry_v1 (R296): does Deribit's Friday 08:00 UTC expiry move the BTC and ETH perps? As set out in
experiments/charm_expiry_v1/PREREG.md.

Deribit's BTC and ETH options expire on Fridays at 08:00 UTC and settle on the 30-minute TWAP of its index from 07:30.
R289 found that a perp move inside that window tends to reverse after 08:00 (gross +11 to +20 bp per trade, t 1.37,
not a pass). Each Deribit option trade carries the taker's side, so an expiring option's net taker position is known;
the makers hold the opposite and are read as dealers (as R292). Three readings of the expiry:
  A  dose: the post-08:00 fade of the window move is larger when more expiring position sits near the money.
  B  unwind after expiry: dealers who delta-hedge hold -D in the perp, D being their delta in the expiring options.
     Once those settle, the hedge is closed by trading +D, so the perp moves with D after 08:00.
  C  unwind inside the window: a hedger who wants the settlement TWAP closes over 07:30-08:00, so the window moves
     with D.

usage: python scripts/run_charmexpiry.py [--plumbing]
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
from lab import data, prereg, stats  # noqa: E402
from scripts.run_clockflow import T0, T1, check_inputs, load_prices, price  # noqa: E402
from scripts.run_vpin import load_bars  # noqa: E402

LANE = ROOT / "experiments" / "charm_expiry_v1"
FLOW = data.ROOT / "deribit_trades"
PROVENANCE = ROOT / "docs" / "provenance" / "deribit_trades.json"
COINS = {"BTC": "BTCUSDT", "ETH": "ETHUSDT"}
MIN, HOUR, DAY = 60_000, 3_600_000, 86_400_000
DISC = ("2021-04-01", "2023-12-31")
VALID = ("2024-01-01", "2026-09-30")
HORIZONS = (60, 120)                 # minutes held after the 08:01 entry
BAND = 0.02                          # "near the money": |K / F - 1| <= 2% at 07:30
FLOOR = 1e-4                         # the dose N / ADV is floored at 0.01% before its log
LOOK, NEED = 52, 12                  # a feature is scaled on the coin's previous 52 Fridays, at least 12 defined
WINSOR = 5.0
ADV_DAYS, ADV_NEED, DAY_BARS = 30, 20, 1200
NW_LAG = 4                           # Fridays
T_MIN = 2.58                         # Bonferroni over 5 trials, two-sided 5%
COST, API = 3e-4, 8.5e-4             # per side: manual web at 1x (R289), API (reported)
ENTRY = 1.0                          # |x| for the signed rules (B, C)
TRIALS = 5
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------------------------------------------------- inputs
def fridays(t0=T0, t1=T1):
    """Expiry instants (ms): every Friday at 08:00 UTC from t0 to before t1."""
    days = pd.date_range(pd.Timestamp(t0, unit="ms"), pd.Timestamp(t1 - DAY, unit="ms"), freq="D")
    return days[days.weekday == 4].as_unit("ms").asi8.astype(np.int64) + 8 * HOUR


def load_expiring(cur, expiries, root=FLOW, hashes=None):
    """The hourly flow rows of one currency's options that expire at one of `expiries` (scripts/
    fetch_deribit_trades.py), from every monthly file, since a position runs from the option's first trade. With
    `hashes` (path relative to `root` -> sha256, from the provenance record), each file must still hash to it."""
    want = np.asarray(expiries, np.int64)
    parts = []
    for p in sorted((root / cur / "flow").glob("*.parquet")):
        if hashes is not None:
            rel = p.relative_to(root).as_posix()
            if hashes.get(rel) != prereg.sha256_file(p):
                raise prereg.PreregError(f"{rel}: not in the provenance record, or changed since it")
        f = pd.read_parquet(p, columns=["t", "instrument", "expiry_ms", "strike", "cp", "buy", "sell"])
        f = f[np.isin(f.expiry_ms.to_numpy(np.int64), want)]
        if len(f):
            parts.append(f)
    return pd.concat(parts, ignore_index=True)


def adv_daily(qv, t0=T0):
    """Per day (days since the epoch): the mean quote volume of the previous ADV_DAYS UTC days that have at least
    DAY_BARS valid 1-minute bars (at least ADV_NEED such days)."""
    nd = len(qv) // 1440
    q = qv[: nd * 1440].reshape(nd, 1440)
    tot = np.where(np.isfinite(q).sum(1) >= DAY_BARS, np.nansum(q, 1), np.nan)
    adv = pd.Series(tot).shift(1).rolling(ADV_DAYS, min_periods=ADV_NEED).mean().to_numpy()
    return pd.Series(adv, index=t0 // DAY + np.arange(nd))


# -------------------------------------------------------------------------------------------------------- exposure
def positions(rows, cut):
    """Per option in `rows` (one expiry): strike, call flag and the takers' net position (coins) over the rows of
    hours that start at or before `cut`. A row for hour t holds the trades in [t, t + 1 h), so it is known at t + 1 h."""
    f = rows[rows.t.to_numpy() <= cut]
    if not len(f):
        return np.zeros(0), np.zeros(0, bool), np.zeros(0)
    g = f.groupby("instrument", sort=True, observed=True).agg(strike=("strike", "first"), cp=("cp", "first"),
                                                               buy=("buy", "sum"), sell=("sell", "sum"))
    return g.strike.to_numpy(float), g.cp.to_numpy() == "C", (g.buy - g.sell).to_numpy(float)


def step_delta(F, K, call):
    """An option's delta at expiry: a call is 1 above its strike and 0 below, a put -1 below and 0 above, half at
    the strike."""
    d = np.where(F > K, 1.0, np.where(F < K, 0.0, 0.5))
    return np.where(call, d, d - 1.0)


def near_money(F, K, pos, band=BAND):
    """The gross expiring position (|taker position|, summed) with strikes within `band` of F, in USD."""
    m = np.abs(K - F) <= band * F
    return float(np.abs(pos[m]).sum() * F)


def dealer_delta(F, K, call, pos):
    """The dealers' delta in the expiring options at price F, in USD: minus the takers' position times the expiry
    delta."""
    return float(np.sum(-pos * step_delta(F, K, call)) * F)


# ----------------------------------------------------------------------------------------------------------- table
def friday_table(rows, P, adv, expiries, cur, t0=T0):
    """One row per Friday expiry e for one coin: the inputs known at each decision and the returns after it.
      07:30 decision (C): positions over rows of hours starting by 06:00, priced at P(07:30).
      08:01 decision (A, B): positions over rows of hours starting by 07:00 (known at 08:00); the dose uses P(07:30),
      the window's start, and the dealers' delta P(08:00)."""
    by = {int(e): g for e, g in rows.groupby("expiry_ms")}
    out = []
    for e in np.asarray(expiries, np.int64):
        g = by.get(int(e))
        p0730, p0731, p0759, p0800, p0801 = price(P, e + np.array([-30, -29, -1, 0, 1]) * MIN, t0)
        r = {"expiry": int(e), "coin": cur, "adv": adv.get(int(e // DAY), np.nan), "p0730": p0730, "p0731": p0731,
             "p0759": p0759, "p0800": p0800, "p0801": p0801, "n_opt": 0, "N": np.nan, "Db": np.nan, "Dc": np.nan}
        for h in HORIZONS:
            r[f"X{h}"] = float(price(P, [e + (1 + h) * MIN], t0)[0])
        if g is not None and np.isfinite(p0730):
            K, call, pos = positions(g, e - HOUR)
            r["n_opt"] = len(K)
            if len(K):
                r["N"] = near_money(p0730, K, pos)
                if np.isfinite(p0800):
                    r["Db"] = dealer_delta(p0800, K, call, pos)
            K, call, pos = positions(g, e - 2 * HOUR)
            r["Dc"] = dealer_delta(p0730, K, call, pos) if len(K) else np.nan
        out.append(r)
    t = pd.DataFrame(out)
    with np.errstate(invalid="ignore", divide="ignore"):
        t["m"] = t.p0800 / t.p0730 - 1
        for h in HORIZONS:
            t[f"y{h}"] = np.where(t.m != 0, -np.sign(t.m) * (t[f"X{h}"] / t.p0801 - 1), np.nan)   # the fade's gross
            t[f"r{h}"] = np.log(t[f"X{h}"] / t.p0801)
        t["rC"] = np.log(t.p0759 / t.p0731)
    return t


def trailing(v, center, look=LOOK, need=NEED):
    """v scaled on its previous `look` values (at least `need` defined): (v - mean) / sd if `center`, else v over
    their root mean square. Winsorized at +-WINSOR; NaN until `need` values exist."""
    v = np.asarray(v, float)
    out = np.full(len(v), np.nan)
    for i in range(len(v)):
        w = v[max(0, i - look):i]
        w = w[np.isfinite(w)]
        if len(w) < need or not np.isfinite(v[i]):
            continue
        if center:
            sd = w.std(ddof=1)
            out[i] = (v[i] - w.mean()) / sd if sd > 0 else np.nan
        else:
            rms = np.sqrt(np.mean(w ** 2))
            out[i] = v[i] / rms if rms > 0 else np.nan
    return np.clip(out, -WINSOR, WINSOR)


def features(tab):
    """xA (dose), xB and xC (dealers' expiring delta) per coin, each on the coin's own previous Fridays."""
    parts = []
    for _, t in tab.sort_values(["coin", "expiry"]).groupby("coin", sort=True):
        t = t.copy()
        with np.errstate(invalid="ignore", divide="ignore"):
            t["xA"] = trailing(np.log(np.maximum(t.N / t.adv, FLOOR)), center=True)
            t["xB"] = trailing(t.Db / t.adv, center=False)
            t["xC"] = trailing(t.Dc / t.adv, center=False)
        parts.append(t)
    t = pd.concat(parts, ignore_index=True)
    t["win"] = window_of(t.expiry.to_numpy())
    return t


def window_of(expiry):
    day = pd.to_datetime(np.asarray(expiry, np.int64) // DAY * DAY, unit="ms")
    out = np.full(len(day), "", dtype=object)
    for name, (a, b) in (("disc", DISC), ("valid", VALID)):
        out[(day >= pd.Timestamp(a)) & (day <= pd.Timestamp(b))] = name
    return out


# ------------------------------------------------------------------------------------------------------ inference
TRIAL_LIST = [("A", 60), ("A", 120), ("B", 60), ("B", 120), ("C", None)]


def _xy(name, h):
    return {"A": ("xA", f"y{h}"), "B": ("xB", f"r{h}"), "C": ("xC", "rC")}[name]


def products(t, name, h):
    """Per row: the product whose mean the trial tests. A demeans x and y per coin within the rows given (a slope
    on the dose, net of the fade's own mean); B and C take x r as it is (the sign of D is the prediction)."""
    x, y = _xy(name, h)
    d = t[np.isfinite(t[x]) & np.isfinite(t[y])].copy()
    if name == "A":
        d["xx"] = d[x] - d.groupby("coin")[x].transform("mean")
        d["yy"] = d[y] - d.groupby("coin")[y].transform("mean")
    else:
        d["xx"], d["yy"] = d[x], d[y]
    d["u"] = d.xx * d.yy
    return d


def nw_t(d, expiries):
    """Newey-West t (lag NW_LAG Fridays) of the mean over Fridays of u summed across coins; Fridays without a row are
    gaps."""
    u = d.groupby("expiry").u.sum().reindex(expiries)
    n, mu, t = stats.newey_west_t(u.to_numpy(), NW_LAG)
    return {"fridays": int(n), "rows": int(len(d)), "mean": float(mu) if np.isfinite(mu) else None,
            "t": float(t) if np.isfinite(t) else None}


def rule_trades(t, name, h):
    """The reported rule's trades (gross, simple return). A: fade the window move when xA >= 0, enter 08:01, hold h.
    B: take the sign of xB at 08:01 when |xB| >= ENTRY, hold h. C: take the sign of xC at 07:31 when |xC| >= ENTRY,
    exit 07:59."""
    if name == "A":
        d = t[(t.xA >= 0) & np.isfinite(t[f"y{h}"])]
        return d.assign(g=d[f"y{h}"])
    x, e, xit = ("xB", "p0801", f"X{h}") if name == "B" else ("xC", "p0731", "p0759")
    d = t[(np.abs(t[x]) >= ENTRY) & np.isfinite(t[e]) & np.isfinite(t[xit])]
    return d.assign(g=np.sign(d[x]) * (d[xit] / d[e] - 1))


def rule_stats(g, years):
    g = np.asarray(g, float)
    if not len(g):
        return {"trades": 0}
    nets = {m: g - 2 * m * COST for m in (1, 2, 3)}
    sd = nets[1].std(ddof=1) if len(g) > 1 else np.nan
    return {"trades": int(len(g)), "per_year": float(len(g) / years), "gross_bp": float(g.mean() * 1e4),
            **{f"net{m}_bp": float(v.mean() * 1e4) for m, v in nets.items()},
            "api_bp": float((g - 2 * API).mean() * 1e4),
            "t_net1": float(nets[1].mean() / sd * np.sqrt(len(g))) if sd > 0 else None,
            "hit": float((g > 0).mean())}


def _years(win):
    a, b = (DISC, VALID)[win == "valid"]
    return (pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25


def analyze(tab, expiries):
    """The 5 trials and their reports."""
    tests, passes, against = [], [], []
    for name, h in TRIAL_LIST:
        label = f"{name}" + (f" h{h}" if h else "")
        rec = {"trial": label, "x": _xy(name, h)[0], "y": _xy(name, h)[1]}
        for w in ("disc", "valid"):
            tw = tab[tab.win == w]
            rec[w] = nw_t(products(tw, name, h), expiries)
            rec[f"{w}_rule"] = rule_stats(rule_trades(tw, name, h).g, _years(w))
        tv = tab[tab.win == "valid"]
        rec["valid_by_coin"] = {c: nw_t(products(tv[tv.coin == c], name, h), expiries)["t"] for c in COINS}
        yr = pd.to_datetime(tv.expiry, unit="ms").dt.year
        rec["valid_by_year"] = {int(y): nw_t(products(tv[yr == y], name, h), expiries)["t"] for y in sorted(yr.unique())}
        if name == "A":                                                       # the fade on low-dose Fridays
            for w in ("disc", "valid"):
                tw = tab[tab.win == w]
                d = tw[(tw.xA < 0) & np.isfinite(tw[f"y{h}"])]
                rec[f"{w}_rule_low_dose"] = rule_stats(d[f"y{h}"], _years(w))
        tv_, td_ = rec["valid"]["t"], rec["disc"]["t"]
        rec["pass"] = bool(tv_ is not None and td_ is not None and tv_ >= T_MIN and td_ > 0)
        rec["significant_against"] = bool(tv_ is not None and td_ is not None and tv_ <= -T_MIN and td_ < 0)
        if rec["pass"]:
            passes.append(label)
        if rec["significant_against"]:
            against.append(label)
        tests.append(rec)
    return {"tests": tests, "passes": passes, "significant_against": against,
            "verdict": "PARTIAL" if passes else "NULL"}


def descriptives(tab):
    out = {}
    for c, t in tab.groupby("coin"):
        for w in ("disc", "valid"):
            x = t[t.win == w]
            out[f"{c} {w}"] = {
                "fridays": int(len(x)), "with_expiring_options": int((x.n_opt > 0).sum()),
                "median_expiring_options": float(x.n_opt.median()),
                "median_near_money_over_adv": float((x.N / x.adv).median()),
                "median_abs_dealer_delta_over_adv": float((x.Db.abs() / x.adv).median()),
                "share_dealers_long_delta": float((x.Db > 0).mean()),
                "rows_xA": int(np.isfinite(x.xA).sum()), "rows_xB": int(np.isfinite(x.xB).sum()),
                "rows_xC": int(np.isfinite(x.xC).sum())}
    return out


def build(hashes):
    exp = fridays()
    parts = []
    for cur, sym in COINS.items():
        rows = load_expiring(cur, exp, hashes=hashes)
        log(f"{cur}: {len(rows):,} flow rows over {rows.expiry_ms.nunique()} Friday expiries")
        path = data.ROOT / "klines_1m" / f"{sym}.parquet"
        parts.append(friday_table(rows, load_prices(path), adv_daily(load_bars(path)["quote_volume"]), exp, cur))
    return features(pd.concat(parts, ignore_index=True)), exp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true", help="counts only, no statistic (before the freeze)")
    a = ap.parse_args()
    hashes = {h["path"]: h["sha256"] for h in json.loads(PROVENANCE.read_text())["file_hashes"]}
    if a.plumbing:
        tab, exp = build(hashes)
        for c, t in tab.groupby("coin"):
            for w in ("disc", "valid"):
                x = t[t.win == w]
                log(f"{c} {w}: fridays {len(x)}, with expiring options {(x.n_opt > 0).sum()}, N = 0 on "
                    f"{(x.N == 0).sum()}, adv missing {x.adv.isna().sum()}, prices missing "
                    f"{x[['p0730', 'p0731', 'p0759', 'p0800', 'p0801', 'X60', 'X120']].isna().any(axis=1).sum()}, "
                    f"defined xA {np.isfinite(x.xA).sum()} xB {np.isfinite(x.xB).sum()} xC {np.isfinite(x.xC).sum()}")
        return
    sha = prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    tab, exp = build(hashes)
    res = analyze(tab, exp)
    (LANE / "results").mkdir(parents=True, exist_ok=True)
    tab.to_csv(LANE / "results" / "fridays.csv", index=False, float_format="%.10g")
    summary = {"lane": "charm_expiry_v1", "rid": "R296", "prereg_sha": sha, "inputs": shas, "trials": TRIALS,
               "bar": T_MIN, "cost_per_side_1x": COST, "api_per_side": API, "descriptives": descriptives(tab), **res,
               "run": pd.Timestamp.now(tz="UTC").isoformat()}
    (LANE / "results" / "summary.json").write_text(json.dumps(summary, indent=1))
    for t in res["tests"]:
        log(f"{t['trial']:>7} disc t {t['disc']['t']}  valid t {t['valid']['t']}  pass {t['pass']}")
    log("verdict", res["verdict"], "passes", res["passes"], "against", res["significant_against"])


if __name__ == "__main__":
    main()
