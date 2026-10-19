"""sizing_v1 (R217): confidence-scaled multipliers on the flow books against a constant size, as set out in
experiments/sizing_v1/PREREG.md."""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, events, prereg, research, slices, stats  # noqa: E402

LANE = ROOT / "experiments" / "sizing_v1"
CELLS = ("flow:top_vs_crowd/xs8", "flow:taker[24]/xs8", "flow:taker[4]/xs8")
HOLD, K = 72, 9.316
VAL, HOLD_OUT, END = "2024-01-01", "2025-07-01", "2026-10-01"
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def ts_multipliers(n, disp_med, idx90):
    """m[d] for each rule from the constant-size daily net n (through d - 1 only)."""
    D = len(n)
    s = pd.Series(n)
    past = s.shift(1)
    out = {"C0": np.ones(D)}
    sig_hat = past.ewm(halflife=30, min_periods=90).std().values
    sig_star = past.expanding(min_periods=90).std().values
    with np.errstate(divide="ignore", invalid="ignore"):
        r1 = np.clip(sig_star / sig_hat, 0, 2)
    out["R1"] = np.where(np.isfinite(r1), r1, 1.0)
    mu = past.rolling(180).mean().values
    sd = past.rolling(180).std().values
    with np.errstate(divide="ignore", invalid="ignore"):
        t = mu / (sd / np.sqrt(180))
        k = np.where(mu > 0, mu / sd ** 2 * np.maximum(0, 1 - 1 / t ** 2), 0.0)
    k = np.where(np.isfinite(k), k, np.nan)
    r2 = np.ones(D)
    pos = []
    for d in range(D):
        if len(pos) >= 30 and np.isfinite(k[d]):
            r2[d] = np.clip(k[d] / np.median(pos), 0, 2)
        if np.isfinite(k[d]) and k[d] > 0:
            pos.append(k[d])                          # k[d] uses nets through d - 1; available for d + 1 on
    out["R2"] = r2
    s60 = past.rolling(60).sum().values
    out["R3"] = np.where(np.isfinite(s60), np.where(s60 > 0, 1.5, 0.5), 1.0)
    q = pd.Series(disp_med).expanding(min_periods=365).quantile(2 / 3).values
    cut = (disp_med >= q) & (idx90 < 0) & np.isfinite(q)
    out["R4"] = np.where(cut, 0.5, 1.0)
    return out


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    assert research.row_of(u.p, "2021-01-01") == 0
    D = research.row_of(u.p, END) // 24
    T = D * 24
    dv, dh = research.row_of(u.p, VAL) // 24, research.row_of(u.p, HOLD_OUT) // 24
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
        flags.append(y & elig)                         # one-hour delay (R213 d = 1)
    unit = 1.0 / (HOLD * K)
    kcount = sum(f.astype(np.float64) for f in flags)
    P = {"A": slices.positions(kcount, HOLD, 0, T, unit, -1),
         "B": slices.positions(flags[0], HOLD, 0, T, unit, -1),
         "X1": slices.positions(kcount > 0, HOLD, 0, T, unit, -1),
         "X2": slices.positions(kcount ** 2, HOLD, 0, T, unit, -1)}
    ge = {k: np.abs(v[:dv * 24]).sum(1).mean() for k, v in P.items()}
    for x in ("X1", "X2"):
        P[x] *= ge["A"] / ge[x]
    log("gross exposure on discovery (before rescale):", {k: round(v, 3) for k, v in ge.items()})
    # market state for R4: daily coin returns among eligible crypto coins at the day's first hour
    r = np.nan_to_num(np.asarray(ret, np.float64)).reshape(D, 24, -1).sum(1)
    e0 = elig[::24] & np.isfinite(np.asarray(ret[::24]))
    rd_ = np.where(e0, r, np.nan)
    disp = np.nanstd(rd_, axis=1)
    idx = np.nanmean(rd_, axis=1)
    disp_med = pd.Series(disp).shift(1).rolling(30, min_periods=20).median().values
    idx90 = pd.Series(idx).shift(1).rolling(90).sum().values
    base = {b: slices.run(P[b], ret, elig, cmat, 0, T, cmult=1.0)["daily"] for b in ("A", "B")}
    rows, keep = [], {}
    windows = {"discovery": slice(0, dv), "validation": slice(dv, dh), "holdout": slice(dh, D)}
    runs = [(b, rule, m) for b in ("A", "B") for rule, m in ts_multipliers(base[b], disp_med, idx90).items()]
    runs += [(x, "X", np.ones(D)) for x in ("X1", "X2")]
    for book, rule, m in runs:
        name = f"{book}_{rule}" if rule != "X" else book
        mh = np.repeat(m, 24)[:, None]
        for cm in (1.0, 2.0, 3.0):
            o = slices.run(P[book] * mh, ret, elig, cmat, 0, T, cmult=cm)
            n = o["daily"]
            gx = o["gross_exposure"].reshape(D, 24).mean(1)
            for w, sl in windows.items():
                x = n[sl]
                s = events.summary(x)
                rows.append({"run": name, "book": book[0], "rule": rule if rule != "X" else book, "cmult": cm,
                             "window": w, "days": len(x), "mean_bp_day": float(x.mean() * 1e4),
                             "t_nw10": float(stats.newey_west_t(x, 10)[2]),
                             "sharpe": float(x.mean() / x.std() * np.sqrt(365)) if x.std() > 0 else np.nan,
                             "max_dd": s.get("max_dd", np.nan), "mean_abs_m": float(np.abs(m[sl]).mean()),
                             "gross_exposure": float(gx[sl].mean()),
                             "mean_per_m_bp": float(x.mean() / max(np.abs(m[sl]).mean(), 1e-9) * 1e4)})
            if cm == 1.0:
                keep[name] = n
                keep[name + "_m"] = m
        log(name, {w: round(r["sharpe"], 2) for w, r in zip(windows, rows[-9:-6])})
    df = pd.DataFrame(rows)
    df.to_csv(out / "results.csv", index=False)
    np.savez_compressed(out / "daily.npz", **keep)
    one = df[df.cmult == 1.0].set_index(["run", "window"])
    verdict = {}
    for name in sorted(set(df.run)):
        if name.endswith("C0") or name in ("A", "B"):
            continue
        ctrl = f"{name[0]}_C0" if not name.startswith("X") else "A_C0"
        gain = {w: float(one.loc[(name, w), "sharpe"] - one.loc[(ctrl, w), "sharpe"]) for w in windows}
        passed = gain["discovery"] >= 0.3 and gain["validation"] >= 0.3 and one.loc[(name, "validation"),
                                                                                   "mean_bp_day"] > 0
        verdict[name] = {"sharpe_gain": gain, "passed": bool(passed)}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    pd.set_option("display.width", 250)
    log("\n" + df[df.cmult == 1.0].round(3).to_string(index=False))
    log(json.dumps(verdict, indent=1))


if __name__ == "__main__":
    main()
