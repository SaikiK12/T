"""Freeze a2x model policy, replay identical actions in the common paper ledger.

Scenario branches are alternative worlds sharing initial capital, never extra
funded accounts to pool. Missing/failed paths withhold the expected result.
This component is an offline conditional model, not prospective execution.
"""
from dataclasses import asdict
from decimal import Decimal, localcontext
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path

from lab.carry_control import Book, Controller, Model, Node
from lab.paper_account import PaperAccount, PaperEvent, CloseMark
from lab.stream_quotes import FrameClock, NS


ANCHOR = FrameClock(1_800_000_000 * NS, 100 * NS)
VENUES = (('mexc-model', 'USDT'), ('lighter-model', 'USDC'))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def decimal(value):
    """Only exact finite decimal cash is accepted by this ledger bridge."""
    value = F(value)
    denominator = value.denominator
    for prime in (2, 5):
        while denominator % prime == 0:
            denominator //= prime
    if denominator != 1:
        raise ValueError('nonterminating model cash cannot silently round into ledger evidence')
    with localcontext() as context:
        context.prec = 80
        result = Decimal(value.numerator) / Decimal(value.denominator)
    if F(result) != value:
        raise ValueError('model cash exceeds exact decimal bridge precision')
    return result


def clock(stage):
    return FrameClock(ANCHOR.utc_ns + stage * NS, ANCHOR.mono_ns + stage * NS)


def model_from_mapping(data):
    expected = {'root', 'nodes', 'horizon', 'inventory_units', 'base_per_unit',
                'initial_capital', 'maximum_loss_fraction', 'exit_capital_buffer', 'input_scope'}
    if not isinstance(data, dict) or set(data) != expected:
        raise ValueError('complete explicit conditional model schema required')
    nodes = []
    for n in data['nodes']:
        if set(n) != {'id', 'stage', 'books', 'funding_quote_per_base', 'children'}:
            raise ValueError('unknown/missing node fields; raw rates cannot stand for funding cash')
        books = tuple(Book(**b) for b in n['books'])
        nodes.append(Node(n['id'], n['stage'], books, tuple(n['funding_quote_per_base']), tuple(n['children'])))
    return Model(**{**data, 'nodes':tuple(nodes), 'inventory_units':tuple(data['inventory_units'])})


def build_plan(model, mode):
    """One reference2x policy; later cost tiers do not select new actions."""
    controller = Controller(model, cost_multiple=2, mode=mode)
    assessment = controller.assessment()
    rows = {}

    def walk(node_id, old_q, equity, inherited=None):
        node = controller.nodes[node_id]
        decision = ({'state':'UNKNOWN', 'model_action_units':None, 'reasons':[inherited],
                     'actual_order_allowed':False} if equity is None else controller.decision(node_id, old_q, equity))
        q = decision['model_action_units']
        rows[node_id] = {'decision':decision, 'old_q':old_q,
                         'reference_equity':None if equity is None else [str(x) for x in equity]}
        after = None
        if q is not None and equity is not None:
            _, after = controller.trade(node, old_q, q, equity)
        for _, child_id in node.children:
            child_equity = None if after is None else controller.edge(node, controller.nodes[child_id], q, after)
            walk(child_id, q if q is not None else old_q, child_equity, 'reference_parent_state_unscored')

    walk(model.root, 0, model.initial_capital)
    result = {'mode':mode, 'planning_cost_multiple':2, 'assessment':assessment, 'nodes':rows,
              'model_identity':digest(model_mapping(model)), 'market_admissible':False,
              'scope':'Conditional2x reference-state policy, same node actions at1x/2x/3x; not a validation winner'}
    return {**result, 'policy_sha256':digest(result)}


def model_mapping(model):
    """Canonical exact identity; Fraction strings stay exact across JSON."""
    def clean(value):
        if isinstance(value, F):
            return str(value)
        if isinstance(value, (tuple, list)):
            return [clean(x) for x in value]
        if isinstance(value, dict):
            return {k:clean(v) for k, v in value.items()}
        return value
    return clean(asdict(model))


def paths(model):
    lookup = {n.id:n for n in model.nodes}

    def walk(key, probability, route):
        node = lookup[key]
        route = route + (key,)
        if not node.children:
            yield probability, route
        for p, child in node.children:
            yield from walk(child, probability * p, route)
    return tuple(walk(model.root, F(1), ()))


def replay(model, plan, cost_multiple, directory):
    if plan['model_identity'] != digest(model_mapping(model)) or plan['planning_cost_multiple'] != 2:
        raise ValueError('fixed policy/model identity mismatch')
    expected = dict(plan)
    signature = expected.pop('policy_sha256')
    if digest(expected) != signature:
        raise ValueError('policy changed after identity binding')
    controller = Controller(model, cost_multiple=cost_multiple, mode=plan['mode'])
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    balances = {k:decimal(c) for k, c in zip(VENUES, model.initial_capital)}
    results = []
    for probability, route in paths(model):
        label = digest([plan['policy_sha256'], cost_multiple, route])
        journal = directory / (label + '.jsonl')
        if journal.exists():
            raise ValueError('existing model path journal retained')
        account = PaperAccount(balances, ANCHOR, journal_path=journal)
        q, parent, failures, records = 0, None, [], []
        stopped = False
        for key in route:
            node = controller.nodes[key]
            at = clock(node.stage)
            # The edge belongs to the inventory held BEFORE this node's trade.
            if parent is not None:
                for i, ((venue, asset), sign) in enumerate(zip(VENUES, (1, -1))):
                    f = node.funding_quote_per_base[i]
                    amount = (-sign * q * model.base_per_unit * f if f is not None else F(0) if q == 0 else None)
                    if model.input_scope != 'invented_scenario_fixture':
                        amount = None
                    event = PaperEvent('fund:' + key + ':' + str(i), 'funding', venue, asset, 'fixture-base',
                                       at.utc_ns, at, 'invented-normalized-funding-model',
                                       amount=None if amount is None else decimal(amount))
                    if account.post(event, at.mono_ns)['status'] != 'applied':
                        raise ValueError('common funding event rejected')
            equity = []
            known = not account.pending and not any(account.reconciliation.values())
            for (venue, asset), book in zip(VENUES, node.books):
                held, entry = account.positions.get((venue, asset, 'fixture-base'), (Decimal(0), Decimal(0)))
                equity.append(F(account.cash[(venue, asset)]) + F(held) * (book.reference - F(entry)))
            intended = plan['nodes'][key]['decision']['model_action_units']
            event_record = {'node':key, 'planned_action':intended, 'incoming_q':q,
                            'incoming_marked_equity':[str(x) for x in equity], 'funding_known':known,
                            'policy_sha256':plan['policy_sha256'], 'executed_model_action':None}
            if not stopped:
                if intended is None or not known:
                    failures.append(key + ':policy_or_cash_unknown')
                    stopped = True
                else:
                    state, _ = controller.trade(node, q, intended, tuple(equity))
                    if state != 'VALUE':
                        failures.append(key + ':' + state + ':fixed_policy_not_reoptimized')
                        stopped = True
                    else:
                        delta = (intended - q) * model.base_per_unit
                        for i, ((venue, asset), sign) in enumerate(zip(VENUES, (1, -1))):
                            signed = sign * delta
                            if not signed:
                                continue
                            state, _, price, fee = controller.execution(node.books[i], signed)
                            if state != 'VALUE':
                                raise ValueError('guarded model execution mismatch')
                            event = PaperEvent('fill:' + key + ':' + str(i), 'fill', venue, asset, 'fixture-base',
                                               at.utc_ns, at, 'invented-bounded-taker-model',
                                               quantity=decimal(signed), price=decimal(price), fee=decimal(fee),
                                               reference_mid=decimal(node.books[i].reference))
                            if account.post(event, at.mono_ns)['status'] != 'applied':
                                raise ValueError('guarded common-account fill rejected')
                        q = intended
                        event_record['executed_model_action'] = q
            records.append(event_record)
            parent = node
        end = controller.nodes[route[-1]]
        at = clock(end.stage)
        marks = []
        for i, (venue, asset) in enumerate(VENUES):
            held, _ = account.positions.get((venue, asset, 'fixture-base'), (Decimal(0), Decimal(0)))
            if not held:
                continue
            state, _, price, fee = controller.execution(end.books[i], -F(held))
            if state == 'VALUE':
                marks.append(CloseMark(venue, asset, 'fixture-base', held, decimal(abs(F(held)) * price),
                                       decimal(fee), at, at.utc_ns, 'invented-prudent-terminal-quote'))
        snapshot = account.snapshot(at.mono_ns, marks)
        reopened = PaperAccount(balances, ANCHOR, journal_path=journal)
        if reopened.snapshot(at.mono_ns, marks) != snapshot:
            raise ValueError('durable common account replay drift')
        complete = all(a['nav'] is not None for a in snapshot['accounts'])
        diagnostic_net = (sum(F(a['nav']) - F(a['initial_cash']) - F(a['external_capital_flows'])
                              for a in snapshot['accounts']) if complete else None)
        if q != 0:
            failures.append('mandatory_terminal_inventory_not_flat')
        if model.input_scope != 'invented_scenario_fixture':
            failures.append('actual_inputs_and_forecasts_unverified')
        scored = diagnostic_net if complete and not failures else None
        results.append({'probability':str(probability), 'route':list(route), 'records':records,
                        'state':'COMPLETE_CONDITIONAL_MODEL' if scored is not None else 'UNSCORED',
                        'failures':failures, 'conditional_net':None if scored is None else str(scored),
                        'known_liquidation_net_component':None if diagnostic_net is None else str(diagnostic_net),
                        'terminal_inventory_units':q, 'snapshot':snapshot,
                        'journal':journal.name, 'journal_sha256':hashlib.sha256(journal.read_bytes()).hexdigest(),
                        'journal_reopened_identical':True})
    if sum(F(r['probability']) for r in results) != 1:
        raise ValueError('complete path probabilities must sum to1; no dropped tail')
    complete = (plan['assessment']['state'] == 'VALUE'
                and all(p['conditional_net'] is not None for p in results))
    net = sum(F(p['probability']) * F(p['conditional_net']) for p in results) if complete else None
    return {'policy_sha256':plan['policy_sha256'], 'mode':plan['mode'], 'planning_cost_multiple':2,
            'replay_cost_multiple':cost_multiple, 'paths':results,
            'conditional_expected_net':None if net is None else str(net),
            'conditional_return_on_total_capital':None if net is None else str(net / sum(model.initial_capital)),
            'state':'COMPLETE_CONDITIONAL_MODEL' if complete else 'INCONCLUSIVE',
            'same_actions_no_tier_reoptimization':True, 'alternative_worlds_not_pooled_capital':True,
            'actual_order_allowed':False, 'new_prospective_paper_days':0,
            'executable_market_expected_net_return':None}
