"""Fast read of R509's journal (R510 xfund_eea_fast), as experiments/xfund_eea_fast/PREREG.md decides.

R508's daily net is mostly funding (funding share 1.04). Its price legs are hedged on the same coin and add noise, not
return: on R508's days the funding part had an annualised Sharpe of 16.9 against 7.1 for the whole net. This read
decides on the funding part net of the measured costs, which a month can show, and keeps the whole net as a guard.
R509's own 90- and 180-day looks are unchanged.

Per scored day of R509's book A (scripts/read_xfund_eea_fwd.series: an interval that starts on a live decision day):
  fund_book = funding - measured cost / (2 * 20)        the funding the held pairs earned, less the leg-sides' costs
  price     = net_book - fund_book                      the price legs plus the live-fill gap
with funding and gross per unit of total capital as R509's journal books them, and the measured cost as R509's read
charges it (the $1,000 book walk plus the taker fee; 21 bp for a leg-side with no record).

usage: python scripts/read_xfund_eea_fast.py [--look 1|2]   (prints JSON; writes nothing)
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
from scripts import read_xfund_eea_fwd as fwd  # noqa: E402

LOOKS = {1: 30, 2: 45}
T_MIN, NW_LAG = 2.5, 5


def series(lane=fwd.LANE, book="A"):
    try:
        s = fwd.series(lane, book)
    except KeyError:                       # R509's read raises on a journal with no scored day yet (its DEVIATIONS.md)
        s = pd.DataFrame(columns=["day", "kind", "net", "net_book", "net_book_2x", "measured_cost", "legs"])
    if s.empty:
        return s.assign(funding=[], cost_pc=[], fund_book=[], price=[])
    dy = fwd._rows(Path(lane) / "journal" / "days.csv")
    dec = fwd._rows(Path(lane) / "journal" / "decisions.csv")
    ok = set(zip(dec.book, dec.day, dec.run))
    dy = dy[[x in ok for x in zip(dy.book, dy.day, dy.run)]]
    dy = dy[(dy.book == book) & dy.kind.isin(["ontime", "late"])]
    f = dict(zip(dy.day, dy.funding.astype(float)))
    k = fwd.SLOTS[book]
    s = s.assign(funding=s.day.map(f))
    s["cost_pc"] = s.measured_cost / (2 * k)
    s["fund_book"] = s.funding - s.cost_pc
    s["price"] = s.net_book - s.fund_book
    return s


def read(s, look=None):
    x = s.fund_book.to_numpy(float)
    rep = {"scored_days": int(len(x))}
    if len(x) >= 3:
        _, mu, t = newey_west_t(x, NW_LAG)
        rep.update({"fund_book_mean_bp": float(mu * 1e4), "fund_book_ann_pct": float(mu * 365 * 100),
                    "fund_book_nw_t": float(t), "net_book_cum": float(s.net_book.sum()),
                    "price_cum": float(s.price.sum()), "measured_cost_cum": float(s.cost_pc.sum())})
    killed = len(s) and float(np.cumsum(s.net_book.to_numpy(float)).min()) < fwd.KILL
    if look:
        need = LOOKS[look]
        if killed:
            rep["verdict"] = "FAIL (R509 kill switch)"
        elif len(x) < need:
            rep["verdict"] = f"NOT DUE ({len(x)} of {need} scored days)"
        else:
            r = read(s.iloc[:need])
            if r["fund_book_mean_bp"] <= 0:
                rep["verdict"] = "FAIL"
            elif r["fund_book_nw_t"] >= T_MIN and r["net_book_cum"] > 0:
                rep["verdict"] = "PASS"
            else:
                rep["verdict"] = "NOT YET" if look == 1 else "NO EARLY PASS (R509's looks decide)"
            rep["at_look"] = r
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--look", type=int, choices=(1, 2))
    a = ap.parse_args(argv)
    print(json.dumps(read(series(), a.look), indent=1))


if __name__ == "__main__":
    main()
