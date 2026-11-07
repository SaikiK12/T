#!/usr/bin/env python3
"""Finite mixture of distinct price-rule targets; imports read no market data."""
from __future__ import annotations

import argparse
import csv
from datetime import date
import gzip
import io
import itertools
import json
from pathlib import Path
import platform
import re
import sys

import numba
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lab import prereg
from scripts import run_slow_trend as trend
from scripts import run_weekly_rotation as weekly
from scripts import fetch_trend_daily as fetcher

LANE = ROOT / 'experiments/mixed_signals_v1'
ROUND_ID = 257
SEED = 20261020000 + ROUND_ID
TREND_VARIANT = 'trend_plain'
REGIMES = ('btc_ret28', 'btc_ret56', 'btc_sma200')
PROPORTIONS = (.25, .5, .75)
BEARS = ('cash', 'trend', 'half_trend_reversal', 'reversal')
GRID = tuple(itertools.product(REGIMES, PROPORTIONS, BEARS))
CONTROLS = ('trend', 'momentum28', 'reversal7', 'passive')
COSTS = (1, 2, 3)
BASE_COST = .0012
DEPENDENCIES = {
    'lab/stats.py': 'bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34',
    'lab/prereg.py': '3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508',
    'scripts/run_slow_trend.py': '3f5b658dbb9bc6991e2c59507f457e6ff5c5720ef1228d1f2cc23cb83cbf724b',
    'scripts/run_weekly_rotation.py': '9084d30faa615d8e02a0b482f60d774537adc868c90cd13f95f23486cda7e8c3',
    'scripts/fetch_trend_daily.py': '3377186f143bcc322d5e3b4bf67adca62edf8087700deef76cdcdfe0f0853f82',
    'experiments/slow_trend_v1/PREREG.md': 'ad247ec8676b8ae817fea41a6a6a82303cedf298e49cdaaea35bfd55625f169b',
    'experiments/slow_trend_v1/results/data_manifest.json': 'fc90fe4886608cbc090231374bcaf593082d54959bdc25de2ed1566d86fd42cd',
}
Error = trend.ContractError


def identity(config):
    regime, p, bear = config
    return f'{regime}_p{round(100*p):02d}_{bear}'


def regime_state(close, regime):
    """Known-at-close bull mask plus explicit warm-up availability mask."""
    close = np.asarray(close, float)
    if (close.ndim != 2 or close.shape[1] != 6 or not np.isfinite(close).all()
            or np.any(close <= 0) or regime not in REGIMES):
        raise Error('Invalid six-coin prices or regime')
    btc = close[:, 0]
    bull, known = np.zeros(len(close), bool), np.zeros(len(close), bool)
    if regime in ('btc_ret28', 'btc_ret56'):
        horizon = 28 if regime == 'btc_ret28' else 56
        known[horizon:] = True
        bull[horizon:] = btc[horizon:] > btc[:-horizon]
    else:
        for t in range(199, len(close)):
            known[t] = True
            bull[t] = btc[t] > btc[t-199:t+1].mean()
    return bull, known


def component_targets(close):
    """Fixed borrowed components, not additional selected variants."""
    return {
        'trend': trend.trend_targets(close)[TREND_VARIANT],
        'momentum28': weekly.rank_targets(close, 28, 1, 3, False),
        'reversal7': weekly.rank_targets(close, 7, -1, 3, False),
        'passive': np.full_like(np.asarray(close, float), 1/6),
    }


def mix_target(components, bull, known, proportion, bear):
    if proportion not in PROPORTIONS or bear not in BEARS:
        raise Error('Mixed rule is outside the frozen family')
    t, m, r = (np.asarray(components[name], float) for name in ('trend', 'momentum28', 'reversal7'))
    bull, known = np.asarray(bull), np.asarray(known)
    if (t.ndim != 2 or t.shape[1] != 6 or m.shape != t.shape or r.shape != t.shape
            or bull.shape != (len(t),) or known.shape != bull.shape
            or bull.dtype.kind != 'b' or known.dtype.kind != 'b'):
        raise Error('Invalid component/regime shapes')
    bearish = {'cash': np.zeros_like(t), 'trend': t,
               'half_trend_reversal': .5*t+.5*r, 'reversal': r}[bear]
    target = np.where(bull[:, None], proportion*t+(1-proportion)*m, bearish)
    target = np.where(known[:, None], target, 0.)
    if (not np.isfinite(target).all() or np.any(target < 0)
            or np.any(target.sum(axis=1) > 1+1e-12)):
        raise Error('Invalid long-only, unlevered mixed target')
    return target


def target_family(close):
    components = component_targets(close)
    states = {regime: regime_state(close, regime) for regime in REGIMES}
    targets = [mix_target(components, *states[regime], proportion, bear)
               for regime, proportion, bear in GRID]
    return components, targets


def calendar(dates):
    daily = np.ones(len(dates), bool)
    schedules = {name: daily for name in CONTROLS}
    schedules['passive'] = np.array([day[8:10] == '01' for day in dates])
    bounds = {name: (dates.index(start), len(dates) if end == '2026-10-01' else dates.index(end))
              for name, (start, end) in trend.SPLITS.items()}
    return daily, schedules, bounds


def account(close, target, schedule, start, end, multiple, scale=1.):
    if multiple not in COSTS:
        raise Error('Cost multiple is outside 1x/2x/3x')
    rows = weekly.account(close, target, schedule, start, end, BASE_COST*multiple,
                          alpha=1., scale=scale)
    if not np.isfinite(rows).all():
        raise Error('Nonfinite self-financing account result')
    return rows


def calibrate(close, targets, controls, daily, schedules, discovery):
    """All scores and capital scales are functions of discovery outcomes only."""
    if len(targets) != len(GRID) or tuple(controls) != CONTROLS:
        raise Error('Candidate or control definitions differ from the finite protocol')
    start, end = discovery
    candidate_scores, candidate_nets, control_scores, control_nets = [], [], [], []
    for config, target in zip(GRID, targets):
        one = account(close, target, daily, start, end, 1)
        two = account(close, target, daily, start, end, 2)
        candidate_nets.append(one[:, 0])
        candidate_scores.append({'candidate': identity(config), **weekly.summary(two)})
    for name in CONTROLS:
        one = account(close, controls[name], schedules[name], start, end, 1)
        two = account(close, controls[name], schedules[name], start, end, 2)
        control_nets.append(one[:, 0])
        control_scores.append({'control': name, **weekly.summary(two)})
    selected = weekly.select_candidate(candidate_scores)
    control_index = weekly.select_candidate(control_scores)
    scales = [weekly.risk_scales(net, control_nets[control_index]) for net in candidate_nets]
    return {'selected_index': selected, 'control_index': control_index,
            'selected_candidate': identity(GRID[selected]), 'selected_control': CONTROLS[control_index],
            'scales': scales, 'candidate_scores': candidate_scores, 'control_scores': control_scores}


def verify_registration():
    digest = prereg.verify(LANE/'PREREG.md')
    text = (LANE/'PREREG.md').read_text()
    runner = trend.sha(Path(__file__).read_bytes())
    declared = re.findall(r'Runner SHA-256: `([0-9a-f]{64})`', text)
    if declared != [runner]:
        raise Error('Mixed-signals runner differs from its frozen declaration')
    ids = re.findall(r'Registry id:\*\*\s+(R[0-9]+)', text)
    if ids != [f'R{ROUND_ID}']:
        raise Error('Round ID/seed must match the frozen Registry id')
    for relative, expected in DEPENDENCIES.items():
        if trend.sha((ROOT/relative).read_bytes()) != expected:
            raise Error(f'Mixed-signals dependency changed: {relative}')
    source_spec, source_runner = weekly.verify_registration()
    return {'prereg_sha256': digest, 'runner_sha256': runner, 'dependencies': DEPENDENCIES,
            'R230_prereg_sha256': source_spec, 'R230_runner_sha256': source_runner}


def write_csv(path, records):
    if not records:
        raise Error('Refusing an empty result table')
    with Path(path).open('x', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(records)


def write_gzip_csv(path, records):
    if not records:
        raise Error('Refusing an empty daily path table')
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(records[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(records)
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, filename='', mode='wb', mtime=0) as compressed:
        compressed.write(stream.getvalue().encode())
    with Path(path).open('xb') as handle:
        handle.write(buffer.getvalue())


def run(raw, output):
    output = Path(output)
    weekly.fresh_output(output)
    provenance = verify_registration()  # No market values or output writes before these guards.
    output.mkdir(parents=True)
    try:
        dates, close, input_metadata = trend.load_prices(trend.LANE/'results/data_manifest.json', Path(raw))
        controls, targets = target_family(close)
        daily, schedules, bounds = calendar(dates)
        choice = calibrate(close, targets, controls, daily, schedules, bounds['discovery'])
        selected, control = choice['selected_index'], choice['selected_control']
        write_csv(output/'candidate_discovery_2x.csv', choice['candidate_scores'])
        write_csv(output/'control_discovery_2x.csv', choice['control_scores'])
        metrics, control_metrics, selected_daily = [], [], []
        bootstrap, differences = {}, None
        fields = ['net', 'gross', 'cost_fraction', 'cost_dollars', 'turnover', 'exposure', 'nav', 'cash_end']
        fields += ['held_units_'+symbol for symbol in fetcher.SYMBOLS]
        for split, (start, end) in bounds.items():
            for multiple in COSTS:
                for name in CONTROLS:
                    rows = account(close, controls[name], schedules[name], start, end, multiple)
                    control_metrics.append({'split': split, 'cost_multiple': multiple,
                                            'control': name, **weekly.summary(rows)})
                validation = np.empty((end-start, len(GRID))) if split == 'validation' and multiple == 1 else None
                for index, target in enumerate(targets):
                    candidate_scale, control_scale = choice['scales'][index]
                    left = account(close, target, daily, start, end, multiple, candidate_scale)
                    right = account(close, controls[control], schedules[control], start, end,
                                    multiple, control_scale)
                    for role, rows, scale in (('candidate', left, candidate_scale),
                                              ('matched_control', right, control_scale)):
                        metrics.append({'split': split, 'cost_multiple': multiple,
                            'candidate': identity(GRID[index]), 'role': role, 'selected_control': control,
                            'capital_scale': scale, **weekly.summary(rows)})
                        if index == selected:
                            selected_daily.extend({'split': split, 'cost_multiple': multiple,
                                'role': role, 'date': day, **dict(zip(fields, row.tolist()))}
                                for day, row in zip(dates[start:end], rows))
                    if validation is not None:
                        validation[:, index] = left[:, 0]-right[:, 0]
                if validation is not None:
                    differences = validation
        for block in (30, 10, 60):
            bootstrap[str(block)] = weekly.bootstrap_family(differences, selected, block,
                                        replicates=5000, seed=SEED)[0]
        selected_name = choice['selected_candidate']
        lookup = {(row['split'], row['cost_multiple'], row['role']): row
                  for row in metrics if row['candidate'] == selected_name}
        checks = weekly.decision_checks(lookup['validation', 1, 'candidate'],
                    lookup['validation', 1, 'matched_control'],
                    lookup['validation', 2, 'candidate']['mean_bp_day'], bootstrap['30'])
        verdict = {'verdict': 'PARTIAL' if all(checks.values()) else 'NULL', 'checks': checks,
                   'selected_candidate': selected_name, 'selected_control': control, 'trials': len(GRID),
                   'evidence': 'Exploratory mixed-target screen on six surviving spot coins and spent dates'}
        write_csv(output/'grid_metrics.csv', metrics)
        write_csv(output/'standalone_controls.csv', control_metrics)
        write_gzip_csv(output/'selected_daily.csv.gz', selected_daily)
        trend.write_json(output/'selection.json', choice)
        trend.write_json(output/'bootstrap.json', bootstrap)
        verdict_payload = json.dumps(trend.clean_json(verdict), indent=2,
                                     sort_keys=True, allow_nan=False)+'\n'
        manifest = {**provenance, 'input_provenance': input_metadata,
            'round_id': f'R{ROUND_ID}', 'trials': len(GRID), 'seed': SEED,
            'trend_variant': TREND_VARIANT, 'grid': [list(config) for config in GRID],
            'control_order': CONTROLS, 'splits': trend.SPLITS,
            'cost_one_way': [BASE_COST*multiple for multiple in COSTS],
            'python': platform.python_version(), 'numpy': np.__version__, 'numba': numba.__version__,
            'output_sha256': {path.name: trend.sha(path.read_bytes()) for path in sorted(output.iterdir())}}
        manifest['output_sha256']['verdict.json'] = trend.sha(verdict_payload.encode())
        trend.write_json(output/'manifest.json', manifest)
        with (output/'verdict.json').open('x') as handle:
            handle.write(verdict_payload)
        return verdict
    except (ValueError, OSError) as exc:
        result = {'verdict': 'INCONCLUSIVE', 'reason': str(exc), 'round_id': f'R{ROUND_ID}'}
        failure = output/('inconclusive.json' if (output/'verdict.json').exists() else 'verdict.json')
        trend.write_json(failure, result)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-dir', type=Path, default=fetcher.DEFAULT_RAW)
    parser.add_argument('--out', type=Path, default=LANE/'results')
    args = parser.parse_args()
    try:
        result = run(args.raw_dir, args.out)
    except (ValueError, OSError) as exc:
        result = {'verdict': 'INCONCLUSIVE', 'reason': str(exc)}
    print(json.dumps(trend.clean_json(result), sort_keys=True))
    return 2 if result['verdict'] == 'INCONCLUSIVE' else 0


if __name__ == '__main__':
    raise SystemExit(main())
