"""One prospective, bounded per-contract public source qualification; no orders."""
import argparse
from decimal import Decimal
import gzip
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import quote

from lab import carry_snapshot_cost as arithmetic, prereg
from lab.acquisition_budget import BudgetJournal, BudgetLimits
from scripts import qualify_carry_costs as source

ROOT = source.ROOT
BODY_LIMIT = 32768
TOTAL_BODY_LIMIT = 5 * 1024 * 1024
BASELINE = dict(requests_used=1, body_bytes_upper_bound=2 * 1024 * 1024,
                reserved_duration_ns=4_000_000_000,
                source='R401 incomplete MEXC inventory, receipt SHA bound below; no allowance renewal')
INPUTS = ('scripts/qualify_carry_costs_targeted.py', 'lab/carry_snapshot_cost.py',
          'scripts/qualify_carry_costs.py', 'lab/mexc_depth.py', 'lab/acquisition_budget.py',
          'lab/prereg.py', 'requirements-test.lock', '.python-version',
          'experiments/carry_cost_qualification_v1/evidence/mexc_metadata.receipt.json')
LOADED = {p: source.digest((ROOT / p).read_bytes()) for p in INPUTS}


def make_plan(symbols=source.DEFAULT_SYMBOLS):
    raw, rows = source.cohort(symbols)
    table = str(source.regular(symbols))
    try: table = source.regular(symbols).relative_to(ROOT).as_posix()
    except ValueError: pass
    requests = []
    for row in sorted(rows, key=lambda r: r['key']):
        for venue in ('mexc', 'kucoin'):
            symbol = row[venue]
            if not symbol: continue
            escaped = quote(symbol, safe='')
            urls = (('https://api.mexc.com/api/v1/contract/detail?symbol=' + escaped,
                     'https://api.mexc.com/api/v1/contract/depth/' + escaped + '?limit=20')
                    if venue == 'mexc' else
                    ('https://api-futures.kucoin.com/api/v1/contracts/' + escaped,
                     'https://api-futures.kucoin.com/api/v1/level2/depth20?symbol=' + escaped))
            requests.append(dict(key=row['key'], venue=venue, symbol=symbol,
                                 metadata_url=urls[0], depth_url=urls[1]))
    count = 2 * len(requests)
    if not count or count > 96 or BASELINE['body_bytes_upper_bound'] + count * BODY_LIMIT > TOTAL_BODY_LIMIT:
        raise ValueError('fixed accumulated byte/request budget cannot cover this cohort')
    plan = dict(schema='carry_targeted_qualification/v1', cohort=rows, cohort_path=table,
        inputs={**LOADED, table: source.digest(raw)}, contracts=requests, max_new_requests=count,
        body_limit=BODY_LIMIT, total_body_limit=TOTAL_BODY_LIMIT, baseline=BASELINE,
        worker_seconds=3, reservation_ns=4_000_000_000, dispatch_seconds=300,
        global_start_interval_seconds=1, mexc_metadata_interval_seconds='5.1',
        target_mid_notional_per_leg='1000', depth_levels=20,
        actual_order_allowed=False, activation_allowed=False)
    plan['plan_sha256'] = source.digest(source.canonical(plan))
    return plan


def verify(plan, protocol):
    protocol = source.regular(protocol)
    prereg.verify(protocol)
    expected = make_plan(ROOT / plan['cohort_path'])
    if plan != expected or 'Plan SHA256: ' + plan['plan_sha256'] not in protocol.read_text():
        raise ValueError('frozen plan/loaded code mismatch')
    for name, sha in plan['inputs'].items():
        if source.digest(source.regular(ROOT / name).read_bytes()) != sha or f'{sha}  {name}' not in protocol.read_text():
            raise ValueError('bound input changed or absent: ' + name)
    return protocol


def durable_write(path, raw):
    path = Path(path)
    with path.open('xb') as handle:
        handle.write(raw); handle.flush(); os.fsync(handle.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


def write_json(path, value):
    durable_write(path, source.canonical(value))


def decode(raw):
    def unique(pairs):
        out = {}
        for k, v in pairs:
            if k in out: raise ValueError('duplicate JSON key')
            out[k] = v
        return out
    def invalid(_): raise ValueError('nonfinite JSON')
    return json.loads(raw.decode('utf8'), parse_float=Decimal,
                      object_pairs_hook=unique, parse_constant=invalid)


def capture(plan, out, protocol, *, transport=source.fetch, monotonic=time.monotonic,
            sleep=time.sleep):
    protocol = verify(plan, protocol)
    out = Path(out).absolute()
    if out.exists() or not out.parent.is_dir() or any(p.is_symlink() for p in (out, *out.parents)):
        raise ValueError('new output directory with existing nonsymlink parent required')
    write_json(protocol.parent / 'qualification.started.json',
               dict(plan_sha256=plan['plan_sha256'], started_utc_ns=time.time_ns(), out=str(out)))
    out.mkdir()
    write_json(out / 'plan.json', plan)
    limits = BudgetLimits(1 + plan['max_new_requests'], TOTAL_BODY_LIMIT,
                          (1 + plan['max_new_requests']) * plan['reservation_ns'], plan['reservation_ns'])
    journal = BudgetJournal(protocol.parent / 'acquisition_budget.jsonl',
        'carry public-source qualification R401+R402 single accumulated grant', limits, baseline=BASELINE)
    # Journal file and its newly created directory entry are durable before dispatch.
    fd = os.open(protocol.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)
    deadline = monotonic() + plan['dispatch_seconds']
    last, mexc_meta = float('-inf'), float('-inf')
    records, qualified, books, reasons = [], {}, {}, {}
    stopped = None

    def get(item, kind):
        nonlocal last, mexc_meta, stopped
        due = last + plan['global_start_interval_seconds']
        if item['venue'] == 'mexc' and kind == 'metadata':
            due = max(due, mexc_meta + float(plan['mexc_metadata_interval_seconds']))
        wait = max(0, due - monotonic())
        if monotonic() + wait + 4 > deadline:
            stopped = 'dispatch_deadline'; return None
        if wait: sleep(wait)
        name = item['venue'] + '_' + item['symbol'] + '_' + kind
        start = monotonic()
        reserved = journal.reserve(name, BODY_LIMIT, plan['reservation_ns'],
            now_ns=int(start * 1e9), deadline_ns=int(deadline * 1e9))
        if not reserved['dispatch_allowed']:
            stopped = 'reservation_replay'; return None
        last = start
        if item['venue'] == 'mexc' and kind == 'metadata': mexc_meta = start
        receipt, raw = transport(item[kind + '_url'], BODY_LIMIT, plan['worker_seconds'])
        elapsed = max(0, int((monotonic() - start) * 1e9))
        if not isinstance(raw, bytes) or len(raw) > BODY_LIMIT:
            raise ValueError('transport violated reserved body cap; reservation retained')
        failed = (not receipt.get('complete') or receipt.get('error')
            or receipt.get('worker_reaped') is not True or receipt.get('headers', {}).get('Retry-After') is not None)
        status = receipt.get('http_status')
        journal.complete(name, len(raw), elapsed, outcome='failure' if failed or status != 200 else 'success')
        receipt = dict(receipt, name=name, url=item[kind + '_url'], body=name + '.json.gz',
            body_bytes=len(raw), body_sha256=source.digest(raw), body_limit=BODY_LIMIT,
            reservation_bytes_charged=BODY_LIMIT, elapsed_including_cleanup_ns=elapsed)
        durable_write(out / receipt['body'], gzip.compress(raw, mtime=0))
        write_json(out / (name + '.receipt.json'), receipt); records.append(receipt)
        if failed or journal.status()['violations'] or status not in (200, 404):
            stopped = 'access_backoff_transport_body_or_budget_failure'; return None
        if status == 404:
            reasons[(item['venue'], item['symbol'])] = 'source_contract_or_endpoint_not_found_404'
            return None
        try: return decode(raw)
        except (ValueError, UnicodeError, RecursionError):
            stopped = 'invalid_source_json'; return None

    for item in plan['contracts']:
        if stopped: break
        identity = (item['venue'], item['symbol'])
        payload = get(item, 'metadata')
        if payload is None: continue
        try: qualified[identity] = arithmetic.contract(item['venue'], item['key'], item['symbol'], payload)
        except ValueError as exc:
            reasons[identity] = str(exc); continue
        payload = get(item, 'depth')
        if payload is None: continue
        try: books[identity] = arithmetic.book(item['venue'], item['symbol'], qualified[identity], payload)
        except ValueError as exc: reasons[identity] = str(exc)
    rows = []
    for row in plan['cohort']:
        venues = {}
        for venue in ('mexc', 'kucoin'):
            identity = (venue, row[venue])
            snapshot = books.get(identity)
            # Full levels remain in raw evidence; summary contains explicit source identity/clocks only.
            summary = None if snapshot is None else {k: str(v) if isinstance(v, Decimal) else v
                for k, v in snapshot.items() if k not in ('bids', 'asks')}
            venues[venue] = dict(symbol=row[venue] or None, rules=qualified.get(identity), book=summary,
                reason=reasons.get(identity) or (None if snapshot else stopped or 'not_qualified_or_not_declared'))
        identities = [(v, row[v]) for v in ('mexc', 'kucoin')]
        cost = dict(state='UNSCORED', reason='both_declared_contracts_and_books_required', pair_pnl=None)
        if all(i in books for i in identities):
            cost = arithmetic.pair_cost(*(qualified[i] for i in identities), *(books[i] for i in identities),
                                       notional=plan['target_mid_notional_per_leg'])
        rows.append(dict(key=row['key'], venues=venues, pair=cost,
            other_declared_venues={v: row[v] for v in ('dydx', 'lighter') if row[v]}))
    verify(plan, protocol)
    result = dict(plan_sha256=plan['plan_sha256'], rows=rows, requests=records,
        budget=journal.status(), stop_reason=stopped, finished_utc_ns=time.time_ns(),
        predictive_trials=0, prospective_paper_days=0, owner_fees=None,
        historical_returns_read=False, observed_fills=False, pair_pnl=None,
        actual_order_allowed=False, activation_allowed=False)
    write_json(out / 'qualification.json', result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--prereg', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args(argv)
    try:
        plan = make_plan()
        if not args.execute:
            print(json.dumps(dict(state='DRY_PLAN', plan=plan), indent=2, sort_keys=True)); return 0
        if args.prereg is None or args.out is None: raise ValueError('explicit --prereg and new --out required')
        result = capture(plan, args.out, args.prereg)
        print(json.dumps(dict(state='SOURCE_QUALIFICATION_ONLY', requests=len(result['requests']),
                              stop_reason=result['stop_reason'], budget=result['budget'])))
        return 1 if result['stop_reason'] else 0
    except (OSError, ValueError, prereg.PreregError) as exc:
        print('Targeted qualification: ' + str(exc), file=sys.stderr); return 2


if __name__ == '__main__': raise SystemExit(main())
