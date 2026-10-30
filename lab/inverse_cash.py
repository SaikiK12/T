"""Exact simulated inverse-futures COIN cash, separate from linear futures.

USD-face amounts are not base quantities. Daily settlement realizes the same
position, delivery closes it, and neither creates another spot inventory.
No exchange rounding, margin engine, live order, or actual settlement attested.
"""
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path

from lab.acquisition_budget import _locked, _read_records, _append_record
from lab.funding_values import clock_known
from lab.paper_account import number, text
from lab.stream_quotes import FrameClock


def rational(value, *, positive=False, nonnegative=False):
    if type(value) is F:
        out = value
    else:
        if type(value) not in (str, int, Decimal):
            raise ValueError('exact decimal or rational required')
        if type(value) is str and len(value)>1000:raise ValueError('bounded numeric text required')
        try:dec=Decimal(value)
        except (InvalidOperation,ValueError,TypeError) as exc:raise ValueError('finite decimal required') from exc
        if not dec.is_finite() or abs(dec.as_tuple().exponent)>200:raise ValueError('bounded finite decimal scale required')
        dec=number(dec)
        out = F(dec)
    if (abs(out) > 10**30 or out.denominator > 10**200
            or positive and out <= 0 or nonnegative and out < 0):
        raise ValueError('rational outside supported range')
    return out


def wire(value):
    value = rational(value)
    return {'numerator':value.numerator, 'denominator':value.denominator}


def unwire(value):
    if (type(value) is not dict or set(value) != {'numerator','denominator'}
            or type(value['numerator']) is not int or type(value['denominator']) is not int
            or value['denominator'] <= 0):
        raise ValueError('exact rational wire object required')
    return rational(F(value['numerator'],value['denominator']))


@dataclass(frozen=True)
class InverseContract:
    instrument: str
    coin: str
    face_step_usd: F
    minimum_face_usd: F
    expiry_ns: int
    source_identity: str

    def __post_init__(self):
        for s in (self.instrument,self.coin,self.source_identity):text(s)
        for name in ('face_step_usd','minimum_face_usd'):
            object.__setattr__(self,name,rational(getattr(self,name),positive=True))
        if type(self.expiry_ns) is not int or self.expiry_ns <= 0:
            raise ValueError('finite dated expiry required; no perpetual')

    def mapping(self):
        out=asdict(self)
        for name in ('face_step_usd','minimum_face_usd'):out[name]=wire(out[name])
        return out


@dataclass(frozen=True)
class InverseEvent:
    event_id: str
    kind: str
    instrument: str
    occurred_ns: int
    clock: FrameClock
    source_identity: str
    price_usd_per_coin: F
    signed_face_usd: F = F(0)
    fee_coin: F | None = None
    simulation_only: bool = True

    def __post_init__(self):
        for s in (self.event_id,self.instrument,self.source_identity):text(s)
        if self.simulation_only is not True or self.kind not in ('open','daily','delivery'):
            raise ValueError('explicit simulated inverse operation required')
        if (type(self.occurred_ns) is not int or self.occurred_ns < 0
                or not isinstance(self.clock,FrameClock) or self.occurred_ns > self.clock.utc_ns):
            raise ValueError('separate economic/receipt clocks required')
        object.__setattr__(self,'price_usd_per_coin',rational(self.price_usd_per_coin,positive=True))
        object.__setattr__(self,'signed_face_usd',rational(self.signed_face_usd))
        if self.fee_coin is not None:
            object.__setattr__(self,'fee_coin',rational(self.fee_coin,nonnegative=True))
        if (self.kind=='open') != bool(self.signed_face_usd):
            raise ValueError('opening uses signed USD face; settlement supplies no position override')
        if self.kind=='daily' and self.fee_coin != 0:
            raise ValueError('daily settlement is explicitly fee-free, not another delivery')

    def mapping(self):
        out=asdict(self)
        for name in ('price_usd_per_coin','signed_face_usd','fee_coin'):
            if out[name] is not None:out[name]=wire(out[name])
        return out

    @classmethod
    def from_mapping(cls,value):
        if (type(value) is not dict or value.get('simulation_only') is not True
                or set(value)!=set(cls.__dataclass_fields__)):
            raise ValueError('explicit inverse event mapping required')
        value=dict(value);value['clock']=FrameClock(**value['clock'])
        for name in ('price_usd_per_coin','signed_face_usd','fee_coin'):
            if value[name] is not None:value[name]=unwire(value[name])
        return cls(**value)


class InverseCashAccount:
    """One dated position and its coin collateral; no USD principal credit.

    Only same-direction opening fills are supported. No borrowing, withdrawals,
    resizing/rolls, exchange liquidation or private account evidence is implied.
    """
    def __init__(self,contract,initial_coin,anchor,*,journal_path=None):
        if not isinstance(contract,InverseContract) or not isinstance(anchor,FrameClock):
            raise ValueError('typed contract and common anchor required')
        self.contract,self.anchor=contract,anchor
        self.initial=rational(initial_coin,nonnegative=True)
        self.journal_path=None if journal_path is None else Path(journal_path)
        self.config={'kind':'inverse_cash_model_config','contract':contract.mapping(),
                     'initial_coin':wire(self.initial),'anchor':asdict(anchor),'simulation_only':True}
        self._reset()
        if self.journal_path is not None:
            with _locked(self.journal_path) as h:self._load(h)

    def _reset(self):
        self.coin=self.initial;self.face=F(0);self.entry_reciprocal=F(0)
        self.price_pnl=F(0);self.fees=F(0);self.delivered=False
        self.pending=set();self.conflicts=set();self.risks=set();self.seen={}
        self.last_asof=-1;self.last_economic=self.anchor.utc_ns

    def _load(self,h):
        rows=_read_records(h)
        if not rows:_append_record(h,rows,self.config)
        elif rows[0]['event']!=self.config:raise ValueError('inverse journal identity/capital cannot reset')
        self._reset()
        for row in rows[1:]:
            e=row['event']
            if e['kind']!='inverse_model_attempt':raise ValueError('unknown inverse journal operation')
            self._apply(InverseEvent.from_mapping(e['payload']),e['asof'])
        return rows

    def post(self,event,asof):
        if not isinstance(event,InverseEvent) or type(asof) is not int or asof < 0:
            raise ValueError('typed inverse event/asof required')
        if self.journal_path is None:return self._apply(event,asof)
        with _locked(self.journal_path) as h:
            rows=self._load(h)
            _append_record(h,rows,{'kind':'inverse_model_attempt','payload':event.mapping(),'asof':asof})
            return self._apply(event,asof)

    def _apply(self,e,asof):
        payload=e.mapping();payload.pop('clock')
        signature=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        reasons=[]
        if asof < self.last_asof:reasons.append('asof_regressed')
        if not clock_known(e.clock,asof,self.anchor):reasons.append('future_receipt_or_clock_step')
        if not self.anchor.utc_ns <= e.occurred_ns <= self.anchor.utc_ns+asof-self.anchor.mono_ns:
            reasons.append('economic_event_outside_known_baseline')
        if e.instrument!=self.contract.instrument:reasons.append('inverse_contract_mismatch')
        status='rejected' if reasons else 'applied'
        if not reasons and e.event_id in self.seen:
            status='duplicate' if signature==self.seen[e.event_id] else 'conflicting_revision'
            if status=='conflicting_revision':self.conflicts.add(e.event_id)
        elif not reasons:
            if self.delivered:reasons.append('position_already_delivered')
            if e.occurred_ns < self.last_economic:reasons.append('economic_time_regressed')
            if e.kind=='open':
                q=e.signed_face_usd;c=self.contract
                if self.pending or self.conflicts:reasons.append('opening_collateral_unknown')
                if e.occurred_ns >= c.expiry_ns:reasons.append('opening_at_or_after_expiry')
                if abs(q)<c.minimum_face_usd or q%c.face_step_usd:reasons.append('face_minimum_or_increment')
                if self.face*q < 0:reasons.append('opposite_fill_requires_separate_close_protocol')
                # Fully collateralized model only; not a venue margin attestation.
                equity=self.coin+self.face*(self.entry_reciprocal-1/e.price_usd_per_coin)
                if abs(self.face+q)/e.price_usd_per_coin > equity-(e.fee_coin or 0):
                    reasons.append('full_coin_collateral_unavailable')
            else:
                if not self.face:reasons.append('no_open_inverse_position')
                if e.kind=='delivery' and e.occurred_ns<self.contract.expiry_ns:
                    reasons.append('delivery_before_expiry')
                if e.kind=='daily' and e.occurred_ns>=self.contract.expiry_ns:
                    reasons.append('expired_position_requires_delivery')
            if reasons:status='rejected'
            else:
                if e.kind=='open':
                    old=self.face
                    self.face+=e.signed_face_usd
                    self.entry_reciprocal=(old*self.entry_reciprocal+e.signed_face_usd/e.price_usd_per_coin)/self.face
                else:
                    pnl=self.face*(self.entry_reciprocal-1/e.price_usd_per_coin)
                    self.coin+=pnl;self.price_pnl+=pnl
                    self.entry_reciprocal=1/e.price_usd_per_coin
                    if e.kind=='delivery':self.face=F(0);self.delivered=True
                if e.fee_coin is None:self.pending.add(e.event_id)
                else:self.coin-=e.fee_coin;self.fees+=e.fee_coin
                if self.coin<0:self.risks.add('negative_coin_cash')
                self.seen[e.event_id]=signature;self.last_economic=e.occurred_ns
        self.last_asof=max(self.last_asof,asof)
        return {'status':status,'reasons':reasons,
                'entry_collateral_assessment':('unknown_fee' if e.fee_coin is None else
                    'conditional_supplied_coin_only') if e.kind=='open' else None}

    def snapshot(self):
        known=not self.pending and not self.conflicts
        return {'coin_asset':self.contract.coin,'known_coin_component':str(self.coin),
                'coin_cash':str(self.coin) if known else None,'signed_face_usd':str(self.face),
                'entry_reciprocal':str(self.entry_reciprocal),'realized_price_pnl_coin':str(self.price_pnl),
                'fees_coin':str(self.fees),'pending_fees':sorted(self.pending),'conflicts':sorted(self.conflicts),
                'risk_flags':sorted(self.risks),'delivered':self.delivered,
                'actual_account_credit_verified':False,'net_usdt':None}


def walk(levels,amount,*,side,unit):
    """Exact finite shown-depth walk. Inverse amount is USD face, spot is base.

    Inverse hedge uses SUM(face_i / price_i), never face / arithmetic VWAP.
    No extrapolation, fill probability, source freshness or unit inference.
    """
    amount=rational(amount,positive=True)
    if side not in ('buy','sell') or unit not in ('base','USD_face'):
        raise ValueError('explicit side and source amount unit required')
    left=amount;fills=[];last=None
    for row in levels:
        if type(row) not in (list,tuple) or len(row)!=2:raise ValueError('price/amount pair required')
        p,q=(rational(v,positive=True) for v in row)
        if last is not None and (p<=last if side=='buy' else p>=last):
            raise ValueError('strict sorted book required')
        last=p
        take=min(q,left)
        if take:
            fills.append((p,take));left-=take
    if left:raise ValueError('insufficient_shown_depth_fixed_face_or_base')
    if unit=='USD_face':return fills,sum((q/p for p,q in fills),F(0))
    return fills,sum((q*p for p,q in fills),F(0))


def terminal_conversion(face_usd,hedge_coin,initial_coin,entry_fee_coin,delivery_fee_rate,
                        delivery_price,exit_ratio,spot_exit_rate):
    """Conditional terminal USDT, NOT an observed payment or locked cash gain.

    exit_ratio = actual spot USDT/coin divided by delivery USD/coin; it includes
    venue/TWAP timing and USD/USDT effects. Unknown ratio/price stays unknown.
    """
    face=rational(face_usd,positive=True);a=rational(hedge_coin,positive=True)
    initial=rational(initial_coin,nonnegative=True);fee=rational(entry_fee_coin,nonnegative=True)
    df=rational(delivery_fee_rate,nonnegative=True);sf=rational(spot_exit_rate,nonnegative=True)
    if df>=1 or sf>=1:raise ValueError('fee rate must be below one')
    if delivery_price is None or exit_ratio is None:return None
    x=rational(delivery_price,positive=True);ratio=rational(exit_ratio,positive=True)
    residual=initial-fee-a
    coin=face*(1-df)/x+residual
    return {'coin_after_delivery':coin,'residual_coin_delta':residual,
            'usdt_proceeds_before_spot_fee':coin*x*ratio,
            'usdt_proceeds':coin*x*ratio*(1-sf)}
