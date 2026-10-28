"""Independent stdlib R344 raw-input, capital, journal and terminal arithmetic oracle.

No production price, account, selector or reporting function is imported.
"""
import argparse
from decimal import Decimal
from fractions import Fraction as F
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
LANE=ROOT/'experiments/same_venue_carry_v2'
EVIDENCE=ROOT/'experiments/same_venue_carry_v1/evidence'
NS=10**9
DAY=86400*NS


def load(p):return json.loads(p.read_text(),parse_float=Decimal)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)


class Checks:
    def __init__(self):self.count=0
    def yes(self,value,label):
        self.count+=1
        if value is not True:raise AssertionError(label)
    def eq(self,a,b,label):self.yes(a==b,label+': '+str(a)[:120]+' != '+str(b)[:120])
    def num(self,a,b,label):self.eq(None if a is None else F(a),b,label)


def chain(text,c):
    c.yes(text.endswith('\n'),'complete journal tail');previous='0'*64;events=[]
    for i,line in enumerate(text.splitlines()):
        row=json.loads(line);sha=row.pop('sha256')
        c.eq(row['sequence'],i,'journal sequence');c.eq(row['previous_sha256'],previous,'journal predecessor')
        c.eq(hashlib.sha256(canonical(row).encode()).hexdigest(),sha,'journal hash')
        events.append(row['event']);previous=sha
    return events


def exact(x):
    if type(x) not in (str,int,Decimal,F):raise ValueError('exact number required')
    return F(x)


def swept(levels,amount):
    left=amount;fills=[]
    for price,size in levels:
        take=min(size,left)
        if take:fills.append((price,take));left-=take
    if left:raise ValueError('insufficient depth')
    return fills


def sides(body,metadata,step,received):
    if type(body['timestamp']) is not int or not 946684800*NS<=body['timestamp']*10**6<=received:
        raise ValueError('publication')
    out=[]
    thresholds=[(exact(x['above_price']),exact(x['tick_size'])) for x in metadata.get('tick_size_steps',[])]
    if any(a[0]>=b[0] for a,b in zip(thresholds,thresholds[1:])):raise ValueError('tick order')
    for name in ('bids','asks'):
        rows=body[name]
        if type(rows) is not list or not 1<=len(rows)<=5:raise ValueError('finite book')
        levels=[]
        for row in rows:
            if type(row) is not list or len(row)!=2:raise ValueError('book row')
            price,size=map(exact,row);tick=exact(metadata['tick_size'])
            for above,new_tick in thresholds:
                if price>above:tick=new_tick
            if price<=0 or size<=0 or size%step or price%tick:raise ValueError('quantity/tick grid')
            if levels and ((price>=levels[-1][0]) if name=='bids' else (price<=levels[-1][0])):
                raise ValueError('strict side order')
            levels.append((price,size))
        out.append(levels)
    if out[0][0][0]>=out[1][0][0]:raise ValueError('crossed book')
    return out


def joint_flags(receipts,publications):
    if not receipts:return ['no_book_receipts','incomplete_four_book_scope']
    last=max(receipts,key=lambda r:r['received_mono_ns']);decision=last['received_mono_ns'];target=last['received_utc_ns']
    flags=[]
    for r,pub in zip(receipts,publications):
        delay=r['received_mono_ns']-r['started_mono_ns']
        if decision-r['started_mono_ns']>2*NS or delay>2*NS:flags.append('joint_request_or_body_age_over_2s')
        if decision-r['received_mono_ns']>NS or r['received_mono_ns']>decision:flags.append('joint_receive_skew_over_1s_or_future')
        if abs(r['received_utc_ns']-r['started_utc_ns']-delay)>50_000_000:flags.append('clock_step_over_50ms')
        if not -100_000_000<=target-pub<=2*NS:flags.append('publication_age_over_2s_or_future')
        if abs(r['received_utc_ns']-last['received_utc_ns']-r['received_mono_ns']+last['received_mono_ns'])>50_000_000:
            flags.append('cross_receipt_clock_step_over_50ms')
    if len(receipts)!=4:flags.append('incomplete_four_book_scope')
    return sorted(set(flags))


def independent_plan(raw,coin,target,profile,config,joint):
    sm,_=raw(coin+'_spot_rules');sb,sr=raw(coin+'_spot_book')
    fm,_=raw(coin+'_future_rules');fb,fr=raw(coin+'_future_book')
    spot=coin+'_USDC';future=coin+'-25DEC26'
    if not (sm['instrument_name']==spot and sm['kind']=='spot' and sm['base_currency']==coin
            and sm['quote_currency']==sm['counter_currency']=='USDC' and exact(sm['contract_size'])==F('0.00000001')
            and type(sm['is_active']) is bool):raise ValueError('spot units')
    if all(type(sm.get(k)) is bool and sm[k] is True for k in ('is_csr','is_cbe_routed')):route='Coinbase-routed'
    elif 'is_csr' not in sm and 'is_cbe_routed' not in sm:route='native'
    else:raise ValueError('route')
    if not (fm['instrument_name']==future and fm['kind']=='future' and fm['instrument_type']=='reversed'
            and fm['base_currency']==fm['settlement_currency']==coin and fm['quote_currency']==fm['counter_currency']=='USD'
            and fm['settlement_period']=='month' and type(fm['expiration_timestamp']) is int
            and fm['expiration_timestamp']*10**6==config['expiry_ns'] and type(fm['is_active']) is bool):
        raise ValueError('inverse units')
    if sb['instrument_name']!=spot or fb['instrument_name']!=future:raise ValueError('book identity')
    step=exact(sm['min_trade_amount']);face_step=exact(fm['min_trade_amount'])
    if min(step,face_step,exact(fm['contract_size']))<=0:raise ValueError('positive lot')
    spot_bids,spot_asks=sides(sb,sm,step,sr['received_utc_ns'])
    future_bids,_=sides(fb,fm,face_step,fr['received_utc_ns'])
    flags=list(joint);decision=max(sr['received_mono_ns'],fr['received_mono_ns'])
    for name,r in (('spot',sr),('dated',fr)):
        elapsed=r['received_mono_ns']-r['started_mono_ns']
        if elapsed<0 or elapsed>2*NS:flags.append(name+':body_latency_over_2s_or_negative')
        if decision-r['started_mono_ns']>2*NS:flags.append(name+':decision_request_age_over_2s')
        if abs(r['received_utc_ns']-r['started_utc_ns']-elapsed)>50_000_000:flags.append(name+':clock_step_over_50ms')
    if abs(sr['received_mono_ns']-fr['received_mono_ns'])>NS:flags.append('body_receipt_skew_over_1s')
    if abs(sr['received_utc_ns']-fr['received_utc_ns']-sr['received_mono_ns']+fr['received_mono_ns'])>50_000_000:
        flags.append('cross_receipt_clock_step_over_50ms')
    if fr['received_utc_ns']+decision-fr['received_mono_ns']-fb['timestamp']*10**6>2*NS:
        flags.append('dated_publication_age_over_2s')
    if not sm['is_active'] or not fm['is_active'] or sb.get('state')!='open' or fb.get('state')!='open':flags.append('public_market_not_open')
    if max(sr['received_utc_ns'],fr['received_utc_ns'])>=config['expiry_ns']:flags.append('expiry_not_future')
    sf=max(exact(config['spot_rate']),exact(sm.get('taker_commission') or 0))
    ff=max(exact(config['future_rate']),exact(fm.get('taker_commission') or 0))
    if min(sf,ff)<0 or max(3*sf,3*ff)>=1:raise ValueError('fee rate')
    face=(exact(target)//face_step)*face_step
    if face<face_step:raise ValueError('face minimum')
    midpoint_s=(spot_bids[0][0]+spot_asks[0][0])/2
    midpoint_f=(exact(fb['bids'][0][0])+exact(fb['asks'][0][0]))/2
    full=swept(future_bids,face)
    if any(midpoint_f-3*(midpoint_f-p)<=0 for p,_ in full):raise ValueError('stressed price')
    a3=sum((n/(midpoint_f-3*(midpoint_f-p)) for p,n in full),F(0))
    q=-((-(a3*(1+3*ff)/(1-3*sf)))//step)*step
    limit=None if profile=='full' else 1
    inverse=swept(future_bids[:limit],face);spot_fill=swept(spot_asks[:limit],q);swept(spot_bids[:limit],q)
    reserve=sum((n*(midpoint_s+3*(p-midpoint_s)) for p,n in spot_fill),F(0))*(1+3*sf)
    return {'coin':coin,'spot_instrument':spot,'future_instrument':future,'route':route,'spot_step':step,'face_step':face_step,
        'face_usd':face,'spot_base':q,'spot_fills':spot_fill,'inverse_fills':inverse,'spot_mid_usdc':midpoint_s,
        'future_mid_usd':midpoint_f,'spot_rate':sf,'future_rate':ff,'reserve_usdc':reserve,
        'spot_publication_ns':sb['timestamp']*10**6,'future_publication_ns':fb['timestamp']*10**6,
        'input_flags':sorted(set(flags)),'public_input_usable':not flags,'expiry_ns':config['expiry_ns'],
        'source_effective_age_verified':False,'actual_order_allowed':False}


def numeric_tree(value):
    if isinstance(value,F):return str(value)
    if isinstance(value,dict):return {k:numeric_tree(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [numeric_tree(v) for v in value]
    return value


def audit(out):
    c=Checks();spec=LANE/'PREREG.md';c.eq(digest(spec),(LANE/'PREREG.sha256').read_text().strip(),'frozen spec')
    for name in ('inputs.json','code_inputs.json','fixtures.json','sources.json'):
        c.yes(digest(LANE/name) in spec.read_text(),'bound '+name)
    for name in ('inputs.json','code_inputs.json','data_inputs.json'):
        m=load(LANE/name)
        for p,h in m['sha256'].items():c.eq(digest(ROOT/p),h,'identity '+p)
    data=load(LANE/'data_inputs.json');c.eq(data['prereg_sha256'],digest(spec),'raw freeze')
    inventory={str(p.relative_to(ROOT)) for p in (EVIDENCE).iterdir() if p.is_file()}
    c.eq(inventory,set(data['sha256']),'raw exact inventory')
    for name in ('PREREG.md','PREREG.sha256','code_inputs.json','data_inputs.json'):
        p=LANE/name;c.eq(subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT),p.read_bytes(),'committed '+name)
    config=load(LANE/'fixtures.json');r=load(out/'results.json');capture=load(EVIDENCE/'capture.json')
    c.eq(r['capture'],capture,'capture unchanged');records={row['name']:row for row in capture['records']}
    c.eq(len(records),len(capture['records']),'unique request identity');c.yes(len(records)<=8,'eight attempts maximum')
    c.yes(capture['closed'] is True and capture['unused_allowance_closed'] is True,'closed finite scope')
    c.eq(capture['actual_orders'],0,'zero orders');c.eq(capture['historical_requests_spent_unchanged'],7757,'historical budget unchanged')
    for row in records.values():
        c.eq(digest(EVIDENCE/row['body']),row['body_sha256'],'raw body identity')
        c.eq(row['redirects'],0,'zero redirects');c.eq(row['retries'],0,'zero retries')
        c.yes(row['accepted_body_bytes']<=64*1024,'finite body')
        label=row['name'];coin,kind,method=label.split('_')
        c.yes(coin in config['coins'] and kind in ('spot','future') and method in ('rules','book'),'fixed request scope')
        url='https://www.deribit.com/api/v2/public/'+('get_instrument' if method=='rules' else 'get_order_book')+'?instrument_name='+config['instruments'][coin][kind]+('' if method=='rules' else '&depth=5')
        c.eq(row['url'],url,'fixed public endpoint')
    budget=chain((EVIDENCE/'budget.jsonl').read_text(),c)
    c.yes(bool(budget),'budget journal present')
    c.eq(budget[0]['scope'],'R343/one-same-venue-current-capture','new bounded scope')
    c.eq(budget[0]['limits'],{'max_requests':8,'max_body_bytes':512*1024,'max_reserved_duration_ns':56*NS,'max_attempt_duration_ns':7*NS},'frozen limits')
    reserves={e['operation_id']:e for e in budget[1:] if e['kind']=='reserve'}
    completions={e['operation_id']:e for e in budget[1:] if e['kind']=='complete'}
    c.eq(set(reserves),set(records),'every attempt charged');c.eq(set(completions),set(records),'all completions retained')
    for name,reserve in reserves.items():
        row=records[name];completion=completions[name]
        c.eq(reserve['body_limit_bytes'],64*1024,'body charge');c.eq(reserve['duration_ns'],7*NS,'time charge')
        c.eq(completion['actual_bytes'],row['accepted_body_bytes'],'actual body bytes')
        c.yes(0<=completion['elapsed_ns']<=7*NS,'bounded attempt duration')
        c.yes(reserve['issued_at_ns']+7*NS<=reserve['deadline_ns'],'within wall deadline')
    c.eq(capture['budget']['requests_charged'],len(records),'accumulated request counter')
    c.eq(capture['budget']['body_bytes_charged_upper_bound'],len(records)*64*1024,'conservative byte counter')
    c.eq(capture['budget']['duration_ns_charged_upper_bound'],len(records)*7*NS,'conservative time counter')
    c.eq(capture['budget']['violations'],[],'no scope violation')
    def raw(name):
        row=records.get(name)
        if row is None or row['http_status']!=200 or row['complete'] is not True:raise ValueError('unavailable')
        payload=json.loads(gzip.decompress((EVIDENCE/row['body']).read_bytes()),parse_float=Decimal)
        if type(payload) is not dict or 'error' in payload or type(payload.get('result')) is not dict:raise ValueError('JSON-RPC error')
        return payload['result'],row
    receipts=[];publications=[]
    for coin in config['coins']:
        for kind in ('spot','future'):
            try:
                b,rec=raw(coin+'_'+kind+'_book')
                if type(b['timestamp']) is not int:raise ValueError('timestamp')
                receipts.append(rec);publications.append(b['timestamp']*10**6)
            except (ValueError,KeyError,TypeError):pass
    joint=joint_flags(receipts,publications)
    anchor=max(receipts,key=lambda x:x['received_mono_ns']) if receipts else {'received_utc_ns':config['fallback_model_anchor_utc_ns'],'received_mono_ns':1}
    packed=json.loads(gzip.decompress((out/'journals.json.gz').read_bytes()));expected_journals=set();computed={};expected_models=[];expected_worlds=[]
    expected_portfolios=[str(t)+'-'+p for t in config['face_targets'] for p in config['depth_profiles']]
    c.eq([p['id'] for p in r['portfolios']],expected_portfolios,'finite portfolio scope')
    for portfolio in r['portfolios']:
        plans={};remaining=F(config['capital_usdc']);admitted=[];complete=True
        c.eq([i['coin'] for i in portfolio['decisions']],config['coins'],'fixed coin order')
        for item in portfolio['decisions']:
            coin=item['coin'];plan=None
            try:plan=independent_plan(raw,coin,portfolio['face_target_per_coin'],portfolio['profile'],config,joint)
            except (ValueError,KeyError,TypeError,ArithmeticError,IndexError):pass
            if plan is None:
                c.eq(item['plan'],None,'unavailable plan preserved');c.yes(item['input_error'] is not None,'failure retained')
                reason='unavailable_input';allowed=False;complete=False
            else:
                c.eq(item['plan'],numeric_tree(plan),'independent complete plan');plans[coin]=plan
                allowed=plan['public_input_usable'] and plan['reserve_usdc']<=remaining
                reason=None if allowed else ('source_clock_state_or_scope_unqualified' if not plan['public_input_usable'] else 'ordered_shared_capital_exceeded')
                if allowed:remaining-=plan['reserve_usdc'];admitted.append(coin)
                complete=complete and plan['public_input_usable']
            c.eq(item['model_admitted'],allowed,'source/capital admission');c.eq(item['reason'],reason,'reason retained')
        c.eq(portfolio['input_complete'],complete,'incomplete is not cash profitability');c.num(portfolio['shadow_remaining_usdc'],remaining,'shared reserve cash')
        for fees in config['fee_controls']:
            for debit in config['spot_fee_assets']:
                for k in config['cost_multiples']:
                    ident=portfolio['id']+'-'+fees+'-'+debit+'-'+str(k);expected_models.append(ident)
                    model=next(m for m in r['models'] if m['id']==ident)
                    legs={};spends=F(0);ownership={};expected_spot=[]
                    for coin in admitted:
                        p=plans[coin];sf=p['spot_rate']*k if fees=='public_standard' else F(0);ff=p['future_rate']*k if fees=='public_standard' else F(0)
                        spot=[(p['spot_mid_usdc']+k*(v-p['spot_mid_usdc']),n) for v,n in p['spot_fills']]
                        inverse=[(p['future_mid_usd']-k*(p['future_mid_usd']-v),n) for v,n in p['inverse_fills']]
                        a=sum((n/v for v,n in inverse),F(0));entry=a*ff
                        base=p['spot_base']*(1-sf) if debit=='base' else p['spot_base']
                        principal=sum((v*n for v,n in spot),F(0));spent=principal*(1+sf) if debit=='quote' else principal
                        residual=base-entry-a;c.yes(residual>=0,'nonnegative model coin reserve');c.yes(spent<=p['reserve_usdc'],'all cost/debit controls prefunded')
                        spends+=spent;ownership[coin]={'purchased_net_coin':base,'same_coin_earmarked':base,'unearmarked_coin':F(0),'inverse_coin_after_fee':base-entry}
                        legs[coin]=(p,sf,residual)
                        expected_spot.extend((coin,v,n,n*sf if debit=='base' else n*v*sf) for v,n in spot)
                        path='states/'+ident+'/'+coin+'-inverse.jsonl';expected_journals.add(path);events=chain(packed[path],c)
                        c.num(F(events[0]['initial_coin']['numerator'],events[0]['initial_coin']['denominator']),base,'same purchased coin, no deposit')
                        c.eq(events[0]['simulation_only'],True,'inverse model only');c.eq(events[0]['contract']['instrument'],p['future_instrument'],'inverse identity')
                        c.eq(len(events)-1,len(inverse),'all inverse fills')
                        for event,(price,face) in zip(events[1:],inverse):
                            pay=event['payload'];wire=lambda x:F(x['numerator'],x['denominator'])
                            c.eq(pay['kind'],'open','opening only');c.eq(wire(pay['price_usd_per_coin']),price,'harmonic price')
                            c.eq(wire(pay['signed_face_usd']),-face,'USD face, no principal credit');c.eq(wire(pay['fee_coin']),face/price*ff,'coin entry fee once')
                            c.eq(pay['simulation_only'],True,'hypothetical fill');c.eq(pay['source_identity'],'hypothetical-source-book-sweep','no invented execution evidence')
                    c.eq(model['ownership'],numeric_tree(ownership),'same coin ownership');cash=F(config['capital_usdc'])-spends
                    c.num(model['cash_usdc'],cash,'one cash account');c.num(model['spent_usdc'],spends,'spot principal and fee once');c.yes(cash>=0,'no borrowing')
                    c.eq(model['source_input_complete'],complete,'source qualification');c.eq(model['actual_expected_net'],None,'unknown expectation');c.eq(model['actual_order_allowed'],False,'no activation')
                    path='states/'+ident+'/spot.jsonl';expected_journals.add(path);events=chain(packed[path],c)
                    c.num(events[0]['initial_cash'],F(config['capital_usdc']),'one whole initial capital');c.eq(events[0]['quote_asset'],'USDC','quote unit')
                    c.eq(len(events)-1,len(expected_spot),'all spot fills, no added capital')
                    for event,(coin,price,q,fee) in zip(events[1:],expected_spot):
                        e=event['payload'];c.eq(e['kind'],'fill','no external capital');c.eq(e['market'],coin+'_USDC','spot identity')
                        c.num(e['quantity'],q,'base quantity');c.num(e['price'],price,'spot crossing');c.num(e['fee_amount'],fee,'spot fee once')
                        c.eq(e['fee_asset'],coin if debit=='base' else 'USDC','explicit debit unit');c.eq(e['simulation_only'],True,'model clock not actual fill')
                    for scale in config['delivery_price_scales']:
                        unit=F(0)
                        for coin,(p,sf,residual) in legs.items():
                            df=F(config['delivery_rate'])*k if fees=='public_standard' else F(0)
                            unit+=(p['face_usd']*(1-df)+residual*p['future_mid_usd']*F(scale))*(1-sf)
                        for annual in config['cash_benchmark_annual_rates']:
                            expected_worlds.append((ident,scale,annual));reference=F(config['capital_usdc'])*(1+F(annual)*F(config['expiry_ns']-anchor['received_utc_ns'],365*DAY))
                            computed[(ident,scale,annual)]=(reference,unit,(reference-cash)/unit if complete and unit>0 else None,
                                cash+unit-reference if complete else None,cash+unit*F('0.99')-reference if complete else None)
    c.eq([m['id'] for m in r['models']],expected_models,'all 48 controls');c.eq(set(packed),expected_journals,'exact model journal inventory')
    c.eq([(w['model'],w['delivery_price_scale'],w['cash_annual_scenario']) for w in r['worlds']],expected_worlds,'all 432 conditional worlds')
    for world in r['worlds']:
        expected=computed[(world['model'],world['delivery_price_scale'],world['cash_annual_scenario'])]
        for field,value in zip(('cash_benchmark_quote','unit_sale_proceeds_before_ratio','minimum_common_exit_ratio','conditional_excess_if_ratio_1','adverse_ratio_0_99_excess'),expected):c.num(world[field],value,field)
        c.eq(world['actual_future_sale_ratio'],None,'no USD/USDC parity claim');c.eq(world['actual_executable_expected_net'],None,'no expected alpha')
    for path,text in packed.items():
        for event in chain(text,c)[1:]:
            e=event['payload'];clock=e['clock']
            c.yes(clock['mono_ns']>anchor['received_mono_ns'],'constructed fill after input anchor')
            c.eq(clock['utc_ns']-anchor['received_utc_ns'],clock['mono_ns']-anchor['received_mono_ns'],'constructed clock offset')
            c.eq(e['occurred_ns'],clock['utc_ns'],'declared model event clock');c.eq(event['asof'],clock['mono_ns'],'known model asof')
    for field,value in (('registry_id','R344'),('prospective_strategy_days',0),('predictive_strategy_trials',0),('actual_executable_expected_net',None),('activation_allowed',False)):c.eq(r[field],value,field)
    return {'registry_id':'R344','status':'PASS','independent_exact_checks':c.count,'portfolios':len(r['portfolios']),
        'models':len(r['models']),'conditional_worlds':len(r['worlds']),'journals':len(packed),'actual_executable_expected_net':None}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    print(json.dumps(audit(args.out),sort_keys=True,indent=2))
