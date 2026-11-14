"""daylimit_v1 (R208): daily loss and profit limits on the flow slice books, as set out in
experiments/daylimit_v1/PREREG.md."""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, events, prereg, research, slices, stats  # noqa: E402

LANE = ROOT / "experiments" / "daylimit_v1"
START, DISC_END, SECOND, END = "2021-01-01", "2024-01-01", "2025-07-01", "2026-10-01"
CELLS = {"top_vs_crowd": ("flow:top_vs_crowd/xs8", 0), "taker24": ("flow:taker[24]/xs8", 0),
         "taker4": ("flow:taker[4]/xs8", 0)}
BOOKS = {"F": ("top_vs_crowd", "taker24", "taker4"), "T": ("top_vs_crowd",)}
HOLD = 72
GRID = ([(x, y) for x in (0.005, 0.01, 0.02) for y in (0.01, 0.02, 0.04)] + [(x, None) for x in (0.005, 0.01, 0.02)]
        + [(None, y) for y in (0.01, 0.02, 0.04)])
PRIMARY = ("F", 0.01, 0.02)
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def stop_mask(net, x, y):
    """[n] float mask: 0 from the row after the day's PnL first crosses -x or +y to the day's end."""
    D = len(net) // 24
    cum = np.cumsum(net[: D * 24].reshape(D, 24), axis=1)
    hit = np.zeros_like(cum, bool)
    if x is not None:
        hit |= cum <= -x
    if y is not None:
        hit |= cum >= y
    after = np.cumsum(hit, axis=1) > 0
    m = np.ones((D, 24))
    m[:, 1:] = ~after[:, :-1]
    out = np.ones(len(net))
    out[: D * 24] = m.ravel()
    return out


def pieces(P, u, t0, t1):
    """Per-row pieces at 1x costs: PnL before costs, the book's own change cost, the cost of reopening the whole
    book from flat at row r, and the cost of closing it at row r (from the row r - 1 positions)."""
    o = slices.run(P, u.ret, u.elig, u.cmat, t0, t1)
    c = np.asarray(u.cmat[t0:t1], np.float64)
    b = np.asarray(u.elig[t0:t1])
    cmh = np.where(b, c, 0).sum(axis=1) / np.maximum(b.sum(axis=1), 1)
    H = np.abs(o["net_exposure"])
    aP = np.abs(P)
    close = np.zeros(len(P))
    close[1:] = (aP[:-1] * c[1:]).sum(axis=1) + H[:-1] * cmh[1:]
    return {"pnl": o["gross"] + o["hedge"], "cost": o["cost"] + o["hedge_cost"],
            "reopen": (aP * c).sum(axis=1) + H * cmh, "close": close}


def overlaid(pc, x, y, cm):
    """Exact day-by-day solution: before its trigger a day's positions equal the book's, except that the first row
    reopens from flat after a stopped day. Returns (hourly net, mask)."""
    n = len(pc["pnl"])
    D = n // 24
    net = np.zeros(n)
    M = np.ones(n)
    stopped = False
    for d in range(D):
        a = d * 24
        v = pc["pnl"][a:a + 24] - cm * pc["cost"][a:a + 24]
        if stopped:
            v[0] += cm * (pc["cost"][a] - pc["reopen"][a])
        cum = np.cumsum(v)
        hit = np.zeros(24, bool)
        if x is not None:
            hit |= cum <= -x
        if y is not None:
            hit |= cum >= y
        k = int(np.argmax(hit)) if hit.any() else 24
        stopped = k < 23
        if stopped:
            v[k + 1] = -cm * pc["close"][a + k + 1]
            v[k + 2:] = 0.0
            M[a + k + 1:a + 24] = 0.0
        net[a:a + 24] = v
    return net, M


def stats_row(n, base):
    d = n - base
    s = events.summary(n)
    return {"total": float(n.sum()), "mean_bp_day": float(n.mean() * 1e4), "sharpe": s.get("sharpe", np.nan),
            "max_dd": s.get("max_dd", np.nan), "worst_day": float(n.min()), "p01_day": float(np.quantile(n, 0.01)),
            "diff_bp_day": float(d.mean() * 1e4), "diff_t_nw10": float(stats.newey_west_t(d, 10)[2])}


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    rd = data.ROOT / "research"
    fb = np.load(rd / "bins_flow.npy", mmap_mode="r")
    fn = json.loads((rd / "meta_flow.json").read_text())["names"]
    t0, td, ts, t1 = (research.row_of(u.p, d) for d in (START, DISC_END, SECOND, END))
    t1 -= (t1 - t0) % 24
    inds = {k: (np.asarray(fb[fn.index(n), :t1]) == b) & u.elig[:t1] for k, (n, b) in CELLS.items()}
    D = (t1 - t0) // 24
    d_s = (ts - t0) // 24
    win = {"insample": slice(0, d_s), "second": slice(d_s, D)}
    rows, acf = [], {}
    for book, parts in BOOKS.items():
        K = float(np.mean([inds[p][t0:td].sum(axis=1).mean() for p in parts]) * len(parts))
        P = sum(slices.positions(inds[p], HOLD, t0, t1, 1.0 / (HOLD * K), -1) for p in parts)
        pc = pieces(P, u, t0, t1)
        net, M = overlaid(pc, 0.01, 0.02, 2.0)                  # exactness check against the full engine
        chk = slices.run(P * M[:, None], u.ret, u.elig, u.cmat, t0, t1, cmult=2.0)["net"]
        assert np.allclose(chk[: D * 24], net[: D * 24], atol=1e-12), np.abs(chk[: D * 24] - net[: D * 24]).max()
        assert np.array_equal(stop_mask(chk, 0.01, 0.02)[: D * 24], M[: D * 24])
        log(f"book {book}: K {K:.3f}, exact overlay check passed")
        for cm in (1.0, 2.0, 3.0):
            base = slices.run(P, u.ret, u.elig, u.cmat, t0, t1, cmult=cm)
            bd = base["daily"]
            if cm == 1.0:
                h = base["net"][: d_s * 24]
                acf[book] = {f"lag{k}": float(np.corrcoef(h[:-k], h[k:])[0, 1]) for k in range(1, 7)}
            for w, sl in win.items():
                rows.append({"book": book, "x": None, "y": None, "cmult": cm, "window": w, "stopped_share": 0.0,
                             **stats_row(bd[sl], bd[sl])})
            for x, y in GRID:
                net, M = overlaid(pc, x, y, cm)
                n = net[: D * 24].reshape(D, 24).sum(axis=1)
                stopped = (M[: D * 24].reshape(D, 24) == 0).any(axis=1)
                for w, sl in win.items():
                    rows.append({"book": book, "x": x, "y": y, "cmult": cm, "window": w,
                                 "stopped_share": float(stopped[sl].mean()), **stats_row(n[sl], bd[sl])})
            log(f"book {book} cmult {cm} done")
    df = pd.DataFrame(rows)
    df.to_csv(out / "overlays.csv", index=False)
    b, x, y = PRIMARY
    pr = df[(df.book == b) & (df.x == x) & (df.y == y) & (df.cmult == 1.0)].set_index("window")
    verdict = {"primary": {"book": b, "x": x, "y": y},
               "insample_diff_bp_day": float(pr.loc["insample", "diff_bp_day"]),
               "insample_diff_t": float(pr.loc["insample", "diff_t_nw10"]),
               "second_diff_bp_day": float(pr.loc["second", "diff_bp_day"]),
               "improves": bool(pr.loc["insample", "diff_bp_day"] > 0 and pr.loc["insample", "diff_t_nw10"] >= 2
                                and pr.loc["second", "diff_bp_day"] > 0),
               "hourly_autocorrelation_insample": acf}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    pd.set_option("display.width", 250)
    log("\n" + df[df.cmult == 1.0].round(4).to_string(index=False))
    log(verdict)


if __name__ == "__main__":
    main()
