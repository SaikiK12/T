"""oiwick_v1 post-hoc diagnostics (run after the verdict; descriptive): raw vs market-adjusted event returns, the
SQZ/24 book against its event sums, and same-coin re-triggers. usage: python experiments/oiwick_v1/posthoc_diag.py
"""
import sys, numpy as np
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from lab import flowfeat, research, screen
from run_oiwick import triggers
from run_tsbattery import WINDOWS
u, _, _ = research.load_universe()
t = np.asarray(u.p.t)
kl = flowfeat.load("klines", t, u.p.symbols, ("open", "high", "low"))
m = flowfeat.load("metrics", t, u.p.symbols, ("oi",))
o, h, l = (np.asarray(kl[k], np.float64) for k in ("open", "high", "low"))
c = np.asarray(u.p["close"], np.float64); oi = np.asarray(m["oi"], np.float64); e = np.asarray(u.elig)
trig = triggers(o, h, l, c, oi) * e
a0, b0 = screen.Screen(u, windows=WINDOWS).rows["discovery"]
lc = np.log(np.where(c > 0, c, np.nan))
R = np.nan_to_num(np.asarray(u.ret, np.float64))
mk = np.nanmean(np.where(e, R, np.nan), axis=1)
for v, name in ((1, "long_cascade"), (-1, "squeeze")):
    ti, si = np.nonzero(trig[a0:b0] == v); ti = ti + a0
    for k in (4, 24):
        f = np.array([lc[a + k, s] - lc[a, s] for a, s in zip(ti, si)])
        bk = np.array([R[a:a + k, s].sum() for a, s in zip(ti, si)])
        mx = np.array([mk[a:a + k].sum() for a in ti])
        ok = np.isfinite(f)
        print(name, k, "n", ok.sum(), "raw mean %.1f median %.1f" % (f[ok].mean()*1e4, np.median(f[ok])*1e4),
              "| book-ret sum mean %.1f median %.1f" % (bk.mean()*1e4, np.median(bk)*1e4),
              "| market-adj mean %.1f" % ((bk - mx).mean()*1e4),
              "| top5 share of raw sum %.2f" % (np.sort(np.abs(f[ok]))[-5:].sum() / np.abs(f[ok]).sum()))
    yrs = (np.asarray(u.p.t)[ti] // (365.25*86400e3) + 1970).astype(int)
    print(name, "by year counts", {int(y): int((yrs == y).sum()) for y in np.unique(yrs)})
from run_ictlevels import held
n_el = np.maximum(e.sum(axis=1, keepdims=True), 1)
x0 = np.where(trig == -1, -1, 0)
H = held(x0, 24)
for nm, P in (("masked", np.where(e, H, 0.0) / n_el), ("unmasked", H / n_el)):
    print(nm, "gross bp/day %.3f" % ((P[a0:b0] * R[a0:b0]).sum() / 1095 * 1e4), "exposure %.5f" % np.abs(P[a0:b0]).sum(1).mean())
ti, si = np.nonzero(trig[a0:b0] == -1); ti = ti + a0
print("event sum bp/day %.3f" % (sum(-R[a:a + 24, s].sum() for a, s in zip(ti, si)) / 50 / 1095 * 1e4))
print("held rows per event", (H[a0:b0] != 0).sum() / len(ti))
last, first_ev, rep = {}, [], 0
for a, s in sorted(zip(ti, si)):
    if s in last and a - last[s] < 24: rep += 1
    else: first_ev.append((a, s))
    last[s] = a
print("re-triggers within 24h", rep, "of", len(ti))
print("first-event-only sum bp/day %.3f" % (sum(-R[a:a + 24, s].sum() for a, s in first_ev) / 50 / 1095 * 1e4))
