"""Independent invented unit/lot/cost examples, never market observations."""
from copy import deepcopy
from decimal import Decimal
import unittest

from lab import carry_snapshot_cost as c


def metadata(venue, **changes):
    if venue == 'mexc':
        row = dict(symbol='AAA_USDT', baseCoin='AAA', quoteCoin='USDT', settleCoin='USDT',
                   type=1, state=0, apiAllowed=False, contractSize='.1', volUnit=1, minVol=1)
        row.update(changes); return dict(success=True, code=0, data=row)
    row = dict(symbol='AAAUSDTM', baseCurrency='AAA', quoteCurrency='USDT', settleCurrency='USDT',
               type='FFWCSX', status='Open', isInverse=False, expireDate=None, multiplier='.15', lotSize=1)
    row.update(changes); return dict(code='200000', data=row)


def rules(venue, **changes):
    return c.contract(venue, 'AAA', 'AAA_USDT' if venue == 'mexc' else 'AAAUSDTM', metadata(venue, **changes))


def payload(venue, bid='99', ask='101', size=1000):
    if venue == 'mexc':
        return dict(version=1, timestamp=1790000000000, bids=[[bid,size,2]], asks=[[ask,size,2]])
    return dict(code='200000', data=dict(symbol='AAAUSDTM', sequence=1, ts=1790000000000000000,
                                       bids=[[bid,size]], asks=[[ask,size]]))


def snapshot(venue, rule=None, **kwargs):
    rule = rules(venue) if rule is None else rule
    return c.book(venue, rule['symbol'], rule, payload(venue, **kwargs))


class SnapshotCostTests(unittest.TestCase):
    def test_contract_units_are_distinct_from_owner_access_and_fees(self):
        r=rules('mexc'); self.assertEqual(r['base_quantum'],'0.1')
        self.assertFalse(r['reported_api_trading_flag']); self.assertFalse(r['owner_trading_access_verified'])
        self.assertIsNone(r['owner_fees'])
        self.assertEqual(rules('kucoin')['base_quantum'],'0.15')

    def test_metadata_refuses_identity_inverse_class_and_fractional_lots(self):
        for venue, changes in [('mexc',{'symbol':'OTHER'}),('mexc',{'type':2}),
            ('mexc',{'contractSize':'0'}),('mexc',{'volUnit':'.5'}),('mexc',{'minVol':'.5'}),
            ('kucoin',{'isInverse':True}),('kucoin',{'expireDate':123}),('kucoin',{'status':'Closed'})]:
            with self.subTest(venue=venue,changes=changes),self.assertRaises(ValueError): rules(venue,**changes)

    def test_filtered_metadata_must_be_exclusively_request_bound(self):
        p=metadata('mexc'); p['data']=[p['data'],deepcopy(p['data'])]
        with self.assertRaises(ValueError):c.contract('mexc','AAA','AAA_USDT',p)

    def test_book_contract_volume_becomes_base_volume_and_clock_is_not_authenticated(self):
        b=snapshot('kucoin'); self.assertEqual(b['asks'][0],(Decimal(101),Decimal(150)))
        self.assertEqual(b['reported_time_unit'],'provider_raw_unqualified')
        self.assertFalse(b['source_clock_authenticated']);self.assertFalse(b['sequence_continuity_verified'])

    def test_bad_tuples_lots_order_and_clocks_refuse(self):
        for changes in (dict(asks=[['101',1000]]),dict(bids=[['102',1000,2]]),dict(timestamp=True),
                        dict(asks=[['101',1000,2],['100',1000,2]]),dict(asks=[['101','.5',2]])):
            p=payload('mexc');p.update(changes)
            with self.subTest(changes=changes),self.assertRaises(ValueError):c.book('mexc','AAA_USDT',rules('mexc'),p)

    def test_common_lot_and_cost_have_independent_exact_reference(self):
        # LCM(.1,.15)=.3; floor(1000/(100*.3))*.3=9.9 base.
        # Each leg costs 9.9 quote vs its own mid; total19.8 /1980 *10000=100bp.
        r=c.pair_cost(rules('mexc'),rules('kucoin'),snapshot('mexc'),snapshot('kucoin'))
        self.assertEqual(Decimal(r['common_base_lot']),Decimal('.3'))
        self.assertEqual(Decimal(r['quantity_base']),Decimal('9.9'))
        for d in r['directions']:
            self.assertEqual(Decimal(d['book_cost_quote']),Decimal('19.8'))
            self.assertEqual(Decimal(d['book_cost_bp']),100)
        self.assertIsNone(r['round_trip_cost']);self.assertIsNone(r['pair_pnl'])
        self.assertTrue(all(t['full_cost'] is None for t in r['cost_tiers']))

    def test_cross_venue_basis_is_not_counted_as_profit(self):
        r=c.pair_cost(rules('mexc'),rules('kucoin'),snapshot('mexc'),snapshot('kucoin',bid='199',ask='201'))
        # Despite a100 quote basis, both directions pay a spread against their own mids.
        self.assertEqual(Decimal(r['quantity_base']),Decimal('4.8'))
        self.assertTrue(all(Decimal(d['book_cost_quote'])==Decimal('9.6') for d in r['directions']))
        self.assertIsNone(r['capital_return'])

    def test_mixed_multilot_contracts_use_rational_lcm(self):
        a,b=rules('mexc',contractSize='.2',volUnit=3,minVol=3),rules('kucoin',multiplier='.125',lotSize=2)
        r=c.pair_cost(a,b,snapshot('mexc',a,size=3000),snapshot('kucoin',b))
        self.assertEqual(Decimal(r['common_base_lot']),3)
        self.assertEqual(Decimal(r['quantity_base']),9)

    def test_insufficient_depth_and_unknown_minimum_stay_unscored(self):
        r=c.pair_cost(rules('mexc'),rules('kucoin'),snapshot('mexc',size=1),snapshot('kucoin',size=1))
        self.assertEqual(r['state'],'UNSCORED');self.assertTrue(all(d['book_cost_bp'] is None for d in r['directions']))
        a=rules('mexc',minVol=None)
        self.assertEqual(c.pair_cost(a,rules('kucoin'),snapshot('mexc',a),snapshot('kucoin'))['state'],'UNSCORED')

    def test_common_lot_exceeding_target_is_not_rounded_up(self):
        a=rules('mexc',contractSize='100')
        r=c.pair_cost(a,rules('kucoin'),snapshot('mexc',a),snapshot('kucoin'))
        self.assertEqual(r['reason'],'common_lot_exceeds_mid_notional_target')

    def test_bad_numeric_inputs_refuse(self):
        for x in (True,0,-1,'NaN','Infinity','1e-19','1e31',None):
            with self.subTest(x=x),self.assertRaises(ValueError):c.amount(x)

    def test_rules_and_snapshot_identity_cannot_be_crossed(self):
        b=snapshot('kucoin');b['symbol']='OTHER'
        with self.assertRaises(ValueError):c.pair_cost(rules('mexc'),rules('kucoin'),snapshot('mexc'),b)
