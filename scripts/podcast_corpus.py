"""Bounded source-data backend for dig_podcasts, not a methods queue.

RSS metadata, advertised transcript links, acquired native text and actual
semantic reviews are different states. Never fetches audio/video/model weights,
follows redirects, retries failures, authenticates or calls an external LLM.
One accumulated source budget is shared across output folders and restarts.
"""
import csv
from contextlib import contextmanager
from dataclasses import asdict
import fcntl
import hashlib
import ipaddress
import io
import json
import os
from pathlib import Path
import re
import signal
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from lab.acquisition_budget import BudgetJournal,BudgetLimits,BudgetError
from scripts import dig_podcasts as dp

ROOT=Path(__file__).resolve().parents[1]
MiB=1024**2
NS=1_000_000_000
LIMITS=BudgetLimits(72,128*MiB,1800*NS,25*NS)
SCOPE='public_practitioner_corpus_20261026_v1'
LARGE={'top_traders_unplugged','trend_following','masters_in_business','meb_faber'}
sha=lambda raw:hashlib.sha256(raw).hexdigest()
encoded=lambda x:(json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()


def write_new(path,raw):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.is_symlink():raise ValueError('symlink output')
    if path.exists():
        if path.read_bytes()!=raw:raise ValueError('immutable source/output changed: '+str(path))
        return
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as h:h.write(raw);h.flush();os.fsync(h.fileno())


def public_url(url):
    u=urllib.parse.urlsplit(url)
    if u.scheme not in ('https','http') or not u.hostname or u.username or u.password:
        raise ValueError('public unauthenticated HTTP(S) URL required')
    host=u.hostname.lower().rstrip('.')
    if host=='localhost' or host.endswith(('.local','.internal')):raise ValueError('private source URL')
    if u.port not in (None,80,443):raise ValueError('unsupported public source port')
    try:
        if not ipaddress.ip_address(host).is_global:raise ValueError('private source IP')
    except ValueError as e:
        if str(e)=='private source IP':raise
    return urllib.parse.urlunsplit((u.scheme, u.netloc.lower(), u.path, u.query, ''))


def identity_url(url):
    try:u=urllib.parse.urlsplit(public_url(url))
    except (TypeError,ValueError):return None
    if u.path in ('','/') and not u.query:return None
    query=urllib.parse.parse_qsl(u.query,keep_blank_values=True)
    query=[(k,v) for k,v in query if not k.lower().startswith('utm_') and k.lower() not in ('fbclid','gclid')]
    return urllib.parse.urlunsplit((u.scheme,u.netloc,u.path,urllib.parse.urlencode(query),''))


def deduplicate(rows):
    """Exact episode URL/GUID only; never merge merely on a title or a person.

    A link reused by different episodes in one feed is ambiguous and is not
    allowed to collapse that feed. Keep every origin row, including alternative
    transcripts and uncertain duplicate candidates.
    """
    links={}
    for r in rows:
        link=identity_url(r.get('episode_url') or r.get('guid') or '')
        if link:links.setdefault((r['feed'],link),set()).add(r['key'])
    groups={}
    for r in rows:
        link=identity_url(r.get('episode_url') or r.get('guid') or '')
        ambiguous=bool(link and len(links[r['feed'],link])>1)
        canonical=link if link and not ambiguous else r['feed']+'|'+r['guid']
        ident=sha(canonical.encode())[:24]
        groups.setdefault(ident,[]).append({**r,'ambiguous_episode_link':ambiguous})
    result=[]
    for ident,origins in groups.items():
        chosen=sorted(origins,key=lambda r:(not bool(r.get('transcript')),r['feed'],r['key']))[0]
        result.append({**chosen,'canonical_id':ident,'origin_count':len(origins),
            'origins':[{k:r.get(k) for k in ('feed','key','guid','title','pub_utc','audio','episode_url','transcript','transcript_type','transcript_alternatives','source_body_sha256')} for r in origins],
            'review_state':'METADATA_ONLY','profitability_verified':False})
    return sorted(result,key=lambda r:r['canonical_id'])


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


@contextmanager
def deadline(seconds):
    if threading.current_thread() is not threading.main_thread():
        raise ValueError('single main-thread capture required for wall deadline')
    prior=signal.getsignal(signal.SIGALRM)
    if signal.getitimer(signal.ITIMER_REAL)!=(0.0,0.0):raise ValueError('existing process timer')
    def expired(*_):raise TimeoutError('source wall deadline')
    signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,seconds)
    try:yield
    finally:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,prior)


class Corpus:
    def __init__(self,out,*,feeds=None,budget_path=None,opener=None):
        self.out=Path(out).resolve();self.out.mkdir(parents=True,exist_ok=True)
        self.feeds=dict(dp.FEEDS if feeds is None else feeds)
        if len(self.feeds)>64:raise ValueError('finite feed registry required')
        for name,url in self.feeds.items():
            if not re.fullmatch('[a-z0-9_]+',name):raise ValueError('bounded feed identity')
            public_url(url)
        self.budget_path=Path(budget_path or ROOT/'data/videos/public_corpus_budget_20261026.jsonl').resolve()
        self.cache=self.budget_path.parent/(self.budget_path.stem+'_cache')
        self.cache.mkdir(parents=True,exist_ok=True);os.chmod(self.cache,0o700)
        self.budget=BudgetJournal(self.budget_path,SCOPE,LIMITS)
        self.opener=opener or urllib.request.build_opener(NoRedirect())
        code={p:sha((ROOT/p).read_bytes()) for p in ('scripts/podcast_corpus.py','scripts/dig_podcasts.py','scripts/dig_talks.py','lab/acquisition_budget.py')}
        self.config={'scope':SCOPE,'feeds':self.feeds,'feed_order':list(self.feeds),'limits':asdict(LIMITS),'code_sha256':code,
            'max_selected_native_transcripts':24,'text_body_limit':512*1024,'large_rss_body_limit':8*MiB,
            'other_rss_body_limit':2*MiB,'network_wall_seconds':20,'per_attempt_reserved_seconds':25,
            'no_media_models_market_or_full_channel_mirror':True}
        write_new(self.out/'scope.json',encoded(self.config))

    def capture(self,url,kind,cap):
        url=public_url(url);op=kind+'-'+sha(url.encode())[:24]
        if urllib.parse.urlsplit(url).path.lower().endswith(('.mp3','.mp4','.wav','.ogg','.m4a','.webm','.zip','.pdf')):
            raise ValueError('media/archive source path refused')
        path=self.cache/(op+'.json');body_path=self.cache/(op+'.body')
        if path.exists():
            r=json.loads(path.read_text())
            if r['url']!=url or r['kind']!=kind or r['body_cap_bytes']!=cap or r['body_sha256']!=sha(body_path.read_bytes()):raise ValueError('source receipt/cache drift')
            self.budget.complete(op,r['accepted_body_bytes'],r['elapsed_ns'],outcome=r['outcome'])
            return r,body_path.read_bytes()
        if op in self.budget.status()['pending']:
            return {'operation_id':op,'url':url,'state':'PENDING_PRIOR_ATTEMPT_NO_RETRY'},None
        now=time.time_ns()
        try:reservation=self.budget.reserve(op,cap,25*NS,now_ns=now,deadline_ns=now+25*NS)
        except BudgetError as e:return {'operation_id':op,'url':url,'state':'BUDGET_BLOCKED','error':str(e)},None
        if not reservation['dispatch_allowed']:
            return {'operation_id':op,'url':url,'state':'PENDING_PRIOR_ATTEMPT_NO_RETRY'},None
        start=time.monotonic_ns();parts=[];complete=False
        r={'operation_id':op,'url':url,'kind':kind,'requested_utc_ns':now,'body_cap_bytes':cap,
           'http_status':None,'headers':{},'outcome':'failure','state':'FAILED'}
        try:
            with deadline(20):
                req=urllib.request.Request(url,headers={'User-Agent':dp.UA,'Accept-Encoding':'identity'})
                with self.opener.open(req,timeout=20) as response:
                    r['http_status']=response.status
                    r['headers']={k:v for k,v in response.headers.items() if k.lower() in ('content-type','content-length','last-modified','etag','retry-after','location')}
                    if response.status!=200:raise ValueError('non200 source response')
                    content_type=response.headers.get('Content-Type','').lower()
                    if any(t in content_type for t in ('audio/','video/','image/','application/pdf','application/zip')):
                        raise ValueError('nontext/media response refused')
                    size=0
                    while size<cap:
                        chunk=response.read(min(65536,cap-size))
                        if not chunk:complete=True;break
                        parts.append(chunk);size+=len(chunk)
                    if not complete:raise ValueError('body cap reached; complete body not certified')
                    r.update(outcome='success',state='BODY_ACQUIRED')
        except urllib.error.HTTPError as e:
            r.update(http_status=e.code,error=str(e),error_body_not_read=True)
            r['headers']={k:v for k,v in (e.headers or {}).items() if k.lower() in ('content-type','retry-after','location')}
        except TimeoutError as e:r.update(outcome='timeout',state='TIMEOUT',error=str(e))
        except (OSError,ValueError) as e:r['error']=type(e).__name__+': '+str(e)
        raw=b''.join(parts);r.update(accepted_body_bytes=len(raw),complete_body=complete,
            body_sha256=sha(raw),received_utc_ns=time.time_ns(),received_mono_ns=time.monotonic_ns(),
            elapsed_ns=time.monotonic_ns()-start)
        write_new(body_path,raw);write_new(path,encoded(r))
        self.budget.complete(op,len(raw),r['elapsed_ns'],outcome=r['outcome'])
        return r,raw

    def _metadata(self):
        rows=[];states=[]
        for name,url in self.feeds.items():
            receipt,raw=self.capture(url,'rss',8*MiB if name in LARGE else 2*MiB)
            record={'feed':name,**receipt}
            if receipt['state']=='BODY_ACQUIRED':
                try:
                    parsed=dp.parse_episodes(name,raw)
                    if len(parsed)>50000:raise ValueError('source episode bound exceeded')
                    record.update(parse_state='RSS_PARSED' if parsed else 'NO_EPISODES',episodes=len(parsed))
                    for r in parsed:rows.append({**r,'source_body_sha256':receipt['body_sha256']})
                except Exception as e:record.update(parse_state='UNSUPPORTED_OR_INVALID_RSS',parse_error=type(e).__name__+': '+str(e))
            states.append(record)
            print(name,record.get('parse_state',record['state']),record.get('episodes',0),flush=True)
        return deduplicate(rows),states,len(rows)

    def collect(self,*,texts=False):
        fd=os.open(self.out/'writer.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'a+') as lease:
            fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
            if texts:
                metadata_report=json.loads((self.out/'metadata_report.json').read_text())
                if metadata_report['metadata_sha256']!=sha((self.out/'metadata.json').read_bytes()):raise ValueError('metadata input drift')
                index=json.loads((self.out/'metadata.json').read_text());rows=index['episodes'];states=index['feed_states'];origins=index['origin_rows']
            else:
                rows,states,origins=self._metadata()
                write_new(self.out/'metadata.json',encoded({'episodes':rows,'feed_states':states,'origin_rows':origins}))
                import pandas as pd
                fields=['feed','key','canonical_id','title','pub_utc','duration_s','episode_url','audio','transcript','transcript_type','summary','origin_count','source_body_sha256','review_state']
                frame=dp.score(pd.DataFrame(rows)) if rows else pd.DataFrame(columns=fields+['words','mech','firm'])
                write_new(self.out/'episodes.csv',frame[fields+['words','mech','firm']].to_csv(index=False).encode())
            text_states=[]
            if texts:
                plan_path=self.out/'text_plan.json'
                import pandas as pd
                frame=dp.score(pd.DataFrame(rows)) if rows else pd.DataFrame()
                candidates=frame[frame.transcript.fillna('')!=''] if not frame.empty else frame
                plan=[];counts={};seen=set()
                kinds=['application/srt','application/x-subrip','text/vtt','text/plain','application/json','text/html']
                if not candidates.empty:
                    candidates=candidates.sort_values(['mech','firm','pub_utc'],ascending=[False,False,False])
                    for r in candidates.to_dict('records'):
                        alternatives=json.loads(r.get('transcript_alternatives') or '[]')
                        alternatives=[a for a in alternatives if a.get('type','').split(';')[0] in kinds]
                        if not alternatives:continue
                        chosen=min(alternatives,key=lambda a:kinds.index(a['type'].split(';')[0]))
                        url=chosen['url']
                        if counts.get(r['feed'],0)>=8 or url in seen:continue
                        plan.append({**{k:r[k] for k in ('canonical_id','key','feed','title','pub_utc')},
                            'transcript':url,'transcript_type':chosen['type']})
                        counts[r['feed']]=counts.get(r['feed'],0)+1;seen.add(url)
                        if len(plan)==24:break
                write_new(plan_path,encoded(plan))
                for r in plan:
                    try:receipt,raw=self.capture(r['transcript'],'text',512*1024)
                    except ValueError as e:
                        text_states.append({**r,'state':'UNSUPPORTED_URL','error':str(e)});continue
                    state={**r,**receipt,'review_state':'NOT_SEMANTICALLY_REVIEWED','full_episode_verified':False}
                    if receipt['state']=='BODY_ACQUIRED':
                        try:
                            plain=dp.transcript_text(raw,r['transcript_type'])
                            if len(plain.split())<100:raise ValueError('too little text; no full transcript claim')
                            name='pod_'+r['key']+'.txt';write_new(self.out/'subs'/name,plain.encode())
                            state.update(parse_state='TEXT_PARSED_UNREVIEWED',words=len(plain.split()),text_path='subs/'+name,text_sha256=sha(plain.encode()))
                        except Exception as e:state.update(parse_state='UNSUPPORTED_OR_INVALID_TEXT',parse_error=str(e))
                    text_states.append(state)
                    print(r['feed'],state.get('parse_state',state['state']),r['title'][:85],flush=True)
                write_new(self.out/'native_texts.json',encoded(text_states))
            report={'scope':SCOPE,'metadata_origin_rows':origins,'deduplicated_episodes':len(rows),
                'feeds_requested':len(self.feeds),'feeds_parsed':sum(s.get('parse_state')=='RSS_PARSED' for s in states),
                'feeds_failed_or_empty':sum(s.get('parse_state')!='RSS_PARSED' for s in states),
                'advertised_native_transcripts':sum(bool(r.get('transcript')) for r in rows),
                'native_text_attempts':len(text_states),'native_texts_parsed':sum(s.get('parse_state')=='TEXT_PARSED_UNREVIEWED' for s in text_states),
                'full_semantic_reviews':0,'source_methods_extracted':0,'profitability_verified':False,
                'budget':self.budget.status(),'metadata_sha256':sha((self.out/'metadata.json').read_bytes()),
                'scope_notice':'Metadata/name/cue matches are not read speech, verified profitable traders or methods. Raw text remains private; only explicit later source reviews count.',
                'review_counter_scope':'Acquisition stage only. Subsequent explicit method reviews belong to canonical intake, not this immutable snapshot.',
                'market_history_requests':0,'media_models_downloaded':0,'prospective_days':0}
            report_path=self.out/('text_report.json' if texts else 'metadata_report.json')
            if report_path.exists():
                old=json.loads(report_path.read_text())
                if {k:v for k,v in old.items() if k!='budget'}!={k:v for k,v in report.items() if k!='budget'}:
                    raise ValueError('immutable acquisition report drift')
                report=old
            else:write_new(report_path,encoded(report))
            return {**report,'current_shared_budget':self.budget.status()}
