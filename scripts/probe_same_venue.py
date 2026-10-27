"""R343 one finite same-venue public metadata/book capture, not orders."""
from concurrent.futures import ThreadPoolExecutor
import gzip
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lab.acquisition_budget import BudgetJournal,BudgetLimits
from scripts.probe_spot_costs import Acquisition as Parent, fatal
from scripts.run_same_venue import verify,LANE,save


class Acquisition(Parent):
    def __init__(self,out):
        self.out=out;self.deadline=time.monotonic_ns()+90*1_000_000_000
        self.budget=BudgetJournal(out/'budget.jsonl','R343/one-same-venue-current-capture',
            BudgetLimits(8,512*1024,56*1_000_000_000,7*1_000_000_000))


def capture():
    config=verify();out=LANE/'evidence';out.mkdir()  # never reset even after failure.
    a=Acquisition(out);records=[];stopped=False
    endpoint='https://www.deribit.com/api/v2/public/'
    instruments=[(coin+'_'+kind,name) for coin,assets in config['instruments'].items() for kind,name in assets.items()]
    for label,name in instruments:
        r=a.get_reserved(a.reserve(label+'_rules',endpoint+'get_instrument?instrument_name='+name));records.append(r)
        okay=not fatal(r) and r['http_status']==200
        if okay:
            body=json.loads(gzip.decompress((out/r['body']).read_bytes()))
            okay=isinstance(body,dict) and isinstance(body.get('result'),dict) and 'error' not in body
        if not okay or a.budget.status()['violations']:stopped=True;break
    if not stopped:
        jobs=[a.reserve(label+'_book',endpoint+'get_order_book?instrument_name='+name+'&depth=5') for label,name in instruments]
        with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(a.get_reserved,jobs))
        records+=results;stopped=any(fatal(r) or r['http_status']!=200 for r in results)
    save(out/'capture.json',{'registry_id':'R343','records':records,'fatal_stop':stopped,
        'budget':a.budget.status(),'closed':True,'unused_allowance_closed':True,'actual_orders':0,
        'historical_requests_spent_unchanged':7757,'historical_reported_MiB_spent_unchanged':'229.85'})
    save(LANE/'data_inputs.json',{'registry_id':'R343','prereg_sha256':__import__('hashlib').sha256((LANE/'PREREG.md').read_bytes()).hexdigest(),
        'sha256':{str(p.relative_to(ROOT)):__import__('hashlib').sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file()}})
    print('R343 inputs sealed; commit raw identity before economic reporting.')


if __name__=='__main__':capture()
