"""Observed paper pair lifecycle; never places, cancels or retries an order.

Only explicit per-trade fills change inventory/cash. Requests and acknowledgments
are not fills; cancelling does not cancel already executed quantity. The frozen
linear account supplies money arithmetic. This layer preserves pending orders,
residual exposure and incomplete receipt-to-cash joins across process restarts.
"""
from dataclasses import dataclass,asdict
from decimal import Decimal
import fcntl
import json
import os

from lab.paper_account import PaperAccount,PaperEvent,number,text,_precision
from lab.funding_values import clock_known
from lab.stream_quotes import FrameClock


@dataclass(frozen=True)
class PairPlan:
    pair_id:str
    symbol:str
    assets:tuple[str,str]
    quantity_base:Decimal
    mexc_side:int
    entry_deadline_mono_ns:int
    max_orders_per_leg:int=3

    def __post_init__(self):
        text(self.pair_id);text(self.symbol)
        if len(self.assets)!=2:raise ValueError('separate settlement assets required')
        object.__setattr__(self,'assets',tuple(text(a) for a in self.assets))
        object.__setattr__(self,'quantity_base',number(self.quantity_base,positive=True))
        if type(self.mexc_side) is not int or self.mexc_side not in (-1,1):raise ValueError('explicit paired side required')
        if type(self.entry_deadline_mono_ns) is not int or self.entry_deadline_mono_ns<0:raise ValueError('finite entry deadline required')
        if type(self.max_orders_per_leg) is not int or not 1<=self.max_orders_per_leg<=16:raise ValueError('finite order-attempt limit required')

    def mapping(self):return {**asdict(self),'assets':list(self.assets),'quantity_base':str(self.quantity_base)}


@dataclass(frozen=True)
class PairReceipt:
    receipt_id:str
    leg:int
    order_id:str
    kind:str
    occurred_ns:int
    clock:FrameClock
    source_identity:str
    purpose:str='open'
    quantity_base:Decimal|None=None
    trade_id:str|None=None
    price:Decimal|None=None
    fee:Decimal|None=None
    cumulative_filled_base:Decimal|None=None

    def __post_init__(self):
        for k in ('receipt_id','order_id','source_identity'):text(getattr(self,k))
        if type(self.leg) is not int or self.leg not in (0,1):raise ValueError('ordered MEXC/Lighter leg required')
        if self.kind not in ('submit','ack','fill','cancel_request','cancelled','rejected','gap') or self.purpose not in ('open','close'):
            raise ValueError('explicit lifecycle kind/purpose required')
        if type(self.occurred_ns) is not int or not isinstance(self.clock,FrameClock) or not 0<=self.occurred_ns<=self.clock.utc_ns:
            raise ValueError('separate economic and first-seen clocks required')
        for k in ('quantity_base','price','fee','cumulative_filled_base'):
            v=getattr(self,k)
            if v is not None:object.__setattr__(self,k,number(v,positive=k in ('quantity_base','price'),nonnegative=k not in ('quantity_base','price')))
        if self.kind in ('submit','fill') and self.quantity_base is None:raise ValueError('explicit base quantity required')
        if self.kind=='fill':
            text(self.trade_id)
            if self.price is None:raise ValueError('fill price required')
        elif any(getattr(self,k) is not None for k in ('trade_id','price','fee')):raise ValueError('fill-only financial fields')
        if self.kind not in ('submit','fill') and self.quantity_base is not None:raise ValueError('quantity only belongs to submission/fill')
        if self.kind not in ('cancelled','rejected') and self.cumulative_filled_base is not None:raise ValueError('terminal cumulative quantity only')

    def mapping(self):
        d=asdict(self)
        for k in ('quantity_base','price','fee','cumulative_filled_base'):
            if d[k] is not None:d[k]=str(d[k])
        return d

    @classmethod
    def from_mapping(cls,payload):
        if not isinstance(payload,dict) or set(payload)-set(cls.__dataclass_fields__):raise ValueError('unsupported receipt fields')
        d=dict(payload);d['clock']=FrameClock(**d['clock']);return cls(**d)


class PairedAccount:
    """Single-writer receipt coordinator around an existing paper account.

    The supplied account must be dedicated to this pair. This is an offline
    accounting interface, not provider authentication or an order connector.
    """
    def __init__(self,account,plan):
        if not isinstance(account,PaperAccount) or not isinstance(plan,PairPlan):raise ValueError('typed account/plan required')
        if any((v,a) not in account.initial for v,a in zip(('mexc','lighter'),plan.assets)):raise ValueError('both segregated accounts required')
        self.account,self.plan=account,plan;self.lease=None;self.closed=False
        try:
            if account.journal_path is not None:
                path=account.journal_path.with_suffix('.pair-writer.lock')
                fd=os.open(path,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
                self.lease=os.fdopen(fd,'a+')
                fcntl.flock(self.lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
                # Refresh from the durable account before inspecting ownership.
                account.snapshot(max(account.last_asof,account.anchor.mono_ns))
            configs=[e['payload'] for e in account.evidence if e['namespace']=='recovery' and e['payload'].get('component')=='paired_execution_plan']
            if configs and any(e['plan']!=plan.mapping() for e in configs):raise ValueError('pair scope/quantity/deadline cannot reset')
            if not configs:account.record_evidence('recovery',{'component':'paired_execution_plan','plan':plan.mapping()})
            if any(not e.event_id.startswith(self.prefix) for e in account.accepted_events):raise ValueError('dedicated pair account required')
            self._rebuild()
        except BaseException:
            self.close();raise

    @property
    def prefix(self):return 'pair:'+self.plan.pair_id+':'

    def _rebuild(self):
        self.orders={};self.seen={};self.trades={};self.issues=set();self.last_asof=-1
        for item in self.account.evidence:
            p=item['payload']
            if item['namespace']=='recovery' and p.get('component')=='paired_execution_receipt':
                if p['pair_id']!=self.plan.pair_id:raise ValueError('foreign pair receipt in account')
                self._apply(PairReceipt.from_mapping(p['receipt']),p['asof_mono_ns'])

    @_precision
    def _apply(self,r,asof):
        economic=r.mapping();economic.pop('clock')
        sig=json.dumps(economic,sort_keys=True);status='applied';flags=[]
        if asof<self.last_asof or not clock_known(r.clock,asof,self.account.anchor):flags.append('receipt_future_clock_step_or_asof_regression')
        if r.receipt_id in self.seen:
            status='duplicate' if self.seen[r.receipt_id]==sig else 'conflict'
            if status=='conflict':flags.append('receipt_identity_conflict')
        elif flags:status='rejected'
        else:
            self.seen[r.receipt_id]=sig;key=r.leg,r.order_id;o=self.orders.get(key)
            if r.kind=='gap':flags.append('source_gap_requires_reconciliation')
            elif r.kind=='submit':
                n=sum(o['leg']==r.leg for o in self.orders.values())
                if o is not None:flags.append('order_id_reused')
                if n>=self.plan.max_orders_per_leg:flags.append('order_attempt_budget_exhausted')
                if r.purpose=='open':
                    remaining=self.plan.quantity_base-self.open_filled(r.leg)
                    if asof>self.plan.entry_deadline_mono_ns:flags.append('entry_deadline_passed')
                    if any(x['purpose']=='close' for x in self.orders.values()):flags.append('new_entry_after_exit_intent')
                else:remaining=abs(self.position(r.leg))
                if r.quantity_base>remaining:flags.append('order_exceeds_residual_quantity')
                if any(x['leg']==r.leg and not self.terminal_known(x) for x in self.orders.values()):flags.append('previous_order_or_fills_unresolved')
                if not flags:self.orders[key]={'leg':r.leg,'id':r.order_id,'purpose':r.purpose,
                    'requested':r.quantity_base,'filled':Decimal(0),'stage':'submitted','terminal':False,
                    'reported_final':None,'terminal_ns':None,'cancel_requested':False}
            elif o is None:flags.append('order_without_submission')
            elif o['purpose']!=r.purpose:flags.append('order_purpose_mismatch')
            elif r.kind=='fill':
                trade_key=r.leg,r.trade_id
                prior=self.trades.get(trade_key)
                identity=(r.order_id,r.purpose,r.quantity_base,r.price,r.fee,r.occurred_ns,r.source_identity)
                if prior:
                    if prior[0]==identity:status='duplicate_trade'
                    else:flags.append('trade_identity_conflict')
                else:
                    # Preserve overfills and terminal-time contradictions as
                    # exposure; never silently discard an adverse source fill.
                    self.trades[trade_key]=(identity,r)
                    o['filled']+=r.quantity_base
                    if o['filled']>o['requested']:flags.append('reported_fill_exceeds_order')
                    if o['terminal_ns'] is not None and r.occurred_ns>o['terminal_ns']:flags.append('fill_economic_time_after_terminal')
                    if o['filled']==o['requested'] and not o['terminal']:
                        o['terminal']=True;o['reported_final']=o['filled'];o['stage']='filled';o['terminal_ns']=r.occurred_ns
            elif r.kind in ('cancelled','rejected'):
                if o['terminal'] and o['reported_final'] is not None and r.cumulative_filled_base!=o['reported_final']:
                    flags.append('conflicting_terminal_quantity')
                o.update(terminal=True,reported_final=r.cumulative_filled_base,terminal_ns=r.occurred_ns,stage=r.kind)
                if r.cumulative_filled_base is not None and r.cumulative_filled_base>o['requested']:flags.append('terminal_total_exceeds_order')
            elif r.kind=='cancel_request':o['cancel_requested']=True
            elif not o['terminal']:o['stage']='acknowledged'
        if flags:
            self.issues.update(flags)
            if status=='applied' and r.kind!='fill':status='rejected'
        self.last_asof=max(self.last_asof,asof)
        return {'receipt_id':r.receipt_id,'status':status,'reasons':flags}

    @staticmethod
    def terminal_known(o):return o['terminal'] and o['reported_final'] is not None and o['reported_final']==o['filled']

    @_precision
    def open_filled(self,leg):return sum((r.quantity_base for _,r in self.trades.values() if r.leg==leg and r.purpose=='open'),Decimal(0))

    @_precision
    def position(self,leg):
        side=self.plan.mexc_side if leg==0 else -self.plan.mexc_side
        return sum((r.quantity_base*side*(1 if r.purpose=='open' else -1) for _,r in self.trades.values() if r.leg==leg),Decimal(0))

    def financial_event(self,r):
        venue=('mexc','lighter')[r.leg];side=self.plan.mexc_side if r.leg==0 else -self.plan.mexc_side
        return PaperEvent(self.prefix+venue+':'+r.trade_id,'fill',venue,self.plan.assets[r.leg],self.plan.symbol,
                          r.occurred_ns,r.clock,r.source_identity,quantity=r.quantity_base*side*(1 if r.purpose=='open' else -1),price=r.price,fee=r.fee)

    def post(self,receipt,asof):
        if self.closed:raise ValueError('pair coordinator closed')
        if not isinstance(receipt,PairReceipt) or type(asof) is not int or asof<0:raise ValueError('typed receipt/as-of required')
        self.account.snapshot(max(asof,self.account.last_asof));self._rebuild()
        result=self._apply(receipt,asof)
        # A crash after this durable record leaves a visible unapplied fill,
        # not a falsely complete cash account. Replaying the same stable trade
        # can join it later; the original economic/receipt clocks stay intact.
        self.account.record_evidence('recovery',{'component':'paired_execution_receipt','pair_id':self.plan.pair_id,
              'receipt':receipt.mapping(),'asof_mono_ns':asof})
        original=self.trades.get((receipt.leg,receipt.trade_id)) if receipt.kind=='fill' else None
        if original and result['status'] in ('applied','duplicate','duplicate_trade'):
            result['financial_post']=self.account.post(self.financial_event(original[1]),asof)
        return result

    @_precision
    def snapshot(self,asof,marks=()):
        if self.closed:raise ValueError('pair coordinator closed')
        report=self.account.snapshot(asof,marks);self._rebuild()
        if asof<self.last_asof:raise ValueError('cannot backdate pair state')
        expected={self.financial_event(r).event_id for _,r in self.trades.values()}
        applied={e.event_id for e in self.account.accepted_events}
        missing=sorted(expected-applied)
        flags=set(self.issues)
        if missing:flags.add('fill_receipt_not_joined_to_financial_journal')
        unresolved=[o for o in self.orders.values() if o['terminal'] and not self.terminal_known(o)]
        if unresolved:flags.add('terminal_fill_total_missing_or_unreconciled')
        q=[self.position(i) for i in (0,1)];delta=sum(q);lo=hi=delta
        pending=[o for o in self.orders.values() if not self.terminal_known(o)]
        for o in pending:
            amount=max(Decimal(0),o['requested']-o['filled'])
            side=self.plan.mexc_side if o['leg']==0 else -self.plan.mexc_side
            change=amount*side*(1 if o['purpose']=='open' else -1)
            lo+=min(Decimal(0),change);hi+=max(Decimal(0),change)
        if flags:
            for a in report['accounts']:
                for name in ('cash','realized_net_pnl','nav','model_net_return','available_capital'):a[name]=None
                a['nav_state']='unknown';a['reasons'].append('pair_receipts_require_reconciliation')
        money_unknown=any(a['cash'] is None for a in report['accounts'])
        state=('unknown' if flags else 'pending_orders' if pending else 'exposed' if delta else
               'hedged' if q[0] else 'flat' if self.orders else 'inactive')
        suggestions=[]
        for leg in (0,1):
            known=not flags and not any(o['leg']==leg and not self.terminal_known(o) for o in self.orders.values())
            remaining=max(Decimal(0),self.plan.quantity_base-self.open_filled(leg))
            entry=known and asof<=self.plan.entry_deadline_mono_ns and not any(o['purpose']=='close' for o in self.orders.values())
            suggestions.append({'leg':leg,'remaining_entry_base':str(remaining) if known else None,
                'new_entry_model_allowed':entry and remaining>0 and sum(o['leg']==leg for o in self.orders.values())<self.plan.max_orders_per_leg,
                'observed_position_to_reduce_base':str(abs(q[leg])),'actual_order_allowed':False})
        report.update(pair={'pair_id':self.plan.pair_id,'state':state,'positions_base':list(map(str,q)) if not flags else [None,None],
            'net_delta_base':str(delta) if not flags else None,'possible_delta_base':[str(lo),str(hi)] if not flags else [None,None],
            'known_received_positions_base':list(map(str,q)),'known_received_delta_base':str(delta),
            'all_order_totals_reconciled':not pending and not flags,'paired_target_fully_filled':q==[self.plan.quantity_base*self.plan.mexc_side,-self.plan.quantity_base*self.plan.mexc_side] and not pending and not flags,
            'terminal_cash_known':state=='flat' and not money_unknown,'unapplied_fill_ids':missing,
            'reasons':sorted(flags),'orders':[{k:str(v) if isinstance(v,Decimal) else v for k,v in o.items()} for o in self.orders.values()],
            'recovery_quantities':suggestions,'execution_ready':False,'source_reports_authenticated':False},
            scope='supplied paper pair receipts and linear account only; no source/fill/order authentication or strategy activation')
        return report

    def close(self):
        if self.lease is not None:
            fcntl.flock(self.lease,fcntl.LOCK_UN);self.lease.close();self.lease=None
        self.closed=True

    def __enter__(self):return self
    def __exit__(self,*args):self.close()
