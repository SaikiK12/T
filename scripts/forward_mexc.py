"""mexc_fwd (R215): R200's forward signals traded one bar late on MEXC hourly closes and MEXC funding, as set out in
experiments/mexc_fwd/PREREG.md. Reads R200's journal (never writes it); appends to its own journal.

A symbol is tradable at row t when R200 lists it as eligible, it maps to a MEXC crypto contract in today's contract
snapshot, and MEXC has a close for row t (a delisted or halted contract has none).

usage: python scripts/forward_mexc.py
"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import forward_tick as ft  # noqa: E402
from forward_delayed import shift_rows  # noqa: E402
from lab import engine, events, gate, live, mexc, panel, prereg, slices  # noqa: E402

LANE = ROOT / "experiments" / "mexc_fwd"
J = LANE / "journal"
ON_TIME = panel.ms("2026-10-20")
R214 = ROOT / "experiments" / "flow72_fwd3" / "journal" / "tickets.csv"
H = ft.H
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def score():
    sig, ticks = ft.read("signals.csv"), ft.read("ticks.csv")
    syms, t0 = sorted(sig.symbol.unique()), ft.FWD_START
    last = int(ticks.t.max())
    T, S = (last - t0) // H + 1, len(syms)
    table = mexc.contracts()
    mp = mexc.map_symbols(syms, table)
    mx = sorted({m for m in mp.values() if m})
    end = last + 2 * H

    def one(m):
        try:
            return m, mexc.klines_cached(m, t0, end), mexc.funding_history(m, t0, end)
        except mexc.MexcError as e:
            log("mexc failed", m, e)
            return m, None, None

    with ThreadPoolExecutor(4) as ex:
        got = list(ex.map(one, mx))
    tt = np.arange(t0, end, H)
    kl = {m: k for m, k, _ in got if k is not None}
    fr = {m: f for m, _, f in got if f is not None}
    cm_, fm_ = live.grid(kl, tt, "close"), live.grid(fr, tt, "rate")
    ki, fi = {m: i for i, m in enumerate(kl)}, {m: i for i, m in enumerate(fr)}
    c = np.full((T + 1, S), np.nan, np.float32)
    fe = np.zeros((T + 1, S), np.float32)
    for s, j in ((s, j) for j, s in enumerate(syms)):
        m = mp[s]
        if m in ki:
            c[:, j] = cm_[:T + 1, ki[m]]
        if m in fi:
            fe[:, j] = np.nan_to_num(fm_[:T + 1, fi[m]])
    ret = c[1:] / c[:-1] - 1 - fe[1:]
    col = {s: i for i, s in enumerate(syms)}
    ri, ci = ((sig.t.values - t0) // H).astype(int), sig.symbol.map(col).values
    elig = np.zeros((T, S), bool)
    elig[ri, ci] = True
    rank = np.full((T, S), np.nan, np.float32)
    rank[ri, ci] = sig["rank"].values
    trad = elig & np.isfinite(c[:T])
    cmat = engine.cost_matrix(rank)
    ind, ind_all = {}, {}
    for k in ft.CELLS:
        x = np.zeros((T, S), bool)
        x[ri, ci] = sig[k].values == 0
        ind_all[k] = x & elig
        ind[k] = shift_rows(x & trad, trad, np.ones(T, int))
    known = np.isfinite(c[1:]).any(axis=1)
    D = (int(np.flatnonzero(known).max()) + 1 if known.any() else 0) // 24
    if D == 0:
        return None
    unit = 1.0 / (ft.HOLD * ft.K)
    have = pd.read_csv(J / "tickets.csv") if (J / "tickets.csv").exists() else pd.DataFrame()
    done = set(zip(have.day, have.book)) if not have.empty else set()
    rows = []
    for book in ("A", "B"):
        cells = ft.BOOKS[book]
        res = {}
        P = sum(slices.positions(ind[k], ft.HOLD, 0, D * 24, unit, -1) for k in cells)
        for name, cmult in (("1x", 1.0), ("2x", 2.0), ("3x", 3.0)):
            res[name] = slices.run(P, ret, trad, cmat, 0, D * 24, cmult=cmult)
        fund = -(P * fe[1:D * 24 + 1]).sum(axis=1)                     # the book's funding, before the hedge
        n_sig = sum(ind_all[k][:D * 24].sum(axis=1) for k in cells)
        n_trad = sum((ind_all[k] & trad)[:D * 24].sum(axis=1) for k in cells)
        for d in range(D):
            ms = t0 + d * 24 * H
            day = pd.Timestamp(ms, unit="ms", tz="UTC").strftime("%Y-%m-%d")
            if (day, book) in done:
                continue
            h, o = slice(d * 24, d * 24 + 24), res["1x"]
            rows.append({"day": day, "book": book, "net": float(o["daily"][d]), "gross": float(o["gross"][h].sum()),
                         "cost": float(o["cost"][h].sum()), "funding": float(fund[h].sum()),
                         "hedge": float(o["hedge"][h].sum() - o["hedge_cost"][h].sum()),
                         "net_2x": float(res["2x"]["daily"][d]), "net_3x": float(res["3x"]["daily"][d]),
                         "gross_exposure": float(o["gross_exposure"][h].mean()),
                         "coverage": float(n_trad[h].sum() / max(n_sig[h].sum(), 1)),
                         "kind": "ontime" if ms >= ON_TIME else "replay"})
    if rows:
        p = J / "tickets.csv"
        pd.DataFrame(rows).to_csv(p, mode="a", header=not p.exists() or p.stat().st_size == 0, index=False)
    tk = pd.read_csv(J / "tickets.csv")
    dropped = sorted(s for s in syms if not mp[s])
    fees = table[table.symbol.isin(mx)][["taker", "maker"]].describe().loc[["mean", "min", "max"]].to_dict()
    status = {"last_hour": pd.Timestamp(last, unit="ms", tz="UTC").isoformat(), "mapped": len(mx),
              "dropped": dropped, "mexc_fee": fees}
    r214 = pd.read_csv(R214) if R214.exists() else pd.DataFrame()
    for book in ("A", "B"):
        for kind in ("replay", "ontime"):
            n = tk[(tk.book == book) & (tk.kind == kind)].sort_values("day")
            if n.empty:
                continue
            x = n.net.values
            st = {"days": int(len(x)), "total": float(x.sum()), "total_2x": float(n.net_2x.sum()),
                  "total_3x": float(n.net_3x.sum()), "funding": float(n.funding.sum()),
                  "coverage": float(n.coverage.mean()), **events.summary(x)}
            if kind == "ontime" and book == "A":
                st["go_real"] = gate.go_real(x)
            if not r214.empty:
                ref = r214[r214.book == book].set_index("day").net.reindex(n.day).values
                ok = np.isfinite(ref)
                if ok.sum() >= 3:
                    st["r214_same_days_total"] = float(ref[ok].sum())
                    st["corr_r214"] = float(np.corrcoef(x[ok], ref[ok])[0, 1])
            status[f"{book}_{kind}"] = st
    (J / "status.json").write_text(json.dumps(status, indent=1, default=float))
    return status


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    J.mkdir(parents=True, exist_ok=True)
    st = score()
    if st:
        log({k: (v["days"], round(v["total"], 4), round(v.get("corr_r214", np.nan), 2))
             for k, v in st.items() if isinstance(v, dict) and "days" in v}, "dropped", st["dropped"])


if __name__ == "__main__":
    main()
