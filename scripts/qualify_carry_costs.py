"""Bounded public-source qualification for R391's whole frozen symbol table.

Dry planning is the default. A separately frozen protocol must bind this exact
plan and its source inputs before --execute. One attempt creates raw receipts
without replacing source files. This is not pair PnL, orders or observed fills.
KuCoin depth remains unqualified; optional MEXC snapshot walks are conditional
one-way diagnostics and never establish future exits or account fees.
"""
import argparse
import csv
from decimal import Decimal, InvalidOperation, localcontext
import gzip
import hashlib
import io
import json
import multiprocessing
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402
from lab.mexc_depth import parse_depth_levels  # noqa: E402

DEFAULT_SYMBOLS = ROOT / 'experiments/reserved_batch2/symbols.csv'
URLS = {'mexc': 'https://contract.mexc.com/api/v1/contract/detail',
        'kucoin': 'https://api-futures.kucoin.com/api/v1/contracts/active'}
NAME = re.compile(r'[A-Z0-9][A-Z0-9_-]{0,63}')
NS = 1_000_000_000
BODY_LIMIT = 2 * 1024**2
TOTAL_BODY_LIMIT = 5 * 1024**2
MAX_REQUESTS = 4
TOTAL_SECONDS = 20
REQUEST_SECONDS = 3
DEPTH_LEVELS = 20
LOADED_SCRIPT_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
LOADED_DEPTH_SHA256 = hashlib.sha256((ROOT / 'lab/mexc_depth.py').read_bytes()).hexdigest()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(obj):
    return (json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def number(value):
    if isinstance(value, bool):
        raise ValueError('boolean amount')
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError('invalid amount') from exc
    if not result.is_finite() or not 0 < result <= Decimal('1e30') or result.as_tuple().exponent < -18:
        raise ValueError('unsupported positive amount')
    return result


def regular(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
        raise ValueError('regular input without symlink ancestors required')
    return path


def cohort(path):
    path = regular(path)
    if path.stat().st_size > 65536:
        raise ValueError('symbol table exceeds 64 KiB')
    raw = path.read_bytes()
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8')))
    if reader.fieldnames != ['key', 'kucoin', 'dydx', 'lighter', 'mexc']:
        raise ValueError('exact published symbol-table columns required')
    rows = list(reader)
    if not 1 <= len(rows) <= 100:
        raise ValueError('bounded nonempty cohort required')
    seen = set()
    contracts = set()
    for row in rows:
        if None in row or any(not isinstance(v, str) for v in row.values()):
            raise ValueError('malformed symbol-table row')
        if not NAME.fullmatch(row['key']) or row['key'] in seen:
            raise ValueError('invalid or duplicate economic key')
        seen.add(row['key'])
        for venue in ('mexc', 'kucoin', 'dydx', 'lighter'):
            symbol = row[venue]
            if symbol and (not NAME.fullmatch(symbol) or (venue, symbol) in contracts):
                raise ValueError('invalid or duplicated venue symbol')
            if symbol:
                contracts.add((venue, symbol))
    return raw, rows


def make_plan(symbols=DEFAULT_SYMBOLS, *, depth_contracts=0, notional='1000'):
    if type(depth_contracts) is not int or not 0 <= depth_contracts <= 2:
        raise ValueError('at most two predeclared MEXC depth contracts')
    amount = number(notional)
    raw, rows = cohort(symbols)
    table = regular(symbols)
    try:
        table_name = table.relative_to(ROOT).as_posix()
    except ValueError:
        table_name = str(table)
    inputs = {table_name: digest(raw)}
    for name in ('scripts/qualify_carry_costs.py', 'lab/mexc_depth.py', 'lab/prereg.py',
                 'requirements-test.lock', '.python-version'):
        inputs[name] = digest((ROOT / name).read_bytes())
    candidates = [r['mexc'] for r in sorted(rows, key=lambda r: r['key'])
                  if r['mexc'] and r['kucoin']][:depth_contracts]
    plan = dict(schema='carry_cost_qualification/v1', inputs=inputs,
                cohort=rows, cohort_path=table_name, metadata_urls=URLS,
                mexc_depth_candidates=candidates, notional_quote=str(amount),
                max_requests=MAX_REQUESTS, max_body_bytes=BODY_LIMIT,
                max_total_body_bytes=TOTAL_BODY_LIMIT, total_seconds=TOTAL_SECONDS,
                request_seconds=REQUEST_SECONDS, depth_levels=DEPTH_LEVELS,
                scope='Current public source qualification; all cohort rows retained; no historical returns.',
                kucoin_depth='UNQUALIFIED: primary depth schema, quantity units and snapshot identity not bound.',
                depth_selection='First predeclared keys with both MEXC and KuCoin symbols, sorted by key; no PnL selection.',
                fees='UNKNOWN for the owner; public advertised fields are not applied.',
                execution_allowed=False, actual_order_allowed=False, activation_allowed=False)
    plan['plan_sha256'] = digest(canonical(plan))
    return plan


def verify_plan(plan, protocol):
    protocol = regular(protocol)
    prereg.verify(protocol)
    body = protocol.read_text()
    expected = digest(canonical({k: v for k, v in plan.items() if k != 'plan_sha256'}))
    if plan.get('plan_sha256') != expected or f'Plan SHA256: {expected}' not in body:
        raise ValueError('frozen protocol must bind the exact qualification plan')
    if (plan['metadata_urls'] != URLS or plan['max_requests'] != MAX_REQUESTS
            or plan['max_body_bytes'] != BODY_LIMIT or plan['max_total_body_bytes'] != TOTAL_BODY_LIMIT
            or plan['total_seconds'] != TOTAL_SECONDS or plan['request_seconds'] != REQUEST_SECONDS
            or plan['depth_levels'] != DEPTH_LEVELS):
        raise ValueError('source endpoints or fixed bounds changed')
    if (plan['inputs'].get('scripts/qualify_carry_costs.py') != LOADED_SCRIPT_SHA256
            or plan['inputs'].get('lab/mexc_depth.py') != LOADED_DEPTH_SHA256):
        raise ValueError('loaded source differs from the bound on-disk source')
    for name, sha in plan['inputs'].items():
        path = Path(name) if Path(name).is_absolute() else ROOT / name
        if digest(regular(path).read_bytes()) != sha or f'{sha}  {name}' not in body:
            raise ValueError('frozen qualification input missing or changed: ' + name)
    return protocol


def json_object(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('duplicate JSON key')
            value[key] = item
        return value
    def invalid(_):
        raise ValueError('nonfinite JSON')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=invalid)


def metadata_rows(venue, payload):
    if not isinstance(payload, dict):
        raise ValueError('metadata envelope missing')
    if venue == 'mexc':
        if payload.get('success') is not True or type(payload.get('code')) is not int or payload['code'] != 0:
            raise ValueError('MEXC metadata success not reported')
    elif payload.get('code') != '200000':
        raise ValueError('KuCoin metadata success not reported')
    rows = payload.get('data')
    if not isinstance(rows, list) or not rows:
        raise ValueError('nonempty metadata inventory required')
    out = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('symbol'), str) or row['symbol'] in out:
            raise ValueError('metadata symbol absent or duplicated')
        out[row['symbol']] = row
    return out


def qualify(venue, key, symbol, inventory):
    result = dict(symbol=symbol or None, status='UNSCORED', reason='contract_metadata_unavailable',
                  multiplier_base=None, lot_contracts=None, owner_fees=None, execution_allowed=False)
    if not symbol:
        result.update(status='NOT_IN_TABLE', reason='no contract declared; no substitute')
        return result
    if inventory is None or symbol not in inventory:
        return result
    row = inventory[symbol]
    try:
        if venue == 'mexc':
            if not (row.get('baseCoin') == key and row.get('quoteCoin') == row.get('settleCoin') == 'USDT'
                    and row.get('symbol') == key + '_USDT' and type(row.get('type')) is int
                    and row['type'] == 1 and type(row.get('state')) is int and row['state'] == 0
                    and row.get('apiAllowed') is True):
                raise ValueError('MEXC key/USDT/crypto/open/API identity not qualified')
            multiplier, lot = number(row.get('contractSize')), number(row.get('volUnit'))
        else:
            if not (row.get('baseCurrency') == key and row.get('quoteCurrency') == row.get('settleCurrency') == 'USDT'
                    and row.get('type') == 'FFWCSX' and row.get('status') == 'Open'
                    and row.get('isInverse') is False and not row.get('expireDate')):
                raise ValueError('KuCoin key/linear/USDT/perpetual/open identity not qualified')
            multiplier, lot = number(row.get('multiplier')), number(row.get('lotSize'))
        if lot != lot.to_integral_value():
            raise ValueError('contract lot must be an integer')
        result.update(status='REPORTED_METADATA_QUALIFIED', reason=None,
                      multiplier_base=str(multiplier), lot_contracts=str(lot),
                      contract_convention='linear USDT; conditional on supplied source schema')
    except (ValueError, KeyError, TypeError) as exc:
        result['reason'] = str(exc)
    return result


def snapshot_walk(symbol, rules, payload, notional):
    if rules['status'] != 'REPORTED_METADATA_QUALIFIED' or rules['symbol'] != symbol:
        raise ValueError('qualified MEXC contract metadata required')
    if not isinstance(payload, dict) or payload.get('success') is not True:
        raise ValueError('MEXC depth success not reported')
    book = payload.get('data')
    if not isinstance(book, dict) or book.get('symbol', symbol) != symbol:
        raise ValueError('depth identity mismatch')
    if (type(book.get('version')) is not int or book['version'] < 0
            or type(book.get('timestamp')) is not int or not 10**12 <= book['timestamp'] < 10**14):
        raise ValueError('explicit snapshot version and source millisecond timestamp required')
    with localcontext() as context:
        context.prec = 80
        sides = []
        for field in ('bids', 'asks'):
            raw = book.get(field)
            if not isinstance(raw, list) or not 1 <= len(raw) <= DEPTH_LEVELS:
                raise ValueError('bounded nonempty depth side required')
            parse_depth_levels(raw)  # established MEXC [price, contracts, order_count] contract
            levels = [(number(r[0]), number(r[1]) * number(rules['multiplier_base'])) for r in raw]
            prices = [x[0] for x in levels]
            if any((a <= b if field == 'bids' else a >= b) for a, b in zip(prices, prices[1:])):
                raise ValueError('strictly ordered unique depth prices required')
            sides.append(levels)
        bids, asks = sides
        if bids[0][0] >= asks[0][0]:
            raise ValueError('crossed or locked snapshot')
        mid, budget = (bids[0][0] + asks[0][0]) / 2, number(notional)
        def walk(levels, buy):
            left, base = budget, Decimal(0)
            for price, quantity in levels:
                used = min(left, price * quantity)
                base += used / price
                left -= used
                if left == 0:
                    break
            if left:
                return dict(state='UNSCORED', reason='insufficient_shown_depth',
                            unallocated_quote=str(left), vwap=None, impact_bp=None)
            vwap = budget / base
            impact = (vwap / mid - 1 if buy else 1 - vwap / mid) * 10000
            return dict(state='CONDITIONAL_SNAPSHOT', reason=None, unallocated_quote='0',
                        vwap=str(vwap), impact_bp=str(impact), quantity_base=str(base))
        return dict(symbol=symbol, reported_sequence=book['version'], reported_source_ms=book['timestamp'],
                    sequence_continuity_verified=False, source_clock_authenticated=False,
                    mid=str(mid), notional_quote=str(budget), buy=walk(asks, True), sell=walk(bids, False),
                    quantity_convention='Continuous quote-notional walk, not lot-rounded order quantities.',
                    fees_quote=None, future_exit_cost=None, round_trip_cost=None,
                    observed_fills=False, execution_allowed=False, actual_order_allowed=False)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def http_worker(url, connection, limit, seconds):
    """One owned public GET; inherited proxy/CA, no redirects or retries."""
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'quant-lab-source-qualification/1',
                                                       'Accept-Encoding': 'identity'})
        try:
            response = urllib.request.build_opener(NoRedirect()).open(request, timeout=seconds)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            headers = {k: response.headers.get(k) for k in ('Retry-After', 'Content-Type', 'Date')
                       if response.headers.get(k) is not None}
            connection.send(('status', (response.status, headers)))
            remaining = limit
            while remaining:
                chunk = response.read1(min(65536, remaining))
                if not chunk:
                    break
                connection.send(('chunk', chunk))
                remaining -= len(chunk)
        connection.send(('done', None))
    except Exception as exc:
        connection.send(('error', type(exc).__name__))
    finally:
        connection.close()


def fetch(url, limit, seconds, *, worker=http_worker):
    deadline = time.monotonic() + seconds
    ctx = multiprocessing.get_context('spawn')
    receiver, sender = ctx.Pipe(duplex=False)
    child = ctx.Process(target=worker, args=(url, sender, limit, seconds), daemon=True)
    chunks, length = [], 0
    record = dict(started_utc_ns=time.time_ns(), started_mono_ns=time.monotonic_ns(),
                  http_status=None, headers={}, complete=False, error=None, redirects=0, retries=0)
    try:
        child.start()
        sender.close()
        while time.monotonic() < deadline:
            if not receiver.poll(max(0, deadline - time.monotonic())):
                break
            try:
                kind, value = receiver.recv()
            except EOFError:
                break
            if kind == 'status':
                record['http_status'], record['headers'] = value
            elif kind == 'chunk':
                if not isinstance(value, bytes) or length + len(value) > limit:
                    raise ValueError('worker body cap violated')
                chunks.append(value)
                length += len(value)
            elif kind == 'done':
                record['complete'] = length < limit
                break
            elif kind == 'error':
                raise ValueError(value)
            else:
                raise ValueError('unknown worker message')
        if not record['complete']:
            record['error'] = 'incomplete_or_cap_reached'
    except Exception as exc:
        record['error'] = type(exc).__name__ + ': ' + str(exc)[:256]
    finally:
        record.update(received_utc_ns=time.time_ns(), received_mono_ns=time.monotonic_ns())
        if child.pid is not None:
            if child.is_alive():
                child.terminate()
            child.join(.2)
            if child.is_alive():
                child.kill()
                child.join(.2)
            record['worker_reaped'] = not child.is_alive()
        receiver.close()
        sender.close()
    record['cleanup_finished_mono_ns'] = time.monotonic_ns()
    return record, b''.join(chunks)


def write_new(path, obj):
    with Path(path).open('xb') as stream:
        stream.write(canonical(obj))
        stream.flush()
        __import__('os').fsync(stream.fileno())


def capture(plan, out, protocol, *, transport=fetch):
    protocol = verify_plan(plan, protocol)
    out = Path(out).absolute()
    if any(p.is_symlink() for p in (out, *out.parents)) or out.exists():
        raise ValueError('new output directory without symlink ancestors required')
    # Persistent one-attempt guard belongs to the new protocol, independent of --out.
    write_new(protocol.parent / 'qualification.started.json',
              dict(plan_sha256=plan['plan_sha256'], out=str(out), started_utc_ns=time.time_ns()))
    out.mkdir()
    write_new(out / 'plan.json', plan)
    deadline = time.monotonic() + plan['total_seconds']
    records, inventories, walks = [], {}, {}
    read_upper_bound, stopped = 0, None
    def get(name, url):
        nonlocal read_upper_bound, stopped
        if stopped:
            return None
        remaining = deadline - time.monotonic() - .5  # reserve owned-worker cleanup
        limit = min(plan['max_body_bytes'], plan['max_total_body_bytes'] - read_upper_bound)
        if len(records) >= plan['max_requests'] or limit <= 0 or remaining <= 0:
            stopped = 'request_body_or_duration_budget'
            return None
        receipt, raw = transport(url, limit, min(plan['request_seconds'], remaining))
        if not isinstance(raw, bytes) or len(raw) > limit:
            raise ValueError('transport violated body cap')
        receipt = dict(receipt, name=name, url=url, body=name + '.json.gz',
                       body_bytes=len(raw), body_sha256=digest(raw), body_limit=limit)
        upper = len(raw) if receipt.get('complete') else limit
        receipt['body_read_upper_bound'] = upper
        read_upper_bound += upper
        with (out / receipt['body']).open('xb') as stream:
            stream.write(gzip.compress(raw, mtime=0))
        write_new(out / (name + '.receipt.json'), receipt)
        records.append(receipt)
        if (not receipt.get('complete') or receipt.get('error') or receipt.get('http_status') != 200
                or receipt.get('headers', {}).get('Retry-After') is not None
                or receipt.get('worker_reaped') is False):
            stopped = 'access_backoff_transport_or_body_failure'
            return None
        try:
            return json_object(raw)
        except (UnicodeError, ValueError, RecursionError):
            stopped = 'invalid_source_json'
            return None
    for venue in ('mexc', 'kucoin'):
        url = plan['metadata_urls'][venue]
        payload = get(venue + '_metadata', url)
        if payload is not None:
            try:
                inventories[venue] = metadata_rows(venue, payload)
            except ValueError:
                stopped = 'invalid_' + venue + '_metadata_schema'
        if stopped:
            break
    rows = [dict(key=row['key'],
                 venues={v: qualify(v, row['key'], row[v], inventories.get(v)) for v in ('mexc', 'kucoin')},
                 other_declared_venues={v: row[v] for v in ('dydx', 'lighter') if row[v]},
                 pair_execution_cost=None) for row in plan['cohort']]
    rules = {row['venues']['mexc']['symbol']: row['venues']['mexc'] for row in rows}
    for symbol in plan['mexc_depth_candidates']:
        rule = rules[symbol]
        if stopped or rule['status'] != 'REPORTED_METADATA_QUALIFIED':
            walks[symbol] = dict(state='UNSCORED', reason=stopped or rule['reason'])
            continue
        payload = get('mexc_depth_' + symbol,
                      'https://contract.mexc.com/api/v1/contract/depth/' + symbol + '?limit=20')
        try:
            walks[symbol] = snapshot_walk(symbol, rule, payload, plan['notional_quote'])
        except ValueError as exc:
            walks[symbol] = dict(state='UNSCORED', reason=str(exc))
    result = dict(plan_sha256=plan['plan_sha256'], rows=rows, mexc_depth=walks,
                  requests=records, body_read_upper_bound=read_upper_bound, stop_reason=stopped,
                  finished_utc_ns=time.time_ns(), finished_mono_ns=time.monotonic_ns(),
                  owner_fees=None, kucoin_depth=plan['kucoin_depth'], historical_returns_read=False,
                  observed_fills=False, pair_pnl=None, actual_order_allowed=False, activation_allowed=False)
    write_new(out / 'qualification.json', result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--symbols', type=Path, default=DEFAULT_SYMBOLS)
    parser.add_argument('--depth-contracts', type=int, default=0)
    parser.add_argument('--notional', default='1000')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--prereg', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args(argv)
    try:
        plan = make_plan(args.symbols, depth_contracts=args.depth_contracts, notional=args.notional)
        if not args.execute:
            print(json.dumps(dict(state='DRY_PLAN', plan=plan), sort_keys=True, indent=2))
            return 0
        if args.prereg is None or args.out is None:
            raise ValueError('--execute requires --prereg and a new --out directory')
        result = capture(plan, args.out, args.prereg)
        print(json.dumps(dict(state='SOURCE_QUALIFICATION_ONLY', out=str(args.out),
                              stop_reason=result['stop_reason'], requests=len(result['requests']),
                              rows=len(result['rows']), actual_order_allowed=False)))
        return 1 if result['stop_reason'] else 0
    except (OSError, ValueError, prereg.PreregError) as exc:
        print('Carry source qualification: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
