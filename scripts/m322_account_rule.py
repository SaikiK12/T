"""Synthetic-safe cash and inventory primitives for a proposed M322 paper book.

The caller must authenticate source records, clock bounds, exchange contract
units, fees, and complete settlement schedules. No network, disk, clock,
orders, result scoring, margin or liquidation model is implemented here.
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
import math
import re

from scripts.m322_signal_rule import DAY, ENTRY_DELAY, HOLD, MAX_CLOCK_ERROR_MS, Ticket

WINDOW = 2 * 60_000
API_FEE = .0008
_SHA = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class Quote:
    contract: str
    observed_ms: int
    available_ms: int
    clock_error_ms: int
    bid: float
    ask: float
    bid_size_contracts: float
    ask_size_contracts: float
    evidence_sha256: str


@dataclass(frozen=True)
class ContractTerms:
    contract: str
    contract_size_base: float
    volume_step_contracts: float
    min_contracts: float
    max_contracts: float
    active: bool
    api_allowed: bool
    available_ms: int
    clock_error_ms: int
    evidence_sha256: str


@dataclass(frozen=True)
class Funding:
    contract: str
    settlement_ms: int
    rate: float
    fair_price: float
    received_ms: int
    published_ms: int
    clock_error_ms: int
    evidence_sha256: str


@dataclass(frozen=True)
class Position:
    contract: str
    quantity_base: float
    volume_contracts: float
    contract_size_base: float
    requested_quantity_base: float
    entry_price: float
    entry_fee_cash: float
    entry_ms: int
    exit_ms: int


@dataclass(frozen=True)
class Skipped:
    symbol: str
    reason: str


def _digest(value):
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def _finite_positive(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x > 0


def _quote(q, contract, scheduled):
    if not isinstance(q, Quote) or q.contract != contract or not _digest(q.evidence_sha256):
        raise ValueError("invalid quote or evidence")
    if any(isinstance(x, bool) or not isinstance(x, int)
           for x in (q.observed_ms, q.available_ms, q.clock_error_ms)):
        raise ValueError("quote timestamps must be integer milliseconds")
    if not (0 <= q.clock_error_ms <= MAX_CLOCK_ERROR_MS and q.observed_ms <= q.available_ms
            and q.observed_ms - q.clock_error_ms >= scheduled
            and q.available_ms + q.clock_error_ms <= scheduled + WINDOW):
        raise ValueError("quote is outside the on-time window")
    if (not all(_finite_positive(x) for x in (q.bid, q.ask, q.bid_size_contracts, q.ask_size_contracts))
            or q.ask < q.bid):
        raise ValueError("invalid or crossed book")


def _terms(t, contract, deadline):
    if not isinstance(t, ContractTerms) or t.contract != contract or not _digest(t.evidence_sha256):
        raise ValueError("invalid contract terms or evidence")
    if (not all(_finite_positive(x) for x in (t.contract_size_base, t.volume_step_contracts,
                                               t.min_contracts, t.max_contracts))
            or t.min_contracts > t.max_contracts or t.active is not True or t.api_allowed is not True):
        raise ValueError("contract is invalid or not API-tradable")
    if (any(isinstance(x, bool) or not isinstance(x, int) for x in (t.available_ms, t.clock_error_ms))
            or not 0 <= t.clock_error_ms <= MAX_CLOCK_ERROR_MS
            or t.available_ms + t.clock_error_ms > deadline
            or t.available_ms - t.clock_error_ms < deadline - DAY):
        raise ValueError("contract terms were stale or unavailable")


class Account:
    """One segregated account, with five fixed initial-capital slots."""

    def __init__(self, initial_cash, cost_scale):
        if not _finite_positive(initial_cash) or cost_scale not in (1, 2, 3) or isinstance(cost_scale, bool):
            raise ValueError("invalid initial capital or cost tier")
        self.initial_cash = float(initial_cash)
        self.cash = float(initial_cash)
        self.cost_scale = cost_scale
        self.slots = {}
        self.funding_applied = set()
        self.funding_evidence = {}
        self.reconciled_until_ms = None
        self.last_operation_ms = -1
        self.seen_ticket_days = set()

    def open(self, ticket, quotes, terms, *, processed_ms, processed_clock_error_ms,
             schedule_through_ms=None, next_events=None, schedule_sha256=None):
        if not isinstance(ticket, Ticket):
            raise ValueError("invalid ticket")
        if ticket.day_ms in self.seen_ticket_days:
            raise ValueError("ticket day was already processed")
        if (ticket.slot != (ticket.day_ms // DAY) % 5 or ticket.entry_ms != ticket.day_ms + ENTRY_DELAY
                or ticket.exit_ms != ticket.entry_ms + HOLD or ticket.slot in self.slots):
            raise ValueError("invalid or occupied slot")
        if (not ticket.legs or len({x.symbol for x in ticket.legs}) != len(ticket.legs)
                or any(not _finite_positive(x.initial_capital_fraction) for x in ticket.legs)
                or not math.isclose(sum(x.initial_capital_fraction for x in ticket.legs), .20, abs_tol=1e-10)):
            raise ValueError("ticket must allocate one fixed 20% slot")
        mapped = [x.mexc_contract for x in ticket.legs if x.mexc_contract is not None]
        if len(mapped) != len(set(mapped)):
            raise ValueError("duplicate contract")
        if set(quotes) - set(mapped) or set(terms) - set(mapped):
            raise ValueError("quote or terms supplied for an unselected contract")
        for contract in mapped:
            if contract in quotes:
                _quote(quotes[contract], contract, ticket.entry_ms)
        entry_bounds = {q.available_ms + q.clock_error_ms for c, q in quotes.items() if c in mapped}
        if len(entry_bounds) > 1:
            raise ValueError("entry quotes must share one available-time bound")
        latest_entry = max((q.available_ms + q.clock_error_ms for c, q in quotes.items() if c in mapped),
                           default=ticket.entry_ms)
        if (any(isinstance(x, bool) or not isinstance(x, int) for x in (processed_ms, processed_clock_error_ms))
                or not 0 <= processed_clock_error_ms <= MAX_CLOCK_ERROR_MS
                or not latest_entry <= processed_ms - processed_clock_error_ms
                or processed_ms + processed_clock_error_ms > min(ticket.entry_ms + WINDOW, latest_entry + 1000)):
            raise ValueError("ticket must be processed promptly after the quote bound")
        execution_bound = processed_ms + processed_clock_error_ms
        if processed_ms - processed_clock_error_ms < self.last_operation_ms:
            raise ValueError("account time moved backwards")
        for contract in mapped:
            if contract in terms:
                _terms(terms[contract], contract, processed_ms - processed_clock_error_ms)
        if self.slots:
            earliest = processed_ms - processed_clock_error_ms
            if self.reconciled_until_ms is None or self.reconciled_until_ms < earliest:
                raise ValueError("existing positions need complete funding through the new entry")
            held = {p.contract for rows in self.slots.values() for p in rows}
            if (not _digest(schedule_sha256) or not isinstance(next_events, dict) or set(next_events) != held
                    or isinstance(schedule_through_ms, bool) or not isinstance(schedule_through_ms, int)
                    or schedule_through_ms < execution_bound):
                raise ValueError("funding schedule does not cover the entry uncertainty window")
            for t in next_events.values():
                if t is not None and (isinstance(t, bool) or not isinstance(t, int) or t <= execution_bound):
                    raise ValueError("funding event overlaps the entry uncertainty window")
        positions, skipped = [], []
        for leg in ticket.legs:
            contract = leg.mexc_contract
            if contract is None or contract not in quotes:
                skipped.append(Skipped(leg.symbol, "unmapped" if contract is None else "missing_quote"))
                continue
            if contract not in terms:
                skipped.append(Skipped(leg.symbol, "missing_contract_terms"))
                continue
            q = quotes[contract]
            t = terms[contract]
            mid = (q.ask + q.bid) / 2
            price = mid + self.cost_scale * (q.ask - mid)
            budget = self.initial_cash * leg.initial_capital_fraction
            if self.cash + 1e-10 < budget:
                skipped.append(Skipped(leg.symbol, "insufficient_cash"))
                continue
            requested = budget / (price * (1 + self.cost_scale * API_FEE))
            contract_size = Decimal(str(t.contract_size_base))
            step = Decimal(str(t.volume_step_contracts))
            desired = Decimal(str(requested)) / contract_size
            capacity = min(desired, Decimal(str(q.ask_size_contracts)), Decimal(str(t.max_contracts)))
            volume = (capacity / step).to_integral_value(rounding=ROUND_FLOOR) * step
            if volume < Decimal(str(t.min_contracts)):
                skipped.append(Skipped(leg.symbol, "below_minimum_volume"))
                continue
            quantity = float(volume * contract_size)
            fee_cash = quantity * price * self.cost_scale * API_FEE
            self.cash -= quantity * price + fee_cash
            entry_time = execution_bound
            positions.append(Position(contract, quantity, float(volume), float(contract_size), requested, price, fee_cash,
                                      entry_time, entry_time + HOLD))
        if positions:
            self.slots[ticket.slot] = positions
        self.seen_ticket_days.add(ticket.day_ms)
        self.last_operation_ms = execution_bound
        return tuple(positions), tuple(skipped)

    def _funding(self, positions, expected_events, funding, schedule_sha256, asof_ms):
        if (not _digest(schedule_sha256) or isinstance(asof_ms, bool) or not isinstance(asof_ms, int)):
            raise ValueError("missing settlement-schedule evidence or as-of time")
        if asof_ms < self.last_operation_ms or any(p.entry_ms > asof_ms for _, p in positions):
            raise ValueError("account time moved backwards")
        contracts = {p.contract for _, p in positions}
        if set(expected_events) != contracts:
            raise ValueError("missing settlement schedule")
        funding = list(funding)
        if any(not isinstance(f, Funding) for f in funding):
            raise ValueError("invalid settlement")
        expected = {(c, t) for c, times in expected_events.items() for t in times}
        if sum(len(v) for v in expected_events.values()) != len(expected):
            raise ValueError("duplicate expected settlement")
        seen = {(f.contract, f.settlement_ms) for f in funding}
        if len(seen) != len(funding) or seen != expected:
            raise ValueError("missing, duplicate, or unexpected settlement")
        delta, applied, evidence, flows = 0.0, set(), {}, []
        for f in funding:
            if (any(isinstance(t, bool) or not isinstance(t, int) for t in
                    (f.settlement_ms, f.received_ms, f.published_ms, f.clock_error_ms))
                    or not 0 <= f.clock_error_ms <= MAX_CLOCK_ERROR_MS
                    or f.received_ms - f.clock_error_ms < f.settlement_ms
                    or f.received_ms > f.published_ms or f.published_ms + f.clock_error_ms > asof_ms
                    or not _digest(f.evidence_sha256) or not isinstance(f.rate, (int, float))
                    or isinstance(f.rate, bool) or not math.isfinite(f.rate) or abs(f.rate) > 1
                    or not _finite_positive(f.fair_price)):
                raise ValueError("invalid or unavailable funding event")
            key = (f.contract, f.settlement_ms)
            fingerprint = (f.rate, f.fair_price, f.evidence_sha256)
            if key in self.funding_evidence and self.funding_evidence[key] != fingerprint:
                raise ValueError("funding evidence changed")
            evidence[key] = fingerprint
            matched = False
            event_delta = 0.0
            for slot, p in positions:
                if p.contract == f.contract and p.entry_ms < f.settlement_ms <= min(asof_ms, p.exit_ms + WINDOW):
                    matched = True
                    position_key = (slot, f.contract, f.settlement_ms)
                    if position_key not in self.funding_applied:
                        event_delta -= p.quantity_base * f.fair_price * f.rate
                        applied.add(position_key)
            if not matched:
                raise ValueError("settlement outside held positions")
            delta += event_delta
            flows.append((f.settlement_ms, event_delta))
        cash = self.cash
        for _, flow in sorted(flows):  # debits first if settlements share a timestamp
            cash += flow
            if cash < -1e-10:
                raise ValueError("funding exceeds available cash; account requires a separate risk model")
        return delta, applied, evidence

    def reconcile_funding(self, asof_ms, expected_events, funding, schedule_sha256):
        """Book each verified settlement once before spending on a later ticket."""
        if self.reconciled_until_ms is not None and asof_ms < self.reconciled_until_ms:
            raise ValueError("funding coverage moved backwards")
        positions = [(slot, p) for slot, rows in self.slots.items() for p in rows]
        delta, applied, evidence = self._funding(positions, expected_events, funding, schedule_sha256, asof_ms)
        if self.cash + delta < -1e-10:
            raise ValueError("funding exceeds available cash; account requires a separate risk model")
        self.cash += delta
        self.funding_applied.update(applied)
        self.funding_evidence.update(evidence)
        self.reconciled_until_ms = asof_ms
        self.last_operation_ms = asof_ms
        return delta

    def mark(self, asof_ms, quotes):
        """Mark every open position on a recent, already-available midpoint."""
        if isinstance(asof_ms, bool) or not isinstance(asof_ms, int) or asof_ms < self.last_operation_ms:
            raise ValueError("account time moved backwards")
        positions = [p for rows in self.slots.values() for p in rows]
        contracts = {p.contract for p in positions}
        if set(quotes) != contracts:
            raise ValueError("missing mark quote")
        if positions and (self.reconciled_until_ms is None or self.reconciled_until_ms < asof_ms):
            raise ValueError("funding coverage is incomplete at mark time")
        value = self.cash
        for p in positions:
            q = quotes[p.contract]
            if not isinstance(q, Quote) or q.contract != p.contract or not _digest(q.evidence_sha256):
                raise ValueError("invalid mark quote")
            if any(isinstance(x, bool) or not isinstance(x, int)
                   for x in (q.observed_ms, q.available_ms, q.clock_error_ms)):
                raise ValueError("invalid mark timing")
            if not (0 <= q.clock_error_ms <= MAX_CLOCK_ERROR_MS and q.observed_ms <= q.available_ms
                    and q.observed_ms - q.clock_error_ms >= asof_ms - WINDOW
                    and q.available_ms + q.clock_error_ms <= asof_ms):
                raise ValueError("mark quote is stale or unavailable")
            if not (_finite_positive(q.bid) and _finite_positive(q.ask) and q.ask >= q.bid):
                raise ValueError("invalid mark book")
            value += p.quantity_base * (q.bid + q.ask) / 2
        self.last_operation_ms = asof_ms
        return value

    def close(self, slot, quotes, terms, expected_events, funding, schedule_sha256, asof_ms):
        """Close only after every exit and settlement is evidenced, else change nothing.

        expected_events maps each held contract to its independently validated
        settlement timestamps. Missing history must never be supplied as zero.
        """
        if slot not in self.slots or not _digest(schedule_sha256):
            raise ValueError("missing position or settlement-schedule evidence")
        positions = self.slots[slot]
        contracts = {p.contract for p in positions}
        if set(expected_events) != contracts or set(quotes) != contracts or set(terms) != contracts:
            raise ValueError("missing exit quote, terms or settlement schedule")
        funding = list(funding)
        delta, applied, evidence = self._funding([(slot, p) for p in positions], expected_events,
                                                   funding, schedule_sha256, asof_ms)
        if self.cash + delta < -1e-10:
            raise ValueError("funding exceeds available cash; account requires a separate risk model")
        for p in positions:
            q = quotes[p.contract]
            _quote(q, p.contract, p.exit_ms)
            _terms(terms[p.contract], p.contract, q.available_ms + q.clock_error_ms)
            if terms[p.contract].contract_size_base != p.contract_size_base:
                raise ValueError("contract size changed while position was open")
            volume = Decimal(str(p.volume_contracts))
            current = terms[p.contract]
            if (volume < Decimal(str(current.min_contracts)) or volume > Decimal(str(current.max_contracts))
                    or volume % Decimal(str(current.volume_step_contracts)) != 0):
                raise ValueError("position cannot be closed under current contract terms")
            if q.bid_size_contracts < p.volume_contracts:
                raise ValueError("exit depth cannot fill the position")
            mid = (q.ask + q.bid) / 2
            price = mid - self.cost_scale * (mid - q.bid)
            if price <= 0:
                raise ValueError("scaled exit price is nonpositive")
            exit_time = q.available_ms + q.clock_error_ms
            if exit_time > asof_ms or any(f.contract == p.contract and f.settlement_ms > exit_time for f in funding):
                raise ValueError("exit or settlement not available by scoring time")
            delta += p.quantity_base * price * (1 - self.cost_scale * API_FEE)
        self.cash += delta
        self.funding_applied.update(applied)
        self.funding_evidence.update(evidence)
        self.last_operation_ms = asof_ms
        del self.slots[slot]
        return delta
