from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

from lab.fee_evidence import FeeEvidenceBook, FeeStatement, assess_fee, import_fee_statement


def payload(**updates):
    out = {'schema_version': 1, 'statement_id': 'fixture-fee', 'revision': 1,
           'venue': 'mexc', 'instrument': 'BTC_USDT', 'account_scope': 'redacted-paper-owner',
           'order_role': 'taker', 'order_class': 'regular_market', 'rate': '0.02',
           'rate_unit': 'percent', 'fee_asset': 'USDT', 'notional_asset': 'USDT',
           'source_identity': 'fixture:unsigned-fee-v1', 'evidence_level': 'owner_supplied_redacted',
           'source_time_ns': 80, 'valid_from_ns': 50, 'valid_until_ns': 1000,
           'promotional': False, 'entitlement_attested': False, 'entitlement_id': None,
           'quota_total_notional': None, 'quota_used_notional': None}
    out.update(updates); return out


def statement(*, received_ns=100, **updates):
    return FeeStatement.from_mapping(payload(**updates), received_ns=received_ns)


def request(**updates):
    out = {k: payload()[k] for k in ('venue', 'instrument', 'account_scope', 'order_role',
                                   'order_class', 'fee_asset', 'notional_asset')}
    out.update(entry_ns=200, exit_ns=300); out.update(updates); return out


def promo(**updates):
    p = {'promotional': True, 'entitlement_attested': True, 'entitlement_id': 'redacted-grant',
         'quota_total_notional': '1000', 'quota_used_notional': '100', 'rate': '0'}
    p.update(updates); return statement(**p)


class FeeEvidenceTests(unittest.TestCase):
    def test_same_entitlement_cannot_reset_quota_by_switching_instrument(self):
        book=FeeEvidenceBook();a=promo();book.add(a)
        first=book.assess(a.statement_id,request(),150,100,100,reserve=True,reservation_id='one')
        self.assertEqual(first['state'],'conditional')
        b=FeeStatement.from_mapping(payload(**{**a.to_mapping(),'statement_id':'other-export','instrument':'ETH_USDT'}),received_ns=110)
        book.add(b)
        second=book.assess(b.statement_id,request(instrument='ETH_USDT'),160,400,400,reserve=True,reservation_id='two')
        self.assertIn('round_trip_quota_insufficient',second['reasons'])

    def test_official_fee_units_charge_both_fill_notionals_and_never_authenticate(self):
        for rate, unit in [('0.0002', 'fraction'), ('0.02', 'percent'), ('2', 'bp')]:
            s = statement(rate=rate, rate_unit=unit)
            r = assess_fee(s, request(), 150, '30000', '32000')
            self.assertEqual(r['state'], 'conditional'); self.assertEqual(Decimal(r['entry_fee']), Decimal(6))
            self.assertEqual(Decimal(r['exit_fee']), Decimal('6.4')); self.assertEqual(Decimal(r['total_fee']), Decimal('12.4'))
            self.assertFalse(r['provider_authenticated']); self.assertFalse(r['account_effective_fee_verified'])
            self.assertTrue(r['usable_for_paper_assumption'])

    def test_explicit_zero_is_distinct_from_missing_rate_unknown_units_and_missing_statement(self):
        zero = assess_fee(statement(rate='0'), request(), 150, 100, 100)
        self.assertEqual(zero['total_fee'], '0'); self.assertEqual(zero['state'], 'conditional')
        for s in (None, statement(rate=None), statement(rate='0', rate_unit='unverified')):
            r = assess_fee(s, request(), 150, 100, 100)
            self.assertEqual(r['state'], 'unknown'); self.assertIsNone(r['rate_fraction']); self.assertNotIn('total_fee', r)

    def test_notional_and_fee_assets_cannot_be_relabelled_without_conversion(self):
        r = assess_fee(statement(fee_asset='MX'), request(fee_asset='MX'), 150, 100, 100)
        self.assertEqual(r['state'], 'unknown'); self.assertIn('fee_asset_conversion_unverified', r['reasons'])
        self.assertIsNone(r['rate_fraction']); self.assertNotIn('total_fee', r)

    def test_both_legs_must_fit_half_open_validity_and_evidence_must_precede_entry(self):
        s = statement(valid_until_ns=300)
        self.assertIn('entry_or_exit_outside_fee_validity', assess_fee(s, request(), 150, 100, 100)['reasons'])
        self.assertEqual(assess_fee(s, request(exit_ns=299), 150, 100, 100)['state'], 'conditional')
        late = statement(received_ns=210)
        self.assertIn('statement_not_known_before_decision_and_entry', assess_fee(late, request(), 220, 100, 100)['reasons'])
        self.assertIn('statement_not_known_before_decision_and_entry', assess_fee(statement(), request(), 99, 100, 100)['reasons'])
        unknown = assess_fee(statement(valid_until_ns=None), request(), 150, 100, 100)
        self.assertIn('fee_validity_interval_unknown', unknown['reasons'])

    def test_account_instrument_role_class_asset_mismatch_blocks_without_a_rate(self):
        for k, v in [('venue', 'lighter'), ('instrument', 'ETH_USDT'), ('account_scope', 'another-redacted-scope'),
                     ('order_role', 'maker'), ('order_class', 'TWAP'), ('fee_asset', 'USDC')]:
            r = assess_fee(statement(), request(**{k: v}), 150, 100, 100)
            self.assertEqual(r['state'], 'blocked'); self.assertIsNone(r['rate_fraction'])

    def test_public_promo_tag_and_unattested_or_unknown_quota_never_grant_free_trades(self):
        for s in (promo(evidence_level='public_schedule'), promo(entitlement_attested=False),
                  promo(quota_used_notional=None), promo(entitlement_id=None)):
            r = assess_fee(s, request(), 150, 100, 100)
            self.assertEqual(r['state'], 'unknown'); self.assertNotIn('total_fee', r)
        self.assertEqual(assess_fee(promo(), request(), 150, 100, 100)['state'], 'conditional')

    def test_entry_plus_exit_quota_and_external_usage_cannot_be_reduced(self):
        # 900 left: entry500 fits but round-trip1000 does not.
        r = assess_fee(promo(), request(), 150, 500, 500)
        self.assertIn('round_trip_quota_insufficient', r['reasons'])
        r = assess_fee(promo(), request(), 150, 450, 450, used_notional=0)
        self.assertEqual(r['quota_remaining_after_round_trip'], '0')
        with self.assertRaises(ValueError): assess_fee(promo(), request(), 150, 100, 0)

    def test_schema_and_numeric_errors_do_not_echo_unrecognized_values(self):
        sentinel = 'invented-not-a-real-secret-value'
        for extra in ({'api_key': sentinel}, {'received_ns': 1}, {'provider_authenticated': True}):
            with self.assertRaises(ValueError) as cm: FeeStatement.from_mapping(payload(**extra), received_ns=100)
            self.assertNotIn(sentinel, str(cm.exception))
        for change in ({'rate': True}, {'rate': 'NaN'}, {'revision': True}, {'rate': '-1'},
                       {'source_time_ns': 101}, {'evidence_level': 'provider_verified'}):
            with self.assertRaises(ValueError): statement(**change)

    def test_importer_uses_actual_observation_not_document_backdating_and_is_bounded(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'redacted_fees.json'; p.write_text(json.dumps(payload()))
            s = import_fee_statement(p, received_ns=250)
            self.assertEqual(s.received_ns, 250)
            self.assertEqual(assess_fee(s, request(), 260, 100, 100)['state'], 'unknown')
            p.write_text(json.dumps(payload(api_key='invented-sentinel')))
            with self.assertRaises(ValueError) as cm: import_fee_statement(p, received_ns=250)
            self.assertNotIn('invented-sentinel', str(cm.exception))
            p.write_text('{"schema_version":1,"schema_version":1}')
            with self.assertRaises(ValueError): import_fee_statement(p, received_ns=250)
            p.write_text(' '*65537)
            with self.assertRaises(ValueError): import_fee_statement(p, received_ns=250)
            q = Path(d)/'alias.json'; q.symlink_to(p)
            with self.assertRaises(ValueError): import_fee_statement(q)
            with self.assertRaises(ValueError): import_fee_statement(Path(d)/'credentials.json')


class EvidenceBookTests(unittest.TestCase):
    def test_reservations_are_atomic_idempotent_and_cover_complete_round_trip(self):
        b = FeeEvidenceBook(); b.add(promo())
        first = b.assess('fixture-fee', request(), 150, 200, 200, reserve=True, reservation_id='paper-order-1')
        duplicate = b.assess('fixture-fee', request(), 150, 200, 200, reserve=True, reservation_id='paper-order-1')
        self.assertEqual(first['quota_remaining_after_round_trip'], '500')
        self.assertEqual(duplicate['reservation_state'], 'duplicate'); self.assertEqual(duplicate['quota_reserved_notional_delta'], '0')
        conflict = b.assess('fixture-fee', request(), 150, 100, 100, reserve=True, reservation_id='paper-order-1')
        self.assertEqual(conflict['state'], 'blocked')
        next_ = b.assess('fixture-fee', request(), 150, 300, 300, reserve=True, reservation_id='paper-order-2')
        self.assertIn('round_trip_quota_insufficient', next_['reasons'])
        self.assertEqual(len(b.events), 5)

    def test_revision_cannot_reset_quota_and_new_statement_id_cannot_renew_same_grant(self):
        b = FeeEvidenceBook(); b.add(promo())
        b.assess('fixture-fee', request(), 150, 200, 200, reserve=True, reservation_id='one')
        revised = promo(revision=2, received_ns=160, source_time_ns=150, quota_used_notional='200')
        self.assertEqual(b.add(revised)['state'], 'added')
        self.assertIn('round_trip_quota_insufficient', b.assess('fixture-fee', request(), 170, 250, 250)['reasons'])
        newer = promo(statement_id='new-export', received_ns=170, quota_used_notional='0')
        self.assertEqual(b.add(newer)['state'], 'added')
        self.assertIn('round_trip_quota_insufficient', b.assess('new-export', request(), 180, 250, 250)['reasons'])
        reset = promo(statement_id='reset-export', received_ns=170, quota_total_notional='2000')
        self.assertEqual(b.add(reset)['state'], 'blocked')

    def test_conflicting_and_stale_revision_does_not_replace_first_claim_or_backfill_clock(self):
        b = FeeEvidenceBook(); b.add(statement())
        self.assertEqual(b.add(statement(rate='0'))['state'], 'blocked')
        self.assertEqual(b.add(statement(revision=2, valid_until_ns=2000))['state'], 'blocked')
        self.assertEqual(b.add(statement(revision=2, source_time_ns=70))['state'], 'blocked')
        future = statement(revision=2, rate='3', rate_unit='bp', received_ns=170, source_time_ns=160)
        self.assertEqual(b.add(future)['state'], 'added')
        old = b.assess('fixture-fee', request(), 150, 100, 100)
        new = b.assess('fixture-fee', request(), 180, 100, 100)
        self.assertEqual(Decimal(old['rate_fraction']), Decimal('.0002'))
        self.assertEqual(Decimal(new['rate_fraction']), Decimal('.0003'))
        self.assertEqual(b.assess('fixture-fee', request(), 170, 100, 100)['state'], 'blocked')

    def test_replay_retains_consumption_and_rejects_edited_history(self):
        b = FeeEvidenceBook(); b.add(promo())
        b.assess('fixture-fee', request(), 150, 200, 200, reserve=True, reservation_id='one')
        saved = json.loads(json.dumps(b.events)); restored = FeeEvidenceBook.replay(saved)
        self.assertEqual(restored.events, b.events)
        next_ = restored.assess('fixture-fee', request(), 150, 300, 300, reserve=True, reservation_id='two')
        self.assertIn('round_trip_quota_insufficient', next_['reasons'])
        edited = deepcopy(saved); edited[-1]['result']['quota_remaining_after_round_trip'] = '999'
        with self.assertRaises(ValueError): FeeEvidenceBook.replay(edited)
        external = b.events; external[0]['payload']['rate'] = '0.99'
        self.assertNotEqual(external, b.events)
