"""R323 fixed conditional continuation policies and common-account replay."""
import argparse
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab import prereg
from lab.carry_control import Book, Model, Node, Controller
from lab.continuation_paper import build_plan, model_mapping, paths, replay

LANE = ROOT / 'experiments/continuation_control_v1'
sha = prereg.sha256_file


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def save(path, value, *, compressed=False):
    raw = encode(value)
    with Path(path).open('xb') as handle:
        handle.write(gzip.compress(raw, mtime=0) if compressed else raw)


def verify(lane=LANE):
    prereg.verify(lane / 'PREREG.md')
    spec = (lane / 'PREREG.md').read_text()
    for name in ('code_inputs.json', 'inputs.json', 'fixtures.json', 'sources.json'):
        if sha(lane / name) not in spec:
            raise ValueError('unbound continuation input: ' + name)
    code = json.loads((lane / 'code_inputs.json').read_text())
    if code['python_version'] != list(sys.version_info[:3]):
        raise ValueError('continuation runtime drift')
    for manifest in (code, json.loads((lane / 'inputs.json').read_text())):
        for name, checksum in manifest['sha256'].items():
            if sha(ROOT / name) != checksum:
                raise ValueError('continuation code/input drift: ' + name)
    return json.loads((lane / 'fixtures.json').read_text())


def make_model(config, scenario):
    def books(references, sessions=('open', 'open')):
        result = []
        for reference, fee, session in zip(references, config['fee_fraction'], sessions):
            reference, half = F(reference), F(config['quote_half_spread'])
            result.append(Book(reference, reference-half, reference+half, fee, session,
                               config['best_level_capacity_base'], config['best_level_capacity_base'],
                               config['minimum_base'], config['minimum_notional']))
        return tuple(result)
    branches = scenario['branches']
    root = Node('root', 0, books(config['root_reference']), (0, 0),
                tuple((b['probability'], 'b' + str(i) + 's1') for i, b in enumerate(branches)))
    nodes = [root]
    for i, branch in enumerate(branches):
        for t in range(config['horizon']):
            stage = t+1
            name = 'b' + str(i) + 's' + str(stage)
            children = () if stage == config['horizon'] else ((1, 'b' + str(i) + 's' + str(stage+1)),)
            references = (branch['mexc_reference'][t], branch['lighter_reference'][t])
            funding = (branch['mexc_funding_quote_per_base'][t], branch['lighter_funding_quote_per_base'][t])
            nodes.append(Node(name, stage, books(references, branch['sessions'][t]), funding, children))
    return Model('root', tuple(nodes), config['horizon'], tuple(config['inventory_units']), config['base_per_unit'],
                 tuple(scenario.get('capital', config['capital'])), config['maximum_loss_fraction'],
                 config['exit_capital_buffer'], config['input_scope'])


def report(lane=LANE, out=None):
    config = verify(lane)
    out = Path(out) if out is not None else lane
    if any((out / n).exists() for n in ('results.json', 'observations.json.gz', 'journals.json.gz', '.cache')):
        raise ValueError('existing observations/journals retained; explicit fresh --out required')
    out.mkdir(parents=True, exist_ok=True)
    observations, journals, summary, plan_rows = [], {}, [], []
    world_paths, enumerations = 0, 0
    for scenario in config['scenarios']:
        model = make_model(config, scenario)
        nonterminal = sum(bool(n.children) for n in model.nodes)
        enumerations += len(model.inventory_units)**nonterminal
        for mode in config['modes']:
            plan = build_plan(model, mode)
            plan_rows.append({'scenario':scenario['id'], 'plan':plan})
            for tier in config['replay_cost_multiples']:
                relative = Path(scenario['id']) / mode / str(tier)
                raw_directory = out / '.cache/journals' / relative
                result = replay(model, plan, tier, raw_directory)
                world_paths += len(result['paths'])
                for p in result['paths']:
                    key = str(relative / p['journal'])
                    if key in journals:
                        raise ValueError('duplicate scenario journal identity')
                    journals[key] = (raw_directory / p['journal']).read_text()
                    p['journal_archive_key'] = key
                observations.append({'scenario':scenario['id'], 'model':model_mapping(model),
                                     'plan':plan, 'replay':result})
                summary.append({'scenario':scenario['id'], 'mode':mode, 'cost_multiple':tier,
                                'planning_cost_multiple':2, 'policy_sha256':plan['policy_sha256'],
                                'reference_assessment_state':plan['assessment']['state'],
                                'state':result['state'], 'conditional_expected_net':result['conditional_expected_net'],
                                'conditional_return_on_total_capital':result['conditional_return_on_total_capital'],
                                'world_paths':len(result['paths']),
                                'unscored_paths':sum(p['conditional_net'] is None for p in result['paths'])})
    counts = {'scenarios':len(config['scenarios']), 'reference_plans':len(plan_rows),
              'fixed_tier_replays':len(observations), 'alternative_world_paths':world_paths,
              'root_dynamic_policy_enumerations':enumerations}
    if counts != config['expected_counts'] or world_paths != len(journals):
        raise ValueError('registered finite scope drift')
    save(out / 'policies.json', plan_rows)
    save(out / 'observations.json.gz', observations, compressed=True)
    save(out / 'journals.json.gz', journals, compressed=True)
    result = {'registry_id':'R323', 'verdict':'PARTIAL', 'scope':config['scope'], 'counts':counts,
              'controller_variants':4, 'registered_diagnostic_trials':32, 'new_market_strategy_runs':0,
              'new_prospective_paper_days':0, 'actual_order_allowed':False,
              'source_inputs_and_transitions_market_validated':False, 'executable_expected_net_return':None,
              'cost_sensitivity':[{'multiple':k, 'executable_expected_net_return':None} for k in (1, 2, 3)],
              'fixed_policy_selected_at_cost_multiple':2, 'no_tier_winner_switch':True,
              'all_world_probabilities_retained':True, 'rows':summary,
              'input_identity_sha256':sha(lane / 'fixtures.json'), 'code_identity_sha256':sha(lane / 'code_inputs.json'),
              'policies_sha256':sha(out / 'policies.json'), 'observations_sha256':sha(out / 'observations.json.gz'),
              'journals_sha256':sha(out / 'journals.json.gz'), 'missing_for_market':config['missing_for_market'],
              'new_market_history_account_rpc_requests':0, 'historical_requests_spent':7757,
              'historical_reported_mib_spent':'229.85', 'old_results_reclassified':False,
              'uncertainty':'No empirical sampling/inference. Tree probabilities, forecasts and favorable payments are supplied assumptions, not calibrated skill.'}
    verify(lane)
    save(out / 'results.json', result)
    return out / 'results.json'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    print(report(out=parser.parse_args().out))
