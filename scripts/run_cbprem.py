"""cbprem_v1 (R210): the Coinbase premium as a BTC/ETH signal, as set out in experiments/cbprem_v1/PREREG.md."""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, events, prereg, research, slices, stats  # noqa: E402

LANE = ROOT / "experiments" / "cbprem_v1"
START, HOLD_OUT, END = "2021-01-01", "2025-07-01", "2026-10-01"
COINS = {"BTC": ("BTC-USD", "BTCUSDT"), "ETH": ("ETH-USD", "ETHUSDT")}
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def on_clock(path, t, col="close"):
    df = pd.read_parquet(path)
    return pd.Series(df[col].values, index=df["t"].values).reindex(t).values.astype(np.float64)


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    t = u.p.t
    t0, th, t1 = (research.row_of(u.p, d) for d in (START, HOLD_OUT, END))
    t1 -= (t1 - t0) % 24
    th -= (th - t0) % 24
    D, d_ho = (t1 - t0) // 24, (th - t0) // 24
    usdt = on_clock(data.ROOT / "coinbase" / "USDT-USD.parquet", t)
    res, keep, desc = [], {}, {}
    for cur, (cb, sym) in COINS.items():
        j = u.p.symbols.index(sym)
        prem = on_clock(data.ROOT / "coinbase" / f"{cb}.parquet", t) / (
            on_clock(data.ROOT / "binance_spot" / f"{sym}.parquet", t) * usdt) - 1
        s = pd.Series(prem)
        roll = s.rolling(720, min_periods=600)
        z = ((s - roll.mean()) / roll.std()).values
        with np.errstate(invalid="ignore"):
            up, dn = z > 2, z < -2
        ret = u.ret[:, [j]]
        close = u.p["close"][:, j].astype(np.float64)
        fwd = {h: np.concatenate([close[h:] / close[:-h] - 1, np.full(h, np.nan)]) for h in (1, 4, 24)}
        same = np.concatenate([[np.nan], close[1:] / close[:-1] - 1])            # the bar ending at row t's close
        dprem = np.diff(prem, prepend=np.nan)
        ok = np.isfinite(dprem) & np.isfinite(same)
        ins = slice(t0, th)
        d = {"hours_with_prem": int(np.isfinite(prem[t0:t1]).sum()), "up_hours_in": int(up[ins].sum()),
             "dn_hours_in": int(dn[ins].sum()), "up_hours_ho": int(up[th:t1].sum()), "dn_hours_ho": int(dn[th:t1].sum()),
             "corr_dprem_same_hour_ret": float(np.corrcoef(dprem[ok], same[ok])[0, 1])}
        for h, f in fwd.items():
            for name, m in (("up", up), ("dn", dn)):
                for win, sl in (("in", ins), ("ho", slice(th, t1))):
                    x = f[sl][m[sl] & np.isfinite(f[sl])]
                    d[f"fwd{h}h_{name}_{win}_bp"] = float(x.mean() * 1e4) if len(x) else None
        desc[cur] = d
        for h in (24, 4):
            P = (slices.positions(up[:, None], h, t0, t1, 1.0 / h, 1)
                 + slices.positions(dn[:, None], h, t0, t1, 1.0 / h, -1))
            for cm in (1.0, 2.0, 3.0):
                o = slices.run(P, ret, u.elig[:, [j]], u.cmat[:, [j]], t0, t1, hedge=False, cmult=cm)
                n = o["daily"]
                for win, sl in (("insample", slice(0, d_ho)), ("holdout", slice(d_ho, D))):
                    x = n[sl]
                    res.append({"coin": cur, "h": h, "cmult": cm, "window": win, "days": len(x),
                                "days_active": int((np.abs(o["net_exposure"][: D * 24].reshape(D, 24)).sum(1)[sl] > 0)
                                                   .sum()), "total": float(x.sum()), "mean_bp_day": float(x.mean() * 1e4),
                                "t_nw10": float(stats.newey_west_t(x, 10)[2]),
                                **{k: v for k, v in events.summary(x).items() if k != "t_nw"}})
                if cm == 1.0:
                    keep[f"{cur}_h{h}"] = n
    df = pd.DataFrame(res)
    df.to_csv(out / "results.csv", index=False)
    np.savez_compressed(out / "daily.npz", **keep)
    days = pd.to_datetime(t[t0:t1:24], unit="ms", utc=True)
    p = df[(df.coin == "BTC") & (df.h == 24) & (df.cmult == 1.0)].set_index("window")
    yr = pd.Series(keep["BTC_h24"], index=days).groupby(days.year).sum()
    verdict = {"insample_mean_bp_day": float(p.loc["insample", "mean_bp_day"]),
               "insample_t_nw10": float(p.loc["insample", "t_nw10"]),
               "holdout_mean_bp_day": float(p.loc["holdout", "mean_bp_day"]),
               "confirmed": bool(p.loc["insample", "mean_bp_day"] > 0 and p.loc["insample", "t_nw10"] >= 2
                                 and p.loc["holdout", "mean_bp_day"] > 0),
               "per_year_primary": {int(k): float(v) for k, v in yr.items()}, "descriptive": desc}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    pd.set_option("display.width", 250)
    log("\n" + df.round(4).to_string(index=False))
    log(json.dumps(verdict, indent=1))


if __name__ == "__main__":
    main()
