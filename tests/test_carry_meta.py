"""Offline tests for scripts/run_carry_meta.py (R531): features use data up to the entry day only."""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import xfund_v2 as v2  # noqa: E402
from scripts import run_carry_meta as m  # noqa: E402


class U:
    def __init__(self, series):
        self.series = series


def daily(nd, rate, price, seed):
    rng = np.random.default_rng(seed)
    close = price * np.exp(np.cumsum(rng.normal(0, 0.01, nd)))
    fresh = np.ones(nd, bool)
    f = np.full(nd, rate) + rng.normal(0, rate / 5, nd)
    n = np.ones(nd, np.int64)
    return v2.Daily.build(close, fresh, f, n)


def test_features_ignore_the_future():
    nd, d = 80, 50
    a, h = daily(nd, 0.0001, 100.0, 1), daily(nd, 0.0004, 100.0, 2)
    f1 = m.features(U({0: {0: a, 1: h}}), 0, 0, 1, d, "kraken")
    a2, h2 = daily(nd, 0.0001, 100.0, 1), daily(nd, 0.0004, 100.0, 2)
    for x in (a2, h2):
        x.val[d + 1:] *= 3.0
        x.cumf[d + 1:] += 5.0
        x.fresh[d + 1:] = False
    f2 = m.features(U({0: {0: a2, 1: h2}}), 0, 0, 1, d, "kraken")
    assert f1 == f2
    assert f1["s14"] > 0 and math.isfinite(f1["fvol"]) and f1["fresh14"] == 1.0
    assert f1["v_bitfinex"] == 0.0 and f1["v_deribit"] == 0.0


def test_features_none_without_history():
    a, h = daily(20, 0.0001, 100.0, 3), daily(20, 0.0004, 100.0, 4)
    assert m.features(U({0: {0: a, 1: h}}), 0, 0, 1, 5, "deribit") is None


def test_fit_models_respects_purge_and_minimum():
    rng = np.random.default_rng(0)
    n = 400
    tab = pd.DataFrame({k: rng.normal(size=n) for k in m.FEATURES})
    tab["exit_day"] = np.arange(n)
    tab["y"] = (tab.s14 > 0).astype(int)
    models = m.fit_models(tab, [(200, 300), (350, 400), (420, 500)])
    assert 200 not in models          # only 186 trades exit before 200 - 14, under the 300 minimum
    assert 350 in models and 420 in models       # 336 and 400 trades exit before the embargo
