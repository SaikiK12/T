"""Independent R315 receipt, causal value and quote-cost audit; no production imports."""
import argparse
from collections import Counter
from decimal import Decimal as D, ROUND_FLOOR
from fractions import Fraction
import gzip
import hashlib
import importlib.util
import json
from math import lcm
from pathlib import Path

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'experiments/depth_quotes_v1/check_depth.py').exists())
spec=importlib.util.spec_from_file_location('independent_depth_audit',ROOT/'experiments/depth_quotes_v1/check_depth.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
NS=10**9;SYMBOLS=a.SYMBOLS;GRIDS=(10,20,30,40,50,60)
check,near,dec,source=a.check,a.near,a.dec,a.source
read=lambda p:json.loads(p.read_text())
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def freshness(p,t,anchor):
    if p is None:return ['missing']
    flags=[]
    if not 0<=t-p['receive']<=NS:flags.append('receive_age_outside_0_1s')
    if not -100000000<=anchor['utc_ns']+t-anchor['mono_ns']-p['source']<=2*NS:flags.append('reported_source_age_outside_minus100ms_2s')
    if abs((p['utc']-anchor['utc_ns'])-(p['receive']-anchor['mono_ns']))>50000000:flags.append('local_UTC_step_over_50ms')
    return flags


def raw_packet(p,f,venue):
    return {'price':dec(p),'source':f['source'],'receive':f['mono_ns'],'utc':f['utc_ns'],
            'role':'REST_system' if venue=='rest' else 'WS_publication'}


class Replay:
    def __init__(self,frames,names,meta,anchor,connections):
        self.frames=sorted(frames,key=lambda f:(f['mono_ns'],f['venue'],f['number']));self.i=0
        self.states={s:a.OrderBook(m) for m,s in names.items()};self.latest={};self.previous={}
        self.meta,self.names,self.anchor,self.connections=meta,names,anchor,connections
    def advance(self,t):
        while self.i<len(self.frames) and self.frames[self.i]['mono_ns']<=t:
            f=self.frames[self.i];self.i+=1;v=f['venue']
            try:p=json.loads(f['raw']);check(isinstance(p,dict),'nonobject frame')
            except (ValueError,TypeError,AssertionError):
                p=None
                for k in ('book','reference'):
                    for s in SYMBOLS:self.latest[v,k,s]=None
            if v=='lighter':
                for state in self.states.values():state.consume(p,f)
            if p is None:continue
            s=k=None
            try:
                if v=='mexc':
                    ch=p.get('channel');s=str(p.get('symbol','')).removesuffix('_USDT')
                    if ch not in ('push.depth.full','push.fair.price') or s not in SYMBOLS:continue
                    k='book' if ch=='push.depth.full' else 'reference';d=p['data']
                    check(d.get('symbol',s+'_USDT')==s+'_USDT','MEXC identity')
                    if k=='book':
                        lim=a.uint(self.meta[s]['mexc']['marketOrderMaxLevel']);check(lim>0,'depth limit');sides=[]
                        for side in ('bids','asks'):
                            pairs=[]
                            for x in d[side]:
                                check(len(x)==3 and dec(x[2])==dec(x[2]).to_integral_value(),'MEXC full count')
                                pairs.append((dec(x[0]),dec(x[1])*dec(self.meta[s]['mexc']['contractSize'])))
                            pairs=pairs[:lim];prices=[p for p,q in pairs]
                            check(len(prices)==len(set(prices)) and prices==sorted(prices,reverse=side=='bids'),'MEXC side order')
                            sides.append(dict(pairs))
                        b=a.book(*sides,f,source(d['cts'],1000000),a.uint(d['version']))
                    else:b=raw_packet(d['price'],{**f,'source':source(p['ts'],1000000)},'mexc')
                else:
                    ch=p.get('channel','')
                    if not isinstance(ch,str) or not ch.startswith('market_stats:'):continue
                    market=int(ch.split(':')[1]);s=self.names.get(market);k='reference'
                    if s not in SYMBOLS or p.get('type') not in ('subscribed/market_stats','update/market_stats'):continue
                    d=p['market_stats'];check(d['symbol']==s and d['market_id']==market,'index identity')
                    b=raw_packet(d['index_price'],{**f,'source':source(p['timestamp'],1000000)},'lighter')
                key=(v,k,s);old=self.previous.get(key)
                if old:
                    check(b['source']>=old['source'] and (k!='book' or b['version']>=old['version']),'source regression')
                    same=b['version']==old['version'] if k=='book' else b['source']==old['source']
                    if same:
                        check((b['bids'],b['asks'])==(old['bids'],old['asks']) if k=='book' else b['price']==old['price'],'conflicting duplicate');continue
                self.latest[key]=self.previous[key]=b
            except (ValueError,TypeError,KeyError,ArithmeticError,AssertionError):
                if s is not None and k is not None:self.latest[v,k,s]=None
        if self.connections.get('lighter',{}).get('unusable_mono_ns',2**100)<=t:
            for state in self.states.values():state.status='invalid'
    def books(self,s,t):
        st=self.states.get(s)
        return (self.latest.get(('mexc','book',s)),st.export(t,self.anchor) if st else None)


def inputs(lane):
    check(digest(lane/'PREREG.md')==(lane/'PREREG.sha256').read_text().strip(),'prereg hash')
    check(digest(lane/'code_inputs.json') in (lane/'PREREG.md').read_text(),'unbound code')
    for p,h in read(lane/'code_inputs.json')['sha256'].items():check(digest(ROOT/p)==h,'code drift '+p)
    seal=read(lane/'evidence_inputs.json');e=lane/'evidence'
    check(seal['code_manifest_sha256']==digest(lane/'code_inputs.json'),'seal code')
    check(set(seal['sha256'])=={str(p.relative_to(lane)) for p in e.iterdir() if p.is_file()},'sealed inventory')
    for p,h in seal['sha256'].items():check(digest(lane/p)==h,'raw drift '+p)
    anchor=read(e/'anchor.json') if (e/'anchor.json').exists() else {'mono_ns':0,'utc_ns':0}
    mapping=read(e/'metadata.json') if (e/'metadata.json').exists() else {'metadata':{},'names':{}}
    connections=read(e/'connections.json');receipts=read(e/'receipts.json');rr=receipts['records']
    check(len(rr)==receipts['requests']<=7 and receipts['duration_seconds']<=120,'metadata requests/duration')
    check(sum(r['bytes'] for r in rr)==receipts['response_bytes']<=receipts['response_body_read_upper_bound']==sum(r['body_read_upper_bound'] for r in rr)<=2*1024**2,'metadata budget')
    bodies={}
    for r in rr:
        raw=gzip.decompress((e/r['body']).read_bytes())
        check(len(raw)==r['bytes']<=r['body_read_upper_bound']<=1024**2 and hashlib.sha256(raw).hexdigest()==r['sha256'],'metadata raw')
        if not r['error']:bodies[r['name']]=json.loads(raw)
    for sym,pair in mapping['metadata'].items():
        mx=bodies[sym+'_mexc_metadata']['data']
        if isinstance(mx,list):mx,=[x for x in mx if x['symbol']==sym+'_USDT']
        lt,=[x for x in bodies['lighter_metadata']['order_book_details'] if x['symbol']==sym and x['market_type']=='perp']
        check(pair=={'mexc':mx,'lighter':lt},'raw metadata mapping')
    check(mapping['names']=={str(p['lighter']['market_id']):s for s,p in mapping['metadata'].items()},'market IDs')
    frames=[];check(set(connections)<=set(('mexc','lighter')),'unknown connection')
    for v,c in connections.items():
        path=e/(v+'.jsonl.gz');ff=[json.loads(x) for x in gzip.open(path,'rt')] if path.exists() else []
        check(c['handshake_attempts']==1 and len(ff)==c['messages']<=20000,'handshake/messages')
        check(sum(len(f['raw'].encode()) for f in ff)==c['payload_bytes']<=8*1024**2,'stream bytes')
        check(c['unusable_mono_ns']<=c['closed_mono_ns'],'cleanup boundary')
        for i,f in enumerate(ff,1):check(f['venue']==v and f['number']==i and len(f['raw'].encode())<=256*1024 and c['opened_mono_ns']<=f['mono_ns']<=c['unusable_mono_ns'],'frame receipt')
        frames+=ff
    fairs=read(e/'fair_receipts.json')['records'];expected={(s,g) for s in SYMBOLS for g in GRIDS}
    check(not fairs or (len(fairs)==36 and {(r['symbol'],r['grid_second']) for r in fairs}==expected),'fair slots')
    attempts=sum(bool(r['attempted']) for r in fairs);check(attempts<=36 and attempts+len(rr)<=43,'combined GET cap')
    check(sum(r['body_read_upper_bound'] for r in fairs)<=36*4096,'fair upper bound')
    packets=[]
    for r in fairs:
        check(r['scheduled_mono_ns']==anchor['mono_ns']+(r['grid_second']-1)*NS,'changed fair schedule')
        if not r['attempted']:check(r['bytes']==r['body_read_upper_bound']==0,'unattempted bytes');continue
        raw=gzip.decompress((e/r['body']).read_bytes())
        check(len(raw)==r['bytes']<=r['body_read_upper_bound']<=4096 and hashlib.sha256(raw).hexdigest()==r['sha256'],'fair raw SHA/body cap')
        check(r['scheduled_mono_ns']<=r['started_mono_ns']<=r['received_mono_ns']<=r['worker_cleanup_finished_mono_ns'] and r['started_mono_ns']<anchor['mono_ns']+65*NS,'fair clocks')
        try:
            check(not r['error'],'failed latest fair');d=json.loads(raw)
            check(d['success'] is True and d['code']==0 and d['data']['symbol']==r['symbol']+'_USDT','REST identity')
            stamp=source(d['data']['timestamp'],1000000);check(stamp<=r['received_utc_ns']+100000000,'REST clock ahead')
            p=raw_packet(d['data']['fairPrice'],{'source':stamp,'mono_ns':r['received_mono_ns'],'utc_ns':r['received_utc_ns']},'rest')
        except (ValueError,KeyError,TypeError,ArithmeticError,AssertionError):p=None
        packets.append((r,p))
    return anchor,mapping,connections,frames,packets,attempts


def audit(lane):
    a.MAX_ERROR=0.
    lane=Path(lane).resolve();anchor,mapping,connections,frames,fairs,attempts=inputs(lane)
    replay=Replay(frames,{int(k):v for k,v in mapping['names'].items()},mapping['metadata'],anchor,connections)
    rows=[json.loads(x) for x in gzip.open(lane/'observations.jsonl.gz','rt')]
    keys=[(r['symbol'],r['grid_second'],r['access_delay_ms'],r['value_profile']) for r in rows]
    check(len(rows)==len(set(keys))==144 and set(keys)=={(s,g,d,p) for s in SYMBOLS for g in GRIDS for d in (0,300) for p in ('WS_change','REST_system')},'all fixed rows')
    counts=Counter();controls={};quantities={}
    for r in rows:
        s,g,delay,profile=r['symbol'],r['grid_second'],r['access_delay_ms'],r['value_profile'];t=anchor['mono_ns']+g*NS+delay*1000000
        check(r['target_mono_ns']==t and r['execution_ready'] is False and r['cash_ledger_status'].startswith('unscored:'),'deadline/cash status')
        replay.advance(t);books=replay.books(s,t);q=dec(r['quantity_base']) if r['quantity_base'] is not None else None
        k=(s,g,delay);common={x:y for x,y in r.items() if x not in ('value_profile','value_evidence','rest_source_receipt')}
        if k in controls:check(common==controls[k],'value profile changed q/books/cost')
        else:controls[k]=common
        if delay==0:quantities[s,g]=q
        if q is not None:
            check(q==quantities[s,g],'future/resized quantity');mm,lm=mapping['metadata'][s]['mexc'],mapping['metadata'][s]['lighter']
            aa=Fraction(dec(mm['contractSize'])*dec(mm['volUnit']));bb=Fraction(1,10**a.uint(lm['supported_size_decimals']));den=lcm(aa.denominator,bb.denominator)
            step=D(lcm(aa.numerator*(den//aa.denominator),bb.numerator*(den//bb.denominator)))/D(den);check(q%step==0,'common lattice')
            if delay==0:budget=D(250)/max(b['mid'] for b in books);check(q<=budget+D('1e-10') and q+step>budget-D('1e-10'),'causal immediate q')
        if r['cost']:
            check(q is not None and all(not freshness(b,t,anchor) for b in books),'cost used stale/future books')
            for v in ('mexc','lighter'):
                c=connections[v];check(c['opened_mono_ns']<=t<c['unusable_mono_ns'],'cost after stop')
            check(abs(books[0]['source']-books[1]['source'])<=NS and abs(books[0]['receive']-books[1]['receive'])<=NS,'book skew')
            ex=a.economics(*books,q);out=r['cost'];near(out['quantity_base'],q,'cost quantity');check(out['displayed_fillable']==ex['displayed_fillable'],'depth capacity');near(out['capital_usd'],10000,'capital')
            if ex['displayed_fillable']:
                near(out['crossing_usd'],ex['crossing'],'crossing');near(out['fee_usd'],ex['fee'],'reserve');check(all(x<=5000 for x in ex['notionals']),'segregated capital')
                check(len(out['scenarios'])==3,'all fixed stress tiers')
                for n,z in enumerate(out['scenarios'],1):check(z['multiple']==n,'scenario order');near(z['round_trip_cost_usd'],n*ex['cost'],'cost');near(z['break_even_leg_bp'],n*ex['cost']/ex['leg']*10000,'bp');counts['cost_scenarios_checked']+=1
        selected=None;mx=replay.latest.get(('mexc','reference',s));lt=replay.latest.get(('lighter','reference',s))
        if profile=='REST_system':
            eligible=[(rr,p) for rr,p in fairs if rr['symbol']==s and rr['received_mono_ns']<=t]
            selected=max(eligible,key=lambda z:z[0]['received_mono_ns']) if eligible else None;mx=selected[1] if selected else None
        check(r['rest_source_receipt']==(selected[0]['body'] if selected else None),'latest failed/future fair selection')
        value=r['value_evidence'];check(value['cash_certified'] is False and value['execution_ready'] is False,'certified cash')
        flags=[]
        for v,p,b,o in zip(('mexc','lighter'),(mx,lt),books,value['observations']):
            ff=freshness(p,t,anchor)
            if b is None:ff.append('quote_value_identity_unavailable_or_mismatch')
            check(o['venue']==v and o['kind']==('fair' if v=='mexc' else 'index'),'value identity')
            check(o['clock_role']==(p['role'] if p else None),'clock relabel')
            check(o['publication_ns']==(p['source'] if p else None) and o['receive_ns']==(p['receive'] if p else None),'raw value clock')
            check(o['effective_value_time_verified'] is False and o['settlement_cash_verified'] is False,'settlement attestation')
            check(Counter(o['flags'])==Counter(ff),'value flags');flags += [v+':'+f for f in ff]
            if p:near(o['price'],p['price'],'raw price');counts['causal_value_receipts_checked']+=1
            else:check(o['price'] is None,'invented price')
        if mx and lt:
            if abs(mx['receive']-lt['receive'])>NS:flags.append('value_receive_skew_over_1s')
            if abs(mx['source']-lt['source'])>NS:flags.append('value_publication_skew_over_1s')
        check(Counter(value['flags'])==Counter(flags),'paired value flags')
        products=value['products'];check((products is not None)==(q is not None and not flags and not r['book_flags']),'illicit/missing products')
        if products:
            check(len(products)==2,'paired products')
            for z,p,b,v in zip(products,(mx,lt),books,('mexc','lighter')):
                check(z['venue']==v and z['quote_asset']==('USDT' if v=='mexc' else 'USD_quote; settlement_asset_unverified'),'asset relabel')
                near(z['reference_notional_quote_units'],q*p['price'],'qP');near(z['quote_units_per_one_bp'],q*p['price']/10000,'onebp sensitivity');near(z['reference_minus_book_mid_bp'],(p['price']/b['mid']-1)*10000,'mid deviation');counts['notional_sensitivities_checked']+=1
        counts['rows_checked']+=1
    summary=read(lane/'results.json');check(summary['rows']==144 and summary['cash_confirmed']==summary['paper_days']==summary['predictive_trials']==0 and summary['observations_sha256']==digest(lane/'observations.jsonl.gz'),'summary identity')
    check(len(summary['pairs'])==24 and len({(c['symbol'],c['delay_ms'],c['profile']) for c in summary['pairs']})==24,'summary controls')
    for c in summary['pairs']:
        chosen=[r for r in rows if (r['symbol'],r['access_delay_ms'],r['value_profile'])==(c['symbol'],c['delay_ms'],c['profile'])]
        cost=[r for r in chosen if r['cost'] and r['cost']['displayed_fillable'] and not r['book_flags']]
        joint=[r for r in cost if not r['value_evidence']['flags']]
        check(c['grids']==len(chosen)==6 and c['cost_rows']==len(cost) and c['joint_publication_rows']==len(joint),'summary availability')
    return {**dict(counts),'fair_request_receipts_checked':attempts,'maximum_absolute_numeric_difference':a.MAX_ERROR,'production_imports':False,'cash_never_certified':True,'scope':'causal source-typed public values/costs only; no funding settlement, fills, return or paper proof'}


def self_test():
    check(-D(10000)*D('.0001')*D(30000)*D('.0001')==D(-3),'linear official example')
    check(-D(100)*D(100)/D(10000)*D('.0001')==D('-.0001'),'inverse official example')
    q,p=D('2.5'),D('101.25');check((q*p)*D('.0001')==q*p/10000,'onebp sensitivity identity')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('lane',type=Path,nargs='?',default=ROOT/'experiments/funding_values_v1');p.add_argument('--self-test',action='store_true');args=p.parse_args();self_test()
    print(json.dumps({'self_test':'passed','market_inputs_read':False} if args.self_test else audit(args.lane),sort_keys=True,indent=2))
