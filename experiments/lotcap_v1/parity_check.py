"""Post-run diagnostic for R298 (not part of the frozen rule): the uncovered age h24 book against R282's qx spread, by
year, and the tie at the maximum age. Run: python experiments/lotcap_v1/parity_check.py"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import run_lotcap as lc  # noqa: E402

fx = pd.read_parquet(lc.FACTORS)
fx = fx[(fx.t >= lc.T0) & (fx.t < lc.T1)]
sc = lc.scores(fx)
lg = lc.legs(sc, "age", lc.rebalance_times(sc.t.to_numpy(), 24))
syms = {x for v in lg.values() for side in v for x in side}
bars = lc.load_bars(syms)
rows = []
for t, (L, S) in lg.items():
    lr = [bars[s].leg(t, 24, False, 0.0) for s in L if s in bars]
    sr = [bars[s].leg(t, 24, True, 0.0) for s in S if s in bars]
    lr, sr = [x[0] for x in lr if x], [x[0] for x in sr if x]
    if lr and sr:
        rows.append({"t": t, "price": np.mean(lr) - np.mean(sr), "plog": np.mean(np.log1p(lr)) - np.mean(np.log1p(sr)),
                     "long": np.mean(lr), "short": np.mean(sr), "nl": len(lr), "ns": len(sr),
                     "short_max": np.max(sr)})
m = pd.DataFrame(rows).set_index("t")
d = pd.read_csv(ROOT / "experiments" / "pitfac_v1" / "results" / "ic.csv")
a = d[(d.factor == "age") & (d.horizon_h == 24)].set_index("t")
j = a[["ls", "names"]].join(m, how="inner")
print("R282 all", a.ls.mean() * 1e4, len(a), "| mine all", m.price.mean() * 1e4, len(m))
print("joined", len(j), "R282", j.ls.mean() * 1e4, "mine simple", j.price.mean() * 1e4, "mine log", j.plog.mean() * 1e4,
      "corr", j.ls.corr(j.price), "corr log", j.ls.corr(j.plog))
print("median R282", j.ls.median() * 1e4, "mine", j.price.median() * 1e4)
diff = j.price - j.ls
print("mean diff bp", diff.mean() * 1e4, "median diff", diff.median() * 1e4)
big = diff.abs().sort_values(ascending=False).head(10).index
out = j.loc[big, ["ls", "price", "plog", "short_max", "names", "nl", "ns"]].copy()
out.index = pd.to_datetime(out.index, unit="ms")
print(out.round(4))
print("share of the mean gap from the 10 largest |diff| days:", diff.loc[big].sum() / diff.sum())

# by year: the gap, the correlation, and how many long-leg names sat in the tie at the maximum age
jy = j.assign(diff=diff, year=pd.to_datetime(j.index, unit="ms").year)
print(jy.groupby("year").apply(lambda g: pd.Series({"R282": g.ls.mean() * 1e4, "mine": g.price.mean() * 1e4,
                                                     "gap": g["diff"].mean() * 1e4, "corr": g.ls.corr(g.price)})).round(2))
fa = fx[["t", "sym", "age"]].dropna()
mx = fa.groupby("t").age.transform("max")
tied = set(zip(fa.t[fa.age == mx], fa.sym[fa.age == mx]))
nt = fa[fa.age == mx].groupby("t").size()
share = pd.Series({t: np.mean([(t, s) in tied for s in L]) for t, (L, S) in lg.items()})
k = pd.Series({t: len(L) for t, (L, S) in lg.items()})
tab = pd.DataFrame({"tied_at_max": nt, "k": k, "long_leg_share_tied": share}).dropna()
tab["year"] = pd.to_datetime(tab.index, unit="ms").year
print(tab.groupby("year").mean().round(2))
print("days where the tie at max age exceeds k:", (tab.tied_at_max > tab.k).groupby(tab.year).mean().round(2).to_dict())

# with funding (the book's gross): does R282's spread include funding?
g = pd.read_csv(ROOT / "experiments" / "lotcap_v1" / "results" / "periods.csv")
g = g[g.strategy == "age h24 cover0"].set_index("t")
jg = j.join(g[["gross"]], how="inner")
jg["year"] = pd.to_datetime(jg.index, unit="ms").year
print(jg.groupby("year").apply(lambda q: pd.Series({"R282": q.ls.mean() * 1e4, "mine_price": q.price.mean() * 1e4,
                                                     "mine_gross": q.gross.mean() * 1e4,
                                                     "corr_gross": q.ls.corr(q.gross),
                                                     "rmse_gross_bp": np.sqrt(((q.ls - q.gross) ** 2).mean()) * 1e4,
                                                     "rmse_price_bp": np.sqrt(((q.ls - q.price) ** 2).mean()) * 1e4})).round(2))
print("all-days mean: R282", jg.ls.mean() * 1e4, "mine gross", jg.gross.mean() * 1e4, "n", len(jg))
