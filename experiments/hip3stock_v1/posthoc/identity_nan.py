"""Post hoc for R475, R476 and R477 (reported, decides nothing): the frozen identity checks with the NaN fixed.

The frozen checks correlate `diff().tail(59)` of each market's daily log returns. With fewer than 60 marks the first
return is NaN, the correlation is NaN and the market fails. This reruns each lane's decide book with the NaN dropped
before correlating, everything else unchanged, and lists which markets come back.
Writes identity_nan.csv and identity_nan.log next to this file.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import run_hip3stock as hs  # noqa: E402
import run_xyztwin as xt  # noqa: E402


def identity_fixed(self):
    r = (self.perp / self.close).tail(60)
    a, b = np.log(self.perp).diff().tail(59), np.log(self.close).diff().tail(59)
    ok = a.notna() & b.notna()
    a, b = a[ok], b[ok]
    corr = float(np.corrcoef(a, b)[0, 1]) if len(a) >= 19 and a.std() > 0 and b.std() > 0 else 1.0
    return len(r) >= 20 and 0.97 <= float(r.median()) <= 1.03 and corr >= hs.MIN_CORR


def correlated_fixed(mk):
    a, b = np.log(mk.perp).diff().tail(xt.ID_MARKS - 1), np.log(mk.close).diff().tail(xt.ID_MARKS - 1)
    ok = a.notna() & b.notna()
    a, b = a[ok], b[ok]
    if len(a) < 19 or a.std() == 0 or b.std() == 0:
        return False
    return float(np.corrcoef(a, b)[0, 1]) >= hs.MIN_CORR


def decide(markets, bill):
    first = max(min(d for mk in markets.values() for d in mk.days), hs.BOOK_START)
    daily, trades = hs.book(markets, bill, hs.BASE, first, hs.END)
    wk = hs.weekly(daily)
    a, b = wk[wk["last"] <= hs.A_END], wk[wk["last"] > hs.A_END]
    return (trades, hs.stats(a, trades[trades["closed"] <= hs.A_END]),
            hs.stats(b, trades[trades["closed"] > hs.A_END]))


def lanes():
    frozen_id, frozen_corr = hs.Market.identity_ok, xt.correlated
    for lane, data, twin in (("R475", "hip3stock", False), ("R476", "hip3other", False), ("R477", "xyztwin", True)):
        out = {}
        for label, fixed in (("frozen", False), ("fixed", True)):
            hs.Market.identity_ok = identity_fixed if fixed else frozen_id
            xt.correlated = correlated_fixed if fixed else frozen_corr
            if twin:
                with xt.london_marks():
                    markets, bill, _, _ = xt.load(ROOT / "data" / data)
                    out[label] = (markets,) + decide(markets, bill)
            else:
                markets, bill, _ = hs.load(ROOT / "data" / data)
                out[label] = (markets,) + decide(markets, bill)
        hs.Market.identity_ok, xt.correlated = frozen_id, frozen_corr
        added = sorted(set(out["fixed"][0]) - set(out["frozen"][0]))
        for label, (markets, trades, a, b) in out.items():
            new_trades = sorted(set(trades["ticker"]) & set(added))
            yield {"lane": lane, "identity": label, "markets": len(markets), "added": " ".join(added) if label == "fixed"
                   else "", "traded_added": " ".join(new_trades),
                   "A_excess": a["ann_excess_pts"], "A_t": a["nw_t"], "A_2x": a["ann_excess_2x_pts"],
                   "A_carry_only": a["ann_carry_only_pts"], "A_price": a["ann_price_pts"], "A_slots": a["mean_slots"],
                   "A_trades": a["trades"], "A_verdict": hs.verdict(a)[0],
                   "B_excess": b["ann_excess_pts"], "B_t": b["nw_t"], "B_carry_only": b["ann_carry_only_pts"],
                   "B_slots": b["mean_slots"], "B_trades": b["trades"]}


if __name__ == "__main__":
    df = pd.DataFrame(list(lanes()))
    df.to_csv(Path(__file__).with_suffix(".csv"), index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(df.round(2).to_string(index=False))
