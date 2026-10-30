"""vpin_v1 runner (scripts/run_vpin.py) on synthetic minute bars: no look-ahead in the hourly features, a planted
toxicity-to-volatility link is found out of sample, and a null one is not."""
import unittest
from unittest import mock

import numpy as np
import pandas as pd

from scripts import run_vpin as rv

T0 = int(pd.Timestamp("2021-01-01", tz="UTC").value // 10**6)
WINDOWS = dict(DISC=("2021-02-15", "2021-04-10"), VALID=("2021-04-11", "2021-05-28"))


def synth(days=150, planted=True, seed=0):
    """Hourly toxicity tau (0.05 or 0.6, switching with probability 0.1 an hour) sets the taker imbalance of every
    minute; with `planted`, it also scales that hour's volatility, under heavy hourly noise."""
    rng = np.random.default_rng(seed)
    nh = days * 24
    tau = np.empty(nh)
    tau[0] = 0.05
    for h in range(1, nh):
        tau[h] = (0.65 - tau[h - 1]) if rng.random() < 0.1 else tau[h - 1]
    sgn = rng.choice([-1.0, 1.0], nh)
    noise = np.exp(rng.normal(0, 1.2, nh))
    scale = (1 + 4 * tau if planted else np.ones(nh)) * noise * 1e-4
    m = np.repeat(np.arange(nh), 60)
    r = rng.normal(0, 1, nh * 60) * scale[m]
    close = 100 * np.exp(np.cumsum(r))
    vol = 100 * np.exp(rng.normal(0, 0.3, nh * 60))
    share = np.clip(0.5 + 0.5 * tau[m] * sgn[m] + rng.normal(0, 0.02, nh * 60), 0, 1)
    return {"close": close, "volume": vol, "quote_volume": vol * close, "taker_buy_volume": vol * share}


class RunVpinTest(unittest.TestCase):
    def test_hourly_features_do_not_see_the_hour_they_forecast(self):
        with mock.patch.multiple(rv, N=2, PER_DAY=24, SIZE_NEED=3, SIZE_DAYS=5):
            bars = synth(days=40, seed=1)
            f0 = rv.hourly(bars, t0=T0)
            k = 30 * 24 + 5
            b2 = {c: a.copy() for c, a in bars.items()}
            for c in b2:
                b2[c][k * 60:] *= 1.7
            f1 = rv.hourly(b2, t0=T0)
        cols = rv.BASE + ["vpin_exact", "vpin_bvc"]
        pd.testing.assert_frame_equal(f0.loc[:k, cols], f1.loc[:k, cols])
        self.assertFalse(np.allclose(f0.loc[k + 1:, "lrv_h"], f1.loc[k + 1:, "lrv_h"], equal_nan=True))
        self.assertEqual(f0.y1.iloc[k], f0.y1.iloc[k])           # the target itself is defined

    def test_window_keeps_every_target_hour_inside(self):
        with mock.patch.multiple(rv, **WINDOWS):
            end = pd.Timestamp("2021-04-10 23:00", tz="UTC").value // 10**6
            self.assertEqual(list(rv.window_of(np.array([end, end]), 1)), ["disc", "disc"])
            self.assertEqual(rv.window_of(np.array([end]), 24)[0], "")

    def _run(self, planted):
        with mock.patch.multiple(rv, N=2, PER_DAY=24, SIZE_NEED=3, SIZE_DAYS=5, **WINDOWS):
            frames = {c: rv.hourly(synth(planted=planted, seed=s), t0=T0) for s, c in enumerate(("A", "B"))}
            return rv.analyze(frames)

    def test_a_planted_link_is_found_out_of_sample(self):
        res = self._run(planted=True)
        p = res["forecast"]["h1"]["pooled"]["exact"]
        self.assertTrue(res["informative"], p)
        self.assertGreater(p["mse_cut"], 0.05)

    def test_a_null_link_is_not_called_informative(self):
        res = self._run(planted=False)
        p = res["forecast"]["h1"]["pooled"]["exact"]
        self.assertFalse(res["informative"], p)
        self.assertLess(abs(p["mse_cut"]), 0.01)


if __name__ == "__main__":
    unittest.main()
