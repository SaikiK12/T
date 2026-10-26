"""One finite R325 public REST input capture; no account/history/order access."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import json
import multiprocessing
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lab.acquisition_budget import BudgetJournal,BudgetLimits
from lab.prereg import sha256_file
from lab.stream_quotes import NS
from scripts.probe_depth_quotes import metadata_worker
from scripts.probe_stream_quotes import MX_HTTP
from scripts.run_spot_perp_account import encode,save

LANE=ROOT/'experiments/spot_perp_costs_v1'
SYMBOLS=('BTC','WIF','SKR')
BODY=64*1024


class Acquisition:
    def __init__(self,out):
        self.out=Path(out);self.deadline=time.monotonic_ns()+180*NS
        self.budget=BudgetJournal(self.out/'budget.jsonl','R325/current-spot-perp-costs/one-attempt',
                                 BudgetLimits(22,2*1024**2,154*NS,7*NS))

    def reserve(self,name,url):
        utc,mono=time.time_ns(),time.monotonic_ns()
        r=self.budget.reserve(name,BODY,7*NS,now_ns=mono,deadline_ns=self.deadline)
        if not r['dispatch_allowed']:raise ValueError('one-attempt reservation already charged')
        return dict(name=name,url=url,started_utc_ns=utc,started_mono_ns=mono)

    def get_reserved(self,r):
        r=dict(r);begin=r['started_mono_ns'];deadline=begin+6*NS
        ctx=multiprocessing.get_context('spawn');receiver,sender=ctx.Pipe(duplex=False)
        process=ctx.Process(target=metadata_worker,args=(r['url'],sender,BODY,5),daemon=True)
        body=b'';complete=False;r['http_status']=None;r['error']=None
        try:
            process.start();sender.close()
            while time.monotonic_ns()<deadline:
                if not receiver.poll(max(0,(deadline-time.monotonic_ns())/NS)):break
                try:kind,payload=receiver.recv()
                except EOFError:break
                if kind=='status':r['http_status']=payload
                elif kind=='chunk':
                    if not isinstance(payload,bytes) or len(body)+len(payload)>BODY:raise ValueError('body read cap')
                    body+=payload
                elif kind=='done':complete=True;break
                elif kind=='error':r['error']=str(payload)[:512];break
                else:raise ValueError('unknown bounded-worker message')
        except Exception as exc:r['error']=type(exc).__name__
        finally:
            # Full payload first-seen clocks precede parsing, serialization and cleanup.
            r['received_utc_ns']=time.time_ns();r['received_mono_ns']=time.monotonic_ns()
            if process.pid is not None:
                if process.is_alive():process.terminate()
                process.join(.2)
                if process.is_alive():process.kill();process.join(.2)
            receiver.close();sender.close()
        r.update(complete=complete and len(body)<BODY,body_cap_reached=len(body)==BODY,
                 accepted_body_bytes=len(body),uncertain_read_upper_bound=len(body) if complete else BODY,
                 body=r['name']+'.json.gz',redirects=0,retries=0)
        raw_path=self.out/r['body']
        with raw_path.open('xb') as h:h.write(gzip.compress(body,mtime=0))
        r['body_sha256']=sha256_file(raw_path)
        elapsed=time.monotonic_ns()-begin
        self.budget.complete(r['name'],len(body),elapsed,outcome='success' if r['complete'] and r['http_status']==200 else 'failure')
        return r


def fatal(r):
    status=r['http_status']
    return not r['complete'] or status in (301,302,303,307,308,403,429,451) or status is None or status>=500


def capture(lane=LANE):
    from scripts.run_spot_costs import verify
    verify(lane)
    out=lane/'evidence';out.mkdir()  # refuses retry/reset, including failed prior attempts
    acq=Acquisition(out);records=[];stopped=False
    meta=[('spot_rules','https://api.mexc.com/api/v3/exchangeInfo?symbols='+','.join(s+'USDT' for s in SYMBOLS))]
    meta += [(s+'_perp_rules',MX_HTTP+'/detail?symbol='+s+'_USDT') for s in SYMBOLS]
    for name,url in meta:
        r=acq.get_reserved(acq.reserve(name,url));records.append(r)
        if fatal(r):stopped=True;break
    with ThreadPoolExecutor(max_workers=2) as pool:
        for sample in range(3):
            for symbol in SYMBOLS:
                if stopped:break
                jobs=[(f'{sample}_{symbol}_spot','https://api.mexc.com/api/v3/depth?symbol='+symbol+'USDT&limit=5'),
                      (f'{sample}_{symbol}_perp',MX_HTTP+'/depth/'+symbol+'_USDT?limit=5')]
                reservations=[acq.reserve(name,url) for name,url in jobs]
                futures=[pool.submit(acq.get_reserved,r) for r in reservations]
                pair=[f.result() for f in futures];records.extend(pair)
                if any(fatal(r) for r in pair) or acq.budget.status()['violations']:stopped=True
            if stopped:break
            if sample<2:time.sleep(2)
    receipt={'registry_id':'R325','records':records,'fatal_stop':stopped,'budget':acq.budget.status(),
             'fixed_symbols':SYMBOLS,'fixed_samples_per_symbol':3,'historical_requests_spent_unchanged':7757,
             'historical_reported_mib_spent_unchanged':'229.85','actual_order_allowed':False,
             'collection_scope':'CURRENT public metadata/depth only; no authenticated/history/RPC call'}
    save(out/'capture.json',receipt)
    save(lane/'data_inputs.json',{'registry_id':'R325','must_commit_before_report':True,
         'sha256':{str(p.relative_to(ROOT)):sha256_file(p) for p in sorted(out.iterdir()) if p.is_file()}})
    print('Raw finite capture sealed; commit evidence and data identity before reporting costs.')


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args();capture()
