"""Independent R331 OHLC-feature/logit/calibration/selection/Fraction cash audit.

No production feature, learner, calibrator, selector or financial functions.
R330 labels are reused by exact identity from its already source-audited frozen
records; they are not a second independent sample or new intrabar evidence.
"""
import argparse
import gzip
import hashlib
import json
import math
from fractions import Fraction as F
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LANE=ROOT/'experiments/confidence_v1'
H=3_600_000
D=24*H
EPS=1e-12
CLASSES=('break','rebound','timeout')
NAMES=tuple(b+'_'+m for b in ('ridge','tree') for m in ('raw','temperature','dirichlet_identity'))+('frequency',)


def read(p):return json.loads(Path(p).read_text())
def unpack(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ms(s):return int(__import__('datetime').datetime.fromisoformat(s).replace(tzinfo=__import__('datetime').timezone.utc).timestamp()*1000)
def near(a,b,tol=2e-12):
    if not math.isclose(float(a),float(b),rel_tol=tol,abs_tol=tol):raise ValueError(f'independent numeric mismatch {a} vs {b}')


def canonical(p):
    q=[max(float(v),EPS) for v in p];s=sum(q);return [v/s for v in q]


def softmax(z):
    m=max(z);e=[math.exp(v-m) for v in z];s=sum(e);return canonical([v/s for v in e])


def base_probabilities(x,export):
    z=[max(-5.,min(5.,(v-m)/s)) for v,m,s in zip(x,export['mean'],export['scale'])]
    ridge=export['models']['ridge'];rl=[sum(a*b for a,b in zip(row,z))+b for row,b in zip(ridge['coef'],ridge['intercept'])]
    tree=export['models']['tree'];tl=list(tree['baseline'])
    for stage in tree['stages']:
        for k,nodes in enumerate(stage):
            j=0;seen=set()
            while not nodes[j]['leaf']:
                if j in seen:raise ValueError('cyclic numeric tree export')
                seen.add(j);node=nodes[j];j=node['left'] if z[node['feature']]<=node['threshold'] else node['right']
            tl[k]+=nodes[j]['value']
    return dict(ridge=softmax(rl),tree=softmax(tl))


def calibrated(p,m):
    if m is None:return None
    p=canonical(p)
    if m['kind']=='raw':return p
    z=[math.log(v) for v in p]
    if m['kind']=='temperature':return softmax([v/m['temperature'] for v in z])
    if m['kind']=='dirichlet_identity':return softmax([sum(a*b for a,b in zip(row,z))+offset for row,offset in zip(m['w'],m['b'])])
    raise ValueError('unknown calibrator')


def feature_from_raw(row,bars):
    s=row['signal'];sym=row['symbol'];d=s['decision'];side=s['side'];sigma=s['sigma'];p=bars[sym]
    def good(t,asset):
        v=bars[asset].get(t)
        return v is not None and all(math.isfinite(x) for x in v) and min(v[:4])>0 and min(v[4:])>0 and v[2]<=min(v[0],v[3])<=max(v[0],v[3])<=v[1]
    if not all(good(t,sym) for t in range(d-72*H,d+H,H)):return None
    btc=bars['BTC']
    if any(t not in btc or not math.isfinite(btc[t][3]) or btc[t][3]<=0 or not math.isfinite(btc[t][4]) or btc[t][4]<=0 for t in range(d-24*H,d+H,H)):return None
    o,hi,lo,c,vol,_=p[d];closes=[p[t][3] for t in range(d-72*H,d+H,H)]
    r=[math.log(b)-math.log(a) for a,b in zip(closes[:-1],closes[1:])];rv=sum(v*v for v in r)/72
    vv=sorted(p[t][4] for t in range(d-72*H,d,H));median=(vv[35]+vv[36])/2
    span=hi-lo;body=side*(c-o)/span if span else 0.;wick=side*((min(o,c)-lo)-(hi-max(o,c)))/span if span else 0.
    return [side*math.log(c/s['level'])/sigma,side*math.log(c/p[d-H][3])/sigma,
        side*math.log(c/p[d-6*H][3])/sigma,side*math.log(c/p[d-24*H][3])/sigma,
        math.log1p((sum(v*v for v in r[-6:])/6)/rv),math.log(vol/median),body,wick,
        side*(math.log(c/p[d-24*H][3])-math.log(btc[d][3]/btc[d-24*H][3]))/sigma,float(side)]


def financial(accounts,bars,funds):
    events=0;closed=0
    for a in accounts:
        positions={};opened={};price=F(0);funding=F(0);cost=F(0);pending=0;cash=F(10000)
        for e in a['events']:
            sym=e['symbol'];stamp=e['occurred_ns']//1_000_000
            if e['kind']=='fill':
                q,p,fee=F(e['quantity']),F(e['price']),F(e['fee']);old,basis=positions.get(sym,(F(0),F(0)))
                near(p,bars[sym][stamp][3])
                if abs(fee-abs(q)*p*F(8,10000)*a['cost_multiple'])>F(1,10**16):raise ValueError('fee/crossing double count')
                if old:
                    if q!=-old:raise ValueError('unregistered close/borrow sizing')
                    gain=old*(p-basis);price+=gain;cash+=gain;positions[sym]=(F(0),F(0));closed+=1
                else:
                    if abs(abs(q*p)-F(500))>F(1,10**16):raise ValueError('fixed absolute500 notional drift')
                    reserved=sum((abs(q0)*entry for q0,entry in positions.values()),F(0))
                    if cash-reserved<abs(q)*p+fee-F(1,10**14):raise ValueError('unfunded entry/negative cash borrowing')
                    positions[sym]=(q,p);opened[sym]=stamp
                cost+=fee;cash-=fee
            elif e['kind']=='funding':
                if e['amount'] is None:pending+=1
                else:
                    expected=-positions[sym][0]*sum((F(str(bars[sym][t][3]))*F(str(rate)) for t,rate in funds[sym].items() if opened[sym]<t<=stamp),F(0))
                    if abs(F(e['amount'])-expected)>F(1,10**14):raise ValueError('signed source funding mismatch')
                    funding+=F(e['amount']);cash+=F(e['amount'])
            else:raise ValueError('unexpected finance event')
            events+=1
        for key,want in (('shared_cash',cash),('price',price),('funding',funding),('cost',cost)):
            if abs(F(a[key])-want)>F(1,10**14):raise ValueError('Fraction common-cash mismatch '+key)
        if pending!=a['pending']:raise ValueError('unknown funding made zero')
        if a['complete']:
            if pending or any(q for q,_ in positions.values()):raise ValueError('unknown/open account promoted')
            near(a['conditional_net'],price+funding-cost)
        if a['actual_order_allowed'] or a['actual_executable_net'] is not None:raise ValueError('unsupported market activation')
    for policy in {a['policy'] for a in accounts}:
        group=[a for a in accounts if a['policy']==policy]
        ids=[[(t['decision'],t['symbol'],t.get('quantity')) for t in a['tickets'] if t['state'] in ('closed','exit_unknown','funding_unknown')] for a in group]
        if not all(x==ids[0] for x in ids):raise ValueError('costtier-dependent entry rescue')
    return events,closed


def audit(directory,root=ROOT,lane=LANE):
    root,lane,directory=Path(root),Path(lane),Path(directory)
    spec=(lane/'PREREG.md').read_bytes()
    if hashlib.sha256(spec).hexdigest()!=(lane/'PREREG.sha256').read_text().strip():raise ValueError('spec drift')
    for name in ('config.json','data_inputs.json','code_inputs.json','sources.json'):
        if digest(lane/name) not in spec.decode():raise ValueError('unbound prereg input')
    data=read(lane/'data_inputs.json');config=read(lane/'config.json')
    for manifest in (data,read(lane/'code_inputs.json')):
        for path,value in manifest['sha256'].items():
            if digest(root/path)!=value:raise ValueError('input drift '+path)
    for stage in ('training','calibration','selection'):
        for name,value in read(lane/stage/'manifest.json')['sha256'].items():
            if digest(lane/stage/name)!=value:raise ValueError('stage model/observation drift')
    # Labels/causal signal identity comes from previously independently audited
    # R330 records. This transitive reuse is explicit, not a claim of fresh data.
    raw=gzip.decompress((root/data['reference_training']).read_bytes()).decode();decoder=json.JSONDecoder();oldtrain=[]
    while raw.strip():
        raw=raw.lstrip();r,n=decoder.raw_decode(raw);oldtrain.append(r);raw=raw[n:]
    old=unpack(root/data['reference_later']);reference={(r['signal']['decision'],r['symbol']):r for r in oldtrain+[r for group in old.values() for r in group]}
    rows={'training':unpack(lane/'training/observations.json.gz'),'calibration':unpack(lane/'calibration/observations.json.gz'),
          'selection':unpack(lane/'selection/observations.json.gz'),**unpack(directory/'observations.json.gz')}
    bars={s:{} for s in config['symbols']};funds={}
    for r in data['raw_records']:
        packed=(root/r['path']).read_bytes();raw=gzip.decompress(packed)
        if hashlib.sha256(packed).hexdigest()!=r['gzip_sha256'] or hashlib.sha256(raw).hexdigest()!=r['raw_sha256']:raise ValueError('raw page/receipt mismatch')
        d=json.loads(raw)['data']
        for i,t in enumerate(d['time']):
            if type(t) is not int:raise ValueError('noninteger quote-bar clock')
            values=tuple(float(d[k][i]) for k in ('open','high','low','close','vol','amount'));at=t*1000+H
            if at in bars[r['symbol']] and bars[r['symbol']][at]!=values:raise ValueError('conflicting raw OHLC')
            bars[r['symbol']][at]=values
    # Primary funding rows are independent of production accrual/account code.
    import pandas as pd
    for s in config['symbols']:
        f=pd.read_parquet(root/f'data/equations_v2/mexc/funding/{s}_USDT.parquet');funds[s]={int(t):float(rate) for t,rate in zip(f.t,f.rate)}
    features=0;matched=0
    for phase,records in rows.items():
        prefix='train' if phase=='training' else phase
        start,end=ms(config[prefix+'_start']),ms(config[prefix+'_end'])
        keys=[(r['signal']['decision'],r['symbol']) for r in records]
        if len(keys)!=len(set(keys)) or set(keys)!={(d,s) for d in range(start,end,D) for s in config['symbols']}:raise ValueError('opportunity/date/asset omission')
        for r in records:
            key=r['signal']['decision'],r['symbol'];old=reference[key]
            if r['signal']!=old['signal'] or r['outcome']!=old['outcome']:raise ValueError('old causal target/tradability rule changed')
            matched+=1
            if r['outcome'] and r['outcome']['exit_time'] is not None and r['outcome']['exit_time']>=end:raise ValueError('future label crosses stage')
            if r['signal']['state']=='event':
                expected=feature_from_raw(r,bars)
                if (expected is None)!=(r['feature'] is None):raise ValueError('missing feature became0')
                if expected is not None:
                    for a,b in zip(expected,r['feature']):near(a,b)
                    features+=1
    export=read(lane/'training/base_export.json');meta=read(lane/'training/metadata.json');cal=read(lane/'calibration/calibrators.json')['maps']
    train=[r for r in rows['training'] if r['feature'] is not None and r['outcome'] and r['outcome']['financial_known']]
    for k in range(10):
        values=[r['feature'][k] for r in train];mean=sum(values)/len(values);scale=math.sqrt(sum((x-mean)**2 for x in values)/len(values)) or 1.
        near(mean,export['mean'][k]);near(scale,export['scale'][k])
    expected_counts=[sum(r['outcome']['label']==c for r in train) for c in CLASSES]
    if expected_counts!=meta['classes'] or sum(expected_counts)!=meta['n']:raise ValueError('training-only population mismatch')
    for k,c in enumerate(CLASSES):
        near(meta['prior'][k],(expected_counts[k]+1)/(len(train)+3))
        values=[r['outcome']['normalized_total'] for r in train if r['outcome']['label']==c]
        near(meta['class_payoffs'][k],sum(values)/len(values))
    predicted=unpack(directory/'predictions.json.gz');probability_vectors=0
    for phase in ('selection','validation'):
        records=rows[phase];stored=predicted[phase]['predictions']
        for i,r in enumerate(records):
            if r['feature'] is None:continue
            expected=base_probabilities(r['feature'],export)
            for b in ('ridge','tree'):
                for m in ('raw','temperature','dirichlet_identity'):
                    p=calibrated(expected[b],cal[b].get(m));actual=stored[b+'_'+m][i]
                    if (p is None)!=(actual is None):raise ValueError('unavailable calibration promoted')
                    if p is not None:
                        for a,v in zip(actual,p):near(a,v)
                        probability_vectors+=1
    selection=read(lane/'selection/selection.json');candidates=[]
    eligible=[i for i,r in enumerate(rows['selection']) if r['feature'] is not None and r['outcome'] and r['outcome']['label'] is not None]
    order=('frequency',)+NAMES[:-1]
    for name in order:
        p=predicted['selection']['predictions'][name]
        if any(p[i] is None for i in eligible):continue
        loss=sum(-math.log(canonical(p[i])[CLASSES.index(rows['selection'][i]['outcome']['label'])]) for i in eligible)/len(eligible)
        candidates.append((name,loss))
    if len(eligible)>=30:
        best=min(x[1] for x in candidates);winner=next(name for name in order if any(n==name and value<=best+1e-6 for n,value in candidates))
        if winner!=selection['winner']:raise ValueError('winner selected on wrong period/objective')
    books=unpack(directory/'accounts.json.gz');events=closed=accounts=0
    for phase,group in books.items():
        n,c=financial(group,bars,funds);events+=n;closed+=c;accounts+=len(group)
    result=read(directory/'results.json')
    if result['selected_model']!=selection['winner'] or result['actual_executable_net'] is not None or result['actual_order_allowed'] or result['new_prospective_days']:
        raise ValueError('unsupported winner/edge/prospective claim')
    return dict(state='PASS',matched_old_opportunities=matched,checked_new_feature_vectors=features,
        checked_base_calibrated_probability_vectors=probability_vectors,checked_shared_accounts=accounts,
        checked_financial_events=events,closed_position_repetitions=closed,selection_uses_validation=False,
        actual_executable_net=None,new_requests=0,scope='Receipt-bound rawOHLC features, independent exported-logit/calibration/selection and Fractioncash; oldtargets transitiveidentity, no fills/calibratedmarketconfidence')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('--out',type=Path);a=p.parse_args();r=audit(a.directory)
    raw=(json.dumps(r,sort_keys=True,indent=2)+'\n').encode()
    if a.out:
        with a.out.open('xb') as f:f.write(raw)
    print(raw.decode(),end='')
