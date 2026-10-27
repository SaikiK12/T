from copy import deepcopy
from datetime import datetime,timezone
from fractions import Fraction as F
from pathlib import Path
import tempfile
import unittest

from lab.executable_quotes import Receipt
from lab.venue_carry_v2 import spot_rules,prepare,projection,current_flags
from lab.stream_quotes import FrameClock
from scripts.run_same_venue_v2 import model_open
from scripts.check_same_venue_v2 import independent_plan,numeric_tree,chain,Checks

UTC=1790000000*1_000_000_000
EXP=int(datetime(2026,12,25,8,tzinfo=timezone.utc).timestamp()*1_000_000_000)


def inputs(coin='BTC'):
    sr={'result':{'instrument_name':coin+'_USDC','kind':'spot','base_currency':coin,'quote_currency':'USDC',
        'counter_currency':'USDC','contract_size':'.00000001','is_active':True,'is_csr':True,'is_cbe_routed':True,
        'min_trade_amount':'.0001','tick_size':'.01','taker_commission':'.0005'}}
    fr={'result':{'instrument_name':coin+'-25DEC26','kind':'future','instrument_type':'reversed',
        'base_currency':coin,'settlement_currency':coin,'quote_currency':'USD','counter_currency':'USD',
        'settlement_period':'month','expiration_timestamp':EXP//1_000_000,'is_active':True,
        'min_trade_amount':10,'contract_size':10,'tick_size':'.5','taker_commission':'.00035'}}
    sb={'result':{'instrument_name':coin+'_USDC','timestamp':UTC//1_000_000,'state':'open',
        'bids':[['99.5','100']],'asks':[['100.5','100']]}}
    fb={'result':{'instrument_name':coin+'-25DEC26','timestamp':UTC//1_000_000,'state':'open',
        'bids':[['102','10000']],'asks':[['103','10000']]}}
    r=Receipt(UTC-10_000_000,UTC+50_000_000,100_000_000,160_000_000)
    return sr,sb,r,fr,fb,r


def plan(coin='BTC',profile='full',values=None):
    return prepare(coin,1000,profile,*(values or inputs(coin)),expiry_ns=EXP,
        spot_rate='.0005',future_rate='.00035',future_source_identity='invented-not-market-evidence')


class VenueCarryTests(unittest.TestCase):
    def test_typed_route_and_base_amount_identity(self):
        x=inputs()[0];r=spot_rules(x,'BTC')
        self.assertEqual(r.route,'Coinbase-routed');self.assertEqual(r.step,F('.0001'))
        for changed in ({'is_csr':1,'is_cbe_routed':1},{'is_csr':True,'is_cbe_routed':False},
                        {'contract_size':1000},{'contract_size':1},{'counter_currency':'USD'},{'kind':'future'}):
            bad=deepcopy(x);bad['result'].update(changed)
            with self.assertRaises(ValueError):spot_rules(bad,'BTC')

    def test_receipt_cardinality_and_publication_types_cannot_disappear(self):
        r=inputs()[2]
        for receipts,pubs in (([r],[]),([r],[True]),([r],[float(UTC)])):
            with self.assertRaises(ValueError):current_flags(receipts,pubs,r.received_mono_ns)
        self.assertEqual(current_flags([r],[UTC],r.received_mono_ns),[])
        self.assertTrue(current_flags([r],[UTC],r.received_mono_ns+3_000_000_000))

    def test_both_fee_debits_keep_same_quantity_and_full_coin_coverage(self):
        p=plan();quantity=p['spot_base']
        for k in (1,2,3):
            for debit in ('base','quote'):
                v=projection(p,k,'public_standard',debit)
                self.assertTrue(v['coverage']['all_positive_marks_1x_model_coverage'])
                self.assertLessEqual(v['initial_spend_usdc'],p['reserve_usdc'])
                self.assertEqual(sum(q for _,q in v['spot_fills']),quantity)
                self.assertEqual(sum(q for _,q in v['inverse_fills']),1000)
                self.assertIsNone(v['actual_expected_net'])

    def test_top_only_cannot_resize_or_invent_missing_inverse_depth(self):
        x=list(inputs());x[4]=deepcopy(x[4]);x[4]['result']['bids']=[['102','100'],['101.5','2000']]
        self.assertEqual(plan(values=x)['face_usd'],1000)
        with self.assertRaisesRegex(ValueError,'insufficient_shown_depth'):plan(profile='top_only',values=x)

    def test_source_ticks_and_spot_amount_steps_are_checked(self):
        x=list(inputs());x[1]=deepcopy(x[1]);x[1]['result']['asks'][0][0]='100.501'
        with self.assertRaisesRegex(ValueError,'tick'):plan(values=x)
        x=list(inputs());x[1]=deepcopy(x[1]);x[1]['result']['asks'][0][1]='100.00001'
        with self.assertRaisesRegex(ValueError,'increment'):plan(values=x)

    def test_shared_spot_cash_and_virtual_inverse_coin_are_not_duplicate_deposits(self):
        plans={coin:plan(coin) for coin in ('BTC','ETH')}
        with tempfile.TemporaryDirectory() as root:
            model=model_open(plans,['BTC','ETH'],3,'public_standard','base',10000,
                FrameClock(UTC+100_000_000,200_000_000),Path(root)/'state')
            self.assertEqual(model['cash_usdc']+model['spent_usdc'],10000)
            self.assertEqual(len(model['legs']),2)
            for r in model['ownership'].values():
                self.assertEqual(r['same_coin_earmarked'],r['purchased_net_coin'])
                self.assertEqual(r['unearmarked_coin'],0)
                self.assertLess(r['inverse_coin_after_fee'],r['purchased_net_coin'])
            self.assertIsNone(model['actual_expected_net']);self.assertFalse(model['actual_order_allowed'])

    def test_second_coin_cannot_spend_a_separate_copy_of_initial_cash(self):
        plans={coin:plan(coin) for coin in ('BTC','ETH')}
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError,'shared spot model rejected'):
                model_open(plans,['BTC','ETH'],1,'public_standard','quote',1000,
                    FrameClock(UTC+100_000_000,200_000_000),Path(root)/'state')

    def test_larger_public_fee_hint_cannot_lower_registered_cost(self):
        x=list(inputs());x[3]=deepcopy(x[3]);x[3]['result']['taker_commission']='.001'
        self.assertEqual(plan(values=x)['future_rate'],F('.001'))
        self.assertFalse(plan()['actual_order_allowed'])

    def test_independent_raw_unit_and_reserve_derivation_matches_invented_inputs(self):
        values=inputs();data={}
        for name,payload,receipt in (('BTC_spot_rules',values[0],values[2]),('BTC_spot_book',values[1],values[2]),
                ('BTC_future_rules',values[3],values[5]),('BTC_future_book',values[4],values[5])):
            data[name]=(payload['result'],dict(vars(receipt)))
        raw=lambda name:data[name]
        config={'expiry_ns':EXP,'spot_rate':'.0005','future_rate':'.00035'}
        for depth in ('full','top_only'):
            self.assertEqual(numeric_tree(independent_plan(raw,'BTC',1000,depth,config,[])),numeric_tree(plan(profile=depth)))
        data['BTC_spot_rules'][0]['quote_currency']='USD'
        with self.assertRaisesRegex(ValueError,'spot units'):independent_plan(raw,'BTC',1000,'full',config,[])

    def test_independent_journal_chain_detects_changed_cash(self):
        import hashlib,json
        row={'sequence':0,'previous_sha256':'0'*64,'event':{'initial_cash':'10000'}}
        row['sha256']=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        text=json.dumps(row)+'\n';self.assertEqual(chain(text,Checks())[0]['initial_cash'],'10000')
        with self.assertRaisesRegex(AssertionError,'journal hash'):chain(text.replace('10000','20000'),Checks())
