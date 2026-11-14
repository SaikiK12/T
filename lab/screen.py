"""The standard screen for a cross-sectional feature, so a queued method needs a frozen PREREG and a feature, not a
new runner. A feature is binned among eligible coins each hour; slices opened in the top and bottom bins are held
`hold` hours as a spread book with a universe hedge (lab/slices); the book is judged in stages, each computed only if
the previous one passed. This is the construction of R197, R211 and R226, factored out unchanged.

Stages (the defaults below are R226's; a PREREG may pass its own):
  discovery   2021-01-01..2023-12-31: 1x NW t (lag 10) >= 2, 2x mean > 0, and, with a reference, residual t >= 2
  validation  2024-01-01..2025-06-30: 1x mean > 0 with t >= 1.5, and residual > 0
  holdout     2025-07-01..2026-09-30: 1x mean > 0 with t >= 2 (CONFIRMED); read only when the PREREG allows it
"""
import numpy as np
import pandas as pd

from . import events, features, research, slices, stats

WINDOWS = (("discovery", "2021-01-01", "2024-01-01"), ("validation", "2024-01-01", "2025-07-01"),
           ("holdout", "2025-07-01", "2026-10-01"))


def default_rule(window, r, n2):
    """r: the 1x stats row of a book in a window; n2: its 2x daily nets."""
    if window == "discovery":
        return r["t_nw10"] >= 2 and n2.mean() > 0 and r.get("resid_t_nw10", np.inf) >= 2
    if window == "validation":
        return r["mean_bp_day"] > 0 and r["t_nw10"] >= 1.5 and r.get("resid_bp_day", 1.0) > 0
    return r["mean_bp_day"] > 0 and r["t_nw10"] >= 2


def window_stats(n, days, ref=None):
    """Daily nets n over `days` (ms of each day's first hour), optionally against a reference book's nets."""
    s = events.summary(n)
    year = pd.to_datetime(days, unit="ms", utc=True).year
    out = {"days": len(n), "total": float(n.sum()), "mean_bp_day": float(n.mean() * 1e4),
           "t_nw10": float(stats.newey_west_t(n, 10)[2]), "sharpe": s.get("sharpe", np.nan),
           "max_dd": s.get("max_dd", np.nan),
           "by_year_bp_day": {int(y): float(n[year == y].mean() * 1e4) for y in np.unique(year)}}
    if ref is not None:
        beta = np.linalg.lstsq(np.column_stack([np.ones(len(n)), ref]), n, rcond=None)[0]
        resid = n - beta[1] * ref
        out.update(corr_ref=float(np.corrcoef(n, ref)[0, 1]), beta_ref=float(beta[1]),
                   resid_bp_day=float(resid.mean() * 1e4), resid_t_nw10=float(stats.newey_west_t(resid, 10)[2]))
    return out


class Screen:
    """Books on one universe. `bins` are computed lazily per feature; K (slices per hour) is fixed on discovery."""

    def __init__(self, u, hold=72, nbins=8, windows=WINDOWS):
        self.u, self.hold, self.nb = u, hold, nbins
        self.rows = {w: (research.row_of(u.p, a), research.row_of(u.p, b)) for w, a, b in windows}
        a, b = self.rows["holdout"] if "holdout" in self.rows else (None, None)
        if a is not None:
            self.rows["holdout"] = (a, b - (b - a) % 24)
        self.t0, self.tv = self.rows["discovery"]

    def spread(self, x):
        """{"H": (parts, K), "L": (parts, K)} for feature x: H longs the top bin and shorts the bottom one."""
        b = features.bins_xs(x, self.u.elig, self.nb)
        lo, hi = (b == 0) & self.u.elig, (b == self.nb - 1) & self.u.elig
        K = float(lo[self.t0:self.tv].sum(axis=1).mean() + hi[self.t0:self.tv].sum(axis=1).mean())
        return {"H": ([(hi, 1), (lo, -1)], K), "L": ([(lo, 1), (hi, -1)], K)}

    def run(self, parts, K, a, b, cmult=1.0):
        """Daily (net, gross incl. hedge, cost incl. hedge cost) of a book over rows [a, b), warmed up from a - hold."""
        w = max(a - self.hold, 0)
        P = sum(slices.positions(ind, self.hold, w, b, 1.0 / (self.hold * K), side) for ind, side in parts)
        o = slices.run(P, self.u.ret, self.u.elig, self.u.cmat, w, b, cmult=cmult)
        D = (b - a) // 24
        day = lambda x: x[(a - w): (a - w) + D * 24].reshape(D, 24).sum(1)
        return day(o["net"]), day(o["gross"] + o["hedge"]), day(o["cost"] + o["hedge_cost"])

    def days(self, a, b):
        return self.u.p.t[a:a + (b - a) // 24 * 24:24]

    def staged(self, name, parts, K, ref_book=None, rule=default_rule, holdout=False, log=print):
        """Run one book through the stages. Returns (rows, stage) where rows hold 1x/2x/3x stats per window reached."""
        rows, reached, passed = [], None, True
        for w, (a, b) in self.rows.items():
            if not passed or (w == "holdout" and not holdout):
                break
            ref = self.run(*ref_book, a, b)[0] if ref_book is not None else None
            nets = {}
            for cm in (1.0, 2.0, 3.0):
                n, g, c = self.run(parts, K, a, b, cm)
                nets[cm] = n
                rows.append({"book": name, "window": w, "cmult": cm, "K": K, "gross_bp_day": float(g.mean() * 1e4),
                             "cost_bp_day": float(c.mean() * 1e4), **window_stats(n, self.days(a, b), ref)})
            r1 = rows[-3]
            passed, reached = bool(rule(w, r1, nets[2.0])), w
            extra = f" resid {r1['resid_bp_day']:+.1f} t {r1['resid_t_nw10']:+.2f}" if ref is not None else ""
            log(f"{name} {w}: {r1['mean_bp_day']:+.1f} bp/day t {r1['t_nw10']:+.2f}{extra}", "PASS" if passed else "stop")
        return rows, {"reached": reached, "passed": passed}
