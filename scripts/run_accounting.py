"""accounting_v1 (R264): how much the legacy zero-fill of missing next returns moves flow books A, B and X2, as set
out in experiments/accounting_v1/PREREG.md. A measurement (trials 0). Books are rebuilt with R233's build() and checked
against R217 first.

usage: python scripts/run_accounting.py
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
from lab import prereg, research, slices, stats  # noqa: E402
from run_regime import BOOKS, HOLD_OUT, R217, VAL, build  # noqa: E402

LANE = ROOT / "experiments" / "accounting_v1"
SIGNED_MAX, BOUND_MAX = 0.10, 0.25
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def last_finite(x):
    """idx[t] = the last t' <= t with x[t'] finite, else -1 (per column)."""
    T, S = x.shape
    idx = np.where(np.isfinite(x), np.arange(T)[:, None], -1)
    return np.maximum.accumulate(idx, axis=0)


def next_finite(x):
    """idx[t] = the first t' >= t with x[t'] finite, else T (per column)."""
    T, S = x.shape
    idx = np.where(np.isfinite(x), np.arange(T)[:, None], T)
    return np.minimum.accumulate(idx[::-1], axis=0)[::-1]


def episodes(P, ret, close):
    """Held gap episodes: one row per maximal run i..j of non-finite ret in a column with P[i] != 0."""
    T = P.shape[0]
    bad = ~np.isfinite(ret)
    lf, nf = last_finite(close), next_finite(close)
    rows = []
    for s in np.flatnonzero((bad & (P != 0)).any(axis=0)):
        b = bad[:, s]
        edges = np.diff(np.concatenate([[0], b.astype(np.int8), [0]]))
        for i, j in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1) - 1):
            p = P[i, s]
            if p == 0:
                continue
            a = lf[i, s]
            e = nf[j + 1, s] if j + 1 < close.shape[0] else close.shape[0]
            if j == T - 1:
                status = "archive_end"
            elif e >= close.shape[0] or a < 0:
                status = "never_resumed"
            else:
                status = "resumed"
            move = float(close[e, s] / close[a, s] - 1) if status == "resumed" else np.nan
            rows.append({"col": int(s), "i": int(i), "j": int(j), "p": float(p), "move": move, "status": status})
    return pd.DataFrame(rows, columns=["col", "i", "j", "p", "move", "status"])


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    P, idx, elig, ret, cmat, D = build(u)
    T = D * 24
    dv, dh = research.row_of(u.p, VAL) // 24, research.row_of(u.p, HOLD_OUT) // 24
    close = np.asarray(u.p["close"], np.float64)
    r = np.asarray(ret[:T], np.float64)
    ref = np.load(R217)
    legacy = {b: {cm: slices.run(P[b][:T], ret, elig, cmat, 0, T, cmult=cm)["daily"] for cm in (1.0, 2.0, 3.0)}
              for b in BOOKS}
    for b, key in (("A", "A_C0"), ("B", "B_C0"), ("X2", "X2")):
        gap = float(np.max(np.abs(legacy[b][1.0][:dh] - ref[key][:dh])))
        log(f"parity {b} vs R217 {key}: max |diff| {gap:.2e}")
        assert gap < 1e-12, f"book {b} does not reproduce R217"

    W = {"discovery": slice(0, dv), "validation": slice(dv, dh), "spent": slice(dh, D)}
    summary, eps_all, verdict = [], [], {"books": {}}
    for b in BOOKS:
        Pb = np.asarray(P[b][:T], np.float64)
        ep = episodes(Pb, r, close)
        ep.insert(0, "book", b)
        ep["symbol"] = [u.p.symbols[c] for c in ep["col"]]
        ep["day"] = ep["j"] // 24
        eps_all.append(ep)
        res = ep[ep.status == "resumed"]
        bridged = np.zeros(D)
        bound = np.zeros(D)
        np.add.at(bridged, res["day"].values, (res["p"] * res["move"]).values)
        np.add.at(bound, res["day"].values, (res["p"].abs() * res["move"].abs()).values)
        absP = np.abs(Pb)
        miss = absP * ~np.isfinite(r)
        info = {}
        for w, s in W.items():
            rows = slice(s.start * 24, s.stop * 24)
            in_w = (ep["day"] >= s.start) & (ep["day"] < s.stop)
            leg1 = legacy[b][1.0][s].mean()
            row = {"book": b, "window": w,
                   "exposed_missing_share": float(miss[rows].sum() / max(absP[rows].sum(), 1e-300)),
                   "held_episodes": int(in_w.sum()),
                   "resumed": int((in_w & (ep.status == "resumed")).sum()),
                   "never_resumed": int((in_w & (ep.status == "never_resumed")).sum()),
                   "never_resumed_abs_p": float(ep.loc[in_w & (ep.status == "never_resumed"), "p"].abs().sum()),
                   "signed_bp_day": float(bridged[s].mean() * 1e4), "bound_bp_day": float(bound[s].mean() * 1e4),
                   "signed_share": float(abs(bridged[s].mean()) / abs(leg1)) if leg1 != 0 else np.inf,
                   "bound_share": float(bound[s].mean() / abs(leg1)) if leg1 != 0 else np.inf}
            for cm in (1.0, 2.0, 3.0):
                lg, co = legacy[b][cm][s], legacy[b][cm][s] + bridged[s]
                tag = f"{int(cm)}x"
                row[f"legacy_{tag}_bp_day"] = float(lg.mean() * 1e4)
                row[f"legacy_{tag}_t"] = float(stats.newey_west_t(lg, 10)[2])
                row[f"corrected_{tag}_bp_day"] = float(co.mean() * 1e4)
                row[f"corrected_{tag}_t"] = float(stats.newey_west_t(co, 10)[2])
            summary.append(row)
            info[w] = row
            log(b, w, json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items()
                                  if k not in ("book", "window")}))
        verdict["books"][b] = info
    decided = [verdict["books"][b][w] for b in BOOKS for w in ("discovery", "validation")]
    passed = all(x["signed_share"] < SIGNED_MAX and x["bound_share"] < BOUND_MAX for x in decided)
    verdict["verdict"] = "DATA_PASS" if passed else "NULL"
    pd.DataFrame(summary).to_csv(out / "summary.csv", index=False)
    pd.concat(eps_all).to_csv(out / "episodes.csv", index=False)
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1, default=float))
    log("verdict", verdict["verdict"])


if __name__ == "__main__":
    main()
