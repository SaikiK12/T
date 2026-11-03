"""Read-only timing/ID diagnosis after R400 refusal; never loads price/size columns.

This source-engineering audit neither resumes the consumed study nor computes
returns, features, model fits, PnL or a changed admission rule. Counts are marginal
timing-only conditions, not R400's full price-qualified label coverage.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from lab import path_response as rule  # noqa: E402
from scripts import run_path_response as frozen  # noqa: E402

BOOK_COLUMNS=("t","off","u")
TRADE_COLUMNS=("t","off","a")


def quantiles(values):
    x=np.asarray(values,float)
    return None if not len(x) else dict(zip(("p50","p95","p99","max"),
                                          map(float,np.quantile(x,[.5,.95,.99,1.]))))


def audit(book,trades,day):
    def arrays(frame,columns):
        if set(frame.columns)!=set(columns): raise ValueError("only timestamp/ID projections allowed")
        if any(frame[c].dtype.kind not in "iu" for c in columns): raise ValueError("integer metadata required")
        return {c:frame[c].to_numpy(dtype=np.int64) for c in columns}
    b,q=arrays(book,BOOK_COLUMNS),arrays(trades,TRADE_COLUMNS)
    if len(book)<2 or len(trades)<2: return dict(status="INSUFFICIENT_METADATA")
    bt,qt=b["t"]-b["off"],q["t"]-q["off"]
    raw=dict(book_rows=len(bt),trade_rows=len(qt),
             book_nonincreasing_ids=int(np.sum(np.diff(b["u"])<=0)),
             trade_nonincreasing_ids=int(np.sum(np.diff(q["a"])<=0)),
             book_backwards_receive=int(np.sum(np.diff(bt)<0)),
             trade_backwards_receive=int(np.sum(np.diff(qt)<0)),
             book_receive_gap_us=quantiles(np.diff(bt)),trade_receive_gap_us=quantiles(np.diff(qt)))
    if raw["book_backwards_receive"] or raw["trade_backwards_receive"]:
        return dict(status="UNORDERED_RECEIVE_CLOCK",raw=raw)
    _,grid=rule.decision_grid(day,int(b["off"][0]))
    bu=np.r_[False,np.diff(b["u"])<=0];qu=np.r_[False,np.diff(q["a"])<=0]
    counts=Counter();entry=[];exit_=[];spans=[]
    for d in grid:
        i0=np.searchsorted(bt,d-rule.LOOK_US,side="right")-1
        i1=np.searchsorted(bt,d,side="left")
        j0=np.searchsorted(qt,d-rule.LOOK_US,side="left")
        j1=np.searchsorted(qt,d,side="left")
        if i0<0 or i1<=i0 or j1-j0<2:
            counts["past_boundary"]+=1;continue
        stale=(d-rule.LOOK_US-bt[i0]>rule.QUOTE_AGE_US or d-bt[i1-1]>rule.QUOTE_AGE_US
               or np.any(np.diff(bt[i0:i1])>rule.QUOTE_AGE_US)
               or qt[j0]-(d-rule.LOOK_US)>rule.TRADE_AGE_US or d-qt[j1-1]>rule.TRADE_AGE_US
               or np.any(np.diff(qt[j0:j1])>rule.TRADE_AGE_US))
        offsets=np.r_[b["off"][i0:i1],q["off"][j0:j1]]
        if stale: counts["past_stale"]+=1;continue
        if bu[i0:i1].any() or qu[j0:j1].any(): counts["past_nonincreasing_id"]+=1;continue
        if offsets.max()-offsets.min()>rule.CLOCK_STEP_US: counts["past_offset_span"]+=1;continue
        if np.intersect1d(bt[i0+1:i1],qt[j0:j1]).size: counts["past_cross_stream_tie"]+=1;continue
        counts["timing_past_eligible"]+=1
        ie=np.searchsorted(bt,d+rule.LAG_US,side="left")
        ix=np.searchsorted(bt,d+rule.LAG_US+rule.HOLD_US,side="left")
        if ix>=len(bt): counts["future_boundary"]+=1;continue
        de,dx=bt[ie]-(d+rule.LAG_US),bt[ix]-(d+rule.LAG_US+rule.HOLD_US)
        entry.append(de);exit_.append(dx)
        wait=de>rule.EXEC_WAIT_US or dx>rule.EXEC_WAIT_US
        ids=bu[i1:ix+1].any()
        future=b["off"][i1:ix+1]
        span=max(offsets.max(),future.max())-min(offsets.min(),future.min())
        spans.append(span);clock=span>rule.CLOCK_STEP_US
        counts["future_entry_wait"]+=int(de>rule.EXEC_WAIT_US)
        counts["future_exit_wait"]+=int(dx>rule.EXEC_WAIT_US)
        counts["future_nonincreasing_id"]+=int(ids)
        counts["future_offset_span"]+=int(clock)
        counts["future_any_timing_or_id_failure"]+=int(wait or ids or clock)
    return dict(status="TIMING_METADATA_ONLY",raw=raw,grid_decisions=len(grid),counts=dict(counts),
                entry_wait_us=quantiles(entry),exit_wait_us=quantiles(exit_),
                combined_offset_span_us=quantiles(spans),
                denominator="timing-past eligible, not full R400 price/size-qualified decisions",
                price_columns_loaded=False,returns_computed=False,market_fit=False,
                r400_resumed=False,gate_eligible=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data",type=Path,default=ROOT/"data/rawtape")
    args=p.parse_args()
    spec=frozen.verify_inputs()
    expected=json.loads((frozen.LANE/"training_manifest.json").read_text())
    frozen.check_manifest(args.data,expected)
    report={}
    for coin in rule.COINS:
        b=pd.read_parquet(args.data/"bbo"/coin/"2026-10-29.parquet",columns=list(BOOK_COLUMNS))
        q=pd.read_parquet(args.data/"trade"/coin/"2026-10-29.parquet",columns=list(TRADE_COLUMNS))
        report[coin]=audit(b,q,"2026-10-29")
    frozen.check_manifest(args.data,expected)
    print(json.dumps(dict(prereg_sha256=spec,instruments=report),sort_keys=True,indent=2,allow_nan=False))


if __name__=="__main__": main()
