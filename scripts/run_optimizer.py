#!/usr/bin/env python3
"""Finite static M027 allocation screen; imports never read project outcomes."""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import gzip
import hashlib
import io
import itertools
import json
from pathlib import Path
import platform
import re
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lab import prereg, stats
from scripts import run_allocation as source
from scripts import run_weekly_rotation as inference

LANE = ROOT / 'experiments/optimizer_v1'
METHODS = ('min_variance', 'equal_risk', 'hrp')
INCUMBENT = np.array([0., .3, .7])
SEED = 20261020253
DEPENDENCIES = {
    'scripts/run_allocation.py': '2e0bd37ec44587b3e152418e7925183d688278fbaf0d4550624125b0f3d854f9',
    'scripts/run_weekly_rotation.py': '9084d30faa615d8e02a0b482f60d774537adc868c90cd13f95f23486cda7e8c3',
    'lab/stats.py': 'bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34',
    'lab/prereg.py': '3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508',
}
Error = source.ContractError


def covariance_contract(cov):
    cov = np.asarray(cov, float)
    if cov.shape != (3, 3) or not np.isfinite(cov).all():
        raise Error('Finite three-sleeve covariance required')
    magnitude = float(np.abs(cov).max())
    if magnitude <= 0 or not np.allclose(cov, cov.T, atol=magnitude*1e-12, rtol=0):
        raise Error('Symmetric nonzero covariance required')
    cov = (cov+cov.T)/2
    if np.linalg.eigvalsh(cov)[0] <= np.trace(cov)*1e-12:
        raise Error('Covariance fails the common positive-definite contract')
    return cov / np.trace(cov)


def minimum_variance(cov):
    """Exact long-only simplex minimum by enumerating its seven nonempty faces."""
    cov = covariance_contract(cov)
    best, score = None, np.inf
    for size in (1, 2, 3):
        for subset in itertools.combinations(range(3), size):
            indices = list(subset)
            v = np.linalg.solve(cov[np.ix_(indices, indices)], np.ones(size))
            v /= v.sum()
            if (v < -1e-12).any():
                continue
            w = np.zeros(3)
            w[indices] = np.maximum(v, 0)
            w /= w.sum()
            variance = float(w @ cov @ w)
            if variance < score:
                best, score = w, variance
    if best is None:
        raise Error('Minimum-variance solver failed')
    return best


def equal_risk(cov):
    """Cyclic coordinate solution of .5*x'C*x - sum(log(x))/3, then normalize."""
    cov = covariance_contract(cov)
    x = 1/np.sqrt(np.diag(cov))
    for _ in range(10000):
        for j in range(3):
            other = float(cov[j] @ x - cov[j, j]*x[j])
            x[j] = (np.sqrt(other*other+4*cov[j, j]/3)-other)/(2*cov[j, j])
        w = x/x.sum()
        contributions = w*(cov @ w)
        if np.max(np.abs(contributions/contributions.sum()-1/3)) <= 1e-10:
            return w
    raise Error('Equal-risk solver did not converge within the frozen limit')


def hierarchical_risk(cov):
    """Three-leaf single linkage, deterministic leaf order, recursive bisection."""
    cov = covariance_contract(cov)
    sd = np.sqrt(np.diag(cov))
    corr = np.clip(cov/np.outer(sd, sd), -1, 1)
    distance = np.sqrt(np.maximum((1-corr)/2, 0))
    # Three leaves have one nearest pair and one outsider. Tuple order breaks ties.
    pair = min(itertools.combinations(range(3), 2), key=lambda p: (distance[p], p))
    outsider = next(j for j in range(3) if j not in pair)
    order = [outsider, *pair]
    weights = np.ones(3)

    def variance(cluster):
        sub = cov[np.ix_(cluster, cluster)]
        iv = 1/np.diag(sub)
        iv /= iv.sum()
        return float(iv @ sub @ iv)

    def split(cluster):
        if len(cluster) <= 1:
            return
        left, right = cluster[:len(cluster)//2], cluster[len(cluster)//2:]
        vl, vr = variance(left), variance(right)
        weights[left] *= vr/(vl+vr)
        weights[right] *= vl/(vl+vr)
        split(left)
        split(right)

    split(order)
    return weights/weights.sum()


def fit(matrix):
    """Only discovery can affect any weight, choice or comparison risk scale."""
    matrix = np.asarray(matrix, float)
    a, b = source.WINDOWS['discovery']
    if matrix.ndim != 2 or matrix.shape[1] != 3 or len(matrix) < b:
        raise Error('Three complete discovery streams required')
    train = matrix[a:b]
    if not np.isfinite(train).all():
        raise Error('Nonfinite discovery observation')
    cov = np.cov(train, rowvar=False, ddof=1)
    functions = (minimum_variance, equal_risk, hierarchical_risk)
    weights = {name: function(cov) for name, function in zip(METHODS, functions)}
    baseline = train @ INCUMBENT
    scores, scales = [], {}
    for name, w in weights.items():
        if not np.isfinite(w).all() or (w < 0).any() or abs(w.sum()-1) > 1e-12:
            raise Error('Invalid allocation weights')
        x = train @ w
        score = float(source.sharpe(x))
        if not np.isfinite(score):
            raise Error('Undefined discovery selection score')
        scores.append(score)
        sx, sy = x.std(ddof=1), baseline.std(ddof=1)
        if not np.isfinite([sx, sy]).all() or min(sx, sy) <= 0:
            raise Error('Undefined discovery risk scale')
        scales[name] = (min(1., sy/sx), min(1., sx/sy))
    return {'weights': weights, 'selected': METHODS[int(np.argmax(scores))],
            'discovery_sharpes': dict(zip(METHODS, scores)), 'risk_scales': scales,
            'discovery_covariance': cov}


def stress_mean(weights, summaries, window, multiple, scale=1.):
    return float(scale * sum(w*summaries[(name, window, multiple)]['mean_bp_day']
                             for name, w in zip(source.SOURCES, weights)))


def checks(candidate, benchmark, mean2, boot):
    sharpes = [float(source.sharpe(path)) for path in (candidate, benchmark)]
    if not np.isfinite([*sharpes, mean2, boot['lower95'], boot['family_max_p']]).all():
        raise Error('Undefined required decision metric; no NULL may be inferred')
    return {
        'validation_sharpe_gain_at_least_0_15': sharpes[0]-sharpes[1] >= .15,
        'validation_risk_matched_mean_gain_positive': float((candidate-benchmark).mean()) > 0,
        'validation_mean_2x_positive': mean2 > 0,
        'validation_drawdown_no_larger': source.max_drawdown(candidate) <= source.max_drawdown(benchmark),
        'paired_mean_lower95_positive': boot['lower95'] > 0,
        'three_method_family_max_p_at_most_0_05': boot['family_max_p'] <= .05,
    }


def verify_registration():
    digest = prereg.verify(LANE / 'PREREG.md')
    actual = source.sha256(Path(__file__))
    declared = re.findall(r'Runner SHA-256: `([a-f0-9]{64})`', (LANE / 'PREREG.md').read_text())
    if declared != [actual]:
        raise Error('Optimizer runner differs from frozen declaration')
    for relative, expected in DEPENDENCIES.items():
        if source.sha256(ROOT / relative) != expected:
            raise Error(f'Frozen dependency changed: {relative}')
    metadata = source.verify_guards(ROOT)
    return {'spec_sha256': digest, 'runner_sha256': actual, 'dependencies': DEPENDENCIES,
            'source_verification': metadata, 'software': {'python': platform.python_version(),
            'numpy': np.__version__}, 'trials': 3, 'research_gate': 0,
            'claim': 'Exploratory spent-date static-sleeve allocation; no MEXC fills or prospective evidence'}


def run(output):
    metadata = verify_registration()  # before any project outcome value is opened
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise Error('Refusing to overwrite a nonempty output directory')
    output.mkdir(parents=True, exist_ok=True)
    try:
        arrays, summaries = source.read_inputs(ROOT)
        matrix = np.column_stack([arrays[name] for name in source.SOURCES])
        fitted = fit(matrix)
        selected = fitted['selected']
        controls = {'R228_incumbent': INCUMBENT, 'equal_weight': np.ones(3)/3,
                    **{name: np.eye(3)[j] for j, name in enumerate(source.SOURCES)}}
        family = [source.Candidate(name, tuple(w)) for name, w in {**fitted['weights'], **controls}.items()]
        source.write_csv(output/'metrics.csv', source.candidate_rows(matrix, summaries, family))

        risk_rows, differences = [], []
        selected_validation = None
        for name in METHODS:
            w = fitted['weights'][name]
            sx, sy = fitted['risk_scales'][name]
            for window, (a, b) in source.WINDOWS.items():
                x, y = sx*(matrix[a:b]@w), sy*(matrix[a:b]@INCUMBENT)
                risk_rows.append({'method': name, 'window': window, 'candidate_scale': sx,
                    'incumbent_scale': sy, 'candidate_sharpe': float(source.sharpe(x)),
                    'incumbent_sharpe': float(source.sharpe(y)),
                    'candidate_dd': source.max_drawdown(x), 'incumbent_dd': source.max_drawdown(y),
                    **{f'candidate_mean_{cm}x_bp': stress_mean(w, summaries, window, cm, sx)
                       for cm in (1, 2, 3)},
                    **{f'incumbent_mean_{cm}x_bp': stress_mean(INCUMBENT, summaries, window, cm, sy)
                       for cm in (1, 2, 3)}})
                if window == 'validation':
                    differences.append(x-y)
                    if name == selected:
                        selected_validation = x, y
        source.write_csv(output/'risk_matched.csv', risk_rows)
        d = np.column_stack(differences)
        boot = {str(block): inference.bootstrap_family(d, METHODS.index(selected), block,
                replicates=5000, seed=SEED)[0] for block in (30, 10, 60)}
        x, y = selected_validation
        mean2 = stress_mean(fitted['weights'][selected], summaries, 'validation', 2,
                            fitted['risk_scales'][selected][0])
        conditions = checks(x, y, mean2, boot['30'])
        verdict = {'verdict': 'PARTIAL' if all(conditions.values()) else 'NULL', 'checks': conditions,
                   'selected': selected, 'validation_sharpe_gain': float(source.sharpe(x)-source.sharpe(y)),
                   'interpretation': 'Exploratory only; a passed screen requires a new prospective lane'}
        serial = {key: value.tolist() if isinstance(value, np.ndarray) else value
                  for key, value in fitted.items() if key not in ('weights',)}
        serial['weights'] = {name: dict(zip(source.SOURCES, w.tolist()))
                             for name, w in fitted['weights'].items()}
        source.write_json(output/'selection.json', serial)
        source.write_json(output/'bootstrap.json', boot)
        source.write_json(output/'verdict.json', verdict)
        metadata['incumbent_weights'] = dict(zip(source.SOURCES, INCUMBENT.tolist()))
        metadata['weights_sha256'] = source.sha256(output/'selection.json')
        source.write_json(output/'manifest.json', metadata)
        # Only the selected risk-matched pair; deterministic gzip, not duplicate full tensors.
        stream = io.StringIO(newline='')
        import csv
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(['date', 'window', 'candidate_net_1x', 'incumbent_net_1x'])
        w = fitted['weights'][selected]
        sx, sy = fitted['risk_scales'][selected]
        for window, (a, b) in source.WINDOWS.items():
            for t in range(a, b):
                writer.writerow([(date(2021, 1, 1)+timedelta(days=t)).isoformat(), window,
                                 format(float(sx*(matrix[t]@w)), '.17g'),
                                 format(float(sy*(matrix[t]@INCUMBENT)), '.17g')])
        (output/'selected_daily.csv.gz').write_bytes(gzip.compress(stream.getvalue().encode(), mtime=0))
        print(json.dumps(verdict, indent=2))
        return verdict
    except (Error, ValueError, np.linalg.LinAlgError) as exc:
        source.write_json(output/'verdict.json', {'verdict': 'INCONCLUSIVE', 'reason': str(exc)})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=LANE/'results')
    args = parser.parse_args()
    run(args.out)


if __name__ == '__main__':
    main()
