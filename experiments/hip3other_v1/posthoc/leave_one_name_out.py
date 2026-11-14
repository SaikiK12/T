"""R476 post hoc (reported, decides nothing): leave-one-name-out on the decide book in A and B, and the book without
the names whose trades ended with their deployer's shutdown ('gone')."""
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import run_hip3stock as hs

markets, bill, dropped = hs.load(ROOT / "data" / "hip3other")
first = max(min(d for mk in markets.values() for d in mk.days), hs.BOOK_START)


def ab(mk):
    daily, trades = hs.book(mk, bill, hs.BASE, first, hs.END)
    wk = hs.weekly(daily)
    a, b = wk[wk["last"] <= hs.A_END], wk[wk["last"] > hs.A_END]
    return trades, hs.stats(a, trades[trades["closed"] <= hs.A_END]), hs.stats(b, trades[trades["closed"] > hs.A_END])


trades, A, B = ab(markets)
print("base A %.2f t %.2f | B %.2f t %.2f" % (A["ann_excess_pts"], A["nw_t"], B["ann_excess_pts"], B["nw_t"]))
rows = []
for name in sorted(trades["ticker"].unique()):
    _, a, b = ab({k: v for k, v in markets.items() if k != name})
    rows.append({"left_out": name, "A_excess": a["ann_excess_pts"], "A_t": a["nw_t"], "A_2x": a["ann_excess_2x_pts"],
                 "A_price": a["ann_price_pts"], "A_carry_only": a["ann_carry_only_pts"], "A_slots": a["mean_slots"],
                 "B_excess": b["ann_excess_pts"], "B_t": b["nw_t"], "verdict": hs.verdict(a)[0]})
lo = pd.DataFrame(rows).sort_values("A_excess")
lo.to_csv(Path(__file__).with_suffix(".csv"), index=False)
print(lo.round(2).to_string(index=False))
print("verdict counts", lo["verdict"].value_counts().to_dict())
gone = sorted(trades.loc[trades["why"] == "gone", "ticker"].unique())
_, a, b = ab({k: v for k, v in markets.items() if k not in gone})
print("without the 'gone' names", gone)
print("  A %.2f t %.2f 2x %.2f carry %.2f price %.2f slots %.2f verdict %s" % (
    a["ann_excess_pts"], a["nw_t"], a["ann_excess_2x_pts"], a["ann_carry_only_pts"], a["ann_price_pts"],
    a["mean_slots"], hs.verdict(a)[0]))
