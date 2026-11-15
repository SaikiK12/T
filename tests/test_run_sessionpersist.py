"""Pure-logic tests for the sessionpersist_v1 runner: no network, no repo data, no frozen file read."""
import importlib.util
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("rsp", ROOT / "scripts" / "run_sessionpersist.py")
rsp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rsp)


def panel(d=400, s=60, seed=0):
    rng = np.random.default_rng(seed)
    days = pd.date_range(rsp.FIRST_DAY, periods=d, freq="D", tz="UTC")
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, size=(d, s)), axis=0))
    sess = {"A": rng.normal(0, 0.01, size=(d, s)), "B": rng.normal(0, 0.01, size=(d, s))}
    hours = {"A": np.full((d, s), 14.0), "B": np.full((d, s), 10.0)}
    qvol = rng.uniform(1e6, 1e8, size=(d, s))
    return days, close, sess, hours, qvol


class WindowTests(unittest.TestCase):
    def test_holdout_cut_excludes_holdout_and_later(self):
        days = pd.date_range(rsp.FIRST_DAY, rsp.END, freq="D", tz="UTC")
        cut = rsp.holdout_cut(days)
        self.assertLess(cut, len(days))
        self.assertLess(days[cut - 1], pd.Timestamp(rsp.HOLDOUT_START, tz="UTC"))
        self.assertGreaterEqual(days[cut], pd.Timestamp(rsp.HOLDOUT_START, tz="UTC"))

    def test_windows_are_tz_aware_and_ordered(self):
        days = pd.date_range(rsp.FIRST_DAY, rsp.END, freq="D", tz="UTC")
        dl, dh = rsp.window_slice(days, rsp.DISC)
        vl, vh = rsp.window_slice(days, rsp.VAL)
        self.assertEqual(days[dl], pd.Timestamp(rsp.DISC[0], tz="UTC"))
        self.assertEqual(days[dh - 1], pd.Timestamp(rsp.DISC[1], tz="UTC"))
        self.assertEqual(days[vl], pd.Timestamp(rsp.VAL[0], tz="UTC"))
        self.assertLessEqual(dh, vl)  # contiguous: discovery ends 2023-12-31, validation starts 2024-01-01
        self.assertLessEqual(vh, rsp.holdout_cut(days))  # validation reads no holdout day
        self.assertLess(days[vh - 1], pd.Timestamp(rsp.HOLDOUT_START, tz="UTC"))


class EligibilityTests(unittest.TestCase):
    def test_eligibility_is_capped_and_uses_only_past_volume(self):
        days, close, sess, hours, qvol = panel()
        elig, _ = rsp.eligibility(close, qvol)
        self.assertLessEqual(elig.sum(axis=1).max(), rsp.TOP)
        self.assertFalse(elig[0].any())  # no trailing window on day 0
        # changing today's volume must not change today's eligibility
        e2, _ = rsp.eligibility(close, qvol * np.where(np.arange(len(days))[:, None] == 200, 1e6, 1.0))
        np.testing.assert_array_equal(elig[200], e2[200])

    def test_missing_close_makes_a_name_ineligible(self):
        days, close, sess, hours, qvol = panel()
        close[200, 0] = np.nan
        elig, _ = rsp.eligibility(close, qvol)
        self.assertFalse(elig[200, 0])


class FactorTests(unittest.TestCase):
    def test_factors_need_the_full_lookback_and_respect_gaps(self):
        days, close, sess, hours, qvol = panel()
        f, ret = rsp.build_factors(close, sess, hours)
        for name in rsp.FACTORS:
            self.assertTrue(np.isnan(f[name][:rsp.LOOKBACK - 1]).all())
        self.assertTrue(np.isnan(ret[0]).all())
        # a missing session hour voids that day's session sum
        sess["A"][100, 0] = np.nan
        f2, _ = rsp.build_factors(close, sess, hours)
        self.assertTrue(np.isnan(f2["S_A"][100:100 + rsp.LOOKBACK, 0]).all())

    def test_session_factors_sum_to_the_unsplit_control_when_complete(self):
        days, close, sess, hours, qvol = panel()
        ret = np.full_like(close, np.nan)
        ret[1:] = np.log(close[1:] / close[:-1])
        sess = {"A": ret * 0.6, "B": ret * 0.4}
        f, _ = rsp.build_factors(close, sess, hours)
        ok = np.isfinite(f["S_A"]) & np.isfinite(f["S_B"]) & np.isfinite(f["MOM24"])
        np.testing.assert_allclose((f["S_A"] + f["S_B"])[ok], f["MOM24"][ok], atol=1e-12)


class StatTests(unittest.TestCase):
    def test_bootstrap_returns_finite_null_t_values(self):
        rng = np.random.default_rng(1)
        ts = rsp.block_bootstrap_t(rng.normal(0, 1e-3, size=300), n_null=20)
        self.assertEqual(len(ts), 20)
        self.assertTrue(np.isfinite(ts).all())

    def test_bootstrap_on_too_short_a_series_is_zeros_not_a_crash(self):
        ts = rsp.block_bootstrap_t(np.zeros(5), n_null=5)
        np.testing.assert_array_equal(ts, np.zeros(5))

    def test_nanmean_of_empty_is_nan(self):
        self.assertTrue(np.isnan(rsp._nanmean(np.array([np.nan, np.nan]))))
        self.assertEqual(rsp._nanmean(np.array([1.0, np.nan])), 1.0)

    def test_random_data_does_not_pass_the_discovery_gate(self):
        days, close, sess, hours, qvol = panel(seed=7)
        elig, _ = rsp.eligibility(close, qvol)
        f, ret = rsp.build_factors(close, sess, hours)
        cut = rsp.holdout_cut(days)
        res, null = rsp.evaluate(days[:cut], {k: v[:cut] for k, v in f.items()}, ret[:cut], elig[:cut])
        self.assertEqual(rsp.verdict_of(res), "NULL")
        self.assertIn("family_max_q95_t", null)
        for name in rsp.FACTORS:
            self.assertIn("3", res[name]["book"]["disc"]["net"])  # cost sensitivity present


if __name__ == "__main__":
    unittest.main()
