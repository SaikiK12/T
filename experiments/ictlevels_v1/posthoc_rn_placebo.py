"""Post-hoc descriptive check for R246 (not pre-registered, no decision): RN_CROSS on a grid shifted by half a step."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np
from lab import flowfeat, research, screen, slices
from run_tsbattery import WINDOWS
from run_ictlevels import held
u, _, _ = research.load_universe()
t = np.asarray(u.p.t)
kl = flowfeat.load("klines", t, u.p.symbols, ("high", "low"))
c = np.asarray(u.p["close"], np.float64)
e = np.asarray(u.elig)
s = screen.Screen(u, windows=WINDOWS)
a, b = s.rows["discovery"]
pc = np.vstack([np.full((1, c.shape[1]), np.nan), c[:-1]])
with np.errstate(invalid="ignore", divide="ignore"):
    g = 10.0 ** (np.floor(np.log10(pc)) - 1)
n_el = np.maximum(e.sum(axis=1, keepdims=True), 1)
G = {}
for off in (0.0, 0.5):
    with np.errstate(invalid="ignore", divide="ignore"):
        k0, k1 = np.floor(pc / g - off), np.floor(c / g - off)
    ok = np.isfinite(g) & np.isfinite(c) & (pc > 0)
    x = np.where(ok & (k1 > k0), 1, np.where(ok & (k1 < k0), -1, 0))
    P = np.where(e, held(x), 0.0) / n_el
    o = slices.run(P[a:b], u.ret, u.elig, u.cmat, a, b, hedge=False, cmult=1.0)
    D = len(o["daily"])
    gr = o["gross"][:D * 24].reshape(D, 24).sum(1).mean() * 1e4
    G[off] = o["gross"][:D * 24].reshape(D, 24).sum(1)
    print(f"offset {off}: triggers {int((np.abs(x[a:b]) * e[a:b]).sum())}, gross {gr:+.2f} bp/day, net {o['daily'].mean()*1e4:+.2f}")
from lab import stats
d = G[0.0] - G[0.5]
print("round minus half-step gross: %.2f bp/day, NW t %.2f" % (d.mean() * 1e4, stats.newey_west_t(d, 10)[2]))
import pandas as pd
yr = pd.to_datetime(t[a:a + len(d) * 24:24], unit="ms").year
print({int(y): round(float(d[yr == y].mean() * 1e4), 1) for y in np.unique(yr)})
