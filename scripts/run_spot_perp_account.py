"""R324 finite spot/principal, futures/collateral and raw-wire compatibility audit."""
import argparse
import base64
from collections import Counter
from decimal import Decimal as D
import gzip
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lab import prereg
from lab.mexc_spot_wire import decode_depth
from lab.paper_account import PaperAccount,PaperEvent
from lab.spot_cash import SpotCashAccount,SpotEvent
from lab.spot_pair import snapshot
from lab.stream_quotes import FrameClock,NS

LANE=ROOT/'experiments/spot_perp_inputs_v1'
ANCHOR=FrameClock(1_800_000_000*NS,100*NS)
sha=prereg.sha256_file


def encode(v):return (json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def save(p,v):
    with p.open('xb') as h:h.write(encode(v))
def clock(t):return FrameClock(ANCHOR.utc_ns+t*NS,ANCHOR.mono_ns+t*NS)


def verify(lane=LANE,*,data=False):
    prereg.verify(lane/'PREREG.md');spec=(lane/'PREREG.md').read_text()
    for name in ('code_inputs.json','inputs.json','fixtures.json','sources.json','contract.json'):
        if sha(lane/name) not in spec:raise ValueError('unbound R324 input: '+name)
    manifest=json.loads((lane/'code_inputs.json').read_text())
    if manifest['python_version']!=list(sys.version_info[:3]):raise ValueError('Python runtime drift')
    for m in (manifest,json.loads((lane/'inputs.json').read_text())):
        for name,digest in m['sha256'].items():
            if sha(ROOT/name)!=digest:raise ValueError('input/code drift: '+name)
    # Freeze commit must exist BEFORE a collector can run, not merely a local sidecar.
    for path in (lane/'PREREG.md',lane/'PREREG.sha256',lane/'code_inputs.json'):
        relative=str(path.relative_to(ROOT))
        committed=subprocess.check_output(['git','show','HEAD:'+relative],cwd=ROOT)
        if committed!=path.read_bytes():raise ValueError('freeze not committed')
    if data:
        m=json.loads((lane/'data_inputs.json').read_text())
        expected=set(m['sha256'])
        observed={str(p.relative_to(ROOT)) for p in (lane/'evidence').iterdir() if p.is_file()}
        if expected!=observed:raise ValueError('raw inventory drift')
        for name,digest in m['sha256'].items():
            p=ROOT/name
            if sha(p)!=digest:raise ValueError('sealed raw identity drift')
            if subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)!=p.read_bytes():
                raise ValueError('raw data must be committed before statistics')
        name=str((lane/'data_inputs.json').relative_to(ROOT))
        if subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)!=(lane/'data_inputs.json').read_bytes():
            raise ValueError('data identity must be committed')
    return json.loads((lane/'fixtures.json').read_text())


def account_path(case,k,fixtures,out):
    name=case['id']+'-'+str(k);folder=out/'model_journals';folder.mkdir(exist_ok=True)
    sj,pj=folder/(name+'-spot.jsonl'),folder/(name+'-perp.jsonl')
    cap=fixtures['capital_per_wallet']
    s=SpotCashAccount('mexc-spot-model','USDT',cap,{'BTCUSDT':'BTC'},ANCHOR,journal_path=sj)
    p=PaperAccount({('mexc-perp-model','USDT'):cap},ANCHOR,journal_path=pj)
    h=D(fixtures['half_spread'])*k;rate=D(fixtures['fee_rate'])*k
    S0,F0,S1,F1=map(D,case['mid_prices']);entry_spot=S0+h;exit_spot=S1-h
    entry_perp=F0-h;exit_perp=F1+h
    asset=case['entry_fee_asset']
    fee=(None if asset=='UNKNOWN' else D(fixtures['base_fee'])*k if asset=='BTC'
         else D(fixtures['third_fee'])*k if asset=='MX' else entry_spot*rate)
    e=SpotEvent(name+'-spot-open','fill','BTCUSDT',clock(1).utc_ns,clock(1),'invented-spot-fill',
                quantity='1',price=entry_spot,fee_amount=fee,fee_asset=None if asset=='UNKNOWN' else asset)
    states=[s.post(e,clock(1).mono_ns)]
    q=D(1)-(fee if asset=='BTC' else D(0)) if case['hedge']=='net_owned' else D(1)
    def perp(eid,kind,t,**kw):
        event=PaperEvent(name+'-'+eid,kind,'mexc-perp-model','USDT','BTC_USDT',clock(t).utc_ns,
                         clock(t),'invented-perp-fill-or-normalized-funding',**kw)
        states.append(p.post(event,clock(t).mono_ns))
    perp('perp-open','fill',1,quantity=-q,price=entry_perp,fee=q*entry_perp*rate)
    at_open=snapshot(s,p,'BTCUSDT','BTC_USDT',clock(1).mono_ns)
    payment=None if case['funding_quote_per_base'] is None else q*D(case['funding_quote_per_base'])
    perp('funding','funding',2,amount=payment)
    # Supplied settled cash is hypothetical, never Funding.value or a predicted rate.
    base=s.holdings['BTCUSDT']
    close=SpotEvent(name+'-spot-close','fill','BTCUSDT',clock(3).utc_ns,clock(3),'invented-spot-close',
                    quantity=-D(base.numerator)/D(base.denominator),price=exit_spot,
                    fee_amount=(D(base.numerator)/D(base.denominator))*exit_spot*rate,fee_asset='USDT')
    states.append(s.post(close,clock(3).mono_ns))
    perp('perp-close','fill',3,quantity=q,price=exit_perp,fee=q*exit_perp*rate)
    result=snapshot(s,p,'BTCUSDT','BTC_USDT',clock(4).mono_ns)
    reopened=snapshot(SpotCashAccount('mexc-spot-model','USDT',cap,{'BTCUSDT':'BTC'},ANCHOR,journal_path=sj),
                      PaperAccount({('mexc-perp-model','USDT'):cap},ANCHOR,journal_path=pj),
                      'BTCUSDT','BTC_USDT',clock(4).mono_ns)
    if result!=reopened:raise ValueError('spot/perp append-only replay mismatch')
    return {'id':case['id'],'cost_multiple':k,'quantity_perp':str(q),'open_account':at_open,
            'final_account':result,'attempt_states':states,'reopened_identical':True,
            'cash_control_net_pnl':'0','funding_quote_known_component':str(p.funding[('mexc-perp-model','USDT')]),
            'journals':{str(path.relative_to(out)):sha(path) for path in (sj,pj)},
            'scope':'invented finite accounting case, not a forecast or market outcome'}


def wire_rows(lane):
    rows=[];capture=json.loads((lane/'evidence/capture.json').read_text())
    for venue in ('spot','perp'):
        path=lane/'evidence'/(venue+'.jsonl.gz')
        if not path.exists():continue
        for line in gzip.decompress(path.read_bytes()).splitlines():
            f=json.loads(line);r={'venue':venue,'number':f['number'],'clock':f['clock']}
            if venue=='spot' and f['binary']:
                try:r['depth']=decode_depth(base64.b64decode(f['payload'],validate=True),FrameClock(**f['clock']))
                except (ValueError,UnicodeError) as exc:r['decode_failure']=str(exc)
            else:
                # Reuse supplied perp raw stream shapes without certifying unseen metadata.
                try:
                    payload=json.loads(f['payload']);r['channel']=payload.get('channel')
                    r['symbol']=payload.get('symbol');r['source_ts_raw']=payload.get('ts')
                    body=payload.get('data')
                    if (venue=='perp' and r['channel']=='push.depth.full' and isinstance(body,dict)
                            and all(isinstance(body.get(k),list) for k in ('bids','asks'))):
                        r['structural_perp_depth']=True
                        r['bids_received']=len(body.get('bids',[]));r['asks_received']=len(body.get('asks',[]))
                    else:r['control_message']=True
                except (ValueError,TypeError,AttributeError):r['decode_failure']='not a supported structural JSON message'
            r['executable_quote_eligible']=False
            rows.append(r)
    return capture,rows


def report(lane=LANE,out=None):
    fixtures=verify(lane,data=True)
    out=Path(out) if out is not None else lane
    if (out/'results.json').exists() or (out/'model_journals').exists():raise ValueError('existing result retained; use fresh --out')
    out.mkdir(parents=True,exist_ok=True)
    accounts=[account_path(case,k,fixtures,out) for case in fixtures['cases'] for k in fixtures['cost_multiples']]
    capture,wire=wire_rows(lane)
    counts=dict(account_paths=len(accounts),model_journals=2*len(accounts),wire_messages=len(wire))
    payload={'accounts':accounts,'wire':wire}
    with (out/'observations.json.gz').open('xb') as h:h.write(gzip.compress(encode(payload),mtime=0))
    packed={str(p.relative_to(out)):p.read_text() for p in sorted((out/'model_journals').iterdir())}
    with (out/'journals.json.gz').open('xb') as h:h.write(gzip.compress(encode(packed),mtime=0))
    symbols={}
    for symbol in fixtures['symbols']:
        spot=[r for r in wire if r['venue']=='spot' and r.get('depth',{}).get('subscription_symbol')==symbol+'USDT']
        perp=[r for r in wire if r.get('structural_perp_depth') and r.get('symbol')==symbol+'_USDT']
        symbols[symbol]={'spot_structural_depth_packets':len(spot),'perp_structural_depth_packets':len(perp),
                         'both_streams_received':bool(spot and perp),'executable_synchronized_pairs':0,
                         'net_market_return':None,'market_availability_certified':False}
    summary={'registry_id':'R324','verdict':'PARTIAL','counts':counts,'symbols':symbols,
             'structural_spot_packets':sum('depth' in r for r in wire),
             'structural_perp_packets':sum(bool(r.get('structural_perp_depth')) for r in wire),
             'decode_failures':dict(Counter(r['decode_failure'] for r in wire if 'decode_failure' in r)),
             'capture':capture,'cost_sensitivity':[{'multiple':k,'market_net_return':None,
              'conditional_account_cases':[{'id':a['id'],'net':a['final_account']['combined_net_pnl']} for a in accounts if a['cost_multiple']==k]} for k in fixtures['cost_multiples']],
             'output_sha256':{name:sha(out/name) for name in ('observations.json.gz','journals.json.gz')},
             'data_inputs_sha256':sha(lane/'data_inputs.json'),'code_inputs_sha256':sha(lane/'code_inputs.json'),
             'predictive_strategy_trials':0,'new_prospective_paper_days':0,'actual_order_allowed':False,
             'market_net_return':None,'old_market_results_reclassified':False,
             'unresolved':['spot_source_timestamp_unit','spot_quantity_asset_and_snapshot_semantics',
                           'spot_and_perp_lot_tick_minimum_status_metadata','actual_owner_fees_and_fee_asset',
                           'synchronized_executable_exit_depth','actual_funding_event_cash_and_reference_notional',
                           'calibrated_positive_expectancy_and_prospective_protocol']}
    verify(lane,data=True);save(out/'results.json',summary)
    return out/'results.json'


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path)
    print(report(out=p.parse_args().out))
