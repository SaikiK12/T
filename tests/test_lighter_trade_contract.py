import copy
import unittest

from lab.lighter_trade_contract import canonicalize, evaluate
from scripts.check_lighter_trade_contract import identities, lot_integer


def fixture():
    return [dict(trade_id=10, t=1000, T=1, tx_us=100, ask_acct=1, bid_acct=2,
                 maker_ask=1, liq=0, sz=2, mpos=0, tpos=0),
            dict(trade_id=12, t=1100, T=1, tx_us=200, ask_acct=1, bid_acct=2,
                 maker_ask=0, liq=0, sz=1, mpos=2, tpos=-2),
            dict(trade_id=15, t=1200, T=1, tx_us=300, ask_acct=1, bid_acct=2,
                 maker_ask=1, liq=0, sz=3, mpos=-3, tpos=3)]


def score(rows):
    return evaluate(rows, 3, min_transitions=4, min_accounts=2, min_side_transitions=2)


class LighterTradeContractTest(unittest.TestCase):
    def test_signed_positions_identify_maker_side(self):
        r = score(fixture())
        self.assertEqual(r["verdict"], "SAMPLED_ROLE_CONTRACT_PASS")
        self.assertEqual(r["supported_hypothesis"], "true_is_maker_ask")
        self.assertEqual(r["hypotheses"]["true_is_maker_ask"]["exact_matches"], 4)
        self.assertGreater(r["hypotheses"]["true_is_taker_ask"]["mismatches"], 0)
        self.assertIsNone(r["pnl"])
        self.assertFalse(r["complete_feed_certified"])

    def test_opposite_source_mapping_can_pass_without_strategy_selection(self):
        rows = fixture()
        for row in rows:
            row["maker_ask"] = 1 - row["maker_ask"]
        self.assertEqual(score(rows)["supported_hypothesis"], "true_is_taker_ask")

    def test_new_accounts_are_insufficient_evidence(self):
        rows = fixture()
        for i, row in enumerate(rows):
            row["ask_acct"], row["bid_acct"] = i * 2 + 1, i * 2 + 2
        self.assertEqual(score(rows)["verdict"], "INCONCLUSIVE_COVERAGE")

    def test_corruption_is_retained_as_identity_mismatch(self):
        rows = fixture()
        rows[-1]["mpos"] = 37
        r = score(rows)
        self.assertEqual(r["verdict"], "UNQUALIFIED_POSITION_CONTRACT")
        self.assertTrue(any(x["residual_lots"] for x in r["hypotheses"]["true_is_maker_ask"]["identities"]))

    def test_liquidation_is_a_barrier_not_an_ignored_position_change(self):
        rows = fixture()
        rows[1]["liq"] = 1
        r = score(rows)
        self.assertEqual(r["hypotheses"]["true_is_maker_ask"]["transitions"], 0)
        self.assertEqual(r["hypotheses"]["true_is_maker_ask"]["liquidation_barriers"], 1)

    def test_unordered_storage_uses_the_frozen_transaction_order(self):
        self.assertEqual(score(list(reversed(fixture()))), score(fixture()))

    def test_duplicate_and_clock_conflict_are_rejected(self):
        for field, value in (("trade_id", 10), ("tx_us", 50), ("T", 0)):
            rows = fixture()
            rows[1][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                score(rows)

    def test_invalid_source_fields_fail_closed(self):
        for field, value in (("tpos", float("nan")), ("mpos", None), ("maker_ask", 2),
                             ("liq", None), ("tx_us", -1), ("sz", 0), ("ask_acct", 2)):
            rows = fixture()
            rows[1][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                score(rows)

    def test_lot_quantization_only_admits_tiny_serialization_noise(self):
        rows = fixture()
        rows[0]["sz"] = "2.000000000000001"
        self.assertEqual(score(rows)["verdict"], "SAMPLED_ROLE_CONTRACT_PASS")
        rows[0]["sz"] = "2.0004"
        with self.assertRaises(ValueError):
            score(rows)

    def test_both_sides_required_even_with_many_matching_identities(self):
        rows = fixture()
        for i, row in enumerate(rows):
            row["bid_acct"] = 100 + i
        r = evaluate(rows, 3, min_transitions=2, min_accounts=1, min_side_transitions=1)
        self.assertEqual(r["verdict"], "INCONCLUSIVE_COVERAGE")

    def test_inputs_are_not_mutated_or_price_consumed(self):
        rows = fixture()
        for row in rows:
            row["px"] = object()
        original = [{k: v for k, v in row.items() if k != "px"} for row in rows]
        score(rows)
        self.assertEqual([{k: v for k, v in row.items() if k != "px"} for row in rows], original)
        self.assertEqual(canonicalize(original, 3), canonicalize(copy.deepcopy(original), 3))

    def test_independent_account_history_check_finds_tampering(self):
        rows = fixture()
        native = score(rows)["hypotheses"]["true_is_maker_ask"]["identities"]
        expected = identities(rows, 3, "true_is_maker_ask")
        key = lambda x: (x["next_trade_id"], x["next_side"])
        self.assertEqual(sorted(native, key=key), expected)
        native[0]["next_before_lots"] += 1
        self.assertNotEqual(sorted(native, key=key), expected)
        self.assertEqual(lot_integer("-2.345", 3), -2345)
