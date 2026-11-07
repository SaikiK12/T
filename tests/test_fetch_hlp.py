import unittest

import numpy as np

from scripts import fetch_hlp


def portfolio(av, pnl, step_ms=14 * 86_400_000, t0=1_704_844_800_000):
    hist = lambda xs: [[t0 + i * step_ms, str(x)] for i, x in enumerate(xs)]
    return [["allTime", {"accountValueHistory": hist(av), "pnlHistory": hist(pnl), "vlm": "0"}]]


class FetchHlpTest(unittest.TestCase):
    def test_step_return_is_pnl_change_over_previous_account_value(self):
        p = portfolio(av=[0, 100, 220, 210], pnl=[0, 0, 10, 0])
        r = fetch_hlp.steps(p, "allTime")
        self.assertEqual(len(r), 2)                                      # no return from an empty vault
        self.assertTrue(np.allclose(r.values, [0.10, -10 / 220]))        # a deposit (100 -> 220) is not a return

    def test_summary_compounds_by_year_and_finds_the_drawdown(self):
        p = portfolio(av=[100] * 6, pnl=[0, 10, 20, 15, 25, 35])
        s = fetch_hlp.summary(fetch_hlp.steps(p, "allTime"))
        self.assertEqual(s["steps"], 5)
        self.assertEqual(s["negative_steps"], 1)
        self.assertAlmostEqual(s["max_drawdown_seen"], -0.05)
        total = np.prod([1.1, 1.1, 0.95, 1.1, 1.1]) - 1
        self.assertAlmostEqual(sum(s["by_year"].values()), total)        # all steps fall in 2024


if __name__ == "__main__":
    unittest.main()
