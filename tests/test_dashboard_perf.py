import json
import math
import unittest

from scripts import dashboard_perf as perf


class DashboardPerfTest(unittest.TestCase):
    def test_notes_t(self):
        self.assertEqual(perf.notes_t("Primary +12.7%/yr t3.80 (disc), +5.9%/yr t2.82 (val)"), 3.8)
        self.assertEqual(perf.notes_t("LONG_NEG -38.5 bp/event t-0.69 (funding"), -0.69)
        self.assertIsNone(perf.notes_t("at 2x cost, 3x t 12x"))

    def test_leaderboard_bars(self):
        rounds = [{"id": "R1", "order": 1, "date": "2026-10-20", "lane": "a", "verdict": "NULL", "status": "DONE",
                   "trials": 100, "title": "x"},
                  {"id": "R2", "order": 2, "date": "2026-10-20", "lane": "b", "verdict": "NULL", "status": "DONE",
                   "trials": 1, "title": "y"}]
        strategies = [{"round": "R1", "t": 2.5, "strategy": "s1"}, {"round": "R1", "t": 3.1, "strategy": "s2"}]
        lb = perf.leaderboard(rounds, strategies)
        self.assertEqual((lb[0]["best_t"], lb[0]["best_strategy"]), (3.1, "s2"))
        self.assertEqual([r["program_trials"] for r in lb], [100, 101])
        self.assertGreater(lb[0]["chance_bar_t"], 2.0)          # 100 tries reach t ~2.5 by chance
        self.assertIsNone(lb[1]["chance_bar_t"])
        json.dumps(lb, allow_nan=False)

    def test_tearsheets_are_json_safe(self):
        days = [{"series": "R9 A", "round": "R9", "group": "g", "book": "A", "day": f"2026-10-0{i}", "kind": "replay",
                 "net": v} for i, v in enumerate([0.01, -0.02, 0.0, 0.015], 1)]
        sheets, equity, monthly = perf.tearsheets(days, 1000)
        fwd = [s for s in sheets if s["series"] == "R9 A"][0]
        self.assertEqual(fwd["days"], 4)
        self.assertIsNone(fwd["cagr"])                          # too short to annualize
        self.assertAlmostEqual(fwd["total_return"], 1.01 * 0.98 * 1.0 * 1.015 - 1)
        json.dumps([sheets, equity, monthly], allow_nan=False)
        self.assertTrue(all(e["equity"] is None or math.isfinite(e["equity"]) for e in equity))


if __name__ == "__main__":
    unittest.main()
