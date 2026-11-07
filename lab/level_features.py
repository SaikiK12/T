"""Receipt-bound retained candle features; no invented order-flow inputs.

Normal API open/high/low match the existing close/volume series. 'real*' fields
are deliberately unused; their semantics are not inferred. Bar shapes are not
quote-event OFI, absorption, executable quotes or first-seen market evidence.
"""
import gzip
import hashlib
import json
import math
from pathlib import Path
from urllib.parse import parse_qs,urlsplit

import numpy as np
import pandas as pd
from lab.level_probability import HOUR

FEATURES=('level_distance','return1','return6','return24','rv6_ratio',
          'volume_shock','body_direction','wick_asymmetry','btc_residual24','level_side')


def retained_ohlc(root,records,symbol,prices,cutoff):
    """Decode ONLY receipt-bound pages, return close-times strictly before cutoff.

    Hashing reads whole pages. Rows outside the stage are not returned or used
    for features/fit. Current clock/fair-index/first-seen meaning is not granted
    by a historical API receipt. Conflicting duplicates and mismatches abort.
    """
    rows={}
    pages=[r for r in records if r['symbol']==symbol]
    if not pages:raise ValueError('missing registered original pages')
    for r in pages:
        url=urlsplit(r['url']);q=parse_qs(url.query)
        if (url.scheme!='https' or url.netloc!='contract.mexc.com' or url.path!='/api/v1/contract/kline/'+symbol+'_USDT'
            or set(q)!={'interval','start','end'} or q.get('interval')!=['Min60']
            or any(len(q[k])!=1 or not q[k][0].isdigit() for k in ('start','end'))):
            raise ValueError('wrong source/asset/interval identity')
        first,last=int(q['start'][0])*1000,int(q['end'][0])*1000
        if last<first:raise ValueError('source query range reversed')
        if first+HOUR>=cutoff:continue
        path=Path(root)/r['path'];packed=path.read_bytes()
        if hashlib.sha256(packed).hexdigest()!=r['gzip_sha256']:raise ValueError('retained page bytes drift')
        raw=gzip.decompress(packed)
        if hashlib.sha256(raw).hexdigest()!=r['raw_sha256']:raise ValueError('receipt raw identity mismatch')
        data=json.loads(raw)
        if data.get('success') is not True or not isinstance(data.get('data'),dict):raise ValueError('source success required')
        d=data['data'];names=('open','high','low','close','vol','amount');n=len(d['time'])
        if any(len(d[k])!=n for k in names):raise ValueError('source array length mismatch')
        for i,stamp in enumerate(d['time']):
            if type(stamp) is not int:raise ValueError('native integer source clock required')
            stamp=stamp*1000
            if stamp%HOUR or not first<=stamp<=last:raise ValueError('nonhourly or out-of-query source candle')
            if stamp+HOUR>=cutoff:continue
            x=tuple(float(d[k][i]) for k in names)
            if stamp in rows and rows[stamp]!=x:raise ValueError('conflicting retained OHLC rows')
            rows[stamp]=x
    p=prices[prices.t+HOUR<cutoff]
    for r in p.itertuples(index=False):
        x=rows.get(int(r.t))
        if x is None or x[3:]!=(float(r.close),float(r.vol),float(r.amount)):
            raise ValueError('original OHLC does not match frozen close/volume/amount')
    index=np.asarray(p.t,np.int64)+HOUR
    x=np.asarray([rows[int(t)] for t in p.t],float)
    frame=pd.DataFrame(x,index=index,columns=names)
    return frame


def attach(m,ohlc):
    f=ohlc.reindex(m['t']);x=f[['open','high','low','close','vol','amount']].to_numpy(float)
    valid=np.isfinite(x).all(axis=1)&(x[:,:4]>0).all(axis=1)&(x[:,4:]>0).all(axis=1)
    valid&=(x[:,2]<=np.minimum(x[:,0],x[:,3]))&(np.maximum(x[:,0],x[:,3])<=x[:,1])
    # Existing prices/volume remain authoritative for activity; OHLC adds a
    # feature constraint, never relaxes the old source/volume eligibility.
    return {**m,'ohlc':x,'ohlc_valid':valid}


def vector(m,btc,s):
    if s['state']!='event':return None
    i=s['index']
    if i<72 or len(btc['t'])<=i or btc['t'][i]!=s['decision']:
        return None
    if not m['ohlc_valid'][i-72:i+1].all() or not btc['valid'][i-24:i+1].all():return None
    sigma=s['sigma'];side=s['side'];p=m['close'];o,h,l,c,vol,_=m['ohlc'][i]
    span=h-l
    body=side*(c-o)/span if span>0 else 0.
    wick=side*((min(o,c)-l)-(h-max(o,c)))/span if span>0 else 0.
    ret=np.diff(np.log(p[i-72:i+1]));rv=float(np.mean(ret*ret))
    past_volume=m['ohlc'][i-72:i,4];median=float(np.median(past_volume))
    if median<=0 or sigma<=0 or rv<=0:return None
    r24=math.log(p[i]/p[i-24]);b24=math.log(btc['close'][i]/btc['close'][i-24])
    x=[side*math.log(p[i]/s['level'])/sigma,
       side*math.log(p[i]/p[i-1])/sigma,
       side*math.log(p[i]/p[i-6])/sigma,side*r24/sigma,
       math.log1p(float(np.mean(ret[-6:]**2))/rv),math.log(vol/median),
       body,wick,side*(r24-b24)/sigma,float(side)]
    return [float(v) for v in x] if np.isfinite(x).all() else None
