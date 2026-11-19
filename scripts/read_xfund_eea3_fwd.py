"""Read of xfund_eea3_fwd (R512), as its PREREG decides: the daily net with measured book costs, monitored every
scored day by lab.anytime's HAC mixture rule.

net_book per scored day is R509's definition (scripts/read_xfund_eea_fwd.py), with Aster's taker fee added:
  net_book = net (1x, fill accounting, flat 7 bp) + (0.0007 * legs - sum of measured costs) / (2 * 20)
over the leg-sides of the previous decision day's enter, exit and inherit tickets. One leg-side costs its book record's
cost_bp_1000 plus the venue's taker fee; with no record it costs 21 bp. fund_book = funding - measured cost / 40 is
reported, not decided.

Decision (PREREG):
- PASS on the first scored day n in [30, 180] with E_n >= 40 (lab.anytime.monitor with its defaults);
- FAIL at once if cumulative net_book < -3% (kill switch), at 90 scored days if the mean net_book <= 0, or at 180
  scored days without a crossing;
- otherwise RUNNING.

usage: python scripts/read_xfund_eea3_fwd.py   (prints JSON; writes nothing)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import anytime  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402

LANE = ROOT / "experiments" / "xfund_eea3_fwd"
FEE_BP = {"kraken": 5.0, "hyperliquid": 4.5, "aster": 4.0}
FLAT, MISSING = 0.0007, 0.0021
SLOTS = 20
CHARGED = ("enter", "exit", "inherit")
MAX_DAYS, FUTILITY_DAY, KILL = 180, 90, -0.03


def _rows(path):
    p = Path(path)
    return pd.read_csv(p, dtype=str).fillna("") if p.exists() and p.stat().st_size else pd.DataFrame()


def series(lane=LANE, book="A"):
    """Scored days of one book: day, kind, net, net_book, fund_book, measured cost (per unit of one leg)."""
    cols = ["day", "kind", "net", "net_book", "fund_book", "measured_cost", "legs"]
    j = Path(lane) / "journal"
    dec, tk, dy, bf = (_rows(j / f) for f in ("decisions.csv", "tickets.csv", "days.csv", "book_fills.csv"))
    if dec.empty or dy.empty:
        return pd.DataFrame(columns=cols)
    ok = set(zip(dec.book, dec.day, dec.run))
    keep = lambda f: f[[x in ok for x in zip(f.book, f.day, f.run)]] if len(f) else f
    tk, dy = keep(tk), keep(dy)
    dy = dy[(dy.book == book) & dy.kind.isin(["ontime", "late"])]
    cost = {}
    for _, r in bf.iterrows() if len(bf) else []:
        c = r.get("cost_bp_1000", "")
        cost[(r.run, r.book, r.action, r.coin, r.venue)] = (float(c) + FEE_BP[r.venue]) / 1e4 if c != "" else MISSING
    out = []
    for _, r in dy.iterrows():
        prev = str((pd.Timestamp(r.day) - pd.Timedelta(days=1)).date())
        legs = tk[(tk.book == book) & (tk.day == prev) & tk.action.isin(CHARGED)] if len(tk) else tk
        c = sum(cost.get((t.run, t.book, t.action, t.coin, v), MISSING) for _, t in legs.iterrows()
                for v in (t.long, t.short))
        net = float(r.net)
        out.append({"day": r.day, "kind": r.kind, "net": net,
                    "net_book": net + (FLAT * float(r.legs) - c) / (2 * SLOTS),
                    "fund_book": float(r.funding) - c / (2 * SLOTS), "measured_cost": c, "legs": float(r.legs)})
    if not out:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(out).sort_values("day", ignore_index=True)


def read(s):
    x = s.net_book.to_numpy(float)[:MAX_DAYS]
    n = len(x)
    rep = {"scored_days": int(n), "late_share": float((s.kind == "late").mean()) if len(s) else None}
    if n >= 3:
        _, mu, t = newey_west_t(x, 10)
        _, muf, tf = newey_west_t(s.fund_book.to_numpy(float)[:MAX_DAYS], 5)
        rep.update({"mean_bp": float(mu * 1e4), "ann_pct": float(mu * 365 * 100), "nw_t": float(t),
                    "cum": float(x.sum()), "fund_book_mean_bp": float(muf * 1e4), "fund_book_nw_t": float(tf)})
    m = anytime.monitor(x) if n else {"log_e": [], "first_cross": None, "rho": None}
    last = next((v for v in reversed(m["log_e"]) if v is not None), None)
    rep["log_e_last"], rep["e_last"] = last, (float(np.exp(last)) if last is not None else None)
    rep["first_cross_day"] = m["first_cross"]
    cum = np.cumsum(x)
    kill_day = int(np.argmax(cum < KILL)) + 1 if n and (cum < KILL).any() else None
    if kill_day is not None and (m["first_cross"] is None or kill_day <= m["first_cross"]):
        rep["verdict"] = f"FAIL (kill switch, day {kill_day})"
    elif m["first_cross"] is not None:
        rep["verdict"] = f"PASS (day {m['first_cross']})"
    elif n >= FUTILITY_DAY and float(x[:FUTILITY_DAY].mean()) <= 0:
        rep["verdict"] = "FAIL (mean <= 0 at 90 days)"
    elif n >= MAX_DAYS:
        rep["verdict"] = "FAIL (no crossing by 180 days)"
    else:
        rep["verdict"] = "RUNNING"
    return rep


def main():
    print(json.dumps(read(series()), indent=1))


if __name__ == "__main__":
    main()
