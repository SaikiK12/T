"""Run the unchanged R338 independent oracle against the frozen R339 closure."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.check_opportunity_execution import audit


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.out, ROOT/'experiments/opportunity_execution_v2')
    result['scope'] = 'R339 canonical-mark correction, unchanged R338 independent rational oracle'
    prior = json.loads((ROOT/'experiments/opportunity_execution_v1/audit.json').read_text())
    current = {(r['case_id'], r['cost_multiple']): r for r in result['paths']}
    compared = 0
    for old in prior['paths']:
        key = old['case_id'], old['cost_multiple']; new = current.get(key)
        fields = ('cash', 'nav', 'known_realized_net_component')
        same = new is not None and len(new['final_accounts']) == len(old['final_accounts'])
        if same:
            for a, b in zip(old['final_accounts'], new['final_accounts']):
                same = same and (a['venue'], a['asset']) == (b['venue'], b['asset'])
                same = same and all((None if a[k] is None else Fraction(a[k])) ==
                    (None if b[k] is None else Fraction(b[k])) for k in fields)
        if not same:
            result['failures'].append({'case_id': key[0], 'cost_multiple': key[1],
                'error': 'a previously complete R338 path changed its final financial amounts'})
        compared += 1
    result['prior_completed_paths_compared'] = compared
    result['prior_failures_retained'] = len(prior['failures'])
    result['passed'] = not result['failures']
    (args.out/'audit.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'paths'}, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
