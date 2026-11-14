"""Independent Decimal oracle for linear simulated-account integration.

Standard library only, no production accounting/replay imports and no network.
Artifact arithmetic uses reported accepted inputs, not an independent market
decoder. The original oracle was written by the independent financial reviewer;
the root integration added the artifact adapter and remains responsible for it.
Only already accepted MODEL postings belong in this oracle; it does not attest
source/fee/session/fill validity or confer prospective/actual-money eligibility.
"""
from decimal import Decimal as D


def amount(value):
    if isinstance(value, bool):
        raise ValueError('boolean is not an accounting quantity')
    x=D(str(value))
    if not x.is_finite():
        raise ValueError('finite accounting quantity required')
    return x


def close(actual,expected,label,tolerance=D('1e-18')):
    if actual is None or abs(amount(actual)-amount(expected))>tolerance:
        raise AssertionError(label+': accounting mismatch')


class LinearOracle:
    """Single venue/asset, accepted signed base fills, no full-notional cash flow."""
    def __init__(self,venue,asset,initial_cash):
        self.venue,self.asset=venue,asset
        self.initial=amount(initial_cash)
        self.realized,self.funding,self.fees=D(0),D(0),D(0)
        self.positions={}

    @property
    def cash(self):
        return self.initial+self.realized+self.funding-self.fees

    def fill(self,symbol,delta,price,fee):
        delta,price,fee=map(amount,(delta,price,fee))
        if delta==0 or price<=0 or fee<0:
            raise ValueError('nonzero signed base, positive price, nonnegative fee required')
        old,basis=self.positions.get(symbol,(D(0),D(0)))
        new=old+delta
        if old==0:
            new_basis=price
        elif old*delta>0:
            new_basis=(abs(old)*basis+abs(delta)*price)/abs(new)
        else:
            closed=min(abs(old),abs(delta))
            self.realized+=closed*(price-basis)*(1 if old>0 else -1)
            new_basis=(D(0) if new==0 else basis if old*new>0 else price)
        self.fees+=fee
        if new==0:self.positions.pop(symbol,None)
        else:self.positions[symbol]=(new,new_basis)

    def funding_post(self,value,asset):
        if asset!=self.asset:
            raise ValueError('funding cannot relabel or convert assets')
        self.funding+=amount(value)

    def fee_post(self,value,asset):
        if asset!=self.asset:
            raise ValueError('fee cannot relabel or convert assets')
        value=amount(value)
        if value<0:raise ValueError('nonnegative model fee required')
        self.fees+=value

    def unrealized(self,marks):
        total=D(0)
        for symbol,(q,basis) in self.positions.items():
            value=marks.get(symbol)
            if value is None:return None
            value=amount(value)
            if value<=0:raise ValueError('positive liquidation-price mark required')
            total+=q*(value-basis)
        return total

    def snapshot(self,marks):
        unrealized=self.unrealized(marks)
        return {'initial_cash':self.initial,'cash':self.cash,
                'realized_price_pnl':self.realized,'funding_pnl':self.funding,
                'fees_paid':self.fees,'realized_net_pnl':self.realized+self.funding-self.fees,
                'unrealized_liquidation_pnl':unrealized,
                'nav':None if unrealized is None else self.cash+unrealized}


def self_test():
    x=LinearOracle('mexc','USDT',1000)
    x.fill('BTC',2,100,1)
    close(x.cash,999,'opening collateral, not spot purchase')
    x.fill('BTC',2,110,'.5')
    close(x.positions['BTC'][1],105,'weighted entry basis')
    x.fill('BTC',-1,120,'.2')
    close(x.realized,15,'partial close')
    x.fill('BTC',-5,90,'.3')
    if x.positions['BTC']!=(D(-2),D(90)):
        raise AssertionError('reversal residual basis')
    close(x.realized,-30,'close old portion of reversal')
    close(x.snapshot({'BTC':94})['unrealized_liquidation_pnl'],-8,'short ask mark')
    if x.snapshot({})['nav'] is not None:
        raise AssertionError('missing mark cannot create known equity')
    x.fill('BTC',2,80,'.1');x.funding_post(3,'USDT')
    close(x.realized,-10,'closed trade conservation')
    close(x.cash,'990.9','price plus funding minus fees once')
    close(x.snapshot({})['nav'],'990.9','flat account needs no market mark')
    if x.positions:raise AssertionError('flat residual')
    try:x.fee_post(1,'USDC')
    except ValueError:pass
    else:raise AssertionError('asset relabelling')
    return {'self_test':'passed','scope':'invented accepted linear-model postings only',
            'production_imports':False,'network':False}


def check_case(case):
    accounts={(x['venue'],x['asset']):x for x in case['snapshot']['accounts']}
    models={k:LinearOracle(*k,x['initial_cash']) for k,x in accounts.items()}
    pending={};incomplete=set();seen=set()
    if len(case['events'])!=len(case['attempts']):raise AssertionError('attempt inventory mismatch')
    for e,attempt in zip(case['events'],case['attempts']):
        key=e['venue'],e['asset'];ident=e['event_id'];state=attempt['status']
        if state in ('rejected','conflicting_revision'):
            if state=='conflicting_revision' or 'late_fill_order_requires_reconciliation' in attempt['reasons']:incomplete.add(key)
            continue
        if state=='duplicate':
            if ident not in seen:raise AssertionError('duplicate without original')
            continue
        if state!='applied' or ident in seen:raise AssertionError('event state/id mismatch')
        seen.add(ident);m=models[key]
        if e['kind']=='fill':
            fee=e['fee']
            m.fill(e['symbol'],e['quantity'],e['price'],0 if fee is None else fee)
            if fee is None:pending[ident]=(key,'fee')
        elif e['kind']=='funding':
            if e['amount'] is None:pending[ident]=(key,'funding')
            else:m.funding_post(e['amount'],e['asset'])
        elif e['kind'] in ('fee_resolution','funding_resolution'):
            old=pending.pop(e['resolves'])
            if old!=(key,'fee' if e['kind']=='fee_resolution' else 'funding'):raise AssertionError('resolution identity')
            if old[1]=='fee':m.fee_post(e['amount'],e['asset'])
            else:m.funding_post(e['amount'],e['asset'])
        else:raise AssertionError('unregistered fixture event kind')
    for key,m in models.items():
        x=accounts[key];unknown=key in incomplete or any(k==key for k,_ in pending.values())
        close(x['known_cash_component'],m.cash,'cash conservation')
        close(x['realized_price_pnl'],m.realized,'realized price')
        close(x['fees_paid'],m.fees,'fees once');close(x['funding_pnl'],m.funding,'funding once')
        if unknown:
            if x['cash'] is not None or x['realized_net_pnl'] is not None or x['nav'] is not None:
                raise AssertionError('unknown financial event became known cash/NAV')
        else:
            close(x['cash'],m.cash,'complete cash');close(x['realized_net_pnl'],m.cash-m.initial,'net decomposition')
        marks={};exit_fee=D(0);complete=True
        for symbol,(q,basis) in m.positions.items():
            mark=next((z for z in case.get('marks',[]) if (z['venue'],z['asset'],z['symbol'])==(*key,symbol)),None)
            if mark is None:complete=False;continue
            close(mark['position_quantity'],q,'close mark quantity')
            marks[symbol]=amount(mark['exit_notional'])/abs(q)
            if mark['estimated_exit_fee'] is None:complete=False
            else:exit_fee+=amount(mark['estimated_exit_fee'])
        unreal=m.unrealized(marks)
        if unreal is None:
            if x['unrealized_liquidation_pnl'] is not None:raise AssertionError('missing mark erased open risk')
        else:close(x['unrealized_liquidation_pnl'],unreal,'side-aware open PnL')
        if complete and not unknown:close(x['nav'],m.cash+unreal-exit_fee,'liquidation net NAV')
        elif x['nav'] is not None:raise AssertionError('incomplete liquidation equity')
        locked=sum(abs(q)*basis for q,basis in m.positions.values())
        close(x['locked_capital'],locked,'segregated1x collateral reservation')
    return len(models)


def check_artifact(path):
    import gzip,json
    from pathlib import Path
    path=Path(path);report=json.loads(path.read_text());self_test()
    if report['activation_allowed'] is not False or report['prospective_days']!=0 or report['predictive_trials']!=0:
        raise AssertionError('engine diagnostics promoted to strategy evidence')
    accounts=sum(check_case(c) for c in report['engine_cases'])
    f=report['funding_integration']
    mx=next(x for x in f['resolved_snapshot']['accounts'] if x['venue']=='mexc')
    # Independent linear units, including percent->fraction. Exposure is derived
    # from the account's actual accepted synthetic opening fill, not invented
    # as a second unrelated quantity by this adapter.
    opening=f['events'][0];q=amount(opening['quantity'])
    expected=-q*D(30000)*D('.01')/100
    close(f['bound_model']['cash_delta'],expected,'linear event notional')
    close(mx['funding_pnl'],expected,'funding resolution conservation')
    if f['actual_event_index_proof_acquired'] or f['lighter_declared_basis_only']['source_bridge_verified']:
        raise AssertionError('caller-supplied index is not proof')
    fee=report['fee_integration'];x=fee['linked_snapshot']['accounts'][0]
    close(x['cash'],D(5000)-10-D('0.19'),'fee statement to account')
    if fee['regular']['account_effective_fee_verified'] or fee['missing']['rate_fraction'] is not None:
        raise AssertionError('unsigned or missing fees became actual')
    op=report['operations_integration']
    if op['budget_duplicate_after_restart']['dispatch_allowed'] or not op['budget_final']['new_dispatch_blocked']:
        raise AssertionError('budget reset or exhausted grant allowed')
    if op['historical_accumulated']['requests_charged']!=7757 or op['historical_accumulated']['remaining_body_bytes'] is not None:
        raise AssertionError('historical allowance reset or rounded byte invention')
    if op['reopen_requires_new_transport']['state']!='invalid':raise AssertionError('old transport resumed')
    rows=[json.loads(line) for line in gzip.decompress((path.parent/'observations.jsonl.gz').read_bytes()).splitlines()]
    if len(rows)!=72:raise AssertionError('held deadline inventory')
    costs=stresses=unknown_links=0;maxdiff=D(0)
    for row in rows:
        if row['execution_ready'] or row['readiness']['execution_ready']:raise AssertionError('diagnostic activated')
        if len(row['sizes'])!=6:raise AssertionError('size inventory')
        for size in row['sizes']:
            cost=size['cost']
            if not cost or not cost['displayed_fillable']:continue
            fills=list(map(amount,size['observed_quantity']['current_buy_sell_quote']))
            crossing=fills[0]-fills[1]+fills[2]-fills[3]
            fees=(fills[0]+fills[1])/1000+(fills[2]+fills[3])*D(4)/10000
            expected=crossing+fees
            for field,value in (('crossing_usd',crossing),('fee_usd',fees)):
                maxdiff=max(maxdiff,abs(amount(cost[field])-value));close(cost[field],value,field,D('1e-8'))
            if [s['multiple'] for s in cost['scenarios']]!=[1,2,3]:raise AssertionError('stress inventory')
            for stress in cost['scenarios']:
                wanted=stress['multiple']*expected
                maxdiff=max(maxdiff,abs(amount(stress['round_trip_cost_usd'])-wanted))
                close(stress['round_trip_cost_usd'],wanted,'1x/2x/3x unchanged cost',D('1e-8'));stresses+=1
            if size['capital_total_quote_equivalent']!='10000' or size['capital_per_venue_quote_equivalent']!='5000':
                raise AssertionError('capital denominator drift')
            costs+=1
        link=row['counterfactual_account_linkage']
        if link:
            if any(a['nav'] is not None or a['realized_net_pnl'] is not None for a in link['accounts']):
                raise AssertionError('missing entry fee in held illustration became net PnL')
            unknown_links+=1
    return {'self_test':'passed','engine_cases':len(report['engine_cases']),'segregated_accounts_checked':accounts,
            'held_deadlines':len(rows),'displayed_costs_checked':costs,'cost_stresses_checked':stresses,
            'unknown_fee_account_links':unknown_links,'max_reported_quote_arithmetic_difference':str(maxdiff),
            'scope':'independent arithmetic on reported invented/model postings and held sweeps; not independent raw market decoding, actual fills or alpha verification'}


if __name__=='__main__':
    import argparse,json
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('report',nargs='?')
    args=p.parse_args();print(json.dumps(check_artifact(args.report) if args.report else self_test(),sort_keys=True,indent=2))
