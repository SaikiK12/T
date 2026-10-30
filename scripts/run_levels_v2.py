"""R333 level_probability_v2: the owner's break-or-rebound probability model (M412) on the top 100 Binance perps.

Codex's R330 tested the idea on four MEXC coins, one decision a day; its preselected policy declined all 178
validation events (NULL_INACTIVE). This lane keeps R330's level and outcome definitions and widens the sample:
- levels: the extremes of the prior `lookback` hourly closes, excluding the decision close; sigma12 = sqrt(12 x mean of
  the last 72 squared hourly log returns); a close qualifies within 0.25 sigma12 of the nearest level (ties go to
  support). Resistance is side +1 (its breakout is up), support side -1.
- outcome: barriers at +/- sigma12 around the entry's log close, read on hourly closes; the first one crossed within
  the horizon decides, else a timeout at the horizon. The class is "through" (+1, the breakout way), "away" (-1) or
  "timeout" (0).
- payoff: class means of the realized through-direction return in sigma12 units, learned on training events only;
  the expected through-direction return is sigma12 x sum(p_class x payoff_class).
New here: every hour of 2021-01..2026-09, the point-in-time top 100 crypto perps by 30-day quote volume, one open
event per coin, a gradient-boosted classifier on 17 causal features, refit each quarter on events that ended at least a
day before the quarter. V0 enters at the decision close (the lab's convention); V1 keeps R330's one-hour delay.

usage: python scripts/run_levels_v2.py --plumbing    # event counts and the data digest; no label, return or model
       python scripts/run_levels_v2.py --run         # verifies the frozen PREREG and its inputs, then runs
"""
import argparse
import gzip
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from numba import njit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, panel, prereg, research  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402

LANE = ROOT / "experiments" / "level_probability_v2"
TRADFI = ROOT / "experiments" / "venue_gap_v1" / "results" / "tradfi_symbols.json"
H = 3_600_000
DAY = 24 * H
SIG_N = 72                    # hourly log returns in sigma12
PROX = 0.25                   # a close within 0.25 sigma12 of a level qualifies
TOP = 100                     # point-in-time eligibility: top 100 by trailing 30-day quote volume
MAJOR_N = 720                 # a level is "major" when it is also the extreme of the prior 720 closes
FIRST_TEST = "2022-01-01"     # walk-forward: quarterly test blocks from here; training starts 2021-01-01
MID = "2024-01-01"            # the two halves of the test period
EMBARGO = 24                  # hours between a training event's exit close and its test block's start
FEATURES = ("dist", "app24", "app4", "age", "touches", "range", "major", "volr", "vsurge", "taker", "fund", "prem",
            "btc", "lrank", "hsin", "hcos", "side")
# (name, level lookback in hours, horizon in hours, entry delay in hours); V0 is the primary
VARIANTS = (("V0", 72, 12, 0), ("V1", 72, 12, 1), ("V2", 24, 12, 0), ("V3", 168, 12, 0), ("V4", 72, 24, 0))
HGB = dict(learning_rate=0.05, max_iter=300, max_leaf_nodes=31, min_samples_leaf=500, l2_regularization=1.0,
           early_stopping=False, random_state=0)
MULTS = (1, 2, 3)
ZERO_FEE = 1e-4               # one-way cost on a MEXC 0/0-fee contract with a one-tick spread (half of ~2 bp): measured only
TRIALS = 11                   # 8 books (V0 P1/P2/P3/P0, V1-V4 P1) and 3 controls (CLIM, THROUGH, AWAY)
FIELDS = ("lr", "qv", "tbq", "fund", "prem", "elig", "rank", "cost", "ret")
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def prev_max(x, n):
    """max of x[i-n..i-1]; NaN unless all n are valid."""
    return pd.Series(x).shift(1).rolling(n, min_periods=n).max().values


def prev_min(x, n):
    return pd.Series(x).shift(1).rolling(n, min_periods=n).min().values


def sigma12(lr):
    r = np.diff(lr, prepend=np.nan)
    return np.sqrt(12 * pd.Series(r ** 2).rolling(SIG_N, min_periods=SIG_N).mean().values)


@njit(cache=True)
def _age_touches(lr, level, sig, rows, n):
    """At each decision row: hours since the level was last printed among the prior n closes, and how many other of
    those closes sat within PROX sigma12 of it."""
    age = np.full(len(rows), np.nan)
    touch = np.full(len(rows), np.nan)
    for k in range(len(rows)):
        i = rows[k]
        last = -1
        for j in range(i - n, i):
            if lr[j] == level[k]:
                last = j
        if last < 0:
            continue
        cnt = 0
        for j in range(i - n, i):
            if j != last and abs(lr[j] - level[k]) <= PROX * sig[i]:
                cnt += 1
        age[k] = i - last
        touch[k] = cnt
    return age, touch


@njit(cache=True)
def _label(cand, side, lr, ret, sig, horizon, delay):
    """Walk the candidate rows in order with one open event per coin. Entry row e = i + delay; barriers at
    lr[e] +/- sig[i] on the closes e+1..e+horizon; exit x at the first close on or beyond a barrier, else e+horizon.
    Class +side when the upper barrier is crossed, -side for the lower one, 0 on a timeout. The through-direction
    return is side x sum(ret[e..x-1]) (next-bar returns net of funding). Status per candidate: 1 kept, 2 dropped (a
    close or return on the path is missing; the coin is free again from the next row), 0 skipped (an event is open, or
    the archive ends before the horizon). The next event may start at row x + 1."""
    T = len(lr)
    n = len(cand)
    ent = np.full(n, -1, np.int64)
    ext = np.full(n, -1, np.int64)
    cls = np.zeros(n, np.int8)
    g = np.full(n, np.nan)
    st = np.zeros(n, np.int8)
    free = -1
    for k in range(n):
        i = cand[k]
        if i < free:
            continue
        e = i + delay
        if e + horizon >= T:
            break
        d = side[k]
        bad = np.isnan(lr[e])
        x = e + horizon
        c = 0
        if not bad:
            up = lr[e] + sig[i]
            dn = lr[e] - sig[i]
            for h in range(1, horizon + 1):
                v = lr[e + h]
                if np.isnan(v):
                    bad = True
                    break
                if v >= up:
                    c = d
                    x = e + h
                    break
                if v <= dn:
                    c = -d
                    x = e + h
                    break
        s = 0.0
        if not bad:
            for j in range(e, x):
                s += ret[j]
            bad = np.isnan(s)
        if bad:
            st[k] = 2
            free = i + 1
            continue
        ent[k] = e
        ext[k] = x
        cls[k] = c
        g[k] = d * s
        st[k] = 1
        free = x + 1
    return ent, ext, cls, g, st


def coin_events(t, x, btc_lr, btc_sig, lookback, horizon, delay):
    """One coin's events for one variant: the features at the decision row, entry and exit rows, class and
    through-direction return. x holds the coin's hourly arrays (FIELDS). Returns (frame or None, candidates, dropped)."""
    lr = x["lr"]
    sig = sigma12(lr)
    res, sup = prev_max(lr, lookback), prev_min(lr, lookback)
    qv_ok = pd.Series((x["qv"] > 0).astype(float)).rolling(SIG_N, min_periods=SIG_N).min().values == 1
    with np.errstate(invalid="ignore", divide="ignore"):
        valid = x["elig"] & np.isfinite(lr) & (sig > 0) & np.isfinite(res) & np.isfinite(sup) & qv_ok
        dr = np.abs(res - lr) / sig
        ds = np.abs(lr - sup) / sig
    near_s = valid & (ds <= PROX) & (ds <= dr)
    near_r = valid & (dr <= PROX) & (dr < ds)
    cand = np.flatnonzero(near_s | near_r)
    if len(cand) == 0:
        return None, 0, 0
    side = np.where(near_r[cand], 1, -1).astype(np.int8)
    ent, ext, cls, g, st = _label(cand, side, lr, x["ret"], sig, horizon, delay)
    keep = st == 1
    n_drop = int((st == 2).sum())
    if not keep.any():
        return None, len(cand), n_drop
    i, d = cand[keep], side[keep].astype(float)
    level = np.where(d > 0, res[i], sup[i])
    s = sig[i]
    age, touch = _age_touches(lr, level, sig, i, lookback)
    hi, lo = prev_max(lr, MAJOR_N)[i], prev_min(lr, MAJOR_N)[i]
    major = np.where(d > 0, level >= hi, level <= lo).astype(float)
    major[~np.isfinite(np.where(d > 0, hi, lo))] = np.nan
    r = np.diff(lr, prepend=np.nan)
    roll = lambda a, n, f: getattr(pd.Series(a).rolling(n, min_periods=n), f)().values[i]
    back = lambda a, k: a[i - k]                     # every kept row has i >= max(lookback, SIG_N) >= 24
    hour = (t[i] // H) % 24
    q4, q72 = roll(x["qv"], 4, "sum"), roll(x["qv"], 72, "mean")
    with np.errstate(invalid="ignore", divide="ignore"):
        out = pd.DataFrame({
            "row": i, "t": t[i], "entry": ent[keep], "exit": ext[keep], "cls": cls[keep], "g": g[keep], "sig": s,
            "cost": x["cost"][i],
            "dist": d * (level - lr[i]) / s,
            "app24": d * (lr[i] - back(lr, 24)) / s,
            "app4": d * (lr[i] - back(lr, 4)) / s,
            "age": age / lookback,
            "touches": touch,
            "range": (res[i] - sup[i]) / s,
            "major": major,
            "volr": roll(r, 24, "std") / roll(r, 72, "std"),
            "vsurge": np.log(q4 / 4 / q72),
            "taker": d * (2 * roll(x["tbq"], 4, "sum") / q4 - 1),
            "fund": d * x["fund"][i],
            "prem": d * x["prem"][i],
            "btc": d * (btc_lr[i] - back(btc_lr, 24)) / btc_sig[i],
            "lrank": np.log(x["rank"][i]),
            "hsin": np.sin(2 * np.pi * hour / 24), "hcos": np.cos(2 * np.pi * hour / 24),
            "side": d})
    return out, len(cand), n_drop


def load():
    """The point-in-time top 100, built as research.make_universe builds the lab's universes, over every hourly kline
    file with the TradFi perps removed before ranking: rank by trailing 30-day mean quote volume (past bars only),
    eligible when rank <= 100, the one-way cost tier of the rank (engine.cost_matrix), and the next-bar return net of
    the funding a long pays (engine.forward_returns). The cache in data/research cannot serve: its columns are the
    coins ever in the top 50, so its ranks 51-100 would hold only coins that reach the top 50 at some time. The panel
    loader refuses reserved rows."""
    tradfi = set(json.loads(TRADFI.read_text()))
    syms = sorted(f.stem for f in (data.ROOT / "klines_1h").glob("*.parquet") if f.stem not in tradfi)
    p = panel.load_panel(syms, start=panel.START)
    p = p.columns(np.flatnonzero(~np.isnan(p["close"]).all(axis=0)))        # a bar inside the window
    u = research.make_universe(p, elig_top=TOP, col_top=TOP)
    del p
    c = u.p["close"].astype(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        lr = np.where(c > 0, np.log(np.where(c > 0, c, 1.0)), np.nan)
    f = lambda k: u.p[k].astype(float)
    return dict(t=np.asarray(u.p.t, np.int64), syms=list(u.p.symbols), lr=lr, elig=u.elig, rank=u.rank.astype(float),
                cost=u.cmat.astype(float), ret=u.ret.astype(float), qv=f("quote_volume"),
                tbq=f("taker_buy_quote_volume"), fund=f("funding"), prem=f("premium"),
                btc=list(u.p.symbols).index("BTCUSDT"))


def digest(D):
    """sha256 of the symbols and every array the run reads, in a fixed order: the data identity frozen in the PREREG."""
    h = hashlib.sha256("\n".join(D["syms"]).encode())
    for k in ("t",) + FIELDS:
        a = np.ascontiguousarray(D[k])
        h.update(f"{k}:{a.dtype}:{a.shape}".encode())
        h.update(a.tobytes())
    return h.hexdigest()


def events(D, lookback, horizon, delay):
    t = D["t"]
    btc_lr = D["lr"][:, D["btc"]]
    btc_sig = sigma12(btc_lr)
    frames, n_cand, n_drop = [], 0, 0
    for j, s in enumerate(D["syms"]):
        ev, c, dr = coin_events(t, {k: D[k][:, j] for k in FIELDS}, btc_lr, btc_sig, lookback, horizon, delay)
        n_cand += c
        n_drop += dr
        if ev is not None:
            ev.insert(0, "symbol", s)
            frames.append(ev)
    ev = pd.concat(frames, ignore_index=True)
    ev["exit_t"] = t[ev["exit"].values]
    ev = ev.sort_values(["t", "symbol"], kind="stable").reset_index(drop=True)
    return ev, {"candidates": n_cand, "dropped_invalid_path": n_drop}


def blocks(end_ms):
    """Quarterly test blocks [start, end) in ms from FIRST_TEST while the block starts within the archive."""
    starts = [int(a.timestamp() * 1000) for a in pd.date_range(FIRST_TEST, periods=40, freq="QS", tz="UTC")]
    return [(a, b) for a, b in zip(starts[:-1], starts[1:]) if a <= end_ms]


def train_mask(exit_t, a):
    """Training events for the block starting at a: the exit bar closed at least EMBARGO hours before a."""
    return exit_t + H + EMBARGO * H <= a


def fit_predict(ev, block_list, params=HGB):
    """Walk-forward. Per test block: fit on every earlier event that passes train_mask, then predict the block.
    Returns per event (NaN outside the test blocks): the class probabilities (through, away, timeout), the training
    climatology, the expected through-direction return in sigma12 units from each, and the training 90th percentile of
    the model's |expected|; plus one record per fit."""
    from sklearn.ensemble import HistGradientBoostingClassifier
    n = len(ev)
    P, C = np.full((n, 3), np.nan), np.full((n, 3), np.nan)
    E, EC, Q90 = np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan)
    order = [1, -1, 0]
    X = ev[list(FEATURES)].values.astype(float)
    y = ev["cls"].values.astype(int)
    gs = ev["g"].values / ev["sig"].values
    tt, xt = ev["t"].values, ev["exit_t"].values
    fits = []
    for a, b in block_list:
        test = (tt >= a) & (tt < b)
        train = train_mask(xt, a)
        if not test.any() or train.sum() < 1000:
            continue
        m = HistGradientBoostingClassifier(**params).fit(X[train], y[train])
        proba = lambda Z: np.stack([m.predict_proba(Z)[:, list(m.classes_).index(c)] if c in m.classes_
                                    else np.zeros(len(Z)) for c in order], axis=1)   # a class absent in training: 0
        clim = np.array([(y[train] == c).mean() for c in order])
        pay = np.array([gs[train][y[train] == c].mean() if (y[train] == c).any() else 0.0 for c in order])
        p = proba(X[test])
        P[test], C[test] = p, clim
        E[test], EC[test] = p @ pay, clim @ pay
        Q90[test] = np.quantile(np.abs(proba(X[train]) @ pay), 0.9)
        fits.append({"block": pd.Timestamp(a, unit="ms", tz="UTC").strftime("%Y-%m-%d"), "train": int(train.sum()),
                     "test": int(test.sum()), "clim": clim.round(4).tolist(), "payoff_sigma": pay.round(4).tolist()})
        log("fit", fits[-1]["block"], fits[-1]["train"], fits[-1]["test"])
    return P, C, E, EC, Q90, fits


def decide(ev, E, rule, Q90=None):
    """Side per event: +1 trade through the level, -1 trade away from it, 0 abstain. E is in sigma12 units."""
    sig, rt2 = ev["sig"].values, 4 * ev["cost"].values          # 2x round trip = 2 x (entry + exit) one-way cost
    edge = E * sig
    with np.errstate(invalid="ignore"):
        if rule == "P1":                                          # the expected gross covers the 2x round trip
            take = np.abs(edge) > rt2
        elif rule == "P2":                                        # R330's rule: plus a 0.25 sigma12 reserve
            take = np.abs(edge) > rt2 + 0.25 * sig
        elif rule == "P3":                                        # the model's most confident tenth, still above P1
            take = (np.abs(E) >= Q90) & (np.abs(edge) > rt2)
        elif rule == "P0":                                        # the 2x round trip at the zero-fee cost (measured)
            take = np.abs(edge) > 4 * ZERO_FEE
        else:
            raise ValueError(rule)
    return np.where(take & np.isfinite(E), np.sign(edge), 0).astype(int)


def book(ev, sides, mult, one_way=None):
    """Per-trade net returns at mult x the one-way cost on entry and exit (the coin's tier, or a flat one_way), and each
    trade's entry day."""
    on = sides != 0
    cost = ev["cost"].values[on] if one_way is None else np.full(int(on.sum()), one_way)
    net = sides[on] * ev["g"].values[on] - 2 * mult * cost
    return net, (ev["t"].values[on] // DAY).astype(np.int64)


def measures(ev, sides, d0, d1):
    """Reported, never decided on: the gross book, the book at the zero-fee cost, and the one-way cost at which the
    mean trade breaks even."""
    on = sides != 0
    return {"gross": summarize(*book(ev, sides, 0), d0, d1),
            "zero_fee": summarize(*book(ev, sides, 1, ZERO_FEE), d0, d1),
            "break_even_bp_one_way": round(1e4 * float(np.mean(sides[on] * ev["g"].values[on])) / 2, 2)
            if on.any() else None}


def summarize(net, day, d0, d1, best=10):
    """Trades, the calendar-day series of each day's mean net per trade with its Newey-West t (lag 3), the hit rate
    and the day mean without the best `best` days."""
    sel = (day >= d0) & (day < d1)
    net, day = net[sel], day[sel]
    if len(net) == 0:
        return {"trades": 0}
    s = pd.Series(net).groupby(day).mean()
    full = pd.Series(np.nan, index=np.arange(d0, d1))
    full.loc[s.index] = s.values
    n, mu, t = newey_west_t(full.values, 3)
    trimmed = s.drop(s.nlargest(best).index) if len(s) > best else s.iloc[:0]
    return {"trades": int(len(net)), "days": int(n), "bp_per_trade": round(1e4 * float(np.mean(net)), 2),
            "bp_per_day": round(1e4 * mu, 2), "t": None if np.isnan(t) else round(float(t), 2),
            "hit": round(float((net > 0).mean()), 4),
            "bp_per_day_wo_best10": round(1e4 * float(trimmed.mean()), 2) if len(trimmed) else None}


def reliability(p, hit, bins=10):
    """Mean predicted probability against the realized share, by decile of the prediction."""
    q = pd.qcut(p, bins, labels=False, duplicates="drop")
    g = pd.DataFrame({"q": q, "p": p, "y": hit}).groupby("q")
    return [{"n": int(len(x)), "pred": round(float(x.p.mean()), 4), "real": round(float(x.y.mean()), 4)}
            for _, x in g]


def plumbing():
    log("loading")
    D = load()
    out = {"symbols": len(D["syms"]), "rows": len(D["t"]), "digest": digest(D), "variants": {}}
    for name, lb, hz, dl in VARIANTS:
        t0 = time.time()
        ev, counts = events(D, lb, hz, dl)
        yr = pd.to_datetime(ev["t"], unit="ms", utc=True).dt.year
        out["variants"][name] = {**counts, "events": int(len(ev)), "coins": int(ev["symbol"].nunique()),
                                 "by_year": {int(k): int(v) for k, v in yr.value_counts().sort_index().items()},
                                 "support_share": round(float((ev["side"] < 0).mean()), 4),
                                 "missing_share": {f: round(float(ev[f].isna().mean()), 4) for f in FEATURES},
                                 "seconds": round(time.time() - t0, 1)}
        log(name, len(ev), "events")
    print(json.dumps(out, indent=1))


def frozen_digest(text):
    return re.search(r"Data digest:\*\* `([0-9a-f]{64})`", text).group(1)


def run():
    from scripts.run_clockflow import check_inputs
    sha = prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    import sklearn
    out_dir = LANE / "results"
    out_dir.mkdir(exist_ok=True)
    D = load()
    dg = digest(D)
    if dg != frozen_digest((LANE / "PREREG.md").read_text()):
        raise prereg.PreregError(f"data digest {dg} differs from the frozen one")
    blist = blocks(int(D["t"][-1]))
    d0, d1 = blist[0][0] // DAY, int(D["t"][-1]) // DAY + 1
    mid = int(pd.Timestamp(MID, tz="UTC").timestamp() * 1000) // DAY
    res = {"rid": "R333", "prereg_sha256": sha, "inputs": shas, "data_digest": dg, "trials": TRIALS,
           "versions": {"sklearn": sklearn.__version__, "numpy": np.__version__, "pandas": pd.__version__},
           "variants": {}, "books": {}, "controls": {}, "skill": {}}
    rng = np.random.default_rng(333)
    for name, lb, hz, dl in VARIANTS:
        ev, counts = events(D, lb, hz, dl)
        P, C, E, EC, Q90, fits = fit_predict(ev, blist)
        oos = np.isfinite(E)
        res["variants"][name] = {"lookback": lb, "horizon": hz, "delay": dl, **counts, "events": int(len(ev)),
                                 "oos_events": int(oos.sum()), "fits": fits}
        for rule in (("P1", "P2", "P3", "P0") if name == "V0" else ("P1",)):
            sides = decide(ev, E, rule, Q90)
            entry = {f"{m}x": summarize(*book(ev, sides, m), d0, d1) for m in MULTS}
            entry.update(measures(ev, sides, d0, d1))
            net, day = book(ev, sides, 1)
            early = day < mid
            entry["halves_1x"] = [summarize(net[early], day[early], d0, mid),
                                  summarize(net[~early], day[~early], mid, d1)]
            years = pd.to_datetime(day * DAY, unit="ms", utc=True).year.values
            entry["by_year_1x_bp_per_trade"] = {int(y): round(1e4 * float(net[years == y].mean()), 2)
                                                for y in sorted(set(years))}
            entry["through_share"] = round(float((sides[sides != 0] > 0).mean()), 4) if (sides != 0).any() else None
            res["books"][f"{name}{rule}"] = entry
            log(f"{name}{rule}", entry["1x"], entry["2x"].get("bp_per_day"), entry["3x"].get("bp_per_day"))
        if name != "V0":
            continue
        for key, sides in (("CLIM", decide(ev, EC, "P1")), ("THROUGH", np.where(oos, 1, 0)),
                           ("AWAY", np.where(oos, -1, 0))):
            res["controls"][key] = {f"{m}x": summarize(*book(ev, sides, m), d0, d1) for m in MULTS}
            res["controls"][key].update(measures(ev, sides, d0, d1))
        s1 = decide(ev, E, "P1", Q90)
        on = s1 != 0
        if on.any():                                  # placebo: V0P1's trades with random sides, 1x
            g, c = ev["g"].values[on], ev["cost"].values[on]
            actual = float(np.mean(s1[on] * g - 2 * c))
            draws = np.array([np.mean(rng.choice((-1, 1), size=on.sum()) * g - 2 * c) for _ in range(1000)])
            res["controls"]["RANDOM_SIDES"] = {"actual_bp_per_trade_1x": round(1e4 * actual, 2),
                                               "placebo_mean_bp": round(1e4 * float(draws.mean()), 2),
                                               "p_placebo_ge_actual": float((draws >= actual).mean())}
        y = ev["cls"].values
        hot = np.stack([y == 1, y == -1, y == 0], axis=1).astype(float)
        ll_m = -np.log(np.clip((P * hot).sum(1), 1e-9, 1))
        ll_c = -np.log(np.clip((C * hot).sum(1), 1e-9, 1))
        br_m, br_c = ((P - hot) ** 2).sum(1), ((C - hot) ** 2).sum(1)
        day = (ev["t"].values // DAY).astype(np.int64)
        for key, m_, c_ in (("logloss", ll_m, ll_c), ("brier", br_m, br_c)):
            s = pd.Series((m_ - c_)[oos]).groupby(day[oos]).mean()
            full = pd.Series(np.nan, index=np.arange(d0, d1))
            full.loc[s.index] = s.values
            n, mu, t = newey_west_t(full.values, 3)
            res["skill"][key] = {"days": int(n), "model_minus_clim": round(float(mu), 6),
                                 "t": None if np.isnan(t) else round(float(t), 2),
                                 "model": round(float(m_[oos].mean()), 5), "clim": round(float(c_[oos].mean()), 5)}
        res["skill"]["reliability_through"] = reliability(P[oos, 0], (y[oos] == 1).astype(float))
        res["skill"]["reliability_away"] = reliability(P[oos, 1], (y[oos] == -1).astype(float))
        frame = ev.loc[oos, ["symbol", "t", "exit", "cls", "g", "sig", "cost", "side"]].copy()
        frame["p_through"], frame["p_away"], frame["p_timeout"] = P[oos, 0], P[oos, 1], P[oos, 2]
        frame["E_sigma"], frame["side_P1"] = E[oos], s1[oos]
        with gzip.open(out_dir / "v0_oos_events.csv.gz", "wt") as fh:
            frame.to_csv(fh, index=False, float_format="%.6g")
    primary, sk = res["books"]["V0P1"], res["skill"]["logloss"]
    checks = {
        "t_1x_ge_2": (primary["1x"].get("t") or -99) >= 2.0,
        "mean_2x_positive": (primary["2x"].get("bp_per_day") or -1) > 0,
        "wo_best10_1x_positive": (primary["1x"].get("bp_per_day_wo_best10") or -1) > 0,
        "both_halves_1x_positive": all((h.get("bp_per_day") or -1) > 0 for h in primary["halves_1x"]),
        "logloss_beats_clim_t_le_-2": (sk.get("t") or 99) <= -2.0}
    res["decision"] = {"checks": checks, "verdict": "PARTIAL (gate 0)" if all(checks.values()) else "NULL"}
    (out_dir / "summary.json").write_text(json.dumps(res, indent=1))
    log("verdict", res["decision"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.plumbing:
        plumbing()
    elif a.run:
        run()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
