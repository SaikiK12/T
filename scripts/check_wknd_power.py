"""Power of the weekend fade, raw against a balanced (market-neutral) book, on R462's own weekends (descriptive).

Reads R462's bars (data/xyz_wknd, refetched by the frozen scripts/fetch_xyz_wknd.py with end 2026-11-10, so no
forward weekend of R463 is on disk) through R462's frozen `build`. It never opens R463's or R467's journals.

1. Reproduction: R462's D2 cell (all, |W| >= 50 bp, Sunday 22:00 exit), sample A and B.
2. Per-weekend nets at measured costs (fee 2 x 0.9 bp + the recorded Sunday book round trip):
   - raw: fade every market with |W| >= 50 bp (R462's D2 = R463's rule), weekend net = mean over its trades;
   - balanced: rel W = W - the weekend's median W over eligible markets; buy rel W <= -50, sell rel W >= +50,
     equal notional per side; weekend net = (mean long + mean short) / 2 - cost; traded only if both sides exist.
3. Power under R463's schedule (futility at 15 weekends; pass at 20 with p < 0.01 or 30 with p < 0.04, mean at 2x > 0,
   mean without the best 3 > 0), by resampling the weekends, at the in-sample effect, half of it and zero.

    python scripts/check_wknd_power.py [--book-bp 6.05] [--runs 2000]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_xyzwknd as r462  # noqa: E402

FEE_BP = 2 * 0.9
THETA = 50.0


def raw_weekends(per: pd.DataFrame, sample: str, cost: float) -> pd.DataFrame:
    d = per[(per["sample"] == sample) & (per.W.abs() >= THETA) & np.isfinite(per.g_x1)]
    g = d.groupby("F").agg(n=("g_x1", "size"), gross=("g_x1", "mean"))
    g["net"] = g.gross - cost
    return g


def balanced_weekends(per: pd.DataFrame, sample: str, cost: float, min_side: int = 1) -> pd.DataFrame:
    rows = []
    for f, g in per[per["sample"] == sample].groupby("F"):
        g = g[np.isfinite(g.W) & np.isfinite(g.g_x1)]
        if len(g) < 5:
            continue
        rel = g.W.to_numpy() - float(np.median(g.W))
        b = np.where(rel <= -THETA, 1.0, np.where(rel >= THETA, -1.0, 0.0))
        gb = b * g.s.to_numpy() * g.g_x1.to_numpy()          # the return of side b (price + funding)
        lo, sh = gb[b > 0], gb[b < 0]
        if len(lo) < min_side or len(sh) < min_side:
            continue
        gross = 0.5 * float(lo.mean()) + 0.5 * float(sh.mean())
        rows.append({"F": f, "n": len(lo) + len(sh), "n_long": len(lo), "n_short": len(sh), "gross": gross})
    out = pd.DataFrame(rows).set_index("F") if rows else pd.DataFrame(columns=["n", "gross"])
    out["net"] = out.gross - cost
    return out


def boot_p(x: np.ndarray, rng: np.random.Generator, draws: int) -> float:
    m = rng.choice(x, size=(draws, len(x)), replace=True).mean(axis=1)
    return float(np.mean(m <= 0))


def decide(seq: np.ndarray, cost: float, rng: np.random.Generator, draws: int) -> str:
    """R463's Decision on one sequence of weekend nets at 1x (B's ticket condition left out)."""
    if seq[:15].mean() <= 0:
        return "futile"
    for n, alpha in ((20, 0.01), (30, 0.04)):
        x = seq[:n]
        if boot_p(x, rng, draws) < alpha and (x - cost).mean() > 0 and np.sort(x)[:-3].mean() > 0:
            return f"pass{n}"
    return "null"


def power(net: np.ndarray, cost: float, shift: float, runs: int, rng: np.random.Generator, draws: int) -> dict:
    x = net - shift
    res = [decide(rng.choice(x, size=30, replace=True), cost, rng, draws) for _ in range(runs)]
    s = pd.Series(res).value_counts(normalize=True)
    return {k: float(s.get(k, 0.0)) for k in ("pass20", "pass30", "futile", "null")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book-bp", type=float, default=6.05, help="recorded Sunday $1k round trip (cycle 4)")
    ap.add_argument("--runs", type=int, default=2000)
    ap.add_argument("--draws", type=int, default=2000)
    a = ap.parse_args()
    rng = np.random.default_rng(20261125)
    cost = FEE_BP + a.book_bp

    per, skipped = r462.build()
    print("events:", per.groupby("sample").size().to_dict(), "skipped:", skipped)
    for smp in ("A", "B"):
        d = per[(per["sample"] == smp) & (per.W.abs() >= THETA) & np.isfinite(per.g_x1)]
        print(f"reproduction D2 {smp}: n {len(d)}, weekends {d.F.nunique()}, mean {d.g_x1.mean():+.1f} bp, "
              f"sd {d.g_x1.std(ddof=1):.0f}, hit {np.mean(d.g_x1 > 0):.0%}")

    print(f"\ncost per round trip: {cost:.2f} bp (fee {FEE_BP} + book {a.book_bp})")
    books = {}
    for name, fn in (("raw", raw_weekends), ("balanced", balanced_weekends)):
        for smp in ("A", "B"):
            w = fn(per, smp, cost)
            books[(name, smp)] = w
            print(f"{name:8s} {smp}: weekends {len(w)}, trades/weekend {w.n.mean():.1f}, weekend gross "
                  f"{w.gross.mean():+.1f} bp, net {w.net.mean():+.1f}, sd {w.net.std(ddof=1):.1f}, "
                  f"t {w.net.mean() / (w.net.std(ddof=1) / np.sqrt(len(w))):.2f}, "
                  f"weekends > 0: {int((w.net > 0).sum())}/{len(w)}")
    ab = {n: pd.concat([books[(n, 'A')], books[(n, 'B')]]) for n in ("raw", "balanced")}
    both = ab["raw"][["net"]].rename(columns={"net": "net_raw"}).join(
        ab["balanced"][["net"]].rename(columns={"net": "net_bal"}), how="inner")
    print(f"\ncorrelation of weekend nets, raw vs balanced (A+B, {len(both)} weekends): "
          f"{both.net_raw.corr(both.net_bal):.2f}")

    proxy = {"MSTR", "COIN", "HOOD", "CRCL", "BMNR", "STRC", "IREN"}   # fixed before the computation (6b)
    print("\ncrypto-proxy names against the rest (D2 trades, gross bp per trade):")
    for smp in ("A", "B"):
        d = per[(per["sample"] == smp) & (per.W.abs() >= THETA) & np.isfinite(per.g_x1)]
        for lab, sub in (("crypto-proxy", d[d.coin.isin(proxy)]), ("rest", d[~d.coin.isin(proxy)])):
            wk = sub.groupby("F").g_x1.mean()
            print(f"  {smp} {lab:12s}: n {len(sub)}, mean {sub.g_x1.mean():+.1f}, hit {np.mean(sub.g_x1 > 0):.0%}, "
                  f"weekend-mean t {wk.mean() / (wk.std(ddof=1) / np.sqrt(len(wk))):.2f} over {len(wk)} weekends")

    print("\npower under R463's schedule (A+B weekends resampled):")
    for name in ("raw", "balanced"):
        w = ab[name]
        g = float(w.gross.mean())
        for label, shift in (("in-sample", 0.0), ("half", 0.5 * g), ("zero", g - cost + 0.0)):
            p = power(w.net.to_numpy(), cost, shift, a.runs, rng, a.draws)
            print(f"  {name:8s} {label:9s} (net mean {w.net.mean() - shift:+.1f}): pass {p['pass20'] + p['pass30']:.0%} "
                  f"(20: {p['pass20']:.0%}, 30: {p['pass30']:.0%}), futile {p['futile']:.0%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
