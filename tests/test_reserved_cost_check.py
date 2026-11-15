"""The reserved-cost check must use each lane's frozen cost unit and label what it cannot price."""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "research/reserved_cost_check_20261115.json"
STATUS = ROOT / "experiments/book_costs_v1/journal/status.json"


def load():
    spec = importlib.util.spec_from_file_location("rcc", ROOT / "scripts/reserved_cost_check.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@unittest.skipUnless(STATUS.exists() and OUT.exists(), "recorder status or saved output absent")
class ReservedCostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()
        cls.saved = json.loads(OUT.read_text())

    def test_cost_units_match_the_lanes_own_frozen_specs(self):
        # R275 / batch1 carry.toml and batch2 PREREG both use 7 bp per leg per side at 1x
        toml = (ROOT / "experiments/reserved_batch1/carry.toml").read_text()
        self.assertIn("costs = [0.0007, 0.0014, 0.0021]", toml)
        for name, b in self.m.BOOKS.items():
            self.assertEqual(b["cost_1x_bp_leg_side"], 7.0, name)

    def test_source_hash_matches(self):
        import hashlib
        self.assertEqual(hashlib.sha256(STATUS.read_bytes()).hexdigest(),
                         self.saved["source_sha256"])

    def test_unrecorded_venues_are_declared_not_assumed_cheap(self):
        c14 = self.saved["books"]["R286_C14_binance_gate"]
        self.assertEqual(c14["bands_priced"], 0)
        self.assertIn("binance", c14["unpriced_venues"])
        self.assertIn("gate", c14["unpriced_venues"])
        # an unpriced book must not be reported as surviving
        self.assertFalse(c14["survives_3x_on_every_priced_band"])

    def test_kucoin_long_tail_costs_far_more_than_the_assumed_unit(self):
        b = self.saved["books"]["R391_kucoin_dydx_lighter_mexc"]
        thin = [r for r in b["measured_bands"]
                if r["venue"] == "kucoin" and r["band_usd"] != "5e+06-inf"]
        self.assertTrue(thin)
        for r in thin:
            self.assertGreater(r["multiple_of_assumed_1x"], 3.0)
        self.assertFalse(b["survives_3x_on_every_priced_band"])

    def test_mexc_is_the_cheap_leg(self):
        b = self.saved["books"]["R391_kucoin_dydx_lighter_mexc"]
        for r in b["measured_bands"]:
            if r["venue"] == "mexc":
                self.assertLess(r["multiple_of_assumed_1x"], 3.0)

    def test_limits_state_the_band_median_caveat(self):
        self.assertTrue(any("band medians" in s for s in self.saved["limits"]))
        self.assertTrue(any("no reserved read" in s for s in self.saved["limits"]))


if __name__ == "__main__":
    unittest.main()
