"""R328 exact-ratio compatibility driver; frozen R327 failure/raw remain intact."""
import argparse
from decimal import Decimal as D
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lab import prereg
from lab.executable_quotes import Receipt
from lab.dated_carry import rules,entry_plan,projected_result as parent_projection
from scripts.run_dated_carry import (sha,save,encode,plain,model_account,committed,
                                    verify as parent_verify)
LANE=ROOT/'experiments/dated_carry_v2'
SOURCE_LANE=ROOT/'experiments/dated_carry_v1'


def projected_result(plan,**kwargs):
    # Ratio literals are an exact arithmetic protocol, not decimal API fields.
    ratio=kwargs.get('exit_ratio')
    if ratio is not None:
        if type(ratio) not in (str,int,F):raise ValueError('exact ratio literal required')
        kwargs['exit_ratio']=F(ratio)
    return parent_projection(plan,**kwargs)


def verify(lane=LANE,*,data=False):
    prereg.verify(lane/'PREREG.md');spec=(lane/'PREREG.md').read_text()
    for name in ('code_inputs.json','inputs.json','fixtures.json','contract.json','sources.json'):
        if sha(lane/name) not in spec:raise ValueError('unbound R328 input:'+name)
    code=json.loads((lane/'code_inputs.json').read_text())
    if code['python_version']!=list(sys.version_info[:3]):raise ValueError('runtime drift')
    for manifest in (code,json.loads((lane/'inputs.json').read_text())):
        for name,digest in manifest['sha256'].items():
            if sha(ROOT/name)!=digest:raise ValueError('frozen R328 input drift:'+name)
    for name in ('PREREG.md','PREREG.sha256','code_inputs.json'):committed(lane/name)
    ref=json.loads((lane/'fixtures.json').read_text())
    if ref['path']!=str((SOURCE_LANE/'fixtures.json').relative_to(ROOT)) or ref['sha256']!=sha(SOURCE_LANE/'fixtures.json'):
        raise ValueError('finite protocol changed')
    return parent_verify(SOURCE_LANE,data=True)


def report(lane=LANE,out=None):
    fixtures=verify(lane,data=True);out=Path(out) if out else lane
    if (out/'results.json').exists() or (out/'model_journals').exists():raise ValueError('preserve previous outcomes; fresh --out required')
    out.mkdir(parents=True,exist_ok=True)
    capture=json.loads((SOURCE_LANE/'evidence/capture.json').read_text());raws={r['name']:r for r in capture['records']}
    def raw(name):
        r=raws.get(name)
        if r is None or r['http_status']!=200 or not r['complete']:raise ValueError(name+':missing_or_failed_source')
        p=json.loads(gzip.decompress((SOURCE_LANE/'evidence'/r['body']).read_bytes()),parse_float=D)
        return p,Receipt(**{k:r[k] for k in Receipt.__dataclass_fields__})
    rows=[];computed=0;model_count=0
    for coin,instrument in fixtures['instruments'].items():
        for profile in fixtures['depth_profiles']:
            row={'coin':coin,'instrument':instrument,'profile':profile,'input_error':None,'plan':None,'controls':[]}
            try:
                meta,_=raw(coin+'_instrument');d=rules(meta,instrument,coin,fixtures['expiry_ns'],raws[coin+'_instrument']['body_sha256'])
                sm,_=raw('spot_rules');sb,sr=raw(coin+'_spot');fb,fr=raw(coin+'_dated')
                plan=entry_plan(sb,sm,sr,fb,d,fr,face_target=fixtures['target_USD_face'],profile=profile,
                                future_entry_rate=fixtures['standard_future_taker_rate'])
                row['plan']=plan
            except (ValueError,TypeError,KeyError,IndexError,ArithmeticError) as exc:
                row['input_error']=type(exc).__name__+':'+str(exc)[:300]
            for fees in fixtures['fee_controls']:
                for k in fixtures['cost_multiples']:
                    cell={'fee_control':fees,'cost_multiple':k,'primary_future_result':None,'terminal_worlds':[],'models':[]}
                    if row['input_error'] is None:
                        cell['primary_future_result']=projected_result(plan,cost_multiple=k,fee_control=fees,
                            delivery_rate=fixtures['standard_delivery_rate'])
                    for xscale in fixtures['delivery_price_scales']:
                        model=None
                        for ratio in fixtures['exit_conversion_ratios']:
                            world={'delivery_price_scale':xscale,'exit_USDT_per_delivery_USD_ratio':ratio,
                                   'conditional':None,'uncomputed_reason':row['input_error']}
                            if row['input_error'] is None:
                                x=plan['future_mid_usd']*F(xscale)
                                result=projected_result(plan,cost_multiple=k,fee_control=fees,
                                    delivery_rate=fixtures['standard_delivery_rate'],delivery_price=x,exit_ratio=ratio)
                                world['conditional']=result;computed+=1
                                if model is None:
                                    name=coin+'-'+profile+'-'+fees+'-'+str(k)+'-x'+str(xscale).replace('/','_')
                                    model=model_account(plan,result,d.contract,x,name,out);model_count+=1
                            cell['terminal_worlds'].append(world)
                        if model is not None:cell['models'].append(model)
                    row['controls'].append(cell)
            rows.append(row)
    save(out/'results.json',plain({'registry_id':'R328','parent_raw_registry_id':'R327','new_market_requests':0,'verdict':'PARTIAL','rows':rows,'capture':capture,
         'entry_plan_slots':4,'fee_cost_cells':24,'terminal_scenario_slots':216,'computed_scenarios':computed,
         'uncomputed_scenarios':216-computed,'constructed_inverse_models':model_count,
         'predictive_strategy_trials':0,'new_prospective_strategy_days':0,'actual_executable_admissions':0,
         'market_expected_net':None,'program_trials_entering':fixtures['program_trials_entering'],
         'source_reciprocal_payoff_and_coin_fee_serialization_verified':False,
         'cost_stress':'same face/base inventory; 1x/2x/3x ENTRY crossing and all modeled commissions at fixed conditional exit ratio',
         'exit_cost_limitation':'future executable exit/TWAP ratio exogenous scenarios, not a full exit impact/latency/counterparty model',
         'code_inputs_sha256':sha(lane/'code_inputs.json'),'data_inputs_sha256':sha(SOURCE_LANE/'data_inputs.json')}))
    packed={str(p.relative_to(out)):p.read_text() for p in sorted((out/'model_journals').glob('*.jsonl'))}
    with (out/'journals.json.gz').open('xb') as h:h.write(gzip.compress(encode(packed),mtime=0))
    verify(lane,data=True)
    print('Wrote finite conditional diagnosis; actual net and expected return remain unknown.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path)
    report(out=p.parse_args().out)
