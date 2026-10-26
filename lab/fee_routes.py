"""Source-labelled conditional taker costs, never owner-effective fee evidence.

Keep the original reserve and crossing floor distinct from public instrument and
account-type assumptions. Later-read fee prose cannot become an earlier paid
fee, account entitlement, exact access latency or strategy result.
"""
from dataclasses import dataclass
from decimal import Decimal,InvalidOperation

from lab.executable_quotes import pair_costs

PATHS=('reserve_control','crossing_floor','nominal_standard','nominal_premium','nominal_plus',
       'advertised_standard','advertised_premium','advertised_plus')
TIERS={'standard':('0',300),'premium':('2.8',140),'plus':('0.5',300)}


def nonnegative(value):
    if isinstance(value,bool):raise ValueError('boolean fee is not a rate')
    try:x=Decimal(str(value))
    except (InvalidOperation,TypeError,ValueError) as exc:raise ValueError('explicit finite fee required') from exc
    if not x.is_finite() or x<0:raise ValueError('nonnegative finite fee required')
    return x


@dataclass(frozen=True)
class FeeTerm:
    venue:str
    symbol:str
    value:Decimal
    unit:str
    source_kind:str
    source_identity:str

    def __post_init__(self):
        object.__setattr__(self,'value',nonnegative(self.value))
        if self.venue not in ('mexc','lighter') or not self.symbol or not self.source_identity:
            raise ValueError('source-bound instrument fee required')
        if self.unit not in ('fraction','percent','bp'):raise ValueError('explicit fee-rate unit required')
        if self.source_kind not in ('reserve','floor','instrument_nominal','public_account_scenario'):
            raise ValueError('conditional public fee kind required')
        if self.fraction()>1:raise ValueError('fee fraction outside supported range')

    def fraction(self):return self.value/{'fraction':Decimal(1),'percent':Decimal(100),'bp':Decimal(10000)}[self.unit]
    def bp(self):return self.fraction()*10000


def nominal_mexc(symbol,metadata,receipt,asof,anchor,source):
    """Interpret a held public field conditionally; never grant zero-fee access."""
    flags=[]
    if metadata.get('symbol')!=symbol+'_USDT' or metadata.get('settleCoin')!='USDT' or type(metadata.get('type')) is not int or metadata['type']!=1:
        flags.append('instrument_or_linear_quote_units_unverified')
    if receipt is None or any(type(receipt.get(k)) is not int or receipt[k]<0 for k in ('received_mono_ns','received_utc_ns')):
        flags.append('public_metadata_clock_missing_or_invalid')
    elif receipt['received_mono_ns']>asof:
        flags.append('public_metadata_not_yet_known')
    elif abs((receipt['received_utc_ns']-anchor.utc_ns)-(receipt['received_mono_ns']-anchor.mono_ns))>50_000_000:
        flags.append('metadata_local_clock_step')
    if metadata.get('feeRateMode')!='NORMAL' or metadata.get('feeRateType')!='BASE':
        flags.append('nonbase_or_temporary_fee_entitlement_unverified')
    if type(metadata.get('isZeroFeeRate')) is not bool or type(metadata.get('isZeroFeeSymbol')) is not bool:
        flags.append('zero_fee_status_unknown')
    elif metadata['isZeroFeeRate'] or metadata['isZeroFeeSymbol']:
        flags.append('zero_fee_quota_account_or_expiry_unverified')
    try:
        term=FeeTerm('mexc',symbol,metadata['takerFeeRate'],'fraction','instrument_nominal',source)
        if term.value==0:flags.append('zero_nominal_is_not_fee_entitlement')
    except (KeyError,ValueError):term=None;flags.append('public_taker_rate_missing_or_invalid')
    return (None if flags else term),tuple(flags)


def routes(symbol,metadata,receipt,asof,anchor,sources,lighter_metadata):
    nominal,unknown=nominal_mexc(symbol,metadata,receipt,asof,anchor,sources['metadata'])
    make=lambda venue,value,kind,source:FeeTerm(venue,symbol,Decimal(value),'bp',kind,source)
    out=[]
    for name in PATHS:
        flags=()
        if name=='reserve_control':
            mx=make('mexc','10','reserve',sources['reserve']);lt=make('lighter','4','reserve',sources['reserve']);minimum=0
        elif name=='crossing_floor':
            mx=make('mexc','0','floor',sources['floor']);lt=make('lighter','0','floor',sources['floor']);minimum=0
        else:
            origin,tier=name.split('_');rate,minimum=TIERS[tier]
            mx=nominal if origin=='nominal' else make('mexc','4','public_account_scenario',sources['mexc_advertised'])
            if mx is None:flags=unknown
            lt=make('lighter',rate,'public_account_scenario',sources['lighter_'+tier])
            if tier in ('premium','plus') and (lighter_metadata.get('symbol')!=symbol or lighter_metadata.get('is_taker_fee_enabled') is not True):
                flags=(*flags,'lighter_paid_tier_fee_enabled_contract_unverified')
        out.append({'path':name,'fees':(mx,lt),'minimum_venue_delay_ms':minimum,'fee_flags':flags})
    return out


def assess_route(route,books,quantity,delay_ms,book_flags=()):
    if type(delay_ms) is not int or delay_ms not in (0,300):raise ValueError('fixed0/300ms access control required')
    if len(books)!=2:raise ValueError('exactly two ordered books required')
    if len(route['fees'])!=2 or any(t is not None and not isinstance(t,FeeTerm) for t in route['fees']):
        raise ValueError('exactly two source-typed fees required')
    mx,lt=route['fees'];cost=None;flags=list(route['fee_flags'])
    for i,(venue,term) in enumerate(zip(('mexc','lighter'),(mx,lt))):
        if term is None:flags.append(venue+':fee_unknown')
        b=books[i]
        if b is None or getattr(b,'venue',None)!=venue:
            flags.append(venue+':book_identity_unavailable')
        elif term is not None and (term.venue!=venue or term.symbol!=b.symbol):
            flags.append(venue+':fee_book_instrument_mismatch')
    if not flags and not book_flags and quantity is not None:
        cost=pair_costs(*books,quantity,fees_bp=(float(mx.bp()),float(lt.bp())),capital=10000)
    return {'fee_path':route['path'],'assumed_taker_bp':[str(t.bp()) if t else None for t in (mx,lt)],
            'fee_sources':[t.source_identity if t else None for t in (mx,lt)],'fee_flags':flags,
            'minimum_venue_delay_ms':route['minimum_venue_delay_ms'],
            'minimum_delay_satisfied':delay_ms>=route['minimum_venue_delay_ms'],
            'cost':cost,'account_effective_fee_verified':False,'fee_schedule_asof_verified':False,
            'execution_ready':False,'cost_unit':'USD_equivalent_under_USDT_USD_quote_parity_assumption',
            'scope':'conditional current-book taker arithmetic; later-read public schedules, not paid fees/fills or a strategy result'}
