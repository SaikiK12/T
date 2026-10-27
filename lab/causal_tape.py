"""First-seen/finalized evidence around the unchanged second-bucket Tape.

Exchange timestamps, observed updates and finalized feature availability are
distinct clocks. This wrapper posts no financial event and certifies no fill.
Create a separate instance for each connection; reconnects never share state.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
import math

from lab.tape import Tape, BOOK, TRADES
from lab.funding_values import clock_known
from lab.paper_account import text
from lab.stream_quotes import FrameClock, NS


@dataclass(frozen=True)
class FinalTapeRow:
    venue: str
    connection: str
    kind: str
    second_ms: int
    symbol: str
    columns: tuple
    values: tuple
    max_received_clock: FrameClock
    finalized_clock: FrameClock
    source_identities: tuple
    complete: bool
    reasons: tuple

    def mapping(self):
        d = asdict(self)
        d['row'] = dict(zip(self.columns, self.values))
        d['actual_execution_ready'] = False
        return d


class CausalTape:
    """One receive-time writer and connection, with append-only evidence.

    An update received after the watermark is evidence of a late omission;
    an already released row is never rewritten. Quality remains stopped for
    this connection. Caller must persist returned evidence with its raw source
    receipt before using this component in an actual prospective protocol.
    """
    def __init__(self, venue, connection, anchor, *, settle_ms=2000):
        for value in (venue, connection):
            text(value)
        if not isinstance(anchor, FrameClock) or type(settle_ms) is not int or settle_ms < 0:
            raise ValueError('typed first-seen anchor and finite settlement grace required')
        self.venue, self.connection, self.anchor = venue, connection, anchor
        self.tape = Tape(settle_ms=settle_ms)
        self.last = anchor.mono_ns
        self.metadata, self.seen = {}, {}
        self.released, self.evidence = [], []
        self.flags = set()
        self.flag_first_seen = {}
        self.closed = False

    def _flag(self, reason, clock):
        self.flags.add(reason)
        self.flag_first_seen.setdefault(reason, clock.mono_ns)

    def _clock(self, clock):
        if (not isinstance(clock, FrameClock) or clock.mono_ns < self.last
                or not clock_known(clock, clock.mono_ns, self.anchor)):
            raise ValueError('nonregressed first-seen clock without UTC step required')
        self.last = clock.mono_ns

    def ingest(self, kind, symbol, source_ms, values, clock, source_identity):
        try:
            return self._ingest(kind, symbol, source_ms, values, clock, source_identity)
        except (ValueError, TypeError) as exc:
            observed_mono = max(self.last, clock.mono_ns) if isinstance(clock, FrameClock) else self.last
            self.flags.add('invalid_input_requires_reconciliation')
            self.flag_first_seen.setdefault('invalid_input_requires_reconciliation', observed_mono)
            self.evidence.append({'status': 'invalid_input_requires_reconciliation',
                'observed_mono_ns': observed_mono, 'error': type(exc).__name__+':'+str(exc)[:256],
                'connection': self.connection})
            self.last = observed_mono
            raise

    def _ingest(self, kind, symbol, source_ms, values, clock, source_identity):
        self._clock(clock)
        text(symbol); text(source_identity)
        if kind not in ('book', 'trade') or type(source_ms) is not int or source_ms < 0:
            raise ValueError('explicit source timestamp and tape event kind required')
        if source_ms*1_000_000 > clock.utc_ns+100_000_000:
            raise ValueError('source timestamp ahead of first-seen clock')
        if type(values) not in (tuple, list) or len(values) != (4 if kind == 'book' else 3):
            raise ValueError('book quadruple or trade price/quantity/side required')
        if any(type(x) not in (float, int) or not math.isfinite(x) for x in values):
            raise ValueError('finite native tape numeric values required')
        if kind == 'book' and not (0 < values[0] < values[2] and values[1] > 0 and values[3] > 0):
            raise ValueError('valid uncrossed book and positive base sizes required')
        if kind == 'trade' and not (values[0] > 0 and values[1] > 0 and values[2] in (-1, 1)):
            raise ValueError('positive trade price/quantity and explicit aggressor sign required')
        signature = hashlib.sha256(json.dumps([kind, symbol, source_ms, values], separators=(',', ':')).encode()).hexdigest()
        status = 'accepted'
        if self.closed:
            status = 'after_connection_close'
        elif source_identity in self.seen:
            status = 'duplicate' if self.seen[source_identity]['signature'] == signature else 'conflicting_source_revision'
            if status != 'duplicate':
                self._flag(status, clock)
        else:
            self.seen[source_identity] = {'signature': signature, 'clock': clock}
            second = source_ms//1000*1000
            if second < self.tape.done.get(self.venue, -1):
                status = 'late_after_finalization'
                self._flag(status, clock)
            else:
                key = (kind, symbol, second)
                old = self.metadata.get(key)
                if old is None:
                    self.metadata[key] = {'clock': clock, 'identities': [source_identity]}
                else:
                    old['clock'] = clock
                    old['identities'].append(source_identity)
                if kind == 'book':
                    self.tape.on_book(self.venue, symbol, source_ms, *values, clock.utc_ns//1_000_000)
                else:
                    self.tape.on_trade(self.venue, symbol, source_ms, *values)
        receipt = {'kind': kind, 'symbol': symbol, 'source_ms': source_ms,
                   'first_seen_clock': asdict(self.seen[source_identity]['clock']) if source_identity in self.seen else asdict(clock),
                   'observed_clock': asdict(clock), 'source_identity': source_identity,
                   'payload_sha256': signature, 'status': status, 'connection': self.connection}
        self.evidence.append(receipt)
        return receipt

    def finalize(self, clock, *, terminal=False):
        self._clock(clock)
        if self.closed or type(terminal) is not bool:
            raise ValueError('one explicit terminal finalization per connection')
        frames = self.tape.drain(None if terminal else clock.utc_ns//1_000_000)
        out = []
        for kind, columns, frame in zip(('book', 'trade'), (BOOK, TRADES), frames.get(self.venue, ([], []))):
            if len(frame) == 0:
                continue
            for raw in frame.itertuples(index=False, name=None):
                row = dict(zip(columns, raw))
                second, symbol = int(row['s']), row['sym']
                meta = self.metadata.pop((kind, symbol, second))
                reasons = set(self.flags)
                mature = clock.utc_ns >= (second+1000+self.tape.settle_ms)*1_000_000
                if not mature:
                    reasons.add('terminal_bucket_before_settlement_grace')
                if meta['clock'].mono_ns > clock.mono_ns:
                    raise ValueError('finalized feature precedes its own received input')
                values = tuple(None if isinstance(x, float) and not math.isfinite(x) else x for x in raw)
                item = FinalTapeRow(self.venue, self.connection, kind, second, symbol, tuple(columns), values,
                    meta['clock'], clock, tuple(meta['identities']), not reasons, tuple(sorted(reasons)))
                self.released.append(item); out.append(item)
        if terminal:
            self.closed = True
        return out

    def readiness(self, item, asof_mono_ns):
        if not isinstance(item, FinalTapeRow) or type(asof_mono_ns) is not int:
            raise ValueError('typed finalized evidence and monotonic decision required')
        reasons = set(item.reasons) | {reason for reason, first_seen in self.flag_first_seen.items()
                                      if first_seen <= asof_mono_ns}
        if not any(item is released for released in self.released):
            reasons.add('finalized_row_not_issued_by_this_connection')
        if item.venue != self.venue or item.connection != self.connection:
            reasons.add('wrong_connection')
        if item.finalized_clock.mono_ns > asof_mono_ns or item.max_received_clock.mono_ns > asof_mono_ns:
            reasons.add('feature_not_received_and_finalized_at_decision')
        if not item.complete:
            reasons.add('incomplete_feature')
        return {'finalized_feature_known': not reasons, 'reasons': sorted(reasons),
                'actual_execution_ready': False, 'fills_fees_sessions_and_forecast_unverified': True}


def legacy_availability(row):
    """A historical s/lag aggregate cannot authenticate finalized availability."""
    if not isinstance(row, dict) or 's' not in row or 'sym' not in row:
        raise ValueError('explicit legacy tape row required')
    return {'finalized_feature_known': None, 'actual_execution_ready': False,
            'reasons': ['finalized_first_seen_clock_absent', 'connection_identity_absent'],
            'exchange_second_is_not_availability': True}
