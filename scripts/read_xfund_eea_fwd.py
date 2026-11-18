"""Read of xfund_eea_fwd (R509), as its PREREG decides: the daily net with measured book costs.

For each scored day (an interval that starts on a live decision day, `ontime` or `late`):
  net_book = net (1x, fill accounting, flat 7 bp) + (0.0007 * legs - sum of measured costs) / (2 * slots)
where the sum runs over the leg-sides of that decision day's `enter`, `exit` and `inherit` tickets (the legs the journal
charges), and one leg-side costs its book record's `cost_bp_1000` plus the venue's taker fee (FEE_BP). A leg-side
with no book record costs 21 bp (3x the flat cost). `drop` tickets were never held and cost nothing, as in the journal.

usage: python scripts/read_xfund_eea_fwd.py [--look 1|2]   (prints JSON; writes nothing)
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab.stats import newey_west_t  # noqa: E402

LANE = ROOT / "experiments" / "xfund_eea_fwd"
FEE_BP = {"kraken": 5.0, "hyperliquid": 4.5}
FLAT, MISSING = 0.0007, 0.0021
SLOTS = {"A": 20}
LOOKS = {1: 90, 2: 180}
T_MIN, DD_MIN, KILL = 2.5, -0.03, -0.03
CHARGED = ("enter", "exit", "inherit")


def _rows(path):
    return pd.read_csv(path, dtype=str).fillna("") if Path(path).exists() and Path(path).stat().st_size else \
        pd.DataFrame()


def series(lane=LANE, book="A"):
    """The scored days of one book with net, net_book and net_book_2x (costs doubled), in day order."""
    j = Path(lane) / "journal"
    dec, tk, dy, bf = (_rows(j / f) for f in ("decisions.csv", "tickets.csv", "days.csv", "book_fills.csv"))
    if dec.empty or dy.empty:
        return pd.DataFrame(columns=["day", "kind", "net", "net_book", "net_book_2x"])
    ok = set(zip(dec.book, dec.day, dec.run))
    keep = lambda f: f[[x in ok for x in zip(f.book, f.day, f.run)]] if len(f) else f
    tk, dy = keep(tk), keep(dy)
    dy = dy[(dy.book == book) & dy.kind.isin(["ontime", "late"])].copy()
    cost = {}
    if len(bf):
        for _, r in bf.iterrows():
            c = r.get("cost_bp_1000", "")
            cost[(r.run, r.book, r.action, r.coin, r.venue)] = (float(c) + FEE_BP[r.venue]) / 1e4 if c != "" else \
                MISSING
    k = SLOTS[book]
    out = []
    for _, r in dy.iterrows():
        prev = str((pd.Timestamp(r.day) - pd.Timedelta(days=1)).date())
        legs = tk[(tk.book == book) & (tk.day == prev) & tk.action.isin(CHARGED)] if len(tk) else tk
        c = sum(cost.get((t.run, t.book, t.action, t.coin, v), MISSING) for _, t in legs.iterrows()
                for v in (t.long, t.short))
        net = float(r.net)
        flat = FLAT * float(r.legs)
        out.append({"day": r.day, "kind": r.kind, "net": net, "net_book": net + (flat - c) / (2 * k),
                    "net_book_2x": net + (flat - 2 * c) / (2 * k), "measured_cost": c, "legs": float(r.legs)})
    return pd.DataFrame(out).sort_values("day", ignore_index=True)


def drawdown(x):
    eq = np.cumsum(x)
    return float((eq - np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]).min()) if len(x) else 0.0


def read(s, look=None):
    x = s.net_book.to_numpy(float)
    rep = {"scored_days": int(len(x)), "late_share": float((s.kind == "late").mean()) if len(s) else None}
    if len(x) >= 3:
        _, mu, t = newey_west_t(x, 10)
        rep.update({"mean_bp": float(mu * 1e4), "ann_pct": float(mu * 365 * 100), "nw_t": float(t),
                    "sum_2x": float(s.net_book_2x.sum()), "max_dd": drawdown(x), "cum": float(x.sum()),
                    "flat_ann_pct": float(s.net.mean() * 365 * 100)})
    killed = len(x) and float(np.cumsum(x).min()) < KILL
    rep["kill_switch"] = bool(killed)
    if look:
        need = LOOKS[look]
        if killed:
            rep["verdict"] = "FAIL (kill switch)"
        elif len(x) < need:
            rep["verdict"] = f"NOT DUE ({len(x)} of {need} scored days)"
        else:
            y = s.iloc[:need]
            r = read(y)
            ok = r["nw_t"] >= T_MIN and r["sum_2x"] > 0 and r["max_dd"] > DD_MIN
            rep["verdict"] = "PASS" if ok else ("FAIL" if look == 2 or r["mean_bp"] <= 0 else "CONTINUE")
            rep["at_look"] = r
        if rep.get("verdict", "").startswith("PASS") and rep["late_share"] and rep["late_share"] > 0.2:
            rep["verdict"] += " (degraded timing)"
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--look", type=int, choices=(1, 2))
    a = ap.parse_args(argv)
    print(json.dumps(read(series(), a.look), indent=1))


if __name__ == "__main__":
    main()
