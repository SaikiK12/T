"""R321 registered null-only size/power study; no market outcome is read."""
import argparse
from collections import Counter
import gzip
from importlib.metadata import version
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from lab import prereg
from lab.dependent_null import N,FAMILY,BLOCKS,METHODS,obm,calibrate,calibrated_intervals,iid_intervals,binomial_interval
from lab.volatility_validation import block_intervals

LANE=ROOT/'experiments/dependent_null_v1'
sha=prereg.sha256_file


def encode(obj):return (json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()


def new(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as h:h.write(raw)


def verify(lane=LANE):
    prereg.verify(lane/'PREREG.md');spec=(lane/'PREREG.md').read_text()
    for name in ('code_inputs.json','inputs.json','design.json','sources.json'):
        if sha(lane/name) not in spec:raise ValueError('unbound null-study contract: '+name)
    code=json.loads((lane/'code_inputs.json').read_text())
    if code['python_version']!=list(sys.version_info[:3]) or any(version(k)!=v for k,v in code['packages'].items()):raise ValueError('null-study runtime drift')
    for name,digest in code['sha256'].items():
        if sha(ROOT/name)!=digest:raise ValueError('null-study code drift: '+name)
    for name,digest in json.loads((lane/'inputs.json').read_text())['sha256'].items():
        if sha(ROOT/name)!=digest:raise ValueError('null-study input identity drift: '+name)
    return json.loads((lane/'design.json').read_text())


def generate(profile,seed):
    """273trivariate artificial days, unit stationary marginal SD before stress.

    Common innovation factor produces0.5 cross-coordinate correlation. Shift
    alternatives later use the same held-out noise paths; no winner selection.
    """
    rng=np.random.default_rng(seed);rho=profile['rho'];tail=profile['tail'];shape=(N+128,FAMILY+1)
    if tail=='gaussian':noise=rng.normal(size=shape)
    elif tail=='t5':noise=rng.standard_t(5,size=shape)*np.sqrt(3/5)
    elif tail=='jump':
        noise=(rng.normal(size=shape)+10*(rng.random(shape)<.01)*rng.choice([-1,1],size=shape))/np.sqrt(2)
    else:raise ValueError('undeclared innovation profile')
    innovations=(noise[:,:FAMILY]+noise[:,[FAMILY]])/np.sqrt(2)
    x=np.zeros((N+128,FAMILY));scale=np.sqrt(1-rho*rho)
    for t in range(1,len(x)):x[t]=rho*x[t-1]+scale*innovations[t]
    x=x[128:]
    if profile.get('kind')=='variance_step':x[N//2:]*=3
    return x


def base_intervals(x,calibration,seed):
    days=np.arange(N);out={'iid_gaussian':iid_intervals(x,days)}
    c=block_intervals(x,block=14,repetitions=400,seed=seed)
    out['circular14']={'state':'ASSESSED','lower':c['lower'],'upper':c['upper']}
    for b in BLOCKS:
        out['calibrated_obm'+str(b)]=(calibrated_intervals(x,days,block=b,calibration=calibration)
            if calibration['state']=='CALIBRATED' else {'state':'INCONCLUSIVE','lower':None,'upper':None})
    return out


def flags(interval,shift):
    if interval['lower'] is None or interval['upper'] is None:return None
    lower=np.asarray(interval['lower'],float).copy();upper=np.asarray(interval['upper'],float).copy()
    if not np.isfinite(lower).all() or not np.isfinite(upper).all():return None
    lower[0]+=shift;upper[0]+=shift
    reject=(lower>0)|(upper<0)
    return {'any_rejection':bool(reject.any()),'null_coordinate_exclusion':bool(reject[1:].any()),
            'positive_detection':bool(lower[0]>0),'wrong_sign':bool(upper[0]<0)}


def summarize_cell(profile,method,shift,records,expected):
    available=[r for r in records if r is not None];n=len(available)
    out={'profile':profile['id'],'kind':profile['kind'],'rho':profile['rho'],'tail':profile['tail'],
        'method':method,'effect_shift':shift,'paths':expected,'scored_paths':n,'unscored_paths':expected-n,
        'state':'COMPLETE' if n==expected else 'INCONCLUSIVE','family_false_exclusions':None,'power':None,
        'scope':'Registered simulated daily mean differences; not returns or executed profit.'}
    if not n:return out
    if shift==0:
        count=sum(r['any_rejection'] for r in available);out.update({'family_false_exclusions':count,
            'family_false_exclusion_fraction':count/n,'exact_binomial_interval':binomial_interval(count,n,comparisons=40)})
    else:
        count=sum(r['positive_detection'] for r in available);out.update(positive_detections=count,power=count/n,
            power_exact_binomial_interval=binomial_interval(count,n,comparisons=96),
            wrong_signs=sum(r['wrong_sign'] for r in available),
            null_coordinate_false_exclusions=sum(r['null_coordinate_exclusion'] for r in available))
    return out


def assess(rows,profile_ids):
    """Preset finite null/power criteria, never a market strategy-selection gate."""
    if len(profile_ids)!=10 or len(set(profile_ids))!=10:raise ValueError('exact ten held-out null profiles required')
    reports=[]
    for m in METHODS:
        size=[r for r in rows if r['method']==m and r['effect_shift']==0]
        signals=[r for r in rows if r['method']==m and r['profile']=='gaussian_rho0.6' and r['effect_shift']==.5]
        signal=signals[0] if len(signals)==1 else {'state':'INCONCLUSIVE','power':None,'profile':'gaussian_rho0.6'}
        failures=[r['profile'] for r in size if r['state']!='COMPLETE' or
            r.get('family_false_exclusion_fraction',1)>.05 or r.get('exact_binomial_interval',[0,1])[1]>.05]
        seen=[r['profile'] for r in size]
        failures+=sorted(set(profile_ids)-set(seen))+sorted(set(seen)-set(profile_ids))
        if len(seen)!=len(set(seen)):failures.append('duplicate_null_profile')
        power_ok=signal['state']=='COMPLETE' and signal.get('power',0)>=.20
        candidate=not failures and power_ok and m.startswith('calibrated_obm')
        reports.append({'method':m,'state':'FINITE_SYNTHETIC_CANDIDATE' if candidate else 'NOT_ACCEPTED',
            'failed_size_profiles':failures,'preselected_power_profile':signal['profile'],'power_at_shift_point5':signal['power'],
            'power_requirement_passed':power_ok,'market_validated':False,'actual_order_allowed':False,
            'old_market_results_reclassified':False})
    return reports


def report(lane=LANE,out=None):
    design=verify(lane);out=Path(out) if out is not None else lane
    if (out/'results.json').exists():raise ValueError('existing result retained; choose a new --out only for explicit reproduction')
    out.mkdir(parents=True,exist_ok=True);days=np.arange(N);statistics={};profiles=design['calibration_profiles']
    for i,p in enumerate(profiles):
        values={b:[] for b in BLOCKS}
        for rep in range(design['calibration_paths']):
            x=generate(p,design['calibration_seed']+10000*i+rep)
            for b in BLOCKS:
                s=obm(x,days,block=b);values[b].append(None if s['t'] is None else max(abs(v) for v in s['t']))
        for b in BLOCKS:statistics[p['id']+'|'+str(b)]=values[b]
    try:
        if any(v is None for a in statistics.values() for v in a):raise ValueError('degenerate calibration path retained')
        calibration={**calibrate(statistics,[p['id'] for p in profiles],paths=design['calibration_paths']),'state':'CALIBRATED'}
    except ValueError as e:calibration={'state':'INCONCLUSIVE','reason':str(e),'cutoffs':{},'market_validated':False}
    new(out/'calibration_max_t.json.gz',gzip.compress(encode(statistics),mtime=0))
    new(out/'calibration.json',encode(calibration))
    observations=[];cells=[]
    for i,p in enumerate(profiles+design['stress_profiles']):
        shifts=design['effect_shifts'] if p['kind']=='stationary' else [0.]
        counts={(m,d):[] for m in METHODS for d in shifts}
        for rep in range(design['validation_paths']):
            seed=design['validation_seed']+10000*i+rep;x=generate(p,seed)
            intervals=base_intervals(x,calibration,design['bootstrap_seed']+10000*i+rep)
            observations.append({'profile':p['id'],'replication':rep,'seed':seed,'mean':x.mean(axis=0).tolist(),
                'intervals':intervals})
            for m in METHODS:
                for delta in shifts:
                    if delta==0 or rep<design['power_paths']:counts[(m,delta)].append(flags(intervals[m],delta))
        for (m,d),rows in counts.items():
            expected=design['validation_paths'] if d==0 else design['power_paths']
            cells.append(summarize_cell(p,m,d,rows,expected))
    raw=b''.join(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n' for r in observations)
    new(out/'observations.jsonl.gz',gzip.compress(raw,mtime=0));procedures=assess(cells,[p['id'] for p in profiles+design['stress_profiles']])
    output={'registry_id':'R321','scope':'Null-only finite dependent-inference calibration and independent held-out size/power checks.',
        'calibration':calibration,'procedures':procedures,'cells':cells,'design_sha256':sha(lane/'design.json'),
        'code_identity_sha256':sha(lane/'code_inputs.json'),'source_identity_sha256':sha(lane/'sources.json'),
        'calibration_cells':16,'heldout_cells':len(cells),'registered_diagnostic_trials':16+len(cells),
        'unique_calibration_paths':len(profiles)*design['calibration_paths'],'unique_heldout_paths':len(observations),
        'power_paths_share_noise_with_first_null_replications':True,'no_market_outcomes_read':True,
        'source_only_lighter_bridge':'UNVERIFIED; raw Funding.value is not normalized settled cash.',
        'strategy_trials':0,'new_market_requests':0,'new_prospective_paper_days':0,'activation_allowed':False,
        'net_return':None,'cost_sensitivity':[{'multiple':k,'net_return':None,'scope':'Statistical null experiment; no fee-free profit implied. New market use needs separately frozen1x/2x/3x labels.'} for k in (1,2,3)],
        'observations_sha256':sha(out/'observations.jsonl.gz'),'calibration_statistics_sha256':sha(out/'calibration_max_t.json.gz'),
        'all_old_market_conclusions_unchanged':True,'historical_allowance_unchanged':{'requests_spent':7757,'reported_mib_spent':'229.85'}}
    if len(cells)!=136:raise ValueError('registered finite diagnostic-cell scope changed')
    verify(lane);new(out/'results.json',encode(output));return out/'results.json'


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path)
    print(report(out=p.parse_args().out))
