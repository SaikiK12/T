"""levcarry_v1 (R280) audit: are the legs liquidated at L = 1 real moves, or one venue's trade prints?

A leg at L = 1 under `iso_daily` is liquidated only by a move of at least 95-99% against it within one day. This reads
R280's events (experiments/levcarry_v1/results/events.csv) and, for each such leg, the raw bars of its venue and of
the same coin on every other venue in the engine run's table. It writes results/audit_l1.csv, one row per leg-day:

- move: the leg's worst adverse move of the day from the opening close, as R280 read it;
- close_move: the close-to-close move against the leg;
- bar_move: the extreme bar's own wick against the leg, from the nearer of its open and close (a one-bar spike shows a
  large bar_move);
- other_max, other_venue: the largest move the same way on the coin's other venues that day (NaN when none lists it);
- kind:
  - `one-venue print` when no other venue moved 20% the same way and the leg's own close moved less than 20%;
  - `real move` when another venue moved at least 50% the same way;
  - `mixed` otherwise;
- leg_ret: the leg's return that day at 1x without liquidation (price and funding, R275's accounting);
- cap_effect: -1 - leg_ret, what the liquidation at L = 1 changes against R275's accounting for that leg (positive
  when the loss is capped below the close-to-close loss).

Days are dated by their end: the day dated D runs from 00:00 UTC on D - 1 to 00:00 UTC on D.
A post-hoc audit of a measurement; it counts no trials.

usage: python scripts/audit_levcarry.py
"""
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import xfund  # noqa: E402

LANE = ROOT / "experiments" / "levcarry_v1"
RUNS = {"R278": "xfund_v1", "R279": "xfund_kd_v1"}
DAY = xfund.DAY


def bars(spec, venue, symbol, lo_ms, hi_ms):
    """The venue's bars that end in (lo_ms, hi_ms], or None if the coin has no file there."""
    v = {x["name"]: x for x in spec["venues"]}[venue]
    p = ROOT / "data" / v["prices"] / f"{symbol}.parquet"
    if not symbol or not p.exists():
        return None
    df = pd.read_parquet(p, columns=["t", "open", "high", "low", "close"])
    end = df.t + v.get("bar_h", 1) * xfund.H
    return df[(end > lo_ms) & (end <= hi_ms)], df[end <= lo_ms].tail(1)


def against(b, prev, side):
    """(worst move against a leg of `side` from the previous close, close-to-close move against it, the extreme bar's
    own wick against it) over bars b; NaN when there is no bar."""
    if b is None or not len(b) or not len(prev):
        return np.nan, np.nan, np.nan
    c0, c1 = prev.close.iloc[0], b.close.iloc[-1]
    if side > 0:
        i = b.low.idxmin()
        return 1 - b.low.min() / c0, 1 - c1 / c0, 1 - b.low[i] / min(b.open[i], b.close[i])
    i = b.high.idxmax()
    return b.high.max() / c0 - 1, c1 / c0 - 1, b.high[i] / max(b.open[i], b.close[i]) - 1


def main():
    ev = pd.read_csv(LANE / "results" / "events.csv")
    ev = ev[(ev.leverage == 1) & (ev.policy == "iso_daily") & (ev.mm == 0.05)]
    rows = []
    for lane, run in RUNS.items():
        spec = tomllib.loads((ROOT / "experiments" / run / "spec.toml").read_text())
        sym = pd.read_csv(ROOT / spec["symbols"], dtype=str).fillna("").set_index("key")
        t0 = int(pd.Timestamp(spec["start"], tz="UTC").value // 10**6)
        venues = {v["name"]: v for v in spec["venues"]}
        for (date, coin, venue, leg), g in ev[ev.lane == lane].groupby(["date", "coin", "venue", "leg"]):
            side = 1 if leg == "long" else -1
            hi_ms = int(pd.Timestamp(date, tz="UTC").value // 10**6)
            got = bars(spec, venue, sym.at[coin, venue], hi_ms - DAY, hi_ms)
            move, close_move, bar_move = against(*got, side) if got else (np.nan,) * 3
            other, other_v = np.nan, ""
            for name in venues:
                if name == venue:
                    continue
                o = bars(spec, name, sym.at[coin, name], hi_ms - DAY, hi_ms)
                m = against(*o, side)[0] if o else np.nan
                if np.isfinite(m) and not (m <= other):
                    other, other_v = m, name
            # R275's accounting for the leg that day, as lab.xfund reads it (price and funding at 1x)
            v = venues[venue]
            s = xfund.load_daily(ROOT / "data" / v["prices"] / f"{sym.at[coin, venue]}.parquet",
                                 ROOT / "data" / v["funding"] / f"{sym.at[coin, venue]}.parquet", v["vol"],
                                 v.get("bar_h", 1), t0, (hi_ms - t0) // DAY + 2)
            d = (hi_ms - t0) // DAY - 1
            leg_ret = side * s.ret(d) - side * s.fund_on(d + 1) if s else np.nan
            same = (other >= 0.5) if np.isfinite(other) else False
            quiet = (not np.isfinite(other) or other < 0.2) and close_move < 0.2
            rows.append({"lane": lane, "books": "".join(sorted(g.book)), "date": date, "coin": coin, "venue": venue,
                         "leg": leg, "move": move, "close_move": close_move, "bar_move": bar_move,
                         "other_max": other, "other_venue": other_v,
                         "kind": "real move" if same else "one-venue print" if quiet else "mixed",
                         "leg_ret": leg_ret, "cap_effect": -1 - leg_ret})
    out = pd.DataFrame(rows)
    out.to_csv(LANE / "results" / "audit_l1.csv", index=False, float_format="%.6g")
    print(out.groupby(["lane", "kind"]).agg(legs=("coin", "size"), cap_effect=("cap_effect", "sum")).to_string())
    print(out.groupby(["lane", "venue", "kind"]).size().to_string())


if __name__ == "__main__":
    main()
