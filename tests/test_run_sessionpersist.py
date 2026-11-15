"""Pure-logic tests for the sessionpersist_v1 runner: no network, no repo data, no frozen file read."""
import importlib.util
import tempfile
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
        self.assertTrue(np.isnan(ret[-1]).all())   # the last day has no forward close
        # a missing session day reduces the hour count and can void the window
        sess["A"][100, 0] = np.nan
        hours["A"][100, 0] = 0.0
        f2, _ = rsp.build_factors(close, sess, hours)
        self.assertTrue(np.isnan(f2["S_A"][100 + rsp.LOOKBACK - 1, 0]))

    def test_session_factors_sum_to_the_unsplit_control_when_complete(self):
        days, close, sess, hours, qvol = panel()
        ret = np.full_like(close, np.nan)
        ret[:-1] = np.log(close[1:] / close[:-1])   # ret[d] is earned on day d
        sess = {"A": ret * 0.6, "B": ret * 0.4}
        hours = {"A": np.full_like(close, float(rsp.SESSION_HOURS_A)),
                 "B": np.full_like(close, float(rsp.SESSION_HOURS_B))}
        f, _ = rsp.build_factors(close, sess, hours)
        ok = np.isfinite(f["S_A"]) & np.isfinite(f["S_B"]) & np.isfinite(f["MOM24"])
        np.testing.assert_allclose((f["S_A"] + f["S_B"])[ok], f["MOM24"][ok], atol=1e-12)


    def test_factor_never_overlaps_its_own_target(self):
        """f[d] may use returns earned through day d, never the target return earned on day d+1."""
        days, close, sess, hours, qvol = panel(seed=3)
        f, ret = rsp.build_factors(close, sess, hours)
        i = 40
        np.testing.assert_allclose(ret[i], np.log(close[i + 1] / close[i]), atol=1e-15)
        # The target earned on day i+1 depends on close[i+2]; moving it must not touch f[i].
        c2 = close.copy()
        c2[i + 2] *= 1.05
        f2, ret2 = rsp.build_factors(c2, {k: v.copy() for k, v in sess.items()}, hours)
        for name in rsp.FACTORS:
            np.testing.assert_allclose(f[name][i], f2[name][i], atol=1e-12)
        self.assertFalse(np.allclose(ret[i + 1], ret2[i + 1]))
        # and the runner's scoring aligns f[d] with ret[d+1]
        fwd = np.full_like(ret, np.nan)
        fwd[:-1] = ret[1:]
        np.testing.assert_allclose(fwd[i], np.log(close[i + 2] / close[i + 1]), atol=1e-15)


class PanelAccumulationTests(unittest.TestCase):
    """np.add.at on a NaN-initialised array stays NaN, which silently voided a whole panel once."""

    def test_session_and_volume_accumulators_produce_observations(self):
        rows = []
        base = rsp.ms(rsp.FIRST_DAY)
        for k in range(24 * 12):
            t = base + k * rsp.HOUR_MS
            px = 100.0 + k * 0.01
            prev = 100.0 + (k - 1) * 0.01 if k else px   # a continuous book: open == prior close
            rows.append({"t": t, "open": prev, "high": px, "low": prev, "close": px,
                         "volume": 1.0, "quote_volume": 1000.0, "count": 5,
                         "taker_buy_volume": 0.5, "taker_buy_quote_volume": 500.0})
        with tempfile.TemporaryDirectory() as d:
            raw = Path(d)
            (raw / "klines_1h").mkdir()
            pd.DataFrame(rows).to_parquet(raw / "klines_1h" / "TESTUSDT.parquet", index=False)
            orig = rsp.RAW
            try:
                rsp.RAW = raw
                days, close, sess, hours, qvol, cov = rsp.load_panel(["TESTUSDT"])
            finally:
                rsp.RAW = orig
        self.assertGreater(np.isfinite(qvol).sum(), 0, "quote volume must accumulate, not stay NaN")
        self.assertGreater(np.isfinite(sess["A"]).sum(), 0, "session A sums must accumulate")
        self.assertGreater(np.isfinite(sess["B"]).sum(), 0, "session B sums must accumulate")
        self.assertGreater(np.isfinite(close).sum(), 0)
        # a complete day's two session sums equal its full-day log return
        i = 5
        full = np.log(close[i + 1, 0] / close[i, 0])
        self.assertAlmostEqual(sess["A"][i, 0] + sess["B"][i, 0], full, places=10)


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
