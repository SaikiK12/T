"""The value-review arithmetic must reproduce the committed metrics, and must not adopt a filter."""
import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EVENTS = ROOT / "experiments/unlocks_v1/results/events_priced.csv"
METRICS = ROOT / "research/value_review_20261115/metrics.json"


@unittest.skipUnless(EVENTS.exists() and METRICS.exists(), "R265 events or the saved metrics are absent")
class ValueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location("vr", ROOT / "scripts/value_review.py")
        cls.vr = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.vr)
        cls.df = pd.read_csv(EVENTS)
        cls.saved = json.loads(METRICS.read_text())

    def test_source_hash_matches_the_saved_metrics(self):
        import hashlib
        self.assertEqual(hashlib.sha256(EVENTS.read_bytes()).hexdigest(), self.saved["source_sha256"])

    def test_robustness_reproduces(self):
        got = self.vr.robustness(self.df.net1x.to_numpy())
        for k, v in self.saved["robustness_net1x"].items():
            self.assertAlmostEqual(got[k], v, places=6, msg=k)

    def test_trimmed_mean_is_not_below_the_raw_mean(self):
        r = self.vr.robustness(self.df.net1x.to_numpy())
        self.assertGreaterEqual(r["trimmed_mean_10pct"], r["mean_pct"])

    def test_tail_adv_association_is_not_significant(self):
        t = self.vr.tail_vs_adv(self.df)
        self.assertTrue(t["all_worse_are_low_adv"])
        self.assertGreater(t["fisher_one_sided_p"], 0.05)  # must NOT be adopted as a filter

    def test_sizing_survives_the_worst_event_at_the_owner_cap(self):
        s = self.vr.sizing(self.df)["0.020"]
        self.assertGreater(s["max_drawdown_pct"], -5.0)     # inside a 5% daily-loss style limit
        self.assertGreater(s["worst_single_event_equity_pct"], -5.0)

    def test_concurrency_exceeds_one_so_a_per_event_cap_is_not_enough(self):
        c = self.vr.concurrency(self.df)
        self.assertGreater(c["max_open"], 1)
        self.assertLess(c["worst_cluster_sum_pct"], -100.0)  # a cluster can exceed one event's notional

    def test_no_intrabar_path_so_no_stop_is_claimed(self):
        self.assertFalse(self.saved["has_intrabar_path"])
        self.assertTrue(any("no stop" in s for s in self.saved["limits"]))


if __name__ == "__main__":
    unittest.main()
