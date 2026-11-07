"""One fixed public CDE candle-schema probe; counts only, never prices or returns."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
from urllib import request,error
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'research/intake/funding_notional_20261103/cde_candle_probe_20261107'
CAP=32768
class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None

def acquire():
    OUT.mkdir(parents=True,exist_ok=True)
    parent=json.loads((ROOT/'research/intake/funding_notional_20261103/cde_rate_contract_20261107/budget_before.json').read_text())
    budget=dict(parent_path='research/intake/funding_notional_20261103/cde_rate_contract_20261107/budget_before.json',parent_conservative_calls=parent['conservative_total_requests'],parent_conservative_bytes=parent['conservative_total_bytes'],worst_new_calls=2,worst_new_bytes=2*(CAP+1),original_call_ceiling=8000,original_byte_ceiling=262144000,allowance_reset=False)
    budget['conservative_total_calls']=budget['parent_conservative_calls']+budget['worst_new_calls']
    budget['conservative_total_bytes']=budget['parent_conservative_bytes']+budget['worst_new_bytes']
    if budget['conservative_total_calls']>8000 or budget['conservative_total_bytes']>262144000: raise ValueError('accumulated allowance exhausted')
    with (OUT/'ACQUISITION_STARTED.json').open('x') as f: f.write(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(),budget=budget))+'\n')
    with (OUT/'budget_before.json').open('x') as f: f.write(json.dumps(budget,indent=2)+'\n')
    # Four hours at the first available MDA history boundary; predetermined, no price selection.
    start=int(datetime(2026,8,9,2,tzinfo=timezone.utc).timestamp()); end=start+4*3600
    receipts=[]
    for coin,product in [('btc','BIP-20DEC30-CDE'),('eth','ETP-20DEC30-CDE')]:
        url=f'https://api.coinbase.com/api/v3/brokerage/market/products/{product}/candles?start={start}&end={end}&granularity=ONE_HOUR&limit=8'
        row=dict(organization='Coinbase',publication_date='undated API',url=url,started_utc=datetime.now(timezone.utc).isoformat(),requested_start=start,requested_end=end,cap=CAP,scope='counts/schema/time bounds only; no OHLC values summarized',auth=False,user_agent='Python urllib default',redirects=False)
        with (OUT/'requests.jsonl').open('a') as f: f.write(json.dumps(dict(event='START',coin=coin,**row))+'\n');f.flush()
        raw=b'';status=None;complete=False;problem=None
        try:
            try: response=request.build_opener(NoRedirect).open(url,timeout=20)
            except error.HTTPError as exc: response=exc
            with response:
                status=response.code;row['content_type']=response.headers.get('Content-Type','');raw=response.read(CAP+1)
            complete=len(raw)<=CAP
            if not complete or status!=200 or 'html' in row['content_type'].lower(): raise ValueError('denied/over-limit/unusable; no retry')
            obj=json.loads(raw); bars=obj.get('candles')
            if not isinstance(bars,list) or len(bars)>8: raise ValueError('schema/limit drift')
            times=[int(x['start']) for x in bars]
            row['counts_only']=dict(rows=len(bars),unique_times=len(set(times)),oldest=min(times) if times else None,newest=max(times) if times else None,fields=sorted(set().union(*(x.keys() for x in bars))) if bars else [])
        except (OSError,ValueError,TypeError,KeyError) as exc: problem=type(exc).__name__+': '+str(exc)
        row.update(status=status,received_utc=datetime.now(timezone.utc).isoformat(),bytes_read=len(raw),response_complete=complete,charged_bytes=len(raw) if complete else CAP+1,sha256=hashlib.sha256(raw).hexdigest(),body=coin+'.body.gz',error=problem)
        with (OUT/row['body']).open('xb') as f: f.write(gzip.compress(raw,mtime=0))
        with (OUT/(coin+'.receipt.json')).open('x') as f: f.write(json.dumps(row,indent=2)+'\n')
        with (OUT/'requests.jsonl').open('a') as f: f.write(json.dumps(dict(event='END',coin=coin,**row))+'\n')
        receipts.append(row)
        if problem: break
    with (OUT/'acquisition.json').open('x') as f: f.write(json.dumps(dict(requests=receipts,total_calls=len(receipts),total_charged_bytes=sum(x['charged_bytes'] for x in receipts),financial_values_inspected=False),indent=2)+'\n')
    print(json.dumps([dict(status=x['status'],bytes=x['bytes_read'],counts_only=x.get('counts_only'),error=x['error']) for x in receipts]))
    return int(any(x['error'] for x in receipts))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--acquire',action='store_true');a=p.parse_args()
    raise SystemExit(acquire() if a.acquire else print('INACTIVE counts-only probe'))
