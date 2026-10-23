"""dispgate_v1 (R260): flow books A, B and X2 at half size on days when 30-day cross-sectional dispersion is in its
top tercile and the alt index's 90-day return is negative (docs/SIZING_EVIDENCE.md rule #7), against constant size, as
set out in experiments/dispgate_v1/PREREG.md. Books are rebuilt with R233's build() and checked against R217 first.

usage: python scripts/run_dispgate.py
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
from lab import events, prereg, research, slices, stats  # noqa: E402
from run_regime import BOOKS, HOLD_OUT, R217, VAL, build, describe  # noqa: E402

LANE = ROOT / "experiments" / "dispgate_v1"
MIN_COINS, LOOK_D, LOOK_A, MIN_HIST = 10, 30, 90, 180
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def multiplier(u, elig, D):
    """m[d] in {0.5, 1} from data through day d-1, plus its inputs."""
    T = D * 24
    ret = np.asarray(u.ret[:T], np.float64)
    r = np.nan_to_num(ret).reshape(D, 24, -1).sum(1)
    e0 = elig[::24] & np.isfinite(ret[::24])
    x = np.where(e0, r, np.nan)
    n = e0.sum(1)
    disp = np.where(n >= MIN_COINS, np.nanstd(x, axis=1), np.nan)
    alts = e0.copy()
    for s in ("BTCUSDT", "ETHUSDT"):
        alts[:, list(u.p.symbols).index(s)] = False
    a = np.nanmean(np.where(alts, r, np.nan), axis=1)
    d30 = pd.Series(disp).shift(1).rolling(LOOK_D).mean()
    q = d30.expanding(min_periods=MIN_HIST).quantile(2 / 3).shift(1)
    a90 = pd.Series(a).shift(1).rolling(LOOK_A).sum()
    top = (d30 >= q).values & q.notna().values & d30.notna().values
    down = (a90 < 0).values & a90.notna().values
    m = np.where(top & down, 0.5, 1.0)
    return m, {"d30": d30.values, "q": q.values, "a90": a90.values, "top": top, "down": down}


def episodes(on, days):
    """(start, end, n_days) of each run of consecutive gated days."""
    out, start = [], None
    for i, v in enumerate(list(on) + [False]):
        if v and start is None:
            start = i
        elif not v and start is not None:
            out.append((str(pd.to_datetime(days[start], unit="ms").date()),
                        str(pd.to_datetime(days[i - 1], unit="ms").date()), i - start))
            start = None
    return out


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    P, idx, elig, ret, cmat, D = build(u)
    dv, dh = research.row_of(u.p, VAL) // 24, research.row_of(u.p, HOLD_OUT) // 24
    days = np.asarray(u.p.t[0:D * 24:24])
    run = lambda Q, cm: slices.run(Q[:dh * 24], ret, elig, cmat, 0, dh * 24, cmult=cm)
    base = {b: {cm: run(P[b], cm) for cm in (1.0, 2.0, 3.0)} for b in BOOKS}
    ref = np.load(R217)
    for b, key in (("A", "A_C0"), ("B", "B_C0"), ("X2", "X2")):
        gap = float(np.max(np.abs(base[b][1.0]["daily"] - ref[key][:dh])))
        log(f"parity {b} vs R217 {key}: max |diff| {gap:.2e}")
        assert gap < 1e-12, f"book {b} does not reproduce R217"

    m, parts = multiplier(u, elig, D)
    W = {"discovery": slice(0, dv), "validation": slice(dv, dh)}
    on = m < 1
    gate = {w: {"share_half": float(on[s].mean()), "share_top_tercile": float(parts["top"][s].mean()),
                "share_alt90_down": float(parts["down"][s].mean()), "episodes": episodes(on[s], days[s])}
            for w, s in W.items()}
    for w, g in gate.items():
        log(w, f"half-size days {g['share_half']:.1%} (top tercile {g['share_top_tercile']:.1%}, alt 90d down"
            f" {g['share_alt90_down']:.1%}), episodes {len(g['episodes'])}:", g["episodes"][:12])

    rows, verdict = [], {"gate": gate, "variants": {}}
    mh = np.repeat(m, 24)[:, None]
    for b in BOOKS:
        name = f"G-{b}"
        res = {cm: run(P[b] * mh, cm) for cm in (1.0, 2.0, 3.0)}
        for w, s in W.items():
            for cm in (1.0, 2.0, 3.0):
                x, c = res[cm]["daily"][s], base[b][cm]["daily"][s]
                g = on[s]
                rows.append({"variant": name, "window": w, "cmult": cm, **describe(x, days[s], m[s] < 1),
                             "control_sharpe": float(c.mean() / c.std() * np.sqrt(365)),
                             "control_max_dd": events.summary(c).get("max_dd", np.nan),
                             "control_mean_bp_day": float(c.mean() * 1e4),
                             "control_mean_on_gated_days_bp": float(c[g].mean() * 1e4) if g.any() else np.nan,
                             "control_mean_other_days_bp": float(c[~g].mean() * 1e4),
                             "diff_bp_day": float((x - c).mean() * 1e4),
                             "diff_t_nw10": float(stats.newey_west_t(x - c, 10)[2])})
        pick = lambda w, cm: next(r for r in rows if r["variant"] == name and r["window"] == w and r["cmult"] == cm)
        d1, v1, v2 = pick("discovery", 1.0), pick("validation", 1.0), pick("validation", 2.0)
        ok = (d1["sharpe"] - d1["control_sharpe"] > 0 and v1["sharpe"] - v1["control_sharpe"] >= 0.15
              and v2["mean_bp_day"] > 0 and v1["max_dd"] <= v1["control_max_dd"])
        verdict["variants"][name] = {"passed": bool(ok),
                                     "discovery_sharpe_gain": d1["sharpe"] - d1["control_sharpe"],
                                     "validation_sharpe_gain": v1["sharpe"] - v1["control_sharpe"],
                                     "validation_mean_2x_bp": v2["mean_bp_day"], "validation_max_dd": v1["max_dd"],
                                     "validation_control_max_dd": v1["control_max_dd"]}
        log(name, f"discovery Sharpe {d1['sharpe']:.2f} vs {d1['control_sharpe']:.2f};"
            f" validation Sharpe {v1['sharpe']:.2f} vs {v1['control_sharpe']:.2f}, 2x {v2['mean_bp_day']:+.1f} bp/day,"
            f" DD {v1['max_dd']:.3f} vs {v1['control_max_dd']:.3f}; control on gated days"
            f" {v1['control_mean_on_gated_days_bp']:+.1f} vs other {v1['control_mean_other_days_bp']:+.1f} bp",
            "PASS" if ok else "NULL")
    df = pd.DataFrame(rows)
    df.drop(columns="by_year_bp_day").to_csv(out / "variants.csv", index=False)
    verdict["by_year_1x"] = {f"{r.variant}/{r.window}": r.by_year_bp_day for r in df[df.cmult == 1.0].itertuples()}
    verdict["passers"] = [k for k, v in verdict["variants"].items() if v["passed"]]
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1, default=float))
    pd.set_option("display.width", 250)
    log("\n" + df.drop(columns="by_year_bp_day").round(4).to_string(index=False))
    log(json.dumps({k: verdict[k] for k in ("variants", "passers")}, indent=1, default=float))


if __name__ == "__main__":
    main()
