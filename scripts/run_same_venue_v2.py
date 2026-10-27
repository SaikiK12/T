"""R344 finite current same-venue carry economics, not strategy activation."""
import argparse
from decimal import Decimal as D
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lab import prereg
from lab.venue_carry_v2 import prepare,projection,current_flags
from lab.inverse_cash import InverseContract,InverseCashAccount,InverseEvent
from lab.inverse_offer import terminal_hurdle
from lab.spot_cash import SpotCashAccount,SpotEvent
from lab.executable_quotes import Receipt
from lab.stream_quotes import FrameClock
from scripts.run_dated_carry import exact_decimal

LANE=ROOT/'experiments/same_venue_carry_v2'
EVIDENCE=ROOT/'experiments/same_venue_carry_v1/evidence'
DAY=86400*1_000_000_000


def plain(x):
    if isinstance(x,(F,D)):return str(x)
    if isinstance(x,dict):return {k:plain(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [plain(v) for v in x]
    return x


def encoded(x):return (json.dumps(plain(x),sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def save(p,x):
    with p.open('xb') as handle:handle.write(encoded(x))


def committed(p):
    name=str(p.relative_to(ROOT))
    if subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)!=p.read_bytes():
        raise ValueError('required committed identity: '+name)


def verify(*,data=False):
    spec=(LANE/'PREREG.md').read_text();digest=prereg.verify(LANE/'PREREG.md')
    for n in ('code_inputs.json','inputs.json','fixtures.json','sources.json'):
        if prereg.sha256_file(LANE/n) not in spec:raise ValueError('unbound input '+n)
    code=json.loads((LANE/'code_inputs.json').read_text())
    if code['python_version']!=list(sys.version_info[:3]):raise ValueError('runtime drift')
    for m in (code,json.loads((LANE/'inputs.json').read_text())):
        for p,h in m['sha256'].items():
            if prereg.sha256_file(ROOT/p)!=h:raise ValueError('frozen input drift '+p)
    for n in ('PREREG.md','PREREG.sha256','code_inputs.json'):committed(LANE/n)
    if data:
        m=json.loads((LANE/'data_inputs.json').read_text());committed(LANE/'data_inputs.json')
        if m['prereg_sha256']!=digest:raise ValueError('capture/spec drift')
        actual={str(p.relative_to(ROOT)) for p in (EVIDENCE).iterdir() if p.is_file()}
        if actual!=set(m['sha256']):raise ValueError('raw inventory drift')
        for p,h in m['sha256'].items():
            if prereg.sha256_file(ROOT/p)!=h:raise ValueError('raw input drift')
            committed(ROOT/p)
    return json.loads((LANE/'fixtures.json').read_text())


def model_open(plans,admitted,k,fees,debit,capital,anchor,folder):
    """Hypothetical source sweeps; one quote cash ledger, virtual coin earmarks.

    Timestamps after receipt are CONSTRUCTED model clocks, never actual fills.
    Inverse initial coin is the SAME purchased spot inventory, not another deposit.
    """
    folder.mkdir(parents=True)
    spot=SpotCashAccount('deribit-model','USDC',capital,{'BTC_USDC':'BTC','ETH_USDC':'ETH'},anchor,journal_path=folder/'spot.jsonl')
    owned={};cursor=0;legs=[]
    def clock():
        nonlocal cursor
        cursor+=1;return FrameClock(anchor.utc_ns+cursor,anchor.mono_ns+cursor)
    for coin in ('BTC','ETH'):
        if coin not in admitted:continue
        p=plans[coin];v=projection(p,k,fees,debit)
        for i,(price,q) in enumerate(v['spot_fills']):
            at=clock();amount=q*v['spot_rate'] if debit=='base' else q*price*v['spot_rate']
            e=SpotEvent(coin+'-model-spot-'+str(i),'fill',p['spot_instrument'],at.utc_ns,at,'hypothetical-source-book-sweep',
                quantity=exact_decimal(q),price=exact_decimal(price),fee_amount=exact_decimal(amount),fee_asset=coin if debit=='base' else 'USDC')
            if spot.post(e,at.mono_ns)['status']!='applied':raise ValueError('shared spot model rejected')
        if spot.holdings[p['spot_instrument']]!=v['net_spot_coin']:raise ValueError('spot fee debit inconsistent')
        contract=InverseContract(p['future_instrument'],coin,p['face_step'],p['face_step'],p['expiry_ns'],'R344-hypothetical-source-contract')
        inv=InverseCashAccount(contract,v['net_spot_coin'],anchor,journal_path=folder/(coin+'-inverse.jsonl'))
        for i,(price,face) in enumerate(v['inverse_fills']):
            at=clock();e=InverseEvent(coin+'-model-inverse-'+str(i),'open',contract.instrument,at.utc_ns,at,
                'hypothetical-source-book-sweep',price,-face,face/price*v['future_rate'])
            if inv.post(e,at.mono_ns)['status']!='applied':raise ValueError('fully collateralized inverse model rejected')
        if inv.pending or inv.conflicts or inv.coin!=v['net_spot_coin']-v['entry_fee_coin']:
            raise ValueError('inverse fees/collateral mismatch')
        if v['coverage']['all_positive_marks_1x_model_coverage'] is not True:raise ValueError('fee reserve proof failed')
        owned[coin]={'purchased_net_coin':v['net_spot_coin'],'same_coin_earmarked':inv.initial,
            'unearmarked_coin':spot.holdings[p['spot_instrument']]-inv.initial,'inverse_coin_after_fee':inv.coin}
        legs.append({'coin':coin,'plan':p,'projection':v})
    total_spent=sum((v['projection']['initial_spend_usdc'] for v in legs),F(0))
    if spot.cash!=F(capital)-total_spent or any(v['unearmarked_coin'] for v in owned.values()):
        raise ValueError('shared cash or same-coin ownership counted twice')
    reopened=SpotCashAccount('deribit-model','USDC',capital,spot.markets,anchor,journal_path=folder/'spot.jsonl')
    if reopened.cash!=spot.cash or reopened.holdings!=spot.holdings:raise ValueError('shared cash restart drift')
    return {'cash_usdc':spot.cash,'spent_usdc':total_spent,'ownership':owned,'legs':legs,
        'actual_fills_verified':False,'actual_expected_net':None,'actual_order_allowed':False}


def report(out):
    config=verify(data=True)
    if out.exists():raise ValueError('fresh output required')
    out.mkdir(parents=True)
    capture=json.loads((EVIDENCE/'capture.json').read_text());records={r['name']:r for r in capture['records']}
    def raw(name):
        r=records.get(name)
        if r is None or r['http_status']!=200 or not r['complete']:raise ValueError(name+':unavailable')
        value=json.loads(gzip.decompress((EVIDENCE/r['body']).read_bytes()),parse_float=D)
        return value,Receipt(**{k:r[k] for k in Receipt.__dataclass_fields__})
    book_receipts=[];publications=[]
    for coin in config['coins']:
        for kind in ('spot','future'):
            try:
                p,r=raw(coin+'_'+kind+'_book');stamp=p['result']['timestamp']
                if type(stamp) is not int:raise ValueError('native publication clock required')
                book_receipts.append(r);publications.append(stamp*1_000_000)
            except (ValueError,KeyError,TypeError):pass
    decision=max((r.received_mono_ns for r in book_receipts),default=0)
    joint=current_flags(book_receipts,publications,decision)
    if len(book_receipts)!=4:joint+=['incomplete_four_book_scope']
    last=max(book_receipts,key=lambda r:r.received_mono_ns) if book_receipts else None
    anchor=FrameClock(last.received_utc_ns,last.received_mono_ns) if last else FrameClock(config['fallback_model_anchor_utc_ns'],1)
    portfolios=[];models=[];worlds=[];packed={}
    for target in config['face_targets']:
        for depth in config['depth_profiles']:
            plans={};decisions=[];remaining=F(config['capital_usdc'])
            for coin in config['coins']:
                item={'coin':coin,'plan':None,'input_error':None,'model_admitted':False,'reason':None}
                try:
                    sm,_=raw(coin+'_spot_rules');sb,sr=raw(coin+'_spot_book');fm,_=raw(coin+'_future_rules');fb,fr=raw(coin+'_future_book')
                    p=prepare(coin,target,depth,sm,sb,sr,fm,fb,fr,expiry_ns=config['expiry_ns'],
                        spot_rate=config['spot_rate'],future_rate=config['future_rate'],future_source_identity=records[coin+'_future_rules']['body_sha256'])
                    p['input_flags']=sorted(set(p['input_flags']+joint));p['public_input_usable']=not p['input_flags'];plans[coin]=p;item['plan']=p
                    if p['input_flags']:item['reason']='source_clock_state_or_scope_unqualified'
                    elif p['reserve_usdc']>remaining:item['reason']='ordered_shared_capital_exceeded'
                    else:item['model_admitted']=True;remaining-=p['reserve_usdc']
                except (ValueError,TypeError,KeyError,ArithmeticError,IndexError) as error:
                    item['input_error']=type(error).__name__+':'+str(error)[:240];item['reason']='unavailable_input'
                decisions.append(item)
            name=str(target)+'-'+depth;admitted=[r['coin'] for r in decisions if r['model_admitted']]
            complete=all(r['plan'] is not None and r['plan']['public_input_usable'] for r in decisions)
            portfolios.append({'id':name,'face_target_per_coin':target,'profile':depth,'decisions':decisions,
                'common_capital_usdc':config['capital_usdc'],'shadow_remaining_usdc':remaining,'input_complete':complete})
            for fees in config['fee_controls']:
                for debit in config['spot_fee_assets']:
                    for k in config['cost_multiples']:
                        ident=name+'-'+fees+'-'+debit+'-'+str(k);folder=out/'states'/ident
                        model=model_open(plans,admitted,k,fees,debit,config['capital_usdc'],anchor,folder)
                        models.append({'id':ident,'portfolio':name,'fee_control':fees,'fee_asset':debit,'cost_multiple':k,
                            'cash_usdc':model['cash_usdc'],'spent_usdc':model['spent_usdc'],'ownership':model['ownership'],
                            'source_input_complete':complete,'actual_expected_net':None,'actual_order_allowed':False})
                        for scale in config['delivery_price_scales']:
                            unit=F(0)
                            for leg in model['legs']:
                                p,v=leg['plan'],leg['projection'];df=F(config['delivery_rate'])*k if fees=='public_standard' else F(0)
                                h=terminal_hurdle(p['face_usd'],v['inverse_entry_cost_coin'],v['net_spot_coin'],v['entry_fee_coin'],df,v['spot_rate'],
                                    delivery_price=p['future_mid_usd']*F(scale),exit_ratio=None,initial_spend_quote=v['initial_spend_usdc'],
                                    total_capital_quote=v['initial_spend_usdc'],other_exit_cost_quote=0)
                                if h['unit_terminal_quote_before_ratio'] is None:raise ValueError('supplied-world terminal unit unavailable')
                                unit+=h['unit_terminal_quote_before_ratio']
                            for annual in config['cash_benchmark_annual_rates']:
                                growth=1+F(annual)*F(config['expiry_ns']-anchor.utc_ns,365*DAY)
                                reference=F(config['capital_usdc'])*growth
                                worlds.append({'model':ident,'delivery_price_scale':scale,'cash_annual_scenario':annual,
                                    'cash_benchmark_quote':reference,'unit_sale_proceeds_before_ratio':unit,
                                    'minimum_common_exit_ratio':(reference-model['cash_usdc'])/unit if complete and unit>0 else None,
                                    'conditional_excess_if_ratio_1':model['cash_usdc']+unit-reference if complete else None,
                                    'adverse_ratio_0_99_excess':model['cash_usdc']+unit*F('.99')-reference if complete else None,
                                    'actual_future_sale_ratio':None,'actual_executable_expected_net':None})
                        for p in sorted(folder.glob('*.jsonl')):packed[str(p.relative_to(out))]=p.read_text()
    save(out/'results.json',{'registry_id':'R344','portfolios':portfolios,'models':models,'worlds':worlds,'capture':capture,
        'prospective_strategy_days':0,'predictive_strategy_trials':0,'actual_executable_expected_net':None,'activation_allowed':False})
    with (out/'journals.json.gz').open('xb') as h:h.write(gzip.compress(encoded(packed),mtime=0))
    verify(data=True)
    return {'portfolios':len(portfolios),'model_cells':len(models),'conditional_worlds':len(worlds),
        'complete_input_portfolios':sum(p['input_complete'] for p in portfolios),'actual_executable_expected_net':None}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    print(json.dumps(report(p.parse_args().out),indent=2))
