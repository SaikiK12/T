"""One predeclared, append-only batch of public native podcast transcripts.

No audio, credentials, retry, redirect, market data, model download or implicit
budget renewal. A scope is tied to ONE shared journal and closure marker, not
to the caller's output directory. Captured text remains in ignored data/.
"""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab.acquisition_budget import BudgetJournal, BudgetLimits
from scripts.dig_podcasts import transcript_text
from scripts.podcast_corpus import NoRedirect, public_url

NS = 1_000_000_000
SCOPE_ROOT = ROOT / 'data/videos/transcript_scope_budgets'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_new(path, data):
    path = Path(path)
    with path.open('xb') as f:
        f.write(data);f.flush();os.fsync(f.fileno())


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2)+'\n').encode()


def classify_exception(exc):
    """Proxy CONNECT errors have no upstream HTTP response; keep them distinct."""
    if isinstance(exc, urllib.error.HTTPError):
        code=exc.code
        # Do not follow redirects, payment/auth/challenge/rate-limit responses.
        # A missing individual transcript (404/410) does not imply host denial.
        stop=300<=code<400 or (400<=code<500 and code not in (404,410)) or code in (502,503,504)
        return {'error_kind':'upstream_http', 'http_status':exc.code,
                'proxy_status':None, 'stop_host':stop}
    if isinstance(exc, urllib.error.URLError):
        reason=str(exc.reason)
        match=re.search(r'(?i)\btunnel connection failed:\s*(\d{3})\b',reason)
        return {'error_kind':'proxy_connect_denied' if match else 'transport_unknown',
                'http_status':None, 'proxy_status':int(match.group(1)) if match else None,
                'stop_host':True}
    return {'error_kind':'transport_unknown', 'http_status':None, 'proxy_status':None, 'stop_host':True}


def bounded_body(response, cap, parts=None):
    parts=[] if parts is None else parts;used=sum(map(len,parts))
    while used<cap:
        requested=min(65536,cap-used)
        try:part=response.read(requested)
        except http.client.IncompleteRead as exc:
            if exc.partial:parts.append(exc.partial)
            raise
        if not part:return b''.join(parts),True
        parts.append(part);used+=len(part)
        if len(part)>requested:raise ValueError('response exceeded bounded read size')
    # Reading another byte could exceed the reservation. Even an exact-cap
    # response remains incomplete unless EOF was observed inside the bound.
    return b''.join(parts),False


def validate_plan(plan):
    if plan.get('schema_version') != 1 or not re.fullmatch(r'[a-z0-9_]{1,90}',plan.get('scope_id','')):
        raise ValueError('one explicitly named finite scope required')
    if plan.get('scope_budget_directory') != 'data/videos/transcript_scope_budgets/'+plan['scope_id']:
        raise ValueError('budget directory must derive from the single scope identity')
    if plan.get('source_metadata_path')!='data/videos/corpus_20261026/metadata.json' or plan.get('catalogue_index_path')!='research/intake/podcast_episode_index_20261026.csv.gz':
        raise ValueError('the original received source catalogue identity is required')
    if not (1 <= len(plan['sources']) <= 12 and plan['limits'] == {
            'max_requests':12,'max_body_bytes':6*1024*1024,
            'max_reserved_duration_ns':120*NS,'max_attempt_duration_ns':10*NS}):
        raise ValueError('declared 12 request / 6 MiB / 120 second scope required')
    if plan['body_cap_bytes'] != 512*1024 or plan['minimum_dispatch_interval_seconds'] != 1:
        raise ValueError('fixed per-body and pacing limits required')
    seen_keys=set();seen_urls=set()
    required_code={'scripts/collect_transcript_batch.py','scripts/podcast_corpus.py',
                   'scripts/dig_podcasts.py','lab/acquisition_budget.py'}
    if not required_code <= set(plan['code_sha256']):raise ValueError('collector dependencies must be bound')
    for source in plan['sources']:
        key,url=source['key'],public_url(source['transcript'])
        if not re.fullmatch('[0-9a-f]{12}',key) or key in seen_keys or url in seen_urls:
            raise ValueError('unique exact source identities required')
        parts=urllib.parse.urlsplit(url)
        if parts.hostname.lower() not in ('transcripts.captivate.fm','api.omny.fm'):
            raise ValueError('this scope permits only the two predeclared public transcript hosts')
        if source['transcript_type'] not in ('application/srt','application/x-subrip','text/vtt','text/html','application/json'):
            raise ValueError('a recognized advertised transcript format is required')
        if parts.path.lower().endswith(('.mp3','.mp4','.wav','.m4a','.webm','.zip','.pdf')):
            raise ValueError('media or nontext source is outside scope')
        seen_keys.add(key);seen_urls.add(url)
    return plan


def verify_metadata(plan, raw):
    if digest(raw)!=plan['source_metadata_sha256']:
        raise ValueError('original private source metadata digest mismatch')
    episodes={r['key']:r for r in json.loads(raw)['episodes']}
    for source in plan['sources']:
        original=episodes.get(source['key'])
        if original is None or source['canonical_id']!=original.get('canonical_id'):
            raise ValueError('selected episode differs from original publisher metadata: '+source['key'])
        alternatives=json.loads(original.get('transcript_alternatives') or '[]')
        advertised={(x.get('url'),x.get('type')) for x in alternatives if isinstance(x,dict)}
        advertised.add((original.get('transcript'),original.get('transcript_type')))
        if (source['transcript'],source['transcript_type']) not in advertised:
            raise ValueError('selected source differs from original publisher metadata: '+source['key'])


def committed_plan(path, *, deadline=None):
    path=Path(path).resolve();relative=path.relative_to(ROOT)
    data=path.read_bytes();side=path.with_suffix('.sha256')
    if side.read_text().strip()!=digest(data):raise ValueError('source plan digest mismatch')
    plan=validate_plan(json.loads(data))
    bound={str(relative):digest(data), str(side.relative_to(ROOT)):digest(side.read_bytes()),
           plan['catalogue_index_path']:plan['catalogue_index_sha256'], **plan['code_sha256']}
    for name,expected in bound.items():
        local=(ROOT/name).read_bytes()
        if digest(local)!=expected:raise ValueError('source code/plan drift: '+name)
        timeout=5 if deadline is None else min(5,deadline-time.monotonic())
        if timeout<=0:raise TimeoutError('plan verification exceeded scope deadline')
        committed=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT,timeout=timeout)
        if committed!=local:raise ValueError('source code/plan must be committed before capture: '+name)
    verify_metadata(plan,(ROOT/plan['source_metadata_path']).read_bytes())
    return plan


def preflight(path, started):
    """Bound plan, source and Git reads before the acquisition scope begins."""
    if signal.getitimer(signal.ITIMER_REAL)!=(0.0,0.0):raise ValueError('existing process timer')
    old_handler=signal.getsignal(signal.SIGALRM)
    def expired(*_):raise TimeoutError('bounded plan verification deadline')
    remaining=started+110-time.monotonic()
    if remaining<=0:raise TimeoutError('bounded plan verification deadline')
    signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,remaining)
    try:return committed_plan(path,deadline=started+110)
    finally:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old_handler)


def authentication_or_unrecognized_html(body, mime):
    """Conservative publisher-fragment check; not a universal CAPTCHA detector."""
    if re.search(rb'''(?i)access\s+denied|permission\s+denied|not\s+authori[sz]ed|(?:authentication|subscription|payment|login)\s+required|subscribe\s+to\s+(?:read|view|continue|access)|rate\s+limit(?:ed|\s+exceeded)|too\s+many\s+requests|403\s+forbidden|^\s*forbidden\b|sign\s*in\s+(?:required|to\s+(?:continue|view|read|access|watch))|log\s*in\s+to\s+(?:continue|view|read|access|watch)|verify\s+you\s+are\s+human|cf-chl-|captcha|<input\b[^>]*\btype\s*=\s*["']?\s*password\b|<form\b[^>]*\baction\s*=\s*["'][^"']*(?:login|signin|auth)|<title[^>]*>\s*(?:sign in|log in|access denied|just a moment)''',body):
        return True
    if mime=='text/html':
        # These RSS URLs advertise Captivate native HTML transcript fragments:
        # speaker <cite>, timestamp <time> and repeated spoken <p> elements.
        # An unrecognized page is stopped, not treated as an empty transcript.
        return not (re.search(rb'(?i)<cite\b',body) and re.search(rb'(?i)<time\b',body)
                    and len(re.findall(rb'(?i)<p\b',body))>=3)
    return False


def recognized_transcript(body, mime, advertised_type):
    """Require the advertised format's real structure; arbitrary text is unknown."""
    if authentication_or_unrecognized_html(body,mime):return False
    if advertised_type in ('application/srt','application/x-subrip','text/vtt'):
        return bool(re.search(rb'(?m)^\s*\d{1,2}:\d{2}:\d{2}(?:[,.]\d{1,3})?\s*-->\s*\d{1,2}:\d{2}:\d{2}',body))
    if advertised_type=='text/html':
        return not authentication_or_unrecognized_html(body,'text/html')
    if advertised_type=='application/json':
        try:value=json.loads(body)
        except (ValueError,UnicodeDecodeError):return False
        segments=value.get('segments') if isinstance(value,dict) else None
        return bool(isinstance(segments,list) and segments and all(isinstance(x,dict) and
                    isinstance(x.get('body',x.get('text')),str) for x in segments))
    return False


def execute(plan, out, *, opener=None, pace=True, started=None):
    validate_plan(plan)
    if signal.getitimer(signal.ITIMER_REAL)!=(0.0,0.0):raise ValueError('existing process timer')
    # Scope identity, rather than caller-supplied output path, determines one
    # exclusive budget directory. Its mere existence blocks a restart even if
    # setup, the process, the journal or a closure-marker write failed.
    scope_dir=SCOPE_ROOT/plan['scope_id'];journal,closed=scope_dir/'journal.jsonl',scope_dir/'CLOSED.json'
    out=Path(out);budget=None;created_scope=False
    blocked=set();reports=[];started=time.monotonic() if started is None else started
    work_end=started+110;scope_end=started+120
    next_dispatch=started;failure=None;cleanup_errors=[];active=None;old_handler=signal.getsignal(signal.SIGALRM)
    def expired(*_):raise TimeoutError('bounded request or scope deadline')
    def arm(until):
        remaining=until-time.monotonic()
        if remaining<=0:raise TimeoutError('bounded scope deadline')
        signal.setitimer(signal.ITIMER_REAL,remaining)
    signal.signal(signal.SIGALRM,expired)
    try:
        arm(work_end)  # includes scope setup, parsing, durable writes and journal work
        try:scope_dir.mkdir(parents=True,exist_ok=False)
        except FileExistsError as exc:raise ValueError('existing scope cannot be reset or restarted') from exc
        created_scope=True;out.mkdir(parents=True,exist_ok=False)
        budget=BudgetJournal(journal,plan['scope_id'],BudgetLimits(**plan['limits']))
        write_new(out/'scope.json',json_bytes(plan));(out/'subs').mkdir()
        opener=opener or urllib.request.build_opener(NoRedirect())
        for source in plan['sources']:
            url=public_url(source['transcript']);host=urllib.parse.urlsplit(url).hostname.lower()
            if host in blocked:
                reports.append({**source,'state':'HOST_DENIED_NO_ATTEMPT'});continue
            wait=max(0,next_dispatch-time.monotonic()) if pace else 0
            if time.monotonic()+wait+10>work_end:
                reports.append({**source,'state':'WALL_BUDGET_NO_ATTEMPT'});continue
            if wait:time.sleep(wait)
            op='transcript-'+digest(url.encode())[:24];now=time.time_ns()
            reservation=budget.reserve(op,plan['body_cap_bytes'],10*NS,now_ns=now,deadline_ns=now+10*NS)
            if not reservation['dispatch_allowed']:raise ValueError('duplicate scope operation refuses dispatch')
            begin=time.monotonic_ns();next_dispatch=time.monotonic()+plan['minimum_dispatch_interval_seconds']
            parts=[];complete=False;status=None;mime=None;error=None;proxy_status=None;stop_host=False
            active={'source':source,'operation_id':op,'parts':parts,'begin':begin}
            try:
                arm(min(work_end,time.monotonic()+9.5))
                req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; transcript-research/1.0)',
                                                      'Accept-Encoding':'identity'})
                with opener.open(req,timeout=9) as response:
                    status=response.status;mime=response.headers.get_content_type()
                    active.update(http_status=status,content_type=mime)
                    if status!=200:raise urllib.error.HTTPError(url,status,'non-200 response',None,None)
                    if mime not in ('text/plain','text/html','text/vtt','application/json','application/srt','application/x-subrip'):
                        raise ValueError('unsupported/nontext response outside scope')
                    _,complete=bounded_body(response,plan['body_cap_bytes'],parts)
            except (urllib.error.HTTPError,urllib.error.URLError,http.client.HTTPException,TimeoutError,OSError,ValueError) as exc:
                classified=classify_exception(exc)
                if classified['http_status'] is not None:status=classified['http_status']
                proxy_status=classified['proxy_status'];error=classified['error_kind'];stop_host=classified['stop_host']
            finally:
                # Resume the overall work deadline during parse/IO, too.
                arm(work_end)
            chunks=b''.join(parts);elapsed=time.monotonic_ns()-begin
            write_new(out/(source['key']+'.body'),chunks)
            receipt={**source,'host':host,'http_status':status,'proxy_status':proxy_status,'content_type':mime,
                'operation_id':op,'accepted_body_bytes':len(chunks),'body_sha256':digest(chunks),
                'complete_body':complete,'actual_body_bytes_known':bool(complete),
                'elapsed_ns':elapsed,'received_utc_ns':time.time_ns(),
                'state':'FAILED_OR_INCOMPLETE','error_kind':error,'parsed_text':None}
            active['receipt']=receipt
            if status==200 and complete:
                try:
                    if not recognized_transcript(chunks,mime,source['transcript_type']):
                        raise PermissionError('challenge, authentication or unrecognized HTML')
                    text=transcript_text(chunks,source['transcript_type'])
                    raw=text.encode();target=out/'subs'/('pod_'+source['key']+'.txt');write_new(target,raw)
                    receipt.update(state='TEXT_PARSED_UNREVIEWED',parsed_text={'path':str(target),
                        'sha256':digest(raw),'words':len(text.split()),'audio_or_episode_complete_verified':False})
                except PermissionError:
                    receipt['error_kind']='authentication_or_challenge';stop_host=True
                except (ValueError,UnicodeError,KeyError,TypeError) as exc:
                    receipt['error_kind']='parse_error:'+type(exc).__name__;stop_host=True
            elif status==200 and not complete and error is None:receipt['error_kind']='body_cap_reached_no_eof'
            write_new(out/(source['key']+'.json'),json_bytes(receipt))
            outcome='success' if receipt['state']=='TEXT_PARSED_UNREVIEWED' else 'failure'
            completion=budget.complete(op,len(chunks),elapsed,outcome=outcome)
            reports.append(receipt);active=None
            if stop_host:blocked.add(host)
            if completion['violations']:raise RuntimeError('budget reservation overrun; scope stopped')
    except BaseException as exc:
        failure=exc
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        try:
            if not created_scope:
                if failure:raise failure
                raise RuntimeError('scope setup did not complete')
            try:
                arm(scope_end)  # ten seconds reserved for reconciliation/closure
                status_snapshot=budget.status() if budget is not None else None
            except BaseException as exc:
                cleanup_errors.append('initial reconciliation:'+type(exc).__name__);status_snapshot=None;arm(scope_end)
            done={r['key'] for r in reports}
            if active is not None and active['source']['key'] not in done and budget is not None:
              try:
                chunks=b''.join(active['parts']);receipt=active.get('receipt',{})
                report_row={**active['source'],**receipt,'state':'INTERRUPTED_AFTER_RESERVATION',
                    'operation_id':active['operation_id'],'accepted_body_bytes':len(chunks),
                    'body_sha256':digest(chunks),'error_kind':type(failure).__name__ if failure else 'interrupted',
                    'http_status':active.get('http_status',receipt.get('http_status')),
                    'content_type':active.get('content_type',receipt.get('content_type')),
                    'actual_body_bytes_known':False,'partial_body_preserved':False}
                raw_path=out/(active['source']['key']+'.body')
                if not raw_path.exists():write_new(raw_path,chunks)
                report_row['partial_body_preserved']=raw_path.exists() and raw_path.read_bytes()==chunks
                if active['operation_id'] in budget.status()['pending']:
                    elapsed=time.monotonic_ns()-active['begin']
                    budget.complete(active['operation_id'],len(chunks),elapsed,outcome='failure')
                reports.append(report_row)
              except BaseException as exc:
                cleanup_errors.append('partial receipt:'+type(exc).__name__);arm(scope_end)
            # A signal may interrupt immediately after reservation but before
            # the active object exists. The journal still proves the spend;
            # unknown bytes are not replaced by fabricated zeroes.
            try:status_snapshot=budget.status() if budget is not None else None
            except BaseException as exc:
                cleanup_errors.append('budget status:'+type(exc).__name__);status_snapshot=None;arm(scope_end)
            pending=set(status_snapshot['pending']) if status_snapshot is not None else set()
            done={r['key'] for r in reports}
            for source in plan['sources']:
                if source['key'] in done:continue
                op='transcript-'+digest(public_url(source['transcript']).encode())[:24]
                state=('INTERRUPTED_PENDING_BYTES_UNKNOWN' if op in pending or status_snapshot is None
                       else 'NOT_ATTEMPTED_AFTER_SCOPE_FAILURE')
                reports.append({**source,'state':state,'operation_id':op if op in pending else None})
            report={'scope_id':plan['scope_id'],'reports':reports,'status':status_snapshot,
                'accepted_body_bytes_known':sum(r.get('accepted_body_bytes',0) for r in reports),
                'accepted_body_bytes_basis':'bytes returned to Python or supplied in IncompleteRead.partial; buffered/transport and wire bytes can remain unknown',
                'any_accepted_body_bytes_unknown':status_snapshot is None or bool(pending) or any(
                    r.get('state') in ('FAILED_OR_INCOMPLETE','INTERRUPTED_AFTER_RESERVATION')
                    and not r.get('complete_body',False) for r in reports),
                'parsed_texts':sum(r.get('state')=='TEXT_PARSED_UNREVIEWED' for r in reports),
                'blocked_hosts':sorted(blocked),'failure':type(failure).__name__+': '+str(failure) if failure else None,
                'cleanup_errors':cleanup_errors,'elapsed_ns_before_finalization':int((time.monotonic()-started)*NS),'closed':True,
                'unused_allowance_closed':True,'new_market_requests':0,'audio_or_model_weights_acquired':False}
            try:
                if out.is_dir():write_new(out/'report.json',json_bytes(report))
            except BaseException as exc:cleanup_errors.append('report write:'+type(exc).__name__);arm(scope_end)
        finally:
            try:
                if created_scope and not closed.exists():
                    arm(scope_end)
                    write_new(closed,json_bytes({'scope_id':plan['scope_id'],'closed':True,'cleanup_errors':cleanup_errors,
                        'failure':type(failure).__name__ if failure else None,'elapsed_ns':int((time.monotonic()-started)*NS)}))
            finally:
                signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old_handler)
    if failure:
        if not created_scope:raise failure
        raise RuntimeError(type(failure).__name__+': '+str(failure)) from failure
    if cleanup_errors:raise RuntimeError('scope closed with reconciliation errors: '+', '.join(cleanup_errors))
    return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--plan',type=Path,required=True)
    args=parser.parse_args();started=time.monotonic();plan=preflight(args.plan,started)
    out=(ROOT/plan['output_dir']).resolve();out.relative_to(ROOT/'data/videos')
    report=execute(plan,out,started=started)
    print(json.dumps({'scope_id':report['scope_id'],'requests':report['status']['requests_charged'],
                      'parsed_texts':report['parsed_texts'],'accepted_body_bytes_known':report['accepted_body_bytes_known'],
                      'blocked_hosts':report['blocked_hosts'],'closed':True}))

if __name__=='__main__':main()
