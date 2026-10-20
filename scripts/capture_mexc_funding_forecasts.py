#!/usr/bin/env python3
"""One-shot public MEXC next-funding capture. No history, scheduling or trading."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

SYMBOLS = ('BTC_USDT', 'ETH_USDT', 'SOL_USDT', 'XRP_USDT', 'DOGE_USDT', 'ADA_USDT')
BASE = 'https://contract.mexc.com/api/v1/contract'
SCHEMA_VERSION = 1
MAX_BODY_BYTES = 65536
TIMEOUT_SECONDS = 10
MAX_CLOCK_SKEW_MS = 120000
SETTLEMENT_BUFFER_MS = 15000
HOUR_MS = 3600000
SOURCES = {
    'retrieved_utc_date': '2026-10-20',
    'funding_schema': 'https://www.mexc.io/api-docs/futures/market-endpoints/get-funding-rate',
    'ticker_schema': 'https://www.mexc.io/api-docs/futures/market-endpoints/get-ticker-contract-market-data',
    'settlement_rules': 'https://www.mexc.com/support/article/mexc-futures-funding-rate-305432020820705280',
    'settlement_rules_version': '2026-06-01 13:48:50 as displayed; inspected 2026-10-20',
    'mechanism': 'https://www.mexc.com/announcements/article/funding-rate-mechanism-13322295212313',
    'mechanism_version': '2024-09-06 as displayed; inspected 2026-10-20',
}
PROTOCOL = Path(__file__).resolve().parents[1]/'research/mexc_funding_forecasts/PROTOCOL.md'


class CaptureError(ValueError):
    pass


@dataclass(frozen=True)
class Reply:
    status: int | None
    body: bytes
    error: str | None = None
    truncated: bool = False


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n').encode()


def write_new(path, payload):
    with Path(path).open('xb') as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def utc_now():
    return datetime.now(timezone.utc)


def timestamp(clock):
    now = clock()
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise CaptureError('Capture clock must return an aware datetime')
    now = now.astimezone(timezone.utc)
    return now.isoformat(timespec='microseconds').replace('+00:00', 'Z'), int(now.timestamp()*1000)


def public_get(url):
    """Fixed public endpoints only. Inherited proxy/CA settings remain in force."""
    request = urllib.request.Request(url, headers={'User-Agent': 'quant-prospective-capture/1'})
    try:
        opener = urllib.request.build_opener(NoRedirect())
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read(MAX_BODY_BYTES+1)
            return Reply(response.status, body, truncated=len(body)>MAX_BODY_BYTES)
    except urllib.error.HTTPError as exc:
        body = exc.read(MAX_BODY_BYTES+1)
        return Reply(exc.code, body, f'HTTP {exc.code}', len(body)>MAX_BODY_BYTES)
    except (OSError, ValueError) as exc:
        return Reply(None, b'', type(exc).__name__)


def number(value, label, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise CaptureError(f'{label} must be numeric')
    try:
        result = float(value)
    except (ValueError, OverflowError) as exc:
        raise CaptureError(f'{label} must be numeric') from exc
    if not math.isfinite(result) or (positive and result <= 0):
        raise CaptureError(f'{label} is nonfinite or outside its allowed range')
    return result


def integer(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise CaptureError(f'{label} must be an integer')
    return value


def milliseconds(value, label):
    value = integer(value, label)
    if not 946684800000 <= value < 4102444800000:
        raise CaptureError(f'{label} must be Unix milliseconds in 2000..2099')
    return value


def decode(reply, symbol):
    if reply.error or reply.status != 200 or reply.truncated:
        raise CaptureError('Unsuccessful, oversized or unreadable HTTP response')
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON field')
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError(f'Non-JSON numeric constant: {value}')

    try:
        payload = json.loads(reply.body.decode('utf-8'), object_pairs_hook=unique_object,
                             parse_constant=invalid_constant)
    except (ValueError, UnicodeError) as exc:
        raise CaptureError('Invalid JSON response') from exc
    if (not isinstance(payload, dict) or payload.get('success') is not True
            or type(payload.get('code')) is not int or payload['code'] != 0):
        raise CaptureError('API success envelope missing or unsuccessful')
    data = payload.get('data')
    if not isinstance(data, dict) or data.get('symbol') != symbol:
        raise CaptureError('Response symbol/data shape mismatch')
    return data


def optional_price(data, key):
    # Absent prices are explicit nulls, never zero or a fabricated fill price.
    if key not in data or data[key] is None:
        return None
    return number(data[key], key, positive=True)


def normalize(funding, ticker, symbol, request_start_ms, request_end_ms):
    required = ('fundingRate', 'minFundingRate', 'maxFundingRate', 'collectCycle',
                'nextSettleTime', 'timestamp')
    if any(key not in funding for key in required) or 'timestamp' not in ticker:
        raise CaptureError('Required funding/clock fields missing')
    rate = number(funding['fundingRate'], 'fundingRate')
    floor = number(funding['minFundingRate'], 'minFundingRate')
    ceiling = number(funding['maxFundingRate'], 'maxFundingRate')
    if not -1 <= floor <= rate <= ceiling <= 1:
        raise CaptureError('Funding fraction/cap ordering is invalid')
    cycle = integer(funding['collectCycle'], 'collectCycle')
    if not 1 <= cycle <= 24:
        raise CaptureError('collectCycle must be 1..24 hours')
    system_time = milliseconds(funding['timestamp'], 'funding system timestamp')
    settlement = milliseconds(funding['nextSettleTime'], 'nextSettleTime')
    trade_time = milliseconds(ticker['timestamp'], 'ticker trade timestamp')
    if not request_start_ms-MAX_CLOCK_SKEW_MS <= system_time <= request_end_ms+MAX_CLOCK_SKEW_MS:
        raise CaptureError('Funding system timestamp is stale or clock skew exceeds the contract')
    if trade_time > request_end_ms+MAX_CLOCK_SKEW_MS:
        raise CaptureError('Ticker trade timestamp is in the future')
    if not 0 < settlement-system_time <= cycle*HOUR_MS+MAX_CLOCK_SKEW_MS:
        raise CaptureError('Next settlement does not follow the reported cycle')
    if settlement <= request_end_ms+MAX_CLOCK_SKEW_MS+SETTLEMENT_BUFFER_MS:
        raise CaptureError('Too close to settlement for an unambiguous prospective snapshot')
    bid, ask = optional_price(ticker, 'bid1'), optional_price(ticker, 'ask1')
    if bid is not None and ask is not None and bid > ask:
        raise CaptureError('Ticker best bid exceeds best ask')
    return {'symbol': symbol, 'funding_rate_fraction': rate,
            'funding_rate_floor_fraction': floor, 'funding_rate_ceiling_fraction': ceiling,
            'collect_cycle_hours': cycle, 'next_settle_time_ms': settlement,
            'funding_system_timestamp_ms': system_time, 'ticker_trade_timestamp_ms': trade_time,
            'ticker_trade_age_ms_at_capture_end': request_end_ms-trade_time,
            'funding_fair_price': optional_price(funding, 'fairPrice'),
            'funding_index_price': optional_price(funding, 'idxPrice'),
            'ticker_fair_price': optional_price(ticker, 'fairPrice'),
            'ticker_index_price': optional_price(ticker, 'indexPrice'),
            'ticker_last_price': optional_price(ticker, 'lastPrice'),
            'ticker_best_bid': bid, 'ticker_best_ask': ask}


def collect(root, capture_id, fetch=public_get, clock=utc_now):
    """One immutable evidence batch; injected fetch/clock permit fully offline tests."""
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', capture_id):
        raise CaptureError('Invalid capture ID')
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    lock = root/'.capture.lock'
    try:
        descriptor = os.open(lock, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise CaptureError('Capture root is already locked; no request was made') from exc
    try:
        os.write(descriptor, (capture_id+'\n').encode())
        batch = root/'captures'/capture_id
        try:
            batch.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise CaptureError('Capture ID already exists; no request was made') from exc
        started, started_ms = timestamp(clock)
        metadata = {'schema_version': SCHEMA_VERSION, 'capture_id': capture_id, 'symbols': list(SYMBOLS),
                    'capture_start_utc': started, 'collector_sha256': sha(Path(__file__).read_bytes()),
                    'protocol_sha256': sha(PROTOCOL.read_bytes()),
                    'sources': SOURCES, 'max_body_bytes': MAX_BODY_BYTES, 'request_limit': 2*len(SYMBOLS)}
        write_new(batch/'intent.json', json_bytes(metadata))
        requests, observations, errors = [], [], []
        for symbol in SYMBOLS:
            decoded = {}
            funding_start_ms = None
            for kind, endpoint in (('funding', f'funding_rate/{symbol}'), ('ticker', f'ticker?symbol={symbol}')):
                url = f'{BASE}/{endpoint}'
                begin, begin_ms = timestamp(clock)
                try:
                    reply = fetch(url)
                except (OSError, ValueError) as exc:
                    reply = Reply(None, b'', type(exc).__name__)
                end, end_ms = timestamp(clock)
                raw_name = f'{symbol}_{kind}.raw'
                write_new(batch/raw_name, reply.body)
                request = {'symbol': symbol, 'kind': kind, 'url': url, 'start_utc': begin, 'end_utc': end,
                           'start_ms': begin_ms, 'end_ms': end_ms, 'http_status': reply.status,
                           'transport_error': reply.error, 'body_truncated': reply.truncated,
                           'raw_file': raw_name, 'retained_bytes': len(reply.body), 'sha256': sha(reply.body)}
                requests.append(request)
                write_new(batch/f'{symbol}_{kind}.request.json', json_bytes(request))
                if end_ms < begin_ms:
                    errors.append({'symbol': symbol, 'kind': 'clock', 'error': 'UTC request clock moved backwards'})
                if kind == 'funding':
                    funding_start_ms = begin_ms
                try:
                    decoded[kind] = decode(reply, symbol)
                except CaptureError as exc:
                    errors.append({'symbol': symbol, 'kind': kind, 'error': str(exc)})
            if len(decoded) == 2:
                try:
                    row = normalize(decoded['funding'], decoded['ticker'], symbol, funding_start_ms, end_ms)
                    row['capture_id'] = capture_id
                    row['request_metadata'] = [request for request in requests if request['symbol']==symbol]
                    observations.append(row)
                except CaptureError as exc:
                    errors.append({'symbol': symbol, 'kind': 'schema', 'error': str(exc)})
        finished, finished_ms = timestamp(clock)
        if finished_ms < started_ms:
            raise CaptureError('UTC capture clock moved backwards')
        for row in observations:
            if row['next_settle_time_ms'] <= finished_ms+MAX_CLOCK_SKEW_MS+SETTLEMENT_BUFFER_MS:
                errors.append({'symbol': row['symbol'], 'kind': 'clock', 'error': 'Settlement too close at batch completion'})
        targets = []
        if not errors:
            for row in observations:
                key = f"{row['funding_system_timestamp_ms']}_{row['next_settle_time_ms']}.json"
                target = root/'observations'/row['symbol']/key
                if target.exists():
                    errors.append({'symbol': row['symbol'], 'kind': 'duplicate',
                                   'error': 'Funding timestamp/target settlement already recorded'})
                targets.append((target, row))
        recorded = []
        if not errors:
            for target, row in targets:
                target.parent.mkdir(parents=True, exist_ok=True)
                write_new(target, json_bytes(row))
                recorded.append(str(target.relative_to(root)))
        manifest = {**metadata, 'capture_end_utc': finished, 'requests': requests,
                    'status': 'COMPLETE' if not errors else 'FAILED', 'errors': errors,
                    'observation_files': recorded, 'valid_symbol_count': len(observations),
                    'interpretation': 'Raw prospective observations only; no forecast test, PnL or fill claim'}
        write_new(batch/'manifest.json', json_bytes(manifest))
        return manifest
    finally:
        owned = os.fstat(descriptor)
        os.close(descriptor)
        try:
            current = lock.stat()
            if (current.st_dev, current.st_ino) == (owned.st_dev, owned.st_ino):
                lock.unlink()
        except FileNotFoundError:
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='Dedicated append-only capture root')
    parser.add_argument('--capture-id', required=True, help='Unique immutable batch ID')
    args = parser.parse_args()
    try:
        manifest = collect(args.out, args.capture_id)
    except (CaptureError, OSError) as exc:
        print(f'Capture failed: {exc}', file=sys.stderr)
        return 2
    print(json.dumps({'capture_id': manifest['capture_id'], 'status': manifest['status'],
                      'observations': len(manifest['observation_files']), 'errors': manifest['errors']}))
    return 0 if manifest['status']=='COMPLETE' else 2


if __name__ == '__main__':
    raise SystemExit(main())
