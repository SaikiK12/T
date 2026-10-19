import tempfile
import threading
import unittest
from datetime import date
from pathlib import Path

import numpy as np

from lab import config, gate, nulls, prereg, registry, stats

ROOT = Path(__file__).resolve().parent.parent


class SplitTests(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(config.split_of(date(2023, 12, 31)), "disc")
        self.assertEqual(config.split_of(date(2024, 1, 1)), "val")
        self.assertEqual(config.split_of(date(2025, 6, 30)), "val")
        self.assertEqual(config.split_of(date(2025, 7, 1)), "hold")


class NeweyWestTests(unittest.TestCase):
    def test_lag_zero_is_plain_t(self):
        x = np.random.default_rng(1).normal(0.01, 0.05, 400)
        n, mu, t = stats.newey_west_t(x, 0)
        self.assertEqual(n, 400)
        self.assertAlmostEqual(t, x.mean() / (x.std(ddof=0) / np.sqrt(400)), places=9)

    def test_autocorrelation_shrinks_t(self):
        rng = np.random.default_rng(2)
        e = rng.normal(0, 1, 2000)
        x = np.convolve(e, np.ones(7) / 7, mode="valid") + 0.05  # overlapping windows, like multi-day holds
        self.assertLess(abs(stats.newey_west_t(x, 7)[2]), abs(stats.newey_west_t(x, 0)[2]))

    def test_gaps_are_not_observations(self):
        x = np.full(100, np.nan)
        x[::2] = np.random.default_rng(3).normal(0.02, 0.05, 50)
        self.assertEqual(stats.newey_west_t(x, 3)[0], 50)

    def test_degenerate_inputs(self):
        self.assertTrue(np.isnan(stats.newey_west_t([np.nan, 0.1], 1)[2]))
        self.assertTrue(np.isnan(stats.newey_west_t([0.1, 0.1, 0.1], 1)[2]))


class NullTests(unittest.TestCase):
    def test_shifts_are_reproducible_and_in_range(self):
        a, b = nulls.null_shifts(2099, 60, 20261012), nulls.null_shifts(2099, 60, 20261012)
        self.assertEqual(a, b)
        self.assertEqual(a[0], 0)
        self.assertEqual(len(a), 61)
        self.assertTrue(all(180 <= s < 2099 - 180 for s in a[1:]))

    def test_shift_panel_moves_time_only(self):
        fwd = np.arange(2 * 10 * 3).reshape(2, 10, 3)
        out = nulls.shift_panel(fwd, 4)
        self.assertTrue(np.array_equal(out[:, 0], fwd[:, 4]))
        self.assertTrue(np.array_equal(nulls.shift_panel(fwd, 0), fwd))

    def test_verdict_and_familywise_p(self):
        null_counts = [0, 1, 1, 2, 3, 0, 1, 4, 1, 0] * 6
        self.assertEqual(nulls.search_verdict(2, null_counts)[0], "NOISE")
        self.assertEqual(nulls.search_verdict(9, null_counts)[0], "SIGNAL")
        self.assertEqual(nulls.familywise_p(3.0, [1.0, 2.0, 3.0, 4.0]), 0.6)
        self.assertEqual(nulls.familywise_p(99.0, [1.0, 2.0, 3.0, 4.0]), 0.2)

    def test_shifts_are_unique(self):
        shifts = nulls.null_shifts(2099, 60, 20261012)
        self.assertEqual(len(set(shifts[1:])), 60)

    def test_empty_familywise_null_is_undefined(self):
        self.assertTrue(np.isnan(nulls.familywise_p(1.0, [])))

    def test_invalid_null_statistics_cannot_look_significant(self):
        self.assertTrue(np.isnan(nulls.familywise_p(np.nan, np.arange(100.0))))
        with self.assertRaises(ValueError):
            nulls.familywise_p(10.0, [0.0, np.nan])


class GateTests(unittest.TestCase):
    def test_passes_when_every_rule_holds(self):
        r = [0.05] * 14 + [-0.02] * 6
        out = gate.go_real(r, entry_days=list(range(20)))
        self.assertTrue(out["pass"])
        self.assertEqual(out["n_clusters"], 20)

    def test_each_rule_can_block(self):
        self.assertFalse(gate.go_real([0.05] * 19)["pass"])                      # too few scored
        self.assertFalse(gate.go_real([-0.01] * 20)["pass"])                     # mean not positive
        self.assertFalse(gate.go_real([0.2] * 10 + [-0.01] * 10)["pass"])        # hit rate 50%
        self.assertFalse(gate.go_real([0.05] * 19 + [-0.41])["pass"])            # tail event
        self.assertFalse(gate.go_real([])["pass"])
        self.assertFalse(gate.go_real([0.1] * 20 + [np.inf])["pass"])

    def test_clusters_expose_correlated_tickets(self):
        out = gate.go_real([0.05] * 20, entry_days=["2026-10-13"] * 10 + ["2026-10-16"] * 10)
        self.assertTrue(out["pass"])
        self.assertEqual(out["n_clusters"], 2)


class PreregTests(unittest.TestCase):
    def test_freeze_verify_and_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            spec = Path(d) / "PREREG.md"
            spec.write_bytes(b"hypothesis\r\nCRLF kept\r\n")
            with self.assertRaises(prereg.PreregError):
                prereg.verify(spec)                       # no hash yet
            digest = prereg.freeze(spec)
            self.assertEqual(prereg.verify(spec), digest)
            self.assertEqual((Path(d) / "PREREG.sha256").stat().st_size, 65)
            with self.assertRaises(prereg.PreregError):
                prereg.freeze(spec)                       # never re-freeze
            spec.write_bytes(b"edited after freezing")
            with self.assertRaises(prereg.PreregError):
                prereg.verify(spec)


class RegistryTests(unittest.TestCase):
    def test_seed_file_is_valid(self):
        path = ROOT / "registry" / "rounds.csv"
        registry.validate(path)
        seed = [r for r in registry.rows(path) if int(r["id"][1:]) <= 183]   # rows imported from the original project
        self.assertEqual(sum(int(r["trials"]) for r in seed if r["trials"]), 139377)
        self.assertGreaterEqual(registry.program_trials(path), 139377)       # the journal only grows
        self.assertNotIn(b"\r", path.read_bytes())

    def test_ids_continue_and_never_repeat(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "rounds.csv"
            registry.append(path, id="R183", lane="a", title="t", status="DONE", verdict="NULL")
            self.assertEqual(registry.append(path, lane="b", title="t", status="PLANNED", verdict="PENDING",
                                             path="experiments/b"), "R184")
            self.assertEqual(registry.rows(path)[-1]["path"], "experiments/b")
            with self.assertRaises(registry.RegistryError):
                registry.append(path, id="R184", lane="c", title="t", status="DONE", verdict="NULL")
            with self.assertRaises(registry.RegistryError):
                registry.append(path, lane="c", title="t", status="MAYBE", verdict="NULL")
            registry.validate(path)

    def test_concurrent_writers_get_distinct_ids(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "rounds.csv"
            got = []

            def work():
                for _ in range(5):
                    got.append(registry.append(path, lane="x", title="t", status="PLANNED", verdict="PENDING"))

            threads = [threading.Thread(target=work) for _ in range(8)]
            [t.start() for t in threads]
            [t.join() for t in threads]
            self.assertEqual(len(set(got)), 40)
            registry.validate(path)


if __name__ == "__main__":
    unittest.main()
