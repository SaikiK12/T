"""Finite-deadline conditional carry control; no forecast calibration or orders.

State equity is marked to each model reference price. Execution drag and fees
are paid once, funding uses OLD held inventory on each edge, and terminal
inventory must be closed. Exact rational arithmetic avoids hidden tolerances.
"""
from dataclasses import dataclass
from fractions import Fraction as F


def rational(value):
    if type(value) not in (int, str, F):
        raise ValueError('explicit exact integer/string/fraction required')
    try:
        number = F(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError('finite exact rational required') from exc
    if abs(number) > 10**12 or number.denominator > 10**12:
        raise ValueError('rational outside bounded model domain')
    return number


@dataclass(frozen=True)
class Book:
    reference: F
    bid: F | None
    ask: F | None
    fee_fraction: F | None
    session: str
    buy_capacity_base: F | None = None
    sell_capacity_base: F | None = None
    minimum_base: F | None = None
    minimum_notional: F | None = None

    def __post_init__(self):
        if self.reference is None:
            raise ValueError('model reference is required, not an inferred missing price')
        for name in ('reference', 'bid', 'ask', 'fee_fraction', 'buy_capacity_base',
                     'sell_capacity_base', 'minimum_base', 'minimum_notional'):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, rational(value))
        if self.reference <= 0 or self.session not in ('open', 'closed', 'unknown'):
            raise ValueError('positive model reference and explicit session required')
        if (self.bid is None) != (self.ask is None):
            raise ValueError('no fabricated missing side')
        if self.bid is not None and not 0 < self.bid <= self.reference <= self.ask:
            raise ValueError('ordered positive quote required')
        if self.bid is not None and self.reference != (self.bid + self.ask) / 2:
            raise ValueError('model reference must equal supplied quote midpoint')
        if self.fee_fraction is not None and not 0 <= self.fee_fraction <= F(1, 10):
            raise ValueError('explicit bounded nonnegative fee required')
        if any(v is not None and v < 0 for v in (self.buy_capacity_base, self.sell_capacity_base,
                                                self.minimum_base, self.minimum_notional)):
            raise ValueError('declared nonnegative capacity/minima required')


@dataclass(frozen=True)
class Node:
    id: str
    stage: int
    books: tuple
    funding_quote_per_base: tuple
    children: tuple

    def __post_init__(self):
        if not isinstance(self.id, str) or not self.id or len(self.id) > 64 or type(self.stage) is not int:
            raise ValueError('bounded model node identity required')
        if len(self.books) != 2 or any(not isinstance(b, Book) for b in self.books):
            raise ValueError('two separately funded model venues required')
        object.__setattr__(self, 'books', tuple(self.books))
        if len(self.funding_quote_per_base) != 2:
            raise ValueError('two normalized funding-cash inputs required, never raw rates')
        object.__setattr__(self, 'funding_quote_per_base', tuple(None if x is None else rational(x)
                                                               for x in self.funding_quote_per_base))
        object.__setattr__(self, 'children', tuple((rational(p), child) for p, child in self.children))
        if self.children and (any(p <= 0 for p, _ in self.children) or sum(p for p, _ in self.children) != 1):
            raise ValueError('positive complete probabilities must sum exactly to1; no renormalization')


@dataclass(frozen=True)
class Model:
    root: str
    nodes: tuple
    horizon: int
    inventory_units: tuple
    base_per_unit: F
    initial_capital: tuple
    maximum_loss_fraction: F
    exit_capital_buffer: F
    input_scope: str

    def __post_init__(self):
        object.__setattr__(self, 'nodes', tuple(self.nodes))
        object.__setattr__(self, 'inventory_units', tuple(self.inventory_units))
        if any(not isinstance(n, Node) for n in self.nodes):
            raise ValueError('typed scenario nodes required')
        if type(self.horizon) is not int or not 1 <= self.horizon <= 4 or not 1 <= len(self.nodes) <= 31:
            raise ValueError('finite horizon1..4 and <=31nodes required')
        ids = [n.id for n in self.nodes]
        if len(ids) != len(set(ids)) or self.root not in ids:
            raise ValueError('unique complete node identities required')
        lookup = {n.id:n for n in self.nodes}
        reached, parents = set(), {}

        def visit(key, stage):
            if key not in lookup or lookup[key].stage != stage:
                raise ValueError('missing/gapped stage or cycle')
            n = lookup[key]
            reached.add(key)
            if bool(n.children) != (stage < self.horizon) or len(n.children) > 2:
                raise ValueError('common mandatory terminal stage and <=2children required')
            for _, child in n.children:
                parents[child] = parents.get(child, 0) + 1
                if parents[child] > 1:
                    raise ValueError('explicit scenario tree, not shared/duplicated child paths')
                visit(child, stage + 1)
        visit(self.root, 0)
        if reached != set(ids):
            raise ValueError('unreachable model nodes retained as an error')
        if (not 1 <= len(self.inventory_units) <= 5 or len(set(self.inventory_units)) != len(self.inventory_units)
                or 0 not in self.inventory_units or any(type(q) is not int or abs(q) > 2 for q in self.inventory_units)):
            raise ValueError('<=5fixed integer inventory choices in[-2,2], including cash')
        object.__setattr__(self, 'base_per_unit', rational(self.base_per_unit))
        object.__setattr__(self, 'initial_capital', tuple(rational(v) for v in self.initial_capital))
        object.__setattr__(self, 'maximum_loss_fraction', rational(self.maximum_loss_fraction))
        object.__setattr__(self, 'exit_capital_buffer', rational(self.exit_capital_buffer))
        if not 0 < self.base_per_unit <= 1 or len(self.initial_capital) != 2 or min(self.initial_capital) <= 0:
            raise ValueError('positive bounded base unit and segregated capital required')
        if not 0 <= self.maximum_loss_fraction < 1 or not 0 <= self.exit_capital_buffer <= 1:
            raise ValueError('fixed loss limit and capital buffer required')
        if self.input_scope not in ('invented_scenario_fixture', 'unverified_public_model'):
            raise ValueError('no implicit calibrated/market-admissible model')


@dataclass(frozen=True)
class Outcome:
    state: str
    terminal_equity: F | None
    action: int | None
    reasons: tuple = ()


class ModelLimit(ValueError):
    pass


class Controller:
    MODES = ('dynamic', 'myopic', 'cash', 'hold_long')

    def __init__(self, model, *, cost_multiple=1, mode='dynamic'):
        if not isinstance(model, Model) or type(cost_multiple) is not int or cost_multiple not in (1, 2, 3) or mode not in self.MODES:
            raise ValueError('finite typed model, fixed1x/2x/3x tier and registered control required')
        if mode == 'hold_long' and max(model.inventory_units) <= 0:
            raise ValueError('registered hold-long control needs positive inventory')
        self.model, self.multiple, self.mode = model, cost_multiple, mode
        self.nodes = {n.id:n for n in model.nodes}
        self.hold_target = max(model.inventory_units)
        self.cache = {}
        self.evaluated_states = 0

    def execution(self, book, signed_base):
        """Stress quote half-spread and fee RATE by the same fixed tier.

        Fee is charged on the stressed fill notional. Spread is embedded in
        fill price; drag below is a NAV identity, not another ledger payment.
        """
        signed_base = rational(signed_base)
        if not signed_base:
            return 'VALUE', F(0), None, F(0)
        if book.session == 'closed':
            return 'INFEASIBLE', None, None, None
        capacity = book.buy_capacity_base if signed_base > 0 else book.sell_capacity_base
        if (book.session == 'unknown' or book.bid is None or book.fee_fraction is None
                or capacity is None or book.minimum_base is None or book.minimum_notional is None):
            return 'UNKNOWN', None, None, None
        side = 1 if signed_base > 0 else -1
        price = book.reference + side * self.multiple * (book.ask - book.bid) / 2
        if price <= 0:
            return 'INFEASIBLE', None, None, None
        if (abs(signed_base) > capacity or abs(signed_base) < book.minimum_base
                or abs(signed_base) * price < book.minimum_notional):
            return 'INFEASIBLE', None, None, None
        fee = abs(signed_base) * price * book.fee_fraction * self.multiple
        drag = signed_base * (price - book.reference)
        return 'VALUE', drag + fee, price, fee

    def trade(self, node, old_q, new_q, equity):
        if any(type(q) is not int or q not in self.model.inventory_units for q in (old_q, new_q)):
            raise ValueError('registered integer inventory required')
        if not self.feasible(node, old_q, equity):
            return 'INFEASIBLE', None
        delta = (new_q - old_q) * self.model.base_per_unit
        executions = tuple(self.execution(book, sign * delta) for sign, book in zip((1, -1), node.books))
        if any(x[0] == 'INFEASIBLE' for x in executions):
            return 'INFEASIBLE', None
        if any(x[0] == 'UNKNOWN' for x in executions):
            return 'UNKNOWN', None
        next_equity = tuple(e - x[1] for e, x in zip(equity, executions))
        if not self.feasible(node, new_q, next_equity):
            return 'INFEASIBLE', None
        return 'VALUE', next_equity

    def feasible(self, node, q, equity):
        """Both incoming and outgoing inventory must fit EACH model account.

        An immediate close cannot erase an already breached margin/loss state.
        Only declared model nodes are checked; intraperiod liquidation is not
        certified by this discrete scenario tree.
        """
        return all(e >= initial * (1 - self.model.maximum_loss_fraction)
                   and e >= abs(q * self.model.base_per_unit) * book.reference * (1 + self.model.exit_capital_buffer)
                   for e, initial, book in zip(equity, self.model.initial_capital, node.books))

    def edge(self, parent, child, q, equity):
        quantity = q * self.model.base_per_unit
        if quantity and any(x is None for x in child.funding_quote_per_base):
            return None
        return tuple(e + sign * quantity * (b.reference - a.reference)
                     - sign * quantity * (funding if funding is not None else 0)
                     for e, sign, a, b, funding in zip(equity, (1, -1), parent.books, child.books,
                                                       child.funding_quote_per_base))

    def terminal(self, node, old_q, equity):
        state, after = self.trade(node, old_q, 0, equity)
        return Outcome(state, sum(after) if after is not None else None, 0 if after is not None else None,
                       () if after is not None else ('terminal_close_or_risk_unavailable',))

    @staticmethod
    def choose(choices, old_q):
        if any(r.state == 'UNKNOWN' for r in choices.values()):
            return Outcome('UNKNOWN', None, None, ('a_required_candidate_value_is_unknown',))
        valid = {q:r for q, r in choices.items() if r.state == 'VALUE'}
        if not valid:
            return Outcome('INFEASIBLE', None, None, ('no_feasible_registered_action',))
        q = min(valid, key=lambda q:(-valid[q].terminal_equity, abs(q - old_q), abs(q), q))
        return Outcome('VALUE', valid[q].terminal_equity, q)

    def candidate(self, node, old_q, q, equity, *, one_step=False):
        state, after = self.trade(node, old_q, q, equity)
        if after is None:
            return Outcome(state, None, None, ('trade_cost_session_or_segregated_risk',))
        futures = []
        for probability, child_id in node.children:
            child = self.nodes[child_id]
            next_equity = self.edge(node, child, q, after)
            if next_equity is None:
                futures.append((probability, Outcome('UNKNOWN', None, None, ('normalized_funding_cash_missing',))))
            else:
                future = self.terminal(child, q, next_equity) if one_step else self.solve(child_id, q, next_equity)
                futures.append((probability, future))
        if any(r.state == 'INFEASIBLE' for _, r in futures):
            return Outcome('INFEASIBLE', None, None, ('positive_probability_branch_infeasible',))
        if any(r.state == 'UNKNOWN' for _, r in futures):
            return Outcome('UNKNOWN', None, None, ('positive_probability_branch_unknown',))
        return Outcome('VALUE', sum(p * r.terminal_equity for p, r in futures), q)

    def solve(self, node_id=None, old_q=0, equity=None):
        node_id = self.model.root if node_id is None else node_id
        equity = self.model.initial_capital if equity is None else tuple(rational(e) for e in equity)
        if (node_id not in self.nodes or type(old_q) is not int
                or old_q not in self.model.inventory_units or len(equity) != 2):
            raise ValueError('declared node,inventory and two exact equities required')
        key = (node_id, old_q, equity)
        if key in self.cache:
            return self.cache[key]
        if self.evaluated_states >= 20000:
            raise ModelLimit('finite registered compute-state budget exceeded')
        self.evaluated_states += 1
        node = self.nodes[node_id]
        if not node.children:
            result = self.terminal(node, old_q, equity)
        elif self.mode in ('cash', 'hold_long'):
            q = 0 if self.mode == 'cash' else self.hold_target
            result = self.candidate(node, old_q, q, equity)
        elif self.mode == 'myopic':
            pick = self.choose({q:self.candidate(node, old_q, q, equity, one_step=True)
                                for q in self.model.inventory_units}, old_q)
            result = pick if pick.action is None else self.candidate(node, old_q, pick.action, equity)
        else:
            result = self.choose({q:self.candidate(node, old_q, q, equity)
                                  for q in self.model.inventory_units}, old_q)
        self.cache[key] = result
        return result

    def decision(self, node_id, old_q, equity):
        """Separate a causal local decision from its full-policy outcome.

        In particular, fixed-hold can have a known initial intention and later
        fail its terminal contract. That future failure must remain visible;
        it must not be rewritten as a decision to stay flat from the start.
        """
        if node_id not in self.nodes or type(old_q) is not int or old_q not in self.model.inventory_units:
            raise ValueError('registered model state required')
        equity = tuple(rational(e) for e in equity)
        if len(equity) != 2:
            raise ValueError('two separate model equities required')
        node = self.nodes[node_id]
        if not node.children:
            value = self.terminal(node, old_q, equity)
        elif self.mode == 'dynamic':
            value = self.solve(node_id, old_q, equity)
        elif self.mode == 'myopic':
            value = self.choose({q:self.candidate(node, old_q, q, equity, one_step=True)
                                 for q in self.model.inventory_units}, old_q)
        else:
            q = 0 if self.mode == 'cash' else self.hold_target
            state, _ = self.trade(node, old_q, q, equity)
            value = Outcome(state, None, q if state == 'VALUE' else None,
                            () if state == 'VALUE' else ('local_fixed_control_cannot_execute',))
        return {'state': value.state, 'model_action_units': value.action,
                'reasons': list(value.reasons), 'actual_order_allowed': False}

    def assessment(self):
        result = self.solve()
        return {'state': result.state, 'model_action_units': result.action,
                'conditional_terminal_equity': None if result.terminal_equity is None else str(result.terminal_equity),
                'conditional_expected_net': None if result.terminal_equity is None else str(result.terminal_equity - sum(self.model.initial_capital)),
                'reasons': list(result.reasons), 'mode': self.mode, 'cost_multiple': self.multiple,
                'input_scope': self.model.input_scope, 'calibrated_forecasts_verified': False,
                'executable_market_expectancy_verified': False, 'actual_order_allowed': False,
                'new_prospective_paper_days': 0}
