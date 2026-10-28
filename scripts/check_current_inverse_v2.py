"""R341 exact-type adapter for R340's unchanged independent rational oracle.

Only canonicalize numeric arguments of the original hurdle helper. The frozen
zero-charge branch creates exactly1.0 via integer division; noninteger binary
floats are rejected rather than rounded or allowed to weaken an equality.
Original R340 failure stays retained. No economic result is recalculated.
"""
import argparse
from fractions import Fraction as F
import json
import math
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import check_current_inverse as parent
from scripts.check_opportunity_execution import verify

LANE = ROOT/'experiments/current_inverse_check_v2'
original_hurdle = parent.check_hurdle


def exact(value):
    if isinstance(value, float) and (not math.isfinite(value) or not value.is_integer()):
        raise ValueError('noninteger binary float is not an exact oracle input')
    return F(value)


def check_hurdle(check, observed, q, delta, price, delivery_rate, exit_rate, spent, capital):
    return original_hurdle(check, observed, *(exact(x) for x in
        (q, delta, price, delivery_rate, exit_rate, spent, capital)))


def audit(directory):
    verify(LANE)
    # Scoped only to this one-process diagnostic. No source gate, assumption,
    # tolerance, actual cash field or frozen file is changed. The registered
    # replacement invokes the literal original exact-equality helper.
    with patch.object(parent, 'check_hurdle', check_hurdle):
        result = parent.audit(directory)
    result['registry_id'] = 'R341'; result['parent_round'] = 'R340'
    result['economic_results_recomputed'] = False
    result['original_oracle_failure_retained'] = True
    verify(LANE); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--out', type=Path, required=True)
    args = p.parse_args(); result = audit(args.out)
    (args.out/'audit_R341.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps(result, indent=2))
