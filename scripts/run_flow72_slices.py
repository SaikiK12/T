"""flow72_v2 (R197): the three 72 h flow cells as overlapping slices, as set out in experiments/flow72_v2/PREREG.md."""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, events, prereg, research, slices  # noqa: E402

LANE = ROOT / "experiments" / "flow72_v2"
OUT = LANE / "results"
START, DISC_END, END = "2021-01-01", "2024-01-01", "2025-07-01"
CELLS = (("flow:top_vs_crowd/xs8", 0), ("flow:taker[24]/xs8", 0), ("flow:taker[4]/xs8", 0))
HOLD, CMULTS = 72, (1.0, 2.0, 3.0)
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    OUT.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    rd = data.ROOT / "research"
    fb = np.load(rd / "bins_flow.npy", mmap_mode="r")
    fn = json.loads((rd / "meta_flow.json").read_text())["names"]
    t0, td, t1 = (research.row_of(u.p, d) for d in (START, DISC_END, END))
    assert t1 <= u.holdout_row
    inds = {n.split(":")[1]: (np.asarray(fb[fn.index(n), :t1]) == b) & u.elig[:t1] for n, b in CELLS}
    books = {**{k: [v] for k, v in inds.items()}, "combined": list(inds.values())}
    btc = u.p.symbols.index("BTCUSDT")
    c_btc = u.p["close"][t0:t1 + 1:24, btc].astype(np.float64)
    r_btc = c_btc[1:] / c_btc[:-1] - 1
    years = pd.to_datetime(u.p.t[t0:t1:24], unit="ms", utc=True).year.values
    split = np.where(np.arange(len(years)) < (td - t0) // 24, "disc", "val")
    rows, keep = [], {}
    for name, parts in books.items():
        K = float(np.mean([p[t0:td].sum(axis=1).mean() for p in parts]) * len(parts))
        unit = 1.0 / (HOLD * K)
        for hedge in (True, False):
            for cm in CMULTS:
                outs = [slices.book(p, u.ret, u.elig, u.cmat, HOLD, unit, t0, t1, side=-1, hedge=hedge, cmult=cm)
                        for p in parts]
                o = {k: sum(x[k] for x in outs) for k in outs[0]}
                n = o["daily"]
                D = len(n)
                day = lambda x: x[: D * 24].reshape(D, 24).sum(axis=1)
                ok = np.isfinite(r_btc[:D])
                r = {"book": name, "hedge": hedge, "cmult": cm, "K": K, **events.summary(n),
                     "beta_btc": float(np.polyfit(r_btc[:D][ok], n[ok], 1)[0]),
                     "gross_exposure": float(o["gross_exposure"].mean()), "net_exposure": float(o["net_exposure"].mean())}
                for k in ("gross", "cost", "hedge", "hedge_cost"):
                    r[f"{k}_ann"] = float(day(o[k]).mean() * 365)
                for s in ("disc", "val"):
                    r[f"{s}_ann"] = float(n[split[:D] == s].mean() * 365)
                    r[f"{s}_t"] = events.summary(n[split[:D] == s]).get("t_nw", np.nan)
                for y in np.unique(years):
                    r[f"y{y}"] = float(n[years[:D] == y].sum())
                rows.append(r)
                keep[f"{name}_h{int(hedge)}_c{int(cm)}"] = n
                log(f"{name} hedge {hedge} cmult {cm}: ann {r.get('ann', np.nan):+.3f} t {r.get('t_nw', np.nan):+.2f}")
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "books.csv", index=False)
    np.savez_compressed(OUT / "daily.npz", **keep)
    log("\n" + df.round(3).to_string(index=False))
    pr = df[(df.book == "combined") & df.hedge].set_index("cmult")
    ycols = [c for c in pr if c.startswith("y")]
    passed = bool(pr.loc[1.0, "t_nw"] >= 3 and (pr.loc[1.0, ycols] > 0).sum() >= 4 and pr.loc[2.0, "ann"] > 0)
    (OUT / "verdict.json").write_text(json.dumps({"pass": passed}, indent=1))
    log("PASS" if passed else "NULL")


if __name__ == "__main__":
    main()
