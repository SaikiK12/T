"""Causal ticket construction for the proposed M090 forecast comparison.

Pure functions only: no network, file access, journal, outcome scoring, or orders.
The caller must authenticate each evidence hash and clock certificate before use.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import re

HOUR = 3_600_000
DAY = 24 * HOUR
MAX_CLOCK_ERROR_MS = 1_000
PRIMARY = "BTC_USDT"
_SHA = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class ClockBound:
    valid_from_ms: int
    valid_until_ms: int
    max_error_ms: int
    evidence_sha256: str


@dataclass(frozen=True)
class Observation:
    symbol: str
    settlement_ms: int
    rate: float
    request_start_ms: int
    received_ms: int
    published_ms: int
    evidence_sha256: str
    clock: ClockBound


@dataclass(frozen=True)
class Ticket:
    symbol: str
    settlement_ms: int
    decision_ms: int
    previous_settlement_ms: int
    displayed_rate: float
    previous_rate: float
    display_evidence_sha256: str
    previous_evidence_sha256: str
    inputs_ready_ms: int


@dataclass(frozen=True)
class SealedTicket:
    ticket: Ticket
    ticket_sha256: str
    published_ms: int
    clock: ClockBound


def _valid(o):
    if (not isinstance(o, Observation) or not isinstance(o.symbol, str) or not o.symbol
            or not isinstance(o.clock, ClockBound)):
        raise ValueError("invalid observation")
    timestamps = (o.settlement_ms, o.request_start_ms, o.received_ms, o.published_ms,
                  o.clock.valid_from_ms, o.clock.valid_until_ms, o.clock.max_error_ms)
    if any(isinstance(x, bool) or not isinstance(x, int) for x in timestamps):
        raise ValueError("timestamps and clock bound must be integer milliseconds")
    if (not isinstance(o.rate, (int, float)) or isinstance(o.rate, bool)
            or not math.isfinite(o.rate) or abs(o.rate) > 1):
        raise ValueError("invalid funding rate")
    if not (o.request_start_ms <= o.received_ms <= o.published_ms):
        raise ValueError("invalid receipt or publication order")
    if not (0 <= o.clock.max_error_ms <= MAX_CLOCK_ERROR_MS
            and o.clock.valid_from_ms <= o.request_start_ms <= o.published_ms <= o.clock.valid_until_ms):
        raise ValueError("clock bound missing, stale, or too uncertain")
    if (not isinstance(o.evidence_sha256, str) or not isinstance(o.clock.evidence_sha256, str)
            or not _SHA.fullmatch(o.evidence_sha256) or not _SHA.fullmatch(o.clock.evidence_sha256)):
        raise ValueError("missing evidence digest")


def _select(rows, symbol, settlement_ms, decision_ms, *, display):
    eligible = []
    for o in rows:
        if not isinstance(o, Observation):
            raise ValueError("invalid observation")
        if o.symbol != symbol or o.settlement_ms != settlement_ms:
            continue
        _valid(o)
        error = o.clock.max_error_ms
        # Use conservative clock bounds: receipt and durable publication must
        # both have occurred by the decision, not merely started by it.
        if o.published_ms + error > decision_ms:
            continue
        if display and o.received_ms - error < settlement_ms - 3 * HOUR:
            continue
        if not display and o.request_start_ms - error < settlement_ms:
            continue  # a pre-settlement request cannot establish a settled rate
        eligible.append(o)
    if not eligible:
        return None
    last_key = max((o.received_ms, o.published_ms) for o in eligible)
    winners = [o for o in eligible if (o.received_ms, o.published_ms) == last_key]
    if len({(o.rate, o.evidence_sha256) for o in winners}) != 1:
        raise ValueError("conflicting observations at identical timestamps")
    return winners[0]


def ticket(target_ms, previous_settlement_ms, displayed, history, symbol=PRIMARY):
    """Return one immutable ticket or None if either input was not available.

    previous_settlement_ms must come from an authenticated event schedule; do
    not infer an eight-hour interval or substitute an older available event.
    """
    if any(isinstance(v, bool) or not isinstance(v, int) for v in (target_ms, previous_settlement_ms)):
        raise ValueError("settlement times must be integer milliseconds")
    decision = target_ms - HOUR
    if previous_settlement_ms >= decision:
        raise ValueError("previous settlement must precede the decision")
    display = _select(displayed, symbol, target_ms, decision, display=True)
    previous = _select(history, symbol, previous_settlement_ms, decision, display=False)
    if display is None or previous is None:
        return None
    inputs_ready = max(display.published_ms + display.clock.max_error_ms,
                       previous.published_ms + previous.clock.max_error_ms)
    return Ticket(symbol, target_ms, decision, previous_settlement_ms, float(display.rate),
                  float(previous.rate), display.evidence_sha256, previous.evidence_sha256, inputs_ready)


def ticket_bytes(ticket_):
    if not isinstance(ticket_, Ticket):
        raise ValueError("invalid ticket")
    return (json.dumps(asdict(ticket_), sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def seal(ticket_, persisted, published_ms, clock):
    """Check a caller-authenticated durable ticket was available by decision.

    A byte match is not proof of publication time or a valid clock: the caller
    must independently authenticate the receipt and clock evidence.
    """
    if (not isinstance(ticket_, Ticket) or not isinstance(clock, ClockBound)
            or isinstance(published_ms, bool) or not isinstance(published_ms, int)
            or any(isinstance(x, bool) or not isinstance(x, int)
                   for x in (clock.valid_from_ms, clock.valid_until_ms, clock.max_error_ms,
                             ticket_.settlement_ms, ticket_.decision_ms, ticket_.previous_settlement_ms,
                             ticket_.inputs_ready_ms))
            or not 0 <= clock.max_error_ms <= MAX_CLOCK_ERROR_MS
            or not isinstance(clock.evidence_sha256, str) or not _SHA.fullmatch(clock.evidence_sha256)):
        raise ValueError("invalid ticket publication or clock bound")
    if (ticket_.decision_ms != ticket_.settlement_ms - HOUR or ticket_.previous_settlement_ms >= ticket_.decision_ms
            or not isinstance(ticket_.symbol, str) or not ticket_.symbol
            or any(not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x) or abs(x) > 1
                   for x in (ticket_.displayed_rate, ticket_.previous_rate))
            or any(not isinstance(x, str) or not _SHA.fullmatch(x)
                   for x in (ticket_.display_evidence_sha256, ticket_.previous_evidence_sha256))):
        raise ValueError("invalid ticket contents")
    if (not clock.valid_from_ms <= published_ms <= clock.valid_until_ms
            or published_ms - clock.max_error_ms < ticket_.inputs_ready_ms
            or published_ms + clock.max_error_ms > ticket_.decision_ms):
        raise ValueError("ticket was not durably available by the decision")
    expected = ticket_bytes(ticket_)
    if not isinstance(persisted, bytes) or persisted != expected:
        raise ValueError("persisted ticket bytes do not match")
    return SealedTicket(ticket_, hashlib.sha256(persisted).hexdigest(), published_ms, clock)


def outcome(sealed, labels):
    """Return the verified-event label or None. This does not calculate a score."""
    if not isinstance(sealed, SealedTicket):
        raise ValueError("sealed ticket required")
    ticket_ = sealed.ticket
    checked = seal(ticket_, ticket_bytes(ticket_), sealed.published_ms, sealed.clock)
    if checked.ticket_sha256 != sealed.ticket_sha256:
        raise ValueError("sealed ticket digest mismatch")
    matches = []
    for o in labels:
        if not isinstance(o, Observation):
            raise ValueError("invalid observation")
        if o.symbol != ticket_.symbol or o.settlement_ms != ticket_.settlement_ms:
            continue
        _valid(o)
        if o.request_start_ms - o.clock.max_error_ms < ticket_.settlement_ms:
            continue
        matches.append(o)
    if not matches:
        return None
    if len({o.rate for o in matches}) != 1:
        raise ValueError("conflicting settled-rate labels")
    return float(matches[0].rate)


def final_look_ready(scored_events):
    """Check coverage only; scoring remains gated by a frozen, registered run."""
    events = list(scored_events)
    if len(events) != len(set(events)):
        raise ValueError("duplicate settlement event")
    if any(isinstance(x, bool) or not isinstance(x, int) for x in events):
        raise ValueError("event time must be integer milliseconds")
    return len(events) >= 90 and len({t // DAY for t in events}) >= 30
