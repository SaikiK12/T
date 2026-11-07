"""Independent R317 conditional fee-route audit; stdlib/frozen independent utilities only."""
import argparse
from collections import Counter
from decimal import Decimal as D
from fractions import Fraction
import gzip
import hashlib
import importlib.util
import json
from math import lcm
from pathlib import Path

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'experiments/warm_values_v1/check_warm.py').exists())
spec=importlib.util.spec_from_file_location('independent_parent',ROOT/'experiments/warm_values_v1/check_warm.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
a=p.a
check,near,dec=p.check,p.near,p.dec
NS=10**9;SYMBOLS=p.SYMBOLS;GRIDS=p.GRIDS
PATHS=('reserve_control','crossing_floor','nominal_standard','nominal_premium','nominal_plus',
       'advertised_standard','advertised_premium','advertised_plus')
TIERS={'standard':(D(0),300),'premium':(D('2.8'),140),'plus':(D('.5'),300)}
read=lambda path:json.loads(path.read_text())
digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()


def nominal(symbol,m,r,target,anchor):
    flags=[]
    if m.get('symbol')!=symbol+'_USDT' or m.get('settleCoin')!='USDT' or type(m.get('type')) is not int or m['type']!=1:
        flags.append('instrument_or_linear_quote_units_unverified')
    if r is None or any(type(r.get(k)) is not int or r[k]<0 for k in ('received_mono_ns','received_utc_ns')):
        flags.append('public_metadata_clock_missing_or_invalid')
    elif r['received_mono_ns']>target:flags.append('public_metadata_not_yet_known')
    elif abs((r['received_utc_ns']-anchor['utc_ns'])-(r['received_mono_ns']-anchor['mono_ns']))>50000000:
        flags.append('metadata_local_clock_step')
    if m.get('feeRateMode')!='NORMAL' or m.get('feeRateType')!='BASE':flags.append('nonbase_or_temporary_fee_entitlement_unverified')
    if type(m.get('isZeroFeeRate')) is not bool or type(m.get('isZeroFeeSymbol')) is not bool:flags.append('zero_fee_status_unknown')
    elif m['isZeroFeeRate'] or m['isZeroFeeSymbol']:flags.append('zero_fee_quota_account_or_expiry_unverified')
    try:
        rate=dec(m['takerFeeRate'],zero=True);check(rate<=1,'fee fraction range')
        if rate==0:flags.append('zero_nominal_is_not_fee_entitlement')
    except (ValueError,KeyError,ArithmeticError,AssertionError):rate=None;flags.append('public_taker_rate_missing_or_invalid')
    return (None if flags else rate*10000),flags


def expected_path(path,s,m,l,r,t,anchor,sources):
    if path=='reserve_control':return (D(10),D(4)),0,[],[sources['reserve']]*2
    if path=='crossing_floor':return (D(0),D(0)),0,[],[sources['floor']]*2
    origin,tier=path.split('_');lr,minimum=TIERS[tier]
    if origin=='nominal':mr,flags=nominal(s,m,r,t,anchor);ms=sources['metadata'] if mr is not None else None
    else:mr,flags,ms=D(4),[],sources['mexc_advertised']
    if tier in ('premium','plus') and (l.get('symbol')!=s or l.get('is_taker_fee_enabled') is not True):flags.append('lighter_paid_tier_fee_enabled_contract_unverified')
    if mr is None:flags.append('mexc:fee_unknown')
    return (mr,lr),minimum,flags,[ms,sources['lighter_'+tier]]


def exact_cost(books,q,rates):
    fills=[a.sweep(side,q) for b in books for side in (b['asks'],b['bids'])]
    capacity=min(sum(sz for _,sz in side) for b in books for side in (b['bids'],b['asks']))
    if None in fills:return {'displayed_fillable':False,'capacity':capacity}
    mb,ms,lb,ls=fills;cross=mb-ms+lb-ls;fee=(mb+ms)*rates[0]/10000+(lb+ls)*rates[1]/10000
    notionals=[q*b['mid'] for b in books];leg=sum(notionals)/2
    return {'displayed_fillable':True,'capacity':capacity,'crossing':cross,'fee':fee,'total':cross+fee,
            'leg':leg,'notionals':notionals,
            'long_mexc':mb-notionals[0]+notionals[1]-ls+mb*rates[0]/10000+ls*rates[1]/10000,
            'long_lighter':lb-notionals[1]+notionals[0]-ms+lb*rates[1]/10000+ms*rates[0]/10000}


def cost_check(out,ex,q,counts,label):
    check(out['displayed_fillable']==ex['displayed_fillable'],label+' capacity eligibility')
    near(out['quantity_base'],q,label+' quantity');near(out['capital_usd'],10000,label+' capital')
    near(out['shown_two_way_capacity_base'],ex['capacity'],label+' capacity')
    if not ex['displayed_fillable']:return
    check(all(n<=5000 for n in ex['notionals']),label+' segregated capital')
    near(out['crossing_usd'],ex['crossing'],label+' crossing');near(out['fee_usd'],ex['fee'],label+' own-fill notional charge')
    near(out['leg_mid_notional_usd'],ex['leg'],label+' bp denominator')
    for actual,n in zip(out['venue_margin_mid_notionals_usd'],ex['notionals']):near(actual,n,label+' venue notional')
    near(out['long_mexc_entry_cost_usd'],ex['long_mexc'],label+' long-MEXC orientation')
    near(out['long_lighter_entry_cost_usd'],ex['long_lighter'],label+' long-Lighter orientation')
    check(len(out['scenarios'])==3,label+' all stress tiers')
    for k,z in enumerate(out['scenarios'],1):
        check(z['multiple']==k,label+' stress order')
        near(z['round_trip_cost_usd'],k*ex['total'],label+' stressed whole cost')
        near(z['break_even_leg_bp'],k*ex['total']/ex['leg']*10000,label+' stressed leg bp')
        near(z['capital_cost_bp'],k*ex['total'],label+' stressed capital bp')
        counts[label+'_cost_scenarios_checked']+=1


def check_rows(rows,result,anchor,mapping,connections,frames,receipts,sources,base_controls):
    a.MAX_ERROR=0.;counts=Counter();replay=p.Replay(frames,{int(k):v for k,v in mapping['names'].items()},mapping['metadata'],anchor,connections)
    expected={(s,g,d,f) for s in SYMBOLS for g in GRIDS for d in (0,300) for f in PATHS}
    keys=[(r['symbol'],r['grid_second'],r['access_delay_ms'],r['fee_path']) for r in rows]
    check(len(keys)==len(set(keys))==576 and set(keys)==expected,'all fixed576 fee rows')
    controls={};quantities={}
    dynamic={'fee_path','assumed_taker_bp','fee_sources','fee_flags','minimum_venue_delay_ms','minimum_delay_satisfied','cost','reserve_minus_scenario_charge_usd'}
    for r in rows:
        s,g,delay,path=r['symbol'],r['grid_second'],r['access_delay_ms'],r['fee_path'];t=anchor['mono_ns']+g*NS+delay*1000000
        check(r['target_mono_ns']==t,'fixed causal deadline')
        check(r['account_effective_fee_verified'] is r['fee_schedule_asof_verified'] is r['execution_ready'] is False,'fee/execution certification')
        check(r['funding_cash_status'].startswith('unscored:'),'funding cash claim')
        check(r['cost_unit']=='USD_equivalent_under_USDT_USD_quote_parity_assumption','hidden asset conversion')
        k=(s,g,delay);common={x:y for x,y in r.items() if x not in dynamic}
        if k in controls:check(common==controls[k],'fee profile changed books/q/guards/control')
        else:
            controls[k]=common;counts['base_rows_checked']+=1
            old=base_controls[k]
            for field in ('quantity_base','book_flags','book_source_times_ns','book_receive_times_ns','session_metadata','shown_levels','lighter_assembly'):
                check((field in r)==(field in old) and r.get(field)==old.get(field),'changed frozen parent control '+field)
            check(r['reference_reserve_cost']==old['cost'],'changed original reserve cost')
        replay.advance(t);books=replay.books(s,t);q=dec(r['quantity_base']) if r['quantity_base'] is not None else None
        if delay==0:quantities[s,g]=q
        check(q==quantities[s,g],'future/resized q')
        if q is not None:
            mm,lm=mapping['metadata'][s]['mexc'],mapping['metadata'][s]['lighter']
            x=Fraction(dec(mm['contractSize'])*dec(mm['volUnit']));y=Fraction(1,10**a.uint(lm['supported_size_decimals']));den=lcm(x.denominator,y.denominator)
            step=D(lcm(x.numerator*(den//x.denominator),y.numerator*(den//y.denominator)))/D(den)
            check(q%step==0,'common base lattice')
            if delay==0:
                budget=D(250)/max(b['mid'] for b in books);check(q<=budget+D('1e-10') and q+step>budget-D('1e-10'),'immediate budget rounding')
        m=mapping['metadata'].get(s,{});rates,minimum,flags,refs=expected_path(path,s,m.get('mexc',{}),m.get('lighter',{}),receipts.get(s),t,anchor,sources)
        for v,b in zip(('mexc','lighter'),books):
            if b is None:flags.append(v+':book_identity_unavailable')
        check(Counter(r['fee_flags'])==Counter(flags),'fee/source flags')
        check(r['fee_sources']==refs,'source provenance changed')
        for observed,rate in zip(r['assumed_taker_bp'],rates):
            check((observed is None)==(rate is None),'unknown fee became zero')
            if rate is not None:near(observed,rate,'fraction/percent/bp conversion')
        check(r['minimum_venue_delay_ms']==minimum and r['minimum_delay_satisfied']==(delay>=minimum),'minimum delay versus control')
        should_cost=not flags and not r['book_flags'] and q is not None
        check((r['cost'] is not None)==should_cost,'missing/invented scenario cost')
        if should_cost:
            check(all(not p.freshness(b,t,anchor) for b in books),'stale/future quoted cost')
            check(abs(books[0]['source']-books[1]['source'])<=NS and abs(books[0]['receive']-books[1]['receive'])<=NS,'paired skew')
            for v in ('mexc','lighter'):check(connections[v]['opened_mono_ns']<=t<connections[v]['unusable_mono_ns'],'cost outside stream availability')
            ex=exact_cost(books,q,rates);cost_check(r['cost'],ex,q,counts,'scenario')
            if ex['displayed_fillable']:
                control=exact_cost(books,q,(D(10),D(4)));near(r['reserve_minus_scenario_charge_usd'],control['fee']-ex['fee'],'charge difference is not PnL')
                if path=='reserve_control':check(r['cost']==r['reference_reserve_cost'],'original reserve changed')
        else:check(r['reserve_minus_scenario_charge_usd'] is None,'invented charge saving')
        counts['rows_checked']+=1
    check(result['registry_id']=='R317' and result['rows']==576 and tuple(result['descriptive_fee_paths'])==PATHS,'summary identity/finite paths')
    check(result['predictive_trials']==result['paper_days']==0 and result['net_return_tested'] is False,'return/paper/trial claim')
    near(result['capital_usd'],10000,'summary capital');near(result['capital_per_venue_usd'],5000,'summary capital segregation')
    cells=result['cells'];check(len(cells)==96 and len({(c['symbol'],c['delay_ms'],c['fee_path']) for c in cells})==96,'all96 summary cells')
    for c in cells:
        chosen=[r for r in rows if (r['symbol'],r['access_delay_ms'],r['fee_path'])==(c['symbol'],c['delay_ms'],c['fee_path'])]
        good=[r for r in chosen if r['cost'] and r['cost']['displayed_fillable'] and not r['book_flags']]
        check(c['grids']==len(chosen)==6 and c['cost_rows']==len(good),'summary costs')
        check(c['minimum_delay_supported_cost_rows']==sum(r['minimum_delay_satisfied'] for r in good),'delay-applicability count')
        check(Counter(c['fee_flags'])==Counter(f for r in chosen for f in r['fee_flags']),'summary fee flags')
        check(len(c['cost_tiers'])==3,'summary stress tiers')
        for k,z in enumerate(c['cost_tiers'],1):
            check(z['multiple']==k and z['n']==len(good),'summary tier count')
            for field,metric in [('round_trip_usd_range','round_trip_cost_usd'),('break_even_leg_bp_range','break_even_leg_bp')]:
                values=[r['cost']['scenarios'][k-1][metric] for r in good]
                if values:near(z[field][0],min(values),'summary min');near(z[field][1],max(values),'summary max')
                else:check(z[field] is None,'invented summary range')
    return {**dict(counts),'maximum_absolute_numeric_difference':a.MAX_ERROR,'production_imports':False,'owner_fee_and_execution_never_certified':True,
            'scope':'conditional post-hoc fee arithmetic on previously seen input, not actual fees/fills, net return or prospective evidence'}


def audit(lane):
    lane=Path(lane).resolve();check(digest(lane/'PREREG.md')==(lane/'PREREG.sha256').read_text().strip(),'prereg hash')
    check(digest(lane/'code_inputs.json') in (lane/'PREREG.md').read_text(),'unbound code manifest')
    for name,h in read(lane/'code_inputs.json')['sha256'].items():check(digest(ROOT/name)==h,'code drift '+name)
    data=read(lane/'data_inputs.json');check(digest(lane/'data_inputs.json') in (lane/'PREREG.md').read_text(),'unbound seen data identity')
    check(data['parent_path']=='experiments/warm_values_v1' and data['parent_data_already_seen'] is True,'parent/seen-data scope')
    required={data['parent_path']+'/'+f for f in ('PREREG.md','PREREG.sha256','code_inputs.json','evidence_inputs.json','results.json','observations.jsonl.gz')}
    check(required==set(data['sha256']),'incomplete or nonfixed parent identity')
    for name,h in data['sha256'].items():check(digest(ROOT/name)==h,'parent data drift '+name)
    parent=ROOT/data['parent_path'];anchor,mapping,connections,frames,_,_=p.inputs(parent)
    rr=read(parent/'evidence/receipts.json')['records'];receipts={r['name'].removesuffix('_mexc_metadata'):r for r in rr if r['name'].endswith('_mexc_metadata')}
    oldrows=[json.loads(x) for x in gzip.open(parent/'observations.jsonl.gz','rt')]
    base={(r['symbol'],r['grid_second'],r['access_delay_ms']):r for r in oldrows if r['value_profile']=='WS_change'}
    check(len(base)==72,'complete held parent controls')
    rows=[json.loads(x) for x in gzip.open(lane/'observations.jsonl.gz','rt')];result=read(lane/'results.json')
    check(result['observations_sha256']==digest(lane/'observations.jsonl.gz') and result['data_identity_sha256']==digest(lane/'data_inputs.json'),'result identity')
    return check_rows(rows,result,anchor,mapping,connections,frames,receipts,read(lane/'sources.json')['scenario_sources'],base)


def self_test():
    check(D(30000)*D(10000)*D('.0001')*D('.0002')==6,'official MEXC fee example')
    check(D('0.0280')/100*10000==D('2.8'),'Premium percent conversion')
    b={'asks':((D(101),D(10)),),'bids':((D(99),D(10)),),'mid':D(100)}
    x=exact_cost((b,b),D('2.5'),(D(2),D('2.8')))
    check(x['crossing']==10 and x['fee']==D('.24') and x['total']==D('10.24'),'own fill cash fee, not midpoint omission')
    check(exact_cost((b,b),D(5),(D(2),D('2.8')))['fee']==2*x['fee'],'quantity scaling')


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('lane',nargs='?',type=Path,default=ROOT/'experiments/fee_routes_v1');ap.add_argument('--self-test',action='store_true')
    args=ap.parse_args();self_test();print(json.dumps({'self_test':'passed','market_inputs_read':False} if args.self_test else audit(args.lane),sort_keys=True,indent=2))
