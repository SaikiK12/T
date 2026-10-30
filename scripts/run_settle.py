"""settle_v1 (R223): hold across one funding settlement to collect an extreme rate, as set out in
experiments/settle_v1/PREREG.md."""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, events, panel, prereg, research  # noqa: E402

LANE = ROOT / "experiments" / "settle_v1"
START, VAL, HOLD_OUT, END = "2021-01-01", "2024-01-01", "2025-07-01", "2026-10-01"
TH = 0.0020
VARIANTS = {"LONG_NEG": 1, "SHORT_POS": -1}
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def settlements(sym, t0, T):
    """(row, interval_h, rate) of the contract's settlements on the grid, sorted by row."""
    p = data.ROOT / "fundingRate" / f"{sym}.parquet"
    if not p.exists():
        return None
    d = pd.read_parquet(p)
    row = ((d.t.values - t0) // panel.HOUR).astype(np.int64)
    ok = (row >= 0) & (row < T)
    d = pd.DataFrame({"row": row[ok], "iv": d.interval_h.values[ok], "rate": d.rate.values[ok]})
    return d.drop_duplicates("row", keep="last").sort_values("row").reset_index(drop=True)


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    t0, tv, th, t1 = (research.row_of(u.p, d) for d in (START, VAL, HOLD_OUT, END))
    T = t1
    syms = list(u.p.symbols)
    tf = set(json.loads((ROOT / "experiments" / "venue_gap_v1" / "results" / "tradfi_symbols.json").read_text()))
    close = np.asarray(u.p["close"][:T], np.float64)
    ret = np.asarray(u.ret[:T], np.float64)
    rank, cmat = np.asarray(u.rank[:T]), np.asarray(u.cmat[:T], np.float64)
    elig = np.asarray(u.elig[:T]) & np.array([s not in tf for s in syms])[None, :]
    with np.errstate(invalid="ignore"):
        uni = np.nanmean(np.where(elig, ret, np.nan), axis=1)  # equal-weight eligible crypto, per row
    uni = np.nan_to_num(uni)
    ev = []
    for j, s in enumerate(syms):
        if s in tf:
            continue
        st = settlements(s, int(u.p.t[0]), T)
        if st is None or len(st) < 2:
            continue
        rows, ivs, rates = st.row.values, st.iv.values, st.rate.values
        for k in range(len(rows) - 1):
            L, I, rate = rows[k], ivs[k], rates[k]
            if I not in (4, 8) or abs(rate) < TH:
                continue
            sx = L + I
            r = sx - 2
            if r + 2 >= T or rows[k + 1] <= r:                # another settlement inside L+1..r: L is not the last
                continue
            if not (np.isfinite(close[r, j]) and np.isfinite(close[r + 2, j]) and np.isfinite(rank[r, j])):
                continue
            side = 1 if rate < 0 else -1
            fe = rates[k + 1] if rows[k + 1] == sx else 0.0     # what settled at the expected row
            gross = side * (ret[r, j] + ret[r + 1, j])
            fund = -side * fe
            o = r - I // 2                                     # off-cycle window, no settlement inside
            off = side * (ret[o, j] + ret[o + 1, j]) if o >= 0 and np.isfinite(ret[o:o + 2, j]).all() else np.nan
            ev.append({"symbol": s, "row": int(r), "interval_h": int(I), "rate": float(rate), "side": side,
                       "rank": float(rank[r, j]), "gross": float(gross), "funding": float(fund),
                       "price": float(gross - fund), "cost": float(cmat[r, j] + cmat[r + 2, j]),
                       "excess": float(gross - side * (uni[r] + uni[r + 1])),
                       "off_gross": float(off), "off_cost": float(cmat[o, j] + cmat[o + 2, j]) if o >= 0 else np.nan})
    E = pd.DataFrame(ev)
    E["month"] = pd.to_datetime(u.p.t[E.row.values], unit="ms", utc=True).strftime("%Y-%m")
    E["window"] = np.where(E.row < tv, "discovery", np.where(E.row < th, "validation", "holdout"))
    log("events by window:", E.window[E.window != "holdout"].value_counts().to_dict())

    def describe(x, name, w, uni_name):
        n1 = x.gross - x.cost
        n, mu, t = events.clustered_t(n1.values, x.month.values)
        bysym = n1.groupby(x.symbol).sum().sort_values(ascending=False)
        fc = x.funding.mean()
        off = (x.off_gross - x.off_cost).dropna()
        return {"variant": name, "window": w, "universe": uni_name, "events": int(n), "months": int(x.month.nunique()),
                "symbols": int(x.symbol.nunique()), "mean_net_bp": mu * 1e4, "t_month": t,
                "net_2x_bp": float((x.gross - 2 * x.cost).mean() * 1e4),
                "net_3x_bp": float((x.gross - 3 * x.cost).mean() * 1e4), "hit": float((n1 > 0).mean()),
                "funding_bp": fc * 1e4, "price_bp": float(x.price.mean() * 1e4), "cost_bp": float(x.cost.mean() * 1e4),
                "pass_through": float(-x.price.mean() / fc) if fc else np.nan,
                "excess_net_bp": float((x.excess - x.cost).mean() * 1e4),
                "offcycle_net_bp": float(off.mean() * 1e4) if len(off) else np.nan,
                "top5_share": float(bysym.head(5).sum() / n1.sum()) if n1.sum() != 0 else np.nan,
                "n_4h": int((x.interval_h == 4).sum()), "n_8h": int((x.interval_h == 8).sum()),
                "net_4h_bp": float(n1[x.interval_h == 4].mean() * 1e4) if (x.interval_h == 4).any() else np.nan,
                "net_8h_bp": float(n1[x.interval_h == 8].mean() * 1e4) if (x.interval_h == 8).any() else np.nan}

    rows, stage = [], {}
    for name, side in VARIANTS.items():
        passed = True
        for w, gate in (("discovery", 2.0), ("validation", 1.5), ("holdout", 2.0)):
            if not passed:
                break
            x = E[(E.side == side) & (E.window == w)]
            prim = x[x["rank"] <= 50]
            r1 = describe(prim, name, w, "rank<=50")
            rows.append(r1)
            sec = x[(x["rank"] > 50) & (x["rank"] <= 100)]
            if len(sec) >= 3:
                rows.append(describe(sec, name, w, "rank 51-100"))
            passed = bool(r1["events"] >= 3 and r1["mean_net_bp"] > 0 and r1["t_month"] >= gate)
            stage[name] = {"reached": w, "passed": passed}
            log(name, w, f"n {r1['events']} net {r1['mean_net_bp']:+.1f} bp t {r1['t_month']:+.2f} funding "
                         f"{r1['funding_bp']:+.1f} price {r1['price_bp']:+.1f} cost {r1['cost_bp']:.1f}",
                "PASS" if passed else "stop")
    df = pd.DataFrame(rows)
    df.to_csv(out / "results.csv", index=False)
    E[E.window != "holdout"].to_csv(out / "events_disc_val.csv", index=False)
    verdict = {"stages": stage, "confirmed": [k for k, v in stage.items() if v["reached"] == "holdout" and v["passed"]]}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    pd.set_option("display.width", 250)
    log("\n" + df.round(3).to_string(index=False))
    log(json.dumps(verdict, indent=1))


if __name__ == "__main__":
    main()
