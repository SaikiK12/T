"""R316 finite matched prestarted/cold fair requests on identical paired books.

Capture and raw seal precede reporting. Old R315 code/semantics stay frozen;
readiness/worker-dispatch clocks are never a market-source or effective-value time.
"""
import argparse
import asyncio
from collections import Counter
import fcntl
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from lab.depth_replay import DepthReplay  # noqa:E402
from lab.fair_workers import FairWorker,endpoint  # noqa:E402
from lab.funding_values import mexc_rest_fair,paired_values,streamed_value  # noqa:E402
from lab.stream_quotes import FrameClock,NS,SYMBOLS  # noqa:E402
from scripts import probe_funding_values as cold  # noqa:E402

depth=cold.depth
LANE=ROOT/'experiments/warm_values_v1'
GRIDS=cold.GRIDS
PROFILES=('WS_change','REST_cold','REST_warm')
sha,write=depth.sha,depth.write


def verify(lane=LANE):depth.verify(lane)
def seal(lane=LANE):return depth.seal(lane)


class Schedule:
    def __init__(self,out,anchor,workers):
        self.out,self.anchor,self.workers=out,anchor,workers
        self.records=[{'name':f'{p}_{g}_{s}','body':f'{p}_{g}_{s}.json.gz','symbol':s,'grid_second':g,
                       'profile':p,'scheduled_mono_ns':anchor.mono_ns+(g-1)*NS,
                       'read_window_end_mono_ns':anchor.mono_ns+65*NS,'attempted':False,
                       'bytes':0,'body_read_upper_bound':0,'error':'slot_not_started','url':endpoint(s)}
                      for g in GRIDS for s in SYMBOLS for p in ('REST_cold','REST_warm')]

    async def run(self):
        for g in GRIDS:
            await asyncio.sleep(max(0,(self.anchor.mono_ns+(g-1)*NS-time.monotonic_ns())/NS))
            if time.monotonic_ns()>=self.anchor.mono_ns+65*NS:break
            jobs=[]
            # Fixed interleaved dispatch: same six pairs and grid. Cold keeps
            # its original R315 spawned-worker implementation, without edits.
            for r in self.records:
                if r['grid_second']!=g:continue
                fn=cold.fair_request if r['profile']=='REST_cold' else self.workers[r['symbol']].request
                jobs.append(asyncio.to_thread(fn,r,self.out))
            await asyncio.gather(*jobs)
            if any(r.get('http_status') in cold.STOP_HTTP for r in self.records if r['attempted']):
                for r in self.records:
                    if not r['attempted']:r['error']='skipped_after_server_backoff_or_access_denial'
                break


def capture(lane=LANE):
    verify(lane);out=lane/'evidence';out.mkdir()
    begin=time.monotonic();network=depth.Metadata(out)
    meta,names,errors,connections,workers={}, {}, [], {}, {}
    schedule=None
    depth.old.LT_LOCK.parent.mkdir(parents=True,exist_ok=True)
    with depth.old.LT_LOCK.open('a') as lock:
        locked=False
        try:
            while time.monotonic()-begin<10:
                try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);locked=True;break
                except BlockingIOError:time.sleep(.05)
            if not locked:raise depth.old.BudgetStop('existing public API writer held lock')
            network.start=time.monotonic()
            listing=network.get('lighter_metadata',depth.old.LT_HTTP+'/orderBookDetails?filter=perp')
            if network.records[-1].get('http_status') in cold.STOP_HTTP:
                raise depth.old.BudgetStop('metadata server backoff/access stop')
            for s in SYMBOLS:
                try:
                    m=network.get(s+'_mexc_metadata',depth.old.MX_HTTP+'/detail?symbol='+s+'_USDT')
                    if network.records[-1].get('http_status') in cold.STOP_HTTP:
                        raise depth.old.BudgetStop('metadata server backoff/access stop')
                    if not m or m.get('success') is not True or not listing or listing.get('code')!=200:
                        raise ValueError('metadata_failed')
                    mm=m['data']
                    if isinstance(mm,list):mm,=[x for x in mm if x['symbol']==s+'_USDT']
                    lm,=[x for x in listing['order_book_details'] if x['symbol']==s and x['market_type']=='perp']
                    if mm['symbol']!=s+'_USDT':raise ValueError('MEXC identity mismatch')
                    meta[s]={'mexc':mm,'lighter':lm};names[int(lm['market_id'])]=s
                except (ValueError,KeyError,TypeError,depth.old.BudgetStop) as exc:
                    errors.append(s+':'+type(exc).__name__+':'+str(exc))
                    if isinstance(exc,depth.old.BudgetStop):raise
            write(out/'metadata.json',{'symbols':list(SYMBOLS),'metadata':meta,'names':names,'errors':errors})
            readiness_deadline=time.monotonic()+10
            for s in SYMBOLS:workers[s]=FairWorker(s)
            for w in workers.values():w.wait_ready(readiness_deadline)
            anchor=FrameClock(time.time_ns(),time.monotonic_ns());write(out/'anchor.json',vars(anchor))
            schedule=Schedule(out,anchor,workers)
            mx=[{'method':k,'param':{'symbol':s+'_USDT',**({'limit':5} if k=='sub.depth.full' else {})}}
                for s in SYMBOLS if s in meta for k in ('sub.depth.full','sub.fair.price')]
            lt=[{'type':'subscribe','channel':f'{k}/{m}'} for m in sorted(names) for k in ('order_book','market_stats')]
            connections={v:{} for v in ('mexc','lighter')}
            async def both():
                await asyncio.wait_for(asyncio.gather(depth.stream('mexc',mx,out,anchor,connections['mexc']),
                    depth.stream('lighter',lt,out,anchor,connections['lighter']),schedule.run()),
                    timeout=min(75.,max(.001,120-(time.monotonic()-begin)-3)))
            asyncio.run(both())
        except Exception as exc:errors.append(type(exc).__name__+': '+str(exc))
        finally:
            for w in workers.values():w.close()
            write(out/'warm_workers.json',{'workers':{s:w.status for s,w in workers.items()}})
            write(out/'connections.json',connections)
            write(out/'fair_receipts.json',{'records':schedule.records if schedule else []})
            write(out/'receipts.json',{'records':network.records,'requests':len(network.records),
                'response_bytes':network.total,'response_body_read_upper_bound':network.read_upper_bound,
                'duration_seconds':time.monotonic()-begin,'errors':errors})
            if locked:fcntl.flock(lock,fcntl.LOCK_UN)
    return out


def read_fairs(lane,anchor):
    records=json.loads((lane/'evidence/fair_receipts.json').read_text())['records']
    expected={(s,g,p) for s in SYMBOLS for g in GRIDS for p in ('REST_cold','REST_warm')}
    if records and (len(records)!=72 or {(r['symbol'],r['grid_second'],r['profile']) for r in records}!=expected):
        raise ValueError('fair fixed slot inventory')
    if sum(r['attempted'] for r in records)>72 or sum(r['body_read_upper_bound'] for r in records)>72*4096:
        raise ValueError('fair request/body-read cap')
    workers=json.loads((lane/'evidence/warm_workers.json').read_text())['workers']
    if set(workers)-set(SYMBOLS):raise ValueError('unknown prestarted worker')
    for s,w in workers.items():
        if w['symbol']!=s or w['url']!=endpoint(s) or not 0<=w['network_commands']<=6:
            raise ValueError('warm worker identity/finite command cap')
        if w['network_commands']!=sum(bool(r['attempted']) for r in records if r['profile']=='REST_warm' and r['symbol']==s):
            raise ValueError('warm command/attempt receipts disagree')
        if w['ready_received_mono_ns'] is not None and not w['started_mono_ns']<=w['ready_received_mono_ns']<=anchor.mono_ns:
            raise ValueError('worker was not readied before anchor')
        if w['ready_received_mono_ns'] is not None and not w['started_mono_ns']<=w['worker_ready_clock']['mono_ns']<=w['ready_received_mono_ns']:
            raise ValueError('child readiness/parent first-seen clocks disagree')
        if w['closed_mono_ns'] is None or w['closed_mono_ns']<w['started_mono_ns']:
            raise ValueError('worker cleanup receipt missing')
    out=[]
    for r in records:
        if r['url']!=endpoint(r['symbol']) or r['scheduled_mono_ns']!=anchor.mono_ns+(r['grid_second']-1)*NS:
            raise ValueError('fair endpoint/schedule changed')
        if not r['attempted']:
            if r['bytes'] or r['body_read_upper_bound']:raise ValueError('unattempted fair bytes')
            continue
        if not r['scheduled_mono_ns']<=r['started_mono_ns']<=r['received_mono_ns'] or r['started_mono_ns']>=anchor.mono_ns+65*NS:
            raise ValueError('fair parent dispatch/receipt window')
        raw=gzip.decompress((lane/'evidence'/r['body']).read_bytes())
        if len(raw)!=r['bytes'] or hashlib.sha256(raw).hexdigest()!=r['sha256'] or not len(raw)<=r['body_read_upper_bound']<=4096:
            raise ValueError('fair raw receipt/cap changed')
        if r['profile']=='REST_warm':
            w=workers[r['symbol']];finished=r['parent_request_finished_mono_ns'];dispatch=r.get('worker_network_started_mono_ns')
            if w['ready_received_mono_ns'] is None or w['ready_received_mono_ns']>r['started_mono_ns'] or r['received_mono_ns']>finished:
                raise ValueError('warm readiness/receipt causality')
            if r['received_mono_ns']>w['closed_mono_ns']:raise ValueError('warm receipt after worker close')
            if dispatch is not None and (not r['started_mono_ns']<=dispatch<=r['received_mono_ns'] or dispatch>=anchor.mono_ns+65*NS):
                raise ValueError('warm application GET dispatch outside window')
            if not r['error'] and dispatch is None:raise ValueError('successful warm reply without worker dispatch')
        elif r['received_mono_ns']>r['worker_cleanup_finished_mono_ns']:
            raise ValueError('cold receipt after worker cleanup')
        clock=FrameClock(r['received_utc_ns'],r['received_mono_ns'])
        try:
            if r['error']:raise ValueError(r['error'])
            packet=mexc_rest_fair(json.loads(raw),r['symbol'],clock,r['body'])
            if packet.source_time_ns>clock.utc_ns+100_000_000:raise ValueError('fair system time ahead of receipt')
        except (ValueError,KeyError,TypeError,AttributeError) as exc:
            packet=None;r={**r,'decode_error':str(exc)}
        out.append((r,packet))
    return out


def rows_for(replay,fairs):
    rows=[]
    for g in GRIDS:
        quantities={}
        for delay in (0,300):
            for s in SYMBOLS:
                target=replay.anchor.mono_ns+g*NS+delay*1_000_000
                row,books=replay.observe(s,target,quantities.get(s),allow_new_quantity=(delay==0))
                if delay==0:quantities[s]=row['quantity_base']
                for profile in PROFILES:
                    mx=streamed_value(replay.latest.get(('mexc','reference',s)))
                    lt=streamed_value(replay.latest.get(('lighter','reference',s)));selected=None
                    if profile!='WS_change':
                        selected=next(((r,p) for r,p in sorted(fairs,key=lambda x:x[0]['received_mono_ns'],reverse=True)
                            if r['symbol']==s and r['profile']==profile and r['received_mono_ns']<=target),None)
                        mx=selected[1] if selected else None
                    values=paired_values((mx,lt),row['quantity_base'],books,target,replay.anchor)
                    if row['book_flags']:values['products']=None
                    rows.append({**row,'grid_second':g,'access_delay_ms':delay,'value_profile':profile,'value_evidence':values,
                        'rest_source_receipt':selected[0]['body'] if selected else None,
                        'cash_ledger_status':'unscored: no funding-event-bound value, units, asset or exposure evidence'})
    return rows


def report(lane=LANE,out=None):
    frames,mapping,anchor,connections=depth.load_capture(lane);fairs=read_fairs(lane,anchor)
    replay=DepthReplay(frames,mapping['metadata'],{int(k):v for k,v in mapping['names'].items()},anchor,connections)
    rows=rows_for(replay,fairs);out=Path(out) if out is not None else lane;out.mkdir(exist_ok=True)
    encoded=''.join(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n' for r in rows).encode()
    depth.immutable(out/'observations.jsonl.gz',gzip.compress(encoded,mtime=0))
    summary={'registry_id':'R316','rows':len(rows),'predictive_trials':0,'cash_confirmed':0,'paper_days':0,
        'evidence_manifest_sha256':sha(lane/'evidence_inputs.json'),'observations_sha256':sha(out/'observations.jsonl.gz'),
        'scope':'matched warm/cold source-publication and quote-cost availability; no settled cash or return inference',
        'capital_usd':10000,'capital_per_venue_usd':5000,'charge_reserve_bp':[10,4],'pairs':[]}
    for s in SYMBOLS:
        for delay in (0,300):
            for profile in PROFILES:
                subset=[r for r in rows if r['symbol']==s and r['access_delay_ms']==delay and r['value_profile']==profile]
                cost=[r for r in subset if depth.eligible(r)];joint=[r for r in cost if not r['value_evidence']['flags']]
                summary['pairs'].append({'symbol':s,'delay_ms':delay,'profile':profile,'grids':len(subset),'cost_rows':len(cost),
                    'joint_publication_rows':len(joint),'value_flags':dict(Counter(f for r in subset for f in r['value_evidence']['flags'])),
                    'cost_tiers':[{'multiple':k,'n':len(joint),'round_trip_usd_range':[min(v),max(v)] if v else None}
                        for k in (1,2,3) for v in [[r['cost']['scenarios'][k-1]['round_trip_cost_usd'] for r in joint]]]})
    summary['request_profiles']=[]
    for profile in ('REST_cold','REST_warm'):
        rr=[r for r,p in fairs if r['profile']==profile]
        times=[(r['received_mono_ns']-r['started_mono_ns'])/1e6 for r in rr]
        summary['request_profiles'].append({'profile':profile,'attempts':len(rr),'successful_bodies':sum(p is not None for r,p in fairs if r['profile']==profile),
            'latency_ms':{'min':min(times),'max':max(times),'median':__import__('statistics').median(times)} if times else None,
            'own_grid_received':{str(d):sum(r['received_mono_ns']<=anchor.mono_ns+r['grid_second']*NS+d*1_000_000 for r in rr) for d in (0,300)}})
    depth.immutable(out/'results.json',(json.dumps(summary,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())
    return out/'results.json'


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('capture','seal','report'));p.add_argument('--out',type=Path)
    args=p.parse_args()
    if args.out is not None and args.command!='report':p.error('--out is report-only; collection cannot reset')
    print(report(out=args.out) if args.command=='report' else {'capture':capture,'seal':seal}[args.command]())
