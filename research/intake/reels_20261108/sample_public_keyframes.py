"""Read MPD/SIDX byte indices and preview each declared video fragment; never a full/audio transcript."""
import gzip
import json
from pathlib import Path
import struct
import subprocess
import sys

from read_public_media import RAW, get, initialize


def index(raw):
    cursor = 0
    while cursor + 8 <= len(raw):
        size, name = struct.unpack_from('>I4s', raw, cursor)
        if size < 8 or cursor + size > len(raw):
            raise ValueError('incomplete/unsupported MP4 index box')
        if name == b'sidx':
            version = raw[cursor + 8]
            scale = struct.unpack_from('>I', raw, cursor + 16)[0]
            if version == 0:
                earliest, first = struct.unpack_from('>II', raw, cursor + 20)
                count = struct.unpack_from('>H', raw, cursor + 30)[0]
                pos = cursor + 32
            elif version == 1:
                earliest, first = struct.unpack_from('>QQ', raw, cursor + 20)
                count = struct.unpack_from('>H', raw, cursor + 38)[0]
                pos = cursor + 40
            else:
                raise ValueError('unsupported SIDX version')
            offset, time = cursor + size + first, earliest
            result = []
            for number in range(count):
                size_word, duration, sap = struct.unpack_from('>III', raw, pos)
                pos += 12
                if size_word >> 31 or not scale:
                    raise ValueError('nested/invalid-timing segment is outside this preview')
                length = size_word & 0x7fffffff
                result.append(dict(number=number, start=offset, end=offset + length - 1,
                                   seconds=time / scale, duration_seconds=duration / scale,
                                   starts_with_sap=bool(sap >> 31), sap_type=(sap >> 28) & 7,
                                   sap_delta=sap & 0x0fffffff))
                offset += length
                time += duration
            if pos != cursor + size:
                raise ValueError('SIDX closure mismatch')
            return result
        cursor += size
    raise ValueError('SIDX absent')


def plan():
    path = RAW / 'candidates.json'
    if path.exists():
        raise ValueError('preview already planned; no silent source redefinition')
    all_sources = json.loads((RAW / 'source_media.json').read_text())
    caps = {'DfVJWnfMysj': 12288, 'DfdWYmkv6Cy': 24576, 'Dc7BZU2hqaC': 20480}
    candidates = {}
    for source in all_sources:
        code = source['shortcode']
        video = min((r for r in source['representations'] if r['mimeType'] == 'video/mp4'),
                    key=lambda r: int(r['FBContentLength']))
        raw = gzip.decompress((RAW / (code + '_init.gz')).read_bytes())
        segments = index(raw)
        expected = video['segments'][0]
        assert str(segments[0]['start']) + '-' + str(segments[0]['end']) == expected['FBFirstSegmentRange']
        assert str(segments[1]['start']) + '-' + str(segments[1]['end']) == expected['FBSecondSegmentRange']
        assert segments[-1]['end'] + 1 == int(video['FBContentLength'])
        for segment in segments:
            label = code + '_segment_' + str(segment['number']).zfill(2)
            end = min(segment['end'], segment['start'] + caps[code] - 1)
            candidates[label] = dict(label=label, url=video['url'], shortcode=code,
                source_representation=video['id'], source_segment=segment,
                byte_range=[segment['start'], end], cap=end - segment['start'] + 2,
                purpose='first random-access picture preview, not complete video/audio')
    path.write_text(json.dumps(candidates, indent=2))
    print(json.dumps(dict(previews=len(candidates), reserved_body_bytes=sum(x['cap'] for x in candidates.values()))))


def fetch():
    initialize()
    candidates = json.loads((RAW / 'candidates.json').read_text())
    for item in candidates.values():
        get(item['label'], item['url'], item['cap'], byte_range=item['byte_range'])


def decode():
    candidates = json.loads((RAW / 'candidates.json').read_text())
    output = RAW / 'frames'
    output.mkdir(exist_ok=True)
    result = []
    for item in candidates.values():
        label, code = item['label'], item['shortcode']
        source = RAW / (label + '.gz')
        if not source.exists():
            result.append(dict(label=label, state='NOT_ACQUIRED'))
            continue
        clip = output / (label + '.partial.mp4')
        image = output / (label + '.png')
        if clip.exists() or image.exists():
            raise ValueError('derived preview already exists; preserve it')
        clip.write_bytes(gzip.decompress((RAW / (code + '_init.gz')).read_bytes())
                         + gzip.decompress(source.read_bytes()))
        run = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(clip), '-frames:v', '1', str(image)],
                             capture_output=True, text=True, timeout=30)
        result.append(dict(label=label, source_seconds=item['source_segment']['seconds'],
            state='PREVIEW_FRAME' if image.exists() else 'UNDECODABLE_PREFIX',
            path=str(image) if image.exists() else None, ffmpeg_exit=run.returncode,
            diagnostic=run.stderr[:1200], complete_video=False, audio_read=False))
    (RAW / 'preview_decode.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(dict(preview_frames=sum(x['state'] == 'PREVIEW_FRAME' for x in result), planned=len(result))))


def recover():
    """One adjacent continuation for the sole undecodable prefix; retain the original failure."""
    original = json.loads((RAW / 'preview_decode.json').read_text())
    failed = [r for r in original if r['state'] == 'UNDECODABLE_PREFIX']
    if len(failed) != 1 or failed[0]['label'] != 'DfdWYmkv6Cy_segment_09':
        raise ValueError('recovery is limited to the recorded single missing preview')
    result_path = RAW / 'preview_recovery.json'
    if result_path.exists():
        raise ValueError('recovery already attempted')
    item = json.loads((RAW / 'candidates.json').read_text())[failed[0]['label']]
    start = item['byte_range'][1] + 1
    end = min(item['source_segment']['end'], start + 24576 - 1)
    label = item['label'] + '_tail'
    (RAW / 'preview_recovery_plan.json').write_text(json.dumps(dict(label=label,
        original=item['label'], byte_range=[start, end], reserved_bytes=end - start + 2,
        financial_statistics=False), indent=2))
    _, tail = get(label, item['url'], end - start + 2, byte_range=(start, end))
    original_prefix = gzip.decompress((RAW / (item['label'] + '.gz')).read_bytes())
    init = gzip.decompress((RAW / (item['shortcode'] + '_init.gz')).read_bytes())
    clip = RAW / 'frames' / (item['label'] + '_extended.partial.mp4')
    image = RAW / 'frames' / (item['label'] + '_extended.png')
    clip.write_bytes(init + original_prefix + tail)
    run = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(clip), '-frames:v', '1', str(image)],
                         capture_output=True, text=True, timeout=30)
    row = dict(label=item['label'], source_seconds=item['source_segment']['seconds'],
        state='RECOVERED_PREVIEW_FRAME' if image.exists() else 'STILL_UNDECODABLE',
        path=str(image) if image.exists() else None, ffmpeg_exit=run.returncode,
        diagnostic=run.stderr[:1200], original_failure_preserved=True,
        complete_video=False, audio_read=False)
    result_path.write_text(json.dumps(row, indent=2))
    print(json.dumps(row))


if __name__ == '__main__':
    {'plan': plan, 'fetch': fetch, 'decode': decode, 'recover': recover}[sys.argv[1]]()
