"""Verify an explicit immutable export and optionally build a new static dashboard.

Default is a read-only plan. --build creates a new directory without replacement;
it never runs the exporter, scans native lanes, uploads or deploys anything.
Supply a local D3 v7-compatible asset and its independently pinned SHA256.
"""
import argparse
from contextlib import contextmanager
import ctypes
import datetime as dt
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.dashboard_data import TITLES  # noqa: E402; constants only, no export invoked

MAX_MANIFEST = 2 * 1024**2
MAX_DATASET = 32 * 1024**2
MAX_TOTAL = 128 * 1024**2
MAX_ASSET = 2 * 1024**2
MAX_ROWS = 200_000
SHA = re.compile(r'[a-f0-9]{64}')


def _digest(value):
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise ValueError('explicit lowercase SHA256 required')
    return value


def _absolute(path):
    path = Path(path)
    if '..' in path.parts or '\\' in str(path) or any(ord(c) < 32 for c in str(path)):
        raise ValueError('unsafe filesystem path')
    return path.absolute()


@contextmanager
def _directory(path):
    path = _absolute(path)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(path.anchor, flags)
    try:
        for name in path.parts[1:]:
            child = os.open(name, flags, dir_fd=fd)
            os.close(fd); fd = child
        yield fd
    finally:
        os.close(fd)


def _read(path, bound):
    path = _absolute(path)
    with _directory(path.parent) as parent:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size > bound:
                raise ValueError('bounded regular file required: ' + path.name)
            with os.fdopen(fd, 'rb', closefd=False) as stream:
                raw = stream.read(bound + 1)
            fields = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
            if (len(raw) > bound or fields(before) != fields(os.fstat(fd)) or
                    fields(before) != fields(os.stat(path.name, dir_fd=parent, follow_symlinks=False))):
                raise ValueError('source changed while reading: ' + path.name)
            return raw
        finally:
            os.close(fd)


def _json(raw):
    def unique(pairs):
        out = {}
        for k, v in pairs:
            if k in out: raise ValueError('duplicate JSON key')
            out[k] = v
        return out
    def number(text):
        value = float(text)
        if not math.isfinite(value): raise ValueError('nonfinite JSON number')
        return value
    def invalid(_): raise ValueError('nonfinite JSON constant')
    try:
        return json.loads(raw, object_pairs_hook=unique, parse_float=number, parse_constant=invalid)
    except (RecursionError, UnicodeError) as exc:
        raise ValueError('invalid or deeply nested JSON') from exc


def _rows(value):
    if (not isinstance(value, list) or len(value) > MAX_ROWS or
            any(not isinstance(row, dict) for row in value)):
        raise ValueError('dataset must be a bounded array of row objects')
    stack = [(value, 0)]
    while stack:
        item, depth = stack.pop()
        if depth > 64: raise ValueError('dataset nesting exceeds bound')
        if type(item) is int and abs(item) > 2**53-1:
            raise ValueError('unsafe JavaScript integer; exporter must encode exact large identifiers as strings')
        if isinstance(item, dict): stack.extend((x, depth+1) for x in item.values())
        elif isinstance(item, list): stack.extend((x, depth+1) for x in item)
    return value


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def _script_json(value):
    return json.dumps(value, separators=(',', ':'), allow_nan=False).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')


THEME = '''
:root{--font-anthropic-sans:system-ui,sans-serif;--font-anthropic-serif:Georgia,serif;
--color-fg:#1f2937;--color-fg-muted:#596579;--color-bg:#f4f6f8;--color-panel:#fff;
--color-border-line:#d8dee8;--color-bad:#b42318;--color-warn:#946200;--color-ok:#067647;
--cds-font-size-title:2rem;--cds-font-size-heading:1.12rem;--cds-font-size-body:1rem;
--cds-font-size-caption:.85rem;--cds-font-weight-medium:600;--cds-gap-xs:6px;
--cds-gap-sm:10px;--cds-gap-md:18px;--cds-pad-xs:6px;--cds-pad-sm:10px;
--cds-pad-md:18px;--cds-pad-lg:22px;--cds-radius:7px;--cds-surface-popover:#fff;
--cds-border:#d8dee8;--cds-text-secondary:#596579;--cds-chart-muted:#8796a8;
--cds-chart-axis:#9aa5b4;--cds-shadow-popover:0 4px 15px #0002;--cds-dur-slow:200ms}
body{margin:0;padding:20px;background:var(--color-bg);font-family:var(--font-anthropic-sans)}
#standalone-status{padding:12px;margin-bottom:16px;border:1px solid var(--color-border-line);border-radius:7px;font-size:.9rem}
#standalone-status[data-state=error]{color:var(--color-bad);border-color:var(--color-bad)}
.dash-skeleton{opacity:.6}
'''


def plan(export_dir, generation, d3_asset, d3_sha256):
    """Validate all sources, returning an in-memory bounded build and plan receipt."""
    generation = _digest(generation); d3_sha256 = _digest(d3_sha256)
    export_dir = _absolute(export_dir)
    if export_dir.name != generation:
        raise ValueError('explicit generation directory must be named by its pinned ID')
    raw_manifest = _read(export_dir / 'manifest.json', MAX_MANIFEST)
    manifest = _json(raw_manifest)
    if (not isinstance(manifest, dict) or set(manifest) != {'schema_version', 'generation', 'generated_at', 'sets'} or
            type(manifest['schema_version']) is not int or manifest['schema_version'] != 2 or
            manifest['generation'] != generation or not isinstance(manifest['sets'], dict)):
        raise ValueError('schema-v2 immutable generation manifest required')
    at = manifest['generated_at']
    if not isinstance(at, str) or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', at):
        raise ValueError('explicit UTC export clock required')
    dt.datetime.fromisoformat(at.replace('Z', '+00:00'))
    if set(manifest['sets']) != set(TITLES):
        raise ValueError('generation has missing or unknown dashboard dataset IDs')
    signatures = {}
    files = {}; datasets = {}; total = len(raw_manifest)
    for key, item in sorted(manifest['sets'].items()):
        if not isinstance(item, dict) or set(item) != {'file', 'rows', 'sha256'}:
            raise ValueError('invalid dataset declaration')
        expected = f'dashboard/data/generations/{generation}/{key}.json'
        if item['file'] != expected or type(item['rows']) is not int or not 0 <= item['rows'] <= MAX_ROWS:
            raise ValueError('unexpected dataset path or row count')
        signatures[key] = _digest(item['sha256'])
        raw = _read(export_dir / (key + '.json'), min(MAX_DATASET, MAX_TOTAL - total))
        if _hash(raw) != item['sha256']: raise ValueError('dataset SHA256 mismatch: ' + key)
        if len(_rows(_json(raw))) != item['rows']: raise ValueError('dataset row-count mismatch: ' + key)
        total += len(raw)
        if total > MAX_TOTAL: raise ValueError('generation exceeds total byte bound')
        files[f'data/{key}.json'] = raw
        datasets[key] = dict(file=f'data/{key}.json', sha256=item['sha256'], bytes=len(raw), rows=item['rows'])
    identity = _hash(json.dumps({'at': at, 'sets': signatures}, sort_keys=True).encode())
    if identity != generation: raise ValueError('generation content identity mismatch')
    d3 = _read(d3_asset, MAX_ASSET)
    if _hash(d3) != d3_sha256: raise ValueError('D3 asset SHA256 mismatch')
    d3.decode('utf-8')
    adapter = _read(ROOT / 'dashboard/standalone_adapter.js', MAX_ASSET)
    shell = _read(ROOT / 'dashboard/index.html', MAX_ASSET)
    config = dict(version=1, generation=generation, generated_at=at, datasets=datasets,
                  max_dataset_bytes=MAX_DATASET, max_total_bytes=MAX_TOTAL)
    sri = lambda raw: __import__('base64').b64encode(hashlib.sha256(raw).digest()).decode()
    document = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<title>Quant Lab Control Room — static snapshot</title><style>' + THEME + '</style></head><body>'
                '<aside id="standalone-status" role="status" data-state="loading">'
                'Static snapshot: verifying local datasets. This page starts no jobs or orders.</aside>'
                '<script id="standalone-config" type="application/json">' + _script_json(config) + '</script>'
                f'<script src="assets/d3.js" integrity="sha256-{sri(d3)}"></script>'
                f'<script src="assets/standalone_adapter.js" integrity="sha256-{sri(adapter)}"></script>' +
                shell.decode('utf-8') + '<script>dash.start();</script></body></html>').encode()
    files.update({'index.html': document, 'assets/d3.js': d3,
                  'assets/standalone_adapter.js': adapter, 'export-manifest.json': raw_manifest})
    bundle = dict(version=1, generation=generation, generated_at=at,
                  export_manifest_sha256=_hash(raw_manifest), d3_sha256=d3_sha256,
                  source_shell_sha256=_hash(shell),
                  files={k: dict(bytes=len(v), sha256=_hash(v)) for k, v in sorted(files.items())})
    files['bundle-manifest.json'] = _canonical(bundle)
    size = sum(map(len, files.values()))
    if size > MAX_TOTAL + 3 * MAX_ASSET + MAX_MANIFEST:
        raise ValueError('static bundle exceeds total byte bound')
    receipt = dict(state='PLAN', generation=generation, generated_at=at, datasets=len(datasets),
                   output_files=len(files), output_bytes=size,
                   bundle_manifest_sha256=_hash(files['bundle-manifest.json']), d3_sha256=d3_sha256,
                   scope='Verified immutable export bytes only; no native scan, live health certification or deployment.')
    return files, receipt


def build(export_dir, generation, d3_asset, d3_sha256, out=None):
    files, receipt = plan(export_dir, generation, d3_asset, d3_sha256)
    if out is None: return receipt
    out = _absolute(out); source = _absolute(export_dir)
    if out == source or out in source.parents or source in out.parents:
        raise ValueError('output and export directory must not overlap')
    with _directory(out.parent) as parent_fd:
        try: os.stat(out.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError: pass
        else: raise FileExistsError('output already exists; never overwritten')
        temporary = Path(tempfile.mkdtemp(prefix='.dashboard-', dir=out.parent))
        published = False
        try:
            for relative, body in files.items():
                path = temporary / relative; path.parent.mkdir(parents=True, exist_ok=True)
                with path.open('xb') as stream:
                    stream.write(body); stream.flush(); os.fsync(stream.fileno())
            # Persist the two fixed asset directories and the bundle root
            # before the atomic directory publication becomes visible.
            for directory in (temporary / 'assets', temporary / 'data', temporary):
                with _directory(directory) as directory_fd:
                    os.fsync(directory_fd)
            libc = ctypes.CDLL(None, use_errno=True); rename = getattr(libc, 'renameat2', None)
            if rename is None: raise ValueError('atomic no-overwrite publication requires Linux renameat2')
            rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
            rename.restype = ctypes.c_int
            if rename(parent_fd, os.fsencode(temporary.name), parent_fd, os.fsencode(out.name), 1):
                code = ctypes.get_errno(); raise OSError(code, os.strerror(code))
            published = True; os.fsync(parent_fd)
        finally:
            if not published: shutil.rmtree(temporary)
    return dict(receipt, state='BUILT', output=str(out))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export-dir', required=True, type=Path)
    parser.add_argument('--generation', required=True)
    parser.add_argument('--d3-asset', required=True, type=Path)
    parser.add_argument('--d3-sha256', required=True)
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args(argv)
    if args.build != (args.out is not None): parser.error('--build and --out must be supplied together')
    try:
        receipt = build(args.export_dir, args.generation, args.d3_asset, args.d3_sha256, args.out)
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps(dict(state='REFUSED', error=str(exc)))); return 2
    print(json.dumps(receipt, sort_keys=True)); return 0


if __name__ == '__main__': raise SystemExit(main())
