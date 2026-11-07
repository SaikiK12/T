import csv
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.repository_index import trace

try:
    from playwright.sync_api import sync_playwright
except ImportError:sync_playwright=None


class EvidenceTraceTests(unittest.TestCase):
    def test_trace_uses_canonical_records_and_hash_metadata_without_opening_market_or_outcomes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'registry').mkdir();lane=root/'experiments/example';lane.mkdir(parents=True)
            for name,rows in [('methods.csv',[{'id':'M1','method':'example','rid':'R2 PARTIAL'}]),
                              ('rounds.csv',[{'id':'R2','lane':'example','status':'DONE','verdict':'PARTIAL','trials':'4','prereg_sha':'b'*64}])]:
                with (root/'registry'/name).open('w',newline='') as h:
                    w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
            (lane/'code_inputs.json').write_text(json.dumps({'sha256':{'data/not-opened.parquet':'a'*64}}))
            (lane/'PREREG.md').write_text('# exact test')
            (lane/'FINDINGS.md').write_bytes(b'\xff not read as a result')
            files=['experiments/example/'+x for x in ('code_inputs.json','PREREG.md','FINDINGS.md')]
            z=trace(root,'M1',files);self.assertEqual(z['rounds'][0]['id'],'R2')
            self.assertEqual(z['rounds'][0]['identities'][0]['reported_sha256'],'a'*64)
            self.assertFalse(z['rounds'][0]['identities'][0]['identity_reverified'])
            with self.assertRaises(ValueError):trace(root,'../M1',files)
            with self.assertRaises(ValueError):trace(root,'M999',files)


@unittest.skipUnless(sync_playwright and shutil.which('chromium'),'Playwright and system chromium required')
class PaperViewTests(unittest.TestCase):
    def test_paper_view_keeps_missing_money_unknown_currency_separate_and_reproduction_inert(self):
        html=(Path(__file__).resolve().parents[1]/'dashboard/index.html').read_text()
        data={'paper_accounts':[{'venue':'mexc','asset':'USDT','initial_cash':'5000','fees_paid':'0',
            'realized_net_pnl':'-2','observed_net_pnl':None,'evidence_mode':'invented_validation',
            'source_report':'fixture','report_sha256':'a'*64,'source_input_sha256':'b'*64},
            {'venue':'lighter','asset':'USDC','initial_cash':'5000','observed_net_pnl':None}],
            'paper_controls':[{'cost_multiple':2,'expected_gross_quote':None,'expected_net_lower_quote':None,
                'calibrated_error_quote':None,'risk_state':'HALTED','missing_input':'<img src=x onerror=alert(1)>',
                'reproduce':'python -m lab account --controls --out /tmp/R320-reproduction'}],
            'paper_admission':[{'series':'old','reported_rows':3,'native_ontime_labels':2,
                'strict_executable_scored_days':0,'strict_net_return':None,'missing_inputs':['source-bound fees']}],
            'paper_requirements':[{'id':12,'text':'Event notional','state':'blocked','reason':'No index proof'}]}
        harness='''<script>const fixture=DATA;
        window.d3={format:()=>String,utcFormat:()=>String};
        window.dash={calc:()=>{},data:id=>Object.hasOwn(fixture,id)?{status:'ok',data:fixture[id]}:{status:'loading'},onData:()=>{},setLink:()=>{},colors:['blue']};</script>'''.replace('DATA',json.dumps(data))
        with sync_playwright() as p:
            b=p.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox'])
            try:
                page=b.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.set_content(harness+html);page.get_by_role('tab',name='Compte simulé',exact=True).click()
                rows=page.locator('#paper-accounts tbody tr');self.assertEqual(rows.count(),2)
                self.assertIn('USDT',rows.nth(0).inner_text());self.assertIn('USDC',rows.nth(1).inner_text())
                self.assertEqual(rows.nth(0).locator('td').last.inner_text(),'inconnu')
                self.assertIn('inconnu',page.locator('#paper-controls').inner_text())
                self.assertEqual(page.locator('#paper-controls img').count(),0)
                page.get_by_text('Source et reproduction vérifiable',exact=True).click()
                self.assertEqual(page.locator('#paper-provenance code').inner_text(),data['paper_controls'][0]['reproduce'])
                self.assertIn('inconnu',page.locator('#paper-admission').inner_text())
                self.assertIn('bloqué',page.locator('#paper-coverage').inner_text());self.assertEqual(errors,[])
            finally:b.close()
