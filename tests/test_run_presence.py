import unittest

import numpy as np
import pandas as pd

from scripts import run_presence as rp


class TestPresence(unittest.TestCase):
    def test_decide(self):
        self.assertEqual(rp.decide(3.1, 2.4, 0.5, True)[0], "survives")
        self.assertEqual(rp.decide(3.1, 1.2, 2.5, True)[0], "metrics-leak")
        self.assertEqual(rp.decide(3.1, -2.5, 2.5, True)[0], "metrics-leak")          # signed: a flip is below 2
        self.assertEqual(rp.decide(3.1, 1.2, 1.0, True)[0], "not-reproduced")
        self.assertEqual(rp.decide(3.1, 2.4, 0.5, False)[0], "INVALID")
        self.assertEqual(rp.decide(1.9, 2.4, 0.5, True)[0], "INVALID")
        self.assertEqual(rp.decide(3.1, 2.4, 2.9, True)[1], "PARTIAL")

    def test_same_is_nan_aware(self):
        self.assertTrue(rp.same(np.array([1.0, np.nan]), np.array([1.0, np.nan])))
        self.assertFalse(rp.same(np.array([1.0, np.nan]), np.array([1.0, 2.0])))

    def test_has_oi_reads_the_row_of_the_decision_day(self):
        day = pd.to_datetime(["2022-03-01", "2022-03-01", "2022-03-02"])
        panel = pd.DataFrame({"day": day, "perp": ["AAAUSDT", "BBBUSDT", "AAAUSDT"], "oi_usd": [5.0, np.nan, np.nan]})
        t = (pd.to_datetime(["2022-03-01", "2022-03-01", "2022-03-02"]).astype("datetime64[ms]").astype(np.int64)
             - rp.H)
        keys = pd.DataFrame({"t": t, "sym": ["AAAUSDT", "BBBUSDT", "AAAUSDT"]})
        self.assertEqual(list(rp.has_oi(panel, keys)), [1.0, 0.0, 0.0])

    def test_presence_score_ranks_rows_with_metrics_above_rows_without(self):
        u = np.random.default_rng(rp.SEED).random(1000)
        has = (np.arange(1000) % 3 == 0).astype(float)
        s = has + u
        self.assertGreater(s[has == 1].min(), s[has == 0].max() - 1.0)
        self.assertTrue((s[has == 1] >= 1).all() and (s[has == 0] < 1).all())


if __name__ == "__main__":
    unittest.main()
