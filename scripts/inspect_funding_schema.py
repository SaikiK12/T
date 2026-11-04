#!/usr/bin/env python3
"""Inspect one funding ZIP header or Parquet schema; never decode observation rows.

Opaque file hashing authenticates bytes only against a separately supplied
identity. Field presence never authenticates settlement values, eligibility,
historical coverage or cash. No network, fitting, orders or archive rewrites.
"""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
import zipfile


MAX_BYTES = 128 * 1024**2
MAX_HEADER = 4096
MAX_UNCOMPRESSED = 2 * 1024**2
ROLES = {
    'settlement_time': ('calc_time', 'fundingTime', 't'),
    'settlement_interval': ('funding_interval_hours', 'interval_h'),
    'settled_rate': ('last_funding_rate', 'fundingRate', 'rate'),
    'settlement_value': ('markPrice',),
    'payment_kind': ('rateType',),
}


def safe_path(path):
    path = Path(os.path.abspath(path))
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('symlink source/output path is unsupported')
    return path


def signature(st):
    return st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns


def inspect(path, *, expected_sha256=None, max_bytes=MAX_BYTES):
    """Hash opaque bytes and inspect declared column names, not rates/prices.

    ZIPs require exactly one safe regular CSV member and a bounded, explicit
    header. Parquet uses read_schema, never read_table/row-group decoding.
    No missing field is inferred from another price family or a default kind.
    """
    path = safe_path(path)
    if type(max_bytes) is not int or not 0 < max_bytes <= MAX_BYTES:
        raise ValueError('positive bounded source-byte limit required')
    if expected_sha256 is not None and not re.fullmatch('[0-9a-f]{64}', expected_sha256):
        raise ValueError('full lowercase SHA256 required')
    if path.suffix not in ('.zip', '.parquet'):
        raise ValueError('one explicit .zip or .parquet source required')
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > max_bytes:
        raise ValueError('regular bounded source required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as source:
        opened = os.fstat(source.fileno())
        if signature(before) != signature(opened):
            raise ValueError('source changed before inspection')
        digest = hashlib.sha256()
        total = 0
        for block in iter(lambda: source.read(min(1024**2, max_bytes + 1 - total)), b''):
            total += len(block)
            if total > max_bytes:
                raise ValueError('source exceeded byte limit during inspection')
            digest.update(block)
        identity = digest.hexdigest()
        if expected_sha256 is not None and identity != expected_sha256:
            raise ValueError('source SHA256 mismatch')
        source.seek(0)
        member = None
        if path.suffix == '.zip':
            with zipfile.ZipFile(source) as archive:
                entries = archive.infolist()
                if len(entries) != 1:
                    raise ValueError('exactly one CSV member required')
                info = entries[0]
                member = info.filename
                mode = info.external_attr >> 16
                if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*\.csv', member)
                        or info.is_dir() or stat.S_ISLNK(mode)
                        or (stat.S_IFMT(mode) not in (0, stat.S_IFREG))
                        or not 0 < info.file_size <= MAX_UNCOMPRESSED):
                    raise ValueError('unsafe or oversized ZIP member')
                with archive.open(info) as stream:
                    raw = stream.readline(MAX_HEADER + 1)
                if len(raw) > MAX_HEADER or not raw.endswith(b'\n'):
                    raise ValueError('bounded newline-terminated CSV header required')
                rows = list(csv.reader(io.StringIO(raw.decode('utf-8-sig')), strict=True))
                if len(rows) != 1:
                    raise ValueError('one CSV header row required')
                columns = rows[0]
                types = None
        else:
            import pyarrow.parquet as pq
            schema = pq.read_schema(source)
            columns = schema.names
            types = [str(field.type) for field in schema]
        if (not 1 <= len(columns) <= 256 or len(set(columns)) != len(columns)
                or any(not re.fullmatch('[A-Za-z_][A-Za-z0-9_]{0,127}', name) for name in columns)):
            raise ValueError('unique explicit field names required; no inferred header')
        if (signature(opened) != signature(os.fstat(source.fileno()))
                or signature(opened) != signature(path.stat())):
            raise ValueError('source changed during inspection')
    roles = {role: [name for name in names if name in columns] for role, names in ROLES.items()}
    missing = [role for role in ('settlement_time', 'settled_rate', 'settlement_value', 'payment_kind')
               if not roles[role]]
    return {
        'schema_version': 1, 'source_path': str(path), 'source_bytes': total,
        'source_sha256': identity, 'expected_identity_matched': expected_sha256 is not None,
        'format': path.suffix[1:], 'member': member, 'columns': columns, 'column_types': types,
        'field_name_candidates': roles, 'missing_cash_field_roles': missing,
        'observation_rows_decoded': False, 'historical_coverage_verified': False,
        'field_semantics_verified': False, 'cash_settlement_ready': False,
        'source_eligibility_verified': False, 'research_trials_added': 0,
        'scope': 'Opaque byte identity and schema only; name candidates are not authenticated economic semantics.',
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--expected-sha256')
    parser.add_argument('--max-bytes', type=int, default=MAX_BYTES)
    parser.add_argument('--output', type=Path, help='optional new receipt; never replaces an existing file')
    args = parser.parse_args(argv)
    try:
        report = inspect(args.source, expected_sha256=args.expected_sha256, max_bytes=args.max_bytes)
        raw = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + '\n'
        if args.output is not None:
            out = safe_path(args.output)
            if out == safe_path(args.source):
                raise ValueError('output must differ from source')
            with out.open('x', encoding='utf-8') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        else:
            print(raw, end='')
        return 0
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile, csv.Error, ImportError) as exc:
        print('Funding schema: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
