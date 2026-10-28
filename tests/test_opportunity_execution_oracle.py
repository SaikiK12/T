"""Independent oracle self-checks, not an unfrozen R338 diagnostic run."""
from fractions import Fraction as F
import json
import unittest

from scripts.check_opportunity_execution import Money, chain, digest, numeric_event


class OpportunityExecutionOracleTests(unittest.TestCase):
    def event(self, ident, kind='fill', **fields):
        return dict(event_id=ident, kind=kind, venue='mexc', asset='USDT', symbol='ETH',
            quantity='1', price='100', fee='.1', amount=None, **fields)

    def test_cash_is_not_futures_principal_and_flat_trade_pays_costs(self):
        m = Money({('mexc', 'USDT'): 1000}); key = 'mexc', 'USDT'
        opening = self.event('entry'); m.post(opening); m.post(opening)
        self.assertEqual(m.cash(key), F('999.9'))
        closing = self.event('exit'); closing.update(quantity='-1', price='99')
        m.post(closing)
        self.assertEqual(m.cash(key), F('998.8'))
        self.assertEqual(m.positions[(*key, 'ETH')], (0, 0))
        revision = dict(opening, fee='.2')
        with self.assertRaises(ValueError):m.post(revision)

    def test_unknown_amount_requires_matching_resolution(self):
        m = Money({('mexc', 'USDT'): 1000}); entry = self.event('unknown'); entry['fee'] = None
        m.post(entry); self.assertTrue(m.pending)
        resolve = self.event('resolution', 'fee_resolution'); resolve.update(resolves='unknown', amount='.7')
        m.post(resolve); self.assertFalse(m.pending)
        self.assertEqual(m.cash(('mexc', 'USDT')), F('999.3'))

    def test_chain_and_first_clock_tampering_are_detected(self):
        row = {'sequence': 0, 'previous_sha256': '0'*64, 'event': {'data': 1}}
        row['sha256'] = digest(row); raw = json.dumps(row)+'\n'
        self.assertEqual(len(chain(raw)), 1)
        with self.assertRaises(ValueError):chain(raw.rstrip())
        with self.assertRaises(ValueError):chain(raw.replace('"data": 1', '"data": 2'))
        m = Money({('mexc', 'USDT'): 1000}); e = self.event('t'); e['clock'] = {'mono_ns': 1}
        m.post(e)
        with self.assertRaises(ValueError):m.post(dict(e, clock={'mono_ns': 2}))
        self.assertEqual(numeric_event(dict(e, price='100.00')), numeric_event(e))
