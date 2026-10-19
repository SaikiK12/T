"""Glue between data and search: the point-in-time research universe, costs, and guarded rule evaluation.

Nothing here may touch the holdout (from 2025-07-01) until a lane has been pre-registered and says so explicitly.
"""
from dataclasses import dataclass

import json
from pathlib import Path

import numpy as np

from . import data, engine, features, panel

HOLDOUT = "2025-07-01"
DISC_END = "2024-01-01"      # discovery: [START, 2024-01-01); validation: [2024-01-01, 2025-07-01)


def row_of(p, day):
    """Hour-row index of 00:00 UTC on `day`."""
    return int(np.searchsorted(p.t, panel.ms(day)))


@dataclass
class Universe:
    p: panel.Panel           # the columns ever liquid enough to trade
    elig: np.ndarray         # [T, S] bool, tradable at row t (point in time)
    cmat: np.ndarray         # [T, S] one-way cost per unit of weight
    ret: np.ndarray          # [T, S] next-bar return net of funding paid by longs
    rank: np.ndarray         # [T, S] trailing liquidity rank (1 = most liquid)
    bank: features.Bank
    index: tuple = None      # engine.eligible_index(elig), computed once

    def __post_init__(self):
        if self.index is None:
            self.index = engine.eligible_index(self.elig)

    @property
    def holdout_row(self):
        return row_of(self.p, HOLDOUT)


def make_universe(p, elig_top=100, col_top=150, window=24 * 30):
    """Tradable = in the top `elig_top` by trailing 30-day volume at that time. Columns = anything ever in the top
    `col_top`, so delisted and once-liquid symbols are included. Ranks come from the full panel, using past data only."""
    rank_full = panel.liquidity_rank(p, window)
    cols = np.flatnonzero((rank_full <= col_top).any(axis=0))
    q = p.columns(cols)
    rank = rank_full[:, cols]
    elig = rank <= elig_top
    cmat = engine.cost_matrix(rank)
    ret = engine.forward_returns(q["close"], q["fund_event"])
    return Universe(q, elig, cmat, ret, rank, features.Bank(q))


def eval_rules(u, bins, rules, t0, t1, slots=10, cmult=1.0, batch=128, allow_holdout=False):
    """Daily results over return rows [t0, t1): net return, cost and mean positions, each [R, D].

    The final return uses close[t1], so ending exactly at a present holdout boundary also requires opt-in.
    """
    holdout = u.holdout_row
    if not allow_holdout and (t1 > holdout or (t1 == holdout and holdout < u.p.T)):
        raise PermissionError(f"returns ending at row {t1} reach a holdout price (from row {holdout}); register the lane first")
    assert t0 % 24 == 0 and t1 % 24 == 0
    D = (t1 - t0) // 24
    ret_d, cost_d, act_d = (np.zeros((len(rules), D), np.float32) for _ in range(3))
    for a in range(0, len(rules), batch):
        out = engine.run_rules(bins, u.ret, u.elig, u.cmat, rules[a:a + batch], t0, t1, slots, cmult, index=u.index)
        seg = out[:, t0:t1].reshape(len(out), D, 24, 3)
        ret_d[a:a + batch] = seg[..., 0].sum(axis=2)
        cost_d[a:a + batch] = seg[..., 1].sum(axis=2)
        act_d[a:a + batch] = seg[..., 2].mean(axis=2)
    return ret_d, cost_d, act_d


def load_universe(root=None):
    """Reload what scripts/build_views.py saved: the universe arrays in memory and the feature bins as a read-only
    memory map. Returns (Universe, bins, view names)."""
    root = Path(root or data.ROOT / "research")
    meta = json.loads((root / "meta.json").read_text())
    t = np.load(root / "t.npy")
    close = np.load(root / "close.npy")
    p = panel.Panel(t, meta["symbols"], {"close": close})
    u = Universe(p, np.load(root / "elig.npy"), np.load(root / "cmat.npy"), np.load(root / "ret.npy"),
                 np.load(root / "rank.npy"), None)
    return u, np.load(root / "bins.npy", mmap_mode="r"), meta["names"]
