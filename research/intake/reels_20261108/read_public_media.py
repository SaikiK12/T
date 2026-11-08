"""One bounded public-media intake, with persistent call/body reservations and no redirects."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib import error, parse, request

from read_public_pages import IDS, Metadata, NoRedirect

HERE = Path(__file__).resolve().parent
RAW = Path('/tmp/owner_reels_20261108/media')
EVENTS = HERE / 'media_requests.jsonl'
MAX_CALLS = 12
MAX_BYTES = 1700000


def now():
    return datetime.now(timezone.utc).isoformat()


def rows():
    raw = EVENTS.read_bytes() if EVENTS.exists() else b''
    if raw and not raw.endswith(b'\n'):
        raise RuntimeError('cut source ledger; no retry')
    return [json.loads(x) for x in raw.splitlines()]


def append(row):
    with EVENTS.open('ab') as f:
        f.write((json.dumps(row, sort_keys=True) + '\n').encode())


def initialize():
    reservation = HERE / 'media_reservation.json'
    if not reservation.exists():
        if EVENTS.exists() or RAW.exists():
            raise RuntimeError('unreconciled prior source attempt')
        RAW.mkdir(parents=True)
        reservation.write_text(json.dumps(dict(reserved_utc=now(), max_calls=MAX_CALLS,
            max_application_bytes=MAX_BYTES, claim_issue_comment=6721852787,
            inherited_conservative_calls=7854, inherited_conservative_bytes=260396010,
            cumulative_conservative_calls=7866, cumulative_conservative_bytes=262096010,
            original_call_cap=8000, original_byte_cap=262144000,
            remaining_original_calls=134, remaining_original_bytes=47990,
            refund=False, new_grant=False, scope='exact owner-linked public source assets only'), indent=2) + '\n')
    else:
        stored = json.loads(reservation.read_text())
        if stored['max_calls'] != MAX_CALLS or stored['max_application_bytes'] != MAX_BYTES:
            raise RuntimeError('reservation mismatch')


def get(label, url, cap, method='GET', accept_encoding=None, post_data=None, public_nonce=None, byte_range=None):
    parsed = parse.urlsplit(url)
    host = parsed.hostname or ''
    if (parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port not in (None, 443)
            or not (host == 'www.instagram.com' or host.endswith('.cdninstagram.com') or host.endswith('.fbcdn.net'))):
        raise RuntimeError('URL outside fixed public source scope')
    history = rows()
    if any(r['event'] == 'STOP' for r in history):
        raise RuntimeError('persistent source stop; no access variant')
    starts = [r for r in history if r['event'] == 'START']
    finished = {r['label'] for r in history if r['event'] == 'END'}
    if any(r['label'] not in finished for r in starts):
        raise RuntimeError('unknown source spend; no resume')
    if any(r['label'] == label or (method != 'POST' and r['url'] == url and r['method'] == method
                                  and r.get('accept_encoding') == accept_encoding
                                  and r.get('byte_range') == (list(byte_range) if byte_range is not None else None)) for r in starts):
        raise RuntimeError('request already attempted')
    if not re.fullmatch('[A-Za-z0-9_-]+', label) or method not in ('GET', 'HEAD', 'POST') or cap < 0:
        raise RuntimeError('invalid fixed request')
    if method == 'POST' and (host != 'www.instagram.com' or parsed.path != '/api/graphql'
                             or label not in [x + '_public_query' for x in IDS]
                             or not post_data or not public_nonce):
        raise RuntimeError('only the fixed anonymous read query is allowed')
    if method == 'POST':
        fields = parse.parse_qs(post_data.decode('utf-8'), strict_parsing=True)
        if (fields.get('doc_id') != ['27130156389949648']
                or fields.get('fb_api_req_friendly_name') != ['PolarisLoggedOutDesktopWWWPostRootContentQuery']
                or fields.get('lsd') != [public_nonce]
                or set(json.loads(fields['variables'][0])) != {'media_id'}):
            raise RuntimeError('POST outside the fixed anonymous read query')
    extra = HERE / 'media_call_extension.json'
    call_limit = MAX_CALLS
    if extra.exists():
        extension = json.loads(extra.read_text())
        prefix = EVENTS.read_bytes()[:extension['inherited_ledger_bytes']]
        if hashlib.sha256(prefix).hexdigest() != extension['inherited_ledger_sha256']:
            raise RuntimeError('inherited source ledger changed')
        call_limit += extension['added_calls']
    if len(starts) + 1 > call_limit or sum(r['reserved_bytes'] for r in starts) + cap > MAX_BYTES:
        raise RuntimeError('original source reservation exhausted')
    row = dict(event='START', label=label, url=url, method=method, reserved_bytes=cap,
               started_utc=now(), user_agent='Python urllib default; no override', redirects=False,
               cookies=False, authentication=False, no_refund=True, accept_encoding=accept_encoding,
               byte_scope='HTTP response-body bytes as received, including Content-Encoding; not TLS/network wire')
    if byte_range is not None:
        start, end = byte_range
        if method != 'GET' or not (0 <= start <= end) or cap != end - start + 2:
            raise RuntimeError('invalid bounded source range')
        row['byte_range'] = [start, end]
    if post_data:
        row.update(read_only_post=True, request_body_sha256=hashlib.sha256(post_data).hexdigest(),
                   query='PolarisLoggedOutDesktopWWWPostRootContentQuery',
                   public_nonce_source='__eqmc.l from the same already-held anonymous page; no account session')
    append(row)
    try:
        try:
            headers = {'Accept-Encoding': accept_encoding} if accept_encoding else {}
            if byte_range is not None:
                headers['Range'] = 'bytes=' + str(start) + '-' + str(end)
            if post_data:
                headers.update({'Content-Type': 'application/x-www-form-urlencoded',
                                'X-FB-LSD': public_nonce,
                                'X-FB-Friendly-Name': 'PolarisLoggedOutDesktopWWWPostRootContentQuery'})
            response = request.build_opener(NoRedirect()).open(request.Request(url, method=method, headers=headers, data=post_data), timeout=30)
        except error.HTTPError as exc:
            response = exc
        with response:
            body = response.read(cap) if method != 'HEAD' else b''
            result = dict(event='END', label=label, status=response.code, method=method,
                received_utc=now(), body_bytes=len(body), body_sha256=hashlib.sha256(body).hexdigest(),
                content_type=response.headers.get('Content-Type'), content_length=response.headers.get('Content-Length'),
                content_encoding=response.headers.get('Content-Encoding'),
                content_range=response.headers.get('Content-Range'),
                full_response_proven=method == 'GET' and len(body) < cap, reserved_bytes_retained=cap,
                location=response.headers.get('Location'), local_body=str(RAW / (label + '.gz')))
            (RAW / (label + '.gz')).write_bytes(gzip.compress(body, mtime=0))
            append(result)
            if byte_range is not None:
                expected = 'bytes ' + str(start) + '-' + str(end) + '/'
                if response.code != 206 or not (result['content_range'] or '').startswith(expected) or len(body) != end - start + 1:
                    raise RuntimeError('range response identity/length mismatch; no retry')
            if response.code not in (200, 206, 404, 410):
                append(dict(event='STOP', reason='HTTP ' + str(response.code), utc=now()))
            print(json.dumps(result), flush=True)
            return result, body
    except Exception as exc:
        append(dict(event='STOP', reason=type(exc).__name__ + ': ' + str(exc), utc=now()))
        raise


def main():
    initialize()
    phase = sys.argv[1]
    if phase == 'embeds':
        for shortcode in IDS:
            get(shortcode + '_embed', 'https://www.instagram.com/reel/' + shortcode + '/embed/', 98304)
    elif phase == 'thumbs':
        receipts = json.loads((HERE / 'receipts.json').read_text())
        for row in receipts['rows']:
            get(row['shortcode'] + '_thumb', row['metadata']['og:image'], 65536)
    elif phase == 'compressed-pages':
        # Ordinary content negotiation after successful 200 prefixes, never an access-denial retry.
        for shortcode in IDS:
            get(shortcode + '_page_gzip', 'https://www.instagram.com/reel/' + shortcode + '/',
                131072, accept_encoding='gzip')
    elif phase == 'public-query':
        shortcode = sys.argv[2]
        if shortcode not in IDS:
            raise SystemExit('source outside the owner links')
        text = (RAW / (shortcode + '_page_gzip.html')).read_text()
        match = re.search(r'<script\b[^>]*\bid="__eqmc"[^>]*>(.+?)</script>', text, re.S)
        nonce = json.loads(match.group(1))['l']
        initial = json.loads((HERE / 'receipts.json').read_text())
        source = next(r for r in initial['rows'] if r['shortcode'] == shortcode)
        media_id = parse.parse_qs(parse.urlsplit(source['metadata']['al:ios:url']).query)['id'][0]
        payload = parse.urlencode(dict(lsd=nonce, fb_api_caller_class='RelayModern',
            fb_api_req_friendly_name='PolarisLoggedOutDesktopWWWPostRootContentQuery',
            server_timestamps='true', variables=json.dumps({'media_id': media_id}, separators=(',', ':')),
            doc_id='27130156389949648')).encode()
        get(shortcode + '_public_query', 'https://www.instagram.com/api/graphql', 32768,
            method='POST', accept_encoding='gzip', post_data=payload, public_nonce=nonce)
    elif phase == 'range-inits':
        extra = HERE / 'media_call_extension.json'
        if extra.exists():
            raise RuntimeError('source range-init phase already reserved; no repeat')
        inherited = EVENTS.read_bytes()
        extra.write_text(json.dumps(dict(reserved_utc=now(), added_calls=40, added_bytes=0,
            inherited_ledger_bytes=len(inherited), inherited_ledger_sha256=hashlib.sha256(inherited).hexdigest(),
            claim_issue_comment=6722033543, cumulative_conservative_calls=7906,
            cumulative_conservative_bytes=262096010, remaining_original_calls=94,
            remaining_original_bytes=47990, new_grant=False, reset=False), indent=2) + '\n')
        sources = json.loads((RAW / 'source_media.json').read_text())
        for source in sources:
            video = min((x for x in source['representations'] if x['mimeType'] == 'video/mp4'),
                        key=lambda x: int(x['FBContentLength']))
            end = int(video['segments'][0]['indexRange'].split('-')[1])
            get(source['shortcode'] + '_init', video['url'], end + 2, byte_range=(0, end))
    elif phase == 'candidate':
        candidates = json.loads((RAW / 'candidates.json').read_text())
        candidate = candidates[sys.argv[2]]
        get(candidate['label'], candidate['url'], int(candidate['cap']), candidate.get('method', 'GET'),
            byte_range=candidate.get('byte_range'))
    else:
        raise SystemExit('unknown phase; no source request')


if __name__ == '__main__':
    main()
