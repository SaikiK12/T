"""Two margin accounts, not one pool: how often a levered design-gap book must move collateral between its venues,
how much, and how close an account comes to liquidation between daily checks. A descriptive measurement on R525's
in-sample books; it changes no lane and reads no forward result.

The engine (lab.xfund_v2) nets both legs in one capital pool. A real book holds each leg on its own venue's cross-margin
account. A rally makes the short venue lose and the long venue gain, so collateral must move from one to the other.

Per pair (R525's book, its trades and daily valuation prices):
- **Size:** each slot's leg notional at entry is capital x L / (2 K), K = 20.
- **Accounts:** each venue's equity is its deposit, plus the price PnL of its legs, plus the funding paid or received
  there, less 7 bp a leg traded there. Legs are revalued at each day's close.
- **Margin:** the ticket's `worst_move` with per-venue maintenance (MM below): the move against every leg at once that
  brings the account to its maintenance. (`lab.margin.liq_move`'s uniform move nets a mixed account's legs and reads
  near-infinite; the first run of this script found that flaw.)
- **Rule** (`docs/reviews/stake_dhl_20261123.md`): at the daily check, if either account's distance is under 30%,
  transfer collateral so both have the same distance; a "cut" is counted when even equal distances stay under 25%.
- **Also reported:** the worst distance seen at a daily check, the days an account was under 10% from liquidation at
  the check, and the days it was at or past liquidation. The daily check is the only one, so these are the moves a
  next-day transfer could not have stopped.

usage: python scripts/rebalance_sim.py [--L 2]
"""
import argparse
import json
import math
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import xfund as v1  # noqa: E402
from lab import xfund_v2 as v2  # noqa: E402
from scripts import run_carry_v2_audit as loader  # noqa: E402
from scripts import run_gap_breadth as gb  # noqa: E402
from scripts import stake_ticket as st  # noqa: E402  (the equalising split)

SPEC = ROOT / "experiments" / "gap_breadth_v1" / "spec.toml"
K = gb.BOOK[2]
COST = gb.COSTS[0]
# maintenance per venue: Kraken's retail schedule on most alts (25%), Hyperliquid's thin alts (max leverage 5 -> 10%),
# 5% elsewhere (assumed, as in the ticket)
MM = {"kraken": 0.25, "hyperliquid": 0.10}
MM_OTHER = 0.05
REBALANCE_AT, CUT_AT = 0.30, 0.25


def mm(venue):
    return MM.get(venue, MM_OTHER)


def simulate(u, trades, a, b, L, first_day, last_day):
    """Daily account states for the pair (a, b): list of dicts, plus transfer and cut events."""
    n = L / (2 * K)
    names = u.names
    by_entry, by_exit = {}, {}
    for t in trades:
        by_entry.setdefault(t["entry_day"], []).append(t)
        by_exit.setdefault(t["exit_day"], []).append(t)
    open_, realized = [], {a: 0.0, b: 0.0}
    deposit = None
    rows, events = [], []
    for d in range(first_day, last_day + 1):
        for t in open_:                         # funding over (d - 1, d] on each venue, booked on day d as the engine
            if t["entry_day"] >= d:
                continue
            for v, q, p0, sgn in t["_legs"]:
                s = u.series[t["_c"]][names.index(v)]
                f, px = s.fund_on(d), s.val[d - 1]
                if math.isfinite(f) and math.isfinite(px):
                    realized[v] += -sgn * q * px * f
        for t in by_exit.get(d, []):            # close at day d's prices: realise both legs
            if "_legs" not in t:
                continue
            for v, q, p0, sgn in t["_legs"]:
                s = u.series[t["_c"]][names.index(v)]
                px = s.val[d] if math.isfinite(s.val[d]) else p0
                realized[v] += sgn * q * (px - p0) - COST * n
            open_ = [x for x in open_ if x is not t]
        for t in by_entry.get(d, []):
            c = u.keys.index(t["coin"])
            sl, sh = u.series[c][names.index(t["long"])], u.series[c][names.index(t["short"])]
            pl, ph = float(sl.val[d]), float(sh.val[d])
            t["_c"] = c
            t["_legs"] = [(t["long"], n / pl, pl, 1.0), (t["short"], n / ph, ph, -1.0)]
            for v in (t["long"], t["short"]):
                realized[v] -= COST * n
            open_.append(t)
        unreal, legs = {a: 0.0, b: 0.0}, {a: [], b: []}
        for t in open_:
            for v, q, p0, sgn in t["_legs"]:
                s = u.series[t["_c"]][names.index(v)]
                px = s.val[d] if math.isfinite(s.val[d]) else p0
                unreal[v] += sgn * q * (px - p0)
                legs[v].append((sgn * q * px, mm(v)))
        eq = {v: (deposit[v] if deposit else 0.0) + realized[v] + unreal[v] for v in (a, b)}
        if deposit is None:
            if not (legs[a] or legs[b]):
                continue
            ea, eb = st.split(1.0, legs[a], legs[b])
            deposit = {a: ea - realized[a] - unreal[a], b: eb - realized[b] - unreal[b]}
            eq = {a: ea, b: eb}
        dist = {v: st.worst_move(eq[v], legs[v]) for v in (a, b)}
        row = {"day": d, "eq_" + a: eq[a], "eq_" + b: eq[b], "dist_" + a: dist[a], "dist_" + b: dist[b],
               "transfer": 0.0, "cut": False}
        if min(dist.values()) < REBALANCE_AT and (legs[a] or legs[b]):
            total = eq[a] + eq[b]
            ea, eb = st.split(total, legs[a], legs[b])
            move = ea - eq[a]                      # + : from b to a
            deposit[a] += move
            deposit[b] -= move
            nd = min(st.worst_move(ea, legs[a]), st.worst_move(eb, legs[b]))
            row.update(transfer=abs(move), cut=nd < CUT_AT, dist_after=nd)
            events.append({"day": d, "size": abs(move), "from": b if move > 0 else a, "cut": nd < CUT_AT,
                           "min_dist_before": min(dist.values())})
        rows.append(row)
    return pd.DataFrame(rows), events


def summarize(df, events, a, b, t0):
    if df.empty:
        return {"days": 0}
    years = len(df) / 365.0
    sizes = np.array([e["size"] for e in events]) if events else np.array([])
    md = df[["dist_" + a, "dist_" + b]].replace(np.inf, np.nan).min(axis=1)
    dates = pd.to_datetime(t0 + df.day * v1.DAY, unit="ms")
    return {"days": int(len(df)), "from": str(dates.iloc[0].date()), "transfers": len(events),
            "transfers_per_year": len(events) / years if years else None,
            "transfer_median_pct": float(np.median(sizes) * 100) if len(sizes) else 0.0,
            "transfer_p95_pct": float(np.quantile(sizes, 0.95) * 100) if len(sizes) else 0.0,
            "transfer_max_pct": float(sizes.max() * 100) if len(sizes) else 0.0,
            "cuts": int(sum(e["cut"] for e in events)),
            "worst_daily_distance_pct": float(np.nanmin(md) * 100) if md.notna().any() else None,
            "median_distance_pct": float(np.nanmedian(md) * 100) if md.notna().any() else None,
            "days_under_10pct": int((md < 0.10).sum()), "days_liquidated": int((md <= 0).sum()),
            "days_under_10pct_per_year": float((md < 0.10).sum() / years) if years else None}


def run(L=2.0, pairs=None):
    sp = tomllib.loads(SPEC.read_text())
    u = loader.load(sp, v2, set(gb.FLOORLESS + gb.FLOOR))
    out = {}
    for a in gb.FLOORLESS:
        for b in gb.FLOOR:
            if pairs and f"{a}+{b}" not in pairs:
                continue
            rows, trades = v2.replay(u, v2.Book([u.names.index(a), u.names.index(b)], *gb.BOOK),
                                     v2.window_start(u, [u.names.index(a), u.names.index(b)], gb.BOOK[0]))
            if not len(rows):
                continue
            df, ev = simulate(u, trades, a, b, L, int(rows.day.iloc[0]), int(rows.day.iloc[-1]))
            out[f"{a}+{b}"] = summarize(df, ev, a, b, u.t0)
            print(f"{a}+{b}", json.dumps({k: (round(v, 2) if isinstance(v, float) else v)
                                          for k, v in out[f'{a}+{b}'].items()}), flush=True)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=float, default=2.0)
    ap.add_argument("--pairs", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--mm-kraken", type=float, default=None, help="Kraken maintenance (0.05: the EU entity's retail)")
    a = ap.parse_args(argv)
    if a.mm_kraken is not None:
        MM["kraken"] = a.mm_kraken
    out = run(a.L, [p for p in a.pairs.split(",") if p])
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    main()
