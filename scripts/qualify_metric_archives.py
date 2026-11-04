"""One frozen, bounded metrics archive schema/time-label qualification; no returns."""
import argparse
import csv
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import re
import stat
import time
import zipfile
import zlib

from lab import prereg
from lab.acquisition_budget import BudgetJournal, BudgetLimits
from scripts import qualify_carry_costs as transport_source
from scripts.qualify_carry_costs_targeted import durable_write, write_json

ROOT = Path(__file__).resolve().parent.parent
DATES = ('2026-06-24', '2026-06-25')
BODY_LIMIT = 65536
TOTAL_BODY = 4 * BODY_LIMIT
EXPANDED_LIMIT = 131072
COLUMNS = ['create_time', 'symbol', 'sum_open_interest', 'sum_open_interest_value',
           'count_toptrader_long_short_ratio', 'sum_toptrader_long_short_ratio',
           'count_long_short_ratio', 'sum_taker_long_short_vol_ratio']
INPUT_NAMES = ('scripts/qualify_metric_archives.py', 'scripts/qualify_carry_costs.py',
    'scripts/qualify_carry_costs_targeted.py', 'lab/mexc_depth.py', 'lab/acquisition_budget.py',
    'lab/prereg.py', '.python-version', 'requirements-test.lock')
LOADED = {n: transport_source.digest((ROOT / n).read_bytes()) for n in INPUT_NAMES}


def plan():
    requests = []
    for day in DATES:
        name = 'BTCUSDT-metrics-' + day + '.zip'
        url = 'https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT/' + name
        requests.extend([dict(day=day, name=name + '.CHECKSUM', url=url + '.CHECKSUM'),
                         dict(day=day, name=name, url=url)])
    value = dict(schema='metrics_archive_labels/v1', inputs=LOADED, requests=requests,
        max_requests=4, max_body_bytes=BODY_LIMIT, max_total_body_bytes=TOTAL_BODY,
        max_expanded_bytes=EXPANDED_LIMIT, max_rows=400, dispatch_seconds=30,
        worker_seconds=3, reservation_ns=5_000_000_000,
        numeric_metric_values_interpreted=False, predictive_trials=0,
        actual_order_allowed=False, activation_allowed=False)
    value['plan_sha256'] = transport_source.digest(transport_source.canonical(value))
    return value


def verify(value, protocol):
    protocol = transport_source.regular(protocol); prereg.verify(protocol)
    text = protocol.read_text()
    if value != plan() or 'Plan SHA256: ' + value['plan_sha256'] not in text:
        raise ValueError('exact frozen source plan required')
    for name, sha in value['inputs'].items():
        if transport_source.digest(transport_source.regular(ROOT / name).read_bytes()) != sha or f'{sha}  {name}' not in text:
            raise ValueError('frozen input absent/changed: ' + name)
    return protocol


def inspect_labels(raw, filename):
    """Interpret only header, exact symbol and raw time labels; numerical cells opaque."""
    if not isinstance(raw, bytes) or len(raw) > BODY_LIMIT:
        raise ValueError('bounded opaque ZIP bytes required')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        if len(entries) != 1: raise ValueError('one exclusive CSV member required')
        info = entries[0]; mode = info.external_attr >> 16
        if (info.filename != filename[:-4] + '.csv' or '/' in info.filename or '\\' in info.filename
                or info.is_dir() or info.flag_bits & 1 or stat.S_IFMT(mode) not in (0, stat.S_IFREG)
                or info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                or not 0 < info.file_size <= EXPANDED_LIMIT):
            raise ValueError('safe bounded unencrypted regular CSV required')
        with archive.open(info) as stream:
            expanded = stream.read(EXPANDED_LIMIT + 1)
        if len(expanded) != info.file_size or len(expanded) > EXPANDED_LIMIT or not expanded.endswith(b'\n'):
            raise ValueError('expanded byte identity/limit/newline failure')
    reader = csv.reader(io.StringIO(expanded.decode('utf-8-sig')), strict=True)
    if next(reader, None) != COLUMNS: raise ValueError('exact declared unique schema required')
    stamps, labels = [], []
    for row in reader:
        if len(labels) >= 400 or len(row) != len(COLUMNS) or row[1] != 'BTCUSDT':
            raise ValueError('bounded exact-symbol rows and widths required')
        label = row[0]
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', label):
            raise ValueError('strict unzoned create_time label required')
        stamp = datetime.strptime(label, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        labels.append(label); stamps.append(int(stamp.timestamp()))
    if not labels: raise ValueError('nonempty label sequence required')
    day = datetime.strptime(filename, 'BTCUSDT-metrics-%Y-%m-%d.zip').replace(tzinfo=timezone.utc)
    lower = int(day.timestamp())
    if any(not lower <= stamp <= lower + 86400 for stamp in stamps):
        raise ValueError('time labels outside the declared day and inclusive next boundary')
    deltas = [b-a for a,b in zip(stamps, stamps[1:])]
    return dict(source_sha256=transport_source.digest(raw), columns=COLUMNS, member=info.filename,
        expanded_bytes=len(expanded), row_count=len(labels), first_label=labels[0], last_label=labels[-1],
        minimum_label=min(labels), maximum_label=max(labels), raw_labels=labels,
        duplicate_labels=len(labels)-len(set(labels)), strictly_increasing=all(d>0 for d in deltas),
        adjacent_steps_not_300_seconds=sum(d != 300 for d in deltas),
        timezone_assumption='unqualified unzoned labels compared on a declared UTC calendar; no source-clock proof',
        period_semantics='UNKNOWN', historical_availability_proven=False,
        numerical_metric_values_interpreted=False, point_in_time_verified=False)


def checksum(raw, filename):
    if not isinstance(raw, bytes) or len(raw)>4096: raise ValueError('bounded checksum body required')
    match = re.fullmatch(rb'([0-9a-f]{64}) [ *]' + re.escape(filename.encode()) + rb'\n?', raw)
    if match is None: raise ValueError('exact filename and SHA256 checksum required')
    return match[1].decode()


def capture(value, protocol, out, *, transport=transport_source.fetch):
    protocol = verify(value, protocol); out = Path(out).absolute()
    if out.exists() or not out.parent.is_dir() or any(p.is_symlink() for p in (out,*out.parents)):
        raise ValueError('new output under existing nonsymlink parent required')
    write_json(protocol.parent/'qualification.started.json',
               dict(plan_sha256=value['plan_sha256'],started_utc_ns=time.time_ns(),out=str(out)))
    out.mkdir(); write_json(out/'plan.json',value)
    journal = BudgetJournal(protocol.parent/'acquisition_budget.jsonl',
        'R403 Binance two-archive metadata-only qualification; new distinct256KiB scope',
        BudgetLimits(4,TOTAL_BODY,20_000_000_000,5_000_000_000))
    fd=os.open(protocol.parent,os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)
    deadline=time.monotonic_ns()+30_000_000_000
    records, bodies, reports, cancelled = [], {}, {}, []; stopped=None
    for item in value['requests']:
        start=time.monotonic_ns()
        reservation=journal.reserve(item['name'],BODY_LIMIT,5_000_000_000,now_ns=start,deadline_ns=deadline)
        if not reservation['dispatch_allowed']: raise ValueError('attempt reservation already consumed')
        dispatch_ns=time.monotonic_ns()
        if dispatch_ns+value['reservation_ns']>deadline:
            journal.complete(item['name'],0,dispatch_ns-start,outcome='cancelled')
            cancellation=dict(name=item['name'],url=item['url'],dispatched=False,
                              reason='insufficient_window_after_reservation',monotonic_ns=dispatch_ns)
            cancelled.append(cancellation);write_json(out/(item['name']+'.cancelled.json'),cancellation)
            stopped='reserved_dispatch_deadline';break
        receipt, raw=transport(item['url'],BODY_LIMIT,3)
        elapsed=time.monotonic_ns()-start
        if not isinstance(raw,bytes) or len(raw)>BODY_LIMIT: raise ValueError('transport exceeded source cap')
        failed=(receipt.get('http_status')!=200 or not receipt.get('complete') or receipt.get('error')
                or receipt.get('worker_reaped') is not True or receipt.get('headers',{}).get('Retry-After') is not None)
        journal.complete(item['name'],len(raw),elapsed,outcome='failure' if failed else 'success')
        receipt=dict(receipt,url=item['url'],name=item['name'],body_bytes=len(raw),
                     body_sha256=transport_source.digest(raw),elapsed_including_cleanup_ns=elapsed,
                     reservation_bytes_charged=BODY_LIMIT)
        durable_write(out/item['name'],raw);write_json(out/(item['name']+'.receipt.json'),receipt)
        records.append(receipt); bodies[item['name']]=raw
        if failed or journal.status()['violations']:
            stopped='access_backoff_transport_body_or_budget_failure';break
        if item['name'].endswith('.CHECKSUM'):
            try: checksum(raw,item['name'][:-9])
            except ValueError: stopped='invalid_checksum_schema';break
        else:
            try:
                sha=checksum(bodies[item['name']+'.CHECKSUM'],item['name'])
                if sha!=transport_source.digest(raw): raise ValueError('published checksum mismatch')
                reports[item['day']]=inspect_labels(raw,item['name'])
            except (ValueError,UnicodeError,zipfile.BadZipFile,csv.Error,RuntimeError,NotImplementedError,zlib.error) as exc:
                stopped='archive_qualification_refused: '+str(exc);break
    verify(value,protocol)
    shared=None
    if all(day in reports for day in DATES):
        shared=sorted(set(reports[DATES[0]]['raw_labels'])&set(reports[DATES[1]]['raw_labels']))
    result=dict(plan_sha256=value['plan_sha256'],requests=records,archives=reports,cancelled_reservations=cancelled,
        shared_labels_across_archives=shared,stop_reason=stopped,budget=journal.status(),
        finished_utc_ns=time.time_ns(),predictive_trials=0,prospective_paper_days=0,
        period_semantics='UNKNOWN; label ranges alone cannot prove end/start, publication or availability',
        historical_coverage_complete=False,source_clock_authenticated=False,
        numerical_metric_values_interpreted=False,returns_read=False,pair_pnl=None,
        cost_tiers=[dict(multiple=k,net_pnl=None) for k in (1,2,3)],
        actual_order_allowed=False,activation_allowed=False)
    write_json(out/'qualification.json',result);return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true');parser.add_argument('--prereg',type=Path)
    parser.add_argument('--out',type=Path);args=parser.parse_args(argv)
    if not args.execute:
        print(json.dumps(dict(state='DRY_PLAN',plan=plan()),indent=2));return 0
    if args.prereg is None or args.out is None: parser.error('explicit --prereg and new --out required')
    result=capture(plan(),args.prereg,args.out)
    print(json.dumps(dict(state='METADATA_ONLY',archives=len(result['archives']),requests=len(result['requests']),
                          stop_reason=result['stop_reason'],budget=result['budget'])))
    return 1 if result['stop_reason'] else 0


if __name__=='__main__':raise SystemExit(main())
