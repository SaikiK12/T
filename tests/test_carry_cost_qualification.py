"""Invented source qualification; no live endpoints or historical return reads."""
import contextlib
from decimal import Decimal
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from lab import prereg
from scripts import qualify_carry_costs as q


def mexc(symbol='AAA_USDT', key='AAA'):
    return dict(symbol=symbol, baseCoin=key, quoteCoin='USDT', settleCoin='USDT',
                type=1, state=0, apiAllowed=True, contractSize='.1', volUnit=1,
                takerFeeRate='.0002')


def kucoin(symbol='AAAUSDTM', key='AAA'):
    return dict(symbol=symbol, baseCurrency=key, quoteCurrency='USDT', settleCurrency='USDT',
                type='FFWCSX', status='Open', isInverse=False, expireDate=None,
                multiplier='.1', lotSize=1)


def book():
    return dict(success=True, code=0, data=dict(symbol='AAA_USDT', version=7,
        timestamp=1_790_000_000_000, bids=[['99', 1000, 2]], asks=[['101', 1000, 3]]))


def hanging_worker(url, connection, limit, seconds):
    connection.send(('status', (200, {})))
    connection.send(('chunk', b'{"partial":'))
    time.sleep(8)


class CarrySourceQualificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.table = self.root/'symbols.csv'
        self.table.write_text('key,kucoin,dydx,lighter,mexc\nBBB,BBBUSDTM,,,BBB_USDT\nAAA,AAAUSDTM,,,AAA_USDT\n')

    def frozen(self, **options):
        plan = q.make_plan(self.table, **options)
        protocol = self.root/'PREREG.md'
        protocol.write_text('Registry id: R999\nPlan SHA256: '+plan['plan_sha256']+'\n\n```inputs\n'+
            ''.join(f'{sha}  {name}\n' for name, sha in plan['inputs'].items())+'```\n')
        prereg.freeze(protocol)
        return plan, protocol

    def transport(self, *, status=200, incomplete=False, raw_override=None):
        self.calls = []
        def get(url, limit, seconds):
            self.calls.append((url, limit, seconds))
            if 'depth/' in url: payload = book()
            elif 'kucoin' in url: payload = dict(code='200000', data=[kucoin(),kucoin('BBBUSDTM','BBB')])
            else: payload = dict(success=True, code=0, data=[mexc(),mexc('BBB_USDT','BBB')])
            raw = json.dumps(payload).encode() if raw_override is None else raw_override
            return dict(http_status=status, headers={}, complete=not incomplete, error=None,
                        worker_reaped=True, started_mono_ns=1, received_mono_ns=2), raw
        return get

    def test_plan_keeps_whole_cohort_and_selects_depth_without_pnl(self):
        a=q.make_plan(self.table,depth_contracts=1)
        self.assertEqual(a,q.make_plan(self.table,depth_contracts=1))
        self.assertEqual(len(a['cohort']),2)
        self.assertEqual(a['mexc_depth_candidates'],['AAA_USDT'])
        self.assertIn('UNKNOWN',a['fees']);self.assertFalse(a['actual_order_allowed'])
        with self.assertRaises(ValueError):q.make_plan(self.table,depth_contracts=3)

    def test_metadata_fields_are_qualified_without_adopting_advertised_fees(self):
        r=q.qualify('mexc','AAA','AAA_USDT',{'AAA_USDT':mexc()})
        self.assertEqual(r['status'],'REPORTED_METADATA_QUALIFIED')
        self.assertEqual(r['multiplier_base'],'0.1')
        self.assertIsNone(r['owner_fees'])
        self.assertFalse(r['execution_allowed'])
        for changes in ({'apiAllowed':False},{'contractSize':None},{'baseCoin':'OTHER'},
                        {'settleCoin':'USDC'},{'type':True},{'volUnit':'.5'}):
            r=q.qualify('mexc','AAA','AAA_USDT',{'AAA_USDT':dict(mexc(),**changes)})
            self.assertEqual(r['status'],'UNSCORED',changes)

    def test_kucoin_inverse_and_missing_contract_never_become_linear_pairs(self):
        self.assertEqual(q.qualify('kucoin','AAA','AAAUSDTM',{'AAAUSDTM':kucoin()})['status'],
                         'REPORTED_METADATA_QUALIFIED')
        for changes in ({'isInverse':True},{'settleCurrency':'BTC'},{'expireDate':123},{'multiplier':None}):
            self.assertEqual(q.qualify('kucoin','AAA','AAAUSDTM',{'AAAUSDTM':dict(kucoin(),**changes)})['status'],'UNSCORED')
        self.assertEqual(q.qualify('kucoin','AAA','',{})['status'],'NOT_IN_TABLE')

    def test_snapshot_contract_units_and_unknown_cost_components(self):
        rule=q.qualify('mexc','AAA','AAA_USDT',{'AAA_USDT':mexc()})
        r=q.snapshot_walk('AAA_USDT',rule,book(),'1000')
        self.assertEqual(Decimal(r['buy']['vwap']),101)
        self.assertEqual(Decimal(r['buy']['impact_bp']),100)
        self.assertLess(abs(Decimal(r['sell']['impact_bp'])-100),Decimal('1e-60'))
        self.assertIsNone(r['fees_quote']);self.assertIsNone(r['round_trip_cost'])
        self.assertFalse(r['observed_fills']);self.assertFalse(r['sequence_continuity_verified'])
        short=book();short['data']['asks'][0][1]=1
        self.assertEqual(q.snapshot_walk('AAA_USDT',rule,short,'1000')['buy']['state'],'UNSCORED')

    def test_crossed_unsorted_missing_clock_and_bad_depth_units_are_rejected(self):
        rule=q.qualify('mexc','AAA','AAA_USDT',{'AAA_USDT':mexc()})
        for change in (dict(bids=[['102',1000,2]]),dict(timestamp=None),dict(version=True),
                       dict(asks=[['101',1000,2],['100',1000,1]]),dict(asks=[['101',1000]])):
            b=book();b['data'].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):q.snapshot_walk('AAA_USDT',rule,b,'1000')

    def test_capture_requires_exact_frozen_inputs_before_any_request(self):
        plan,protocol=self.frozen()
        self.table.write_text(self.table.read_text().replace('BBB_USDT','CCC_USDT'))
        transport=self.transport()
        with self.assertRaises(ValueError):q.capture(plan,self.root/'out',protocol,transport=transport)
        self.assertEqual(self.calls,[]);self.assertFalse((self.root/'qualification.started.json').exists())

    def test_capture_retains_all_rows_receipts_and_stops_a_second_attempt(self):
        plan,protocol=self.frozen(depth_contracts=1)
        result=q.capture(plan,self.root/'out',protocol,transport=self.transport())
        self.assertEqual(len(self.calls),3);self.assertEqual(len(result['rows']),2)
        self.assertIsNone(result['pair_pnl']);self.assertIsNone(result['owner_fees'])
        self.assertTrue(all(r['pair_execution_cost'] is None for r in result['rows']))
        self.assertEqual(len(list((self.root/'out').glob('*.receipt.json'))),3)
        self.assertTrue((self.root/'qualification.started.json').exists())
        with self.assertRaises(FileExistsError):q.capture(plan,self.root/'another',protocol,transport=self.transport())
        self.assertEqual(self.calls,[])

    def test_access_denial_stops_without_trying_another_venue(self):
        plan,protocol=self.frozen(depth_contracts=2)
        result=q.capture(plan,self.root/'out',protocol,transport=self.transport(status=451))
        self.assertEqual(len(self.calls),1)
        self.assertEqual(result['stop_reason'],'access_backoff_transport_or_body_failure')
        self.assertTrue(all(r['venues']['kucoin']['status']=='UNSCORED' for r in result['rows']))
        self.assertTrue((self.root/'out'/'mexc_metadata.json.gz').exists())

    def test_uncertain_body_tail_charges_full_reservation_and_remains_unscored(self):
        plan,protocol=self.frozen()
        result=q.capture(plan,self.root/'out',protocol,transport=self.transport(incomplete=True,raw_override=b'{'))
        self.assertEqual(result['body_read_upper_bound'],q.BODY_LIMIT)
        self.assertEqual(len(self.calls),1)

    def test_duplicate_source_fields_are_not_silently_accepted(self):
        with self.assertRaises(ValueError):q.json_object(b'{"success":true,"success":false}')
        with self.assertRaises(ValueError):q.metadata_rows('mexc',dict(success=True,code=0,data=[mexc(),mexc()]))

    def test_default_cli_plans_without_fetch_or_output(self):
        with patch.object(q,'fetch',side_effect=AssertionError('network')),contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(q.main(['--symbols',str(self.table)]),0)
        self.assertEqual(json.loads(out.getvalue())['state'],'DRY_PLAN')
        self.assertFalse((self.root/'qualification.started.json').exists())

    def test_owned_hanging_worker_is_reaped_under_absolute_deadline(self):
        started=time.monotonic()
        receipt,raw=q.fetch('https://fixture.invalid',64,3,worker=hanging_worker)
        self.assertLess(time.monotonic()-started,5)
        self.assertTrue(receipt['worker_reaped'])
        self.assertFalse(receipt['complete'])
        self.assertEqual(raw,b'{"partial":')


if __name__=='__main__':unittest.main()
