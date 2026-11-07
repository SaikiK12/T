"""R326 same-data mechanical input repair; frozen R325 failures remain untouched."""
import argparse
from dataclasses import asdict
from decimal import Decimal as D
import gzip
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lab import prereg
from lab.executable_quotes import Receipt
from lab.spot_quote_costs import spot_book,illustrative_quantity,conditional_costs
from lab.spot_input_bridge import spot_rules,mexc_book
from scripts.run_spot_costs import plain,cost_account,encode,save,sha,verify as parent_verify
LANE=ROOT/'experiments/spot_perp_costs_v2'
SOURCE_LANE=ROOT/'experiments/spot_perp_costs_v1'


def verify(lane=LANE,*,data=False):
    prereg.verify(lane/'PREREG.md');spec=(lane/'PREREG.md').read_text()
    for name in ('code_inputs.json','inputs.json','fixtures.json','contract.json','sources.json'):
        if sha(lane/name) not in spec:raise ValueError('unbound R326 input')
    code=json.loads((lane/'code_inputs.json').read_text())
    if code['python_version']!=list(sys.version_info[:3]):raise ValueError('runtime drift')
    for manifest in (code,json.loads((lane/'inputs.json').read_text())):
        for name,digest in manifest['sha256'].items():
            if sha(ROOT/name)!=digest:raise ValueError('frozen R326 source/input drift:'+name)
    import subprocess
    for name in ('PREREG.md','PREREG.sha256','code_inputs.json'):
        p=lane/name
        if subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)!=p.read_bytes():
            raise ValueError('R326 freeze must be committed before outcomes')
    ref=json.loads((lane/'fixtures.json').read_text())
    if ref['path']!=str((SOURCE_LANE/'fixtures.json').relative_to(ROOT)) or ref['sha256']!=sha(SOURCE_LANE/'fixtures.json'):
        raise ValueError('finite economic controls changed')
    return parent_verify(SOURCE_LANE,data=True)


def report(lane=LANE,out=None):
    f=verify(lane,data=True);out=Path(out) if out else lane
    if (out/'results.json').exists() or (out/'model_journals').exists():raise ValueError('existing result preserved; fresh --out required')
    out.mkdir(parents=True,exist_ok=True)
    capture=json.loads((SOURCE_LANE/'evidence/capture.json').read_text());records={r['name']:r for r in capture['records']}
    def raw(name):
        r=records.get(name)
        if r is None or r['http_status']!=200 or not r['complete']:raise ValueError(name+':missing/failed bounded response')
        payload=json.loads(gzip.decompress((SOURCE_LANE/'evidence'/r['body']).read_bytes()),parse_float=D)
        receipt=Receipt(**{k:r[k] for k in Receipt.__dataclass_fields__})
        return payload,receipt
    rows=[]
    for sample in range(f['samples_per_symbol']):
        for symbol in f['symbols']:
            name=str(sample)+'_'+symbol;row={'sample':sample,'symbol':symbol,'inputs_error':None,'views':[]}
            try:
                source,_=raw('spot_rules');rules=spot_rules(symbol+'USDT',source)
                source,_=raw(symbol+'_perp_rules')
                if source.get('success') is not True or not isinstance(source.get('data'),dict):raise ValueError('perp metadata failed identity')
                m=source['data'];sb,sr=raw(name+'_spot');pb,pr=raw(name+'_perp')
                s=spot_book(symbol+'USDT',sb,sr);p=mexc_book(symbol+'_USDT',pb,m,pr)
                q,step=illustrative_quantity(rules,m,max(s.mid,p.mid),D(f['reference_mid_leg_budget']))
                row.update(spot_rules=asdict(rules),perp_rules={k:m.get(k) for k in f['perp_fields']},
                           illustrative_base_quantity=str(q),illustrative_grid_step=str(step),
                           observed_spot_mid=str(s.mid),observed_perp_mid=str(p.mid))
            except (ValueError,TypeError,KeyError,ArithmeticError,AttributeError) as exc:
                row['inputs_error']=type(exc).__name__+':'+str(exc)[:256]
            for profile in f['depth_profiles']:
                for fees in f['fee_controls']:
                    cellname=name+'_'+profile+'_'+fees
                    if row['inputs_error']:
                        cell={'profile':profile,'fee_control':fees,'costs':None,'conditional_calculation_reasons':[row['inputs_error']],
                              'executable_pair_eligible':False,'net_market_return':None}
                    else:
                        try:cell=conditional_costs(s,p,rules,m,q,profile=profile,fee_control=fees)
                        except (ValueError,TypeError,KeyError,ArithmeticError) as exc:
                            cell={'profile':profile,'fee_control':fees,'costs':None,'conditional_calculation_reasons':[str(exc)[:256]],
                                  'executable_pair_eligible':False,'net_market_return':None}
                    cell['cost_account']=cost_account(cell,symbol,cellname,out);row['views'].append(cell)
            rows.append(plain(row))
    payload={'rows':rows}
    with (out/'observations.json.gz').open('xb') as h:h.write(gzip.compress(encode(payload),mtime=0))
    paths=list((out/'model_journals').iterdir()) if (out/'model_journals').exists() else []
    packed={str(p.relative_to(out)):p.read_text() for p in sorted(paths)}
    with (out/'journals.json.gz').open('xb') as h:h.write(gzip.compress(encode(packed),mtime=0))
    views=[v for r in rows for v in r['views']];computed=sum(len(v['costs'] or []) for v in views)
    summary={'registry_id':'R326','parent_raw_registry_id':'R325','new_market_requests':0,'verdict':'PARTIAL','fixed_pair_slots':len(rows),'fixed_cost_control_cells':len(views),
             'fixed_cost_tier_slots':3*len(views),'computed_conditional_cost_tiers':computed,
             'uncomputed_tier_slots':3*len(views)-computed,'model_journals':len(paths),'rows':rows,'capture':capture,
             'data_inputs_sha256':sha(SOURCE_LANE/'data_inputs.json'),'code_inputs_sha256':sha(lane/'code_inputs.json'),
             'outputs_sha256':{n:sha(out/n) for n in ('observations.json.gz','journals.json.gz')},
             'cost_stress':'1x/2x/3x of fixed observed crossing plus explicit assumed quote commissions; same q, no tier reselection',
             'execution_admitted_pairs':0,'market_net_return':None,'new_prospective_strategy_days':0,
             'predictive_strategy_trials':0,'actual_order_allowed':False,'cash_control_four_fill_component':'0',
             'actual_funding_cash':None,'spot_increment_contract_verified':False,'source_clock_contract_verified':False}
    verify(lane,data=True);save(out/'results.json',plain(summary));return out/'results.json'

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path)
    print(report(out=p.parse_args().out))
