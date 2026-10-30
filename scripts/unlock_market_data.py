#!/usr/bin/env python3
"""Immutable public funding/mark archive acquisition and portable data bundle; no PnL."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import csv
import gzip
import io
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile
import zipfile

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from lab import prereg
from scripts import unlocks_daily_check as source

DATASET = ROOT/'research/datasets/unlock_market_data_v1'
DEFAULT_RAW = Path('/workspace/quant-small-data/unlock_market_data_v1')
START, END, DAY = source.START, source.END+source.DAY, source.DAY
KINDS = ('fundingRate','markPriceKlines')
MAX_MEMBERS, MAX_UNPACK = 24000,64*1024*1024
sha, put_json = source.sha, source.put_json


def verify():
    protocol=prereg.verify(DATASET/'PROTOCOL.md');text=(DATASET/'PROTOCOL.md').read_text()
    for label,path in [('Collector SHA-256',Path(__file__)),('Requests SHA-256',DATASET/'REQUESTS.csv'),
                       ('Catalogs SHA-256',DATASET/'catalogs.json'),('R258 helper SHA-256',Path(source.__file__))]:
        if re.findall(re.escape(label)+r': `([0-9a-f]{64})`',text)!=[sha(path.read_bytes())]:
            raise ValueError('Frozen declaration mismatch: '+label)
    source.verify()
    with (DATASET/'REQUESTS.csv').open(newline='') as f:rows=list(csv.DictReader(f))
    if [r['key'] for r in rows]!=sorted({r['key'] for r in rows}):raise ValueError('Duplicate/unordered requests')
    for r in rows:
        kind,symbol=r['kind'],r['symbol']
        if kind not in KINDS or not re.fullmatch(r'[A-Z0-9]+USDT',symbol):raise ValueError('Unsafe kind/symbol')
        interval='1d/' if kind=='markPriceKlines' else ''
        prefix=f'data/futures/um/monthly/{kind}/{symbol}/{interval}'
        name=r['key'].removeprefix(prefix)
        expected=symbol+('-1d-' if interval else '-fundingRate-')
        if (not r['key'].startswith(prefix) or not name.startswith(expected) or not name.endswith('.zip')
                or not re.fullmatch(r'20[0-9]{2}-[01][0-9]',name[-11:-4])
                or not '2021-01'<=name[-11:-4]<='2026-09' or not 0<int(r['size'])<=source.MAX_ZIP):
            raise ValueError('Request outside the frozen scope')
    return protocol,rows


def parse(blob,record):
    name=record['key'].rsplit('/',1)[-1]
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        if z.namelist()!=[name[:-4]+'.csv'] or z.infolist()[0].file_size>131072 or z.testzip() is not None:
            raise ValueError('Unexpected CSV/CRC/inflation size: '+name)
        raw=z.read(z.namelist()[0])
    rows=[]
    for i,r in enumerate(csv.reader(io.StringIO(raw.decode()))):
        if i==0 and r[0] in ('calc_time','open_time','open time'):continue
        if len(r)!=(3 if record['kind']=='fundingRate' else 12):raise ValueError('Unexpected schema: '+name)
        t=int(r[0])
        if not START<=t<END:raise ValueError('Reserved/out-of-scope timestamp or unit: '+name)
        month=pd.Timestamp(t,unit='ms',tz='UTC').strftime('%Y-%m')
        if month!=name[-11:-4]:raise ValueError('Timestamp outside its source month')
        if record['kind']=='fundingRate':
            interval,rate=float(r[1]),float(r[2])
            if not np.isfinite([interval,rate]).all() or interval!=int(interval) or not 1<=interval<=24 or abs(rate)>1:
                raise ValueError('Invalid settlement rate/interval')
            rows.append((t,interval,rate))
        else:
            op,hi,lo,cl=[float(x) for x in r[1:5]]
            if (t%DAY or int(r[6])!=t+DAY-1 or not np.isfinite([op,hi,lo,cl]).all()
                    or min(op,hi,lo,cl)<=0 or not lo<=min(op,cl)<=max(op,cl)<=hi):
                raise ValueError('Invalid mark OHLC/timestamp')
            # Volume columns in mark klines are not traded liquidity; never use them as a fill proxy.
            rows.append((t,op,hi,lo,cl))
    if not rows or len({r[0] for r in rows})!=len(rows):raise ValueError('Empty/duplicate source rows')
    return rows


def local_path(record):
    return Path(record['kind'])/record['key'].rsplit('/',1)[-1]


def verify_pair(root,r):
    p=Path(root)/local_path(r);blob=p.read_bytes();check=Path(str(p)+'.CHECKSUM').read_bytes()
    tokens=check.decode('ascii').strip().split()
    if (len(tokens)!=2 or tokens[0]!=sha(blob) or tokens[1].lstrip('*')!=p.name
            or len(blob)!=int(r['size'])):raise ValueError('Source checksum/size mismatch: '+p.name)
    if r.get('sha256') and (sha(blob)!=r['sha256'] or sha(check)!=r['checksum_sha256']):
        raise ValueError('Cached pair changed')
    return blob,check


def acquire(raw):
    protocol,requests=verify();raw=Path(raw);raw.mkdir(parents=True,exist_ok=True)
    started=datetime.now(timezone.utc).isoformat()
    if (raw/'manifest.json').exists():raise FileExistsError('A complete manifest exists; validate instead')
    attempt=len(list(raw.glob('attempt_*.json')))+1
    if attempt>3:raise ValueError('Three bounded passes exhausted; retain failed attempts')
    catalogs=json.loads((DATASET/'catalogs.json').read_text())
    for c in catalogs:
        if sha((raw/c['catalog']).read_bytes())!=c['sha256']:raise ValueError('Catalog changed')
    budget=source.Budget(sum(p.stat().st_size for p in raw.glob('*.xml')))
    def one(r):
        path=raw/local_path(r);checkpath=Path(str(path)+'.CHECKSUM')
        cached=path.exists() and checkpath.exists()
        request_start=None if cached else datetime.now(timezone.utc).isoformat()
        if path.exists() and checkpath.exists():
            blob,check=verify_pair(raw,r)
            with budget.lock:
                budget.used+=len(blob)+len(check)
                if budget.used>source.MAX_TOTAL:raise ValueError('32MiB cache/budget limit')
        else:
            if path.exists() or checkpath.exists():raise ValueError('Partial pair requires inspection; no overwrite')
            blob=budget.get(source.BASE+r['key'],source.MAX_ZIP)
            check=budget.get(source.BASE+r['key']+'.CHECKSUM',512)
            tokens=check.decode('ascii').strip().split()
            if len(tokens)!=2 or tokens[0]!=sha(blob) or tokens[1].lstrip('*')!=path.name or len(blob)!=int(r['size']):
                raise ValueError('Publisher checksum/size mismatch')
            parse(blob,r)
            path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('xb') as f:f.write(blob)
            with checkpath.open('xb') as f:f.write(check)
        rows=parse(blob,r)
        return {**r,'size':int(r['size']),'path':local_path(r).as_posix(),'sha256':sha(blob),
                'checksum_sha256':sha(check),'request_start_utc':request_start,
                'request_end_utc':None if cached else datetime.now(timezone.utc).isoformat(),'cached':cached,'rows':len(rows),'first_ms':min(x[0] for x in rows),'last_ms':max(x[0] for x in rows)}
    records=[];errors=[]
    with ThreadPoolExecutor(24) as pool:
        futures={pool.submit(one,r):r for r in requests}
        for i,f in enumerate(as_completed(futures),1):
            try:records.append(f.result())
            except Exception as exc:errors.append({'key':futures[f]['key'],'error':type(exc).__name__+': '+str(exc)})
            if i%400==0:print(json.dumps({'finished':i,'expected':len(requests),'errors':len(errors),'bytes':budget.used}),flush=True)
    m={'acquisition_start_utc':started,'acquisition_end_utc':datetime.now(timezone.utc).isoformat(),
       'protocol_sha256':protocol,'collector_sha256':sha(Path(__file__).read_bytes()),
       'requests_sha256':sha((DATASET/'REQUESTS.csv').read_bytes()),'catalogs_sha256':sha((DATASET/'catalogs.json').read_bytes()),
       'response_bytes':budget.used,'archives':sorted(records,key=lambda x:x['key']),
       'errors':sorted(errors,key=lambda x:x['key']),'status':'COMPLETE' if not errors and len(records)==len(requests) else 'INCOMPLETE',
       'source':'https://data.binance.vision/','meaning':'Public acquisition/schema validation only; no return, funding PnL or liquidation computation'}
    put_json(raw/f'attempt_{attempt}.json',m)
    if m['status']=='COMPLETE':put_json(raw/'manifest.json',m)
    return m


def validate(raw):
    protocol,requests=verify();raw=Path(raw);m=json.loads((raw/'manifest.json').read_text())
    if m['status']!='COMPLETE' or m['errors'] or m['protocol_sha256']!=protocol:
        raise ValueError('No complete matching acquisition')
    if [r['key'] for r in m['archives']]!=[r['key'] for r in requests]:raise ValueError('Inventory changed')
    groups={}
    for r in m['archives']:
        blob,_=verify_pair(raw,r);rows=parse(blob,r);key=(r['kind'],r['symbol'])
        out=groups.setdefault(key,[]);out.extend(x[0] for x in rows)
    coverage=[]
    for (kind,symbol),times in sorted(groups.items()):
        if len(set(times))!=len(times):raise ValueError('Duplicate timestamps across archives')
        times=sorted(times)
        coverage.append({'kind':kind,'symbol':symbol,'rows':len(times),'first_ms':times[0],'last_ms':times[-1],
                         'gaps_over_one_day':sum(b-a>DAY for a,b in zip(times,times[1:]))})
    return m,coverage


def bundle_files(raw,prices):
    m,coverage=validate(raw);raw=Path(raw);prices=Path(prices)
    price_manifest=prices/'manifest.json';expected=(source.LANE/'DATA.sha256').read_text().strip()
    if sha(price_manifest.read_bytes())!=expected:raise ValueError('R258 price input manifest changed')
    pm=json.loads(price_manifest.read_text());files={}
    if pm['status']!='COMPLETE' or pm['errors']:raise ValueError('Incomplete original prices')
    for r in pm['archives']:
        for suffix,h in [('',r['sha256']),('.CHECKSUM',r['checksum_sha256'])]:
            p=prices/(r['path']+suffix)
            if sha(p.read_bytes())!=h:raise ValueError('R258 price pair changed')
            files['prices/'+p.name]=p
    for r in m['archives']:
        for suffix in ('','.CHECKSUM'):
            p=raw/(r['path']+suffix);files['auxiliary/'+p.relative_to(raw).as_posix()]=p
    for prefix,folder in [('prices',prices),('auxiliary',raw)]:
        for pattern in ('*.xml','manifest.json','attempt_*.json'):
            for p in folder.glob(pattern):files[prefix+'/'+p.name]=p
    return files,m,coverage


def pack(raw,prices,out):
    verify();out=Path(out)
    if out.exists():raise FileExistsError('Never replace a published data bundle')
    files,m,coverage=bundle_files(raw,prices)
    contents={name:{'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for name,p in sorted(files.items())}
    if sum(x['bytes'] for x in contents.values())>MAX_UNPACK or len(contents)>MAX_MEMBERS:
        raise ValueError('Portable bundle exceeds fixed bounds')
    index=json.dumps(contents,sort_keys=True,separators=(',',':')).encode()
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('xb') as dest,gzip.GzipFile(fileobj=dest,mode='wb',filename='',mtime=0) as gz,tarfile.open(fileobj=gz,mode='w',format=tarfile.USTAR_FORMAT) as tar:
        for name,blob in [('BUNDLE_CONTENTS.json',index)]+[(name,p.read_bytes()) for name,p in sorted(files.items())]:
            info=tarfile.TarInfo(name);info.size=len(blob);info.mtime=0;info.uid=info.gid=0;info.mode=0o644
            tar.addfile(info,io.BytesIO(blob))
    if out.stat().st_size>source.MAX_TOTAL:raise ValueError('Compressed bundle too large; retain evidence')
    result={'file':out.name,'sha256':sha(out.read_bytes()),'bytes':out.stat().st_size,'files':len(files),
            'unpacked_payload_bytes':sum(x['bytes'] for x in contents.values()),'coverage':coverage,
            'price_manifest_sha256':sha((Path(prices)/'manifest.json').read_bytes()),
            'auxiliary_manifest_sha256':sha((Path(raw)/'manifest.json').read_bytes()),
            'protocol_sha256':prereg.verify(DATASET/'PROTOCOL.md'),'meaning':m['meaning']}
    put_json(Path(str(out)+'.json'),result)
    return result


def restore(bundle,descriptor,out):
    bundle,out=Path(bundle),Path(out);meta=json.loads(Path(descriptor).read_text())
    if out.exists():raise FileExistsError('Restoration needs a fresh directory')
    if bundle.stat().st_size>source.MAX_TOTAL or sha(bundle.read_bytes())!=meta['sha256']:
        raise ValueError('Bundle size/hash mismatch')
    payloads={};total=0
    with tarfile.open(bundle,'r:gz') as tar:
        for member in tar:
            p=PurePosixPath(member.name)
            if (not member.isfile() or p.is_absolute() or '..' in p.parts or '\\' in member.name
                    or member.name in payloads or member.size>MAX_UNPACK or len(payloads)>=MAX_MEMBERS+1):
                raise ValueError('Unsafe/duplicate/oversized bundle member')
            total+=member.size
            if total>MAX_UNPACK+8*1024*1024:raise ValueError('Inflated bundle exceeds limit')
            payloads[member.name]=tar.extractfile(member).read()
    if 'BUNDLE_CONTENTS.json' not in payloads:raise ValueError('Bundle index missing')
    index=json.loads(payloads.pop('BUNDLE_CONTENTS.json'))
    if set(index)!=set(payloads):raise ValueError('Bundle members differ from index')
    for name,blob in payloads.items():
        if name.split('/',1)[0] not in ('prices','auxiliary') or sha(blob)!=index[name]['sha256'] or len(blob)!=index[name]['bytes']:
            raise ValueError('Bundle index/hash/scope mismatch')
    out.mkdir(parents=True)
    for name,blob in payloads.items():
        p=out/name;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(blob)
    return {'restored_files':len(payloads),'bytes':sum(map(len,payloads.values())),'price_cache':str(out/'prices'),'auxiliary_cache':str(out/'auxiliary')}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['fetch','validate','pack','restore'])
    p.add_argument('--raw',type=Path,default=DEFAULT_RAW);p.add_argument('--prices',type=Path,default=Path('/workspace/quant-small-data/unlocks_daily_v1'))
    p.add_argument('--bundle',type=Path,default=DATASET/'market-data.tar.gz');p.add_argument('--out',type=Path)
    a=p.parse_args()
    if a.action=='fetch':r=acquire(a.raw);print(json.dumps({k:v for k,v in r.items() if k!='archives'},sort_keys=True))
    elif a.action=='validate':m,c=validate(a.raw);print(json.dumps({'status':m['status'],'archives':len(m['archives']),'series':len(c),'rows':sum(x['rows'] for x in c)},sort_keys=True))
    elif a.action=='pack':r=pack(a.raw,a.prices,a.bundle);print(json.dumps({k:v for k,v in r.items() if k!='coverage'},sort_keys=True))
    else:
        if a.out is None:p.error('restore requires --out')
        print(json.dumps(restore(a.bundle,Path(str(a.bundle)+'.json'),a.out),sort_keys=True))

if __name__=='__main__':main()
