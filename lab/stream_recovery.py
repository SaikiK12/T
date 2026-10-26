"""Bounded explicit Lighter subscription epochs; no network/reconnect loop.

A caller saves token at subscription creation. A disconnect/gap poisons state;
only an explicitly budgeted restart plus replacement snapshot restores export.
Opening a previous journal invalidates transport state, never resumes old quotes.
"""
from dataclasses import asdict
import fcntl
import os
from pathlib import Path

from lab.acquisition_budget import _append_record,_integer,_read_records,_text
from lab.lighter_depth_state import LighterDepthState
from lab.stream_quotes import FrameClock


class RecoveryError(ValueError):
    pass


class StreamRecovery:
    def __init__(self,market_id,symbol,*,max_restarts,max_frames=20000,journal_path=None):
        _integer(max_restarts,'max_restarts');_integer(max_frames,'max_frames')
        self.state=LighterDepthState(market_id,symbol);self.max_restarts=max_restarts;self.max_frames=max_frames
        self.restarts=0;self.frames=0;self.events=[];self._handle=None;self._closed=False
        config={'kind':'config','market_id':market_id,'symbol':symbol,'max_restarts':max_restarts,'max_frames':max_frames}
        if journal_path is not None:
            path=Path(journal_path);path.parent.mkdir(parents=True,exist_ok=True)
            fd=os.open(path,os.O_RDWR|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW,0o600)
            self._handle=os.fdopen(fd,'a+',encoding='utf8')
            try:
                fcntl.flock(self._handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
                self.events=_read_records(self._handle)
                if self.events:
                    if self.events[0]['event']!=config:raise RecoveryError('existing stream scope cannot be reset')
                    allowed={'restart','frame','frame_result','frame_failed','disconnect','restart_denied','frame_denied','reopened','closed'}
                    if any(r['event'].get('kind') not in allowed for r in self.events[1:]):raise RecoveryError('unknown stream journal event')
                    self.restarts=sum(r['event']['kind']=='restart' for r in self.events)
                    self.frames=sum(r['event']['kind']=='frame' for r in self.events)
                    if self.restarts>max_restarts or self.frames>max_frames:raise RecoveryError('recorded stream budget exceeded')
                    for _ in range(self.restarts):self.state.reset()
                    self.state.invalidate('reopened transport requires explicit restart and replacement snapshot')
                    self._record({'kind':'reopened','reason':self.state.reason,'epoch':self.token})
                else:self._record(config)
            except Exception:
                self._handle.close();self._handle=None;raise
        else:self._record(config)

    @property
    def token(self):return self.state.epoch

    def _record(self,event):
        try:
            if self._handle is not None:_append_record(self._handle,self.events,event)
            else:self.events.append({'sequence':len(self.events),'event':event})
        except Exception:
            self.state.invalidate('journal write failed; source state unavailable')
            raise

    def _clock(self,clock):
        if self._closed:raise RecoveryError('closed coordinator cannot resume')
        if not isinstance(clock,FrameClock):raise RecoveryError('validated receive clock required')
        return asdict(clock)

    def disconnect(self,reason,clock):
        stamp=self._clock(clock);_text(reason,'reason');self.state.invalidate(reason)
        self._record({'kind':'disconnect','reason':reason,'clock':stamp,'epoch':self.token})
        return self.status()

    def restart(self,reason,clock):
        stamp=self._clock(clock);_text(reason,'reason')
        if self.state.status!='invalid':raise RecoveryError('explicit failure required before replacement epoch')
        if self.restarts>=self.max_restarts:
            self.state.invalidate('restart budget exhausted')
            self._record({'kind':'restart_denied','reason':self.state.reason,'clock':stamp,'epoch':self.token})
            raise RecoveryError('restart budget exhausted')
        self._record({'kind':'restart','phase':'reserved_before_epoch_reset','reason':reason,'clock':stamp,'epoch':self.token+1})
        self.restarts+=1;self.state.reset()
        return self.token

    def consume(self,payload,clock,*,epoch):
        stamp=self._clock(clock);_integer(epoch,'epoch')
        if self.frames>=self.max_frames:
            self.state.invalidate('frame budget exhausted')
            self._record({'kind':'frame_denied','epoch':self.token,'clock':stamp,'reason':self.state.reason})
            raise RecoveryError('frame budget exhausted')
        sequence=len(self.events)
        self._record({'kind':'frame','phase':'reserved_before_consume','epoch':epoch,'clock':stamp})
        self.frames+=1
        try:result=self.state.consume(payload,clock,epoch=epoch)
        except Exception as exc:
            self.state.invalidate('frame processing failed; source state unavailable')
            self._record({'kind':'frame_failed','frame_sequence':sequence,'epoch':epoch,'error_type':type(exc).__name__})
            raise
        self._record({'kind':'frame_result','frame_sequence':sequence,'epoch':epoch,'result':asdict(result)})
        return asdict(result)|{'epoch':epoch}

    def status(self):
        return {'market_id':self.state.market_id,'symbol':self.state.symbol,'epoch':self.token,
                'state':self.state.status,'reason':self.state.reason,'frames_used':self.frames,'max_frames':self.max_frames,
                'restarts_used':self.restarts,'max_restarts':self.max_restarts,'consistent_book_available':self.state.status=='ready',
                'execution_ready':False,'automatic_reconnect':False,'closed':self._closed}

    def close(self):
        if self._closed:return
        self.state.invalidate('coordinator closed')
        try:self._record({'kind':'closed','epoch':self.token})
        finally:
            self._closed=True
            if self._handle is not None:
                fcntl.flock(self._handle,fcntl.LOCK_UN);self._handle.close();self._handle=None

    def __enter__(self):return self
    def __exit__(self,*args):self.close()
