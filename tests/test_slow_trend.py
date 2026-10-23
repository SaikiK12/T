"""Synthetic-only tests: importing the runner never reads market inputs."""
import calendar
import csv
from datetime import datetime, timezone
import io
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import zipfile

import numpy as np

from scripts import run_slow_trend as runner


def archive_fixture(year=2024, month=1, edit=None, header=False):
    symbol = "BTCUSDT"
    name = f"{symbol}-1d-{year}-{month:02d}.zip"
    divisor = 1000 if year >= 2025 else 1
    rows = []
    for day in range(1, calendar.monthrange(year, month)[1]+1):
        opening = int(datetime(year, month, day, tzinfo=timezone.utc).timestamp()*1000)
        rows.append([str(opening*divisor), "100", "102", "98", "101", "10",
                     str((opening+runner.DAY_MS)*divisor-1), "1000", "5", "5", "500", "0"])
    if edit:
        edit(rows)
    text = io.StringIO()
    writer = csv.writer(text)
    if header:
        writer.writerow(sorted(runner.HEADERS)[0])
    writer.writerows(rows)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name[:-4]+".csv", text.getvalue())
    return output.getvalue(), name


class SourceContract(unittest.TestCase):
    def test_millisecond_complete_month(self):
        rows = runner.parse_archive(*archive_fixture())
        self.assertEqual(len(rows), 31)
        self.assertEqual(rows[0], ("2024-01-01", 101.0))

    def test_microsecond_complete_month(self):
        rows = runner.parse_archive(*archive_fixture(2025, 2, header=True))
        self.assertEqual((len(rows), rows[-1][0]), (28, "2025-02-28"))

    def test_wrong_timestamp_unit_rejected(self):
        def edit(rows):
            for row in rows:
                row[0], row[6] = str(int(row[0])//1000), str(int(row[6])//1000)
        with self.assertRaises(runner.ContractError):
            runner.parse_archive(*archive_fixture(2025, 1, edit))

    def test_missing_duplicate_schema_price_rejected(self):
        edits = [lambda r: r.pop(2), lambda r: r.__setitem__(2, r[1].copy()),
                 lambda r: r[0].pop(), lambda r: r[0].__setitem__(4, "nan"),
                 lambda r: r[0].__setitem__(2, "90"),
                 lambda r: r[0].__setitem__(5, "-1"),
                 lambda r: r[0].__setitem__(8, "1.5")]
        for edit in edits:
            with self.subTest(edit=edit), self.assertRaises(runner.ContractError):
                runner.parse_archive(*archive_fixture(edit=edit))

    def test_unknown_header_rejected(self):
        with self.assertRaises(runner.ContractError):
            runner.parse_archive(*archive_fixture(edit=lambda r: r.__setitem__(0, ["unknown"]*12)))

    def test_manifest_lock_rejected_before_archive_reader(self):
        with tempfile.TemporaryDirectory() as directory:
            lane = Path(directory)
            (lane/"DATA.sha256").write_text("0"*64)
            manifest = lane/"manifest.json"
            manifest.write_text("synthetic manifest")
            with patch.object(runner, "verify_registration", return_value=("a", "b", "c")), \
                    patch.object(runner.fetcher, "verify_manifest") as verify:
                with self.assertRaises(runner.ContractError):
                    runner.load_prices(manifest, lane, lane)
                verify.assert_not_called()

    def test_old_output_rejected_before_market_reader(self):
        with tempfile.TemporaryDirectory() as directory:
            lane = Path(directory)
            output = lane/"results"
            output.mkdir()
            (output/"verdict.json").write_text("preserved prior result")
            with patch.object(runner, "load_prices") as reader:
                with self.assertRaises(runner.ContractError):
                    runner.run(lane/"unused", lane, lane)
                reader.assert_not_called()
            self.assertEqual((output/"verdict.json").read_text(), "preserved prior result")

    def test_source_manifest_allowed_without_overwrite_permission(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output/"data_manifest.json").write_text("synthetic source identity")
            runner.verify_fresh_output(output)
            with self.assertRaises(FileExistsError):
                runner.write_json(output/"data_manifest.json", {})


class TrendState(unittest.TestCase):
    def test_current_inclusive_channel_tie_precedence(self):
        np.testing.assert_array_equal(runner.component_positions([10, 10, 10, 10], 3), [0, 0, 1, 1])

    def test_prior_stop_not_current_midpoint(self):
        positions = runner.component_positions([10, 12, 14, 13, 12.9], 3)
        np.testing.assert_array_equal(positions, [0, 0, 1, 1, 0])

    def test_stop_reset_on_reentry(self):
        positions = runner.component_positions([10, 12, 14, 13, 11, 10, 11, 10.75], 3)
        np.testing.assert_array_equal(positions, [0, 0, 1, 1, 0, 0, 1, 1])

    def test_future_changes_do_not_change_past_targets(self):
        t = np.arange(500)
        close = np.column_stack([100*np.exp(.0004*t+.03*np.sin(t/(8+j))) for j in range(6)])
        changed = close.copy()
        changed[400:] *= np.linspace(.2, 4, 100)[:, None]
        for name, original in runner.trend_targets(close).items():
            np.testing.assert_array_equal(original[:400], runner.trend_targets(changed)[name][:400])

    def test_ninety_returns_warmup_and_zero_vol_cap(self):
        targets = runner.trend_targets(np.full((100, 6), 10.0))
        self.assertTrue((targets["trend_vol"][:90] == 0).all())
        np.testing.assert_allclose(targets["trend_vol"][90], targets["trend_plain"][90])
        self.assertTrue((targets["trend_plain"].sum(1) <= 1+1e-12).all())

    def test_sample_std_and_calendar_annualization(self):
        t = np.arange(100)
        close = np.column_stack([100*np.exp(.002*t+.1*np.sin(t/2)) for _ in range(6)])
        targets = runner.trend_targets(close)
        vol = np.std(close[10:100, 0]/close[9:99, 0]-1, ddof=1)*np.sqrt(365)
        plain = targets["trend_plain"][-1]
        np.testing.assert_allclose(targets["trend_vol"][-1], plain*min(1, .25/vol))


class Account(unittest.TestCase):
    def test_exact_self_financing_entry_and_exit(self):
        cost = .0036
        units, cash, fee, traded = runner.rebalance(np.zeros(6), 1, np.ones(6)*100, np.ones(6)/6, cost)
        self.assertAlmostEqual(units@np.full(6, 100), 1/(1+cost))
        self.assertAlmostEqual(fee, cost/(1+cost))
        self.assertAlmostEqual(cash, 0)
        units, cash, exit_fee, _ = runner.rebalance(units, cash, np.ones(6)*100, np.zeros(6), cost)
        self.assertAlmostEqual(cash, (1-cost)/(1+cost))
        self.assertTrue((units == 0).all())

    def test_drifted_units_not_old_targets_determine_cost(self):
        units = np.array([.5, .5])
        prices = np.array([2., 1.])
        _, cash, fee, traded = runner.rebalance(units, 0, prices, np.array([.5, .5]), .01)
        self.assertGreater(traded, .49)
        self.assertGreater(fee, 0)
        self.assertGreaterEqual(cash, 0)

    def test_random_long_only_cash_nonnegative(self):
        rng = np.random.default_rng(998)
        units, cash = np.zeros(6), 1.0
        for _ in range(100):
            prices = np.exp(rng.normal(size=6))
            weights = rng.dirichlet(np.ones(7))[:6]
            before = cash+units@prices
            units, cash, fee, _ = runner.rebalance(units, cash, prices, weights, .0036)
            self.assertGreaterEqual(cash, 0)
            self.assertLess(abs(cash+units@prices+fee-before)/before, 1e-12)

    def test_invalid_borrowing_rejected(self):
        with self.assertRaises(runner.ContractError):
            runner.rebalance(np.zeros(2), 1, np.ones(2), np.ones(2), .0012)

    def test_two_day_delay_and_initial_final_fees(self):
        dates = runner.date_range("2024-01-01", "2024-01-09")
        close = np.full((8, 6), 100.)
        targets = np.zeros_like(close)
        targets[2] = 1/6
        rows = runner.simulate(close, dates, 4, 6, .0012, targets)
        self.assertAlmostEqual(rows[0]["exposure"], 1)
        self.assertAlmostEqual(rows[1]["exposure"], 0)
        self.assertAlmostEqual(rows[-1]["nav"], (1-.0012)/(1+.0012))
        self.assertGreater(rows[0]["cost_dollars"], 0)
        self.assertGreater(rows[1]["cost_dollars"], 0)

    def test_new_signal_unavailable_at_first_execution(self):
        dates = runner.date_range("2024-01-01", "2025-02-04")
        t = np.arange(len(dates))
        close = np.column_stack([100*np.exp(.001*t+.02*np.sin(t/(8+j))) for j in range(6)])
        changed = close.copy()
        changed[350] *= .1
        base_targets = runner.trend_targets(close)["trend_vol"]
        changed_targets = runner.trend_targets(changed)["trend_vol"]
        left = runner.simulate(close, dates, 351, 352, 0, base_targets)[0]
        right = runner.simulate(changed, dates, 351, 352, 0, changed_targets)[0]
        self.assertAlmostEqual(left["exposure"], right["exposure"])

    def test_passive_only_monthly_and_final_exit(self):
        dates = runner.date_range("2024-01-28", "2024-02-05")
        close = np.tile(np.array([100, 200, 100, 100, 100, 100.]), (8, 1))
        close[3:, 0] *= 2
        rows = runner.simulate(close, dates, 2, 8, .0012)
        self.assertEqual(rows[1]["cost_dollars"], 0)
        self.assertGreater(rows[2]["cost_dollars"], 0)  # February 1 rebalances drift.
        self.assertEqual(rows[3]["cost_dollars"], 0)
        self.assertGreater(rows[-1]["cost_dollars"], 0)
        self.assertAlmostEqual(rows[-1]["cash_end"], rows[-1]["nav"])

    def test_sample_scale_and_degenerate_discovery(self):
        self.assertAlmostEqual(runner.discovery_scale([.01, -.01, .02], [.04, -.04, .08]), .25)
        with self.assertRaises(runner.ContractError):
            runner.discovery_scale([0, 0], [1, 2])

    def test_full_synthetic_pipeline_discovery_scale_and_portable_csv(self):
        dates = runner.date_range("2021-01-01", "2026-10-01")
        t = np.arange(len(dates))
        close = np.column_stack([100*np.exp(.0003*t+.1*np.sin(t/(12+j))) for j in range(6)])
        changed = close.copy()
        validation_start = dates.index("2024-01-01")
        changed[validation_start:] *= np.exp(.2*np.sin(t[validation_start:]/3))[:, None]
        with tempfile.TemporaryDirectory() as directory:
            lane = Path(directory)
            scales = []
            for index, prices in enumerate((close, changed)):
                output = lane/f"synthetic_run_{index}"
                with patch.object(runner, "load_prices", return_value=(dates, prices, {})):
                    result = runner.run(lane/"unused.json", lane, lane, output)
                scales.append(result["discovery_risk_scale"])
                self.assertIn(result["verdict"], ("NULL", "PARTIAL"))
            self.assertEqual(scales[0], scales[1])
            for name in ("daily.csv", "metrics.csv", "paired_differences.csv"):
                payload = (output/name).read_bytes()
                self.assertNotIn(b"\r", payload)
            with (output/"metrics.csv").open() as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), 36)
            manifest = json.loads((output/"run_manifest.json").read_text())
            for name, digest in manifest["output_sha256"].items():
                self.assertEqual(runner.sha((output/name).read_bytes()), digest)

    def test_bootstrap_reproducible_and_initial_nav_drawdown(self):
        x = np.sin(np.arange(90))*.01
        self.assertEqual(runner.paired_bootstrap(x, 30), runner.paired_bootstrap(x, 30))
        rows = [{"net": -.1, "nav": .9, "cost_dollars": .01, "turnover": 1., "exposure": .5}]
        self.assertAlmostEqual(runner.metrics(rows)["max_drawdown"], .1)


if __name__ == "__main__":
    unittest.main()
