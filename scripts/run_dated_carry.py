"""R327 finite current-quote dated carry diagnosis; no executable-profit claim."""
import argparse
from dataclasses import asdict
from datetime import datetime,timezone,timedelta
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lab import prereg
from lab.dated_carry import rules,entry_plan,projected_result
from lab.inverse_cash import InverseCashAccount,InverseEvent
from lab.spot_cash import SpotCashAccount,SpotEvent
from lab.executable_quotes import Receipt
from lab.stream_quotes import FrameClock,NS
from scripts.run_spot_perp_account import encode,save

LANE=ROOT/'experiments/dated_carry_v1'
sha=prereg.sha256_file


def plain(x):
    if isinstance(x,F):return str(x)
    if isinstance(x,D):return str(x)
    if isinstance(x,dict):return {k:plain(v) for k,v in x.items()}
    if isinstance(x,(tuple,list)):return [plain(v) for v in x]
    return x


def exact_decimal(x):
    x=F(x)
    with localcontext() as ctx:
        ctx.prec=250
        out=D(x.numerator)/D(x.denominator)
    if F(out)!=x:raise ValueError('nonterminating decimal cannot enter spot cash adapter')
    return out


def committed(path):
    relative=str(Path(path).relative_to(ROOT))
    if subprocess.check_output(['git','show','HEAD:'+relative],cwd=ROOT)!=Path(path).read_bytes():
        raise ValueError('finite code/input must be committed before outcomes:'+relative)


def verify(lane=LANE,*,data=False):
    digest=prereg.verify(lane/'PREREG.md');spec=(lane/'PREREG.md').read_text()
    for name in ('code_inputs.json','inputs.json','fixtures.json','contract.json','sources.json'):
        if sha(lane/name) not in spec:raise ValueError('unbound finite input:'+name)
    code=json.loads((lane/'code_inputs.json').read_text())
    if code['python_version']!=list(sys.version_info[:3]):raise ValueError('runtime drift')
    for manifest in (code,json.loads((lane/'inputs.json').read_text())):
        for name,expected in manifest['sha256'].items():
            p=ROOT/name
            if p.is_symlink() or sha(p)!=expected:raise ValueError('frozen code/source/input drift:'+name)
    for name in ('PREREG.md','PREREG.sha256','code_inputs.json'):committed(lane/name)
    if data:
        manifest=json.loads((lane/'data_inputs.json').read_text());committed(lane/'data_inputs.json')
        if manifest['prereg_sha256']!=digest or manifest['code_inputs_sha256']!=sha(lane/'code_inputs.json'):
            raise ValueError('capture not tied to frozen contract/code')
        actual={str(p.relative_to(ROOT)) for p in (lane/'evidence').iterdir() if p.is_file()}
        if actual!=set(manifest['sha256']):raise ValueError('raw evidence inventory drift')
        for name,expected in manifest['sha256'].items():
            if sha(ROOT/name)!=expected:raise ValueError('raw evidence drift:'+name)
            committed(ROOT/name)
    return json.loads((lane/'fixtures.json').read_text())


def model_account(plan,projection,contract,delivery_price,name,out):
    """Hypothetical supplied fills/clocks; no future market observation.

    SAME purchased coins are earmarked as collateral. Spot stock is NOT added
    again to the inverse collateral NAV. This is an ownership projection, not
    an actual transfer or an entitlement/withdrawal attestation.
    """
    folder=out/'model_journals';folder.mkdir(exist_ok=True)
    sp=folder/(name+'-spot.jsonl');ip=folder/(name+'-inverse.jsonl')
    anchor=FrameClock(1792972800*NS,100*NS)  # constructed Oct26 00UTC, not source receipt
    market=plan['coin']+'USDT'
    s=SpotCashAccount('mexc-dated-model','USDT','10000',{market:plan['coin']},anchor,journal_path=sp)
    inv=InverseCashAccount(contract,plan['initial_coin'],anchor,journal_path=ip)
    def clock(t):return FrameClock(anchor.utc_ns+t*NS,anchor.mono_ns+t*NS)
    k=projection['cost_multiple'];sf=projection['spot_fee_rate'];fee=projection['entry_fee_coin']
    for i,(price,q) in enumerate(plan['spot_fills']):
        p=plan['spot_mid_usdt']+k*(price-plan['spot_mid_usdt'])
        e=SpotEvent(name+'-spot'+str(i),'fill',market,clock(1).utc_ns,clock(1),
                    'constructed-supplied-quote-fill',quantity=exact_decimal(q),price=exact_decimal(p),
                    fee_amount=exact_decimal(q*p*sf),fee_asset='USDT')
        if s.post(e,clock(1).mono_ns)['status']!='applied':raise ValueError('spot model rejected')
    for i,(p,n) in enumerate(projection['stressed_inverse_fills']):
        ef=F(0) if projection['fee_control']=='zero_charge' else n/p*plan['future_entry_rate']*k
        e=InverseEvent(name+'-short'+str(i),'open',contract.instrument,clock(2).utc_ns,clock(2),
                       'constructed-inverse-fill',p,-n,ef)
        if inv.post(e,clock(2).mono_ns)['status']!='applied':raise ValueError('inverse opening model rejected')
    # One hypothetical non-expiry08UTC realization; retained in coin, not paid twice.
    daily=8*3600
    e=InverseEvent(name+'-daily','daily',contract.instrument,clock(daily).utc_ns,clock(daily),
                   'constructed-daily-reference',plan['future_mid_usd']*F(11,10),fee_coin=F(0))
    if inv.post(e,clock(daily).mono_ns)['status']!='applied':raise ValueError('daily model rejected')
    expiry=(contract.expiry_ns-anchor.utc_ns)//NS
    if expiry*NS+anchor.utc_ns!=contract.expiry_ns or expiry<=daily:raise ValueError('fixed model expiry drift')
    e=InverseEvent(name+'-delivery','delivery',contract.instrument,clock(expiry).utc_ns,clock(expiry),
                   'constructed-delivery-TWAP',delivery_price,
                   fee_coin=plan['face_usd']/delivery_price*projection['delivery_fee_rate'])
    if inv.post(e,clock(expiry).mono_ns)['status']!='applied':raise ValueError('delivery model rejected')
    if s.holdings[market]!=inv.initial or s.cash!=projection['idle_cash_usdt']:
        raise ValueError('ownership or idle cash mismatch')
    end=inv.snapshot()
    if inv.coin!=projection['terminal']['coin_after_delivery'] or inv.face or inv.pending:
        raise ValueError('inverse path versus terminal algebra mismatch')
    reopened=InverseCashAccount(contract,plan['initial_coin'],anchor,journal_path=ip).snapshot()
    reopened_spot=SpotCashAccount('mexc-dated-model','USDT','10000',{market:plan['coin']},anchor,journal_path=sp)
    if reopened!=end or reopened_spot.cash!=s.cash or reopened_spot.holdings!=s.holdings:
        raise ValueError('append-only account replay mismatch')
    return {'inverse':end,'initial_spot_coin_earmarked_as_same_inverse_collateral':str(s.holdings[market]),
            'remaining_unearmarked_spot_coin':'0','idle_cash_usdt':str(s.cash),'combined_market_nav':None,
            'actual_transfer_or_exit_verified':False,'funding_applies_to_this_dated_model':False,
            'constructed_clocks':True,'reopened_identical':True,
            'journal_sha256':{str(p.relative_to(out)):sha(p) for p in (sp,ip)}}


def report(lane=LANE,out=None):
    fixtures=verify(lane,data=True);out=Path(out) if out else lane
    if (out/'results.json').exists() or (out/'model_journals').exists():raise ValueError('preserve previous outcomes; fresh --out required')
    out.mkdir(parents=True,exist_ok=True)
    capture=json.loads((lane/'evidence/capture.json').read_text());raws={r['name']:r for r in capture['records']}
    def raw(name):
        r=raws.get(name)
        if r is None or r['http_status']!=200 or not r['complete']:raise ValueError(name+':missing_or_failed_source')
        p=json.loads(gzip.decompress((lane/'evidence'/r['body']).read_bytes()),parse_float=D)
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
    save(out/'results.json',plain({'registry_id':'R327','verdict':'PARTIAL','rows':rows,'capture':capture,
         'entry_plan_slots':4,'fee_cost_cells':24,'terminal_scenario_slots':216,'computed_scenarios':computed,
         'uncomputed_scenarios':216-computed,'constructed_inverse_models':model_count,
         'predictive_strategy_trials':0,'new_prospective_strategy_days':0,'actual_executable_admissions':0,
         'market_expected_net':None,'program_trials_entering':fixtures['program_trials_entering'],
         'source_reciprocal_payoff_and_coin_fee_serialization_verified':False,
         'cost_stress':'same face/base inventory; 1x/2x/3x ENTRY crossing and all modeled commissions at fixed conditional exit ratio',
         'exit_cost_limitation':'future executable exit/TWAP ratio exogenous scenarios, not a full exit impact/latency/counterparty model',
         'code_inputs_sha256':sha(lane/'code_inputs.json'),'data_inputs_sha256':sha(lane/'data_inputs.json')}))
    packed={str(p.relative_to(out)):p.read_text() for p in sorted((out/'model_journals').glob('*.jsonl'))}
    with (out/'journals.json.gz').open('xb') as h:h.write(gzip.compress(encode(packed),mtime=0))
    verify(lane,data=True)
    print('Wrote finite conditional diagnosis; actual net and expected return remain unknown.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path)
    report(out=p.parse_args().out)
