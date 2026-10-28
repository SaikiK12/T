"""Frozen R360 finite offline equivalence/service-time experiment; no network."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
import platform
from pathlib import Path
import resource
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab.depth_replay import DepthReplay
from lab.incremental_pair_control import IncrementalDepthReplay, IncrementalPairControl
from lab.live_pair_control import LivePairControl, book_mapping, encoded
from lab.prereg import verify as verify_prereg
from lab.stream_quotes import FrameClock, SYMBOLS

LANE = ROOT / 'experiments/incremental_pair_control_v1'
SOURCE = ROOT / 'experiments/live_pair_controls_v1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('xb') as f:
        f.write(encoded(value))


def guard(started, config):
    if time.monotonic() - started > config['max_wall_seconds']:
        raise RuntimeError('finite benchmark wall budget exhausted; retain partial outputs')
    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss > config['max_process_rss_KiB']:
        raise RuntimeError('finite benchmark memory budget exhausted; retain partial outputs')


def verify(lane=LANE):
    verify_prereg(lane / 'PREREG.md')
    spec = (lane / 'PREREG.md').read_text()
    bound = [lane / name for name in ('PREREG.md', 'PREREG.sha256', 'config.json',
                                     'code_inputs.json', 'input_identity.json')]
    for name in ('config.json', 'code_inputs.json', 'input_identity.json'):
        if sha(lane / name) not in spec:
            raise ValueError('unbound finite R360 input: ' + name)
        manifest = json.loads((lane / name).read_text())
        for path, digest in manifest.get('sha256', {}).items():
            if sha(ROOT / path) != digest:
                raise ValueError('frozen dependency drift: ' + path)
            bound.append(ROOT / path)
    paths = sorted({str(p.relative_to(ROOT)) for p in bound})
    tracked = set(subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', 'HEAD'], cwd=ROOT,
                                        text=True).splitlines())
    if not set(paths) <= tracked:
        raise ValueError('specification, code and input identity must be committed before measurement')
    subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--', *paths], cwd=ROOT, check=True)
    return json.loads((lane / 'config.json').read_text())


def digest_files(directory):
    return {p.name: sha(p) for p in sorted(directory.iterdir()) if p.is_file()}


def summary_ns(values):
    xs = sorted(values)
    def quantile(p):
        return xs[max(0, math.ceil(p * len(xs)) - 1)] if xs else None
    return {'n': len(xs), 'total_ns': sum(xs), 'min_ns': xs[0] if xs else None,
            'median_ns': quantile(.5), 'p95_ns': quantile(.95), 'p99_ns': quantile(.99),
            'max_ns': xs[-1] if xs else None}


def load():
    meta = json.loads((SOURCE / 'evidence/metadata.json').read_text())
    return {'metadata': meta['metadata'], 'names': {int(k): v for k, v in meta['names'].items()},
            'anchor': FrameClock(**json.loads((SOURCE / 'evidence/anchor.json').read_text())),
            'connections': json.loads((SOURCE / 'evidence/connections.json').read_text()),
            'frames': [json.loads(line) for line in gzip.decompress(
                (SOURCE / 'evidence/first_seen.jsonl.gz').read_bytes()).splitlines()],
            'original': json.loads((SOURCE / 'results.json').read_text()),
            'config': json.loads((SOURCE / 'config.json').read_text()),
            'finished': FrameClock(**json.loads((SOURCE / 'evidence/final_clock.json').read_text()))}


def one(profile, out, source):
    adaptive = profile == 'incremental'
    begin_wall, begin_cpu = time.perf_counter_ns(), time.process_time_ns()
    args = (out / 'online', source['metadata'], source['names'], source['anchor'], source['config'])
    t = time.perf_counter_ns()
    c = IncrementalPairControl(*args, source['connections']) if adaptive else LivePairControl(*args)
    init_ns = time.perf_counter_ns() - t
    frames, prefix, index, preprocessing, stages = source['frames'], [], 0, [], []
    # Resource-service illustration on OLD arrivals, never a new first-seen
    # observation or simulated replacement clock for the original account.
    busy_until, max_queue_lag_ns = source['anchor'].mono_ns, 0
    for receipt in source['original']['online_receipts']:
        stage, kind = receipt['stage'].split('_')
        now, issued = FrameClock(**receipt['decision_clock']), FrameClock(**receipt['issued_clock'])
        while index < len(frames) and frames[index]['mono_ns'] <= now.mono_ns:
            f = frames[index]; t = time.perf_counter_ns()
            if adaptive: c.receive(f)
            else: prefix.append(f)
            service = time.perf_counter_ns() - t
            preprocessing.append(service)
            lag = max(0, busy_until - f['mono_ns'])
            max_queue_lag_ns = max(max_queue_lag_ns, lag)
            busy_until = max(busy_until, f['mono_ns']) + service
            index += 1
        t = time.perf_counter_ns()
        method = c.plan if kind == 'decision' else c.tick
        args = (stage, now, source['connections']) if adaptive else (stage, now, prefix, source['connections'])
        result = method(*args, completed_clock=lambda c=issued: c)
        duration = time.perf_counter_ns() - t
        if result != receipt:
            raise AssertionError('original receipt semantics changed: ' + receipt['stage'])
        service_start = max(now.mono_ns, busy_until)
        busy_until = service_start + duration
        stages.append({'stage': receipt['stage'], 'processing_and_io_ns': duration,
            'source_frames': index, 'cumulative_preprocessing_ns': sum(preprocessing),
            'old_arrival_service_queue_ns': service_start - now.mono_ns,
            'old_arrival_service_finish_minus_original_start_ns': busy_until - now.mono_ns,
            'original_on_time': receipt['on_time'], 'original_issued_clock': asdict(issued),
            'offline_measured_duration_within_250ms': duration <= source['config']['deadline_lateness_ns'],
            'timeliness_reclassified': False})
    # Include the whole finite source trace, including the otherwise unused tail.
    while index < len(frames):
        f = frames[index]; t = time.perf_counter_ns()
        if adaptive: c.receive(f)
        else: prefix.append(f)
        service = time.perf_counter_ns() - t
        preprocessing.append(service)
        lag = max(0, busy_until - f['mono_ns'])
        max_queue_lag_ns = max(max_queue_lag_ns, lag)
        busy_until = max(busy_until, f['mono_ns']) + service
        index += 1
    t = time.perf_counter_ns()
    result = c.report(source['finished'])
    result['capture_state'], result['errors'] = source['original']['capture_state'], source['original']['errors']
    report_ns = time.perf_counter_ns() - t
    if encoded(result) != (SOURCE / 'results.json').read_bytes():
        raise AssertionError('financial/receipt report differs from sealed original')
    expected, actual = digest_files(SOURCE / 'evidence/online'), digest_files(out / 'online')
    if expected != actual:
        raise AssertionError('native journals or receipt bytes differ from sealed originals')
    save(out / 'core_result.json', result)
    return {'profile': profile, 'init_ns': init_ns, 'stages': stages,
            'preprocessing': summary_ns(preprocessing), 'report_ns': report_ns,
            'whole_wall_ns': time.perf_counter_ns() - begin_wall,
            'whole_cpu_ns': time.process_time_ns() - begin_cpu,
            'peak_process_rss_KiB_shared_high_water': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'old_arrival_service_max_queue_lag_ns': max_queue_lag_ns,
            'source_frame_count': index, 'core_result_sha256': sha(out / 'core_result.json'),
            'journal_and_receipt_sha256': actual, 'exact_original_equivalence': True}


def depth_equivalence(source, checkpoints, started, config):
    frames = source['frames']
    points = sorted({max(1, math.ceil(i * len(frames) / checkpoints)) for i in range(1, checkpoints+1)})
    if len(points) != checkpoints:
        raise ValueError('fixed number of distinct prefix checkpoints required')
    r = IncrementalDepthReplay(source['metadata'], source['names'], source['anchor'], source['connections'])
    index, checks, rows = 0, 0, []
    for count in points:
        guard(started, config)
        target = frames[count-1]['mono_ns']
        # Include tied receipts exactly as the frozen monotonic-time contract.
        while index < len(frames) and frames[index]['mono_ns'] <= target:
            r.receive(frames[index]); index += 1
        base = DepthReplay(frames[:index], source['metadata'], source['names'], source['anchor'], source['connections'])
        projections = []
        for profile in ('full', 'top_only'):
            for symbol in SYMBOLS:
                a, ba = base.observe(symbol, target, profile=profile)
                b, bb = r.observe(symbol, target, profile=profile)
                checks += 1
                if a != b or ba != bb:
                    raise AssertionError(('source-state differs', index, symbol, profile))
                projections.append({'row': a, 'books': [book_mapping(book) for book in ba]})
        checks += 2
        if base.errors != r.errors or base.assembly_events != r.assembly_events:
            raise AssertionError('decoder/nonce accounting differs at prefix')
        rows.append({'prefix_frames': index, 'target_mono_ns': target,
                     'projection_sha256': hashlib.sha256(encoded(projections)).hexdigest(),
                     'same_rows_books_errors_assembly': True})
    return {'checkpoints': checkpoints, 'comparisons': checks, 'prefixes': rows,
            'state_oracle': 'unchanged frozen decoder/assembler, not an independent venue parser'}


def run(out):
    config = verify()
    save(LANE / 'run_started.json', {'registry_id': 'R360', 'offline_only': True,
         'started_UTC': datetime.now(timezone.utc).isoformat(), 'new_source_requests': 0,
         'config_sha256': sha(LANE / 'config.json'), 'prereg_sha256': sha(LANE / 'PREREG.md')})
    out.mkdir(exist_ok=False)
    started = time.monotonic()
    source = load()
    if len(source['frames']) != config['source_frames']:
        raise ValueError('fixed input population changed')
    runs = []
    for repeat in range(config['paired_repetitions']):
        # A fixed alternating order; no fastest run/profile selection.
        order = ('baseline', 'incremental') if repeat % 2 == 0 else ('incremental', 'baseline')
        for profile in order:
            guard(started, config)
            directory = out / f'{repeat+1:02d}_{profile}'
            directory.mkdir()
            runs.append({'repetition': repeat+1, **one(profile, directory, source)})
            print(json.dumps({'repetition': repeat+1, 'profile': profile, 'exact_original_equivalence': True}), flush=True)
    depths = depth_equivalence(source, config['prefix_checkpoints'], started, config)
    profiles = {}
    for profile in ('baseline', 'incremental'):
        subset = [r for r in runs if r['profile'] == profile]
        profiles[profile] = {'stages': {stage: summary_ns([s['processing_and_io_ns']
            for r in subset for s in r['stages'] if s['stage'] == stage])
            for stage in ('entry_decision', 'entry_execution', 'exit_decision', 'exit_execution')},
            'receive_services': {'run_totals_ns': [r['preprocessing']['total_ns'] for r in subset],
                                 'run_p99_ns': [r['preprocessing']['p99_ns'] for r in subset],
                                 'run_max_ns': [r['preprocessing']['max_ns'] for r in subset]},
            'run_total_cpu_ns': [r['whole_cpu_ns'] for r in subset]}
    result = {'registry_id': 'R360', 'offline_only': True, 'new_prospective_tickets': 0,
        'new_alpha_variants': 0, 'engineering_profiles': ['baseline', 'incremental'],
        'source_input_identity_sha256': sha(LANE / 'input_identity.json'),
        'config_sha256': sha(LANE / 'config.json'), 'code_inputs_sha256': sha(LANE / 'code_inputs.json'),
        'original_timeliness_preserved': True, 'source_frames': len(source['frames']),
        'all_original_native_journals_and_results_exact': True, 'runs': runs,
        'profiles': profiles, 'depth_equivalence': depths,
        'runtime': {'python': platform.python_version(), 'platform': platform.platform(),
                    'machine': platform.machine(), 'logical_cpus': __import__('os').cpu_count(),
                    'timer': time.get_clock_info('perf_counter')._asdict() if hasattr(time.get_clock_info('perf_counter'), '_asdict')
                              else vars(time.get_clock_info('perf_counter'))},
        'limitations': ['offline service times on cached old inputs; no new receive or order latency',
            'all receive preprocessing, original journal IO and account work retained',
            'source file read/decompression and initialization are separate from stage durations',
            'single shared process RSS high water is not isolated profile memory attribution',
            'old-arrival serial service illustration cannot certify live schedulability',
            'same frozen parser is used on both sides of depth equivalence',
            'full funding, fee entitlement, session, margin, FX qualification and expected net stay unknown'],
        'actual_expected_net': None, 'full_net_pnl': None, 'prospective_strategy_days': 0}
    save(out / 'benchmark.json', result)
    verify()
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.out)
    except Exception as exc:
        if args.out.is_dir() and not (args.out / 'failure.json').exists():
            save(args.out / 'failure.json', {'exception': type(exc).__name__, 'reason': str(exc),
                                            'scope_closed': True, 'new_source_requests': 0})
        raise
    print(json.dumps({'registry_id': 'R360', 'runs': len(result['runs']),
                      'exact_equivalence': result['all_original_native_journals_and_results_exact'],
                      'state_comparisons': result['depth_equivalence']['comparisons'], 'new_tickets': 0}))
