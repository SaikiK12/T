"""regime_v1 (R233): flow books A, B and X2 traded only in some trend x volatility regimes, and a regime-wise choice
among them (MacroHFT's sub-agents and hyper-agent), against constant size, as set out in
experiments/regime_v1/PREREG.md. Books are rebuilt as R217 and checked against its daily.npz first.

usage: python scripts/run_regime.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, events, prereg, research, slices, stats  # noqa: E402

LANE = ROOT / "experiments" / "regime_v1"
R217 = ROOT / "experiments" / "sizing_v1" / "results" / "daily.npz"
CELLS = ("flow:top_vs_crowd/xs8", "flow:taker[24]/xs8", "flow:taker[4]/xs8")
HOLD, K = 72, 9.316
VAL, HOLD_OUT, END = "2024-01-01", "2025-07-01", "2026-10-01"
BOOKS = ("A", "B", "X2")
REGIMES = ("UL", "UH", "DL", "DH")
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def build(u):
    """R217's books (run_sizing.main, unchanged) and its daily equal-weight index of eligible crypto coins."""
    assert research.row_of(u.p, "2021-01-01") == 0
    D = research.row_of(u.p, END) // 24
    T = D * 24
    dv = research.row_of(u.p, VAL) // 24
    tf = set(json.loads((ROOT / "experiments" / "venue_gap_v1" / "results" / "tradfi_symbols.json").read_text()))
    crypto = np.array([s not in tf for s in u.p.symbols])
    elig = np.asarray(u.elig[:T]) & crypto[None, :]
    ret, cmat = u.ret[:T], u.cmat[:T]
    rd = data.ROOT / "research"
    fb = np.load(rd / "bins_flow.npy", mmap_mode="r")
    fn = json.loads((rd / "meta_flow.json").read_text())["names"]
    flags = []
    for c in CELLS:
        x = (np.asarray(fb[fn.index(c)][:T]) == 0) & elig
        y = np.zeros_like(x)
        y[1:] = x[:-1]
        flags.append(y & elig)
    unit = 1.0 / (HOLD * K)
    kcount = sum(f.astype(np.float64) for f in flags)
    P = {"A": slices.positions(kcount, HOLD, 0, T, unit, -1),
         "B": slices.positions(flags[0], HOLD, 0, T, unit, -1),
         "X2": slices.positions(kcount ** 2, HOLD, 0, T, unit, -1)}
    ge = {k: np.abs(v[:dv * 24]).sum(1).mean() for k, v in P.items()}
    P["X2"] *= ge["A"] / ge["X2"]
    r = np.nan_to_num(np.asarray(ret, np.float64)).reshape(D, 24, -1).sum(1)
    e0 = elig[::24] & np.isfinite(np.asarray(ret[::24]))
    idx = np.nanmean(np.where(e0, r, np.nan), axis=1)
    return P, idx, elig, ret, cmat, D


def regimes(idx):
    """Regime of each day from the index through the day before; None during warm-up."""
    s = pd.Series(idx)
    trend = s.shift(1).rolling(30).sum().values
    v = s.shift(1).rolling(30).std()
    med = v.expanding(min_periods=180).median().shift(1).values
    v = v.values
    out = np.full(len(idx), None, object)
    ok = np.isfinite(trend) & np.isfinite(v) & np.isfinite(med)
    out[ok] = [("U" if t > 0 else "D") + ("H" if a >= m else "L") for t, a, m in zip(trend[ok], v[ok], med[ok])]
    return out


def describe(x, days, m=None, gx=None):
    s = events.summary(x)
    year = pd.to_datetime(days, unit="ms", utc=True).year
    out = {"days": len(x), "mean_bp_day": float(x.mean() * 1e4), "t_nw10": float(stats.newey_west_t(x, 10)[2]),
           "sharpe": float(x.mean() / x.std() * np.sqrt(365)) if x.std() > 0 else np.nan,
           "max_dd": s.get("max_dd", np.nan),
           "by_year_bp_day": {int(y): float(x[year == y].mean() * 1e4) for y in np.unique(year)}}
    if m is not None:
        out["share_traded"] = float((m > 0).mean())
    if gx is not None:
        out["gross_exposure"] = float(gx.mean())
    return out


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    P, idx, elig, ret, cmat, D = build(u)
    dv, dh = research.row_of(u.p, VAL) // 24, research.row_of(u.p, HOLD_OUT) // 24
    days = u.p.t[0:D * 24:24]
    run = lambda Q, cm, nd: slices.run(Q[:nd * 24], ret, elig, cmat, 0, nd * 24, cmult=cm)
    # constant-size controls over discovery + validation only; the parity check needs only those rows
    base = {b: {cm: run(P[b], cm, dh) for cm in (1.0, 2.0, 3.0)} for b in BOOKS}
    ref = np.load(R217)
    for b, key in (("A", "A_C0"), ("B", "B_C0"), ("X2", "X2")):
        gap = float(np.max(np.abs(base[b][1.0]["daily"] - ref[key][:dh])))
        log(f"parity {b} vs R217 {key}: max |diff| {gap:.2e}")
        assert gap < 1e-12, f"book {b} does not reproduce R217"
    reg = regimes(idx)
    W = {"discovery": slice(0, dv), "validation": slice(dv, dh), "holdout": slice(dh, D)}
    shares = {w: {r: float(np.mean(reg[s] == r)) for r in REGIMES + (None,)} for w, s in W.items()}
    log("regime shares", json.dumps({w: {str(k): round(v, 3) for k, v in x.items()} for w, x in shares.items()}))
    disc = np.zeros(D, bool)
    disc[:dv] = True
    table = {}
    for b in BOOKS:
        for r in REGIMES:
            sel = disc & (reg == r)
            row = {"days": int(sel.sum())}
            for cm in (1.0, 2.0, 3.0):
                x = base[b][cm]["daily"][sel[:dh]]
                row[f"mean_{cm:g}x_bp"] = float(x.mean() * 1e4) if len(x) else np.nan
                row[f"t_{cm:g}x"] = float(stats.newey_west_t(x, 10)[2]) if len(x) > 20 else np.nan
            table[(b, r)] = row
    log("discovery by regime:\n" + pd.DataFrame(table).T.round(2).to_string())
    gates = {b: [r for r in REGIMES if table[(b, r)]["mean_2x_bp"] > 0] for b in BOOKS}
    best = {r: max(BOOKS, key=lambda b: table[(b, r)]["mean_2x_bp"]) for r in REGIMES}
    mix = {r: (best[r] if table[(best[r], r)]["mean_2x_bp"] > 0 else None) for r in REGIMES}
    ctrl_mix = max(BOOKS, key=lambda b: base[b][2.0]["daily"][:dv].mean())
    log("gates", gates, "mix", mix, "mix control", ctrl_mix)

    variants = {}
    for b in BOOKS:
        if 0 < len(gates[b]) < len(REGIMES):
            m = np.array([1.0 if (r is None or r in gates[b]) else 0.0 for r in reg])
            variants[f"G-{b}"] = (lambda m=m, b=b: P[b] * np.repeat(m, 24)[:, None], m, b)
    held = np.array([ctrl_mix if r is None else (mix[r] or "") for r in reg], object)
    variants["MIX"] = (lambda: sum(P[b] * np.repeat((held == b).astype(float), 24)[:, None] for b in BOOKS),
                       (held != "").astype(float), ctrl_mix)
    rows, verdict = [], {"gates": gates, "mix": mix, "mix_control": ctrl_mix,
                         "regime_shares": {w: {str(k): v for k, v in x.items()} for w, x in shares.items()},
                         "discovery_by_regime": {f"{b}/{r}": v for (b, r), v in table.items()},
                         "no_gate_selected": [b for b in BOOKS if f"G-{b}" not in variants], "variants": {}}
    for name, (make, m, ctrl) in variants.items():
        Q = make()
        res = {cm: run(Q, cm, dh) for cm in (1.0, 2.0, 3.0)}
        for w in ("discovery", "validation"):
            s = W[w]
            for cm in (1.0, 2.0, 3.0):
                x, c = res[cm]["daily"][s], base[ctrl][cm]["daily"][s]
                gx = res[cm]["gross_exposure"][s.start * 24:s.stop * 24].reshape(-1, 24).mean(1)
                rows.append({"variant": name, "control": ctrl, "window": w, "cmult": cm,
                             **describe(x, days[s], m[s], gx),
                             "control_sharpe": float(c.mean() / c.std() * np.sqrt(365)),
                             "control_max_dd": events.summary(c).get("max_dd", np.nan),
                             "control_mean_bp_day": float(c.mean() * 1e4),
                             "diff_bp_day": float((x - c).mean() * 1e4),
                             "diff_t_nw10": float(stats.newey_west_t(x - c, 10)[2])})
        v1 = next(r for r in rows if r["variant"] == name and r["window"] == "validation" and r["cmult"] == 1.0)
        v2 = next(r for r in rows if r["variant"] == name and r["window"] == "validation" and r["cmult"] == 2.0)
        ok = (v1["sharpe"] - v1["control_sharpe"] >= 0.15 and v2["mean_bp_day"] > 0
              and v1["max_dd"] <= v1["control_max_dd"])
        verdict["variants"][name] = {"passed": bool(ok), "sharpe_gain": v1["sharpe"] - v1["control_sharpe"],
                                     "mean_2x_bp": v2["mean_bp_day"], "max_dd": v1["max_dd"],
                                     "control_max_dd": v1["control_max_dd"]}
        log(name, f"validation Sharpe {v1['sharpe']:.2f} vs {v1['control_sharpe']:.2f}, 2x {v2['mean_bp_day']:+.1f}"
            f" bp/day, DD {v1['max_dd']:.3f} vs {v1['control_max_dd']:.3f}", "PASS" if ok else "NULL")
        if ok:                                       # holdout only for passers; its outcome decides nothing
            for cm in (1.0, 2.0, 3.0):
                x = run(Q, cm, D)["daily"][W["holdout"]]
                c = run(P[ctrl], cm, D)["daily"][W["holdout"]]
                rows.append({"variant": name, "control": ctrl, "window": "holdout", "cmult": cm,
                             **describe(x, days[W["holdout"]], m[W["holdout"]]),
                             "control_mean_bp_day": float(c.mean() * 1e4),
                             "diff_bp_day": float((x - c).mean() * 1e4),
                             "diff_t_nw10": float(stats.newey_west_t(x - c, 10)[2])})
    df = pd.DataFrame(rows)
    if not df.empty:
        df.drop(columns="by_year_bp_day").to_csv(out / "variants.csv", index=False)
        verdict["by_year_1x"] = {f"{r.variant}/{r.window}": r.by_year_bp_day
                                 for r in df[df.cmult == 1.0].itertuples()}
    verdict["passed"] = [k for k, v in verdict["variants"].items() if v["passed"]]
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1, default=float))
    pd.set_option("display.width", 250)
    if not df.empty:
        log("\n" + df.drop(columns="by_year_bp_day").round(3).to_string(index=False))
    log("passed:", verdict["passed"] or "none")


if __name__ == "__main__":
    main()
