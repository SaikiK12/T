"""Source-specific MEXC spot rules and conditional spot/perpetual quote costs.

Minimum amounts are not increments. Public commission fields are advertised
metadata, not owner fees. A decimal-grid/base-quantity convention below supports
diagnostics only; missing clock/lot/fee evidence NEVER admits an executable pair.
"""
from dataclasses import dataclass,replace
from decimal import Decimal as D,ROUND_FLOOR,InvalidOperation
from math import lcm

from lab.executable_quotes import RestBook,positive,_aggregate,walk,receipt_quality


def optional_number(value,*,positive_only=False,fee=False):
    if value is None:return None
    if isinstance(value,bool):raise ValueError('boolean metadata amount')
    try:x=D(str(value))
    except (InvalidOperation,ValueError,TypeError) as exc:raise ValueError('invalid metadata amount') from exc
    if (not x.is_finite() or x<0 or x>D('1e30') or x.as_tuple().exponent < -18
            or positive_only and x==0 or fee and x>1):
        raise ValueError('unsupported metadata amount')
    return x


@dataclass(frozen=True)
class SpotRules:
    symbol:str
    base_asset:str
    quote_asset:str
    minimum_base:D|None
    minimum_quote_market:D|None
    maximum_quote_market:D|None
    base_asset_precision:int|None
    advertised_taker_rate:D|None
    public_status:str|None
    api_spot_allowed:bool|None
    trade_side_type:int|None
    market_order_advertised:bool
    lot_step_base:D|None=None
    price_tick_quote:D|None=None

    def __post_init__(self):
        if self.lot_step_base is not None or self.price_tick_quote is not None:
            raise ValueError('received contract does not define spot lot/tick increments')


def spot_rules(symbol,payload):
    if not isinstance(payload,dict) or not isinstance(payload.get('symbols'),list):
        raise ValueError('spot exchangeInfo symbol inventory missing')
    selected=[m for m in payload['symbols'] if isinstance(m,dict) and m.get('symbol')==symbol]
    if len(selected)!=1:raise ValueError('spot symbol absent/duplicated; no substitute')
    m=selected[0];base=m.get('baseAsset');quote=m.get('quoteAsset')
    if not isinstance(base,str) or not base or quote!='USDT' or symbol!=base+quote:
        raise ValueError('explicit base/USDT symbol mapping required')
    precision=m.get('baseAssetPrecision')
    if precision is not None and (type(precision) is not int or not 0<=precision<=12):
        raise ValueError('unsupported spot base precision')
    allowed=m.get('isSpotTradingAllowed');side=m.get('tradeSideType');status=m.get('status')
    if allowed is not None and type(allowed) is not bool:raise ValueError('typed API permission required')
    if side is not None and (type(side) is not int or side not in (1,2,3,4)):raise ValueError('unknown tradeSideType')
    if status is not None and status not in ('1','2','3'):raise ValueError('unknown spot status')
    return SpotRules(symbol,base,quote,optional_number(m.get('baseSizePrecision'),positive_only=True),
                     optional_number(m.get('quoteAmountPrecisionMarket'),positive_only=True),
                     optional_number(m.get('maxQuoteAmountMarket'),positive_only=True),precision,
                     optional_number(m.get('takerCommission'),fee=True),status,allowed,side,
                     isinstance(m.get('orderTypes'),list) and 'MARKET' in m['orderTypes'])


def spot_book(symbol,payload,receipt):
    if not isinstance(payload,dict):raise ValueError('spot REST book missing')
    sides=[]
    for name in ('bids','asks'):
        rows=payload.get(name)
        if not isinstance(rows,list) or not rows or len(rows)>5:raise ValueError('bounded nonempty spot REST side required')
        if any(not isinstance(x,list) or len(x)!=2 for x in rows):raise ValueError('spot rows are price/quantity pairs')
        sides.append(_aggregate(rows,name=='bids'))
    version=payload.get('lastUpdateId')
    if type(version) is not int or version<0:raise ValueError('explicit spot snapshot version required')
    # REST contract provides NO source quote clock; version cannot be used as one.
    return RestBook('mexc',symbol,receipt,*sides,None,'spot_REST_source_clock_not_reported',version)


def illustrative_quantity(rules,perp,max_mid,budget=250):
    """Exact PERP grid plus declared decimal-only spot convention, never a live lot.

    Source baseSizePrecision is a MINIMUM, not a step. maxQuote/minQuote are
    tested later against actual hypothetical buy/sell cash, not a max-mid proxy.
    """
    if not isinstance(rules,SpotRules) or rules.base_asset+'_USDT'!=perp.get('symbol'):
        raise ValueError('spot/perpetual underlying identity mismatch')
    if type(perp.get('type')) is not int or perp['type']!=1 or perp.get('settleCoin')!='USDT':
        raise ValueError('linear USDT futures required')
    if rules.base_asset_precision is None:raise ValueError('spot decimal convention unavailable')
    a=optional_number(perp['contractSize'],positive_only=True)*optional_number(perp['volUnit'],positive_only=True)
    b=D(10)**(-rules.base_asset_precision)
    denominator=lcm(a.as_integer_ratio()[1],b.as_integer_ratio()[1])
    an=a.as_integer_ratio()[0]*(denominator//a.as_integer_ratio()[1]);bn=b.as_integer_ratio()[0]*(denominator//b.as_integer_ratio()[1])
    step=D(lcm(an,bn))/D(denominator)
    q=(positive(budget)/positive(max_mid)/step).to_integral_value(rounding=ROUND_FLOOR)*step
    if q<=0:raise ValueError('illustrative common grid yields zero size')
    return q,step


def conditional_costs(spot,perp,rules,metadata,q,*,profile='full',fee_control='zero_charge',capital=10000):
    if profile not in ('full','top_only') or fee_control not in ('zero_charge','advertised_quote_fee'):
        raise ValueError('fixed diagnostic control required')
    if spot.symbol!=rules.symbol or perp.symbol!=metadata.get('symbol') or rules.base_asset+'_USDT'!=perp.symbol:
        raise ValueError('explicit underlying identity required')
    if type(metadata.get('type')) is not int or metadata['type']!=1 or metadata.get('settleCoin')!='USDT':
        raise ValueError('linear USDT futures required')
    if capital!=10000:raise ValueError('registered segregated capital is fixed')
    q=optional_number(q,positive_only=True)
    if profile=='top_only':
        spot=replace(spot,bids=spot.bids[:1],asks=spot.asks[:1]);perp=replace(perp,bids=perp.bids[:1],asks=perp.asks[:1])
    fees=[D(0),D(0)] if fee_control=='zero_charge' else [rules.advertised_taker_rate,optional_number(metadata.get('takerFeeRate'),fee=True)]
    local=receipt_quality([spot,perp],max(spot.receipt.received_mono_ns,perp.receipt.received_mono_ns),age_ns=2_000_000_000,skew_ns=1_000_000_000)
    flags=[]
    if rules.public_status!='1':flags.append('spot_not_advertised_online_or_unknown')
    if rules.api_spot_allowed is not True:flags.append('spot_API_not_advertised_allowed_or_unknown')
    if rules.trade_side_type!=1:flags.append('spot_two_way_permission_not_advertised')
    if not rules.market_order_advertised:flags.append('spot_market_order_not_advertised')
    if (metadata.get('apiAllowed') is not True or type(metadata.get('state')) is not int or metadata['state']!=0):
        flags.append('perp_API_or_state_not_advertised_open')
    fills=[walk(side,q) for book in (spot,perp) for side in (book.asks,book.bids)]
    capacity=min(sum(D(str(level.size)) for level in side) for book in (spot,perp) for side in (book.asks,book.bids))
    result={'profile':profile,'fee_control':fee_control,'illustrative_base_quantity':str(q),'public_rule_flags':flags,
            'local_receipt_quality':local,'conditional_shown_capacity_base':str(capacity),
            'quantity_convention':'spot quantity as base; decimal precision grid only, not verified spot increment',
            'executable_pair_eligible':False,'actual_order_allowed':False,'net_market_return':None,
            'unresolved':['spot_quantity_asset_contract','spot_lot_and_tick_increment','REST_source_quote_age',
                          'actual_owner_fee_rate_and_asset','actual_fill_latency_and_exit','actual_funding_cash_and_notional',
                          'owner_permission_and_session_availability']}
    reasons=list(local['first_seen_flags'])+flags
    perp_step=optional_number(metadata['contractSize'],positive_only=True)*optional_number(metadata['volUnit'],positive_only=True)
    if q%perp_step:reasons.append('quantity_off_perp_lattice')
    if rules.base_asset_precision is None:reasons.append('spot_decimal_grid_convention_unknown')
    elif q%(D(10)**(-rules.base_asset_precision)):reasons.append('quantity_off_spot_decimal_convention')
    if any(v is None for v in fills):reasons.append('insufficient_shown_depth_fixed_quantity')
    if any(v is None for v in fees):reasons.append('public_advertised_commission_unknown')
    minimum=positive(metadata['minVol'])*positive(metadata['contractSize'])
    if q<minimum or q>positive(metadata['maxVol'])*positive(metadata['contractSize']):reasons.append('perp_quantity_outside_published_range')
    if rules.minimum_base is None:reasons.append('spot_minimum_base_unknown')
    elif q<rules.minimum_base:reasons.append('spot_below_minimum_base')
    if rules.minimum_quote_market is None:reasons.append('spot_minimum_market_amount_unknown')
    if rules.maximum_quote_market is None:reasons.append('spot_maximum_market_amount_unknown')
    if all(v is not None for v in fills):
        buy,sell,pbuy,psell=map(lambda v:D(str(v)),fills)
        # Shared depth helpers use floats. Do not certify a threshold equality
        # that those conversions could have rounded across; retain it unknown.
        margin=D('1e-8')
        if rules.minimum_quote_market is not None and abs(min(buy,sell)-rules.minimum_quote_market)<=margin:
            reasons.append('spot_minimum_quote_rounding_boundary_unknown')
        if rules.maximum_quote_market is not None and abs(max(buy,sell)-rules.maximum_quote_market)<=margin:
            reasons.append('spot_maximum_quote_rounding_boundary_unknown')
        if rules.minimum_quote_market is not None and min(buy,sell)<rules.minimum_quote_market:reasons.append('spot_below_minimum_market_amount')
        if rules.maximum_quote_market is not None and max(buy,sell)>rules.maximum_quote_market:reasons.append('spot_above_maximum_market_amount')
        if all(v is not None for v in fees):
            spot_cash=buy*(1+fees[0]);perp_reserve=q*D(str(perp.mid))+psell*fees[1]
            if min(abs(spot_cash-D(5000)),abs(perp_reserve-D(5000)))<=margin:
                reasons.append('segregated_cash_rounding_boundary_unknown')
            if spot_cash>D(5000) or perp_reserve>D(5000):reasons.append('segregated_entry_cash_or_reservation_exceeded')
        if reasons:result['hypothetical_fill_cash']=list(map(str,(buy,sell,pbuy,psell)))
    result['conditional_calculation_reasons']=sorted(set(reasons))
    result['costs']=None
    if not reasons:
        crossing=buy-sell+pbuy-psell;fee=(buy+sell)*fees[0]+(pbuy+psell)*fees[1]
        notional=q*(D(str(spot.mid))+D(str(perp.mid)))/2
        result.update(hypothetical_fill_cash=list(map(str,(buy,sell,pbuy,psell))),
                      hypothetical_quote_fee_rates=list(map(str,fees)),crossing_quote=str(crossing),
                      commission_quote=str(fee),one_leg_reference_notional=str(notional),
                      costs=[{'multiple':k,'required_gross_quote_to_break_even':str(k*(crossing+fee)),
                              'break_even_one_leg_bp':str(k*(crossing+fee)/notional*10000),
                              'cost_on_total_capital_bp':str(k*(crossing+fee))} for k in (1,2,3)])
    return result
