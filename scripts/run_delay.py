"""delay_v1 (R213): the flow books with entry delayed d hours after the signal bar, as set out in
experiments/delay_v1/PREREG.md."""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, events, prereg, research, slices, stats  # noqa: E402

LANE = ROOT / "experiments" / "delay_v1"
CELLS = ("flow:top_vs_crowd/xs8", "flow:taker[24]/xs8", "flow:taker[4]/xs8")
HOLD, K = 72, 9.316
START, HOLD_OUT, END = "2021-01-01", "2025-07-01", "2026-10-01"
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def delayed(ind, elig, d):
    """A slice signalled at row t opens at row t + d if the symbol is eligible there."""
    if d == 0:
        return ind
    out = np.zeros_like(ind)
    out[d:] = ind[:-d]
    return out & elig


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    t0, th, t1 = (research.row_of(u.p, d) for d in (START, HOLD_OUT, END))
    th -= (th - t0) % 24
    t1 -= (t1 - th) % 24
    rd = data.ROOT / "research"
    fb = np.load(rd / "bins_flow.npy", mmap_mode="r")
    fn = json.loads((rd / "meta_flow.json").read_text())["names"]
    inds = {n: (np.asarray(fb[fn.index(n)]) == 0) & u.elig for n in CELLS}
    books = {"A": list(CELLS), "B": [CELLS[0]]}
    windows = {"in_sample": (t0, th), "holdout": (th, t1)}
    rows, keep = [], {}
    for d in (0, 1, 2):
        dind = {n: delayed(x, u.elig, d) for n, x in inds.items()}
        for book, cells in books.items():
            for w, (a, b) in windows.items():
                wu = max(a - HOLD, 0)                          # warm-up: slices opened before a are held into it
                D = (b - a) // 24
                for cm in (1.0, 2.0, 3.0):
                    P = sum(slices.positions(dind[n], HOLD, wu, b, 1.0 / (HOLD * K), -1) for n in cells)
                    o = slices.run(P, u.ret, u.elig, u.cmat, wu, b, cmult=cm)
                    day = lambda x: x[a - wu: a - wu + D * 24].reshape(D, 24).sum(1)
                    n = day(o["net"])
                    s = events.summary(n)
                    rows.append({"book": book, "delay_h": d, "window": w, "cmult": cm, "days": D,
                                 "mean_bp_day": float(n.mean() * 1e4), "t_nw10": float(stats.newey_west_t(n, 10)[2]),
                                 "total": float(n.sum()), "max_dd": s.get("max_dd", np.nan),
                                 "gross_bp_day": float(day(o["gross"] + o["hedge"]).mean() * 1e4),
                                 "cost_bp_day": float(day(o["cost"] + o["hedge_cost"]).mean() * 1e4)})
                    if cm == 1.0:
                        keep[f"{book}_d{d}_{w}"] = n
                r = rows[-3]
                log(f"{book} d={d} {w}: {r['mean_bp_day']:+.1f} bp/day t {r['t_nw10']:+.2f}")
    df = pd.DataFrame(rows)
    df.to_csv(out / "results.csv", index=False)
    np.savez_compressed(out / "daily.npz", **keep)
    one = df[df.cmult == 1.0].set_index(["book", "window", "delay_h"]).mean_bp_day
    loss = {f"{bk}_{w}_d{d}": float((one[bk, w, 0] - one[bk, w, d]) / one[bk, w, 0])
            for bk in books for w in windows for d in (1, 2)}
    verdict = {"share_of_d0_net_lost": loss, "flag_R200_optimistic": bool(loss["A_in_sample_d1"] >= 0.25),
               "linear_guess_12min_A_in_sample": 0.2 * loss["A_in_sample_d1"]}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    pd.set_option("display.width", 250)
    log("\n" + df.round(3).to_string(index=False))
    log(json.dumps(verdict, indent=1))


if __name__ == "__main__":
    main()
