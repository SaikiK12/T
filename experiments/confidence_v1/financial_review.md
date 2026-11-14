# R331 bounded independent component review

Review target: `lab/level_features.py` SHA `9f06cbaaebc662b393b77a0dcabb04f0a3c84690c1f2365d6f822337fa399062`; `lab/confidence_models.py` SHA `12bb7b0627e18ada2e7c392cdf431301f9c518aecd53a86aad2bc67b13df4ef9`.

No network, actual historical market/source data, project-trained models/outcomes,
or tracked file edits. All data below are invented and source bytes are mocked in
memory. Earlier stale-hash invocations aborted before tests. One earlier broad
review run passed its 26 model checks, then stopped on my fixture's NumPy integer
JSON encoding error; it is not a complete pass and is superseded by the executable
review below. Reruns are not additional independent trials.

## Reproducible literal review

```python
from pathlib import Path
import copy, gzip, hashlib, json
from unittest.mock import patch
import numpy as np
import pandas as pd
from scipy.special import softmax
expected = {
 'lab/level_features.py':'9f06cbaaebc662b393b77a0dcabb04f0a3c84690c1f2365d6f822337fa399062',
 'lab/confidence_models.py':'12bb7b0627e18ada2e7c392cdf431301f9c518aecd53a86aad2bc67b13df4ef9'}
for f,h in expected.items(): assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h
import lab.level_features as lf
import lab.confidence_models as cm
checks=[]
def ck(name, ok):
 assert ok, name
 checks.append(name)
rng=np.random.default_rng(331)
p=rng.dirichlet([1.,2.,3.],size=36); z=np.log(p); y=np.tile([0,1,2],12)
errors=[]
for theta in [np.r_[np.eye(3).ravel(),np.zeros(3)],np.zeros(12),rng.normal(size=12)]:
 _,g=cm.objective(theta,z,y)
 for j in range(12):
  a=theta.copy(); b=theta.copy(); a[j]+=1e-6; b[j]-=1e-6
  errors.append(abs((cm.objective(a,z,y)[0]-cm.objective(b,z,y)[0])/2e-6-g[j]))
ck('identity-L2 gradient:36 central differences',max(errors)<2e-8)
for name,m in [('raw',dict(kind='raw')),('temperature1',dict(kind='temperature',temperature=1.)),('DirichletI',dict(kind='dirichlet_identity',w=np.eye(3).tolist(),b=[0,0,0]))]:
 ck(name+' identity',np.allclose(cm.transform(p,m),p,atol=1e-12,rtol=0))
for t in [.1,.4,2.,10.]:
 q=cm.transform(p,dict(kind='temperature',temperature=t))
 ck('positiveT argmax '+str(t),np.array_equal(q.argmax(1),p.argmax(1)))
 ck('positiveT simplex '+str(t),np.isfinite(q).all() and np.all(q>0) and np.allclose(q.sum(1),1))
w=np.array([[1,.3,0],[0,1,0],[.1,0,1]]); b=np.array([.1,-.2,0])
ck('Dirichlet matrix orientation',np.allclose(cm.transform(p,dict(kind='dirichlet_identity',w=w.tolist(),b=b.tolist())),softmax(z@w.T+b,axis=1)))
for bad in [np.ones((4,3)),np.array([[1.,-.1,.1]]),np.array([[np.nan,.4,.6]]),np.ones((2,2))]:
 try: cm.probabilities(bad)
 except ValueError: pass
 else: raise AssertionError('invalid probability accepted')
ck('invalid probability contracts',True)
for bad in [[0.,1.,2.],[True,False,True],[0,1,3]]:
 try: cm.labels(bad)
 except ValueError: pass
 else: raise AssertionError('invalid label accepted')
ck('canonical integer labels',True)
x=rng.normal(size=(90,10)); x[:,0]=np.linspace(-1,1,90); x[:,9]=0
bundle=cm.fit_bases(x,np.repeat([0,1,2],30))
ck('training-only scaler/constant coordinate',np.array_equal(bundle['mean'],x.mean(0)) and bundle['scale'][9]==1)
ck('fixed base hyperparameters',bundle['models']['ridge'].C==.1 and bundle['models']['tree'].max_iter==32 and bundle['models']['tree'].early_stopping is False)
ck('canonical class order',all(m.classes_.tolist()==[0,1,2] for m in bundle['models'].values()))
ck('empty prediction shape',all(a.shape==(0,3) for a in cm.predict_bases(bundle,np.empty((0,10))).values()))
exports=cm.export_bases(bundle); scaled=np.clip((x-bundle['mean'])/bundle['scale'],-5,5)
pred=cm.predict_bases(bundle,x); rm=exports['models']['ridge']
ridge_error=float(np.max(np.abs(softmax(scaled@np.array(rm['coef']).T+rm['intercept'],axis=1)-pred['ridge'])))
ck('independent ridge export',ridge_error<1e-14)
tm=exports['models']['tree']; logits=np.tile(tm['baseline'],(len(x),1)); traversals=0
for stage in tm['stages']:
 for k,nodes in enumerate(stage):
  for i,row in enumerate(scaled):
   j=0
   while not nodes[j]['leaf']:
    j=nodes[j]['left'] if row[nodes[j]['feature']]<=nodes[j]['threshold'] else nodes[j]['right']
    traversals+=1
   logits[i,k]+=nodes[j]['value']
tree_error=float(np.max(np.abs(softmax(logits,axis=1)-pred['tree'])))
ck('independent every reached numeric HGB branch',tree_error<1e-14)
fitted=cm.fit_maps(p,y)
ck('calibration optimizers',fitted['state']=='FIT')
ck('fitted positiveT bounds',.1<=fitted['temperature']['temperature']<=10)
ck('no earned market confidence',fitted['calibrated_market_confidence'] is False)
ck('sparse calibration unavailable',cm.fit_maps(p[:20],y[:20])['state']=='UNAVAILABLE')
prior=np.tile([.2,.3,.5],(36,1))
ck('simpler prior on NLL tie',cm.select({'frequency':prior,'ridge_raw':prior.copy()},y)['winner']=='frequency')
H=lf.HOUR; N=100; t=np.arange(N)*H
c=100+np.sin(np.arange(N)/8)+np.arange(N)*.01; vol=10+np.arange(N)%7
payload={'success':True,'data':{'time':list(map(int,t//1000)),'open':list(map(float,c*.998)),
 'high':list(map(float,c*1.003)),'low':list(map(float,c*.992)),'close':list(map(float,c)),
 'vol':list(map(int,vol)),'amount':list(map(float,c*vol)),'realOpen':[-999]*N}}
raw=json.dumps(payload).encode(); packed=gzip.compress(raw,mtime=0)
record=dict(symbol='TOY',url='https://contract.mexc.com/api/v1/contract/kline/TOY_USDT?interval=Min60&start=0&end=356400',
 path='raw/toy.json.gz',gzip_sha256=hashlib.sha256(packed).hexdigest(),raw_sha256=hashlib.sha256(raw).hexdigest())
frame=pd.DataFrame(dict(t=t,close=c,vol=vol,amount=c*vol))
with patch.object(Path,'read_bytes',return_value=packed): out=lf.retained_ohlc('/UNUSED',[record],'TOY',frame,85*H)
ck('strict source cutoff/receipt reconciliation',out.index.max()<85*H and len(out)==84 and out.loc[H,'open']>0)
for field,value in [('gzip_sha256','0'*64),('raw_sha256','0'*64),('url',record['url'].replace('contract.mexc.com','wrong.example')),('url',record['url'].replace('https:','http:')),('url',record['url']+'&start=0')]:
 with patch.object(Path,'read_bytes',return_value=packed):
  try: lf.retained_ohlc('/UNUSED',[record|{field:value}],'TOY',frame,85*H)
  except ValueError: pass
  else: raise AssertionError('bad source identity accepted')
ck('source URL/scheme/query/twohash guards',True)
bad=frame.copy(); bad.loc[10,'close']+=.01
with patch.object(Path,'read_bytes',return_value=packed):
 try: lf.retained_ohlc('/UNUSED',[record],'TOY',bad,85*H)
 except ValueError: pass
 else: raise AssertionError('close mismatch accepted')
ck('held close mismatch',True)
for wrongclock in [3600.9,False]:
 bp=copy.deepcopy(payload); bp['data']['time'][1]=wrongclock
 br=json.dumps(bp).encode(); bg=gzip.compress(br,mtime=0)
 rec=record|{'gzip_sha256':hashlib.sha256(bg).hexdigest(),'raw_sha256':hashlib.sha256(br).hexdigest()}
 with patch.object(Path,'read_bytes',return_value=bg):
  try: lf.retained_ohlc('/UNUSED',[rec],'TOY',frame,85*H)
  except ValueError: pass
  else: raise AssertionError('fractional/bool clock accepted')
ck('fractional/bool sourceclock regression',True)
index=t+H
ohlc=pd.DataFrame({k:payload['data'][k] for k in ['open','high','low','close','vol','amount']},index=index)
m=lf.attach(dict(t=index,close=c.copy(),valid=np.ones(N,bool)),ohlc)
btc=dict(t=index,close=200+np.arange(N)*.02,valid=np.ones(N,bool))
i=72; sig=dict(state='event',index=i,decision=int(index[i]),sigma=.01,side=1,level=float(c[i]-.1))
v=lf.vector(m,btc,sig)
ck('ten finite dimensionless features',len(v)==10 and np.isfinite(v).all())
future=copy.deepcopy(m); future['close'][i+1:]=1e20; future['ohlc'][i+1:]=np.nan; future['ohlc_valid'][i+1:]=False
fb=copy.deepcopy(btc); fb['close'][i+1:]=0; fb['valid'][i+1:]=False
ck('future feature invariance',lf.vector(future,fb,sig)==v)
flip=lf.vector(m,btc,sig|{'side':-1})
ck('eight signed feature flips/two unsigned invariants',all(abs(flip[j]+v[j])<1e-12 for j in [0,1,2,3,6,7,8,9]) and flip[4:6]==v[4:6])
ck('wick/body dimensionless units',abs(v[6]-.002/.011)<1e-10 and abs(v[7]-.003/.011)<1e-10)
gap=copy.deepcopy(m); gap['ohlc_valid'][i-4]=False
ck('OHLC gap remains unknown',lf.vector(gap,btc,sig) is None)
gb=copy.deepcopy(btc); gb['valid'][i-3]=False
ck('BTC gap remains unknown',lf.vector(m,gb,sig) is None)
for f,h in expected.items(): assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h
review_result=dict(hashes=expected,passed=len(checks),checks=checks,max_gradient_error=max(errors),
 ridge_export_maxdiff=ridge_error,HGB_export_maxdiff=tree_error,node_comparisons=traversals)
print(json.dumps(review_result,indent=2))
```

## Counterexample and pre-freeze correction

At original feature SHA `2428f695c0a28593808874a508dac878506591c4687867622e7ac6876fbee7e2`, source time `3600.9` was silently truncated to `3600` seconds. In an executed literal case, URL/gzip/raw identities and frozen close reconciliation all passed, producing hourly closes `[3600000,7200000]` ms. The final reviewed candidate requires native integer nonboolean clocks, HTTPS, unique query parameters and hourly/in-query timestamps. No historical output was read or modified.

## Limits

- The Dirichlet objective is mean NLL plus `0.5/3` times identity/intercept squared norms. Its gradient and matrix orientation are checked; it is our identity regularizer, not source ODIR.
- Temperature calibration and class probability guards do not establish future market calibration or create information. Full chronology of train/Cfit/Cselect/validation and committed artifacts belongs to the driver, outside this review.
- The receipt decoder verifies caller-supplied registered records. The driver must bind them to actual retained public receipts. A historical receipt does not supply first-seen market clocks, fills or live book evidence.
- Feature code assumes the caller's frozen event and common hourly asset/BTC grid. BTC residual is fixed-beta-one log-return subtraction, not an estimated correlation or hedge. Wicks/volume are bar features, not OFI or absorption.
- Numeric HGB exports are checked on complete numeric feature inputs; categorical or missing-value traversal is outside this scope. The export omits missing-direction metadata because production rejects incomplete feature matrices.
- Optimizer NLL is evaluated before final probability flooring; delivered proper losses must be recomputed after the explicit `1e-12` clipping/renormalization. In extreme logits the stored optimizer objective need not equal delivered floored NLL. No market calibration can be inferred from optimizer success.
- `transform` checks Dirichlet map shape/finiteness but not its fit-time bounds; sealed map identity is necessary. No full system, source provenance, executable costs/funding, uncertainty coverage, positive expected return or activation is certified.

## Executed result

```json
{
  "hashes": {
    "lab/level_features.py": "9f06cbaaebc662b393b77a0dcabb04f0a3c84690c1f2365d6f822337fa399062",
    "lab/confidence_models.py": "12bb7b0627e18ada2e7c392cdf431301f9c518aecd53a86aad2bc67b13df4ef9"
  },
  "passed": 36,
  "checks": [
    "identity-L2 gradient:36 central differences",
    "raw identity",
    "temperature1 identity",
    "DirichletI identity",
    "positiveT argmax 0.1",
    "positiveT simplex 0.1",
    "positiveT argmax 0.4",
    "positiveT simplex 0.4",
    "positiveT argmax 2.0",
    "positiveT simplex 2.0",
    "positiveT argmax 10.0",
    "positiveT simplex 10.0",
    "Dirichlet matrix orientation",
    "invalid probability contracts",
    "canonical integer labels",
    "training-only scaler/constant coordinate",
    "fixed base hyperparameters",
    "canonical class order",
    "empty prediction shape",
    "independent ridge export",
    "independent every reached numeric HGB branch",
    "calibration optimizers",
    "fitted positiveT bounds",
    "no earned market confidence",
    "sparse calibration unavailable",
    "simpler prior on NLL tie",
    "strict source cutoff/receipt reconciliation",
    "source URL/scheme/query/twohash guards",
    "held close mismatch",
    "fractional/bool sourceclock regression",
    "ten finite dimensionless features",
    "future feature invariance",
    "eight signed feature flips/two unsigned invariants",
    "wick/body dimensionless units",
    "OHLC gap remains unknown",
    "BTC gap remains unknown"
  ],
  "max_gradient_error": 9.185849858539541e-10,
  "ridge_export_maxdiff": 1.1102230246251565e-16,
  "HGB_export_maxdiff": 1.1102230246251565e-16,
  "node_comparisons": 10560
}
```
