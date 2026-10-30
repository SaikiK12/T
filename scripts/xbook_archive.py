"""xbook_fwd (R285) archive context: the three families of the cross-family book (carry, flow, events) rebuilt as daily
series from the archive results of the lanes that feed it. Gives each family's daily sd (the book's frozen risk
weights), the correlations, and how often the book reached the decision bar in past windows. Everything read here was
read before (gate 0, in sample): this is context for the PREREG, not evidence.

usage: python scripts/xbook_archive.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg, stats  # noqa: E402

E = ROOT / "experiments"
OUT = E / "xbook_fwd" / "archive"
SLOTS = 10                                    # the event family's capital is split into 10 equal slots
EV_COST = 0.004                               # R267/R269/R271's 1x model cost, round trip
WINDOW = ("2023-06-01", "2026-09-30")         # R275 book A's archive begins 2023-05-26
CARRY = {"R278 A": ("xfund_v1", "gate+hyperliquid L14d th5% K20"), "R278 B": ("xfund_v1", "binance+mexc L14d th10% K20"),
         "R279 A": ("xfund_kd_v1", "gate+kucoin L14d th5% K20"), "R279 B": ("xfund_kd_v1", "binance+kucoin L14d th5% K20")}
FLOW = {"R215 A": "A_C0", "R215 B": "B_C0", "R218 X2": "X2"}
LAG = 10
INPUTS = ["xfund_v1/results/daily.csv", "xfund_kd_v1/results/daily.csv", "sizing_v1/results/daily.npz",
          "unlocks_v1/results/events_priced.csv", "delist_v1/results/legs_priced.csv",
          "montag_v1/results/legs_priced.csv", "announce_v1/results/legs_priced.csv"]


def carry_sleeves():
    out = {}
    for lane in {v[0] for v in CARRY.values()}:
        d = pd.read_csv(E / lane / "results" / "daily.csv")
        d = d[d.cost_multiple == 1]
        for name, (ln, strat) in CARRY.items():
            if ln == lane:
                s = d[d.strategy == strat].set_index("date").net
                out[name] = pd.Series(s.values, index=pd.to_datetime(s.index))
    return pd.DataFrame(out).sort_index()


def flow_sleeves():
    d = np.load(E / "sizing_v1" / "results" / "daily.npz")
    days = pd.date_range("2021-01-01", periods=len(d["A_C0"]), freq="D")       # sizing_v1 row 0 is 2021-01-01
    return pd.DataFrame({name: d[key] for name, key in FLOW.items()}, index=days)


def event_tickets():
    """One row per archive leg, closest to each forward lane's primary: its 1x net and its exit day (UTC)."""
    day = lambda ms: pd.to_datetime(ms, unit="ms").dt.normalize()
    hour = 3_600_000
    u = pd.read_csv(E / "unlocks_v1" / "results" / "events_priced.csv")
    d = pd.read_csv(E / "delist_v1" / "results" / "legs_priced.csv")
    d = d[d.kind == "spot"]                                                  # R268 trades spot delisting notices
    m = pd.read_csv(E / "montag_v1" / "results" / "legs_priced.csv")
    a = pd.read_csv(E / "announce_v1" / "results" / "legs_priced.csv")
    ff, pl = a[a.kind == "fund_freq"], a[a.kind == "prelist"]
    parts = [
        pd.DataFrame({"lane": "R266 unlocks", "day": pd.to_datetime(u.day), "net": u.net1x}),
        pd.DataFrame({"lane": "R268 delist", "day": day(d.t0 + hour), "net": d.net_1h_1x}),
        pd.DataFrame({"lane": "R270 montag", "day": day(m.t0 + 24 * hour), "net": m.net_24h_1x}),
        pd.DataFrame({"lane": "R272 FF", "day": day(ff.t0 + hour), "net": -ff.sg_1 - EV_COST}),        # long
        pd.DataFrame({"lane": "R272 PL", "day": day(pl.t0 + 168 * hour), "net": pl.sg_168 - EV_COST}),  # short
    ]
    return pd.concat(parts, ignore_index=True).dropna(subset=["net"])


def families(carry, flow, tickets, days):
    ev = tickets.groupby("day").net.sum() / SLOTS
    return pd.DataFrame({"carry": carry.reindex(days).mean(axis=1), "flow": flow.reindex(days).mean(axis=1),
                         "events": ev.reindex(days).fillna(0.0)}, index=days)


def window_share(x, n, bar=2.5):
    ts = np.array([stats.newey_west_t(x[i:i + n], LAG)[2] for i in range(len(x) - n + 1)])
    return float(np.mean(ts >= bar)) if len(ts) else float("nan")


def main():
    days = pd.date_range(*WINDOW, freq="D")
    carry, flow, tickets = carry_sleeves(), flow_sleeves(), event_tickets()
    fam = families(carry, flow, tickets, days)
    fam = fam[fam.carry.notna() & fam.flow.notna()]
    sd = fam.std(ddof=1)
    book = (fam / sd).mean(axis=1)
    sleeves = pd.concat([carry.reindex(fam.index), flow.reindex(fam.index), fam[["events"]]], axis=1)
    ann = lambda x: {"days": int(np.isfinite(x).sum()), "mean_pct_yr": float(np.nanmean(x) * 365 * 100),
                     "sharpe": float(np.nanmean(x) / np.nanstd(x, ddof=1) * np.sqrt(365)),
                     "nw_t": float(stats.newey_west_t(x, LAG)[2])}
    out = {"rid": "R285", "window": [str(fam.index[0].date()), str(fam.index[-1].date())], "slots": SLOTS,
           "family_daily_sd": {k: float(v) for k, v in sd.items()},
           "families": {k: ann(fam[k].values) for k in fam},
           "sleeves": {k: ann(sleeves[k].values) for k in sleeves},
           "family_corr": fam.corr().round(4).to_dict(), "sleeve_corr": sleeves.corr().round(3).to_dict(),
           "event_tickets": tickets.groupby("lane").net.agg(["size", "mean"]).rename(columns={"size": "n"})
                                   .round(5).to_dict("index"),
           "book_risk_balanced": {**{k: v for k, v in ann(book.values).items() if k != "mean_pct_yr"},
                                  "units": "each family over its daily sd, then averaged: only Sharpe and t mean anything",
                                  "share_90d_windows_t_ge_2.5": window_share(book.values, 90),
                                  "share_180d_windows_t_ge_2.5": window_share(book.values, 180),
                                  "share_365d_windows_t_ge_2.5": window_share(book.values, 365)},
           "book_equal_capital": ann(fam.mean(axis=1).values),
           "inputs_sha256": {p: prereg.sha256_file(E / p) for p in INPUTS}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "context.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("window", "family_daily_sd", "families", "book_risk_balanced",
                                          "book_equal_capital")}, indent=1))
    print(fam.corr().round(3).to_string())
    return out


if __name__ == "__main__":
    main()
