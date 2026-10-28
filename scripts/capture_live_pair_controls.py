"""R359 bounded future input capture and online fixed-inventory controls.

One capture only. No real order, private endpoint, restart, retry or strategy
activation. The frozen R314 transport and depth guards remain unchanged.
"""
import argparse
import asyncio
from dataclasses import asdict
import fcntl
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab.live_pair_control import LivePairControl, encoded
from lab.stream_quotes import FrameClock, NS, SYMBOLS
from scripts import probe_depth_quotes as transport

LANE = ROOT / 'experiments/live_pair_controls_v1'
DENIED = (401, 403, 429, 451, 503)


def clock():
    return FrameClock(time.time_ns(), time.monotonic_ns())


def save(path, value):
    with Path(path).open('xb') as handle:
        handle.write(encoded(value))


def verify(lane=LANE):
    transport.verify(lane)
    spec = (lane / 'PREREG.md').read_text()
    for name in ('PREREG.md', 'PREREG.sha256', 'code_inputs.json', 'config.json', 'sources.json'):
        p = lane / name
        if name.endswith('.json') and hashlib.sha256(p.read_bytes()).hexdigest() not in spec:
            raise ValueError('unbound R359 manifest ' + name)
        if subprocess.check_output(['git', 'show', 'HEAD:' + str(p.relative_to(ROOT))], cwd=ROOT) != p.read_bytes():
            raise ValueError('R359 code/specification must be committed before collection')
    return json.loads((lane / 'config.json').read_text())


class MirroredSocket:
    def __init__(self, websocket, venue, status, frames, anchor):
        self.websocket, self.venue, self.status = websocket, venue, status
        self.frames, self.anchor = frames, anchor

    def __getattr__(self, name):
        return getattr(self.websocket, name)

    async def recv(self):
        started = time.monotonic_ns()
        raw = await self.websocket.recv()
        received = clock()
        text = raw.decode('utf-8') if isinstance(raw, bytes) else raw
        size = len(text.encode())
        if size > transport.FRAME_BYTES:
            raise ValueError('received frame exceeds inherited cap')
        if self.status['messages'] >= transport.MAX_MESSAGES or self.status['payload_bytes'] + size > transport.STREAM_BYTES:
            raise ValueError('mirrored frame exceeds inherited stream budget')
        self.frames.append({'venue': self.venue, 'number': self.status['messages'] + 1,
            'utc_ns': received.utc_ns, 'mono_ns': received.mono_ns, 'raw': text,
            'read_started_mono_ns': started})
        return raw


def mirror_connector(venue, status, frames, anchor, base=None):
    connect = base or transport.old.no_redirect_connector()

    def factory(*args, **kwargs):
        context = connect(*args, **kwargs)

        class Context:
            async def __aenter__(self):
                ws = await context.__aenter__()
                return MirroredSocket(ws, venue, status, frames, anchor)

            async def __aexit__(self, *exc):
                return await context.__aexit__(*exc)

        return Context()

    return factory


async def online(observer, frames, connections):
    async def wait_until(target):
        await asyncio.sleep(max(0, (target - time.monotonic_ns()) / NS))

    for stage in ('entry', 'exit'):
        await wait_until(observer.anchor.mono_ns + observer.config[stage + '_second'] * NS)
        issued = observer.plan(stage, clock(), list(frames), connections, completed_clock=clock)
        await wait_until(issued['execution_not_before_ns'])
        observer.tick(stage, clock(), list(frames), connections, completed_clock=clock)


def capture(lane=LANE):
    config = verify(lane)
    out = lane / 'evidence'
    out.mkdir(exist_ok=False)  # a failed capture cannot be reset or retried
    begin = time.monotonic()
    network = transport.Metadata(out)
    metadata, names, errors, connections, frames = {}, {}, [], {}, []
    observer, anchor, metadata_start = None, None, None
    transport.old.LT_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with transport.old.LT_LOCK.open('a') as lock:
        locked = False
        try:
            while time.monotonic() - begin < 10:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                    break
                except BlockingIOError:
                    time.sleep(.05)
            if not locked:
                raise transport.old.BudgetStop('existing public API writer held lock')
            metadata_start = clock()
            network.start = metadata_start.mono_ns / NS

            def get(name, url):
                result = network.get(name, url)
                status = network.records[-1].get('http_status')
                if status in DENIED:
                    raise transport.old.BudgetStop('source denial stops all new calls:' + str(status))
                return result

            listing = get('lighter_metadata', transport.old.LT_HTTP + '/orderBookDetails?filter=perp')
            if not listing or listing.get('code') != 200:
                raise transport.old.BudgetStop('mandatory market listing unavailable; no new call')
            for symbol in SYMBOLS:
                try:
                    m = get(symbol + '_mexc_metadata', transport.old.MX_HTTP + '/detail?symbol=' + symbol + '_USDT')
                    if not m or m.get('success') is not True:
                        raise ValueError('MEXC metadata unavailable')
                    mm = m['data']
                    if isinstance(mm, list):
                        mm, = [x for x in mm if x['symbol'] == symbol + '_USDT']
                    lm, = [x for x in listing['order_book_details'] if x['symbol'] == symbol and x['market_type'] == 'perp']
                    if mm['symbol'] != symbol + '_USDT':
                        raise ValueError('MEXC instrument mismatch')
                    metadata[symbol] = {'mexc': mm, 'lighter': lm}
                    names[int(lm['market_id'])] = symbol
                except transport.old.BudgetStop:
                    raise
                except (KeyError, ValueError, TypeError) as exc:
                    errors.append(symbol + ':' + type(exc).__name__ + ':' + str(exc))
            anchor = clock()
            save(out / 'anchor.json', asdict(anchor))
            observer = LivePairControl(out / 'online', metadata, names, anchor, config)
            mx = [{'method': kind, 'param': {'symbol': s + '_USDT', **({'limit': 5} if kind == 'sub.depth.full' else {})}}
                  for s in SYMBOLS if s in metadata for kind in ('sub.depth.full', 'sub.fair.price')]
            lt = [{'type': 'subscribe', 'channel': f'{kind}/{m}'} for m in sorted(names)
                  for kind in ('order_book', 'market_stats')]
            connections = {v: {} for v in ('mexc', 'lighter')}

            async def both():
                await asyncio.wait_for(asyncio.gather(
                    transport.stream('mexc', mx, out, anchor, connections['mexc'],
                        connector=mirror_connector('mexc', connections['mexc'], frames, anchor)),
                    transport.stream('lighter', lt, out, anchor, connections['lighter'],
                        connector=mirror_connector('lighter', connections['lighter'], frames, anchor)),
                    online(observer, frames, connections)),
                    timeout=min(75., max(.001, transport.TOTAL_SECONDS - (time.monotonic() - begin) - 3)))

            asyncio.run(both())
        except Exception as exc:
            errors.append(type(exc).__name__ + ':' + str(exc))
        finally:
            finished = clock()
            save(out / 'metadata.json', {'symbols': list(SYMBOLS), 'metadata': metadata, 'names': names})
            save(out / 'connections.json', connections)
            save(out / 'final_clock.json', asdict(finished))
            with (out / 'first_seen.jsonl.gz').open('xb') as handle:
                handle.write(gzip.compress(b''.join(encoded(f) for f in frames), mtime=0))
            save(out / 'receipts.json', {'records': network.records, 'requests': len(network.records),
                'response_bytes': network.total, 'response_body_read_upper_bound': network.read_upper_bound,
                'duration_seconds': time.monotonic() - begin, 'errors': errors,
                'metadata_window_started_clock': None if metadata_start is None else asdict(metadata_start),
                'scope_state': 'CLOSED', 'historical_allowance_used': False,
                'unused_metadata_slots_closed': 7 - len(network.records),
                'mirrored_first_seen_frames': len(frames), 'wire_bytes_measured': False})
            if locked:
                fcntl.flock(lock, fcntl.LOCK_UN)
    if observer is None:
        cells = [{'id': f'{s}_d{d}_k{k}', 'symbol': s, 'direction': d, 'cost_multiple': k,
                  'entry': {'state': 'not_started', 'reasons': errors}, 'exit': None,
                  'quantity': None, 'price_fee_only_native_snapshot': None,
                  'closed_price_fee_subtotal': None, 'funding_cash': None,
                  'full_net_pnl': None, 'actual_expected_net': None,
                  'prospective_strategy_days': 0}
                 for s in SYMBOLS for d in config['directions'] for k in config['cost_multiples']]
        result = {'registry_id': 'R359', 'diagnostic_variants': 12, 'cost_cells': 36,
                  'cells': cells, 'online_receipts': [], 'missed_stages': ['entry', 'exit'],
                  'capture_state': 'NOT_STARTED_OR_METADATA_BLOCKED', 'errors': errors,
                  'prospective_strategy_days': 0, 'actual_expected_net': None, 'funding_cash': None, 'full_net_pnl': None}
    else:
        result = observer.report(finished)
        result['capture_state'] = 'FINISHED_OR_PARTIAL'
        result['errors'] = errors
    save(lane / 'results.json', result)
    verify(lane)
    files = sorted(p for p in out.rglob('*') if p.is_file())
    save(lane / 'evidence_inputs.json', {'code_manifest_sha256': transport.sha(lane / 'code_inputs.json'),
        'sha256': {str(p.relative_to(lane)): transport.sha(p) for p in files},
        'result_sha256': transport.sha(lane / 'results.json')})
    return result


def reproduce(lane, out):
    config = verify(lane)
    identity = json.loads((lane / 'evidence_inputs.json').read_text())
    actual = {str(p.relative_to(lane)) for p in (lane / 'evidence').rglob('*') if p.is_file()}
    if actual != set(identity['sha256']):
        raise ValueError('sealed evidence inventory drift')
    for p, digest in identity['sha256'].items():
        if transport.sha(lane / p) != digest:
            raise ValueError('sealed evidence drift:' + p)
    if transport.sha(lane / 'results.json') != identity['result_sha256']:
        raise ValueError('sealed online result drift')
    out.mkdir(exist_ok=False)
    original = json.loads((lane / 'results.json').read_text())
    if original['capture_state'] == 'NOT_STARTED_OR_METADATA_BLOCKED':
        result = original
    else:
        meta = json.loads((lane / 'evidence/metadata.json').read_text())
        names = {int(k): v for k, v in meta['names'].items()}
        anchor = FrameClock(**json.loads((lane / 'evidence/anchor.json').read_text()))
        connections = json.loads((lane / 'evidence/connections.json').read_text())
        frames = list(map(json.loads, gzip.decompress((lane / 'evidence/first_seen.jsonl.gz').read_bytes()).splitlines()))
        replay = LivePairControl(out / 'online', meta['metadata'], names, anchor, config)
        for receipt in original['online_receipts']:
            stage, kind = receipt['stage'].split('_')
            now = FrameClock(**receipt['decision_clock'])
            issued = FrameClock(**receipt['issued_clock'])
            prefix = [f for f in frames if f['mono_ns'] <= now.mono_ns]
            method = replay.plan if kind == 'decision' else replay.tick
            method(stage, now, prefix, connections, completed_clock=lambda c=issued: c)
        finished = FrameClock(**json.loads((lane / 'evidence/final_clock.json').read_text()))
        result = replay.report(finished)
        result['capture_state'], result['errors'] = original['capture_state'], original['errors']
    save(out / 'results.json', result)
    save(out / 'replay_notice.json', {'offline_reproduction_only': True, 'new_prospective_tickets': 0,
                                    'source_evidence_manifest_sha256': transport.sha(lane / 'evidence_inputs.json')})
    if encoded(result) != (lane / 'results.json').read_bytes():
        raise ValueError('offline source-asof/account reconstruction differs from online result')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('capture', 'reproduce'))
    parser.add_argument('--out')
    args = parser.parse_args()
    if args.mode == 'capture':
        result = capture()
    else:
        if not args.out:
            parser.error('fresh --out required for reproduction')
        result = reproduce(LANE, Path(args.out))
    print(json.dumps({'registry_id': 'R359', 'capture_state': result['capture_state'],
                      'cells': len(result['cells']), 'issued_receipts': len(result['online_receipts']),
                      'actual_expected_net': None, 'prospective_strategy_days': 0}))


if __name__ == '__main__':
    main()
