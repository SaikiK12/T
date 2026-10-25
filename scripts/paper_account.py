"""One offline account command: original account, lifecycle or registered controls."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    group=p.add_mutually_exclusive_group()
    group.add_argument('--lifecycle',action='store_true',help='integrate paired partial-fill lifecycle and cost evidence')
    group.add_argument('--controls',action='store_true',help='R320 paper controls, finite risk-component/tool validation and exact owner requirements')
    p.add_argument('--out',type=Path)
    args=p.parse_args(argv)
    if args.controls:
        from scripts.run_owner_acceptance import report
    elif args.lifecycle:
        from scripts.run_paired_account import report
    else:
        from scripts.run_paper_account import report
    print(report(out=args.out))


if __name__=='__main__':main()
