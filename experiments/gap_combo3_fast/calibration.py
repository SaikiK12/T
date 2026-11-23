# R527 calibration, run once before the freeze (2026-11-23): in-sample funding-net series of the three forward pairs
# (R509 Kraken+HL, R520 Deribit+HL, R524 Bitfinex+Binance) on R525's engine.
import sys, tomllib
sys.path.insert(0, "/home/user/T")
import numpy as np, pandas as pd
from pathlib import Path
from lab import xfund_v2 as v2, xfund as v1
from lab.stats import newey_west_t
from scripts import run_carry_v2_audit as loader, run_gap_breadth as gb
sp = tomllib.loads(Path("/home/user/T/experiments/gap_breadth_v1/spec.toml").read_text())
u = loader.load(sp, v2, {"kraken", "hyperliquid", "deribit", "bitfinex", "binance"})
S = {}
for a, b in (("kraken", "hyperliquid"), ("deribit", "hyperliquid"), ("bitfinex", "binance")):
    rows, _ = gb.pair_book(u, a, b)
    dates = pd.to_datetime(u.t0 + rows.day * v1.DAY, unit="ms").dt.normalize()
    S[a] = pd.DataFrame({"fund": ((rows.funding - 0.0007 * rows.legs) / 40).to_numpy(), "net": v2.net(rows, 20, 0.0007).to_numpy()}, index=dates)
for k, v in S.items():
    f = v.fund
    print(k, "days", len(f), "fund ann %.1f" % (f.mean() * 36500), "daily sharpe %.3f" % (f.mean() / f.std()), "net ann %.1f" % (v.net.mean() * 36500))
common = S["kraken"].index.intersection(S["deribit"].index).intersection(S["bitfinex"].index)
print("common days", len(common), common.min().date(), common.max().date())
F = pd.DataFrame({k: v.fund.reindex(common) for k, v in S.items()})
print("corr\n", F.corr().round(3))
def power(x, w, thr=3.0, step=3):
    hits = tot = 0
    for s in range(0, len(x) - w + 1, step):
        y = x[s:s + w]; tot += 1; hits += newey_west_t(y, 5)[2] >= thr
    return hits / tot
inv = 1 / F.std()
combos = {"two (K+D) equal": F[["kraken", "deribit"]].mean(axis=1),
          "three equal": F.mean(axis=1),
          "three inverse-vol": (F * inv).sum(axis=1) / inv.sum(),
          "kraken alone": F.kraken, "deribit alone": F.deribit, "bitfinex alone": F.bitfinex}
for name, x in combos.items():
    x = x.to_numpy(float)
    print(f"{name:20s} ann {x.mean()*36500:5.1f}  power20 {power(x,20):.2f} power30 {power(x,30):.2f}  size20 {power(x-x.mean(),20):.3f} size30 {power(x-x.mean(),30):.3f}")
print("inverse-vol weights", (inv / inv.sum()).round(3).to_dict())
