"""R314 paired-depth replay with a same-state top-level capacity control.

Reuse the frozen R313 clock/MEXC/reference/quantity/cost contract. Lighter depth
adds explicit subscription epochs and atomic nonce-linked reconstruction. No
clock or tradability guard is relaxed, no own fill or open session is inferred.
"""
from collections import Counter
from dataclasses import replace
import json

from lab.lighter_depth_state import LighterDepthState
from lab.stream_quotes import FrameClock, Replay, StreamBook


class DepthReplay(Replay):
    def __init__(self, frames, metadata, names, anchor, connections):
        frames = list(frames)
        connections = {v:{**c, "closed_mono_ns":c.get("unusable_mono_ns",c.get("closed_mono_ns"))}
                       for v,c in connections.items()}
        super().__init__(frames, metadata, names, anchor, connections)
        self.depth_frames = iter(sorted((f for f in frames if f["venue"] == "lighter"),
                                        key=lambda f: (f["mono_ns"], f["number"])))
        self.next_depth = next(self.depth_frames, None)
        self.states = {s: LighterDepthState(m, s) for m, s in names.items()}
        # Saved at subscription creation, not stamped with a later state epoch.
        self.subscription_epochs = {s: state.epoch for s, state in self.states.items()}
        self.assembly_events = Counter()
        self.profile = "full"
        self.disconnected = False

    def advance(self, target):
        super().advance(target)
        while self.next_depth is not None and self.next_depth["mono_ns"] <= target:
            frame = self.next_depth
            self.next_depth = next(self.depth_frames, None)
            clock = FrameClock(frame["utc_ns"], frame["mono_ns"])
            try:
                payload = json.loads(frame["raw"])
            except (ValueError, TypeError):
                payload = None
            for symbol, state in self.states.items():
                result = state.consume(payload, clock, epoch=self.subscription_epochs[symbol])
                if result.status != "ignored":
                    self.assembly_events[(symbol, result.status, result.reason or "")] += 1
        closed = self.connections.get("lighter", {}).get("closed_mono_ns")
        if closed is not None and closed <= target and not self.disconnected:
            for state in self.states.values():
                state.invalidate("transport disconnected")
            self.disconnected = True
        for symbol, state in self.states.items():
            try:
                book = state.as_stream_book()
                flags = [f for f in state.freshness_flags(target, self.anchor) if f.startswith("state_")]
                if flags:
                    book = ";".join(flags)
                elif self.profile == "top_only":
                    book = replace(book, depth=replace(book.depth, bids=book.bids[:1], asks=book.asks[:1]))
            except ValueError as exc:
                book = "assembled_depth_unavailable:" + str(exc)
            self.latest["lighter", "book", symbol] = book

    def observe(self, symbol, target, quantity=None, *, allow_new_quantity=True, profile="full"):
        if profile not in ("full", "top_only"):
            raise ValueError("fixed depth profile required")
        self.profile = profile
        row, books = super().observe(symbol, target, quantity, allow_new_quantity=allow_new_quantity)
        state = self.states.get(symbol)
        row["depth_profile"] = profile
        row["lighter_assembly"] = ({"status": state.status, "reason": state.reason,
            "epoch": self.subscription_epochs[symbol], "nonce": state.nonce, "offset": state.offset,
            "last_state_receive_ns": getattr(state.last_state_clock, "mono_ns", None),
            "liquidity_receive_ns": getattr(state.liquidity_clock, "mono_ns", None),
            "reported_last_state_us": state.reported_time_us,
            "reported_liquidity_us": state.liquidity_time_us} if state else None)
        row["shown_levels"] = [[len(b.bids), len(b.asks)] if isinstance(b, StreamBook) else None for b in books]
        if symbol in self.metadata:
            m, l = self.metadata[symbol]["mexc"], self.metadata[symbol]["lighter"]
            row["session_metadata"] = {"mexc_state": m.get("state"), "mexc_api_allowed": m.get("apiAllowed"),
                "lighter_status": l.get("status"), "lighter_is_frozen": l.get("is_frozen"),
                "lighter_force_reduce_only": (l.get("market_config") or {}).get("force_reduce_only"),
                "lighter_trading_hours_raw": (l.get("market_config") or {}).get("trading_hours"),
                "permission_certified": False}
        row["unresolved"].append("Lighter_depth_tail_and_idle_freshness_contract")
        return row, books
