"""Current-capital veto around frozen paper risk controls; no real activation.

Historical ledgers/engines stay unchanged. New callers must use the wrapper;
this does not retrofit old runners or establish exchange margin availability.
"""
from copy import deepcopy

from lab.paper_account import number,text,_precision
from lab.paper_controls import PaperRisk

CAPITAL_BASIS='simulated1x entry-notional reservation, not exchange margin availability'


@_precision
def capital_status(snapshot,required_reserves=None,*,expected_accounts=None):
    """A read-only capacity component. It can veto but cannot admit entries alone.

    Reserves are quote amounts keyed by (venue, asset), with no cross-account
    netting. Unknown balances/marks/reconciliation never become free capital.
    """
    if (not isinstance(snapshot,dict) or type(snapshot.get('schema_version')) is not int or snapshot['schema_version']!=1
            or snapshot.get('simulation_only') is not True or snapshot.get('activation_allowed') is not False
            or type(snapshot.get('asof_mono_ns')) is not int or snapshot['asof_mono_ns']<0):
        raise ValueError('typed current paper snapshot required')
    records=snapshot.get('accounts')
    if not isinstance(records,list) or not records or any(not isinstance(a,dict) for a in records):
        raise ValueError('explicit separate paper accounts required')
    keys=[(text(a.get('venue')),text(a.get('asset'))) for a in records]
    if len(set(keys))!=len(keys): raise ValueError('duplicate paper account')
    if required_reserves is not None and not isinstance(required_reserves,dict):
        raise ValueError('explicit per-account reserve mapping required')
    required={}
    for key,value in ({} if required_reserves is None else required_reserves).items():
        if not isinstance(key,tuple) or len(key)!=2: raise ValueError('venue/asset reserve key required')
        key=(text(key[0]),text(key[1]))
        if key not in keys: raise ValueError('reserve names an absent account')
        required[key]=number(value,nonnegative=True)
    global_reasons=[]
    if expected_accounts is not None and set(keys)!=set(expected_accounts):
        global_reasons.append('registered_account_set_incomplete_or_changed')
    accounts=[]
    for key,a in zip(keys,records):
        reasons=[];unknown=[];values={}
        for field in ('cash','nav','locked_capital','available_capital'):
            if a.get(field) is None: unknown.append(field+'_unknown');values[field]=None
            else: values[field]=number(a[field],nonnegative=field=='locked_capital')
        for field in ('reasons','unresolved_events','reconciliation_required','positions'):
            if not isinstance(a.get(field),list): unknown.append(field+'_unknown')
            elif field!='positions' and a[field]: reasons.append(field+'_not_clear')
        if a.get('nav_state')!='known_simulated_liquidation': unknown.append('liquidation_nav_not_known')
        if a.get('capital_basis')!=CAPITAL_BASIS: unknown.append('capital_basis_not_supported')
        cash,nav,locked,available=(values[k] for k in ('cash','nav','locked_capital','available_capital'))
        if cash is not None and cash<0: reasons.append('negative_cash')
        if nav is not None and nav<=0: reasons.append('nonpositive_nav')
        if available is not None and available<=0: reasons.append('no_free_simulated_capital')
        if all(x is not None for x in (cash,locked,available)) and available!=cash-locked:
            reasons.append('available_capital_identity_mismatch')
        reserve=required.get(key,number(0))
        if available is not None and available<reserve: reasons.append('proposed_reserve_exceeds_available_capital')
        state='BLOCKED' if reasons else 'UNKNOWN' if unknown else 'AVAILABLE'
        accounts.append(dict(venue=key[0],asset=key[1],state=state,
            available_capital=None if available is None else str(available),required_reserve=str(reserve),
            reasons=sorted(set(reasons)),unknown=sorted(set(unknown))))
    state=('BLOCKED' if global_reasons or any(a['state']=='BLOCKED' for a in accounts) else
           'UNKNOWN' if any(a['state']=='UNKNOWN' for a in accounts) else 'AVAILABLE')
    return dict(state=state,capacity_available=True if state=='AVAILABLE' else None if state=='UNKNOWN' else False,
                asof_mono_ns=snapshot['asof_mono_ns'],accounts=accounts,reasons=global_reasons,
                model_new_entries_allowed=False,actual_order_allowed=False,activation_allowed=False,
                scope='capacity component only; no risk, forecast, execution or real-order admission')


class PaperSolvencyGuard:
    """Observe the same copied snapshot through legacy risk and current capacity.

    Legacy persistent loss/drawdown stops are retained. Capacity is rechecked
    each observation; restoring simulated capital does not clear legacy stops.
    No orders, closes or capital events are produced by this wrapper.
    """
    def __init__(self,risk):
        if not isinstance(risk,PaperRisk): raise ValueError('typed PaperRisk required')
        self.risk=risk

    def observe(self,snapshot,*,required_reserves=None,**kwargs):
        current=deepcopy(snapshot)
        capacity=capital_status(current,required_reserves,expected_accounts=self.risk.initial)
        legacy=self.risk.observe(current,**kwargs)
        allowed=legacy.get('model_new_entries_allowed') is True and capacity['capacity_available'] is True
        state=(legacy['state'] if legacy.get('model_new_entries_allowed') is not True else
               'MODEL_WITHIN_LIMITS' if allowed else 'CAPITAL_'+capacity['state'])
        return dict(state=state,model_new_entries_allowed=allowed,actual_order_allowed=False,
                    activation_allowed=False,positions_retained=True,automatic_flatten_performed=False,
                    asof_mono_ns=current['asof_mono_ns'],capital=capacity,legacy_risk=legacy,
                    scope='conditional paper-entry veto; simulated capital is not exchange margin or market validation')
