import json
from pathlib import Path
import tempfile
import unittest

from scripts.run_paper_account import run_case,funding_case,fee_cases,operations_cases,verify
from scripts.paper_account_view import render_report
from lab.stream_quotes import FrameClock

ROOT=Path(__file__).resolve().parents[1]


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.config=json.loads((ROOT/'experiments/paper_account_v1/fixtures.json').read_text())
        self.anchor=FrameClock(**self.config['anchor'])
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.path=Path(self.temp.name)

    def test_fee_assumption_replays_in_same_account_and_quota_does_not_renew(self):
        x=fee_cases(self.config['fee_statement'],self.anchor,self.path)
        self.assertEqual(x['linked_snapshot']['accounts'][0]['realized_net_pnl'],'-10.190')
        self.assertEqual(x['duplicate']['reserved_notional_delta'],'0')
        self.assertIn('round_trip_quota_insufficient',x['after_restart_quota']['reasons'])
        self.assertIsNone(x['missing']['rate_fraction']);self.assertFalse(x['regular']['account_effective_fee_verified'])

    def test_funding_uses_account_exposure_and_new_resolution_not_retroactive_zero(self):
        x=funding_case(self.config['funding'],self.anchor,self.path)
        mx=lambda key:next(a for a in x[key]['accounts'] if a['venue']=='mexc')
        self.assertIsNone(mx('unknown_snapshot')['cash']);self.assertEqual(x['bound_model']['cash_delta'],'0.030000')
        self.assertEqual(mx('resolved_snapshot')['cash'],'4999.730000')
        self.assertIsNone(mx('resolved_snapshot')['nav'])  # no executable current mark
        self.assertIsNone(x['lighter_missing_basis']['cash_delta'])
        self.assertFalse(x['lighter_declared_basis_only']['source_bridge_verified'])
        self.assertEqual(x['estimate_error']['error_fraction'],'-0.0001')

    def test_restarts_and_acquisition_limits_integrate_without_network_or_new_grant(self):
        x=operations_cases(self.config['operations'],self.anchor,self.path)
        self.assertFalse(x['budget_duplicate_after_restart']['dispatch_allowed'])
        self.assertTrue(x['budget_final']['new_dispatch_blocked'])
        self.assertEqual(x['historical_accumulated']['requests_charged'],7757)
        self.assertIsNone(x['historical_accumulated']['remaining_body_bytes'])
        self.assertEqual(x['after_gap']['state'],'invalid');self.assertEqual(x['stale_epoch']['status'],'stale_epoch')
        self.assertEqual(x['reopen_requires_new_transport']['state'],'invalid');self.assertEqual(x['network_requests'],0)

    def test_every_fixture_replays_and_unknowns_survive_view(self):
        for case in self.config['cases']:
            with self.subTest(case=case['name']):
                result=run_case(case,self.anchor,self.path)
                self.assertTrue(result['journal_replay_identical'])
                html=render_report({**result['snapshot'],'scope':'Invented <fixture>'})
                self.assertIn('Invented &lt;fixture&gt;',html)
                self.assertFalse(result['snapshot']['activation_allowed'])
                if case['name'] in ('missing_fee_and_mark','late_fill_reconciliation'):
                    mx=next(a for a in result['snapshot']['accounts'] if a['venue']=='mexc')
                    self.assertIsNone(mx['cash']);self.assertIsNone(mx['nav'])

    def test_unfrozen_or_drifted_spec_cannot_run_report(self):
        with self.assertRaises(Exception):verify(self.path)

