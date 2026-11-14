"""flow72_fwd2 (R200): one forward tick, as set out in experiments/flow72_fwd2/PREREG.md. Paper only.

Computes every closed hour not yet journaled (from 2026-10-01 00:00 UTC), appends the tradable coins' rows to
journal/signals.csv and one row per hour to journal/ticks.csv, then marks books A and B and appends one ticket per
book for every complete UTC day not yet ticketed. Idempotent: a second run right after adds nothing.

usage: python scripts/forward_tick.py [--max-hours N] [--no-score]
"""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import engine, events, flowfeat, gate, live, panel, prereg, slices  # noqa: E402

LANE = ROOT / "experiments" / "flow72_fwd2"
J = LANE / "journal"
H = live.HOUR
FWD_START = panel.ms("2026-10-01")
FROZEN_ON = panel.ms("2026-10-19")         # hours before the freeze date are flagged late
MARGIN = 12 * 60_000                       # an hour is computed 12 minutes after its bar closes
WARM = 30 * H                              # ratio history fetched before the first hour to compute (taker[24])
RANK_WINDOW = 720
CELLS = {"tvc": "top_vs_crowd", "t24": "taker[24]", "t4": "taker[4]"}
BOOKS = {"A": ("tvc", "t24", "t4"), "B": ("tvc",)}
HOLD, K = 72, 9.316
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def read(name):
    p = J / name
    return pd.read_csv(p) if p.exists() and p.stat().st_size else pd.DataFrame()


def append(name, df):
    if df.empty:
        return
    p = J / name
    new = not p.exists() or p.stat().st_size == 0
    df.to_csv(p, mode="a", header=new, index=False)


def gate_shift():
    par = json.loads((LANE / "parity.json").read_text())
    gated = [f"flow:{v}/xs8" for v in CELLS.values()]          # the PREREG gates the book's three specs only
    bad = {k: par["bins_common"][k]["match"] for k in gated
           if par["bins_common"][k]["match"] is None or par["bins_common"][k]["match"] < 0.99}
    if bad:
        raise SystemExit(f"data gate failed, forward test not started: {bad}")
    return {k: int(v) for k, v in par["shifts_ms"].items()}


def universe(end):
    """Klines for every trading perpetual on [FWD_START - 744 h, end), the live liquidity rank and tradable mask."""
    perps = live.perpetuals()
    k0 = FWD_START - (RANK_WINDOW + 24) * H

    def one(s):
        try:
            return s, live.klines_cached(s, k0, end)
        except live.LiveError as e:
            log("klines failed", s, e)
            return s, None

    with ThreadPoolExecutor(6) as ex:
        kl = dict(ex.map(one, perps))
    failed = sorted(s for s, df in kl.items() if df is None)
    if failed:                                     # a dropped coin would shift every rank: write nothing this tick
        raise SystemExit(f"klines failed for {failed}; tick aborted, the hours are computed on the next run")
    kl = {s: df for s, df in kl.items() if df is not None and len(df)}
    tt = np.arange(k0, end, H)
    close = live.grid(kl, tt, "close")
    qv = live.grid(kl, tt, "quote_volume")
    rank = live.liquidity_rank(qv, close, RANK_WINDOW)
    elig = (rank <= 50) & np.isfinite(close)
    return tt, list(kl), close, qv, rank, elig


def compute_hours(todo, tt, names, close, qv, rank, elig, shift):
    rows_todo = ((np.asarray(todo) - tt[0]) // H).astype(int)
    cols = np.flatnonzero(elig[rows_todo].any(axis=0))
    frames, cover = {}, {}
    for i, j in enumerate(cols):
        s = names[j]
        f = live.ratios_cached(s, int(todo[0]) - WARM, int(todo[-1]) + H + live.FIVE)
        frames[s] = live.hourly_metrics(f, shift)
        for ep, key in (("topLongShortPositionRatio", "n_top"), ("takerlongshortRatio", "n_taker"),
                        ("globalLongShortAccountRatio", "n_ls")):
            d = f.get(ep)
            if d is not None and len(d):
                ts = d["timestamp"].values + shift.get(ep, 0)
                cover[(s, key)] = pd.Series(1, index=(ts // H) * H).groupby(level=0).sum()
        if i % 20 == 0:
            log(f"ratios {i + 1}/{len(cols)} {s}")
    full = {s: frames.get(s) for s in names}
    m = {c: live.grid(full, tt, c) for c in flowfeat.METRIC_COLS}
    f = flowfeat.raw_features(m, None, close, qv)
    b = {k: flowfeat.binned(f[v], flowfeat.XS8, elig) for k, v in CELLS.items()}
    sig, ticks = [], []
    run_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for t, r in zip(todo, rows_todo):
        late = int(t < FROZEN_ON)
        idx = np.flatnonzero(elig[r])
        for j in idx:
            s = names[j]
            sig.append({"t": int(t), "symbol": s, "rank": int(rank[r, j]), "close": float(close[r, j]),
                        **{c: float(m[c][r, j]) for c in flowfeat.METRIC_COLS},
                        "n_top": int(cover.get((s, "n_top"), pd.Series(dtype=int)).get(t, 0)),
                        "n_taker": int(cover.get((s, "n_taker"), pd.Series(dtype=int)).get(t, 0)),
                        "n_ls": int(cover.get((s, "n_ls"), pd.Series(dtype=int)).get(t, 0)),
                        **{k: int(b[k][r, j]) for k in CELLS}, "late": late})
        ticks.append({"t": int(t), "utc": pd.Timestamp(int(t), unit="ms", tz="UTC").strftime("%Y-%m-%d %H:%M"),
                      "n_elig": int(len(idx)), "n_feat": int((b["tvc"][r, idx] >= 0).sum()),
                      **{f"n_{k}0": int((b[k][r, idx] == 0).sum()) for k in CELLS}, "run_at": run_at, "late": late})
    return pd.DataFrame(sig), pd.DataFrame(ticks)


def funding_event(names, tt):
    def one(s):
        try:
            return s, live.funding_history(s, int(tt[0]), int(tt[-1]) + 2 * H)
        except live.LiveError as e:
            log("funding failed", s, e)
            return s, None

    with ThreadPoolExecutor(4) as ex:
        fr = dict(ex.map(one, names))
    failed = sorted(s for s, df in fr.items() if df is None)
    if failed:                                     # missing funding would score as zero funding: write no ticket
        raise SystemExit(f"funding failed for {failed}; scoring aborted, tickets are written on the next run")
    return live.grid(fr, tt, "rate")


def score(tt, names, close):
    """Rebuild the books from the journal and append tickets for complete days not yet ticketed."""
    sig = read("signals.csv")
    if sig.empty:
        return None
    syms = sorted(sig.symbol.unique())
    t0 = FWD_START
    last = int(read("ticks.csv").t.max())
    g = np.arange(t0, last + H, H)
    T, S = len(g), len(syms)
    col = {s: i for i, s in enumerate(syms)}
    ri, ci = ((sig.t.values - t0) // H).astype(int), sig.symbol.map(col).values
    elig = np.zeros((T, S), bool)
    elig[ri, ci] = True
    rank = np.full((T, S), np.nan, np.float32)
    rank[ri, ci] = sig["rank"].values
    cmat = engine.cost_matrix(rank)
    ind = {}
    for k in CELLS:
        x = np.zeros((T, S), bool)
        x[ri, ci] = sig[k].values == 0
        ind[k] = x
    # prices: close on the grid plus one hour, funding settled in the next bar
    k_of = {s: names.index(s) for s in syms if s in names}
    off = int((t0 - tt[0]) // H)
    c = np.full((T + 1, S), np.nan, np.float32)
    for s, j in k_of.items():
        seg = close[off:off + T + 1, j]
        c[:len(seg), col[s]] = seg
    fe = funding_event(syms, np.arange(t0, last + 2 * H, H))
    ret = c[1:] / c[:-1] - 1 - np.nan_to_num(fe[1:T + 1])
    known = np.isfinite(c[1:]).any(axis=1)                 # rows whose next close exists
    n_known = int(np.flatnonzero(known).max()) + 1 if known.any() else 0
    D = n_known // 24                                      # complete days
    if D == 0:
        return None
    have = read("tickets.csv")
    done = set(zip(have.day, have.book)) if not have.empty else set()
    top10 = elig & (rank <= 10)
    only_btc = np.zeros_like(elig)
    if "BTCUSDT" in col:
        only_btc[:, col["BTCUSDT"]] = True
    rows, unit = [], 1.0 / (HOLD * K)
    for book, cells in BOOKS.items():
        out = {}
        for name, cm, basket in (("1x", 1.0, None), ("2x", 2.0, None), ("3x", 3.0, None), ("top10", 1.0, top10),
                                 ("btc", 1.0, only_btc)):
            parts = [slices.book(ind[k] & elig, ret, elig, cmat, HOLD, unit, 0, D * 24, side=-1, hedge=True,
                                 cmult=cm, basket=basket) for k in cells]
            out[name] = {key: sum(p[key] for p in parts) for key in parts[0]}
        for d in range(D):
            day = pd.Timestamp(int(t0 + d * 24 * H), unit="ms", tz="UTC").strftime("%Y-%m-%d")
            if (day, book) in done:
                continue
            h = slice(d * 24, d * 24 + 24)
            o = out["1x"]
            rows.append({"day": day, "book": book, "net": float(o["daily"][d]), "gross": float(o["gross"][h].sum()),
                         "cost": float(o["cost"][h].sum()), "hedge": float(o["hedge"][h].sum() - o["hedge_cost"][h].sum()),
                         "net_2x": float(out["2x"]["daily"][d]), "net_3x": float(out["3x"]["daily"][d]),
                         "net_top10": float(out["top10"]["daily"][d]), "net_btc": float(out["btc"]["daily"][d]),
                         "gross_exposure": float(o["gross_exposure"][h].mean()),
                         "late": int(t0 + d * 24 * H < FROZEN_ON)})
    append("tickets.csv", pd.DataFrame(rows))
    tk = read("tickets.csv")
    status = {"last_hour": pd.Timestamp(last, unit="ms", tz="UTC").isoformat(), "days_scored": int(tk.day.nunique()),
              "short_now": {k: sorted(sig[(sig.t == last) & (sig[k] == 0)].symbol) for k in CELLS}}
    for book in BOOKS:
        n = tk[tk.book == book].sort_values("day")
        x = n.net.values
        status[book] = {"days": int(len(x)), "total": float(x.sum()), "total_2x": float(n.net_2x.sum()),
                        "total_3x": float(n.net_3x.sum()), "go_real": gate.go_real(x), **events.summary(x)}
        eq = np.cumsum(x)
        peak = np.maximum.accumulate(eq)
        hit = np.flatnonzero((peak > 0) & (eq <= 0.5 * peak))
        t_nw = status[book].get("t_nw")
        pass_now = bool(status[book]["go_real"]["pass"] and t_nw is not None and t_nw >= 2)
        # pass_now is a checkpoint reading; the PREREG decides only at 90 scored days
        status[book]["prereg"] = {"pass_now": pass_now, "decision_at_days": 90,
                                  "verdict": ("PASS" if pass_now else "FAIL") if len(x) >= 90 else "PENDING",
                                  "stop_rule_hit_day": n.day.iloc[hit[0]] if len(hit) and book == "A" else None}
    (J / "status.json").write_text(json.dumps(status, indent=1, default=float))
    return status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-hours", type=int, default=0)
    ap.add_argument("--no-score", action="store_true")
    a = ap.parse_args()
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    shift = gate_shift()
    J.mkdir(parents=True, exist_ok=True)
    now = int(time.time() * 1000)
    last_ok = (now - H - MARGIN) // H * H
    ticks = read("ticks.csv")
    nxt = int(ticks.t.max()) + H if not ticks.empty else FWD_START
    todo = np.arange(nxt, last_ok + H, H)
    if a.max_hours:
        todo = todo[: a.max_hours]
    end = int(max(last_ok + 2 * H, nxt + H))
    end = min(end, now // H * H)                           # never include the bar still open
    tt, names, close, qv, rank, elig = universe(end)
    log(f"{len(names)} perpetuals, grid {len(tt)} h, {len(todo)} hours to compute")
    if len(todo):
        sig, tk = compute_hours(todo, tt, names, close, qv, rank, elig, shift)
    if len(todo) and sig.empty:
        log("no eligible rows in the hours to compute; nothing journaled")
    elif len(todo):
        # an hour is averaged over all twelve 5-minute rows (PREREG); the newest rows publish minutes after the
        # close, so an hour waits until 95% of its coins have 12 rows of all three ratios (top, crowd, taker), or
        # until 3 h after its close. n_ls (crowd rows) gates only; it is not journaled (fixed signals.csv columns).
        full = ((sig.n_top >= 12) & (sig.n_taker >= 12) & (sig.n_ls >= 12)).groupby(sig.t).mean()
        short = [t for t in todo if full.get(t, 0.0) < 0.95 and now < t + H + 3 * H]
        if short:
            log(f"deferred {len(todo) - list(todo).index(short[0])} hours from "
                f"{pd.Timestamp(int(short[0]), unit='ms', tz='UTC')}: complete share {full.get(short[0], 0.0):.2f}")
            sig, tk = sig[sig.t < short[0]], tk[tk.t < short[0]]
        have = read("signals.csv")
        if not have.empty:                         # a run killed between the two appends must not duplicate rows
            sig = sig[~sig.t.isin(set(have.t))]
        append("signals.csv", sig.drop(columns="n_ls"))
        append("ticks.csv", tk)
        if len(tk):
            log(f"journaled {len(tk)} hours, {len(sig)} rows; last {tk.utc.iloc[-1]}")
    if not a.no_score:
        st = score(tt, names, close)
        if st:
            log(json.dumps({k: st[k] for k in ("last_hour", "days_scored")}),
                {b: (st[b]["days"], round(st[b]["total"], 4)) for b in BOOKS})


if __name__ == "__main__":
    main()
