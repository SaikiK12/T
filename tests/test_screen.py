import unittest
from types import SimpleNamespace

import numpy as np

from lab import panel, screen


def universe(alpha, seed=0, S=12):
    """Hourly 2021-01-01..2026-10-01; ret = noise + alpha * z where z is a per-coin state known at t."""
    t = np.arange(panel.ms("2021-01-01"), panel.ms("2026-10-01"), 3_600_000)
    T = len(t)
    rng = np.random.default_rng(seed)
    z = np.repeat(rng.standard_normal((T // 200 + 1, S)), 200, axis=0)[:T]
    ret = (0.004 * rng.standard_normal((T, S)) + alpha * z).astype(np.float32)
    return SimpleNamespace(p=SimpleNamespace(t=t), elig=np.ones((T, S), bool), ret=ret,
                           cmat=np.full((T, S), 0.0006, np.float32)), z


class TestScreen(unittest.TestCase):
    def test_planted_feature_passes_and_holdout_stays_unread(self):
        u, z = universe(alpha=2e-4)
        s = screen.Screen(u)
        books = s.spread(z)
        quiet = []
        rows, stage = s.staged("z/H", *books["H"], log=lambda *a: quiet.append(a))
        self.assertEqual(stage, {"reached": "validation", "passed": True})
        self.assertNotIn("holdout", {r["window"] for r in rows})
        self.assertEqual(len(rows), 6)                       # 2 windows x 3 cost multiples
        rows_l, stage_l = s.staged("z/L", *books["L"], log=lambda *a: None)
        self.assertEqual(stage_l, {"reached": "discovery", "passed": False})
        self.assertAlmostEqual(rows[0]["gross_bp_day"], -rows_l[0]["gross_bp_day"], places=6)

    def test_noise_feature_fails_discovery(self):
        u, _ = universe(alpha=0.0, seed=1)
        noise = np.random.default_rng(2).standard_normal(u.ret.shape)
        s = screen.Screen(u)
        _, stage = s.staged("noise/H", *s.spread(noise)["H"], log=lambda *a: None)
        self.assertEqual(stage, {"reached": "discovery", "passed": False})

    def test_holdout_is_read_only_when_allowed(self):
        u, z = universe(alpha=2e-4)
        s = screen.Screen(u)
        rows, stage = s.staged("z/H", *s.spread(z)["H"], holdout=True, log=lambda *a: None)
        self.assertEqual(stage["reached"], "holdout")
        self.assertEqual(s.rows["holdout"][1] % 24, s.rows["holdout"][0] % 24)

    def test_residual_against_reference(self):
        rng = np.random.default_rng(3)
        ref = rng.standard_normal(500) * 1e-3
        n = 2 * ref + 1e-4 + rng.standard_normal(500) * 1e-5
        days = panel.ms("2022-01-01") + np.arange(500) * 86_400_000
        st = screen.window_stats(n, days, ref)
        self.assertAlmostEqual(st["beta_ref"], 2.0, places=2)
        self.assertAlmostEqual(st["resid_bp_day"], 1.0, places=1)
        self.assertEqual(set(st["by_year_bp_day"]), {2022, 2023})


if __name__ == "__main__":
    unittest.main()
