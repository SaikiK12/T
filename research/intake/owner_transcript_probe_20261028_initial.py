"""One owner-requested finite source probe; no media, orders, retries or login."""
from hashlib import sha256
from pathlib import Path
import json
import signal
import time
import urllib.error
import urllib.parse
import urllib.request

from lab.acquisition_budget import BudgetJournal, BudgetLimits
from scripts.podcast_corpus import NoRedirect, public_url

NS = 1_000_000_000
CAP = 512 * 1024
OUT = Path('data/videos/owner_transcript_recovery_20261028')
SOURCES = [
 ('owner_instagram_unread', 'https://www.instagram.com/reel/Dec0l3vtE3f/'),
 ('old_404_why_now_publisher_episode', 'https://resolve-gestalt-university.captivate.fm/episode/managed-futures-why-now-positioning-energy-de-dollarization-and-portfolio-blind-spots'),
 ('old_404_live_qa_publisher_episode', 'https://resolve-gestalt-university.captivate.fm/episode/live-qa-managed-futures-trend-carry-flash-update'),
 ('owner_tiktok_missing_caption', 'https://www.tiktok.com/@aleks_rosme/video/7670945661621128470'),
 ('owner_youtube_options', 'https://www.youtube.com/watch?v=E_PSlPIq0R4'),
 ('owner_youtube_gex', 'https://www.youtube.com/watch?v=SkvitOO2Zog'),
 ('owner_youtube_footprint', 'https://www.youtube.com/watch?v=ljk9BovCSqI'),
 ('owner_youtube_market', 'https://www.youtube.com/watch?v=dN8eOAgnJgQ'),
]


def store(path, value):
    with path.open('xb') as f:
        f.write((json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)+'\n').encode())


def main():
    OUT.mkdir(exist_ok=False)
    baseline = {'requests_used': 3, 'body_bytes_upper_bound': 3*CAP,
                'reserved_duration_ns': 30*NS, 'exact_body_bytes_known': False,
                'source': 'three provider search queries returned before journal initialization; actual provider-internal network/transport bytes are not exposed'}
    limits = BudgetLimits(12, 6*1024*1024, 120*NS, 10*NS)
    budget = BudgetJournal(OUT/'budget.jsonl', 'owner_requested_transcript_recovery_20261028_v1', limits, baseline=baseline)
    store(OUT/'scope.json', {'urls': SOURCES, 'limits': limits.__dict__, 'baseline': baseline,
        'web_queries_before_journal': ['exact owner Instagram shortcode', 'managed futures why now transcript', 'managed futures live QA transcript'],
        'old_public_corpus_scope_closed': True, 'historical_market_allowance_unchanged': True,
        'scope_notice': 'provider search normalized text constrained; provider internal wire/network bytes unknown; subsequent direct accepted bodies are metered. Stop a host on 401/403/429/451/503; no redirect/retry/login or audio/model weights.'})
    opener = urllib.request.build_opener(NoRedirect());blocked=set();reports=[];deadline=time.monotonic()+90
    for label,url in SOURCES:
        host=urllib.parse.urlsplit(public_url(url)).hostname.lower()
        if host in blocked:
            reports.append({'label':label,'url':url,'state':'HOST_DENIED_NO_ATTEMPT'});continue
        if time.monotonic()+10>deadline:
            reports.append({'label':label,'url':url,'state':'WALL_BUDGET_NO_ATTEMPT'});continue
        op='text-'+sha256(url.encode()).hexdigest()[:24];now=time.time_ns()
        reservation=budget.reserve(op,CAP,10*NS,now_ns=now,deadline_ns=now+10*NS)
        if not reservation['dispatch_allowed']:raise RuntimeError('scope refuses duplicate dispatch')
        start=time.monotonic_ns();parts=[];status=None;complete=False;reason=None;mime=None
        def timeout(*_):raise TimeoutError('bounded source deadline')
        old=signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,9.5)
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; source-research/1.0)','Accept-Encoding':'identity'})
            with opener.open(req,timeout=9) as response:
                status=response.status;mime=response.headers.get_content_type()
                if mime.startswith(('audio/','video/','image/')):raise ValueError('media body excluded')
                used=0
                while used<CAP:
                    b=response.read(min(65536,CAP-used))
                    if not b:complete=True;break
                    parts.append(b);used+=len(b)
                if not complete:reason='body cap reached; complete body unverified'
        except urllib.error.HTTPError as e:
            status=e.code;reason='HTTP '+str(e.code)+'; error body not read'
        except (OSError,TimeoutError,ValueError) as e:reason=type(e).__name__+': '+str(e)
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)
        raw=b''.join(parts);elapsed=time.monotonic_ns()-start
        outcome='success' if status==200 and complete else ('timeout' if reason and 'Timeout' in reason else 'failure')
        receipt={'label':label,'url':url,'host':host,'http_status':status,'content_type':mime,
                 'state':'BODY_RECEIVED' if outcome=='success' else 'FAILED_OR_INCOMPLETE',
                 'reason':reason,'accepted_bytes':len(raw),'complete_body':complete,
                 'body_sha256':sha256(raw).hexdigest(),'elapsed_ns':elapsed,'operation_id':op}
        with (OUT/(label+'.body')).open('xb') as f:f.write(raw)
        store(OUT/(label+'.json'),receipt)
        completion=budget.complete(op,len(raw),elapsed,outcome=outcome)
        reports.append(receipt)
        if status in (401,403,429,451,503):blocked.add(host)
        if completion['violations']:break
    store(OUT/'report.json', {'scope':'owner_requested_transcript_recovery_20261028_v1',
        'requests_including_three_search_queries':budget.status()['requests_charged'],
        'direct_http_attempts':sum('http_status' in x for x in reports),
        'direct_accepted_body_bytes':sum(x.get('accepted_bytes',0) for x in reports),
        'status':budget.status(),'reports':reports,'unused_allowance_closed':True,
        'provider_wire_bytes_known':False,'new_market_requests':0,'new_audio_or_weights':False})
    print(json.dumps({'requests_charged':budget.status()['requests_charged'],
                      'direct_attempts':sum('http_status' in x for x in reports),
                      'states':[(x['label'],x['state'],x.get('http_status'),x.get('accepted_bytes',0)) for x in reports],
                      'scope_closed':True}))


if __name__=='__main__':main()
