"""R400: causal raw-tape features, bounded equation selection and quote replay.

Public arrival-ordered BBO/trades, not queue positions or confirmed executions.
All clocks and provenance still need external qualification before admission.
"""
from collections import Counter
import datetime as dt

import numpy as np
import pandas as pd

from lab import formula_space as fs

COINS = ("BTCUSDT", "ETHUSDT")
BASE = ("flow", "ofi", "r5", "imb", "spread", "depth", "coin_eth")
LEAVES = ("area", "refill", "flow")
LOOK_US = 5_000_000
LAG_US = 500_000
HOLD_US = 5_000_000
STEP_US = 10_000_000
QUOTE_AGE_US = 500_000
EXEC_WAIT_US = 100_000
TRADE_AGE_US = 1_000_000
CLOCK_STEP_US = 1_000
NOTIONAL = 100.0
CAPITAL = 1000.0
FEE_BP = 5.0  # declared scenario per leg, not an owner's observed fee
RIDGE = 10.0
MIN_COVERAGE = .80
MIN_FORWARD_DAYS = 5
MIN_FORWARD_BLOCKS = 20
BOOTSTRAPS = 2000
SEED = 400


class DataError(ValueError):
    pass


def equation_family():
    return fs.enumerate_family(tuple(fs.variable(s) for s in LEAVES)+(fs.constant(1),),
                               max_nodes=5,max_attempts=2000)


def _arrays(frame,columns):
    out={}
    for name in columns:
        if name not in frame or frame[name].dtype.kind not in "iu":
            raise DataError(f"missing/noninteger source column: {name}")
        out[name]=frame[name].to_numpy(dtype=np.int64)
    # Historical off is int32: the absolute offset is truncated. This is a
    # relative receive clock up to a constant while encoded off stays stable,
    # never authenticated absolute monotonic time or UTC.
    out["mono"]=out["t"]-out["off"]
    if len(frame)<2 or np.any(np.diff(out["mono"])<0):
        raise DataError("empty/short tape or backwards receive clock; no sorting repair")
    return out


def decision_grid(day,offset):
    start=int(dt.datetime.fromisoformat(day+"T13:00:00+00:00").timestamp()*1e6)
    end=start+4*3600*1_000_000
    wall=np.arange(start+STEP_US,end-LAG_US-HOLD_US,STEP_US,dtype=np.int64)
    # Avoid every local UTC-labelled hour boundary, including possible funding.
    phase=wall%(3600*1_000_000)
    wall=wall[(phase>=30_000_000)&(phase<=3600*1_000_000-30_000_000)]
    return wall,wall-offset


def make_samples(book,trades,day,coin):
    """Fixed nonoverlapping decisions; features use only events strictly before d.

    Receive timestamps order streams; tied cross-stream observations are unknown.
    Same-price positive displayed-size changes are a net-replenishment proxy,
    not identified new orders. Future quotes enter labels/replay only.
    """
    if coin not in COINS:
        raise DataError("undeclared instrument")
    b=_arrays(book,("t","off","u","bid","sp","bq","aq"))
    q=_arrays(trades,("t","off","a","p","q","m"))
    bt,qt=b["mono"],q["mono"]
    wall,grid=decision_grid(day,int(b["off"][0]))
    badb=(b["bid"]<=0)|(b["sp"]<=0)|(b["bq"]<=0)|(b["aq"]<=0)
    badq=(q["p"]<=0)|(q["q"]<=0)|~np.isin(q["m"],(0,1))
    badb[1:]|=np.diff(b["u"])<=0
    badq[1:]|=np.diff(q["a"])<=0
    mid=(b["bid"].astype(float)+b["sp"]*.5)/100
    ask=(b["bid"]+b["sp"])/100
    bid=b["bid"]/100
    signed=q["q"].astype(float)*np.where(q["m"]==1,-1,1)
    output=[]; reasons=Counter()
    for w,d in zip(wall,grid):
        i0=np.searchsorted(bt,d-LOOK_US,side="right")-1
        i1=np.searchsorted(bt,d,side="left")
        j0=np.searchsorted(qt,d-LOOK_US,side="left")
        j1=np.searchsorted(qt,d,side="left")
        ie=np.searchsorted(bt,d+LAG_US,side="left")
        ix=np.searchsorted(bt,d+LAG_US+HOLD_US,side="left")
        if i0<0 or i1<=i0 or j1-j0<2:
            reasons["boundary_or_no_flow_coverage"]+=1;continue
        # All feature state is already observed by d; no future execution field
        # is used in any feature or action threshold.
        if (d-LOOK_US-bt[i0]>QUOTE_AGE_US or d-bt[i1-1]>QUOTE_AGE_US
                or np.any(np.diff(bt[i0:i1])>QUOTE_AGE_US)
                or qt[j0]-(d-LOOK_US)>TRADE_AGE_US or d-qt[j1-1]>TRADE_AGE_US
                or np.any(np.diff(qt[j0:j1])>TRADE_AGE_US)):
            reasons["stale_feature_window"]+=1;continue
        if np.any(badb[i0:i1]) or np.any(badq[j0:j1]):
            reasons["invalid_or_nonincreasing_ids"]+=1;continue
        offsets=np.r_[b["off"][i0:i1],q["off"][j0:j1]]
        if offsets.max()-offsets.min()>CLOCK_STEP_US:
            reasons["clock_step"]+=1;continue
        if np.intersect1d(bt[i0+1:i1],qt[j0:j1],assume_unique=False).size:
            reasons["cross_stream_tie"]+=1;continue
        depth0=(float(b["bq"][i0])+b["aq"][i0])/2
        qs=signed[j0:j1]/depth0
        cs=np.r_[0.,np.cumsum(qs)]
        # Integrate two staircase paths without inventing an order at ties.
        k=np.searchsorted(bt,qt[j0:j1],side="right")-1
        p_at_trade=1e4*(mid[k]/mid[i0]-1)
        p=1e4*(mid[i0:i1]/mid[i0]-1)
        before_quote=np.searchsorted(qt[j0:j1],bt[i0+1:i1],side="left")
        area=.5*(np.dot(p_at_trade,qs)-np.dot(cs[before_quote],np.diff(p)))
        samebid=np.diff(b["bid"][i0:i1])==0
        asks=b["bid"][i0:i1]+b["sp"][i0:i1]
        sameask=np.diff(asks)==0
        rb=np.maximum(np.diff(b["bq"][i0:i1]),0)[samebid].sum()/depth0
        ra=np.maximum(np.diff(b["aq"][i0:i1]),0)[sameask].sum()/depth0
        bids=b["bid"][i0:i1];bsize=b["bq"][i0:i1];asize=b["aq"][i0:i1]
        ofi=((bids[1:]>=bids[:-1])*bsize[1:]-(bids[1:]<=bids[:-1])*bsize[:-1]
             -(asks[1:]<=asks[:-1])*asize[1:]+(asks[1:]>=asks[:-1])*asize[:-1]).sum()/depth0
        last=i1-1
        # Future quality never removes an otherwise eligible decision. An
        # unavailable exit is unresolved, not a conveniently omitted loss.
        label_valid=(ix<len(bt) and bt[ie]-(d+LAG_US)<=EXEC_WAIT_US
                     and bt[ix]-(d+LAG_US+HOLD_US)<=EXEC_WAIT_US
                     and not np.any(badb[i1:ix+1]))
        if label_valid:
            future_offsets=b["off"][i1:ix+1]
            label_valid=(max(offsets.max(),future_offsets.max())-
                         min(offsets.min(),future_offsets.min())<=CLOCK_STEP_US)
        execution_valid=label_valid and min(bid[ie]*b["bq"][ie]/1000,ask[ie]*b["aq"][ie]/1000,
                                           bid[ix]*b["bq"][ix]/1000,ask[ix]*b["aq"][ix]/1000)>=NOTIONAL
        mid_return=1e4*(mid[ix]/mid[ie]-1) if label_valid else np.nan
        if not label_valid: reasons["unknown_future_label"]+=1
        if not execution_valid: reasons["unknown_future_execution"]+=1
        def future(arr,index): return float(arr[index]) if label_valid else np.nan
        output.append(dict(day=day,coin=coin,decision_us=int(w),
            block=int(w//(3600*1_000_000)),flow=float(np.clip(cs[-1],-20,20)),
            ofi=float(np.clip(ofi,-20,20)),
            r5=float(np.clip(p[-1],-50,50)),
            imb=float((float(b["bq"][last])-b["aq"][last])/(float(b["bq"][last])+b["aq"][last])),
            spread=float(np.clip(1e4*(ask[last]-bid[last])/mid[last],0,20)),
            depth=float(np.clip((float(b["bq"][last])+b["aq"][last])/(2*depth0),0,20)),
            coin_eth=int(coin=="ETHUSDT"),area=float(np.clip(area,-100,100)),
            refill=float(np.clip(rb-ra,-20,20)),mid_return=float(mid_return),
            label_valid=bool(label_valid),execution_valid=bool(execution_valid),
            entry_mid=future(mid,ie),exit_mid=future(mid,ix),
            entry_bid=future(bid,ie),entry_ask=future(ask,ie),
            exit_bid=future(bid,ix),exit_ask=future(ask,ix)))
    return pd.DataFrame(output),dict(expected=len(grid),eligible=len(output),reasons=dict(reasons))


def scale_fit(x):
    x=np.asarray(x,float)
    mean=x.mean(axis=0);std=x.std(axis=0)
    return dict(mean=mean.tolist(),std=np.where(std<1e-8,1.,std).tolist())


def scale_apply(x,state):
    return np.clip((np.asarray(x,float)-np.asarray(state["mean"]))/np.asarray(state["std"]),-10,10)


def expression_values(expr,values):
    """Small float64 adapter; declared guards and original input masks survive.

    Exact symbolic identities do not promise bitwise floating-point equality.
    Near-zero denominators (abs <=1e-6) are unknown, never zero-filled.
    """
    n=len(next(iter(values.values())))
    mask=np.ones(n,dtype=bool)
    for atom in expr.inputs:
        mask&=np.isfinite(values[atom.name])
    def poly(terms):
        out=np.zeros(n)
        with np.errstate(all="ignore"):
            for atoms,c in terms:
                term=np.full(n,float(c))
                for atom in atoms: term*=values[atom.name]
                out+=term
        return out
    for guard in expr.guards:
        v=poly(guard);mask&=np.isfinite(v)&(np.abs(v)>1e-6)
    num,den=poly(expr.numerator),poly(expr.denominator)
    mask&=np.isfinite(num)&np.isfinite(den)&(np.abs(den)>1e-6)
    out=np.full(n,np.nan)
    with np.errstate(all="ignore"): out[mask]=num[mask]/den[mask]
    out[~np.isfinite(out)]=np.nan
    return out


def ridge_fit(x,y):
    x=np.column_stack((np.ones(len(x)),x))
    penalty=np.eye(x.shape[1])*RIDGE;penalty[0,0]=0
    return np.linalg.solve(x.T@x+penalty,x.T@np.asarray(y,float)).tolist()


def ridge_predict(x,coef):
    return np.column_stack((np.ones(len(x)),x))@np.asarray(coef)


def residualize(x,feature,projection=None):
    design=np.column_stack((np.ones(len(x)),x))
    if projection is None:
        projection=np.linalg.lstsq(design,feature,rcond=None)[0]
    return feature-design@np.asarray(projection),np.asarray(projection).tolist()


def choose_equation(train,selection):
    """Fit only development data; select once, including baseline/no-extra option."""
    if len(train)<100 or len(selection)<100:
        raise DataError("too few development observations")
    if not np.isfinite(train[[*BASE,*LEAVES,"mid_return"]].to_numpy()).all():
        raise DataError("nonfinite development input")
    if not np.isfinite(selection[[*BASE,*LEAVES,"mid_return"]].to_numpy()).all():
        raise DataError("nonfinite selection input")
    bscale=scale_fit(train[list(BASE)])
    lscale=scale_fit(train[list(LEAVES)])
    xb,xs=(scale_apply(d[list(BASE)],bscale) for d in (train,selection))
    z,zs=(dict(zip(LEAVES,scale_apply(d[list(LEAVES)],lscale).T)) for d in (train,selection))
    y,ys=train.mid_return.to_numpy(),selection.mid_return.to_numpy()
    base_coef=ridge_fit(xb,y)
    base_mse=float(np.mean((ys-ridge_predict(xs,base_coef))**2))
    family=equation_family();attempts=[];best=None
    for index,expr in enumerate(family.forms):
        row=dict(index=index,text=expr.text,nodes=expr.nodes)
        if not any(a.name in ("area","refill") for a in expr.inputs):
            row["status"]="no_new_primitive";attempts.append(row);continue
        ft,fv=expression_values(expr,z),expression_values(expr,zs)
        if not np.isfinite(ft).all() or not np.isfinite(fv).all() or np.std(ft)<1e-8:
            row["status"]="undefined_or_constant";attempts.append(row);continue
        ft,projection=residualize(xb,ft)
        fv,_=residualize(xs,fv,projection)
        if np.std(ft)<1e-8:
            row["status"]="baseline_span";attempts.append(row);continue
        fscale=scale_fit(ft[:,None])
        xt=np.column_stack((xb,scale_apply(ft[:,None],fscale)))
        xv=np.column_stack((xs,scale_apply(fv[:,None],fscale)))
        coef=ridge_fit(xt,y)
        mse=float(np.mean((ys-ridge_predict(xv,coef))**2))
        row.update(status="fit",selection_mse=mse);attempts.append(row)
        rank=(mse,expr.nodes,expr.text,index)
        if best is None or rank<best[0]: best=(rank,index)
    selected=best[1] if best and best[0][0]<.99*base_mse else None
    # The selection rule is over; refit the chosen artifact on all development.
    dev=pd.concat((train,selection),ignore_index=True)
    bscale=scale_fit(dev[list(BASE)]);lscale=scale_fit(dev[list(LEAVES)])
    x=scale_apply(dev[list(BASE)],bscale)
    artifact=dict(version=1,baseline_scale=bscale,leaf_scale=lscale,
                  baseline_coef=ridge_fit(x,dev.mid_return),selected_index=selected,
                  selected_text=None,selected_scale=None,selected_coef=None,selected_projection=None,
                  selection_baseline_mse=base_mse,
                  family=dict(attempts=family.attempts,retained=len(family.forms),
                              duplicates=family.duplicates,invalid=family.invalid,
                              exhausted=family.budget_exhausted),search=attempts)
    if selected is not None:
        expr=family.forms[selected]
        vals=dict(zip(LEAVES,scale_apply(dev[list(LEAVES)],lscale).T))
        feature=expression_values(expr,vals)
        if not np.isfinite(feature).all():
            # Changed normalization can expose a divisor at zero. No rescue,
            # next-best search or replacement is permitted after selection.
            artifact["refit_status"]="selected_domain_invalid";return artifact
        feature,projection=residualize(x,feature)
        if np.std(feature)<1e-8:
            artifact["refit_status"]="selected_baseline_span";return artifact
        fscale=scale_fit(feature[:,None])
        artifact.update(selected_text=expr.text,selected_scale=fscale,selected_projection=projection,
                        selected_coef=ridge_fit(np.column_stack((x,scale_apply(feature[:,None],fscale))),dev.mid_return))
    artifact["refit_status"]="ready"
    return artifact


def predict(frame,artifact):
    x=scale_apply(frame[list(BASE)],artifact["baseline_scale"])
    baseline=ridge_predict(x,artifact["baseline_coef"])
    if artifact["selected_index"] is None:
        return baseline,baseline.copy(),np.ones(len(frame),bool)
    if artifact.get("refit_status")!="ready":
        raise DataError("selected expression invalid after declared refit; no fallback")
    family=equation_family();expr=family.forms[artifact["selected_index"]]
    if expr.text!=artifact["selected_text"]:
        raise DataError("formula identity drift")
    vals=dict(zip(LEAVES,scale_apply(frame[list(LEAVES)],artifact["leaf_scale"]).T))
    feature=expression_values(expr,vals)
    valid=np.isfinite(feature);augmented=np.full(len(frame),np.nan)
    feature[valid],_=residualize(x[valid],feature[valid],artifact["selected_projection"])
    augmented[valid]=ridge_predict(np.column_stack((x[valid],scale_apply(feature[valid,None],artifact["selected_scale"]))),artifact["selected_coef"])
    return baseline,augmented,valid


def replay(frame,prediction,cost_multiplier=1):
    """$100 taker quote replay; size checked upstream, fills/impact unverified."""
    # Decisions cannot use future spreads, labels, fills or selected costs.
    threshold=2*FEE_BP+frame.spread.to_numpy()
    action=np.where(np.isfinite(prediction)&(np.abs(prediction)>threshold),np.sign(prediction),0)
    entry=np.where(action>0,frame.entry_ask,frame.entry_bid)
    exit_=np.where(action>0,frame.exit_bid,frame.exit_ask)
    ratio=np.asarray(exit_/entry)
    executable=action*1e4*(ratio-1)
    gross=action*frame.mid_return.to_numpy()
    fees=FEE_BP*(1+ratio)
    costs=gross-executable+fees
    pnl=np.where(action!=0,(gross-cost_multiplier*costs)*NOTIONAL/1e4,0)
    pnl[(action!=0)&~frame.execution_valid.to_numpy(dtype=bool)]=np.nan
    return action,pnl


def ratio_interval(numerators,denominators,seed=SEED,replicas=BOOTSTRAPS):
    """Resample common hourly clusters, retaining unequal cluster sizes."""
    a,b=np.asarray(numerators,float),np.asarray(denominators,float)
    if len(a)<2 or np.sum(b)<=0: return dict(mean=None,lower=None,upper=None,blocks=len(a))
    rng=np.random.default_rng(seed);ix=rng.integers(0,len(a),size=(replicas,len(a)))
    den=b[ix].sum(axis=1)
    boot=a[ix].sum(axis=1)[den>0]/den[den>0]
    if not len(boot): return dict(mean=None,lower=None,upper=None,blocks=len(a))
    return dict(mean=float(a.sum()/b.sum()),lower=float(np.quantile(boot,.025)),
                upper=float(np.quantile(boot,.975)),blocks=len(a))


def evaluate(frame,artifact):
    baseline,selected,valid=predict(frame,artifact)
    blocks=np.sort(frame.block.unique());out={};paired={}
    for name,pred in (("baseline",baseline),("selected",selected)):
        costs={}
        for tier in (1,2,3):
            action,pnl=replay(frame,pred,tier)
            sums=np.array([np.nansum(pnl[frame.block.to_numpy()==h]) for h in blocks])
            unresolved=int(np.isnan(pnl).sum())
            observed=float(np.nansum(pnl))
            costs[str(tier)]=dict(trades=int(np.count_nonzero(action)),unresolved_trades=unresolved,
                                 observed_pnl_usd=observed,pnl_usd=None if unresolved else observed,
                                 return_bp=None if unresolved else observed/CAPITAL*1e4,
                                 hourly=(dict(mean=None,lower=None,upper=None,blocks=len(blocks)) if unresolved
                                         else ratio_interval(sums,np.ones(len(blocks)))))
            if tier==2: paired[name]=sums
        out[name]=costs
    # Undefined selected values mean abstention and a missing predictive score;
    # no zero imputation, and >1% undefined blocks a positive lane verdict.
    err=(frame.mid_return.to_numpy()-baseline)**2-(frame.mid_return.to_numpy()-selected)**2
    err[~valid|~np.isfinite(frame.mid_return.to_numpy())]=np.nan
    mse_sums=np.array([np.nansum(err[frame.block.to_numpy()==h]) for h in blocks])
    mse_counts=np.array([np.isfinite(err[frame.block.to_numpy()==h]).sum() for h in blocks])
    unresolved=max(out[n]["2"]["unresolved_trades"] for n in out)
    delta=(dict(mean=None,lower=None,upper=None,blocks=len(blocks)) if unresolved else
           ratio_interval(paired["selected"]-paired["baseline"],np.ones(len(blocks))))
    mse=ratio_interval(mse_sums,mse_counts,seed=SEED+1)
    gooddays=int(frame.day.nunique());nblocks=len(blocks)
    sufficient=(gooddays>=MIN_FORWARD_DAYS and nblocks>=MIN_FORWARD_BLOCKS
                and unresolved==0 and frame.label_valid.mean()>=.99)
    positive=(artifact["selected_index"] is not None and sufficient and valid.mean()>=.99
              and (delta["lower"] or 0)>0 and (mse["lower"] or 0)>0
              and (out["selected"]["2"]["hourly"]["lower"] or 0)>0)
    return dict(verdict="EXPLORATORY_SIGNAL" if positive else ("NULL" if sufficient else "INCONCLUSIVE"),
                portfolios=out,incremental_hourly_usd_2x=delta,incremental_mse=mse,
                days=gooddays,blocks=nblocks,observations=len(frame),
                selected_undefined=int((~valid).sum()),gate_eligible=False,
                execution="public BBO quote replay only; actual fills, impact, owner fees and UTC qualification unverified")
