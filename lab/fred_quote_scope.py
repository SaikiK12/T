"""A dated view of the same public DTB3 series, keeping native 400-day paper rules and old budgets."""
from contextlib import contextmanager
import csv
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import io
from pathlib import Path
from urllib import parse, request

from lab.paper_transport import InheritedBudget, fence as previous_fence
from lab.runtime_transport import TransportStop, append

FRED = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTB3'
DAYS = 400


def window(now):
    if now.tzinfo is None:
        raise ValueError('quote receipt clock must be timezone-aware')
    now = now.astimezone(timezone.utc)
    return (now - timedelta(days=DAYS)).date(), now.date()


def scoped_url(now):
    start, end = window(now)
    return FRED + '&' + parse.urlencode(dict(cosd=start.isoformat(), coed=end.isoformat()))


def csv_view(raw, now):
    """Validate the provider view without changing its bytes or filling missing observations."""
    start, end = window(now)
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    if reader.fieldnames not in (['DATE', 'DTB3'], ['observation_date', 'DTB3']):
        raise ValueError('unexpected DTB3 CSV fields')
    dates, values = [], []
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise ValueError('malformed DTB3 CSV row')
        day = datetime.strptime(row[reader.fieldnames[0]], '%Y-%m-%d').date()
        if not start <= day <= end:
            raise ValueError('observation outside the fixed 400-day source view')
        value = row['DTB3']
        if value not in ('', '.'):
            try:
                number = Decimal(value)
            except InvalidOperation:
                raise ValueError('invalid DTB3 rate string') from None
            if not number.is_finite():
                raise ValueError('nonfinite DTB3 rate')
        else:
            number = None
        dates.append(day)
        values.append(number)
    if not dates or dates != sorted(set(dates)) or all(v is None for v in values):
        raise ValueError('missing, duplicate, unordered or unusable quote view')
    return dict(rows=len(dates), oldest=dates[0].isoformat(), newest=dates[-1].isoformat())


def admitted_rows(raw, now):
    """Native row eligibility, including its intraday lower cutoff; for the registered identity check only."""
    csv_view(raw, now)
    cutoff = now.astimezone(timezone.utc) - timedelta(days=DAYS)
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    answer = []
    for row in reader:
        day = datetime.strptime(row[reader.fieldnames[0]], '%Y-%m-%d').replace(tzinfo=timezone.utc)
        if day >= cutoff:
            value = row['DTB3']
            answer.append((day.date().isoformat(), None if value in ('', '.') else Decimal(value)))
    return answer


@contextmanager
def fence(folder, policy, *, baseline, frozen_baseline, clock=None):
    """Scope only the original FRED GET; old transport retains spend, blocks, raw bodies and decoding."""
    clock = clock or (lambda: datetime.now(timezone.utc))
    folder = Path(folder)
    with previous_fence(folder, policy, baseline=baseline, frozen_baseline=frozen_baseline):
        original = request.OpenerDirector.open

        def opened(self, fullurl, *args, **kwargs):
            req = fullurl if isinstance(fullurl, request.Request) else request.Request(fullurl)
            if req.full_url != FRED:
                return original(self, req, *args, **kwargs)
            if req.get_method() != 'GET':
                raise TransportStop('only the original public FRED GET may be scoped')
            now = clock()
            physical = scoped_url(now)
            scoped = request.Request(physical, headers=dict(req.header_items()), method='GET')
            response = original(self, scoped, *args, **kwargs)
            try:
                raw = response.getvalue()
                meta = csv_view(raw, now)
            except (ValueError, UnicodeError) as exc:
                key = parse.urlsplit(FRED).netloc + parse.urlsplit(FRED).path
                InheritedBudget(folder, policy, baseline, frozen_baseline).block(key, 'FRED dated-view validation failed')
                response.close()
                raise TransportStop(str(exc)) from None
            try:
                append(folder / 'quote_views.jsonl', dict(event='FRED_VIEW', original_url=FRED,
                    physical_url=physical, receipt_utc=now.astimezone(timezone.utc).isoformat(),
                    body_sha256=hashlib.sha256(raw).hexdigest(), native_lookback_days=DAYS,
                    source_body_unchanged=True, **meta))
            except OSError as exc:
                response.close()
                raise TransportStop('FRED view receipt unavailable: ' + str(exc)) from None
            return response

        request.OpenerDirector.open = opened
        try:
            yield
        finally:
            request.OpenerDirector.open = original
