"""Prestarted finite public-fair workers; readiness is never market freshness.

Only standard-library imports in this worker module. Parent wall deadlines bound
trickling bodies, unknown read tails and owned-process cleanup. A failed worker
is never replaced, retried or used to relabel a source value's clock.
"""
import gzip
import hashlib
import json
import multiprocessing
from pathlib import Path
import threading
import time
import urllib.error
import urllib.request

CAP=4096
SYMBOLS=('BTC','WIF','SKR','ROBO','MEGA','XPD')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None


def endpoint(symbol):
    if symbol not in SYMBOLS:
        raise ValueError('fixed public fair symbol required')
    return 'https://contract.mexc.com/api/v1/contract/fair_price/'+symbol+'_USDT'


def worker(url,connection,max_jobs=6):
    """One fixed URL, <=six commands; no network until a request command."""
    try:
        opener=urllib.request.build_opener(NoRedirect())
        connection.send(('ready',{'mono_ns':time.monotonic_ns(),'utc_ns':time.time_ns()}))
        for _ in range(max_jobs):
            command=connection.recv()
            if command is None:break
            seconds,start_before_ns=command
            if time.monotonic_ns()>=start_before_ns:
                connection.send(('skipped','worker_request_start_window_expired'));continue
            connection.send(('network_start',{'mono_ns':time.monotonic_ns(),'utc_ns':time.time_ns()}))
            req=urllib.request.Request(url,headers={'User-Agent':'quant-lab-R316-public/1','Accept-Encoding':'identity'})
            try:
                response=opener.open(req,timeout=seconds)
            except urllib.error.HTTPError as exc:
                response=exc
            with response:
                connection.send(('status',response.status));remaining=CAP
                while remaining:
                    chunk=response.read1(min(65536,remaining))
                    if not chunk:break
                    connection.send(('chunk',chunk));remaining-=len(chunk)
            connection.send(('done',None))
    except Exception as exc:
        try:connection.send(('error',type(exc).__name__+': '+str(exc)))
        except (EOFError,OSError):pass
    finally:connection.close()


class FairWorker:
    def __init__(self,symbol,*,target=worker,max_jobs=6):
        if not isinstance(max_jobs,int) or not 1<=max_jobs<=6:
            raise ValueError('one to six finite worker slots required')
        self.symbol,self.url,self.max_jobs=symbol,endpoint(symbol),max_jobs
        self.calls=0;self.ready=False;self.lock=threading.Lock()
        ctx=multiprocessing.get_context('spawn')
        self.parent,child=ctx.Pipe()
        self.process=ctx.Process(target=target,args=(self.url,child,max_jobs),daemon=True)
        self.status={'symbol':symbol,'url':self.url,'started_mono_ns':time.monotonic_ns(),
                     'ready_received_mono_ns':None,'closed_mono_ns':None,'network_commands':0,'error':None}
        self.process.start();child.close()

    def wait_ready(self,deadline):
        try:
            if time.monotonic()>=deadline:
                raise TimeoutError('absolute worker readiness deadline')
            if not self.parent.poll(max(0,deadline-time.monotonic())):
                raise TimeoutError('absolute worker readiness deadline')
            kind,value=self.parent.recv()
            if kind!='ready':raise ValueError('worker readiness protocol')
            self.status.update(ready_received_mono_ns=time.monotonic_ns(),ready_received_utc_ns=time.time_ns(),worker_ready_clock=value)
            self.ready=True
        except (ValueError,EOFError,OSError,TimeoutError) as exc:
            self.status['error']=type(exc).__name__+': '+str(exc);self.close()
        return self.ready

    def close(self):
        if self.status['closed_mono_ns'] is not None:return
        self.ready=False
        if self.process.pid is not None:
            if self.process.is_alive():self.process.terminate()
            self.process.join(.2)
            if self.process.is_alive():self.process.kill();self.process.join(.2)
        self.parent.close()
        self.status['closed_mono_ns']=time.monotonic_ns()

    def request(self,record,out,seconds=3.):
        if not 0<seconds<=3:raise ValueError('request deadline must be in (0,3] seconds')
        with self.lock:
            if not self.ready or not self.process.is_alive() or self.calls>=self.max_jobs:
                record['error']='prestarted_worker_unavailable_or_exhausted';return record
            if time.monotonic_ns()>=record['read_window_end_mono_ns']:
                record['error']='request_start_window_expired';return record
            self.calls+=1;self.status['network_commands']+=1
            record.update(attempted=True,started_mono_ns=time.monotonic_ns(),started_utc_ns=time.time_ns(),error=None)
            deadline=time.monotonic()+seconds
            chunks=[];total=0;complete=False;received=None
            try:
                self.parent.send((seconds,record['read_window_end_mono_ns']))
                while time.monotonic()<deadline:
                    if not self.parent.poll(max(0,deadline-time.monotonic())):break
                    kind,value=self.parent.recv()
                    if kind=='network_start':
                        record['worker_network_started_mono_ns']=value['mono_ns']
                        record['worker_network_started_utc_ns']=value['utc_ns']
                    elif kind=='status':record['http_status']=value
                    elif kind=='chunk':
                        if not isinstance(value,bytes) or len(value)>CAP-total:
                            raise ValueError('warm worker body cap/protocol')
                        chunks.append(value);total+=len(value)
                    elif kind=='done':
                        received=(time.time_ns(),time.monotonic_ns());complete=True;break
                    elif kind=='skipped':
                        # No network start was observed; conservatively consumed
                        # command still counts against the attempt allowance.
                        raise ValueError(value)
                    elif kind=='error':raise ValueError(value)
                    else:raise ValueError('unknown warm worker message')
                if not complete:raise TimeoutError('absolute warm request wall deadline or premature exit')
                if total==CAP or not 200<=record.get('http_status',0)<300:
                    raise ValueError('failed or possibly truncated fair response')
                json.loads(b''.join(chunks))
            except Exception as exc:
                record['error']=type(exc).__name__+': '+str(exc)
                if received is None:received=(time.time_ns(),time.monotonic_ns())
                if not complete:self.close()  # no replacement or stale messages on reuse
            body=b''.join(chunks)
            record.update(received_utc_ns=received[0],received_mono_ns=received[1],parent_request_finished_mono_ns=time.monotonic_ns(),
                          bytes=len(body),body_read_upper_bound=len(body) if complete else CAP,
                          sha256=hashlib.sha256(body).hexdigest())
            (Path(out)/record['body']).write_bytes(gzip.compress(body,mtime=0))
            return record
