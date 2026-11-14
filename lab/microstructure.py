"""Offline features from caller-validated, consecutive best-quote observations.

Cont, Kukanov & Stoikov, arXiv:1011.6402v3 (13 Apr 2011), section 2.1:
https://arxiv.org/html/1011.6402v3
e = 1[b>=b0]*q_b - 1[b<=b0]*q_b0 - 1[a<=a0]*q_a + 1[a>=a0]*q_a0.
OFI is the sum of e in an open-left, closed-right time interval. Units are the
input quantity unit, consistently contracts or base units for one instrument.

Here windows use a caller-supplied monotonic receive clock in integer ns.
Exchange timestamps are separately ordered; they are never compared to the
receive clock. A logical sequence is an upstream assertion of continuity,
NOT a raw venue version number. Missing sequence knowledge invalidates OFI.
Full-window warmup is required after every discontinuity. This cannot repair
a feed or prove that snapshots contain every intermediate best-quote event.

Official MEXC documentation inspected 2026-10-21:
https://www.mexc.com/api-docs/futures/websocket-api/order-book-depth
https://www.mexc.com/api-docs/futures/websocket-api/incremental-order-book-maintenance-mechanism
https://www.mexc.com/api-docs/futures/market-endpoints/get-contract-order-book-depth
Unversioned-page UTF-8 web-extraction SHA256s, in the same order:
137378486e3fd32a90041eb514f8906843615530a6717809019dc1e71dbe71a2
f28ef8b335acbf0befafa15e8d959280330b4b7cd8415e92fdd1dfd3538d1bc0
56a4f26b50113ec07d257edf7f9f9d79ebd2fb16238022740397acc7c5c10423
Its 200-ms depth pushes have version and matching-engine cts fields. Feed
reconstruction, timestamp coverage and any omitted intermediate transitions
must be resolved upstream; this module implements no venue adapter. Applying
the formula to sampled quotes gives sampled BBO OFI, not recovered event OFI.

weighted_mid = (ask*q_bid + bid*q_ask)/(q_bid+q_ask) is an opposite-price
quantity-weighted midpoint, not Stoikov's fitted microprice. Depth imbalance
is (sum_L q_bid - sum_L q_ask)/(sum_L q_bid + sum_L q_ask). These are displayed
book features, with no fill, queue, profitability or probability interpretation.
Weighted midpoint/microprice distinction: author sstoikov/microprice notebook,
commit 94205fe5bedb98b627b43e4abeb59f91fa6d7075 (2020-06-02):
https://github.com/sstoikov/microprice/blob/94205fe5bedb98b627b43e4abeb59f91fa6d7075/Microprice%20-%20Big%20Data%20Conference.ipynb
"""

from collections import deque
from dataclasses import dataclass
from math import fsum, isfinite
from numbers import Real
from typing import Literal


def _integer(name: str, value: int, *, positive: bool = False) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < (1 if positive else 0):
        raise ValueError(f"{name} must be a {'positive' if positive else 'nonnegative'} integer")


def _symbol(value: str) -> None:
    if not isinstance(value, str) or not value or any(c.isspace() for c in value):
        raise ValueError("symbol must be a nonempty string without whitespace")


def _positive(name: str, value: float) -> float:
    try:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError
        out = float(value)
        if not isfinite(out) or out <= 0:
            raise ValueError
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be positive and finite") from exc
    return out


def _finite_sum(values) -> float:
    try:
        value = fsum(values)
    except OverflowError as exc:
        raise ValueError("OFI is outside finite float range") from exc
    if not isfinite(value):
        raise ValueError("OFI is outside finite float range")
    return value


@dataclass(frozen=True, slots=True)
class BestQuote:
    symbol: str
    exchange_time_ns: int
    receive_time_ns: int
    sequence: int | None
    bid_price: float
    bid_size: float
    ask_price: float
    ask_size: float

    def __post_init__(self) -> None:
        _symbol(self.symbol)
        _integer("exchange_time_ns", self.exchange_time_ns)
        _integer("receive_time_ns", self.receive_time_ns)
        if self.sequence is not None:
            _integer("sequence", self.sequence)
        for name in ("bid_price", "bid_size", "ask_price", "ask_size"):
            object.__setattr__(self, name, _positive(name, getattr(self, name)))
        if self.bid_price >= self.ask_price:
            raise ValueError("best quotes must be strictly uncrossed")


@dataclass(frozen=True, slots=True)
class DepthLevel:
    price: float
    size: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "price", _positive("price", self.price))
        object.__setattr__(self, "size", _positive("size", self.size))


@dataclass(frozen=True, slots=True)
class DepthSnapshot:
    """Complete displayed levels supplied by the caller, best price first.

    Zero-size deletions must already have been applied by the upstream book
    builder. No incremental message, order count or notional conversion is
    interpreted here. Both sides must contain at least the requested L levels.
    """

    symbol: str
    exchange_time_ns: int
    receive_time_ns: int
    bids: tuple[DepthLevel, ...]
    asks: tuple[DepthLevel, ...]

    def __post_init__(self) -> None:
        _symbol(self.symbol)
        _integer("exchange_time_ns", self.exchange_time_ns)
        _integer("receive_time_ns", self.receive_time_ns)
        for name in ("bids", "asks"):
            levels = tuple(getattr(self, name))
            if not levels or any(not isinstance(level, DepthLevel) for level in levels):
                raise ValueError("both sides must contain validated DepthLevel objects")
            object.__setattr__(self, name, levels)
        if any(a.price <= b.price for a, b in zip(self.bids, self.bids[1:])):
            raise ValueError("bids must have distinct descending prices")
        if any(a.price >= b.price for a, b in zip(self.asks, self.asks[1:])):
            raise ValueError("asks must have distinct ascending prices")
        if self.bids[0].price >= self.asks[0].price:
            raise ValueError("depth must be strictly uncrossed")


def bbo_ofi(previous: BestQuote, current: BestQuote) -> float:
    """CKS contribution between known consecutive observations of one symbol.

    Continuity and clock order are checked here; caller-specific maximum time
    gaps and observation availability are checked by RollingOFI.
    """
    if current.symbol != previous.symbol:
        raise ValueError("symbol mismatch")
    if previous.sequence is None or current.sequence is None or current.sequence != previous.sequence + 1:
        raise ValueError("known consecutive logical sequences required")
    if (current.exchange_time_ns < previous.exchange_time_ns
            or current.receive_time_ns < previous.receive_time_ns):
        raise ValueError("observations must be ordered on both clocks")
    # At an unchanged price both indicators fire, giving the size difference.
    bid = (current.bid_size if current.bid_price >= previous.bid_price else 0.0)
    bid -= previous.bid_size if current.bid_price <= previous.bid_price else 0.0
    ask = (previous.ask_size if current.ask_price >= previous.ask_price else 0.0)
    ask -= current.ask_size if current.ask_price <= previous.ask_price else 0.0
    return _finite_sum((bid, ask))


def weighted_mid(quote: BestQuote) -> float:
    """Opposite-price quantity-weighted midpoint, bounded by the two quotes."""
    scale = max(quote.bid_size, quote.ask_size)
    bid, ask = quote.bid_size / scale, quote.ask_size / scale
    return quote.bid_price + (quote.ask_price - quote.bid_price) * (bid / (bid + ask))


def depth_imbalance(snapshot: DepthSnapshot, levels: int) -> float:
    """Normalized size imbalance across exactly L levels on each side."""
    _integer("levels", levels, positive=True)
    if min(len(snapshot.bids), len(snapshot.asks)) < levels:
        raise ValueError("insufficient depth on one or both sides")
    bids, asks = snapshot.bids[:levels], snapshot.asks[:levels]
    scale = max(level.size for level in (*bids, *asks))
    bid = fsum(level.size / scale for level in bids)
    ask = fsum(level.size / scale for level in asks)
    return (bid - ask) / (bid + ask)


Status = Literal["warming", "ready", "duplicate", "gap", "unknown_sequence",
                 "out_of_order", "conflict", "stale", "reset"]


@dataclass(frozen=True, slots=True)
class OFIValue:
    value: float | None
    status: Status
    contribution: float | None
    asof_receive_time_ns: int
    window_start_receive_time_ns: int
    event_count: int

    @property
    def ready(self) -> bool:
        return self.value is not None


class RollingOFI:
    """Past-only OFI in receive-time (now-window, now], with full warmup.

    All methods take an explicit nondecreasing local clock. Nonduplicate
    updates cannot precede the last queried time: past answers are never
    backfilled. Equal event timestamps are allowed when logical sequences
    establish their order. A future observation or symbol mismatch raises
    without mutation. An identical repeat of the latest logical event ignores
    its new receipt time, so duplicates cannot refresh stale data. Older events
    invalidate, even if they might be duplicates of an older observation.

    A known sequence/time gap clears the window and uses the new quote only
    as a fresh baseline. Unknown sequences, conflicting latest sequences,
    regressions and staleness clear it without a baseline. A new known quote
    then starts full-window warmup. Trusted sequence/exchange watermarks survive
    invalidation: an exchange/sequence epoch change requires explicit reset().
    reset() preserves the local clock watermark; construct a new instance for
    a new receive-clock epoch.
    """

    def __init__(self, symbol: str, *, window_ns: int, max_exchange_gap_ns: int,
                 max_receive_gap_ns: int):
        _symbol(symbol)
        for name, value in (("window_ns", window_ns), ("max_exchange_gap_ns", max_exchange_gap_ns),
                            ("max_receive_gap_ns", max_receive_gap_ns)):
            _integer(name, value, positive=True)
        self.symbol = symbol
        self.window_ns = window_ns
        self.max_exchange_gap_ns = max_exchange_gap_ns
        self.max_receive_gap_ns = max_receive_gap_ns
        self._last: BestQuote | None = None
        self._seen: BestQuote | None = None
        self._exchange_watermark: int | None = None
        self._start: int | None = None
        self._now: int | None = None
        self._events: deque[tuple[int, float]] = deque()

    def _clock(self, now: int) -> None:
        _integer("now_receive_time_ns", now)
        if self._now is not None and now < self._now:
            raise ValueError("receive clock moved backwards")

    def _clear(self) -> None:
        self._last = None
        self._start = None
        self._events.clear()

    def _result(self, now: int, status: Status, contribution: float | None = None) -> OFIValue:
        self._now = now
        boundary = now - self.window_ns
        while self._events and self._events[0][0] <= boundary:
            self._events.popleft()
        if self._last is not None and now - self._last.receive_time_ns > self.max_receive_gap_ns:
            self._clear()
            status, contribution = "stale", None
        ready = (self._start is not None and self._start <= boundary and self._last is not None
                 and self._last.receive_time_ns - self._start >= self.window_ns)
        try:
            value = _finite_sum(event[1] for event in self._events) if ready else None
        except ValueError:
            self._clear()
            raise
        if status == "warming" and ready:
            status = "ready"
        return OFIValue(value, status, contribution, now, boundary, len(self._events))

    def update(self, quote: BestQuote, *, now_receive_time_ns: int) -> OFIValue:
        now = now_receive_time_ns
        self._clock(now)
        if quote.symbol != self.symbol:
            raise ValueError("symbol mismatch")
        if quote.receive_time_ns > now:
            raise ValueError("observation is not yet received")
        last = self._last
        seen = self._seen
        if quote.sequence is not None and seen is not None and quote.sequence == seen.sequence:
            if (quote.exchange_time_ns, quote.bid_price, quote.bid_size, quote.ask_price, quote.ask_size) == (
                    seen.exchange_time_ns, seen.bid_price, seen.bid_size, seen.ask_price, seen.ask_size):
                if quote.receive_time_ns >= seen.receive_time_ns:
                    return self._result(now, "duplicate")
            self._clear()
            return self._result(now, "conflict")
        if ((self._now is not None and quote.receive_time_ns < self._now)
                or (seen is not None and quote.sequence is not None and quote.sequence < seen.sequence)
                or (self._exchange_watermark is not None
                    and quote.exchange_time_ns < self._exchange_watermark)):
            self._clear()
            return self._result(now, "out_of_order")
        self._exchange_watermark = quote.exchange_time_ns
        if quote.sequence is None:
            self._clear()
            return self._result(now, "unknown_sequence")
        self._seen = quote
        gap = last is not None and (
            quote.sequence != last.sequence + 1
            or quote.exchange_time_ns - last.exchange_time_ns > self.max_exchange_gap_ns
            or quote.receive_time_ns - last.receive_time_ns > self.max_receive_gap_ns)
        contribution = None
        if last is None or gap:
            self._clear()
            self._start = quote.receive_time_ns
        else:
            try:
                contribution = bbo_ofi(last, quote)
            except ValueError:
                self._clear()
                self._now = now
                raise
            self._events.append((quote.receive_time_ns, contribution))
        self._last = quote
        return self._result(now, "gap" if gap else "warming", contribution)

    def at(self, *, now_receive_time_ns: int) -> OFIValue:
        self._clock(now_receive_time_ns)
        return self._result(now_receive_time_ns, "warming")

    def reset(self, *, now_receive_time_ns: int) -> OFIValue:
        self._clock(now_receive_time_ns)
        self._clear()
        self._seen = None
        self._exchange_watermark = None
        return self._result(now_receive_time_ns, "reset")
