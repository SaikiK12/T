from dataclasses import replace
from decimal import Decimal as D
import unittest

from lab.funding_values import (FundingContract,FundingEvent,FundingLedger,PositionSpan,ValuePacket,
    assess_funding,mexc_rest_fair,paired_values,value_flags)
from tests.test_stream_quotes import ANCHOR,UTC,NS,replay,frame


def clock(s):return type(ANCHOR)(UTC+int(s*NS),ANCHOR.mono_ns+int(s*NS))


def contract(**kw):
    args=dict(venue='mexc',symbol='BTC',model='linear_base',settlement_asset='USDT',asset_verified=True,
        source_version='official worked arithmetic fixture',base_asset='BTC',price_quote_asset='USDT',batch_delay_ns=15*NS)
    return FundingContract(**{**args,**kw})


def event(**kw):
    args=dict(event_id='fixture-event',venue='mexc',symbol='BTC',funding_ns=UTC+10*NS,rate=D('.01'),
        rate_unit='percent',stage='settled',clock=clock(13))
    return FundingEvent(**{**args,**kw})


def exposure(q=1,**kw):
    args=dict(start_ns=UTC,end_ns=UTC+30*NS,quantity=D(q),clock=clock(30),venue='mexc',symbol='BTC',quantity_unit='base')
    return PositionSpan(**{**args,**kw})


def settlement(**kw):
    args=dict(venue='mexc',symbol='BTC',kind='fair',price=D(30000),clock=clock(13),
        source_time_ns=UTC+12*NS,clock_role='settlement_value',source_identity='invented event-bound value',
        effective_value_ns=UTC+12*NS,settlement_event_id='fixture-event')
    return ValuePacket(**{**args,**kw})


def assess(c=None,e=None,spans=None,p=None,at=30):
    return assess_funding(c or contract(),e or event(),spans if spans is not None else [exposure()],
                          p if p is not None else settlement(),clock(at).mono_ns,ANCHOR)


class ValueContractTests(unittest.TestCase):
    def test_rest_system_timestamp_and_receive_are_preserved_without_value_time_claim(self):
        payload={'success':True,'code':0,'data':{'symbol':'BTC_USDT','fairPrice':30000,'timestamp':(UTC+5*NS)//1_000_000}}
        p=mexc_rest_fair(payload,'BTC',clock(5.1),'fixture.json')
        self.assertEqual(p.clock_role,'REST_system');self.assertIsNone(p.effective_value_ns)
        self.assertEqual(p.source_time_ns,UTC+5*NS);self.assertEqual(p.clock,clock(5.1))
        payload['data'].pop('timestamp')
        with self.assertRaises(KeyError):mexc_rest_fair(payload,'BTC',clock(5.1),'fixture.json')

    def test_trade_clock_is_rejected_even_when_recent(self):
        p=ValuePacket('mexc','BTC','fair',D(30000),clock(5),UTC+5*NS,'trade_time','ticker fixture')
        self.assertIn('trade_time_is_not_value_publication',value_flags(p,clock(5.1).mono_ns,ANCHOR))
        self.assertIn('receive_age_outside_0_1s',value_flags(p,clock(7).mono_ns,ANCHOR))

    def test_paired_notional_and_one_bp_sensitivity_are_not_cash_or_different_book_identity(self):
        r=replay([frame('mexc',5),frame('lighter',5)])
        _,books=r.observe('BTC',clock(5).mono_ns)
        p=ValuePacket('mexc','BTC','fair',D(102),clock(5),UTC+5*NS,'REST_system','a')
        l=ValuePacket('lighter','BTC','index',D(103),clock(5),UTC+5*NS,'WS_publication','b')
        x=paired_values((p,l),'2',books,clock(5).mono_ns,ANCHOR)
        self.assertEqual(x['flags'],[]);self.assertFalse(x['cash_certified'])
        self.assertEqual(D(x['products'][0]['reference_notional_quote_units']),D(204))
        self.assertEqual(D(x['products'][1]['quote_units_per_one_bp']),D('.0206'))
        y=paired_values((replace(p,symbol='ETH'),replace(l,symbol='ETH')),'2',books,clock(5).mono_ns,ANCHOR)
        self.assertIsNone(y['products']);self.assertTrue(any('identity' in f for f in y['flags']))

    def test_future_effective_or_publication_time_cannot_certify_settlement(self):
        with self.assertRaises(ValueError):settlement(clock=clock(9))
        with self.assertRaises(ValueError):settlement(source_time_ns=UTC+14*NS)
        with self.assertRaises(ValueError):settlement(effective_value_ns=UTC+13*NS)
        with self.assertRaises(ValueError):event(clock=clock(9))
        with self.assertRaises(ValueError):settlement(clock_role='REST_system')


class FundingCashTests(unittest.TestCase):
    def test_official_linear_example_and_signs_with_explicit_percentage_or_fraction(self):
        #10000 contracts*.0001BTC=1BTC;30000USDT*.01%=3USDT.
        self.assertEqual(assess()['cash_delta'],D(-3))
        self.assertEqual(assess(e=event(rate=D('.0001'),rate_unit='fraction'))['cash_delta'],D(-3))
        self.assertEqual(assess(e=event(rate=D('-.01')))['cash_delta'],D(3))
        self.assertEqual(assess(spans=[exposure(-1)])['cash_delta'],D(3))
        self.assertFalse(assess()['real_account_credit_verified'])

    def test_inverse_example_settles_in_base_coin_and_cannot_use_linear_asset_units(self):
        c=contract(model='inverse_contracts',settlement_asset='BTC',price_quote_asset='USD',contract_quote_value=D(100))
        x=assess(c=c,spans=[exposure(100,quantity_unit='contracts')],p=settlement(price=D(10000)))
        self.assertEqual(x['cash_delta'],D('-.0001'));self.assertEqual(x['asset'],'BTC')
        with self.assertRaises(ValueError):contract(model='inverse_contracts',contract_quote_value=D(100))
        with self.assertRaises(ValueError):contract(settlement_asset='BTC')

    def test_contract_symbol_venue_and_quantity_units_bind_position_coverage(self):
        for kwargs in ({'symbol':'ETH'},{'venue':'lighter'},{'quantity_unit':'contracts'}):
            self.assertIsNone(assess(spans=[exposure(**kwargs)])['cash_delta'])
        self.assertIsNone(assess(c=contract(symbol='ETH'))['cash_delta'])

    def test_rate_units_asset_and_estimate_stage_stay_unknown_instead_of_zero(self):
        for kwargs in ({'rate_unit':'unknown'},{'stage':'estimated'},{'stage':'unknown'}):
            x=assess(e=event(**kwargs));self.assertEqual(x['status'],'unscored');self.assertIsNone(x['cash_delta'])
        x=assess(c=contract(asset_verified=False,settlement_asset=None))
        self.assertIn('settlement_asset_unverified',x['flags'])

    def test_fresh_published_index_or_fair_is_not_a_settlement_value(self):
        p=ValuePacket('mexc','BTC','fair',D(30000),clock(13),UTC+12*NS,'REST_system','snapshot')
        self.assertIn('value_not_bound_to_actual_funding_event',assess(p=p)['flags'])
        self.assertIn('value_not_bound_to_actual_funding_event',assess(p=settlement(settlement_event_id='other-event'))['flags'])

    def test_mexc_window_requires_full_closed_interval_not_a_nominal_instant(self):
        spans=[exposure(0,end_ns=UTC+15*NS),exposure(1,start_ns=UTC+15*NS)]
        self.assertIsNone(assess(spans=spans)['cash_delta'])  #entry5s after nominal may participate
        spans=[exposure(1,end_ns=UTC+15*NS),exposure(0,start_ns=UTC+15*NS)]
        self.assertIsNone(assess(spans=spans)['cash_delta'])
        self.assertIsNone(assess(spans=[exposure(end_ns=UTC+25*NS)])['cash_delta'])
        with self.assertRaises(ValueError):contract(batch_delay_ns=0)

    def test_missing_unknown_or_future_coverage_is_not_flat_inactivity(self):
        self.assertIsNone(assess(spans=[])['cash_delta'])
        self.assertIsNone(assess(spans=[exposure(clock=clock(40))])['cash_delta'])
        with self.assertRaises(ValueError):exposure(end_ns=UTC+40*NS)
        self.assertIsNone(assess(at=20)['cash_delta'])
        flat=assess(spans=[exposure(0)],e=event(rate_unit='unknown',stage='estimated'))
        self.assertEqual(flat['status'],'inactive');self.assertEqual(flat['cash_delta'],0)

    def test_late_exact_event_can_be_known_later_but_never_backfilled_into_earlier_score(self):
        p=settlement(clock=clock(300))
        self.assertIsNone(assess(p=p)['cash_delta'])
        self.assertEqual(assess(p=p,at=300)['cash_delta'],D(-3))
        bad=replace(event(),clock=type(ANCHOR)(clock(13).utc_ns+100_000_000,clock(13).mono_ns))
        self.assertIsNone(assess(e=bad)['cash_delta'])


class FundingLedgerTests(unittest.TestCase):
    def test_unknown_then_exact_is_append_only_and_duplicates_do_not_mint_cash(self):
        ledger=FundingLedger();c,e=contract(),event()
        pub=ValuePacket('mexc','BTC','fair',D(30000),clock(13),UTC+12*NS,'REST_system','snapshot')
        a=ledger.post(c,e,[exposure()],pub,clock(30).mono_ns,ANCHOR)
        b=ledger.post(c,e,[exposure()],settlement(),clock(30).mono_ns,ANCHOR)
        d=ledger.post(c,e,[exposure()],settlement(),clock(30).mono_ns,ANCHOR)
        self.assertEqual([a['status'],b['status'],d['status']],['unscored','model_cash','duplicate'])
        self.assertIsNone(ledger.attempts[0]['cash_delta']);self.assertEqual(d['cash_delta'],0)
        self.assertEqual(ledger.totals,{('mexc','USDT'):D(-3)})

    def test_conflicting_rate_or_event_time_keeps_the_original_cash(self):
        ledger=FundingLedger();ledger.post(contract(),event(),[exposure()],settlement(),clock(30).mono_ns,ANCHOR)
        x=ledger.post(contract(),event(rate=D('.02')),[exposure()],settlement(),clock(30).mono_ns,ANCHOR)
        self.assertEqual(x['status'],'conflicting_revision');self.assertIsNone(x['cash_delta'])
        shifted=event(funding_ns=UTC+3600*NS,clock=clock(3601))
        span=exposure(start_ns=UTC+3500*NS,end_ns=UTC+3700*NS,clock=clock(3700))
        p=settlement(effective_value_ns=UTC+3601*NS,source_time_ns=UTC+3601*NS,clock=clock(3602))
        x=ledger.post(contract(),shifted,[span],p,clock(3700).mono_ns,ANCHOR)
        self.assertEqual(x['status'],'conflicting_event_time');self.assertEqual(ledger.totals[('mexc','USDT')],D(-3))

    def test_equal_rates_at_distinct_events_are_not_deduplicated_and_venues_do_not_net(self):
        ledger=FundingLedger();ledger.post(contract(),event(),[exposure()],settlement(),clock(30).mono_ns,ANCHOR)
        c=contract(venue='lighter',settlement_asset='USDC',price_quote_asset='USDC',batch_delay_ns=0)
        e=event(venue='lighter',event_id='lighter-event')
        p=settlement(venue='lighter',kind='index',settlement_event_id='lighter-event',effective_value_ns=UTC+10*NS)
        x=ledger.post(c,e,[exposure(venue='lighter')],p,clock(30).mono_ns,ANCHOR)
        self.assertEqual(x['cash_delta'],D(-3))
        self.assertEqual(ledger.totals,{('mexc','USDT'):D(-3),('lighter','USDC'):D(-3)})
        e2=event(event_id='next-distinct-event',funding_ns=UTC+3600*NS,clock=clock(3601))
        span=exposure(start_ns=UTC+3500*NS,end_ns=UTC+3700*NS,clock=clock(3700))
        p2=settlement(settlement_event_id='next-distinct-event',effective_value_ns=UTC+3601*NS,
                      source_time_ns=UTC+3601*NS,clock=clock(3602))
        ledger.post(contract(),e2,[span],p2,clock(3700).mono_ns,ANCHOR)
        self.assertEqual(ledger.totals[('mexc','USDT')],D(-6))

    def test_unscored_settled_event_cannot_later_move_its_id_to_a_payable_time(self):
        ledger=FundingLedger()
        pub=ValuePacket('mexc','BTC','fair',D(30000),clock(13),UTC+12*NS,'REST_system','snapshot')
        ledger.post(contract(),event(),[exposure()],pub,clock(30).mono_ns,ANCHOR)
        e=event(funding_ns=UTC+3600*NS,clock=clock(3601))
        p=settlement(effective_value_ns=UTC+3601*NS,source_time_ns=UTC+3601*NS,clock=clock(3602))
        x=ledger.post(contract(),e,[exposure(start_ns=UTC+3500*NS,end_ns=UTC+3700*NS,clock=clock(3700))],p,clock(3700).mono_ns,ANCHOR)
        self.assertEqual(x['status'],'conflicting_event_time');self.assertEqual(ledger.totals,{})
