"""R231 synthetic accounting/timing/provenance checks, with no market reads."""
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from scripts import run_partial_execution as runner


class PartialAccount(unittest.TestCase):
    def test_adjustment_starts_from_drifted_weights(self):
        weights = runner.adjusted_weights(np.array([.5, .5]), 0., np.array([2., 1.]),
                                          np.array([.5, .5]), .25)
        np.testing.assert_allclose(weights, .75*np.array([2/3, 1/3])+.25*np.array([.5, .5]))

    def test_zero_step_preserves_units_and_charges_no_cost(self):
        units, prices = np.array([.5, .5]), np.array([2., 1.])
        weights = runner.adjusted_weights(units, .4, prices, np.zeros(2), 0.)
        updated, cash, fee, _ = runner.base.rebalance(units, .4, prices, weights, .0036)
        np.testing.assert_allclose(updated, units, atol=1e-15)
        self.assertAlmostEqual(cash, .4)
        self.assertLess(fee, 1e-16)

    def test_full_step_is_unchanged_target(self):
        target = np.array([.2, .3])
        np.testing.assert_array_equal(runner.adjusted_weights(np.array([2., 3.]), 1.,
                                      np.array([4., 5.]), target, 1.), target)

    def test_scaled_control_target_is_fixed_not_scaled_old_holdings(self):
        np.testing.assert_allclose(runner.adjusted_weights(np.array([2., 3.]), 1.,
                                   np.array([4., 5.]), np.array([.4, .2]), 1., .3), [.12, .06])

    def test_entry_post_cost_fraction_and_final_liquidation(self):
        dates = runner.base.date_range("2024-01-01", "2024-01-05")
        close, target = np.ones((4, 6))*100, np.ones((4, 6))/6
        cost = .0036
        rows = runner.simulate(close, dates, 2, 3, cost, target, .25)
        expected = (1-.25*cost)/(1+.25*cost)
        self.assertAlmostEqual(rows[0]["nav"], expected)
        self.assertAlmostEqual(rows[0]["exposure"], .25)
        self.assertAlmostEqual(rows[0]["cash_end"], expected)
        self.assertGreater(rows[0]["cost_dollars"], 0)

    def test_exit_target_is_partially_approached_then_split_forces_exit(self):
        dates = runner.base.date_range("2024-01-01", "2024-01-07")
        close, target = np.ones((6, 6))*100, np.zeros((6, 6))
        target[0] = 1/6
        rows = runner.simulate(close, dates, 2, 5, 0., target, .5)
        np.testing.assert_allclose([row["exposure"] for row in rows], [.5, .25, .125])
        self.assertAlmostEqual(rows[-1]["cash_end"], 1.)

    def test_two_day_delay_excludes_newly_observed_target(self):
        dates = runner.base.date_range("2024-01-01", "2024-01-07")
        close, target = np.ones((6, 6))*100, np.zeros((6, 6))
        target[2] = 1/6
        rows = runner.simulate(close, dates, 3, 5, 0., target, .5)
        self.assertEqual(rows[0]["exposure"], 0.)
        self.assertAlmostEqual(rows[1]["exposure"], .5)

    def test_full_adjustment_matches_frozen_r229_on_synthetic_paths(self):
        rng = np.random.default_rng(204)
        dates = runner.base.date_range("2024-01-01", "2024-03-01")
        close = np.exp(rng.normal(0, .02, size=(len(dates), 6)).cumsum(axis=0))*100
        target = rng.dirichlet(np.ones(7), size=len(dates))[:, :6]
        for cost in (.0012, .0024, .0036):
            observed = runner.simulate(close, dates, 2, len(dates), cost, target)
            expected = runner.base.simulate(close, dates, 2, len(dates), cost, target)
            for x, y in zip(observed, expected):
                for key in ("net", "gross", "cost_fraction", "cost_dollars", "turnover", "nav", "exposure"):
                    self.assertEqual(x[key], y[key])

    def test_daily_gross_cost_identity_and_no_borrowing(self):
        rng = np.random.default_rng(77)
        dates = runner.base.date_range("2024-01-01", "2024-02-01")
        close = np.exp(rng.normal(0, .1, size=(len(dates), 6)).cumsum(axis=0))*100
        target = rng.dirichlet(np.ones(7), size=len(dates))[:, :6]
        for fraction in (.25, .5):
            rows = runner.simulate(close, dates, 2, len(dates), .0036, target, fraction)
            for row in rows:
                self.assertAlmostEqual(row["net"], row["gross"]-row["cost_fraction"])
                self.assertGreaterEqual(row["cash_end"], 0.)
                self.assertLessEqual(row["exposure"], 1+1e-12)

    def test_unsafe_weights_fraction_scale_rejected(self):
        for fraction, scale, target in ((-.1, 1., [.2, .3]), (1.1, 1., [.2, .3]),
                                        (.5, 1.1, [.2, .3]), (.5, 1., [.7, .7]),
                                        (.5, 1., [float("nan"), .1])):
            with self.subTest(fraction=fraction, scale=scale, target=target):
                with self.assertRaises(runner.ContractError):
                    runner.adjusted_weights(np.zeros(2), 1., np.ones(2), np.array(target), fraction, scale)


def fake_rows(net):
    nav = np.cumprod(1+np.asarray(net))
    return [{"net": float(value), "nav": float(n), "gross": float(value)+.0001,
             "cost_fraction": .0001, "cost_dollars": .0001, "turnover": .1, "exposure": .2}
            for value, n in zip(net, nav)]


class StudyContract(unittest.TestCase):
    def test_discovery_selection_and_tie_preference(self):
        half = fake_rows([.01, -.003, .02])
        quarter = fake_rows([.01, -.003, .02])
        self.assertEqual(runner.select_fraction({"half": half, "quarter": quarter}), "half")
        quarter = fake_rows([.02, .001, .03])
        self.assertEqual(runner.select_fraction({"half": half, "quarter": quarter}), "quarter")

    def test_degenerate_discovery_is_inconclusive_not_new_policy(self):
        with self.assertRaises(runner.ContractError):
            runner.select_fraction({"half": fake_rows([0., 0.]), "quarter": fake_rows([.01, -.01])})

    def test_bootstrap_uses_new_reproducible_seed_and_preserves_mean(self):
        first = runner.paired_bootstrap(np.arange(70)*.00001, 30)
        self.assertEqual(first, runner.paired_bootstrap(np.arange(70)*.00001, 30))
        self.assertEqual(first["seed"], 20261020261)
        self.assertAlmostEqual(first["mean"], .000345)

    def test_nonempty_output_rejected_before_price_reader(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output/"old.txt").write_text("keep")
            with patch.object(runner.base, "load_prices") as reader:
                with self.assertRaises(runner.ContractError):
                    runner.run(output, output)
                reader.assert_not_called()

    def test_bad_registration_rejected_before_price_reader(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/"fresh"
            with patch.object(runner, "verify_registration", side_effect=runner.ContractError("wrong code")), \
                    patch.object(runner.base, "load_prices") as reader:
                with self.assertRaises(runner.ContractError):
                    runner.run(Path(directory), output)
                reader.assert_not_called()

    def test_archived_control_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"archived.csv"
            fields = ["strategy", "split", "cost_multiple", "date", "net", "gross", "cost_fraction",
                      "cost_dollars", "turnover", "exposure", "nav", "cash_end"]
            fields += ["units_"+s for s in runner.base.fetcher.SYMBOLS]
            old = dict.fromkeys(fields, 0.)
            old.update(strategy="trend_vol", split="discovery", cost_multiple=1, date="synthetic", net=.01)
            with path.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow(old)
            row = dict(old, net=.02, held_units=[0.]*6)
            with self.assertRaises(runner.ContractError):
                runner.verify_archived_control({("discovery", 1, "synthetic"): row}, path)

    def test_small_synthetic_pipeline_all_tiers_and_training_only_selection(self):
        dates = runner.base.date_range("2024-01-01", "2024-05-02")
        t = np.arange(len(dates))
        close = np.column_stack([100*np.exp(.001*t+.05*np.sin(t/(2+j))) for j in range(6)])
        splits = {"discovery": ("2024-04-01", "2024-04-11"),
                  "validation": ("2024-04-11", "2024-04-21"),
                  "known_holdout": ("2024-04-21", "2024-05-01")}
        changed = close.copy()
        changed[dates.index("2024-04-11"):] *= np.exp(.2*np.sin(t[dates.index("2024-04-11"):]))[:, None]
        with tempfile.TemporaryDirectory() as directory:
            results = []
            for index, prices in enumerate((close, changed)):
                output = Path(directory)/str(index)
                with patch.object(runner, "verify_registration", return_value={}), \
                        patch.object(runner.base, "SPLITS", splits), \
                        patch.object(runner.base, "load_prices", return_value=(dates, prices, {})), \
                        patch.object(runner, "verify_archived_control", return_value={"synthetic": True}):
                    results.append(runner.run(Path(directory), output))
                with (output/"metrics.csv").open() as handle:
                    self.assertEqual(len(list(csv.DictReader(handle))), 36)
                manifest = json.loads((output/"run_manifest.json").read_text())
                for name, digest in manifest["output_sha256"].items():
                    payload = (output/name).read_bytes()
                    self.assertEqual(runner.base.sha(payload), digest)
                    if name.endswith(".csv"):
                        self.assertNotIn(b"\r", payload)
            self.assertEqual(results[0]["selected_policy"], results[1]["selected_policy"])
            self.assertEqual(results[0]["discovery_risk_scale"], results[1]["discovery_risk_scale"])


if __name__ == "__main__":
    unittest.main()
