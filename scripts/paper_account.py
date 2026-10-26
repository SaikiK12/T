"""One offline account command: account, lifecycle, controls or funding component."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def restore_input(root=ROOT):
    """Restore one small pinned public input, never fetch or replace anything."""
    from lab.artifact_io import read_bytes
    root=Path(root).resolve();relative='data/equations_v2/mexc/prices/BTC_USDT.parquet'
    expected=json.loads((root/'experiments/owner_acceptance_v1/data_inputs.json').read_text())['sha256'][relative]
    source=root/'research/datasets/owner_acceptance_v1/BTC_USDT.parquet'
    raw,digest=read_bytes(source,limit=512*1024)
    if digest!=expected:raise ValueError('portable raw input identity mismatch')
    target=root/relative
    if any(p.is_symlink() for p in (target,*target.parents)):raise ValueError('restore target cannot contain symlinks')
    if target.exists():
        _,current=read_bytes(target,limit=512*1024)
        if current!=expected:raise ValueError('existing cache differs; refusing replacement')
        return 'Existing input has the exact frozen identity; no write.'
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as h:h.write(raw)
    return 'Restored one pinned held input; no market request, overwrite or new observations.'


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    group=p.add_mutually_exclusive_group()
    group.add_argument('--lifecycle',action='store_true',help='integrate paired partial-fill lifecycle and cost evidence')
    group.add_argument('--controls',action='store_true',help='R320 paper controls, finite risk-component/tool validation and exact owner requirements')
    group.add_argument('--funding-prefix',action='store_true',help='R322 conditional encoded-funding component fixtures; no API cash decoder')
    group.add_argument('--continuation',action='store_true',help='R323 fixed-deadline conditional carry policies and common-account replay; no market activation')
    group.add_argument('--spot-perp',action='store_true',help='R324 segregated physical-spot/futures accounting and sealed public wire compatibility; no live collection')
    group.add_argument('--spot-costs',action='store_true',help='R325 sealed spot/perp quote-cost, minimum/permission and account controls; no live collection')
    group.add_argument('--spot-costs-v2',action='store_true',help='R326 exact same-data Decimal/zero-minimum compatibility repair; no live collection')
    group.add_argument('--dated',action='store_true',help='R327 inverse dated-carry entry and conditional terminal accounting; no live collection')
    group.add_argument('--dated-v2',action='store_true',help='R328 same-data exact-ratio compatibility repair; no live collection')
    group.add_argument('--levels',action='store_true',help='R330 frozen close-level probability/cost diagnostic; held sources only, no activation')
    p.add_argument('--restore-input',action='store_true',help='with --controls: restore its one small pinned held input if absent; never overwrite/download')
    p.add_argument('--out',type=Path)
    args=p.parse_args(argv)
    if args.restore_input:
        if not args.controls:p.error('--restore-input requires --controls')
        print(restore_input())
    if args.controls:
        from scripts.run_owner_acceptance import report
    elif args.funding_prefix:
        from scripts.run_funding_prefix import report
    elif args.continuation:
        from scripts.run_continuation_control import report
    elif args.spot_perp:
        from scripts.run_spot_perp_account import report
    elif args.spot_costs:
        from scripts.run_spot_costs import report
    elif args.spot_costs_v2:
        from scripts.run_spot_costs_v2 import report
    elif args.dated:
        from scripts.run_dated_carry import report
    elif args.dated_v2:
        from scripts.run_dated_carry_v2 import report
    elif args.levels:
        from scripts.run_level_probability import report
    elif args.lifecycle:
        from scripts.run_paired_account import report
    else:
        from scripts.run_paper_account import report
    print(report(out=args.out))


if __name__=='__main__':main()
