"""maker_v1 (R193): limit-order entries on the replicated gross edges, as set out in experiments/maker_v1/PREREG.md."""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import atlas, events, maker, panel, prereg, research, stats  # noqa: E402

LANE = ROOT / "experiments" / "maker_v1"
OUT = LANE / "results"
SPLITS = {"discovery": ("2021-01-01", "2024-01-01"), "validation": ("2024-01-01", "2025-07-01")}
KAPPA, EXITS, FEES, CMULTS = (-1.0, 0.0, 0.25, 0.5, 1.0), (0, 1), (0.0, 2e-4), (1.0, 2.0, 3.0)
PRIMARY = (0.5, 0, 2e-4, 1.0)
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def cells_list():
    v = pd.read_csv(ROOT / "experiments" / "atlas_v1" / "results" / "replication_main+clock.csv")
    r = v[(v.kind == "real") & (v.level == "CGE(all)") & v.rep & (v.measure == "raw") & (v.tensor == "main")
          & ~v.time_only.astype(bool)]
    r = r.sort_values("t", key=abs, ascending=False).drop_duplicates(["view", "bin", "h"])
    return r.assign(side=np.sign(r.mean_bp).astype(int))[["view", "name", "bin", "h", "side", "mean_bp", "t"]]


def cell_table(o, cells, h, split, kappa, ex):
    rows = []
    D = o["gross"].shape[1]
    for fee in FEES:
        for cm in CMULTS:
            n = maker.net(o, fee, cm)
            for i in range(len(cells)):
                f = o["fills"][i].sum()
                _, mu, t = stats.newey_west_t(n[i], atlas.lag_for(h[i]))
                rows.append({"cell": i, "split": split, "kappa": kappa, "exit": ex, "fee_bp": fee * 1e4, "cmult": cm,
                             "posts": o["posts"][i].sum(), "fills": f,
                             "fill_rate": f / max(o["posts"][i].sum(), 1),
                             "gross_bp": 1e4 * o["gross"][i].sum() / max(f, 1),
                             "net_bp": 1e4 * n[i].sum() / max(f, 1), "daily_t": t, "days": D})
    return rows


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
    cells = cells_list().reset_index(drop=True)
    cells.to_csv(OUT / "cells.csv", index_label="cell")
    C = cells[["view", "bin", "h", "side"]].values.astype(np.int64)
    base = np.array([[-1, 0, h, s] for h in atlas.HORIZONS for s in (1, -1)], np.int64)
    log(f"{len(C)} cells; fires per cell computed on episode starts")
    rows, brows = [], []
    for split, (a, b) in SPLITS.items():
        t0, t1 = research.row_of(u.p, a), research.row_of(u.p, b)
        assert t1 <= u.holdout_row
        for kappa in KAPPA:
            for ex in EXITS:
                o = maker.run_cells(bins, C, close, low, high, fund, vol, u.elig, cmat, u.index, t0, t1, kappa,
                                    exit_mode=ex)
                rows += cell_table(o, C, C[:, 2], split, kappa, ex)
                ob = maker.run_cells(bins, base, close, low, high, fund, vol, u.elig, cmat, u.index, t0, t1, kappa,
                                     exit_mode=ex, episodes=False)
                for i, (_, _, h, s) in enumerate(base):
                    f = ob["fills"][i].sum()
                    brows.append({"split": split, "kappa": kappa, "exit": ex, "h": h, "side": s,
                                  "fill_rate": f / max(ob["posts"][i].sum(), 1), "gross_bp": 1e4 * ob["gross"][i].sum() / max(f, 1),
                                  "tcost_bp": 1e4 * ob["tcost"][i].sum() / max(f, 1), "legs": ob["legs"][i].sum() / max(f, 1)})
                log(f"{split} kappa {kappa} exit {ex}")
    df = pd.DataFrame(rows)
    df.to_parquet(OUT / "cells_results.parquet")
    pd.DataFrame(brows).to_csv(OUT / "baseline.csv", index=False)

    # share of cells with a positive per-trade net, taker vs maker
    share = df[df.fills >= 30].groupby(["split", "kappa", "exit", "fee_bp", "cmult"]).net_bp.agg(
        cells="size", positive=lambda x: (x > 0).mean(), median_bp="median").reset_index()
    share.to_csv(OUT / "share_positive.csv", index=False)
    log("\n" + share[(share.cmult == 1) & (share.exit == 0)].round(3).to_string(index=False))

    # selection on discovery, book on validation
    k, ex, fee, cm = PRIMARY
    d = df[(df.split == "discovery") & (df.kappa == k) & (df.exit == ex) & (df.fee_bp == fee * 1e4) & (df.cmult == cm)]
    sel = d[(d.daily_t >= 3) & (d.net_bp > 0)].sort_values("daily_t", ascending=False)
    log(f"selected on discovery: {len(sel)} cells")
    sel_cells = C[sel.cell.values]
    cells.loc[sel.cell.values].assign(disc_t=sel.daily_t.values).to_csv(OUT / "selected.csv", index_label="cell")
    out, series = [], {}
    for split, (a, b) in SPLITS.items():
        t0, t1 = research.row_of(u.p, a), research.row_of(u.p, b)
        years = pd.to_datetime(u.p.t[t0:t1:24], unit="ms", utc=True).year.values
        for mode, kap in (("maker", k), ("taker", -1.0)):
            if len(sel_cells) == 0:
                continue
            o = maker.book(bins, sel_cells, close, low, high, fund, vol, u.elig, cmat, u.index, t0, t1, kap,
                           exit_mode=ex)
            for fee_ in FEES:
                for cm_ in CMULTS:
                    n = o["gross"] - cm_ * o["tcost"] - fee_ * o["legs"]
                    r = {"split": split, "entry": mode, "fee_bp": fee_ * 1e4, "cmult": cm_,
                         "gross_ann": o["gross"].mean() * 365, "avg_open": o["n_open"].mean(),
                         "conflicts": o["conflicts"], **events.summary(n)}
                    for y in np.unique(years):
                        r[f"y{y}"] = float(n[years == y].sum())
                    out.append(r)
                    if (fee_, cm_) == (fee, cm):
                        series[f"{split}_{mode}"] = n
    book = pd.DataFrame(out)
    book.to_csv(OUT / "book.csv", index=False)
    np.savez_compressed(OUT / "book_daily.npz", **series)
    log("\n" + book[(book.cmult == 1)].round(4).to_string(index=False))
    pv = book[(book.split == "validation") & (book.entry == "maker") & (book.fee_bp == 2) & (book.cmult == 1)]
    verdict = "SIGNAL" if len(pv) and pv.t_nw.iloc[0] >= 2 and pv.ann.iloc[0] > 0 else "NULL"
    (OUT / "verdict.json").write_text(json.dumps({"selected": int(len(sel)), "verdict": verdict}, indent=1))
    log("verdict", verdict)


if __name__ == "__main__":
    main()
