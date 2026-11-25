"""R531 carry_meta_v1: an ML meta-label filter on R275's carry book, across R525's 12 floorless x floor venue pairs.
Specification: experiments/carry_meta_v1/PREREG.md (frozen before `run`).

- **Primary rule (unchanged):** R275's book (L14d th5% K20, correlation guard) on `lab.xfund_v2`, R525's frozen loader
  and spec. It decides the side and the candidates.
- **Secondary model (the meta-label):** at each entry, a logistic regression (L2, standardized) predicts whether the
  trade will be profitable over its life at 2x costs (14 bp a leg, four leg-trades). A candidate whose probability is
  below 0.5 is skipped, and its slot stays free for the next candidate.
- **Features at the entry day d** (past and present only):
  s14 (the 14-day spread, %/yr); ds14 (s14 minus the same spread 14 days earlier); fvol (14-day standard deviation of
  the daily funding difference, annualized); basis (log of the long leg's value over the short leg's); fresh14 (share
  of the last 14 days on which both legs traded); two dummies for the floorless venue (bitfinex, deribit; kraken is
  the base).
- **Walk-forward, purged:** refit at the start of every calendar quarter. The training set holds the trades of the
  unfiltered books whose exit day is at least 14 days (the embargo) before the quarter starts. The first test quarter
  is the first one from 2024-01-01 with at least 300 training trades.
- **Compared:** the equal-weight portfolio of pairs (as R525) with and without the filter, over the test days.

usage: python scripts/run_carry_meta.py count   (supply of trades per year and pair; no P&L)
       python scripts/run_carry_meta.py run     (after the freeze; once)
"""
import json
import math
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import xfund as v1  # noqa: E402
from lab import xfund_v2 as v2  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402
from scripts import run_carry_v2_audit as loader  # noqa: E402  (frozen R437 loader)

LANE = ROOT / "experiments" / "carry_meta_v1"
SPEC = ROOT / "experiments" / "gap_breadth_v1" / "spec.toml"
FLOORLESS = ("kraken", "bitfinex", "deribit")
FLOOR = ("binance", "gate", "hyperliquid", "kucoin")
BOOK = (14, 0.05, 20)
COSTS = (0.0007, 0.0014, 0.0021)
LABEL_COST = 0.0014            # 2x, per leg-trade; four leg-trades per round trip
EMBARGO = 14
MIN_TRAIN = 300
TEST_FROM = pd.Timestamp("2024-01-01")
THRESHOLD = 0.5
FEATURES = ["s14", "ds14", "fvol", "basis", "fresh14", "v_bitfinex", "v_deribit"]


def features(u, c, lo, hi, d, floorless):
    """Feature dict for coin c, long venue lo, short venue hi, on day d (data up to d only), or None."""
    a, h = u.series[c][lo], u.series[c][hi]
    fa, fh = a.window(d, 14), h.window(d, 14)
    if fa is None or fh is None:
        return None
    s14 = (fh - fa) * 365.0 / 14
    fa0, fh0 = (a.window(d - 14, 14), h.window(d - 14, 14)) if d >= 28 else (None, None)
    ds14 = s14 - (fh0 - fa0) * 365.0 / 14 if fa0 is not None and fh0 is not None else 0.0
    diffs = [h.fund_on(k) - a.fund_on(k) for k in range(max(d - 13, 1), d + 1)]
    fvol = float(np.std(diffs)) * 365.0 if len(diffs) > 2 else 0.0
    va, vh = a.val[d], h.val[d]
    basis = math.log(va / vh) if math.isfinite(va) and math.isfinite(vh) and va > 0 and vh > 0 else 0.0
    fr = [bool(a.fresh[k] and h.fresh[k]) for k in range(max(d - 13, 0), d + 1)]
    return {"s14": s14, "ds14": ds14, "fvol": fvol, "basis": basis, "fresh14": sum(fr) / len(fr),
            "v_bitfinex": float(floorless == "bitfinex"), "v_deribit": float(floorless == "deribit")}


class FilterBook(v2.Book):
    """R275's book whose entries skip candidates the meta-model scores below THRESHOLD. `scorer(d, rows)` returns a
    probability per candidate row, or None before the first test quarter (then nothing is filtered)."""

    def __init__(self, vset, l, th, k, u=None, floorless=None, scorer=None, log=None):
        super().__init__(vset, l, th, k)
        self.u, self.floorless, self.scorer, self.log = u, floorless, scorer, log

    def entries(self, u, d):
        if len(self.open) >= self.slots:
            return []
        held = {p.coin for p in self.open}
        cs = []
        for c in range(len(u.keys)):
            if c in held:
                continue
            x = u.candidate(c, self.vset, d, self.lookback)
            if x is None or x.spread < self.threshold:
                continue
            a, h = u.series[c][x.lo], u.series[c][x.hi]
            if math.isfinite(a.val[d]) and math.isfinite(h.val[d]) and a.val[d] > 0 and h.val[d] > 0:
                cs.append((c, x))
        cs.sort(key=lambda z: (-z[1].spread, z[0]))
        free = self.slots - len(self.open)
        if self.scorer is not None and cs:
            feats = [features(u, c, x.lo, x.hi, d, self.floorless) for c, x in cs]
            ok = [(c, x, f) for (c, x), f in zip(cs, feats) if f is not None]
            p = self.scorer(d, [f for _, _, f in ok])
            if p is not None:
                kept = [(c, x) for (c, x, _), pi in zip(ok, p) if pi >= THRESHOLD]
                if self.log is not None:
                    self.log.append({"day": d, "candidates": len(ok), "kept": len(kept)})
                cs = kept
        new = []
        for c, x in cs[:free]:
            a, h = u.series[c][x.lo], u.series[c][x.hi]
            new.append(v2.Position(c, x.lo, x.hi, d, x.spread, pl_e=float(a.val[d]), ph_e=float(h.val[d])))
        self.open.extend(new)
        return new


def pairs():
    return [(a, b) for a in FLOORLESS for b in FLOOR]


def replay_pair(u, a, b, scorer=None, log=None):
    vset = [u.names.index(a), u.names.index(b)]
    book = FilterBook(vset, *BOOK, u=u, floorless=a, scorer=scorer, log=log)
    return v2.replay(u, book, v2.window_start(u, vset, BOOK[0]))


def trade_table(u, a, trades):
    """One row per trade of the unfiltered book: features at entry, label at 2x costs, entry and exit days."""
    out = []
    for t in trades:
        c = u.keys.index(t["coin"])
        lo, hi = u.names.index(t["long"]), u.names.index(t["short"])
        f = features(u, c, lo, hi, t["entry_day"], a)
        if f is None:
            continue
        net2 = t["price_pnl"] + t["funding_pnl"] - 4 * LABEL_COST
        out.append({**f, "entry_day": t["entry_day"], "exit_day": t["exit_day"], "net2": net2, "y": int(net2 > 0),
                    "floorless": a})
    return out


def day_ts(u, d):
    return pd.Timestamp(u.t0 + d * v1.DAY, unit="ms")


def quarters(u):
    """[(start_day, end_day)] of calendar quarters from TEST_FROM to the last day."""
    out, q = [], TEST_FROM
    last = day_ts(u, u.nd - 1)
    while q <= last:
        q2 = q + pd.offsets.QuarterBegin(startingMonth=1)
        s = int((q - pd.Timestamp(u.t0, unit="ms")) / pd.Timedelta(days=1))
        e = int((q2 - pd.Timestamp(u.t0, unit="ms")) / pd.Timedelta(days=1))
        out.append((max(s, 0), min(e, u.nd)))
        q = q2
    return out


def fit_models(tab, qs):
    """{quarter start day: (scaler mean, scale, model)} for quarters with at least MIN_TRAIN purged training trades."""
    from sklearn.linear_model import LogisticRegression
    models = {}
    for s, _ in qs:
        tr = tab[tab.exit_day < s - EMBARGO]
        if len(tr) < MIN_TRAIN or tr.y.nunique() < 2:
            continue
        X = tr[FEATURES].to_numpy(float)
        mu, sd = X.mean(0), X.std(0)
        sd[sd == 0] = 1.0
        m = LogisticRegression(C=1.0, max_iter=1000).fit((X - mu) / sd, tr.y.to_numpy())
        models[s] = (mu, sd, m)
    return models


def make_scorer(models, qs):
    starts = sorted(models)
    first = starts[0] if starts else None

    def scorer(d, rows):
        if first is None or d < first:
            return None
        s = max(x for x in starts if x <= d)
        mu, sd, m = models[s]
        X = np.array([[r[k] for k in FEATURES] for r in rows], float)
        return m.predict_proba((X - mu) / sd)[:, 1]
    return scorer, first


def portfolio(u, books, cost, d0):
    nets = {}
    for name, rows in books.items():
        if not len(rows):
            continue
        dates = pd.to_datetime(u.t0 + rows.day * v1.DAY, unit="ms").dt.normalize()
        nets[name] = pd.Series(v2.net(rows, BOOK[2], cost).to_numpy(float), index=dates)
    df = pd.concat(nets, axis=1, sort=True)
    port = df.mean(axis=1, skipna=True).dropna()
    return port[port.index >= day_ts(u, d0).normalize()]


def count(u):
    rows = []
    for a, b in pairs():
        _, tr = replay_pair(u, a, b)
        for t in tr:
            rows.append({"pair": f"{a}+{b}", "year": day_ts(u, t["entry_day"]).year})
    df = pd.DataFrame(rows)
    print(df.groupby(["year"]).size().to_string())
    print(df.groupby(["pair"]).size().to_string())


def run(lane=LANE):
    from lab.prereg import verify
    verify(lane / "PREREG.md")
    res = lane / "results"
    if (res / "report.json").exists():
        raise SystemExit("results exist: this lane is read once")
    sp = tomllib.loads(SPEC.read_text())
    u = loader.load(sp, v2, set(FLOORLESS + FLOOR))
    base_rows, tabs = {}, []
    for a, b in pairs():
        rows, tr = replay_pair(u, a, b)
        base_rows[f"{a}+{b}"] = rows
        tabs += trade_table(u, a, tr)
    tab = pd.DataFrame(tabs)
    qs = quarters(u)
    models = fit_models(tab, qs)
    scorer, first = make_scorer(models, qs)
    if first is None:
        raise SystemExit("no quarter reaches the training minimum")
    filt_rows, log = {}, []
    for a, b in pairs():
        rows, _ = replay_pair(u, a, b, scorer=scorer, log=log)
        filt_rows[f"{a}+{b}"] = rows
    rep = {"first_test_day": str(day_ts(u, first).date()), "models": len(models), "trades_unfiltered": len(tab),
           "label_positive_share": float(tab.y.mean())}
    for k, cost in zip(("1x", "2x", "3x"), COSTS):
        p0, p1 = portfolio(u, base_rows, cost, first), portfolio(u, filt_rows, cost, first)
        j = pd.concat([p0.rename("frozen"), p1.rename("meta")], axis=1, sort=True).dropna()
        diff = j.meta - j.frozen
        rep[k] = {"days": len(j), "frozen_ann_pct": float(j.frozen.mean() * 36500),
                  "meta_ann_pct": float(j.meta.mean() * 36500), "diff_ann_pct": float(diff.mean() * 36500),
                  "diff_nw_t": float(newey_west_t(diff.to_numpy(), 10)[2]) if len(diff) > 30 else None,
                  "by_year_diff_ann_pct": {int(y): float(g.mean() * 36500) for y, g in diff.groupby(diff.index.year)},
                  "by_year_meta_ann_pct": {int(y): float(g.mean() * 36500) for y, g in
                                           j.meta.groupby(j.index.year)}}
    lg = pd.DataFrame(log)
    rep["filter"] = {"days_scored": len(lg), "candidates": int(lg.candidates.sum()) if len(lg) else 0,
                     "kept": int(lg.kept.sum()) if len(lg) else 0}
    r2 = rep["2x"]
    years = r2["by_year_diff_ann_pct"]
    checks = {"diff_nw_t_ge_2p5": (r2["diff_nw_t"] or 0) >= 2.5,
              "diff_pos_every_year": bool(years) and all(v > 0 for v in years.values()),
              "meta_pos_at_2x": r2["meta_ann_pct"] > 0}
    rep["checks"] = checks
    rep["verdict"] = "PASS" if all(checks.values()) else "FAIL"
    res.mkdir(parents=True, exist_ok=True)
    tab.to_csv(res / "trades_unfiltered.csv", index=False)
    (res / "report.json").write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps(rep, indent=1, default=str))
    return rep


if __name__ == "__main__":
    cmd = sys.argv[1:]
    if cmd == ["count"]:
        count(loader.load(tomllib.loads(SPEC.read_text()), v2, set(FLOORLESS + FLOOR)))
    elif cmd == ["run"]:
        run()
    else:
        raise SystemExit("usage: python scripts/run_carry_meta.py count|run")
