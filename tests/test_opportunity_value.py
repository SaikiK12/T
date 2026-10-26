from dataclasses import replace
from decimal import Decimal as D
from fractions import Fraction as F
from pathlib import Path
import tempfile
import unittest
import gzip
import json
from unittest.mock import patch

from lab.microstructure import DepthLevel, DepthSnapshot
from lab.stream_quotes import FrameClock, StreamBook, NS
from lab.paper_account import PaperAccount, PaperEvent
from lab.paper_controls import PaperRisk, RiskPolicy
from lab.opportunity_value import Opportunity, Outcome, forecast_value, quote_cost, assess_batch

ANCHOR = FrameClock(1790000000*NS, 10*NS)
CLOCK = FrameClock(ANCHOR.utc_ns+NS, ANCHOR.mono_ns+NS)


def fixture(name='break', *, quantity='1', asset='USDT', venue='mexc', outcomes=None):
    return Opportunity(name, 'invented-'+name, venue, asset, 'ETH', D(quantity), CLOCK,
        CLOCK.utc_ns+12*3600*NS, outcomes or (Outcome('.9', '100', '0'), Outcome('.1', '-100', '0')),
        D(2), 'invented-calibration-not-market-evidence', D('.5'))


def book(o, *, asks=((100.5, 20),), bids=((99.5, 20),)):
    return StreamBook(o.venue, o.symbol, CLOCK,
        DepthSnapshot(o.symbol, CLOCK.utc_ns, CLOCK.mono_ns, tuple(DepthLevel(*x) for x in bids),
                      tuple(DepthLevel(*x) for x in asks)), 1, 'invented-book')


def market(o, asof=CLOCK.mono_ns):
    return {'state': 'pass', 'asof_mono_ns': asof, 'venue': o.venue, 'asset': o.asset,
            'symbol': o.symbol, 'quantity_base': str(abs(o.quantity)), 'scope': 'invented inputs only',
            'contract_model': 'linear_base', 'quote_asset': o.asset, 'step_base': '.1', 'min_base': '.1', 'max_base': '20',
            'valid_from_utc_ns': CLOCK.utc_ns, 'valid_until_utc_ns': CLOCK.utc_ns+NS,
            **{f: 'invented-not-authenticated' for f in ('source_identity', 'fee_source_identity', 'lot_source_identity',
                                                      'session_source_identity', 'settlement_source_identity')}}


def batch_case(opportunities, *, balances=None, policy=None, mutate=None, account_event=None):
    policy = policy or RiskPolicy('invented')
    balances = balances or {('mexc', 'USDT'): 1000}
    with tempfile.TemporaryDirectory() as d:
        account = PaperAccount(balances, ANCHOR, journal_path=Path(d)/'account.jsonl')
        if account_event: account.post(account_event, CLOCK.mono_ns)
        risk = PaperRisk(Path(d)/'risk.jsonl', policy, ANCHOR, contract_version='invented-v1', initial_balances=balances)
        inputs = dict(account=account, opportunities=opportunities,
            books={o.opportunity_id: book(o) for o in opportunities},
            fees_bp={o.opportunity_id: '10' for o in opportunities}, asof=CLOCK.mono_ns,
            anchor=ANCHOR, risk=risk, risk_inputs=dict(clock=CLOCK, complete=True, session_open=True,
                fee_inputs_known=True, contract_version='invented-v1', expected_contract_version='invented-v1', mode='fixture'),
            market_reports={o.opportunity_id: market(o) for o in opportunities})
        if mutate: mutate(inputs)
        prefix = (Path(d)/'account.jsonl').read_bytes()
        result = assess_batch(**inputs)
        if (Path(d)/'account.jsonl').read_bytes() != prefix: raise AssertionError('forecast changed journal')
        return result


class OpportunityTests(unittest.TestCase):
    def test_confidence_is_not_expected_profit_and_no_spread_double_count(self):
        o = fixture(outcomes=(Outcome('.7', '1', '0'), Outcome('.3', '-1', '0')))
        r = batch_case([o])['rows'][0]
        self.assertEqual(r['forecast']['expected_gross_quote'], '0.4')
        self.assertEqual(D(r['cost']['crossing_quote']), D(1))
        self.assertEqual(D(r['cost']['fee_quote']), D('.2'))
        # Independent exact-rational arithmetic, not the production threshold.
        for k, tier in enumerate(r['cost_tiers'], 1):
            self.assertEqual(F(tier['expected_net_lower_quote']), F(2, 5)-k*(F(6, 5)+F(1, 2))-2)
        self.assertFalse(r['conditional_batch_inclusion'])

    def test_positive_forecast_joins_cost_and_capital_without_crediting_cash(self):
        r = batch_case([fixture()]); row = r['rows'][0]
        self.assertTrue(row['conditional_batch_inclusion'])
        self.assertEqual(D(row['planned_capital_quote']), D('105.6'))
        self.assertEqual([D(x['expected_net_lower_quote']) for x in row['cost_tiers']], [D('76.3'), D('74.6'), D('72.9')])
        self.assertEqual(r['account_before'], r['account_after'])
        self.assertEqual(r['account_after']['accounts'][0]['cash'], '1000')
        self.assertFalse(r['durable_reservation_created']); self.assertFalse(r['activation_allowed'])

    def test_two_axes_cannot_reuse_capital_or_ignore_projected_concentration(self):
        rows = batch_case([fixture('break'), fixture('funding', outcomes=(Outcome(1, 0, 80),)), fixture('third')])['rows']
        self.assertEqual([r['conditional_batch_inclusion'] for r in rows], [True, True, False])
        self.assertIn('planned_symbol_concentration_limit', rows[-1]['reasons'])
        # More permissive concentration still cannot spend the same cash twice.
        p = RiskPolicy('invented', max_symbol_gross_fraction=1)
        r = batch_case([fixture('first', quantity=6), fixture('second', quantity=6)], policy=p)['rows']
        self.assertTrue(r[0]['conditional_batch_inclusion']); self.assertFalse(r[1]['conditional_batch_inclusion'])
        self.assertIn('batch_segregated_capital_exceeded', r[1]['reasons'])

    def test_unknown_or_wrong_units_never_become_zero(self):
        for change in ({'error_quote': None}, {'calibration_id': None}, {'exit_reserve_quote': None},
                       {'payoff_basis': 'already_net_of_spread'},
                       {'outcomes': (Outcome(1, 20, None),)}):
            row = batch_case([replace(fixture(), **change)])['rows'][0]
            self.assertFalse(row['conditional_batch_inclusion'])
        unknown = forecast_value(replace(fixture(), outcomes=(Outcome(1, 20, None),)))
        self.assertIsNone(unknown['expected_gross_quote'])
        self.assertEqual(D(unknown['expected_price_quote']), D(20))
        self.assertIsNone(unknown['expected_funding_quote'])
        self.assertIsNone(unknown['realized_pnl'])

    def test_stale_quotes_futures_session_fees_and_depth_block(self):
        for mutate in (lambda x: x['books'].__setitem__('break', None),
                       lambda x: x['fees_bp'].__setitem__('break', None),
                       lambda x: x['market_reports']['break'].update(state='unknown'),
                       lambda x: x['market_reports']['break'].pop('fee_source_identity'),
                       lambda x: x['market_reports']['break'].update(valid_until_utc_ns=CLOCK.utc_ns),
                       lambda x: x['market_reports']['break'].update(step_base='.3'),
                       lambda x: x['books'].__setitem__('break', replace(book(fixture()), clock=FrameClock(CLOCK.utc_ns+NS, CLOCK.mono_ns+NS))),
                       lambda x: x['books'].__setitem__('break', book(fixture(), asks=((100.5, .5),)))):
            self.assertFalse(batch_case([fixture()], mutate=mutate)['rows'][0]['conditional_batch_inclusion'])
        self.assertFalse(batch_case([replace(fixture(), clock=FrameClock(CLOCK.utc_ns+NS, CLOCK.mono_ns+NS))])['rows'][0]['conditional_batch_inclusion'])

    def test_currency_and_risk_stops_cannot_be_offset_by_other_venue(self):
        o = fixture(asset='USDC')
        self.assertFalse(batch_case([o])['rows'][0]['conditional_batch_inclusion'])
        loss = PaperEvent('loss', 'capital_change', 'mexc', 'USDT', 'ETH', CLOCK.utc_ns, CLOCK,
                          'invented withdrawal', amount='-900')
        # This is an external flow, not a loss; available cash still limits entry.
        r = batch_case([fixture()], account_event=loss)['rows'][0]
        self.assertIn('batch_segregated_capital_exceeded', r['reasons'])
        r = batch_case([fixture()], mutate=lambda x: x['risk_inputs'].update(complete=False))
        self.assertFalse(r['rows'][0]['conditional_batch_inclusion'])

    def test_short_and_multi_level_sweep_same_economic_cost(self):
        for q in ('1', '-1'):
            o = fixture(quantity=q)
            b = book(o, asks=((100.5, .5), (101.5, 1)), bids=((99.5, .5), (98.5, 1)))
            c = quote_cost(o, b, 10, CLOCK.mono_ns, ANCHOR)
            self.assertEqual(D(c['round_trip_quote']), D('2.2'))
            self.assertEqual(D(c['entry_notional_quote']), D(101 if q == '1' else 99))

    def test_malformed_distributions_scope_and_unknown_risk_fail_closed(self):
        with self.assertRaises(ValueError): fixture(outcomes=(Outcome('.9', 1, 0),))
        with self.assertRaises(ValueError): replace(fixture(), quantity=True)
        with self.assertRaises(ValueError): Outcome('NaN', 1, 0)
        with self.assertRaises(ValueError): batch_case([fixture(), fixture()])
        with self.assertRaises(ValueError): batch_case([fixture()], mutate=lambda x: x['books'].clear())
        r = batch_case([fixture()], mutate=lambda x: x['risk_inputs'].update(contract_version='changed'))
        self.assertFalse(r['rows'][0]['conditional_batch_inclusion'])

    def test_entire_invented_protocol_and_independent_oracle_before_freeze(self):
        from scripts import run_opportunity_value as run
        from scripts import check_opportunity_value as audit
        from lab import prereg
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); lane = root/'experiments/opportunity_value_v1'; lane.mkdir(parents=True)
            (lane/'fixtures.json').write_bytes((run.LANE/'fixtures.json').read_bytes())
            (lane/'code_inputs.json').write_bytes(run.encode({'python_version': list(run.sys.version_info[:3]), 'sha256': {}}))
            (lane/'data_inputs.json').write_bytes(run.encode({'sha256': {}}))
            (lane/'PREREG.md').write_text('\n'.join(prereg.sha256_file(lane/n) for n in ('fixtures.json', 'code_inputs.json', 'data_inputs.json')))
            prereg.freeze(lane/'PREREG.md')
            old = root/'experiments/paper_account_v1'; old.mkdir()
            invented = {'symbol': 'ETH', 'grid_second': 10, 'delay_ms': 0, 'readiness': {'state': 'unknown'},
                'sizes': [{'leg_budget_quote': '250', 'quantity_base': '1',
                    'cost': {'displayed_fillable': True, 'scenarios': [{'round_trip_cost_usd': k*2.5} for k in (1,2,3)]}},
                    {'leg_budget_quote': '500', 'quantity_base': None, 'cost': None}]}
            (old/'observations.jsonl.gz').write_bytes(gzip.compress(json.dumps(invented).encode(), mtime=0))
            with patch.object(run, 'ROOT', root), patch.object(audit, 'ROOT', root):
                out = root/'out'; run.report(out, lane)
                result = audit.check(out)
                self.assertTrue(result['passed']); self.assertEqual(result['invented_cases'], 15)
                self.assertEqual(result['held_cells'], 6)
                with self.assertRaises(ValueError): run.report(out, lane)
                p = out/'results.json'; value = json.loads(p.read_text())
                value['cases'][1]['rows'][0]['cost_tiers'][2]['expected_net_lower_quote'] = '999'
                p.write_bytes(run.encode(value))
                with self.assertRaises(ValueError): audit.check(out)


if __name__ == '__main__': unittest.main()
