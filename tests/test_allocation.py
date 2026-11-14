"""Synthetic-only tests: this module never loads the project's outcome files."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/run_allocation.py"
SPEC = importlib.util.spec_from_file_location("allocation_runner", SCRIPT)
allocation = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = allocation
SPEC.loader.exec_module(allocation)


class AllocationTests(unittest.TestCase):
    def synthetic(self):
        rng = np.random.default_rng(852901)
        matrix = rng.normal(0.0003, 0.01, (allocation.N_DAYS, 3))
        arrays = {name: matrix[:, j] for j, name in enumerate(allocation.SOURCES)}
        summaries = {}
        for j, name in enumerate(allocation.SOURCES):
            for window, (a, b) in allocation.WINDOWS.items():
                for cm in (1, 2, 3):
                    summaries[(name, window, cm)] = {
                        "days": b - a,
                        "mean_bp_day": matrix[a:b, j].mean() * 1e4 - (cm - 1) * (j + 1),
                        "gross_exposure": 0.5 * (j + 1),
                    }
        return matrix, arrays, summaries

    def test_exact_family_and_deterministic_ids(self):
        family = allocation.candidates()
        self.assertEqual(len(family), 30)
        self.assertEqual(len(set(c.weights for c in family)), 30)
        self.assertEqual(sum(c.interior for c in family), 27)
        self.assertEqual([c.identifier for c in family], sorted(c.identifier for c in family))
        for c in family:
            self.assertAlmostEqual(sum(c.weights), 1.0)
            self.assertTrue(all(w >= 0 for w in c.weights))
        self.assertEqual(family[0].weights, (1.0, 0.0, 0.0))
        self.assertEqual(family[1].weights, (0.0, 1.0, 0.0))
        self.assertEqual(family[2].weights, (0.0, 0.0, 1.0))

    def test_selection_and_scale_use_discovery_only(self):
        matrix, _, _ = self.synthetic()
        before = allocation.choose_discovery(matrix)
        changed = matrix.copy()
        changed[allocation.WINDOWS["discovery"][1]:] *= np.array([1000, -100, 0])
        after = allocation.choose_discovery(changed)
        self.assertEqual(before, after)

    def test_exact_ties_choose_first_endpoint(self):
        # A single exactly identical endpoint comparison avoids rounding from
        # summing distinct weights in a numerical convex combination.
        x = np.linspace(-0.01, 0.02, allocation.N_DAYS)
        matrix = np.column_stack((x, x, x))
        endpoints = allocation.candidates()[:3]
        choice = allocation.choose_discovery(matrix, endpoints)
        self.assertEqual(choice["selected"].identifier, endpoints[0].identifier)
        self.assertEqual(choice["control"].identifier, endpoints[0].identifier)
        self.assertEqual(choice["control_scale"], 1.0)

    def test_drawdown_includes_zero_initial_equity(self):
        self.assertAlmostEqual(allocation.max_drawdown([-0.1, 0.03]), 0.1)
        self.assertAlmostEqual(allocation.max_drawdown([0.1, -0.2, 0.05]), 0.2)
        self.assertEqual(allocation.max_drawdown([0.1, 0.2]), 0.0)

    def test_sharpe_population_and_nw_parity(self):
        matrix, _, summaries = self.synthetic()
        one = allocation.candidates()[0]
        rows = allocation.candidate_rows(matrix, summaries, (one,))
        x = matrix[:1095, 0]
        self.assertAlmostEqual(rows[0]["annualized_sharpe"], x.mean() / x.std(ddof=0) * np.sqrt(365))
        self.assertEqual(rows[0]["t_nw10"], allocation.stats.newey_west_t(x, 10)[2])

    def test_stressed_means_only_never_fabricates_paths(self):
        matrix, _, summaries = self.synthetic()
        candidate = allocation.candidates()[3]
        rows = allocation.candidate_rows(matrix, summaries, (candidate,))
        for row in rows:
            if row["cost_multiple"] == 1:
                self.assertTrue(row["daily_path_available"])
                continue
            self.assertFalse(row["daily_path_available"])
            for key in ("annualized_sharpe", "t_nw10", "max_additive_drawdown", "bootstrap_interval"):
                self.assertEqual(row[key], allocation.NA)
            expected = sum(w * summaries[(name, row["window"], row["cost_multiple"])]["mean_bp_day"]
                           for name, w in zip(allocation.SOURCES, candidate.weights))
            self.assertAlmostEqual(row["mean_bp_day"], expected)

    def test_paired_bootstrap_identical_inputs_exact_zero(self):
        x = np.random.default_rng(111).normal(0.001, 0.01, 97)
        out = allocation.paired_bootstrap(x, x.copy(), 10, replicates=200)
        self.assertEqual(out["lower_95"], 0.0)
        self.assertEqual(out["upper_95"], 0.0)
        self.assertEqual(out["observed_sharpe_difference"], 0.0)

    def test_bootstrap_matches_declared_circular_blocks(self):
        n, block, reps, seed = 7, 3, 4, 177
        idx = allocation.circular_indices(n, block, reps, seed)
        rng = np.random.default_rng(seed)
        starts = rng.integers(0, n, size=(reps, 3))
        expected = np.array([[(start + offset) % n for start in row for offset in range(block)][:n]
                             for row in starts])
        np.testing.assert_array_equal(idx, expected)
        self.assertTrue(np.any((idx[:, :-1] == n - 1) & (idx[:, 1:] == 0)))

    def test_bootstrap_pairs_paths_and_is_deterministic(self):
        rng = np.random.default_rng(21)
        x, y = rng.normal(0.001, 0.02, (2, 111))
        result = allocation.paired_bootstrap(x, y, 30, replicates=200, seed=123)
        self.assertEqual(result, allocation.paired_bootstrap(x, y, 30, replicates=200, seed=123))
        idx = allocation.circular_indices(len(x), 30, 200, 123)
        delta = allocation.sharpe(x[idx], axis=1) - allocation.sharpe(y[idx], axis=1)
        low, high = np.percentile(delta, [2.5, 97.5])
        self.assertEqual(result["lower_95"], low)
        self.assertEqual(result["upper_95"], high)

    def test_undefined_bootstrap_is_not_silently_discarded(self):
        with self.assertRaises(allocation.ContractError):
            allocation.paired_bootstrap(np.zeros(20), np.arange(20), 10, replicates=10)

    def test_contract_rejects_missing_nonfinite_and_mismatched_inputs(self):
        _, arrays, summaries = self.synthetic()
        allocation.validate_inputs(arrays, summaries)
        with self.assertRaises(allocation.ContractError):
            allocation.validate_inputs({k: v for k, v in arrays.items() if k != "X2"}, summaries)
        bad = {k: v.copy() for k, v in arrays.items()}
        bad["A_C0"][0] = np.nan
        with self.assertRaises(allocation.ContractError):
            allocation.validate_inputs(bad, summaries)
        bad_summaries = {k: dict(v) for k, v in summaries.items()}
        bad_summaries[("A_C0", "validation", 1)]["mean_bp_day"] += 0.01
        with self.assertRaises(allocation.ContractError):
            allocation.validate_inputs(arrays, bad_summaries)

    def test_contract_rejects_nonlinear_or_negative_costs(self):
        _, arrays, summaries = self.synthetic()
        for change in (100.0, -0.25):
            altered = {k: dict(v) for k, v in summaries.items()}
            altered[("A_C0", "discovery", 2)]["mean_bp_day"] += change
            with self.assertRaises(allocation.ContractError):
                allocation.validate_inputs(arrays, altered)

    def test_missing_files_reject(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(allocation.ContractError):
                allocation.read_inputs(folder)
            with self.assertRaises(allocation.ContractError):
                allocation.sha256(Path(folder) / "missing")

    def test_unfrozen_guard_rejects_before_np_load(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(allocation.np, "load") as load:
            with self.assertRaises(allocation.prereg.PreregError):
                allocation.verify_guards(folder)
            load.assert_not_called()

    def test_wrong_runner_hash_rejects_before_np_load(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(allocation.np, "load") as load:
            root = Path(folder)
            spec = root / "experiments/allocation_v1/PREREG.md"
            spec.parent.mkdir(parents=True)
            spec.write_text("Runner SHA-256: `" + "0" * 64 + "`.\n")
            allocation.prereg.freeze(spec)
            with self.assertRaisesRegex(allocation.ContractError, "Runner hash"):
                allocation.verify_guards(root)
            load.assert_not_called()


if __name__ == "__main__":
    unittest.main()
