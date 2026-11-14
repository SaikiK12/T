"""R317 fixed fee-route decomposition on already-seen sealed R316 books.

No network/capture mode, no historical policy rerun, owner fee inference, order,
funding cash or paper activation. Freeze code/spec/old raw identity before report.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from lab.depth_replay import DepthReplay  # noqa:E402
from lab.fee_routes import PATHS,routes,assess_route  # noqa:E402
from scripts import probe_warm_values as parent  # noqa:E402

LANE=ROOT/'experiments/fee_routes_v1'
PARENT=ROOT/'experiments/warm_values_v1'
sha,write=parent.sha,parent.write


def verify(lane=LANE):
    parent.verify(lane)
    m=json.loads((lane/'data_inputs.json').read_text())
    if sha(lane/'data_inputs.json') not in (lane/'PREREG.md').read_text():raise ValueError('unbound held data identity')
    if m['parent_path']!='experiments/warm_values_v1':raise ValueError('fixed held parent required')
    expected={'experiments/warm_values_v1/'+s for s in ('PREREG.md','PREREG.sha256','code_inputs.json','evidence_inputs.json','results.json','observations.jsonl.gz')}
    if set(m['sha256'])!=expected or m.get('parent_data_already_seen') is not True:
        raise ValueError('complete fixed parent spec/code/raw seal/seen-outcome identity required')
    for name,digest in m['sha256'].items():
        if sha(ROOT/name)!=digest:raise ValueError('held parent identity drift: '+name)


def rows_for(replay,receipts,sources):
    rows=[]
    for grid in parent.GRIDS:
        quantities={}
        for delay in (0,300):
            for s in parent.SYMBOLS:
                target=replay.anchor.mono_ns+grid*10**9+delay*10**6
                row,books=replay.observe(s,target,quantities.get(s),allow_new_quantity=(delay==0))
                if delay==0:quantities[s]=row['quantity_base']
                metadata=replay.metadata.get(s,{}).get('mexc',{})
                lm=replay.metadata.get(s,{}).get('lighter',{})
                for route in routes(s,metadata,receipts.get(s),target,replay.anchor,sources,lm):
                    new=assess_route(route,books,row['quantity_base'],delay,row['book_flags'])
                    control=row['cost']
                    delta=(control['fee_usd']-new['cost']['fee_usd'] if control and new['cost'] and
                           control['displayed_fillable'] and new['cost']['displayed_fillable'] else None)
                    rows.append({**row,'grid_second':grid,'access_delay_ms':delay,'reference_reserve_cost':control,
                                 **new,'reserve_minus_scenario_charge_usd':delta,
                                 'funding_cash_status':'unscored: no actual event-bound value/exposure/units or owner fee evidence'})
    return rows


def report(lane=LANE,out=None):
    verify(lane)
    frames,mapping,anchor,connections=parent.depth.load_capture(PARENT)
    raw=json.loads((PARENT/'evidence/receipts.json').read_text())['records']
    receipts={r['name'].removesuffix('_mexc_metadata'):r for r in raw if r['name'].endswith('_mexc_metadata')}
    provenance=json.loads((lane/'sources.json').read_text())['scenario_sources']
    replay=DepthReplay(frames,mapping['metadata'],{int(k):v for k,v in mapping['names'].items()},anchor,connections)
    rows=rows_for(replay,receipts,provenance)
    out=Path(out) if out is not None else lane;out.mkdir(exist_ok=True)
    encoded=''.join(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n' for r in rows).encode()
    parent.depth.immutable(out/'observations.jsonl.gz',gzip.compress(encoded,mtime=0))
    result={'registry_id':'R317','rows':len(rows),'descriptive_fee_paths':list(PATHS),'predictive_trials':0,'paper_days':0,
            'net_return_tested':False,'data_identity_sha256':sha(lane/'data_inputs.json'),
            'observations_sha256':sha(out/'observations.jsonl.gz'),'capital_usd':10000,'capital_per_venue_usd':5000,
            'scope':'already-seen book sample; public fee assumptions read later; no as-of/account entitlement, paid cash, fills or alpha evidence','cells':[]}
    for s in parent.SYMBOLS:
        for delay in (0,300):
            for profile in PATHS:
                rr=[r for r in rows if r['symbol']==s and r['access_delay_ms']==delay and r['fee_path']==profile]
                cc=[r for r in rr if r['cost'] and r['cost']['displayed_fillable'] and not r['book_flags']]
                result['cells'].append({'symbol':s,'delay_ms':delay,'fee_path':profile,'grids':len(rr),'cost_rows':len(cc),
                    'minimum_delay_supported_cost_rows':sum(r['minimum_delay_satisfied'] for r in cc),
                    'fee_flags':dict(Counter(f for r in rr for f in r['fee_flags'])),
                    'cost_tiers':[{'multiple':k,'n':len(cc),
                        'round_trip_usd_range':[min(v),max(v)] if v else None,
                        'break_even_leg_bp_range':[min(b),max(b)] if b else None}
                        for k in (1,2,3) for v in [[r['cost']['scenarios'][k-1]['round_trip_cost_usd'] for r in cc]]
                        for b in [[r['cost']['scenarios'][k-1]['break_even_leg_bp'] for r in cc]]]})
    verify(lane)  # immutable source/data identities must also survive the report
    parent.depth.immutable(out/'results.json',(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())
    return out/'results.json'


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path)
    print(report(out=p.parse_args().out))
