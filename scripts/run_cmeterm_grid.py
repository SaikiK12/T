"""R506 cmeterm_grid_v1 (M551): a pre-registered grid of 432 cost- and confidence-aware variants of R503's commodity
carry book, on R505's CME data, read with walk-forward selection, CSCV PBO, Hansen's SPA and the deflated Sharpe.

Why: R503-R505 read one textbook rule. The owner asked (2026-11-17) why so few parameters, when costs can be managed
by strategy and by confidence and both the losses and the edge can sit anywhere. Searching wide is fine if the search
is counted: every variant below is fixed before any CME settlement is read, all 432 are counted as trials, and the
verdict is on a walk-forward strategy that picks each year's variant from the past only.

The grid (4 x 3 x 3 x 3 x 2 x 2 = 432), on R503's data, contracts, costs and validity rules:
- signal: carry (R503's), carry12 (mean of the root's monthly carry readings over the last 365 days, at least 8; damps
  seasonal curves), mom12 (sum of the n.1 contract's same-contract daily returns from 365 to 30 days back, at least
  150), combo (cross-sectional z of carry plus z of mom12);
- k per leg: 2, 3, or a third of the valid roots (R503's);
- weights inside each leg (0.5 a leg): ivol (R503's), ew, conf (|cross-sectional z of the signal| / volatility:
  bigger when the signal is more extreme);
- signal frequency: every two weeks (the month's first settlement day and the first on or after the 15th), monthly
  (R503's), quarterly (Sep, Dec, Mar, Jun). Held contracts are rolled to the current far contract on every monthly date
  whatever the frequency;
- band: off (R503's), or on: a root already long stays long while it ranks in the top k + 1 (shorts likewise);
- cost gate: off (R503's), or on: a root is a candidate only if |carry| over the holding period covers 4 x its per-side
  cost (entry, exit and one roll).

Primary read: the walk-forward strategy, 2014-01..2026-10. Each 1 January it switches to the variant with the best net
daily Sharpe from 2010-09 to the day before, at 1x costs, and pays to move from the old holdings to the new.
GRID_PASS needs its net > 0 with Newey-West t >= 2 at 1x, net > 0 at 2x, and Hansen's SPA (consistent) p < 0.05 over
the 432 variants. PBO (CSCV, 16 blocks) and the deflated Sharpe of the best full-sample variant are reported.

Paper research only: nothing here can place an order.

    python scripts/run_cmeterm_grid.py run     # PREREG must verify; needs R505's fetched data
"""
import argparse
import bisect
import csv
import datetime as dt
import hashlib
import itertools
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts import run_cmeterm as r1          # noqa: E402  R503's frozen rule pieces
from scripts import run_cmeterm_v3 as m3       # noqa: E402  R505's frozen data loader

LANE = ROOT / "experiments" / "cmeterm_grid_v1"
SIGNALS = ("carry", "carry12", "mom12", "combo")
KS = (2, 3, "third")
WEIGHTS = ("ivol", "ew", "conf")
FREQS = ("2w", "1m", "3m")
BANDS = (False, True)
GATES = (False, True)
HOLD_DAYS = {"2w": 14, "1m": 30, "3m": 91}
GATE_SIDES = 4
C12_DAYS, C12_MIN = 365, 8
MOM_FROM, MOM_TO, MOM_MIN = 365, 30, 150
WF_FIRST_YEAR = 2014
PBO_BLOCKS = 16
SPA_BOOT, SPA_BLOCK = 1000, 20
PRIMARY_R503 = {"signal": "carry", "k": "third", "weight": "ivol", "freq": "1m", "band": False, "gate": False}


def configs():
    return [dict(signal=s, k=k, weight=w, freq=f, band=b, gate=g)
            for s, k, w, f, b, g in itertools.product(SIGNALS, KS, WEIGHTS, FREQS, BANDS, GATES)]


def name(c):
    return (f"{c['signal']}|k{c['k']}|{c['weight']}|{c['freq']}|{'band' if c['band'] else 'noband'}|"
            f"{'gate' if c['gate'] else 'nogate'}")


class World:
    """R503's data with fast trailing windows."""

    def __init__(self, cal, settle, ranks):
        self.cal, self.settle, self.ranks = cal, settle, ranks
        vols = r1.vol_series(cal, settle, ranks)
        self.vdays = {r: [d for d, _ in s] for r, s in vols.items()}
        self.vret = {r: [x for _, x in s] for r, s in vols.items()}
        self.vcum = {r: np.concatenate([[0.0], np.cumsum(self.vret[r])]) for r in vols}
        self.end = dt.date.fromisoformat(r1.LAST_DAY)
        self.first = dt.date.fromisoformat(r1.FIRST_MONTH + "-01")
        self.days = [d for d in cal if self.first - dt.timedelta(days=120) <= d <= self.end]
        self.tdays = [d for d in self.days if d >= self.first]
        self.roots = list(r1.ROOTS)
        self._cands = {}

    def sd(self, root, day):
        """R503's trailing volatility: the last 63 same-contract n.1 returns up to day, at least 40."""
        if root not in self.vdays:
            return None
        i = bisect.bisect_right(self.vdays[root], day)
        xs = self.vret[root][max(0, i - r1.VOL_N):i]
        return statistics.stdev(xs) if len(xs) >= r1.VOL_MIN else None

    def mom(self, root, day):
        if root not in self.vdays:
            return None
        i0 = bisect.bisect_right(self.vdays[root], day - dt.timedelta(days=MOM_FROM))
        i1 = bisect.bisect_right(self.vdays[root], day - dt.timedelta(days=MOM_TO))
        return float(self.vcum[root][i1] - self.vcum[root][i0]) if i1 - i0 >= MOM_MIN else None

    def candidates(self, day, entry):
        """R503's valid roots on day (rank, carry, 40 days to expiry, a positive entry price, a volatility)."""
        key = (day, entry)
        if key in self._cands:
            return self._cands[key]
        out = {}
        for root in self.roots:
            rk = r1.rank_for(self.ranks, day, root)
            if not rk or 0 not in rk or 1 not in rk:
                continue
            c = r1.carry_of(rk[0], rk[1], self.settle, day)
            if c is None:
                continue
            carry, far = c
            if (far[1] - day).days < r1.MIN_DAYS_TO_EXPIRY:
                continue
            px = self.settle.get((far[0], entry))
            if not px or px <= 0:
                continue
            sd = self.sd(root, day)
            if not sd:
                continue
            notional = px * far[3]
            out[root] = {"carry": carry, "iid": far[0], "sd": sd,
                         "rate": (r1.FEE_USD + r1.SLIP_TICKS * far[2] * far[3]) / notional}
        self._cands[key] = out
        return out

    def schedule(self, freq):
        """{entry day: (decision day, is a signal date, is a monthly date)}; entry is the next settlement day."""
        out, seen = {}, set()
        for i, d in enumerate(self.days):
            if d < self.first or i + 1 >= len(self.days) or self.days[i + 1] > self.end:
                continue
            ym = (d.year, d.month)
            monthly = ym not in seen
            if monthly:
                seen.add(ym)
            mid = (freq == "2w" and d.day >= 15 and (ym, "mid") not in seen)
            if mid:
                seen.add((ym, "mid"))
            if not (monthly or mid):
                continue
            sig = mid or (monthly and (freq != "3m" or (d.month - 9) % 3 == 0))
            out[self.days[i + 1]] = (d, sig, monthly)
        return out


def zscores(vals):
    xs = list(vals.values())
    if len(xs) < 2:
        return None
    mu, sd = statistics.mean(xs), statistics.pstdev(xs)
    if sd <= 0:
        return None
    return {k: (v - mu) / sd for k, v in vals.items()}


def select(c, w, day, cands, held, hist):
    """Target weights {root: w} at a signal date, or {} for no book."""
    sig = {}
    for root, x in cands.items():
        if c["gate"] and abs(x["carry"]) * HOLD_DAYS[c["freq"]] / 365.25 < GATE_SIDES * x["rate"]:
            continue
        if c["signal"] == "carry":
            sig[root] = x["carry"]
        elif c["signal"] == "carry12":
            xs = [v for d, v in hist[root] if d > day - dt.timedelta(days=C12_DAYS)]
            if len(xs) >= C12_MIN:
                sig[root] = sum(xs) / len(xs)
        elif c["signal"] in ("mom12", "combo"):
            m = w.mom(root, day)
            if m is not None:
                sig[root] = m if c["signal"] == "mom12" else (x["carry"], m)
    if c["signal"] == "combo":
        zc = zscores({r: v[0] for r, v in sig.items()})
        zm = zscores({r: v[1] for r, v in sig.items()})
        sig = {r: zc[r] + zm[r] for r in sig} if zc and zm else {}
    if len(sig) < r1.MIN_ROOTS:
        return {}
    k = len(sig) // 3 if c["k"] == "third" else c["k"]
    order = sorted(sig, key=lambda r: (-sig[r], r))
    pos = {r: i for i, r in enumerate(order)}
    if c["band"]:
        keep_l = sorted((r for r, v in held.items() if v > 0 and r in pos and pos[r] < k + 1), key=pos.get)[:k]
        longs = keep_l + [r for r in order if r not in keep_l][:k - len(keep_l)]
        keep_s = sorted((r for r, v in held.items() if v < 0 and r in pos and pos[r] >= len(order) - k - 1
                         and r not in longs), key=lambda r: -pos[r])[:k]
        shorts = keep_s + [r for r in reversed(order) if r not in keep_s and r not in longs][:k - len(keep_s)]
    else:
        longs, shorts = order[:k], [r for r in order[-k:] if r not in order[:k]]
    z = zscores(sig) or {r: 1.0 for r in sig}
    out = {}
    for leg, sign in ((longs, 1.0), (shorts, -1.0)):
        if c["weight"] == "ivol":
            base = {r: 1.0 / cands[r]["sd"] for r in leg}
        elif c["weight"] == "ew":
            base = {r: 1.0 for r in leg}
        else:
            base = {r: abs(z[r]) / cands[r]["sd"] for r in leg}
        tot = sum(base.values())
        if tot <= 0:
            base, tot = {r: 1.0 for r in leg}, float(len(leg))
        for r in leg:
            out[r] = sign * 0.5 * base[r] / tot
    return out


def run_config(w, c, keep_contrib=False):
    """Daily gross, 1x cost and held weights for one variant (R503's mechanics when c is R503's rule)."""
    sched = w.schedule(c["freq"])
    roots = w.roots
    T = len(w.tdays)
    gross, cost = np.zeros(T), np.zeros(T)
    W = np.zeros((T, len(roots)), dtype=np.float32)
    contrib = np.zeros((T, len(roots)), dtype=np.float32) if keep_contrib else None
    held, last_px, hist = {}, {}, defaultdict(list)
    for t, d in enumerate(w.tdays):
        for root, (wt, iid, rate) in held.items():
            p = w.settle.get((iid, d))
            if p is None or last_px[root] <= 0:
                continue
            r = p / last_px[root] - 1.0
            last_px[root] = p
            gross[t] += wt * r
            if keep_contrib:
                contrib[t, roots.index(root)] = wt * r
        is_last = t == T - 1
        if d in sched or is_last:
            new = {}
            if d in sched and not is_last:
                day, is_sig, monthly = sched[d]
                cands = w.candidates(day, d)
                if monthly:
                    for root, x in cands.items():
                        hist[root].append((day, x["carry"]))
                if is_sig:
                    target = select(c, w, day, cands, {r: v[0] for r, v in held.items()}, hist)
                else:
                    target = {r: v[0] for r, v in held.items()}
                new = {r: (wt, cands[r]["iid"], cands[r]["rate"]) for r, wt in target.items() if r in cands}
            for root in set(held) | set(new):
                wo, io, ro = held.get(root, (0.0, None, 0.0))
                wn, inn, rn = new.get(root, (0.0, None, 0.0))
                cost[t] += abs(wn - wo) * rn if io == inn else abs(wo) * ro + abs(wn) * rn
            held = new
            for root, (wt, iid, rate) in held.items():
                last_px[root] = w.settle[(iid, d)]
        for root, (wt, iid, rate) in held.items():
            W[t, roots.index(root)] = wt
    return {"gross": gross, "cost": cost, "W": W, "contrib": contrib}


def rates_matrix(w):
    """Per-side cost rate of each root's current far contract on each day (for walk-forward switches)."""
    R = np.zeros((len(w.tdays), len(w.roots)))
    last = {}
    for t, d in enumerate(w.tdays):
        cands = w.candidates(d, d)
        for j, root in enumerate(w.roots):
            if root in cands:
                last[root] = cands[root]["rate"]
            R[t, j] = last.get(root, 0.0)
    return R


# ---------- statistics ----------

def stats(net, days):
    from lab.stats import newey_west_t
    net = np.asarray(net, dtype=float)
    if len(net) < 30:
        return {"days": len(net)}
    yrs = (days[-1] - days[0]).days / 365.25
    ann = net.sum() / yrs
    vol = net.std(ddof=1) * math.sqrt(len(net) / yrs)
    eq = np.cumsum(net)
    mdd = float((eq - np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]).min())
    return {"start": days[0].isoformat(), "end": days[-1].isoformat(), "years": round(yrs, 3),
            "ann_net_pct": round(ann * 100, 3), "ann_vol_pct": round(vol * 100, 3),
            "sharpe": round(ann / vol, 3) if vol > 0 else None,
            "nw_t": round(float(newey_west_t(net, r1.NW_LAG)[2]), 3), "max_drawdown_pct": round(mdd * 100, 3)}


def daily_sharpe(x):
    x = np.asarray(x, dtype=float)
    s = x.std(ddof=1)
    return float(x.mean() / s) if s > 0 else -np.inf


def walk_forward(G, C, W, R, days, k=1.0, first_year=WF_FIRST_YEAR):
    """Each 1 January from first_year, switch to the variant with the best net daily Sharpe on all earlier days; pay
    k x the cost of moving from the previous holdings (none at the start) to the new ones. Returns the out-of-sample
    daily net, gross and cost, and the picks by year."""
    net_all = G - k * C
    years = sorted({d.year for d in days if d.year >= first_year})
    idx_year = np.array([d.year for d in days])
    out_net, out_gross, out_cost, out_days, picks = [], [], [], [], {}
    prev = None
    for y in years:
        train = idx_year < y
        test = np.where(idx_year == y)[0]
        if train.sum() < 250 or len(test) == 0:
            continue
        sh = [daily_sharpe(net_all[i, train]) for i in range(len(G))]
        pick = int(np.argmax(sh))
        picks[y] = pick
        t0 = test[0]
        w_old = W[prev, t0 - 1] if prev is not None else np.zeros(W.shape[2])
        switch = float(np.abs(W[pick, t0 - 1] - w_old) @ R[t0 - 1]) * k if pick != prev else 0.0
        g = G[pick, test].copy()
        c = k * C[pick, test].copy()
        c[0] += switch
        out_gross += list(g)
        out_cost += list(c)
        out_net += list(g - c)
        out_days += [days[t] for t in test]
        prev = pick
    return np.array(out_net), np.array(out_gross), np.array(out_cost), out_days, picks


def monthly(net, days):
    by = defaultdict(float)
    for x, d in zip(net, days):
        by[(d.year, d.month)] += x
    return [by[k] for k in sorted(by)]


def verdict_of(wf1, wf2, spa_p):
    """PBO is reported, not gating: when many variants share one edge, picking among near-twins is a coin flip and
    PBO sits near or above 0.5 even for a real edge (a planted world in the tests gives 0.73)."""
    if wf1.get("ann_net_pct", 0) > 0 and wf1.get("nw_t", 0) >= 2.0 and wf2.get("ann_net_pct", 0) > 0 and \
            spa_p < 0.05:
        return "GRID_PASS"
    if wf1.get("ann_net_pct", 0) > 0:
        return "GRID_WEAK"
    return "GRID_NULL"


def check_inputs(prereg=None):
    import re
    text = Path(prereg or LANE / "PREREG.md").read_text(encoding="utf-8")
    pairs = re.findall(r"\|\s*`([^`]+)`\s*\|\s*([0-9a-f]{64})\s*\|", text)
    if not pairs:
        raise SystemExit("no input hashes in the PREREG")
    for path, digest in pairs:
        got = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        if got != digest:
            raise SystemExit(f"{path} changed since the freeze: {got} != {digest}")
    return pairs


def analyze(cal, settle, ranks):
    from lab.inference import cscv_pbo, dsr, spa
    w = World(cal, settle, ranks)
    cfgs = configs()
    runs = [run_config(w, c) for c in cfgs]
    G = np.array([x["gross"] for x in runs])
    C = np.array([x["cost"] for x in runs])
    W = np.array([x["W"] for x in runs])
    R = rates_matrix(w)
    days = w.tdays
    rep = {"grid_size": len(cfgs), "days": len(days)}
    full = []
    for i, c in enumerate(cfgs):
        s = stats(G[i] - C[i], days)
        s2 = stats(G[i] - 2 * C[i], days)
        full.append(dict(name=name(c), **{k: s.get(k) for k in ("ann_net_pct", "sharpe", "nw_t", "max_drawdown_pct")},
                         ann_net_2x_pct=s2.get("ann_net_pct"),
                         ann_cost_pct=round(float(C[i].sum()) / s["years"] * 100, 3) if "years" in s else None))
    rep["r503_rule_in_grid"] = next(f for f, c in zip(full, cfgs) if c == PRIMARY_R503)
    # where the edge and the losses sit: each grid dimension's levels, across all variants
    marg = {}
    for dim, levels in (("signal", SIGNALS), ("k", KS), ("weight", WEIGHTS), ("freq", FREQS), ("band", BANDS),
                        ("gate", GATES)):
        marg[dim] = {}
        for lv in levels:
            xs = [f for f, c in zip(full, cfgs) if c[dim] == lv]
            nets = [f["ann_net_pct"] for f in xs if f["ann_net_pct"] is not None]
            shs = [f["sharpe"] for f in xs if f["sharpe"] is not None]
            marg[dim][str(lv)] = {"n": len(xs), "mean_net_pct": round(statistics.mean(nets), 3) if nets else None,
                                  "median_net_pct": round(statistics.median(nets), 3) if nets else None,
                                  "mean_sharpe": round(statistics.mean(shs), 3) if shs else None,
                                  "share_net_positive": round(sum(x > 0 for x in nets) / len(nets), 3) if nets else None}
    rep["marginals_1x"] = marg
    nets_all = [f["ann_net_pct"] for f in full]
    rep["grid_spread"] = {"share_net_positive_1x": round(sum(x > 0 for x in nets_all) / len(nets_all), 3),
                          "share_net_positive_2x": round(sum((f["ann_net_2x_pct"] or 0) > 0 for f in full) / len(full), 3),
                          "best_10_1x": sorted(full, key=lambda f: -(f["sharpe"] or -9))[:10],
                          "worst_5_1x": sorted(full, key=lambda f: (f["sharpe"] or 9))[:5]}
    # primary: walk-forward
    wf = {}
    for k in (1.0, 2.0, 3.0):
        net, g, cst, d, picks = walk_forward(G, C, W, R, days, k=k)
        wf[k] = (net, g, cst, d, picks)
        rep[f"walk_forward_{int(k)}x"] = stats(net, d)
    net1, g1, c1, d1, picks1 = wf[1.0]
    rep["walk_forward_picks"] = {str(y): name(cfgs[i]) for y, i in picks1.items()}
    rep["walk_forward_break_even_cost_multiple"] = round(float(g1.sum() / c1.sum()), 2) if c1.sum() > 0 else None
    rep["walk_forward_gross_pct"] = round(float(g1.sum()) / ((d1[-1] - d1[0]).days / 365.25) * 100, 3)
    by_year = defaultdict(list)
    for x, d in zip(net1, d1):
        by_year[d.year].append((x, d))
    rep["walk_forward_by_year_1x"] = {str(y): stats([x for x, _ in v], [d for _, d in v]) for y, v in by_year.items()}
    # attribution of the walk-forward strategy by root and leg (variants re-run with contributions)
    contrib = {}
    for y, i in picks1.items():
        if i not in contrib:
            contrib[i] = run_config(w, cfgs[i], keep_contrib=True)
    by_root, by_leg = defaultdict(float), defaultdict(float)
    idx = {d: t for t, d in enumerate(days)}
    for y, i in picks1.items():
        for t in [idx[d] for d in d1 if d.year == y]:
            for j, root in enumerate(w.roots):
                x = float(contrib[i]["contrib"][t, j])
                by_root[root] += x
                by_leg["long" if W[i, t - 1, j] > 0 else "short" if W[i, t - 1, j] < 0 else "flat"] += x
    yrs1 = (d1[-1] - d1[0]).days / 365.25
    rep["walk_forward_gross_by_root_pct"] = {k: round(v / yrs1 * 100, 3) for k, v in sorted(by_root.items())}
    rep["walk_forward_gross_by_leg_pct"] = {k: round(v / yrs1 * 100, 3) for k, v in sorted(by_leg.items())}
    # overfitting checks over the whole grid (1x)
    M = np.array([monthly(G[i] - C[i], days) for i in range(len(cfgs))]).T
    rep["pbo"] = round(cscv_pbo(M, n_blocks=PBO_BLOCKS)["pbo"], 4)
    D = (G - C).T
    s = spa(D, n_boot=SPA_BOOT, block=SPA_BLOCK, rng=np.random.default_rng(0))
    rep["spa"] = {"consistent_p": round(s["consistent"], 4), "upper_p": round(s["upper"], 4),
                  "best": name(cfgs[s["best"]])}
    sh = np.array([daily_sharpe(G[i] - C[i]) for i in range(len(cfgs))])
    best = int(np.argmax(sh))
    rep["best_full_sample"] = {"name": name(cfgs[best]), **stats(G[best] - C[best], days),
                               "dsr_432": round(dsr(G[best] - C[best], sh[np.isfinite(sh)], n_trials=len(cfgs)), 4)}
    rep["verdict"] = verdict_of(rep["walk_forward_1x"], rep["walk_forward_2x"], rep["spa"]["consistent_p"])
    return rep, full, (net1, d1)


def run():
    from lab.prereg import verify
    verify(LANE / "PREREG.md")
    check_inputs()
    cal, settle, ranks, missing = m3.load()
    rep, full, (net1, d1) = analyze(cal, settle, ranks)
    rep["mapped_contract_days_without_details"] = missing
    res = LANE / "results"
    res.mkdir(parents=True, exist_ok=True)
    with (res / "grid.csv").open("w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(full[0]), lineterminator="\n")
        wr.writeheader()
        wr.writerows(full)
    with (res / "walk_forward_daily.csv").open("w", newline="") as f:
        wr = csv.writer(f, lineterminator="\n")
        wr.writerow(["day", "net"])
        for x, d in zip(net1, d1):
            wr.writerow([d.isoformat(), f"{x:.8f}"])
    (res / "report.json").write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps({k: rep[k] for k in ("verdict", "walk_forward_1x", "walk_forward_2x", "pbo", "spa")}, default=str))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("run",))
    ap.parse_args(argv)
    return run()


if __name__ == "__main__":
    sys.exit(main() or 0)
