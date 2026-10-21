import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from scripts import fetch_coinmetrics as cm


class FetchCoinmetricsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="coinmetrics-toy-")
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)
        self.metrics = ["CapMrktCurUSD", "AdrActCnt"]
        self.frame = pd.DataFrame({"t": [cm.OPEN_FROM_MS - 86400000, cm.OPEN_FROM_MS],
                                   "CapMrktCurUSD": [1.0, 2.0], "AdrActCnt": [3, 4]})
        (self.out / "catalog.json").write_text(json.dumps({"toy": self.metrics}))

    @property
    def receipt_path(self):
        return self.out / "completion/toy.json"

    def run_main(self, frame=None, only="toy"):
        argv = ["fetch_coinmetrics.py", "--out", str(self.out), "--only", only, "--pause", "0"]
        with patch.object(cm.sys, "argv", argv), patch.object(cm, "series", return_value=frame) as series, \
                patch.object(cm, "catalog", side_effect=AssertionError("unexpected network catalog")), \
                contextlib.redirect_stdout(io.StringIO()):
            cm.main()
        return series

    def assert_preflight_refused(self):
        before = {str(p.relative_to(self.out)): p.read_bytes() for p in self.out.rglob("*") if p.is_file()}
        argv = ["fetch_coinmetrics.py", "--out", str(self.out), "--only", "toy"]
        with patch.object(cm.sys, "argv", argv), patch.object(cm, "series") as series, \
                contextlib.redirect_stderr(io.StringIO()) as errors, self.assertRaises(SystemExit) as raised:
            cm.main()
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("fresh --out", errors.getvalue())
        series.assert_not_called()
        after = {str(p.relative_to(self.out)): p.read_bytes() for p in self.out.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_two_partitions_publish_receipt_and_skip(self):
        self.run_main(self.frame).assert_called_once_with("toy", self.metrics, 0)
        d = cm.completed(self.out, "toy", list(reversed(self.metrics)))
        self.assertEqual(d["source"], cm.API)
        self.assertEqual(d["frequency"], "1d")
        self.assertEqual(d["metrics"], sorted(self.metrics))
        self.assertEqual([d["partitions"][k]["rows"] for k in cm.PARTITIONS], [1, 1])
        for where in cm.PARTITIONS:
            path = self.out / d["partitions"][where]["path"]
            self.assertEqual(len(pd.read_parquet(path)), 1)
            self.assertEqual(d["partitions"][where]["sha256"], cm._sha256(path))
        before = self.receipt_path.read_bytes()
        self.run_main().assert_not_called()
        self.assertEqual(before, self.receipt_path.read_bytes())
        self.assertFalse(list(self.out.rglob("*.part")))

    def test_one_sided_and_empty_histories_are_explicit_and_skip(self):
        for indexes, counts in (([1], [1, 0]), ([0], [0, 1]), ([], [0, 0])):
            with self.subTest(counts=counts), tempfile.TemporaryDirectory() as name:
                out = Path(name)
                cm.publish_asset(out, "toy", self.metrics, self.frame.iloc[indexes])
                receipt = cm.completed(out, "toy", self.metrics)
                for where, count in zip(cm.PARTITIONS, counts):
                    part = receipt["partitions"][where]
                    self.assertEqual(part["rows"], count)
                    self.assertEqual((out / part["path"]).exists(), bool(count))
                    self.assertEqual(part["sha256"] is None, not count)

    def test_empty_http_history_gets_receipt_and_skips(self):
        with patch.object(cm, "get", return_value={"data": []}), patch.object(cm.time, "sleep"):
            empty = cm.series("toy", self.metrics, 0)
        self.run_main(empty)
        self.run_main().assert_not_called()
        self.assertEqual(cm.completed(self.out, "toy", self.metrics)["partitions"]["open"]["rows"], 0)

    def test_interruption_after_first_shard_cannot_be_silently_skipped(self):
        real = pd.DataFrame.to_parquet
        writes = []

        def interrupted(frame, target, **kwargs):
            writes.append(target.name)
            if len(writes) == 2:
                target.write(b"synthetic interrupted parquet")
                raise OSError("synthetic interruption")
            return real(frame, target, **kwargs)

        with patch.object(pd.DataFrame, "to_parquet", interrupted), self.assertRaisesRegex(OSError, "synthetic"):
            self.run_main(self.frame)
        self.assertTrue((self.out / "open/toy.parquet").is_file())
        self.assertFalse((self.out / "reserved/toy.parquet").exists())
        self.assertTrue((self.out / "reserved/toy.parquet.part").is_file())
        self.assertFalse(self.receipt_path.exists())
        self.assert_preflight_refused()

    def test_interruption_before_receipt_preserves_both_shards(self):
        real = cm._publish

        def interrupted(path, write):
            if path.parent.name == "completion":
                raise OSError("synthetic receipt interruption")
            return real(path, write)

        with patch.object(cm, "_publish", interrupted), self.assertRaises(OSError):
            self.run_main(self.frame)
        self.assertTrue(all((self.out / where / "toy.parquet").exists() for where in cm.PARTITIONS))
        self.assertFalse(self.receipt_path.exists())
        self.assert_preflight_refused()

    def test_legacy_shard_is_preserved_and_refused(self):
        path = self.out / "open/toy.parquet"
        path.parent.mkdir()
        path.write_bytes(b"synthetic legacy bytes")
        (self.out / "manifest.json").write_text("old synthetic provenance")
        self.assert_preflight_refused()

    def test_preflight_checks_all_selected_assets_before_fetch(self):
        (self.out / "catalog.json").write_text(json.dumps({"fresh": self.metrics, "toy": self.metrics}))
        (self.out / "open").mkdir()
        (self.out / "open/toy.parquet").write_bytes(b"synthetic legacy bytes")
        argv = ["fetch_coinmetrics.py", "--out", str(self.out)]
        with patch.object(cm.sys, "argv", argv), patch.object(cm, "series") as series, \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cm.main()
        series.assert_not_called()

    def test_missing_or_changed_shards_are_refused(self):
        for missing in (True, False):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as name:
                self.out = Path(name)
                (self.out / "catalog.json").write_text(json.dumps({"toy": self.metrics}))
                cm.publish_asset(self.out, "toy", self.metrics, self.frame)
                path = self.out / "open/toy.parquet"
                if missing:
                    path.unlink()
                else:
                    path.write_bytes(b"synthetic changed bytes")
                self.assert_preflight_refused()

    def test_unexpected_shard_invalidates_empty_partition(self):
        cm.publish_asset(self.out, "toy", self.metrics, self.frame.iloc[[1]])
        (self.out / "reserved").mkdir()
        (self.out / "reserved/toy.parquet").write_bytes(b"synthetic unexpected bytes")
        self.assert_preflight_refused()

    def test_missing_corrupt_or_mismatched_receipts_are_refused(self):
        mutations = (None, "{", {}, {"source": "wrong-api"}, {"metrics": ["AdrActCnt"]},
                     {"frequency": "1h"}, {"open_from_ms": 0}, {"captured_utc": "invalid"},
                     {"partitions": {}}, {"schema_version": 2})
        for change in mutations:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as name:
                self.out = Path(name)
                (self.out / "catalog.json").write_text(json.dumps({"toy": self.metrics}))
                receipt = cm.publish_asset(self.out, "toy", self.metrics, self.frame)
                if change is None:
                    self.receipt_path.unlink()
                elif isinstance(change, str):
                    self.receipt_path.write_text(change)
                else:
                    self.receipt_path.write_text(json.dumps({**receipt, **change} if change else change))
                self.assert_preflight_refused()

    def test_changed_request_metrics_are_refused(self):
        cm.publish_asset(self.out, "toy", self.metrics, self.frame)
        (self.out / "catalog.json").write_text(json.dumps({"toy": [*self.metrics, "SplyCur"]}))
        self.assert_preflight_refused()

    def test_staging_remnant_is_refused_even_with_valid_receipt(self):
        cm.publish_asset(self.out, "toy", self.metrics, self.frame)
        (self.out / "completion/toy.json.part").write_bytes(b"synthetic incomplete write")
        self.assert_preflight_refused()

    def test_publish_never_overwrites_complete_cache(self):
        cm.publish_asset(self.out, "toy", self.metrics, self.frame)
        before = self.receipt_path.read_bytes()
        with self.assertRaises(cm.CacheError):
            cm.publish_asset(self.out, "toy", self.metrics, self.frame.iloc[[1]])
        self.assertEqual(before, self.receipt_path.read_bytes())

    def test_malformed_response_cannot_be_certified_as_empty_history(self):
        for response in ({}, {"data": None}, {"data": {}}, []):
            with self.subTest(response=response), patch.object(cm, "get", return_value=response), \
                    patch.object(cm.time, "sleep"), self.assertRaisesRegex(RuntimeError, "data list"):
                cm.series("toy", self.metrics, 0)

    def test_out_does_not_touch_default_cache(self):
        with tempfile.TemporaryDirectory() as name:
            default = Path(name)
            sentinel = default / "unchanged"
            sentinel.write_bytes(b"synthetic default cache sentinel")
            with patch.object(cm, "OUT", default):
                self.run_main(self.frame)
            self.assertEqual(list(default.iterdir()), [sentinel])
            self.assertEqual(sentinel.read_bytes(), b"synthetic default cache sentinel")


if __name__ == "__main__":
    unittest.main()
