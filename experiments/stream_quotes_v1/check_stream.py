"""Independent raw-frame/Decimal accounting audit; imports no production replay or cost code."""
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path

LANE=Path(__file__).resolve().parent
D=lambda x:Decimal(str(x))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    identity=json.loads((LANE/'evidence_inputs.json').read_text())
    for p,h in identity['sha256'].items():assert sha(LANE/p)==h,p
    summary=json.loads((LANE/'results.json').read_text())
    assert summary['evidence_manifest_sha256']==sha(LANE/'evidence_inputs.json')
    assert summary['observations_sha256']==sha(LANE/'observations.jsonl.gz')
    with gzip.open(LANE/'observations.jsonl.gz','rt') as f:rows=[json.loads(line) for line in f]
    assert len(rows)==144 and summary['predictive_trials']==0
    expected={(s,t,k) for s in ('BTC','WIF','SKR','ROBO','MEGA','XPD') for t in range(5,61,5) for k in (0,300)}
    assert {(r['symbol'],r['grid_second'],r['access_delay_ms']) for r in rows}==expected
    for r in rows:assert r['execution_ready'] is False
    anchor=json.loads((LANE/'evidence/anchor.json').read_text()) if (LANE/'evidence/anchor.json').exists() else {'utc_ns':0,'mono_ns':0}
    md=json.loads((LANE/'evidence/metadata.json').read_text())['metadata'] if (LANE/'evidence/metadata.json').exists() else {}
    raw={};frame_counts={}
    for venue in ('mexc','lighter'):
        path=LANE/'evidence'/(venue+'.jsonl.gz')
        count=0
        if path.exists():
            with gzip.open(path,'rt') as f:
                for line in f:
                    event=json.loads(line);raw[venue,event['mono_ns']]=event;count+=1
        frame_counts[venue]=count
    errors=[];notionals=0;causal_clocks=0;cost_rows=0

    def cash(side,quantity,reverse=False):
        left,value=quantity,D(0)
        for price,size in sorted(side,key=lambda x:x[0],reverse=reverse):
            take=min(left,size);value+=take*price;left-=take
            if not left:return value
        raise AssertionError('audit encountered insufficient displayed depth')

    for r in rows:
        target=anchor['mono_ns']+r['grid_second']*10**9+r['access_delay_ms']*10**6
        assert r['target_mono_ns']==target
        for receive in r.get('book_receive_times_ns',[]):
            if receive is not None:assert receive<=target;causal_clocks+=1
        if r['access_delay_ms']==300:
            before=next(x for x in rows if x['symbol']==r['symbol'] and x['grid_second']==r['grid_second'] and x['access_delay_ms']==0)
            if r['quantity_base'] is not None:assert r['quantity_base']==before['quantity_base']
        if not r['cost'] or not r['cost']['displayed_fillable'] or r['book_flags']:continue
        symbol=r['symbol'];q=D(r['quantity_base']);pair=md[symbol]
        q_m=D(pair['mexc']['contractSize'])*D(pair['mexc']['volUnit'])
        q_l=D(10)**(-pair['lighter']['supported_size_decimals'])
        assert q%q_m==q%q_l==0
        mx,lt=[raw[v,t] for v,t in zip(('mexc','lighter'),r['book_receive_times_ns'])]
        m=json.loads(mx['raw'],parse_float=Decimal)['data']
        l=json.loads(lt['raw'],parse_float=Decimal)['ticker']
        source=[int(m['cts'])*10**6,int(l['last_updated_at'])*1000]
        assert source==r['book_source_times_ns']
        utc_now=anchor['utc_ns']+target-anchor['mono_ns']
        for event,stamp in zip((mx,lt),source):
            assert 0<=target-event['mono_ns']<=10**9
            assert -100_000_000<=utc_now-stamp<=2*10**9
            assert abs((event['utc_ns']-anchor['utc_ns'])-(event['mono_ns']-anchor['mono_ns']))<=50_000_000
        assert abs(source[0]-source[1])<=10**9
        assert abs(mx['mono_ns']-lt['mono_ns'])<=10**9
        size=D(pair['mexc']['contractSize']);limit=pair['mexc']['marketOrderMaxLevel']
        ma=[(D(x[0]),D(x[1])*size) for x in m['asks'][:limit]]
        mb=[(D(x[0]),D(x[1])*size) for x in m['bids'][:limit]]
        la=[(D(l['a']['price']),D(l['a']['size']))];lb=[(D(l['b']['price']),D(l['b']['size']))]
        m_buy,m_sell,l_buy,l_sell=cash(ma,q),cash(mb,q,True),cash(la,q),cash(lb,q,True)
        crossing=m_buy-m_sell+l_buy-l_sell
        reserve=(m_buy+m_sell)*D('.001')+(l_buy+l_sell)*D('.0004')
        for tier in r['cost']['scenarios']:
            error=abs((crossing+reserve)*D(tier['multiple'])-D(tier['round_trip_cost_usd']))
            assert error<D('1e-8');errors.append(error)
        for ref in r['references']:
            if ref.get('notional_usd') is not None:
                assert abs(q*D(ref['price'])-D(ref['notional_usd']))<D('1e-8');notionals+=1
        cost_rows+=1
    out={'scope':'independent accounting and causal-clock audit; no signal or fill claim',
         'summary_sha256':sha(LANE/'results.json'),'audit_code_sha256':sha(Path(__file__)),
         'retained_rows':len(rows),'raw_frames':frame_counts,'causal_book_receipts_checked':causal_clocks,
         'cost_rows_checked':cost_rows,'cost_scenarios_checked':len(errors),
         'max_cost_error_usd':str(max(errors,default=D(0))),'observed_notionals_checked':notionals}
    encoded=json.dumps(out,sort_keys=True,indent=2)+'\n';path=LANE/'audit.json'
    if path.exists():assert path.read_text()==encoded
    else:path.write_text(encoded)
    print(encoded,end='')


if __name__=='__main__':main()
