"""Segment, verify or restore one explicit RECORDED file; never uploads or deletes originals.

For ordinary small-file backups use handover.py. Keep the pack receipt's
manifest_sha256 outside the segment directory and supply it when verifying or
restoring. A destination root must already contain registry/data_manifest.csv.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab.recording_segments import pack_recording, restore_recording, verify_recording  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    pack = sub.add_parser('pack', help='explicitly copy a file into a new local segment directory')
    pack.add_argument('--root', type=Path, default=ROOT)
    pack.add_argument('--source', required=True, help='relative data/... path, classified RECORDED')
    pack.add_argument('--out', type=Path, required=True, help='new directory outside root; parent must exist')
    pack.add_argument('--chunk-mb', type=int, default=50)
    pack.add_argument('--min-age-min', type=int, default=15)
    for name in ('verify', 'restore'):
        p = sub.add_parser(name)
        p.add_argument('--archive', type=Path, required=True)
        p.add_argument('--expected-manifest-sha256', required=True)
        if name == 'restore':
            p.add_argument('--root', type=Path, required=True)
    for p in (pack, *[sub.choices[x] for x in ('verify', 'restore')]):
        p.add_argument('--budget-mb', type=int, required=True,
                       help='maximum bytes in this local bundle including manifest, decimal MB; not a remote archive budget')
    args = parser.parse_args(argv)
    try:
        budget = args.budget_mb * 1_000_000
        if args.command == 'pack':
            receipt = pack_recording(args.root, args.source, args.out,
                                     chunk_bytes=args.chunk_mb * 1_000_000,
                                     budget_bytes=budget, min_age_seconds=args.min_age_min * 60)
        else:
            kw = dict(expected_manifest_sha256=args.expected_manifest_sha256, budget_bytes=budget)
            receipt = (verify_recording(args.archive, **kw) if args.command == 'verify' else
                       restore_recording(args.archive, args.root, **kw))
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps(dict(state='REFUSED', error=str(exc), destination_success_not_claimed=True)))
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
