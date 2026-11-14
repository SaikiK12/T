"""Durable conservative acquisition reservations; no network or permission grant.

Reserve before dispatch, and dispatch only when ``dispatch_allowed`` is true.
Every reservation remains charged after failure, process death or completion;
uncertain tails are never refunded. A journal is one accumulated scope, not a
per-run allowance. Reported historical MiB must not become invented exact bytes.
"""
from contextlib import contextmanager
from dataclasses import asdict, dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time


class BudgetError(ValueError):
    pass


def _integer(value, name):
    if type(value) is not int or value < 0:
        raise BudgetError(name+' must be a nonnegative integer')
    return value


def _text(value, name):
    if not isinstance(value,str) or not value or len(value)>256:
        raise BudgetError(name+' must be nonempty bounded text')
    return value


def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def _read_records(handle):
    handle.seek(0);raw=handle.read()
    if raw and not raw.endswith('\n'):
        raise BudgetError('incomplete journal tail; no repair or dispatch authorized')
    records=[];previous='0'*64
    for sequence,line in enumerate(raw.splitlines()):
        try:
            row=json.loads(line);digest=row.pop('sha256')
            if row['sequence']!=sequence or row['previous_sha256']!=previous or hashlib.sha256(_canonical(row).encode()).hexdigest()!=digest:
                raise ValueError('chain mismatch')
        except (ValueError,TypeError,KeyError) as exc:
            raise BudgetError('invalid append-only journal') from exc
        row['sha256']=digest;records.append(row);previous=digest
    return records


def _append_record(handle,records,event):
    row={'sequence':len(records),'previous_sha256':records[-1]['sha256'] if records else '0'*64,'event':event}
    row['sha256']=hashlib.sha256(_canonical(row).encode()).hexdigest()
    handle.seek(0,os.SEEK_END);handle.write(_canonical(row)+'\n');handle.flush();os.fsync(handle.fileno())
    records.append(row)
    return row


@contextmanager
def _locked(path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(path,os.O_RDWR|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'a+',encoding='utf8') as handle:
        deadline=time.monotonic()+5
        while True:
            try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB);break
            except BlockingIOError:
                if time.monotonic()>=deadline:raise BudgetError('budget journal writer lock deadline exceeded')
                time.sleep(.01)
        try:yield handle
        finally:fcntl.flock(handle,fcntl.LOCK_UN)


@dataclass(frozen=True)
class BudgetLimits:
    max_requests:int
    max_body_bytes:int
    max_reserved_duration_ns:int
    max_attempt_duration_ns:int

    def __post_init__(self):
        for k,v in asdict(self).items():_integer(v,k)


def historical_baseline():
    """User-reported accumulated spend; exact bytes/remaining grant unverified."""
    return {'requests_used':7757,'body_bytes_upper_bound':None,'reserved_duration_ns':0,
            'reported_response_mib':'229.85','exact_body_bytes_known':False,
            'source':'owner-reported single R310/R311 accumulated allowance; not a renewed grant'}


class BudgetJournal:
    def __init__(self,path,scope,limits,*,baseline=None):
        if not isinstance(limits,BudgetLimits):raise BudgetError('typed finite limits required')
        base=dict({'requests_used':0,'body_bytes_upper_bound':0,'reserved_duration_ns':0} if baseline is None else baseline)
        allowed={'requests_used','body_bytes_upper_bound','reserved_duration_ns','reported_response_mib','exact_body_bytes_known','source'}
        if set(base)-allowed:raise BudgetError('unknown budget baseline fields')
        for k in ('requests_used','reserved_duration_ns'):_integer(base.get(k),k)
        if base.get('body_bytes_upper_bound') is not None:_integer(base['body_bytes_upper_bound'],'baseline bytes')
        if 'exact_body_bytes_known' in base and (type(base['exact_body_bytes_known']) is not bool or base['exact_body_bytes_known'] and base.get('body_bytes_upper_bound') is None):
            raise BudgetError('exact-byte flag requires explicit byte count')
        if base['requests_used']>limits.max_requests or (base.get('body_bytes_upper_bound') or 0)>limits.max_body_bytes or base['reserved_duration_ns']>limits.max_reserved_duration_ns:
            raise BudgetError('baseline exceeds finite scope')
        self.path=Path(path);self.config={'kind':'config','scope':_text(scope,'scope'),'limits':asdict(limits),'baseline':base}
        with _locked(self.path) as h:
            rows=_read_records(h)
            if not rows:_append_record(h,rows,self.config)
            elif rows[0]['event']!=self.config:raise BudgetError('existing scope/limits/baseline cannot be reset or changed')
            self._state(rows)

    def _state(self,rows):
        if not rows or rows[0]['event']!=self.config:raise BudgetError('journal scope drift')
        base=self.config['baseline'];requests=base['requests_used'];size=base.get('body_bytes_upper_bound');duration=base['reserved_duration_ns']
        reservations={};completions={};violations=[];last_time=0
        for row in rows[1:]:
            e=row['event'];op=e['operation_id']
            if e['kind']=='reserve':
                if op in reservations:raise BudgetError('duplicate reservation in journal')
                reservations[op]=e;requests+=1
                if size is not None:size+=e['body_limit_bytes']
                duration+=e['duration_ns'];last_time=max(last_time,e['issued_at_ns'])
            elif e['kind']=='complete':
                if op not in reservations or op in completions:raise BudgetError('completion inventory mismatch')
                completions[op]=e;r=reservations[op]
                if e['actual_bytes']>r['body_limit_bytes']:
                    if size is not None:size+=e['actual_bytes']-r['body_limit_bytes']
                    violations.append(op+':body_reservation_exceeded')
                if e['elapsed_ns']>r['duration_ns']:
                    duration+=e['elapsed_ns']-r['duration_ns'];violations.append(op+':duration_reservation_exceeded')
            else:raise BudgetError('unknown journal event')
        limits=self.config['limits']
        if requests>limits['max_requests'] or size is not None and size>limits['max_body_bytes'] or duration>limits['max_reserved_duration_ns']:
            violations.append('accumulated_limit_exceeded')
        return {'scope':self.config['scope'],'requests_charged':requests,'body_bytes_charged_upper_bound':size,
                'duration_ns_charged_upper_bound':duration,'pending':sorted(set(reservations)-set(completions)),
                'reservations':reservations,'completions':completions,'violations':violations,'last_time_ns':last_time}

    def status(self):
        with _locked(self.path) as h:s=self._state(_read_records(h))
        limits=self.config['limits']
        reasons=[]
        if s['violations']:reasons.append('recorded_overrun')
        if s['requests_charged']>=limits['max_requests']:reasons.append('request_allowance_exhausted')
        if s['body_bytes_charged_upper_bound'] is None:reasons.append('baseline_body_bytes_unknown')
        elif s['body_bytes_charged_upper_bound']>=limits['max_body_bytes']:reasons.append('body_allowance_exhausted')
        if s['duration_ns_charged_upper_bound']>=limits['max_reserved_duration_ns']:reasons.append('duration_allowance_exhausted')
        if limits['max_attempt_duration_ns']==0:reasons.append('attempt_duration_unavailable')
        return {k:v for k,v in s.items() if k not in ('reservations','completions','last_time_ns')}|{
            'limits':dict(limits),'baseline':dict(self.config['baseline']),
            'remaining_requests':max(0,limits['max_requests']-s['requests_charged']),
            'remaining_body_bytes':None if s['body_bytes_charged_upper_bound'] is None else max(0,limits['max_body_bytes']-s['body_bytes_charged_upper_bound']),
            'new_dispatch_blocked':bool(reasons),'dispatch_block_reasons':reasons,
            'authorization_verified':False}

    def reserve(self,operation_id,body_limit_bytes,duration_ns,*,now_ns,deadline_ns):
        op=_text(operation_id,'operation_id')
        for k,v in [('body_limit_bytes',body_limit_bytes),('duration_ns',duration_ns),('now_ns',now_ns),('deadline_ns',deadline_ns)]:_integer(v,k)
        if body_limit_bytes==0:raise BudgetError('positive body reservation required')
        if duration_ns==0 or duration_ns>self.config['limits']['max_attempt_duration_ns']:
            raise BudgetError('attempt duration outside finite scope')
        wanted={'kind':'reserve','operation_id':op,'body_limit_bytes':body_limit_bytes,'duration_ns':duration_ns,'deadline_ns':deadline_ns}
        with _locked(self.path) as h:
            rows=_read_records(h);s=self._state(rows);old=s['reservations'].get(op)
            if old is not None:
                if {k:old[k] for k in wanted}!=wanted:raise BudgetError('conflicting operation replay')
                return {'dispatch_allowed':False,'replayed':True,'reservation':dict(old)}
            if s['violations'] or s['body_bytes_charged_upper_bound'] is None:
                raise BudgetError('overrun or unknown byte baseline blocks new dispatch')
            limits=self.config['limits']
            if now_ns<s['last_time_ns'] or now_ns+duration_ns>deadline_ns:
                raise BudgetError('clock regression or request deadline exceeded')
            if s['requests_charged']+1>limits['max_requests'] or s['body_bytes_charged_upper_bound']+body_limit_bytes>limits['max_body_bytes'] or s['duration_ns_charged_upper_bound']+duration_ns>limits['max_reserved_duration_ns']:
                raise BudgetError('accumulated request/byte/duration limit exhausted')
            event={**wanted,'issued_at_ns':now_ns};_append_record(h,rows,event)
            return {'dispatch_allowed':True,'replayed':False,'reservation':dict(event)}

    def complete(self,operation_id,actual_bytes,elapsed_ns,*,outcome):
        op=_text(operation_id,'operation_id');_integer(actual_bytes,'actual_bytes');_integer(elapsed_ns,'elapsed_ns')
        if outcome not in ('success','failure','timeout','cancelled'):raise BudgetError('explicit bounded completion outcome required')
        event={'kind':'complete','operation_id':op,'actual_bytes':actual_bytes,'elapsed_ns':elapsed_ns,'outcome':outcome}
        with _locked(self.path) as h:
            rows=_read_records(h);s=self._state(rows)
            if op not in s['reservations']:raise BudgetError('completion has no reserved attempt')
            if op in s['completions']:
                if s['completions'][op]!=event:raise BudgetError('conflicting completion replay')
                return {'replayed':True,'receipt':dict(event),'violations':s['violations']}
            _append_record(h,rows,event);s=self._state(rows)
            return {'replayed':False,'receipt':dict(event),'violations':s['violations']}
