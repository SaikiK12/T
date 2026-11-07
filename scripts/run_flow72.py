"""flow72_v1 (R196): short the coins with heavy taker selling / top traders short vs the crowd, 72 h, universe-hedged,
as set out in experiments/flow72_v1/PREREG.md."""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, events, maker, pack, panel, prereg, research  # noqa: E402

LANE = ROOT / "experiments" / "flow72_v1"
OUT = LANE / "results"
START, END = "2021-01-01", "2025-07-01"
CELLS = (("flow:top_vs_crowd/xs8", 0), ("flow:taker[24]/xs8", 0), ("flow:taker[4]/xs8", 0))
ENTRY = {"market": -1.0, "limit": 0.5}
HEDGE = ("universe", "btc", "none")
SLOTS, CMULTS = (10, 20), (1.0, 2.0, 3.0)
PRIMARY = ("market", "universe", 20)
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    OUT.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    rd = data.ROOT / "research"
    fbins = np.load(rd / "bins_flow.npy", mmap_mode="r")
    fnames = json.loads((rd / "meta_flow.json").read_text())["names"]
    C = np.array([[fnames.index(n), b, 72, -1] for n, b in CELLS], np.int64)
    p = panel.load_panel(symbols=u.p.symbols)
    assert np.array_equal(p.t, u.p.t)
    close, low, high = (np.ascontiguousarray(p[k], np.float64) for k in ("close", "low", "high"))
    fund = np.ascontiguousarray(p["fund_event"], np.float64)
    del p
    vol = maker.trailing_vol(close)
    cmat = u.cmat.astype(np.float64)
    t0, t1 = research.row_of(u.p, START), research.row_of(u.p, END)
    assert t1 <= u.holdout_row
    btc = u.p.symbols.index("BTCUSDT")
    years = pd.to_datetime(u.p.t[t0:t1:24], unit="ms", utc=True).year.values
    c_btc = close[t0:t1 + 1:24, btc]
    r_btc = c_btc[1:] / c_btc[:-1] - 1
    hcol = {"universe": -2, "btc": btc, "none": -1}
    rows, keep = [], {}
    for entry, kappa in ENTRY.items():
        for hedge in HEDGE:
            for slots in SLOTS:
                for cm in CMULTS:
                    o = pack.run(fbins, C, close, low, high, fund, vol, u.elig, cmat, u.index, t0, t1, kappa=kappa,
                                 fee=2e-4, cmult=cm, slots=slots, hedge_col=hcol[hedge])
                    n = o["daily"]
                    D = len(n)
                    day = lambda x: x[: D * 24].reshape(D, 24).sum(axis=1)
                    ok = np.isfinite(r_btc[:D])
                    r = {"entry": entry, "hedge": hedge, "slots": slots, "cmult": cm, **events.summary(n),
                         "beta_btc": float(np.polyfit(r_btc[:D][ok], n[ok], 1)[0]),
                         "exposure": float(o["exposure"].mean()), "n_open": float(o["n_open"].mean()),
                         "fills_day": float(o["fills"].sum() / D)}
                    for k in ("gross", "entry_cost", "exit_cost", "hedge", "hedge_cost"):
                        r[f"{k}_ann"] = float(day(o[k]).mean() * 365)
                    for y in np.unique(years):
                        r[f"y{y}"] = float(n[years[:D] == y].sum())
                    rows.append(r)
                    keep[f"{entry}_{hedge}_s{slots}_c{int(cm)}"] = n
                    log(f"{entry} {hedge} slots {slots} cmult {cm}: ann {r.get('ann', np.nan):+.3f} "
                        f"t {r.get('t_nw', np.nan):+.2f}")
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "books.csv", index=False)
    np.savez_compressed(OUT / "daily.npz", **keep)
    log("\n" + df[df.cmult == 1].round(3).to_string(index=False))
    pr = df[(df.entry == PRIMARY[0]) & (df.hedge == PRIMARY[1]) & (df.slots == PRIMARY[2])].set_index("cmult")
    ycols = [c for c in pr if c.startswith("y")]
    passed = bool(pr.loc[1.0, "t_nw"] >= 3 and (pr.loc[1.0, ycols] > 0).sum() >= 4 and pr.loc[2.0, "ann"] > 0)
    (OUT / "verdict.json").write_text(json.dumps({"pass": passed}, indent=1))
    log("PASS" if passed else "NULL")


if __name__ == "__main__":
    main()
