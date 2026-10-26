from copy import deepcopy
from decimal import Decimal as D
from pathlib import Path
import tempfile
import unittest

from lab.paper_controls import RiskPolicy,PaperRisk,entry_threshold
from lab.stream_quotes import FrameClock,NS

UTC=1790000000*NS;ANCHOR=FrameClock(UTC,10*NS)
def clock(s):return FrameClock(UTC+int(s*NS),ANCHOR.mono_ns+int(s*NS))
def snapshot(nav='1000',flow='0',positions=()):
    return {'simulation_only':True,'activation_allowed':False,'asof_mono_ns':clock(1).mono_ns,
        'accounts':[{'venue':'mexc','asset':'USDT','initial_cash':'1000','nav':nav,'external_capital_flows':flow,'positions':list(positions)}]}


class ControlsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'risk.jsonl'
    def guard(self,**kw):return PaperRisk(self.path,RiskPolicy('fixture',**kw),ANCHOR,contract_version='one',initial_balances={('mexc','USDT'):1000})
    def observe(self,g,s=None,**kw):
        d=dict(asof=clock(1).mono_ns,clock=clock(1),complete=True,session_open=True,fee_inputs_known=True,
            contract_version='one',expected_contract_version='one',mode='fixture')
        d.update(kw);return g.observe(s or snapshot(),**d)

    def test_threshold_requires_gross_quote_and_measured_error_at_all_costs(self):
        r=[entry_threshold(10,2,3,asset='USDT',cost_multiple=k,error_calibrated=True,extra_reserve_quote=1) for k in (1,2,3)]
        self.assertEqual([D(x['expected_net_lower_quote']) for x in r],[D(4),D(1),D(-2)])
        self.assertEqual([x['model_entry_allowed'] for x in r],[True,True,False]);self.assertTrue(all(not x['actual_order_allowed'] for x in r))
        self.assertFalse(entry_threshold(5,2,3,asset='USDT',error_calibrated=True)['model_entry_allowed'])
        for kw in ({'error_calibrated':False},{'prediction_unit':'variance'},{'prediction_unit':'quote_per_base'}):
            x=entry_threshold(10,2,3,asset='USDT',**kw);self.assertIsNone(x['expected_net_lower_quote'])
        self.assertIsNone(entry_threshold(10,2,None,asset='USDT',error_calibrated=True)['required_gross_quote'])

    def test_loss_and_drawdown_stay_stopped_after_reopen_and_deposit(self):
        g=self.guard();self.assertTrue(self.observe(g)['model_new_entries_allowed'])
        s=snapshot('960');r=self.observe(g,s);self.assertIn('risk:loss_limit',r['stops']);self.assertIn('risk:drawdown_limit',r['stops'])
        prefix=self.path.read_bytes();g=self.guard();r=self.observe(g,snapshot('1160','200'))
        self.assertFalse(r['model_new_entries_allowed']);self.assertTrue(self.path.read_bytes().startswith(prefix))
        self.assertFalse(r['automatic_flatten_performed']);self.assertTrue(r['positions_retained'])

    def test_gain_high_water_and_currency_separation(self):
        g=self.guard();self.observe(g,snapshot('1100'))
        r=self.observe(g,snapshot('1075'));self.assertIn('risk:drawdown_limit',r['stops'])
        self.assertNotIn('risk:loss_limit',r['new_stops'])
        # Another asset's profit cannot offset a losing venue/asset.
        g=PaperRisk(Path(self.tmp.name)/'separate.jsonl',RiskPolicy('different'),ANCHOR,contract_version='one',initial_balances={('mexc','USDT'):1000,('lighter','USDC'):1000})
        s=snapshot('960');s['accounts'].append({**s['accounts'][0],'venue':'lighter','asset':'USDC','nav':'1400'})
        r=self.observe(g,s);self.assertIn('risk:loss_limit',r['stops']);self.assertEqual(len(r['accounts']),2)

    def test_hedged_net_delta_does_not_remove_gross_concentration(self):
        positions=[{'symbol':'BTC','quantity_base':q,'average_entry':'100','unrealized_liquidation_pnl':'0'} for q in ('2','-2')]
        r=self.observe(self.guard(),snapshot(positions=positions))
        self.assertIn('risk:symbol_concentration_limit',r['stops']);self.assertEqual(r['accounts'][0]['gross_notional'],'400')

    def test_missing_mark_fee_session_rule_or_future_data_halts_without_exit(self):
        for i,change in enumerate(({'complete':False},{'session_open':False},{'fee_inputs_known':False},
                                  {'contract_version':'changed'},{'clock':clock(2)},{'mode':'historical'})):
            g=PaperRisk(Path(self.tmp.name)/str(i),RiskPolicy('p'),ANCHOR,contract_version='one',initial_balances={('mexc','USDT'):1000});r=self.observe(g,**change)
            self.assertEqual(r['state'],'HALTED');self.assertFalse(r['automatic_flatten_performed'])
        g=PaperRisk(Path(self.tmp.name)/'mark',RiskPolicy('p'),ANCHOR,contract_version='one',initial_balances={('mexc','USDT'):1000})
        s=snapshot(nav=None,positions=[{'symbol':'BTC','quantity_base':'1','average_entry':'100','unrealized_liquidation_pnl':None}])
        r=self.observe(g,s);self.assertFalse(r['accounts'][0]['gross_notional_complete']);self.assertIsNone(r['accounts'][0]['net_pnl'])

    def test_partial_pair_and_changed_baseline_or_policy_are_not_silently_accepted(self):
        g=self.guard();s=snapshot();s['pair']={'state':'pending_orders','net_delta_base':'0'}
        self.assertIn('risk:pair_exposure_or_orders_unreconciled',self.observe(g,s)['stops'])
        s=snapshot();s['accounts'][0]['initial_cash']='2000'
        with self.assertRaises(ValueError):self.observe(g,s)
        with self.assertRaises(ValueError):self.guard(max_loss_fraction='.10')
        with self.assertRaises(ValueError):self.observe(g,asof=clock(0).mono_ns,clock=clock(0))

    def test_malformed_nonfinite_and_duplicate_accounts_fail(self):
        for values in ((10,True,3),(10,2,-1),(10,'NaN',3)):
            with self.assertRaises(ValueError):entry_threshold(*values,asset='USDT',error_calibrated=True)
        s=snapshot();s['accounts']*=2
        with self.assertRaises(ValueError):self.observe(self.guard(),s)
        with self.assertRaises(ValueError):RiskPolicy('leveraged',max_symbol_gross_fraction=2)

    def test_registered_rules_positions_and_account_set_cannot_disappear_or_reset(self):
        g=self.guard();self.observe(g)
        self.assertIn('data:contract_rules_missing_or_changed',self.observe(g,contract_version='two',expected_contract_version='two')['stops'])
        with self.assertRaises(ValueError):PaperRisk(self.path,RiskPolicy('fixture'),ANCHOR,contract_version='two',initial_balances={('mexc','USDT'):1000})
        p=Path(self.tmp.name)/'missing';g=PaperRisk(p,RiskPolicy('two-venues'),ANCHOR,contract_version='one',initial_balances={('mexc','USDT'):1000,('lighter','USDC'):1000})
        s=snapshot();r=self.observe(g,s);self.assertIn('data:registered_account_set_incomplete_or_changed',r['stops'])
        self.assertTrue(any(a['gross_notional'] is None for a in r['accounts']))
        s=snapshot();del s['accounts'][0]['positions']
        r=self.observe(self.guard(),s);self.assertIn('data:positions_unknown',r['stops']);self.assertIsNone(r['accounts'][0]['gross_notional'])

