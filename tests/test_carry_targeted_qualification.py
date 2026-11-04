"""Fake transports and clocks only; no market network or predictive labels."""
import contextlib
from decimal import Decimal
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lab import prereg
from scripts import qualify_carry_costs_targeted as q
from tests.test_carry_snapshot_cost import metadata, payload


class Clock:
    def __init__(self):self.now=10.;self.waits=[]
    def __call__(self):return self.now
    def sleep(self,s):self.waits.append(s);self.now+=s


class TargetedQualificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.table=self.root/'symbols.csv'
        self.table.write_text('key,kucoin,dydx,lighter,mexc\nAAA,AAAUSDTM,,,AAA_USDT\n')
        self.clock=Clock();self.calls=[]

    def frozen(self):
        plan=q.make_plan(self.table);protocol=self.root/'PREREG.md'
        protocol.write_text('Registry id: R999\nPlan SHA256: '+plan['plan_sha256']+'\n```inputs\n'+
            ''.join(f'{sha}  {name}\n' for name,sha in plan['inputs'].items())+'```\n')
        prereg.freeze(protocol);return plan,protocol

    def transport(self, status=200, incomplete=False, override=None):
        def get(url, limit, seconds):
            self.calls.append((url,self.clock(),limit,seconds))
            venue='mexc' if 'mexc.com' in url else 'kucoin'
            raw=json.dumps(metadata(venue) if '/depth' not in url else payload(venue)).encode() if override is None else override
            return dict(http_status=status, complete=not incomplete,error=None,worker_reaped=True,headers={}),raw
        return get

    def run_capture(self, plan, protocol, **opts):
        return q.capture(plan,self.root/'out',protocol,transport=opts.pop('transport',self.transport()),
                         monotonic=self.clock,sleep=self.clock.sleep,**opts)

    def test_plan_retains_all_rows_and_never_renews_r401_budget(self):
        p=q.make_plan();self.assertEqual(len(p['cohort']),28)
        self.assertLessEqual(p['baseline']['body_bytes_upper_bound']+p['max_new_requests']*q.BODY_LIMIT,q.TOTAL_BODY_LIMIT)
        self.assertTrue(all('symbol=' in r['metadata_url'] or '/contracts/' in r['metadata_url'] for r in p['contracts']))

    def test_capture_costs_exact_fixture_and_conservatively_charges_all_reservations(self):
        p,pr=self.frozen();r=self.run_capture(p,pr)
        self.assertEqual(len(self.calls),4)
        self.assertEqual(r['budget']['requests_charged'],5)
        self.assertEqual(r['budget']['body_bytes_charged_upper_bound'],2097152+4*32768)
        self.assertEqual(r['rows'][0]['pair']['state'],'CONDITIONAL_ASYNCHRONOUS_SNAPSHOTS')
        self.assertIsNone(r['pair_pnl']);self.assertFalse(r['actual_order_allowed'])
        self.assertEqual(len(list((self.root/'out').glob('*.receipt.json'))),4)

    def test_second_output_cannot_reset_attempt(self):
        p,pr=self.frozen();self.run_capture(p,pr)
        with self.assertRaises(FileExistsError):q.capture(p,self.root/'another',pr,transport=self.transport())
        self.assertEqual(len(self.calls),4)

    def test_bound_input_drift_refuses_before_marker_or_network(self):
        p,pr=self.frozen();self.table.write_text(self.table.read_text()+'BBB,,,,BBB_USDT\n')
        with self.assertRaises(ValueError):self.run_capture(p,pr)
        self.assertEqual(self.calls,[]);self.assertFalse((self.root/'qualification.started.json').exists())

    def test_denial_and_partial_body_stop_without_second_venue(self):
        p,pr=self.frozen();r=self.run_capture(p,pr,transport=self.transport(status=451,incomplete=True,override=b'{'))
        self.assertEqual(len(self.calls),1);self.assertIsNotNone(r['stop_reason'])
        self.assertEqual(r['budget']['body_bytes_charged_upper_bound'],2097152+32768)
        self.assertEqual(r['rows'][0]['pair']['state'],'UNSCORED')

    def test_404_is_retained_without_retry_or_symbol_substitution(self):
        p,pr=self.frozen();r=self.run_capture(p,pr,transport=self.transport(status=404))
        self.assertEqual(len(self.calls),2);self.assertIsNone(r['stop_reason'])
        self.assertTrue(all(v['reason'].endswith('_404') for v in r['rows'][0]['venues'].values()))

    def test_mexc_metadata_rate_limit_is_enforced_across_contracts(self):
        self.table.write_text(self.table.read_text()+'BBB,,,,BBB_USDT\n')
        p,pr=self.frozen();self.run_capture(p,pr)
        starts=[t for url,t,_,_ in self.calls if 'mexc.com' in url and '/detail' in url]
        self.assertEqual(len(starts),2);self.assertGreaterEqual(starts[1]-starts[0],5.1)
        self.assertTrue(all(b[1]-a[1]>=1 for a,b in zip(self.calls,self.calls[1:])))

    def test_duplicate_nonfinite_and_decimal_precision(self):
        for raw in (b'{"a":1,"a":2}',b'{"a":NaN}'):
            with self.assertRaises(ValueError):q.decode(raw)
        self.assertEqual(q.decode(b'{"a":0.123456789012345678}')['a'],Decimal('0.123456789012345678'))

    def test_cli_default_only_plans(self):
        with patch.object(q.source,'fetch',side_effect=AssertionError('network')),contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(q.main([]),0)
        self.assertEqual(json.loads(out.getvalue())['state'],'DRY_PLAN')
