"""Persistent paper-only entry/data/loss/concentration controls.

Controls stop new model entries and retain exposure; they never invent a close,
place orders, certify a strategy or aggregate different settlement currencies.
Forecast error must be in settlement quote, not variance or a mislabeled percent.
"""
from dataclasses import dataclass,asdict
from decimal import Decimal

from lab.acquisition_budget import _locked,_read_records,_append_record
from lab.paper_account import number,text,_precision
from lab.stream_quotes import FrameClock
from lab.funding_values import clock_known


@dataclass(frozen=True)
class RiskPolicy:
    policy_id:str
    max_loss_fraction:Decimal=Decimal('.03')
    max_drawdown_fraction:Decimal=Decimal('.02')
    max_venue_gross_fraction:Decimal=Decimal('1')
    max_symbol_gross_fraction:Decimal=Decimal('.25')
    max_receive_age_ns:int=1_000_000_000

    def __post_init__(self):
        text(self.policy_id)
        for k in ('max_loss_fraction','max_drawdown_fraction','max_venue_gross_fraction','max_symbol_gross_fraction'):
            x=number(getattr(self,k),positive=True)
            if x>1:raise ValueError('unlevered fractional risk limit required')
            object.__setattr__(self,k,x)
        if type(self.max_receive_age_ns) is not int or self.max_receive_age_ns<=0:raise ValueError('positive receive-age limit required')

    def mapping(self):return {k:str(v) if isinstance(v,Decimal) else v for k,v in asdict(self).items()}


@_precision
def entry_threshold(expected_gross_quote,cost_quote,error_bound_quote,*,asset,cost_multiple=1,
                    error_calibrated=False,prediction_unit='settlement_quote',extra_reserve_quote=0):
    """Gross forecast minus all costs and a measured uncertainty allowance.

    Output is conditional model arithmetic; no caller flag can authorize real
    orders or confer market validation. Missing uncertainty is never zero.
    """
    text(asset)
    if type(cost_multiple) is not int or cost_multiple not in (1,2,3):raise ValueError('fixed1x/2x/3x tier required')
    result={'state':'unknown','expected_net_lower_quote':None,'required_gross_quote':None,'asset':asset,
            'cost_multiple':cost_multiple,'model_entry_allowed':False,'actual_order_allowed':False,'reasons':[]}
    if prediction_unit!='settlement_quote':result['reasons'].append('forecast_unit_is_not_profit_in_settlement_quote')
    if error_calibrated is not True:result['reasons'].append('forecast_error_not_calibrated')
    if any(x is None for x in (expected_gross_quote,cost_quote,error_bound_quote,extra_reserve_quote)):
        result['reasons'].append('forecast_cost_error_or_reserve_unknown')
    if result['reasons']:return result
    gross=number(expected_gross_quote);cost=number(cost_quote,nonnegative=True)
    error=number(error_bound_quote,nonnegative=True);reserve=number(extra_reserve_quote,nonnegative=True)
    required=cost_multiple*(cost+reserve)+error;lower=gross-required
    return {**result,'state':'conditional_pass' if lower>0 else 'negative',
            'required_gross_quote':str(required),'expected_net_lower_quote':str(lower),
            'model_entry_allowed':lower>0,'reasons':['conditional_supplied_forecast_not_market_validation']}


class PaperRisk:
    """Hash-chained risk state. Reopening cannot reset a loss/high-water stop."""
    def __init__(self,path,policy,anchor,*,contract_version,initial_balances):
        if not isinstance(policy,RiskPolicy) or not isinstance(anchor,FrameClock):raise ValueError('typed risk policy/anchor required')
        self.path,self.policy,self.anchor=path,policy,anchor
        self.contract_version=text(contract_version)
        self.initial={(text(v),text(a)):number(x,positive=True) for (v,a),x in initial_balances.items()}
        if not self.initial:raise ValueError('registered separate account balances required')
        self.header={'kind':'paper_risk_policy','policy':policy.mapping(),'anchor':asdict(anchor),
            'contract_version':self.contract_version,'initial_balances':[
                {'venue':v,'asset':a,'cash':str(x)} for (v,a),x in sorted(self.initial.items())]}
        with _locked(path) as handle:
            rows=_read_records(handle)
            if not rows:_append_record(handle,rows,self.header)
            if rows[0]['event']!=self.header:raise ValueError('risk policy/anchor cannot reset')
            self._state(rows)

    def _state(self,rows):
        peaks={};stops=set();last=-1;initial={}
        for row in rows[1:]:
            e=row['event']
            if e.get('kind')!='paper_risk_observation' or e['asof_mono_ns']<last:raise ValueError('invalid/regressed risk journal')
            last=e['asof_mono_ns'];stops.update(e['new_stops'])
            for a in e['accounts']:
                key=a['venue'],a['asset'];base=number(a['initial_cash'],positive=True)
                if key in initial and initial[key]!=base:raise ValueError('risk capital baseline drift')
                initial[key]=base
                if a['net_pnl'] is not None:peaks[key]=max(peaks.get(key,Decimal(0)),number(a['net_pnl']))
        return peaks,stops,last,initial

    @_precision
    def observe(self,snapshot,*,asof,clock,complete,session_open,fee_inputs_known,
                contract_version,expected_contract_version,mode='historical'):
        if type(asof) is not int or asof<0 or not isinstance(clock,FrameClock):raise ValueError('explicit as-of/first-seen clocks required')
        if mode not in ('historical','prospective','fixture'):raise ValueError('explicit evidence mode required')
        if snapshot.get('simulation_only') is not True or snapshot.get('activation_allowed') is not False:raise ValueError('paper-only snapshot required')
        records=snapshot.get('accounts')
        if not isinstance(records,list) or not records:raise ValueError('explicit separate accounts required')
        if len({(a.get('venue'),a.get('asset')) for a in records})!=len(records):raise ValueError('duplicate account identity')
        flags=set()
        if any(x is not True for x in (complete,session_open,fee_inputs_known)):flags.add('data:complete_session_fee_inputs_required')
        if mode=='historical':flags.add('data:historical_capture_is_not_live')
        if not clock_known(clock,asof,self.anchor) or not 0<=asof-clock.mono_ns<=self.policy.max_receive_age_ns:
            flags.add('data:stale_future_or_stepped_clock')
        if contract_version!=self.contract_version or expected_contract_version!=self.contract_version:
            flags.add('data:contract_rules_missing_or_changed')
        lookup={(a.get('venue'),a.get('asset')):a for a in records}
        if set(lookup)!=set(self.initial):flags.add('data:registered_account_set_incomplete_or_changed')
        if snapshot.get('asof_mono_ns')!=asof:flags.add('data:snapshot_asof_mismatch')
        pair=snapshot.get('pair')
        if pair and (pair.get('state') in ('unknown','pending_orders') or pair.get('net_delta_base') is None):
            flags.add('risk:pair_exposure_or_orders_unreconciled')
        with _locked(self.path) as handle:
            rows=_read_records(handle)
            if rows[0]['event']!=self.header:raise ValueError('risk header drift')
            peaks,old_stops,last,initial=self._state(rows)
            if asof<last:raise ValueError('risk as-of cannot regress')
            accounts=[]
            for key,registered_base in sorted(self.initial.items()):
                a=lookup.get(key)
                if a is None:
                    accounts.append({'venue':key[0],'asset':key[1],'initial_cash':str(registered_base),'net_pnl':None,
                        'gross_notional':None,'known_gross_component':'0','gross_notional_complete':False,'symbol_gross':{}})
                    continue
                base=number(a['initial_cash'],positive=True)
                if base!=registered_base:raise ValueError('registered capital baseline drift')
                if key in initial and base!=initial[key]:raise ValueError('risk baseline cannot change after deposit')
                nav=a.get('nav');flows=a.get('external_capital_flows');net=None;gross=Decimal(0);symbol_gross={}
                if nav is None or flows is None:flags.add('data:net_equity_or_external_flows_unknown')
                else:
                    net=number(nav)-base-number(flows)
                    peak=max(peaks.get(key,Decimal(0)),net)
                    if -net>=base*self.policy.max_loss_fraction:flags.add('risk:loss_limit')
                    if peak-net>=base*self.policy.max_drawdown_fraction:flags.add('risk:drawdown_limit')
                positions=a.get('positions');gross_complete=isinstance(positions,list)
                if not gross_complete:
                    flags.add('data:positions_unknown');positions=[]
                for p in positions:
                    q=number(p['quantity_base']);entry=abs(q)*number(p['average_entry'],nonnegative=True)
                    if not q:continue
                    pnl=p.get('unrealized_liquidation_pnl')
                    if pnl is None:flags.add('data:position_liquidation_mark_unknown');gross_complete=False;continue
                    close_notional=entry+(1 if q>0 else -1)*number(pnl)
                    if close_notional<0:flags.add('data:invalid_liquidation_notional');gross_complete=False;continue
                    amount=max(entry,close_notional);gross+=amount
                    symbol=text(p['symbol']);symbol_gross[symbol]=symbol_gross.get(symbol,Decimal(0))+amount
                if gross>base*self.policy.max_venue_gross_fraction:flags.add('risk:venue_gross_limit')
                if any(x>base*self.policy.max_symbol_gross_fraction for x in symbol_gross.values()):flags.add('risk:symbol_concentration_limit')
                accounts.append({'venue':key[0],'asset':key[1],'initial_cash':str(base),'net_pnl':None if net is None else str(net),
                    'gross_notional':str(gross) if gross_complete else None,'known_gross_component':str(gross),'gross_notional_complete':gross_complete,
                    'symbol_gross':{k:str(v) for k,v in symbol_gross.items()}})
            event={'kind':'paper_risk_observation','asof_mono_ns':asof,'clock':asdict(clock),
                   'accounts':accounts,'new_stops':sorted(flags),'mode':mode}
            _append_record(handle,rows,event);stops=old_stops|flags
        return {'state':'HALTED' if stops else 'MODEL_WITHIN_LIMITS','model_new_entries_allowed':not stops,
                'actual_order_allowed':False,'automatic_flatten_performed':False,'positions_retained':True,
                'stops':sorted(stops),'new_stops':sorted(flags),'accounts':accounts,
                'scope':'paper risk controls only; supplied marks/fees/clock completeness are not authenticated execution evidence'}
