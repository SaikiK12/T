"""Independent literal R321 binomial/OBM/selected-bootstrap arithmetic audit.

Uses registered simulated-path generator/seeds, not an independent DGP/source
implementation. Does not call production OBM/tolerance/interval functions or
read/reclassify a market outcome. No general market coverage assertion.
"""
import argparse
import gzip
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from scipy.stats import binom
from scripts.run_dependent_null import generate


def audit(directory):
    directory=Path(directory);lane=ROOT/'experiments/dependent_null_v1'
    design=json.loads((lane/'design.json').read_text());result=json.loads((directory/'results.json').read_text())
    c=json.loads((directory/'calibration.json').read_text());observations=[json.loads(x) for x in gzip.decompress((directory/'observations.jsonl.gz').read_bytes()).splitlines()]
    if len(observations)!=5000 or result['registered_diagnostic_trials']!=152:raise ValueError('null-study finite scope changed')
    if c['state']!='CALIBRATED':return {'state':'INCONCLUSIVE','scope':'Calibration failure retained; no invented passing audit.'}
    t=c['tolerance'];k=t['order'];m=t['paths'];p=1-t['alpha'];budget=t['cell_error_budget']
    exact=float(binom.sf(k-1,m,p));previous=float(binom.sf(k-2,m,p))
    if not exact<=budget<previous or not math.isclose(exact,t['tail_probability'],rel_tol=1e-10,abs_tol=1e-14):raise ValueError('independent binomial-order audit failed')
    statistics=json.loads(gzip.decompress((directory/'calibration_max_t.json.gz').read_bytes()))
    for b in (14,28):
        cutoff=max(sorted(statistics[x['id']+'|'+str(b)])[k-1] for x in design['calibration_profiles'])
        if cutoff!=c['cutoffs'][str(b)]:raise ValueError('worst-profile tolerance cutoff failed')
    profiles={x['id']:(i,x) for i,x in enumerate(design['calibration_profiles']+design['stress_profiles'])};checked=0;bootstrap_checked=0
    for row in observations:
        if row['replication'] not in (0,499):continue
        i,profile=profiles[row['profile']];x=generate(profile,design['validation_seed']+10000*i+row['replication'])
        mean=x.mean(axis=0)
        for b in (14,28):
            # Direct contiguous windows, independent of production cumulative sums.
            squares=sum((x[j:j+b].mean(axis=0)-mean)**2 for j in range(273-b+1))
            se=np.sqrt(b*squares/((273-b)*(273-b+1)));record=row['intervals']['calibrated_obm'+str(b)]
            np.testing.assert_allclose(se,record['se'],rtol=2e-12,atol=1e-15)
            np.testing.assert_allclose(mean-c['cutoffs'][str(b)]*se,record['lower'],rtol=2e-12,atol=1e-14)
            np.testing.assert_allclose(mean+c['cutoffs'][str(b)]*se,record['upper'],rtol=2e-12,atol=1e-14);checked+=3
        if row['replication']==0:
            rng=np.random.default_rng(design['bootstrap_seed']+10000*i);starts=rng.integers(0,273,size=(400,20));means=[]
            for starts_row in starts:
                ids=[(int(s)+j)%273 for s in starts_row for j in range(14)][:273]
                means.append(x[ids].mean(axis=0))
            lower,upper=np.quantile(means,[.05/6,1-.05/6],axis=0)
            np.testing.assert_allclose(lower,row['intervals']['circular14']['lower'],rtol=2e-12,atol=1e-14)
            np.testing.assert_allclose(upper,row['intervals']['circular14']['upper'],rtol=2e-12,atol=1e-14);bootstrap_checked+=3
    for cell in result['cells']:
        if cell['scored_paths']+cell['unscored_paths']!=cell['paths']:raise ValueError('lost diagnostic replication')
    if any(p['market_validated'] or p['actual_order_allowed'] or p['old_market_results_reclassified'] for p in result['procedures']):raise ValueError('unsupported market inference or activation')
    if result['new_prospective_paper_days'] or not result['no_market_outcomes_read']:raise ValueError('unsupported prospective evidence')
    return {'state':'ARITHMETIC_CHECKED','binomial_order':k,'independent_binomial_tail':exact,
        'selected_obm_coordinates':checked,'selected_bootstrap_coordinates':bootstrap_checked,
        'full_heldout_path_rows':len(observations),'cells':len(result['cells']),
        'scope':'Independent binomial/direct-window/selected resampling arithmetic; shared generator,not proof of DGP correctness or universal coverage.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,default=ROOT/'experiments/dependent_null_v1')
    print(json.dumps(audit(p.parse_args().directory),sort_keys=True))
