"""venue_gap_v1 (R216): the flow books' PnL split into crypto and TradFi contracts, in the archive and on the forward
replay, as set out in experiments/venue_gap_v1/PREREG.md."""
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
from forward_delayed import shift_rows  # noqa: E402
from lab import data, engine, events, live, mexc, prereg, research, slices, stats  # noqa: E402

LANE = ROOT / "experiments" / "venue_gap_v1"
CELLS = ("flow:top_vs_crowd/xs8", "flow:taker[24]/xs8", "flow:taker[4]/xs8")
HOLD, K = 72, 9.316
START, HOLD_OUT, END = "2021-01-01", "2025-07-01", "2026-10-01"
REPLAY_END = "2026-10-19"
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def tradfi_symbols():
    info = live.get("fapi/v1/exchangeInfo")
    return sorted(s["symbol"] for s in info["symbols"] if s.get("contractType") == "TRADIFI_PERPETUAL"
                  or s.get("underlyingType") not in ("COIN", "PREMARKET", None))


def stats_of(n):
    s = events.summary(n)
    return {"days": len(n), "total": float(n.sum()), "mean_bp_day": float(n.mean() * 1e4),
            "t_nw10": float(stats.newey_west_t(n, 10)[2]), "max_dd": s.get("max_dd", np.nan)}


def book(inds, cells, ret, elig, cmat, a, b, cm):
    """Rows [a, b) warmed up from a - HOLD: daily net, gross by symbol (before the hedge), and the run."""
    w = max(a - HOLD, 0)
    P = sum(slices.positions(inds[c], HOLD, w, b, 1.0 / (HOLD * K), -1) for c in cells)
    o = slices.run(P, ret, elig, cmat, w, b, cmult=cm)
    D = (b - a) // 24
    n = o["net"][a - w: a - w + D * 24].reshape(D, 24).sum(1)
    by_sym = (P * np.nan_to_num(np.asarray(ret[w:b], np.float64)))[a - w:].sum(0)
    return n, by_sym


def archive(tf, out):
    u, _, _ = research.load_universe()
    t0, th, t1 = (research.row_of(u.p, d) for d in (START, HOLD_OUT, END))
    th -= (th - t0) % 24
    t1 -= (t1 - th) % 24
    is_tf = np.array([s in tf for s in u.p.symbols])
    log("TradFi symbols in the archive:", int(is_tf.sum()), [s for s in u.p.symbols if s in tf][:40])
    rd = data.ROOT / "research"
    fb = np.load(rd / "bins_flow.npy", mmap_mode="r")
    fn = json.loads((rd / "meta_flow.json").read_text())["names"]
    raw = {c: (np.asarray(fb[fn.index(c)]) == 0) for c in CELLS}
    crypto_elig = u.elig & ~is_tf[None, :]
    rows, contrib = [], []
    for book_name, cells in (("A", CELLS), ("B", CELLS[:1])):
        for w, (a, b) in (("in_sample", (t0, th)), ("holdout", (th, t1))):
            for universe, el in (("all", u.elig), ("crypto", crypto_elig)):
                inds = {c: raw[c] & el for c in cells}
                for cm in (1.0, 2.0, 3.0):
                    n, by_sym = book(inds, cells, u.ret, el, u.cmat, a, b, cm)
                    r = {"part": "archive", "book": book_name, "window": w, "universe": universe, "cmult": cm,
                         **stats_of(n)}
                    if universe == "all" and cm == 1.0:
                        g = by_sym.sum()
                        r["tradfi_share_of_gross"] = float(by_sym[is_tf].sum() / g) if g else np.nan
                        r["tradfi_gross_bp_day"] = float(by_sym[is_tf].sum() / len(n) * 1e4)
                        top = np.argsort(-by_sym)[:10]
                        contrib += [{"book": book_name, "window": w, "symbol": u.p.symbols[j],
                                     "gross_total": float(by_sym[j]), "tradfi": bool(is_tf[j])} for j in top]
                    rows.append(r)
                log(book_name, w, universe, {k: round(v, 3) for k, v in rows[-3].items() if isinstance(v, float)})
    return rows, contrib, u.p.symbols, is_tf


def replay(tf):
    sig, ticks = ft.read("signals.csv"), ft.read("ticks.csv")
    syms, t0 = sorted(sig.symbol.unique()), ft.FWD_START
    last = int(ticks.t.max())
    T, S = (last - t0) // ft.H + 1, len(syms)
    D = (ft.panel.ms(REPLAY_END) - t0) // (24 * ft.H)
    tt, names, close, _, _, _ = ft.universe(last + 2 * ft.H)
    col = {s: i for i, s in enumerate(syms)}
    ri, ci = ((sig.t.values - t0) // ft.H).astype(int), sig.symbol.map(col).values
    elig = np.zeros((T, S), bool)
    elig[ri, ci] = True
    rank = np.full((T, S), np.nan, np.float32)
    rank[ri, ci] = sig["rank"].values
    cmat = engine.cost_matrix(rank)
    off = int((t0 - tt[0]) // ft.H)
    c = np.full((T + 1, S), np.nan, np.float32)
    for s in syms:
        if s in names:
            seg = close[off:off + T + 1, names.index(s)]
            c[:len(seg), col[s]] = seg
    fe = ft.funding_event(syms, np.arange(t0, last + 2 * ft.H, ft.H))
    ret = c[1:] / c[:-1] - 1 - np.nan_to_num(fe[1:T + 1])
    mp = mexc.map_symbols(syms, mexc.contracts())
    is_tf = np.array([s in tf for s in syms])
    mapped = np.array([mp[s] is not None for s in syms])
    raw = {}
    for k in ft.CELLS:
        x = np.zeros((T, S), bool)
        x[ri, ci] = sig[k].values == 0
        raw[k] = x
    rows, contrib = [], []
    for universe, keep in (("all", np.ones(S, bool)), ("crypto", ~is_tf), ("mexc_mapped", mapped)):
        el = elig & keep[None, :]
        inds = {k: shift_rows(raw[k] & el, el, np.ones(T, int)) for k in ft.CELLS}
        for book_name in ("A", "B"):
            for cm in (1.0, 2.0, 3.0):
                P = sum(slices.positions(inds[k], ft.HOLD, 0, D * 24, 1.0 / (ft.HOLD * ft.K), -1)
                        for k in ft.BOOKS[book_name])
                o = slices.run(P, ret, el, cmat, 0, D * 24, cmult=cm)
                r = {"part": "replay", "book": book_name, "window": "2026-10-01..18", "universe": universe,
                     "cmult": cm, **stats_of(o["daily"])}
                if universe == "all" and cm == 1.0:
                    by_sym = (P * np.nan_to_num(ret[:D * 24])).sum(0)
                    g = by_sym.sum()
                    r["tradfi_share_of_gross"] = float(by_sym[is_tf].sum() / g) if g else np.nan
                    top = np.argsort(-by_sym)[:10]
                    contrib += [{"book": book_name, "window": "replay", "symbol": syms[j],
                                 "gross_total": float(by_sym[j]), "tradfi": bool(is_tf[j])} for j in top]
                rows.append(r)
            log("replay", universe, book_name, round(rows[-3]["total"], 4))
    return rows, contrib


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    tf = set(tradfi_symbols())
    (out / "tradfi_symbols.json").write_text(json.dumps(sorted(tf)))
    rows, contrib, _, _ = archive(tf, out)
    r2, c2 = replay(tf)
    df = pd.DataFrame(rows + r2)
    df.to_csv(out / "results.csv", index=False)
    pd.DataFrame(contrib + c2).to_csv(out / "top_contributors.csv", index=False)
    pick = lambda part, bk, w: df[(df.part == part) & (df.book == bk) & (df.window == w) & (df.universe == "all")
                                  & (df.cmult == 1.0)].tradfi_share_of_gross.iloc[0]
    verdict = {"tradfi_share_A_holdout": float(pick("archive", "A", "holdout")),
               "tradfi_share_A_replay": float(pick("replay", "A", "2026-10-01..18"))}
    verdict["flag_partly_non_crypto"] = bool(max(verdict.values()) >= 0.30)
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    pd.set_option("display.width", 250)
    log("\n" + df.round(4).to_string(index=False))
    log("\n" + pd.DataFrame(contrib + c2).round(4).to_string(index=False))
    log(json.dumps(verdict, indent=1))


if __name__ == "__main__":
    main()
