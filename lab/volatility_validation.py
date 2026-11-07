"""Finite causal RV forecast controls; risk skill, not direction or net alpha.

Daily target is the sum of24 hourly squared log returns. Missing/stale hourly
closes stay missing. Existing APSI's univariate EWMA component is compared to
fixed1/7/30-day RV means; this does not validate its unimplemented PIT top20 basket.
"""
import math
import numpy as np
from lab.apsi import basket_sigma24

HOUR=3_600_000
DAY=24*HOUR
MODELS=('mean1','mean7','mean30','ewma72')


def daily_returns(frame,start_ms,end_ms):
    if (type(start_ms) is not int or type(end_ms) is not int or start_ms%DAY or end_ms%DAY or end_ms<=start_ms):
        raise ValueError('ordered exact UTC-day boundaries required')
    if frame.t.duplicated().any() or not np.all(frame.t.to_numpy(np.int64)%HOUR==0):raise ValueError('unique exact hourly source timestamps required')
    grid=np.arange(start_ms,end_ms+HOUR,HOUR,dtype=np.int64)
    source=frame.assign(close_time=frame.t.astype('int64')+HOUR).set_index('close_time')
    p=source.close.reindex(grid).to_numpy(float);v=source.vol.reindex(grid).to_numpy(float)
    valid=np.isfinite(p)&(p>0)&np.isfinite(v)&(v>0)
    r=np.full(len(grid)-1,np.nan)
    ok=valid[:-1]&valid[1:]
    r[ok]=np.log(p[1:][ok]/p[:-1][ok])
    hours=r.reshape(-1,24)
    rv=np.where(np.isfinite(hours).all(axis=1),np.sum(hours*hours,axis=1),np.nan)
    return grid[::24][:-1],r,rv


def forecasts(hourly,daily_rv):
    r=np.asarray(hourly,float);y=np.asarray(daily_rv,float)
    if r.ndim!=1 or y.ndim!=1 or len(r)!=24*len(y):raise ValueError('aligned24-hour targets required')
    out=np.full((len(y),len(MODELS)),np.nan)
    for i in range(len(y)):
        for j,n in enumerate((1,7,30)):
            h=y[max(0,i-n):i]
            if len(h)==n and np.isfinite(h).all():out[i,j]=float(h.mean())
        if i>=7:
            x=r[i*24-168:i*24]
            if np.isfinite(x).all():out[i,3]=basket_sigma24(x[:,None],[1.],half_life_hours=72.)**2
    return out


def loss(target,predicted):
    y,p=np.broadcast_arrays(np.asarray(target,float),np.asarray(predicted,float))
    out=np.full(y.shape,np.nan);ok=np.isfinite(y)&(y>=0)&np.isfinite(p)&(p>0)
    # Gaussian quasi-likelihood up to a target-only constant. Remains finite
    # for a genuinely zero realized variance; no artificial epsilon forecast.
    out[ok]=np.log(p[ok])+y[ok]/p[ok]
    return out


def block_intervals(differences,*,block,repetitions=2000,seed=320):
    x=np.asarray(differences,float)
    if x.ndim!=2 or not np.isfinite(x).all() or len(x)<30 or block not in (7,14):raise ValueError('complete daily paired losses and fixed7/14-day blocks required')
    if type(repetitions) is not int or not 100<=repetitions<=4000:raise ValueError('bounded bootstrap repetitions required')
    rng=np.random.default_rng(seed);n,k=x.shape;blocks=(n+block-1)//block
    origins=rng.integers(0,n,size=(repetitions,blocks))
    idx=((origins[:,:,None]+np.arange(block))%n).reshape(repetitions,-1)[:,:n]
    means=x[idx].mean(axis=1)
    # Simultaneous within this finite three-comparison family only. No claim
    # of global FWER control after the lab's prior adaptive9478782 trials.
    alpha=.05/k
    lo,hi=np.quantile(means,[alpha/2,1-alpha/2],axis=0)
    return {'block_days':block,'repetitions':repetitions,'seed':seed,'mean':x.mean(axis=0).tolist(),
        'lower':lo.tolist(),'upper':hi.tolist(),'scope':'circular block percentile intervals; Bonferroni within this fixed family, not program-wide adaptation control'}


def null_calibration(*,paths=100,n=273,repetitions=400,seed=1320):
    if type(paths) is not int or not 10<=paths<=200:raise ValueError('bounded null path count required')
    rng=np.random.default_rng(seed);out=[]
    for block in (7,14):
        failed=0
        for rep in range(paths):
            innovations=rng.normal(size=(n+128,3));x=np.zeros_like(innovations)
            for t in range(1,len(x)):x[t]=.6*x[t-1]+innovations[t]
            z=block_intervals(x[128:],block=block,repetitions=repetitions,seed=seed+rep)
            failed+=any(l>0 or u<0 for l,u in zip(z['lower'],z['upper']))
        p=failed/paths;se=math.sqrt(p*(1-p)/paths)
        out.append({'block_days':block,'paths':paths,'family_false_exclusions':failed,'fraction':p,
                    'binomial_standard_error':se,'null':'three zero-mean AR1(.6) series after128 burn-in; not a universal coverage guarantee'})
    return out
