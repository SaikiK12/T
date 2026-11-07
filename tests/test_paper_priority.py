from contextlib import contextmanager
from email.message import Message
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from urllib import error, request

from lab.paper_transport import InheritedBudget, TransportStop, content_bytes, fence
from scripts import quant_runtime_v2 as runtime

URL = "https://public.test/feed"


class Reply(io.BytesIO):
    def __init__(self, raw, *, status=200, encoding="", content_type="application/json"):
        super().__init__(raw)
        self.code, self.url = status, URL
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        self.headers["Content-Length"] = str(len(raw))
        if encoding:
            self.headers["Content-Encoding"] = encoding


class PaperTransport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.baseline = self.root / "legacy.jsonl"
        self.frozen = self.root / "baseline.jsonl"
        raw = b'{"event":"START","id":"0","reserved_bytes":100}\n{"event":"END","id":"0","charged_bytes":90}\n'
        self.baseline.write_bytes(raw)
        self.frozen.write_bytes(raw)
        self.folder = self.root / "network"
        self.policy = dict(prefixes=[URL], wire_caps={URL: 1024}, max_requests=10,
                           max_body_bytes=10000, max_decoded_bytes=4096)

    @contextmanager
    def intercepted(self, reply=None, opener=None):
        fake = opener or (lambda _self, req, *a, **kw: reply)
        with patch.object(request.OpenerDirector, "open", fake):
            with fence(self.folder, self.policy, baseline=self.baseline, frozen_baseline=self.frozen):
                yield

    def budget(self):
        return InheritedBudget(self.folder, dict(self.policy, response_cap=1024), self.baseline, self.frozen)

    def test_gzip_is_exact_content_with_wire_and_content_hashes(self):
        content = b'{"value":"1.234567890123456789","empty":null}'
        wire = gzip.compress(content, mtime=0)
        seen = []
        def opener(_self, req, *a, **kw):
            seen.append(req.get_header("Accept-encoding"))
            return Reply(wire, encoding="gzip")
        with self.intercepted(opener=opener):
            with request.urlopen(URL) as r:
                self.assertEqual(r.read(), content)
                self.assertIsNone(r.headers.get("Content-Encoding"))
                self.assertEqual(r.headers.get("content-type"), "application/json")
        self.assertEqual(seen, ["gzip"])
        self.assertEqual(self.budget().usage(), (2, 90 + len(wire)))
        row = next(x for x in self.budget().records() if x["event"] == "CONTENT")
        self.assertEqual(row["wire_sha256"], hashlib.sha256(wire).hexdigest())
        self.assertEqual(row["content_sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(gzip.decompress((self.folder / row["stored_wire"]).read_bytes()), wire)

    def test_identity_is_charged_and_not_reserialized(self):
        raw = b'{ "value" : "0001" }'
        with self.intercepted(Reply(raw)):
            self.assertEqual(request.urlopen(URL).read(), raw)
        self.assertEqual(self.budget().usage(), (2, 90 + len(raw)))

    def test_old_spend_and_new_reservation_must_fit_before_http(self):
        self.policy["max_body_bytes"] = 90 + 1024
        calls = []
        with self.intercepted(opener=lambda *a, **kw: calls.append(1)):
            with self.assertRaises(TransportStop):
                request.urlopen(URL)
        self.assertEqual(calls, [])
        self.assertEqual(self.budget().usage(), (1, 90))

    def test_old_request_count_is_not_reset(self):
        self.policy["max_requests"] = 1
        with self.intercepted(Reply(b"{}")), self.assertRaises(TransportStop):
            request.urlopen(URL)
        self.assertEqual(self.budget().usage(), (1, 90))

    def test_uncertain_old_reservation_is_not_shrunk_to_the_new_response_cap(self):
        with self.baseline.open("ab") as f:
            f.write(b'{"event":"START","id":"1","reserved_bytes":4096}\n')
        self.policy["wire_caps"][URL] = 32
        with self.intercepted(Reply(b'{}')):
            self.assertEqual(request.urlopen(URL).read(), b'{}')
        self.assertEqual(self.budget().usage(), (3, 90 + 4096 + 2))

    def test_cut_new_journal_refuses_before_network(self):
        self.folder.mkdir()
        (self.folder / "requests.jsonl").write_bytes(b'{"event":"START","id":"1","reserved_bytes":100}')
        calls = []
        with self.intercepted(opener=lambda *a, **kw: calls.append(1)), self.assertRaises(TransportStop):
            request.urlopen(URL)
        self.assertFalse(calls)

    def test_missing_or_divergent_old_ledger_never_creates_a_fresh_budget(self):
        self.baseline.write_bytes(b'{}\n')
        with self.intercepted(Reply(b"{}")), self.assertRaises(TransportStop):
            request.urlopen(URL)

    def test_absent_baseline_cannot_be_swallowed_as_an_ordinary_network_error(self):
        with self.intercepted(Reply(b"{}")), patch.object(Path, "read_bytes", side_effect=FileNotFoundError()):
            with self.assertRaises(TransportStop):
                try:
                    request.urlopen(URL)
                except Exception:
                    self.fail("legacy handler swallowed missing budget")

    def test_legacy_source_block_is_inherited(self):
        with self.baseline.open("ab") as f:
            f.write(b'{"event":"BLOCK","key":"public.test/feed","reason":"prior denial"}\n')
        with self.intercepted(Reply(b"{}")), self.assertRaises(TransportStop):
            request.urlopen(URL)
        self.assertEqual(self.budget().usage(), (1, 90))

    def test_denial_body_is_preserved_and_next_attempt_never_reaches_network(self):
        calls = []
        def denied(_self, req, *a, **kw):
            calls.append(1)
            raise error.HTTPError(URL, 451, "denied", Message(), io.BytesIO(b"denied body"))
        with self.intercepted(opener=denied):
            for _ in range(2):
                with self.assertRaises(TransportStop):
                    request.urlopen(URL)
        self.assertEqual(len(calls), 1)
        self.assertEqual(gzip.decompress((self.folder / "raw/1.wire.gz").read_bytes()), b"denied body")

    def test_wire_overrun_and_large_inflation_stop_before_native_read(self):
        self.policy["wire_caps"][URL] = 32
        with self.intercepted(Reply(b"x" * 50)), self.assertRaises(TransportStop):
            request.urlopen(URL)
        self.assertEqual(self.budget().usage(), (2, 90 + 33))
        with self.assertRaises(TransportStop):
            content_bytes(gzip.compress(b"x" * 5000), "gzip", 4096)

    def test_cut_or_concatenated_gzip_not_silently_partially_decoded(self):
        raw = gzip.compress(b"{}")
        for wire in (raw[:-2], raw + raw):
            with self.subTest(wire=wire), self.assertRaises(TransportStop):
                content_bytes(wire, "gzip", 100)

    def test_public_json_error_aborts_even_inside_legacy_exception_handler(self):
        with self.intercepted(Reply(b'{"error":{"code":1}}')):
            with self.assertRaises(TransportStop):
                try:
                    request.urlopen(URL)
                except Exception:
                    self.fail("legacy retry handler swallowed a source stop")

    def test_invalid_json_and_html_are_blocked(self):
        with self.intercepted(Reply(b"<html>blocked</html>", content_type="text/html")), self.assertRaises(TransportStop):
            request.urlopen(URL)
        self.assertTrue(any(r["event"] == "BLOCK" for r in self.budget().records()))

    def test_mislabeled_html_and_business_error_code_are_not_market_data(self):
        for body in [b'<html>blocked</html>', b'{"code":1002,"data":[]}']:
            with self.subTest(body=body), self.intercepted(Reply(body)), self.assertRaises(TransportStop):
                request.urlopen(URL)

    def test_incomplete_content_length_keeps_the_full_reservation(self):
        reply = Reply(b'{}')
        reply.headers.replace_header("Content-Length", "100")
        with self.intercepted(reply), self.assertRaises(TransportStop):
            request.urlopen(URL)
        self.assertEqual(self.budget().usage(), (2, 90 + 1025))

    def test_redirect_never_reaches_the_target_and_persists_a_stop(self):
        calls = []
        def redirected(_self, req, *a, **kw):
            calls.append(req.full_url)
            request.HTTPRedirectHandler().redirect_request(req, None, 302, "redirect", Message(), "https://elsewhere.test/")
        with self.intercepted(opener=redirected), self.assertRaises(TransportStop):
            request.urlopen(URL)
        self.assertEqual(calls, [URL])
        self.assertTrue(any(x["event"] == "BLOCK" for x in self.budget().records()))

    def test_auth_browser_spoof_post_and_unregistered_url_are_refused(self):
        requests = [request.Request(URL, headers={"Authorization": "invented"}),
                    request.Request(URL, headers={"User-Agent": "Mozilla/5.0"}),
                    request.Request(URL, data=b"{}"), request.Request("https://elsewhere.test/")]
        calls = []
        with self.intercepted(opener=lambda *a, **kw: calls.append(1)):
            for req in requests:
                with self.subTest(req=req), self.assertRaises(TransportStop):
                    request.urlopen(req)
        self.assertEqual(calls, [])

    def test_network_loss_retains_full_new_reservation(self):
        def lost(*a, **kw):
            raise OSError("synthetic lost connection")
        with self.intercepted(opener=lost), self.assertRaises(TransportStop):
            request.urlopen(URL)
        self.assertEqual(self.budget().usage(), (2, 90 + 1025))


class Migration(unittest.TestCase):
    def test_foreign_host_cannot_migrate(self):
        with patch.dict("os.environ", {"GITHUB_ACTIONS": "false"}), self.assertRaises(ValueError):
            runtime.migrate({}, Path("unused"), "fixture")

    def test_unfinished_predecessor_blocks_activation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            state, lane = root / "state", root / "lane"
            state.mkdir();lane.mkdir()
            legacy = root / runtime.LEGACY
            legacy.mkdir(parents=True)
            (legacy / "dispatch.jsonl").write_text('{"event":"RUNNING"}\n')
            with patch.object(runtime, "ROOT", root), patch.object(runtime, "LANE", lane), \
                    patch.object(runtime, "verify", return_value=("a" * 64, {})), \
                    patch.object(runtime, "restore", return_value={"active_contract": "R420"}), \
                    patch.dict("os.environ", {"GITHUB_ACTIONS": "true"}), self.assertRaisesRegex(ValueError, "unfinished"):
                runtime.migrate({}, state, "fixture")
            self.assertFalse((state / "manifest.json").exists())

    def test_successful_migration_selects_contract_and_persists_before_http(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d);state = root / "state";lane = root / "lane"
            state.mkdir();lane.mkdir()
            legacy = root / runtime.LEGACY
            (legacy / "network/aux").mkdir(parents=True)
            raw = b'{"event":"END"}\n'
            (legacy / "dispatch.jsonl").write_text('{"event":"FINISHED"}\n')
            (legacy / "network/aux/requests.jsonl").write_bytes(raw)
            (lane / "baseline_aux_requests.jsonl").write_bytes(raw)
            def saved(*args, **kwargs):
                self.assertEqual(json.loads((state / "manifest.json").read_text())["active_contract"], "R422")
                self.assertTrue((root / runtime.OPS / "migrations/fixture.json").exists())
            with patch.object(runtime, "ROOT", root), patch.object(runtime, "LANE", lane), \
                    patch.object(runtime, "verify", return_value=("a" * 64, {})), \
                    patch.object(runtime, "restore", return_value={"active_contract": "R420"}), \
                    patch.object(runtime, "snapshot", side_effect=saved) as snap, \
                    patch.object(runtime.subprocess, "check_output", return_value="synthetic\n"), \
                    patch.dict("os.environ", {"GITHUB_ACTIONS": "true"}):
                r = runtime.migrate({}, state, "fixture")
            self.assertEqual(r["source_http_requests"], 0)
            snap.assert_called_once()
            self.assertEqual((legacy / "network/aux/requests.jsonl").read_bytes(), raw)

    def test_successful_legacy_paper_hour_is_not_attempted_twice(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            old = root / runtime.LEGACY
            old.mkdir(parents=True)
            hour = runtime.datetime.now(runtime.timezone.utc).strftime("%Y%m%dT%H")
            (old / "latest.json").write_text(json.dumps({"hour": hour, "tasks": [{"id": "R413", "state": "PROCESS_OK"}]}))
            cfg = {"tasks": [{"id": "R413", "script": "scripts/forward_boroslock.py", "policy": "aux", "args": []}]}
            with patch.object(runtime, "ROOT", root), patch.object(runtime.previous, "child") as called:
                runtime.child("scripts/forward_boroslock.py", "aux", [], cfg)
            called.assert_not_called()

    def test_composed_runtime_prepares_commits_and_finishes_a_synthetic_hour(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d);root = base / "root";state = base / "state";lane = base / "lane"
            for p in (root, state, lane):
                p.mkdir()
            def git(folder, *args):
                return subprocess.check_output(["git", *args], cwd=folder, stderr=subprocess.DEVNULL)
            for folder in (root, state):
                git(folder, "init", "-q")
                (folder / "fixture").write_text("synthetic only\n")
                git(folder, "add", "fixture")
                git(folder, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture")
            old = root / runtime.LEGACY
            (old / "network/aux").mkdir(parents=True)
            (old / "dispatch.jsonl").write_text('{"event":"FINISHED"}\n')
            raw = b'{"event":"START","id":"0","reserved_bytes":100}\n{"event":"END","id":"0","charged_bytes":90}\n'
            (old / "network/aux/requests.jsonl").write_bytes(raw)
            (lane / "baseline_aux_requests.jsonl").write_bytes(raw)
            manifest = {"schema": 1, "owner": "github-actions", "active_contract": "R420", "bootstrap": False, "files": {}}
            (state / "manifest.json").write_text(json.dumps(manifest))
            cfg = {"state_prefixes": [runtime.LEGACY, runtime.OPS], "max_stored_bytes": 1000000,
                   "health_lanes": {}, "blocked": {}, "start": "2020-01-01", "end": "2099-01-01",
                   "tasks": [{"id": "SYNTHETIC", "script": "unused.py", "policy": "aux", "args": [], "timeout": 1}]}
            names = ["OPS", "LANE", "verify", "run_child", "fence", "ROOT"]
            original = {k: getattr(runtime.previous, k) for k in names}
            with patch.multiple(runtime.previous, **original), patch.object(runtime, "ROOT", root), \
                    patch.object(runtime, "LANE", lane), patch.object(runtime, "verify", return_value=("a" * 64, {})), \
                    patch.dict("os.environ", {"GITHUB_ACTIONS": "true"}):
                runtime.compose()
                runtime.previous.ROOT = root
                runtime.migrate(cfg, state, "fixture")
                runtime.previous.prepare(cfg, state, "fixture")
                git(state, "add", ".")
                git(state, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "checkpoint")
                with patch.object(runtime.previous, "run_child", return_value={"state": "PROCESS_OK", "returncode": 0}) as child:
                    report = runtime.previous.execute(cfg, state, "fixture")
                child.assert_called_once()
            self.assertEqual(report["prereg_sha256"], "a" * 64)
            events = [json.loads(x)["event"] for x in (root / runtime.OPS / "dispatch.jsonl").read_text().splitlines()]
            self.assertEqual(events, ["PREPARED", "RUNNING", "FINISHED"])
            self.assertEqual((old / "network/aux/requests.jsonl").read_bytes(), raw)
            self.assertEqual(json.loads((state / "manifest.json").read_text())["active_contract"], "R422")


if __name__ == "__main__":
    unittest.main()
