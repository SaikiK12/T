"""Frozen R330 audit-only sign correction; original failure/model stay intact."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.check_level_probability_v2 import check_corrected_entry_sign

LANE=ROOT/'experiments/level_probability_v1'


def verify():
    spec=(LANE/'audit_correction.md').read_bytes()
    if hashlib.sha256(spec).hexdigest()!=(LANE/'audit_correction.sha256').read_text().strip():
        raise ValueError('audit correction spec drift')
    raw=(LANE/'audit_code_inputs.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() not in spec.decode():raise ValueError('unbound audit code identity')
    for name,digest in json.loads(raw)['sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('audit input drift '+name)


def audit(directory):
    verify()
    failure=json.loads((LANE/'original_audit_failure.json').read_text())
    if hashlib.sha256((Path(directory)/'results.json').read_bytes()).hexdigest()!=failure['frozen_results_sha256']:
        raise ValueError('audit correction cannot substitute financial results')
    result=check_corrected_entry_sign(directory)
    verify()
    return result|dict(audit_id='R330-AUDIT-SIGN1',original_failure_retained=True,
                       financial_model_or_result_changed=False,new_strategy_variants=0)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('--out',type=Path)
    a=p.parse_args();result=audit(a.directory);raw=(json.dumps(result,sort_keys=True,indent=2)+'\n').encode()
    if a.out:
        with a.out.open('xb') as f:f.write(raw)
    print(raw.decode(),end='')
