"""listings_holdout (R189): one-shot holdout test, as set out in experiments/listings_holdout/PREREG.md."""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import engine, events, panel, prereg, research  # noqa: E402

LANE = ROOT / "experiments" / "listings_holdout"
START, LAST, END = "2025-07-01", "2026-09-01", "2026-09-30"
DELAY, VOL, STOP = 24, 1e7, 0.30
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def stopped(ret, bench, ev, delay, hold, stop):
    """Excess return of a short with a stop: exit at the first hourly close where the cumulative excess gain of the
    coin (the short's loss) reaches `stop`."""
    out = np.full(len(ev), np.nan)
    for i, (s, r) in enumerate(ev):
        a, b = r + delay, r + delay + hold
        if b > len(ret) or np.isnan(ret[a, s]):
            continue
        path = np.cumsum(np.nan_to_num(ret[a:b, s]) - np.nan_to_num(bench[a:b]))
        hit = np.flatnonzero(path >= stop)
        out[i] = path[hit[0]] if len(hit) else path[-1]
    return out


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    p = panel.load_panel()
    live = np.isfinite(p["close"])
    keep = np.flatnonzero(live.any(axis=0))
    p = p.columns(keep)
    live = live[:, keep]
    ret = engine.forward_returns(p["close"], p["fund_event"])
    rank = panel.liquidity_rank(p, 24 * 30)
    cost = engine.cost_matrix(rank)
    with np.errstate(invalid="ignore"):
        mkt = np.nanmean(np.where(rank <= 50, ret, np.nan), axis=1)
    vol24 = pd.DataFrame(np.nan_to_num(p["quote_volume"])).rolling(24, min_periods=1).sum().values
    first = np.argmax(live, axis=0)
    a, z, end = (research.row_of(p, d) for d in (START, LAST, END))
    T = ret.shape[0]
    ev = [(s, int(first[s])) for s in range(p.S) if a <= first[s] < z and first[s] + DELAY < T
          and vol24[first[s] + DELAY, s] >= VOL]
    log(f"{len(ev)} holdout listings pass the volume filter")
    res = {}
    for h in (7, 14, 30):
        x, b = events.event_returns(ret, ev, DELAY, 24 * h, mkt, end=end)
        exc = x - b
        c = np.array([4 * cost[r + DELAY, s] for s, r in ev])
        net = -exc - c
        mon = pd.to_datetime(p.t[[r for _, r in ev]], unit="ms", utc=True).strftime("%Y-%m")
        n, mu, t = events.clustered_t(net, mon)
        ok = np.isfinite(exc)
        res[f"hold{h}"] = {"events": n, "mean_net_short": mu, "t_cl": t, "median_exc": float(np.nanmedian(exc)),
                           "share_neg": float((exc[ok] < 0).mean()), "max_exc": float(np.nanmax(exc)),
                           "min_exc": float(np.nanmin(exc))}
        if h == 7:
            nd, gd, no = events.book(ret, ev, DELAY, 24 * h, -1, mkt, cost, start=a, end=end)
            res["book_hold7"] = {**events.summary(nd), "net_total": float(nd.sum()), "gross_total": float(gd.sum()),
                                 "avg_open": float(no.mean())}
            s = stopped(ret, mkt, ev, DELAY, 24 * h, STOP)
            _, mu_s, t_s = events.clustered_t(-s - c, mon)
            res["hold7_stop30"] = {"mean_net_short": mu_s, "t_cl": t_s, "stops_hit": int(np.nansum(s >= STOP))}
    p7 = res["hold7"]
    verdict = "CONFIRMED" if (p7["mean_net_short"] > 0 and p7["t_cl"] >= 2 and res["book_hold7"]["net_total"] > 0) \
        else "NOT CONFIRMED"
    res["verdict"] = verdict
    (out / "holdout.json").write_text(json.dumps(res, indent=1, default=float))
    log(json.dumps(res, indent=1, default=float))
    log("verdict:", verdict)


if __name__ == "__main__":
    main()
