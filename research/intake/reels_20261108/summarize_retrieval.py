"""Offline source identity, bounded-body and preview checks; no performance measurement or source request."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import zlib

from read_public_pages import IDS
from read_public_media import HERE, RAW


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    pages = json.loads((HERE / 'receipts.json').read_text())['rows']
    requests = [json.loads(r) for r in (HERE / 'media_requests.jsonl').read_text().splitlines()]
    starts = [r for r in requests if r['event'] == 'START']
    ends = [r for r in requests if r['event'] == 'END']
    assert len(starts) == len(ends) == 52 and not any(r['event'] == 'STOP' for r in requests)
    assert sum(r['reserved_bytes'] for r in starts) <= 1700000
    for r in ends:
        raw = gzip.decompress(Path(r['local_body']).read_bytes())
        assert len(raw) == r['body_bytes'] and sha(raw) == r['body_sha256']
    previews = json.loads((RAW / 'preview_decode.json').read_text())
    recovered = json.loads((RAW / 'preview_recovery.json').read_text())
    packets = json.loads((RAW / 'keyframe_packet_checks.json').read_text())
    assert len(packets) == 36 and all(r['keyframe'] for r in packets)
    assert all('C' not in r['first_packet']['flags'] for r in packets)
    sources = []
    for code in IDS:
        page = next(p for p in pages if p['shortcode'] == code)
        original_page = gzip.decompress(Path(page['local_body']).read_bytes())
        assert sha(original_page) == page['sha256']
        record = next(r for r in ends if r['label'] == code + '_public_query')
        encoded = gzip.decompress(Path(record['local_body']).read_bytes())
        dec = zlib.decompressobj(16 + zlib.MAX_WBITS)
        prefix = dec.decompress(encoded, 1048577)
        text = prefix.decode('utf-8')
        assert text.startswith('{"data":')
        data, end = json.JSONDecoder().raw_decode(text, 8)
        media = data['xig_polaris_media']
        public = media['if_not_gated_logged_out']
        assert media['code'] == public['code'] == code
        assert str(public['pk']) == media['pk']
        assert page['metadata']['al:ios:url'] == 'instagram://media?id=' + media['pk']
        assert code in page['metadata']['canonical'] and code in page['metadata']['og:url']
        frames = [r for r in packets if r['label'].startswith(code + '_')]
        sources.append(dict(shortcode=code, source_url=page['url'], author=public['user']['username'],
            publication_utc=datetime.fromtimestamp(public['taken_at'], timezone.utc).isoformat(),
            accessed_utc=record['received_utc'], source_media_pk=media['pk'],
            requested_media_identity_verified=True, source_data_object_complete=True,
            complete_http_envelope=dec.eof, data_object_end_character=end,
            source_encoded_prefix_sha256=sha(encoded), decoded_prefix_bytes=len(prefix),
            preview_frames=len(frames), sample_seconds=[r['source_seconds'] for r in frames],
            first_packet_keyframes=all(r['keyframe'] for r in frames),
            packet_pts_equal_index_times=all(float(r['first_packet']['pts_time']) == r['source_seconds'] for r in frames),
            frames=frames, complete_video_read=False, audio_read=False, exact_audio_transcript=False,
            captions_endpoint_exposed_in_received_data=False))
    result = dict(scope='Public source review; technical counts/identity/time/byte checks only',
        financial_statistics_measured=False, predictive_trials=0,
        original_page_calls=3, page_bytes_read=sum(r['body_bytes_read'] for r in pages),
        media_calls=len(starts), media_reserved_bytes=sum(r['reserved_bytes'] for r in starts),
        media_received_body_bytes=sum(r['body_bytes'] for r in ends),
        body_byte_scope='HTTP response bodies as read, including Content-Encoding; not TLS/network wire',
        whole_original_historical_cap=dict(conservative_calls=7906, conservative_bytes=262096010,
            original_calls=8000, original_bytes=262144000, remaining_calls=94, remaining_bytes=47990,
            complete_media_reservation_retained=True, refund=False, reset=False, new_grant=False),
        original_failed_preview_preserved=True, recovered_preview=recovered,
        retained_local_source_folder=str(RAW), sources=sources,
        retained_workspace_archive=json.loads((HERE / 'local_archive_manifest.json').read_text())['root'],
        local_archive_manifest_sha256=sha((HERE / 'local_archive_manifest.json').read_bytes()),
        source_journal_sha256=sha((HERE / 'media_requests.jsonl').read_bytes()))
    (HERE / 'retrieval_summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('sources','recovered_preview')}))


if __name__ == '__main__':
    main()
