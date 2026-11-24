"""R529 roll_frontrun_v1: front-running the commodity index roll in CME energy calendar spreads, as set out in
experiments/roll_frontrun_v1/PREREG.md. Paper only.

The payer: commodity index funds (S&P GSCI, BCOM) must move their long positions from the nearby contract to the
next on announced dates, business days 5-9 (GSCI) and 6-10 (BCOM) of each month. CFTC economists (Brunetti and
Reiffen) find that the deferred-minus-nearby spread rises as index holdings move into the deferred contract.

Data: R505's held CME settlements and contract map (data/databento/cmeterm_v3, loaded read-only by
`scripts/run_cmeterm_v3.load()`): the daily settlement of the three contracts with the most open interest per root.

Per root (the 13 R505 holds: CL HO RB NG GC SI HG PL ZC ZS ZW LE HE) and month m:
- A = the contract among the root's top three by open interest at BD0 that expires in calendar month m+1 (the index
  rolls about 30-40 days before expiry); B = the next-expiring contract among them, at most 4 months after A.
  No index table is used: a liquid next contract is the index's next month for these roots.
- BD0 = the root's last settlement day before month m; BDk = its k-th settlement day of month m.
- Trade: long B, short A, equal notional, from the BD0 settlement to the BD9 settlement:
  ret = (P_B(BD9)/P_B(BD0) - 1) - (P_A(BD9)/P_A(BD0) - 1), minus the round-trip cost.
- An event counts only if A and B both have settlements on BD0 and BD9.
- Months: 2010-08..2026-10. The decided series is the mean over the roots with an event that month.

usage: python scripts/run_roll_frontrun.py run
"""
import datetime as dt
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab.stats import newey_west_t  # noqa: E402

LANE = ROOT / "experiments" / "roll_frontrun_v1"
ENERGY = ("CL", "HO", "RB", "NG")
ALL = ("CL", "HO", "RB", "NG", "GC", "SI", "HG", "PL", "ZC", "ZS", "ZW", "LE", "HE")
MAX_GAP = 4                             # B expires at most 4 months after A
COSTS = (0.0002, 0.0004, 0.0006)        # round trip of the spread, both legs, on one leg's notional
EXIT_BD, PRE_BD = 9, 4
T_MIN, NW_LAG = 2.8, 3
FIRST, LAST = (2010, 8), (2026, 10)


def contracts(ranks, roots=ALL):
    """{root: {iid: expiry}} from the rank map."""
    out = defaultdict(dict)
    for rr in ranks.values():
        for root in roots:
            for iid, exp, *_ in (rr.get(root) or {}).values():
                out[root][iid] = exp
    return out


def rank_on(ranks, day, root):
    """The root's top-3 contracts on `day`, or on the latest earlier day with a rank record."""
    for back in range(0, 10):
        rr = ranks.get(day - dt.timedelta(days=back))
        if rr and root in rr:
            return rr[root]
    return None


def trading_days(settle, cons):
    """{root: sorted settlement days} from the settlements of the root's contracts."""
    ids = {iid: root for root, m in cons.items() for iid in m}
    out = defaultdict(set)
    for (iid, d) in settle:
        if iid in ids:
            out[ids[iid]].add(d)
    return {r: sorted(v) for r, v in out.items()}


def add_months(y, m, k):
    t = y * 12 + (m - 1) + k
    return t // 12, t % 12 + 1


def months(first=FIRST, last=LAST):
    y, m = first
    while (y, m) <= last:
        yield y, m
        y, m = add_months(y, m, 1)


def events(settle, ranks, roots=ALL, first=FIRST, last=LAST):
    """[(root, (y, m), price dict)] with the A and B settlements at BD0, BD4 and BD9, where both exist. A = the
    contract among the root's top three by open interest at BD0 that expires in month m+1; B = the next-expiring
    contract among them, at most MAX_GAP months after A."""
    cons = contracts(ranks, roots)
    days = trading_days(settle, cons)
    out = []
    for root in roots:
        dd = days.get(root, [])
        for y, m in months(first, last):
            start = dt.date(y, m, 1)
            before = [d for d in dd if d < start]
            inside = [d for d in dd if d >= start and (d.year, d.month) == (y, m)]
            if not before or len(inside) < EXIT_BD:
                continue
            bd = {0: before[-1], PRE_BD: inside[PRE_BD - 1], EXIT_BD: inside[EXIT_BD - 1]}
            ya, ma = add_months(y, m, 1)
            held = {iid: e for iid, e, *_ in (rank_on(ranks, bd[0], root) or {}).values()}
            a = [i for i, e in held.items() if (e.year, e.month) == (ya, ma)]
            if len(a) != 1:
                continue
            ea = held[a[0]]
            later = sorted((e, i) for i, e in held.items() if e > ea and add_months(ea.year, ea.month, MAX_GAP) >=
                           (e.year, e.month))
            if not later:
                continue
            b = [later[0][1]]
            px = {(leg, k): settle.get((iid, bd[k])) for leg, iid in (("A", a[0]), ("B", b[0])) for k in bd}
            if any(v is None or not v > 0 for v in px.values()):
                continue
            out.append((root, (y, m), px))
    return out


def ret(px, k0, k1):
    return (px[("B", k1)] / px[("B", k0)] - 1.0) - (px[("A", k1)] / px[("A", k0)] - 1.0)


def monthly(evs, k0, k1, cost):
    """{(y, m): mean over roots of the net return} and the per-event list."""
    by = defaultdict(list)
    for root, ym, px in evs:
        by[ym].append(ret(px, k0, k1) - cost)
    return {ym: float(np.mean(v)) for ym, v in sorted(by.items())}


def stats(x):
    x = np.asarray(list(x), float)
    if len(x) < 12:
        return {"n": len(x)}
    return {"n": len(x), "mean_bp": float(x.mean() * 1e4), "ann_pct": float(x.mean() * 12 * 100),
            "nw_t": float(newey_west_t(x, NW_LAG)[2]), "hit": float((x > 0).mean()),
            "sharpe_ann": float(x.mean() / x.std() * math.sqrt(12)) if x.std() > 0 else None}


def decide(s1, s2, halves):
    checks = {"t_ge_2.8": (s1.get("nw_t") or 0) >= T_MIN, "mean_2x_pos": (s2.get("mean_bp") or 0) > 0,
              "both_halves_pos": min(halves) > 0}
    return ("PASS" if all(checks.values()) else "FAIL"), checks


def run(lane=LANE):
    from lab.prereg import verify
    from scripts import run_cmeterm_v3 as v3
    from scripts import run_xfund_bfx as base
    verify(lane / "PREREG.md")
    base.check_inputs(lane / "PREREG.md")
    res = lane / "results"
    if (res / "report.json").exists():
        raise SystemExit("results exist: this lane is read once")
    _, settle, ranks, _ = v3.load()
    evs = events(settle, ranks)
    rep = {"events": len(evs), "events_by_root": {r: sum(1 for e in evs if e[0] == r) for r in ALL}}
    series = {}
    for name, (k0, k1) in {"full_bd0_bd9": (0, EXIT_BD), "pre_bd0_bd4": (0, PRE_BD),
                           "roll_bd4_bd9": (PRE_BD, EXIT_BD)}.items():
        rep[name] = {}
        for c in COSTS:
            s = monthly(evs, k0, k1, c)
            rep[name][f"{round(c * 1e4)}bp"] = stats(s.values())
            if c == COSTS[0]:
                series[name] = s
    full = list(series["full_bd0_bd9"].values())
    h = len(full) // 2
    halves = [float(np.mean(full[:h]) * 1e4), float(np.mean(full[h:]) * 1e4)]
    rep["halves_mean_bp"] = halves
    rep["by_year_mean_bp"] = {y: float(np.mean([v for (yy, _), v in series["full_bd0_bd9"].items() if yy == y]) * 1e4)
                              for y in sorted({y for y, _ in series["full_bd0_bd9"]})}
    rep["by_root_mean_bp"] = {r: float(np.mean([ret(px, 0, EXIT_BD) - COSTS[0] for rr, _, px in evs if rr == r]) * 1e4)
                              for r in ALL if any(e[0] == r for e in evs)}
    en = [e for e in evs if e[0] in ENERGY]
    rep["energy_only_full_2bp"] = stats(monthly(en, 0, EXIT_BD, COSTS[0]).values())
    rep["verdict"], rep["checks"] = decide(rep["full_bd0_bd9"]["2bp"], rep["full_bd0_bd9"]["4bp"], halves)
    res.mkdir(parents=True, exist_ok=True)
    (res / "report.json").write_text(json.dumps(rep, indent=1, default=str))
    with (res / "monthly_full_2bp.csv").open("w") as f:
        f.write("year,month,net\n" + "".join(f"{y},{m},{v:.8f}\n" for (y, m), v in series["full_bd0_bd9"].items()))
    print(json.dumps(rep, indent=1, default=str))
    return rep


if __name__ == "__main__":
    if sys.argv[1:] != ["run"]:
        raise SystemExit("usage: python scripts/run_roll_frontrun.py run")
    run()
