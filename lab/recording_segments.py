"""Streaming, non-overwriting recovery bundles for explicit RECORDED files.

The ordinary small-file archive remains scripts/handover.py. This supplements
it for individual files above its limit, without parsing their market payloads.
Publication requires Linux renameat2(RENAME_NOREPLACE); unsupported hosts fail
closed. Hashes establish identity to a caller-pinned manifest, not source truth
or completeness of the recorder. No remote upload or original deletion occurs.
"""
from contextlib import contextmanager
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
import time

from scripts.handover import CLASSES, PUBLIC_EXCLUDE, classify, skipped


FORMAT = 'recorded-file-segments'
VERSION = 1
MAX_SEGMENT_BYTES = 95_000_000
MAX_SEGMENTS = 10_000
MAX_MANIFEST_BYTES = 4 * 1024**2
BLOCK_BYTES = 1024**2
DIGEST = re.compile(r'[a-f0-9]{64}')
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


class SegmentError(ValueError):
    pass


def _integer(value, name, *, minimum=0, maximum=2**63-1):
    if type(value) is not int or not minimum <= value <= maximum:
        raise SegmentError(name + ' must be a bounded integer')
    return value


def _relative(value):
    if (not isinstance(value, str) or not value or len(value) > 4096 or
            '\\' in value or any(ord(c) < 32 for c in value)):
        raise SegmentError('explicit safe relative data path required')
    p = PurePosixPath(value)
    if (p.is_absolute() or p.parts[:1] != ('data',) or len(p.parts) < 2 or
            any(x in ('', '.', '..') for x in value.split('/')) or
            any(':' in x for x in p.parts)):
        raise SegmentError('explicit safe relative data path required')
    return value


def _absolute(value):
    p = Path(value)
    if ('..' in p.parts or '\\' in str(p) or
            any(ord(c) < 32 for c in str(p))):
        raise SegmentError('parent traversal in filesystem path')
    return p.absolute()


def _separate(a, b):
    if a == b or a in b.parents or b in a.parents:
        raise SegmentError('archive and repository must be separate, non-overlapping paths')


@contextmanager
def _directory(path):
    """Open each existing ancestor without following a symlink."""
    p = _absolute(path)
    fd = os.open(p.anchor, _DIR_FLAGS)
    try:
        for part in p.parts[1:]:
            new = os.open(part, _DIR_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = new
        yield fd
    finally:
        os.close(fd)


@contextmanager
def _parents(root_fd, parts, *, create=False):
    fd = os.dup(root_fd)
    try:
        for name in parts:
            if create:
                try:
                    os.mkdir(name, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
                else:
                    os.fsync(fd)
            new = os.open(name, _DIR_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = new
        yield fd
    finally:
        os.close(fd)


def _fingerprint(s):
    return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_mode


@contextmanager
def _regular(parent_fd, name):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
    try:
        initial = os.fstat(fd)
        if not stat.S_ISREG(initial.st_mode):
            raise SegmentError('regular file required')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            yield stream, initial
        current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if (_fingerprint(initial) != _fingerprint(os.fstat(fd)) or
                _fingerprint(initial) != _fingerprint(current)):
            raise SegmentError('file changed while it was read')
    finally:
        os.close(fd)


def _load_classification(root_fd):
    """Use handover's longest-prefix classes, from the root's actual manifest."""
    import csv
    import io
    with _parents(root_fd, ('registry',)) as fd:
        with _regular(fd, 'data_manifest.csv') as (stream, before):
            if before.st_size > MAX_MANIFEST_BYTES:
                raise SegmentError('oversized classification manifest')
            raw = stream.read(MAX_MANIFEST_BYTES + 1)
    if len(raw) > MAX_MANIFEST_BYTES:
        raise SegmentError('oversized classification manifest')
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    if (not {'path', 'class'} <= set(reader.fieldnames or []) or
            len(reader.fieldnames) != len(set(reader.fieldnames))):
        raise SegmentError('classification manifest needs path and class')
    rows = list(reader)
    seen = set()
    for row in rows:
        p = _relative(row.get('path'))
        if p in seen or row.get('class') not in CLASSES or None in row:
            raise SegmentError('duplicate or invalid classification row')
        seen.add(p)
    return rows, hashlib.sha256(raw).hexdigest()


def _permitted(relative, rows):
    _relative(relative)
    if classify(relative, rows) != 'RECORDED':
        raise SegmentError('source must be classified RECORDED by data_manifest.csv')
    if any(relative == p or relative.startswith(p + '/') for p in PUBLIC_EXCLUDE):
        raise SegmentError('public archive exclusion applies to this source')
    if any(skipped(x) for x in PurePosixPath(relative).parts[1:]):
        raise SegmentError('live state, temporary or skipped source path')


def _json(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SegmentError('duplicate JSON manifest key')
        result[key] = value
    return result


def _digest(value):
    if not isinstance(value, str) or not DIGEST.fullmatch(value):
        raise SegmentError('explicit SHA256 required')
    return value


def _manifest(archive_fd, expected, budget):
    _digest(expected)
    _integer(budget, 'budget_bytes', minimum=1)
    with _regular(archive_fd, 'manifest.json') as (stream, before):
        if before.st_size > min(MAX_MANIFEST_BYTES, budget):
            raise SegmentError('manifest exceeds its bound or budget')
        raw = stream.read(MAX_MANIFEST_BYTES + 1)
    if len(raw) > MAX_MANIFEST_BYTES or hashlib.sha256(raw).hexdigest() != expected:
        raise SegmentError('manifest SHA256 mismatch or size bound exceeded')
    try:
        m = json.loads(raw, object_pairs_hook=_unique,
                       parse_constant=lambda _: (_ for _ in ()).throw(SegmentError('nonfinite manifest')))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise SegmentError('invalid manifest JSON') from exc
    if not isinstance(m, dict) or set(m) != {
            'format', 'version', 'source', 'classification_manifest_sha256',
            'public_exclusions_applied', 'chunk_bytes', 'segments'}:
        raise SegmentError('unsupported manifest fields')
    if m['format'] != FORMAT or type(m['version']) is not int or m['version'] != VERSION:
        raise SegmentError('unsupported manifest format/version')
    if m['public_exclusions_applied'] is not True:
        raise SegmentError('public exclusion declaration required')
    _digest(m['classification_manifest_sha256'])
    chunk = _integer(m['chunk_bytes'], 'chunk_bytes', minimum=1, maximum=MAX_SEGMENT_BYTES)
    source = m['source']
    if not isinstance(source, dict) or set(source) != {'path', 'class', 'bytes', 'mtime_ns', 'sha256'}:
        raise SegmentError('invalid source identity')
    _relative(source['path'])
    if source['class'] != 'RECORDED':
        raise SegmentError('RECORDED identity required')
    _integer(source['bytes'], 'source bytes')
    _integer(source['mtime_ns'], 'source mtime_ns')
    _digest(source['sha256'])
    parts = m['segments']
    if not isinstance(parts, list) or len(parts) > MAX_SEGMENTS:
        raise SegmentError('bounded segment list required')
    count = (source['bytes'] + chunk - 1) // chunk
    if len(parts) != count:
        raise SegmentError('segment count differs from declared file size')
    offset = 0
    for i, part in enumerate(parts):
        if not isinstance(part, dict) or set(part) != {'name', 'offset', 'bytes', 'sha256'}:
            raise SegmentError('invalid segment identity')
        if part['name'] != f'segment-{i:06d}.bin':
            raise SegmentError('unexpected, duplicate or unsafe segment name')
        _integer(part['offset'], 'segment offset')
        _integer(part['bytes'], 'segment bytes', minimum=1, maximum=chunk)
        if part['offset'] != offset or part['bytes'] != min(chunk, source['bytes'] - offset):
            raise SegmentError('segment overlap, gap or invalid length')
        _digest(part['sha256'])
        offset += part['bytes']
    if source['bytes'] + len(raw) > budget:
        raise SegmentError('archive exceeds explicit byte budget')
    entries = set()
    with os.scandir(archive_fd) as scan:
        for entry in scan:
            entries.add(entry.name)
            if len(entries) > len(parts) + 1:
                raise SegmentError('archive has unlisted entries')
    if entries != {'manifest.json', *(p['name'] for p in parts)}:
        raise SegmentError('archive has missing or unlisted entries')
    return m, len(raw)


def _consume(archive_fd, manifest, sink=None):
    full = hashlib.sha256()
    for part in manifest['segments']:
        h = hashlib.sha256()
        with _regular(archive_fd, part['name']) as (stream, before):
            if before.st_size != part['bytes']:
                raise SegmentError('segment size mismatch')
            remaining = part['bytes']
            while remaining:
                block = stream.read(min(BLOCK_BYTES, remaining))
                if not block:
                    raise SegmentError('truncated segment')
                remaining -= len(block)
                h.update(block); full.update(block)
                if sink is not None:
                    sink.write(block)
            if stream.read(1):
                raise SegmentError('segment grew beyond declared bytes')
        if h.hexdigest() != part['sha256']:
            raise SegmentError('segment SHA256 mismatch')
    if full.hexdigest() != manifest['source']['sha256']:
        raise SegmentError('reconstructed file SHA256 mismatch')


def _publish_directory(parent_fd, temporary, destination):
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, 'renameat2', None)
    if rename is None:
        raise SegmentError('atomic no-overwrite directory publication requires Linux renameat2')
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(parent_fd, os.fsencode(temporary), parent_fd, os.fsencode(destination), 1):
        error = ctypes.get_errno()
        if error in (errno.ENOSYS, errno.EINVAL):
            raise SegmentError('filesystem lacks atomic no-overwrite directory publication')
        raise OSError(error, os.strerror(error), destination)


def _receipt(state, manifest, digest, manifest_bytes):
    return dict(state=state, path=manifest['source']['path'],
                source_bytes=manifest['source']['bytes'], segments=len(manifest['segments']),
                archive_bytes=manifest['source']['bytes'] + manifest_bytes,
                manifest_sha256=digest, source_sha256=manifest['source']['sha256'],
                budget_scope='This local bundle only; remote archive capacity is not assessed.',
                scope='Opaque local byte identity only; no remote backup, source authenticity or recorder completeness proved.')


def pack_recording(root, relative_path, out, *, chunk_bytes=50_000_000,
                   budget_bytes, min_age_seconds=900, now_ns=None):
    """Publish one new segment directory outside root, without changing its source.

    root and out.parent must already be real directories. The byte budget covers
    segments plus the manifest; no compression or payload interpretation occurs.
    Files still changing fail the stat/identity checks; age alone proves no lock.
    """
    root, out = _absolute(root), _absolute(out)
    _separate(root, out)
    _relative(relative_path)
    _integer(chunk_bytes, 'chunk_bytes', minimum=1, maximum=MAX_SEGMENT_BYTES)
    _integer(budget_bytes, 'budget_bytes', minimum=1)
    _integer(min_age_seconds, 'min_age_seconds')
    now_ns = time.time_ns() if now_ns is None else _integer(now_ns, 'now_ns')
    with _directory(root) as root_fd, _directory(out.parent) as parent_fd:
        rows, classification_sha = _load_classification(root_fd)
        _permitted(relative_path, rows)
        try:
            os.stat(out.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise FileExistsError('archive destination already exists')
        source_parts = PurePosixPath(relative_path).parts
        temporary = '.segments-' + secrets.token_hex(16)
        published = False
        created = []
        os.mkdir(temporary, 0o700, dir_fd=parent_fd)
        temporary_fd = os.open(temporary, _DIR_FLAGS, dir_fd=parent_fd)
        try:
            with _parents(root_fd, source_parts[:-1]) as source_parent:
                with _regular(source_parent, source_parts[-1]) as (stream, before):
                    _integer(before.st_mtime_ns, 'source mtime_ns')
                    if before.st_size > budget_bytes:
                        raise SegmentError('source exceeds explicit byte budget')
                    if now_ns - before.st_mtime_ns < min_age_seconds * 10**9:
                        raise SegmentError('source is too recent or has a future timestamp')
                    if (before.st_size + chunk_bytes - 1) // chunk_bytes > MAX_SEGMENTS:
                        raise SegmentError('too many segments; increase chunk size')
                    full = hashlib.sha256(); parts = []; total = 0
                    while total < before.st_size:
                        name = f'segment-{len(parts):06d}.bin'
                        length = min(chunk_bytes, before.st_size - total)
                        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                     0o600, dir_fd=temporary_fd)
                        created.append(name)
                        h = hashlib.sha256(); remaining = length
                        with os.fdopen(fd, 'wb') as target:
                            while remaining:
                                block = stream.read(min(BLOCK_BYTES, remaining))
                                if not block:
                                    raise SegmentError('source truncated while packing')
                                target.write(block); h.update(block); full.update(block)
                                remaining -= len(block)
                            target.flush(); os.fsync(target.fileno())
                        parts.append(dict(name=name, offset=total, bytes=length, sha256=h.hexdigest()))
                        total += length
                    if stream.read(1):
                        raise SegmentError('source grew while packing')
                # _regular checks both the open descriptor and current path identity.
            # Also detect an availability/classification edit during the copy.
            _, current_classification = _load_classification(root_fd)
            if classification_sha != current_classification:
                raise SegmentError('classification manifest changed during packing')
            m = dict(format=FORMAT, version=VERSION,
                     source=dict(path=relative_path, **{'class': 'RECORDED'}, bytes=total,
                                 mtime_ns=before.st_mtime_ns, sha256=full.hexdigest()),
                     classification_manifest_sha256=classification_sha,
                     public_exclusions_applied=True, chunk_bytes=chunk_bytes, segments=parts)
            raw = _json(m)
            if len(raw) > MAX_MANIFEST_BYTES or total + len(raw) > budget_bytes:
                raise SegmentError('segments plus manifest exceed budget')
            fd = os.open('manifest.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=temporary_fd)
            created.append('manifest.json')
            with os.fdopen(fd, 'wb') as f:
                f.write(raw); f.flush(); os.fsync(f.fileno())
            os.fsync(temporary_fd)
            _publish_directory(parent_fd, temporary, out.name)
            published = True
            os.fsync(parent_fd)
            return _receipt('PACKED', m, hashlib.sha256(raw).hexdigest(), len(raw))
        finally:
            if not published:
                for name in created:
                    os.unlink(name, dir_fd=temporary_fd)
            os.close(temporary_fd)
            if not published:
                os.rmdir(temporary, dir_fd=parent_fd)


def verify_recording(archive, *, expected_manifest_sha256, budget_bytes):
    """Read-only verification against a manifest identity pinned outside the bundle."""
    with _directory(archive) as fd:
        m, size = _manifest(fd, expected_manifest_sha256, budget_bytes)
        # A receipt's RECORDED claim never overrides the public exclusion.
        _permitted(m['source']['path'], [{'path': m['source']['path'], 'class': 'RECORDED'}])
        _consume(fd, m)
    return _receipt('VERIFIED', m, expected_manifest_sha256, size)


def restore_recording(archive, root, *, expected_manifest_sha256, budget_bytes):
    """Verify while streaming to a private file, then publish without replacement.

    The destination root must already exist and classify the path RECORDED in
    its own data_manifest.csv. Missing parent directories may be created; a
    failed restore never publishes a partially reconstructed destination file.
    """
    root, archive = _absolute(root), _absolute(archive)
    _separate(root, archive)
    with _directory(archive) as archive_fd, _directory(root) as root_fd:
        m, size = _manifest(archive_fd, expected_manifest_sha256, budget_bytes)
        rows, classification_sha = _load_classification(root_fd)
        relative = m['source']['path']
        _permitted(relative, rows)
        parts = PurePosixPath(relative).parts
        with _parents(root_fd, parts[:-1], create=True) as parent_fd:
            try:
                os.stat(parts[-1], dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise FileExistsError('restore destination already exists; never overwritten')
            temporary = '.restore-' + secrets.token_hex(16)
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=parent_fd)
            try:
                with os.fdopen(fd, 'wb') as target:
                    _consume(archive_fd, m, target)
                    target.flush()
                    os.utime(target.fileno(), ns=(m['source']['mtime_ns'], m['source']['mtime_ns']))
                    os.fsync(target.fileno())
                _, current_classification = _load_classification(root_fd)
                if current_classification != classification_sha:
                    raise SegmentError('destination classification changed during restoration')
                os.link(temporary, parts[-1], src_dir_fd=parent_fd, dst_dir_fd=parent_fd,
                        follow_symlinks=False)
                os.fsync(parent_fd)
            finally:
                os.unlink(temporary, dir_fd=parent_fd)
    return _receipt('RESTORED', m, expected_manifest_sha256, size)
