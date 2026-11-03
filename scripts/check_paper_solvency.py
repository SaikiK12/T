"""Read a paper snapshot and report capital capacity; never starts a runner.

This component alone never authorizes new entries. API callers combine it with
the frozen risk engine through lab.paper_solvency.PaperSolvencyGuard.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from lab.paper_solvency import capital_status  # noqa: E402


def unique(pairs):
    out={}
    for key,value in pairs:
        if key in out: raise ValueError('duplicate JSON key')
        out[key]=value
    return out


def reject_constant(_):
    raise ValueError('nonfinite JSON')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot',type=Path)
    args=parser.parse_args(argv)
    try:
        if args.snapshot.is_symlink() or not args.snapshot.is_file() or args.snapshot.stat().st_size>2*1024**2:
            raise ValueError('bounded regular snapshot file required')
        with args.snapshot.open('rb') as f: raw=f.read(2*1024**2+1)
        if len(raw)>2*1024**2: raise ValueError('snapshot grew beyond bound')
        snapshot=json.loads(raw,object_pairs_hook=unique,parse_constant=reject_constant)
        result=capital_status(snapshot)
    except (OSError,TypeError,ValueError) as exc:
        print(json.dumps(dict(state='UNKNOWN',error=str(exc),model_new_entries_allowed=False,
                              actual_order_allowed=False,activation_allowed=False)))
        return 2
    print(json.dumps(result,sort_keys=True,allow_nan=False))
    return 0 if result['state']=='AVAILABLE' else 1


if __name__=='__main__': raise SystemExit(main())
