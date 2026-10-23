"""Read-only project status using the Control Room's existing execution receipts.

No collector, scheduler, market arrays, logs, trades or journal writes. A recorded
process success is separate from data completeness and scientific eligibility.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab.operations import OBJECTIVE, forward_tasks
from lab.runtime import environment
from scripts.dashboard_jobs import build_jobs


def build_status(root, *, state_dir=None, now=None):
    root = Path(root).resolve()
    jobs = build_jobs(root, state_dir=state_dir, now=now)
    blockers = []
    for job in jobs:
        reasons = []
        if job['state'] != 'SUCCESS':
            reasons.append('process_' + job['state'].lower())
        if job['stale'] is True:
            reasons.append('stale_receipt')
        if job['data_state'] != 'COMPLETE':
            reasons.append('data_' + job['data_state'].lower())
        if reasons:
            blockers.append({'task_id': job['task_id'], 'reasons': reasons})
    methods = root / 'registry/methods.csv'
    queue = {'state': 'UNAVAILABLE', 'rows': None, 'by_status': {}}
    if methods.is_file() and not methods.is_symlink():
        try:
            with methods.open(newline='') as stream:
                rows = list(csv.DictReader(stream))
            if any(not row.get('id') or not row.get('status') for row in rows):
                raise ValueError('invalid method rows')
            queue = {'state': 'READ', 'rows': len(rows),
                     'by_status': dict(sorted(Counter(row['status'] for row in rows).items()))}
        except (OSError, ValueError, csv.Error):
            pass
    env = environment(root)
    return {'schema_version': 1, 'objective': OBJECTIVE,
            'observed_at': datetime.fromtimestamp(now, timezone.utc).isoformat() if now is not None else datetime.now(timezone.utc).isoformat(),
            'scope': 'Recorded operational state only; no process liveness or trading eligibility certified.',
            'gate_eligibility': 'UNASSESSED',
            'queue': queue, 'environment': env,
            'disk_free_bytes': shutil.disk_usage(root).free,
            'tasks': jobs, 'attention': blockers,
            'dependencies': {t.name: {'required': list(t.needs), 'optional': list(t.optional)} for t in forward_tasks()},
            'operational_attention_required': bool(blockers) or queue['state'] != 'READ' or env['qx_source_binding'] != 'MATCHES_BUILD_RECEIPT'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', type=Path, help='existing external orchestrator receipt directory')
    parser.add_argument('--json', action='store_true', help='emit the same observations as JSON')
    parser.add_argument('--strict', action='store_true', help='exit1 for attention items; never a live-trading gate')
    args = parser.parse_args(argv)
    result = build_status(ROOT, state_dir=args.state_dir)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    else:
        print(OBJECTIVE)
        print(f"Methods: {result['queue']['rows']} | qx binding: {result['environment']['qx_source_binding']} | free disk: {result['disk_free_bytes']/1e9:.2f} GB")
        print('TASK          PROCESS      DATA         STALE   RUN')
        for row in result['tasks']:
            print(f"{row['task_id']:<13} {row['state']:<12} {row['data_state']:<12} {str(row['stale']):<7} {row['run_id'] or '-'}")
        print(f"{len(result['attention'])} tasks need attention. Gate eligibility: UNASSESSED.")
        print('Use the same --state-dir as lab forward; missing receipts stay unknown. No work started.')
    return int(args.strict and result['operational_attention_required'])


if __name__ == '__main__':
    raise SystemExit(main())
