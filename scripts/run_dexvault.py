"""dexvault_v1 (R446, M505): a deposit in each of two public liquidity vaults on perp DEXes that do not exclude France,
Hyperliquid's HLP and Lighter's LLP, read as a return on capital against the 4% hurdle. Rule, costs, windows and
decision are in experiments/dexvault_v1/PREREG.md.

Data: the `vaults/` folder of the data branch claude/okx-xperp-data (scripts/record_dex_vaults.py). The report and the
gate-1 decision are R441's (the frozen scripts/run_xperp_carry.py). Paper only: it reads files and writes results; no
deposit, no order.

usage: python scripts/run_dexvault.py --data DIR --window gate0|forward [--until YYYY-MM-DD] [--out DIR] [--status]
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
_spec = importlib.util.spec_from_file_location("run_xperp_carry", ROOT / "scripts" / "run_xperp_carry.py")
rx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rx)
from lab.stats import newey_west_t  # noqa: E402

LANE = ROOT / "experiments" / "dexvault_v1"
DAY = rx.DAY
# ---- the frozen rule (PREREG "Rule"); tests/test_run_dexvault.py checks these against the PREREG text
BOOKS = ("hlp", "llp")
HURDLE_ANN = rx.HURDLE_ANN                    # 4%
COST_ANN = 0.0010                             # one deposit-and-withdrawal round trip a year, 10 bp of capital, at 1x
GATE0_LAG = {"hlp": 4, "llp": 10}             # NW lags of gate 0: HLP's periods are about a week, LLP's a day
FALLBACK = ("week", "month", "allTime")       # HLP windows tried in turn for a forward day
WINDOWS = {"gate0": ("2025-01-01", "2026-11-10"), "forward": ("2026-11-11", None)}
LOOKS = {90: "2027-02-08", 180: "2027-05-09"}
DAILY_COLS = ["day", "held", "forced", "missing", "funding", "price", "gross", "net_1x", "net_2x", "net_3x"]


# ---------------------------------------------------------------- data
def llp_prices(data):
    """Series of LLP share prices by stamp (ms), one per UTC day (the day's last stamp)."""
    sp = rx.read_dir(Path(data) / "vaults" / "llp" / "share_prices")
    if not len(sp):
        return pd.Series(dtype=float)
    sp = sp.drop_duplicates("ts").sort_values("ts")
    sp["day"] = [rx.day_label(t) for t in sp.ts]
    sp = sp.groupby("day").tail(1)
    return pd.Series(sp.share_price.astype(float).to_numpy(), index=sp.ts.astype(np.int64).to_numpy())


def hlp_snaps(data):
    """[(fetch ms, DataFrame of window, ts, account_value, pnl)], oldest first."""
    out = []
    for p in sorted((Path(data) / "vaults" / "hlp" / "snap").glob("*.csv"), key=lambda p: int(p.stem)):
        out.append((int(p.stem), pd.read_csv(p)))
    return out


# ---------------------------------------------------------------- periods
def llp_periods(prices, start, end):
    """[(day, days spanned, return)] for each stamp whose UTC day is in [start, end], against the stamp before it."""
    ts, v = prices.index.to_numpy(), prices.to_numpy()
    out = []
    for i in range(1, len(ts)):
        d = rx.day_label(ts[i])
        if start <= d <= end:
            out.append((d, (ts[i] - ts[i - 1]) / DAY, v[i] / v[i - 1] - 1))
    return out


def hlp_gate0_periods(snaps, start, end):
    """Periods between consecutive points of the first snapshot's allTime window, by the UTC day of the later point."""
    if not snaps:
        return []
    w = snaps[0][1]
    w = w[w.window == "allTime"].sort_values("ts")
    t, av, pnl = w.ts.to_numpy(np.int64), w.account_value.to_numpy(float), w.pnl.to_numpy(float)
    out = []
    for i in range(1, len(t)):
        d = rx.day_label(t[i])
        if start <= d <= end and av[i - 1] > 0:
            out.append((d, (t[i] - t[i - 1]) / DAY, (pnl[i] - pnl[i - 1]) / av[i - 1]))
    return out


def hlp_day(snaps, d_ms):
    """Return over (d_ms - 1 day, d_ms] from the earliest snapshot fetched at or after d_ms whose window holds a point
    at or before d_ms - 1 day; windows tried in FALLBACK order. None if no snapshot covers the day."""
    a_ms = d_ms - DAY
    for win in FALLBACK:
        for fetched, df in snaps:
            if fetched < d_ms:
                continue
            w = df[df.window == win].sort_values("ts")
            before_a, before_b = w[w.ts <= a_ms], w[w.ts <= d_ms]
            if not len(before_a) or not len(before_b):
                continue
            pa, pb = before_a.iloc[-1], before_b.iloc[-1]
            if float(pa.account_value) <= 0:
                continue
            return (float(pb.pnl) - float(pa.pnl)) / float(pa.account_value)
    return None


# ---------------------------------------------------------------- reads
def gate0_summary(periods, lag):
    """Annualized net and excess over the hurdle at 1x/2x/3x, with NW t on the per-period excess."""
    if not periods:
        return {"periods": 0, "1x": {"net_ann": None, "excess_ann": None, "nw_t_excess": float("nan")}}
    span = np.array([p[1] for p in periods])
    r = np.array([p[2] for p in periods])
    out = {"periods": len(periods), "first": periods[0][0], "last": periods[-1][0], "years": float(span.sum() / 365),
           "median_period_days": float(np.median(span))}
    for m in (1, 2, 3):
        net = r - m * COST_ANN * span / 365
        ex = net - HURDLE_ANN * span / 365
        _, _, t = newey_west_t(ex, lag)
        out[f"{m}x"] = {"net_ann": float(net.sum() / span.sum() * 365),
                        "excess_ann": float(ex.sum() / span.sum() * 365), "nw_t_excess": t}
    cum = np.cumsum(r - COST_ANN * span / 365)
    out["max_dd"] = float((cum - np.maximum.accumulate(np.maximum(cum, 0))).min())
    out["worst_period"] = float(r.min())
    out["worst_period_day"] = periods[int(r.argmin())][0]
    out["sd_period"] = float(np.std(r - HURDLE_ANN * span / 365, ddof=1)) if len(r) > 1 else float("nan")
    return out


def forward_daily(data, book, start, end):
    """One row per UTC day in [start, end]; a day with no return is booked at 0 and counted as missing."""
    rows = []
    if book == "llp":
        got = {d: r for d, _, r in llp_periods(llp_prices(data), start, end)}
    else:
        snaps = hlp_snaps(data)
    for d in range(rx.ms(start), rx.ms(end) + DAY, DAY):
        day = rx.day_label(d)
        r = got.get(day) if book == "llp" else hlp_day(snaps, d + DAY)   # HLP: the interval ending at day's end
        miss = r is None
        r = 0.0 if miss else r
        c = COST_ANN / 365
        rows.append({"day": day, "held": 1, "forced": 0, "missing": int(miss), "funding": r, "price": 0.0, "gross": r,
                     "net_1x": r - c, "net_2x": r - 2 * c, "net_3x": r - 3 * c})
    return pd.DataFrame(rows, columns=DAILY_COLS)


def decide_gate0(s):
    """Gate 0 decides only a stop, book by book."""
    e1 = s["1x"]["excess_ann"]
    return "NULL (stop)" if e1 is None or e1 < 0 else "CONTINUE to gate 1"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--window", choices=sorted(WINDOWS), required=True)
    ap.add_argument("--until", help="last day of a forward read (default: the last day the data covers)")
    ap.add_argument("--status", action="store_true", help="forward progress read: no decision")
    ap.add_argument("--out")
    a = ap.parse_args()
    from lab import prereg
    prereg.verify(LANE / "PREREG.md")
    pinned = rx.check_inputs(LANE / "PREREG.md")
    if a.window == "gate0" and rx.data_head(a.data) != pinned:
        raise SystemExit(f"gate 0 reads the data branch at {pinned} only; {a.data} is at {rx.data_head(a.data)}")
    start, end = WINDOWS[a.window]
    out = Path(a.out) if a.out else LANE / "results" / (a.window + ("_status" if a.status else ""))
    out.mkdir(parents=True, exist_ok=True)
    rep = {"window": a.window, "start": start}
    if a.window == "gate0":
        rep["end"] = end
        per = {"hlp": hlp_gate0_periods(hlp_snaps(a.data), start, end),
               "llp": llp_periods(llp_prices(a.data), start, end)}
        for b in BOOKS:
            s = gate0_summary(per[b], GATE0_LAG[b])
            s["decision"] = decide_gate0(s)
            rep[b] = s
            pd.DataFrame(per[b], columns=["day", "days", "return"]).to_csv(out / f"{b}_periods.csv", index=False,
                                                                          lineterminator="\n")
    else:
        if a.until:
            end = a.until
        else:
            last = [rx.day_label(t) for t in llp_prices(a.data).index[-1:]]
            snaps = hlp_snaps(a.data)
            if snaps:
                last.append(rx.day_label(snaps[-1][0] - DAY))
            end = min(last) if last else start           # the last day both books can cover
        rep["end"] = end
        for b in BOOKS:
            daily = forward_daily(a.data, b, start, end)
            s = rx.summary(daily)
            s["missing_days"] = int(daily.missing.sum())
            if not a.status:
                n = s["days"]
                look = max((k for k in LOOKS if n >= k), default=None)
                s["decision"] = rx.decide(s, look) if look else f"no look reached ({n} scored days)"
            rep[b] = s
            daily.to_csv(out / f"{b}_daily.csv", index=False, lineterminator="\n")
    (out / "report.json").write_text(json.dumps(rep, indent=1, default=float) + "\n")
    print(json.dumps(rep, indent=1, default=float))


if __name__ == "__main__":
    main()
