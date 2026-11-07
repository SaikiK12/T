import copy
from decimal import Decimal
import unittest
from pathlib import Path
import tempfile
import json
import gzip
from unittest.mock import patch
import numpy as np
import pandas as pd
from lab.level_probability import HOUR,DAY,market,signal,outcome,fit,score,replay,prediction


class LevelProbabilityTests(unittest.TestCase):
    def source(self):
        t=np.arange(100)*HOUR
        p=pd.DataFrame(dict(t=t,close=np.r_[100+np.sin(np.arange(72)),99.,100.,np.repeat(101.,26)],vol=1.))
        f=pd.DataFrame(dict(t=np.arange(0,101,8)*HOUR,rate=.001,cycle_h=8))
        return market(p,f,0,100*HOUR)

    def event(self,m):
        return dict(decision=3*DAY,state='event',reason=None,index=72,side=1,level=100.,sigma=.01,cell='approach')

    def model(self):
        return dict(probability=[.7,.2,.1],class_payoff_means=[1.,-1.,0.],cells={x:dict(probability=[.7,.2,.1]) for x in ('approach','recede')})

    def test_causal_level_and_volume_invalidity(self):
        m=self.source();s=signal(m,3*DAY)
        # Future mutation cannot change a signal or its approach cell.
        n=copy.deepcopy(m);n['close'][73:]=1e9;n['valid'][73:]=False
        self.assertEqual(s,signal(n,3*DAY))
        m['valid'][70]=False;self.assertEqual(signal(m,3*DAY)['reason'],'feature_price_or_volume_gap')

    def test_hour_delay_overshoot_and_funding_entry_exclusion(self):
        m=self.source();m['close'][73:76]=[100.,100.5,102.]
        m['funding_known'][:]=True;m['rate'][:]=0;m['rate'][73]=.9;m['rate'][75]=.001
        o=outcome(m,self.event(m));self.assertEqual(o['entry'],100);self.assertEqual(o['exit'],102)
        self.assertEqual(o['label'],'break');self.assertAlmostEqual(o['price_outside'],.02)
        self.assertAlmostEqual(o['funding_outside'],-.00102)
        self.assertEqual(len(o['funding_events']),1)

    def test_gap_and_missing_funding_are_not_zero(self):
        m=self.source();s=self.event(m);m['valid'][74]=False
        o=outcome(m,s);self.assertIsNone(o['exit']);self.assertIsNone(o['label'])
        m=self.source();m['funding_known'][:]=False
        o=outcome(m,s);self.assertIsNotNone(o['label']);self.assertFalse(o['financial_known']);self.assertIsNone(o['funding_outside'])

    def test_strict_schedule_and_duplicate_guard(self):
        p=pd.DataFrame(dict(t=np.arange(26)*HOUR,close=100.,vol=1.))
        f=pd.DataFrame(dict(t=np.array([0,8,24])*HOUR,rate=0.,cycle_h=8))
        m=market(p,f,0,26*HOUR);self.assertTrue(m['funding_known'][1:9].all());self.assertFalse(m['funding_known'][9:24].any())
        with self.assertRaises(ValueError):market(pd.concat([p,p.iloc[:1]]),f,0,26*HOUR)

    def test_sparse_model_and_payoff_not_just_win_rate(self):
        self.assertIsNone(fit([])['probability'])
        model=self.model();s=self.event(self.source());s['sigma']=.01
        p=prediction(model,s,'conditional');self.assertEqual(p['direction'],0)  # .005 < cost+.0025reserve
        model['class_payoff_means']=[.1,-3.,0.]
        self.assertLess(prediction(model,s,'conditional')['expected_outside'],0)

    def test_full_constructed_model_score_account_protocol(self):
        m=self.source();m['funding_known'][:]=True;m['rate'][:]=0
        m['close'][73:76]=[100.,100.5,102.]
        s=self.event(m);o=outcome(m,s);rows=[dict(symbol='TOY',signal=s,outcome=o)]
        model=self.model();result=score(rows,model)
        self.assertAlmostEqual(result['conditional']['brier'],.14)
        accounts=replay(rows,model,3*DAY,4*DAY)
        self.assertEqual(len(accounts),18)
        for a in accounts:
            self.assertEqual(a['initial_capital'],'10000');self.assertTrue(a['complete'])
            self.assertFalse(a['actual_order_allowed']);self.assertIsNone(a['actual_executable_net'])
        cells={a['cost_multiple']:a for a in accounts if a['policy']=='always_break'}
        # q=5; gain10, funding0, cost(.4+.408)*tier. One common10k account.
        for k,a in cells.items():self.assertEqual(Decimal(a['conditional_net']),Decimal(10)-Decimal('.808')*k)
        self.assertEqual([a['tickets'][0]['direction'] for a in cells.values()],[1,1,1])
        with self.assertRaises(ValueError):replay(rows+rows,model,3*DAY,4*DAY)

    def test_persistent_unknown_and_no_fictitious_close(self):
        m=self.source();m['valid'][74]=False;s=self.event(m)
        rows=[dict(symbol='TOY',signal=s,outcome=outcome(m,s))]
        a=[x for x in replay(rows,self.model(),3*DAY,5*DAY) if x['policy']=='always_break'][0]
        self.assertFalse(a['complete']);self.assertIsNone(a['conditional_net']);self.assertTrue(a['open_positions'])
        self.assertTrue(all(d['net'] is None for d in a['days']))

    def test_bankruptcy_cannot_open_another_position(self):
        m=self.source();s=self.event(m);o=outcome(m,s)
        # Short500 at100, adverse exit5000 -> loss24500: next day cannot
        # reserve500 collateral. The already existing adverse close remains.
        o.update(entry=100.,exit=5000.,financial_known=True,funding_events=[],exit_time=3*DAY+2*HOUR)
        a=dict(symbol='TOY',signal=s,outcome=o)
        b=copy.deepcopy(a);b['signal']['decision']+=DAY;b['outcome']['exit_time']+=DAY
        path=[x for x in replay([a,b],self.model(),3*DAY,5*DAY) if x['policy']=='always_rebound' and x['cost_multiple']==1][0]
        self.assertEqual(path['tickets'][0]['state'],'closed')
        self.assertEqual(path['tickets'][1]['state'],'blocked_capital');self.assertTrue(path['capital_stopped'])
        self.assertEqual(len([e for e in path['events'] if e['kind']=='fill']),2)

    def test_capital_shadow_and_unentered_unknown_not_poisoning(self):
        m=self.source();s=self.event(m);o=outcome(m,s)
        o.update(entry=100.,exit=1998.,financial_known=True,funding_events=[],exit_time=3*DAY+2*HOUR)
        a=dict(symbol='TOY',signal=s,outcome=o);b=copy.deepcopy(a)
        b['signal']['decision']+=DAY;b['outcome']['exit']=None;b['outcome']['exit_time']=None
        b['outcome']['failure_time']=4*DAY+3*HOUR
        paths=[x for x in replay([a,b],self.model(),3*DAY,5*DAY) if x['policy']=='always_rebound']
        for path in paths:
            self.assertEqual(path['tickets'][1]['state'],'blocked_capital')
            self.assertTrue(path['complete']);self.assertEqual(path['days'][1]['net'],'0')
            self.assertFalse(path['unknown_markers'])

    def test_two_stage_runner_complete_serialization_on_constructed_sources(self):
        # Exercises the ENTIRE new fit/evaluate driver on invented sources,
        # including model sidecar/record identity,18accounts/window and exports.
        # No real held input, outcome or commit assertion is used as evidence.
        import scripts.run_level_probability as runner
        with tempfile.TemporaryDirectory() as td:
            lane=Path(td);start=runner.ms('2025-04-20');end=runner.ms('2025-07-01')
            times=np.arange(start,end,HOUR);i=np.arange(len(times))
            p=pd.DataFrame(dict(t=times,close=100*np.exp(.03*np.sin(i/16)),vol=1.))
            f=pd.DataFrame(dict(t=times[::8],rate=.0001,cycle_h=8))
            source=market(p,f,start,end)
            config=dict(symbols=['BTC','ETH','SOL','WIF'],train_start='2025-05-01',train_end='2025-06-01',
                calibration_start='2025-06-01',calibration_end='2025-06-15',
                validation_start='2025-06-15',validation_end='2025-07-01',limitations=['constructed'])
            (lane/'config.json').write_bytes(runner.encode(config));(lane/'data_inputs.json').write_text('{}')
            fitdir=lane/'fit';fitdir.mkdir();evaldir=lane/'evaluate';evaldir.mkdir()
            with patch.object(runner,'LANE',lane),patch.object(runner,'load_markets',return_value={x:source for x in config['symbols']}):
                r=runner.fit_stage(fitdir,config);self.assertEqual(r['state'],'TRAINING_ONLY')
                for name in ('model.json','model.sha256','training.jsonl.gz'):(lane/name).write_bytes((fitdir/name).read_bytes())
                with patch.object(runner,'require_committed') as committed:
                    result=runner.evaluate_stage(evaldir,config,lane/'model.json')
                self.assertEqual(committed.call_count,3)
            self.assertEqual(len(result['windows']['validation']['accounts']),18)
            self.assertIsNone(result['actual_executable_net']);self.assertEqual(result['new_prospective_days'],0)
            accounts=json.loads(gzip.decompress((evaldir/'accounts.json.gz').read_bytes()))
            self.assertEqual(len(accounts['calibration']),18)


if __name__=='__main__':unittest.main()
