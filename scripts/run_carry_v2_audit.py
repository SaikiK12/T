"""R437 carry_v2_audit_v1: R275's seven headline carry books re-run on the M468 engine (lab/xfund_v2), as set out in
experiments/carry_v2_audit_v1/PREREG.md.

The question is accounting, not search: do the books that carry the lab's only passing family keep their edge once the
three defects of the 2026-11-04 audit are fixed (bar-length freshness H1, constant-notional marks H2, stale dead legs
F4)? Each book is run twice on the same archive and the same frozen rule:
  v1  lab/xfund (the frozen Python twin of qx spread). Its 1x daily net must equal R275's own results/daily.csv to
      1e-9 for every book, which also proves the data are the ones R275 read. A mismatch stops the run.
  v2  lab/xfund_v2 (fresh = any traded bar in the day, fixed-quantity legs, no price gain on an unobserved interval,
      blowout exits at a 20% move of the legs' price ratio, dead legs closed). No mark files (all venues alike).

usage: python scripts/run_carry_v2_audit.py --plumbing   (v1 parity and coverage only; no v2 statistic)
       python scripts/run_carry_v2_audit.py --run        (once, after the freeze)
       python scripts/run_carry_v2_audit.py --dry        (synthetic universe, writes nowhere in the repo)
"""
import argparse
import json
import math
import sys
import time
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402
from lab import xfund as v1  # noqa: E402
from lab import xfund_v2 as v2  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402

LANE = ROOT / "experiments" / "carry_v2_audit_v1"
RUN275 = ROOT / "experiments" / "xfund_v1"
# R275's best book per venue set (its FINDINGS table); the four forward books are marked.
BOOKS = [
    ("gate+hyperliquid", 14, 0.05, 20, "R278 A"),
    ("binance+hyperliquid", 14, 0.10, 20, ""),
    ("binance+mexc", 14, 0.10, 20, "R278 B"),
    ("binance+gate+hyperliquid+mexc", 14, 0.10, 20, ""),
    ("gate+mexc", 7, 0.10, 20, "R278 C"),
    ("binance+gate", 14, 0.10, 20, "R390 A"),
    ("hyperliquid+mexc", 3, 0.05, 20, ""),
]
T_MIN, HURDLE = 2.5, 4.13            # decision t at 1x; R275's T-bill hurdle in %/yr (reported, not a gate)


def label(s, l, th, k):
    return f"{s} L{l}d th{round(th * 100)}% K{k}"


def load(spec, mod, need):
    """Universe of R275's archive with `mod`'s Daily (v1 or v2); only venues in `need` are read."""
    t0 = int(pd.Timestamp(spec["start"], tz="UTC").value // 10**6)
    nd = int((pd.Timestamp(spec["end"], tz="UTC").value // 10**6 + v1.DAY - t0) // v1.DAY + 1)
    sym = pd.read_csv(ROOT / spec["symbols"], dtype=str).fillna("")
    venues = spec["venues"]

    def one(row):
        out = []
        for v in venues:
            s = row[v["name"]].strip()
            if not s or v["name"] not in need:
                out.append(None)
                continue
            out.append(mod.load_daily(ROOT / "data" / v["prices"] / f"{s}.parquet",
                                      ROOT / "data" / v["funding"] / f"{s}.parquet", v["vol"], v.get("bar_h", 1),
                                      t0, nd))
        return out

    with ThreadPoolExecutor(8) as ex:
        series = list(ex.map(one, [r for _, r in sym.iterrows()]))
    return v1.Universe(sym.key.tolist(), [v["name"] for v in venues], series, t0, nd, spec["corr_days"],
                       spec["corr_min"], spec["corr_obs"])


def stats(net, days, cost_mult_nets, recent_from_day):
    """Book statistics on the 1x daily net (fraction of book capital per day)."""
    x = np.asarray(net, float)
    n = len(x)
    _, mu, t = newey_west_t(x, 10)
    h = n // 2
    cum = np.cumsum(x)
    dd = float((cum - np.maximum.accumulate(np.concatenate([[0.0], cum]))[1:]).min()) if n else math.nan
    pos = np.sort(x)[::-1]
    tot = float(x.sum())
    rec = x[np.asarray(days) >= recent_from_day]
    return {
        "days": n, "ann_1x_pct": mu * 365 * 100, "ann_2x_pct": float(np.mean(cost_mult_nets[2])) * 365 * 100,
        "ann_3x_pct": float(np.mean(cost_mult_nets[3])) * 365 * 100, "mean_2x": float(np.mean(cost_mult_nets[2])),
        "nw_t_1x": t, "half1_bp": float(x[:h].mean()) * 1e4, "half2_bp": float(x[h:].mean()) * 1e4,
        "recent_bp": float(rec.mean()) * 1e4 if len(rec) else math.nan, "max_dd_pct": dd * 100,
        "top10_share": float(pos[:10].sum()) / tot if tot > 0 else math.nan,
    }


def run_book(u, mod, s, l, th, k, costs):
    vset = [u.names.index(v) for v in s.split("+")]
    w0 = mod.window_start(u, vset, l)
    rows, trades = mod.replay(u, mod.Book(vset, l, th, k), w0)
    nets = {m: mod.net(rows, k, c).to_numpy() for m, c in zip((1, 2, 3), costs)}
    return rows, trades, nets


def audit(u1, u2, spec, eng_daily=None, plumbing=False, log=print):
    """Per book: v1 parity against R275's output, then (unless plumbing) the v2 statistics and the frozen decision."""
    costs = spec["costs"]
    day0 = pd.Timestamp(spec["start"])
    recent = (pd.Timestamp(spec["recent_from"]) - day0).days
    out, daily, trade_rows = [], [], []
    for s, l, th, k, fwd in BOOKS:
        lab_ = label(s, l, th, k)
        t_start = time.time()
        rows1, trades1, nets1 = run_book(u1, v1, s, l, th, k, costs)
        rec = {"book": lab_, "forward": fwd, "v1_trades": len(trades1), "v1_days": len(rows1)}
        if eng_daily is not None:
            e = eng_daily[(eng_daily.strategy == lab_) & (eng_daily.cost_multiple == 1)].net.to_numpy()
            diff = float(np.abs(nets1[1] - e).max()) if len(e) == len(nets1[1]) else math.inf
            rec["v1_parity_max_diff"] = diff
            if not diff < 1e-9:
                raise SystemExit(f"{lab_}: v1 does not reproduce R275's daily net (max diff {diff}); data or code moved")
        rec.update({f"v1_{k_}": v_ for k_, v_ in stats(nets1[1], rows1.day.to_numpy(), nets1, recent).items()})
        if plumbing:
            # coverage only: how many coin-days each venue is fresh under v1 and v2 (no return is read)
            vset = [u1.names.index(v) for v in s.split("+")]
            for name, u in (("v1", u1), ("v2", u2)):
                rec[f"{name}_fresh_coin_days"] = int(sum(int(np.sum(u.series[c][a].fresh)) for c in range(len(u.keys))
                                                         for a in vset if u.series[c][a] is not None))
            out.append(rec)
            log(f"{lab_}: v1 parity {rec.get('v1_parity_max_diff', 'n/a')}; fresh coin-days v1 "
                f"{rec['v1_fresh_coin_days']} v2 {rec['v2_fresh_coin_days']} ({time.time() - t_start:.0f}s)")
            continue
        rows2, trades2, nets2 = run_book(u2, v2, s, l, th, k, costs)
        st = stats(nets2[1], rows2.day.to_numpy(), nets2, recent)
        rec.update({f"v2_{k_}": v_ for k_, v_ in st.items()})
        tr = pd.DataFrame(trades2)
        gross_total = float(rows2.gross.sum())
        for reason in ("spread", "dead", "blowout", "end"):
            sub = tr[tr.reason == reason] if len(tr) else tr
            rec[f"v2_exits_{reason}"] = int(len(sub))
            pnl = float((sub.price_pnl + sub.funding_pnl).sum()) if len(sub) else 0.0
            rec[f"v2_gross_share_{reason}"] = pnl / gross_total if gross_total else math.nan
        rec["v2_trades"] = int(len(tr))
        rec["v2_funding_share"] = float(rows2.funding.sum()) / gross_total if gross_total else math.nan
        rec["v2_avg_held"] = float(rows2.held.mean()) if len(rows2) else math.nan
        rec["v2_unobserved_pair_days"] = int(rows2.unobserved.sum())
        rec["survives"] = bool(st["nw_t_1x"] >= T_MIN and st["mean_2x"] > 0 and st["half1_bp"] > 0
                               and st["half2_bp"] > 0)
        rec["beats_tbill_1x"] = bool(st["ann_1x_pct"] > HURDLE)
        out.append(rec)
        for ver, rows, nets in (("v1", rows1, nets1), ("v2", rows2, nets2)):
            for d, a, b, c in zip(rows.day.to_numpy(), nets[1], nets[2], nets[3]):
                daily.append((lab_, ver, str((day0 + pd.Timedelta(days=int(d))).date()), a, b, c))
        for x in trades2:
            trade_rows.append({"book": lab_, **{kk: (str((day0 + pd.Timedelta(days=int(vv))).date())
                                                     if kk in ("entry_day", "exit_day") and vv is not None else vv)
                                                for kk, vv in x.items()}})
        log(f"{lab_}: v1 {rec['v1_ann_1x_pct']:+.2f}%/yr t {rec['v1_nw_t_1x']:.2f} -> v2 {st['ann_1x_pct']:+.2f}%/yr "
            f"t {st['nw_t_1x']:.2f}, 2x {st['ann_2x_pct']:+.2f}; {'SURVIVES' if rec['survives'] else 'FAILS'} "
            f"({time.time() - t_start:.0f}s)")
    return out, daily, trade_rows


def synthetic(spec, nd=400, n=12, seed=1):
    """A small fake universe for the dry run: two to four venues, random walks with a funding gap and one dead leg."""
    rng = np.random.default_rng(seed)
    names = [v["name"] for v in spec["venues"]]
    u = {}
    for mod in (v1, v2):
        rng = np.random.default_rng(seed)
        series = []
        for c in range(n):
            p = 10 * np.exp(np.cumsum(rng.normal(0, 0.03, nd)))
            row = []
            for j, _ in enumerate(names):
                close = p * np.exp(rng.normal(0, 0.002, nd))
                fresh = rng.random(nd) > 0.05
                if c == 0 and j == 1:
                    fresh[nd // 2:] = False
                f = np.full(nd, 0.0001 * (j + 1)) + rng.normal(0, 0.00005, nd)
                cnt = np.ones(nd, np.int64)
                if mod is v1:
                    row.append(v1.Daily.build(close, fresh, f, cnt))
                else:
                    row.append(v2.Daily.build(close, fresh, f, cnt))
            series.append(row)
        u[mod.__name__] = v1.Universe([f"C{c}" for c in range(n)], names, series, 0, nd, 30, 0.5, 20)
    return u["lab.xfund"], u["lab.xfund_v2"]


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--plumbing", action="store_true")
    g.add_argument("--run", action="store_true")
    g.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    spec = tomllib.loads((RUN275 / "spec.toml").read_text())
    if a.dry:
        u1, u2 = synthetic(spec)
        out, daily, trades = audit(u1, u2, {**spec, "start": "2021-01-01", "recent_from": "2021-08-01"})
        print(json.dumps({"books": len(out), "daily_rows": len(daily), "trades": len(trades),
                          "survives": [r["survives"] for r in out]}))
        return
    if a.run:
        from scripts.run_clockflow import check_inputs
        prereg.verify(LANE / "PREREG.md")
        check_inputs(LANE / "PREREG.md")
    need = {v for s, *_ in BOOKS for v in s.split("+")}
    t = time.time()
    u1 = load(spec, v1, need)
    u2 = load(spec, v2, need)
    print(f"loaded {len(u1.keys)} coins x {len(u1.names)} venues, {u1.nd} days ({time.time() - t:.0f}s)", flush=True)
    eng = pd.read_csv(RUN275 / "results" / "daily.csv")
    out, daily, trades = audit(u1, u2, spec, eng, plumbing=a.plumbing, log=lambda m: print(m, flush=True))
    if a.plumbing:
        print(json.dumps(out, indent=1, default=float))
        return
    res = LANE / "results"
    res.mkdir(exist_ok=True)
    pd.DataFrame(out).to_csv(res / "books.csv", index=False, float_format="%.10g")
    pd.DataFrame(daily, columns=["book", "engine", "date", "net_1x", "net_2x", "net_3x"]).to_csv(
        res / "daily.csv", index=False, float_format="%.10g")
    pd.DataFrame(trades).to_csv(res / "trades_v2.csv", index=False, float_format="%.10g")
    fwd = [r for r in out if r["forward"]]
    report = {"rid": "R437", "trials": len(BOOKS), "books": out,
              "survive_count": int(sum(r["survives"] for r in out)),
              "forward_books_surviving": {r["forward"]: r["survives"] for r in fwd}}
    (res / "report.json").write_text(json.dumps(report, indent=1, default=float))
    print(json.dumps({k: report[k] for k in ("survive_count", "forward_books_surviving")}))


if __name__ == "__main__":
    main()
