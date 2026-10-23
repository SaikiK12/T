"""vt_fwd (R225): R217's volatility target (rule R1) applied forward to the MEXC flow books A and B (R215) and X2
(R218), warmed up on R217's archived daily nets, as set out in experiments/vt_fwd/PREREG.md. Reads the other lanes'
tickets (never writes them); appends to its own journal. Paper only.

usage: python scripts/forward_vt.py   (after scripts/forward_mexc.py and scripts/forward_mexc_sq.py)
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402

LANE = ROOT / "experiments" / "vt_fwd"
J = LANE / "journal"
ARCHIVE = ROOT / "experiments" / "sizing_v1" / "results" / "daily.npz"
SOURCES = {"A": ("mexc_fwd", "A_C0"), "B": ("mexc_fwd", "B_C0"), "X2": ("mexc_fwd_sq", "X2")}
RESIZE = 0.0008
DECIDE_DAYS = 365
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def r1(n):
    """R217's R1 multiplier for every day of n and for the day after its last: m[d] uses n through d - 1."""
    past = pd.Series(np.append(n, np.nan)).shift(1)
    sig_hat = past.ewm(halflife=30, min_periods=90).std().values
    sig_star = past.expanding(min_periods=90).std().values
    with np.errstate(divide="ignore", invalid="ignore"):
        m = np.clip(sig_star / sig_hat, 0, 2)
    return np.where(np.isfinite(m), m, 1.0)


def stats(x):
    eq = np.cumsum(x)
    return {"total": float(x.sum()), "sharpe": float(x.mean() / x.std(ddof=1) * np.sqrt(365)) if len(x) > 1 and
            x.std() > 0 else None, "max_dd": float(np.max(np.maximum.accumulate(np.append(0.0, eq)) - np.append(0.0, eq)))}


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    J.mkdir(parents=True, exist_ok=True)
    arch = np.load(ARCHIVE)
    p = J / "days.csv"
    have = pd.read_csv(p) if p.exists() and p.stat().st_size else pd.DataFrame()
    done = set(zip(have.day, have.book)) if not have.empty else set()
    rows, status = [], {}
    for book, (lane, key) in SOURCES.items():
        tk = pd.read_csv(ROOT / "experiments" / lane / "journal" / "tickets.csv")
        tk = tk[tk.book == book].sort_values("day").reset_index(drop=True)
        m_all = r1(np.concatenate([arch[key], tk.net.values]))
        m, m_next = m_all[len(arch[key]):-1], float(m_all[-1])
        prev = np.concatenate([[m_all[len(arch[key]) - 1]], m[:-1]])
        resize = np.abs(m - prev) * tk.gross_exposure.values * RESIZE
        tk = tk.assign(m=m, resize_cost=resize, net_vt=m * tk.net - resize, net_vt_2x=m * tk.net_2x - 2 * resize,
                       net_vt_3x=m * tk.net_3x - 3 * resize)
        rows += [r for r in tk[["day", "book", "kind", "m", "net", "net_vt", "net_vt_2x", "net_vt_3x",
                                "resize_cost"]].to_dict("records") if (r["day"], r["book"]) not in done]
        s = {"m_next": m_next, "m_last": float(m[-1]) if len(m) else None}
        for kind in ("replay", "ontime"):
            x = tk[tk.kind == kind]
            if x.empty:
                continue
            s[kind] = {"days": int(len(x)), "mean_m": float(x.m.mean()),
                       "unscaled": {**stats(x.net.values), "total_2x": float(x.net_2x.sum()),
                                    "total_3x": float(x.net_3x.sum())},
                       "scaled": {**stats(x.net_vt.values), "total_2x": float(x.net_vt_2x.sum()),
                                  "total_3x": float(x.net_vt_3x.sum())}}
        first = tk[tk.kind == "ontime"].head(DECIDE_DAYS)
        if len(first) == DECIDE_DAYS:                  # the decision uses the first 365 on-time days only
            u, v = stats(first.net.values), stats(first.net_vt.values)
            ok = v["max_dd"] < u["max_dd"] and (v["sharpe"] or 0) >= (u["sharpe"] or 0) - 0.2
            s["verdict_at_365"] = "KEEPS ITS PROMISE" if ok else "DOES NOT"
        status[book] = s
    if rows:
        pd.DataFrame(rows).to_csv(p, mode="a", header=not p.exists() or p.stat().st_size == 0, index=False)
        log(f"journaled {len(rows)} rows")
    (J / "status.json").write_text(json.dumps(status, indent=1, default=float))
    log({b: (round(s["m_next"], 2), s.get("ontime", {}).get("days", 0)) for b, s in status.items()})


if __name__ == "__main__":
    main()
