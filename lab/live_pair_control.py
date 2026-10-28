"""Deadline-issued, no-signal shadow controls; no network or activation.

Known price/fee components use the native fixed-inventory account. Full funding,
fees, session/permission, matching and margin qualification remain separate and
unknown. These controls cannot certify executable net or strategy paper days.
"""
from dataclasses import asdict
from decimal import Decimal as D, localcontext
import hashlib
import json
from pathlib import Path
import time

from lab.depth_replay import DepthReplay
from lab.execution_envelope import quantity_check
from lab.executable_quotes import common_quantity
from lab.funding_values import clock_known
from lab.paper_account import PaperAccount, PaperEvent, _precision
from lab.execution_envelope import liquidation_quote
from lab.settlement_account import EntryLeg, SettlementAccount, _exact_shown_notional, _stressed
from lab.stream_quotes import FrameClock, StreamBook, NS, SYMBOLS


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def book_mapping(book):
    if not isinstance(book, StreamBook):
        return None
    value = {'venue': book.venue, 'symbol': book.symbol, 'clock': asdict(book.clock),
             'source_time_ns': book.source_time_ns, 'version': book.version,
             'bids': [[x.price, x.size] for x in book.bids],
             'asks': [[x.price, x.size] for x in book.asks]}
    if len(encoded(value)) > 65536:
        raise ValueError('full observed book exceeds declared snapshot evidence cap')
    return value


class LivePairControl:
    """One writer; all snapshot decisions are made from then-received frames."""
    def __init__(self, out, metadata, names, anchor, config):
        self.out, self.metadata, self.names = Path(out), metadata, names
        self.anchor, self.config = anchor, config
        self.out.mkdir(exist_ok=False)
        self.cells, self.receipts = {}, []
        self.symbols = tuple(config['symbols'])
        if self.symbols != SYMBOLS:
            raise ValueError('unchanged fixed six-symbol universe required')
        self.next_stage = 0
        self.plans = {}
        balances = {('mexc', 'USDT'): D(config['capital_per_venue']),
                    ('lighter', 'USDC'): D(config['capital_per_venue'])}
        for symbol in self.symbols:
            for direction in config['directions']:
                for k in config['cost_multiples']:
                    key = f'{symbol}_d{direction}_k{k}'
                    account = PaperAccount(balances, anchor, journal_path=self.out / (key + '.jsonl'))
                    self.cells[key] = {'symbol': symbol, 'direction': direction, 'cost_multiple': k,
                        'account': account, 'adapter': SettlementAccount(account, k),
                        'entry': None, 'exit': None, 'quantity': None, 'admission_reasons': []}
        self.cash = PaperAccount(balances, anchor, journal_path=self.out / 'cash_reference.jsonl')

    def _persist(self, receipt, completed_clock):
        # Hash the complete snapshot/planned quantity BEFORE the execution
        # deadline is set. Generation and actual persistence completion differ.
        self.cash.record_evidence('recovery', {'stage': receipt['stage'],
            'decision_clock': receipt['decision_clock'], 'planned_mono_ns': receipt['planned_mono_ns'],
            'receipt_sha256': hashlib.sha256(encoded(receipt)).hexdigest()})
        with (self.out / 'online_receipts.jsonl').open('ab') as handle:
            handle.write(encoded(receipt)); handle.flush()
        finished = completed_clock() if completed_clock is not None else FrameClock(**receipt['decision_clock'])
        if finished.mono_ns < receipt['decision_clock']['mono_ns']:
            raise ValueError('actual issue completion clock cannot precede decision')
        receipt['issued_clock'] = asdict(finished)
        receipt['on_time'] = finished.mono_ns <= receipt['planned_mono_ns'] + self.config['deadline_lateness_ns']
        with (self.out / 'online_receipts.jsonl').open('ab') as handle:
            handle.write(encoded({'kind': 'receipt_completion', 'stage': receipt['stage'],
                                 'issued_clock': asdict(finished), 'on_time': receipt['on_time']})); handle.flush()
        self.receipts.append(receipt)
        return receipt

    @_precision
    def plan(self, stage, now, frames, connections, *, completed_clock=None):
        if stage in self.plans or stage not in ('entry', 'exit'):
            raise ValueError('each original decision may be planned once')
        if stage == 'exit' and self.next_stage != 1:
            raise ValueError('entry execution must precede exit decision')
        planned = self.anchor.mono_ns + self.config[stage + '_second'] * NS
        if now.mono_ns < planned or not clock_known(now, now.mono_ns, self.anchor):
            raise ValueError('causal actual planning clock required')
        if any(f['mono_ns'] > now.mono_ns for f in frames):
            raise ValueError('future input in plan')
        replay = DepthReplay(list(frames), self.metadata, self.names, self.anchor, connections)
        quantities = {}
        views = {}
        for symbol in self.symbols:
            row, books = replay.observe(symbol, now.mono_ns)
            reasons = list(row['book_flags'])
            q = None
            if symbol == 'XPD':
                reasons.append('predeclared_metal_session_negative_control')
            if stage == 'entry' and not reasons:
                try:
                    mm, lm = self.metadata[symbol]['mexc'], self.metadata[symbol]['lighter']
                    q, _ = common_quantity(mm, lm, max(b.mid for b in books), self.config['leg_budget'])
                    reasons.extend(quantity_check(books, mm, lm, q, 2 * D(self.config['capital_per_venue']))['reasons'])
                except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
                    reasons.append('fixed_lot_quantity:' + str(exc))
            try:
                snaps = [book_mapping(b) for b in books]
            except ValueError as exc:
                snaps = []; reasons.append(str(exc))
            quantities[symbol] = None if q is None or reasons else str(q)
            views[symbol] = {'row': row, 'books': snaps, 'quantity': quantities[symbol], 'reasons': reasons}
        receipt = {'stage': stage + '_decision', 'planned_mono_ns': planned, 'decision_clock': asdict(now),
                   'views': views, 'simulation_only': True, 'actual_execution_ready': False,
                   'strategy_evidence_eligible': False,
                   'source_prefixes': {v: {'frames': len([f for f in frames if f['venue'] == v]),
                       'sha256': hashlib.sha256(b''.join(encoded(f) for f in frames if f['venue'] == v)).hexdigest()}
                       for v in ('mexc', 'lighter')}}
        receipt = self._persist(receipt, completed_clock)
        receipt['execution_not_before_ns'] = receipt['issued_clock']['mono_ns'] + self.config['decision_to_execution_ns']
        self.plans[stage] = receipt
        return receipt

    @_precision
    def tick(self, stage, now, frames, connections, *, completed_clock=None):
        """now is the actual evaluation clock, never a reconstructed deadline."""
        expected = ('entry', 'exit')
        if self.next_stage >= 2 or stage != expected[self.next_stage]:
            raise ValueError('each original deadline must issue once, in order')
        if not isinstance(now, FrameClock) or not clock_known(now, now.mono_ns, self.anchor):
            raise ValueError('actual coherent decision UTC/monotonic clock required')
        if stage not in self.plans:
            raise ValueError('a persisted original decision must precede execution')
        planned = self.plans[stage]['execution_not_before_ns']
        if now.mono_ns < planned:
            raise ValueError('deadline cannot be issued early')
        if any(f['mono_ns'] > now.mono_ns for f in frames):
            raise ValueError('future frame supplied to current decision')
        lateness = now.mono_ns - planned
        source = {v: [f for f in frames if f['venue'] == v] for v in ('mexc', 'lighter')}
        prefix = {v: {'frames': len(xs), 'sha256': hashlib.sha256(b''.join(encoded(x) for x in xs)).hexdigest()}
                  for v, xs in source.items()}
        replay = DepthReplay(list(frames), self.metadata, self.names, self.anchor, connections)
        views = {}
        for symbol in self.symbols:
            original_quantity = self.plans['entry']['views'][symbol]['quantity']
            row, books = replay.observe(symbol, now.mono_ns,
                None if original_quantity is None else D(original_quantity), allow_new_quantity=False)
            reasons = list(row['book_flags'])
            if symbol == 'XPD':
                reasons.append('predeclared_metal_session_negative_control')
            snapshots = []
            try:
                snapshots = [book_mapping(b) for b in books]
            except ValueError as exc:
                reasons.append(str(exc))
            q = None
            if stage == 'entry':
                original = self.plans['entry']['views'][symbol]
                reasons.extend(original['reasons'])
                if not self.plans['entry']['on_time']:
                    reasons.append('late_entry_decision_no_new_position')
                q = None if original['quantity'] is None else D(original['quantity'])
            if stage == 'entry' and not reasons and q is not None:
                try:
                    mm, lm = self.metadata[symbol]['mexc'], self.metadata[symbol]['lighter']
                    check = quantity_check(books, mm, lm, q, 2 * D(self.config['capital_per_venue']))
                    reasons.extend(check['reasons'])
                except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
                    reasons.append('fixed_lot_quantity:' + str(exc))
            if stage == 'entry' and lateness > self.config['deadline_lateness_ns']:
                reasons.append('late_entry_no_new_position')
            if stage == 'entry' and q is None:
                reasons.append('no_original_decision_quantity')
            views[symbol] = {'row': row, 'books': snapshots, 'quantity': None if q is None else str(q),
                             'reasons': list(dict.fromkeys(reasons))}
            for direction in self.config['directions']:
                for k in self.config['cost_multiples']:
                    key = f'{symbol}_d{direction}_k{k}'
                    cell = self.cells[key]
                    adapter = cell['adapter']
                    if stage == 'entry':
                        cell['admission_reasons'] = list(views[symbol]['reasons'])
                        if reasons:
                            cell['entry'] = {'state': 'blocked', 'reasons': list(views[symbol]['reasons'])}
                        else:
                            legs = []
                            for venue, asset, side, book in zip(('mexc', 'lighter'), ('USDT', 'USDC'),
                                                               (-direction, direction), books):
                                signed = q * side
                                with localcontext() as context:
                                    context.prec = 80
                                    p = _exact_shown_notional(book, -signed) / abs(signed)
                                legs.append(EntryLeg(venue, asset, symbol, signed, p, D(str(book.mid)),
                                    D(self.config['fees_bp'][venue]), now,
                                    'R359 conditional shown-book sweep:' + venue + ':' + str(book.version)))
                            cell['entry'] = adapter.enter_pair(key, legs, now.mono_ns)
                            cell['quantity'] = str(q)
                    elif cell['entry'] and cell['entry']['state'] == 'conditional_model':
                        closed = {}
                        for venue, asset, book in zip(('mexc', 'lighter'), ('USDT', 'USDC'), books):
                            # Old paired freshness/connection/session/identity flags
                            # veto exits as well. No thin or disconnected close.
                            if reasons:
                                closed[venue] = {'state': 'unknown', 'reasons': list(views[symbol]['reasons'])}
                            else:
                                # The immutable old adapter timestamps hypothetical
                                # closes at quote receipt. Here the online modeled
                                # action occurs NOW, after the persisted decision;
                                # the original quote clock remains unchanged.
                                held = cell['account'].positions.get((venue, asset, symbol), (D(0),))[0]
                                if held == 0:
                                    closed[venue] = {'state': 'already_flat'}
                                    continue
                                quote = liquidation_quote(book, held, D(self.config['fees_bp'][venue]),
                                                          now.mono_ns, self.anchor)
                                if quote['state'] != 'conditional':
                                    closed[venue] = quote
                                    continue
                                p = _stressed(_exact_shown_notional(book, held) / abs(held), D(str(book.mid)), k)
                                fee = abs(held) * p * D(self.config['fees_bp'][venue]) * k / 10000
                                event = PaperEvent(key + ':' + venue + ':exit', 'fill', venue, asset, symbol,
                                    now.utc_ns, now, 'R359 conditional shown-book sweep:' + venue + ':' + str(book.version),
                                    quantity=-held, price=p, fee=fee, reference_mid=D(str(book.mid)))
                                posted = cell['account'].post(event, now.mono_ns)
                                closed[venue] = {'state': 'conditional_model', 'event': posted, 'price': str(p),
                                    'quantity': str(-held), 'fee': str(fee), 'source_first_seen_clock': asdict(book.clock),
                                    'model_action_clock': asdict(now), 'actual_fill_verified': False}
                        cell['exit'] = closed
                    else:
                        cell['exit'] = {'state': 'inactive_or_entry_blocked'}
        receipt = {'stage': stage + '_execution', 'planned_mono_ns': planned, 'decision_clock': asdict(now),
                   'lateness_ns': lateness,
                   'source_prefixes': prefix, 'views': views, 'simulation_only': True,
                   'actual_execution_ready': False, 'strategy_evidence_eligible': False}
        receipt = self._persist(receipt, completed_clock)
        self.next_stage += 1
        return receipt

    @_precision
    def report(self, now):
        records = []
        for key, cell in self.cells.items():
            account = cell['account']
            native = account.snapshot(now.mono_ns)
            reopen = PaperAccount(account.initial, self.anchor, journal_path=account.journal_path)
            if reopen.snapshot(now.mono_ns) != native:
                raise ValueError('native restart differs from issued financial state')
            fx = self.config.get('fx_scenario')
            fx_known = isinstance(fx, dict) and all(r['asset'] in fx for r in native['accounts'])
            if fx_known and any(not D(str(v)).is_finite() or D(str(v)) <= 0 for v in fx.values()):
                raise ValueError('explicit positive finite FX scenario required')
            known_component = (sum((D(r['known_realized_net_component']) * D(str(fx[r['asset']]))
                                    for r in native['accounts']), D(0)) if fx_known else None)
            flat = all(not r['positions'] for r in native['accounts'])
            entered = bool(cell['entry'] and cell['entry']['state'] == 'conditional_model')
            records.append({k: v for k, v in cell.items() if k not in ('account', 'adapter')}
                           | {'id': key, 'price_fee_only_native_snapshot': native,
                              'known_realized_price_fee_component': None if known_component is None else str(known_component),
                              'closed_price_fee_subtotal': str(known_component) if entered and flat and fx_known else None,
                              'funding_needed_to_break_even': str(-known_component) if entered and flat and fx_known else None,
                              'price_fee_fx_scenario': fx,
                              'funding_cash': None, 'full_net_pnl': None, 'full_account_nav': None,
                              'actual_expected_net': None, 'actual_execution_ready': False,
                              'prospective_strategy_days': 0, 'funding_coverage_verified': False})
        return {'registry_id': 'R359', 'cells': records, 'online_receipts': self.receipts,
                'missed_stages': ['entry', 'exit'][self.next_stage:],
                'cash_reference': self.cash.snapshot(now.mono_ns),
                'diagnostic_variants': 12, 'cost_cells': 36, 'prospective_strategy_days': 0,
                'actual_expected_net': None, 'funding_cash': None, 'full_net_pnl': None,
                'scope': 'on-time issued controls and known price/fee components; no actual fills, funding or strategy qualification'}
