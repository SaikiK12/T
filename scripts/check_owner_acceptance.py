"""R320 independent literal risk-target/forecast and paper-report audit.

Does not call the production target/forecast/QLIKE/threshold functions, choose
a policy, repair gaps or infer prospective profit. Reads one pinned held file.
"""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def audit(directory):
    import pandas as pd
    directory=Path(directory);lane=ROOT/'experiments/owner_acceptance_v1'
    data=json.loads((lane/'data_inputs.json').read_text())
    path='data/equations_v2/mexc/prices/BTC_USDT.parquet'
    if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=data['sha256'][path]:raise ValueError('raw audit input drift')
    frame=pd.read_parquet(ROOT/path)
    hour=3_600_000;day=24*hour
    start=int(pd.Timestamp('2025-04-01',tz='UTC').timestamp()*1000)
    end=int(pd.Timestamp('2026-10-01',tz='UTC').timestamp()*1000)
    points={int(r.t)+hour:(float(r.close),float(r.vol)) for r in frame.itertuples()}
    hourly=[]
    for t in range(start+hour,end+hour,hour):
        a,b=points.get(t-hour),points.get(t)
        valid=a and b and all(math.isfinite(x) and x>0 for x in (*a,*b))
        hourly.append(math.log(b[0]/a[0]) if valid else None)
    rv=[]
    for i in range(0,len(hourly),24):
        x=hourly[i:i+24];rv.append(sum(v*v for v in x) if all(v is not None for v in x) else None)
    rows=[json.loads(x) for x in gzip.decompress((directory/'risk_predictions.jsonl.gz').read_bytes()).splitlines()]
    expected=(end-int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()*1000))//day
    if len(rows)!=expected:raise ValueError('missing validation day rows')
    checked=0
    def close(a,b,label):
        if (a is None)!=(b is None) or a is not None and not math.isclose(a,b,rel_tol=2e-12,abs_tol=1e-16):
            raise ValueError('independent risk oracle disagreement: '+label)
    for row in rows:
        t=int(pd.Timestamp(row['day'],tz='UTC').timestamp()*1000);i=(t-start)//day
        close(row['target_rv'],rv[i],'daily target')
        predictions={}
        for n in (1,7,30):
            h=rv[max(0,i-n):i];predictions['mean'+str(n)]=sum(h)/n if len(h)==n and all(v is not None for v in h) else None
        x=hourly[i*24-168:i*24]
        if i>=7 and all(v is not None for v in x):
            weights=[.5**((167-j)/72) for j in range(168)]
            predictions['ewma72']=24*sum(w*v*v for w,v in zip(weights,x))/sum(weights)
        else:predictions['ewma72']=None
        for m,p in predictions.items():
            close(row['forecasts'][m],p,m)
            loss=math.log(p)+rv[i]/p if p is not None and p>0 and rv[i] is not None else None
            close(row['qlike'][m],loss,m+' loss');checked+=1
    result=json.loads((directory/'results.json').read_text())
    if result['activation_allowed'] is not False or result['new_prospective_days']!=0 or result['new_market_requests']!=0:
        raise ValueError('unsupported activation/acquisition/prospective claim')
    if result['risk_summary']['historical_state']!='HALTED':raise ValueError('old capture admitted')
    for k,t in result['entry_thresholds'].items():
        if t['model_entry_allowed'] or t['expected_net_lower_quote'] is not None or t['actual_order_allowed']:
            raise ValueError('unknown forecast/error became entry or zero-profit fact')
    coverage=json.loads((directory/'requirements_coverage.json').read_text())
    if [x['id'] for x in coverage['items']]!=list(range(1,101)):raise ValueError('owner scope loss')
    if coverage['all100_implemented'] or coverage['all100_market_validated']:raise ValueError('unsupported100-completed claim')
    return {'independent_daily_forecast_losses_checked':checked,'validation_rows':len(rows),
        'owner_requirements':100,'historical_entries_blocked':True,'unknown_net_forecast_preserved':True,
        'scope':'Literal raw-target/finite forecast/loss and report guards; not independent source authentication,bootstrap validity or profitable strategy evidence.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,default=ROOT/'experiments/owner_acceptance_v1')
    print(json.dumps(audit(p.parse_args().directory),sort_keys=True))
