"""Synthetic-only R232 cadence, fixed-unit, accounting and research-contract checks."""
import csv
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from scripts import run_rebalancing as runner


def fixture():
    dates = runner.base.date_range("2024-01-01", "2024-02-08")
    t = np.arange(len(dates))
    close = np.column_stack([100*np.exp(.002*t+.05*np.sin(t/(2+j))) for j in range(6)])
    return dates, close


def fake_rows(net):
    nav = np.cumprod(1+np.asarray(net))
    return [{"net": float(x), "nav": float(n), "gross": float(x)+.0001, "cost_fraction": .0001,
             "cost_dollars": .0001, "turnover": .1, "exposure": 1., "rebalance": True}
            for x, n in zip(net, nav)]


class CadenceAccounting(unittest.TestCase):
    def test_calendar_monday_and_month_first(self):
        self.assertTrue(runner.scheduled("2024-01-01", "weekly"))
        self.assertFalse(runner.scheduled("2024-01-02", "weekly"))
        self.assertTrue(runner.scheduled("2024-02-01", "monthly"))
        self.assertFalse(runner.scheduled("2024-02-02", "monthly"))
        self.assertTrue(runner.scheduled("2024-01-14", "daily"))
        self.assertFalse(runner.scheduled("2024-02-01", "buyhold"))

    def test_initial_entry_happens_even_off_cadence(self):
        dates, close = fixture()
        for cadence in ("weekly", "monthly", "buyhold"):
            rows = runner.simulate(close, dates, 2, 4, .0012, cadence)
            self.assertTrue(rows[0]["rebalance"])
            self.assertGreater(rows[0]["exposure"], .99)
            self.assertGreater(rows[0]["cost_dollars"], 0.)

    def test_buyhold_units_fixed_through_every_intermediate_day(self):
        dates, close = fixture()
        rows = runner.simulate(close, dates, 2, len(dates), .0012, "buyhold")
        for row in rows[1:]:
            np.testing.assert_array_equal(row["held_units"], rows[0]["held_units"])
            self.assertFalse(row["rebalance"])
        self.assertEqual(sum(r["cost_dollars"] for r in rows[1:-1]), 0.)

    def test_equal_weight_reset_uses_drifted_values(self):
        dates = runner.base.date_range("2024-01-01", "2024-01-06")
        close = np.ones((5, 6))*100
        close[2:, 0] = 200
        rows = runner.simulate(close, dates, 2, 5, .0012, "daily")
        self.assertGreater(rows[1]["turnover"], .2)
        self.assertGreater(rows[1]["cost_dollars"], 0.)
        np.testing.assert_allclose(np.array(rows[1]["held_units"])*close[2],
                                   np.ones(6)*(np.array(rows[1]["held_units"])@close[2])/6)

    def test_exact_initial_and_final_costs_on_constant_prices(self):
        dates = runner.base.date_range("2024-01-01", "2024-01-05")
        cost = .0036
        rows = runner.simulate(np.ones((4, 6))*100, dates, 2, 3, cost, "buyhold")
        self.assertAlmostEqual(rows[0]["nav"], (1-cost)/(1+cost))
        self.assertAlmostEqual(rows[0]["cash_end"], rows[0]["nav"])

    def test_monthly_reproduces_frozen_r229_passive_on_synthetic_path(self):
        dates, close = fixture()
        for cost in (.0012, .0024, .0036):
            observed = runner.simulate(close, dates, 2, len(dates), cost, "monthly")
            expected = runner.base.simulate(close, dates, 2, len(dates), cost)
            for x, y in zip(observed, expected):
                for field in ("net", "gross", "cost_fraction", "cost_dollars", "turnover", "exposure", "nav", "cash_end"):
                    self.assertEqual(x[field], y[field])

    def test_scaled_buyhold_cash_is_fixed_exposure_allowed_to_drift(self):
        dates, close = fixture()
        rows = runner.simulate(close, dates, 2, len(dates), .0012, "buyhold", .5)
        for row in rows[1:-1]:
            self.assertEqual(row["cash_end"], rows[0]["cash_end"])
        self.assertNotEqual(rows[1]["exposure"], .5)

    def test_reversal_example_can_earn_rebalancing_gain(self):
        dates = runner.base.date_range("2024-01-01", "2024-01-05")
        close = np.ones((4, 6))*100
        close[2, :2] = [200, 50]
        daily = runner.simulate(close, dates, 2, 4, 0., "daily")
        buyhold = runner.simulate(close, dates, 2, 4, 0., "buyhold")
        self.assertAlmostEqual(buyhold[-1]["nav"], 1.)
        self.assertAlmostEqual(daily[-1]["nav"], (6.5/6)**2)

    def test_costs_identity_and_no_borrowing_every_cadence(self):
        dates, close = fixture()
        for cadence in (*runner.CADENCES, "buyhold"):
            rows = runner.simulate(close, dates, 2, len(dates), .0036, cadence, .8)
            for row in rows:
                self.assertAlmostEqual(row["net"], row["gross"]-row["cost_fraction"])
                self.assertGreaterEqual(row["cash_end"], 0.)
                self.assertLessEqual(row["exposure"], 1.+1e-12)

    def test_future_prices_do_not_change_initial_trade(self):
        dates, close = fixture()
        changed = close.copy()
        changed[3:] *= 3
        for cadence in (*runner.CADENCES, "buyhold"):
            a = runner.simulate(close, dates, 2, len(dates), .0012, cadence)
            b = runner.simulate(changed, dates, 2, len(dates), .0012, cadence)
            self.assertEqual(a[0], b[0])

    def test_invalid_scale_universe_cadence_rejected(self):
        dates, close = fixture()
        for cadence, scale, prices in (("friday", 1., close), ("daily", 1.1, close),
                                        ("daily", -.1, close), ("daily", 1., close[:, :5])):
            with self.assertRaises(runner.ContractError):
                runner.simulate(prices, dates, 2, len(dates), .0012, cadence, scale)


class StudyContract(unittest.TestCase):
    def test_selection_exact_ties_favor_monthly_then_weekly(self):
        same = fake_rows([.01, -.003, .02])
        self.assertEqual(runner.select_cadence(dict.fromkeys(runner.CADENCES, same)), "monthly")
        weaker = fake_rows([.001, -.02, .01])
        self.assertEqual(runner.select_cadence({"daily": same, "weekly": same, "monthly": weaker}), "weekly")

    def test_symmetric_scaling_down_only(self):
        a, b = np.array([.01, -.02, .03]), np.array([.02, -.04, .06])
        self.assertEqual(runner.symmetric_scales(a, b), (1., .5))
        self.assertEqual(runner.symmetric_scales(b, a), (.5, 1.))
        with self.assertRaises(runner.ContractError):
            runner.symmetric_scales([0., 0.], [1., 2.])

    def test_circular_bootstrap_seed_repeatability(self):
        x = np.sin(np.arange(80))*.001
        self.assertEqual(runner.paired_bootstrap(x, 30), runner.paired_bootstrap(x, 30))
        self.assertEqual(runner.paired_bootstrap(x, 30)["seed"], 20261020262)

    def test_deterministic_gzip_and_output_overwrite_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            a, b = Path(directory)/"a.csv.gz", Path(directory)/"b.csv.gz"
            runner.write_csv(a, [{"x": 1., "y": "ok"}])
            runner.write_csv(b, [{"x": 1., "y": "ok"}])
            self.assertEqual(a.read_bytes(), b.read_bytes())
            self.assertEqual(gzip.decompress(a.read_bytes()), b"x,y\n1.0,ok\n")
            with self.assertRaises(FileExistsError):
                runner.write_csv(a, [{"x": 2.}])

    def test_old_output_rejected_before_price_reader(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output/"old.json").write_text("keep")
            with patch.object(runner.base, "load_prices") as reader:
                with self.assertRaises(runner.ContractError):
                    runner.run(output, output)
                reader.assert_not_called()

    def test_registration_failure_before_price_reader(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/"fresh"
            with patch.object(runner, "verify_registration", side_effect=runner.ContractError("bad source")), \
                    patch.object(runner.base, "load_prices") as reader:
                with self.assertRaises(runner.ContractError):
                    runner.run(Path(directory), output)
                reader.assert_not_called()

    def test_small_synthetic_pipeline_no_hindsight_selection_or_scales(self):
        dates = runner.base.date_range("2024-01-01", "2024-02-08")
        t = np.arange(len(dates))
        close = np.column_stack([100*np.exp(.002*t+.04*np.sin(t/(2+j))) for j in range(6)])
        changed = close.copy()
        changed[dates.index("2024-01-15"):] *= np.exp(.3*np.sin(t[dates.index("2024-01-15"):]))[:, None]
        splits = {"discovery": ("2024-01-03", "2024-01-15"),
                  "validation": ("2024-01-15", "2024-01-27"),
                  "known_holdout": ("2024-01-27", "2024-02-07")}
        with tempfile.TemporaryDirectory() as directory:
            results = []
            for index, prices in enumerate((close, changed)):
                output = Path(directory)/str(index)
                with patch.object(runner, "verify_registration", return_value={}), \
                        patch.object(runner.base, "SPLITS", splits), \
                        patch.object(runner.base, "load_prices", return_value=(dates, prices, {})), \
                        patch.object(runner, "verify_monthly", return_value={"synthetic": True}):
                    results.append(runner.run(Path(directory), output))
                with (output/"metrics.csv").open() as handle:
                    self.assertEqual(len(list(csv.DictReader(handle))), 54)
                manifest = json.loads((output/"run_manifest.json").read_text())
                for name, digest in manifest["output_sha256"].items():
                    self.assertEqual(runner.base.sha((output/name).read_bytes()), digest)
            for key in ("selected_cadence", "discovery_winner_scale", "discovery_buyhold_scale"):
                self.assertEqual(results[0][key], results[1][key])


if __name__ == "__main__":
    unittest.main()
