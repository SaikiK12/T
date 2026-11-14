"""flow72_holdout (R198): one shot of the frozen 72 h flow slice book on 2025-07-01..2026-09-30, as set out in
experiments/flow72_holdout/PREREG.md. Run once."""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, events, prereg, research, slices  # noqa: E402

LANE = ROOT / "experiments" / "flow72_holdout"
OUT = LANE / "results"
CELLS = (("flow:top_vs_crowd/xs8", 0), ("flow:taker[24]/xs8", 0), ("flow:taker[4]/xs8", 0))
HOLD, K = 72, 9.316
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def run_book(parts, u, t0, t1, cm, hedge, basket):
    outs = [slices.book(p, u.ret, u.elig, u.cmat, HOLD, 1.0 / (HOLD * K), t0, t1, side=-1, hedge=hedge, cmult=cm,
                        basket=basket) for p in parts]
    return {k: sum(x[k] for x in outs) for k in outs[0]}


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    OUT.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    rd = data.ROOT / "research"
    fb = np.load(rd / "bins_flow.npy", mmap_mode="r")
    fn = json.loads((rd / "meta_flow.json").read_text())["names"]
    inds = {n.split(":")[1]: (np.asarray(fb[fn.index(n)]) == b) & u.elig for n, b in CELLS}
    btc = u.p.symbols.index("BTCUSDT")
    top10 = u.rank <= 10
    only_btc = np.zeros_like(u.elig)
    only_btc[:, btc] = True
    periods = {"holdout": (u.holdout_row, len(u.p.t) - len(u.p.t) % 24),
               "in_sample": (0, u.holdout_row)}
    hedges = {"universe": (True, None), "none": (False, None), "top10": (True, top10), "btc": (True, only_btc)}
    rows, keep = [], {}
    for period, (t0, t1) in periods.items():
        c_btc = u.p["close"][t0:t1 + 1:24, btc].astype(np.float64)
        r_btc = np.full((t1 - t0) // 24, np.nan)
        r_btc[:len(c_btc) - 1] = c_btc[1:] / c_btc[:-1] - 1     # the last day has no next close at the data end
        days = pd.to_datetime(u.p.t[t0:t1:24], unit="ms", utc=True)
        for book, parts in {"combined": list(inds.values()), **{k: [v] for k, v in inds.items()}}.items():
            for hname, (hedge, basket) in hedges.items():
                if period == "in_sample" and (book != "combined" or hname in ("universe", "none")):
                    continue                      # in-sample reference only for the practical hedges
                if period == "holdout" and book != "combined" and hname != "universe":
                    continue
                for cm in (1.0, 2.0, 3.0):
                    o = run_book(parts, u, t0, t1, cm, hedge, basket)
                    n = o["daily"]
                    D = len(n)
                    ok = np.isfinite(r_btc[:D])
                    r = {"period": period, "book": book, "hedge": hname, "cmult": cm, "days": D,
                         "total": float(n.sum()), "mean_bp_day": float(n.mean() * 1e4), **events.summary(n),
                         "beta_btc": float(np.polyfit(r_btc[:D][ok], n[ok], 1)[0]),
                         "gross_exposure": float(o["gross_exposure"].mean())}
                    rows.append(r)
                    if cm == 1.0:
                        keep[f"{period}_{book}_{hname}"] = n
                        if period == "holdout" and book == "combined" and hname == "universe":
                            monthly = pd.Series(n, index=days[:D]).groupby(days[:D].strftime("%Y-%m")).sum()
                            monthly.to_csv(OUT / "primary_monthly.csv", header=["net"])
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "holdout.csv", index=False)
    np.savez_compressed(OUT / "daily.npz", **keep)
    log("\n" + df.round(4).to_string(index=False))
    p = df[(df.period == "holdout") & (df.book == "combined") & (df.hedge == "universe") & (df.cmult == 1.0)].iloc[0]
    confirmed = bool(p.mean_bp_day > 0 and p.t_nw >= 2)
    (OUT / "verdict.json").write_text(json.dumps({"confirmed": confirmed, "t_nw": p.t_nw, "ann": p.ann,
                                                  "total": p.total, "days": int(p.days)}, indent=1, default=float))
    log("CONFIRMED" if confirmed else "NOT CONFIRMED")
    log("monthly:\n" + pd.read_csv(OUT / "primary_monthly.csv").round(4).to_string(index=False))


if __name__ == "__main__":
    main()
