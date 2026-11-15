"""The frozen risk rule must stay frozen, and the portfolio path must respect the gross cap."""
import importlib.util
import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "experiments/unlockrisk_v1/results/report.json"


def load_runner():
    spec = importlib.util.spec_from_file_location("ur", ROOT / "scripts/run_unlockrisk.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def synth(n=120, seed=0):
    rng = np.random.default_rng(seed)
    d = pd.DataFrame({"day": pd.date_range("2021-01-10", periods=n, freq="2D"),
                      "gross": rng.normal(0.03, 0.15, n),
                      "funding": rng.normal(-0.004, 0.01, n)})
    d.loc[5, "gross"], d.loc[5, "funding"] = -1.32, -0.45
    for k in ("net1x", "net2x", "net3x"):
        d[k] = d.gross - 0.002
    d["entry"] = d.day - pd.Timedelta(days=7)
    d["tot"] = d.gross + d.funding
    return d.sort_values("day").reset_index(drop=True)


class RuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_runner()

    def test_primary_rule_is_the_owner_cap_not_a_searched_cell(self):
        self.assertEqual(self.m.PRIMARY, (0.02, 0.10))
        self.assertEqual(self.m.S1_MAX_DD, -0.10)
        self.assertEqual(self.m.S2_WORST_DAY, -0.05)

    def test_gross_cap_is_never_exceeded(self):
        d = synth()
        for c, G in ((0.02, 0.10), (0.03, 0.10), (0.03, 0.20)):
            p = self.m.portfolio(d, c, G, "lump")
            self.assertLessEqual(p["peak_gross"], G + 1e-12)

    def test_lump_is_at_least_as_bad_as_spread_on_the_worst_day(self):
        d = synth()
        l = self.m.portfolio(d, 0.02, 0.10, "lump")
        s = self.m.portfolio(d, 0.02, 0.10, "spread")
        self.assertLessEqual(l["worst_day"], s["worst_day"])

    def test_no_position_means_no_return_that_day(self):
        d = synth(n=3)
        p = self.m.portfolio(d, 0.02, 0.10, "lump")
        self.assertGreater(p["calendar_days"], 3)
        self.assertTrue(np.isfinite(p["terminal_equity_x"]))

    def test_cap_reduces_the_mean_net_per_event(self):
        d = synth()
        dr = self.m.drag(d, 0.02, 0.10)
        self.assertLess(dr["net1x"], float(d.net1x.mean()))


@unittest.skipUnless(REPORT.exists(), "the lane has not been run")
class FrozenResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rep = json.loads(REPORT.read_text())

    def test_prereg_still_matches_its_freeze(self):
        import sys
        sys.path.insert(0, str(ROOT))
        from lab import prereg
        got = prereg.verify(ROOT / "experiments/unlockrisk_v1/PREREG.md")
        self.assertEqual(got, self.rep["prereg_sha256"])

    def test_one_trial_and_no_filter(self):
        self.assertEqual(self.rep["trials"], 1)
        r = self.rep["primary_rule"]
        self.assertIsNone(r["stop"])
        self.assertFalse(r["funding_veto"])
        self.assertFalse(r["adv_filter"])

    def test_non_binding_gross_caps_are_identical(self):
        rows = {(x["c"], x["G"]): x["lump"] for x in self.rep["sensitivity_not_deciding"]}
        a, b = rows[(0.02, 0.20)], rows[(0.02, 0.30)]
        self.assertEqual(a["days_cap_binds"], 0)
        self.assertAlmostEqual(a["terminal_equity_x"], b["terminal_equity_x"], places=9)

    def test_owner_stop_conflict_is_recorded_not_resolved(self):
        oc = self.rep["owner_stop_conflict"]
        self.assertLess(oc["worst_event_in_equity_at_cap"], oc["stop_in_equity_at_cap"])
        self.assertIn("owner decides", oc["note"])


if __name__ == "__main__":
    unittest.main()
