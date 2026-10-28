"""Receive-time state for the frozen R359 control, without a second money model.

This adapter has no socket, background worker or order capability. Call receive
once at first receipt, in monotonic order, and issue the original control from
that owned prefix. A new connection epoch requires a new adapter. Neither an
offline replay nor a faster calculation changes an old receipt's timeliness.
"""
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import importlib.util
from pathlib import Path

from lab.depth_replay import DepthReplay
from lab.live_pair_control import encoded as original_encoded
from lab.paper_account import _precision
from lab.stream_quotes import integer


@dataclass(frozen=True)
class ReceivedFrame(Mapping):
    """Owned scalar values and their exact canonical encoding; no mutable cache key."""
    fields: tuple
    canonical: bytes

    @classmethod
    def copy(cls, frame):
        value = dict(frame)
        required = {'venue', 'number', 'utc_ns', 'mono_ns', 'raw'}
        if set(value) not in (required, required | {'read_started_mono_ns'}):
            raise ValueError('fixed first-seen frame schema required')
        if value['venue'] not in ('mexc', 'lighter') or not isinstance(value['raw'], str):
            raise ValueError('known venue and raw text required')
        for key in ('number', 'utc_ns', 'mono_ns'):
            integer(value[key])
        if 'read_started_mono_ns' in value:
            integer(value['read_started_mono_ns'])
            if value['read_started_mono_ns'] > value['mono_ns']:
                raise ValueError('read cannot start after first receipt')
        if len(value['raw'].encode()) > 256 * 1024:
            raise ValueError('inherited raw frame cap exceeded')
        return cls(tuple(sorted(value.items())), original_encoded(value))

    def __getitem__(self, key):
        for name, value in self.fields:
            if name == key:
                return value
        raise KeyError(key)

    def __iter__(self):
        return (name for name, _ in self.fields)

    def __len__(self):
        return len(self.fields)


class IncrementalDepthReplay(DepthReplay):
    """Reuse the original decoder/nonce/freshness rules, advancing only a suffix.

    Frames are consumed immediately. There is no unbounded future queue and no
    backfill into a state already observed. Capacity/refusal checks happen before
    mutating the stream. Duplicate CONTENT with a new receipt number is retained
    for the frozen parser; duplicate receipt identity is a caller error.
    """
    def __init__(self, metadata, names, anchor, connections):
        self.owned_metadata, self.owned_names = deepcopy(metadata), deepcopy(names)
        super().__init__([], self.owned_metadata, self.owned_names, anchor, deepcopy(connections))
        self.received = []
        self.last_order_key = None
        self.last_numbers = {}
        self.payload_bytes = {'mexc': 0, 'lighter': 0}
        self.frame_counts = {'mexc': 0, 'lighter': 0}

    @_precision
    def receive(self, frame):
        item = ReceivedFrame.copy(frame)
        order = item['mono_ns'], item['venue'], item['number']
        venue, number = item['venue'], item['number']
        size = len(item['raw'].encode())
        if (item['mono_ns'] < self.target or
                (self.last_order_key is not None and order <= self.last_order_key)):
            raise ValueError('first-seen order cannot regress or be backfilled')
        if number <= self.last_numbers.get(venue, -1):
            raise ValueError('receipt number must progress within one connection epoch')
        if self.frame_counts[venue] >= 20000 or self.payload_bytes[venue] + size > 8 * 1024 * 1024:
            raise ValueError('inherited finite stream capacity exceeded; no reset')
        if self.next is not None or self.next_depth is not None:
            raise ValueError('unconsumed source queue cannot be replaced')
        self.received.append(item)
        self.last_order_key, self.last_numbers[venue] = order, number
        self.frame_counts[venue] += 1
        self.payload_bytes[venue] += size
        self.next, self.frames = item, iter(())
        self.next_depth = item if venue == 'lighter' else None
        self.depth_frames = iter(())
        # The inherited code decodes/poisons/assembles exactly once per source
        # receipt. It also retains the original first-seen and liquidity clocks.
        super().advance(item['mono_ns'])
        return item

    def update_connections(self, connections):
        normalized = {v: {**c, 'closed_mono_ns': c.get('unusable_mono_ns', c.get('closed_mono_ns'))}
                      for v, c in deepcopy(connections).items()}
        for venue in set(self.connections) | set(normalized):
            before, after = self.connections.get(venue, {}), normalized.get(venue, {})
            opened, later_opened = before.get('opened_mono_ns'), after.get('opened_mono_ns')
            if opened is not None and opened != later_opened:
                raise ValueError('connection epoch change requires a new adapter')
            if opened is None and later_opened is not None:
                integer(later_opened)
                if later_opened < self.target:
                    raise ValueError('connection cannot be opened retroactively')
            closed, later_closed = before.get('closed_mono_ns'), after.get('closed_mono_ns')
            if closed is not None and closed != later_closed:
                raise ValueError('a known unusable boundary cannot be reset or widened')
            if closed is None and later_closed is not None:
                integer(later_closed)
                if later_closed < self.target:
                    raise ValueError('connection cannot be closed retroactively')
        self.connections = normalized


class IncrementalPairControl:
    """Instance-local dependency adapter around byte-unchanged R359 source.

    The original class resolves DepthReplay/encoded in its module globals. Load
    its same file into a PRIVATE namespace to inject this instance's maintained
    state/immutable frame encodings. The shared imported module is never patched;
    no financial method or output label is rewritten. Frozen manifests bind both
    files. Exposed original receipts keep R359 identity, with R360 validation in
    the outer experiment report rather than invented new strategy observations.
    """
    def __init__(self, out, metadata, names, anchor, config, connections):
        self.replay = IncrementalDepthReplay(metadata, names, anchor, connections)
        source = Path(__file__).with_name('live_pair_control.py')
        spec = importlib.util.spec_from_file_location('_r360_private_control', source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.parent_source_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()

        def maintained(frames, metadata_arg, names_arg, anchor_arg, connections_arg):
            if (metadata_arg is not self.replay.metadata or names_arg is not self.replay.names or
                    anchor_arg != self.replay.anchor or len(frames) != len(self.replay.received) or
                    any(a is not b for a, b in zip(frames, self.replay.received))):
                raise ValueError('control must use its complete owned first-seen prefix')
            self.replay.update_connections(connections_arg)
            return self.replay

        module.DepthReplay = maintained
        module.encoded = lambda value: value.canonical if isinstance(value, ReceivedFrame) else original_encoded(value)
        self.control = module.LivePairControl(out, self.replay.metadata, self.replay.names, anchor, deepcopy(config))

    def receive(self, frame):
        return self.replay.receive(frame)

    def plan(self, stage, now, connections, *, completed_clock=None):
        return self.control.plan(stage, now, tuple(self.replay.received), connections,
                                 completed_clock=completed_clock)

    def tick(self, stage, now, connections, *, completed_clock=None):
        return self.control.tick(stage, now, tuple(self.replay.received), connections,
                                 completed_clock=completed_clock)

    def report(self, now):
        return self.control.report(now)
