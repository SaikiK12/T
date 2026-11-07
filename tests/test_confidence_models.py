import copy
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd
from scipy.special import softmax
from lab.confidence_models import fit_bases,predict_bases,fit_maps,transform,objective,select,probabilities,export_bases
from lab.level_features import retained_ohlc,attach,vector,FEATURES
from lab.level_probability import market,HOUR,DAY


class ConfidenceModelTests(unittest.TestCase):
    def source(self):
        times=np.arange(120)*HOUR;p=100+np.sin(np.arange(120)/3)
        prices=pd.DataFrame(dict(t=times,close=p,vol=1.,amount=p))
        funding=pd.DataFrame(dict(t=times[::8],rate=0.,cycle_h=8))
        m=market(prices,funding,0,120*HOUR)
        bars=pd.DataFrame(dict(open=p-.1,high=p+.5,low=p-.6,close=p,vol=1.,amount=p),index=times+HOUR)
        return attach(m,bars),prices

    def test_feature_causality_direction_and_volume_unit_invariance(self):
        m,_=self.source();s=dict(state='event',index=96,decision=4*DAY,side=1,level=100.,sigma=.02)
        x=vector(m,m,s);self.assertEqual(len(x),len(FEATURES))
        later=copy.deepcopy(m);later['close'][97:]=1e8;later['ohlc'][97:]=1e9
        np.testing.assert_array_equal(x,vector(later,later,s))
        scaled=copy.deepcopy(m);scaled['ohlc'][:,4]*=100
        np.testing.assert_allclose(x,vector(scaled,scaled,s),atol=1e-14)
        reversed_s={**s,'side':-1};reverse=vector(m,m,reversed_s)
        for j in (0,1,2,3,6,7,8,9):self.assertAlmostEqual(reverse[j],-x[j])
        m['ohlc_valid'][95]=False;self.assertIsNone(vector(m,m,s))

    def test_raw_receipt_identity_cutoff_and_close_reconciliation(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);raw=json.dumps(dict(success=True,data=dict(time=[0,3600],open=[99.,100.],high=[101.,102.],low=[98.,99.],close=[100.,101.],vol=[1.,2.],amount=[100.,202.]))).encode()
            packed=gzip.compress(raw,mtime=0);(root/'raw.gz').write_bytes(packed)
            receipt=dict(symbol='BTC',path='raw.gz',url='https://contract.mexc.com/api/v1/contract/kline/BTC_USDT?interval=Min60&start=0&end=3600',gzip_sha256=hashlib.sha256(packed).hexdigest(),raw_sha256=hashlib.sha256(raw).hexdigest())
            prices=pd.DataFrame(dict(t=[0,3600000],close=[100.,101.],vol=[1.,2.],amount=[100.,202.]))
            f=retained_ohlc(root,[receipt],'BTC',prices,2*HOUR)
            self.assertEqual(list(f.index),[HOUR]);self.assertEqual(float(f.high.iloc[0]),101.)
            prices.loc[0,'close']=999.
            with self.assertRaisesRegex(ValueError,'does not match'):retained_ohlc(root,[receipt],'BTC',prices,2*HOUR)
            (root/'raw.gz').write_bytes(packed+b'x')
            with self.assertRaisesRegex(ValueError,'bytes drift'):retained_ohlc(root,[receipt],'BTC',prices,2*HOUR)

    def test_fractional_source_clock_cannot_be_rounded_to_an_hour(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);d=dict(time=[3600.9],open=[99.],high=[101.],low=[98.],close=[100.],vol=[1.],amount=[100.])
            raw=json.dumps(dict(success=True,data=d)).encode();packed=gzip.compress(raw,mtime=0);(root/'r.gz').write_bytes(packed)
            r=dict(symbol='BTC',path='r.gz',url='https://contract.mexc.com/api/v1/contract/kline/BTC_USDT?interval=Min60&start=0&end=7200',gzip_sha256=hashlib.sha256(packed).hexdigest(),raw_sha256=hashlib.sha256(raw).hexdigest())
            p=pd.DataFrame(dict(t=[HOUR],close=[100.],vol=[1.],amount=[100.]))
            with self.assertRaisesRegex(ValueError,'native integer'):retained_ohlc(root,[r],'BTC',p,3*HOUR)

    def test_identity_map_temperature_argmax_and_invalid_probabilities(self):
        p=np.array([[.7,.2,.1],[.1,.3,.6]])
        identity=dict(kind='dirichlet_identity',w=np.eye(3).tolist(),b=[0.,0.,0.])
        np.testing.assert_allclose(transform(p,identity),p,atol=1e-14)
        for t in (.1,.5,1.,2.,10.):
            q=transform(p,dict(kind='temperature',temperature=t));np.testing.assert_array_equal(q.argmax(axis=1),p.argmax(axis=1))
            np.testing.assert_allclose(q.sum(axis=1),1)
        for bad in ([[1.,1.,0.]],[[np.nan,0,1]],[[.2,.3]]):
            with self.assertRaises(ValueError):probabilities(bad)

    def test_dirichlet_mean_loss_analytic_gradient(self):
        p=np.array([[.7,.2,.1],[.1,.3,.6],[.2,.4,.4],[.5,.2,.3]])
        y=np.array([0,2,1,2]);theta=np.r_[np.eye(3).ravel(),[.1,-.2,.3]]+.03
        loss,gradient=objective(theta,np.log(p),y);numeric=[]
        for j in range(12):
            a=theta.copy();b=theta.copy();a[j]+=1e-6;b[j]-=1e-6
            numeric.append((objective(a,np.log(p),y)[0]-objective(b,np.log(p),y)[0])/2e-6)
        np.testing.assert_allclose(gradient,numeric,atol=1e-7,rtol=1e-5)
        loss2,g2=objective(theta,np.tile(np.log(p),(2,1)),np.tile(y,2))
        self.assertAlmostEqual(loss,loss2);np.testing.assert_allclose(gradient,g2,atol=1e-14)

    def test_finite_fit_calibration_and_disjoint_selection_contract(self):
        rng=np.random.default_rng(331);x=rng.normal(size=(90,10));y=np.tile(np.arange(3),30)
        base=fit_bases(x,y);before=copy.deepcopy(base['mean']);raw=predict_bases(base,x[:36])
        export=export_bases(base);z=np.clip((x[:36]-export['mean'])/export['scale'],-5,5)
        r=export['models']['ridge'];np.testing.assert_allclose(softmax(z@np.array(r['coef']).T+r['intercept'],axis=1),raw['ridge'],atol=1e-14)
        t=export['models']['tree'];scores=np.tile(t['baseline'],(len(z),1))
        for stage in t['stages']:
            for k,nodes in enumerate(stage):
                for i,row in enumerate(z):
                    j=0
                    while not nodes[j]['leaf']:
                        n=nodes[j];j=n['left'] if row[n['feature']]<=n['threshold'] else n['right']
                    scores[i,k]+=nodes[j]['value']
        np.testing.assert_allclose(softmax(scores,axis=1),raw['tree'],atol=1e-14)
        for name,p in raw.items():
            maps=fit_maps(p,y[:36]);self.assertEqual(maps['state'],'FIT')
            for k in ('raw','temperature','dirichlet_identity'):
                q=transform(p,maps[k]);np.testing.assert_allclose(q.sum(axis=1),1)
        np.testing.assert_array_equal(before,base['mean'])
        prior=np.tile([1/3]*3,(36,1));better=np.full((36,3),.05);better[np.arange(36),y[:36]]=.9
        choice=select(dict(frequency=prior,ridge_raw=better),y[:36]);self.assertEqual(choice['winner'],'ridge_raw')
        tied=select(dict(frequency=prior,ridge_raw=prior),y[:36]);self.assertEqual(tied['winner'],'frequency')
        unavailable=fit_maps(prior[:12],y[:12]);self.assertIsNone(unavailable['temperature'])


if __name__=='__main__':unittest.main()
