"""R475 post hoc (reported, decides nothing): leave-one-name-out on the decide book, and A without liquidation days."""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import run_hip3stock as hs

markets, bill, dropped = hs.load(hs.DATA)
first = max(min(d for mk in markets.values() for d in mk.days), hs.BOOK_START)

def ab(mk):
    daily, trades = hs.book(mk, bill, hs.BASE, first, hs.END)
    wk = hs.weekly(daily)
    a, b = wk[wk["last"] <= hs.A_END], wk[wk["last"] > hs.A_END]
    return daily, trades, hs.stats(a, trades[trades["closed"] <= hs.A_END]), hs.stats(b, trades[trades["closed"] > hs.A_END])

daily, trades, A, B = ab(markets)
print("base A %.2f t %.2f | B %.2f t %.2f" % (A["ann_excess_pts"], A["nw_t"], B["ann_excess_pts"], B["nw_t"]))
rows = []
for name in sorted(trades["ticker"].unique()):
    _, tr, a, b = ab({k: v for k, v in markets.items() if k != name})
    rows.append({"left_out": name, "A_excess": a["ann_excess_pts"], "A_t": a["nw_t"], "A_2x": a["ann_excess_2x_pts"],
                 "A_price": a["ann_price_pts"], "A_carry_only": a["ann_carry_only_pts"], "B_excess": b["ann_excess_pts"],
                 "B_t": b["nw_t"], "verdict": hs.verdict(a)[0]})
lo = pd.DataFrame(rows).sort_values("A_excess")
lo.to_csv(Path(__file__).with_suffix(".csv"), index=False)
print(lo.round(2).to_string(index=False))
print("verdict counts", lo["verdict"].value_counts().to_dict())
# A and B without liquidation days (their whole day's excess removed: the liquidated slot and the other slots that day)
d = daily.copy()
liqd = d[d["liquidations"] > 0]["date"].tolist()
print("liquidation days", liqd)
d2 = d[d["liquidations"] == 0]
wk = hs.weekly(d2)
a, b = wk[wk["last"] <= hs.A_END], wk[wk["last"] > hs.A_END]
sa, sb = hs.stats(a, trades.iloc[0:0]), hs.stats(b, trades.iloc[0:0])
print("ex-liquidation days: A %.2f t %.2f price %.2f carry %.2f | B %.2f t %.2f price %.2f" % (
    sa["ann_excess_pts"], sa["nw_t"], sa["ann_price_pts"], sa["ann_carry_only_pts"], sb["ann_excess_pts"], sb["nw_t"], sb["ann_price_pts"]))
lq = d[d["liquidations"] > 0][["date", "fund", "price", "cost", "excess", "liquidations"]]
print(lq.to_string(index=False))
