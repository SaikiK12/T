"""One append-only simulated linear-futures account, separated by venue/asset.

Opening notional is collateral reservation, not spent cash. Closed price PnL,
funding and fees post once; execution drag embedded in fill prices is diagnostic
only. Unknown cash never becomes zero and missing marks never erase known cash.
No network, real orders, account access or activation is implemented here.
"""
from dataclasses import dataclass,asdict
from decimal import Decimal,InvalidOperation,localcontext
from functools import wraps
import hashlib
import json
from pathlib import Path

from lab.acquisition_budget import _locked,_read_records,_append_record
from lab.stream_quotes import FrameClock,NS
from lab.funding_values import clock_known,PositionSpan


def number(value,*,positive=False,nonnegative=False):
    if isinstance(value,bool):raise ValueError('explicit finite amount required')
    try:x=Decimal(str(value))
    except (InvalidOperation,TypeError,ValueError):raise ValueError('invalid amount') from None
    if not x.is_finite() or abs(x)>Decimal('1e30') or (positive and x<=0) or (nonnegative and x<0):
        raise ValueError('amount outside supported finite range')
    return x


def text(value):
    if not isinstance(value,str) or not value or len(value)>256 or any(ord(c)<32 for c in value):
        raise ValueError('explicit bounded identity required')
    return value


def _precision(fn):
    @wraps(fn)
    def bounded(*args,**kwargs):
        with localcontext() as context:
            context.prec=80
            return fn(*args,**kwargs)
    return bounded


@dataclass(frozen=True)
class PaperEvent:
    event_id:str
    kind:str
    venue:str
    asset:str
    symbol:str
    occurred_ns:int
    clock:FrameClock
    source_identity:str
    quantity:Decimal|None=None
    price:Decimal|None=None
    fee:Decimal|None=None
    amount:Decimal|None=None
    reference_mid:Decimal|None=None
    resolves:str|None=None
    simulation_only:bool=True

    def __post_init__(self):
        for k in ('event_id','venue','asset','symbol','source_identity'):text(getattr(self,k))
        if self.simulation_only is not True or self.kind not in ('fill','funding','capital_change','fee_resolution','funding_resolution'):
            raise ValueError('explicit supported simulated event required')
        if type(self.occurred_ns) is not int or self.occurred_ns<0 or not isinstance(self.clock,FrameClock):
            raise ValueError('separate economic and first-seen clocks required')
        if self.occurred_ns>self.clock.utc_ns:raise ValueError('economic event cannot be later than its first observation')
        for k in ('quantity','price','fee','amount','reference_mid'):
            v=getattr(self,k)
            if v is not None:object.__setattr__(self,k,number(v,positive=k in ('price','reference_mid'),nonnegative=k=='fee'))
        if self.kind=='fill' and (self.quantity is None or self.quantity==0 or self.price is None):
            raise ValueError('signed base quantity and fill price required')
        if self.kind=='fill' and self.amount is not None:raise ValueError('fill cash is derived, not supplied')
        if self.kind!='fill' and any(getattr(self,k) is not None for k in ('quantity','price','fee','reference_mid')):
            raise ValueError('fill-only fields on a cash event')
        if self.kind=='capital_change' and self.amount is None:raise ValueError('explicit external flow required')
        if self.kind.endswith('_resolution'):
            text(self.resolves)
            if self.amount is None or (self.kind=='fee_resolution' and self.amount<0):raise ValueError('explicit resolved amount required')
        elif self.resolves is not None:raise ValueError('resolution target only applies to resolution event')

    def mapping(self):
        d=asdict(self)
        for k in ('quantity','price','fee','amount','reference_mid'):
            if d[k] is not None:d[k]=str(d[k])
        return d

    @classmethod
    def from_mapping(cls,data):
        if not isinstance(data,dict) or set(data)-set(cls.__dataclass_fields__):raise ValueError('unsupported event fields')
        if data.get('simulation_only') is not True:raise ValueError('simulation-only declaration required')
        d=dict(data);d['clock']=FrameClock(**d['clock']);return cls(**d)


@dataclass(frozen=True)
class CloseMark:
    venue:str
    asset:str
    symbol:str
    position_quantity:Decimal
    exit_notional:Decimal
    estimated_exit_fee:Decimal|None
    clock:FrameClock
    source_time_ns:int
    source_identity:str

    def __post_init__(self):
        for k in ('venue','asset','symbol','source_identity'):text(getattr(self,k))
        object.__setattr__(self,'position_quantity',number(self.position_quantity))
        object.__setattr__(self,'exit_notional',number(self.exit_notional,positive=True))
        if self.position_quantity==0 or not isinstance(self.clock,FrameClock) or type(self.source_time_ns) is not int:
            raise ValueError('explicit position and quote clocks required')
        if self.estimated_exit_fee is not None:object.__setattr__(self,'estimated_exit_fee',number(self.estimated_exit_fee,nonnegative=True))


class PaperAccount:
    def __init__(self,initial_balances,anchor,*,journal_path=None):
        if not isinstance(anchor,FrameClock):raise ValueError('common clock anchor required')
        self.anchor=anchor
        self.initial={(text(v),text(a)):number(c,nonnegative=True) for (v,a),c in initial_balances.items()}
        if not self.initial:raise ValueError('segregated initial balances required')
        self.journal_path=Path(journal_path) if journal_path is not None else None
        self._reset()
        if self.journal_path is not None:
            with _locked(self.journal_path) as handle:self._load(handle)

    def _reset(self):
        self.cash=dict(self.initial);self.price={k:Decimal(0) for k in self.initial};self.funding=dict(self.price)
        self.fees=dict(self.price);self.flows=dict(self.price);self.drag=dict(self.price)
        self.positions={};self.seen={};self.pending={};self.attempts=[];self.last_asof=-1;self.last_fill={}
        self.accepted_events=[];self.evidence=[]
        self.reconciliation={k:set() for k in self.initial}

    def _header(self):
        return {'kind':'paper_account_header','anchor':asdict(self.anchor),
                'initial':[{'venue':v,'asset':a,'cash':str(c)} for (v,a),c in sorted(self.initial.items())]}

    def _load(self,handle):
        records=_read_records(handle)
        if not records:_append_record(handle,records,self._header())
        if records[0]['event']!=self._header():raise ValueError('account baseline/anchor cannot reset')
        self._reset()
        for record in records[1:]:
            row=record['event']
            if row.get('kind')=='paper_evidence':self.evidence.append(row)
            elif row.get('kind')=='paper_account_attempt':self._apply(PaperEvent.from_mapping(row['payload']),row['asof_mono_ns'])
            else:raise ValueError('unexpected account journal event')
        return records

    def record_evidence(self,namespace,payload):
        """Persist caller assumptions alongside, without converting them to cash."""
        if namespace not in ('fee_assumption','funding_assessment','recovery','acquisition_budget'):raise ValueError('unsupported evidence namespace')
        encoded=json.dumps(payload,sort_keys=True,allow_nan=False)
        if len(encoded.encode())>65536:raise ValueError('evidence record exceeds64KiB')
        row={'kind':'paper_evidence','namespace':namespace,'payload':json.loads(encoded)}
        if self.journal_path is None:self.evidence.append(row)
        else:
            with _locked(self.journal_path) as handle:
                records=self._load(handle);_append_record(handle,records,row);self.evidence.append(row)

    def post(self,event,asof):
        if not isinstance(event,PaperEvent) or type(asof) is not int or asof<0:raise ValueError('typed simulated event/as-of required')
        if self.journal_path is None:return self._apply(event,asof)
        with _locked(self.journal_path) as handle:
            records=self._load(handle)
            # Durable intent before mutating exposed financial state. Reopen
            # replays rejected, duplicate and accepted attempts identically.
            _append_record(handle,records,{'kind':'paper_account_attempt','payload':event.mapping(),'asof_mono_ns':asof})
            return self._apply(event,asof)

    @_precision
    def _apply(self,e,asof):
        key=(e.venue,e.asset);pos=(*key,e.symbol)
        economic=e.mapping();del economic['clock']
        # A later delivery of the same provider event cannot post twice or
        # refresh the original first-seen clock. Numeric spelling is immaterial.
        for k in ('quantity','price','fee','amount','reference_mid'):
            if economic[k] is not None:economic[k]=str(Decimal(economic[k]).normalize())
        signature=hashlib.sha256(json.dumps(economic,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        status='applied';reasons=[]
        if asof<self.last_asof:reasons.append('asof_regressed')
        if key not in self.initial:reasons.append('unfunded_venue_or_asset')
        if not clock_known(e.clock,asof,self.anchor):reasons.append('event_future_receipt_or_clock_step')
        if self.anchor.utc_ns+asof-self.anchor.mono_ns<e.occurred_ns:reasons.append('economic_event_future')
        if e.occurred_ns<self.anchor.utc_ns:reasons.append('event_before_initial_flat_baseline')
        if reasons:status='rejected'
        elif e.event_id in self.seen:
            oldsig,oldkey=self.seen[e.event_id]
            status='duplicate' if oldsig==signature else 'conflicting_revision'
            if status=='conflicting_revision':
                reasons.append('financial_revision_requires_reconciliation')
                for k in (key,oldkey):
                    if k in self.reconciliation:self.reconciliation[k].add(e.event_id+':financial_revision_requires_reconciliation')
        elif e.kind=='fill' and e.occurred_ns<self.last_fill.get(pos,-1):
            status='rejected';reasons.append('late_fill_order_requires_reconciliation')
            self.reconciliation[key].add(e.event_id+':late_fill_order_requires_reconciliation')
        elif e.kind.endswith('_resolution'):
            old=self.pending.get(e.resolves)
            expected='fee' if e.kind=='fee_resolution' else 'funding'
            if old is None or old!=(key,e.symbol,expected):status='rejected';reasons.append('resolution_identity_missing_or_mismatch')
        if status=='applied':
            self.seen[e.event_id]=(signature,key)
            self.accepted_events.append(e)
            if e.kind=='fill':
                oldq,entry=self.positions.get(pos,(Decimal(0),Decimal(0)));q=e.quantity;newq=oldq+q
                realized=Decimal(0)
                if oldq==0 or oldq*q>0:
                    basis=(abs(oldq)*entry+abs(q)*e.price)/abs(newq)
                else:
                    closed=min(abs(oldq),abs(q));realized=(1 if oldq>0 else -1)*closed*(e.price-entry)
                    basis=Decimal(0) if newq==0 else entry if oldq*newq>0 else e.price
                self.positions[pos]=(newq,basis);self.price[key]+=realized;self.cash[key]+=realized
                self.last_fill[pos]=e.occurred_ns
                if e.fee is None:self.pending[e.event_id]=(key,e.symbol,'fee')
                else:self.fees[key]+=e.fee;self.cash[key]-=e.fee
                if e.reference_mid is not None:self.drag[key]+=q*(e.price-e.reference_mid)
            elif e.kind=='funding':
                if e.amount is None:self.pending[e.event_id]=(key,e.symbol,'funding')
                else:self.funding[key]+=e.amount;self.cash[key]+=e.amount
            elif e.kind=='capital_change':self.flows[key]+=e.amount;self.cash[key]+=e.amount
            else:
                del self.pending[e.resolves]
                if e.kind=='fee_resolution':self.fees[key]+=e.amount;self.cash[key]-=e.amount
                else:self.funding[key]+=e.amount;self.cash[key]+=e.amount
        self.last_asof=max(asof,self.last_asof)
        result={'event_id':e.event_id,'status':status,'reasons':reasons,'asof_mono_ns':asof,'simulation_only':True}
        self.attempts.append(result);return result

    def position_spans(self,venue,asset,symbol,observed_clock):
        """Known simulated exposure since the initial flat baseline, never fills.

        Reconciliation faults withhold coverage rather than supplying a false
        flat interval. The caller still needs actual event-bound funding inputs.
        """
        if self.journal_path is not None:
            with _locked(self.journal_path) as handle:self._load(handle)
        key=(venue,asset)
        if key not in self.initial or not isinstance(observed_clock,FrameClock):raise ValueError('funded identity/clock required')
        at=observed_clock.mono_ns
        if at<self.last_asof or not clock_known(observed_clock,at,self.anchor):raise ValueError('current causal observation required')
        if self.reconciliation[key]:return None
        start=self.anchor.utc_ns;end=observed_clock.utc_ns;q=Decimal(0);spans=[]
        for e in self.accepted_events:
            if (e.venue,e.asset,e.symbol)!=(venue,asset,symbol) or e.kind!='fill':continue
            if e.occurred_ns>start:spans.append(PositionSpan(start,e.occurred_ns,q,observed_clock,venue,symbol,'base'))
            q+=e.quantity;start=e.occurred_ns
        if end>start:spans.append(PositionSpan(start,end,q,observed_clock,venue,symbol,'base'))
        return spans

    @_precision
    def snapshot(self,asof,marks=()):
        if self.journal_path is not None:
            with _locked(self.journal_path) as handle:self._load(handle)
        if type(asof) is not int or asof<self.last_asof:raise ValueError('snapshot cannot backdate current state')
        lookup={}
        for m in marks:
            if not isinstance(m,CloseMark):raise ValueError('typed liquidation mark required')
            key=(m.venue,m.asset,m.symbol)
            if key in lookup:raise ValueError('duplicate liquidation mark')
            lookup[key]=m
        accounts=[]
        for key,initial in sorted(self.initial.items()):
            reasons=[];pending=[eid for eid,(k,_,_) in self.pending.items() if k==key]
            if pending:reasons.append('fee_or_funding_amount_unknown')
            issues=sorted(self.reconciliation[key])
            if issues:reasons.append('financial_event_reconciliation_required')
            open_pnl=Decimal(0);exit_fees=Decimal(0);marks_known=True;fees_known=True;locked=Decimal(0);positions=[]
            for (v,a,s),(q,basis) in sorted(self.positions.items()):
                if (v,a)!=key or q==0:continue
                locked+=abs(q)*basis;m=lookup.get((v,a,s));flags=[];pnl=None
                if m is None:flags.append('liquidation_quote_missing')
                else:
                    age=self.anchor.utc_ns+asof-self.anchor.mono_ns-m.source_time_ns
                    if m.position_quantity!=q:flags.append('mark_quantity_mismatch')
                    if not clock_known(m.clock,asof,self.anchor) or not 0<=asof-m.clock.mono_ns<=NS:flags.append('mark_receive_stale_or_future')
                    if not -100_000_000<=age<=2*NS:flags.append('mark_source_stale_or_future')
                    if not flags:
                        pnl=(1 if q>0 else -1)*(m.exit_notional-abs(q)*basis);open_pnl+=pnl
                        if m.estimated_exit_fee is None:fees_known=False
                        else:exit_fees+=m.estimated_exit_fee
                if flags:marks_known=False;reasons+=flags
                positions.append({'symbol':s,'quantity_base':str(q),'average_entry':str(basis),
                                  'unrealized_liquidation_pnl':str(pnl) if pnl is not None else None,'reasons':flags})
            if not fees_known:reasons.append('future_exit_fee_unknown')
            known_cash=self.cash[key];cash=known_cash if not pending and not issues else None
            realized=self.price[key]+self.funding[key]-self.fees[key]
            nav=cash+open_pnl-exit_fees if cash is not None and marks_known and fees_known else None
            available=cash-locked if cash is not None else None
            if known_cash<0:reasons.append('negative_known_cash')
            if available is not None and available<0:reasons.append('simulated_collateral_shortfall')
            accounts.append({'venue':key[0],'asset':key[1],'initial_cash':str(initial),'cash':str(cash) if cash is not None else None,
                'known_cash_component':str(known_cash),'realized_price_pnl':str(self.price[key]),'funding_pnl':str(self.funding[key]),
                'fees_paid':str(self.fees[key]),'external_capital_flows':str(self.flows[key]),
                'realized_net_pnl':str(realized) if not pending and not issues else None,'known_realized_net_component':str(realized),
                'unrealized_liquidation_pnl':str(open_pnl) if marks_known else None,
                'estimated_future_exit_fees':str(exit_fees) if marks_known and fees_known else None,
                'execution_drag_diagnostic_not_additive':str(self.drag[key]),'nav':str(nav) if nav is not None else None,
                'nav_state':'known_simulated_liquidation' if nav is not None else 'unknown',
                'model_net_return':str((nav-initial-self.flows[key])/initial) if nav is not None and initial>0 else None,
                'locked_capital':str(locked),'available_capital':str(available) if available is not None else None,
                'capital_basis':'simulated1x entry-notional reservation, not exchange margin availability',
                'positions':positions,'unresolved_events':pending,'reconciliation_required':issues,'reasons':sorted(set(reasons))})
        return {'schema_version':1,'simulation_only':True,'activation_allowed':False,'accounts':accounts,
                'asof_mono_ns':asof,'certified_net_return':None,'prospective_days':0,
                'scope':'simulated linear-futures accounting only; no source/fill/account settlement or profitable strategy certification'}
