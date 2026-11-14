"""Independent R330 raw-close/label and Fraction cash oracle; zero network.

Does not import production label, probability, financial or account functions.
Checks conditional research arithmetic, not fills, fair notionals or inference.
"""
import argparse
import gzip
import hashlib
import json
import math
from fractions import Fraction as F
from pathlib import Path

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
LANE=ROOT/'experiments/level_probability_v1'
H=3_600_000
D=24*H


def read(p):return json.loads(p.read_text())
def near(a,b,tolerance=1e-14):
    if not math.isclose(float(a),float(b),rel_tol=tolerance,abs_tol=tolerance):
        raise ValueError(f'independent numeric mismatch: {a} versus {b}')


def check(directory):
    directory=Path(directory);result=read(directory/'results.json')
    spec=(LANE/'PREREG.md').read_bytes()
    if hashlib.sha256(spec).hexdigest()!=(LANE/'PREREG.sha256').read_text().strip():raise ValueError('spec drift')
    for name in ('config.json','data_inputs.json','code_inputs.json','sources.json'):
        if hashlib.sha256((LANE/name).read_bytes()).hexdigest() not in spec.decode():raise ValueError('unbound input')
    for name in ('data_inputs.json','code_inputs.json'):
        for path,sha in read(LANE/name)['sha256'].items():
            if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=sha:raise ValueError('input drift')
    model=read(LANE/'model.json')
    if hashlib.sha256((LANE/'model.json').read_bytes()).hexdigest()!=result['model_sha256']:raise ValueError('model drift')
    raw=gzip.decompress((LANE/'training.jsonl.gz').read_bytes()).decode()
    # Training uses pretty multiline JSON objects; independent incremental decoder.
    decoder=json.JSONDecoder();training=[]
    while raw.strip():
        raw=raw.lstrip();obj,n=decoder.raw_decode(raw);training.append(obj);raw=raw[n:]
    rows=json.loads(gzip.decompress((directory/'observations.json.gz').read_bytes()))
    books=json.loads(gzip.decompress((directory/'accounts.json.gz').read_bytes()))
    config=read(LANE/'config.json')
    all_windows={'training':training,**rows}
    for name,records in all_windows.items():
        prefix='train' if name=='training' else name
        start=int(pd.Timestamp(config[prefix+'_start'],tz='UTC').timestamp()*1000)
        end=int(pd.Timestamp(config[prefix+'_end'],tz='UTC').timestamp()*1000)
        expected={(d,s) for d in range(start,end,D) for s in config['symbols']}
        actual=[(r['signal']['decision'],r['symbol']) for r in records]
        if len(actual)!=len(set(actual)) or set(actual)!=expected:raise ValueError('date/asset cutoff or missing opportunity')
        if any(r['outcome'] and r['outcome']['exit_time'] is not None and r['outcome']['exit_time']>=end for r in records):
            raise ValueError('training/calibration/validation label crosses registered boundary')
    prices={};funds={};valid={};funding_known={}
    for sym in ('BTC','ETH','SOL','WIF'):
        p=pd.read_parquet(ROOT/f'data/equations_v2/mexc/prices/{sym}_USDT.parquet')
        f=pd.read_parquet(ROOT/f'data/equations_v2/mexc/funding/{sym}_USDT.parquet')
        prices[sym]={int(t)+H:float(c) for t,c in zip(p.t,p.close)}
        valid[sym]={int(t)+H:math.isfinite(c) and c>0 and math.isfinite(v) and v>0 for t,c,v in zip(p.t,p.close,p.vol)}
        funds[sym]={int(t):float(r) for t,r in zip(f.t,f.rate)}
        known=set(int(t) for t in f.t)
        for k in range(1,len(f)):
            gap=(int(f.t.iloc[k])-int(f.t.iloc[k-1]))//H
            if all(math.isfinite(c) and c>0 and abs(gap-c)<1e-9 for c in (f.cycle_h.iloc[k-1],f.cycle_h.iloc[k])):
                known.update(range(int(f.t.iloc[k-1])+H,int(f.t.iloc[k])+H,H))
        funding_known[sym]=known
    checked_labels=0;checked_signals=0
    for r in training+[x for values in rows.values() for x in values]:
        s=r['signal'];d=s['decision'];sym=r['symbol'];p=prices[sym];v=valid[sym]
        if not all(v.get(t,False) for t in range(d-72*H,d+H,H)):
            if s['state']=='event':raise ValueError('future/missing features admitted')
            continue
        x=[math.log(p[t]) for t in range(d-72*H,d+H,H)]
        sigma=math.sqrt(12*sum((b-a)**2 for a,b in zip(x[:-1],x[1:]))/72)
        if not sigma>0:continue
        low,high=min(x[:-1]),max(x[:-1]);side=-1 if abs(x[-1]-low)<=abs(x[-1]-high) else 1
        level=low if side==-1 else high
        eligible=abs(x[-1]-level)<=.25*sigma
        if eligible!=(s['state']=='event'):raise ValueError('raw causal event mismatch')
        checked_signals+=1
        if not eligible:continue
        near(s['sigma'],sigma);near(s['level'],math.exp(level))
        if s['side']!=side or s['cell']!=('approach' if side*(x[-1]-x[-25])>=0 else 'recede'):
            raise ValueError('source signal direction/cell mismatch')
        o=r['outcome'];en=d+H
        if not v.get(en,False):
            if o['entry'] is not None:raise ValueError('entry gap manufactured')
            continue
        near(o['entry'],p[en]);expected=None;exit_time=None
        for t in range(en+H,en+13*H,H):
            if not v.get(t,False):break
            z=side*math.log(p[t]/p[en])
            if z>=sigma:expected='break'
            elif z<=-sigma:expected='rebound'
            elif t==en+12*H:expected='timeout'
            if expected:exit_time=t;break
        if o['label']!=expected or o['exit_time']!=exit_time:raise ValueError('raw delayed close-barrier mismatch')
        if exit_time is not None:
            near(o['exit'],p[exit_time]);near(o['price_outside'],side*(p[exit_time]/p[en]-1))
            if o['financial_known']!=all(t in funding_known[sym] for t in range(en+H,exit_time+H,H)):
                raise ValueError('funding interval certified without both adjacent cycles')
            if o['financial_known']:
                expected_events=[(t,p[t],rate) for t,rate in funds[sym].items() if en<t<=exit_time and rate!=0]
                if [list(x) for x in expected_events]!=o['funding_events']:raise ValueError('funding source omission or boundary error')
                near(o['funding_outside'],-side*sum(p0*rate for _,p0,rate in expected_events)/p[en])
                near(o['normalized_total'],(o['price_outside']+o['funding_outside'])/sigma)
        checked_labels+=1
    clean=[r for r in training if (r['outcome'] or {}).get('financial_known')]
    classes=('break','rebound','timeout');counts=[sum(r['outcome']['label']==c for r in clean) for c in classes]
    if counts!=model['counts'] or len(clean)!=model['n']:raise ValueError('training-only fit population mismatch')
    base=[(n+1)/(len(clean)+3) for n in counts]
    if model['probability'] is not None:
        for a,b in zip(base,model['probability']):near(a,b)
    for k,c in enumerate(classes):
        values=[r['outcome']['normalized_total'] for r in clean if r['outcome']['label']==c]
        if len(values)>=5:near(model['class_payoff_means'][k],sum(values)/len(values))
        elif model['class_payoff_means'][k] is not None:raise ValueError('sparse class payoff invented')
    for cell in ('approach','recede'):
        sub=[r for r in clean if r['signal']['cell']==cell]
        n=[sum(r['outcome']['label']==c for r in sub) for c in classes]
        if n!=model['cells'][cell]['counts']:raise ValueError('conditional cell count mismatch')
        if model['cells'][cell]['probability'] is not None:
            for a,b in zip(model['cells'][cell]['probability'],[(c+20*p)/(len(sub)+20) for c,p in zip(n,base)]):near(a,b)
    checked_events=0;checked_accounts=0;closed=0
    for window,accounts in books.items():
        for a in accounts:
            price=F(0);funding=F(0);cost=F(0);positions={};opened={};pending=0
            for e in a['events']:
                symbol=e['symbol']
                if e['kind']=='fill':
                    q=F(e['quantity']);p=F(e['price']);fee=F(e['fee']);oldq,basis=positions.get(symbol,(F(0),F(0)))
                    if oldq:
                        if q!=-oldq:raise ValueError('not a full close/no borrowing repair')
                        price+=oldq*(p-basis);positions[symbol]=(F(0),F(0));closed+=1
                    else:
                        if abs(q*p-F(500))>F(1,10**18):raise ValueError('fixed500 notional drift')
                        positions[symbol]=(q,p)
                        opened[symbol]=e['occurred_ns']//1_000_000
                    # Independent source-close and literal lumped8bp/side fee.
                    stamp=e['occurred_ns']//1_000_000
                    near(e['price'],prices[symbol][stamp])
                    if abs(fee-abs(q)*p*F(8,10000)*a['cost_multiple'])>F(1,10**18):raise ValueError('cost/double-counting mismatch')
                    cost+=fee
                elif e['kind']=='funding':
                    if e['amount'] is None:pending+=1
                    else:
                        stamp=e['occurred_ns']//1_000_000
                        quantity=positions[symbol][0]
                        expected=-quantity*sum((F(str(prices[symbol][t]))*F(str(rate))
                            for t,rate in funds[symbol].items() if opened[symbol]<t<=stamp),F(0))
                        if abs(F(e['amount'])-expected)>F(1,10**16):raise ValueError('raw signed funding cash mismatch')
                        funding+=F(e['amount'])
                else:raise ValueError('unexpected financial event')
                checked_events+=1
            for name,expected in (('price',price),('funding',funding),('cost',cost),('shared_cash',F(10000)+price+funding-cost)):
                if abs(F(a[name])-expected)>F(1,10**16):raise ValueError('shared account Fraction cash mismatch '+name)
            if pending!=a['pending']:raise ValueError('pending cash manufactured')
            if a['complete']:
                if any(q for q,_ in positions.values()) or pending:raise ValueError('incomplete account called complete')
                near(a['conditional_net'],price+funding-cost)
            if a['actual_executable_net'] is not None or a['actual_order_allowed']:raise ValueError('unsupported execution claim')
            checked_accounts+=1
        # All tiers must share entry tickets, including common3x capital stops.
        for policy in ('conditional','climatology','always_break','always_rebound','long_control','cash'):
            paths=[a for a in accounts if a['policy']==policy]
            identities=[[(t['decision'],t['symbol'],t.get('quantity')) for t in a['tickets'] if t['state'] in ('closed','funding_unknown','exit_unknown')] for a in paths]
            if not all(x==identities[0] for x in identities):raise ValueError('cost-dependent entry rescue')
    if result['new_prospective_days'] or result['actual_executable_net'] is not None or result['actual_order_allowed']:
        raise ValueError('unsupported return/prospective claim')
    return dict(state='PASS',checked_raw_signals=checked_signals,checked_close_labels=checked_labels,
        checked_shared_accounts=checked_accounts,checked_financial_events=checked_events,closed_positions=closed,
        scope='Raw causal close labels, training counts/shrinkage and independent Fraction common-cash oracle; not venue fills/calibrated inference/net edge',new_requests=0)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);a=p.parse_args();print(json.dumps(check(a.directory),sort_keys=True))
