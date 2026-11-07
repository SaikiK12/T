"""Invented archive/cache fixtures; every acquisition call is mocked."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import pandas as pd

from lab import data
from scripts import fetch_coinm as cm


HEADER = ("open_time,open,high,low,close,volume,close_time,base_volume,count,"
          "taker_buy_volume,taker_buy_base_volume,ignore")
ROW = "{t},1,2,0.5,1.5,17,0,2.5,11,7,1.25,0\n"
CONTRACT = "TOYUSD_240628"


class CoinmSchemaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.out = self.root / "coinm_1h_v2"
        self.out.mkdir()
        self.legacy = self.root / "coinm_1h" / "old.parquet"
        self.legacy.parent.mkdir()
        self.legacy.write_bytes(b"invented legacy bytes: preserve exactly")
        for target, value in (("scripts.fetch_coinm.OUT", self.out), ("lab.data.ROOT", self.root)):
            mock = patch(target, value)
            mock.start()
            self.addCleanup(mock.stop)
        self.archive = self.zip("toy.zip")
        self.key = f"{cm.CM}{CONTRACT}/1h/{CONTRACT}-1h-2024-01.zip"

    def zip(self, name, header=None, t=1704067200000):
        path = self.root / name
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("invented.csv", (header + "\n" if header else "") + ROW.format(t=t))
        return path

    def publish(self):
        with patch.object(data, "list_zips", return_value=[self.key]), \
                patch.object(data, "fetch", return_value=self.archive):
            return cm.one(CONTRACT)

    def test_headered_headerless_and_generic_semantics(self):
        plain = cm.parse_coinm(self.archive)
        headed = cm.parse_coinm(self.zip("headed.zip", HEADER))
        pd.testing.assert_frame_equal(plain, headed)
        self.assertEqual(list(plain.columns), list(cm.COLUMNS))
        self.assertEqual(float(plain.base_asset_volume.iloc[0]), 2.5)
        self.assertEqual(float(plain.taker_buy_base_asset_volume.iloc[0]), 1.25)
        self.assertEqual(float(plain.volume.iloc[0]), 17)
        self.assertEqual(float(plain.close.iloc[0]), 1.5)
        # The USD-M/spot parser is retained; the COIN-M wrapper supplies only names.
        generic = data.parse(self.archive, "klines")
        pd.testing.assert_frame_equal(plain.rename(columns={v:k for k,v in cm.RENAMES.items()}), generic)

    def test_wrong_market_header_refuses_and_microseconds_keep_existing_rule(self):
        wrong = HEADER.replace("base_volume", "quote_volume")
        with self.assertRaisesRegex(ValueError, "base-asset volume"):
            cm.parse_coinm(self.zip("wrong.zip", wrong))
        micro = cm.parse_coinm(self.zip("micro.zip", t=1704067200000000))
        self.assertEqual(int(micro.t.iloc[0]), 1704067200000)

    def test_publication_and_verified_resume_preserve_legacy(self):
        old = self.legacy.read_bytes()
        self.assertEqual(self.publish(), (CONTRACT, "1 bars"))
        output = self.out / f"{CONTRACT}.parquet"
        receipt = self.out / "completion" / f"{CONTRACT}.json"
        before = output.read_bytes(), receipt.read_bytes()
        self.assertEqual(list(pd.read_parquet(output).columns), list(cm.COLUMNS))
        d = json.loads(receipt.read_text())
        self.assertEqual(d["schema_version"], "coinm_klines_v2")
        self.assertEqual(d["archives"], [self.key])
        with patch.object(data, "list_zips") as listing, patch.object(data, "fetch") as fetch:
            self.assertEqual(cm.one(CONTRACT), (CONTRACT, "skip"))
            listing.assert_not_called()
            fetch.assert_not_called()
        self.assertEqual(before, (output.read_bytes(), receipt.read_bytes()))
        self.assertEqual(old, self.legacy.read_bytes())

    def test_missing_receipt_staging_and_orphan_receipt_fail_before_acquisition(self):
        for name, suffix in (("unreceipted", ".parquet"), ("staged", ".parquet.part"),
                             ("orphan", ".json"), ("receipt_staged", ".json.part")):
            with self.subTest(name=name):
                folder = self.out / name
                folder.mkdir()
                p = folder / ("completion" if "json" in suffix else "") / f"{CONTRACT}{suffix}"
                p.parent.mkdir(exist_ok=True)
                p.write_bytes(b"unfinished invented artifact")
                with patch.object(cm, "OUT", folder), patch.object(data, "list_zips") as listing, \
                        patch.object(data, "fetch") as fetch:
                    with self.assertRaises(cm.CacheError):
                        cm.one(CONTRACT)
                    listing.assert_not_called()
                    fetch.assert_not_called()
                self.assertEqual(p.read_bytes(), b"unfinished invented artifact")

    def test_wrong_receipt_and_tampered_file_are_preserved(self):
        self.publish()
        output = self.out / f"{CONTRACT}.parquet"
        receipt = self.out / "completion" / f"{CONTRACT}.json"
        good = receipt.read_bytes()
        changed = json.loads(good)
        changed["schema_version"] = "legacy"
        receipt.write_text(json.dumps(changed))
        with patch.object(data, "list_zips") as listing:
            with self.assertRaises(cm.CacheError):
                cm.one(CONTRACT)
            listing.assert_not_called()
        receipt.write_bytes(good)
        output.write_bytes(output.read_bytes() + b"changed")
        before = output.read_bytes()
        with self.assertRaises(cm.CacheError):
            cm.one(CONTRACT)
        self.assertEqual(output.read_bytes(), before)

    def test_parquet_schema_checked_even_with_matching_hash(self):
        output = self.out / f"{CONTRACT}.parquet"
        data.parse(self.archive, "klines").to_parquet(output, index=False)
        receipt = self.out / "completion" / f"{CONTRACT}.json"
        receipt.parent.mkdir()
        receipt.write_text(json.dumps({**cm._request(CONTRACT), "rows":1, "sha256":cm._sha256(output)}))
        with self.assertRaisesRegex(cm.CacheError, "Parquet schema"):
            cm.one(CONTRACT)

    def test_legacy_destination_and_invalid_manifest_refuse_before_remote_listing(self):
        for destination in (self.legacy.parent, self.legacy.parent / "nested"):
            with self.subTest(destination=destination), patch.object(sys, "argv", ["fetch_coinm.py", "--out", str(destination)]), \
                    patch.object(data, "_list") as listing:
                with self.assertRaisesRegex(cm.CacheError, "legacy"):
                    cm.main()
                listing.assert_not_called()
        manifest = self.out / "manifest.json"
        manifest.write_text('{"schema_version":"legacy"}')
        with patch.object(sys, "argv", ["fetch_coinm.py", "--out", str(self.out)]), patch.object(data, "_list") as listing:
            with self.assertRaisesRegex(cm.CacheError, "manifest"):
                cm.main()
            listing.assert_not_called()
        self.assertEqual(manifest.read_text(), '{"schema_version":"legacy"}')

    def test_incomplete_local_cache_preflight_and_manifest_publication(self):
        (self.out / f"{CONTRACT}.parquet").write_bytes(b"no completion receipt")
        with patch.object(sys, "argv", ["fetch_coinm.py", "--out", str(self.out)]), patch.object(data, "_list") as listing:
            with self.assertRaises(cm.CacheError):
                cm.main()
            listing.assert_not_called()
        fresh = self.root / "fresh_v2"
        with patch.object(sys, "argv", ["fetch_coinm.py", "--out", str(fresh)]), \
                patch.object(data, "_list", return_value=([], [])):
            cm.main()
        d = json.loads((fresh / "manifest.json").read_text())
        self.assertEqual(d["schema_version"], "coinm_klines_v2")
        self.assertEqual(d["columns"][6], "base_asset_volume")
        self.assertEqual(d["contracts"], {})

    def test_interrupted_publication_never_gains_completion(self):
        receipt = self.out / "completion" / f"{CONTRACT}.json"
        original = cm._publish
        def interrupt(path, write, **kwargs):
            if path == receipt:
                raise OSError("invented interruption before completion receipt")
            return original(path, write, **kwargs)
        with patch.object(cm, "_publish", side_effect=interrupt):
            with self.assertRaises(OSError):
                self.publish()
        self.assertTrue((self.out / f"{CONTRACT}.parquet").exists())
        self.assertFalse(receipt.exists())
        with self.assertRaises(cm.CacheError):
            cm.one(CONTRACT)

    def test_missing_listed_archive_cannot_complete_partial_history(self):
        second = self.key.replace("2024-01", "2024-02")
        with patch.object(data, "list_zips", return_value=[self.key, second]), \
                patch.object(data, "fetch", side_effect=[self.archive, None]):
            with self.assertRaisesRegex(cm.CacheError, "listed archive disappeared"):
                cm.one(CONTRACT)
        self.assertFalse((self.out / f"{CONTRACT}.parquet").exists())
        self.assertFalse((self.out / "completion" / f"{CONTRACT}.json").exists())

    def test_symlinked_receipt_directory_cannot_write_into_legacy(self):
        (self.out / "completion").symlink_to(self.legacy.parent, target_is_directory=True)
        before = {p.name: p.read_bytes() for p in self.legacy.parent.iterdir()}
        with patch.object(data, "list_zips") as listing:
            with self.assertRaisesRegex(cm.CacheError, "symlinked"):
                cm.one(CONTRACT)
            listing.assert_not_called()
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.legacy.parent.iterdir()})

    def test_new_publication_never_overwrites_concurrently_created_target(self):
        target = self.out / "race.parquet"
        def concurrent_writer(f):
            f.write(b"our staged fixture")
            target.write_bytes(b"other writer's fixture")
        with self.assertRaises(FileExistsError):
            cm._publish(target, concurrent_writer)
        self.assertEqual(target.read_bytes(), b"other writer's fixture")
        self.assertEqual(target.with_name(target.name + ".part").read_bytes(), b"our staged fixture")


if __name__ == "__main__":
    unittest.main()
