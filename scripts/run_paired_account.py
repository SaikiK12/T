"""R319 registered paper lifecycle and held-book economic accounting, offline only.

No capture/order/secret/account access. Source formulas inform mechanics; this
does not run Hummingbot or turn its defaults or old quotes into expected profit.
"""
import argparse
from collections import Counter
from dataclasses import asdict
from decimal import Decimal as D
import gzip
import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lab import prereg
from lab.paired_execution import PairPlan,PairReceipt,PairedAccount
from lab.paper_account import PaperAccount,CloseMark
from lab.stream_quotes import FrameClock,NS
from scripts import run_paper_account as base
from scripts.paper_account_view import render_report,render_text

LANE=ROOT/'experiments/paired_execution_v1'
PARENT=ROOT/'experiments/paper_account_v1'
sha=prereg.sha256_file


def verify(lane=LANE):
    prereg.verify(lane/'PREREG.md');spec=(lane/'PREREG.md').read_text()
    for name in ('code_inputs.json','data_inputs.json','fixtures.json','sources.json'):
        if sha(lane/name) not in spec:raise ValueError('unbound paired input: '+name)
    code=json.loads((lane/'code_inputs.json').read_text())
    if code['python_version']!=list(sys.version_info[:3]):raise ValueError('runtime drift')
    for name,digest in code['sha256'].items():
        if sha(ROOT/name)!=digest:raise ValueError('paired code drift: '+name)
    data=json.loads((lane/'data_inputs.json').read_text())
    if data['already_seen'] is not True:raise ValueError('held data is not unseen evidence')
    for name,digest in data['sha256'].items():
        if sha(ROOT/name)!=digest:raise ValueError('held account/cost identity drift: '+name)
    base.verify(PARENT)


def build_receipt(config,case,index):
    kind,leg,order,second,fields=case['receipts'][index]
    u,m=config['anchor']['utc_ns'],config['anchor']['mono_ns']
    stamp=FrameClock(u+int(D(str(second))*NS),m+int(D(str(second))*NS))
    d=dict(receipt_id=case['name']+':'+str(index),leg=leg,order_id=order,kind=kind,
           occurred_ns=stamp.utc_ns,clock=stamp,source_identity='invented R319 paper lifecycle')
    d.update(fields)
    return PairReceipt(**d)


def run_case(config,case,multiple,scratch):
    anchor=FrameClock(**config['anchor']);plan=PairPlan(case['name'],'BTC',('USDT','USDC'),D(1),1,anchor.mono_ns+10*NS)
    initial={('mexc','USDT'):5000,('lighter','USDC'):5000};path=scratch/(case['name']+str(multiple)+'.jsonl')
    account=PaperAccount(initial,anchor,journal_path=path);attempts=[];receipts=[]
    with PairedAccount(account,plan) as pair:
        for i in range(len(case['receipts'])):
            r=build_receipt(config,case,i)
            if r.fee is not None:
                r=PairReceipt(**{**r.__dict__,'fee':r.fee*multiple})
            receipts.append(r.mapping());attempts.append(pair.post(r,r.clock.mono_ns))
        at=anchor.mono_ns+12*NS
        marks=[]
        for (v,a,s),(q,basis) in account.positions.items():
            if not q:continue
            price=D(99) if q>0 else D(101)
            rate=D(10 if v=='mexc' else 4)*multiple/10000
            marks.append(CloseMark(v,a,s,q,abs(q)*price,abs(q)*price*rate,
                FrameClock(anchor.utc_ns+12*NS,at),anchor.utc_ns+12*NS,'invented exit mark'))
        before=pair.snapshot(at,marks)
    prefix=path.read_bytes()
    reopened=PaperAccount(initial,anchor,journal_path=path)
    with PairedAccount(reopened,plan) as pair:after=pair.snapshot(at,marks)
    if before!=after or not path.read_bytes().startswith(prefix):raise ValueError('paired replay drift')
    return {'name':case['name'],'cost_multiple':multiple,'receipts':receipts,'attempts':attempts,
            'financial_events':[e.mapping() for e in reopened.accepted_events],
            'snapshot':after,'journal_replay_identical':True,'journal_sha256':sha(path),
            'scope':'invented supplied fill/status/fee/exit fixtures; not actual matching, fees or strategy PnL'}


def economic_rows(held):
    """Reported held sweeps, both directions; same q/capital and original costs.

    Entry basis is NOT futures cash profit. The only immediate closed-pair PnL
    here is the negative of the old paired crossing+reserve cost. Failure losses
    are fixed counterfactuals, not estimated probabilities or observed exits.
    """
    for row in held:
        s=row['sizes'][3];c=s['cost']
        for direction in (1,-1):
            new={'symbol':row['symbol'],'grid_second':row['grid_second'],'delay_ms':row['delay_ms'],
                'direction_mexc':direction,'quantity_base':s['quantity_base'],'capital_quote_equivalent':10000,
                'capital_per_venue_quote_equivalent':5000,'quote_parity_assumed':True,
                'original_input_state':row['readiness']['state'],'execution_ready':False,
                'hypothetical_daily_funding_fraction':'0.001','actual_expected_funding':None,
                'source_rate_threshold_is_not_a_forecast':True,'scenarios':None}
            if c and c['displayed_fillable']:
                mb,ms,lb,ls=map(lambda x:D(str(x)),s['observed_quantity']['current_buy_sell_quote'])
                mn,ln=map(lambda x:D(str(x)),c['venue_margin_mid_notionals_usd'])
                netbasis=(ln-mn) if direction==1 else (mn-ln)
                entry=D(str(c['long_mexc_entry_cost_usd' if direction==1 else 'long_lighter_entry_cost_usd']))
                fees=(D('0.001'),D('0.0004'));scenarios=[]
                for k in (1,2,3):
                    hurdles=D(str(c['scenarios'][k-1]['round_trip_cost_usd']));leg_notional=(mn+ln)/2
                    failures=[]
                    for leg,(buy,sell,fee) in enumerate(((mb,ms,fees[0]),(lb,ls,fees[1]))):
                        side=direction if leg==0 else -direction
                        cross=buy-sell;charges=(buy+sell)*fee;close=sell if side==1 else buy
                        for shock in (0,20,50):
                            move=close*D(shock)/10000
                            # Closing fee shrinks when a long's sale price falls,
                            # and grows when a short's buyback price rises.
                            loss=k*(cross+charges)+move*(1-k*fee if side==1 else 1+k*fee)
                            failures.append({'filled_leg':leg,'adverse_exit_bp':shock,
                                'hypothetical_loss_quote':str(loss),'probability':None,
                                'future_exit_observed':False})
                    scenarios.append({'multiple':k,'entry_basis_after_model_cost_quote':str(netbasis-k*entry),
                        'entry_basis_is_not_realized_futures_pnl':True,'instantaneous_paired_unwind_net_quote':str(-hurdles),
                        'round_trip_hurdle_quote':str(hurdles),'break_even_days_at_declared_10bp_per_day':str(hurdles/(leg_notional*D('.001'))),
                        'actual_break_even_hold_days':None,'one_leg_failure_scenarios':failures})
                new['scenarios']=scenarios
            yield new


def report(lane=LANE,out=None):
    verify(lane);config=json.loads((lane/'fixtures.json').read_text())
    parent=json.loads((PARENT/'results.json').read_text())
    with tempfile.TemporaryDirectory(prefix='R319-offline-') as d:
        cases=[run_case(config,c,k,Path(d)) for c in config['cases'] for k in (1,2,3)]
    held=[json.loads(x) for x in gzip.decompress((PARENT/'observations.jsonl.gz').read_bytes()).splitlines()]
    rows=list(economic_rows(held));counts=Counter(c['snapshot']['pair']['state'] for c in cases)
    first=next(c for c in cases if c['name']=='both_legs_then_exit' and c['cost_multiple']==1)
    result={**first['snapshot'],'registry_id':'R319','scope':'invented lifecycle validation plus already-seen quote arithmetic; no observed account or prospective PnL',
        'predictive_trials':0,'prospective_days':0,'new_market_requests':0,'net_return_tested':False,
        'cases':cases,'held_summary':{'rows':len(rows),'two_directions_per_deadline':True,'input_deadlines':len(held),
            'eligible_direction_rows':sum(r['scenarios'] is not None for r in rows),
            'account_lifecycle_cases':len(cases),'lifecycle_states':dict(counts)},
        'readiness':parent['readiness'],'fee_integration':parent['fee_integration'],
        'funding_integration':parent['funding_integration'],'operations_integration':parent['operations_integration'],
        'coverage':{'invented_lifecycle_paths':len(cases),'held_deadlines':len(held),'new_prospective_days':0},
        'cost_comparisons':[{'multiple':c['cost_multiple'],'asset':a['asset'],'net_pnl':a['realized_net_pnl'],
            'fee_assumption':'invented matched lifecycle; same capital/prices and fixed1x/2x/3x charges'}
            for c in cases if c['name']=='both_legs_then_exit' for a in c['snapshot']['accounts'] if a['venue']=='mexc'],
        'next_evidence':parent['next_evidence']+['Rapports complets des exécutions, annulations et positions par plateforme'],
        'parent_scope':'R318 fee/funding/budget controls are reused validation, not additional independent evidence',
        'data_identity_sha256':sha(lane/'data_inputs.json')}
    result['readiness']['components']['exposition entre les deux plateformes']={
        'state':'conditional','reasons':['Lifecycle conserves supplied partial fills; actual complete/authenticated fill reports still absent'],
        'next_evidence':['First-seen complete fills, terminal cumulative quantities and cancel/gap reconciliation']}
    out=Path(out) if out is not None else lane;out.mkdir(parents=True,exist_ok=True)
    raw=''.join(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n' for r in rows).encode()
    base.parent.depth.immutable(out/'observations.jsonl.gz',gzip.compress(raw,mtime=0))
    result['observations_sha256']=sha(out/'observations.jsonl.gz');verify(lane)
    base.parent.depth.immutable(out/'results.json',base.encode(result))
    base.parent.depth.immutable(out/'account.html',render_report(result).encode())
    base.parent.depth.immutable(out/'account.txt',render_text(result).encode())
    return out/'results.json'


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path)
    print(report(out=p.parse_args().out))
