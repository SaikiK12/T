"""R429 sole frozen, offline DTB3 source-view identity measurement; default is an inactive plan."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab.fred_quote_scope import admitted_rows  # noqa: E402
from lab.registry import program_trials  # noqa: E402
from scripts import quant_runtime_v4 as runtime  # noqa: E402

LANE = ROOT / 'experiments/paper_quote_scope_v1'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if not args.run:
        print(json.dumps(dict(state='INACTIVE_PLAN', source_http_calls=0, predictive_trials=0)))
        return 0
    sha, _ = runtime.verify(require_gate=False)
    case = json.loads((LANE / 'case.json').read_text())
    now = datetime.fromisoformat(case['asof_utc'])
    results = LANE / 'results'
    results.mkdir(exist_ok=True)
    started = dict(started_utc=datetime.now(timezone.utc).isoformat(), prereg_sha256=sha,
                   premeasurement_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip())
    with (results / 'RUN_STARTED.json').open('x') as f:
        f.write(json.dumps(started, indent=2) + '\n')
    report = dict(**started, source_http_calls=0, predictive_trials=0,
                  program_trials=program_trials(ROOT / 'registry/rounds.csv'),
                  costs={'1x': 'N/A', '2x': 'N/A', '3x': 'N/A'},
                  cash_funding_or_income_proven=False, real_orders_allowed=False)
    try:
        expected = dict(admitted_rows((ROOT / case['held_reference']).read_bytes(), now))
        actual = dict(admitted_rows((ROOT / case['scoped_probe']).read_bytes(), now))
        comparisons = []
        for day in sorted(set(expected) | set(actual)):
            same = day in expected and day in actual and expected[day] == actual[day]
            comparisons.append(dict(date=day, reference_present=day in expected, view_present=day in actual,
                reference=None if expected.get(day) is None else str(expected[day]),
                view=None if actual.get(day) is None else str(actual[day]), equal=same))
        old_latest = max((d, v) for d, v in expected.items() if v is not None)
        new_latest = max((d, v) for d, v in actual.items() if v is not None)
        passed = bool(comparisons) and all(r['equal'] for r in comparisons) and old_latest == new_latest
        report.update(state='SOURCE_VIEW_PARITY_PASS' if passed else 'SOURCE_VIEW_PARITY_FAIL',
                      comparisons=comparisons, matched_dates=sum(r['equal'] for r in comparisons),
                      date_count=len(comparisons), latest_date_equal=old_latest[0] == new_latest[0],
                      latest_value_equal=old_latest[1] == new_latest[1], latest_date=new_latest[0],
                      pairing='one held native response versus one later scoped response; not independent bets')
    except Exception as exc:
        report.update(state='SOURCE_INPUT_FAILURE', error=type(exc).__name__ + ': ' + str(exc))
    raw = (json.dumps(report, indent=2) + '\n').encode()
    (results / 'source_contract.json').write_bytes(raw)
    (results / 'source_contract.sha256').write_text(hashlib.sha256(raw).hexdigest() + '  source_contract.json\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'comparisons'}))
    return 0 if report['state'] == 'SOURCE_VIEW_PARITY_PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
