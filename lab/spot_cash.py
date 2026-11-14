"""Append-only simulated SPOT cash/inventory, separate from futures collateral.

Buys spend quote principal; sells consume owned base. Quote/base commissions
are applied once, third-token or missing commissions remain pending. Exact
rationals describe supplied model fills, not exchange rounding or real orders.
"""
from dataclasses import dataclass, asdict
from decimal import Decimal
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path

from lab.acquisition_budget import _locked, _read_records, _append_record
from lab.funding_values import clock_known
from lab.paper_account import number, text
from lab.stream_quotes import FrameClock, NS


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


@dataclass(frozen=True)
class SpotEvent:
    event_id: str
    kind: str
    market: str
    occurred_ns: int
    clock: FrameClock
    source_identity: str
    quantity: Decimal | None = None
    price: Decimal | None = None
    fee_amount: Decimal | None = None
    fee_asset: str | None = None
    amount: Decimal | None = None
    resolves: str | None = None
    simulation_only: bool = True

    def __post_init__(self):
        for value in (self.event_id, self.market, self.source_identity):
            text(value)
        if self.simulation_only is not True or self.kind not in ('fill', 'fee_resolution', 'capital_change'):
            raise ValueError('explicit supported simulated spot event required; no funding credit on spot')
        if type(self.occurred_ns) is not int or self.occurred_ns < 0 or not isinstance(self.clock, FrameClock):
            raise ValueError('separate economic/receive clocks required')
        if self.occurred_ns > self.clock.utc_ns:
            raise ValueError('economic event cannot follow receipt')
        for name in ('quantity', 'price', 'fee_amount', 'amount'):
            v = getattr(self, name)
            if v is not None:
                if type(v) not in (str,int,Decimal):
                    raise ValueError('explicit decimal string/integer/Decimal required')
                object.__setattr__(self, name, number(v, positive=name == 'price', nonnegative=name == 'fee_amount'))
        if self.fee_asset is not None:
            text(self.fee_asset)
        if self.kind == 'fill':
            if self.quantity is None or not self.quantity or self.price is None or self.amount is not None or self.resolves is not None:
                raise ValueError('signed base fill/quote price required; no supplied principal cash override')
        elif self.quantity is not None or self.price is not None:
            raise ValueError('fill-only quantity/price')
        if self.kind == 'fee_resolution':
            text(self.resolves)
            if self.fee_amount is None or self.fee_asset is None or self.amount is not None:
                raise ValueError('explicit fee amount/asset and target required')
        elif self.resolves is not None:
            raise ValueError('resolution target only on fee resolution')
        if self.kind == 'capital_change':
            if self.amount is None or self.fee_amount is not None or self.fee_asset is not None:
                raise ValueError('explicit external quote flow, no fill/fee fields')

    def mapping(self):
        result = asdict(self)
        for name in ('quantity', 'price', 'fee_amount', 'amount'):
            if result[name] is not None:
                result[name] = str(result[name])
        return result

    @classmethod
    def from_mapping(cls, value):
        if (not isinstance(value,dict) or value.get('simulation_only') is not True
                or set(value)-set(cls.__dataclass_fields__)):
            raise ValueError('explicit typed simulation-only spot mapping required')
        value = dict(value)
        value['clock'] = FrameClock(**value['clock'])
        for name in ('quantity', 'price', 'fee_amount', 'amount'):
            if value.get(name) is not None:
                if type(value[name]) not in (str,int,Decimal):
                    raise ValueError('exact decimal event mapping required')
                #Event inputs must remain finite decimals, not rounded fractions.
                value[name] = Decimal(value[name])
        return cls(**value)


@dataclass(frozen=True)
class SpotMark:
    market: str
    inventory_consumed: Decimal
    quote_proceeds_before_quote_fee: Decimal
    estimated_quote_fee: Decimal | None
    clock: FrameClock
    source_time_ns: int | None
    source_unit_verified: bool
    base_fee_included_in_consumed_inventory: bool
    source_identity: str

    def __post_init__(self):
        text(self.market);text(self.source_identity)
        object.__setattr__(self, 'inventory_consumed', number(self.inventory_consumed, positive=True))
        object.__setattr__(self, 'quote_proceeds_before_quote_fee', number(self.quote_proceeds_before_quote_fee, nonnegative=True))
        if self.estimated_quote_fee is not None:
            object.__setattr__(self, 'estimated_quote_fee', number(self.estimated_quote_fee, nonnegative=True))
        if (not isinstance(self.clock, FrameClock) or type(self.source_unit_verified) is not bool
                or type(self.base_fee_included_in_consumed_inventory) is not bool
                or (self.source_time_ns is not None and type(self.source_time_ns) is not int)):
            raise ValueError('explicit source/clock/consumed-inventory declarations required')


class SpotCashAccount:
    def __init__(self, venue, quote_asset, initial_cash, markets, anchor, *, journal_path=None):
        text(venue);text(quote_asset)
        if not isinstance(anchor, FrameClock) or not isinstance(markets, dict) or not markets:
            raise ValueError('explicit spot base/quote mapping and common anchor required')
        for market, base in markets.items():
            text(market);text(base)
            if base == quote_asset:
                raise ValueError('distinct base and quote asset required')
        if len(set(markets.values())) != len(markets):
            raise ValueError('cross-market fungibility requires a separate explicit wallet contract')
        self.venue,self.quote_asset,self.markets,self.anchor = venue,quote_asset,dict(markets),anchor
        self.initial = F(number(initial_cash, nonnegative=True))
        self.journal_path = None if journal_path is None else Path(journal_path)
        self.config = {'kind':'spot_cash_model_config', 'venue':venue, 'quote_asset':quote_asset,
                       'initial_cash':str(self.initial), 'markets':self.markets, 'anchor':asdict(anchor),
                       'simulation_only':True}
        self._reset()
        if self.journal_path is not None:
            with _locked(self.journal_path) as handle:
                self._load(handle)

    def _reset(self):
        self.cash,self.flows,self.realized = self.initial,F(0),F(0)
        self.holdings = {m:F(0) for m in self.markets}
        self.cost_pool = dict(self.holdings)
        self.fees,self.pending,self.seen,self.last_fill = {},{},{},{}
        self.reconciliation,self.risk_events,self.attempts = set(),set(),[]
        self.last_asof = -1

    def _load(self, handle):
        rows = _read_records(handle)
        if not rows:
            _append_record(handle, rows, self.config)
        elif rows[0]['event'] != self.config:
            raise ValueError('existing spot capital/market identity cannot reset')
        self._reset()
        for row in rows[1:]:
            e = row['event']
            if e['kind'] != 'spot_model_attempt':
                raise ValueError('unknown spot journal operation')
            self._apply(SpotEvent.from_mapping(e['payload']), e['asof'])
        return rows

    def post(self, event, asof):
        if not isinstance(event, SpotEvent) or type(asof) is not int or asof < 0:
            raise ValueError('typed spot event and nonnegative as-of required')
        if self.journal_path is None:
            return self._apply(event, asof)
        with _locked(self.journal_path) as handle:
            rows = self._load(handle)
            _append_record(handle, rows, {'kind':'spot_model_attempt','payload':event.mapping(),'asof':asof})
            return self._apply(event, asof)

    def _apply(self, event, asof):
        payload = event.mapping();payload.pop('clock')
        for name in ('quantity','price','fee_amount','amount'):
            if payload[name] is not None:
                payload[name] = str(F(payload[name]))
        signature = hashlib.sha256(canonical(payload).encode()).hexdigest()
        reasons = []
        if asof < self.last_asof:
            reasons.append('asof_regressed')
        if not clock_known(event.clock, asof, self.anchor):
            reasons.append('future_receipt_or_clock_step')
        if not self.anchor.utc_ns <= event.occurred_ns <= self.anchor.utc_ns+asof-self.anchor.mono_ns:
            reasons.append('economic_event_outside_known_baseline')
        if event.kind != 'capital_change' and event.market not in self.markets:
            reasons.append('unknown_spot_market')
        status = 'rejected' if reasons else 'applied'
        if not reasons and event.event_id in self.seen:
            status = 'duplicate' if self.seen[event.event_id] == signature else 'conflicting_revision'
            if status == 'conflicting_revision':
                self.reconciliation.add(event.event_id)
        elif not reasons:
            if event.kind == 'fill':
                status, reasons = self._fill(event)
            elif event.kind == 'fee_resolution':
                status, reasons = self._resolve(event)
            elif self.pending or self.reconciliation or self.cash+F(event.amount) < 0:
                status,reasons = 'rejected',['unknown_cash_or_unfunded_withdrawal']
            else:
                self.cash += F(event.amount);self.flows += F(event.amount)
            if status == 'applied':
                self.seen[event.event_id] = signature
                if self.cash < 0:
                    self.risk_events.add(event.event_id+':negative_quote_cash')
        self.last_asof = max(self.last_asof, asof)
        result = {'event_id':event.event_id, 'status':status, 'reasons':reasons, 'simulation_only':True}
        self.attempts.append(result)
        return result

    def _fill(self, e):
        if self.pending or self.reconciliation:
            return 'rejected',['fee_or_financial_reconciliation_pending']
        if e.occurred_ns < self.last_fill.get(e.market, -1):
            self.reconciliation.add(e.event_id)
            return 'rejected',['late_fill_order_requires_reconciliation']
        q, price = F(e.quantity), F(e.price)
        if q > 0 and self.risk_events:
            return 'rejected',['historical_cash_deficit_blocks_new_spot_buys']
        base = self.markets[e.market]
        known = e.fee_amount is not None and e.fee_asset in (self.quote_asset, base)
        fb = F(e.fee_amount) if known and e.fee_asset == base else F(0)
        fq = F(e.fee_amount) if known and e.fee_asset == self.quote_asset else F(0)
        owned = self.holdings[e.market]
        if q > 0 and (self.cash < q*price+fq or owned+q < fb):
            return 'rejected',['spot_buy_not_funded']
        if q < 0 and owned < -q+fb:
            return 'rejected',['spot_short_or_base_fee_borrow_forbidden']
        basis = self.cost_pool[e.market]/owned if owned else F(0)
        if q > 0:
            self.cash -= q*price+fq
            self.holdings[e.market] += q-fb
            self.cost_pool[e.market] += q*price+fq
        else:
            consumed = -q+fb
            self.cash += -q*price-fq
            self.holdings[e.market] -= consumed
            self.cost_pool[e.market] -= basis*consumed
            self.realized += -q*price-fq-basis*consumed
        if known:
            self.fees[e.fee_asset] = self.fees.get(e.fee_asset,F(0))+F(e.fee_amount)
        else:
            self.pending[e.event_id] = {'market':e.market,'quantity':q,'basis':basis,
                                        'occurred_ns':e.occurred_ns,'declared_asset':e.fee_asset,
                                        'declared_amount':None if e.fee_amount is None else F(e.fee_amount)}
        self.last_fill[e.market] = e.occurred_ns
        if not self.holdings[e.market] and self.cost_pool[e.market]:
            self.realized -= self.cost_pool[e.market]
            self.cost_pool[e.market] = F(0)
        return 'applied',[]

    def _resolve(self, e):
        pending = self.pending.get(e.resolves)
        if pending is None or pending['market'] != e.market or e.occurred_ns < pending['occurred_ns']:
            return 'rejected',['fee_resolution_target_mismatch']
        base = self.markets[e.market]
        if ((pending['declared_amount'] is not None and F(e.fee_amount) != pending['declared_amount'])
                or (pending['declared_asset'] is not None and e.fee_asset != pending['declared_asset'])):
            self.reconciliation.add(e.event_id)
            return 'rejected',['reported_fee_revision_requires_reconciliation']
        if (e.fee_asset not in (base,self.quote_asset)
                or (pending['declared_amount'] is not None and pending['declared_asset'] not in (None,base,self.quote_asset))):
            return 'rejected',['third_fee_wallet_or_conversion_unmodeled']
        fee = F(e.fee_amount)
        if e.fee_asset == base and fee > self.holdings[e.market]:
            return 'rejected',['unfunded_base_fee_resolution']
        if e.fee_asset == self.quote_asset:
            self.cash -= fee
            if pending['quantity'] > 0:
                self.cost_pool[e.market] += fee
            else:
                self.realized -= fee
        else:
            self.holdings[e.market] -= fee
            if pending['quantity'] < 0:
                self.cost_pool[e.market] -= pending['basis']*fee
                self.realized -= pending['basis']*fee
        self.fees[e.fee_asset] = self.fees.get(e.fee_asset,F(0))+fee
        del self.pending[e.resolves]
        if not self.holdings[e.market] and self.cost_pool[e.market]:
            self.realized -= self.cost_pool[e.market]
            self.cost_pool[e.market] = F(0)
        return 'applied',[]

    def snapshot(self, asof, marks=()):
        if self.journal_path is not None:
            with _locked(self.journal_path) as handle:
                self._load(handle)
        if type(asof) is not int or asof < self.last_asof:
            raise ValueError('snapshot cannot backdate financial state')
        lookup = {}
        for mark in marks:
            if not isinstance(mark, SpotMark) or mark.market in lookup:
                raise ValueError('one typed liquidation mark per spot market required')
            lookup[mark.market] = mark
        reasons = []
        if self.pending:reasons.append('fee_amount_asset_or_conversion_unknown')
        if self.reconciliation:reasons.append('financial_revision_or_order_unreconciled')
        liquidation = F(0)
        for market, quantity in self.holdings.items():
            if not quantity:continue
            m = lookup.get(market)
            if m is None:
                reasons.append(market+':liquidation_mark_missing');continue
            age = None if m.source_time_ns is None else self.anchor.utc_ns+asof-self.anchor.mono_ns-m.source_time_ns
            if (F(m.inventory_consumed) != quantity or not m.base_fee_included_in_consumed_inventory
                    or not clock_known(m.clock,asof,self.anchor) or not 0 <= asof-m.clock.mono_ns <= NS
                    or not m.source_unit_verified or age is None or not -100_000_000 <= age <= 2*NS
                    or m.estimated_quote_fee is None):
                reasons.append(market+':liquidation_quantity_fee_or_clock_unverified');continue
            liquidation += F(m.quote_proceeds_before_quote_fee)-F(m.estimated_quote_fee)
        complete = not reasons
        nav = self.cash+liquidation if complete else None
        return {'simulation_only':True,'venue':self.venue,'quote_asset':self.quote_asset,
                'initial_cash':str(self.initial),'cash_known_component':str(self.cash),
                'cash':str(self.cash) if not self.pending and not self.reconciliation else None,
                'spot_principal_is_spent_cash':True,'spot_inventory_not_reserved_again':True,
                'holdings':{m:str(q) for m,q in self.holdings.items()},
                'holdings_available':None if self.pending or self.reconciliation else {m:str(q) for m,q in self.holdings.items()},
                'cost_pool_quote':{m:str(c) for m,c in self.cost_pool.items()},
                'realized_net_allocated_known_component':str(self.realized),
                'fees_by_asset_diagnostic_not_subtracted_again':{a:str(v) for a,v in self.fees.items()},
                'external_quote_flows':str(self.flows),'nav':None if nav is None else str(nav),
                'net_pnl':None if nav is None else str(nav-self.initial-self.flows),
                'reasons':sorted(set(reasons)),'pending_fee_events':list(self.pending),
                'negative_cash_violation':self.cash<0,'actual_order_allowed':False,
                'historical_risk_events':sorted(self.risk_events),
                'model_new_buys_allowed':not(self.pending or self.reconciliation or self.risk_events) and self.cash>0,
                'certified_market_net_return':None,'new_prospective_paper_days':0}
