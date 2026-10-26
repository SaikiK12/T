"""Causal close-level probabilities and common-capital research accounting.

Hourly traded closes are NOT executable quotes or intrabar barriers. Historical
funding uses the explicitly conditional trade-close notional. Nothing here
authorizes orders, certifies calibration or substitutes missing data with zero.
"""
from decimal import Decimal, localcontext
import math
import numpy as np

from lab.paper_account import PaperAccount, PaperEvent, _precision
from lab.stream_quotes import FrameClock

HOUR = 3_600_000
DAY = 24 * HOUR
CLASSES = ('break', 'rebound', 'timeout')
POLICIES = ('conditional', 'climatology', 'always_break', 'always_rebound', 'long_control', 'cash')


def market(prices, funding, start, end):
    """Same strict adjacent-cycle certificate as R311, without its other venue.

    start/end are close-time boundaries, inclusive. No row/volume imputation.
    A source price bar's timestamp denotes its START; close is available an hour
    later only under this historical-clock assumption, not a first-seen claim.
    """
    if type(start) is not int or type(end) is not int or start % HOUR or end % HOUR or end <= start:
        raise ValueError('ordered hourly boundaries required')
    t = np.arange(start, end + HOUR, HOUR, dtype=np.int64)
    for f in (prices, funding):
        ts = f.t.to_numpy(np.int64)
        if f.t.duplicated().any() or (ts % HOUR).any() or (np.diff(ts) <= 0).any():
            raise ValueError('unique ordered hourly source timestamps required')
    p = prices.assign(close_time=prices.t + HOUR).set_index('close_time').reindex(t)
    close, volume = p.close.to_numpy(float), p.vol.to_numpy(float)
    valid = np.isfinite(close) & (close > 0) & np.isfinite(volume) & (volume > 0)
    rates = np.zeros(len(t)); known = np.zeros(len(t), bool)
    ts = funding.t.to_numpy(np.int64); rr = funding.rate.to_numpy(float)
    cycles = funding.cycle_h.to_numpy(float)
    if not np.isfinite(rr).all():
        raise ValueError('nonfinite funding rate')
    for k, stamp in enumerate(ts):
        ix = int((stamp-start)//HOUR)
        if 0 <= ix < len(t):
            rates[ix] = rr[k]; known[ix] = True
        if k and all(np.isfinite(c) and c > 0 and abs((stamp-ts[k-1])/HOUR-c) < 1e-9
                     for c in (cycles[k-1], cycles[k])):
            a = max(0, int((ts[k-1]-start)//HOUR)+1)
            b = min(len(t), ix+1)
            if b > a: known[a:b] = True
    return dict(t=t, close=close, valid=valid, rate=rates, funding_known=known)


def signal(m, decision):
    """Prior72 close extrema; nearest level within .25 sigma12 at 00UTC.

    One event per asset/day. Both levels exclude the decision close. The sign
    +1 is resistance/upward breakout, -1 support/downward breakout. Ties choose
    support. Approach is sign of the past24h move toward the chosen level.
    """
    t = m['t']; i = int(np.searchsorted(t, decision))
    row = dict(decision=int(decision), state='ineligible', reason=None)
    if decision % DAY or i >= len(t) or t[i] != decision or i < 72:
        return {**row, 'reason':'clock_or_warmup'}
    if not m['valid'][i-72:i+1].all():
        return {**row, 'reason':'feature_price_or_volume_gap'}
    x = np.log(m['close'][i-72:i+1]); sigma = float(np.sqrt(12*np.mean(np.diff(x)**2)))
    if not math.isfinite(sigma) or sigma <= 0:
        return {**row, 'reason':'zero_or_invalid_volatility'}
    low, high = float(x[:-1].min()), float(x[:-1].max())
    side, level = (-1, low) if abs(x[-1]-low) <= abs(x[-1]-high) else (1, high)
    if abs(x[-1]-level) > .25*sigma:
        return {**row, 'reason':'not_near_prior_close_level'}
    return {**row, 'state':'event', 'reason':None, 'index':i, 'side':side,
            'level':float(np.exp(level)), 'sigma':sigma,
            'cell':'approach' if side*(x[-1]-x[-25]) >= 0 else 'recede'}


def outcome(m, s):
    """Entry one hour after signal; first +/-sigma12 HOURLY CLOSE, else12h.

    Entry is never at the touched level. Overshoots use the observed close,
    not the ideal barrier. A gap before resolution leaves the exit unknown.
    Funding at entry is excluded, at exit included, matching (entry, exit].
    """
    if s['state'] != 'event': return None
    en = s['index']+1; last = en+12
    out = dict(label=None, financial_known=False, reason=None, failure_time=None, entry_index=en,
               entry_time=int(m['t'][en]) if en<len(m['t']) else None, exit_time=None,
               exit_index=None, entry=None, exit=None, price_outside=None,
               funding_outside=None, funding_events=[], normalized_total=None)
    if en >= len(m['t']) or not m['valid'][en]:
        return {**out, 'reason':'entry_price_or_volume_gap'}
    entry = float(m['close'][en]); out['entry'] = entry
    for j in range(en+1, last+1):
        if j >= len(m['t']) or not m['valid'][j]:
            return {**out, 'reason':'path_price_or_volume_gap', 'failure_time':s['decision']+(j-s['index'])*HOUR}
        z = s['side']*math.log(m['close'][j]/entry)
        label = 'break' if z >= s['sigma'] else 'rebound' if z <= -s['sigma'] else None
        if label is not None or j == last:
            exit_price = float(m['close'][j]); out.update(label=label or 'timeout', exit_time=int(m['t'][j]),
                exit_index=j, exit=exit_price, price_outside=s['side']*(exit_price/entry-1))
            if not m['funding_known'][en+1:j+1].all():
                return {**out, 'reason':'funding_interval_unknown'}
            events = [(int(m['t'][k]), float(m['close'][k]), float(m['rate'][k]))
                      for k in range(en+1,j+1) if m['rate'][k] != 0]
            f = -s['side']*sum(price*rate for _,price,rate in events)/entry
            return {**out, 'funding_outside':f, 'funding_events':events,
                    'normalized_total':(out['price_outside']+f)/s['sigma'],
                    'financial_known':True}
    raise AssertionError('finite horizon must resolve or preserve a gap')


def fit(rows):
    """ONE fixed global climatology and two shrunken approach/recede cells.

    No asset, side, feature, threshold, temperature or hyperparameter selection.
    Label frequencies are distinct from conditional realized payoff magnitudes.
    """
    clean = [r for r in rows if (r.get('outcome') or {}).get('financial_known')]
    counts = np.array([sum(r['outcome']['label']==c for r in clean) for c in CLASSES])
    base = (counts+1)/(len(clean)+3)
    means = [float(np.mean([r['outcome']['normalized_total'] for r in clean if r['outcome']['label']==c]))
             if counts[k] >= 5 else None for k,c in enumerate(CLASSES)]
    cells = {}
    for cell in ('approach','recede'):
        sub = [r for r in clean if r['signal']['cell']==cell]
        n = np.array([sum(r['outcome']['label']==c for r in sub) for c in CLASSES])
        cells[cell] = dict(n=len(sub), counts=n.tolist(),
                           probability=((n+20*base)/(len(sub)+20)).tolist() if len(clean)>=50 and len(sub)>=20 else None)
    return dict(classes=list(CLASSES), n=len(clean), counts=counts.tolist(),
                probability=base.tolist() if len(clean)>=50 else None,
                class_payoff_means=means, cells=cells, calibrated=False,
                actual_order_allowed=False)


def prediction(model, s, policy):
    if policy not in POLICIES: raise ValueError('registered finite policy required')
    p = model['probability'] if policy=='climatology' else model['cells'][s['cell']]['probability']
    expected = None
    if p is not None and all(x is not None for x in model['class_payoff_means']):
        expected = s['sigma']*sum(a*b for a,b in zip(p,model['class_payoff_means']))
    if policy=='cash': direction=0
    elif policy=='always_break': direction=s['side']
    elif policy=='always_rebound': direction=-s['side']
    elif policy=='long_control': direction=1
    else:
        # FIXED decision at2x: round-trip16bp *2 plus .25sigma reserve.
        # This is a registered research policy, NOT a calibrated lower bound.
        direction = (s['side']*(1 if expected>0 else -1)
                     if expected is not None and abs(expected) > .0032+.25*s['sigma'] else 0)
    return dict(direction=direction, probability=p, expected_outside=expected,
                calibrated=False, actual_order_allowed=False)


def score(rows, model):
    out = {}
    for policy in ('conditional','climatology'):
        observations=[]
        for r in rows:
            y=(r.get('outcome') or {}).get('label')
            if y is None:continue
            p=prediction(model,r['signal'],policy)['probability']
            if p is None:continue
            truth=[int(y==c) for c in CLASSES]
            observations.append(dict(day=r['signal']['decision']//DAY, symbol=r['symbol'],
                probability=p, truth=truth, brier=sum((a-b)**2 for a,b in zip(p,truth)),
                log_loss=-math.log(p[CLASSES.index(y)])))
        bins=[]
        for k,c in enumerate(CLASSES):
            for b in range(5):
                sub=[x for x in observations if min(4,int(x['probability'][k]*5))==b]
                bins.append(dict(label=c, bin=b, n=len(sub),
                    days=len({x['day'] for x in sub}), blocks14=len({x['day']//14 for x in sub}),
                    predicted=float(np.mean([x['probability'][k] for x in sub])) if sub else None,
                    observed=float(np.mean([x['truth'][k] for x in sub])) if sub else None,
                    calibrated_interval=None))
        out[policy]=dict(n=len(observations),
            brier=float(np.mean([x['brier'] for x in observations])) if observations else None,
            log_loss=float(np.mean([x['log_loss'] for x in observations])) if observations else None,
            reliability=bins, observations=observations, calibrated=False)
    # Dependence diagnostic: same calendar shift for ALL coins, multiples14days.
    # Not an exchangeable null, significance p-value or repaired R321 interval.
    a={(x['day'],x['symbol']):x for x in out['conditional']['observations']}
    b={(x['day'],x['symbol']):x for x in out['climatology']['observations']}
    paired=sorted(set(a)&set(b));shifts=[]
    if rows:
        lo=min(r['signal']['decision']//DAY for r in rows);hi=max(r['signal']['decision']//DAY for r in rows);n=hi-lo+1
        for shift in range(14,n,14):
            dif=[]
            for key in paired:
                target=(lo+(key[0]-lo+shift)%n,key[1])
                if target not in a:continue
                y=a[target]['truth']
                dif.append(sum((p-z)**2 for p,z in zip(a[key]['probability'],y))-
                           sum((p-z)**2 for p,z in zip(b[key]['probability'],y)))
            shifts.append(dict(shift_days=shift,n=len(dif),difference=float(np.mean(dif)) if dif else None))
    out['paired_brier_difference']=float(np.mean([a[k]['brier']-b[k]['brier'] for k in paired])) if paired else None
    out['paired_n']=len(paired);out['joint_14day_shifts']=shifts
    out['calibrated_uncertainty']=None;out['significance_or_activation_allowed']=False
    return out


@_precision
def replay(rows, model, start, end):
    """Single10000USDT MEXC account per policy/cost,500 notional per coin.

    Decisions are identical at1x/2x/3x. Costs are an8bp-per-side LUMPED fill
    proxy on actual entry/exit notional, not another spread on top of fills.
    Cash is initial capital, not proceeds from short notional. Inactive days
    remain zero. Missing exit stops that symbol; unknown funding stops NEW risk
    account-wide while existing positions still close when known.
    """
    keys=[(r['signal']['decision'],r['symbol']) for r in rows]
    if len(keys)!=len(set(keys)) or any(not start<=d<end or d%DAY for d,_ in keys):
        raise ValueError('unique within-window daily opportunities required')
    if len({s for _,s in keys})>4:raise ValueError('maximum four fixed500-notional sleeves')
    output=[]
    for policy in POLICIES:
        # Causal3x cash shadow admits the SAME entries at every cost tier.
        # Lower-cost accounts cannot continue after the conservative shadow
        # stops. Never consult a future exit before its chronological event.
        capital_rejected=set()
        for tier in (3,1,2):
            anchor=FrameClock(start*1_000_000,0)
            account=PaperAccount({('mexc','USDT'):'10000'},anchor)
            timeline=[];tickets=[];unknown_after=None;unknown_markers=[]
            for r in sorted(rows,key=lambda r:(r['signal']['decision'],r['symbol'])):
                s=r['signal']
                if s['state']!='event':continue
                pred=prediction(model,s,policy);o=r['outcome'];d=pred['direction']
                ticket=dict(symbol=r['symbol'],decision=s['decision'],direction=d,
                            state='inactive' if not d else 'candidate',price=None,funding=None,cost=None,net=None)
                tickets.append(ticket)
                if not d:ticket.update(price='0',funding='0',cost='0',net='0');continue
                entry_time=s['decision']+HOUR
                if o['entry'] is None:
                    ticket.update(state='entry_unavailable',price='0',funding='0',cost='0',net='0');continue
                with localcontext() as ctx:
                    ctx.prec=80
                    entry=Decimal(str(o['entry']));q=Decimal(d)*Decimal(500)/entry
                    fee_rate=Decimal('.0008')*tier
                    entry_cost=abs(q)*entry*fee_rate
                    ticket.update(quantity=str(q),entry_time=entry_time,entry=str(entry),entry_cost=str(entry_cost))
                    timeline.append((entry_time,1,r['symbol'],ticket,'fill',q,entry,entry_cost))
                    if o['exit'] is None:
                        ticket['state']='exit_unknown'
                        timeline.append((o['failure_time'],0,r['symbol'],ticket,'missing_exit',None,None,None))
                        continue
                    exit_time=o['exit_time'];exit_price=Decimal(str(o['exit']))
                    cost=entry_cost+abs(q)*exit_price*fee_rate
                    price=q*(exit_price-entry)
                    fund=(-q*sum((Decimal(str(p))*Decimal(str(rate)) for _,p,rate in o['funding_events']),Decimal(0))) if o['financial_known'] else None
                    ticket.update(state='closed' if fund is not None else 'funding_unknown',exit_time=exit_time,
                        exit=str(exit_price),price=str(price),funding=str(fund) if fund is not None else None,
                        cost=str(cost),net=str(price+fund-cost) if fund is not None else None)
                    # Historical aggregate conditional funding, one credit only.
                    timeline.append((exit_time,0,r['symbol'],ticket,'funding',None,None,fund))
                    timeline.append((exit_time,1,r['symbol'],ticket,'fill',-q,exit_price,abs(q)*exit_price*fee_rate))
            records=[];capital_stopped=False
            for k,(stamp,_,symbol,ticket,kind,q,p,amount) in enumerate(sorted(timeline,key=lambda x:(x[0],x[1],x[2]))):
                if ticket['state'] in ('blocked_capital','blocked_after_unknown'):continue
                if kind=='missing_exit':
                    unknown_after=stamp if unknown_after is None else min(unknown_after,stamp)
                    unknown_markers.append(dict(time=stamp,symbol=symbol,reason='admitted_position_path_unknown'))
                    continue
                opening=kind=='fill' and stamp==ticket['entry_time']
                if opening:
                    if unknown_after is not None or account.pending:
                        ticket.update(state='blocked_after_unknown',price='0',funding='0',cost='0',net='0')
                        continue
                    # Explicit100%-entry-notional model collateral, not venue
                    # maintenance/liquidation rules. Stop new risk permanently
                    # if the known shared cash cannot reserve it plus cost.
                    reserved=sum((abs(v[0])*v[1] for v in account.positions.values()),Decimal(0))
                    identity=(ticket['decision'],symbol)
                    insufficient=capital_stopped or account.cash[('mexc','USDT')]-reserved < abs(q)*p+amount
                    if tier==3 and insufficient:capital_rejected.add(identity)
                    if identity in capital_rejected:
                        capital_stopped=True
                        ticket.update(state='blocked_capital',price='0',funding='0',cost='0',net='0')
                        continue
                    if insufficient:raise AssertionError('lower-cost account cannot fail an admitted3x cash reserve')
                clock=FrameClock(stamp*1_000_000,(stamp-start)*1_000_000)
                event=PaperEvent(f'{policy}:{tier}:{k}',kind,'mexc','USDT',symbol,stamp*1_000_000,clock,
                    'R330:historical_trade_close_proxy:NOT_first_seen',quantity=q,price=p,
                    fee=amount if kind=='fill' else None,amount=amount if kind=='funding' else None)
                status=account.post(event,clock.mono_ns)
                if status['status']!='applied':raise ValueError(f'account rejected research proxy: {status}')
                records.append(event.mapping())
                if kind=='funding' and amount is None:
                    unknown_after=stamp if unknown_after is None else min(unknown_after,stamp)
            days=[]
            for day in range(start,end,DAY):
                sub=[x for x in tickets if x['decision']==day]
                unknown=any(x['net'] is None and x['state'] not in ('entry_unavailable',) for x in sub)
                # Earlier unresolved account cash/exposure stays unknown on idle days too.
                if unknown_after is not None and day+DAY>unknown_after:unknown=True
                known=sum((Decimal(x['net']) for x in sub if x['net'] is not None),Decimal(0))
                days.append(dict(day=day,known_net=str(known),net=None if unknown else str(known)))
            key=('mexc','USDT');open_positions={k[-1]:str(v[0]) for k,v in account.positions.items() if v[0]}
            complete=not open_positions and not account.pending and all(x['net'] is not None for x in days)
            output.append(dict(policy=policy,cost_multiple=tier,initial_capital='10000',
                per_symbol_notional='500',maximum_entry_gross_fraction='.2',
                capital_admission='causal3x shadow shared across alltiers;100percent entry-notional reserve',
                marked_gross_limit_verified=False,margin_and_liquidation_verified=False,capital_stopped=capital_stopped,
                shared_cash=str(account.cash[key]),price=str(account.price[key]),funding=str(account.funding[key]),
                cost=str(account.fees[key]),conditional_net=str(account.cash[key]-Decimal(10000)) if complete else None,
                known_cash_component=str(account.cash[key]-Decimal(10000)),complete=complete,
                pending=len(account.pending),open_positions=open_positions,tickets=tickets,days=days,unknown_markers=unknown_markers,
                events=records,actual_executable_net=None,actual_order_allowed=False))
    return sorted(output,key=lambda x:(POLICIES.index(x['policy']),x['cost_multiple']))
