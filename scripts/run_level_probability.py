"""R330 two-stage, offline close-level probability and net-cost diagnostic.

First commit code/spec, run --fit on training ONLY, commit model.json and its
sidecar, then evaluate calibration AND validation without tuning or selection.
Uses held cache identities; never fetches, restores or overwrites market data.
"""
import argparse
from collections import Counter
from decimal import Decimal, localcontext
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from lab import prereg
from lab.level_probability import DAY,HOUR,POLICIES,market,signal,outcome,fit,score,replay

LANE=ROOT/'experiments/level_probability_v1'


def encode(x):return (json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()


def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(data)


def ms(text):return int(pd.Timestamp(text,tz='UTC').timestamp()*1000)


def verify():
    prereg.verify(LANE/'PREREG.md');spec=(LANE/'PREREG.md').read_text()
    for name in ('config.json','data_inputs.json','code_inputs.json','sources.json'):
        if prereg.sha256_file(LANE/name) not in spec:raise ValueError('unbound R330 input '+name)
    code=json.loads((LANE/'code_inputs.json').read_text())
    from importlib.metadata import version
    if code['python_version']!=list(sys.version_info[:3]):raise ValueError('runtime drift')
    for name,v in code['packages'].items():
        if version(name)!=v:raise ValueError('numeric package drift '+name)
    for manifest in (code,json.loads((LANE/'data_inputs.json').read_text())):
        for name,digest in manifest['sha256'].items():
            if prereg.sha256_file(ROOT/name)!=digest:raise ValueError('frozen code/held source drift '+name)
    for name in ('PREREG.md','PREREG.sha256','code_inputs.json','data_inputs.json','config.json','sources.json'):
        require_committed(LANE/name)
    return json.loads((LANE/'config.json').read_text())


def require_committed(path):
    rel=path.resolve().relative_to(ROOT).as_posix()
    committed=subprocess.run(['git','show','HEAD:'+rel],cwd=ROOT,capture_output=True,check=True).stdout
    if committed!=path.read_bytes():raise ValueError('uncommitted research input '+rel)


def load_markets(config,*,training=False):
    out={}
    for symbol in config['symbols']:
        base=ROOT/'data/equations_v2/mexc'
        cutoff=ms(config['train_end']) if training else ms(config['source_end'])
        out[symbol]=market(pd.read_parquet(base/'prices'/f'{symbol}_USDT.parquet',
            filters=[('t','<',cutoff-HOUR)] if training else None),
            pd.read_parquet(base/'funding'/f'{symbol}_USDT.parquet',
            filters=[('t','<',cutoff)] if training else None),ms(config['source_start']),cutoff)
    return out


def observations(markets,start,end):
    rows=[]
    for d in range(start,end,DAY):
        for symbol,m in markets.items():
            s=signal(m,d)
            rows.append(dict(symbol=symbol,signal=s,outcome=outcome(m,s)))
    return rows


def rows_bytes(rows):
    return gzip.compress(b''.join(encode(r) for r in rows),mtime=0)


def statistics(account):
    days=account['days'];complete=account['complete'];vals=[float(r['net']) for r in days if r['net'] is not None]
    risk=None
    if complete:
        path=np.r_[0,np.cumsum(vals)];draw=path-np.maximum.accumulate(path)
        risk=dict(daily_std_usdt=float(np.std(vals,ddof=1)) if len(vals)>1 else None,
                  max_drawdown_usdt=float(draw.min()),maximum_initial_gross_usdt='2000',
                  matched_empirical_risk=False)
    by_symbol={}
    for symbol in sorted({t['symbol'] for t in account['tickets']}):
        tickets=[t for t in account['tickets'] if t['symbol']==symbol]
        with localcontext() as ctx:
            ctx.prec=80
            by_symbol[symbol]=dict(states=dict(Counter(t['state'] for t in tickets)),
                known_price=str(sum((Decimal(t['price']) for t in tickets if t['price'] is not None),Decimal(0))),
                known_funding=str(sum((Decimal(t['funding']) for t in tickets if t['funding'] is not None),Decimal(0))),
                known_cost=str(sum((Decimal(t['cost']) for t in tickets if t['cost'] is not None),Decimal(0))),
                net=str(sum((Decimal(t['net']) for t in tickets),Decimal(0))) if all(t['net'] is not None for t in tickets) else None)
    return {k:v for k,v in account.items() if k not in ('days','tickets','events')}|dict(
        days_expected=len(days),days_scored=len(vals),states=dict(Counter(t['state'] for t in account['tickets'])),
        by_symbol=by_symbol,risk=risk,full_expected_net=None,
        source_scope='historical trade-close/cost/funding-notional proxies; no first-seen execution evidence')


def fit_stage(out,config):
    markets=load_markets(config,training=True)
    rows=observations(markets,ms(config['train_start']),ms(config['train_end']))
    model=fit(rows)
    raw=rows_bytes(rows)
    model.update(registry_id='R330',config_sha256=prereg.sha256_file(LANE/'config.json'),
        data_inputs_sha256=prereg.sha256_file(LANE/'data_inputs.json'),
        training_records_sha256=hashlib.sha256(raw).hexdigest(),
        window=[config['train_start'],config['train_end']],
        selection='none: fixed before training; calibration/validation rows filtered out of fit_stage; full input bytes hashed only')
    model_raw=encode(model)
    save(out/'training.jsonl.gz',raw);save(out/'model.json',model_raw)
    save(out/'model.sha256',(hashlib.sha256(model_raw).hexdigest()+'\n').encode())
    return dict(state='TRAINING_ONLY',n=model['n'],model_sha256=hashlib.sha256(model_raw).hexdigest(),
                next='Commit model/training/sidecar before evaluation; no selection or retuning.')


def evaluate_stage(out,config,model_path):
    for path in (model_path,model_path.with_suffix('.sha256'),model_path.with_name('training.jsonl.gz')):
        require_committed(path)
    raw=model_path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    if digest!=model_path.with_suffix('.sha256').read_text().strip():raise ValueError('model identity drift')
    model=json.loads(raw)
    if model['config_sha256']!=prereg.sha256_file(LANE/'config.json') or model['data_inputs_sha256']!=prereg.sha256_file(LANE/'data_inputs.json'):
        raise ValueError('model/config/input mismatch')
    if hashlib.sha256(model_path.with_name('training.jsonl.gz').read_bytes()).hexdigest()!=model['training_records_sha256']:
        raise ValueError('training identity drift')
    markets=load_markets(config);results={};accounts={};all_rows={}
    for name in ('calibration','validation'):
        start,end=ms(config[name+'_start']),ms(config[name+'_end'])
        rows=observations(markets,start,end);all_rows[name]=rows
        scores=score(rows,model)
        accounts[name]=replay(rows,model,start,end)
        results[name]=dict(opportunities=len(rows),
            states=dict(Counter(r['signal']['reason'] or 'event' for r in rows)),
            outcome_states=dict(Counter((r['outcome']['reason'] or r['outcome']['label']) for r in rows if r['outcome'])),
            scores={k:({a:b for a,b in v.items() if a!='observations'} if k in ('conditional','climatology') else v) for k,v in scores.items()},
            accounts=[statistics(a) for a in accounts[name]])
    candidate=next(a for a in results['validation']['accounts'] if a['policy']=='conditional' and a['cost_multiple']==2)
    paired=results['validation']['scores']['paired_brier_difference']
    n=results['validation']['scores']['paired_n']
    if not candidate['complete'] or paired is None or n<100:
        screen='INCONCLUSIVE'
    elif candidate['states'].get('closed',0)==0:screen='NULL_INACTIVE'
    elif Decimal(candidate['conditional_net'])<=0:screen='NULL_COST_PROXY'
    elif paired>=0:screen='NULL_NO_PROBABILITY_GAIN'
    else:screen='PARTIAL_PROXY_ONLY'
    result=dict(registry_id='R330',verdict='PARTIAL',policy_screen=screen,method_id='M412',model_sha256=digest,
        strategy_variants=6,predictive_models=2,selection_or_retuning=False,windows=results,
        historical_out_of_sample=False,calibrated_uncertainty=None,actual_executable_net=None,
        new_prospective_days=0,actual_order_allowed=False,
        historical_acquisition=dict(requests_spent=7757,approved_requests=8000,reported_mib_spent='229.85',approved_mib=250,exact_remaining_bytes=None,reset=False),
        new_market_requests=0,
        limitations=config['limitations'])
    save(out/'results.json',encode(result))
    save(out/'observations.json.gz',gzip.compress(encode(all_rows),mtime=0))
    save(out/'accounts.json.gz',gzip.compress(encode(accounts),mtime=0))
    return result


def report(out=None,*,training=False):
    config=verify();out=Path(out or LANE/'results')
    if out.exists():raise FileExistsError('fresh output directory required; no overwrite')
    out.mkdir(parents=True)
    result=fit_stage(out,config) if training else evaluate_stage(out,config,LANE/'model.json')
    verify()
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fit',action='store_true');p.add_argument('--out',type=Path)
    a=p.parse_args();r=report(a.out,training=a.fit)
    print(json.dumps({k:v for k,v in r.items() if k not in ('windows','limitations')},sort_keys=True))


if __name__=='__main__':main()
