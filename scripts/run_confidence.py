"""R331 four committed stages: train, calibrate, select, evaluate.

Retained OHLC pages only; no network, new acquisition, tuning on validation,
strategy activation or permanent execution. Use a fresh output for every stage.
"""
import argparse
from collections import Counter
import copy
import gzip
import hashlib
import json
from pathlib import Path
import pickle
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from lab import prereg
from lab.level_probability import DAY,HOUR,CLASSES,market,signal,outcome,fit as prior_fit,replay
from lab.level_features import FEATURES,retained_ohlc,attach,vector
from lab.confidence_models import BASES,MAPS,CANDIDATES,fit_bases,predict_bases,fit_maps,transform,losses,select,export_bases
from scripts.run_level_probability import encode,save,ms,statistics

LANE=ROOT/'experiments/confidence_v1'
PROB_MODELS=CANDIDATES+('R330_reference',)
CONTROLS=('always_break','always_rebound','long_control','cash')


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())


def require_committed(path):
    p=Path(path);relative=p.resolve().relative_to(ROOT).as_posix()
    actual=subprocess.run(['git','show','HEAD:'+relative],cwd=ROOT,capture_output=True,check=True).stdout
    if actual!=p.read_bytes():raise ValueError('uncommitted stage input '+relative)


def verify():
    prereg.verify(LANE/'PREREG.md');spec=(LANE/'PREREG.md').read_text()
    for name in ('config.json','code_inputs.json','data_inputs.json','sources.json'):
        if sha(LANE/name) not in spec:raise ValueError('unbound confidence input '+name)
        require_committed(LANE/name)
    require_committed(LANE/'PREREG.md');require_committed(LANE/'PREREG.sha256')
    from importlib.metadata import version
    code=load(LANE/'code_inputs.json')
    if code['python_version']!=list(sys.version_info[:3]):raise ValueError('frozen Python drift')
    for name,v in code['packages'].items():
        if version(name)!=v:raise ValueError('numeric/model package drift '+name)
    for manifest in (code,load(LANE/'data_inputs.json')):
        for name,digest in manifest['sha256'].items():
            if sha(ROOT/name)!=digest:raise ValueError('frozen input drift '+name)
    return load(LANE/'config.json')


def seal(out):
    files={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()}
    save(out/'manifest.json',encode(dict(sha256=files)))


def require_stage(path):
    path=Path(path);require_committed(path/'manifest.json');manifest=load(path/'manifest.json')
    for name,digest in manifest['sha256'].items():
        if '/' in name or name.startswith('.'):raise ValueError('bounded stage filename required')
        require_committed(path/name)
        if sha(path/name)!=digest:raise ValueError('sealed model/stage artifact drift')
    return manifest


def markets(config,cutoff):
    manifest=load(LANE/'data_inputs.json');out={}
    for symbol in config['symbols']:
        base=ROOT/'data/equations_v2/mexc'
        p=pd.read_parquet(base/'prices'/f'{symbol}_USDT.parquet',filters=[('t','<',cutoff-HOUR)])
        f=pd.read_parquet(base/'funding'/f'{symbol}_USDT.parquet',filters=[('t','<',cutoff)])
        m=market(p,f,ms(config['source_start']),cutoff)
        bars=retained_ohlc(ROOT,manifest['raw_records'],symbol,p,cutoff)
        out[symbol]=attach(m,bars)
    return out


def observations(config,start,end):
    m=markets(config,end);rows=[]
    for d in range(start,end,DAY):
        for symbol in config['symbols']:
            s=signal(m[symbol],d);x=vector(m[symbol],m['BTC'],s)
            rows.append(dict(symbol=symbol,signal=s,outcome=outcome(m[symbol],s),feature=x,
                feature_reason='missing_causal_ohlc_or_btc' if s['state']=='event' and x is None else None))
    return rows


def packed(rows):return gzip.compress(encode(rows),mtime=0)


def matrix(rows,*,financial=False):
    indices=[i for i,r in enumerate(rows) if r['feature'] is not None and r['outcome'] and r['outcome']['label'] is not None
             and (not financial or r['outcome']['financial_known'])]
    return indices,np.asarray([rows[i]['feature'] for i in indices],float).reshape(-1,len(FEATURES)),np.asarray([CLASSES.index(rows[i]['outcome']['label']) for i in indices],int)


def training_bundle():
    require_stage(LANE/'training');meta=load(LANE/'training/metadata.json')
    if meta['config_sha256']!=sha(LANE/'config.json') or meta['data_sha256']!=sha(LANE/'data_inputs.json'):raise ValueError('training/spec identity mismatch')
    # Only our own committed hash-verified artifact is deserialized. No remote,
    # uploaded or unsigned pickle is accepted.
    bundle=pickle.loads((LANE/'training/base_models.pkl').read_bytes())
    return bundle,meta


def train(out,config):
    rows=observations(config,ms(config['train_start']),ms(config['train_end']))
    indices,x,y=matrix(rows,financial=True);bundle=fit_bases(x,y)
    prior=prior_fit([rows[i] for i in indices])
    save(out/'base_models.pkl',pickle.dumps(bundle,protocol=5));save(out/'base_export.json',encode(export_bases(bundle)))
    meta=dict(registry_id='R331',config_sha256=sha(LANE/'config.json'),data_sha256=sha(LANE/'data_inputs.json'),
        features=list(FEATURES),n=len(y),classes=bundle['classes'],prior=prior['probability'],class_payoffs=prior['class_payoff_means'],
        source_window=[config['train_start'],config['train_end']],calibration_validation_used=False,actual_order_allowed=False)
    save(out/'metadata.json',encode(meta));save(out/'observations.json.gz',packed(rows));seal(out)
    return dict(stage='TRAINING_ONLY',n=len(y),classes=bundle['classes'])


def calibrate(out,config):
    bundle,meta=training_bundle()
    rows=observations(config,ms(config['calibration_start']),ms(config['calibration_end']))
    indices,x,y=matrix(rows);raw=predict_bases(bundle,x)
    maps={base:fit_maps(raw[base],y) for base in BASES}
    artifact=dict(registry_id='R331',parent_manifest_sha256=sha(LANE/'training/manifest.json'),maps=maps,
        n=len(y),classes=np.bincount(y,minlength=3).tolist(),source_window=[config['calibration_start'],config['calibration_end']],
        selection_validation_used=False,calibrated_market_confidence=False)
    save(out/'calibrators.json',encode(artifact));save(out/'observations.json.gz',packed(rows));seal(out)
    return dict(stage='CALIBRATION_ONLY',n=len(y),states={k:v['state'] for k,v in maps.items()})


def calibration_bundle():
    bundle,meta=training_bundle();require_stage(LANE/'calibration');cal=load(LANE/'calibration/calibrators.json')
    if cal['parent_manifest_sha256']!=sha(LANE/'training/manifest.json'):raise ValueError('calibrator bound to different base models')
    return bundle,meta,cal


def predictions(rows,bundle,meta,cal):
    # Full daily opportunities are retained; absent features/targets do not
    # silently change the event universe or become invented forecasts.
    eligible=[i for i,r in enumerate(rows) if r['signal']['state']=='event']
    feature_indices=[i for i in eligible if rows[i]['feature'] is not None]
    x=np.asarray([rows[i]['feature'] for i in feature_indices],float).reshape(-1,len(FEATURES))
    raw=predict_bases(bundle,x);result={name:[None]*len(rows) for name in PROB_MODELS};ood={}
    for j,i in enumerate(feature_indices):
        z=(x[j]-bundle['mean'])/bundle['scale'];ood[i]=bool((np.abs(z)>5).any())
    for base in BASES:
        for method in MAPS:
            transformed=transform(raw[base],cal['maps'][base].get(method))
            if transformed is not None:
                for j,i in enumerate(feature_indices):result[base+'_'+method][i]=transformed[j].tolist()
    old=load(ROOT/'experiments/level_probability_v1/model.json')
    for i in eligible:
        result['frequency'][i]=meta['prior']
        result['R330_reference'][i]=old['cells'][rows[i]['signal']['cell']]['probability']
    return result,ood


def choose(out,config):
    bundle,meta,cal=calibration_bundle()
    rows=observations(config,ms(config['selection_start']),ms(config['selection_end']))
    p,ood=predictions(rows,bundle,meta,cal);indices,x,y=matrix(rows)
    available={name:np.asarray([p[name][i] for i in indices],float)
               for name in CANDIDATES if all(p[name][i] is not None for i in indices)}
    try:selection=select(available,y);selection['state']='SELECTED'
    except ValueError as e:selection=dict(state='INCONCLUSIVE',winner=None,reason=str(e),ranking=[])
    selection.update(registry_id='R331',parent_manifest_sha256=sha(LANE/'calibration/manifest.json'),
        source_window=[config['selection_start'],config['selection_end']],n=len(y),validation_used=False,
        unavailable_candidates=[name for name in CANDIDATES if name not in available],actual_order_allowed=False)
    save(out/'selection.json',encode(selection));save(out/'observations.json.gz',packed(rows));seal(out)
    return dict(stage='SELECTION_ONLY',winner=selection['winner'],state=selection['state'],n=len(y))


def scores(rows,p):
    result={};indices=[i for i,r in enumerate(rows) if r['outcome'] and r['outcome']['label'] is not None]
    for name in PROB_MODELS:
        keep=[i for i in indices if p[name][i] is not None]
        probs=np.asarray([p[name][i] for i in keep],float).reshape(-1,3)
        y=np.asarray([CLASSES.index(rows[i]['outcome']['label']) for i in keep],int)
        if not keep:result[name]=dict(n=0,state='UNAVAILABLE');continue
        l=losses(probs,y);baseline=losses(np.asarray([p['frequency'][i] for i in keep]),y)
        bins=[]
        for k,c in enumerate(CLASSES):
            for b in range(5):
                ix=[j for j in range(len(keep)) if min(4,int(probs[j,k]*5))==b]
                days={rows[keep[j]]['signal']['decision']//DAY for j in ix}
                bins.append(dict(label=c,bin=b,n=len(ix),days=len(days),blocks14=len({d//14 for d in days}),
                    predicted=float(probs[ix,k].mean()) if ix else None,observed=float((y[ix]==k).mean()) if ix else None,
                    calibrated_interval=None))
        # Fixed calendar shifts preserve cross-asset targets; descriptive only.
        target={(r['signal']['decision']//DAY,r['symbol']):r['outcome']['label'] for r in rows if r['outcome'] and r['outcome']['label'] is not None}
        lo=min(r['signal']['decision']//DAY for r in rows);n=(max(r['signal']['decision']//DAY for r in rows)-lo+1);shifted=[]
        for shift in range(14,n,14):
            diff=[]
            for j,i in enumerate(keep):
                r=rows[i];key=(lo+(r['signal']['decision']//DAY-lo+shift)%n,r['symbol'])
                if key not in target:continue
                k=CLASSES.index(target[key]);diff.append(-np.log(probs[j,k])+np.log(p['frequency'][i][k]))
            shifted.append(dict(days=shift,n=len(diff),mean_logloss_difference=float(np.mean(diff)) if diff else None))
        result[name]=dict(n=len(keep),state='SCORED',log_loss=float(l['log_loss'].mean()),brier=float(l['brier'].mean()),
            paired_logloss_difference=float((l['log_loss']-baseline['log_loss']).mean()),
            paired_brier_difference=float((l['brier']-baseline['brier']).mean()),reliability=bins,
            joint14day_shifts=shifted,calibrated_uncertainty=None,valid_pvalue=None)
    return result


def economic(rows,p,ood,meta,start,end):
    """Reuse the frozen R330 account unchanged; adapters carry finite predictions.

    Eight adapter calls exercise repeated controls; compare/deduplicate exact
    cash/ticket/day states into13semantic policies, retaining equality receipts.
    This changes neither R330's financial math nor its historical journals.
    """
    books={};duplicates=0;old=load(ROOT/'experiments/level_probability_v1/model.json')
    for name in PROB_MODELS:
        use_old=name=='R330_reference';gain=old['class_payoff_means'] if use_old else meta['class_payoffs']
        prior=old['probability'] if use_old else meta['prior'];cells={};adapted=copy.deepcopy(rows)
        for i,r in enumerate(adapted):
            if r['signal']['state']!='event':continue
            key=r['symbol']+':'+str(r['signal']['decision']);r['signal']['cell']=key
            probability=p[name][i]
            # Score all finite forecasts, but a learned model cannot open a
            # research position beyond5training-SD on any feature. Prior and
            # original references require no new feature/extrapolation gate.
            if name not in ('frequency','R330_reference') and ood.get(i,False):probability=None
            cells[key]=dict(probability=probability)
        adapter=dict(probability=prior,class_payoff_means=gain,cells=cells)
        for a in replay(adapted,adapter,start,end):
            source_policy=a['policy']
            policy=(name if source_policy=='conditional' else ('R330_frequency' if use_old else 'frequency') if source_policy=='climatology' else source_policy)
            a['engine_policy']=source_policy;a['policy']=policy;a['protocol']='R331;frozenR330cashengine'
            key=policy,a['cost_multiple']
            if key in books:
                fields=('shared_cash','price','funding','cost','days','tickets','pending','open_positions','complete')
                if any(a[k]!=books[key][k] for k in fields):raise ValueError('supposed common control differs; retain failure, do not discard a distinct variant')
                duplicates+=1
            else:books[key]=a
    return sorted(books.values(),key=lambda a:(a['policy'],a['cost_multiple'])),duplicates


def null_diagnostic(paths=100):
    """Finite synthetic no-information procedure diagnostic, not a market pvalue.

    Four observations share every day's target; target has .6persistence.
    Ten AR(.7) features have independent innovations. No failed path is redrawn.
    """
    if type(paths) is not int or not 1<=paths<=100:raise ValueError('finite1..100 synthetic path budget required')
    rng=np.random.default_rng(33101);records=[]
    for rep in range(paths):
        days=105;latent=np.zeros((days,10));noise=rng.normal(size=latent.shape)
        for t in range(1,days):latent[t]=.7*latent[t-1]+noise[t]
        x=np.repeat(latent,4,axis=0)+rng.normal(scale=.2,size=(days*4,10))
        states=[];last=int(rng.choice(3,p=[.15,.25,.6]))
        for t in range(days):
            if rng.random()>.6:last=int(rng.choice(3,p=[.15,.25,.6]))
            states.extend([last]*4)
        y=np.asarray(states,int)
        try:
            base=fit_bases(x[:120],y[:120]);prior=(np.bincount(y[:120],minlength=3)+1)/123
            c=predict_bases(base,x[120:180]);maps={b:fit_maps(c[b],y[120:180]) for b in BASES}
            def predict(block):
                raw=predict_bases(base,block);out={'frequency':np.tile(prior,(len(block),1))}
                for b in BASES:
                    for m in MAPS:out[b+'_'+m]=transform(raw[b],maps[b].get(m))
                return out
            s=predict(x[180:240]);choice=select(s,y[180:240]);test=predict(x[240:]);selected=test[choice['winner']]
            l=losses(selected,y[240:]);control=losses(test['frequency'],y[240:])
            records.append(dict(path=rep,state='SCORED',winner=choice['winner'],
                held_logloss_difference=float((l['log_loss']-control['log_loss']).mean()),held_brier_difference=float((l['brier']-control['brier']).mean())))
        except (ValueError,RuntimeError) as e:records.append(dict(path=rep,state='UNAVAILABLE',reason=str(e)))
    return dict(paths=paths,records=records,seed=33101,scope='Synthetic dependent/no-information selection diagnostic; failures retained, not a calibrated market inference procedure',market_validated=False,valid_pvalue=None)


def evaluate(out,config):
    bundle,meta,cal=calibration_bundle();require_stage(LANE/'selection');selection=load(LANE/'selection/selection.json')
    if selection['parent_manifest_sha256']!=sha(LANE/'calibration/manifest.json'):raise ValueError('selection bound to wrong calibration')
    allrows={};allbooks={};allprobs={};report={};duplicates={}
    for name in ('selection','validation'):
        start,end=ms(config[name+'_start']),ms(config[name+'_end']);rows=observations(config,start,end)
        p,ood=predictions(rows,bundle,meta,cal);books,repeated=economic(rows,p,ood,meta,start,end)
        report[name]=dict(opportunities=len(rows),qualified=sum(r['signal']['state']=='event' for r in rows),
            feature_missing=sum(r['signal']['state']=='event' and r['feature'] is None for r in rows),ood_events=sum(ood.values()),
            scores=scores(rows,p),accounts=[statistics(a) for a in books])
        allrows[name]=rows;allbooks[name]=books;allprobs[name]=dict(predictions=p,ood={str(k):v for k,v in ood.items()});duplicates[name]=repeated
    winner=selection['winner'];v=report['validation'];candidate=next((a for a in v['accounts'] if a['policy']==winner and a['cost_multiple']==2),None)
    if candidate is None or not candidate['complete']:screen='INCONCLUSIVE'
    elif candidate['states'].get('closed',0)==0:screen='NULL_INACTIVE'
    elif float(candidate['conditional_net'])<=0:screen='NULL_COST_PROXY'
    elif v['scores'][winner]['paired_logloss_difference']>=0:screen='NULL_PROBABILITY_GAIN'
    else:screen='PARTIAL_PROXY_ONLY'
    result=dict(registry_id='R331',method_id='M412',verdict='PARTIAL',selected_model=winner,policy_screen=screen,
        windows=report,selection_ranking=selection['ranking'],registered_policy_variants=14,
        distinct_account_policies=13,unique_account_cells=78,deduplicated_verified_control_repetitions=duplicates,
        model_source='Two fixed base learners x raw/temperature/ouridentityDirichlet; frequency and oldreferences; unchangedfourcontrols; frozenselector is14thvariant',
        model_manifest_sha256=sha(LANE/'training/manifest.json'),calibration_manifest_sha256=sha(LANE/'calibration/manifest.json'),
        selection_manifest_sha256=sha(LANE/'selection/manifest.json'),actual_executable_net=None,
        calibrated_uncertainty=None,new_market_requests=0,new_prospective_days=0,actual_order_allowed=False,
        history_already_seen=True,limitations=config['limitations'])
    save(out/'results.json',encode(result));save(out/'observations.json.gz',packed(allrows));save(out/'predictions.json.gz',packed(allprobs));save(out/'accounts.json.gz',packed(allbooks))
    save(out/'null_diagnostic.json.gz',packed(null_diagnostic(config['null_paths'])));seal(out)
    return dict(stage='LATER_PERIOD_DIAGNOSTIC',selected_model=winner,policy_screen=screen,actual_executable_net=None,new_prospective_days=0)


def report(out=None,stage='evaluate'):
    config=verify();out=Path(out or LANE/'results')
    if out.exists():raise FileExistsError('fresh output required; no overwrite/refetch')
    out.mkdir(parents=True)
    try:r={'train':train,'calibrate':calibrate,'select':choose,'evaluate':evaluate}[stage](out,config)
    except Exception as e:
        save(out/'failure.json',encode(dict(stage=stage,state='FAILED',error=type(e).__name__+':'+str(e),no_reclassification=True)))
        raise
    verify();return r


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--stage',choices=('train','calibrate','select','evaluate'),default='evaluate');p.add_argument('--out',type=Path)
    a=p.parse_args();print(json.dumps(report(a.out,a.stage),sort_keys=True))
