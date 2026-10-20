#!/usr/bin/env python3
"""Validate source/alias/queue metadata without reading outcomes or contacting providers.

Historical intake status may differ from the live queue: that is not an error.
Missing or changed source versions remain explicit; no file is repaired, imported,
frozen or promoted. This checks provenance structure, not the truth of a source,
complete corpus coverage, profitable evidence or permission to acquire a dataset.
"""

import argparse
import csv
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
from urllib.parse import urlsplit


QUEUE = "registry/methods.csv"
ALIASES = "registry/methods_aliases.csv"
INTAKE = "research/intake/source_methods_20261020.json"
QUEUE_STATES = {"UNTESTED", "BLOCKED", "PARTIAL", "TESTED", "N/A"}
INTAKE_STATES = {"untested", "blocked", "partial", "null", "forward", "confirmed_original"}


def audit(root):
    root = Path(root).resolve()
    report = {"summary": {"queue_rows": 0, "source_methods": 0, "aliases": 0,
                          "source_files": 0, "provider_entries": 0, "id_reassignments": 0,
                          "errors": 0, "warnings": 0},
              "issues": []}

    def issue(level, code, message, path, record_id=None):
        item = dict(severity=level, code=code, message=message, path=path)
        if record_id is not None:
            item['record_id'] = record_id
        report['issues'].append(item)
        report['summary'][level + 's'] += 1

    def local(raw):
        if not isinstance(raw, str) or not raw:
            raise ValueError("Empty/non-text local path")
        rel = PurePosixPath(raw)
        if rel.is_absolute() or '..' in rel.parts or '\\' in raw:
            raise ValueError("Local source path escapes repository")
        if any((root / Path(*rel.parts[:i])).is_symlink() for i in range(1, len(rel.parts) + 1)):
            raise ValueError("Local source path contains a symlink")
        path = root / raw
        path.resolve().relative_to(root)
        return path

    def table(path, columns):
        try:
            with local(path).open(newline='', encoding='utf-8') as handle:
                reader = csv.DictReader(handle)
                if not set(columns) <= set(reader.fieldnames or []):
                    raise ValueError("Missing required CSV columns")
                if len(reader.fieldnames) != len(set(reader.fieldnames)):
                    raise ValueError("Duplicate CSV column names")
                rows = list(reader)
                if any(None in row or any(row[k] is None for k in columns) for row in rows):
                    raise ValueError("Malformed CSV row")
                return rows
        except (OSError, ValueError) as exc:
            issue('error', 'TABLE_INVALID', str(exc), path)
            return []

    def unique(rows, key, path):
        result = {}
        for row in rows:
            identifier = row.get(key)
            if not isinstance(identifier, str) or not identifier.strip():
                issue('error', 'ID_MISSING', f"Missing {key}", path)
            elif identifier in result:
                issue('error', 'DUPLICATE_ID', f"Duplicate {key}", path, identifier)
            else:
                result[identifier] = row
        return result

    def targets(value, path, identifier):
        if not isinstance(value, str):
            issue('error', 'TARGET_INVALID', 'Queue targets must be text', path, identifier)
            return
        if not queue_readable:
            return  # A malformed queue is reported once, not as hundreds of false dangling targets.
        for target in value.split(';'):
            if target and target != 'CONTEXT' and target not in queue:
                issue('error', 'QUEUE_TARGET_MISSING', f"Unknown queue target {target}", path, identifier)

    queue_rows = table(QUEUE, ['id', 'method', 'status', 'data_held', 'rid'])
    queue_readable = not any(i['path'] == QUEUE and i['code'] == 'TABLE_INVALID' for i in report['issues'])
    queue = unique(queue_rows, 'id', QUEUE)
    report['summary']['queue_rows'] = len(queue_rows)
    for identifier, row in queue.items():
        if not re.fullmatch(r'M[0-9]+', identifier):
            issue('error', 'QUEUE_ID_INVALID', 'Expected an M-number', QUEUE, identifier)
        if row['status'] not in QUEUE_STATES:
            issue('error', 'QUEUE_STATUS_INVALID', 'Unknown live queue status', QUEUE, identifier)
        if not row['method'].strip():
            issue('error', 'METHOD_TITLE_EMPTY', 'Live queue method is unnamed', QUEUE, identifier)
    # IDs need uniqueness, not continuity: writers can reserve separate blocks.
    alias_rows = table(ALIASES, ['rec_id', 'title', 'intake_status', 'queue_id', 'also'])
    aliases = unique(alias_rows, 'rec_id', ALIASES)
    report['summary']['aliases'] = len(alias_rows)
    for identifier, row in aliases.items():
        if not row['queue_id'].strip():
            issue('error', 'QUEUE_TARGET_EMPTY', 'Alias has no queue or CONTEXT target', ALIASES, identifier)
        targets(row['queue_id'], ALIASES, identifier)
        targets(row['also'], ALIASES, identifier)
        if row['intake_status'] not in INTAKE_STATES | {'context'}:
            issue('error', 'ALIAS_STATUS_INVALID', 'Unknown intake status', ALIASES, identifier)

    try:
        payload = json.loads(local(INTAKE).read_text(encoding='utf-8'))
        if not isinstance(payload, dict) or not isinstance(payload.get('methods'), list):
            raise ValueError('Expected an object with a methods array')
        if not all(isinstance(row, dict) for row in payload['methods']):
            raise ValueError('Methods must be objects')
    except (OSError, ValueError) as exc:
        issue('error', 'INTAKE_INVALID', str(exc), INTAKE)
        return report
    methods = unique(payload['methods'], 'id', INTAKE)
    report['summary']['source_methods'] = len(payload['methods'])
    for identifier, method in methods.items():
        for field in ('title', 'exact_tested_scope', 'unrun_scope', 'next_action'):
            if not isinstance(method.get(field), str) or not method[field].strip():
                issue('error', 'SCOPE_MISSING', f'Missing explicit {field}', INTAKE, identifier)
        for field in ('required_inputs', 'blockers', 'source_refs'):
            if not isinstance(method.get(field), list):
                issue('error', 'METHOD_SCHEMA_INVALID', f'{field} must be a list', INTAKE, identifier)
        if method.get('status') not in INTAKE_STATES:
            issue('error', 'INTAKE_STATUS_INVALID', 'Unknown historical intake status', INTAKE, identifier)
        if identifier not in aliases:
            issue('error', 'ALIAS_MISSING', 'Source method is not reconciled to the live queue or CONTEXT', INTAKE, identifier)
        if not method.get('source_refs'):
            issue('error', 'SOURCE_REFERENCE_MISSING', 'Method has no source reference', INTAKE, identifier)
        elif isinstance(method['source_refs'], list):
            for reference in method['source_refs']:
                raw = reference.get('path') if isinstance(reference, dict) else None
                if not isinstance(raw, str) or not raw.strip():
                    issue('error', 'SOURCE_REFERENCE_INVALID', 'Source reference must name its received path or URL', INTAKE, identifier)
                    continue
                try:
                    parsed = urlsplit(raw)
                    if parsed.scheme:
                        if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
                            raise ValueError('Unsupported source URL')
                    else:
                        local(raw.split('#', 1)[0])  # Validate the path, not historical file availability.
                except ValueError as exc:
                    issue('error', 'SOURCE_REFERENCE_INVALID', str(exc), INTAKE, identifier)
    for identifier in aliases:
        if identifier not in methods:
            issue('error', 'SOURCE_METHOD_MISSING', 'Alias has no corresponding extracted source method', ALIASES, identifier)

    sources = payload.get('sources', [])
    if not isinstance(sources, list) or not all(isinstance(row, dict) for row in sources):
        issue('error', 'SOURCE_SCHEMA_INVALID', 'sources must be an array of objects', INTAKE)
        sources = []
    source_map = unique(sources, 'path', INTAKE)
    report['summary']['source_files'] = len(sources)
    for path, source in source_map.items():
        if 'current_source_review_required' in source and not isinstance(source['current_source_review_required'], bool):
            issue('error', 'SOURCE_SCHEMA_INVALID', 'Review-required flag must be a boolean', INTAKE, path)
        snapshot = source.get('sha256', '')
        reviewed = source.get('current_sha256') or snapshot
        for value in (snapshot, reviewed):
            if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
                issue('error', 'SOURCE_DIGEST_INVALID', 'Expected SHA-256 source digest', INTAKE, path)
        identifiers = source.get('method_ids', [])
        if not isinstance(identifiers, list) or not all(isinstance(x, str) for x in identifiers):
            issue('error', 'SOURCE_SCHEMA_INVALID', 'Source method_ids must be an array of IDs', INTAKE, path)
            identifiers = []
        for identifier in identifiers:
            if identifier not in methods:
                issue('error', 'SOURCE_METHOD_MISSING', 'Source lists unknown method', INTAKE, identifier)
        try:
            actual = hashlib.sha256(local(path).read_bytes()).hexdigest()
        except (OSError, ValueError) as exc:
            issue('error', 'SOURCE_FILE_UNREADABLE', str(exc), path)
            continue
        if source.get('current_source_review_required'):
            issue('warning', 'SOURCE_REVIEW_PENDING', 'Changed source sections are explicitly not yet reconciled', path)
        if actual != reviewed:
            issue('warning', 'SOURCE_CHANGED_SINCE_REVIEW', 'Local source differs from the last recorded source version', path)
        elif actual != snapshot and not source.get('current_source_review_required'):
            issue('warning', 'SOURCE_VERSION_AMBIGUOUS', 'Snapshot differs but no pending extraction review is marked', path)

    supplements = payload.get('supplemental_intakes', [])
    if not isinstance(supplements, list) or not all(isinstance(row, dict) for row in supplements):
        issue('error', 'SUPPLEMENT_INVALID', 'Supplemental intakes must be objects', INTAKE)
        supplements = []
    unique(supplements, 'intake_id', INTAKE)
    received = set()
    for supplement in supplements:
        sid = supplement.get('intake_id', '')
        records = supplement.get('records_added', [])
        if not isinstance(records, list) or not all(isinstance(x, str) for x in records):
            issue('error', 'SUPPLEMENT_INVALID', 'records_added must be an array of IDs', INTAKE, sid)
            continue
        for identifier in records:
            if identifier not in methods:
                issue('error', 'SUPPLEMENT_METHOD_MISSING', 'Supplement refers to unknown method', INTAKE, identifier)
            if identifier in received:
                issue('error', 'SUPPLEMENT_RECORD_DUPLICATE', 'Method counted more than once across supplements', INTAKE, identifier)
            received.add(identifier)
        media = supplement.get('media_sources', [])
        if not isinstance(media, list) or not all(isinstance(x, dict) for x in media):
            issue('error', 'SUPPLEMENT_INVALID', 'media_sources must be objects', INTAKE, sid)
            continue
        if 'media_source_count' in supplement and supplement['media_source_count'] != len(media):
            issue('error', 'SOURCE_COUNT_MISMATCH', 'Declared source count does not match enumerated sources', INTAKE, sid)
        for item in media:
            if not item.get('basis') or not item.get('url'):
                issue('error', 'SOURCE_BASIS_MISSING', 'Media source lacks URL or actual received basis', INTAKE, sid)

    folder = root / 'research' / 'intake'
    if folder.is_dir():
        for path in sorted(folder.glob('source_catalog*.csv')):
            relative = path.relative_to(root).as_posix()
            providers = table(relative, ['id', 'provider', 'url', 'received_scope', 'access_boundary', 'existing_queue'])
            unique(providers, 'id', relative)
            report['summary']['provider_entries'] += len(providers)
            urls = set()
            for row in providers:
                identifier = row['id']
                try:
                    parsed = urlsplit(row['url'])
                    valid_url = parsed.scheme in {'http', 'https'} and bool(parsed.netloc)
                except ValueError:
                    valid_url = False
                if not valid_url:
                    issue('error', 'PROVIDER_URL_INVALID', 'Provider URL must be HTTP(S)', relative, identifier)
                if row['url'] in urls:
                    issue('error', 'PROVIDER_URL_DUPLICATE', 'Repeated provider URL', relative, identifier)
                urls.add(row['url'])
                if not row['provider'].strip() or not row['received_scope'].strip() or not row['access_boundary'].strip():
                    issue('error', 'PROVIDER_SCOPE_MISSING', 'Provider scope and access boundary must be explicit', relative, identifier)
                if not row['existing_queue'].strip():
                    issue('error', 'QUEUE_TARGET_EMPTY', 'Provider must name related queue IDs or CONTEXT', relative, identifier)
                targets(row['existing_queue'], relative, identifier)
    for path in sorted((root/'registry').glob('method_id_reassignment_*.json')):
        relative = path.relative_to(root).as_posix()
        try:
            record = json.loads(local(relative).read_text(encoding='utf-8'))
            if not isinstance(record, dict) or not all(isinstance(record.get(k), str) and record[k].strip()
                                                       for k in ('declared_id', 'canonical_id', 'reason', 'source_commit', 'round')):
                raise ValueError('ID collision record lacks explicit provenance and reason')
            header, original = record.get('original_header'), record.get('original_row')
            if (not isinstance(header, list) or not isinstance(original, list) or len(header) != len(original)
                    or not all(isinstance(k, str) for k in header) or len(set(header)) != len(header)):
                raise ValueError('Collision record must preserve the original row and columns')
            before = dict(zip(header, original))
            if before.get('id') != record['declared_id'] or not before.get('method'):
                raise ValueError('Original row does not match the declared ID')
            canonical = queue.get(record['canonical_id'])
            if queue_readable and (not canonical or canonical['method'] != before['method']):
                raise ValueError('Mapped canonical method is absent or describes a different rule')
            report['summary']['id_reassignments'] += 1
        except (OSError, ValueError) as exc:
            issue('error', 'ID_REASSIGNMENT_INVALID', str(exc), relative)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--strict', action='store_true', help='also fail on warnings')
    args = parser.parse_args(argv)
    report = audit(args.root)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(json.dumps(report['summary'], sort_keys=True))
        for item in report['issues']:
            print(f"{item['severity']} {item['code']}: {item['path']} — {item['message']}")
    return int(bool(report['summary']['errors'] or (args.strict and report['summary']['warnings'])))


if __name__ == '__main__':
    sys.exit(main())
