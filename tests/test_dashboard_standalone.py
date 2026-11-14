"""Verify portable bundles and browser behavior using invented export rows."""
import contextlib
import functools
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from unittest.mock import patch

from scripts import dashboard_data as export
from scripts import build_dashboard_standalone as standalone

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

D3 = standalone.ROOT/'dashboard/vendor/d3.v7.9.0.min.js'
D3_SHA = 'f2094bbf6141b359722c4fe454eb6c4b0f0e42cc10cc7af921fc158fceb86539'


def fixture(root):
    fake=root/'source';out=fake/'dashboard/data'
    sets={key:[] for key in export.TITLES}
    sets['program']=[dict(strict_ontime_days=3,program_trials=0,rounds=0,null=0,partial=0,
                          confirmed=0,running=0,candidates=0,generated_at='2026-11-04T00:00:00Z')]
    sets['jobs']=[dict(key='REC_FIXTURE',task_id='REC_FIXTURE',display_name='Invented recorder',
                      category='Market data collection',state='UNKNOWN',ok=None,stale=None,
                      status_source='fixture',returncode=None,log_path=None)]
    sets['methods']=[dict(id='M001',method='Invented method',status='BLOCKED',data_held='N',
                         note='Missing receipt clock',source='invented fixture'),
                     dict(id='M002',method='Invented control',status='UNTESTED',data_held='Y')]
    with patch.multiple(export,ROOT=fake,OUT=out):
        manifest=export.publish_sets(sets,'2026-11-04T00:00:00Z')
    return out/'generations'/manifest['generation'],manifest


class StandaloneBundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.source,self.manifest=fixture(self.root)
        self.generation=self.manifest['generation'];self.out=self.root/'bundle'

    def build(self,out=None):
        return standalone.build(self.source,self.generation,D3,D3_SHA,out)

    def test_plan_is_read_only_and_build_reuses_existing_view_with_pinned_assets(self):
        before={p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in self.source.iterdir()}
        plan=self.build();self.assertEqual(plan['state'],'PLAN');self.assertFalse(self.out.exists())
        self.assertEqual(before,{p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in self.source.iterdir()})
        built=self.build(self.out);self.assertEqual(built['state'],'BUILT')
        html=(self.out/'index.html').read_bytes()
        self.assertIn((standalone.ROOT/'dashboard/index.html').read_bytes(),html)
        self.assertIn(b'dash.start()',html);self.assertIn(b'integrity="sha256-',html)
        self.assertEqual(hashlib.sha256((self.out/'assets/d3.js').read_bytes()).hexdigest(),D3_SHA)
        manifest=json.loads((self.out/'bundle-manifest.json').read_bytes())
        for name,identity in manifest['files'].items():
            body=(self.out/name).read_bytes()
            self.assertEqual(hashlib.sha256(body).hexdigest(),identity['sha256'])
            self.assertEqual(len(body),identity['bytes'])
        with self.assertRaises(FileExistsError):self.build(self.out)

    def test_tampered_export_is_refused_before_any_output_publication(self):
        (self.source/'methods.json').write_text('[]')
        with self.assertRaisesRegex(ValueError,'SHA256'):self.build(self.out)
        self.assertFalse(self.out.exists());self.assertFalse(list(self.root.glob('.dashboard-*')))

    def test_incomplete_generation_and_bad_d3_identity_are_refused(self):
        with self.assertRaisesRegex(ValueError,'D3 asset SHA256'):
            standalone.build(self.source,self.generation,D3,'0'*64,self.out)
        (self.source/'jobs.json').unlink()
        with self.assertRaises(OSError):self.build(self.out)
        self.assertFalse(self.out.exists())

    def test_manifest_paths_and_symlink_sources_are_not_followed(self):
        p=self.source/'manifest.json';m=json.loads(p.read_bytes())
        m['sets']['methods']['file']='../../private.json';p.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'path'):self.build(self.out)
        p.write_text(json.dumps(self.manifest))
        (self.source/'methods.json').rename(self.source/'original.json')
        (self.source/'methods.json').symlink_to(self.source/'original.json')
        with self.assertRaises(OSError):self.build(self.out)

    def test_duplicate_json_nonfinite_and_non_row_arrays_are_rejected(self):
        for raw in (b'{"x":1,"x":2}',b'[NaN]',b'[1e999]'):
            with self.assertRaises(ValueError):standalone._json(raw)
        for rows in ([1],[[]],[{'large':2**60}]):
            with self.assertRaises(ValueError):standalone._rows(rows)

    def test_cli_defaults_to_plan_and_requires_explicit_paired_build_arguments(self):
        args=['--export-dir',str(self.source),'--generation',self.generation,
              '--d3-asset',str(D3),'--d3-sha256',D3_SHA]
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(standalone.main(args),0)
        self.assertEqual(json.loads(out.getvalue())['state'],'PLAN')
        self.assertFalse(self.out.exists())


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass


@unittest.skipUnless(sync_playwright and shutil.which('chromium'),'Playwright and system Chromium required')
class StandaloneBrowserTests(unittest.TestCase):
    def test_real_pinned_d3_adapter_filters_unknowns_and_integrity_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source,manifest=fixture(root);bundle=root/'bundle'
            standalone.build(source,manifest['generation'],D3,D3_SHA,bundle)
            server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(bundle)))
            thread=threading.Thread(target=lambda:server.serve_forever(poll_interval=.05),daemon=True);thread.start()
            try:
                with sync_playwright() as p:
                    browser=p.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox'])
                    try:
                        page=browser.new_page();errors=[];requests=[]
                        page.on('pageerror',lambda error:errors.append(str(error)))
                        page.on('request',lambda request:requests.append(request.url))
                        url=f'http://127.0.0.1:{server.server_port}/index.html#health'
                        page.goto(url);page.wait_for_function("document.querySelector('#standalone-status').dataset.state === 'ok'")
                        self.assertEqual(page.locator('#tbl-jobs tbody tr').count(),1)
                        self.assertIn('UNKNOWN',page.locator('#tbl-jobs tbody').inner_text())
                        self.assertEqual(page.locator('#kpi-ontime .val').inner_text(),'3')
                        page.get_by_role('tab',name='Method queue').click()
                        page.get_by_label('Method status').select_option('BLOCKED')
                        self.assertEqual(page.locator('#tbl-methods tbody tr').count(),1)
                        self.assertIn('M001',page.locator('#tbl-methods tbody').inner_text())
                        self.assertTrue(page.evaluate("Object.isFrozen(dash.data('methods').data)"))
                        result=page.evaluate("""() => {
                          dash.calc('test_count',{inputs:['methods'],fn:rows=>[{n:rows.length}]});
                          dash.calc('cycle_a',{inputs:['cycle_b'],fn:x=>x});
                          dash.calc('cycle_b',{inputs:['cycle_a'],fn:x=>x});
                          dash.calc('bad_value',{inputs:['methods'],fn:()=>[{n:NaN}]});
                          return {count:dash.data('test_count').data[0].n,cycle:dash.data('cycle_a').status,
                                  bad:dash.data('bad_value').status,missing:dash.data('unlisted').status};
                        }""")
                        self.assertEqual(result,dict(count=2,cycle='error',bad='error',missing='missing'))
                        self.assertEqual(errors,[])
                        self.assertTrue(all(u.startswith(f'http://127.0.0.1:{server.server_port}/') for u in requests))
                        (bundle/'data/methods.json').write_text('[]')
                        page.reload();page.wait_for_function("document.querySelector('#standalone-status').dataset.state === 'error'")
                        self.assertEqual(page.evaluate("dash.data('methods').status"),'error')
                        self.assertIn('failed verification',page.locator('#standalone-status').inner_text())
                    finally:browser.close()
            finally:server.shutdown();server.server_close();thread.join(timeout=2)


if __name__=='__main__':unittest.main()
