from decimal import Decimal as D
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lab.carry_execution import Book
from lab.eea_execution import normalize, execution_case
from scripts import run_eea_execution as runner


def simple(mid="100", available="100"):
    return Book(((D(mid) - 1, available),), ((D(mid) + 1, available),))


def measure(a=None, b=None, **kw):
    params = dict(target="100", contract_size="0.1", kraken_lot="0.01",
                  cde_notional_fee="0.0002", cde_contract_fee="0.12", kraken_fee="0.0005", multiple=1)
    params.update(kw)
    return execution_case(a or simple(), b or simple(), **params)


class EeaExecution(unittest.TestCase):
    def test_fixed_contract_charge_is_not_a_base_unit_fee(self):
        r = measure()
        cde_buy = r["directions"][0]["buy"]
        self.assertEqual(cde_buy["native_cde_contracts"], D(10))
        self.assertEqual(cde_buy["fee_fixed"], D("1.20"))
        self.assertEqual(cde_buy["fee"], D("1.2202"))

    def test_entry_directions_reconcile_one_round_trip_without_basis_profit(self):
        r = measure(b=simple("200"))
        self.assertEqual(r["quantity"], D("0.5"))
        self.assertEqual(r["same_snapshot_round_trip_cost"],
                         sum(d["complete_entry_cost"] for d in r["directions"]))
        self.assertGreater(r["same_snapshot_round_trip_cost"], 0)
        self.assertIsNone(r["pnl"])
        self.assertFalse(r["margin_admitted"])

    def test_partial_pair_keeps_unmatched_inventory_and_no_full_cost(self):
        r = measure(a=simple(available="0.2"))
        self.assertFalse(r["round_trip_complete"])
        self.assertIsNone(r["same_snapshot_round_trip_cost"])
        self.assertIsNone(r["directions"][0]["complete_entry_cost"])
        self.assertEqual(r["directions"][0]["unmatched_base"], D("-0.8"))
        self.assertEqual(r["directions"][1]["unmatched_base"], D("0.8"))

    def test_cost_scenarios_scale_drag_and_fixed_fee_not_liquidity(self):
        a, b, c = [measure(multiple=m) for m in (1, 2, 3)]
        self.assertEqual([r["quantity"] for r in (a, b, c)], [D(1)] * 3)
        for m, r in enumerate((a, b, c), 1):
            self.assertEqual(r["directions"][0]["book_cost"], D(2 * m))
            self.assertEqual(r["directions"][0]["buy"]["fee_fixed"], D("1.2") * m)
        self.assertLess(a["same_snapshot_round_trip_cost"], b["same_snapshot_round_trip_cost"])

    def test_size_conventions_are_distinct_and_not_chosen_by_result(self):
        raw = {"pricebook": {"bids": [{"price": "99", "size": "1"}],
                             "asks": [{"price": "101", "size": "1"}]}}
        contract = normalize(raw, "cde", "contracts", "0.1")
        base = normalize(raw, "cde", "base", "0.1")
        self.assertFalse(measure(a=contract)["round_trip_complete"])
        self.assertTrue(measure(a=base)["round_trip_complete"])

    def test_duplicate_levels_sum_and_zero_is_no_liquidity(self):
        raw = {"orderBook": {"bids": [["99", "0"], ["98", "2"], ["98", "3"]],
                              "asks": [["102", "1"]]}}
        r = normalize(raw, "kraken", "base", "0.1")
        self.assertEqual(r.bids, ((D(98), D(5)),))

    def test_fractional_displayed_contracts_refuse_unit_convention(self):
        with self.assertRaisesRegex(ValueError, "fractional displayed"):
            measure(a=simple(available="0.15"))

    def test_common_lot_and_target_round_down(self):
        r = measure(target="107", kraken_lot="0.03")
        self.assertEqual(r["common_lot"], D("0.3"))
        self.assertEqual(r["quantity"], D("0.9"))
        self.assertEqual(r["initial_segregated_cash"], D(214))

    def test_under_minimum_is_not_a_free_trade(self):
        r = measure(target="1")
        self.assertEqual(r["state"], "BLOCKED_MINIMUM")
        self.assertIsNone(r["same_snapshot_round_trip_cost"])

    def test_invalid_market_and_fee_inputs_refuse(self):
        for fee in [None, "-0.1", "NaN"]:
            with self.subTest(fee=fee), self.assertRaises(ValueError):
                measure(cde_contract_fee=fee)
        raw = {"pricebook": {"bids": [{"price": "101", "size": "1"}],
                             "asks": [{"price": "100", "size": "1"}]}}
        with self.assertRaises(ValueError):
            normalize(raw, "cde", "contracts", "0.1")

    def test_failed_registered_run_cannot_retry_or_discard_its_marker(self):
        with tempfile.TemporaryDirectory() as d:
            lane = Path(d)
            (lane / "cases.json").write_text("{}")
            with patch.object(runner, "LANE", lane), patch.object(runner, "verify", return_value="a" * 64), \
                    patch.object(runner.subprocess, "check_output", return_value="synthetic\n"), \
                    patch.object(runner, "load_packet", side_effect=ValueError("synthetic incomplete capture")) as load:
                with self.assertRaisesRegex(ValueError, "incomplete capture"):
                    runner.main()
                self.assertTrue((lane / "results/RUN_STARTED.json").exists())
                self.assertTrue((lane / "results/ERROR.json").exists())
                with self.assertRaises(FileExistsError):
                    runner.main()
                self.assertEqual(load.call_count, 1)

    def test_source_hash_is_checked_before_decoding(self):
        with tempfile.TemporaryDirectory() as d:
            lane = Path(d)
            (lane / "source").mkdir()
            (lane / "source/x.body.gz").write_bytes(b"invalid compressed body")
            (lane / "source_manifest.json").write_text(json.dumps({"sha256": {"x.body.gz": "0" * 64}}))
            with patch.object(runner, "LANE", lane), self.assertRaisesRegex(ValueError, "copied source drift"):
                runner.load_packet()


if __name__ == "__main__":
    unittest.main()
