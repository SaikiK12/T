"""Conditional paired-book size, delay and adverse-exit arithmetic, never fills.

All books, fee assumptions and clocks are caller supplied. The decision fixes q;
later books cannot create or resize it. USDT/USD-quote parity is an explicit model
assumption. Session, effective funding value, margin tiers, matching and actual
account fees remain external requirements. No network, orders or ledger writes.
"""
from decimal import Decimal
from fractions import Fraction
from math import isfinite,lcm

from lab.executable_quotes import common_quantity,pair_costs,positive,walk
from lab.stream_quotes import FrameClock,StreamBook,NS,freshness,integer


def _number(value,*,zero=False):
    if isinstance(value,bool):raise ValueError('boolean is not a quantity/rate')
    try:x=Decimal(str(value))
    except (ValueError,ArithmeticError) as exc:raise ValueError('explicit finite decimal required') from exc
    if not x.is_finite() or x<0 or (not zero and x==0):raise ValueError('finite nonnegative value required')
    return x


def _books(books,target,anchor):
    if len(books)!=2:raise ValueError('exactly two ordered books required')
    flags=[]
    for venue,b in zip(('mexc','lighter'),books):
        if not isinstance(b,StreamBook) or b.venue!=venue:
            flags.append(venue+':source_book_unavailable');continue
        flags.extend(venue+':'+f for f in freshness(b,target,anchor))
    if all(isinstance(b,StreamBook) for b in books):
        if books[0].symbol!=books[1].symbol:flags.append('paired_instrument_mismatch')
        if abs(books[0].clock.mono_ns-books[1].clock.mono_ns)>NS:flags.append('paired_receive_skew')
        if abs(books[0].source_time_ns-books[1].source_time_ns)>NS:flags.append('paired_source_skew')
    return flags


def _step(mexc,lighter):
    decimals=lighter['supported_size_decimals']
    if type(decimals) is not int or not 0<=decimals<=12:raise ValueError('invalid base precision')
    a=Fraction(positive(mexc['contractSize'])*positive(mexc['volUnit']))
    b=Fraction(1,10**decimals);d=lcm(a.denominator,b.denominator)
    return Decimal(lcm(a.numerator*(d//a.denominator),b.numerator*(d//b.denominator)))/Decimal(d)


def quantity_check(books,mexc_meta,lighter_meta,quantity,capital=10000):
    """Math/identity constraints only; callers separately validate source clocks.

    Per-venue minimum quote uses that venue's actual buy AND sell quote cash,
    never the larger midpoint from the other venue. No delayed resizing.
    """
    if len(books)!=2:raise ValueError('exactly two ordered books required')
    out={'state':'blocked','reasons':[],'quantity_base':None,'common_step_base':None,
         'venue_notionals_quote':None,'displayed_fillable':False,'execution_ready':False}
    try:
        q,cap=positive(quantity),positive(capital);out['quantity_base']=str(q)
        if not isinstance(mexc_meta,dict) or not isinstance(lighter_meta,dict):raise ValueError('explicit venue metadata required')
        mx,lt=books
        if not isinstance(mx,StreamBook) or not isinstance(lt,StreamBook) or (mx.venue,lt.venue)!=('mexc','lighter'):
            raise ValueError('ordered source books unavailable')
        if (mx.symbol!=lt.symbol or mexc_meta.get('symbol')!=mx.symbol+'_USDT'
                or lighter_meta.get('symbol')!=lt.symbol):raise ValueError('instrument metadata mismatch')
        if type(mexc_meta.get('type')) is not int or mexc_meta['type']!=1 or mexc_meta.get('settleCoin')!='USDT':
            raise ValueError('unsupported linear/quote units')
        step=_step(mexc_meta,lighter_meta);out['common_step_base']=str(step)
        if q%step:out['reasons'].append('quantity_off_common_lattice')
        if q<positive(mexc_meta['contractSize'])*positive(mexc_meta['minVol']):out['reasons'].append('mexc_minimum_contracts')
        if q<positive(lighter_meta['min_base_amount']):out['reasons'].append('lighter_minimum_base')
        if 'maxVol' in mexc_meta and q>positive(mexc_meta['maxVol'])*positive(mexc_meta['contractSize']):
            out['reasons'].append('mexc_maximum_contracts')
        fills=[walk(side,q) for b in books for side in (b.asks,b.bids)]
        out['displayed_fillable']=all(x is not None for x in fills)
        out['shown_two_way_capacity_base']=min(sum(positive(x.size) for x in side) for b in books for side in (b.asks,b.bids))
        out['shown_two_way_capacity_base']=str(out['shown_two_way_capacity_base'])
        out['venue_notionals_quote']=[str(q*positive(b.mid)) for b in books]
        out['current_buy_sell_quote']=fills
        if not out['displayed_fillable']:out['reasons'].append('insufficient_displayed_depth')
        for i,venue in enumerate(('mexc','lighter')):
            if q*positive(books[i].mid)>cap/2 or any(v is not None and positive(v)>cap/2 for v in fills[2*i:2*i+2]):
                out['reasons'].append(venue+':segregated_capital_exceeded')
        minimum=positive(lighter_meta['min_quote_amount'])
        if any(v is not None and positive(v)<minimum for v in fills[2:]):out['reasons'].append('lighter_actual_quote_minimum')
        out['state']='conditional' if not out['reasons'] else 'blocked'
    except (KeyError,ValueError,TypeError,ArithmeticError) as exc:
        out['reasons'].append('metadata_or_quantity:'+str(exc))
    return out


def liquidation_quote(book,signed_quantity,fee_bp,asof,anchor,adverse_bp=0):
    """Close-order notional flow, NOT linear-futures collateral/PnL change.

    The account must subtract its signed entry basis before deriving futures
    liquidation PnL, and count entry/exit fees once. Shock is hypothetical only.
    """
    integer(asof)
    if not isinstance(anchor,FrameClock) or isinstance(signed_quantity,bool):raise ValueError('explicit anchor/signed quantity required')
    try:q=Decimal(str(signed_quantity))
    except (ValueError,ArithmeticError) as exc:raise ValueError('explicit signed decimal quantity required') from exc
    fee=_number(fee_bp,zero=True);shock=_number(adverse_bp,zero=True)
    if not q.is_finite() or q==0 or shock>=10000 or fee>10000:raise ValueError('finite nonzero q,fee<=10000bp,adverse<10000bp required')
    out={'state':'unknown','reasons':[],'close_order_quote_flow':None,'gross_close_quote':None,
         'fee_quote':None,'adverse_exit_bp':str(shock),'hypothetical_adverse_exit':shock!=0,
         'cash_is_not_futures_pnl':True,'actual_fill_verified':False,'execution_ready':False}
    if not isinstance(book,StreamBook):out['reasons']=['source_book_unavailable'];return out
    out.update(venue=book.venue,symbol=book.symbol,quantity_base=str(q))
    out['reasons']=freshness(book,asof,anchor)
    if out['reasons']:return out
    cash=walk(book.bids if q>0 else book.asks,abs(q))
    if cash is None:out['reasons']=['insufficient_displayed_depth'];return out
    gross=positive(cash)*(1-shock/10000 if q>0 else 1+shock/10000)
    charge=gross*fee/10000
    out.update(state='conditional',gross_close_quote=str(gross),fee_quote=str(charge),
               close_order_quote_flow=str(gross-charge if q>0 else -gross-charge))
    return out


def execution_envelope(decision_books,observed_books,mexc_meta,lighter_meta,decision_ns,observed_ns,anchor,
                       quantity=None,leg_budget=250,fees_bp=(10,4),venue_delay_ms=(0,0),fee_source=None,
                       adverse_exit_bp=(0,20,50),capital=10000,exit_fees_bp=None,extra_exit_delay_ms=0):
    """Fix q at decision, then assess later observed liquidity and declared exits."""
    integer(decision_ns);integer(observed_ns)
    if not isinstance(anchor,FrameClock) or observed_ns<decision_ns:raise ValueError('causal decision/observation clocks required')
    if len(fees_bp)!=2:raise ValueError('two explicit fee assumptions required')
    fees=tuple(_number(f,zero=True) for f in fees_bp)
    if any(f>10000 for f in fees):raise ValueError('fee assumption exceeds100percent')
    exit_fees=fees if exit_fees_bp is None else tuple(_number(f,zero=True) for f in exit_fees_bp)
    if len(exit_fees)!=2 or any(f>10000 for f in exit_fees):raise ValueError('two explicit exit fees<=10000bp required')
    if type(extra_exit_delay_ms) is not int or extra_exit_delay_ms<0:raise ValueError('nonnegative declared additional exit delay required')
    if len(venue_delay_ms)!=2 or any(type(t) is not int or t<0 for t in venue_delay_ms):raise ValueError('two nonnegative integer venue delays required')
    if fee_source is not None and (not isinstance(fee_source,str) or not fee_source):raise ValueError('fee evidence pointer must be nonempty text')
    shocks=tuple(_number(s,zero=True) for s in adverse_exit_bp)
    if not shocks or len(shocks)>16 or any(s>=10000 for s in shocks):raise ValueError('finite declared adverse scenarios required')
    cap=positive(capital)
    if not isfinite(float(cap)):raise ValueError('capital outside supported numeric range')
    decision_flags=_books(decision_books,decision_ns,anchor)
    out={'state':'blocked','decision_reasons':decision_flags,'observed_reasons':[],'quantity_base':None,
         'decision_quantity':None,'observed_quantity':None,'cost':None,'liquidation_quotes':[],
         'decision_to_evaluation_ms':(observed_ns-decision_ns)/1000000,
         'observed_quote_receipt_offset_ms':[None,None],
         'minimum_additional_venue_delay_ms':list(venue_delay_ms),
         'minimum_venue_delay_satisfied':observed_ns-decision_ns>=max(venue_delay_ms)*1000000,
         'total_order_latency_verified':False,'actual_fills_verified':False,'actual_fees_verified':False,
         'fee_evidence_pointer':fee_source,'capital_total_quote_equivalent':str(cap),
         'capital_per_venue_quote_equivalent':str(cap/2),'execution_ready':False,
         'entry_fee_assumptions_bp':[str(f) for f in fees],'exit_fee_assumptions_bp':[str(f) for f in exit_fees],
         'declared_additional_exit_delay_ms':extra_exit_delay_ms,'additional_exit_delay_price_effect_verified':False,
         'unresolved':['sessions_and_permissions','actual_matching_fills_and_latency','funding_event_value',
                       'margin_tiers_and_liquidation','fee_debit_assets_and_USDT_USD_quote_parity','own_impact',
                       'source_sequence_and_connection_readiness','future_exit_fee_and_latency_price_effect'],
         'scope':'conditional displayed sweeps and DECLARED hypothetical exits; no maker/fill/cash/return evidence'}
    if decision_flags:return out
    try:
        if quantity is None:
            quantity,_=common_quantity(mexc_meta,lighter_meta,max(b.mid for b in decision_books),leg_budget)
        quantity=positive(quantity)
    except (ValueError,TypeError,KeyError,ArithmeticError) as exc:
        out['decision_reasons'].append('decision_quantity:'+str(exc));return out
    decision=quantity_check(decision_books,mexc_meta,lighter_meta,quantity,cap);out['decision_quantity']=decision
    if any(r!='insufficient_displayed_depth' for r in decision['reasons']):
        out['decision_reasons'].extend(decision['reasons']);return out
    # Thin decision depth can define q, but cannot justify a displayed fill.
    out['quantity_base']=str(quantity)
    out['observed_reasons']=_books(observed_books,observed_ns,anchor)
    out['observed_quote_receipt_offset_ms']=[(b.clock.mono_ns-decision_ns)/1000000 if isinstance(b,StreamBook) else None for b in observed_books]
    if out['observed_reasons']:return out
    observed=quantity_check(observed_books,mexc_meta,lighter_meta,quantity,cap);out['observed_quantity']=observed
    out['observed_reasons'].extend(observed['reasons'])
    if any(r!='insufficient_displayed_depth' for r in observed['reasons']):return out
    out['cost']=pair_costs(*observed_books,quantity,tuple(float(f) for f in fees),float(cap))
    if not out['cost']['displayed_fillable']:return out
    out['state']='conditional'
    for shock in shocks:
        for b,f in zip(observed_books,exit_fees):
            for side in (1,-1):
                quote=liquidation_quote(b,quantity*side,f,observed_ns,anchor,shock)
                quote.update(exit_fee_assumption_bp=str(f),declared_additional_exit_delay_ms=extra_exit_delay_ms,
                             hypothetical_fee_or_delay_change=exit_fees!=fees or extra_exit_delay_ms>0,
                             actual_future_exit_observed=False)
                out['liquidation_quotes'].append(quote)
    return out


def size_envelope(decision_books,observed_books,mexc_meta,lighter_meta,decision_ns,observed_ns,anchor,
                  leg_budgets=(25,50,100,250,500,1000),**kwargs):
    """Finite size sensitivity, each size fixed at its own common decision time."""
    if not leg_budgets or len(leg_budgets)>32:raise ValueError('one to32 finite size cases required')
    if 'quantity' in kwargs or 'leg_budget' in kwargs:raise ValueError('size cases define decision budget, not later q')
    return [{'leg_budget_quote':str(positive(b)),**execution_envelope(decision_books,observed_books,mexc_meta,lighter_meta,
            decision_ns,observed_ns,anchor,leg_budget=b,**kwargs)} for b in leg_budgets]
