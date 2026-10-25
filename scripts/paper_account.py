"""One offline account command: original R318 or explicit paired lifecycle R319."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--lifecycle',action='store_true',help='integrate paired partial-fill lifecycle and cost evidence')
    p.add_argument('--out',type=Path)
    args=p.parse_args(argv)
    if args.lifecycle:
        from scripts.run_paired_account import report
    else:
        from scripts.run_paper_account import report
    print(report(out=args.out))


if __name__=='__main__':main()
