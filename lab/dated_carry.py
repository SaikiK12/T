"""Source-bound inverse dated-future entry and conditional terminal conversion.

No funding-rate prediction or perpetual convergence assumption. The final
delivery TWAP is not a subsequent executable spot exit or a USD/USDT parity.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from fractions import Fraction as F

from lab.inverse_cash import InverseContract, rational, walk, terminal_conversion
from lab.executable_quotes import Receipt
from lab.spot_input_bridge import spot_rules


@dataclass(frozen=True)
class DatedRules:
    contract: InverseContract
    contract_size_usd: F
    tick_usd_per_coin: F
    active: bool
    public_taker_rate: F | None


def response(payload):
    if type(payload) is not dict or 'error' in payload or type(payload.get('result')) is not dict:
        raise ValueError('successful public Deribit JSON-RPC result required')
    return payload['result']


def rules(payload,instrument,coin,expiry_ns,source_identity):
    d=response(payload)
    if (d.get('instrument_name')!=instrument or d.get('kind')!='future'
            or d.get('instrument_type')!='reversed' or d.get('base_currency')!=coin
            or d.get('settlement_currency')!=coin or d.get('quote_currency')!='USD'
            or d.get('counter_currency')!='USD' or d.get('settlement_period')!='month'
            or type(d.get('expiration_timestamp')) is not int
            or d['expiration_timestamp']*1_000_000!=expiry_ns or 'PERPETUAL' in instrument):
        raise ValueError('fixed dated inverse coin/USD identity or expiry mismatch')
    if type(d.get('is_active')) is not bool:raise ValueError('explicit public visibility flag required')
    minimum=rational(d['min_trade_amount'],positive=True)
    size=rational(d['contract_size'],positive=True)
    tick=rational(d['tick_size'],positive=True)
    rate=None if d.get('taker_commission') is None else rational(d['taker_commission'],nonnegative=True)
    if rate is not None and rate>=1:raise ValueError('invalid public commission')
    c=InverseContract(instrument,coin,minimum,minimum,expiry_ns,source_identity)
    return DatedRules(c,size,tick,d['is_active'],rate)


def book(payload,d,receipt):
    b=response(payload)
    if b.get('instrument_name')!=d.contract.instrument or type(b.get('timestamp')) is not int:
        raise ValueError('dated book instrument/publication clock required')
    if not isinstance(receipt,Receipt):raise ValueError('first-seen full body receipt required')
    timestamp=b['timestamp']*1_000_000
    # Publication timestamp is not a matching-engine/effective-value attestation.
    if not 946684800_000_000_000 <= timestamp <= receipt.received_utc_ns:
        raise ValueError('invalid/future dated publication time')
    sides=[]
    for name,side in (('bids','sell'),('asks','buy')):
        levels=b.get(name)
        if type(levels) is not list or not 1<=len(levels)<=5:
            raise ValueError('nonempty finite five-level dated book required')
        parsed=[(rational(row[0],positive=True),rational(row[1],positive=True))
                for row in levels if type(row) is list and len(row)==2]
        if len(parsed)!=len(levels):raise ValueError('exact dated price/amount rows required')
        if any(q%d.contract.face_step_usd for _,q in parsed):
            raise ValueError('shown_USD_face_outside_quantity_increment')
        # Validate all displayed levels; do not silently sort or deduplicate.
        walk(parsed,min(q for _,q in parsed),side=side,unit='USD_face')
        sides.append(parsed)
    if sides[0][0][0]>=sides[1][0][0]:raise ValueError('crossed dated book')
    return {'bids':sides[0],'asks':sides[1],'publication_ns':timestamp,
            'state':b.get('state'),'settlement_price_untrusted':b.get('settlement_price'),
            'tick_size_steps_verified':False,
            'source_effective_age_verified':False}


def local_pair_flags(spot_receipt,dated_receipt,publication_ns):
    flags=[]
    if not isinstance(spot_receipt,Receipt) or not isinstance(dated_receipt,Receipt):
        raise ValueError('separate receipt clocks required')
    decision=max(spot_receipt.received_mono_ns,dated_receipt.received_mono_ns)
    for name,r in (('spot',spot_receipt),('dated',dated_receipt)):
        if not isinstance(r,Receipt):raise ValueError('separate receipt clocks required')
        elapsed=r.received_mono_ns-r.started_mono_ns
        if elapsed<0 or elapsed>2_000_000_000:flags.append(name+':body_latency_over_2s_or_negative')
        if decision-r.started_mono_ns>2_000_000_000:flags.append(name+':decision_request_age_over_2s')
        if abs((r.received_utc_ns-r.started_utc_ns)-elapsed)>50_000_000:
            flags.append(name+':clock_step_over_50ms')
    if abs(spot_receipt.received_mono_ns-dated_receipt.received_mono_ns)>1_000_000_000:
        flags.append('body_receipt_skew_over_1s')
    if abs((spot_receipt.received_utc_ns-dated_receipt.received_utc_ns)-
           (spot_receipt.received_mono_ns-dated_receipt.received_mono_ns))>50_000_000:
        flags.append('cross_receipt_clock_step_over_50ms')
    target_utc=dated_receipt.received_utc_ns+decision-dated_receipt.received_mono_ns
    if target_utc-publication_ns>2_000_000_000:
        flags.append('dated_publication_age_over_2s')
    return flags


def entry_plan(spot_payload,spot_metadata,spot_receipt,dated_payload,dated_rules,dated_receipt,
               *,face_target='250',profile='full',future_entry_rate='0.00035'):
    """Fixed USD-face short, fixed base purchase including 3x coin-fee reserve.

    Fractional ideal spot quantities are explicit model inputs. The actual spot
    lot/fee debit permission and cross-venue collateral route remain unknown.
    """
    if profile not in ('full','top_only'):raise ValueError('registered depth profile required')
    c=dated_rules.contract;s=spot_rules(c.coin+'USDT',spot_metadata)
    b=book(dated_payload,dated_rules,dated_receipt)
    flags=local_pair_flags(spot_receipt,dated_receipt,b['publication_ns'])
    if max(spot_receipt.received_utc_ns,dated_receipt.received_utc_ns)>=c.expiry_ns:
        flags.append('opening_at_or_after_expiry')
    if not dated_rules.active or b['state']!='open':flags.append('dated_not_open')
    if (s.public_status!='1' or s.api_spot_allowed is not True or s.trade_side_type!=1
            or not s.market_order_advertised):
        flags.append('spot_public_market_state_not_two_sided')
    if (type(spot_payload) is not dict or type(spot_payload.get('lastUpdateId')) is not int
            or spot_payload['lastUpdateId']<0
            or any(type(spot_payload.get(k)) is not list or not 1<=len(spot_payload[k])<=5 for k in ('bids','asks'))):
        raise ValueError('finite spot REST snapshot required')
    bids=spot_payload['bids'];asks=spot_payload['asks']
    # Exact whole-book validation includes positivity, ordering and spread.
    walk(bids,min(rational(r[1],positive=True) for r in bids),side='sell',unit='base')
    walk(asks,min(rational(r[1],positive=True) for r in asks),side='buy',unit='base')
    if rational(bids[0][0])>=rational(asks[0][0]):raise ValueError('crossed spot book')
    if flags:raise ValueError(';'.join(flags))
    target=rational(face_target,positive=True)
    face=(target//c.face_step_usd)*c.face_step_usd
    if face<c.minimum_face_usd:raise ValueError('target_below_dated_minimum')
    f=rational(future_entry_rate,nonnegative=True)
    if f>=F(1,3):raise ValueError('invalid 3x commission reserve')
    count=None if profile=='full' else 1
    full_fills,_=walk(b['bids'],face,side='sell',unit='USD_face')
    future_mid=(b['bids'][0][0]+b['asks'][0][0])/2
    worst_prices=[(future_mid-3*(future_mid-p),n) for p,n in full_fills]
    if any(p<=0 for p,_ in worst_prices):raise ValueError('3x_price_crossing_nonpositive')
    worst_hedge=sum((n/p for p,n in worst_prices),F(0))
    if s.base_asset_precision is None:raise ValueError('spot_declared_decimal_grid_unknown')
    # Declared decimal-only convention, NOT proof of actual spot increment.
    step=F(1,10**s.base_asset_precision)
    q=-((-worst_hedge*(1+3*f))//step)*step
    # Identical full/top, fee paths, cost tiers and terminal worlds.
    inverse_fills,hedge=walk(b['bids'][:count],face,side='sell',unit='USD_face')
    spot_fills,spot_principal=walk(asks[:count],q,side='buy',unit='base')
    # Need observed current exit capacity as a diagnostic only, not a future fill.
    _,current_exit=walk(bids[:count],q,side='sell',unit='base')
    if s.minimum_base is None or q<F(s.minimum_base):raise ValueError('spot_base_minimum_unknown_or_failed')
    if s.minimum_quote_market is None or spot_principal<F(s.minimum_quote_market):
        raise ValueError('spot_quote_minimum_unknown_or_failed')
    if s.maximum_quote_market is None or spot_principal>F(s.maximum_quote_market):
        raise ValueError('spot_quote_maximum_unknown_or_failed')
    if not F(s.minimum_quote_market)<=current_exit<=F(s.maximum_quote_market):
        raise ValueError('spot_current_exit_amount_outside_public_range')
    if s.advertised_taker_rate is None:raise ValueError('public_spot_rate_unknown')
    if 3*F(s.advertised_taker_rate)>=1:raise ValueError('invalid_stressed_spot_rate')
    if spot_principal*(1+3*F(s.advertised_taker_rate))>5000:
        raise ValueError('fixed_spot_cash_allocation_exceeded')
    mid=(rational(bids[0][0])+rational(asks[0][0]))/2
    # This arithmetic assumes base quantity from public spot book; not certified.
    return {'instrument':c.instrument,'coin':c.coin,'face_usd':face,'hedge_coin':hedge,
            'initial_coin':q,'entry_fee_coin_1x':hedge*f,'future_entry_rate':f,'spot_principal_usdt':spot_principal,
            'spot_taker_rate':F(s.advertised_taker_rate),'spot_current_exit_usdt':current_exit,
            'spot_mid_usdt':mid,'future_mid_usd':future_mid,'future_harmonic_entry_usd':face/hedge,
            'inverse_fills':inverse_fills,'spot_fills':spot_fills,'profile':profile,
            'deribit_USD_face_contract_verified':True,'spot_base_unit_contract_verified':False,
            'deribit_tick_size_steps_verified':False,
            'actual_spot_grid_verified':False,'actual_quote_units_verified':False,
            'executable_admission':False,'future_net_usdt':None}


def projected_result(plan,*,cost_multiple,fee_control,delivery_rate,delivery_price=None,exit_ratio=None,
                     total_capital='10000'):
    if type(cost_multiple) is not int or cost_multiple not in (1,2,3):raise ValueError('fixed 1x/2x/3x required')
    if fee_control not in ('zero_charge','public_standard'):raise ValueError('registered fee control required')
    k=cost_multiple;paid=fee_control=='public_standard'
    sf=plan['spot_taker_rate']*k if paid else F(0)
    stressed_fills=[(plan['future_mid_usd']-k*(plan['future_mid_usd']-p),n)
                    for p,n in plan['inverse_fills']]
    if any(p<=0 for p,_ in stressed_fills):raise ValueError('stressed_inverse_price_nonpositive')
    hedge=sum((n/p for p,n in stressed_fills),F(0))
    ef=hedge*plan['future_entry_rate']*k if paid else F(0)
    df=rational(delivery_rate,nonnegative=True)*k if paid else F(0)
    capital=rational(total_capital,positive=True)
    principal=sum((n*(plan['spot_mid_usdt']+k*(p-plan['spot_mid_usdt'])) for p,n in plan['spot_fills']),F(0))
    initial_spend=principal*(1+sf)
    if initial_spend>min(capital,F(5000)):raise ValueError('initial_cash_allocation_exceeded')
    if plan['initial_coin']-ef<hedge:raise ValueError('full_coin_collateral_unavailable_after_fees')
    terminal=terminal_conversion(plan['face_usd'],hedge,plan['initial_coin'],ef,df,
                                 delivery_price,exit_ratio,sf)
    result={'total_initial_capital_usdt':capital,'coin_counted_once':True,'initial_spend_usdt':initial_spend,
            'idle_cash_usdt':capital-initial_spend,'entry_fee_coin':ef,'delivery_fee_rate':df,
            'stressed_inverse_fills':stressed_fills,'stressed_hedge_coin':hedge,
            'stressed_spot_principal_usdt':principal,'spot_fee_rate':sf,
            'cost_multiple':k,'fee_control':fee_control,'terminal':terminal,
            'actual_net_usdt':None,'executable_admission':False,'conditional_net_usdt':None,
            'actual_transfer_cost_usdt':None,'modeled_transfer_cost':'zero-cost optimistic floor; actual route/withdrawal/network costs unknown',
            'conditional_net_on_total_capital':None,'matched_realized_risk_verified':False}
    if terminal is not None:
        result['conditional_net_usdt']=terminal['usdt_proceeds']-initial_spend
        result['conditional_net_on_total_capital']=result['conditional_net_usdt']/capital
        x=rational(delivery_price,positive=True);ratio=rational(exit_ratio,positive=True)
        result['same_initial_coin_passive_net_usdt']=plan['initial_coin']*x*ratio*(1-sf)-initial_spend
        # Reverse hurdle, includes residual coin and all modeled coin/quote fees.
        unit=terminal_conversion(plan['face_usd'],hedge,plan['initial_coin'],ef,df,x,1,sf)
        result['break_even_exit_ratio']=initial_spend/unit['usdt_proceeds'] if unit['usdt_proceeds']>0 else None
        result['residual_unhedged_coin']=terminal['residual_coin_delta']
    return result
