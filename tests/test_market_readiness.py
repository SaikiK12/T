from dataclasses import replace
from decimal import Decimal as D
import json
import unittest

from lab.funding_values import ValuePacket, FundingEvent, FundingContract, PositionSpan
from lab.market_readiness import (InstrumentSpec, SessionWindow, assess_instrument,
    assess_pair, assess_session, assess_settlement, compare_funding_estimate,
    event_value_from_mapping, instrument_from_metadata)
from tests.test_stream_quotes import ANCHOR, NS, UTC, frame, replay, metadata


def clock(s):return type(ANCHOR)(UTC+int(s*NS),ANCHOR.mono_ns+int(s*NS))


def spec(venue='mexc', **kw):
    data=dict(venue=venue, symbol='BTC', instrument_id='BTC_USDT' if venue=='mexc' else 'BTC',
              base_asset='BTC', quote_asset='USDT', settlement_asset='USDT',contract_model='linear_base',
              asset_class='crypto', clock=clock(0), source_identity='invented contract',
              active=True, api_allowed=True, reduce_only=False, frozen=False)
    return InstrumentSpec(**{**data,**kw})


def session(venue='mexc', **kw):
    data=dict(venue=venue,symbol='BTC',state='open',clock=clock(0),source_identity='invented explicit session',
              valid_from_ns=UTC,valid_until_ns=UTC+100*NS,raw_trading_hours='fixture-only grammar')
    return SessionWindow(**{**data,**kw})


def values(s=5):
    return tuple(ValuePacket(v,'BTC',k,D(100),clock(s),UTC+int(s*NS),'WS_publication','invented value')
                 for v,k in (('mexc','fair'),('lighter','index')))


def books(s=5):
    r=replay([frame('mexc',s),frame('lighter',s)])
    return r.observe('BTC',clock(s).mono_ns)[1]


class InstrumentAndSessionTests(unittest.TestCase):
    def test_empty_metadata_hours_never_make_session_or_settlement_asset_known(self):
        m=metadata()['BTC'];m['lighter']['market_type']='perp'
        mx=instrument_from_metadata('mexc','BTC',m['mexc'],clock(0),'public metadata')
        lt=instrument_from_metadata('lighter','BTC',m['lighter'],clock(0),'public metadata')
        self.assertIsNone(mx.asset_class);self.assertIsNone(lt.settlement_asset)
        a=assess_instrument(lt,None,clock(5).mono_ns,ANCHOR)
        self.assertEqual(a['state'],'unknown');self.assertEqual(a['session']['state'],'unknown')
        self.assertFalse(a['account_permission_verified']);self.assertFalse(a['execution_ready'])

    def test_explicit_session_checks_identity_window_source_clock_and_closed_state(self):
        at=clock(5).mono_ns
        self.assertEqual(assess_session(spec(),session(),at,ANCHOR)['state'],'pass')
        self.assertEqual(assess_session(spec(),session(state='closed'),at,ANCHOR)['state'],'blocked')
        self.assertEqual(assess_session(spec(),session(symbol='ETH'),at,ANCHOR)['state'],'blocked')
        self.assertEqual(assess_session(spec(),session(valid_until_ns=UTC+4*NS),at,ANCHOR)['state'],'unknown')
        self.assertEqual(assess_session(spec(),session(state='closed',valid_until_ns=UTC+4*NS),at,ANCHOR)['state'],'unknown')
        self.assertEqual(assess_session(spec(),session(clock=clock(6)),at,ANCHOR)['state'],'blocked')
        self.assertEqual(assess_instrument(spec(),session(state='closed'),at,ANCHOR)['session']['state'],'blocked')

    def test_future_clock_step_unknown_units_and_inactive_instruments_remain_distinct(self):
        at=clock(5).mono_ns
        for change in ({'clock':clock(6)},{'clock':type(ANCHOR)(UTC+NS,ANCHOR.mono_ns)},
                       {'active':False},{'api_allowed':False},{'reduce_only':True},{'frozen':True},{'instrument_id':'ETH_USDT'}):
            self.assertEqual(assess_instrument(spec(**change),None,at,ANCHOR)['state'],'blocked')
        self.assertEqual(assess_instrument(spec(settlement_asset=None),None,at,ANCHOR)['state'],'unknown')
        for key in ('symbol','instrument_id','source_identity','base_asset','quote_asset','settlement_asset'):
            for value in ('', ' ', 123):
                with self.assertRaises(ValueError):spec(**{key:value})


class PairedReadinessTests(unittest.TestCase):
    def assess(self, **kw):
        args=dict(books=books(),specs=(spec(),spec('lighter')),sessions=(session(),session('lighter')),
                  values=values(),asof=clock(5).mono_ns,anchor=ANCHOR)
        return assess_pair(**{**args,**kw})

    def test_complete_supplied_input_pass_is_not_an_execution_or_effective_value_claim(self):
        a=self.assess();self.assertEqual(a['state'],'pass');self.assertTrue(a['input_contract_pass'])
        self.assertFalse(a['execution_ready']);self.assertFalse(a['settlement_cash_verified'])
        self.assertTrue(all(x['effective_value_state']=='unknown' for x in a['observations']))
        json.dumps(a,allow_nan=False)

    def test_missing_session_or_value_is_unknown_but_explicit_fault_is_blocked(self):
        self.assertEqual(self.assess(sessions=(None,None))['state'],'unknown')
        self.assertEqual(self.assess(values=(None,None))['state'],'unknown')
        self.assertEqual(self.assess(books=(None,books()[1]))['state'],'unknown')
        self.assertEqual(self.assess(books=('nonce gap',books()[1]))['state'],'blocked')

    def test_no_future_stale_wrong_symbol_trade_clock_or_wrong_base_can_pass(self):
        for kw in ({'asof':clock(4.9).mono_ns},{'asof':clock(7).mono_ns},
                   {'values':(replace(values()[0],symbol='ETH'),values()[1])},
                   {'values':(replace(values()[0],clock_role='trade_time'),values()[1])},
                   {'specs':(spec(),spec('lighter',base_asset='ETH'))},
                   {'specs':(spec('lighter'),spec())},
                   {'specs':(spec(),spec('lighter',asset_class='metal'))},
                   {'sessions':(session(state='closed'),session('lighter'))}):
            self.assertEqual(self.assess(**kw)['state'],'blocked')

    def test_reference_and_book_skew_are_separate_and_strict(self):
        a=self.assess(values=(values()[0],replace(values()[1],source_time_ns=UTC+3*NS)))
        self.assertIn('value:source_skew_over_1s',a['reasons'])
        with self.assertRaises(ValueError):self.assess(values=(values()[0],))


class FundingInputTests(unittest.TestCase):
    def event(self,stage='settled',**kw):
        data=dict(event_id='evt',venue='lighter',symbol='BTC',funding_ns=UTC+10*NS,
                  rate=D('.01'),rate_unit='percent',stage=stage,clock=clock(12 if stage=='settled' else 5))
        return FundingEvent(**{**data,**kw})

    def setup_inputs(self,q=1):
        c=FundingContract('lighter','BTC','linear_base','USDT',True,'invented contract','BTC','USDT')
        e=self.event();span=PositionSpan(UTC,UTC+30*NS,D(q),clock(30),'lighter','BTC','base')
        p=ValuePacket('lighter','BTC','index',D(100),clock(12),UTC+11*NS,'settlement_value','invented event value',UTC+10*NS,'evt')
        return c,e,[span],p

    def test_complete_event_declaration_is_strict_and_never_borrows_clock_or_proves_bridge(self):
        c,e,spans,p=self.setup_inputs()
        data={**vars(p),'price':str(p.price),'clock':vars(p.clock)}
        parsed=event_value_from_mapping(data);self.assertEqual(parsed,p)
        for change in ({'clock_role':'WS_publication'},{'clock':{'mono_ns':1}},{'price':True}):
            with self.assertRaises(ValueError):event_value_from_mapping({**data,**change})
        a=assess_settlement(c,e,spans,p,clock(30).mono_ns,ANCHOR)
        self.assertEqual(a['state'],'unknown');self.assertIsNone(a['cash_delta'])
        self.assertIn('lighter_preupdate_event_index_basis_unverified',a['reasons'])
        b=assess_settlement(c,e,spans,p,clock(30).mono_ns,ANCHOR,index_basis='pre_update_event_index')
        self.assertEqual(D(b['cash_delta']),D('-.01'));self.assertFalse(b['source_bridge_verified']);self.assertFalse(b['settlement_cash_verified'])

    def test_zero_observed_exposure_is_inactive_while_missing_or_estimated_nonzero_stays_unknown(self):
        c,e,spans,p=self.setup_inputs(q=0)
        a=assess_settlement(c,e,spans,None,clock(30).mono_ns,ANCHOR)
        self.assertEqual(a['model_status'],'inactive');self.assertEqual(D(a['cash_delta']),0)
        b=assess_settlement(c,e,[],None,clock(30).mono_ns,ANCHOR)
        self.assertIsNone(b['cash_delta']);self.assertEqual(b['state'],'unknown')
        self.assertEqual(assess_settlement(c,e,None,None,clock(30).mono_ns,ANCHOR)['state'],'unknown')
        c,e,spans,p=self.setup_inputs()
        b=assess_settlement(c,replace(e,stage='estimated'),spans,p,clock(30).mono_ns,ANCHOR,index_basis='pre_update_event_index')
        self.assertEqual(b['state'],'unknown');self.assertIsNone(b['cash_delta'])

    def test_announcement_error_requires_same_original_event_on_time_units_and_known_settlement(self):
        est=self.event('estimated',rate=D('0'));actual=self.event(rate=D('-.01'))
        a=compare_funding_estimate(est,actual,clock(15).mono_ns,ANCHOR,announcement_source='forecast.json',settlement_source='actual.json')
        self.assertEqual(a['state'],'pass');self.assertEqual(D(a['estimated_fraction']),0)
        self.assertEqual(D(a['error_fraction']),D('-.0001'));self.assertFalse(a['settlement_cash_verified'])
        b=compare_funding_estimate(replace(est,rate=D('-.0001'),rate_unit='fraction'),actual,clock(15).mono_ns,ANCHOR)
        self.assertEqual(D(b['error_fraction']),0)
        for altered in (replace(est,clock=clock(11)),replace(est,event_id='other'),replace(est,event_id=True),replace(est,symbol='ETH'),replace(est,funding_ns=UTC+11*NS)):
            self.assertEqual(compare_funding_estimate(altered,actual,clock(15).mono_ns,ANCHOR)['state'],'blocked')
        for altered in (replace(actual,rate_unit='unknown'),replace(actual,stage='corrected')):
            b=compare_funding_estimate(est,altered,clock(15).mono_ns,ANCHOR)
            self.assertEqual(b['state'],'unknown');self.assertIsNone(b['error_fraction'])
        b=compare_funding_estimate(est,actual,clock(11).mono_ns,ANCHOR)
        self.assertEqual(b['state'],'blocked')
        b=compare_funding_estimate(est,actual,clock(15).mono_ns,ANCHOR,previous_settlement=replace(actual,rate=D(0)))
        self.assertEqual(b['state'],'unknown');self.assertIsNone(b['error_fraction'])
        self.assertEqual(compare_funding_estimate(None,actual,clock(15).mono_ns,ANCHOR)['state'],'unknown')
