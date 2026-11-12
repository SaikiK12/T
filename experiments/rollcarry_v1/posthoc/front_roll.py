"""Post hoc for R478 (decides nothing): price xyz's monthly roll against the continuous front future.

On business day 10 xyz's oracle has moved to the next contract (business days 5-9), while Yahoo's continuous front
future (CL=F, NG=F, BZ=F) stays on the old one until it expires later in the month. So at the same instant
    r(day) = perp / front - 1
is about 0 before the roll (business day 4: same contract, plus the perp's premium) and about the
next-to-front spread after it (business day 10). roll = r(BD10) - r(BD4) is the roll-up the oracle passed to longs
that month, as a fraction of notional. Marks: 20:00 UTC (a 1 h and a 4 h candle boundary), the perp from R478's
held candles, the future from Yahoo 60-minute bars (bar opening 19:00 UTC).

Per R478 cycle (business day 10 to business day 10, results/cycles_<PAIR>.csv) it compares
    R478's gap / notional   (perp + US fund, the fund's own roll timing and mark noise)
with  -roll of the month that ends the cycle, and funding - roll with R478's net (both before cost and bill).
Its spread of nets across cycles is an input to the power of the forward lane M532 earned.

usage: .venv/bin/python experiments/rollcarry_v1/posthoc/front_roll.py   (fetches 3 Yahoo series, ~10 s)
"""
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_hip3stock as fs  # noqa: E402
import run_rollcarry as rc  # noqa: E402  (frozen in R478; helpers only)
from fetch_hip3carry import retry  # noqa: E402

OUT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "rollcarry_posthoc"
FRONT = {"NATGAS": "NG=F", "CL": "CL=F", "BRENTOIL": "BZ=F"}
URL = "https://query1.finance.yahoo.com/v8/finance/chart/{t}?period1={a}&period2={b}&interval=60m"
NOTIONAL = 0.75          # R478: notional is 3/4 of capital
H = 3_600_000


def front_bars(sym, start="2025-12-01", end="2026-11-12"):
    RAW.mkdir(parents=True, exist_ok=True)
    f = RAW / f"{sym.replace('=', '_')}_60m.json"
    if not f.exists():
        raw = retry(fs.request, URL.format(t=sym, a=int(pd.Timestamp(start, tz="UTC").timestamp()),
                                           b=int(pd.Timestamp(end, tz="UTC").timestamp())))
        f.write_bytes(raw)
        time.sleep(3)
    r = json.loads(f.read_bytes())["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    df = pd.DataFrame({"open_ms": np.asarray(r["timestamp"], np.int64) * 1000, "close": q["close"]}).dropna()
    return df


def at(df, t_ms, w=H):
    """Close of the bar that opened at t_ms - w (ends at t_ms); nan if missing."""
    o = df["open_ms"].to_numpy(np.int64)
    i = np.searchsorted(o, t_ms - w)
    return float(df["close"].iloc[i]) if i < len(o) and o[i] == t_ms - w else math.nan


def months():
    for y, m in [(2026, k) for k in range(1, 12)]:
        b = rc.bdays(y, m)
        yield f"{y}-{m:02d}", b[3], b[9]


def main():
    rows, out = [], []
    for pair, sym in FRONT.items():
        c1 = pd.read_csv(ROOT / "data/rollcarry/xyz" / f"{pair}_1h.csv")
        c4 = pd.read_csv(ROOT / "data/rollcarry/xyz" / f"{pair}_4h.csv")
        fut = front_bars(sym)
        for ym, d4, d10 in months():
            r = {}
            for k, d in (("bd4", d4), ("bd10", d10)):
                t = int(pd.Timestamp(f"{d} 20:00", tz="UTC").value // 1_000_000)
                p, src = rc.price_at(c1, c4, t)
                f = at(fut, t)
                r[k] = p / f - 1 if p == p and f == f else math.nan
                r[k + "_src"] = src
            rows.append({"pair": pair, "month": ym, "bd4": d4, "bd10": d10, "r_bd4": r["bd4"], "r_bd10": r["bd10"],
                         "roll": r["bd10"] - r["bd4"], "src": r["bd4_src"] + "/" + r["bd10_src"]})
        cyc = pd.read_csv(ROOT / "experiments/rollcarry_v1/results" / f"cycles_{pair}.csv")
        rr = pd.DataFrame([x for x in rows if x["pair"] == pair])
        for _, c in cyc.iterrows():
            m = rr[rr["bd10"] == c["to"]]
            roll = float(m["roll"].iloc[0]) if len(m) else math.nan
            out.append({"pair": pair, "from": c["from"], "to": c["to"],
                        "funding": c["fund"] / NOTIONAL, "gap_fund": c["gap"] / NOTIONAL, "minus_roll": -roll,
                        "net_fund": (c["fund"] + c["gap"]) / NOTIONAL, "net_front": c["fund"] / NOTIONAL - roll})
    m = pd.DataFrame(rows)
    cy = pd.DataFrame(out)
    m.to_csv(OUT / "front_roll_months.csv", index=False, float_format="%.6f")
    cy.to_csv(OUT / "front_roll_cycles.csv", index=False, float_format="%.6f")
    pd.set_option("display.width", 200)
    print("monthly r = perp/front - 1 at 20:00 UTC (percent of notional)")
    print((m.set_index(["pair", "month"])[["r_bd4", "r_bd10", "roll"]] * 100).round(2).to_string())
    print("\nper cycle (percent of notional; before cost and bill)")
    print((cy.set_index(["pair", "to"])[["funding", "gap_fund", "minus_roll", "net_fund", "net_front"]] * 100)
          .round(2).to_string())
    print("\nsummary per pair (percent of notional per cycle)")
    for pair, g in cy.groupby("pair", sort=False):
        g = g.dropna()
        print(f"{pair}: cycles {len(g)}; corr(gap_fund, -roll) {g['gap_fund'].corr(g['minus_roll']):.2f}; "
              f"mean net_fund {100 * g['net_fund'].mean():+.2f} sd {100 * g['net_fund'].std():.2f}; "
              f"mean net_front {100 * g['net_front'].mean():+.2f} sd {100 * g['net_front'].std():.2f}; "
              f"net_front > 0 in {int((g['net_front'] > 0).sum())} of {len(g)}")


if __name__ == "__main__":
    main()
