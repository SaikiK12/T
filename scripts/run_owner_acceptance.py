"""R320 finite risk/component validation and integrated owner acceptance evidence.

Offline only. Verifies frozen code, source scope and already-held input identity
before calculation. No strategy selection, collection, scheduling or orders.
"""
import argparse
from collections import Counter
from decimal import Decimal as D
import gzip
import hashlib
import io
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time
import tracemalloc

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from lab import prereg
from lab.artifact_io import ContentFrameCache,read_bytes,export_verified
from lab.paper_controls import PaperRisk,RiskPolicy,entry_threshold
from lab.stream_quotes import FrameClock,NS
from lab.volatility_validation import daily_returns,forecasts,loss,block_intervals,null_calibration,MODELS

LANE=ROOT/'experiments/owner_acceptance_v1'
INPUT=ROOT/'data/equations_v2/mexc/prices/BTC_USDT.parquet'
sha=prereg.sha256_file


def encode(obj):return (json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()


def write_new(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as h:h.write(raw)


def verify(lane=LANE):
    from importlib.metadata import version
    prereg.verify(lane/'PREREG.md');spec=(lane/'PREREG.md').read_text()
    for name in ('code_inputs.json','data_inputs.json','fixtures.json','requirements.json',
                 'requirements_evidence.json','sources.json','benchmark_environment.json'):
        if sha(lane/name) not in spec:raise ValueError('unbound acceptance input: '+name)
    code=json.loads((lane/'code_inputs.json').read_text())
    if code['python_version']!=list(sys.version_info[:3]):raise ValueError('registered runtime drift')
    if any(version(k)!=v for k,v in code['packages'].items()):raise ValueError('registered numeric package drift')
    for name,digest in code['sha256'].items():
        if sha(ROOT/name)!=digest:raise ValueError('R320 code identity drift: '+name)
    data=json.loads((lane/'data_inputs.json').read_text())
    if data['already_seen'] is not True:raise ValueError('historical seen-scope marker missing')
    for name,digest in data['sha256'].items():
        if sha(ROOT/name)!=digest:raise ValueError('R320 held input drift: '+name)
    return data


def risk_forecasts(frame,settings,out):
    start,end,validation=(int(pd.Timestamp(settings[k]).timestamp()*1000) for k in ('start','end','validation_start'))
    dates,hourly,y=daily_returns(frame,start,end);pred=forecasts(hourly,y);ql=loss(y[:,None],pred)
    valid=dates>=validation;common=valid&np.isfinite(ql).all(axis=1)
    daily=[]
    for i in np.flatnonzero(valid):
        daily.append({'day':pd.Timestamp(int(dates[i]),unit='ms',tz='UTC').strftime('%Y-%m-%d'),
            'target_rv':None if not np.isfinite(y[i]) else float(y[i]),
            'forecasts':{m:None if not np.isfinite(pred[i,j]) else float(pred[i,j]) for j,m in enumerate(MODELS)},
            'qlike':{m:None if not np.isfinite(ql[i,j]) else float(ql[i,j]) for j,m in enumerate(MODELS)},
            'common_scored':bool(common[i])})
    raw=b''.join(json.dumps(r,sort_keys=True,allow_nan=False).encode()+b'\n' for r in daily)
    write_new(out/'risk_predictions.jsonl.gz',gzip.compress(raw,mtime=0))
    expected=int(valid.sum());complete=int(common.sum())==expected and expected==273
    reference=1;comparators=(0,2,3);paired=ql[common][:,comparators]-ql[common][:,[reference]]
    intervals=[block_intervals(paired,block=b) for b in (7,14)] if complete else []
    calibration=null_calibration()
    # A dependent-null diagnostic can expose poor coverage. It cannot prove
    # finite-sample or program-wide inference; no candidate is selected here.
    for r in calibration:
        n=r['paths'];p=r['fraction'];z=1.96;den=1+z*z/n
        center=(p+z*z/(2*n))/den;half=z*((p*(1-p)/n+z*z/(4*n*n))**.5)/den
        r['wilson_95_interval']=[max(0,center-half),min(1,center+half)]
    metrics=[]
    for j,m in enumerate(MODELS):
        available=valid&np.isfinite(ql[:,j])
        metrics.append({'model':m,'available_scored_days':int(available.sum()),
            'common_mean_qlike':float(ql[common,j].mean()) if common.any() else None,
            'common_mean_squared_error':float(((y[common]-pred[common,j])**2).mean()) if common.any() else None,
            'mean_forecast_rv':float(pred[common,j].mean()) if common.any() else None})
    influence=[]
    if common.any():
        # Keep all days. Five largest absolute contributions are reported,
        # never excluded to select a more flattering policy/holding window.
        ids=np.flatnonzero(common)
        for j,m in enumerate(('mean1','mean30','ewma72')):
            ix=np.argsort(-np.abs(paired[:,j]),kind='stable')[:5]
            influence.append({'model_vs_mean7':m,'all_day_difference_sum':float(paired[:,j].sum()),
                'largest_five_absolute_contribution':float(np.abs(paired[ix,j]).sum()),
                'total_absolute_contribution':float(np.abs(paired[:,j]).sum()),
                'days_retained':[pd.Timestamp(int(dates[ids[i]]),unit='ms',tz='UTC').strftime('%Y-%m-%d') for i in ix]})
    return {'state':'COMPONENT_ASSESSED' if complete else 'INCONCLUSIVE',
        'scope':'Already-seen BTC univariate EWMA risk forecast; no PIT top20 APSI, implied volatility, direction, market strategy or net-PnL test.',
        'validation_days':expected,'common_scored_days':int(common.sum()),'unscored_days':expected-int(common.sum()),
        'models':metrics,'reference':'mean7','comparators':['mean1','mean30','ewma72'],
        'paired_difference_sign':'negative means lower QLIKE loss than the preselected mean7 reference',
        'intervals':intervals,'dependent_null_calibration':calibration,'influence':influence,
        'trial_count':4,'winner_selected':False,'activation_allowed':False,'new_prospective_days':0,
        'uncertainty_scope':'Fixed local family only; neither historical adaptive search nor unknown future regimes are controlled.',
        'cost_sensitivity':[{'multiple':k,'net_pnl':None,'scope':'Variance loss is not money; fixed cost tiers apply to paper controls, not QLIKE.'} for k in (1,2,3)],
        'observations_sha256':sha(out/'risk_predictions.jsonl.gz')}


def benchmark(frame,digest,out,environment):
    """Five fixed warmed rounds; exact outputs required before speed comparison."""
    from collections import OrderedDict
    cache=ContentFrameCache();methods=OrderedDict()
    def pandas_read():
        raw,h=read_bytes(INPUT)
        if h!=digest:raise ValueError('benchmark input drift')
        return pd.read_parquet(io.BytesIO(raw))
    def arrow_read():
        raw,h=read_bytes(INPUT)
        if h!=digest:raise ValueError('benchmark input drift')
        return pq.read_table(pa.BufferReader(raw)).to_pandas()
    methods['pandas']=pandas_read;methods['pyarrow']=arrow_read
    methods['content_cache']=lambda:cache.load(INPUT,expected_sha256=digest)[0]
    duck=None;dependency='UNAVAILABLE'
    vendor=ROOT/'.cache/owner100/vendor'
    if vendor.is_dir():
        # The optional isolated wheel is not a core runtime/CI dependency.
        expected=environment['vendor_sha256']
        actual={str(p.relative_to(vendor)) for p in vendor.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        if actual!=set(expected):raise ValueError('isolated optional dependency inventory drift')
        for relative,digest_expected in expected.items():
            p=vendor/relative
            if p.is_symlink() or sha(p)!=digest_expected:raise ValueError('isolated optional dependency bytes drift')
        sys.path.insert(0,str(vendor))
        import duckdb
        if duckdb.__version__!=environment['version']:raise ValueError('optional DuckDB version drift')
        duck=duckdb.connect(':memory:');duck.execute('SET threads=1')
        def duck_read():
            _,h=read_bytes(INPUT)
            if h!=digest:raise ValueError('benchmark input drift')
            return duck.execute('SELECT * FROM read_parquet(?)',[str(INPUT)]).fetchdf()
        methods['duckdb']=duck_read;dependency='AVAILABLE_PINNED_VERSION'
    timings={k:[] for k in methods};peaks={k:[] for k in methods}
    try:
        for fn in methods.values():pd.testing.assert_frame_equal(frame,fn(),check_exact=True,check_dtype=True)
        names=list(methods)
        for rep in range(5):
            order=names[rep%len(names):]+names[:rep%len(names)]
            for name in order:
                tracemalloc.start();t=time.perf_counter_ns();f=methods[name]();dt=time.perf_counter_ns()-t
                _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
                pd.testing.assert_frame_equal(frame,f,check_exact=True,check_dtype=True)
                timings[name].append(dt);peaks[name].append(peak)
    finally:
        if duck is not None:duck.close()
    exported=export_verified(frame,out/'verified_input.parquet',source_sha256=digest,
        price_role='historical traded hourly close; not executable bid/ask/funding index',
        clock_role='source bar open milliseconds; not first-seen receive/execution time')
    exported['path']='verified_input.parquet'
    return {'input_sha256':digest,'input_file_bytes':INPUT.stat().st_size,
        'frame_bytes':int(frame.memory_usage(index=True,deep=True).sum()),'rows':len(frame),
        'methods':[{'method':k,'nanosecond_runs':v,'median_ns':statistics.median(v),
                    'python_traced_peak_bytes':peaks[k],'equal_values_types_missing_order':True} for k,v in timings.items()],
        'duckdb_state':dependency,'versions':{'pandas':pd.__version__,'pyarrow':pa.__version__,
            'duckdb':environment['version'] if duck is not None else None},
        'export':exported,'warm_runs':5,'cold_disk_benchmark':False,
        'scope':'One402923-byte held numeric table; every path hashes current input, cache returns an independent copy. Python traced allocation excludes much native memory; no RSS claim.',
        'rust_port':'NOT_SELECTED: this study measures I/O and existing vectorized/native arithmetic; no demonstrated CPU kernel justifying a new Rust implementation.'}


def controls(parent,fixtures,out):
    anchor=FrameClock(**fixtures['anchor']);initial={('mexc','USDT'):5000,('lighter','USDC'):5000}
    policy=RiskPolicy('R320-fixed-unlevered');rows=[]
    with tempfile.TemporaryDirectory(prefix='R320-risk-') as d:
        for i,case in enumerate(parent['cases']):
            snapshot=case['snapshot'];at=snapshot['asof_mono_ns']
            risk=PaperRisk(Path(d)/(str(i)+'.jsonl'),policy,anchor,contract_version='invented-v1',initial_balances=initial)
            r=risk.observe(snapshot,asof=at,clock=FrameClock(anchor.utc_ns+at-anchor.mono_ns,at),
                complete=True,session_open=True,fee_inputs_known=True,contract_version='invented-v1',
                expected_contract_version='invented-v1',mode='fixture')
            rows.append({'case':case['name'],'cost_multiple':case['cost_multiple'],'risk':r})
        baseline=next(c['snapshot'] for c in parent['cases'] if c['name']=='both_legs_then_exit' and c['cost_multiple']==1)
        p=Path(d)/'historical.jsonl';risk=PaperRisk(p,policy,anchor,contract_version='invented-v1',initial_balances=initial)
        at=baseline['asof_mono_ns']
        historical=risk.observe(baseline,asof=at,clock=FrameClock(anchor.utc_ns+at-anchor.mono_ns,at),complete=True,
            session_open=True,fee_inputs_known=True,contract_version='invented-v1',expected_contract_version='invented-v1',mode='historical')
        if historical['model_new_entries_allowed'] or historical['actual_order_allowed']:raise ValueError('historical account activated')
        write_new(out/'risk_controls.jsonl',b''.join(json.dumps(r,sort_keys=True,allow_nan=False).encode()+b'\n' for r in rows))
        write_new(out/'risk_journal_example.jsonl',p.read_bytes())
    return baseline,{'lifecycle_paths':len(rows),'by_state':dict(Counter(r['risk']['state'] for r in rows)),
        'historical_state':historical['state'],'historical_stops':historical['stops'],
        'scope':'Supplied invented lifecycle states; not authenticated account/session/fee/market evidence.',
        'journal_sha256':sha(out/'risk_journal_example.jsonl')}


def coverage(lane,out):
    owner=json.loads((lane/'requirements.json').read_text());proof=json.loads((lane/'requirements_evidence.json').read_text())
    if [r['id'] for r in owner['requirements']]!=list(range(1,101)):raise ValueError('exact owner100 numbering required')
    if {r['id'] for r in proof['items']}!=set(range(1,101)):raise ValueError('complete proof mapping required')
    byid={r['id']:dict(r) for r in proof['items']};items=[]
    performance=json.loads((out/'performance.json').read_text())
    if performance['duckdb_state']!='AVAILABLE_PINNED_VERSION':
        byid[52].update(state='partial',reason='DuckDB isolé indisponible dans cette reproduction ; seuls les outils réellement présents sont comparés.')
    result=json.loads((out/'results.json').read_text())
    if result['cache_integration']['export_consumer']['cache_hit'] is not True:raise ValueError('shared content parse not exercised')
    if performance['export']['roundtrip_exact'] is not True:raise ValueError('unverified format export')
    profile=json.loads((lane/'test_profile.json').read_text())
    if profile['successful'] is not True or profile['suite']!='full':raise ValueError('full test gate missing')
    for requirement in owner['requirements']:
        p=byid[requirement['id']]
        if p['state'] not in ('verified','partial','blocked','not_selected'):raise ValueError('explicit acceptance state required')
        for path in p['evidence']:
            candidate=out/path[2:] if path.startswith('./') else ROOT/path
            if not candidate.is_file() or candidate.is_symlink():raise ValueError('acceptance proof missing: '+path)
        items.append({**requirement,**p})
    result={'scope':'Exact owner requirements and bounded proof acceptance; no second methods queue, no market-validation or100-completed claim.',
        'owner_requirements_sha256':sha(lane/'requirements.json'),'items':items,
        'counts':dict(Counter(r['state'] for r in items)),
        'priority_counts':dict(Counter(r['state'] for r in items if r['id']<=20)),
        'all100_implemented':False,'all100_market_validated':False}
    write_new(out/'requirements_coverage.json',encode(result));return result['counts']


def report(lane=LANE,out=None):
    data=verify(lane);out=Path(out) if out is not None else lane
    if (out/'results.json').exists():raise ValueError('Existing result retained; explicit new --out needed for reproduction, not an automatic rerun.')
    out.mkdir(parents=True,exist_ok=True)
    parent=json.loads((ROOT/'experiments/paired_execution_v1/results.json').read_text())
    fixtures=json.loads((lane/'fixtures.json').read_text());environment=json.loads((lane/'benchmark_environment.json').read_text())
    cache=ContentFrameCache();frame,first=cache.load(INPUT,expected_sha256=data['sha256'][str(INPUT.relative_to(ROOT))])
    forecast=risk_forecasts(frame,fixtures['risk_forecast'],out)
    # The risk and export consumers share a content-bound parse, with copies.
    again,second=cache.load(INPUT,expected_sha256=first['source_sha256'])
    pd.testing.assert_frame_equal(frame,again,check_exact=True)
    performance=benchmark(again,first['source_sha256'],out,environment)
    write_new(out/'performance.json',encode(performance))
    snapshot,risk=controls(parent,fixtures,out)
    result={'registry_id':'R320','simulation_only':True,'activation_allowed':False,
        'scope':'Owner100 integration acceptance plus finite historical risk-component and measured tools; no positive net-alpha claim.',
        'paper_snapshot':snapshot,'risk_summary':risk,'risk_forecasts':forecast,
        'entry_thresholds':{str(k):entry_threshold(None,None,None,asset='USDT',cost_multiple=k) for k in (1,2,3)},
        'cache_integration':{'first':first,'export_consumer':second},
        'data_identity_sha256':sha(lane/'data_inputs.json'),'code_identity_sha256':sha(lane/'code_inputs.json'),
        'new_market_requests':0,'new_prospective_days':0,'risk_model_variants':4,'strategy_variants':0,
        'historical_allowance':{'requests_spent':7757,'approved_requests':8000,'reported_mib_spent':'229.85','approved_mib':250,
            'exact_remaining_bytes':None,'rounded_prior_wire_total_is_not_exact':True},
        'performance_report':'performance.json','performance_is_nondeterministic':True}
    verify(lane);write_new(out/'results.json',encode(result))
    result_counts=coverage(lane,out)
    return {'results':str(out/'results.json'),'acceptance_states':result_counts}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path)
    print(json.dumps(report(out=p.parse_args().out),sort_keys=True))
