"""Independent rational policy enumeration and saved-account audit for R323.

No Controller or ledger arithmetic is called. The frozen model generator is
shared only to verify input genealogy. Source interpretation and supplied tree
remain shared assumptions, not market truth.
"""
import argparse
from fractions import Fraction as Q
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_continuation_control import LANE, verify, save, sha, make_model
from lab.continuation_paper import model_mapping


def friction(book, quantity, tier):
    if not quantity:
        return 'VALUE', Q(0)
    if book['session'] == 'closed':
        return 'INFEASIBLE', None
    side = 'buy_capacity_base' if quantity > 0 else 'sell_capacity_base'
    if (book['session'] == 'unknown' or any(book[k] is None for k in
            ('bid', 'ask', 'fee_fraction', side, 'minimum_base', 'minimum_notional'))):
        return 'UNKNOWN', None
    midpoint = Q(book['reference'])
    direction = 1 if quantity > 0 else -1
    fill = midpoint + direction * tier * (Q(book['ask']) - Q(book['bid'])) / 2
    if (fill <= 0 or abs(quantity) > Q(book[side]) or abs(quantity) < Q(book['minimum_base'])
            or abs(quantity)*fill < Q(book['minimum_notional'])):
        return 'INFEASIBLE', None
    return 'VALUE', quantity*(fill-midpoint) + abs(quantity)*fill*Q(book['fee_fraction'])*tier


def legal(model, node, units, money):
    return all(e >= Q(initial)*(1-Q(model['maximum_loss_fraction']))
               and e >= abs(units*Q(model['base_per_unit']))*Q(b['reference'])*(1+Q(model['exit_capital_buffer']))
               for e, initial, b in zip(money, model['initial_capital'], node['books']))


def trade(model, node, before, after, money, tier):
    if not legal(model, node, before, money):
        return 'INFEASIBLE', None
    quantity = (after-before)*Q(model['base_per_unit'])
    values = [friction(b, s*quantity, tier) for b, s in zip(node['books'], (1, -1))]
    state = 'INFEASIBLE' if any(s == 'INFEASIBLE' for s, _ in values) else 'UNKNOWN' if any(s == 'UNKNOWN' for s, _ in values) else 'VALUE'
    if state != 'VALUE':
        return state, None
    money = tuple(e-cost for e, (_, cost) in zip(money, values))
    return ('VALUE', money) if legal(model, node, after, money) else ('INFEASIBLE', None)


def edge(model, parent, child, units, money):
    quantity = units*Q(model['base_per_unit'])
    if quantity and any(x is None for x in child['funding_quote_per_base']):
        return None
    return tuple(e+s*quantity*(Q(b['reference'])-Q(a['reference']))
                 - s*quantity*(Q(f) if f is not None else 0)
                 for e, s, a, b, f in zip(money, (1, -1), parent['books'], child['books'], child['funding_quote_per_base']))


def routes(model, start=None):
    nodes = {n['id']:n for n in model['nodes']}
    def walk(key, p, path):
        node = nodes[key]
        path = path+(key,)
        if not node['children']:
            yield p, path
        for probability, child in node['children']:
            yield from walk(child, p*Q(probability), path)
    return tuple(walk(start or model['root'], Q(1), ()))


def policy_value(model, policy, *, start=None, units=0, money=None, tier=2):
    nodes = {n['id']:n for n in model['nodes']}
    initial = tuple(Q(x) for x in model['initial_capital']) if money is None else money
    values = []
    for probability, path in routes(model, start):
        equity, q, parent, status = initial, units, None, 'VALUE'
        for key in path:
            node = nodes[key]
            if parent is not None:
                equity = edge(model, parent, node, q, equity)
                if equity is None:
                    status = 'UNKNOWN'
                    break
            selection = policy[key]
            if isinstance(selection, dict):
                action = selection['model_action_units']
                if action is None:
                    status = selection['state']
                    break
            else:
                action = selection
            status, equity = trade(model, node, q, action, equity, tier)
            if equity is None:
                break
            q, parent = action, node
        values.append((probability, status, sum(equity) if status == 'VALUE' else None))
    if any(s == 'INFEASIBLE' for _, s, _ in values):
        return 'INFEASIBLE', None
    if any(s != 'VALUE' for _, s, _ in values):
        return 'UNKNOWN', None
    return 'VALUE', sum(p*v for p, _, v in values)


def enumerate_best(model):
    nodes = model['nodes']
    choices = [n['id'] for n in nodes if n['children']]
    terminal = {n['id']:0 for n in nodes if not n['children']}
    valid, unknown, tested = [], False, 0
    for assignment in itertools.product(model['inventory_units'], repeat=len(choices)):
        policy = {**terminal, **dict(zip(choices, assignment))}
        state, value = policy_value(model, policy)
        tested += 1
        unknown |= state == 'UNKNOWN'
        if state == 'VALUE':
            valid.append((value, policy[model['root']]))
    if unknown:
        return 'UNKNOWN', None, None, tested
    if not valid:
        return 'INFEASIBLE', None, None, tested
    value = max(v for v, _ in valid)
    action = min((q for v, q in valid if v == value), key=lambda q:(abs(q), q))
    return 'VALUE', value, action, tested


def one_step(model, node, units, money):
    nodes = {n['id']:n for n in model['nodes']}
    choices = []
    unknown = False
    for q in model['inventory_units']:
        state, after = trade(model, node, units, q, money, 2)
        values = []
        if after is not None:
            for probability, child_id in node['children']:
                child = nodes[child_id]
                e = edge(model, node, child, q, after)
                if e is None:
                    values.append((Q(probability), 'UNKNOWN', None))
                else:
                    status, end = trade(model, child, q, 0, e, 2)
                    values.append((Q(probability), status, None if end is None else sum(end)))
            state = ('INFEASIBLE' if any(s == 'INFEASIBLE' for _, s, _ in values)
                     else 'UNKNOWN' if any(s == 'UNKNOWN' for _, s, _ in values) else 'VALUE')
        unknown |= state == 'UNKNOWN'
        if state == 'VALUE':
            choices.append((sum(p*v for p, _, v in values), q))
    if unknown:
        return 'UNKNOWN', None
    if not choices:
        return 'INFEASIBLE', None
    value = max(v for v, _ in choices)
    action = min((q for v, q in choices if v == value), key=lambda q:(abs(q-units), abs(q), q))
    return 'VALUE', action


def check_local_decisions(model, plan):
    for node in model['nodes']:
        row = plan['nodes'][node['id']]
        decision = row['decision']
        if row['reference_equity'] is None:
            if decision['model_action_units'] is not None:
                raise ValueError('unscored reference state produced an action')
            continue
        money, q = tuple(Q(v) for v in row['reference_equity']), row['old_q']
        if not node['children']:
            state, after = trade(model, node, q, 0, money, 2)
            expected = (state, 0 if after is not None else None)
        elif plan['mode'] == 'myopic':
            expected = one_step(model, node, q, money)
        elif plan['mode'] in ('cash','hold_long'):
            target = 0 if plan['mode'] == 'cash' else max(model['inventory_units'])
            state, after = trade(model, node, q, target, money, 2)
            expected = (state, target if after is not None else None)
        else:
            continue  #Full contingent-policy enumeration checks the dynamic policy optimum.
        if (decision['state'], decision['model_action_units']) != expected:
            raise ValueError('fixed/myopic/terminal local decision disagrees with independent rule')


def journal_chain(raw):
    previous = '0'*64
    rows = 0
    for i, line in enumerate(raw.splitlines()):
        row = json.loads(line)
        checksum = row.pop('sha256')
        encoded = json.dumps(row, sort_keys=True, separators=(',', ':')).encode()
        if row['sequence'] != i or row['previous_sha256'] != previous or hashlib.sha256(encoded).hexdigest() != checksum:
            raise ValueError('saved common journal chain changed')
        previous = checksum
        rows += 1
    return rows


def check_saved_path(model, plan, replay, saved):
    nodes = {n['id']:n for n in model['nodes']}
    money, units, parent = tuple(Q(x) for x in model['initial_capital']), 0, None
    stopped, pending = False, False
    tier = replay['replay_cost_multiple']
    for key, record in zip(saved['route'], saved['records']):
        node = nodes[key]
        if parent is not None:
            quantity = units*Q(model['base_per_unit'])
            missing = quantity != 0 and any(f is None for f in node['funding_quote_per_base'])
            pending |= missing
            money = tuple(e+s*quantity*(Q(b['reference'])-Q(a['reference']))
                          - s*quantity*(Q(f) if f is not None else 0)
                          for e, s, a, b, f in zip(money, (1, -1), parent['books'], node['books'], node['funding_quote_per_base']))
        if record['incoming_q'] != units or tuple(Q(v) for v in record['incoming_marked_equity']) != money:
            raise ValueError('shared ledger incoming equity/old inventory mismatch')
        desired = plan['nodes'][key]['decision']['model_action_units']
        if record['planned_action'] != desired or record['policy_sha256'] != plan['policy_sha256']:
            raise ValueError('cost tier switched policy')
        execute = False
        if not stopped:
            if desired is None or pending:
                stopped = True
            else:
                state, next_money = trade(model, node, units, desired, money, tier)
                if state != 'VALUE':
                    stopped = True
                else:
                    money, units, execute = next_money, desired, True
        if record['executed_model_action'] != (units if execute else None):
            raise ValueError('failed tier action was silently resized or executed')
        if record['funding_known'] == pending:
            raise ValueError('unknown funding became a known zero')
        parent = node
    if len(saved['records']) != len(saved['route']) or saved['terminal_inventory_units'] != units:
        raise ValueError('path truncated or terminal inventory changed')
    close = [friction(b, -s*units*Q(model['base_per_unit']), tier) for b, s in zip(parent['books'], (1, -1))]
    known = not pending and all(s == 'VALUE' for s, _ in close)
    diagnostic = sum(money)-sum(Q(c) for c in model['initial_capital'])-sum(v for _, v in close) if known else None
    if saved['known_liquidation_net_component'] != (None if diagnostic is None else str(diagnostic)):
        raise ValueError('known liquidation component or failed loss mismatch')
    complete = diagnostic is not None and not stopped and units == 0
    expected = diagnostic if complete else None
    if saved['conditional_net'] != (None if expected is None else str(expected)):
        raise ValueError('failed or incomplete path was scored')
    return expected


def audit(directory=LANE):
    config = verify()
    directory = Path(directory)
    result = json.loads((directory/'results.json').read_text())
    observations = json.loads(gzip.decompress((directory/'observations.json.gz').read_bytes()))
    journals = json.loads(gzip.decompress((directory/'journals.json.gz').read_bytes()))
    if result['input_identity_sha256'] != sha(LANE/'fixtures.json'):
        raise ValueError('fixed input identity mismatch')
    expected_models = {s['id']:model_mapping(make_model(config, s)) for s in config['scenarios']}
    required = set(itertools.product(expected_models, config['modes'], config['replay_cost_multiples']))
    seen, seen_journals = set(), set()
    plans = {(p['scenario'],p['plan']['mode']):p['plan'] for p in json.loads((directory/'policies.json').read_text())}
    summaries = {(r['scenario'],r['mode'],r['cost_multiple']):r for r in result['rows']}
    for name, key in (('observations.json.gz','observations_sha256'), ('journals.json.gz','journals_sha256'), ('policies.json','policies_sha256')):
        if sha(directory/name) != result[key]:
            raise ValueError('saved artifact identity changed')
    roots, references, paths_checked, journal_rows = {}, {}, 0, 0
    for row in observations:
        model, plan, replay = row['model'], row['plan'], row['replay']
        scenario = row['scenario']
        key = (scenario, plan['mode'], replay['replay_cost_multiple'])
        if key in seen or key not in required or model != expected_models[scenario]:
            raise ValueError('duplicate/unregistered case or changed model genealogy')
        seen.add(key)
        if plan != plans[(scenario, plan['mode'])]:
            raise ValueError('saved policy copies differ')
        financial = dict(plan)
        signature = financial.pop('policy_sha256')
        if hashlib.sha256(json.dumps(financial,sort_keys=True,separators=(',',':')).encode()).hexdigest() != signature:
            raise ValueError('policy identity changed')
        summary = summaries[key]
        for field in ('state','conditional_expected_net','conditional_return_on_total_capital','policy_sha256'):
            if summary[field] != replay[field]:
                raise ValueError('displayed result differs from saved replay')
        if scenario not in roots:
            roots[scenario] = enumerate_best(model)
        if plan['mode'] == 'dynamic':
            status, value, action, _ = roots[scenario]
            a = plan['assessment']
            if (a['state'], a['model_action_units'], a['conditional_terminal_equity']) != (status, action, None if value is None else str(value)):
                raise ValueError('Bellman optimum differs from exhaustive contingent-policy enumeration')
        reference_key = (scenario, plan['mode'])
        if reference_key not in references:
            check_local_decisions(model, plan)
            policy = {k:v['decision'] for k, v in plan['nodes'].items()}
            state, value = policy_value(model, policy)
            a = plan['assessment']
            if (a['state'], a['conditional_terminal_equity']) != (state, None if value is None else str(value)):
                raise ValueError('fixed2x reference policy value mismatch')
            references[reference_key] = plan['policy_sha256']
        if references[reference_key] != replay['policy_sha256']:
            raise ValueError('different policies selected at different cost tiers')
        values = []
        if [(Q(p['probability']),tuple(p['route'])) for p in replay['paths']] != list(routes(model)):
            raise ValueError('branch identity/probability changed or tail dropped')
        for p in replay['paths']:
            value = check_saved_path(model, plan, replay, p)
            values.append((Q(p['probability']), value))
            raw = journals[p['journal_archive_key']]
            if p['journal_archive_key'] in seen_journals:
                raise ValueError('same journal used as a different independent world')
            seen_journals.add(p['journal_archive_key'])
            if hashlib.sha256(raw.encode()).hexdigest() != p['journal_sha256']:
                raise ValueError('archived append-only journal identity mismatch')
            journal_rows += journal_chain(raw)
            paths_checked += 1
        if sum(p for p, _ in values) != 1:
            raise ValueError('missing/dropped rare branch')
        complete = plan['assessment']['state'] == 'VALUE' and all(v is not None for _, v in values)
        expected = sum(p*v for p, v in values) if complete else None
        if replay['conditional_expected_net'] != (None if expected is None else str(expected)):
            raise ValueError('incomplete paths renormalized or expected net wrong')
        if expected is not None and Q(replay['conditional_return_on_total_capital']) != expected/sum(Q(v) for v in model['initial_capital']):
            raise ValueError('alternative worlds or per-venue capital double counted')
    count = sum(v[3] for v in roots.values())
    if (seen != required or set(summaries) != required or len(result['rows']) != len(required)
            or seen_journals != set(journals)
            or (len(roots), len(references), len(observations), paths_checked, count) != (8,32,96,120,7000)):
        raise ValueError('incomplete fixed audit scope')
    verify()
    return {'exact_matches':True, 'root_dynamic_policy_enumerations':count,
            'reference_policies_checked':len(references), 'fixed_tier_replays_checked':len(observations),
            'alternative_world_paths_checked':paths_checked, 'journal_chain_rows_checked':journal_rows,
            'scope':'Independent rational enumeration/cash identity on supplied model; not independent forecasts, executable fills or market truth',
            'actual_order_allowed':False, 'new_prospective_paper_days':0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=LANE)
    args = parser.parse_args()
    save(args.directory/'audit.json', audit(args.directory))
    print(args.directory/'audit.json')
