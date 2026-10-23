"""Browser checks with a synthetic host adapter; no Artifact service or market data."""
import json
from contextlib import ExitStack
from pathlib import Path
import shutil
import unittest

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


@unittest.skipUnless(sync_playwright and shutil.which("chromium"), "Playwright and system chromium required")
class DashboardView(unittest.TestCase):
    def test_filters_stable_ids_and_missing_cumulative_returns(self):
        html = (Path(__file__).resolve().parents[1] / "dashboard/index.html").read_text()
        data = {
            "jobs": [dict(key="R215", task_id="R215", display_name="MEXC positioning books",
                          category="Prospective paper", state="UNKNOWN", ok=None, stale=False,
                          status_source="legacy_log", log_path="experiments/mexc_fwd/tick.log"),
                     dict(key="REC_TICKER", task_id="REC_TICKER", display_name="MEXC ticker snapshots",
                          category="Market data collection", state="SUCCESS", ok=True, stale=False,
                          status_source="orchestrator", returncode=0)],
            "methods": [dict(id="M001", method="Positioning impulse", status="BLOCKED", data_held="P",
                             note="Missing publication timestamps", source="primary source"),
                        dict(id="M002", method="Reversal control", status="UNTESTED", data_held="Y")],
            "data_sources": [dict(source="mexc", display_name="MEXC forward-data cache",
                                  category="Prospective collection", inventory_state="PARTIAL",
                                  files=1, size_gb=0, age_h=1, stale=None, skipped_links=1,
                                  scan_errors=0, provenance=False),
                             dict(source="mexc_hist", display_name="MEXC historical futures",
                                  category="Historical market data", inventory_state="COMPLETE",
                                  files=2, size_gb=0, age_h=1, stale=None, skipped_links=0,
                                  scan_errors=0, provenance=True)],
            "forward_lanes": [], "rounds": [], "candidates": [], "event_tickets": []}
        harness = """<script>
        const fixture = DATA;
        window.calcFns = {};
        window.d3 = {format: () => (v) => String(v), utcFormat: () => (v) => v.toISOString()};
        window.dash = {
          calc: (id, config) => { calcFns[id] = config.fn; },
          data: (id) => Object.hasOwn(fixture, id) ? {status: 'ok', data: fixture[id]} : {status: 'loading'},
          onData: (fn) => { window.fireData = fn; }, setLink: () => {}, colors: ['blue']
        };
        </script>""".replace("DATA", json.dumps(data))
        with ExitStack() as stack:
            p = stack.enter_context(sync_playwright())
            browser = p.chromium.launch(executable_path=shutil.which("chromium"), headless=True,
                                        args=["--no-sandbox"])
            stack.callback(browser.close)
            page = browser.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.set_content(harness + html)
            page.get_by_role("tab", name="Data and loop").click()
            self.assertEqual(page.locator("#tbl-jobs tbody tr").count(), 2)
            page.get_by_label("Operation category").select_option("Prospective paper")
            self.assertEqual(page.locator("#tbl-jobs tbody tr").count(), 1)
            self.assertIn("R215", page.locator("#tbl-jobs tbody").inner_text())
            page.get_by_label("Search operations").fill("REC_TICKER")
            self.assertEqual(page.locator("#tbl-jobs tbody tr").count(), 0)
            page.get_by_label("Operation category").select_option("")
            self.assertEqual(page.locator("#tbl-jobs tbody tr").count(), 1)
            page.get_by_role("tab", name="Method queue").click()
            page.get_by_label("Method status").select_option("BLOCKED")
            page.get_by_label("Search methods", exact=True).fill("publication")
            self.assertEqual(page.locator("#tbl-methods tbody tr").count(), 1)
            self.assertIn("Missing publication timestamps", page.locator("#tbl-methods tbody").inner_text())
            page.get_by_role("tab", name="Data and loop").click()
            self.assertEqual(page.locator("#tbl-data tbody tr").count(), 2)
            page.get_by_label("Data category", exact=True).select_option("Prospective collection")
            page.get_by_label("Inventory state", exact=True).select_option("PARTIAL")
            self.assertEqual(page.locator("#tbl-data tbody tr").count(), 1)
            self.assertIn("unknown", page.locator("#tbl-data tbody").inner_text())
            self.assertIn("mexc", page.locator("#tbl-data tbody").inner_text())
            result = page.evaluate("""() => calcFns.cum_paper([
              {series:'A',day:'2026-01-01',net:0.01},
              {series:'A',day:'2026-01-02',net:null},
              {series:'A',day:'2026-01-03',net:0.02},
              {series:'B',day:'2026-01-01',net:0}
            ]).map(r => r.cum_pct)""")
            self.assertEqual(result, [1, None, None, 0])
            self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
