"""weekendlink_v1 (R244): BTC's weekend move sets long/short on QQQ and SPY for the first session of the week, as set
out in experiments/weekendlink_v1/PREREG.md.

usage: python scripts/run_weekendlink.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import data, prereg  # noqa: E402
import run_fxindex as fx  # noqa: E402

LANE = ROOT / "experiments" / "weekendlink_v1"
WINDOWS = (("discovery", "2020-01-01", "2023-12-31"), ("validation", "2024-01-01", "2025-06-30"))
COST = 1e-4
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def btc_at(close_by_end, day, hour):
    """BTC close at `hour`:00 New York on `day` (the hourly bar ending then), or NaN."""
    ts = pd.Timestamp(f"{day.date()} {hour:02d}:00", tz="America/New_York").tz_convert("UTC")
    return close_by_end.get(ts, np.nan)


def tstat(x):
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 2 and x.std() > 0 else np.nan


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    p = data.ROOT / "klines_1h" / "BTCUSDT.parquet"
    k = pd.read_parquet(p)
    fx.SHAS["BTCUSDT_klines_1h"] = prereg.sha256_file(p)
    close_by_end = pd.Series(k["close"].values.astype(float),
                             index=pd.to_datetime(k["t"].values + 3_600_000, unit="ms", utc=True)).to_dict()
    rows, stage, extra = [], {}, {}
    for sym in ("QQQ", "SPY"):
        d = fx.etf(sym)
        d["gap"] = d.o / d.c.shift(1) - 1
        iso = d.index.isocalendar()
        wk = (iso.year * 100 + iso.week).values
        first = np.r_[False, wk[1:] != wk[:-1]]
        prev = d.index[np.r_[0, np.arange(len(d) - 1)]]
        rec = []
        for i in np.flatnonzero(first):
            a, b = btc_at(close_by_end, prev[i], 16), btc_at(close_by_end, d.index[i], 9)
            rec.append((d.index[i], np.log(b / a) if a > 0 and b > 0 else np.nan, d.oc.iloc[i], d.gap.iloc[i]))
        f = pd.DataFrame(rec, columns=["day", "btc", "session", "gap"]).set_index("day").dropna()
        name = f"WKND-{sym}"
        passed = True
        for w, a, b in WINDOWS:
            if not passed:
                break
            x = f[(f.index >= a) & (f.index <= b)]
            sg = np.sign(x.btc.values)
            res = {}
            for cm in (1.0, 2.0, 3.0):
                net = sg * x.session.values - 2 * COST * cm * (sg != 0)
                yrs = x.index.year
                res[cm] = {"strategy": name, "window": w, "cmult": cm, "trades": int((sg != 0).sum()),
                           "mean_bp": float(net.mean() * 1e4), "t": tstat(net), "hit": float((net > 0).mean()),
                           "bh_session_mean_bp": float(x.session.mean() * 1e4), "bh_session_t": tstat(x.session.values),
                           "gap_slope": float(np.polyfit(x.btc, x.gap, 1)[0]),
                           "gap_corr": float(np.corrcoef(x.btc, x.gap)[0, 1]),
                           "session_slope": float(np.polyfit(x.btc, x.session, 1)[0]),
                           "session_corr": float(np.corrcoef(x.btc, x.session)[0, 1]),
                           "by_year_bp": {int(y): float(net[yrs == y].mean() * 1e4) for y in np.unique(yrs)}}
                rows.append(res[cm])
            r1 = res[1.0]
            passed = (r1["mean_bp"] > 0 and r1["t"] >= 2 and res[2.0]["mean_bp"] > 0) if w == "discovery" else \
                (r1["mean_bp"] > 0 and r1["t"] >= 1.5)
            stage[name] = {"reached": w, "passed": bool(passed)}
            log(name, w, f"{r1['trades']} trades, {r1['mean_bp']:+.2f} bp/trade t {r1['t']:+.2f} "
                f"(2x {res[2.0]['mean_bp']:+.2f}), hit {r1['hit']:.2f}; gap corr {r1['gap_corr']:+.2f}, "
                f"session corr {r1['session_corr']:+.2f}", "PASS" if passed else "stop")
        extra[f"{sym}_btc_missing"] = int(len(rec) - len(f))
    df = pd.DataFrame(rows)
    df.drop(columns="by_year_bp").to_csv(out / "strategies.csv", index=False)
    verdict = {"stages": stage, "data_sha256": fx.SHAS, **extra,
               "by_year_1x": {f"{x.strategy}/{x.window}": x.by_year_bp for x in df[df.cmult == 1.0].itertuples()},
               "validation_passers": [k for k, v in stage.items() if v["reached"] == "validation" and v["passed"]]}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    pd.set_option("display.width", 250)
    log("\n" + df.drop(columns="by_year_bp").round(4).to_string(index=False))
    log(json.dumps({k: verdict[k] for k in ("stages", "validation_passers")}, indent=1))


if __name__ == "__main__":
    main()
