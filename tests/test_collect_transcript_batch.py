import io
import http.client
import tempfile
import time
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from scripts.collect_transcript_batch import (authentication_or_unrecognized_html, bounded_body,
    classify_exception, execute, preflight, recognized_transcript, validate_plan, verify_metadata, NS)


class Headers:
    def get_content_type(self):return 'text/plain'


class Reply:
    status=200
    headers=Headers()
    def __init__(self,data):self.stream=io.BytesIO(data)
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,n):return self.stream.read(n)


class BrokenReply(Reply):
    def __init__(self):self.calls=0
    def read(self,n):
        self.calls+=1
        if self.calls==1:return b'partial'
        raise urllib.error.URLError('connection dropped')


class IncompleteReply(Reply):
    def __init__(self):self.calls=0
    def read(self,n):
        self.calls+=1
        if self.calls==1:return b'early'
        raise http.client.IncompleteRead(b'late',10)


def plan():
    ids=('000000000001','000000000002','000000000003')
    urls=('https://transcripts.captivate.fm/a.srt','https://api.omny.fm/b.srt',
          'https://transcripts.captivate.fm/c.srt')
    return {'schema_version':1,'scope_id':'test_scope',
        'scope_budget_directory':'data/videos/transcript_scope_budgets/test_scope','body_cap_bytes':512*1024,
        'source_metadata_path':'data/videos/corpus_20261026/metadata.json',
        'catalogue_index_path':'research/intake/podcast_episode_index_20261026.csv.gz',
        'minimum_dispatch_interval_seconds':1,
        'limits':{'max_requests':12,'max_body_bytes':6*1024*1024,
                  'max_reserved_duration_ns':120*NS,'max_attempt_duration_ns':10*NS},
        'code_sha256':{s:'a'*64 for s in ('scripts/collect_transcript_batch.py',
              'scripts/podcast_corpus.py','scripts/dig_podcasts.py','lab/acquisition_budget.py')},
        'sources':[{'key':k,'transcript':u,'transcript_type':'application/srt'} for k,u in zip(ids,urls)]}


class ProbeTests(unittest.TestCase):
    def test_proxy_tunnel_denial_is_not_misreported_as_upstream_http(self):
        r=classify_exception(urllib.error.URLError('Tunnel connection failed: 403 Forbidden'))
        self.assertEqual(r,{'error_kind':'proxy_connect_denied','http_status':None,'proxy_status':403,'stop_host':True})
        r=classify_exception(urllib.error.HTTPError('https://api.omny.fm/x',429,'busy',{},None))
        self.assertEqual((r['http_status'],r['proxy_status'],r['stop_host']),(429,None,True))
        for code in (302,402,407,429,451,503):
            self.assertTrue(classify_exception(urllib.error.HTTPError('https://api.omny.fm/x',code,'blocked',{},None))['stop_host'])
        for code in (404,410):
            self.assertFalse(classify_exception(urllib.error.HTTPError('https://api.omny.fm/x',code,'missing',{},None))['stop_host'])
        self.assertTrue(classify_exception(urllib.error.URLError('unknown transport'))['stop_host'])

    def test_denied_proxy_host_is_not_called_again_and_other_public_host_can_continue(self):
        class Opener:
            def __init__(self):self.calls=[]
            def open(self,request,timeout):
                self.calls.append(request.full_url)
                if 'captivate' in request.full_url:raise urllib.error.URLError('Tunnel connection failed: 403 Forbidden')
                return Reply(b'1\n00:00:01 --> 00:00:02\nPublisher transcript sample.\n')
        op=Opener()
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            with mock.patch('scripts.collect_transcript_batch.SCOPE_ROOT',base/'scopes'):
                r=execute(plan(),base/'out',opener=op,pace=False)
                with self.assertRaises(ValueError):execute(plan(),base/'other_out',opener=op,pace=False)
            self.assertEqual(len(op.calls),2)
            self.assertEqual(r['status']['requests_charged'],2)
            self.assertEqual(r['reports'][0]['proxy_status'],403)
            self.assertIsNone(r['reports'][0]['http_status'])
            self.assertEqual(r['reports'][1]['state'],'TEXT_PARSED_UNREVIEWED')
            self.assertEqual(r['reports'][2]['state'],'HOST_DENIED_NO_ATTEMPT')
            self.assertTrue(r['closed'])
            self.assertEqual(len(op.calls),2)

    def test_partial_bytes_are_recorded_when_a_later_read_fails(self):
        class Opener:
            def open(self,request,timeout):return BrokenReply()
        p=plan();p['sources']=p['sources'][:1]
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            with mock.patch('scripts.collect_transcript_batch.SCOPE_ROOT',base/'scopes'):
                r=execute(p,base/'out',opener=Opener(),pace=False)
            self.assertEqual(r['accepted_body_bytes_known'],7)
            self.assertEqual(r['reports'][0]['accepted_body_bytes'],7)
            self.assertEqual((base/'out'/'000000000001.body').read_bytes(),b'partial')
            self.assertFalse(r['reports'][0]['complete_body'])

    def test_incomplete_read_includes_exception_partial_and_preserves_http_200(self):
        class Opener:
            def open(self,request,timeout):return IncompleteReply()
        p=plan();p['sources']=p['sources'][:1]
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            with mock.patch('scripts.collect_transcript_batch.SCOPE_ROOT',base/'scopes'):
                r=execute(p,base/'out',opener=Opener(),pace=False)
            self.assertEqual(r['accepted_body_bytes_known'],9)
            self.assertEqual((base/'out'/'000000000001.body').read_bytes(),b'earlylate')
            self.assertEqual(r['reports'][0]['http_status'],200)
            self.assertFalse(r['reports'][0]['complete_body'])
            self.assertTrue(r['any_accepted_body_bytes_unknown'])
            self.assertIn('transcripts.captivate.fm',r['blocked_hosts'])

    def test_interrupted_receipt_accounts_for_active_and_marks_remaining_sources(self):
        from scripts import collect_transcript_batch as mod
        real_write=mod.write_new
        def failing_write(path,data):
            if str(path).endswith('000000000001.json'):raise OSError('fixture storage interruption')
            return real_write(path,data)
        class Opener:
            def open(self,request,timeout):return Reply(b'legitimate source text')
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            with mock.patch.object(mod,'SCOPE_ROOT',base/'scopes'),mock.patch.object(mod,'write_new',failing_write):
                with self.assertRaises(RuntimeError):execute(plan(),base/'out',opener=Opener(),pace=False)
            import json
            report=json.loads((base/'out'/'report.json').read_text())
            self.assertEqual(len(report['reports']),3)
            self.assertEqual(report['reports'][0]['state'],'INTERRUPTED_AFTER_RESERVATION')
            self.assertTrue(report['reports'][0]['partial_body_preserved'])
            self.assertEqual(report['reports'][1]['state'],'NOT_ATTEMPTED_AFTER_SCOPE_FAILURE')
            self.assertTrue((base/'scopes'/'test_scope'/'CLOSED.json').exists())
            self.assertEqual(report['status']['requests_charged'],1)

    def test_setup_failure_closes_same_scope_without_dispatch(self):
        from scripts import collect_transcript_batch as mod
        real_write=mod.write_new
        def failing_write(path,data):
            if str(path).endswith('scope.json'):raise OSError('fixture setup interruption')
            return real_write(path,data)
        class Opener:
            def open(self,*args,**kwargs):raise AssertionError('must never dispatch')
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            with mock.patch.object(mod,'SCOPE_ROOT',base/'scopes'),mock.patch.object(mod,'write_new',failing_write):
                with self.assertRaises(RuntimeError):execute(plan(),base/'out',opener=Opener(),pace=False)
            import json
            report=json.loads((base/'out'/'report.json').read_text())
            self.assertEqual(report['status']['requests_charged'],0)
            self.assertTrue(all(r['state']=='NOT_ATTEMPTED_AFTER_SCOPE_FAILURE' for r in report['reports']))
            self.assertTrue((base/'scopes'/'test_scope'/'CLOSED.json').exists())

    def test_report_write_failure_still_closes_scope_and_cannot_reset(self):
        from scripts import collect_transcript_batch as mod
        real_write=mod.write_new
        def failing_write(path,data):
            if str(path).endswith('report.json'):raise OSError('fixture report write failure')
            return real_write(path,data)
        class Opener:
            def open(self,request,timeout):return Reply(b'Publisher text')
        p=plan();p['sources']=p['sources'][:1]
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            with mock.patch.object(mod,'SCOPE_ROOT',base/'scopes'),mock.patch.object(mod,'write_new',failing_write):
                with self.assertRaises(RuntimeError):execute(p,base/'out',opener=Opener(),pace=False)
                with self.assertRaises(ValueError):execute(p,base/'second_output',opener=Opener(),pace=False)
            import json
            marker=json.loads((base/'scopes'/'test_scope'/'CLOSED.json').read_text())
            self.assertIn('report write:OSError',marker['cleanup_errors'])

    def test_expired_preflight_deadline_stops_before_scope_or_network(self):
        class Opener:
            def open(self,*args,**kwargs):raise AssertionError('must never dispatch')
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            with mock.patch('scripts.collect_transcript_batch.SCOPE_ROOT',base/'scopes'):
                with self.assertRaises(TimeoutError):execute(plan(),base/'out',opener=Opener(),pace=False,started=time.monotonic()-111)
            self.assertFalse((base/'out').exists())

    def test_challenge_response_stops_same_host(self):
        class Opener:
            def __init__(self):self.calls=[]
            def open(self,request,timeout):
                self.calls.append(request.full_url)
                return Reply(b'captcha - verification required') if 'captivate' in request.full_url else Reply(b'1\n00:00:01 --> 00:00:02\nPublisher text')
        op=Opener()
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            with mock.patch('scripts.collect_transcript_batch.SCOPE_ROOT',base/'scopes'):
                r=execute(plan(),base/'out',opener=op,pace=False)
            self.assertEqual(len(op.calls),2)
            self.assertEqual(r['reports'][0]['error_kind'],'authentication_or_challenge')
            self.assertEqual(r['reports'][2]['state'],'HOST_DENIED_NO_ATTEMPT')

    def test_whitespace_password_form_stops_same_host(self):
        class HtmlReply(Reply):
            class H:
                def get_content_type(self):return 'text/html'
            headers=H()
        class Opener:
            def __init__(self):self.calls=[]
            def open(self,request,timeout):
                self.calls.append(request.full_url)
                return HtmlReply(b'<form><input type = "password"></form>') if 'captivate' in request.full_url else Reply(b'1\n00:00:01 --> 00:00:02\nPublisher text')
        op=Opener()
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            with mock.patch('scripts.collect_transcript_batch.SCOPE_ROOT',base/'scopes'):
                r=execute(plan(),base/'out',opener=op,pace=False)
            self.assertEqual(len(op.calls),2)
            self.assertEqual(r['reports'][0]['error_kind'],'authentication_or_challenge')
            self.assertEqual(r['reports'][2]['state'],'HOST_DENIED_NO_ATTEMPT')

    def test_plain_login_html_is_not_mistaken_for_a_transcript(self):
        login=b'<html><body><h1>Sign in required</h1><p>Please log in to continue.</p><a href="/login">Continue</a></body></html>'
        self.assertTrue(authentication_or_unrecognized_html(login,'text/html'))
        unknown=b'<html><body><p>This page has text but no transcript markers.</p></body></html>'
        self.assertTrue(authentication_or_unrecognized_html(unknown,'text/html'))
        valid=b'<cite>Speaker</cite><time>00:00:01</time><p>One.</p><p>Two.</p><p>Three.</p>'
        self.assertFalse(authentication_or_unrecognized_html(valid,'text/html'))
        self.assertTrue(authentication_or_unrecognized_html(b'Access denied','text/plain'))
        self.assertTrue(authentication_or_unrecognized_html(b'<html><body>Access denied</body></html>','text/plain'))
        self.assertTrue(authentication_or_unrecognized_html(b'Subscription required','text/plain'))
        self.assertTrue(authentication_or_unrecognized_html(b'403 Forbidden','text/plain'))

    def test_plaintext_denial_stops_future_same_host_requests(self):
        class Opener:
            def __init__(self):self.calls=[]
            def open(self,request,timeout):
                self.calls.append(request.full_url)
                return Reply(b'Access denied') if 'captivate' in request.full_url else Reply(b'1\n00:00:01 --> 00:00:02\nPublisher text')
        op=Opener()
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            with mock.patch('scripts.collect_transcript_batch.SCOPE_ROOT',base/'scopes'):
                r=execute(plan(),base/'out',opener=op,pace=False)
            self.assertEqual(len(op.calls),2)
            self.assertEqual(r['reports'][0]['error_kind'],'authentication_or_challenge')
            self.assertEqual(r['reports'][2]['state'],'HOST_DENIED_NO_ATTEMPT')

    def test_advertised_structure_rejects_unrecognized_denial_text(self):
        for text in (b'You do not have permission to view this resource.',
                     b'This transcript is available to subscribers only.',
                     b'You must be logged in to continue.'):
            self.assertFalse(recognized_transcript(text,'text/plain','application/srt'))
        self.assertTrue(recognized_transcript(b'1\n00:00:01 --> 00:00:02\nWords.', 'text/plain','application/srt'))
        self.assertFalse(recognized_transcript(b'{"error":"not available"}','application/json','application/json'))
        self.assertTrue(recognized_transcript(b'{"segments":[{"text":"words"}]}','application/json','application/json'))

    def test_preflight_timer_bounds_stalled_plan_or_source_reads(self):
        def stalled(*args,**kwargs):time.sleep(.3)
        with mock.patch('scripts.collect_transcript_batch.committed_plan',side_effect=stalled):
            with self.assertRaises(TimeoutError):preflight(Path('unused'),time.monotonic()-109.95)

    def test_cap_is_not_overread_or_mistaken_for_a_complete_body(self):
        reply=Reply(b'a'*11)
        body,complete=bounded_body(reply,10)
        self.assertEqual((len(body),complete,reply.stream.tell()),(10,False,10))
        reply=Reply(b'a'*9)
        body,complete=bounded_body(reply,10)
        self.assertEqual((len(body),complete),(9,True))

    def test_plan_refuses_duplicates_and_unapproved_media_or_hosts(self):
        p=plan();p['sources'][2]['transcript']=p['sources'][0]['transcript']
        with self.assertRaises(ValueError):validate_plan(p)
        p=plan();p['sources'][0]['transcript']='https://www.youtube.com/watch?v=abc'
        with self.assertRaises(ValueError):validate_plan(p)
        p=plan();p['sources'][0]['transcript']='https://transcripts.captivate.fm/x.mp3'
        with self.assertRaises(ValueError):validate_plan(p)

    def test_original_metadata_hash_and_source_identity_must_match(self):
        import hashlib,json
        p=plan()
        for index,s in enumerate(p['sources']):s['canonical_id']='identity-'+str(index)
        raw=json.dumps({'episodes':p['sources']}).encode();p['source_metadata_sha256']=hashlib.sha256(raw).hexdigest()
        verify_metadata(p,raw)
        with self.assertRaises(ValueError):verify_metadata(p,raw+b' ')
        p['sources'][0]['transcript']='https://transcripts.captivate.fm/changed.srt'
        with self.assertRaises(ValueError):verify_metadata(p,raw)

    def test_an_explicitly_advertised_subtitle_alternative_is_allowed_but_not_guessed(self):
        import hashlib,json
        p=plan()
        for index,s in enumerate(p['sources']):s['canonical_id']='identity-'+str(index)
        original=[dict(s) for s in p['sources']]
        original[0]['transcript']='https://transcripts.captivate.fm/source.json'
        original[0]['transcript_type']='application/json'
        original[0]['transcript_alternatives']=json.dumps([{'url':p['sources'][0]['transcript'],'type':'application/srt'}])
        raw=json.dumps({'episodes':original}).encode();p['source_metadata_sha256']=hashlib.sha256(raw).hexdigest()
        verify_metadata(p,raw)
        p['sources'][0]['transcript']='https://transcripts.captivate.fm/guessed.srt'
        with self.assertRaises(ValueError):verify_metadata(p,raw)


if __name__=='__main__':unittest.main()
