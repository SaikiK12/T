"""R325 fixed source-aware spot/perp cost controls; no market PnL inference."""
import argparse
from dataclasses import asdict
from decimal import Decimal as D
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lab.executable_quotes import Receipt,mexc_book
from lab.paper_account import PaperAccount,PaperEvent
from lab.spot_cash import SpotCashAccount,SpotEvent
from lab.spot_pair import snapshot
from lab.spot_quote_costs import spot_rules,spot_book,illustrative_quantity,conditional_costs
from scripts.run_spot_perp_account import verify as shared_verify,encode,save,sha,clock,ANCHOR

LANE=ROOT/'experiments/spot_perp_costs_v1'


def plain(x):
    if isinstance(x,D):return str(x)
    if isinstance(x,dict):return {k:plain(v) for k,v in x.items()}
    if isinstance(x,(tuple,list)):return [plain(v) for v in x]
    return x


def verify(lane=LANE,*,data=False):return shared_verify(lane,data=data)


def cost_account(cell,symbol,name,out):
    if cell['costs'] is None:return None
    folder=out/'model_journals';folder.mkdir(exist_ok=True)
    sp,pp=folder/(name+'-spot.jsonl'),folder/(name+'-perp.jsonl')
    s=SpotCashAccount('mexc-spot-cost-model','USDT','5000',{symbol+'USDT':symbol},ANCHOR,journal_path=sp)
    p=PaperAccount({('mexc-perp-cost-model','USDT'):'5000'},ANCHOR,journal_path=pp)
    q=D(cell['illustrative_base_quantity']);buy,sell,pbuy,psell=map(D,cell['hypothetical_fill_cash'])
    sf,pf=map(D,cell['hypothetical_quote_fee_rates'])
    def spot(eid,t,quantity,cash,fee):
        e=SpotEvent(name+eid,'fill',symbol+'USDT',clock(t).utc_ns,clock(t),'invented-quote-fill-model/'+name,
                    quantity=quantity,price=cash/q,fee_amount=fee,fee_asset='USDT')
        if s.post(e,clock(t).mono_ns)['status']!='applied':raise ValueError('conditional spot model rejected')
    def perp(eid,t,**kw):
        e=PaperEvent(name+eid,'funding' if eid=='unknown-funding' else 'fill','mexc-perp-cost-model','USDT',symbol+'_USDT',
                     clock(t).utc_ns,clock(t),'invented-quote-fill-model/'+name,**kw)
        if p.post(e,clock(t).mono_ns)['status']!='applied':raise ValueError('conditional perp model rejected')
    spot('buy',1,q,buy,buy*sf);perp('short',1,quantity=-q,price=psell/q,fee=psell*pf)
    # Explicitly preserve unsupplied actual funding instead of inserting zero.
    perp('unknown-funding',2,amount=None)
    spot('sell',3,-q,sell,sell*sf);perp('cover',3,quantity=q,price=pbuy/q,fee=pbuy*pf)
    view=snapshot(s,p,symbol+'USDT',symbol+'_USDT',clock(4).mono_ns)
    known=s.realized+F(p.price[('mexc-perp-cost-model','USDT')])-F(p.fees[('mexc-perp-cost-model','USDT')])
    known=D(known.numerator)/D(known.denominator)
    expected=-D(cell['costs'][0]['required_gross_quote_to_break_even'])
    if abs(known-expected)>D('1e-8') or view['combined_nav'] is not None:
        raise ValueError('known cost component mismatch or unknown funding became known NAV')
    reopen=snapshot(SpotCashAccount('mexc-spot-cost-model','USDT','5000',{symbol+'USDT':symbol},ANCHOR,journal_path=sp),
                    PaperAccount({('mexc-perp-cost-model','USDT'):'5000'},ANCHOR,journal_path=pp),
                    symbol+'USDT',symbol+'_USDT',clock(4).mono_ns)
    if reopen!=view:raise ValueError('conditional journals do not reopen identically')
    return {'snapshot':view,'known_four_fill_price_fee_component':str(known),'funding_cash':None,
            'modeled_fill_assumption':'same received book, perfect quote/base conventions, no queue/latency or actual trade proof',
            'journal_sha256':{str(x.relative_to(out)):sha(x) for x in (sp,pp)},'reopened_identical':True}


def report(lane=LANE,out=None):
    f=verify(lane,data=True);out=Path(out) if out else lane
    if (out/'results.json').exists() or (out/'model_journals').exists():raise ValueError('existing result preserved; fresh --out required')
    out.mkdir(parents=True,exist_ok=True)
    capture=json.loads((lane/'evidence/capture.json').read_text());records={r['name']:r for r in capture['records']}
    def raw(name):
        r=records.get(name)
        if r is None or r['http_status']!=200 or not r['complete']:raise ValueError(name+':missing/failed bounded response')
        payload=json.loads(gzip.decompress((lane/'evidence'/r['body']).read_bytes()),parse_float=D)
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
    summary={'registry_id':'R325','verdict':'PARTIAL','fixed_pair_slots':len(rows),'fixed_cost_control_cells':len(views),
             'fixed_cost_tier_slots':3*len(views),'computed_conditional_cost_tiers':computed,
             'uncomputed_tier_slots':3*len(views)-computed,'model_journals':len(paths),'rows':rows,'capture':capture,
             'data_inputs_sha256':sha(lane/'data_inputs.json'),'code_inputs_sha256':sha(lane/'code_inputs.json'),
             'outputs_sha256':{n:sha(out/n) for n in ('observations.json.gz','journals.json.gz')},
             'cost_stress':'1x/2x/3x of fixed observed crossing plus explicit assumed quote commissions; same q, no tier reselection',
             'execution_admitted_pairs':0,'market_net_return':None,'new_prospective_strategy_days':0,
             'predictive_strategy_trials':0,'actual_order_allowed':False,'cash_control_four_fill_component':'0',
             'actual_funding_cash':None,'spot_increment_contract_verified':False,'source_clock_contract_verified':False}
    verify(lane,data=True);save(out/'results.json',plain(summary));return out/'results.json'


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path)
    print(report(out=p.parse_args().out))
