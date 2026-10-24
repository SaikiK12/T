"""Causal full-snapshot/BBO replay with separate source and first-seen clocks.

No incremental book reconstruction, OFI, inferred fills or session calendar.
MEXC cts is a reported matching-engine ms clock; Lighter last_updated_at is
treated as a reported book-update microsecond clock, not certified wall time.
Only full MEXC snapshots and the one complete Lighter BBO level are usable.
Missing source clocks never fall back to an envelope or local receive time.
"""
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
import json

from lab.executable_quotes import common_quantity, pair_costs, positive, walk
from lab.mexc_depth import parse_depth_levels
from lab.microstructure import DepthLevel, DepthSnapshot

NS = 1_000_000_000
SYMBOLS = ("BTC", "WIF", "SKR", "ROBO", "MEGA", "XPD")


def integer(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("nonnegative integer clock/version required")
    return value


def source_ns(value, unit):
    value = integer(value) * {"ms": 1_000_000, "us": 1_000}[unit]
    if not 1_577_836_800 * NS <= value <= 4_102_444_800 * NS:
        raise ValueError("source clock unit/epoch outside 2020..2100")
    return value


@dataclass(frozen=True)
class FrameClock:
    utc_ns: int
    mono_ns: int

    def __post_init__(self):
        integer(self.utc_ns)
        integer(self.mono_ns)


@dataclass(frozen=True)
class StreamBook:
    venue: str
    symbol: str
    clock: FrameClock
    depth: DepthSnapshot
    version: int
    source_role: str

    @property
    def bids(self):
        return self.depth.bids

    @property
    def asks(self):
        return self.depth.asks

    @property
    def mid(self):
        return self.bids[0].price/2 + self.asks[0].price/2

    @property
    def source_time_ns(self):
        return self.depth.exchange_time_ns

    @property
    def signature(self):
        return self.version, self.bids, self.asks


@dataclass(frozen=True)
class ReferencePrice:
    venue: str
    symbol: str
    clock: FrameClock
    source_time_ns: int
    price: Decimal
    source_role: str

    @property
    def signature(self):
        return self.source_time_ns, self.price


def decode(venue, payload, clock, metadata, names):
    """Return (kind, base symbol, observation or explicit fault), or None for controls."""
    if venue == "mexc":
        channel = payload.get("channel")
        if channel not in ("push.depth.full", "push.fair.price"):
            return None
        symbol = str(payload.get("symbol", "")).removesuffix("_USDT")
        kind = "book" if channel == "push.depth.full" else "reference"
    elif venue == "lighter":
        channel = str(payload.get("channel", ""))
        try:
            prefix, market = channel.split(":")
            symbol = names.get(int(market))
        except (ValueError, TypeError):
            return None
        if symbol is None or prefix not in ("ticker", "market_stats"):
            return None
        if payload.get("type") not in ("update/"+prefix, "subscribed/"+prefix):
            return None
        kind = "book" if prefix == "ticker" else "reference"
    else:
        raise ValueError("unknown venue")
    if symbol not in SYMBOLS:
        return None
    try:
        if venue == "mexc":
            data = payload["data"]
            if data.get("symbol", symbol+"_USDT") != symbol+"_USDT":
                raise ValueError("MEXC payload identity mismatch")
            if kind == "reference":
                item = ReferencePrice(venue, symbol, clock, source_ns(payload["ts"], "ms"),
                                      positive(data["price"]), "fair-price WebSocket envelope publication timestamp")
            else:
                meta = metadata[symbol]["mexc"]
                limit = integer(meta["marketOrderMaxLevel"])
                if limit < 1:
                    raise ValueError("invalid market-order depth limit")
                sides = [tuple(DepthLevel(x.price, x.base_quantity(meta["contractSize"]))
                               for x in parse_depth_levels(data[name]))[:limit] for name in ("bids", "asks")]
                depth = DepthSnapshot(symbol, source_ns(data["cts"], "ms"), clock.mono_ns, *sides)
                item = StreamBook(venue, symbol, clock, depth, integer(data["version"]), "reported matching-engine cts (ms)")
        elif kind == "reference":
            data = payload["market_stats"]
            if data.get("symbol") != symbol or data.get("market_id") != int(market):
                raise ValueError("Lighter reference identity mismatch")
            item = ReferencePrice(venue, symbol, clock, source_ns(payload["timestamp"], "ms"),
                                  positive(data["index_price"]), "market-stats envelope publication timestamp")
        else:
            data = payload["ticker"]
            if data.get("s") != symbol:
                raise ValueError("Lighter ticker identity mismatch")
            depth = DepthSnapshot(symbol, source_ns(data["last_updated_at"], "us"), clock.mono_ns,
                                  (DepthLevel(float(positive(data["b"]["price"])), float(positive(data["b"]["size"]))),),
                                  (DepthLevel(float(positive(data["a"]["price"])), float(positive(data["a"]["size"]))),))
            item = StreamBook(venue, symbol, clock, depth, integer(payload["nonce"]), "reported book last_updated_at (us)")
        return kind, symbol, item
    except (ValueError, KeyError, TypeError, AttributeError, OverflowError) as exc:
        return kind, symbol, "invalid:" + str(exc)


def freshness(item, target_ns, anchor):
    if item is None or isinstance(item, str):
        return [item or "missing"]
    utc_now = anchor.utc_ns + target_ns-anchor.mono_ns
    flags = []
    if not 0 <= target_ns-item.clock.mono_ns <= NS:
        flags.append("receive_age_outside_0_1s")
    if not -100_000_000 <= utc_now-item.source_time_ns <= 2*NS:
        flags.append("reported_source_age_outside_minus100ms_2s")
    offset = (item.clock.utc_ns-anchor.utc_ns) - (item.clock.mono_ns-anchor.mono_ns)
    if abs(offset) > 50_000_000:
        flags.append("local_UTC_step_over_50ms")
    return flags


class Replay:
    """One monotonic receive-time sweep. Invalid updates poison a stream until recovery."""
    def __init__(self, frames, metadata, names, anchor, connections):
        self.frames = iter(sorted(frames, key=lambda f: (f["mono_ns"], f["venue"], f["number"])))
        self.next = next(self.frames, None)
        self.metadata, self.names, self.anchor, self.connections = metadata, names, anchor, connections
        self.latest, self.previous, self.errors = {}, {}, Counter()
        self.target = -1

    def advance(self, target):
        if target < self.target:
            raise ValueError("causal replay cannot move backwards")
        self.target = target
        while self.next is not None and self.next["mono_ns"] <= target:
            frame = self.next
            self.next = next(self.frames, None)
            try:
                payload = json.loads(frame["raw"])
                if not isinstance(payload, dict):
                    raise ValueError("non-object frame")
                item = decode(frame["venue"], payload, FrameClock(frame["utc_ns"], frame["mono_ns"]),
                              self.metadata, self.names)
            except (ValueError, TypeError) as exc:
                self.errors["unattributed:"+type(exc).__name__] += 1
                # An unidentified corrupt frame might have been any quote for
                # this venue: invalidate them all rather than keeping a nice book.
                for kind in ("book", "reference"):
                    for symbol in SYMBOLS:
                        self.latest[frame["venue"], kind, symbol] = "unattributed_invalid_frame"
                continue
            if item is None:
                continue
            kind, symbol, observation = item
            key = frame["venue"], kind, symbol
            if isinstance(observation, str):
                self.errors[observation] += 1
                self.latest[key] = observation
                continue
            previous = self.previous.get(key)
            if previous is not None:
                if (observation.source_time_ns < previous.source_time_ns or
                        (kind == "book" and observation.version < previous.version)):
                    self.latest[key] = "source_clock_or_version_regression"
                    self.errors[self.latest[key]] += 1
                    continue
                same = observation.version == previous.version if kind == "book" else observation.source_time_ns == previous.source_time_ns
                if same:
                    if observation.signature != previous.signature:
                        self.latest[key] = "conflicting_duplicate"
                        self.errors["conflicting_duplicate"] += 1
                    # Exact duplicates never refresh first-seen availability,
                    # and cannot clear a prior malformed/conflicting update.
                    continue
            self.latest[key] = self.previous[key] = observation

    def observe(self, symbol, target, quantity=None, *, allow_new_quantity=True):
        self.advance(target)
        flags, books, refs = [], [], []
        for venue in ("mexc", "lighter"):
            connection = self.connections.get(venue, {})
            opened, closed = connection.get("opened_mono_ns"), connection.get("closed_mono_ns")
            if opened is None or not (opened <= target < (closed if closed is not None else 2**63)):
                flags.append(venue+":disconnected")
            item = self.latest.get((venue, "book", symbol))
            flags.extend(venue+":"+s for s in freshness(item, target, self.anchor))
            books.append(item)
            reference = self.latest.get((venue, "reference", symbol))
            ref_flags = freshness(reference, target, self.anchor)
            refs.append({"venue": venue, "flags": ref_flags, "source_role": getattr(reference, "source_role", None),
                         "price": float(reference.price) if isinstance(reference, ReferencePrice) else None,
                         "source_ns": getattr(reference, "source_time_ns", None),
                         "receive_ns": reference.clock.mono_ns if isinstance(reference, ReferencePrice) else None})
        if all(isinstance(b, StreamBook) for b in books):
            for name, delta in (("receive_skew_over_1s", abs(books[0].clock.mono_ns-books[1].clock.mono_ns)),
                                ("source_skew_over_1s", abs(books[0].source_time_ns-books[1].source_time_ns))):
                if delta > NS:
                    flags.append(name)
        row = {"symbol": symbol, "target_mono_ns": target, "book_flags": flags, "execution_ready": False,
               "unresolved": ["market_session_contract", "actual_fill_and_latency", "settlement_notional",
                              "external_source_clock_alignment", "unversioned_MEXC_full_feed_contract"],
               "references": refs, "quantity_base": None, "cost": None}
        try:
            mm, lm = self.metadata[symbol]["mexc"], self.metadata[symbol]["lighter"]
            if not (mm.get("state") == 0 and mm.get("apiAllowed") is True and lm.get("status") == "active"
                    and lm.get("is_frozen") is False and (lm.get("market_config") or {}).get("force_reduce_only") is False):
                flags.append("venue_inactive_API_disabled_or_reduce_only_unknown")
            row["reported_trading_hours"] = (lm.get("market_config") or {}).get("trading_hours")
            if quantity is None and not allow_new_quantity:
                flags.append("no_causal_decision_quantity")
            if not flags:
                if quantity is None:
                    quantity, _ = common_quantity(mm, lm, max(b.mid for b in books))
                else:
                    quantity = positive(quantity)
                row["quantity_base"] = str(quantity)
                row["cost"] = pair_costs(*books, quantity)
                if not row["cost"]["displayed_fillable"]:
                    flags.append("insufficient_displayed_depth")
                if quantity*positive(books[1].bids[0].price) < positive(lm["min_quote_amount"]):
                    flags.append("Lighter_min_quote_not_met")
                    row["cost"] = None
                for reference in refs:
                    reference["notional_usd"] = float(quantity*positive(reference["price"])) if reference["price"] is not None else None
            row["book_source_times_ns"] = [b.source_time_ns if isinstance(b, StreamBook) else None for b in books]
            row["book_receive_times_ns"] = [b.clock.mono_ns if isinstance(b, StreamBook) else None for b in books]
        except (KeyError, ValueError, TypeError) as exc:
            flags.append("metadata_or_quantity:"+str(exc))
        return row, books


def entry_cash_drift(before, after, quantity):
    """Change in quoted entry cash cost, both orientations; no order/holding PnL."""
    q = positive(quantity)
    cash = [[walk(b.asks, q), walk(b.bids, q)] for b in (*before, *after)]
    if any(x is None for side in cash for x in side):
        return None
    (mb0, ms0), (lb0, ls0), (mb1, ms1), (lb1, ls1) = cash
    return {"long_mexc_usd": (mb1-mb0)-(ls1-ls0),
            "long_lighter_usd": (lb1-lb0)-(ms1-ms0)}
