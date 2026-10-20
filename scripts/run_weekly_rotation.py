#!/usr/bin/env python3
"""R230: finite, registered weekly spot rotation search; no network access."""
from __future__ import annotations

import argparse
import csv
from datetime import date
import hashlib
import itertools
import json
from pathlib import Path
import platform
import re
import sys

import numba
from numba import njit
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lab import prereg, stats
from scripts import run_slow_trend as reference
from scripts import fetch_trend_daily as fetcher

LANE = ROOT / 'experiments/weekly_rotation_v1'
GRID = tuple(itertools.product((7, 14, 28, 56), (1, -1), (1, 2, 3), (False, True), (1.0, 0.5)))
SEED = 20261020230
DEPENDENCIES = {
    'lab/stats.py': 'bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34',
    'lab/prereg.py': '3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508',
    'scripts/run_slow_trend.py': '3f5b658dbb9bc6991e2c59507f457e6ff5c5720ef1228d1f2cc23cb83cbf724b',
    'scripts/fetch_trend_daily.py': '3377186f143bcc322d5e3b4bf67adca62edf8087700deef76cdcdfe0f0853f82',
    'experiments/slow_trend_v1/PREREG.md': 'ad247ec8676b8ae817fea41a6a6a82303cedf298e49cdaaea35bfd55625f169b',
    'experiments/slow_trend_v1/results/data_manifest.json': 'fc90fe4886608cbc090231374bcaf593082d54959bdc25de2ed1566d86fd42cd',
}


def identity(config):
    h, sign, k, gate, alpha = config
    return f'h{h:02d}_{"mom" if sign == 1 else "rev"}_k{k}_gate{int(gate)}_a{alpha:g}'


def verify_registration():
    digest = prereg.verify(LANE / 'PREREG.md')
    runner = reference.sha(Path(__file__).read_bytes())
    declared = re.findall(r'Runner SHA-256: `?([0-9a-f]{64})`?', (LANE / 'PREREG.md').read_text())
    if declared != [runner]:
        raise reference.ContractError('R230 runner differs from frozen declaration')
    for path, expected in DEPENDENCIES.items():
        if reference.sha((ROOT / path).read_bytes()) != expected:
            raise reference.ContractError(f'R230 dependency changed: {path}')
    return digest, runner


def rank_targets(close, horizon, sign, k, gate):
    """Targets use only closes through t; ties retain the fixed source-symbol order."""
    close = np.asarray(close, dtype=float)
    if (close.ndim != 2 or close.shape[1] != 6 or not np.isfinite(close).all()
            or np.any(close <= 0) or horizon not in (7, 14, 28, 56)
            or sign not in (1, -1) or k not in (1, 2, 3)):
        raise reference.ContractError('invalid rank input')
    target = np.zeros_like(close)
    for t in range(max(horizon, 56 if gate else horizon), len(close)):
        if gate and close[t, 0] <= close[t-56, 0]:
            continue
        score = sign * (close[t] / close[t-horizon] - 1)
        indices = np.argsort(-score, kind='stable')[:k]
        target[t, indices] = 1.0/k
    return target


@njit(cache=True)
def _account(close, targets, rebalance_days, start, end, cost, alpha, scale):
    """Kernel columns: net, gross, fee fraction/dollars, turnover, exposure, NAV, cash, units[6]."""
    out = np.zeros((end-start, 14))
    units = np.zeros(6)
    cash, previous = 1.0, 1.0
    for i in range(start, end):
        dollars = units * close[i-1]
        before = cash + dollars.sum()
        fee, traded = 0.0, 0.0
        if i == start or rebalance_days[i]:
            weights = (1-alpha)*dollars/before + alpha*scale*targets[i-2]
            lo, hi = 0.0, before
            for iteration in range(55):
                after = (lo+hi)/2
                required = after + cost*np.abs(weights*after-dollars).sum()
                if required > before:
                    hi = after
                else:
                    lo = after
            after = (lo+hi)/2
            traded = np.abs(weights*after-dollars).sum()
            fee = cost*traded
            units = weights*after/close[i-1]
            cash = max(0.0, after-(units*close[i-1]).sum())
        held = units.copy()
        post = cash + (units*close[i-1]).sum()
        exposure = (units*close[i-1]).sum()/post
        gross = (units*(close[i]-close[i-1])).sum()
        nav = cash + (units*close[i]).sum()
        if i == end-1:
            exit_notional = (units*close[i]).sum()
            fee += cost*exit_notional
            traded += exit_notional
            cash = nav-cost*exit_notional
            units[:] = 0
            nav = cash
        if nav <= 0 or cash < -1e-12 or abs(nav-previous-gross+fee) > 1e-10*previous:
            raise ValueError('self-financing account invariant failed')
        row = i-start
        out[row, 0] = nav/previous-1
        out[row, 1] = gross/previous
        out[row, 2] = fee/previous
        out[row, 3] = fee
        out[row, 4] = traded/before
        out[row, 5] = exposure
        out[row, 6] = nav
        out[row, 7] = cash
        out[row, 8:] = held
        previous = nav
    return out


def account(close, targets, days, start, end, cost, alpha=1.0, scale=1.0):
    close, targets, days = np.asarray(close, float), np.asarray(targets, float), np.asarray(days, bool)
    if (close.ndim != 2 or close.shape[1] != 6 or targets.shape != close.shape or days.shape != (len(close),)
            or not np.isfinite(close).all() or np.any(close <= 0)
            or not np.isfinite(targets).all() or np.any(targets < 0)
            or np.any(targets.sum(axis=1) > 1+1e-12)
            or not 2 <= start < end <= len(close) or not 0 <= cost < 1
            or not 0 < alpha <= 1 or not 0 < scale <= 1):
        raise reference.ContractError('invalid account input')
    return _account(close, targets, days, start, end, cost, alpha, scale)


def summary(rows):
    net, nav = rows[:, 0], np.r_[1., rows[:, 6]]
    sd = float(net.std())
    return {'days': len(net), 'mean_bp_day': float(net.mean()*1e4),
            'annual_arithmetic': float(net.mean()*365), 'annual_vol': sd*np.sqrt(365),
            'sharpe': float(net.mean()/sd*np.sqrt(365)) if sd > 0 else None,
            'nw10_t': float(stats.newey_west_t(net, 10)[2]),
            'max_drawdown': float(np.max(1-nav/np.maximum.accumulate(nav))),
            'total_cost_dollars': float(rows[:, 3].sum()), 'turnover': float(rows[:, 4].sum()),
            'mean_exposure': float(rows[:, 5].mean()), 'ending_nav': float(nav[-1])}


def risk_scales(candidate, passive):
    c, p = np.std(candidate, ddof=1), np.std(passive, ddof=1)
    if not np.isfinite([c, p]).all() or min(c, p) <= 0:
        raise reference.ContractError('undefined discovery risk scale')
    return min(1., p/c), min(1., c/p)


def select_candidate(discovery_metrics):
    scores = [row['sharpe'] for row in discovery_metrics]
    if any(s is None or not np.isfinite(s) for s in scores):
        raise reference.ContractError('undefined discovery selection score')
    # GRID order breaks exact ties; no validation statistic is accepted here.
    return int(np.argmax(scores))


def bootstrap_family(differences, selected, block, replicates=5000, seed=SEED):
    """Paired common blocks; least-favorable recentered max statistic with fixed NW(10) SE."""
    x = np.asarray(differences, float)
    if (x.ndim != 2 or not np.isfinite(x).all() or len(x) < 2 or
            not 0 <= selected < x.shape[1] or block < 1 or replicates < 1):
        raise reference.ContractError('invalid family bootstrap')
    n = len(x)
    means = x.mean(axis=0)
    z = x-means
    variance_sum = np.sum(z*z, axis=0)
    for lag in range(1, min(10, n-1)+1):
        variance_sum += 2*(1-lag/11)*np.sum(z[lag:]*z[:-lag], axis=0)
    if np.any(variance_sum <= n*(1e-12*np.max(np.abs(x), axis=0))**2):
        raise reference.ContractError('undefined NW standard error in search family')
    se = np.sqrt(variance_sum)/n
    rng = np.random.default_rng(seed+block)
    boot_selected, boot_max = np.empty(replicates), np.empty(replicates)
    blocks = (n+block-1)//block
    for offset in range(0, replicates, 100):
        size = min(100, replicates-offset)
        starts = rng.integers(n, size=(size, blocks))
        indices = ((starts[:, :, None]+np.arange(block)) % n).reshape(size, -1)[:, :n]
        boot_means = z[indices].mean(axis=1)
        boot_selected[offset:offset+size] = boot_means[:, selected]+means[selected]
        boot_max[offset:offset+size] = np.max(boot_means/se, axis=1)
    statistic = means[selected]/se[selected]
    q = np.quantile(boot_selected, [.025, .975])
    return {'block_days': block, 'replicates': replicates, 'seed': seed+block,
            'selected_mean': float(means[selected]), 'selected_nw10_t': float(statistic),
            'lower95': float(q[0]), 'upper95': float(q[1]),
            'family_max_p': float((1+np.count_nonzero(boot_max >= statistic))/(replicates+1)),
            'family_size': x.shape[1]}, boot_max


def fresh_output(output):
    if output.is_symlink() or output.exists():
        raise reference.ContractError('research output must be a new directory; never overwrite')


def decision_checks(candidate, passive, stressed_mean, bootstrap):
    required = [candidate['sharpe'], passive['sharpe'], candidate['max_drawdown'],
                passive['max_drawdown'], stressed_mean, bootstrap['lower95'], bootstrap['family_max_p']]
    if any(value is None or not np.isfinite(value) for value in required):
        raise reference.ContractError('undefined required validation decision metric')
    return {'validation_sharpe_gain_ge_015': candidate['sharpe'] >= passive['sharpe']+.15,
            'validation_2x_mean_positive': stressed_mean > 0,
            'validation_drawdown_no_worse': candidate['max_drawdown'] <= passive['max_drawdown'],
            'paired_mean_lower95_positive': bootstrap['lower95'] > 0,
            'family_max_p_le_005': bootstrap['family_max_p'] <= .05}


def write_csv(path, records):
    with path.open('x', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(records)


def run(raw, output):
    fresh_output(output)
    spec_sha, runner_sha = verify_registration()
    dates, close, provenance = reference.load_prices(reference.LANE/'results/data_manifest.json', raw)
    mondays = np.array([date.fromisoformat(d).weekday() == 0 for d in dates])
    month_starts = np.array([d[8:10] == '01' for d in dates])
    passive = np.full_like(close, 1/6)
    bounds = {s: (dates.index(a), len(dates) if b == '2026-10-01' else dates.index(b))
              for s, (a, b) in reference.SPLITS.items()}
    a, b = bounds['discovery']
    passive_training = account(close, passive, month_starts, a, b, .0012)
    targets, scales, discovery_scores = [], [], []
    print('Verified fixed input; computing 96 discovery candidates.', flush=True)
    for config in GRID:
        h, sign, k, gate, alpha = config
        target = rank_targets(close, h, sign, k, gate)
        train1 = account(close, target, mondays, a, b, .0012, alpha)
        train2 = account(close, target, mondays, a, b, .0024, alpha)
        targets.append(target)
        scales.append(risk_scales(train1[:, 0], passive_training[:, 0]))
        discovery_scores.append({'candidate': identity(config), **summary(train2)})
    selected = select_candidate(discovery_scores)
    print(f'Discovery selection locked: {identity(GRID[selected])}. Scoring fixed grid, no reselection.', flush=True)
    metrics_rows, selected_rows, paired_rows = [], [], []
    panels, bootstrap_results, bootstrap_maxima = {}, {}, {}
    fields = ['net', 'gross', 'cost_fraction', 'cost_dollars', 'turnover', 'exposure', 'nav', 'cash_end']
    fields += ['units_'+s for s in fetcher.SYMBOLS]
    for split, (a, b) in bounds.items():
        for tier in (1, 2, 3):
            differences = np.empty((b-a, len(GRID)))
            candidate_panel, control_panel = differences.copy(), differences.copy()
            for j, (config, target, (cs, bs)) in enumerate(zip(GRID, targets, scales)):
                left = account(close, target, mondays, a, b, .0012*tier, config[-1], cs)
                right = account(close, passive, month_starts, a, b, .0012*tier, 1., bs)
                candidate_panel[:, j], control_panel[:, j] = left[:, 0], right[:, 0]
                differences[:, j] = left[:, 0]-right[:, 0]
                for role, rows in (('candidate', left), ('matched_passive', right)):
                    metrics_rows.append({'split': split, 'cost_multiple': tier,
                        'candidate': identity(config), 'role': role,
                        'capital_scale': cs if role == 'candidate' else bs, **summary(rows)})
                    if j == selected:
                        for day, values in zip(dates[a:b], rows):
                            selected_rows.append({'split': split, 'cost_multiple': tier,
                                'role': role, 'date': day, **dict(zip(fields, values.tolist()))})
                if j == selected:
                    paired_rows.extend({'split': split, 'cost_multiple': tier, 'date': day,
                                        'difference': float(d)} for day, d in zip(dates[a:b], differences[:, j]))
            panels[f'{split}_{tier}_candidate'] = candidate_panel
            panels[f'{split}_{tier}_passive'] = control_panel
            if split == 'validation' and tier == 1:
                for block in (30, 10, 60):
                    result, maximum = bootstrap_family(differences, selected, block)
                    bootstrap_results[str(block)] = result
                    bootstrap_maxima[f'max_t_block{block}'] = maximum
            print(f'Finished {split}, {tier}x: 192 accounts.', flush=True)
    choice = identity(GRID[selected])
    lookup = {(r['split'], r['cost_multiple'], r['role']): r for r in metrics_rows if r['candidate'] == choice}
    c, p = lookup['validation', 1, 'candidate'], lookup['validation', 1, 'matched_passive']
    boot = bootstrap_results['30']
    checks = decision_checks(c, p, lookup['validation', 2, 'candidate']['mean_bp_day'], boot)
    verdict = {'verdict': 'PARTIAL' if all(checks.values()) else 'NULL', 'checks': checks,
               'selected_index': selected, 'selected_candidate': choice,
               'discovery_selection': 'highest unscaled discovery 2x net Sharpe; fixed grid tie order',
               'candidate_capital_scale': scales[selected][0], 'passive_capital_scale': scales[selected][1],
               'trials': len(GRID), 'validation_bootstrap': bootstrap_results,
               'evidence': 'exploratory six-surviving-coin spot search on previously observed dates'}
    output.mkdir(parents=True)
    write_csv(output/'discovery_selection.csv', discovery_scores)
    write_csv(output/'grid_metrics.csv', metrics_rows)
    write_csv(output/'selected_daily.csv', selected_rows)
    write_csv(output/'paired_differences.csv', paired_rows)
    reference.write_json(output/'verdict.json', verdict)
    # Numeric arrays only, no pickle. Raw price archives never enter Git.
    with (output/'search_returns.npz').open('xb') as handle:
        np.savez_compressed(handle, **panels, **bootstrap_maxima)
    manifest = {'prereg_sha256': spec_sha, 'runner_sha256': runner_sha,
                'dependencies': DEPENDENCIES, 'data_manifest_sha256': provenance['data_manifest_sha256'],
                'source_archives': 414, 'calendar_rows_per_coin': len(dates),
                'python': platform.python_version(), 'numpy': np.__version__, 'numba': numba.__version__,
                'grid': [{'candidate': identity(c), 'config': list(c),
                          'candidate_scale': s[0], 'passive_scale': s[1]} for c, s in zip(GRID, scales)],
                'splits': reference.SPLITS, 'cost_one_way': [.0012, .0024, .0036],
                'output_sha256': {p.name: reference.sha(p.read_bytes()) for p in sorted(output.iterdir())}}
    reference.write_json(output/'run_manifest.json', manifest)
    return verdict


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-dir', type=Path, default=fetcher.DEFAULT_RAW)
    parser.add_argument('--out', type=Path, default=LANE/'results')
    args = parser.parse_args()
    verify_registration()
    fresh_output(args.out)
    try:
        result = run(args.raw_dir, args.out)
    except (ValueError, OSError) as exc:
        result = {'verdict': 'INCONCLUSIVE', 'reason': str(exc)}
        args.out.mkdir(parents=True, exist_ok=True)
        reference.write_json(args.out/'inconclusive.json', result)
    print(json.dumps(reference.clean_json(result), sort_keys=True))


if __name__ == '__main__':
    main()
