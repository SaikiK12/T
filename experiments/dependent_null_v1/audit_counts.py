"""Post-outcome validation of all frozen R321 report counts, not a new test.

This auditor was added after outcomes. It reconstructs predeclared diagnostics
from saved intervals; it cannot select a procedure or repair/re-score outcomes.
"""
import argparse
from collections import defaultdict
import gzip
import json
from pathlib import Path
from scipy.stats import binom


def audit(directory):
    directory=Path(directory);r=json.loads((directory/'results.json').read_text())
    obs=[json.loads(x) for x in gzip.decompress((directory/'observations.jsonl.gz').read_bytes()).splitlines()]
    by=defaultdict(list)
    for row in obs:by[row['profile']].append(row)
    checked=0;tails=0;unique=set()
    for c in r['cells']:
        key=c['profile'],c['method'],c['effect_shift']
        if key in unique:raise ValueError('duplicate diagnostic cell')
        unique.add(key);n=0;rejected=positive=wrong=nulls=0
        for row in by[c['profile']]:
            if c['effect_shift'] and row['replication']>=200:continue
            a=row['intervals'][c['method']]
            if a['lower'] is None or a['upper'] is None:continue
            n+=1;lo=list(a['lower']);hi=list(a['upper']);lo[0]+=c['effect_shift'];hi[0]+=c['effect_shift']
            rejection=[l>0 or u<0 for l,u in zip(lo,hi)]
            rejected+=any(rejection);positive+=lo[0]>0;wrong+=hi[0]<0;nulls+=any(rejection[1:])
        if n!=c['scored_paths'] or c['paths']-n!=c['unscored_paths']:raise ValueError('path accounting disagreement')
        if c['effect_shift']==0:
            if rejected!=c['family_false_exclusions'] or rejected/n!=c['family_false_exclusion_fraction']:raise ValueError('family error count disagreement')
            k=rejected;lo,hi=c['exact_binomial_interval'];tail=.05/80
        else:
            if positive!=c['positive_detections'] or positive/n!=c['power'] or wrong!=c['wrong_signs'] or nulls!=c['null_coordinate_false_exclusions']:raise ValueError('power/null-coordinate count disagreement')
            k=positive;lo,hi=c['power_exact_binomial_interval'];tail=.05/192
        if k and abs(float(binom.sf(k-1,n,lo))-tail)>1e-11:raise ValueError('exact lower endpoint disagreement')
        if k<n and abs(float(binom.cdf(k,n,hi))-tail)>1e-11:raise ValueError('exact upper endpoint disagreement')
        checked+=1;tails+=int(k>0)+int(k<n)
    return {'all_heldout_cells_reconstructed':checked,'binomial_endpoints_checked':tails,
        'saved_base_paths':len(obs),'post_outcome_auditor':True,
        'scope':'Counts and binomial endpoints from all saved intervals; not independent generation/source/market coverage validation.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent)
    print(json.dumps(audit(p.parse_args().directory),sort_keys=True))
