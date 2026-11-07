"""Schema/identity failures on invented data; no historical market scoring."""
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

from scripts.inspect_funding_schema import inspect, main


def make_zip(path, header='calc_time,funding_interval_hours,last_funding_rate\n', member='funding.csv'):
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(member, header + 'invented,rows,not_decoded\n')
    return path


class FundingSchemaTests(unittest.TestCase):
    def test_archive_fields_do_not_invent_missing_cash_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            p = make_zip(Path(d)/'funding.zip')
            sha = hashlib.sha256(p.read_bytes()).hexdigest()
            r = inspect(p, expected_sha256=sha)
            self.assertTrue(r['expected_identity_matched'])
            self.assertEqual(r['missing_cash_field_roles'], ['settlement_value', 'payment_kind'])
            self.assertFalse(r['cash_settlement_ready'])
            self.assertFalse(r['observation_rows_decoded'])
            self.assertNotIn('invented', str(r))

    def test_zip_inspection_never_reads_observation_lines(self):
        with tempfile.TemporaryDirectory() as d:
            p = make_zip(Path(d)/'funding.zip')
            original = zipfile.ZipExtFile.readline
            calls = []
            def header_only(stream, *args):
                calls.append(1)
                if len(calls) != 1:
                    raise AssertionError('observation read')
                return original(stream, *args)
            with mock.patch.object(zipfile.ZipExtFile, 'readline', header_only):
                inspect(p)
            self.assertEqual(len(calls), 1)

    def test_missing_header_duplicates_and_unsafe_members_are_rejected(self):
        for header, member in [('1,2,3\n', 'funding.csv'), ('t,t,rate\n', 'funding.csv'),
                               ('t,rate\n', '../funding.csv'), ('t,rate\n', '/funding.csv'),
                               ('t,rate\n', 'nested/funding.csv'), ('a'*5000+'\n', 'funding.csv')]:
            with self.subTest(header=header[:30], member=member), tempfile.TemporaryDirectory() as d:
                p = make_zip(Path(d)/'funding.zip', header, member)
                with self.assertRaises(ValueError): inspect(p)

    def test_additional_members_or_symlinks_are_not_silently_selected(self):
        with tempfile.TemporaryDirectory() as d:
            p = make_zip(Path(d)/'funding.zip')
            with zipfile.ZipFile(p, 'a') as z: z.writestr('second.csv', 't,rate\n')
            with self.assertRaises(ValueError): inspect(p)
            link = Path(d)/'link.zip'; link.symlink_to(p)
            with self.assertRaises(ValueError): inspect(link)
            linked_dir = Path(d)/'linked'; linked_dir.symlink_to(Path(d), target_is_directory=True)
            with self.assertRaises(ValueError): inspect(linked_dir/'funding.zip')

    def test_hash_and_size_limits_fail_without_schema_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            p = make_zip(Path(d)/'funding.zip')
            for options in [dict(expected_sha256='0'*64), dict(expected_sha256='bad'),
                            dict(max_bytes=1), dict(max_bytes=True), dict(max_bytes=0)]:
                with self.subTest(options=options), self.assertRaises(ValueError): inspect(p, **options)

    def test_source_changed_while_header_is_read_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = make_zip(Path(d)/'funding.zip')
            original = zipfile.ZipExtFile.readline
            def changed(stream, *args):
                header = original(stream, *args)
                with p.open('ab') as out: out.write(b'changed')
                return header
            with mock.patch.object(zipfile.ZipExtFile, 'readline', changed), self.assertRaisesRegex(ValueError, 'changed'):
                inspect(p)

    def test_parquet_reads_schema_not_data_even_when_columns_are_present(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'funding.parquet'
            pq.write_table(pa.table({'t': [1], 'rate': [0.0], 'markPrice': [100.0], 'rateType': ['Regular']}), p)
            with mock.patch.object(pq, 'read_table', side_effect=AssertionError('row read')):
                r = inspect(p)
            self.assertEqual(r['missing_cash_field_roles'], [])
            self.assertFalse(r['cash_settlement_ready'])
            self.assertFalse(r['field_semantics_verified'])
            self.assertFalse(r['historical_coverage_verified'])

    def test_cli_writes_only_new_receipt_and_does_not_replace_source(self):
        with tempfile.TemporaryDirectory() as d, mock.patch('sys.stderr', new_callable=io.StringIO):
            p = make_zip(Path(d)/'funding.zip'); before = p.read_bytes()
            out = Path(d)/'receipt.json'
            self.assertEqual(main([str(p), '--output', str(out)]), 0)
            receipt = out.read_bytes()
            self.assertEqual(main([str(p), '--output', str(out)]), 2)
            self.assertEqual(main([str(p), '--output', str(p)]), 2)
            self.assertEqual(receipt, out.read_bytes())
            self.assertEqual(before, p.read_bytes())


if __name__ == '__main__':
    unittest.main()
