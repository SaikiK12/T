"""flow72_fwd3 (R214): R200's forward books with each slice entered one bar after its signal bar, as set out in
experiments/flow72_fwd3/PREREG.md. Reads R200's journal (never writes it); appends to its own journal.

usage: python scripts/forward_delayed.py   (after scripts/forward_tick.py, which refreshes the price cache)
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
import forward_tick as ft  # noqa: E402
from lab import engine, events, gate, panel, prereg, slices  # noqa: E402

LANE = ROOT / "experiments" / "flow72_fwd3"
J = LANE / "journal"
ON_TIME = panel.ms("2026-10-20")
H = ft.H
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def shift_rows(ind, elig, lag):
    """ind[t] opens at row t + lag[t] (lag per row), kept only if the symbol is eligible there."""
    out = np.zeros_like(ind)
    T = len(ind)
    for t in np.flatnonzero(ind.any(axis=1)):
        e = t + int(lag[t])
        if e < T:
            out[e] |= ind[t]
    return out & elig


def score(tt, names, close):
    sig, ticks = ft.read("signals.csv"), ft.read("ticks.csv")
    syms, t0 = sorted(sig.symbol.unique()), ft.FWD_START
    last = int(ticks.t.max())
    T, S = (last - t0) // H + 1, len(syms)
    col = {s: i for i, s in enumerate(syms)}
    ri, ci = ((sig.t.values - t0) // H).astype(int), sig.symbol.map(col).values
    elig = np.zeros((T, S), bool)
    elig[ri, ci] = True
    rank = np.full((T, S), np.nan, np.float32)
    rank[ri, ci] = sig["rank"].values
    cmat = engine.cost_matrix(rank)
    ind = {}
    for k in ft.CELLS:
        x = np.zeros((T, S), bool)
        x[ri, ci] = sig[k].values == 0
        ind[k] = x & elig
    # realized lag: first bar closing at or after R200's run_at (on-time rows); one bar before ON_TIME (warm-up)
    run_at = pd.to_datetime(ticks.run_at, utc=True).astype("int64").values // 10**6
    ready = (-(-run_at // H)) * H                                   # run_at rounded up to the hour
    lag_rt = np.ones(T, int)
    rows = ((ticks.t.values - t0) // H).astype(int)
    on = ticks.t.values >= ON_TIME
    lag_rt[rows[on]] = np.maximum((ready[on] - H - ticks.t.values[on]) // H, 1)
    d1 = {k: shift_rows(x, elig, np.ones(T, int)) for k, x in ind.items()}
    rt = {k: shift_rows(x, elig, lag_rt) for k, x in ind.items()}
    off = int((t0 - tt[0]) // H)
    c = np.full((T + 1, S), np.nan, np.float32)
    for s in syms:
        if s in names:
            seg = close[off:off + T + 1, names.index(s)]
            c[:len(seg), col[s]] = seg
    fe = ft.funding_event(syms, np.arange(t0, last + 2 * H, H))
    ret = c[1:] / c[:-1] - 1 - np.nan_to_num(fe[1:T + 1])
    known = np.isfinite(c[1:]).any(axis=1)
    D = (int(np.flatnonzero(known).max()) + 1 if known.any() else 0) // 24
    if D == 0:
        return None
    unit = 1.0 / (ft.HOLD * ft.K)
    books = {"A": (d1, ft.BOOKS["A"]), "B": (d1, ft.BOOKS["B"]), "A_rt": (rt, ft.BOOKS["A"])}
    have = pd.read_csv(J / "tickets.csv") if (J / "tickets.csv").exists() else pd.DataFrame()
    done = set(zip(have.day, have.book)) if not have.empty else set()
    out_rows = []
    for book, (src, cells) in books.items():
        res = {}
        for name, cm in (("1x", 1.0), ("2x", 2.0), ("3x", 3.0)):
            P = sum(slices.positions(src[k], ft.HOLD, 0, D * 24, unit, -1) for k in cells)
            res[name] = slices.run(P, ret, elig, cmat, 0, D * 24, cmult=cm)
        for d in range(D):
            ms = t0 + d * 24 * H
            day = pd.Timestamp(ms, unit="ms", tz="UTC").strftime("%Y-%m-%d")
            if (day, book) in done or (book == "A_rt" and ms < ON_TIME):
                continue
            h, o = slice(d * 24, d * 24 + 24), res["1x"]
            out_rows.append({"day": day, "book": book, "net": float(o["daily"][d]),
                             "gross": float(o["gross"][h].sum()), "cost": float(o["cost"][h].sum()),
                             "hedge": float(o["hedge"][h].sum() - o["hedge_cost"][h].sum()),
                             "net_2x": float(res["2x"]["daily"][d]), "net_3x": float(res["3x"]["daily"][d]),
                             "gross_exposure": float(o["gross_exposure"][h].mean()),
                             "kind": "ontime" if ms >= ON_TIME else "replay"})
    if out_rows:
        df = pd.DataFrame(out_rows)
        p = J / "tickets.csv"
        df.to_csv(p, mode="a", header=not p.exists() or p.stat().st_size == 0, index=False)
    tk = pd.read_csv(J / "tickets.csv")
    r200 = ft.read("tickets.csv")
    lag_min = (run_at[on] - (ticks.t.values[on] + H)) / 60000
    status = {"last_hour": pd.Timestamp(last, unit="ms", tz="UTC").isoformat(),
              "run_at_lag_min": ({"n": int(on.sum()), "median": float(np.median(lag_min)),
                                  "p90": float(np.percentile(lag_min, 90)), "max": float(lag_min.max())}
                                 if on.any() else None)}
    for book in books:
        for kind in ("replay", "ontime"):
            n = tk[(tk.book == book) & (tk.kind == kind)].sort_values("day")
            if n.empty:
                continue
            x = n.net.values
            st = {"days": int(len(x)), "total": float(x.sum()), "total_2x": float(n.net_2x.sum()),
                  "total_3x": float(n.net_3x.sum()), **events.summary(x)}
            if kind == "ontime" and book == "A":
                st["go_real"] = gate.go_real(x)
            if kind == "replay" and book in ("A", "B") and not r200.empty:
                ref = r200[(r200.book == book) & r200.day.isin(n.day)]
                st["r200_same_days_total"] = float(ref.net.sum())
            status[f"{book}_{kind}"] = st
    (J / "status.json").write_text(json.dumps(status, indent=1, default=float))
    return status


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    J.mkdir(parents=True, exist_ok=True)
    ticks = ft.read("ticks.csv")
    end = min(int(ticks.t.max()) + 2 * H, int(time.time() * 1000) // H * H)
    tt, names, close, _, _, _ = ft.universe(end)
    st = score(tt, names, close)
    if st:
        log(json.dumps({k: v for k, v in st.items() if k in ("last_hour", "run_at_lag_min")}),
            {k: (v["days"], round(v["total"], 4)) for k, v in st.items() if isinstance(v, dict) and "days" in v})


if __name__ == "__main__":
    main()
