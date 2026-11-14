"""listings_v1 (R188): returns after new perpetual listings, as set out in experiments/listings_v1/PREREG.md.

usage: python scripts/run_listings.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import engine, events, panel, prereg, research  # noqa: E402

LANE = ROOT / "experiments" / "listings_v1"
DISC = ("2021-01-15", "2024-01-01")
VAL = ("2024-01-01", "2025-06-01")
DELAYS, HOLDS, BENCH, FILTERS = (24, 72), (7, 14, 30), ("market", "btc"), (False, True)
PRIMARY = (24, 14, "market", False)
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    p = panel.load_panel()
    close = p["close"]
    live = np.isfinite(close)
    keep = np.flatnonzero(live.any(axis=0))
    p = p.columns(keep)
    close, live = p["close"], live[:, keep]
    T, S = close.shape
    ret = engine.forward_returns(close, p["fund_event"])
    rank = panel.liquidity_rank(p, 24 * 30)
    cost = engine.cost_matrix(rank)
    elig = rank <= 50
    with np.errstate(invalid="ignore"):
        mkt = np.nanmean(np.where(elig, ret, np.nan), axis=1)
    btc = ret[:, p.symbols.index("BTCUSDT")]
    vol24 = pd.DataFrame(np.nan_to_num(p["quote_volume"])).rolling(24, min_periods=1).sum().values
    hold_row = research.row_of(p, research.HOLDOUT)
    first = np.argmax(live, axis=0)
    t0 = research.row_of(p, DISC[0])
    ev = [(s, int(first[s])) for s in range(S) if first[s] >= t0 and first[s] < hold_row]
    stamp = pd.to_datetime(p.t[[r for _, r in ev]], unit="ms", utc=True)
    log(f"{len(ev)} listings from {DISC[0]} to before the holdout; per year:",
        pd.Series(stamp.year).value_counts().sort_index().to_dict())

    def split(name):
        a, b = (DISC if name == "discovery" else VAL)
        ra, rb = research.row_of(p, a), research.row_of(p, b)
        return [(s, r) for s, r in ev if ra <= r < rb]

    rows, books = [], {}
    for name in ("discovery", "validation"):
        E = split(name)
        for d in DELAYS:
            for h in HOLDS:
                for bname in BENCH:
                    bench = mkt if bname == "market" else btc
                    for filt in FILTERS:
                        EE = [(s, r) for s, r in E if r + d < T and (not filt or vol24[r + d, s] >= 1e7)]
                        x, b = events.event_returns(ret, EE, d, 24 * h, bench, end=hold_row)
                        c = np.array([2 * 2 * cost[r + d, s] for s, r in EE])          # both legs, in and out
                        exc = x - b
                        mon = pd.to_datetime(p.t[[r for _, r in EE]], unit="ms", utc=True).strftime("%Y-%m")
                        n, mu, t = events.clustered_t(exc, mon)
                        side = -1 if mu < 0 else 1
                        net = side * exc - c
                        _, mu_net, t_net = events.clustered_t(net, mon)
                        yr = pd.Series(exc).groupby(pd.to_datetime(p.t[[r for _, r in EE]], unit="ms", utc=True).year).mean()
                        ok = np.isfinite(exc)
                        rows.append({"split": name, "delay": d, "hold_d": h, "bench": bname, "vol_filter": filt,
                                     "events": n, "mean_exc": mu, "t_cl": t, "median_exc": np.nanmedian(exc),
                                     "share_neg": float((exc[ok] < 0).mean()), "max_exc": np.nanmax(exc), "min_exc": np.nanmin(exc),
                                     "side": side, "net_mean": mu_net, "net_t_cl": t_net,
                                     **{f"y{k}": v for k, v in yr.items()}})
                        if (d, h, bname, filt) == PRIMARY:
                            a, bb = (research.row_of(p, s) for s in (DISC if name == "discovery" else VAL))
                            netd, grossd, nopen = events.book(ret, EE, d, 24 * h, -1, bench, cost, start=a,
                                                              end=min(bb + 24 * (h + 1), hold_row))
                            books[name] = {**events.summary(netd), "gross_ann": grossd.mean() * 365,
                                           "avg_open": float(nopen.mean())}
                            late = [(s, r + 24 * 180) for s, r in EE if r + 24 * 180 < hold_row]
                            lx, lb = events.event_returns(ret, late, d, 24 * h, bench, end=hold_row)
                            lmon = pd.to_datetime(p.t[[r for _, r in late]], unit="ms", utc=True).strftime("%Y-%m")
                            books[name]["late_baseline"] = dict(zip(("n", "mean", "t_cl"), events.clustered_t(lx - lb, lmon)))
    df = pd.DataFrame(rows)
    df.to_csv(out / "configs.csv", index=False)
    (out / "book.json").write_text(json.dumps(books, indent=1, default=float))
    pr = df[(df.delay == PRIMARY[0]) & (df.hold_d == PRIMARY[1]) & (df.bench == PRIMARY[2]) & (df.vol_filter == PRIMARY[3])]
    log("primary:\n" + pr.round(4).to_string(index=False))
    log("book:", json.dumps(books, default=float))
    log("done")


if __name__ == "__main__":
    main()
