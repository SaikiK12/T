from dataclasses import replace
from decimal import Decimal as D
import json
import unittest

from lab.executable_quotes import common_quantity
from lab.execution_envelope import execution_envelope,liquidation_quote,quantity_check,size_envelope
from lab.microstructure import DepthLevel as L,DepthSnapshot
from lab.stream_quotes import FrameClock,NS,StreamBook

UTC=1790000000*NS
ANCHOR=FrameClock(UTC,10*NS)
DECISION=ANCHOR.mono_ns+10*NS


def book(venue,second=9.9,bids=((99,100),),asks=((101,100),)):
    clock=FrameClock(UTC+int(second*NS),ANCHOR.mono_ns+int(second*NS))
    return StreamBook(venue,'BTC',clock,DepthSnapshot('BTC',clock.utc_ns,clock.mono_ns,
        tuple(L(float(p),float(q)) for p,q in bids),tuple(L(float(p),float(q)) for p,q in asks)),1,'invented source clock')


def metadata():
    return ({'symbol':'BTC_USDT','contractSize':'.01','volUnit':1,'minVol':1,'maxVol':10000000,'type':1,'settleCoin':'USDT'},
            {'symbol':'BTC','supported_size_decimals':2,'min_base_amount':'.01','min_quote_amount':'10'})


class EnvelopeTests(unittest.TestCase):
    def test_actual_cheaper_venue_minimum_is_not_other_venue_midpoint(self):
        mm,lm=metadata();lm['min_quote_amount']='50'
        books=(book('mexc'),book('lighter',bids=((9,100),),asks=((11,100),)))
        q,_=common_quantity(mm,lm,100,250)
        self.assertEqual(q,D('2.5'))  # frozen sizing alone accepts max-mid proxy
        check=quantity_check(books,mm,lm,q)
        self.assertIn('lighter_actual_quote_minimum',check['reasons'])
        out=execution_envelope(books,books,mm,lm,DECISION,DECISION,ANCHOR)
        self.assertIsNone(out['quantity_base']);self.assertIsNone(out['cost'])

    def test_exact_common_lattice_and_invalid_explicit_quantity(self):
        mm,lm=metadata();mm['volUnit']=3;lm['supported_size_decimals']=1
        books=(book('mexc'),book('lighter'))
        out=execution_envelope(books,books,mm,lm,DECISION,DECISION,ANCHOR)
        self.assertEqual(out['quantity_base'],'2.4');self.assertEqual(out['decision_quantity']['common_step_base'],'0.3')
        bad=execution_envelope(books,books,mm,lm,DECISION,DECISION,ANCHOR,quantity='2.5')
        self.assertIsNone(bad['cost']);self.assertIn('quantity_off_common_lattice',bad['decision_reasons'])

    def test_delayed_observation_keeps_decision_q_and_never_backfills_future_decision(self):
        mm,lm=metadata();before=(book('mexc'),book('lighter'))
        later=tuple(book(v,10.3,bids=((199,100),),asks=((201,100),)) for v in ('mexc','lighter'))
        out=execution_envelope(before,later,mm,lm,DECISION,DECISION+300000000,ANCHOR,venue_delay_ms=(0,300))
        self.assertEqual(out['quantity_base'],'2.5');self.assertEqual(out['cost']['quantity_base'],2.5)
        self.assertTrue(out['minimum_venue_delay_satisfied']);self.assertFalse(out['total_order_latency_verified'])
        future=(book('mexc',10.1),book('lighter',10.1))
        denied=execution_envelope(future,later,mm,lm,DECISION,DECISION+300000000,ANCHOR)
        self.assertIsNone(denied['quantity_base']);self.assertIsNone(denied['cost']);self.assertTrue(denied['decision_reasons'])

    def test_partial_depth_stays_unfillable_not_zero_cost(self):
        mm,lm=metadata();thin=(book('mexc'),book('lighter',bids=((99,.1),),asks=((101,.1),)))
        out=execution_envelope(thin,thin,mm,lm,DECISION,DECISION,ANCHOR)
        self.assertEqual(out['quantity_base'],'2.5')
        self.assertFalse(out['cost']['displayed_fillable']);self.assertNotIn('fee_usd',out['cost'])
        self.assertIn('insufficient_displayed_depth',out['observed_reasons'])

    def test_capital_is_segregated_and_actual_buy_cash_can_breach_even_with_small_mid(self):
        mm,lm=metadata();books=(book('mexc'),book('lighter'))
        out=execution_envelope(books,books,mm,lm,DECISION,DECISION,ANCHOR,quantity=60)
        self.assertIn('mexc:segregated_capital_exceeded',out['decision_reasons']);self.assertIsNone(out['cost'])
        wide=(book('mexc',bids=((10,100),),asks=((190,100),)),book('lighter'))
        check=quantity_check(wide,mm,lm,30)
        self.assertEqual(check['venue_notionals_quote'][0],'3000.0')
        self.assertIn('mexc:segregated_capital_exceeded',check['reasons'])

    def test_finite_size_cases_expose_nonlinear_depth_cost_and_json_output(self):
        mm,lm=metadata();books=tuple(book(v,bids=((99,1),(90,100)),asks=((101,1),(110,100))) for v in ('mexc','lighter'))
        rows=size_envelope(books,books,mm,lm,DECISION,DECISION,ANCHOR,leg_budgets=(100,200),fees_bp=(0,0),adverse_exit_bp=(0,))
        a,b=rows;self.assertEqual((a['quantity_base'],b['quantity_base']),('1','2'))
        self.assertGreater(b['cost']['crossing_usd'],2*a['cost']['crossing_usd'])
        for r in rows:
            self.assertEqual([s['multiple'] for s in r['cost']['scenarios']],[1,2,3])
            self.assertFalse(r['execution_ready']);self.assertFalse(r['actual_fills_verified'])
        json.dumps(rows,allow_nan=False)

    def test_long_and_short_adverse_exit_are_side_specific_and_charge_shifted_cash(self):
        b=book('mexc')
        long=liquidation_quote(b,2,10,DECISION,ANCHOR)
        short=liquidation_quote(b,-2,10,DECISION,ANCHOR)
        self.assertEqual(D(long['close_order_quote_flow']),D('197.8020'))
        self.assertEqual(D(short['close_order_quote_flow']),D('-202.2020'))
        self.assertTrue(long['cash_is_not_futures_pnl'])
        worse_long=liquidation_quote(b,2,10,DECISION,ANCHOR,50)
        worse_short=liquidation_quote(b,-2,10,DECISION,ANCHOR,50)
        self.assertLess(D(worse_long['close_order_quote_flow']),D(long['close_order_quote_flow']))
        self.assertLess(D(worse_short['close_order_quote_flow']),D(short['close_order_quote_flow']))
        self.assertEqual(D(worse_long['fee_quote']),D(worse_long['gross_close_quote'])/1000)
        self.assertTrue(worse_long['hypothetical_adverse_exit']);self.assertFalse(worse_short['actual_fill_verified'])

    def test_unknown_fee_proof_and_minimum_delay_are_not_actual_execution(self):
        mm,lm=metadata();before=(book('mexc'),book('lighter'));after=(book('mexc',10.2),book('lighter',10.2))
        out=execution_envelope(before,after,mm,lm,DECISION,DECISION+200000000,ANCHOR,
                               venue_delay_ms=(0,300),fee_source='caller statement only')
        self.assertIsNotNone(out['cost']);self.assertFalse(out['minimum_venue_delay_satisfied'])
        self.assertEqual(out['decision_to_evaluation_ms'],200)
        self.assertEqual(out['observed_quote_receipt_offset_ms'],[200,200])
        self.assertFalse(out['actual_fees_verified']);self.assertFalse(out['execution_ready'])

    def test_declared_exit_fee_reversion_and_extra_delay_never_invent_future_observation(self):
        mm,lm=metadata();books=(book('mexc'),book('lighter'))
        base=execution_envelope(books,books,mm,lm,DECISION,DECISION,ANCHOR,adverse_exit_bp=(0,))
        stressed=execution_envelope(books,books,mm,lm,DECISION,DECISION,ANCHOR,adverse_exit_bp=(0,),
                                    exit_fees_bp=(20,8),extra_exit_delay_ms=500)
        self.assertEqual(base['cost'],stressed['cost'])  # old same-book reserve untouched
        self.assertEqual(stressed['decision_to_evaluation_ms'],0)
        self.assertEqual(stressed['declared_additional_exit_delay_ms'],500)
        self.assertFalse(stressed['additional_exit_delay_price_effect_verified'])
        for a,b in zip(base['liquidation_quotes'],stressed['liquidation_quotes']):
            self.assertEqual(a['gross_close_quote'],b['gross_close_quote'])
            self.assertEqual(D(b['fee_quote']),2*D(a['fee_quote']))
            self.assertTrue(b['hypothetical_fee_or_delay_change']);self.assertFalse(b['actual_future_exit_observed'])
        self.assertEqual([b.clock.mono_ns for b in books],[ANCHOR.mono_ns+9900000000]*2)

    def test_stale_missing_and_mismatched_books_never_supply_close_cash(self):
        b=book('mexc')
        for invalid,when in ((None,DECISION),(b,DECISION+2*NS),(book('mexc',10.1),DECISION)):
            out=liquidation_quote(invalid,2,10,when,ANCHOR)
            self.assertIsNone(out['close_order_quote_flow']);self.assertTrue(out['reasons'])
        mm,lm=metadata();books=(b,replace(book('lighter'),symbol='ETH'))
        self.assertIsNone(execution_envelope(books,books,mm,lm,DECISION,DECISION,ANCHOR)['quantity_base'])
        with self.assertRaises(ValueError):liquidation_quote(b,True,10,DECISION,ANCHOR)
        with self.assertRaises(ValueError):execution_envelope((b,b),(b,b),mm,lm,DECISION,DECISION-1,ANCHOR)
        with self.assertRaises(ValueError):size_envelope((b,b),(b,b),mm,lm,DECISION,DECISION,ANCHOR,leg_budgets=())
