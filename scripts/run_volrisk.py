"""volrisk_v1 (R241): SVXY in VIX contango, SVXY in contango with calm VIX, and R239's VIXREV-QQQ on 2013-2026, as
set out in experiments/volrisk_v1/PREREG.md.

usage: python scripts/run_volrisk.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg, stats  # noqa: E402
import run_fxindex as fx  # noqa: E402

LANE = ROOT / "experiments" / "volrisk_v1"
SV_WINDOWS = (("discovery", "2011-10-05", "2016-12-31"), ("validation", "2017-01-01", "2019-12-31"),
              ("holdout", "2020-01-01", "2026-10-19"))
QQ_WINDOWS = (("validation", "2013-01-01", "2019-12-31"), ("holdout", "2020-01-01", "2026-10-19"))
COST_SV = 3e-4
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def svxy_book(sv, vix, v3m, kind, cm):
    """Daily net and invested flag; signal from closes of d-1, position changed at the open of d."""
    v = vix.reindex(sv.index).ffill()
    v3 = v3m.reindex(sv.index).ffill()
    sig = v < v3
    if kind == "CALM":
        med = vix.rolling(252).median().reindex(sv.index).ffill()
        sig &= v < med
    s = sig.astype(float).values                               # s[d]: decided at the close of d
    s1 = np.r_[0.0, s[:-1]]                                    # held from the open of d
    s2 = np.r_[0.0, s1[:-1]]                                   # held over the night into d
    on = (sv.o / sv.c.shift(1) - 1).fillna(0.0).values
    net = s2 * on + s1 * sv.oc.values - COST_SV * cm * np.abs(s1 - s2)
    return net, s1 > 0


def worst(net, k=5):
    c = np.r_[0, np.cumsum(net)]
    return float((c[k:] - c[:-k]).min()) if len(net) > k else np.nan


def sv_row(net, r, inv, days, spy_r):
    row = fx.etf_row(net, r, inv, days)
    row["alpha_bh_bp_day"], row["alpha_bh_t"] = row.pop("test_mean_bp_day"), row.pop("test_t")
    row["alpha_trimmed_bp_day"] = row.pop("trimmed_bp_day")
    sr = spy_r.reindex(days).fillna(0.0).values
    row["beta_spy"] = float(np.linalg.lstsq(np.column_stack([np.ones(len(sr)), sr]), net, rcond=None)[0][1])
    row["test_mean_bp_day"] = float(net.mean() * 1e4)
    row["test_t"] = float(stats.newey_west_t(net, 10)[2])
    row["trimmed_bp_day"] = fx.trimmed(net)
    row["by_year_bp_day"] = {int(y): float(net[days.year == y].mean() * 1e4) for y in np.unique(days.year)}
    row["worst_day"], row["worst_5d"] = float(net.min()), worst(net)
    row["bh_mean_bp_day"], row["bh_max_dd"] = float(r.mean() * 1e4), fx.etf_row(r, r, inv, days)["max_dd"]
    return row


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    sv, qqq, spy = fx.etf("SVXY"), fx.etf("QQQ"), fx.etf("SPY")
    vix, v3m = fx.load("^VIX")["adjclose"], fx.load("^VIX3M")["adjclose"]
    rows, stage, trig = [], {}, {}

    def staged(name, windows, window_row):
        passed = True
        for w, a, b in windows:
            if not passed:
                break
            res = {cm: window_row(cm, a, b) for cm in (1.0, 2.0, 3.0)}
            for cm, row in res.items():
                rows.append({"strategy": name, "window": w, "cmult": cm, **row})
            passed = bool(fx.decide(w, res[1.0], res[2.0]))
            if w == "validation" and name == "VIXREV-QQQ":
                passed = passed and res[2.0]["test_mean_bp_day"] > 0
            stage[name] = {"reached": w, "passed": passed}
            r1 = res[1.0]
            log(name, w, f"net {r1['mean_bp_day']:+.2f} bp/day, test {r1['test_mean_bp_day']:+.2f} "
                f"t {r1['test_t']:+.2f} (2x {res[2.0]['test_mean_bp_day']:+.2f}), invested {r1['invested']:.2f}, "
                f"max dd {r1['max_dd']:.2f}", "PASS" if passed else "stop")

    for kind in ("CONTANGO", "CALM"):
        nets = {cm: svxy_book(sv, vix, v3m, kind, cm) for cm in (1.0, 2.0, 3.0)}

        def svw(cm, a, b, nets=nets):
            net, inv = nets[cm]
            m = (sv.index >= a) & (sv.index <= b)
            return sv_row(net[m], sv.r.values[m], inv[m], sv.index[m], spy.r)
        staged(f"SVXY-{kind}", SV_WINDOWS, svw)

    qn = {cm: fx.vixrev(qqq, vix, cm) for cm in (1.0, 2.0, 3.0)}

    def qw(cm, a, b):
        net, inv, tg = qn[cm]
        m = (qqq.index >= a) & (qqq.index <= b)
        trig[a[:4]] = int(tg[m].sum())
        return fx.etf_row(net[m], qqq.r.values[m], inv[m], qqq.index[m])
    staged("VIXREV-QQQ", QQ_WINDOWS, qw)

    df = pd.DataFrame(rows)
    df.drop(columns="by_year_bp_day").to_csv(out / "strategies.csv", index=False)
    verdict = {"stages": stage, "data_sha256": fx.SHAS, "vixrev_qqq_triggers": trig,
               "by_year_1x": {f"{x.strategy}/{x.window}": x.by_year_bp_day for x in df[df.cmult == 1.0].itertuples()},
               "holdout_passers": [k for k, v in stage.items() if v["reached"] == "holdout" and v["passed"]]}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    pd.set_option("display.width", 250)
    log("\n" + df.drop(columns="by_year_bp_day").round(3).to_string(index=False))
    log(json.dumps({k: verdict[k] for k in ("stages", "holdout_passers", "vixrev_qqq_triggers")}, indent=1))


if __name__ == "__main__":
    main()
