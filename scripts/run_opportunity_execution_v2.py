"""R339 frozen correction replay of R338's SAME invented cases and oracle."""
import argparse
from decimal import Decimal as D
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.opportunity_execution_v2.fixture_support import FixtureV2
from lab.paper_controls import PaperRisk, RiskPolicy
from scripts.run_opportunity_execution import Scenario as ParentScenario, encoded, verify

LANE = ROOT/'experiments/opportunity_execution_v2'


class Scenario(ParentScenario):
    # Only construction changes. Every operation, cost rule, risk observation,
    # failure injection and output capture is the frozen R338 implementation.
    def __init__(self, case, multiple, directory):
        self.case, self.multiple = case, multiple
        balances = {(r['venue'], r['asset']): D(r['cash']) for r in case.get('balances',
            [{'venue': 'mexc', 'asset': 'USDT', 'cash': '1000'}])}
        options = {'max_symbol_gross_fraction': D(1),
            **{k: D(v) for k, v in case.get('policy', {}).items()}}
        self.fixture = FixtureV2(directory, balances, RiskPolicy('R338-invented', **options))
        f = self.fixture
        self.control_risk = PaperRisk(directory/'control-risk.jsonl', f.policy, f.account.anchor,
            contract_version='R338-invented', initial_balances=balances)
        self.mids = {}; self.spreads = {}; self.trades = {}; self.steps = []; self.t = 0


def report(out):
    verify(LANE)
    if out.exists():
        raise ValueError('fresh correction output path required')
    out.mkdir(parents=True)
    fixture = json.loads((LANE/'fixtures.json').read_text()); rows = []; journals = {}
    for case in fixture['cases']:
        for multiple in fixture['cost_multiples']:
            directory = out/'states'/case['case_id']/str(multiple); directory.mkdir(parents=True)
            try:
                result = Scenario(case, multiple, directory).run()
            except Exception as error:
                result = {'case_id': case['case_id'], 'cost_multiple': multiple,
                    'state': 'failed', 'error': type(error).__name__+': '+str(error)}
            rows.append(result)
            journals[case['case_id']+'/'+str(multiple)] = {
                p.name: p.read_text() for p in sorted(directory.glob('*.jsonl'))}
    output = {'scope': 'R339 canonical-mark adapter; same R338 invented accounting/lifecycle diagnostics',
        'market_requests': 0, 'predictive_strategy_trials': 0, 'prospective_days': 0,
        'actual_executable_expected_net': None, 'cases': rows}
    (out/'results.json').write_bytes(encoded(output))
    (out/'journals.json.gz').write_bytes(gzip.compress(encoded(journals), mtime=0))
    verify(LANE)
    return {'cost_paths': len(rows), 'completed': sum(r['state'] == 'completed' for r in rows),
        'failed': sum(r['state'] == 'failed' for r in rows), 'actual_executable_expected_net': None,
        'prospective_days': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(); print(json.dumps(report(args.out), indent=2))


if __name__ == '__main__':
    main()
