"""Invented CSV/ZIPs and fake transport; no market requests or numerical outcomes."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from lab import prereg
from scripts import qualify_metric_archives as q


def archive(day='2026-06-24',labels=None,header=None,symbol='BTCUSDT',member=None):
    labels=labels or [day+' 00:05:00',day+' 00:10:00']
    text=','.join(header or q.COLUMNS)+'\n'+''.join(label+','+symbol+',OPAQUE,NaN,unparsed,,,\n' for label in labels)
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED) as z:
        info=zipfile.ZipInfo(member or 'BTCUSDT-metrics-'+day+'.csv',date_time=(2026,1,1,0,0,0))
        info.compress_type=zipfile.ZIP_DEFLATED
        z.writestr(info,text)
    return out.getvalue()


class MetricArchiveQualificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.calls=[]

    def frozen(self):
        value=q.plan();p=self.root/'PREREG.md'
        p.write_text('Registry id: R999\nPlan SHA256: '+value['plan_sha256']+'\n```inputs\n'+
                     ''.join(f'{sha}  {name}\n' for name,sha in value['inputs'].items())+'```\n')
        prereg.freeze(p);return value,p

    def transport(self,status=200,incomplete=False,wrong_checksum=False,archive_override=None):
        def get(url,limit,seconds):
            self.calls.append(url);day=next(d for d in q.DATES if d in url)
            raw=archive(day) if archive_override is None else archive_override
            if url.endswith('.CHECKSUM'):
                sha='0'*64 if wrong_checksum else hashlib.sha256(raw).hexdigest()
                raw=(sha+'  BTCUSDT-metrics-'+day+'.zip\n').encode()
            return dict(http_status=status,complete=not incomplete,error=None,worker_reaped=True,headers={}),raw
        return get

    def test_metrics_cells_remain_opaque_and_labels_do_not_prove_semantics(self):
        a=q.inspect_labels(archive(),'BTCUSDT-metrics-2026-06-24.zip')
        self.assertEqual(a['row_count'],2);self.assertEqual(a['columns'],q.COLUMNS)
        self.assertFalse(a['numerical_metric_values_interpreted']);self.assertFalse(a['point_in_time_verified'])
        self.assertEqual(a['period_semantics'],'UNKNOWN');self.assertEqual(a['adjacent_steps_not_300_seconds'],0)

    def test_duplicates_gaps_and_order_are_reported_not_silently_repaired(self):
        labels=['2026-06-24 00:05:00','2026-06-24 00:05:00','2026-06-24 00:20:00']
        a=q.inspect_labels(archive(labels=labels),'BTCUSDT-metrics-2026-06-24.zip')
        self.assertEqual(a['duplicate_labels'],1);self.assertEqual(a['adjacent_steps_not_300_seconds'],2)
        self.assertFalse(a['strictly_increasing']);self.assertEqual(a['raw_labels'],labels)

    def test_inclusive_next_day_boundary_is_allowed_without_interval_inference(self):
        a=q.inspect_labels(archive(labels=['2026-06-25 00:00:00']),'BTCUSDT-metrics-2026-06-24.zip')
        self.assertEqual(a['first_label'],'2026-06-25 00:00:00');self.assertEqual(a['period_semantics'],'UNKNOWN')

    def test_wrong_symbol_header_label_date_member_and_width_refuse(self):
        cases=[archive(symbol='OTHER'),archive(header=q.COLUMNS[:-1]),archive(labels=['2026-06-24T00:00:00Z']),
               archive(labels=['2026-06-26 00:00:00']),archive(member='../bad.csv')]
        for raw in cases:
            with self.subTest(raw=hashlib.sha256(raw).hexdigest()),self.assertRaises(ValueError):
                q.inspect_labels(raw,'BTCUSDT-metrics-2026-06-24.zip')

    def test_duplicate_members_and_bounded_expansion_refuse(self):
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:
            z.writestr('a.csv','a\n');z.writestr('b.csv','a\n')
        with self.assertRaises(ValueError):q.inspect_labels(out.getvalue(),'BTCUSDT-metrics-2026-06-24.zip')
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr('BTCUSDT-metrics-2026-06-24.csv','x'*(q.EXPANDED_LIMIT+1))
        with self.assertRaises(ValueError):q.inspect_labels(out.getvalue(),'BTCUSDT-metrics-2026-06-24.zip')

    def test_checksum_binds_exact_filename_and_lowercase_digest(self):
        raw=('a'*64+'  one.zip\n').encode();self.assertEqual(q.checksum(raw,'one.zip'),'a'*64)
        for bad in (raw.replace(b'one',b'two'),raw+raw,raw.upper()):
            with self.assertRaises(ValueError):q.checksum(bad,'one.zip')

    def test_capture_preserves_all_bodies_and_accumulates_full_reservations(self):
        value,p=self.frozen();a=q.capture(value,p,self.root/'evidence',transport=self.transport())
        self.assertEqual(len(self.calls),4);self.assertEqual(len(a['archives']),2)
        self.assertEqual(a['budget']['body_bytes_charged_upper_bound'],262144)
        self.assertFalse(a['returns_read']);self.assertIsNone(a['pair_pnl'])
        self.assertTrue(all(t['net_pnl'] is None for t in a['cost_tiers']))
        self.assertEqual(len(list((self.root/'evidence').glob('*.receipt.json'))),4)

    def test_guard_blocks_different_output_after_attempt(self):
        value,p=self.frozen();q.capture(value,p,self.root/'evidence',transport=self.transport())
        with self.assertRaises(FileExistsError):q.capture(value,p,self.root/'other',transport=self.transport())
        self.assertEqual(len(self.calls),4)

    def test_changed_plan_or_protocol_refuses_before_dispatch(self):
        value,p=self.frozen();value['max_requests']=5
        with self.assertRaises(ValueError):q.capture(value,p,self.root/'evidence',transport=self.transport())
        self.assertEqual(self.calls,[]);self.assertFalse((self.root/'qualification.started.json').exists())

    def test_denial_partial_tail_and_checksum_mismatch_stop(self):
        value,p=self.frozen();a=q.capture(value,p,self.root/'evidence',transport=self.transport(status=451,incomplete=True))
        self.assertEqual(len(self.calls),1);self.assertIsNotNone(a['stop_reason'])
        self.assertEqual(a['budget']['body_bytes_charged_upper_bound'],65536)

    def test_mismatched_published_hash_never_decodes_archive(self):
        value,p=self.frozen();a=q.capture(value,p,self.root/'evidence',transport=self.transport(wrong_checksum=True))
        self.assertEqual(len(self.calls),2);self.assertEqual(a['archives'],{})
        self.assertIn('checksum mismatch',a['stop_reason'])

    def test_default_cli_only_plans(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:self.assertEqual(q.main([]),0)
        self.assertEqual(json.loads(out.getvalue())['state'],'DRY_PLAN')

    def test_unsupported_compression_refuses_before_decompression(self):
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_BZIP2) as z:
            z.writestr('BTCUSDT-metrics-2026-06-24.csv','a\n')
        with self.assertRaises(ValueError):q.inspect_labels(out.getvalue(),'BTCUSDT-metrics-2026-06-24.zip')

    def test_corrupt_deflate_keeps_a_final_partial_receipt(self):
        raw=bytearray(archive());start=30+int.from_bytes(raw[26:28],'little')+int.from_bytes(raw[28:30],'little')
        raw[start]=7  # reserved DEFLATE block type, despite otherwise valid ZIP directory
        value,p=self.frozen()
        a=q.capture(value,p,self.root/'evidence',transport=self.transport(archive_override=bytes(raw)))
        self.assertEqual(len(self.calls),2);self.assertEqual(a['archives'],{})
        self.assertIn('archive_qualification_refused',a['stop_reason'])
        self.assertTrue((self.root/'evidence/qualification.json').is_file())

    def test_slow_reservation_cannot_dispatch_after_its_window(self):
        value,p=self.frozen()
        with patch.object(q.time,'monotonic_ns',side_effect=[0,1,26_000_000_000]):
            a=q.capture(value,p,self.root/'evidence',transport=self.transport())
        self.assertEqual(self.calls,[]);self.assertEqual(a['stop_reason'],'reserved_dispatch_deadline')
        self.assertEqual(a['budget']['requests_charged'],1)
        self.assertEqual(a['budget']['pending'],[])
        self.assertEqual(a['cancelled_reservations'][0]['dispatched'],False)
