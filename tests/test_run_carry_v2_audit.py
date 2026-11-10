"""R437 runner: statistics and the frozen decision on synthetic inputs (no archive read)."""
import math
import tomllib
import unittest
from pathlib import Path

import numpy as np

from scripts import run_carry_v2_audit as r

ROOT = Path(__file__).resolve().parent.parent


class StatsTests(unittest.TestCase):
    def test_annualised_mean_halves_and_drawdown(self):
        x = np.array([0.001, -0.002, 0.001, 0.003])
        st = r.stats(x, np.arange(4), {1: x, 2: x - 0.0001, 3: x - 0.0002}, 2)
        self.assertAlmostEqual(st["ann_1x_pct"], x.mean() * 365 * 100)
        self.assertAlmostEqual(st["ann_2x_pct"], (x.mean() - 0.0001) * 365 * 100)
        self.assertAlmostEqual(st["half1_bp"], -5.0)
        self.assertAlmostEqual(st["half2_bp"], 20.0)
        self.assertAlmostEqual(st["recent_bp"], 20.0)
        self.assertAlmostEqual(st["max_dd_pct"], -0.2)

    def test_drawdown_counts_a_loss_from_the_start(self):
        x = np.array([-0.01, 0.005])
        st = r.stats(x, np.arange(2), {1: x, 2: x, 3: x}, 0)
        self.assertAlmostEqual(st["max_dd_pct"], -1.0)


class AuditTests(unittest.TestCase):
    def test_dry_audit_returns_one_record_per_book_with_a_frozen_decision(self):
        spec = tomllib.loads((ROOT / "experiments" / "xfund_v1" / "spec.toml").read_text())
        u1, u2 = r.synthetic(spec, nd=200, n=6)
        out, daily, trades = r.audit(u1, u2, {**spec, "start": "2021-01-01", "recent_from": "2021-04-01"},
                                     log=lambda m: None)
        self.assertEqual([x["book"] for x in out], [r.label(*b[:4]) for b in r.BOOKS])
        for x in out:
            want = (x["v2_nw_t_1x"] >= r.T_MIN and x["v2_mean_2x"] > 0 and x["v2_half1_bp"] > 0
                    and x["v2_half2_bp"] > 0)
            self.assertEqual(x["survives"], bool(want))
            shares = [x[f"v2_gross_share_{k}"] for k in ("spread", "dead", "blowout", "end")]
            if all(math.isfinite(s) for s in shares) and x["v2_trades"]:
                self.assertAlmostEqual(sum(shares), 1.0, places=6)

    def test_plumbing_reads_no_v2_return(self):
        spec = tomllib.loads((ROOT / "experiments" / "xfund_v1" / "spec.toml").read_text())
        u1, u2 = r.synthetic(spec, nd=120, n=4)
        out, daily, trades = r.audit(u1, u2, {**spec, "start": "2021-01-01", "recent_from": "2021-03-01"},
                                     plumbing=True, log=lambda m: None)
        self.assertFalse(any(k.startswith("v2_ann") or k == "survives" for x in out for k in x))
        self.assertEqual(daily, [])


if __name__ == "__main__":
    unittest.main()
