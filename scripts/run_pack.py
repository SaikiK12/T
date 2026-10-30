"""pack_v1 (R194): many maker cells in one hedged book, as set out in experiments/pack_v1/PREREG.md."""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import events, maker, pack, panel, prereg, research  # noqa: E402

LANE = ROOT / "experiments" / "pack_v1"
OUT = LANE / "results"
START, END = "2021-01-01", "2025-07-01"
SLOTS, HEDGE, CMULTS = (10, 20, 40), (False, True), (1.0, 2.0, 3.0)
PRIMARY = (20, True, 1.0)
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def select_cells():
    mk = ROOT / "experiments" / "maker_v1" / "results"
    d = pd.read_parquet(mk / "cells_results.parquet")
    d = d[(d.kappa == 1.0) & (d.exit == 0) & (d.fee_bp == 2) & (d.cmult == 1)]
    p = d.pivot_table(index="cell", columns="split", values=["net_bp", "fills"])
    ok = (p["net_bp"] > 0).all(axis=1) & (p["fills"] >= 30).all(axis=1)
    score = p["net_bp"].min(axis=1)[ok].sort_values(ascending=False)
    cells = pd.read_csv(mk / "cells.csv").set_index("cell").loc[score.index]
    return cells.assign(score_bp=score.values)


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    OUT.mkdir(parents=True, exist_ok=True)
    u, bins, _ = research.load_universe()
    p = panel.load_panel(symbols=u.p.symbols)
    assert np.array_equal(p.t, u.p.t)
    close, low, high = (np.ascontiguousarray(p[k], np.float64) for k in ("close", "low", "high"))
    fund = np.ascontiguousarray(p["fund_event"], np.float64)
    del p
    vol = maker.trailing_vol(close)
    cmat = u.cmat.astype(np.float64)
    cells = select_cells()
    cells.to_csv(OUT / "cells.csv")
    C = cells[["view", "bin", "h", "side"]].values.astype(np.int64)
    log(f"{len(C)} cells ({(C[:, 3] > 0).sum()} long), horizons {np.bincount(C[:, 2]).nonzero()[0].tolist()}")
    t0, t1 = research.row_of(u.p, START), research.row_of(u.p, END)
    assert t1 <= u.holdout_row
    btc = u.p.symbols.index("BTCUSDT")
    years = pd.to_datetime(u.p.t[t0:t1:24], unit="ms", utc=True).year.values
    c_btc = close[t0:t1 + 1:24, btc]
    r_btc = c_btc[1:] / c_btc[:-1] - 1
    rows, keep = [], {}
    for slots in SLOTS:
        for hedge in HEDGE:
            for cm in CMULTS:
                o = pack.run(bins, C, close, low, high, fund, vol, u.elig, cmat, u.index, t0, t1, kappa=1.0,
                             fee=2e-4, cmult=cm, slots=slots, hedge_col=btc if hedge else -1)
                n = o["daily"]
                D = len(n)
                day = lambda x: x[: D * 24].reshape(D, 24).sum(axis=1)
                ok = np.isfinite(r_btc[:D])
                beta = float(np.polyfit(r_btc[:D][ok], n[ok], 1)[0])
                r = {"slots": slots, "hedge": hedge, "cmult": cm, **events.summary(n), "beta_btc": beta,
                     "exposure": float(o["exposure"].mean()), "abs_exposure": float(np.abs(o["exposure"]).mean()),
                     "n_open": float(o["n_open"].mean()), "fills_day": float(o["fills"].sum() / D)}
                for k in ("gross", "entry_cost", "exit_cost", "hedge", "hedge_cost"):
                    r[f"{k}_ann"] = float(day(o[k]).mean() * 365)
                for y in np.unique(years):
                    r[f"y{y}"] = float(n[years[:D] == y].sum())
                rows.append(r)
                keep[f"s{slots}_h{int(hedge)}_c{int(cm)}"] = n
                log(f"slots {slots} hedge {hedge} cmult {cm}: ann {r.get('ann', np.nan):+.3f} t {r.get('t_nw', np.nan):+.2f}")
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "books.csv", index=False)
    np.savez_compressed(OUT / "daily.npz", **keep)
    log("\n" + df.round(3).to_string(index=False))
    pr = df[(df.slots == PRIMARY[0]) & (df.hedge == PRIMARY[1])].set_index("cmult")
    ycols = [c for c in pr if c.startswith("y")]
    passed = bool(pr.loc[1.0, "t_nw"] >= 3 and (pr.loc[1.0, ycols] > 0).sum() >= 4 and pr.loc[2.0, "ann"] > 0)
    (OUT / "verdict.json").write_text(json.dumps({"cells": int(len(C)), "pass": passed}, indent=1))
    log("PASS" if passed else "NULL")


if __name__ == "__main__":
    main()
