"""Bounded, one-pass public HTML intake for the owner's three reel links; no trading test."""
from datetime import datetime, timezone
import gzip
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib import error, request

HERE = Path(__file__).resolve().parent
RAW = Path('/tmp/owner_reels_20261108')
CAP = 262144
IDS = ('DfVJWnfMysj', 'DfdWYmkv6Cy', 'Dc7BZU2hqaC')


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Metadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values = {}

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'meta' and values.get('content') is not None:
            key = values.get('property') or values.get('name')
            if key:
                self.values[key] = values['content']
        if tag == 'link' and values.get('rel') == 'canonical':
            self.values['canonical'] = values.get('href')


def now():
    return datetime.now(timezone.utc).isoformat()


def main():
    budget = HERE / 'reservation.json'
    if budget.exists() or (HERE / 'receipts.json').exists() or RAW.exists():
        raise SystemExit('Prior attempt exists; no repeat or allowance reset')
    RAW.mkdir()
    budget.write_text(json.dumps(dict(
        reserved_utc=now(), original_call_cap=8000, original_byte_cap=262144000,
        inherited_conservative_calls=7851, inherited_conservative_bytes=259609578,
        added_reserved_calls=3, added_reserved_bytes=3 * CAP,
        cumulative_conservative_calls=7854, cumulative_conservative_bytes=260396010,
        remaining_original_calls=146, remaining_original_bytes=1747990,
        refund=False, new_grant=False,
        byte_scope='HTTP application-body prefixes only; no TLS/network-wire measurement',
        claim_issue_comment=6721799910,
    ), indent=2) + '\n')
    opener = request.build_opener(NoRedirect())
    receipts = []
    stopped = None
    for shortcode in IDS:
        url = 'https://www.instagram.com/reel/' + shortcode + '/'
        row = dict(shortcode=shortcode, url=url, organization='Instagram / Meta',
                   publication_date='not yet identified', started_utc=now(),
                   max_body_bytes=CAP, user_agent='Python urllib default; no override',
                   cookies=False, authentication=False, redirects=False)
        if stopped:
            row.update(state='NOT_REQUESTED_AFTER_HOST_STOP', reason=stopped)
        else:
            try:
                try:
                    response = opener.open(url, timeout=30)
                except error.HTTPError as exc:
                    response = exc
                with response:
                    body = response.read(CAP)
                    row.update(status=response.code, content_type=response.headers.get('Content-Type'),
                               content_length_header=response.headers.get('Content-Length'),
                               location=response.headers.get('Location'),
                               received_utc=now(), body_bytes_read=len(body),
                               sha256=hashlib.sha256(body).hexdigest(),
                               full_response_proven=len(body) < CAP,
                               local_body=str(RAW / (shortcode + '.body.gz')))
                    Path(row['local_body']).write_bytes(gzip.compress(body, mtime=0))
                    parsed = Metadata()
                    parsed.feed(body.decode('utf-8', errors='replace'))
                    row['metadata'] = parsed.values
                    row['state'] = 'PUBLIC_HTML_PREFIX' if response.code == 200 else 'HTTP_STOP'
                    if response.code not in (200, 404, 410):
                        stopped = 'HTTP ' + str(response.code) + '; no host retry or access variant'
                    if response.code != 200:
                        row['error_excerpt'] = body.decode('utf-8', errors='replace')[:1500]
            except Exception as exc:
                row.update(state='UNKNOWN_SOURCE_STOP', error=type(exc).__name__ + ': ' + str(exc), received_utc=now())
                stopped = row['error']
        receipts.append(row)
        (HERE / 'receipts.json').write_text(json.dumps(dict(scope='public source identification only',
            financial_statistics=False, full_media_read=False, rows=receipts), indent=2) + '\n')
        print(json.dumps(row), flush=True)


if __name__ == '__main__':
    main()
