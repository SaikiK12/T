"""Independent arithmetic for R319 reports, standard library only.

Checks reported model fills/sweeps; it does not authenticate source reports,
reconstruct raw exchange books, import Hummingbot or establish an actual edge.
"""
from decimal import Decimal as D
import gzip
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.check_paper_account import LinearOracle,close


def check(path):
    path=Path(path);report=json.loads(path.read_text())
    if report['activation_allowed'] or report['prospective_days'] or report['predictive_trials']:raise AssertionError('diagnostic promoted to strategy')
    states={};accounts=0
    for case in report['cases']:
        snap=case['snapshot'];pp=snap['pair'];states[case['name']]=pp['state']
        models={(a['venue'],a['asset']):LinearOracle(a['venue'],a['asset'],a['initial_cash']) for a in snap['accounts']}
        seen=set()
        for e in case['financial_events']:
            if e['event_id'] in seen:raise AssertionError('duplicate financial trade')
            seen.add(e['event_id']);m=models[e['venue'],e['asset']]
            m.fill(e['symbol'],e['quantity'],e['price'],e['fee'] or 0)
        for a in snap['accounts']:
            m=models[a['venue'],a['asset']];q,basis=m.positions.get('BTC',(D(0),D(0)))
            close(a['known_cash_component'],m.cash,'known cash conservation')
            close(a['realized_price_pnl'],m.realized,'realized price');close(a['fees_paid'],m.fees,'fees once')
            mark=D(99) if q>0 else D(101);rate=D(10 if a['venue']=='mexc' else 4)*case['cost_multiple']/10000
            if a['cash'] is not None:
                close(a['cash'],m.cash,'complete cash');close(a['nav'],m.cash+q*(mark-basis)-abs(q)*mark*rate,'net liquidation')
            elif a['nav'] is not None:raise AssertionError('unknown cash became equity')
            leg=0 if a['venue']=='mexc' else 1
            close(pp['known_received_positions_base'][leg],q,'receipt inventory retained')
            accounts+=1
        if pp['reasons'] and (pp['net_delta_base'] is not None or any(a['realized_net_pnl'] is not None for a in snap['accounts'])):
            raise AssertionError('unreconciled reports became complete risk or PnL')
        if pp['terminal_cash_known'] and any(D(a['quantity_base'])!=0 for x in snap['accounts'] for a in x['positions']):
            raise AssertionError('residual position became terminal')
        if not case['journal_replay_identical']:raise AssertionError('journal replay drift')
    expected={'inactive':'inactive','acknowledged_without_fills':'pending_orders','both_legs_then_exit':'flat',
              'first_leg_rejected':'exposed','partial_hedge_rejected':'exposed','cancel_race':'exposed',
              'residual_retry':'hedged','oversized_retry':'unknown','terminal_total_missing':'unknown',
              'source_gap':'unknown','duplicate_trade':'hedged','unknown_fee':'exposed',
              'fill_without_order':'unknown','fill_after_terminal':'unknown','entry_timeout':'unknown','partially_closed':'exposed'}
    if states!=expected:raise AssertionError('finite lifecycle coverage or expected state mismatch')
    rows=[json.loads(x) for x in gzip.decompress((path.parent/'observations.jsonl.gz').read_bytes()).splitlines()]
    if len(rows)!=144:raise AssertionError('held pair/direction inventory')
    checks=0
    for row in rows:
        if row['execution_ready'] or row['actual_expected_funding'] is not None:raise AssertionError('counterfactual became expected net return')
        for s in row['scenarios'] or []:
            close(s['instantaneous_paired_unwind_net_quote'],-D(s['round_trip_hurdle_quote']),'basis not futures cash')
            if not s['entry_basis_is_not_realized_futures_pnl']:raise AssertionError('entry notional treated as PnL')
            for f in s['one_leg_failure_scenarios']:
                if D(f['hypothetical_loss_quote'])<0 or f['probability'] is not None or f['future_exit_observed']:
                    raise AssertionError('failure assumption became free profit or measured probability')
                checks+=1
    # Literal dimensional implication of the inspected source denominator,
    # NOT execution of the upstream Hummingbot method or an empirical result.
    source_units={'net_quote':'4','executed_base':'2','entry_price':'100',
        'source_formula_quote_per_base':str(D(4)/2),'correct_fraction_on_entry_notional':str(D(4)/(2*100)),
        'upstream_module_executed':False}
    return {'invented_lifecycle_paths':len(report['cases']),'segregated_account_states':accounts,
            'held_direction_rows':len(rows),'failure_scenarios_checked':checks,'states_match_finite_contract':True,
            'dimensional_counterexample':source_units,
            'scope':'arithmetic on reported invented fills and prior reported sweeps only; no independent raw decoder, provider/fill proof or alpha test'}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('report');args=p.parse_args()
    print(json.dumps(check(args.report),sort_keys=True,indent=2))
