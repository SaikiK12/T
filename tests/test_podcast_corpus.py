import io
import json
from pathlib import Path
import tempfile
import unittest
import urllib.error

from scripts import dig_podcasts as dp
from scripts import podcast_corpus as pc


def rss(items):
    return ('<rss xmlns:podcast="https://podcastindex.org/namespace/1.0"><channel>'+''.join(items)+'</channel></rss>').encode()


def item(guid='one',title='Trader funding basis and carry',link='https://publisher.example/episode/1',transcript=True):
    return ('<item><title>'+title+'</title><guid>'+guid+'</guid><link>'+link+'</link>'
        '<pubDate>Mon, 26 Oct 2026 09:00:00 GMT</pubDate>'
        +('<podcast:transcript url="https://publisher.example/text.json" type="application/json"/>'
          '<podcast:transcript url="https://publisher.example/text.srt" type="application/srt"/>' if transcript else '')+'</item>')


class Response(io.BytesIO):
    status=200
    def __init__(self,body,kind='text/xml'):
        super().__init__(body);self.headers={'Content-Type':kind}


class FakeHTTP:
    def __init__(self,data):self.data=data;self.calls=[]
    def open(self,request,timeout):
        url=request.full_url;self.calls.append(url);value=self.data[url]
        if isinstance(value,BaseException):raise value
        if isinstance(value,tuple):return Response(*value)
        return Response(value)


class CorpusTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.url='https://publisher.example/feed.rss'
        self.http=FakeHTTP({self.url:rss([item()]),'https://publisher.example/text.srt':
            ('1\n00:00:00,000 --> 00:01:00,000\n'+'funding carries price risk '*70).encode()})
    def corpus(self,name='out'):
        return pc.Corpus(self.root/name,feeds={'publisher':self.url},budget_path=self.root/'budget.jsonl',opener=self.http)

    def test_capture_restart_and_cross_output_share_one_budget(self):
        c=self.corpus();first=c.collect();raw=(c.out/'metadata.json').read_bytes()
        self.assertEqual(first['deduplicated_episodes'],1);self.assertEqual(first['advertised_native_transcripts'],1)
        self.assertEqual(first['full_semantic_reviews'],0)
        second=self.corpus().collect();third=self.corpus('second_output').collect()
        self.assertEqual(self.http.calls,[self.url]);self.assertEqual(first['metadata_sha256'],second['metadata_sha256'])
        self.assertEqual(first['metadata_sha256'],third['metadata_sha256']);self.assertEqual(raw,(c.out/'metadata.json').read_bytes())
        self.assertEqual(c.budget.status()['requests_charged'],1)

    def test_metadata_text_metadata_resume_preserves_old_snapshots(self):
        c=self.corpus();c.collect();phase=(c.out/'metadata_report.json').read_bytes()
        report=c.collect(texts=True)
        self.assertEqual(self.http.calls,[self.url,'https://publisher.example/text.srt'])
        self.assertEqual(report['native_texts_parsed'],1);self.assertEqual(report['full_semantic_reviews'],0)
        source=json.loads((c.out/'native_texts.json').read_text())[0]
        self.assertEqual(source['parse_state'],'TEXT_PARSED_UNREVIEWED');self.assertFalse(source['full_episode_verified'])
        c.collect();c.collect(texts=True)
        self.assertEqual(len(self.http.calls),2);self.assertEqual(phase,(c.out/'metadata_report.json').read_bytes())
        self.assertEqual(c.budget.status()['requests_charged'],2)

    def test_distinct_custom_budget_files_cannot_share_receipts(self):
        first=self.corpus();first.collect()
        second=pc.Corpus(self.root/'separate',feeds={'publisher':self.url},
            budget_path=self.root/'separate_budget.jsonl',opener=self.http)
        second.collect()
        self.assertNotEqual(first.cache,second.cache)
        self.assertEqual(first.budget.status()['requests_charged'],1)
        self.assertEqual(second.budget.status()['requests_charged'],1)
        self.assertEqual(len(self.http.calls),2)

    def test_failures_and_rate_limits_remain_charged_without_retry(self):
        self.http.data[self.url]=urllib.error.HTTPError(self.url,429,'rate limited',None,None)
        c=self.corpus();r=c.collect();c.collect()
        self.assertEqual(len(self.http.calls),1);self.assertEqual(r['deduplicated_episodes'],0)
        status=c.budget.status();self.assertEqual(status['requests_charged'],1)
        self.assertEqual(status['body_bytes_charged_upper_bound'],2*pc.MiB)
        state=json.loads((c.out/'metadata.json').read_text())['feed_states'][0]
        self.assertEqual(state['http_status'],429);self.assertFalse(state['complete_body'])

    def test_interrupted_reservation_is_not_a_new_attempt_after_restart(self):
        self.http.data[self.url]=KeyboardInterrupt()
        c=self.corpus()
        with self.assertRaises(KeyboardInterrupt):c.collect()
        self.http.data[self.url]=rss([item()]);r=self.corpus().collect()
        self.assertEqual(len(self.http.calls),1);self.assertEqual(r['deduplicated_episodes'],0)
        states=json.loads((c.out/'metadata.json').read_text())['feed_states']
        self.assertEqual(states[0]['state'],'PENDING_PRIOR_ATTEMPT_NO_RETRY')
        self.assertEqual(len(c.budget.status()['pending']),1)

    def test_exact_byte_cap_is_not_a_complete_body_claim(self):
        c=self.corpus();self.http.data[self.url]=b'x'*100
        r,raw=c.capture(self.url,'rss',64)
        self.assertEqual(len(raw),64);self.assertEqual(r['accepted_body_bytes'],64)
        self.assertFalse(r['complete_body']);self.assertEqual(r['outcome'],'failure')
        c.capture(self.url,'rss',64);self.assertEqual(len(self.http.calls),1)
        with self.assertRaises(ValueError):c.capture(self.url,'rss',65)

    def test_raw_metadata_and_plan_tampering_never_dispatches_new_source(self):
        c=self.corpus();c.collect()
        p=c.out/'metadata.json';original=p.read_bytes();p.write_bytes(original+b' ')
        with self.assertRaises(ValueError):c.collect(texts=True)
        p.write_bytes(original);c.collect(texts=True)
        p=c.out/'text_plan.json';plan=json.loads(p.read_text());plan[0]['transcript']='https://other.example/t.srt';p.write_bytes(pc.encoded(plan))
        with self.assertRaises(ValueError):c.collect(texts=True)
        self.assertEqual(len(self.http.calls),2)

    def test_raw_cache_drift_does_not_refetch_or_overwrite(self):
        c=self.corpus();c.collect();path=next(c.cache.glob('*.body'));path.write_bytes(b'corrupt')
        with self.assertRaises(ValueError):c.collect()
        self.assertEqual(len(self.http.calls),1)

    def test_media_redirect_and_private_urls_are_not_followed(self):
        for url in ('file:///etc/passwd','https://localhost./x','https://127.0.0.1/a','http://[::1]/a',
                    'https://user:pass@publisher.example/a','https://publisher.example:22/a'):
            with self.assertRaises(ValueError):pc.public_url(url)
        c=self.corpus()
        with self.assertRaises(ValueError):c.capture('https://publisher.example/a.mp3','text',100)
        self.assertEqual(len(self.http.calls),0)
        self.http.data[self.url]=urllib.error.HTTPError(self.url,302,'redirect',{'Location':'https://other.example/rss'},None)
        r=c.collect();self.assertEqual(len(self.http.calls),1);self.assertEqual(r['deduplicated_episodes'],0)

    def test_unknown_text_schema_stays_failed_instead_of_empty_success(self):
        self.http.data['https://publisher.example/text.srt']=(b'{"error":"subscription required"}','application/json')
        c=self.corpus();c.collect();r=c.collect(texts=True)
        self.assertEqual(r['native_texts_parsed'],0)
        self.assertFalse((c.out/'subs').exists())
        state=json.loads((c.out/'native_texts.json').read_text())[0]
        self.assertEqual(state['parse_state'],'UNSUPPORTED_OR_INVALID_TEXT')

    def test_dedup_keeps_distinct_dates_reused_links_and_source_aliases(self):
        a=dp.parse_episodes('one',rss([item()]))[0]
        b={**a,'feed':'two','key':dp.key('two','one')}
        result=pc.deduplicate([a,b]);self.assertEqual(len(result),1);self.assertEqual(result[0]['origin_count'],2)
        self.assertIn('title',result[0]['origins'][0]);self.assertIn('pub_utc',result[0]['origins'][0])
        b={**a,'key':'different','guid':'another','pub_utc':'2026-10-25T09:00:00Z'}
        result=pc.deduplicate([a,b]);self.assertEqual(len(result),2)
        self.assertTrue(all(r['ambiguous_episode_link'] for r in result))
        no_guid=rss(['<item><title>Weekly</title><pubDate>Mon, 26 Oct 2026 09:00:00 GMT</pubDate></item>',
                     '<item><title>Weekly</title><pubDate>Mon, 19 Oct 2026 09:00:00 GMT</pubDate></item>'])
        rows=dp.parse_episodes('one',no_guid);self.assertNotEqual(rows[0]['key'],rows[1]['key'])

    def test_bad_duration_and_partial_transcript_schemas_are_explicit(self):
        for value in ('1:xx:30','NaN','-20','1:70:00','1:02:03:04'):
            self.assertIsNone(dp.seconds(value))
        for raw in (b'{"error":"denied"}',b'[]',b'{"segments":[]}',b'{"segments":[{"body":null}]}'):
            with self.assertRaises(ValueError):dp.transcript_text(raw,'application/json')
        self.assertEqual(dp.transcript_text(b'{"segments":[{"text":"Funding matters"}]}','application/json'),'Funding matters')
        self.assertNotIn('not speech',dp.transcript_text(b'WEBVTT\n\nNOTE not speech\nmore note\n\n00:00 --> 00:01\nCarry works\n','text/vtt'))
        with self.assertRaises(ValueError):dp.transcript_text(b'<form><input type="password">Sign in to read</form>','text/html')


if __name__=='__main__':unittest.main()
