"""Causality, same-price refill, independent arithmetic and sealed search tests."""
import datetime as dt
from fractions import Fraction
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from lab import formula_space as fs,path_response as p,prereg
from scripts import run_path_response as runner


DAY="2026-10-29"


def tape():
    start=int(pd.Timestamp(DAY+"T13:00:00Z").value//1000)
    t=start+np.arange(0,120_000_000,100_000,dtype=np.int64)
    n=len(t);zeros=np.zeros(n,dtype=np.int64)
    b=pd.DataFrame(dict(t=t,off=zeros,u=np.arange(n,dtype=np.int64),
        bid=np.full(n,10_000_000,dtype=np.int64),sp=np.full(n,100,dtype=np.int64),
        bq=np.full(n,10000,dtype=np.int64),aq=np.full(n,10000,dtype=np.int64)))
    q=pd.DataFrame(dict(t=t+50_000,off=zeros,a=np.arange(n,dtype=np.int64),
        p=np.full(n,10_000_000,dtype=np.int64),q=np.full(n,100,dtype=np.int64),m=zeros))
    return start,b,q


def first(b,q):
    frame,_=p.make_samples(b,q,DAY,"BTCUSDT")
    return frame.iloc[0]


class CausalTapeTests(unittest.TestCase):
    def test_constant_price_has_zero_area_and_known_flow(self):
        _,b,q=tape();r=first(b,q)
        self.assertEqual(r.area,0);self.assertEqual(r.refill,0)
        self.assertAlmostEqual(r.flow,.5)
        self.assertEqual(r.ofi,0)

    def test_area_matches_independent_polygon_geometry(self):
        start,b,q=tape()
        b.loc[b.t>=start+27_000_000,"bid"]+=100
        r=first(b,q);d=int(r.decision_us);left=d-p.LOOK_US
        bs=b[(b.t>=left)&(b.t<d)]
        qs=q[(q.t>=left)&(q.t<d)]
        events=sorted([(int(x.t),'b',x) for x in bs.itertuples()]+
                      [(int(x.t),'q',x) for x in qs.itertuples()])
        px=Fraction(0);flow=Fraction(0);xs=[px];ys=[flow]
        m0=Fraction(int(bs.iloc[0].bid)*2+int(bs.iloc[0].sp),200)
        for _,kind,x in events:
            if kind=='b': px=10000*(Fraction(x.bid*2+x.sp,200)/m0-1)
            else: flow+=Fraction(x.q,10000)
            xs.append(px);ys.append(flow)
        self.assertAlmostEqual(r.area,float(fs.signed_area(xs,ys)),places=10)

    def test_same_price_replenishment_is_not_a_new_price_level(self):
        start,b,q=tape()
        k=b.index[b.t==start+27_000_000][0]
        b.loc[k:,"bq"]=15000
        self.assertAlmostEqual(first(b,q).refill,.5)
        b.loc[k:,"bid"]+=50
        b.loc[k:,"sp"]-=50  # move only the bid, keeping the ask fixed
        self.assertEqual(first(b,q).refill,0)
        self.assertAlmostEqual(first(b,q).ofi,1.5)

    def test_future_price_and_sizes_cannot_change_features(self):
        start,b,q=tape();a=first(b,q)
        mask=b.t>=start+30_000_000
        b.loc[mask,"bid"]+=2000
        b.loc[mask,"bq"]*=2
        q.loc[q.t>=start+30_000_000,"q"]*=20
        z=first(b,q)
        for name in (*p.BASE,*p.LEAVES): self.assertEqual(a[name],z[name],name)

    def test_unknown_constant_clock_offset_cancels_in_relative_windows(self):
        _,b,q=tape();a=first(b,q)
        b['off']=-1_000_000_000;q['off']=-1_000_000_000
        z=first(b,q)
        for name in ('decision_us',*p.BASE,*p.LEAVES,'mid_return'):
            self.assertEqual(a[name],z[name],name)

    def test_unknown_exit_is_retained_and_never_becomes_a_zero_loss(self):
        start,b,q=tape();b=b[b.t<start+34_000_000]
        r=first(b,q)
        self.assertEqual(r.decision_us,start+30_000_000)
        self.assertFalse(r.label_valid);self.assertFalse(r.execution_valid)
        frame=pd.DataFrame([r]);action,pnl=p.replay(frame,np.array([50.]))
        self.assertEqual(action[0],1);self.assertTrue(np.isnan(pnl[0]))
        flat,flatpnl=p.replay(frame,np.array([0.]))
        self.assertEqual(flat[0],0);self.assertEqual(flatpnl[0],0)

    def test_future_depth_cannot_remove_an_eligible_decision(self):
        start,b,q=tape()
        b.loc[b.t>=start+30_000_000,"aq"]=1
        b.loc[b.t>=start+30_000_000,"bid"]-=1000
        r=first(b,q)
        self.assertEqual(r.decision_us,start+30_000_000)
        self.assertTrue(r.label_valid);self.assertFalse(r.execution_valid)

    def test_future_clock_step_is_an_unknown_label_not_an_absent_decision(self):
        start,b,q=tape();b.loc[b.t>=start+31_000_000,"off"]=2000
        r=first(b,q)
        self.assertEqual(r.decision_us,start+30_000_000)
        self.assertFalse(r.label_valid)

    def test_ties_and_stale_windows_cannot_invent_an_event_order(self):
        start,b,q=tape();q.loc[270,"t"]=b.loc[270,"t"]
        f,qc=p.make_samples(b,q,DAY,"BTCUSDT")
        self.assertNotIn(start+30_000_000,f.decision_us.tolist())
        self.assertGreater(qc['reasons']['cross_stream_tie'],0)
        start,b,q=tape();q=q[~q.t.between(start+26_000_000,start+29_000_000)]
        f,qc=p.make_samples(b,q,DAY,"BTCUSDT")
        self.assertNotIn(start+30_000_000,f.decision_us.tolist())
        self.assertGreater(qc['reasons']['stale_feature_window'],0)

    def test_invalid_units_and_backwards_receive_clock_fail_closed(self):
        _,b,q=tape();b['bid']=b.bid.astype(float)
        with self.assertRaises(p.DataError): p.make_samples(b,q,DAY,"BTCUSDT")
        _,b,q=tape();b.loc[10,'t']=b.loc[8,'t']
        with self.assertRaises(p.DataError): p.make_samples(b,q,DAY,"BTCUSDT")


def invented_frame(values,repeats):
    grid=np.array([(a,r) for a in values for r in values]*repeats)
    rng=np.random.default_rng(400)
    n=len(grid)
    data={k:rng.normal(size=n) for k in p.BASE}
    data.update(area=grid[:,0],refill=grid[:,1],mid_return=20*grid[:,0]*grid[:,1])
    return pd.DataFrame(data)


class EquationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.train=invented_frame([-2,-1,0,1,2],12)
        cls.select=invented_frame([-1.5,-.5,.5,1.5],10)
        cls.artifact=p.choose_equation(cls.train,cls.select)

    def test_bounded_search_recovers_a_planted_interaction(self):
        artifact=self.artifact
        self.assertEqual(artifact['family']['attempts'],1476)
        self.assertEqual(artifact['family']['retained'],623)
        self.assertIsNotNone(artifact['selected_index'])
        unseen=invented_frame([-1.25,-.25,.25,1.25],8)
        base,pred,valid=p.predict(unseen,artifact)
        self.assertTrue(valid.all())
        y=unseen.mid_return.to_numpy()
        self.assertLess(np.mean((y-pred)**2),np.mean((y-base)**2)/100)

    def test_predictions_do_not_accept_future_targets(self):
        f=self.select.copy();a=p.predict(f,self.artifact)
        f['mid_return']=1e10
        b=p.predict(f,self.artifact)
        for x,y in zip(a,b): np.testing.assert_array_equal(x,y)

    def test_constant_and_baseline_span_do_not_fake_new_information(self):
        t=self.train.copy();v=self.select.copy()
        t['mid_return']=20*t.flow;v['mid_return']=20*v.flow
        a=p.choose_equation(t,v)
        self.assertIsNone(a['selected_index'])
        self.assertTrue(any(x['status']=='baseline_span' for x in a['search']))

    def test_expression_adapter_preserves_domains_and_near_zero_guards(self):
        x=fs.variable('area')
        out=p.expression_values(x/x,{'area':np.array([0.,1e-9,1.,np.nan])})
        self.assertTrue(np.isnan(out[[0,1,3]]).all());self.assertEqual(out[2],1)

    def test_projection_is_fitted_on_training_only(self):
        x=np.array([[1.],[2.],[3.]])
        res,coef=p.residualize(x,2+3*x[:,0])
        np.testing.assert_allclose(res,0,atol=1e-12)
        v,_=p.residualize(np.array([[7.]]),np.array([24.]),coef)
        np.testing.assert_allclose(v,[1.],atol=1e-12)


class ReplayTests(unittest.TestCase):
    def frame(self):
        return pd.DataFrame(dict(spread=[2.,2.],mid_return=[20.,-20.],
            entry_bid=[99.99,99.99],entry_ask=[100.01,100.01],
            exit_bid=[100.19,99.79],exit_ask=[100.21,99.81],execution_valid=[True,True]))

    def test_both_sides_pay_crossed_spread_fees_and_cost_stress(self):
        f=self.frame();a,pnl=p.replay(f,np.array([20.,-20.]))
        np.testing.assert_array_equal(a,[1,-1])
        for i,s in enumerate(a):
            e=f.entry_ask[i] if s>0 else f.entry_bid[i]
            x=f.exit_bid[i] if s>0 else f.exit_ask[i]
            expected=(s*1e4*(x/e-1)-5*(1+x/e))*100/1e4
            self.assertAlmostEqual(pnl[i],expected)
        _,double=p.replay(f,np.array([20.,-20.]),2)
        self.assertTrue((double<pnl).all())

    def test_unknown_prediction_is_abstention_and_uses_no_future_spread(self):
        f=self.frame();a,z=p.replay(f,np.array([np.nan,11.]))
        np.testing.assert_array_equal(a,[0,0]);np.testing.assert_array_equal(z,[0,0])
        f['exit_ask']*=20
        a,_=p.replay(f,np.array([np.nan,11.]))
        np.testing.assert_array_equal(a,[0,0])

    def test_cluster_ratio_counts_blocks_not_trades(self):
        a=p.ratio_interval([1,2,3],[1000,2000,3000],replicas=100)
        self.assertEqual(a['blocks'],3);self.assertAlmostEqual(a['mean'],.001)
        self.assertEqual(a,p.ratio_interval([1,2,3],[1000,2000,3000],replicas=100))
        self.assertIsNone(p.ratio_interval([1],[1])['lower'])

    def test_unresolved_trade_blocks_positive_verdict_and_total_pnl(self):
        f=pd.concat([self.frame().iloc[[0]]]*20,ignore_index=True)
        f['mid_return']=50.;f['exit_bid']=100.49;f['exit_ask']=100.51
        f['block']=np.arange(20);f['day']=[str(i//4) for i in range(20)]
        f['label_valid']=True;f.loc[0,'execution_valid']=False
        with patch.object(p,'predict',return_value=(np.zeros(20),np.full(20,50.),np.ones(20,bool))):
            r=p.evaluate(f,dict(selected_index=0))
        self.assertEqual(r['verdict'],'INCONCLUSIVE')
        self.assertEqual(r['portfolios']['selected']['2']['unresolved_trades'],1)
        self.assertIsNone(r['portfolios']['selected']['2']['pnl_usd'])
        self.assertIsNone(r['portfolios']['selected']['2']['hourly']['lower'])
        self.assertIsNone(r['incremental_hourly_usd_2x']['lower'])


class RunnerTests(unittest.TestCase):
    def lane(self,root):
        lane=root/'lane';lane.mkdir()
        (root/'bound.py').write_text('source\n')
        spec=lane/'PREREG.md'
        spec.write_text('```inputs\n'+runner.digest(root/'bound.py')+' bound.py\n```\n')
        prereg.freeze(spec)
        return lane

    def test_frozen_input_change_prevents_any_market_read(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);lane=self.lane(root)
            runner.verify_inputs(lane,root)
            (root/'bound.py').write_text('changed\n')
            with self.assertRaises(prereg.PreregError): runner.verify_inputs(lane,root)

    def test_missing_development_data_does_not_fit_or_consume_the_first_look(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);lane=self.lane(root)
            with patch.object(runner,'verify_inputs',return_value='sealed'),patch.object(runner,'now',return_value=dt.datetime(2026,11,3,tzinfo=dt.timezone.utc)):
                r=runner.run('prepare',root/'missing',lane)
            self.assertEqual(r['status'],'BLOCKED');self.assertFalse(r['market_fit'])
            self.assertFalse((lane/'results/prepare.started.json').exists())

    def test_calendar_refuses_interim_scoring_and_late_training(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);lane=self.lane(root)
            with patch.object(runner,'verify_inputs',return_value='sealed'),patch.object(runner,'now',return_value=dt.datetime(2026,11,4,tzinfo=dt.timezone.utc)):
                self.assertEqual(runner.run('prepare',root,lane)['status'],'BLOCKED')
                self.assertEqual(runner.run('score',root,lane)['status'],'BLOCKED')

    def test_artifact_and_receipt_writes_are_exclusive(self):
        with tempfile.TemporaryDirectory() as td:
            pth=Path(td)/'model.json';runner.write_new(pth,dict(a=1))
            with self.assertRaises(FileExistsError): runner.write_new(pth,dict(a=2))
            self.assertEqual(json.loads(pth.read_text()),dict(a=1))


if __name__=='__main__': unittest.main()
