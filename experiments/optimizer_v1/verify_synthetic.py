"""Manual synthetic review recipe: requires SciPy; reads no project outcomes.
Run from repository root:
NUMBA_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 python experiments/optimizer_v1/verify_synthetic.py
"""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

import numpy as np
import scipy
from scipy.optimize import minimize, least_squares
from scipy.cluster.hierarchy import linkage, leaves_list
from scipy.spatial.distance import squareform

sys.path.insert(0, str(Path.cwd()))
from scripts import run_optimizer as o

rng = np.random.default_rng(523985)
worst = dict(minvar_variance=0., minvar_weight=0., erc_weight=0., hrp_weight=0.)
retries = 0
for case in range(300):
    A = rng.normal(size=(3, 3))
    C = A@A.T + np.eye(3)*(.05 if case % 2 else .5)
    C /= np.trace(C)
    ref = minimize(lambda w: w@C@w, np.ones(3)/3, jac=lambda w: 2*C@w,
                   bounds=[(0., 1.)]*3, method='SLSQP',
                   constraints={'type': 'eq', 'fun': lambda w: w.sum()-1,
                                'jac': lambda w: np.ones(3)},
                   options={'ftol': 1e-13, 'maxiter': 1000})
    assert ref.success, (case, ref.message)
    actual = o.minimum_variance(C)
    worst['minvar_variance'] = max(worst['minvar_variance'], abs(float(actual@C@actual-ref.fun)))
    worst['minvar_weight'] = max(worst['minvar_weight'], float(np.abs(actual-ref.x).max()))

    def weights(z):
        a = np.r_[z, 0.]
        a -= a.max()
        return np.exp(a)/np.exp(a).sum()

    def residual(z):
        w = weights(z)
        q = w*(C@w)
        return ((q-q[2])/q.sum())[:2]

    root = least_squares(residual, np.zeros(2), xtol=1e-13, ftol=1e-13,
                         gtol=1e-13, max_nfev=10000)
    if np.abs(residual(root.x)).max() > 1e-7:
        retries += 1
        positive = minimize(lambda x: .5*x@C@x-np.log(x).sum()/3, np.ones(3),
                            jac=lambda x: C@x-1/(3*x), bounds=[(1e-12, None)]*3,
                            method='SLSQP', options={'ftol': 1e-13, 'maxiter': 1000})
        root = least_squares(residual, np.log(positive.x[:2]/positive.x[2]),
                             xtol=1e-13, ftol=1e-13, gtol=1e-13, max_nfev=10000)
    assert np.abs(residual(root.x)).max() < 1e-7, case
    worst['erc_weight'] = max(worst['erc_weight'], float(np.abs(o.equal_risk(C)-weights(root.x)).max()))

    corr = C/np.sqrt(np.outer(np.diag(C), np.diag(C)))
    distance = np.sqrt(np.maximum((1-np.clip(corr, -1, 1))/2, 0))
    np.fill_diagonal(distance, 0)
    order = leaves_list(linkage(squareform(distance, checks=False), method='single')).tolist()

    def variance(indices):
        sub = C[np.ix_(indices, indices)]
        iv = 1/np.diag(sub)
        iv /= iv.sum()
        return float(iv@sub@iv)

    def allocate(indices):
        if len(indices) == 1:
            return {indices[0]: 1.}
        split = len(indices)//2
        left, right = indices[:split], indices[split:]
        vl, vr = variance(left), variance(right)
        return {**{j: w*vr/(vl+vr) for j, w in allocate(left).items()},
                **{j: w*vl/(vl+vr) for j, w in allocate(right).items()}}

    expected = allocate(order)
    expected = np.array([expected[j] for j in range(3)])
    worst['hrp_weight'] = max(worst['hrp_weight'], float(np.abs(expected-o.hierarchical_risk(C)).max()))
assert worst['minvar_variance'] < 1e-10
assert worst['erc_weight'] < 1e-8
assert worst['hrp_weight'] < 1e-12
print({'cases': 300, 'seed': 523985, 'numpy': np.__version__, 'scipy': scipy.__version__,
       'maximum_errors': worst, 'independent_ERC_solver_retries': retries})

# Mock source data and provenance only for this synthetic pipeline/reproduction test.
rng = np.random.default_rng(87312)
matrix = rng.normal([.0002, .00015, .00025], [.012, .008, .011], (2099, 3))
arrays = {name: matrix[:, j] for j, name in enumerate(o.source.SOURCES)}
summaries = {(name, window, cm): {'days': b-a,
             'mean_bp_day': float(matrix[a:b, j].mean()*1e4-(cm-1)*(.1+j*.1)),
             'gross_exposure': 1.}
             for window, (a, b) in o.source.WINDOWS.items()
             for j, name in enumerate(o.source.SOURCES) for cm in (1, 2, 3)}
with tempfile.TemporaryDirectory(prefix='optimizer_oracle_') as temporary:
    outputs = []
    with patch.object(o, 'verify_registration', return_value={'synthetic_only': True}), \
         patch.object(o.source, 'read_inputs', return_value=(arrays, summaries)):
        for label in ('one', 'two'):
            folder = Path(temporary)/label
            with contextlib.redirect_stdout(io.StringIO()):
                o.run(folder)
            outputs.append({p.name: p.read_bytes() for p in folder.iterdir()})
        assert outputs[0] == outputs[1]
        try:
            o.run(Path(temporary)/'one')
        except o.Error:
            pass
        else:
            raise AssertionError('Nonempty output overwritten')
    print({'synthetic_pipeline': 'pass', 'repeat_output_files_identical': sorted(outputs[0]),
           'nonempty_overwrite_refused': True})
