"""Fail-closed Lighter full-depth assembly, separate from executable freshness.

Source: official WS order_book contract (unversioned, inspected 2026-10-24)
and elliottech/lighter-python a7a9ba88514d38a863a33642acd41f8adf442e5c,
lighter/ws_client.py. Updates replace absolute size, zero deletes a price;
begin_nonce links the previous nonce, offsets increase but need not be adjacent.
The SDK's side-merging example does not maintain these metadata invariants.

Conservative policies beyond explicit documentation are named in the code:
ambiguous duplicates, missing/regressing fields and gaps require a reset plus
replacement snapshot; no-change batches do not renew liquidity freshness.
Consistency is not a venue guarantee of idle freshness, fills or sessions.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import isfinite

from lab.microstructure import DepthLevel, DepthSnapshot
from lab.stream_quotes import FrameClock, StreamBook, freshness, integer, source_ns


@dataclass(frozen=True)
class AssemblyResult:
    status: str
    changed: bool
    reason: str | None = None


def _decimal(value, *, price):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError("numeric price/size required")
    try:
        out = Decimal(str(value))
        projected = float(out)
    except (InvalidOperation, ValueError, OverflowError) as exc:
        raise ValueError("unrepresentable price/size") from exc
    if not out.is_finite() or not isfinite(projected) or out < 0 or (price and out == 0):
        raise ValueError("positive finite price and nonnegative finite size required")
    if out > 0 and projected <= 0:
        raise ValueError("price/size underflows export representation")
    return out


class LighterDepthState:
    """One market, one subscription epoch. Never automatically reconnects/resyncs.

    reset() is an explicit discontinuity. Invalid state cannot export liquidity;
    a fresh snapshot is required after reset. last_state_clock/reported_time_us
    describe a valid received batch; liquidity_clock/liquidity_time_us remain
    unchanged on duplicate, empty or ineffective batches. That last policy is
    intentionally conservative, not a claimed exchange heartbeat contract.
    Capture epoch at subscription creation and pass that saved token with each
    frame. Never stamp buffered frames with the state's epoch at receive time.
    The transport owner must invalidate on disconnect or subscription failure.
    """
    def __init__(self, market_id, symbol, *, max_levels=10_000):
        self.market_id = integer(market_id)
        if not isinstance(symbol, str) or not symbol or any(c.isspace() for c in symbol):
            raise ValueError("nonempty base symbol required")
        self.symbol = symbol
        self.max_levels = integer(max_levels)
        if self.max_levels < 1:
            raise ValueError("positive level capacity required")
        self.epoch = -1
        self.reset()

    def reset(self):
        self.epoch += 1
        self.status, self.reason = "snapshot_required", None
        self.nonce = self.offset = self.reported_time_us = None
        self.last_state_clock = self.liquidity_clock = None
        self.liquidity_time_us = None
        self._bids, self._asks, self._fingerprint = {}, {}, None
        return self.epoch

    def invalidate(self, reason):
        """Transport-level disconnect/failure: keep diagnostics but block exports."""
        if not isinstance(reason,str) or not reason:
            raise ValueError("explicit failure reason required")
        return self._fault(reason)

    def _fault(self, reason):
        self.status, self.reason = "invalid", reason
        return AssemblyResult("invalid", False, reason)

    def _levels(self, rows):
        if not isinstance(rows, list) or len(rows) > self.max_levels:
            raise ValueError("missing/oversized level batch")
        levels = {}
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("level must name price and size")
            price, size = _decimal(row["price"], price=True), _decimal(row["size"], price=False)
            # The docs do not define ordering for repeated prices in a batch.
            if price in levels:
                raise ValueError("ambiguous duplicate price in batch")
            levels[price] = size
        return levels

    def consume(self, payload, clock, *, epoch):
        if not isinstance(clock, FrameClock):
            raise ValueError("validated receive clock required")
        if integer(epoch) != self.epoch:
            return AssemblyResult("stale_epoch",False)
        if not isinstance(payload, dict):
            return self._fault("non-object frame")
        kind = payload.get("type")
        if kind in ("error","shutdown"):
            return self._fault("subscription/transport error frame")
        if kind in ("ping","pong","connected"):
            return AssemblyResult("ignored",False)
        if kind not in ("subscribed/order_book", "update/order_book", "unsubscribed/order_book"):
            if (payload.get("channel") == f"order_book:{self.market_id}" or not isinstance(kind,str)
                    or not kind or not isinstance(payload.get("channel"),str)):
                return self._fault("unrecognized or unattributable book dispatch")
            return AssemblyResult("ignored", False)  # ping/pong/trades never refresh book state
        channel = payload.get("channel")
        if (not isinstance(channel,str) or not channel.startswith("order_book:")
                or not channel[11:].isascii() or not channel[11:].isdigit()):
            return self._fault("unattributable book channel identity")
        if channel != f"order_book:{self.market_id}":
            return AssemblyResult("ignored", False)
        if kind == "unsubscribed/order_book":
            return self._fault("book subscription ended")
        if self.status == "invalid":
            return AssemblyResult("invalid", False, self.reason)
        try:
            data = payload["order_book"]
            if integer(data["code"]) != 0:
                raise ValueError("book service error")
            nonce, offset = integer(data["nonce"]), integer(data["offset"])
            begin = integer(data["begin_nonce"]) if "begin_nonce" in data else None
            stamp = integer(data["last_updated_at"])
            source_ns(stamp, "us")  # configured units; no fallback/guessing
            # These duplicate-field checks are selected conservatism, not a
            # separately documented equality guarantee. Outer timestamp is a
            # different publication clock and is never used as book-event time.
            if "offset" in payload and integer(payload["offset"]) != offset:
                raise ValueError("envelope/nested offset conflict")
            if "last_updated_at" in payload and payload["last_updated_at"] is not None:
                if integer(payload["last_updated_at"]) != stamp:
                    raise ValueError("envelope/nested update-clock conflict")
            bids, asks = self._levels(data["bids"]), self._levels(data["asks"])
            fingerprint = (kind, begin, nonce, offset, stamp, tuple(sorted(bids.items())), tuple(sorted(asks.items())))
            if fingerprint == self._fingerprint:
                return AssemblyResult("duplicate", False)
            if self.last_state_clock is not None and clock.mono_ns < self.last_state_clock.mono_ns:
                raise ValueError("receive clock regressed")
            snapshot = kind == "subscribed/order_book"
            if snapshot:
                if self.status != "snapshot_required":
                    raise ValueError("replacement snapshot requires explicit epoch reset")
                new_bids = {p:q for p,q in bids.items() if q > 0}
                new_asks = {p:q for p,q in asks.items() if q > 0}
            else:
                if self.status != "ready":
                    raise ValueError("update before initial snapshot")
                if begin is None or begin != self.nonce:
                    raise ValueError("nonce chain gap")
                if nonce < begin or offset <= self.offset:
                    raise ValueError("nonce/offset regression or conflicting retransmission")
                if self.reported_time_us is not None and stamp is not None and stamp < self.reported_time_us:
                    raise ValueError("reported update clock regressed")
                new_bids, new_asks = self._bids.copy(), self._asks.copy()
                for updates, side in ((bids,new_bids),(asks,new_asks)):
                    for price,size in updates.items():
                        if size == 0:
                            side.pop(price,None)
                        else:
                            side[price] = size  # absolute replacement, never additive volume
            if max(len(new_bids),len(new_asks)) > self.max_levels:
                raise ValueError("full state exceeds declared capacity; no truncation")
            if new_bids and new_asks and max(new_bids) >= min(new_asks):
                raise ValueError("crossed or locked assembled book")
            changed = snapshot or new_bids != self._bids or new_asks != self._asks
            if not snapshot and nonce == begin and changed:
                raise ValueError("level mutation without advancing nonce")
            # Commit all data and metadata only after every validation passes.
            self._bids, self._asks = new_bids, new_asks
            self.nonce, self.offset, self.reported_time_us = nonce, offset, stamp
            self.last_state_clock = clock
            self._fingerprint = fingerprint
            if changed:
                self.liquidity_clock, self.liquidity_time_us = clock, stamp
            self.status, self.reason = "ready", None
            return AssemblyResult("snapshot" if snapshot else "updated" if changed else "no_effect", changed)
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            return self._fault(str(exc))

    def as_stream_book(self):
        """Export the existing cost/freshness contract, never a live-ready order."""
        if self.status != "ready" or self.liquidity_clock is None or self.liquidity_time_us is None:
            raise ValueError("consistent snapshot and known effective-level event clock required")
        bids = tuple(DepthLevel(float(p),float(self._bids[p])) for p in sorted(self._bids,reverse=True))
        asks = tuple(DepthLevel(float(p),float(self._asks[p])) for p in sorted(self._asks))
        depth = DepthSnapshot(self.symbol,source_ns(self.liquidity_time_us,"us"),self.liquidity_clock.mono_ns,bids,asks)
        return StreamBook("lighter",self.symbol,self.liquidity_clock,depth,self.nonce,
                          "last effective level-mutation reported clock (us), uncertified provenance")

    def freshness_flags(self, target_mono_ns, anchor):
        flags = []
        if self.last_state_clock is not None:
            if self.last_state_clock.mono_ns > target_mono_ns:
                flags.append("state_received_after_deadline")
            offset = ((self.last_state_clock.utc_ns-anchor.utc_ns)
                      -(self.last_state_clock.mono_ns-anchor.mono_ns))
            if abs(offset) > 50_000_000:
                flags.append("state_local_UTC_step_over_50ms")
        try:
            return flags+freshness(self.as_stream_book(),target_mono_ns,anchor)
        except ValueError as exc:
            return flags+["unavailable:"+str(exc)]
