import unittest

from lab.mexc_spot_wire import decode_depth, fields, MAX_FRAME
from lab.stream_quotes import FrameClock


def vi(n):
    result = bytearray()
    while n > 127:
        result.append((n & 127) | 128);n >>= 7
    return bytes(result) + bytes([n])


def pb(n, value):
    if type(value) is int:return vi(n << 3) + vi(value)
    if isinstance(value,str):value = value.encode()
    return vi((n << 3) | 2) + vi(len(value)) + value


def packet(*, asks=(('101','2'),), bids=(('99','3'),), symbol='BTCUSDT', send=True, extra=b''):
    level = lambda p,q:pb(1,p)+pb(2,q)
    body = b''.join(pb(1,level(*a)) for a in asks) + b''.join(pb(2,level(*b)) for b in bids)
    body += pb(3,'limitDepth')+pb(4,'42')+pb(5,1778075384300)
    return (pb(1,'spot@public.limit.depth.v3.api.pb@BTCUSDT@5')+pb(3,symbol)
            +pb(5,1778075384340)+(pb(6,1778075384350) if send else b'')+pb(303,body)+extra)


class SpotWireTests(unittest.TestCase):
    def setUp(self):self.clock = FrameClock(1800000000000000000,100000000000)

    def test_pinned_tags_are_structural_not_units_or_fills(self):
        r = decode_depth(packet(),self.clock)
        self.assertEqual(r['send_time_raw'],1778075384350)
        self.assertEqual(r['asks'],[('101','2')]);self.assertEqual(r['first_seen']['mono_ns'],self.clock.mono_ns)
        self.assertEqual(r['subscribed_levels'],5)
        self.assertIsNone(r['normalized_source_time_ns']);self.assertIsNone(r['normalized_base_quantities'])
        self.assertFalse(r['executable_quote_eligible'])

    def test_missing_send_time_never_uses_create_lastorder_or_receipt(self):
        r = decode_depth(packet(send=False),self.clock)
        self.assertIsNone(r['send_time_raw']);self.assertIsNone(r['normalized_source_time_ns'])
        self.assertIn('send_time_absent_no_fallback',r['flags'])

    def test_one_side_never_inherits_an_earlier_side(self):
        decode_depth(packet(),self.clock)
        r = decode_depth(packet(asks=()),self.clock)
        self.assertEqual(r['asks'],[]);self.assertIn('one_side_or_both_sides_missing',r['flags'])

    def test_symbol_sort_and_crossed_flags(self):
        r = decode_depth(packet(symbol='OTHER',asks=(('98','1'),('97','1')),bids=(('99','1'),('100','1'))),self.clock)
        for flag in ('channel_symbol_mismatch','asks_not_strictly_ascending','bids_not_strictly_descending','crossed_or_locked_book'):
            self.assertIn(flag,r['flags'])

    def test_mistyped_duplicate_or_other_oneof_rejected(self):
        for extra in (pb(6,1),pb(302,b''),pb(303,b''),pb(6,'not-an-int')):
            with self.subTest(extra=extra),self.assertRaises(ValueError):decode_depth(packet(extra=extra),self.clock)
        with self.assertRaises(ValueError):decode_depth(pb(1,'spot@public.limit.depth.v3.api.pb@BTCUSDT@50'),self.clock)

    def test_no_unbounded_or_malformed_numbers(self):
        for asks in ((('NaN','1'),),(('0','1'),),(('1','-1'),),(('1','Infinity'),),tuple(('101','1') for _ in range(6))):
            with self.subTest(asks=asks),self.assertRaises(ValueError):decode_depth(packet(asks=asks),self.clock)
        self.assertIn('zero_quantity_snapshot_semantics_unknown',decode_depth(packet(asks=(('101','0'),)),self.clock)['flags'])

    def test_truncation_groups_and_frame_bound(self):
        for data in (b'\x80',b'\x0b',b'\x0a\x05hi',b'\x08'+b'\xff'*10,b'0'*(MAX_FRAME+1)):
            with self.subTest(length=len(data)),self.assertRaises(ValueError):fields(data)


if __name__=='__main__':unittest.main()
