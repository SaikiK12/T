"""Independent R314 raw-frame audit: standard library only; no production imports."""
import argparse
from collections import Counter
from decimal import Decimal as D, ROUND_FLOOR
from fractions import Fraction
import gzip
import hashlib
import json
from math import lcm
from pathlib import Path

NS = 10**9
SYMBOLS = ('BTC','WIF','SKR','ROBO','MEGA','XPD')
COUNTS = Counter()
MAX_ERROR = 0.


def check(test, message):
    if not test:
        raise AssertionError(message)


def near(observed, exact, message):
    global MAX_ERROR
    error = abs(float(observed)-float(exact))
    MAX_ERROR = max(MAX_ERROR,error)
    check(error <= max(1e-8,abs(float(exact))*1e-10),message+f': {observed} != {exact}')


def dec(value, zero=False):
    check(not isinstance(value,bool),'boolean numeric field')
    x = D(str(value));check(x.is_finite() and (x >= 0 if zero else x > 0),'invalid decimal')
    return x


def uint(x):
    check(type(x) is int and x >= 0,'invalid unsigned integer');return x


def source(x, scale):
    t = uint(x)*scale
    check(1577836800*NS <= t <= 4102444800*NS,'source epoch/unit');return t


def levels(rows, deleting=False):
    check(isinstance(rows,list) and len(rows) <= 10000,'level batch bound')
    out = {}
    for x in rows:
        p,q = dec(x['price']),dec(x['size'],zero=deleting)
        check(p not in out,'canonical duplicate price');out[p] = q
    return out


def book(bids, asks, frame, stamp, version):
    bids = tuple(sorted(bids.items(),reverse=True));asks = tuple(sorted(asks.items()))
    check(bids and asks and bids[0][0] < asks[0][0],'empty/crossed exported book')
    return {'bids':bids,'asks':asks,'receive':frame['mono_ns'],'utc':frame['utc_ns'],
            'source':stamp,'version':version,'mid':(bids[0][0]+asks[0][0])/2}


class OrderBook:
    def __init__(self, market):
        self.market = market;self.status = 'snapshot_required';self.bids = {};self.asks = {}
        self.nonce = self.offset = self.stamp = self.last = self.liquidity = self.fp = None

    def consume(self,p,f):
        try:
            check(isinstance(p,dict),'nonobject')
            t,ch = p.get('type'),p.get('channel')
            check(t not in ('shutdown','error'),'shutdown/error')
            if t in ('ping','pong','connected'):return
            if t not in ('subscribed/order_book','update/order_book','unsubscribed/order_book'):
                check(isinstance(t,str) and t and isinstance(ch,str) and ch != f'order_book:{self.market}','bad dispatch');return
            check(isinstance(ch,str) and ch.startswith('order_book:') and ch[11:].isascii() and ch[11:].isdigit(),'bad channel')
            if ch != f'order_book:{self.market}':return
            check(t != 'unsubscribed/order_book','unsubscribed')
            if self.status == 'invalid':return
            d = p['order_book'];check(uint(d['code']) == 0,'service code')
            n,o,s = uint(d['nonce']),uint(d['offset']),uint(d['last_updated_at']);source(s,1000)
            begin = uint(d['begin_nonce']) if 'begin_nonce' in d else None
            if 'offset' in p:check(uint(p['offset']) == o,'duplicate offset')
            if p.get('last_updated_at') is not None:check(uint(p['last_updated_at']) == s,'duplicate timestamp')
            b,a = levels(d['bids'],True),levels(d['asks'],True)
            fp = (t,begin,n,o,s,tuple(sorted(b.items())),tuple(sorted(a.items())))
            if fp == self.fp:return
            if self.last:check(f['mono_ns'] >= self.last['mono_ns'],'receive regression')
            initial = t == 'subscribed/order_book'
            if initial:
                check(self.status == 'snapshot_required','replacement without reset')
                nb,na = ({p:q for p,q in side.items() if q} for side in (b,a))
            else:
                check(self.status == 'ready' and begin == self.nonce,'chain gap')
                check(n >= begin and o > self.offset and s >= self.stamp,'metadata regression')
                nb,na = self.bids.copy(),self.asks.copy()
                for side,patch in ((nb,b),(na,a)):
                    for price,size in patch.items():
                        if size:side[price] = size
                        else:side.pop(price,None)
            check(max(len(nb),len(na)) <= 10000,'state bound')
            check(not nb or not na or max(nb) < min(na),'crossed state')
            changed = initial or nb != self.bids or na != self.asks
            check(initial or n != begin or not changed,'mutation without nonce')
            self.bids,self.asks,self.nonce,self.offset,self.stamp,self.last,self.fp = nb,na,n,o,s,f,fp
            if changed:self.liquidity = (f,s)
            self.status = 'ready'
        except (AssertionError,KeyError,TypeError,ValueError,ArithmeticError):self.status = 'invalid'

    def export(self,target,anchor):
        if self.status != 'ready' or not self.liquidity:return None
        f,s = self.liquidity
        if self.last['mono_ns'] > target or abs((self.last['utc_ns']-anchor['utc_ns'])-(self.last['mono_ns']-anchor['mono_ns'])) > 50000000:return None
        try:return book(self.bids,self.asks,f,source(s,1000),self.nonce)
        except AssertionError:return None


def fresh(b,target,anchor):
    return (b is not None and 0 <= target-b['receive'] <= NS and
            -100000000 <= anchor['utc_ns']+target-anchor['mono_ns']-b['source'] <= 2*NS and
            abs((b['utc']-anchor['utc_ns'])-(b['receive']-anchor['mono_ns'])) <= 50000000)


def sweep(side,q):
    cash = D(0)
    for p,size in side:
        take = min(q,size);cash += take*p;q -= take
        if q == 0:return cash
    return None


def economics(m,l,q):
    fills = [sweep(side,q) for b in (m,l) for side in (b['asks'],b['bids'])]
    cap = min(sum(v for _,v in side) for b in (m,l) for side in (b['bids'],b['asks']))
    if None in fills:return {'displayed_fillable':False,'capacity':cap}
    mb,ms,lb,ls = fills;cross = mb-ms+lb-ls;fee = (mb+ms)/1000+(lb+ls)*D('.0004')
    return {'displayed_fillable':True,'capacity':cap,'crossing':cross,'fee':fee,'cost':cross+fee,
            'leg':q*(m['mid']+l['mid'])/2,'notionals':[q*m['mid'],q*l['mid']],
            'long_mexc':mb-q*m['mid']+q*l['mid']-ls+mb/1000+ls*D('.0004'),
            'long_lighter':lb-q*l['mid']+q*m['mid']-ms+lb*D('.0004')+ms/1000,'fills':fills}


def audit(lane):
    lane = Path(lane).resolve();root = lane.parents[1]
    digest = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    read = lambda p:json.loads(p.read_text())
    check(digest(lane/'PREREG.md') == (lane/'PREREG.sha256').read_text().strip(),'prereg hash')
    check(digest(lane/'code_inputs.json') in (lane/'PREREG.md').read_text(),'unbound code manifest')
    for p,h in read(lane/'code_inputs.json')['sha256'].items():check(digest(root/p) == h,'code drift '+p)
    identity = read(lane/'evidence_inputs.json')
    check(identity['code_manifest_sha256'] == digest(lane/'code_inputs.json'),'seal code drift')
    check(set(identity['sha256']) == {str(p.relative_to(lane)) for p in (lane/'evidence').iterdir() if p.is_file()},'seal inventory')
    for p,h in identity['sha256'].items():check(digest(lane/p) == h,'input drift '+p)
    e = lane/'evidence';anchor = read(e/'anchor.json') if (e/'anchor.json').exists() else {'utc_ns':0,'mono_ns':0}
    mapping = read(e/'metadata.json') if (e/'metadata.json').exists() else {'metadata':{},'names':{}};meta = mapping['metadata']
    names = {int(k):v for k,v in mapping['names'].items()};connections = read(e/'connections.json')
    receipts = read(e/'receipts.json');check(0 <= receipts['requests'] <= 7 and 0 <= receipts['response_bytes'] <= receipts['response_body_read_upper_bound'] <= 2*1024**2 and 0 <= receipts['duration_seconds'] <= 120,'acquisition caps')
    check(len(receipts['records']) == receipts['requests'] and sum(r['bytes'] for r in receipts['records']) == receipts['response_bytes'] and sum(r['body_read_upper_bound'] for r in receipts['records']) == receipts['response_body_read_upper_bound'],'accumulated metadata counters')
    for r in receipts['records']:
        raw = gzip.decompress((e/r['body']).read_bytes());check(len(raw) == r['bytes'] and hashlib.sha256(raw).hexdigest() == r['sha256'],'metadata receipt')
        check(0 <= len(raw) <= r['body_read_upper_bound'] <= 1024**2,'per-body retained/upper cap')
        check(r['received_mono_ns'] >= r['started_mono_ns'] and (not anchor['mono_ns'] or r['received_mono_ns'] <= anchor['mono_ns']),'metadata clock')
    frames = []
    for venue in ('mexc','lighter'):
        p = e/(venue+'.jsonl.gz');ff = [json.loads(x) for x in gzip.open(p,'rt')] if p.exists() else []
        c = connections.get(venue,{'messages':0,'payload_bytes':0,'handshake_attempts':0,'opened_mono_ns':None,'unusable_mono_ns':0,'closed_mono_ns':0});check(len(ff) == c['messages'] and sum(len(f['raw'].encode()) for f in ff) == c['payload_bytes'] <= 8*1024**2,'stream counters')
        check(0 <= c['handshake_attempts'] <= 1 and len(ff) <= 20000,'stream attempts')
        for i,f in enumerate(ff,1):check(f['venue'] == venue and f['number'] == i and len(f['raw'].encode()) <= 256*1024 and c['opened_mono_ns'] <= f['mono_ns'] <= c['unusable_mono_ns'],'frame receipt')
        frames += ff
    frames.sort(key=lambda f:(f['mono_ns'],f['venue'],f['number']))
    rows = [json.loads(x) for x in gzip.open(lane/'observations.jsonl.gz','rt')]
    expected = {(s,g,d,p) for s in SYMBOLS for g in range(5,61,5) for d in (0,300) for p in ('full','top_only')}
    actual = [(r['symbol'],r['grid_second'],r['access_delay_ms'],r['depth_profile']) for r in rows]
    check(len(rows) == len(set(actual)) == 288 and set(actual) == expected,'all fixed rows retained')
    states = {s:OrderBook(m) for m,s in names.items()};latest = {};previous = {};position = 0;quantities = {};before = {}
    for r in rows:
        s,g,delay,profile = r['symbol'],r['grid_second'],r['access_delay_ms'],r['depth_profile'];target = anchor['mono_ns']+g*NS+delay*1000000
        check(r['target_mono_ns'] == target and r['execution_ready'] is False,'grid/activation')
        while position < len(frames) and frames[position]['mono_ns'] <= target:
            f = frames[position];position += 1;v = f['venue']
            try:
                p = json.loads(f['raw']);check(isinstance(p,dict),'nonobject')
            except (ValueError,AssertionError,TypeError):
                for kind in ('book','reference'):
                    for sym in SYMBOLS:latest[v,kind,sym] = None
                p = None
            if v == 'lighter':
                for state in states.values():state.consume(p,f)
            if p is None:continue
            try:
                if v == 'mexc':
                    channel = p.get('channel');sym = str(p.get('symbol','')).removesuffix('_USDT')
                    if channel not in ('push.depth.full','push.fair.price') or sym not in SYMBOLS:continue
                    kind = 'book' if channel == 'push.depth.full' else 'reference';d = p['data'];check(d.get('symbol',sym+'_USDT') == sym+'_USDT','mexc identity')
                    if kind == 'book':
                        lim = uint(meta[sym]['mexc']['marketOrderMaxLevel']);check(lim > 0,'depth limit');sides = []
                        for side in ('bids','asks'):
                            out = []
                            for x in d[side]:
                                check(len(x) == 3 and dec(x[2]) == dec(x[2]).to_integral_value(),'MEXC count')
                                price,size = dec(x[0]),dec(x[1])*dec(meta[sym]['mexc']['contractSize']);out.append((price,size))
                            selected = out[:lim];check(selected,'empty MEXC side')
                            check(all((a[0] > b[0] if side == 'bids' else a[0] < b[0]) for a,b in zip(selected,selected[1:])),'MEXC side disorder/duplicate')
                            sides.append(dict(selected))
                        b = book(*sides,f,source(d['cts'],1000000),uint(d['version']))
                    else:b = {'price':dec(d['price']),'source':source(p['ts'],1000000),'receive':f['mono_ns'],'utc':f['utc_ns']}
                else:
                    ch = p.get('channel','')
                    if not isinstance(ch,str) or not ch.startswith('market_stats:'):continue
                    prefix,market = ch.split(':');sym = names.get(int(market));kind = 'reference'
                    if sym not in SYMBOLS or p.get('type') not in ('subscribed/market_stats','update/market_stats'):continue
                    kind = 'reference';d = p['market_stats'];check(d['symbol'] == sym and d['market_id'] == int(market),'Lighter ref identity')
                    b = {'price':dec(d['index_price']),'source':source(p['timestamp'],1000000),'receive':f['mono_ns'],'utc':f['utc_ns']}
                key = (v,kind,sym);old = previous.get(key)
                if old:
                    check(b['source'] >= old['source'] and (kind != 'book' or b['version'] >= old['version']),'regression')
                    same = b['version'] == old['version'] if kind == 'book' else b['source'] == old['source']
                    if same:
                        check((b['bids'],b['asks']) == (old['bids'],old['asks']) if kind == 'book' else b['price'] == old['price'],'conflicting duplicate');continue
                latest[key] = previous[key] = b
            except (AssertionError,KeyError,TypeError,ValueError,ArithmeticError):
                if 'sym' in locals() and 'kind' in locals():latest[v,kind,sym] = None
        m = latest.get(('mexc','book',s));state = states.get(s);c = connections.get('lighter',{'unusable_mono_ns':0,'closed_mono_ns':0})
        if c.get('unusable_mono_ns',c['closed_mono_ns']) <= target:
            for st in states.values():st.status = 'invalid'
        l = state.export(target,anchor) if state else None
        if state:
            a = r['lighter_assembly'];check(a['status'] == state.status and a['nonce'] == state.nonce and a['offset'] == state.offset,'assembly metadata')
        if l and profile == 'top_only':l = {**l,'bids':l['bids'][:1],'asks':l['asks'][:1]}
        for i,b in enumerate((m,l)):
            if b:
                check(r['shown_levels'][i] == [len(b['bids']),len(b['asks'])],'shown levels')
                check(b['receive'] <= target,'future receipt');COUNTS['causal_books_checked'] += 1
        clock_ok = all(fresh(b,target,anchor) for b in (m,l))
        if clock_ok:clock_ok = abs(m['source']-l['source']) <= NS and abs(m['receive']-l['receive']) <= NS
        for v in ('mexc','lighter'):
            c = connections.get(v,{'opened_mono_ns':None,'unusable_mono_ns':0,'closed_mono_ns':0});clock_ok &= c['opened_mono_ns'] is not None and c['opened_mono_ns'] <= target < c.get('unusable_mono_ns',c['closed_mono_ns'])
        mm,lm = meta.get(s,{}).get('mexc',{}),meta.get(s,{}).get('lighter',{})
        active = mm.get('state') == 0 and mm.get('apiAllowed') is True and lm.get('status') == 'active' and lm.get('is_frozen') is False and lm.get('market_config',{}).get('force_reduce_only') is False
        q = dec(r['quantity_base']) if r['quantity_base'] is not None else None
        key = (s,g)
        if profile == 'full' and delay == 0:quantities[key] = q
        if q is not None:
            check(quantities[key] == q,'resized or future-backfilled quantity')
            step_a = Fraction(dec(mm['contractSize'])*dec(mm['volUnit']));step_b = Fraction(1,10**uint(lm['supported_size_decimals']));den = lcm(step_a.denominator,step_b.denominator)
            step = D(lcm(step_a.numerator*(den//step_a.denominator),step_b.numerator*(den//step_b.denominator)))/D(den)
            check(q % step == 0,'common lot lattice')
            if profile == 'full' and delay == 0:
                budget = D(250)/max(m['mid'],l['mid']);check(q <= budget+D('1e-10') and q+step > budget-D('1e-10'),'causal budget rounding')
        permitted = clock_ok and active and quantities.get(key) is not None
        if permitted and quantities[key]*l['bids'][0][0] < dec(lm['min_quote_amount']):permitted = False
        check((r['cost'] is not None) == permitted,'missing or illicit conditional cost')
        if r['cost']:
            check(q is not None and not any('age_' in x or 'skew_' in x for x in r['book_flags']),'cost used bad clocks')
            ex = economics(m,l,q);out = r['cost'];near(out['quantity_base'],q,'cost quantity');near(out['capital_usd'],10000,'capital');check(out['displayed_fillable'] == ex['displayed_fillable'],'shown fillability');near(out['shown_two_way_capacity_base'],ex['capacity'],'capacity')
            if ex['displayed_fillable']:
                check(not r['book_flags'],'eligible cost flags');COUNTS['eligible_rows'] += 1
                near(out['crossing_usd'],ex['crossing'],'crossing');near(out['fee_usd'],ex['fee'],'charge reserve');near(out['leg_mid_notional_usd'],ex['leg'],'leg notional')
                near(out['long_mexc_entry_cost_usd'],ex['long_mexc'],'MEXC orientation');near(out['long_lighter_entry_cost_usd'],ex['long_lighter'],'Lighter orientation')
                check(all(n <= 5000 for n in ex['notionals']),'segregated capital')
                for k,scenario in zip((1,2,3),out['scenarios']):
                    check(scenario['multiple'] == k,'cost multiple');near(scenario['round_trip_cost_usd'],k*ex['cost'],'roundtrip');near(scenario['break_even_leg_bp'],k*ex['cost']/ex['leg']*10000,'break-even');near(scenario['capital_cost_bp'],k*ex['cost'],'capital bp');COUNTS['cost_scenarios_checked'] += 1
                if profile == 'full' and delay == 0:before[key] = ex
                if profile == 'full' and delay == 300 and key in before:
                    check(r.get('entry_quote_cash_drift') is not None,'missing matched quote cash drift')
                if r.get('entry_quote_cash_drift') is not None:
                    check(profile == 'full' and delay == 300,'drift outside matched full delayed control')
                    b = before[key]['fills'];a = ex['fills'];near(r['entry_quote_cash_drift']['long_mexc_usd'],(a[0]-b[0])-(a[3]-b[3]),'MEXC cash drift');near(r['entry_quote_cash_drift']['long_lighter_usd'],(a[2]-b[2])-(a[1]-b[1]),'Lighter cash drift');COUNTS['matched_drift_rows'] += 1
        for ref in r['references']:
            b = latest.get((ref['venue'],'reference',s))
            check((ref['price'] is None) == (b is None),'reference availability')
            if b:
                near(ref['price'],b['price'],'raw reference');check(ref['source_ns'] == b['source'] and ref['receive_ns'] == b['receive'] <= target,'reference causal clock')
                if ref.get('notional_usd') is not None:check(q is not None,'notional without q');near(ref['notional_usd'],q*b['price'],'sampled notional');COUNTS['reference_notional_products_checked'] += 1
    summary = read(lane/'results.json');check(summary['rows'] == 288 and summary['predictive_trials'] == 0 and summary['observations_sha256'] == digest(lane/'observations.jsonl.gz'),'summary identity')
    return {'rows_checked':288,**dict(COUNTS),'maximum_absolute_numeric_difference':MAX_ERROR,'production_imports':False,'scope':'raw depth/causal quote-cost arithmetic only; no fills, settlement cash, alpha or prospective evidence'}


def self_test():
    m = {'mid':D(100),'bids':((D(99),D(1)),(D(98),D(3))),'asks':((D(101),D(1)),(D(102),D(3)))}
    l = {'mid':D(200),'bids':((D(199),D(1)),(D(198),D(3))),'asks':((D(201),D(1)),(D(202),D(3)))}
    ex = economics(m,l,D(2));check(ex['cost'] == D('12.72') and ex['long_mexc'] == D('6.3618') and ex['long_lighter'] == D('6.3582'),'hand cost fixture')
    check(ex['cost']/ex['leg']*10000 == D(424),'hand break-even fixture')
    top = {**l,'bids':l['bids'][:1],'asks':l['asks'][:1]};check(not economics(m,top,D(2))['displayed_fillable'],'top capacity fixture')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('lane',type=Path,nargs='?');parser.add_argument('--self-test',action='store_true');args = parser.parse_args()
    self_test()
    if args.self_test:print(json.dumps({'self_test':'passed','market_inputs_read':False}))
    else:print(json.dumps(audit(args.lane or Path(__file__).resolve().parent),sort_keys=True,indent=2))
