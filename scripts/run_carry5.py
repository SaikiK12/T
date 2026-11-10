"""R439 carry5_v1: R275's all-four carry rule (L14d th10% K20) on one book over five venues (Binance, Gate,
Hyperliquid, MEXC, KuCoin), on the M468 engine (lab/xfund_v2), as set out in experiments/carry5_v1/PREREG.md.

Reuses R437's frozen runner functions (scripts/run_carry_v2_audit.py: load, stats, run_book, label) unchanged.
  parity  v1 (lab/xfund) of the four-venue book on this universe must equal R275's results/daily.csv 1x net to 1e-9;
          the universe is R275's manifest with a KuCoin column, so this proves the data and code are R275's.
  book    the five-venue book on v2; the four-venue book on v2 is re-run on the same universe as the paired reference.

usage: python scripts/run_carry5.py --plumbing | --run | --dry
"""
import argparse
import json
import math
import sys
import time
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402
from lab import xfund as v1  # noqa: E402
from lab import xfund_v2 as v2  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402
from scripts import run_carry_v2_audit as base  # noqa: E402

LANE = ROOT / "experiments" / "carry5_v1"
RUN275 = ROOT / "experiments" / "xfund_v1"
BOOK5 = ("binance+gate+hyperliquid+mexc+kucoin", 14, 0.10, 20)
REF4 = ("binance+gate+hyperliquid+mexc", 14, 0.10, 20)
T_MIN = 2.5


class DriftBook(v2.Book):
    """v2 book that also sums funding on constant entry notional (R438's diagnostic, reported only)."""
    f_const = 0.0

    def interval(self, u, d):
        for p in self.open:
            a, h = u.series[p.coin][p.lo], u.series[p.coin][p.hi]
            x = h.fund_on(d + 1) - a.fund_on(d + 1)
            if math.isfinite(x) and math.isfinite(h.val[d] / p.ph_e - a.val[d] / p.pl_e):
                self.f_const += x
        return super().interval(u, d)


def run(u1, u2, spec, eng_daily=None, plumbing=False, log=print):
    costs = spec["costs"]
    day0 = pd.Timestamp(spec["start"])
    recent = (pd.Timestamp(spec["recent_from"]) - day0).days
    rows1, _, nets1 = base.run_book(u1, v1, *REF4, costs)
    out = {"ref4_v1_days": len(rows1)}
    if eng_daily is not None:
        e = eng_daily[(eng_daily.strategy == base.label(*REF4)) & (eng_daily.cost_multiple == 1)].net.to_numpy()
        diff = float(np.abs(nets1[1] - e).max()) if len(e) == len(nets1[1]) else math.inf
        out["ref4_v1_parity_max_diff"] = diff
        if not diff < 1e-9:
            raise SystemExit(f"v1 four-venue book does not reproduce R275's daily net (max diff {diff})")
    if plumbing:
        names = u2.names
        out["coin_days_fresh_v2"] = {n: int(sum(int(np.sum(u2.series[c][j].fresh)) for c in range(len(u2.keys))
                                               if u2.series[c][j] is not None)) for j, n in enumerate(names)}
        log(json.dumps(out))
        return out, [], []
    recs, daily, trades = [], [], []
    for tag, bk in (("book5", BOOK5), ("ref4", REF4)):
        s, l, th, k = bk
        vset = [u2.names.index(v) for v in s.split("+")]
        b = DriftBook(vset, l, th, k)
        rows, tr = v2.replay(u2, b, v2.window_start(u2, vset, l))
        nets = {m: v2.net(rows, k, c).to_numpy() for m, c in zip((1, 2, 3), costs)}
        st = base.stats(nets[1], rows.day.to_numpy(), nets, recent)
        n = len(rows)
        ann = lambda x: float(x) / (2 * k) / n * 365 * 100  # noqa: E731
        t = pd.DataFrame(tr)
        rec = {"tag": tag, "book": base.label(*bk), **st,
               "funding_pct": ann(rows.funding.sum()), "funding_const_notional_pct": ann(b.f_const),
               "price_pct": ann((rows.gross - rows.funding).sum()), "cost_pct": ann(costs[0] * rows.legs.sum()),
               "trades": len(t), "avg_held": float(rows.held.mean()),
               "exits": t.reason.value_counts().to_dict() if len(t) else {},
               "pairs_by_venues": (t["long"] + "/" + t["short"]).value_counts().to_dict() if len(t) else {}}
        if tag == "book5":
            rec["survives"] = bool(st["nw_t_1x"] >= T_MIN and st["mean_2x"] > 0 and st["half1_bp"] > 0
                                   and st["half2_bp"] > 0)
            rec["kucoin_leg_share"] = float(((t["long"] == "kucoin") | (t["short"] == "kucoin")).mean()) if len(t) else 0
        recs.append((rec, rows, nets))
        for d, a, b2, c in zip(rows.day.to_numpy(), nets[1], nets[2], nets[3]):
            daily.append((tag, str((day0 + pd.Timedelta(days=int(d))).date()), a, b2, c))
        for x in tr:
            trades.append({"tag": tag, **x})
        log(f"{rec['book']}: {st['ann_1x_pct']:+.2f}/{st['ann_2x_pct']:+.2f}/{st['ann_3x_pct']:+.2f} %/yr, "
            f"NW t {st['nw_t_1x']:.2f}")
    (r5, rows5, n5), (r4, rows4, n4) = recs
    a = pd.Series(n5[1], index=rows5.day.to_numpy())
    b4 = pd.Series(n4[1], index=rows4.day.to_numpy())
    common = a.index.intersection(b4.index)
    dlt = (a[common] - b4[common]).to_numpy()
    _, mu, tt = newey_west_t(dlt, 10)
    r5["paired_vs_ref4"] = {"days": int(len(common)), "mean_bp_day": mu * 1e4, "ann_pct": mu * 365 * 100, "nw_t": tt}
    return [r5, r4], daily, trades


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--plumbing", action="store_true")
    g.add_argument("--run", action="store_true")
    g.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    spec = tomllib.loads((LANE / "spec.toml").read_text())
    if a.dry:
        u1, u2 = base.synthetic(spec, nd=300, n=10)
        out, daily, trades = run(u1, u2, {**spec, "start": "2021-01-01", "recent_from": "2021-06-01"})
        print(json.dumps({"books": len(out), "daily": len(daily), "trades": len(trades),
                          "survives": out[0].get("survives")}, default=float))
        return
    if a.run:
        from scripts.run_clockflow import check_inputs
        prereg.verify(LANE / "PREREG.md")
        check_inputs(LANE / "PREREG.md")
    need = {v["name"] for v in spec["venues"]}
    t0 = time.time()
    u1 = base.load(spec, v1, need)
    u2 = base.load(spec, v2, need)
    print(f"loaded {len(u1.keys)} coins x {len(u1.names)} venues, {u1.nd} days ({time.time() - t0:.0f}s)", flush=True)
    eng = pd.read_csv(RUN275 / "results" / "daily.csv")
    out, daily, trades = run(u1, u2, spec, eng, plumbing=a.plumbing, log=lambda m: print(m, flush=True))
    if a.plumbing:
        return
    res = LANE / "results"
    res.mkdir(exist_ok=True)
    (res / "report.json").write_text(json.dumps({"rid": "R439", "trials": 1, "books": out}, indent=1, default=float))
    pd.DataFrame(daily, columns=["tag", "date", "net_1x", "net_2x", "net_3x"]).to_csv(res / "daily.csv", index=False,
                                                                                      float_format="%.10g")
    pd.DataFrame(trades).to_csv(res / "trades_v2.csv", index=False, float_format="%.10g")
    print(json.dumps({"survives": out[0]["survives"], "paired_vs_ref4": out[0]["paired_vs_ref4"]}, default=float))


if __name__ == "__main__":
    main()
