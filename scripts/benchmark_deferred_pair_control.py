"""R361 finite changed-code experiment, reusing frozen R360 comparison helpers."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab.deferred_pair_control import DeferredDepthReplay, DeferredPairControl

LANE = ROOT / 'experiments/deferred_pair_control_v1'


def helpers():
    source = Path(__file__).with_name('benchmark_incremental_pair_control.py')
    spec = importlib.util.spec_from_file_location('_r361_private_comparison', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.LANE = LANE
    module.IncrementalDepthReplay = DeferredDepthReplay
    module.IncrementalPairControl = DeferredPairControl
    return module


def run(out):
    h = helpers()
    config = h.verify()
    h.save(LANE / 'run_started.json', {'registry_id': 'R361', 'offline_only': True,
        'started_UTC': datetime.now(timezone.utc).isoformat(), 'new_source_requests': 0,
        'config_sha256': h.sha(LANE / 'config.json'), 'prereg_sha256': h.sha(LANE / 'PREREG.md')})
    out.mkdir(exist_ok=False)
    started = time.monotonic()
    source = h.load()
    if len(source['frames']) != config['source_frames']:
        raise ValueError('fixed source population changed')
    runs = []
    for repeat in range(config['paired_repetitions']):
        order = ('baseline', 'incremental') if repeat % 2 == 0 else ('incremental', 'baseline')
        for profile in order:
            h.guard(started, config)
            directory = out / f'{repeat+1:02d}_{profile}'
            directory.mkdir()
            result = {'repetition': repeat+1, **h.one(profile, directory, source)}
            # Persist the actual measurement immediately. A later failure can
            # never discard it or authorize replaying the same reservation.
            h.save(directory / 'measurement.json', result)
            runs.append(result)
            print(json.dumps({'repetition': repeat+1, 'profile': profile,
                              'exact_original_equivalence': True}), flush=True)
    depth = h.depth_equivalence(source, config['prefix_checkpoints'], started, config)
    h.save(out / 'depth_equivalence.json', depth)
    profiles = {}
    for profile in ('baseline', 'incremental'):
        subset = [r for r in runs if r['profile'] == profile]
        profiles[profile] = {
            'implementation': 'R359 fresh prefix' if profile == 'baseline' else 'R361 deferred/cached export',
            'stages': {stage: h.summary_ns([s['processing_and_io_ns'] for r in subset
                         for s in r['stages'] if s['stage'] == stage])
                       for stage in ('entry_decision', 'entry_execution', 'exit_decision', 'exit_execution')},
            'receive_service_totals_ns': [r['preprocessing']['total_ns'] for r in subset],
            'receive_service_p99_ns': [r['preprocessing']['p99_ns'] for r in subset],
            'receive_service_max_ns': [r['preprocessing']['max_ns'] for r in subset],
            'whole_wall_ns': [r['whole_wall_ns'] for r in subset],
            'whole_cpu_ns': [r['whole_cpu_ns'] for r in subset]}
    result = {'registry_id': 'R361', 'offline_only': True, 'new_prospective_tickets': 0,
        'new_alpha_variants': 0, 'engineering_profiles': ['baseline', 'incremental'],
        'candidate': 'DeferredPairControl; single preselected deferred+same-asof-cache implementation',
        'parent_R360_failure_retained': True, 'source_frames': len(source['frames']),
        'source_input_identity_sha256': h.sha(LANE / 'input_identity.json'),
        'config_sha256': h.sha(LANE / 'config.json'), 'code_inputs_sha256': h.sha(LANE / 'code_inputs.json'),
        'original_timeliness_preserved': True, 'all_original_native_journals_and_results_exact': True,
        'runs': runs, 'profiles': profiles, 'depth_equivalence': depth,
        'total_experiment_wall_ns': int((time.monotonic()-started)*1e9),
        'runtime': {'python': platform.python_version(), 'platform': platform.platform(),
                    'machine': platform.machine(), 'logical_cpus': __import__('os').cpu_count(),
                    'timer': vars(time.get_clock_info('perf_counter'))},
        'limitations': ['offline service on cached old inputs is not new source/order latency',
            'receive preprocessing and native journal IO retained; file read/decompression separate',
            'shared RSS high water is not isolated profile memory attribution',
            'old-arrival serial service diagnostic does not certify live schedulability',
            'depth oracle uses the same frozen venue parser on both sides',
            'unknown funding/actual fees/sessions/margin/FX prevent actual expected net qualification'],
        'actual_expected_net': None, 'full_net_pnl': None, 'prospective_strategy_days': 0}
    h.save(out / 'benchmark.json', result)
    h.verify()
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.out)
    except Exception as exc:
        if args.out.is_dir() and not (args.out / 'failure.json').exists():
            helpers().save(args.out / 'failure.json', {'exception': type(exc).__name__, 'reason': str(exc),
                'scope_closed': True, 'new_source_requests': 0})
        raise
    print(json.dumps({'registry_id': 'R361', 'runs': len(result['runs']),
        'exact_equivalence': True, 'state_comparisons': result['depth_equivalence']['comparisons'], 'new_tickets': 0}))
