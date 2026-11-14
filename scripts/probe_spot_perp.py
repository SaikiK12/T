"""R324 one-shot, public spot/perp wire compatibility capture; never trades.

Twelve seconds, two handshakes, no REST, retry, redirect or reconnect. Binary
spot messages retain original first-seen clocks. This is NOT strategy scoring.
"""
import argparse
import asyncio
import base64
from dataclasses import asdict
import gzip
import json
from pathlib import Path
import ssl
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lab.acquisition_budget import BudgetJournal,BudgetLimits
from lab.stream_quotes import FrameClock,NS
from scripts.probe_stream_quotes import no_redirect_connector,MX_WS

LANE=ROOT/'experiments/spot_perp_inputs_v1'
SYMBOLS=('BTC','WIF','SKR')
FRAME_BYTES=128*1024
CONNECTION_BYTES=4*1024**2
MESSAGES=3000
OBSERVATION_SECONDS=12
ATTEMPT_SECONDS=25
SPOT_WS='wss://wbs-api.mexc.com/ws'


def encode(value):return (json.dumps(value,sort_keys=True,allow_nan=False)+'\n').encode()


def subscriptions(venue):
    if venue=='spot':
        return [{'method':'SUBSCRIPTION','params':['spot@public.limit.depth.v3.api.pb@'+s+'USDT@5' for s in SYMBOLS]}]
    if venue=='perp':return [{'method':'sub.depth.full','param':{'symbol':s+'_USDT','limit':5}} for s in SYMBOLS]
    raise ValueError('fixed public venue required')


async def stream(venue,out,anchor,budget,stop,*,connector=None):
    connector=connector or no_redirect_connector()
    endpoint={'spot':SPOT_WS,'perp':MX_WS}[venue]
    begin=time.monotonic_ns();deadline=begin+ATTEMPT_SECONDS*NS
    r=budget.reserve(venue,CONNECTION_BYTES,ATTEMPT_SECONDS*NS,now_ns=begin,deadline_ns=deadline)
    if not r['dispatch_allowed']:raise ValueError('capture reservation already charged; no retry')
    state={'venue':venue,'endpoint':endpoint,'handshake_attempts':1,'opened_mono_ns':None,
           'closed_mono_ns':None,'accepted_payload_bytes':0,'messages':0,'subscriptions_sent':0,
           'outcome':'failure','reason':'not_started','actual_order_allowed':False,
           'transport_and_handshake_wire_bytes_known':False}
    try:
        async with connector(endpoint,ssl=ssl.create_default_context(),open_timeout=5,close_timeout=1,
                             max_size=FRAME_BYTES,max_queue=1,compression=None,ping_interval=None) as ws:
            state['opened_mono_ns']=time.monotonic_ns()
            for sub in subscriptions(venue):
                await asyncio.wait_for(ws.send(json.dumps(sub)),2)
                state['subscriptions_sent']+=1
            end=min(state['opened_mono_ns']+OBSERVATION_SECONDS*NS,deadline-2*NS)
            with (out/(venue+'.jsonl.gz')).open('xb') as raw_file, gzip.GzipFile(filename='',fileobj=raw_file,mode='wb',mtime=0) as h:
                while time.monotonic_ns()<end and not stop.is_set():
                    if state['accepted_payload_bytes']>CONNECTION_BYTES-FRAME_BYTES:
                        state['reason']='payload_headroom_stop';stop.set();break
                    try:raw=await asyncio.wait_for(ws.recv(),min(.5,max(.001,(end-time.monotonic_ns())/NS)))
                    except asyncio.TimeoutError:continue
                    # Capture both clocks BEFORE parsing, serializing or counting payloads.
                    received=FrameClock(time.time_ns(),time.monotonic_ns())
                    binary=isinstance(raw,bytes);payload=raw if binary else raw.encode('utf8')
                    size=len(payload)
                    state['accepted_payload_bytes']+=size
                    if size>FRAME_BYTES or state['accepted_payload_bytes']>CONNECTION_BYTES:
                        state['reason']='payload_bound_reached';stop.set();break
                    state['messages']+=1
                    h.write(encode({'number':state['messages'],'clock':asdict(received),'binary':binary,
                                    'payload':base64.b64encode(payload).decode('ascii') if binary else raw}))
                    if state['messages']>=MESSAGES:
                        state['reason']='message_bound_reached';stop.set();break
                else:state['reason']='window_completed' if not stop.is_set() else 'peer_stopped'
            state['outcome']='success' if state['reason']=='window_completed' else 'cancelled'
    except Exception as exc:
        # Retain a bounded reason and response status, never broad environment/account dumps.
        response=getattr(exc,'response',None)
        state['reason']=type(exc).__name__
        state['http_status']=getattr(response,'status_code',None)
        body=getattr(response,'body',None)
        if body is not None:
            state['accepted_payload_bytes']+=len(body)
            with (out/(venue+'-handshake-body.bin')).open('xb') as h:h.write(body)
        stop.set()
    finally:
        state['closed_mono_ns']=time.monotonic_ns()
        state['elapsed_ns']=state['closed_mono_ns']-begin
        budget.complete(venue,state['accepted_payload_bytes'],state['elapsed_ns'],outcome=state['outcome'])
        with (out/(venue+'-status.json')).open('xb') as h:h.write(encode(state))
    return state


async def capture(lane=LANE):
    from scripts.run_spot_perp_account import verify
    import websockets
    import websockets.http11
    verify(lane)
    if websockets.__version__!='16.0':raise ValueError('frozen websocket runtime required')
    out=lane/'evidence';out.mkdir()  # one durable attempt, including failed sessions
    budget=BudgetJournal(out/'budget.jsonl','R324/current-spot-perp/one-attempt',
                         BudgetLimits(2,2*CONNECTION_BYTES,2*ATTEMPT_SECONDS*NS,ATTEMPT_SECONDS*NS))
    # Library bounds non-101 handshake bodies; no redirect subclass prevents extra handshakes.
    old_bound=websockets.http11.MAX_BODY_SIZE;websockets.http11.MAX_BODY_SIZE=FRAME_BYTES
    anchor=FrameClock(time.time_ns(),time.monotonic_ns());stop=asyncio.Event()
    try:
        states=await asyncio.wait_for(asyncio.gather(*(stream(v,out,anchor,budget,stop) for v in ('spot','perp'))),30)
    finally:websockets.http11.MAX_BODY_SIZE=old_bound
    receipt={'registry_id':'R324','anchor':asdict(anchor),'symbols':SYMBOLS,'connections':states,
             'budget':budget.status(),'metadata_requests':0,'historical_requests_spent_unchanged':7757,
             'reported_historical_mib_spent_unchanged':'229.85','strict_prospective_strategy_days':0,
             'source_units_and_executable_quote_contract_verified':False,'actual_order_allowed':False}
    with (out/'capture.json').open('xb') as h:h.write(encode(receipt))
    from lab.prereg import sha256_file
    identity={'registry_id':'R324','sha256':{str(p.relative_to(ROOT)):sha256_file(p) for p in sorted(out.iterdir()) if p.is_file()},
              'must_commit_before_report':True,'scope':'one short raw compatibility capture, no market PnL scoring'}
    with (lane/'data_inputs.json').open('xb') as h:h.write(encode(identity))
    print('Raw inputs sealed. Commit data_inputs.json and evidence before any offline report.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.parse_args()
    asyncio.run(capture())
