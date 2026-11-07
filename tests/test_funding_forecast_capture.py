"""Offline fixtures only. This suite never calls a public market endpoint."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit

from scripts import capture_mexc_funding_forecasts as capture

NOW = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
NOW_MS = int(NOW.timestamp()*1000)


def payload(symbol, kind):
    if kind == 'funding':
        data = {'symbol': symbol, 'fundingRate': '0.0002', 'minFundingRate': '-0.01',
                'maxFundingRate': '0.01', 'collectCycle': 8, 'timestamp': NOW_MS,
                'nextSettleTime': NOW_MS+4*capture.HOUR_MS, 'idxPrice': '100', 'fairPrice': '100.01'}
    else:
        data = {'symbol': symbol, 'timestamp': NOW_MS-500, 'lastPrice': '100.02',
                'indexPrice': '100', 'fairPrice': '100.01', 'bid1': '100', 'ask1': '100.02'}
    return {'success': True, 'code': 0, 'data': data}


class FakeFetch:
    def __init__(self, transform=None):
        self.calls = []
        self.transform = transform

    def __call__(self, url):
        self.calls.append(url)
        split = urlsplit(url)
        kind = 'ticker' if split.path.endswith('/ticker') else 'funding'
        symbol = parse_qs(split.query)['symbol'][0] if kind=='ticker' else split.path.rsplit('/', 1)[1]
        value = payload(symbol, kind)
        if self.transform is not None:
            value = self.transform(symbol, kind, value)
        if isinstance(value, capture.Reply):
            return value
        return capture.Reply(200, json.dumps(value).encode())


class CaptureTests(unittest.TestCase):
    def run_capture(self, root, identifier='fixture', fetch=None):
        return capture.collect(root, identifier, fetch=fetch or FakeFetch(), clock=lambda: NOW)

    def test_complete_batch_retains_raw_hashes_and_exact_clock_roles(self):
        with tempfile.TemporaryDirectory() as directory:
            fetch = FakeFetch()
            manifest = self.run_capture(directory, fetch=fetch)
            root = Path(directory)
            self.assertEqual(manifest['status'], 'COMPLETE')
            self.assertEqual(len(fetch.calls), 12)
            self.assertEqual(len(manifest['observation_files']), len(capture.SYMBOLS))
            self.assertEqual(manifest['symbols'], list(capture.SYMBOLS))
            self.assertFalse((root/'.capture.lock').exists())
            batch = root/'captures'/'fixture'
            expected_protocol_hash = hashlib.sha256(capture.PROTOCOL.read_bytes()).hexdigest()
            self.assertEqual(manifest['protocol_sha256'],expected_protocol_hash)
            intent = json.loads((batch/'intent.json').read_text())
            self.assertEqual(intent['protocol_sha256'],expected_protocol_hash)
            for request in manifest['requests']:
                raw = (batch/request['raw_file']).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), request['sha256'])
                self.assertEqual(len(raw), request['retained_bytes'])
                self.assertTrue(request['start_utc'].endswith('Z'))
                self.assertTrue(request['end_utc'].endswith('Z'))
            row = json.loads((root/manifest['observation_files'][0]).read_text())
            self.assertEqual(row['funding_system_timestamp_ms'], NOW_MS)
            self.assertEqual(row['ticker_trade_timestamp_ms'], NOW_MS-500)
            self.assertEqual(row['funding_rate_fraction'], .0002)
            self.assertEqual(row['ticker_last_price'], 100.02)

    def test_duplicate_capture_id_is_rejected_before_requests_and_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            self.run_capture(directory)
            before = {p.relative_to(directory):p.read_bytes() for p in Path(directory).rglob('*') if p.is_file()}
            fetch = FakeFetch()
            with self.assertRaisesRegex(capture.CaptureError, 'Capture ID already exists'):
                self.run_capture(directory, fetch=fetch)
            self.assertEqual(fetch.calls, [])
            after = {p.relative_to(directory):p.read_bytes() for p in Path(directory).rglob('*') if p.is_file()}
            self.assertEqual(before, after)

    def test_duplicate_forecast_cannot_become_an_additional_observation(self):
        with tempfile.TemporaryDirectory() as directory:
            self.run_capture(directory, 'first')
            manifest = self.run_capture(directory, 'second')
            self.assertEqual(manifest['status'], 'FAILED')
            self.assertEqual(manifest['observation_files'], [])
            self.assertEqual(len(list((Path(directory)/'observations').rglob('*.json'))), 6)
            self.assertEqual(len(list((Path(directory)/'captures'/'second').glob('*.raw'))), 12)
            self.assertTrue(all(error['kind']=='duplicate' for error in manifest['errors']))

    def test_existing_lock_is_never_removed_or_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory)/'.capture.lock'
            lock.write_bytes(b'other writer\n')
            fetch = FakeFetch()
            with self.assertRaisesRegex(capture.CaptureError, 'already locked'):
                self.run_capture(directory, fetch=fetch)
            self.assertEqual(lock.read_bytes(), b'other writer\n')
            self.assertEqual(fetch.calls, [])

    def test_http_failure_retains_evidence_and_invalidates_whole_batch(self):
        def transform(symbol, kind, value):
            return capture.Reply(503, b'public service unavailable', 'HTTP 503') if (symbol,kind)==('BTC_USDT','funding') else value
        with tempfile.TemporaryDirectory() as directory:
            fetch = FakeFetch(transform)
            manifest = self.run_capture(directory, fetch=fetch)
            self.assertEqual(manifest['status'], 'FAILED')
            self.assertEqual(manifest['observation_files'], [])
            self.assertEqual(len(fetch.calls), 12)
            raw = Path(directory)/'captures'/'fixture'/'BTC_USDT_funding.raw'
            self.assertEqual(raw.read_bytes(), b'public service unavailable')

    def test_transport_failure_is_recorded_without_silent_partial_success(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.run_capture(directory, fetch=mock.Mock(side_effect=OSError('offline')))
            self.assertEqual(manifest['status'], 'FAILED')
            self.assertEqual(len(manifest['errors']), 12)
            self.assertEqual(manifest['observation_files'], [])
            self.assertTrue(all(request['transport_error']=='OSError' for request in manifest['requests']))

    def test_batch_completion_rechecks_the_settlement_deadline(self):
        # All 12 request intervals are valid, but completing close to the target
        # settlement must not turn them into a COMPLETE prospective batch.
        stamps = iter([NOW]*25+[NOW+timedelta(hours=4,minutes=-1)])
        with tempfile.TemporaryDirectory() as directory:
            manifest = capture.collect(directory,'late-batch',fetch=FakeFetch(),clock=lambda:next(stamps))
            self.assertEqual(manifest['status'],'FAILED')
            self.assertEqual(manifest['observation_files'],[])
            self.assertEqual(manifest['valid_symbol_count'],len(capture.SYMBOLS))
            self.assertEqual(len(manifest['requests']),12)
            self.assertTrue(all(error['kind']=='clock' for error in manifest['errors']))
            self.assertEqual(len(list((Path(directory)/'captures'/'late-batch').glob('*.raw'))),12)

    def test_required_schema_and_nonfinite_or_mismatched_data_fail_closed(self):
        mutations = (
            lambda v:v['data'].pop('nextSettleTime'),
            lambda v:v['data'].update(symbol='OTHER_USDT'),
            lambda v:v['data'].update(fundingRate='nan'),
            lambda v:v['data'].update(fundingRate=.02),
            lambda v:v['data'].update(collectCycle=True),
            lambda v:v['data'].update(timestamp=NOW_MS//1000),
            lambda v:v['data'].update(timestamp=NOW_MS-300000),
            lambda v:v['data'].update(nextSettleTime=NOW_MS+30000),
            lambda v:v['data'].update(nextSettleTime=NOW_MS+9*capture.HOUR_MS),
            lambda v:v['data'].update(fairPrice=0),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                value = payload('BTC_USDT','funding')
                mutation(value)
                with self.assertRaises(capture.CaptureError):
                    data = capture.decode(capture.Reply(200,json.dumps(value).encode()), 'BTC_USDT')
                    capture.normalize(data, payload('BTC_USDT','ticker')['data'], 'BTC_USDT', NOW_MS, NOW_MS)

    def test_nonstandard_json_duplicates_oversize_and_api_failures_are_rejected(self):
        replies = (capture.Reply(200,b'{"success":true,"success":true,"code":0,"data":{}}'),
                   capture.Reply(200,b'{"success":true,"code":0,"data":{"x":NaN}}'),
                   capture.Reply(200,b'not json'),
                   capture.Reply(200,b'{}',truncated=True),
                   capture.Reply(200,b'{"success":false,"code":0,"data":{}}'),
                   capture.Reply(200,b'{"success":true,"code":false,"data":{}}'))
        for reply in replies:
            with self.subTest(reply=reply):
                with self.assertRaises(capture.CaptureError):
                    capture.decode(reply,'BTC_USDT')

    def test_optional_missing_prices_are_null_and_trade_time_is_not_server_time(self):
        funding = payload('BTC_USDT','funding')['data']
        ticker = {'symbol':'BTC_USDT','timestamp':NOW_MS-capture.HOUR_MS}
        funding.pop('fairPrice')
        funding.pop('idxPrice')
        result = capture.normalize(funding,ticker,'BTC_USDT',NOW_MS,NOW_MS)
        self.assertIsNone(result['ticker_last_price'])
        self.assertIsNone(result['funding_fair_price'])
        self.assertEqual(result['ticker_trade_age_ms_at_capture_end'],capture.HOUR_MS)

    def test_pair_specific_intervals_are_retained_instead_of_assuming_eight_hours(self):
        for cycle in (1,4,8):
            funding = payload('BTC_USDT','funding')['data']
            funding.update(collectCycle=cycle,nextSettleTime=NOW_MS+cycle*capture.HOUR_MS-60000)
            result = capture.normalize(funding,payload('BTC_USDT','ticker')['data'],'BTC_USDT',NOW_MS,NOW_MS)
            self.assertEqual(result['collect_cycle_hours'],cycle)

    def test_capture_id_cannot_escape_its_dedicated_root(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ('../outside','x/y','', '.', 'a'*81):
                with self.subTest(name=name):
                    with self.assertRaisesRegex(capture.CaptureError, 'Invalid capture ID'):
                        self.run_capture(directory,name)

    def test_transport_reads_only_the_bound_and_refuses_redirects(self):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.read.return_value = b'x'*(capture.MAX_BODY_BYTES+1)
        opener = mock.Mock()
        opener.open.return_value = response
        with mock.patch.object(capture.urllib.request,'build_opener',return_value=opener):
            reply = capture.public_get(capture.BASE+'/funding_rate/BTC_USDT')
        response.read.assert_called_once_with(capture.MAX_BODY_BYTES+1)
        self.assertTrue(reply.truncated)
        self.assertEqual(opener.open.call_args.kwargs['timeout'],capture.TIMEOUT_SECONDS)
        self.assertIsNone(capture.NoRedirect().redirect_request(None,None,302,'redirect',{},'https://other.invalid'))

    def test_crossed_quotes_are_rejected_and_extreme_numeric_input_is_reported(self):
        funding = payload('BTC_USDT','funding')['data']
        ticker = payload('BTC_USDT','ticker')['data']
        ticker.update(bid1=101,ask1=100)
        with self.assertRaisesRegex(capture.CaptureError,'best bid exceeds'):
            capture.normalize(funding,ticker,'BTC_USDT',NOW_MS,NOW_MS)
        with self.assertRaises(capture.CaptureError):
            capture.number(10**1000,'overflow')


if __name__ == '__main__':
    unittest.main()
