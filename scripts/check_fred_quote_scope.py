"""R429 independent source identity check using csv.reader and exact Fractions; offline only."""
import csv
from datetime import datetime, timedelta, timezone
from fractions import Fraction
import hashlib
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402


def read_rows(raw, clock):
    reader = csv.reader(io.StringIO(raw.decode('utf-8-sig')))
    header = next(reader)
    if header not in [['DATE', 'DTB3'], ['observation_date', 'DTB3']]:
        raise ValueError('independent header mismatch')
    answer = {}
    for day, value in reader:
        stamp = datetime.strptime(day, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        if stamp >= clock - timedelta(days=400):
            if day in answer:
                raise ValueError('independent duplicate date')
            answer[day] = None if value in ('', '.') else Fraction(value)
    return answer


def main():
    lane = ROOT / 'experiments/paper_quote_scope_v1'
    prereg.verify(lane / 'PREREG.md')
    case = json.loads((lane / 'case.json').read_text())
    clock = datetime.fromisoformat(case['asof_utc'])
    primary = lane / 'results/source_contract.json'
    raw = primary.read_bytes();report = json.loads(raw)
    left = read_rows((ROOT / case['held_reference']).read_bytes(), clock)
    right = read_rows((ROOT / case['scoped_probe']).read_bytes(), clock)
    primary_rows = {r['date']:r for r in report['comparisons']}
    assert set(primary_rows) == set(left) | set(right)
    for day, row in primary_rows.items():
        same = day in left and day in right and left[day] == right[day]
        assert row['equal'] == same
        for name, data in [('reference',left),('view',right)]:
            value = row[name]
            assert (None if value is None else Fraction(value)) == data.get(day)
    passed = left == right and bool(left)
    assert (report['state'] == 'SOURCE_VIEW_PARITY_PASS') == passed
    result = dict(state='INDEPENDENT_IDENTITY_PASS', primary_report_sha256=hashlib.sha256(raw).hexdigest(),
                  comparison_dates=len(primary_rows), source_http_calls=0, method='csv.reader + Fraction')
    with (lane / 'results/independent_check.json').open('x') as f:
        f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
