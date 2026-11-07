"""Invented-account checks for R309; no archived market outcomes are loaded."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from scripts import run_capital_mix as run


class CapitalMixTests(unittest.TestCase):
    def spot(self):
        net = np.array([.01, -.02])
        cost = np.array([.0012, .0024])
        nav = np.cumprod(1 + net)
        return pd.DataFrame({"date": ["2025-07-01", "2025-07-02"], "net": net,
                             "gross": net + cost, "cost_fraction": cost,
                             "nav": nav, "cash_end": [.5, nav[-1]], "turnover": [1, 2]})

    def test_spot_accounts_and_terminal_exit(self):
        a = self.spot()
        run.validate_spot(a, a.date, 1)
        bad = a.copy()
        bad.loc[0, "nav"] += .1
        with self.assertRaisesRegex(run.ContractError, "NAV"):
            run.validate_spot(bad, a.date, 1)
        bad = a.copy()
        bad.loc[1, "cash_end"] = .3
        with self.assertRaisesRegex(run.ContractError, "liquidation"):
            run.validate_spot(bad, a.date, 1)
        with self.assertRaisesRegex(run.ContractError, "fee/turnover"):
            run.validate_spot(a, a.date, 2)

    def test_carry_gross_is_already_divided_by_40(self):
        c = pd.DataFrame({"date": ["2025-07-01", "2025-07-02"],
                          "gross": [.01, -.02], "funding": [.009, .003],
                          "legs": [2, 40], "held": [1, 20]})
        c["net"] = c.gross - .00055 * c.legs / 40
        run.validate_carry(c, c.date, 1)
        bad = c.copy()
        bad["gross"] /= 40
        with self.assertRaisesRegex(run.ContractError, "normalization"):
            run.validate_carry(bad, c.date, 1)
        bad = c.copy()
        bad.loc[0, "held"] = 21
        with self.assertRaises(run.ContractError):
            run.validate_carry(bad, c.date, 1)

    def test_same_utc_interval_requires_carry_end_label_minus_one_day(self):
        raw = pd.DataFrame({"date": ["2025-07-01", "2025-07-02", "2026-10-01"],
                            "held": [3, 4, 20]})
        aligned = run.align_carry_dates(raw)
        self.assertEqual(aligned.date.tolist(), ["2025-06-30", "2025-07-01", "2026-09-30"])
        self.assertEqual(aligned[aligned.date == "2025-06-30"].held.iloc[0], 3)
        self.assertEqual(raw.date.iloc[0], "2025-07-01")
        for bad in ("2025-02-30", "2025-07-01T00:00:00Z"):
            with self.assertRaises(run.ContractError):
                run.align_carry_dates(pd.DataFrame({"date": [bad]}))

    def test_calendar_rejects_missing_duplicate_reordered(self):
        a = self.spot()
        for dates in (["2025-07-02", "2025-07-01"], ["2025-07-01"], ["2025-07-01"] * 2):
            with self.assertRaises(run.ContractError):
                run.validate_calendar(a, dates)
        bad = a.copy()
        bad.loc[1, "date"] = bad.loc[0, "date"]
        with self.assertRaises(run.ContractError):
            run.validate_calendar(bad, bad.date)

    def test_equal_paths_have_zero_paired_difference_and_ci(self):
        r = np.array([.01, -.02, .003, .007, -.002] * 8)
        p = {"net": r, "dollar_net": r.copy()}
        paths = {(1, name): p for name in ("carry_trend", "carry", "trend", "carry_passive_matched", "carry_cash")}
        a = run.paired_bootstrap(paths, 10, reps=40)
        self.assertEqual(a, run.paired_bootstrap(paths, 10, reps=40))
        for row in a:
            for key in ("sharpe_difference", "sharpe_ci_low", "sharpe_ci_high",
                        "paired_initial_capital_mean_bp", "profit_ci_low_bp", "profit_ci_high_bp"):
                self.assertEqual(row[key], 0.)

    def test_positive_profit_cannot_rescue_failed_diversification(self):
        rows = []
        for m in (1, 2, 3):
            for name in run.BOOKS:
                rows.append({"cost_multiple": m, "book": name, "sharpe": 1.,
                             "max_drawdown_pct": 2., "ending_equity": 1.1})
        cis = [{"block": 30, "comparator": c, "sharpe_ci_low": -.1}
               for c in ("carry", "trend", "carry_passive_matched")]
        verdict = run.decide(rows, cis)
        self.assertEqual(verdict["verdict"], "NULL")
        self.assertTrue(verdict["gates"]["positive_profit_at_2x_and_3x"])
        self.assertFalse(verdict["gates"]["sharpe_above_both_parents_by_015"])

    def test_existing_output_rejected_before_loading_outcomes(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(run, "verify_inputs", return_value=("abc", {})), patch.object(run, "load_inputs") as load:
                with self.assertRaisesRegex(run.ContractError, "exists"):
                    run.run(Path(d))
                load.assert_not_called()

    def test_frozen_manifest_mismatch_blocks_before_parse(self):
        from lab import prereg
        with tempfile.TemporaryDirectory() as d:
            lane = Path(d)
            (lane / "PREREG.md").write_text("unrelated\n")
            (lane / "inputs.json").write_text('{"sha256": {}}\n')
            prereg.freeze(lane / "PREREG.md")
            with self.assertRaisesRegex(run.ContractError, "manifest"):
                run.verify_inputs(lane, lane)

    def test_verified_input_contract_failure_records_inconclusive_only(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "fresh"
            with patch.object(run, "verify_inputs", return_value=("abc", {})), patch.object(
                    run, "load_inputs", side_effect=run.ContractError("missing UTC day")):
                result = run.run(out)
            self.assertEqual(result["verdict"], "INCONCLUSIVE")
            self.assertEqual(list(p.name for p in out.iterdir()), ["verdict.json"])
            self.assertEqual(json.loads((out / "verdict.json").read_text()), result)


if __name__ == "__main__":
    unittest.main()
