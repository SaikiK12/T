"""One bounded DTB3 view probe plus opaque recent-tail extraction; never inspect rate values."""
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
from urllib import error, parse, request
import zlib

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
REF = 'cd469d7d8f4cd426b015d17e9cfd2b3cc3e5b8b7'
OPS = 'data/operations/quant_participant_v1'
CAP = 16384


def sha(b):
    return hashlib.sha256(b).hexdigest()


def git(path):
    return subprocess.check_output(['git', 'show', REF + ':' + path], cwd=ROOT)


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def date_rows(raw, start, end):
    lines = raw.splitlines()
    header = lines[0].lstrip(b'\xef\xbb\xbf')
    if header not in (b'DATE,DTB3', b'observation_date,DTB3'):
        raise ValueError('unexpected DTB3 CSV header')
    rows = []
    for line in lines[1:]:
        cells = line.split(b',')
        if len(cells) != 2:
            raise ValueError('unexpected DTB3 row shape')
        day = datetime.strptime(cells[0].decode('ascii'), '%Y-%m-%d').date()
        if start <= day <= end:
            rows.append((day, line))
    if not rows or [x[0] for x in rows] != sorted(set(x[0] for x in rows)):
        raise ValueError('missing/duplicate/disordered DTB3 dates')
    return header + b'\n' + b'\n'.join(x[1] for x in rows) + b'\n', dict(
        rows=len(rows), oldest=rows[0][0].isoformat(), newest=rows[-1][0].isoformat())


def main():
    reservation = HERE / 'acquisition_reservation.json'
    if reservation.exists() or (HERE / 'probe.receipt.json').exists():
        raise SystemExit('source attempt already reserved; no retry/reset')
    now = datetime.now(timezone.utc)
    end, start = now.date(), (now - timedelta(days=400)).date()
    url = 'https://fred.stlouisfed.org/graph/fredgraph.csv?' + parse.urlencode(
        dict(id='DTB3', cosd=start.isoformat(), coed=end.isoformat()))
    reservation.write_text(json.dumps(dict(reserved_utc=now.isoformat(), url=url,
        source='Federal Reserve Bank of St. Louis / FRED', publication_date='undated dynamic series view',
        added_calls=1, added_reserved_bytes=CAP + 1, inherited_calls=7906, inherited_bytes=262096010,
        conservative_calls=7907, conservative_bytes=262112395, original_calls=8000,
        original_bytes=262144000, remaining_calls=93, remaining_bytes=31605,
        refund=False, new_grant=False, scope='400-day date/schema/byte counts only; no rate reading'), indent=2) + '\n')
    ledger = [json.loads(x) for x in git('state/' + OPS + '/network/aux/requests.jsonl').splitlines()]
    starts = {r['id']: r for r in ledger if r['event'] == 'START'}
    candidates = [r for r in ledger if r['event'] == 'CONTENT'
                  and starts[r['id']]['url'] == 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTB3']
    old = max(candidates, key=lambda x: int(x['id']))
    stored = git('state/' + OPS + '/network/aux/' + old['stored_wire'])
    wire = gzip.decompress(stored)
    assert sha(wire) == old['wire_sha256'] and len(wire) == old['wire_bytes']
    # Older decompressed bytes stay opaque; only a short recent tail is parsed.
    if old['content_encoding'] == 'gzip':
        dec = zlib.decompressobj(16 + zlib.MAX_WBITS)
        digest, size, tail, first = hashlib.sha256(), 0, b'', b''
        for offset in range(0, len(wire), 1024):
            block = dec.decompress(wire[offset:offset + 1024], 4194305 - size)
            if size == 0:
                first = block.splitlines()[0]
            digest.update(block);size += len(block);tail = (tail + block)[-8192:]
        if not dec.eof or size > 4194304:
            raise ValueError('unqualified held encoding')
        assert digest.hexdigest() == old['content_sha256'] and size == old['content_bytes']
    else:
        assert old['content_encoding'] in ('', 'identity') and sha(wire) == old['content_sha256']
        first, tail = wire.splitlines()[0], wire[-8192:]
    tail = first + b'\n' + b'\n'.join(tail.splitlines()[1:]) + b'\n'
    reference, counts = date_rows(tail, start, end)
    (HERE / 'held_recent_view.csv').write_bytes(reference)
    (HERE / 'held_reference.json').write_text(json.dumps(dict(state_commit=REF,
        original_start=starts[old['id']], original_content=old,
        original_stored_file_sha256=sha(stored), derived_view_sha256=sha(reference),
        derivation='opaque streamed content hash and 8192-byte recent tail; date columns only',
        allowed_start=start.isoformat(), allowed_end=end.isoformat(), counts=counts,
        rate_values_inspected=False), indent=2) + '\n')
    row = dict(url=url, started_utc=datetime.now(timezone.utc).isoformat(),
               user_agent='Python urllib default; no override', redirects=False,
               authentication=False, cookies=False, max_wire_body=CAP)
    try:
        try:
            response = request.build_opener(NoRedirect()).open(
                request.Request(url, headers={'Accept-Encoding': 'gzip'}), timeout=30)
        except error.HTTPError as exc:
            response = exc
        with response:
            body = response.read(CAP + 1)
            row.update(status=response.code, received_utc=datetime.now(timezone.utc).isoformat(),
                       body_bytes=len(body), body_sha256=sha(body), encoding=response.headers.get('Content-Encoding', ''),
                       content_type=response.headers.get('Content-Type'), location=response.headers.get('Location'))
            (HERE / 'probe.body.gz').write_bytes(gzip.compress(body, mtime=0))
            if response.code != 200 or len(body) > CAP:
                raise ValueError('source HTTP/body stop; no retry')
            if row['encoding'] == 'gzip':
                dec = zlib.decompressobj(16 + zlib.MAX_WBITS)
                content = dec.decompress(body, 32769)
                if not dec.eof or len(content) > 32768 or dec.unused_data:
                    raise ValueError('incomplete/oversized source content')
            else:
                if row['encoding'] not in ('', 'identity'):
                    raise ValueError('unqualified content encoding')
                content = body
            (HERE / 'probe.decoded.csv').write_bytes(content)
            _, meta = date_rows(content, start, end)
            row.update(decoded_bytes=len(content), decoded_sha256=sha(content), counts=meta,
                       state='DATE_SCHEMA_BYTE_COUNTS_ONLY', rate_values_inspected=False)
    except Exception as exc:
        row.update(state='SOURCE_STOP', error=type(exc).__name__ + ': ' + str(exc))
    (HERE / 'probe.receipt.json').write_text(json.dumps(row, indent=2) + '\n')
    print(json.dumps(row))


if __name__ == '__main__':
    main()
