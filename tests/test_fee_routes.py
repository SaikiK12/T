import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from decimal import Decimal as D

from lab.depth_replay import DepthReplay
from lab.fee_routes import FeeTerm,PATHS,assess_route,nominal_mexc,routes
from scripts import audit_fee_routes as audit
from tests.test_depth_quotes import depth_frame
from tests.test_stream_quotes import ANCHOR,NS,UTC,frame,metadata
from tests.test_warm_value_probe import fixture as prior_fixture

SOURCES={k:k+'_source' for k in ('metadata','reserve','floor','mexc_advertised','lighter_standard','lighter_premium','lighter_plus')}


def context():
    meta=metadata();mx=meta['BTC']['mexc']
    mx.update(feeRateMode='NORMAL',feeRateType='BASE',isZeroFeeRate=False,isZeroFeeSymbol=False,takerFeeRate=.0002)
    meta['BTC']['lighter']['is_taker_fee_enabled']=True
    receipt={'received_mono_ns':ANCHOR.mono_ns,'received_utc_ns':UTC}
    connections={v:{'opened_mono_ns':0,'closed_mono_ns':100*NS} for v in ('mexc','lighter')}
    replay=DepthReplay([frame('mexc',9.8),depth_frame(9.8)],meta,{1:'BTC'},ANCHOR,connections)
    row,books=replay.observe('BTC',ANCHOR.mono_ns+10*NS)
    return mx,meta['BTC']['lighter'],receipt,row,books


class FeeTests(unittest.TestCase):
    def test_official_notional_fee_fraction_percent_bp_and_reject_unknown_units(self):
        for value,unit in [('0.0002','fraction'),('0.02','percent'),('2','bp')]:
            f=FeeTerm('mexc','BTC',value,unit,'instrument_nominal','official-example')
            self.assertEqual(D(30000)*D(10000)*D('.0001')*f.fraction(),D(6))
        for value,unit in [(True,'bp'),('-1','bp'),('NaN','fraction'),('Infinity','bp'),('1','unknown')]:
            with self.assertRaises(ValueError):FeeTerm('mexc','BTC',value,unit,'instrument_nominal','x')

    def test_zero_temp_tiered_unknown_and_future_are_unscored_nominal_not_inactive_zero(self):
        mx,lm,receipt,row,books=context();when=ANCHOR.mono_ns+10*NS
        mutations=[{'takerFeeRate':0,'isZeroFeeRate':True,'isZeroFeeSymbol':True},{'feeRateType':'TEMP'},
                   {'feeRateMode':'TIERED'},{'isZeroFeeSymbol':None},{'symbol':'ETH_USDT'},{'takerFeeRate':True}]
        for change in mutations:
            term,flags=nominal_mexc('BTC',{**mx,**change},receipt,when,ANCHOR,'metadata')
            self.assertIsNone(term);self.assertTrue(flags)
        for changed in ({**receipt,'received_mono_ns':when+1},{**receipt,'received_utc_ns':UTC+NS},{'received_mono_ns':True}):
            self.assertIsNone(nominal_mexc('BTC',mx,changed,when,ANCHOR,'metadata')[0])

    def test_hand_calculated_fees_crossing_stress_and_original_control(self):
        mx,lm,receipt,row,books=context();rr=routes('BTC',mx,receipt,ANCHOR.mono_ns+10*NS,ANCHOR,SOURCES,lm)
        self.assertEqual(tuple(r['path'] for r in rr),PATHS)
        results={r['path']:assess_route(r,books,row['quantity_base'],0) for r in rr}
        self.assertEqual(results['reserve_control']['cost'],row['cost'])
        self.assertEqual(results['crossing_floor']['cost']['fee_usd'],0)
        # Invented q=2.5 books: MEXC buy252.5/sell247.5; Lighter buy253.7/sell246.3.
        # Crossing12.4; Standard nominal MEXC charge(252.5+247.5)*.0002=.1.
        standard=results['nominal_standard']['cost'];self.assertAlmostEqual(standard['crossing_usd'],12.4)
        self.assertAlmostEqual(standard['fee_usd'],.1)
        for k,x in enumerate(standard['scenarios'],1):self.assertAlmostEqual(x['round_trip_cost_usd'],12.5*k)
        self.assertTrue(all(not z['account_effective_fee_verified'] and not z['fee_schedule_asof_verified'] and not z['execution_ready'] for z in results.values()))

    def test_published_minimum_delay_is_separate_from_total_execution_and_promo_does_not_fall_back(self):
        mx,lm,receipt,row,books=context();mx.update(takerFeeRate=0,isZeroFeeRate=True,isZeroFeeSymbol=True)
        rr=routes('BTC',mx,receipt,ANCHOR.mono_ns+10*NS,ANCHOR,SOURCES,lm)
        for r in rr:
            immediate=assess_route(r,books,row['quantity_base'],0);delayed=assess_route(r,books,row['quantity_base'],300)
            if r['path'].startswith('nominal'):
                self.assertIsNone(immediate['cost']);self.assertTrue(immediate['fee_flags'])
            elif r['path'].startswith('advertised'):
                self.assertIsNotNone(immediate['cost']);self.assertFalse(immediate['minimum_delay_satisfied'])
                self.assertTrue(delayed['minimum_delay_satisfied']);self.assertFalse(delayed['execution_ready'])
        premium=next(r for r in rr if r['path']=='advertised_premium')
        self.assertEqual(premium['minimum_venue_delay_ms'],140)

    def test_instrument_identity_paid_tier_flags_and_bad_book_cannot_create_cost(self):
        mx,lm,receipt,row,books=context()
        for invalid in ({},{'symbol':'ETH','is_taker_fee_enabled':True}):
            rr=routes('BTC',mx,receipt,ANCHOR.mono_ns+10*NS,ANCHOR,SOURCES,invalid)
            for r in rr:
                if r['path'].endswith(('premium','plus')):self.assertIsNone(assess_route(r,books,row['quantity_base'],300)['cost'])
        r=rr[0];bad=FeeTerm('mexc','ETH','10','bp','reserve','x');r={**r,'fees':(bad,r['fees'][1])}
        self.assertIsNone(assess_route(r,books,row['quantity_base'],0)['cost'])
        self.assertIsNone(assess_route(rr[0],books,row['quantity_base'],0,['stale'])['cost'])
        self.assertIsNone(assess_route(rr[0],(None,books[1]),row['quantity_base'],0)['cost'])
        with self.assertRaises(ValueError):assess_route(rr[0],books,row['quantity_base'],140)

    def test_doubled_quantity_doubles_charges_not_rates_or_capital(self):
        mx,lm,receipt,row,books=context();r=routes('BTC',mx,receipt,ANCHOR.mono_ns+10*NS,ANCHOR,SOURCES,lm)[-2]
        a=assess_route(r,books,D('1'),300)['cost'];b=assess_route(r,books,D('2'),300)['cost']
        self.assertAlmostEqual(b['fee_usd'],2*a['fee_usd']);self.assertEqual(a['capital_usd'],b['capital_usd'])


class ReportTests(unittest.TestCase):
    def test_parent_identity_cannot_omit_seal_or_label_seen_data_as_unseen(self):
        with tempfile.TemporaryDirectory() as d,mock.patch.object(audit.parent,'verify'):
            root=Path(d);lane=root/'new';lane.mkdir();prior=root/'experiments/warm_values_v1';prior.mkdir(parents=True)
            paths={}
            for f in ('PREREG.md','PREREG.sha256','code_inputs.json','evidence_inputs.json','results.json','observations.jsonl.gz'):
                p=prior/f;p.write_text('invented-'+f);paths[str(p.relative_to(root))]=hashlib.sha256(p.read_bytes()).hexdigest()
            original={'parent_path':'experiments/warm_values_v1','parent_data_already_seen':True,'sha256':paths}
            with mock.patch.object(audit,'ROOT',root):
                for omit in (False,True):
                    data=json.loads(json.dumps(original))
                    if omit:del data['sha256']['experiments/warm_values_v1/evidence_inputs.json']
                    audit.write(lane/'data_inputs.json',data);(lane/'PREREG.md').write_text(audit.sha(lane/'data_inputs.json'))
                    if omit:
                        with self.assertRaisesRegex(ValueError,'complete fixed parent'):audit.verify(lane)
                    else:audit.verify(lane)
                data=json.loads(json.dumps(original));data['parent_data_already_seen']=False
                audit.write(lane/'data_inputs.json',data);(lane/'PREREG.md').write_text(audit.sha(lane/'data_inputs.json'))
                with self.assertRaisesRegex(ValueError,'complete fixed parent'):audit.verify(lane)

    def test_fixed576_rows_same_books_quantity_control_and_deterministic_report(self):
        with tempfile.TemporaryDirectory() as d,mock.patch.object(audit.parent.depth,'verify'),mock.patch.object(audit.parent.depth.old,'verify'):
            root=Path(d);par=root/'parent';par.mkdir();prior_fixture(par);lane=root/'lane';lane.mkdir()
            audit.write(lane/'sources.json',{'scenario_sources':SOURCES});audit.write(lane/'data_inputs.json',{})
            with mock.patch.object(audit,'verify'),mock.patch.object(audit,'PARENT',par):
                audit.report(lane);audit.report(lane,out=root/'again')
            rows=[json.loads(x) for x in gzip.open(lane/'observations.jsonl.gz','rt')]
            self.assertEqual(len(rows),576)
            chosen=[r for r in rows if r['symbol']=='BTC' and r['grid_second']==10]
            self.assertEqual({r['quantity_base'] for r in chosen},{'2.5'})
            controls=[r for r in chosen if r['fee_path']=='reserve_control']
            self.assertTrue(all(r['cost']==r['reference_reserve_cost'] for r in controls))
            self.assertTrue(all(not r['execution_ready'] and not r['account_effective_fee_verified'] and not r['fee_schedule_asof_verified'] for r in rows))
            for f in ('results.json','observations.jsonl.gz'):self.assertEqual((lane/f).read_bytes(),(root/'again'/f).read_bytes())
            (lane/'results.json').write_text('changed')
            with mock.patch.object(audit,'verify'),mock.patch.object(audit,'PARENT',par):
                with self.assertRaisesRegex(ValueError,'overwrite'):audit.report(lane)
