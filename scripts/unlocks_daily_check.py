#!/usr/bin/env python3
"""R258: bounded Binance daily-bar cross-check of the fixed R265 unlock events."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import threading
import urllib.error
import urllib.request
import zipfile

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lab import prereg

LANE = ROOT/'experiments/unlocks_daily_v1'
EVENTS = ROOT/'experiments/unlocks_v1/events.csv'
EVENT_SHA = '24cd0d052bea6dcab1e4f862dad3227348644fb887ba61d14ca56cdb00cd794e'
DAY = 86400000
START = int(pd.Timestamp('2021-01-01', tz='UTC').timestamp()*1000)
END = int(pd.Timestamp('2026-09-30', tz='UTC').timestamp()*1000)
BASE = 'https://data.binance.vision/'
MAX_TOTAL = 32*1024*1024
MAX_ZIP = 16384


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def put_json(path, value):
    with Path(path).open('x') as f:
        f.write(json.dumps(value, indent=1, sort_keys=True, allow_nan=False)+'\n')


def verify():
    spec = prereg.verify(LANE/'PREREG.md')
    text = (LANE/'PREREG.md').read_text()
    for label, path in [('Runner SHA-256', Path(__file__)), ('Requests SHA-256', LANE/'REQUESTS.json')]:
        declared = re.findall(re.escape(label)+r': `([0-9a-f]{64})`', text)
        if declared != [sha(path.read_bytes())]:
            raise ValueError(f'{label} does not match frozen specification')
    if sha(EVENTS.read_bytes()) != EVENT_SHA:
        raise ValueError('R265 event bytes changed')
    requests = json.loads((LANE/'REQUESTS.json').read_text())
    keys = [r['key'] for r in requests]
    if len(keys) != len(set(keys)) or keys != sorted(keys):
        raise ValueError('Duplicate or unordered request inventory')
    for r in requests:
        symbol = r['symbol']
        if not re.fullmatch(r'[A-Z0-9]+USDT', symbol):
            raise ValueError('Unsafe symbol')
        expected = f'data/futures/um/monthly/klines/{symbol}/1d/{symbol}-1d-'
        month = r['key'][len(expected):-4]
        if not r['key'].startswith(expected) or not r['key'].endswith('.zip') or not '2021-01' <= month <= '2026-09':
            raise ValueError('Request outside the fixed 2021+ daily-perp scope')
        if not 0 < r['size'] <= MAX_ZIP:
            raise ValueError('Catalog archive too large')
    return spec, requests


class Budget:
    def __init__(self, used=0):
        self.used, self.lock = used, threading.Lock()

    def get(self, url, limit):
        # Reserve before opening a connection; in-flight responses cannot exceed the cap.
        with self.lock:
            if self.used+limit+1 > MAX_TOTAL:
                raise ValueError('Hard 32 MiB response budget reached')
            self.used += limit+1
        raw = b''
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'quant-lab-public-data/1'}), timeout=20) as r:
                raw = r.read(limit+1)
            if len(raw) > limit:
                raise ValueError('Oversized public response')
            return raw
        finally:
            with self.lock:
                self.used -= limit+1-len(raw)


def fetch(raw):
    spec, requests = verify()
    raw = Path(raw); raw.mkdir(parents=True, exist_ok=True)
    final = raw/'manifest.json'
    if final.exists():
        raise FileExistsError('Frozen data manifest already exists; run without fetching')
    attempt = len(list(raw.glob('attempt_*.json')))+1
    if attempt > 2:
        raise ValueError('At most two bounded fetch passes; retain failures')
    budget = Budget(sum(p.stat().st_size for p in raw.glob('*.inventory.xml')))
    def one(row):
        name = row['key'].rsplit('/',1)[-1]
        zpath, cpath = raw/name, raw/(name+'.CHECKSUM')
        cached = zpath.exists() and cpath.exists()
        if cached:
            content, check = zpath.read_bytes(), cpath.read_bytes()
            with budget.lock:
                budget.used += len(content)+len(check)
                if budget.used > MAX_TOTAL:
                    raise ValueError('Cached input exceeds bounded data scope')
        else:
            if zpath.exists() or cpath.exists():
                raise ValueError(f'Partial cache requires inspection; never overwrite: {name}')
            content = budget.get(BASE+row['key'], MAX_ZIP)
            check = budget.get(BASE+row['key']+'.CHECKSUM', 512)
        tokens = check.decode('ascii').strip().split()
        if len(tokens)!=2 or tokens[0] != sha(content) or tokens[1].lstrip('*') != name:
            raise ValueError(f'Publisher checksum mismatch: {name}')
        if len(content) != row['size']:
            raise ValueError(f'Catalog size changed: {name}')
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            if z.namelist() != [name[:-4]+'.csv'] or z.infolist()[0].file_size > 32768 or z.testzip() is not None:
                raise ValueError(f'Unexpected archive: {name}')
        if not cached:
            with zpath.open('xb') as f: f.write(content)
            with cpath.open('xb') as f: f.write(check)
        return {**row, 'path': name, 'sha256': sha(content), 'checksum_sha256': sha(check)}
    rows, errors = [], []
    with ThreadPoolExecutor(12) as pool:
        futures = {pool.submit(one,r): r for r in requests}
        for i, future in enumerate(as_completed(futures),1):
            try:
                rows.append(future.result())
            except Exception as exc:
                errors.append({'key': futures[future]['key'], 'error': type(exc).__name__+': '+str(exc)})
            if i%200 == 0:
                print(json.dumps({'finished':i,'expected':len(requests),'errors':len(errors),'bytes':budget.used}),flush=True)
    manifest = {'prereg_sha256': spec, 'runner_sha256': sha(Path(__file__).read_bytes()),
                'requests_sha256': sha((LANE/'REQUESTS.json').read_bytes()), 'bytes': budget.used,
                'archives': sorted(rows,key=lambda x:x['key']), 'errors': sorted(errors,key=lambda x:x['key']),
                'status': 'COMPLETE' if not errors and len(rows)==len(requests) else 'INCONCLUSIVE'}
    manifest['inventory_sha256'] = {p.name:sha(p.read_bytes()) for p in sorted(raw.glob('*.inventory.xml'))}
    put_json(raw/f'attempt_{attempt}.json', manifest)
    if manifest['status']=='COMPLETE':
        put_json(final, manifest)
    return manifest


def parse(content, name):
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        if z.namelist() != [name[:-4]+'.csv']:
            raise ValueError('Unexpected ZIP members')
        blob = z.read(z.namelist()[0])
    records=[]
    for i,row in enumerate(csv.reader(io.StringIO(blob.decode()))):
        if i==0 and row[0] in ('open_time','open time'):
            continue
        if len(row)!=12:
            raise ValueError('Unexpected futures kline schema')
        t=int(row[0]); end=int(row[6]); values=[float(row[k]) for k in (1,2,3,4,5,7)]
        if not START <= t <= END or t%DAY or end != t+DAY-1:
            raise ValueError('Unexpected timestamp unit/calendar or reserved sample')
        op,hi,lo,cl,vol,qv=values
        if not np.isfinite(values).all() or min(op,hi,lo,cl)<=0 or min(vol,qv)<0 or not lo<=min(op,cl)<=max(op,cl)<=hi:
            raise ValueError('Invalid OHLCV')
        records.append((t,cl,hi,lo,vol,qv))
    if len({r[0] for r in records}) != len(records):
        raise ValueError('Duplicate daily bar')
    return records


def load(raw):
    spec, requests = verify()
    raw=Path(raw); payload=(raw/'manifest.json').read_bytes()
    lock=(LANE/'DATA.sha256').read_text().strip()
    if lock != sha(payload):
        raise ValueError('Data manifest is not locked')
    manifest=json.loads(payload)
    if manifest['status']!='COMPLETE' or manifest['errors'] or manifest['prereg_sha256']!=spec:
        raise ValueError('Incomplete/different data capture')
    if [r['key'] for r in manifest['archives']] != [r['key'] for r in requests]:
        raise ValueError('Input inventory differs from the frozen finite request list')
    bars={}
    for record in manifest['archives']:
        path=raw/record['path']; content=path.read_bytes()
        check=(raw/(record['path']+'.CHECKSUM')).read_bytes()
        if sha(content)!=record['sha256'] or sha(check)!=record['checksum_sha256'] or check.decode().split()[0]!=sha(content):
            raise ValueError('Changed archive/checksum')
        target=bars.setdefault(record['symbol'],{})
        for row in parse(content,record['path']):
            if row[0] in target: raise ValueError('Overlapping archive rows')
            target[row[0]]=row
    return bars,sha(payload),manifest


def price(bars,symbol,day):
    rows=bars.get(symbol,{})
    a,b=rows.get(int(day)-7*DAY),rows.get(int(day))
    if a is None or b is None or a[4]<=0 or b[4]<=0:
        return None
    path=[rows.get(int(day)-k*DAY) for k in range(6,-1,-1)]
    complete=all(r is not None and r[4]>0 for r in path)
    adverse=max(r[2]/a[1]-1 for r in path) if complete else None
    return {'gross':1-b[1]/a[1], 'entry':a[1], 'exit':b[1],
            'max_adverse_high':adverse,'complete_hold_path':complete}


def summary(values,days):
    x=np.asarray(values,float)
    if len(x)!=len(days) or not np.isfinite(x).all(): raise ValueError('Invalid event statistics')
    if not len(x):return {'n':0,'mean':None,'cluster_t':None,'hit_rate':None,'worst':None,'clusters':0}
    iso=pd.to_datetime(np.asarray(days,dtype='int64'),unit='ms',utc=True).isocalendar(); groups={}
    for key,v in zip(zip(iso.year,iso.week),x-x.mean()):groups[key]=groups.get(key,0.)+float(v)
    g=len(groups);se=np.sqrt(g/(g-1)*sum(v*v for v in groups.values()))/len(x) if g>1 else np.nan
    return {'n':len(x),'mean':float(x.mean()),'cluster_t':float(x.mean()/se) if np.isfinite(se) and se>0 else None,
            'hit_rate':float(np.mean(x>0)),'worst':float(x.min()),'clusters':g}


def null_test(bars,events,scored,reps=2000):
    rng=np.random.default_rng(265);pools={};counts={}
    for symbol in sorted({r['perp'] for r in scored}):
        dates=events.loc[events.perp==symbol,'day_ms'].to_numpy(dtype=np.int64)
        pool=[]
        for d in range(START+37*DAY,END+1,DAY):
            if len(dates) and np.min(np.abs(dates-d))<=14*DAY:continue
            r=price(bars,symbol,d)
            if r is not None:pool.append(r['gross']-.002)
        if not pool:raise ValueError('No admissible random dates for '+symbol)
        pools[symbol]=np.asarray(pool);counts[symbol]=len(pool)
    means=np.empty(reps)
    for k in range(reps):means[k]=np.mean([pools[r['perp']][rng.integers(len(pools[r['perp']]))] for r in scored])
    observed=np.mean([r['gross']-.002 for r in scored])
    return {'p':float((1+np.count_nonzero(means>=observed))/(reps+1)),'mean':float(means.mean()),
            'observed':float(observed),'replications':reps,'seed':265,'admissible_counts':counts}


def evaluate(bars,events):
    cohort=events[(events.venue=='binance')&(events.window=='archive')&events.check.isin(['verified','unverified'])]
    cohort=cohort.sort_values(['day_ms','perp']);scored=[];excluded=[]
    for r in cohort.to_dict('records'):
        trade=price(bars,r['perp'],r['day_ms'])
        if trade is None:excluded.append({**r,'reason':'missing/nontraded exact entry or exit daily bar'})
        else:scored.append({**r,**trade})
    if not scored:raise ValueError('No priceable fixed events')
    null=null_test(bars,events,scored);days=[r['day_ms'] for r in scored];net=np.array([r['gross']-.002 for r in scored])
    s=summary(net,days);half=len(net)//2;totals={}
    for r,v in zip(scored,net):totals[r['perp']]=totals.get(r['perp'],0.)+v
    top=sorted(totals,key=lambda k:(-totals[k],k))[:3];rest=np.array([r['perp'] not in top for r in scored])
    checks={'G1_week_t_ge2':s['cluster_t'] is not None and s['cluster_t']>=2,'G2_null_p_lt005':null['p']<.05,
            'G3_halves_positive':half>0 and net[:half].mean()>0 and net[half:].mean()>0,
            'G4_without_top3_positive':bool(rest.any() and net[rest].mean()>0)}
    records=[]
    def add(label,subset,values):
        for multiple in (1,2,3):records.append({'label':label,'cost_multiple':multiple,
            **summary(np.asarray(values)-.002*multiple,[r['day_ms'] for r in subset])})
    add('primary',scored,[r['gross'] for r in scored])
    for year in sorted({r['day'][:4] for r in scored}):
        subset=[r for r in scored if r['day'].startswith(year)];add('year_'+year,subset,[r['gross'] for r in subset])
    subset=[r for r in scored if r['check']=='verified'];add('verified_only',subset,[r['gross'] for r in subset])
    hedged=[];values=[]
    for r in scored:
        b=price(bars,'BTCUSDT',r['day_ms'])
        if b is not None:hedged.append(r);values.append(r['gross']-b['gross'])
    # The hedge is a two-leg hypothetical: 20bp round trip on EACH leg at 1x.
    for multiple in (1,2,3):records.append({'label':'btc_hedged_two_leg_cost','cost_multiple':multiple,
        **summary(np.asarray(values)-.004*multiple,[r['day_ms'] for r in hedged])})
    result={'verdict':'PARTIAL' if all(checks.values()) else 'NULL','gate':0,'trials':2,'checks':{k:bool(v) for k,v in checks.items()},
        'expected_events':len(cohort),'priced_events':len(scored),'excluded_events':len(excluded),'null':null,
        'top3_removed':top,'halves_1x':[float(net[:half].mean()) if half else None,float(net[half:].mean())],
        'without_top3_1x':float(net[rest].mean()) if rest.any() else None,
        'events_losing_over40pct_1x':int(np.sum(net<-.4)),'events_losing_over100pct_1x':int(np.sum(net<-1)),
        'complete_hold_path':sum(r['complete_hold_path'] for r in scored),
        'high_adverse_over40pct':sum(r['max_adverse_high'] is not None and r['max_adverse_high']>.4 for r in scored),
        'interpretation':'Spent retrospective fixed-calendar price-only daily-bar diagnostic; not R265 replication, executable MEXC PnL or prospective evidence'}
    return scored,excluded,records,result


def run(raw,out):
    out=Path(out)
    if out.exists():raise FileExistsError('Refuse existing result directory')
    bars,manifest_sha,manifest=load(raw)
    events=pd.read_csv(EVENTS)
    scored,excluded,stats,result=evaluate(bars,events)
    out.mkdir(parents=True)
    for name,rows in [('events.csv',scored),('excluded.csv',excluded),('summary.csv',stats)]:
        pd.DataFrame(rows).to_csv(out/name,index=False,lineterminator='\n')
    put_json(out/'verdict.json',result)
    put_json(out/'manifest.json',{'prereg_sha256':prereg.verify(LANE/'PREREG.md'),'runner_sha256':sha(Path(__file__).read_bytes()),
        'source_manifest_sha256':manifest_sha,'source_events_sha256':EVENT_SHA,'numpy':np.__version__,'pandas':pd.__version__,
        'outputs':{p.name:sha(p.read_bytes()) for p in sorted(out.iterdir())}})
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=['fetch','run'])
    ap.add_argument('--raw',type=Path,default=Path('/workspace/quant-small-data/unlocks_daily_v1'))
    ap.add_argument('--out',type=Path,default=LANE/'results');a=ap.parse_args()
    result=fetch(a.raw) if a.action=='fetch' else run(a.raw,a.out)
    print(json.dumps({k:v for k,v in result.items() if k!='archives'},sort_keys=True))

if __name__=='__main__':main()
