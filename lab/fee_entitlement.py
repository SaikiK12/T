"""Fee-source interpretation and exact rounded-cost envelopes; no account access.

Public contract metadata and official examples are not owner entitlement.
No private balances/identifiers, secrets or original payload are returned.
"""
from decimal import Decimal
from fractions import Fraction as F
import re

from lab.inverse_cash import rational


def fee_view(payload, *, instrument, source_identity, origin, rate_unit, received_utc_ns, asof_utc_ns):
    if (origin not in ('public_contract_metadata','official_documentation_example','owner_redacted_export')
            or rate_unit not in ('fraction','unknown') or not re.fullmatch('[0-9a-f]{64}',source_identity)
            or type(received_utc_ns) is not int or type(asof_utc_ns) is not int
            or not isinstance(instrument,str) or not instrument):
        raise ValueError('explicit bounded source/clock/origin/unit required')
    if type(payload) is not dict or payload.get('success') is not True or type(payload.get('code')) is not int or payload.get('code')!=0 or type(payload.get('data')) is not dict:
        raise ValueError('successful fee-shape envelope required')
    data=payload['data'];flags=[]
    if data.get('symbol')!=instrument:flags.append('instrument_binding_missing_or_different')
    if received_utc_ns>asof_utc_ns:flags.append('future_receipt')
    if asof_utc_ns-received_utc_ns>1_000_000_000:flags.append('receipt_older_than_1s')
    if origin=='public_contract_metadata':flags.append('public_contract_is_not_account_fee')
    elif origin=='official_documentation_example':flags.append('documentation_example_is_not_owner_response')
    else:flags.append('redacted_export_authenticity_and_route_unverified')
    mode=data.get('feeRateMode')
    if mode not in ('NORMAL','TIERED','LEVERAGE'):flags.append('fee_mode_unknown')
    if mode in ('TIERED','LEVERAGE'):flags.append('future_tier_leverage_quota_path_unverified')
    if data.get('statisticType')=='FIXED':
        start,end=data.get('fixedStartTime'),data.get('fixedEndTime')
        if type(start) is not int or type(end) is not int or not start<end:flags.append('fixed_period_invalid')
        elif not start*1_000_000<=asof_utc_ns<end*1_000_000:flags.append('outside_published_fixed_period')
    field='takerFeeRate' if origin=='public_contract_metadata' else 'realTakerFee'
    value=None if data.get(field) is None else rational(data[field],nonnegative=True)
    if value is not None and value>=1:raise ValueError('fee fraction outside bounded hypothesis')
    if rate_unit=='unknown':flags.append('endpoint_decimal_scaling_unverified')
    if value is None:flags.append('taker_value_missing')
    # The endpoint's real* fee already includes its reported adjustments. Never
    # multiply it again by discountRate/deductRate or read walletBalance/KYC.
    return {'instrument':instrument,'source_identity':source_identity,'origin':origin,'fee_mode':mode,
        'published_taker_decimal':value,'conditional_fraction_hypothesis_bp':None if value is None or rate_unit!='fraction' else value*10000,
        'owner_entitlement_verified':False,'opportunity_fee_bp':None,
        'settlement_asset_verified':False,'api_route_verified':False,'flags':sorted(set(flags)),
        'actual_expected_net':None,'actual_order_allowed':False}


def bind_opportunity_fee(market_report,view):
    """Feed unverified fee evidence into the existing opportunity/risk guards.

The bridge does not authenticate an export or promote public metadata. A later
authenticated-fee adapter needs its own source contract, not a green boolean.
"""
    if type(market_report) is not dict or type(view) is not dict or view.get('owner_entitlement_verified') is not False:
        raise ValueError('this adapter accepts unverified fee views only')
    result=dict(market_report);result['state']='unknown'
    result['fee_source_identity']=view['source_identity'];result['fee_evidence_flags']=list(view['flags'])
    return {'market_report':result,'fee_bp':None,'risk_fee_inputs_known':False,'actual_order_allowed':False}


def rounded_cost_interval(record):
    """Intersect BOTH three-decimal published fields with the original1bp floor.

These are numeric serialization bounds, not statistical confidence intervals.
No historical raw spread or exact original threshold is reconstructed.
"""
    med=rational(record['median_half_spread_bp'],nonnegative=True)
    cost=rational(record['one_way_bp'],nonnegative=True);half=F(1,2000)
    lo=max(F(1),med-half,cost-half);hi=min(max(F(1),med+half),cost+half)
    if lo>hi:raise ValueError('published median/floor/cost intervals contradict')
    return lo/10000,hi/10000


def membership(edge,cost):
    lo,hi=(rational(x,nonnegative=True) for x in cost)
    if lo<0 or hi<lo:raise ValueError('ordered nonnegative cost bounds required')
    if edge is None:return 'inactive_missing_prediction'
    edge=rational(edge)
    if abs(edge)>4*hi:return 'certain'
    if abs(edge)<=4*lo:return 'inactive'
    return 'ambiguous'


def payoff_interval(g,side,status,cost,fee_bp,multiple):
    if type(side) is not int or type(multiple) is not int or side not in (-1,0,1) or multiple not in (1,2,3) or status not in ('certain','inactive','inactive_missing_prediction','ambiguous'):
        raise ValueError('fixed side/cost/inclusion controls required')
    fee=rational(fee_bp,nonnegative=True)/10000
    lo,hi=(rational(x,nonnegative=True) for x in cost)
    if hi<lo:raise ValueError('ordered nonnegative cost bounds required')
    if not side or status in ('inactive','inactive_missing_prediction'):return F(0),F(0)
    if g is None:return None,None
    gross=side*rational(g)
    lower=gross-2*multiple*(hi+fee);upper=gross-2*multiple*(lo+fee)
    if status=='ambiguous':return min(F(0),lower),max(F(0),upper)
    return lower,upper
