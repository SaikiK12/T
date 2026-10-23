"""Invented observations, faults and publication races; no network or market data."""
from contextlib import redirect_stdout
from dataclasses import replace
import csv
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import threading
import unittest
from unittest.mock import patch

import pandas as pd

from lab import operations, runtime
from lab import __main__ as cli
from scripts import build_engine, check, dashboard_data, dashboard_perf, panel


class ObservationChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.journal = self.root / "experiments/flow72_fwd2/journal"
        self.journal.mkdir(parents=True)

    def signals(self, rows, ticks):
        for name, fields, values in (("signals.csv", ["t", "symbol"], rows),
                                      ("ticks.csv", ["t", "n_elig"], ticks)):
            with (self.journal / name).open("w", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(fields)
                writer.writerows(values)

    def test_bootstrap_is_allowed_before_writer_but_not_claimed_complete(self):
        self.assertTrue(runtime.check("flow_signals", self.root, phase="before")["usable"])
        self.assertFalse(runtime.check("flow_signals", self.root)["usable"])
        (self.journal / "status.json").write_text("{}")
        self.assertFalse(runtime.check("flow_signals", self.root, phase="before")["usable"])

    def test_complete_batch_has_bound_content_receipts(self):
        self.signals([(0, "A"), (0, "B")], [(0, 2)])
        receipt = runtime.check("flow_signals", self.root)
        self.assertEqual(receipt["state"], "COMPLETE")
        self.assertEqual(receipt["hours"], 1)
        self.assertEqual(len(next(iter(receipt["inputs"].values()))["sha256"]), 64)

    def test_each_interruption_duplicate_or_gap_blocks_without_repair(self):
        cases = [([(0, "A")], []), ([(0, "A")], [(0, 2)]),
                 ([(0, "A"), (0, "A")], [(0, 2)]),
                 ([(0, "A")], [(0, 1), (0, 1)]),
                 ([(0, "A"), (2 * runtime.HOUR, "B")], [(0, 1), (2 * runtime.HOUR, 1)])]
        for signals, ticks in cases:
            with self.subTest(signals=signals, ticks=ticks):
                self.signals(signals, ticks)
                before = {p.name: p.read_bytes() for p in self.journal.iterdir()}
                self.assertFalse(runtime.check("flow_signals", self.root, phase="before")["usable"])
                self.assertEqual(before, {p.name: p.read_bytes() for p in self.journal.iterdir()})

    def test_truncated_csv_and_symlink_do_not_become_empty_valid_batches(self):
        self.signals([(0, "A")], [(0, 1)])
        path = self.journal / "signals.csv"
        path.write_bytes(path.read_bytes().rstrip(b"\r\n"))
        self.assertEqual(runtime.check("flow_signals", self.root)["state"], "INVALID")
        path.unlink()
        path.symlink_to(self.journal / "ticks.csv")
        self.assertEqual(runtime.check("flow_signals", self.root)["state"], "INVALID")

    def test_zero_eligible_hour_can_be_complete(self):
        self.signals([], [(0, 0)])
        self.assertTrue(runtime.check("flow_signals", self.root)["usable"])

    def funding(self, venues, *, rate=0.0, recv=1):
        path = self.root / "data/recorders/funding_board/1970-01-01/00.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([dict(venue=v, symbol="TOY", recv_ms=recv, rate=rate, interval_h=8.)
                      for v in venues]).to_parquet(path, index=False)
        return path

    def test_partial_funding_is_not_current_complete_success(self):
        self.funding(["gate"])
        receipt = runtime.check("funding_snapshot", self.root, now_ms=1000)
        self.assertEqual(receipt["state"], "PARTIAL")
        self.assertFalse(receipt["usable"])
        self.assertEqual(receipt["answered_sources"], ["gate"])
        self.funding(runtime.FUNDING_VENUES)
        self.assertTrue(runtime.check("funding_snapshot", self.root, now_ms=1000)["usable"])

    def test_future_observation_invalid_rate_duplicate_and_previous_hour_stay_unusable(self):
        for venues, rate, recv in ((runtime.FUNDING_VENUES, float("nan"), 1),
                                   (runtime.FUNDING_VENUES, 0., 2000),
                                   ((*runtime.FUNDING_VENUES, "gate"), 0., 1)):
            with self.subTest(venues=venues, rate=rate, recv=recv):
                self.funding(venues, rate=rate, recv=recv)
                self.assertFalse(runtime.check("funding_snapshot", self.root, now_ms=1000)["usable"])
        self.assertEqual(runtime.check("funding_snapshot", self.root, now_ms=runtime.HOUR)["state"], "MISSING")


class ImmutableExports(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.out = self.root / "dashboard/data"
        self.out.mkdir(parents=True)
        (self.root / "dashboard/index.html").write_text("<p>fixture</p>")
        for name, value in (("ROOT", self.root), ("OUT", self.out)):
            manager = patch.object(dashboard_data, name, value)
            manager.start()
            self.addCleanup(manager.stop)

    def publish(self, value, at="2026-10-23T00:00:00Z"):
        return dashboard_data.publish_sets({"program": [{"value": value}]}, at)

    def test_upload_acknowledges_uploaded_generation_even_when_newer_export_exists(self):
        first = self.publish(1)
        second = self.publish(2, "2026-10-23T01:00:00Z")
        with redirect_stdout(io.StringIO()):
            dashboard_data.record(["program=/_blob/first"], first["generation"])
            dashboard_data.docs()
            changed = dashboard_data.changed()
        receipt = json.loads((self.out / "uploads.json").read_text())["program"]
        self.assertEqual(receipt["sha256"], first["sets"]["program"]["sha256"])
        self.assertEqual(changed["generation"], second["generation"])
        self.assertIn("program", changed["files"])
        document = json.loads((self.out / "docs/program.json").read_text())
        self.assertEqual(document["updated"]["at"], first["generated_at"])

    def test_missing_generation_and_changed_bytes_refuse_acknowledgement(self):
        man = self.publish(1)
        with self.assertRaises(ValueError):
            dashboard_data.record(["program=/_blob/unknown"])
        file = self.root / man["sets"]["program"]["file"]
        file.write_text("changed")
        with self.assertRaises(ValueError):
            dashboard_data.record(["program=/_blob/changed"], man["generation"])
        self.assertFalse((self.out / "uploads.json").exists())

    def test_failed_publication_keeps_previous_current_generation(self):
        first = self.publish(1)
        with patch.object(runtime, "atomic_json", side_effect=OSError("interrupted")), self.assertRaises(OSError):
            self.publish(2, "2026-10-23T01:00:00Z")
        self.assertEqual(json.loads((self.out / "manifest.json").read_text()), first)
        self.assertTrue((self.root / first["sets"]["program"]["file"]).is_file())

    def test_stale_ack_and_duplicate_dataset_cannot_overwrite_publication_receipt(self):
        first = self.publish(1)
        second = self.publish(2, "2026-10-23T01:00:00Z")
        with redirect_stdout(io.StringIO()):
            dashboard_data.record(["program=/_blob/new"], second["generation"])
        before = (self.out / "uploads.json").read_bytes()
        with self.assertRaises(ValueError):
            dashboard_data.record(["program=/_blob/old"], first["generation"])
        with self.assertRaises(ValueError):
            dashboard_data.record(["program=/_blob/a", "program=/_blob/b"], second["generation"])
        self.assertEqual((self.out / "uploads.json").read_bytes(), before)

    def test_completed_generation_retry_is_idempotent_but_cannot_regress_latest(self):
        first = self.publish(1)
        self.assertEqual(self.publish(1), first)
        second = self.publish(2, "2026-10-23T01:00:00Z")
        with self.assertRaises(ValueError):
            self.publish(1)
        self.assertEqual(json.loads((self.out / "manifest.json").read_text()), second)

    def test_docs_refresh_cannot_overwrite_a_concurrent_newer_upload_update(self):
        first = self.publish(1)
        second = self.publish(2, "2026-10-23T01:00:00Z")
        with redirect_stdout(io.StringIO()):
            dashboard_data.record(["program=/_blob/first"], first["generation"])
        entered, release, upload_started, upload_done = (threading.Event() for _ in range(4))
        errors = []
        original = runtime.atomic_json
        def paused(path, value):
            if Path(path).name == "program.json":
                entered.set()
                if not release.wait(3):
                    raise AssertionError("fixture release timed out")
            original(path, value)
        def refresh():
            try:
                dashboard_data.docs()
            except BaseException as error:
                errors.append(error)
        def upload():
            upload_started.set()
            try:
                dashboard_data.record(["program=/_blob/second"], second["generation"])
            except BaseException as error:
                errors.append(error)
            finally:
                upload_done.set()
        with patch.object(runtime, "atomic_json", side_effect=paused), redirect_stdout(io.StringIO()):
            old = threading.Thread(target=refresh)
            new = threading.Thread(target=upload)
            old.start()
            try:
                self.assertTrue(entered.wait(2))
                new.start()
                self.assertTrue(upload_started.wait(2))
                self.assertFalse(upload_done.wait(.05))  # The shared publication lock is held by docs().
            finally:
                release.set()
                old.join(3)
                if new.ident is not None:
                    new.join(3)
        self.assertFalse(old.is_alive() or new.is_alive())
        self.assertEqual(errors, [])
        update = json.loads((self.out / "docs/program.update.json").read_text())
        self.assertEqual(update["source"]["url"], "/_blob/second")


class SharedCatalog(unittest.TestCase):
    def test_common_entrypoint_is_idle_by_default_and_delegates_child_help(self):
        with patch.object(cli.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as child, \
                redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main([]), 0)
            child.assert_not_called()
            self.assertEqual(cli.main(["forward", "--help"]), 0)
            self.assertIn("--help", child.call_args.args[0])
            self.assertTrue(child.call_args.args[0][1].endswith("scripts/orchestrate_forward.py"))

    def test_all_operations_are_categorized_and_paper_views_share_inventory(self):
        tasks = operations.forward_tasks()
        self.assertEqual({t.name for t in tasks} - set(operations.LABELS), set())
        self.assertEqual({r[0] for r in panel.FORWARD}, {r[0] for r in dashboard_data.FORWARD})
        self.assertTrue({lane.rid for lane in operations.LANES}.issubset({t.name for t in tasks}))
        self.assertEqual(len({t.name for t in tasks}), len(tasks))

    def test_panel_calls_registry_rows_unranked_and_links_canonical_source(self):
        rows = pd.DataFrame([
            {"id": "M001", "method": "first", "status": "UNTESTED"},
            {"id": "M002", "method": "closed", "status": "TESTED"},
            {"id": "M003", "method": "partial", "status": "PARTIAL"},
        ])
        rendered = "\n".join(panel.queue_section(rows))
        self.assertIn("first 12 open rows in registry order", rendered)
        self.assertIn("does not encode a priority ranking", rendered)
        self.assertIn("../registry/methods.csv", rendered)
        self.assertIn("M001", rendered)
        self.assertIn("M003", rendered)
        self.assertNotIn("M002", rendered)

    def test_late_carry_is_not_relabelled_ontime_or_included_in_strict_totals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            journal = root / "experiments/xfund_fwd/journal"
            journal.mkdir(parents=True)
            pd.DataFrame([dict(book="A", day="2026-10-22", run="r", kind="late", net=.1,
                               net_2x=.05, net_3x=.01)]).to_csv(journal / "days.csv", index=False)
            pd.DataFrame([dict(book="A", day="2026-10-22", run="r")]).to_csv(journal / "decisions.csv", index=False)
            days = operations.forward_days(root)
            self.assertEqual(days[0]["kind"], "late")
            row = next(r for r in operations.forward_lanes(root, days, 0) if r["round"] == "R278")
            self.assertEqual(row["scored"], 0)
            self.assertIsNone(row["net_pct"])

    def test_fast_and_simulation_are_disjoint_and_cover_full_selection(self):
        cases = [unittest.FunctionTestCase(lambda: None),
                 unittest.FunctionTestCase(lambda: None)]
        with patch.object(cases[0], "id", return_value="tests.test_run_fundxs.EndToEndTest.test_toy"), \
                patch.object(cases[1], "id", return_value="tests.test_integrity.NewInvariant.test_toy"):
            fast, simulation = check.select(cases, "fast"), check.select(cases, "simulation")
        self.assertEqual(fast, [cases[1]])
        self.assertEqual(simulation, [cases[0]])
        self.assertEqual(set(fast + simulation), set(check.select(cases, "full")))

    def test_missing_book_does_not_borrow_another_books_days_or_net(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = [dict(book="A", day="2026-10-23", lane="mexc_fwd", kind="ontime", net=.1, net_2x=.1, net_3x=.1)]
            row = next(r for r in operations.forward_lanes(Path(directory), rows, 0) if r["round"] == "R215")
            self.assertEqual(row["scored"], 0)
            self.assertEqual(row["scored_by_book"], {"A": 1, "B": 0})
            self.assertIsNone(row["net_pct"])

    def test_funding_components_are_not_joined_from_different_hour_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            funding = root / "recorders/funding_board/1970-01-01/00.parquet"
            mexc = root / "recorders/mexc_ticker/1970-01-01/01.parquet"
            funding.parent.mkdir(parents=True)
            mexc.parent.mkdir(parents=True)
            pd.DataFrame([dict(venue=v, base="TOY", rate_8h=r, recv_ms=1000)
                          for v, r in (("gate", .001), ("okx", 0.))]).to_parquet(funding)
            pd.DataFrame([dict(symbol="TOY_USDT", f_fundingRate=.02, f_collectCycle=8, recv_ms=3_601_000)]).to_parquet(mexc)
            with patch.object(dashboard_perf.data, "ROOT", root):
                rows = dashboard_perf.funding_board()
            self.assertEqual(rows[0]["venues"], 2)
            self.assertIsNone(rows[0]["mexc_snapshot_at"])
            self.assertEqual(rows[0]["alignment"], "MEXC hour absent")


class EngineBuildIdentity(unittest.TestCase):
    def test_binary_and_source_drift_invalidate_receipt_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            (root / "engine/src").mkdir(parents=True)
            (root / "engine/Cargo.toml").write_text("synthetic")
            (root / "engine/Cargo.lock").write_text("synthetic")
            (root / "engine/src/main.rs").write_text("// synthetic")
            target = root / "engine/target/release/qx"
            target.parent.mkdir(parents=True)
            def compiler(task, working, log):
                target.write_bytes(b"invented binary")
                log.write_text("invented build")
                return {"status": "SUCCESS", "returncode": 0}
            with patch.object(build_engine.subprocess, "check_output", return_value="invented compiler"), \
                    patch.object(runtime, "run_process", side_effect=compiler):
                build_engine.build(root, Path(directory) / "runs", "first")
            self.assertEqual(runtime.environment(root)["qx_source_binding"], "MATCHES_BUILD_RECEIPT")
            target.write_bytes(b"changed binary")
            self.assertEqual(runtime.environment(root)["qx_source_binding"], "UNVERIFIED")
            target.write_bytes(b"invented binary")
            (root / "engine/src/main.rs").write_text("// changed source")
            self.assertEqual(runtime.environment(root)["qx_source_binding"], "UNVERIFIED")
