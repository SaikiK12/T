"""R361: apply source updates once, export books only for an observation.

Extends the frozen R360 source contract. Parser/state transitions and R359
financial decisions stay unchanged. Repeated same-state/asof/profile exports
are cached; a new receipt, asof, profile or connection boundary invalidates it.
"""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path

from lab.depth_replay import DepthReplay
from lab.incremental_pair_control import IncrementalDepthReplay, IncrementalPairControl, ReceivedFrame
from lab.live_pair_control import encoded
from lab.paper_account import _precision
from lab.stream_quotes import FrameClock, Replay


class DeferredDepthReplay(IncrementalDepthReplay):
    def __init__(self, metadata, names, anchor, connections):
        super().__init__(metadata, names, anchor, connections)
        self.generation = 0
        self.materialized_key = None
        self.materializations = 0

    @_precision
    def receive(self, frame):
        # Same finite ownership/order/capacity contract as R360. The only
        # changed work is separating original decoding/consume from export.
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
        self.generation += 1
        self.next, self.frames = item, iter(())
        Replay.advance(self, item['mono_ns'])
        if venue == 'lighter':
            try:
                payload = json.loads(item['raw'])
            except (ValueError, TypeError):
                payload = None
            clock = FrameClock(item['utc_ns'], item['mono_ns'])
            for symbol, state in self.states.items():
                result = state.consume(payload, clock, epoch=self.subscription_epochs[symbol])
                if result.status != 'ignored':
                    self.assembly_events[(symbol, result.status, result.reason or '')] += 1
        # latest is private intermediate decode state. Only observe()/control
        # issue exports an assembled book, with the original guards at its asof.
        return item

    def advance(self, target):
        if target < self.target:
            raise ValueError('causal replay cannot move backwards')
        boundaries = tuple((v, c.get('opened_mono_ns'), c.get('closed_mono_ns'))
                           for v, c in sorted(self.connections.items()))
        key = self.generation, target, self.profile, boundaries
        if key != self.materialized_key:
            DepthReplay.advance(self, target)
            self.materialized_key = key
            self.materializations += 1


class DeferredPairControl(IncrementalPairControl):
    """Same original controller and R360 public adapter API, new source engine."""
    def __init__(self, out, metadata, names, anchor, config, connections):
        self.replay = DeferredDepthReplay(metadata, names, anchor, connections)
        source = Path(__file__).with_name('live_pair_control.py')
        spec = importlib.util.spec_from_file_location('_r361_private_control', source)
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
        module.encoded = lambda value: value.canonical if isinstance(value, ReceivedFrame) else encoded(value)
        self.control = module.LivePairControl(out, self.replay.metadata, self.replay.names, anchor, deepcopy(config))
