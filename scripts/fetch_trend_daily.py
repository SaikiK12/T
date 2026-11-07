#!/usr/bin/env python3
"""Fetch the frozen slow_trend_v1 spot sample; never calculate market outcomes.

Default: 414 monthly 1d ZIPs (six symbols, 2021-01 through 2026-09),
publisher checksums, at most 5 MiB of ZIP payload and 64 KiB per archive.
Existing files are validated and never replaced. A completed manifest is
immutable; reruns validate its entire local snapshot without network requests.

Usage: python3 scripts/fetch_trend_daily.py [--raw-dir PATH] [--manifest PATH]
       python3 scripts/fetch_trend_daily.py --self-test  # synthetic, offline
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.request
import zipfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab.prereg import verify  # noqa: E402

SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT")
MONTHS = tuple(f"{year}-{month:02d}" for year in range(2021, 2027)
               for month in range(1, 13) if (year, month) <= (2026, 9))
BASE = "https://data.binance.vision/data/spot/monthly/klines"
MAX_ZIP = 64 * 1024
MAX_TOTAL = 5 * 1024 * 1024
MAX_CHECKSUM = 4096
WORKERS = 4
PREREG = ROOT / "experiments/slow_trend_v1/PREREG.md"
DEFAULT_RAW = Path("/workspace/quant-small-data/slow_trend_v1/raw")
DEFAULT_MANIFEST = ROOT / "experiments/slow_trend_v1/results/data_manifest.json"


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def names() -> tuple[str, ...]:
    return tuple(f"{symbol}-1d-{month}.zip" for symbol in SYMBOLS for month in MONTHS)


def source_url(name: str) -> str:
    symbol = name.split("-", 1)[0]
    return f"{BASE}/{symbol}/1d/{name}"


def checksum_digest(payload: bytes, filename: str) -> str:
    """Require one publisher sha256sum line bound to the exact ZIP basename."""
    if not payload or len(payload) > MAX_CHECKSUM:
        raise ValueError("checksum response is empty or oversized")
    match = re.fullmatch(r"([0-9a-fA-F]{64})[ \t]+\*?([^\r\n]+)\r?\n?",
                         payload.decode("ascii"))
    if match is None or match.group(2) != filename:
        raise ValueError(f"invalid publisher checksum for {filename}")
    return match.group(1).lower()


def validate_archive(payload: bytes, checksum: bytes, filename: str) -> None:
    if not payload or len(payload) > MAX_ZIP:
        raise ValueError(f"archive size outside limit: {filename}")
    if digest(payload) != checksum_digest(checksum, filename):
        raise ValueError(f"publisher SHA-256 mismatch: {filename}")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        entries = archive.infolist()
        expected_csv = filename[:-4] + ".csv"
        if len(entries) != 1 or entries[0].filename != expected_csv:
            raise ValueError(f"unexpected archive members: {filename}")
        member = entries[0]
        if (member.flag_bits & 1 or member.file_size > MAX_ZIP or
                member.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)):
            raise ValueError(f"unsupported or oversized ZIP member: {filename}")
        if archive.testzip() is not None:
            raise ValueError(f"ZIP CRC failure: {filename}")


def fetch_bytes(url: str, maximum: int, expected_size: int | None = None) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "T-small-research/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200 or response.geturl() != url:
            raise ValueError(f"unexpected status/redirect: {url}")
        payload = response.read(maximum + 1)
    if len(payload) > maximum or (expected_size is not None and len(payload) != expected_size):
        raise ValueError(f"unexpected or oversized response: {url}")
    return payload


def head_size(url: str, maximum: int) -> int:
    request = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "T-small-research/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200 or response.geturl() != url:
            raise ValueError(f"unexpected status/redirect: {url}")
        size = int(response.headers["Content-Length"])
    if not 0 < size <= maximum:
        raise ValueError(f"HEAD size outside limit: {url}")
    return size


def check_plan(plan: dict[str, int]) -> int:
    if set(plan) != set(names()) or any(not 0 < size <= MAX_ZIP for size in plan.values()):
        raise ValueError("fixed 414-archive inventory or per-archive byte limit failed")
    total = sum(plan.values())
    if total > MAX_TOTAL:
        raise ValueError("5 MiB ZIP budget exceeded before writes")
    return total


def read_bounded(path: Path, maximum: int) -> bytes:
    if path.is_symlink() or path.stat().st_size > maximum:
        raise ValueError(f"unsafe or oversized cached file: {path}")
    with path.open("rb") as handle:
        payload = handle.read(maximum + 1)
    if len(payload) > maximum:
        raise ValueError(f"oversized cached file: {path}")
    return payload


def install_immutable(path: Path, payload: bytes) -> None:
    """Publish complete bytes atomically without replacing an existing file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        if path.is_symlink() or read_bounded(path, len(payload)) != payload:
            raise ValueError(f"existing file differs; refusing overwrite: {path}")
        return
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".fetch-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.is_symlink() or read_bounded(path, len(payload)) != payload:
                raise ValueError(f"concurrent existing file differs: {path}")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def verify_registration() -> tuple[str, str]:
    prereg_sha = verify(PREREG)
    script_sha = digest(Path(__file__).read_bytes())
    matches = re.findall(r"^Fetcher SHA-256: ([0-9a-f]{64})\s*$",
                         PREREG.read_text(), flags=re.MULTILINE)
    if matches != [script_sha]:
        raise ValueError("frozen preregistration does not bind this fetcher SHA-256")
    return prereg_sha, script_sha


def make_record(name: str, payload: bytes, checksum: bytes) -> dict:
    return {"path": name, "url": source_url(name), "sha256": digest(payload),
            "bytes": len(payload), "checksum_url": source_url(name) + ".CHECKSUM",
            "checksum_sha256": digest(checksum), "checksum_bytes": len(checksum)}


def verify_manifest(path: Path, raw: Path, prereg_sha: str, script_sha: str) -> dict:
    manifest = json.loads(read_bounded(path, MAX_TOTAL))
    if (manifest.get("schema_version") != 1 or
            manifest.get("prereg_sha256") != prereg_sha or
            manifest.get("fetcher_sha256") != script_sha):
        raise ValueError("manifest registration/script identity mismatch")
    records = manifest.get("archives", [])
    if [record.get("path") for record in records] != list(names()):
        raise ValueError("manifest does not enumerate the fixed 414 archives")
    total = 0
    for record in records:
        name = record["path"]
        payload = read_bounded(raw / name, MAX_ZIP)
        checksum = read_bounded(raw / (name + ".CHECKSUM"), MAX_CHECKSUM)
        validate_archive(payload, checksum, name)
        if make_record(name, payload, checksum) != record:
            raise ValueError(f"cached bytes differ from immutable manifest: {name}")
        total += len(payload)
    if total > MAX_TOTAL or total != manifest.get("total_zip_bytes"):
        raise ValueError("manifest archive-byte budget mismatch")
    return manifest


def run(raw: Path, manifest_path: Path) -> dict:
    prereg_sha, script_sha = verify_registration()  # Before every network/data operation.
    if manifest_path.exists() or manifest_path.is_symlink():
        return verify_manifest(manifest_path, raw, prereg_sha, script_sha)

    def plan_one(name: str) -> tuple[str, int]:
        path = raw / name
        size = len(read_bounded(path, MAX_ZIP)) if path.exists() else head_size(source_url(name), MAX_ZIP)
        checksum_path = raw / (name + ".CHECKSUM")
        if checksum_path.exists():
            checksum_digest(read_bounded(checksum_path, MAX_CHECKSUM), name)
        else:
            head_size(source_url(name) + ".CHECKSUM", MAX_CHECKSUM)
        return name, size

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        plan = dict(executor.map(plan_one, names()))
    total = check_plan(plan)

    def fetch_one(name: str) -> dict:
        checksum_path = raw / (name + ".CHECKSUM")
        checksum = (read_bounded(checksum_path, MAX_CHECKSUM) if checksum_path.exists()
                    else fetch_bytes(source_url(name) + ".CHECKSUM", MAX_CHECKSUM))
        checksum_digest(checksum, name)
        path = raw / name
        payload = (read_bounded(path, MAX_ZIP) if path.exists() else
                   fetch_bytes(source_url(name), MAX_ZIP, plan[name]))
        if len(payload) != plan[name]:
            raise ValueError(f"cached archive changed since byte-budget plan: {name}")
        validate_archive(payload, checksum, name)
        install_immutable(checksum_path, checksum)
        install_immutable(path, payload)
        return make_record(name, payload, checksum)

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        records = list(executor.map(fetch_one, names()))
    manifest = {"schema_version": 1, "prereg_sha256": prereg_sha,
                "fetcher_sha256": script_sha,
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "source": "Binance public spot monthly 1d archives; as downloaded",
                "total_zip_bytes": total, "archives": records}
    encoded = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    install_immutable(manifest_path, encoded)
    return verify_manifest(manifest_path, raw, prereg_sha, script_sha)


class SyntheticTests(unittest.TestCase):
    @staticmethod
    def sample(csv_name="BTCUSDT-1d-2021-01.csv", value=b"synthetic fixture\n"):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(csv_name, value)
        payload = stream.getvalue()
        checksum = f"{digest(payload)}  BTCUSDT-1d-2021-01.zip\n".encode()
        return payload, checksum

    def test_fixed_count(self):
        self.assertEqual((len(MONTHS), len(names()), len(set(names()))), (69, 414, 414))

    def test_valid_archive(self):
        validate_archive(*self.sample(), "BTCUSDT-1d-2021-01.zip")

    def test_bad_checksum(self):
        payload, checksum = self.sample()
        with self.assertRaises(ValueError):
            validate_archive(payload + b"corruption", checksum, "BTCUSDT-1d-2021-01.zip")

    def test_wrong_checksum_name(self):
        with self.assertRaises(ValueError):
            checksum_digest(b"0" * 64 + b"  wrong.zip\n", "BTCUSDT-1d-2021-01.zip")

    def test_wrong_member_name(self):
        with self.assertRaises(ValueError):
            validate_archive(*self.sample("../escape.csv"), "BTCUSDT-1d-2021-01.zip")

    def test_expansion_limit(self):
        with self.assertRaises(ValueError):
            validate_archive(*self.sample(value=b"x" * (MAX_ZIP + 1)), "BTCUSDT-1d-2021-01.zip")

    def test_immutable_install(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot"
            install_immutable(path, b"first")
            install_immutable(path, b"first")
            with self.assertRaises(ValueError):
                install_immutable(path, b"other")
            self.assertEqual(path.read_bytes(), b"first")

    def test_budget_before_writes(self):
        plan = dict.fromkeys(names(), 2000)
        self.assertEqual(check_plan(plan), 828000)
        with self.assertRaises(ValueError):
            check_plan(dict.fromkeys(names(), MAX_ZIP))
        with self.assertRaises(ValueError):
            check_plan({"unexpected.zip": 100})

    def test_frozen_guard_precedes_network(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch(__name__ + ".verify_registration", side_effect=ValueError("unfrozen")):
                with patch(__name__ + ".head_size") as head:
                    with self.assertRaises(ValueError):
                        run(Path(directory) / "raw", Path(directory) / "manifest.json")
                    head.assert_not_called()
            self.assertFalse((Path(directory) / "raw").exists())

    def test_response_bounds(self):
        class Response(io.BytesIO):
            status = 200
            def geturl(self):
                return "https://example.invalid/synthetic"
        with patch("urllib.request.urlopen", return_value=Response(b"oversize")):
            with self.assertRaises(ValueError):
                fetch_bytes("https://example.invalid/synthetic", 3)
        with patch("urllib.request.urlopen", return_value=Response(b"abc")):
            self.assertEqual(fetch_bytes("https://example.invalid/synthetic", 3, 3), b"abc")
        with patch("urllib.request.urlopen", return_value=Response(b"ab")):
            with self.assertRaises(ValueError):
                fetch_bytes("https://example.invalid/synthetic", 3, 3)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        unittest.main(argv=[sys.argv[0]], exit=True)
    manifest = run(args.raw_dir, args.manifest)
    print(json.dumps({"archives": len(manifest["archives"]),
                      "total_zip_bytes": manifest["total_zip_bytes"],
                      "manifest": str(args.manifest)}, sort_keys=True))


if __name__ == "__main__":
    main()
