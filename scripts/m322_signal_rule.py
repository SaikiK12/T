"""Prospective M322 signal and fixed-capital ticket construction.

Pure functions only; inputs must be authenticated by the caller. No file or
network access, journal, historical outcome, scoring, or order placement.
"""
from dataclasses import dataclass
import math
import re

DAY = 86_400_000
MINUTE = 60_000
DECISION_DELAY = 2 * MINUTE
ENTRY_DELAY = 3 * MINUTE
HOLD = 5 * DAY
MAX_CLOCK_ERROR_MS = 1_000
_SHA = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class Close:
    day_ms: int
    price: float


@dataclass(frozen=True)
class Contract:
    symbol: str
    rank: int
    closes: tuple[Close, ...]
    available_ms: int
    clock_error_ms: int
    evidence_sha256: str
    mexc_contract: str | None


@dataclass(frozen=True)
class PriorBreadth:
    day_ms: int
    share: float | None
    available_ms: int
    clock_error_ms: int
    evidence_sha256: str


@dataclass(frozen=True)
class Leg:
    symbol: str
    mexc_contract: str | None
    initial_capital_fraction: float


@dataclass(frozen=True)
class Ticket:
    day_ms: int
    decision_ms: int
    entry_ms: int
    exit_ms: int
    slot: int
    breadth: float
    threshold: float
    legs: tuple[Leg, ...]


def _integer(v, label):
    if isinstance(v, bool) or not isinstance(v, int):
        raise ValueError(f"{label} must be integer")
    return v


def _known(available_ms, clock_error_ms, sha, deadline):
    _integer(available_ms, "availability")
    _integer(clock_error_ms, "clock error")
    if not 0 <= clock_error_ms <= MAX_CLOCK_ERROR_MS:
        raise ValueError("missing or uncertain clock bound")
    if available_ms + clock_error_ms > deadline:
        raise ValueError("input was not available by decision")
    if not isinstance(sha, str) or not _SHA.fullmatch(sha):
        raise ValueError("missing evidence digest")


def _positive(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x > 0


def quantile95(values):
    """Linear interpolation, matching pandas' default rolling quantile."""
    xs = sorted(values)
    if not xs:
        raise ValueError("empty quantile")
    pos = .95 * (len(xs) - 1)
    lo = math.floor(pos)
    return xs[lo] + (xs[math.ceil(pos)] - xs[lo]) * (pos - lo)


def ticket(day_ms, contracts, prior, occupied_slots=()):
    """Return an event ticket, None for no signal, or raise on unsafe inputs.

    No future price, funding, fill, or exit is an input. Missing history is
    excluded from breadth; unlisted basket members retain their cash allocation.
    An occupied five-day slot must not be silently reused.
    """
    _integer(day_ms, "day")
    if day_ms % DAY:
        raise ValueError("day must be 00:00 UTC")
    decision = day_ms + DECISION_DELAY
    universe = list(contracts)
    if any(not isinstance(c, Contract) for c in universe):
        raise ValueError("invalid contract")
    if len({c.symbol for c in universe}) != len(universe):
        raise ValueError("duplicate symbol")
    breadth_values, basket = [], []
    for c in universe:
        if not isinstance(c, Contract) or not isinstance(c.symbol, str) or not c.symbol:
            raise ValueError("invalid contract")
        _integer(c.rank, "rank")
        if c.rank < 1:
            raise ValueError("invalid rank")
        _known(c.available_ms, c.clock_error_ms, c.evidence_sha256, decision)
        if c.available_ms - c.clock_error_ms < day_ms:
            raise ValueError("current close was reported before its bar ended")
        if c.mexc_contract is not None and (not isinstance(c.mexc_contract, str) or not c.mexc_contract):
            raise ValueError("invalid MEXC mapping")
        if not c.closes:
            continue
        if not all(isinstance(x, Close) and _positive(x.price) for x in c.closes):
            raise ValueError("invalid close")
        days = [x.day_ms for x in c.closes]
        if any(isinstance(d, bool) or not isinstance(d, int) for d in days):
            raise ValueError("invalid close day")
        if days != list(range(days[0], day_ms + DAY, DAY)) or days[-1] != day_ms or len(days) > 25:
            raise ValueError("close history has a gap or future value")
        if c.rank <= 50:
            basket.append(c)
        if c.rank <= 150 and len(c.closes) == 25:
            avg = sum(x.price for x in c.closes) / 25
            breadth_values.append(c.closes[-1].price / avg - 1 <= -.20)
    if not breadth_values:
        return None
    prior = list(prior)
    if any(not isinstance(p, PriorBreadth) for p in prior):
        raise ValueError("invalid prior breadth")
    if len({p.day_ms for p in prior}) != len(prior):
        raise ValueError("duplicate breadth day")
    shares = []
    for p in prior:
        if not isinstance(p, PriorBreadth):
            raise ValueError("invalid prior breadth")
        _integer(p.day_ms, "prior day")
        if p.day_ms % DAY or not day_ms - 365 * DAY <= p.day_ms < day_ms:
            raise ValueError("prior breadth outside the 365-day window")
        _known(p.available_ms, p.clock_error_ms, p.evidence_sha256, decision)
        if p.available_ms - p.clock_error_ms < p.day_ms:
            raise ValueError("prior breadth was reported before its day")
        if p.share is None:
            continue
        if (not isinstance(p.share, (int, float)) or isinstance(p.share, bool)
                or not math.isfinite(p.share) or not 0 <= p.share <= 1):
            raise ValueError("invalid prior breadth share")
        shares.append(p.share)
    if len(shares) < 180:
        return None
    breadth, threshold = sum(breadth_values) / len(breadth_values), quantile95(shares)
    if breadth < .10 or breadth < threshold or len(basket) < 30:
        return None
    mapped = [c.mexc_contract for c in basket if c.mexc_contract is not None]
    if len(set(mapped)) != len(mapped):
        raise ValueError("duplicate MEXC mapping")
    slot = (day_ms // DAY) % 5
    if slot in set(occupied_slots):
        raise ValueError("five-day slot is still occupied")
    basket.sort(key=lambda c: (c.rank, c.symbol))
    legs = tuple(Leg(c.symbol, c.mexc_contract, .20 / len(basket)) for c in basket)
    entry = day_ms + ENTRY_DELAY
    return Ticket(day_ms, decision, entry, entry + HOLD, slot, breadth, threshold, legs)
