"""Finite dependent-mean controls and Monte Carlo tolerance calibration.

These kernels support a registered synthetic diagnostic. Calibrating on named
simulated profiles never certifies a market process, net alpha or activation.
All observations are retained; missing/gapped/degenerate samples cannot pass.
"""
import math
from statistics import NormalDist
import numpy as np
from scipy.special import betaincinv

N=273
FAMILY=3
BLOCKS=(14,28)
METHODS=('iid_gaussian','circular14','calibrated_obm14','calibrated_obm28')


def sample(values,day_ids):
    if np.iscomplexobj(values):raise ValueError('real daily differences required')
    x=np.asarray(values,dtype=float);days=np.asarray(day_ids)
    if x.shape!=(N,FAMILY) or not np.isfinite(x).all():raise ValueError('complete273by3 finite differences required; no deletion or imputation')
    if days.shape!=(N,) or days.dtype.kind not in 'iu' or not all(int(b)-int(a)==1 for a,b in zip(days[:-1],days[1:])):raise ValueError('complete consecutive integer day identities required')
    return x


def obm(values,day_ids,*,block):
    """Overlapping batch-means estimate of variance of the full-sample mean.

    se² = b/((n-b)*(n-b+1)) * sum_i(batch_mean_i - full_mean)².
    Every day enters the full mean; all contiguous b-day windows enter the
    variance. No compressed calendar or dropped incomplete final batch.
    """
    if block not in BLOCKS:raise ValueError('fixed14/28day blocks required')
    x=sample(values,day_ids)
    with np.errstate(over='ignore',invalid='ignore',divide='ignore'):
        mean=x.mean(axis=0);sums=np.vstack((np.zeros(FAMILY),np.cumsum(x-mean,axis=0)))
        means=(sums[block:]-sums[:-block])/block
        se2=block*np.sum(means**2,axis=0)/((N-block)*(N-block+1));se=np.sqrt(se2);t=mean/se
    if (x==x[0]).all(axis=0).any() or not all(np.isfinite(v).all() for v in (mean,se2,se,t)) or (se2<=0).any():
        return {'state':'DEGENERATE','mean':mean.tolist() if np.isfinite(mean).all() else None,
                'se':None,'t':None,'actual_order_allowed':False,'reason':'constant_or_unrepresentable_moments'}
    return {'state':'ASSESSED','mean':mean.tolist(),'se':se.tolist(),'t':t.tolist(),'actual_order_allowed':False}


def binomial_tail(n,k,p):
    """P[Binomial(n,p)>=k], evaluated as a bounded finite log-PMF sum."""
    if type(n) is not int or not 1<=n<=10000 or type(k) is not int or not 1<=k<=n or not 0<p<1:
        raise ValueError('finite binomial tolerance parameters required')
    logs=[math.lgamma(n+1)-math.lgamma(j+1)-math.lgamma(n-j+1)+j*math.log(p)+(n-j)*math.log1p(-p) for j in range(k,n+1)]
    m=max(logs)
    return math.exp(m)*sum(math.exp(v-m) for v in logs)


def tolerance_order(paths,*,alpha=.05,confidence=.99,calibration_cells=16):
    """One-sided tolerance order, simultaneous over the fixed calibration cells.

    With independent paths from each specified continuous null distribution,
    P[F(T_(k)) < 1-alpha] = P[Binomial(m,1-alpha)>=k]. Bonferroni over cells
    bounds the probability any declared null CDF has coverage below1-alpha.
    This is Monte Carlo calibration confidence, not market-process coverage.
    """
    if type(paths) is not int or not 20<=paths<=2000 or not 0<alpha<.5 or not .5<confidence<1:
        raise ValueError('bounded calibration parameters required')
    if type(calibration_cells) is not int or not 1<=calibration_cells<=32:raise ValueError('bounded declared calibration family required')
    risk=(1-confidence)/calibration_cells
    # Tail is monotone in k; only its upper end can satisfy the requirement.
    for k in range(max(1,int(paths*(1-alpha))),paths+1):
        tail=binomial_tail(paths,k,1-alpha)
        if tail<=risk:return {'order':k,'paths':paths,'tail_probability':tail,'cell_error_budget':risk,
            'alpha':alpha,'joint_calibration_confidence':confidence,'calibration_cells':calibration_cells}
    raise ValueError('insufficient paths for finite tolerance confidence; no infinite cutoff fallback')


def calibrate(max_statistics,profile_ids,*,paths=500):
    """Return two cutoffs, each maximized over all predeclared null profiles."""
    if len(profile_ids)!=8 or len(set(profile_ids))!=8:raise ValueError('exact eight-profile calibration family required')
    if set(max_statistics)!={f'{p}|{b}' for p in profile_ids for b in BLOCKS}:raise ValueError('missing/extra calibration cell')
    order=tolerance_order(paths,calibration_cells=16);cutoffs={};cells=[]
    for block in BLOCKS:
        values=[]
        for p in profile_ids:
            a=np.asarray(max_statistics[f'{p}|{block}'],float)
            if a.shape!=(paths,) or not np.isfinite(a).all() or (a<0).any():raise ValueError('finite complete max-abs-t paths required')
            c=float(np.sort(a)[order['order']-1]);values.append(c)
            cells.append({'profile':p,'block_days':block,'paths':paths,'tolerance_order':order['order'],'cell_cutoff':c})
        cutoff=max(values)
        if cutoff<=0:raise ValueError('nondegenerate finite positive cutoff required')
        cutoffs[str(block)]=cutoff
    return {'cutoffs':cutoffs,'cells':cells,'tolerance':order,'n':N,'family':FAMILY,
        'scope':'Only the declared simulated null profiles; no market coverage,profitability or activation certified.',
        'market_validated':False,'actual_order_allowed':False}


def calibrated_intervals(values,day_ids,*,block,calibration):
    if calibration.get('n')!=N or calibration.get('family')!=FAMILY or calibration.get('market_validated') is not False:
        raise ValueError('matching synthetic-only calibration contract required')
    s=obm(values,day_ids,block=block)
    if s['state']!='ASSESSED':return {**s,'lower':None,'upper':None,'market_evidence_eligible':False}
    critical=float(calibration['cutoffs'][str(block)])
    if not math.isfinite(critical) or critical<=0:raise ValueError('finite positive calibrated cutoff required')
    with np.errstate(over='ignore',invalid='ignore'):
        mean=np.asarray(s['mean']);width=critical*np.asarray(s['se']);lower=mean-width;upper=mean+width
    if not np.isfinite(lower).all() or not np.isfinite(upper).all():
        return {**s,'state':'DEGENERATE','lower':None,'upper':None,'reason':'unrepresentable_interval',
                'market_evidence_eligible':False}
    return {**s,'lower':lower.tolist(),'upper':upper.tolist(),'critical':critical,
        'market_evidence_eligible':False,'scope':'Synthetic calibration only; a separately frozen market protocol is still required.'}


def iid_intervals(values,day_ids):
    x=sample(values,day_ids)
    with np.errstate(over='ignore',invalid='ignore'):
        mean=x.mean(axis=0);se=np.std(x,axis=0,ddof=1)/math.sqrt(N)
    if (x==x[0]).all(axis=0).any() or not np.isfinite(mean).all() or not np.isfinite(se).all() or (se<=0).any():
        return {'state':'DEGENERATE','lower':None,'upper':None}
    c=NormalDist().inv_cdf(1-.05/(2*FAMILY))
    with np.errstate(over='ignore',invalid='ignore'):
        lower=mean-c*se;upper=mean+c*se
    if not np.isfinite(lower).all() or not np.isfinite(upper).all():return {'state':'DEGENERATE','lower':None,'upper':None}
    return {'state':'ASSESSED','lower':lower.tolist(),'upper':upper.tolist(),
        'scope':'Deliberately naive iid Gaussian negative control; no dependent-size guarantee.'}


def binomial_interval(successes,paths,*,comparisons=40):
    """Exact Clopper-Pearson interval with a declared Bonferroni family.

    The independent units are Monte Carlo paths from one named distribution,
    not financial days. This is not a Wilson normal-score approximation.
    """
    if type(paths) is not int or not 1<=paths<=10000 or type(successes) is not int or not 0<=successes<=paths:raise ValueError('explicit bounded binomial counts required')
    if type(comparisons) is not int or not 1<=comparisons<=1000:raise ValueError('finite diagnostic comparison family required')
    tail=.05/(2*comparisons)
    lower=0. if successes==0 else float(betaincinv(successes,paths-successes+1,tail))
    upper=1. if successes==paths else float(betaincinv(successes+1,paths-successes,1-tail))
    if not 0<=lower<=upper<=1:raise ValueError('unrepresentable binomial interval')
    return [lower,upper]
