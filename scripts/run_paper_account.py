"""R318 offline account integration, on invented fixtures and sealed seen books.

No capture, order, credential, activation or historical-policy rerun capability.
The default output is the frozen lane; --out permits immutable reproduction.
"""
import argparse
from collections import Counter
from dataclasses import asdict,replace
from decimal import Decimal as D
import gzip
import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lab import prereg
from lab.acquisition_budget import BudgetJournal,BudgetLimits,BudgetError,historical_baseline
from lab.depth_replay import DepthReplay
from lab.execution_envelope import size_envelope,liquidation_quote
from lab.fee_evidence import FeeStatement,FeeEvidenceBook,assess_fee
from lab.funding_values import FundingContract,FundingEvent,streamed_value
from lab.market_readiness import (instrument_from_metadata,assess_pair,event_value_from_mapping,
                                  assess_settlement,compare_funding_estimate)
from lab.paper_account import PaperAccount,PaperEvent,CloseMark
from lab.stream_quotes import FrameClock,NS,StreamBook
from lab.stream_recovery import StreamRecovery
from scripts import probe_warm_values as parent
from scripts.paper_account_view import render_report,render_text

LANE=ROOT/'experiments/paper_account_v1'
PARENT=ROOT/'experiments/warm_values_v1'
GRIDS=(10,20,30,40,50,60)
SIZES=(25,50,100,250,500,1000)
sha=prereg.sha256_file


def verify(lane=LANE):
    prereg.verify(lane/'PREREG.md')
    spec=(lane/'PREREG.md').read_text()
    for name in ('code_inputs.json','data_inputs.json','fixtures.json'):
        if sha(lane/name) not in spec:raise ValueError('unbound integration identity: '+name)
    code=json.loads((lane/'code_inputs.json').read_text())
    if code['python_version']!=list(sys.version_info[:3]):raise ValueError('runtime drift')
    for name,digest in code['sha256'].items():
        if sha(ROOT/name)!=digest:raise ValueError('integration code drift: '+name)
    data=json.loads((lane/'data_inputs.json').read_text())
    expected={'experiments/warm_values_v1/'+n for n in ('PREREG.md','PREREG.sha256','code_inputs.json',
                                                        'evidence_inputs.json','results.json','observations.jsonl.gz')}
    if set(data['sha256'])!=expected or data['already_seen'] is not True:raise ValueError('held input scope drift')
    for name,digest in data['sha256'].items():
        if sha(ROOT/name)!=digest:raise ValueError('held input identity drift: '+name)


def encode(obj):return (json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()


def request(statement,start,end):
    return {**{k:getattr(statement,k) for k in ('venue','instrument','account_scope','order_role',
                  'order_class','fee_asset','notional_asset')},'entry_ns':start,'exit_ns':end}


def run_case(case,anchor,scratch):
    """General explicit simulation-event bundle; no price/fee/asset inference."""
    initial={(x['venue'],x['asset']):x['cash'] for x in case['initial']}
    if len(initial)!=len(case['initial']):raise ValueError('duplicate initial account')
    path=scratch/(case['name']+'.jsonl')
    account=PaperAccount(initial,anchor,journal_path=path)
    statuses=[];events=[]
    for row in case['events']:
        event=PaperEvent.from_mapping(row['event']);events.append(event.mapping())
        statuses.append(account.post(event,row['asof_mono_ns']))
    marks=[CloseMark(**{**m,'clock':FrameClock(**m['clock'])}) for m in case.get('marks',[])]
    before=account.snapshot(case['asof_mono_ns'],marks)
    prefix=path.read_bytes()
    reopened=PaperAccount(initial,anchor,journal_path=path)
    after=reopened.snapshot(case['asof_mono_ns'],marks)
    if before!=after or path.read_bytes()!=prefix:raise ValueError('account replay drift')
    return {'name':case['name'],'scope':'invented engine validation, not observed strategy PnL',
            'events':events,'attempts':statuses,'marks':case.get('marks',[]),'snapshot':after,
            'journal_sha256':sha(path),'journal_replay_identical':True}


def funding_case(config,anchor,scratch):
    account=PaperAccount({('mexc','USDT'):5000,('lighter','USDC'):5000},anchor,
                         journal_path=scratch/'funding-account.jsonl')
    opening=PaperEvent.from_mapping(config['opening']);account.post(opening,opening.clock.mono_ns)
    observed=FrameClock(**config['observed_clock']);at=observed.mono_ns
    contract=FundingContract(**config['contract'])
    event=FundingEvent(**{**config['settled'],'rate':D(config['settled']['rate']),
                         'clock':FrameClock(**config['settled']['clock'])})
    estimate=FundingEvent(**{**config['estimated'],'rate':D(config['estimated']['rate']),
                            'clock':FrameClock(**config['estimated']['clock'])})
    packet=event_value_from_mapping(config['value'])
    spans=account.position_spans('mexc','USDT','BTC',observed)
    missing=assess_settlement(contract,event,spans,None,at,anchor)
    bound=assess_settlement(contract,event,spans,packet,at,anchor)
    account.record_evidence('funding_assessment',missing)
    pending=PaperEvent('model-funding','funding','mexc','USDT','BTC',event.funding_ns,observed,
                       'invented funding inputs',amount=None)
    account.post(pending,at);unknown=account.snapshot(at)
    if bound['cash_delta'] is None:raise ValueError('invented bound fixture must yield model cash')
    # A new derived receipt resolves the pending amount; the original is intact.
    later=replace(observed,utc_ns=observed.utc_ns+NS,mono_ns=at+NS)
    account.record_evidence('funding_assessment',bound)
    resolved=PaperEvent('model-funding-resolution','funding_resolution','mexc','USDT','BTC',
                       event.funding_ns,later,'invented event-bound funding',
                       amount=bound['cash_delta'],resolves='model-funding')
    account.post(resolved,later.mono_ns)
    after=account.snapshot(later.mono_ns)
    lt=replace(contract,venue='lighter',settlement_asset='USDC',price_quote_asset='USDC',batch_delay_ns=0)
    le=replace(event,venue='lighter');lp=replace(packet,venue='lighter',kind='index')
    lspans=[replace(s,venue='lighter') for s in spans]
    no_basis=assess_settlement(lt,le,lspans,lp,at,anchor)
    declared_basis=assess_settlement(lt,le,lspans,lp,at,anchor,index_basis='pre_update_event_index')
    return {'missing_value':missing,'unknown_snapshot':unknown,'bound_model':bound,'resolved_snapshot':after,
            'events':[e.mapping() for e in account.accepted_events],
            'exposure_spans':[dict(asdict(s),quantity=str(s.quantity)) for s in spans],
            'estimate_error':compare_funding_estimate(estimate,event,at,anchor,
                        announcement_source='invented early announcement',settlement_source='invented settled event'),
            'lighter_missing_basis':no_basis,'lighter_declared_basis_only':declared_basis,
            'actual_event_index_proof_acquired':False}


def fee_cases(payload,anchor,scratch):
    book=FeeEvidenceBook();statement=FeeStatement.from_mapping(payload,received_ns=anchor.utc_ns)
    book.add(statement);start=anchor.utc_ns+NS;end=start+NS
    regular=book.assess(statement.statement_id,request(statement,start,end),start,100,90)
    absent=assess_fee(None,request(statement,start,end),start,100,90)
    promo=FeeStatement.from_mapping({**payload,'statement_id':'invented-promo','rate':'0','promotional':True,
        'entitlement_attested':True,'entitlement_id':'invented-grant','quota_total_notional':'500',
        'quota_used_notional':'0'},received_ns=anchor.utc_ns)
    book.add(promo);req=request(promo,start,end)
    reserved=book.assess(promo.statement_id,req,start,100,110,reserve=True,reservation_id='roundtrip-one')
    duplicate=book.assess(promo.statement_id,req,start,100,110,reserve=True,reservation_id='roundtrip-one')
    # Persist actual fee-assumption operations in the same account evidence log.
    account=PaperAccount({('mexc','USDT'):5000},anchor,journal_path=scratch/'fees-account.jsonl')
    for e in book.events:account.record_evidence('fee_assumption',e)
    for eid,q,price,fee,second in (('fee-linked-open',1,100,regular.get('entry_fee'),1),
                                 ('fee-linked-close',-1,90,regular.get('exit_fee'),2)):
        clock=FrameClock(anchor.utc_ns+second*NS,anchor.mono_ns+second*NS)
        account.post(PaperEvent(eid,'fill','mexc','USDT','BTC',clock.utc_ns,clock,
                     'invented conditional statement',quantity=q,price=price,fee=fee),clock.mono_ns)
    reopened=PaperAccount({('mexc','USDT'):5000},anchor,journal_path=scratch/'fees-account.jsonl')
    restored=FeeEvidenceBook.replay([e['payload'] for e in reopened.evidence if e['namespace']=='fee_assumption'])
    exhausted=restored.assess(promo.statement_id,req,start,200,200,reserve=True,reservation_id='roundtrip-two')
    expired=assess_fee(statement,request(statement,start,statement.valid_until_ns),start,100,110)
    return {'regular':regular,'missing':absent,'promo_reservation':reserved,'duplicate':duplicate,
            'after_restart_quota':exhausted,'expired_exit':expired,'replayed_operation_count':len(book.events),
            'linked_snapshot':reopened.snapshot(anchor.mono_ns+2*NS),
            'linked_events':[e.mapping() for e in reopened.accepted_events],
            'source_scope':'all statements invented; optional redacted importer exists, no owner statement accessed'}


def operations_cases(config,anchor,scratch):
    budget=BudgetJournal(scratch/'budget.jsonl','invented-integration-only',BudgetLimits(2,100,20,10))
    first=budget.reserve('one',50,10,now_ns=1,deadline_ns=11)
    budget.complete('one',20,5,outcome='timeout')
    reopened=BudgetJournal(scratch/'budget.jsonl','invented-integration-only',BudgetLimits(2,100,20,10))
    again=reopened.reserve('one',50,10,now_ns=2,deadline_ns=11)
    reopened.reserve('two',50,10,now_ns=11,deadline_ns=21)
    state=reopened.status()
    historical=BudgetJournal(scratch/'history.jsonl','R310-R311-existing-accumulated',
        BudgetLimits(8000,250*1024**2,120*NS,3*NS),baseline=historical_baseline()).status()
    # The synthetic coordinator is not connected to an exchange.
    path=scratch/'recovery.jsonl';s=StreamRecovery(1,'BTC',max_restarts=2,max_frames=5,journal_path=path)
    c=lambda offset:FrameClock(anchor.utc_ns+offset,anchor.mono_ns+offset)
    old=s.token;before=s.consume(config['snapshot'],c(0),epoch=old)
    gap=s.consume(config['gap'],c(100_000_000),epoch=old)
    invalid=s.status();new=s.restart('invented nonce gap',c(200_000_000))
    stale=s.consume(config['snapshot'],c(300_000_000),epoch=old)
    replacement=s.consume(config['snapshot'],c(400_000_000),epoch=new);s.close()
    r=StreamRecovery(1,'BTC',max_restarts=2,max_frames=5,journal_path=path);after=r.status();r.close()
    return {'budget_first':first,'budget_duplicate_after_restart':again,'budget_final':state,
            'historical_accumulated':historical,'snapshot':before,'gap':gap,'after_gap':invalid,
            'stale_epoch':stale,'replacement':replacement,'reopen_requires_new_transport':after,
            'network_requests':0,'scope':'invented recovery/budget tests only; no allowance or collection grant'}


def held_rows():
    frames,mapping,anchor,connections=parent.depth.load_capture(PARENT)
    replay=DepthReplay(frames,mapping['metadata'],{int(k):v for k,v in mapping['names'].items()},anchor,connections)
    meta=json.loads((PARENT/'evidence/receipts.json').read_text())['records']
    mxclocks={r['name'].removesuffix('_mexc_metadata'):FrameClock(r['received_utc_ns'],r['received_mono_ns'])
              for r in meta if r['name'].endswith('_mexc_metadata')}
    ltr=next(r for r in meta if r['name']=='lighter_metadata')
    ltclock=FrameClock(ltr['received_utc_ns'],ltr['received_mono_ns'])
    for grid in GRIDS:
        before={}
        for delay in (0,300):
            at=anchor.mono_ns+grid*NS+delay*1_000_000
            for symbol in parent.SYMBOLS:
                row,books=replay.observe(symbol,at,before.get(symbol,(None,None))[0],allow_new_quantity=delay==0)
                if delay==0:before[symbol]=(row['quantity_base'],books)
                mm,lm=(mapping['metadata'].get(symbol,{}).get(v,{}) for v in ('mexc','lighter'))
                values=tuple(streamed_value(replay.latest.get((v,'reference',symbol))) for v in ('mexc','lighter'))
                specs=(instrument_from_metadata('mexc',symbol,mm,mxclocks[symbol],'sealed R316 MEXC detail'),
                       instrument_from_metadata('lighter',symbol,lm,ltclock,'sealed R316 Lighter detail'))
                ready=assess_pair(books,specs,(None,None),values,at,anchor)
                sizes=size_envelope(before[symbol][1],books,mm,lm,anchor.mono_ns+grid*NS,at,anchor,
                      leg_budgets=SIZES,fees_bp=(10,4),venue_delay_ms=(0,300),
                      exit_fees_bp=(20,8),extra_exit_delay_ms=500,capital=10000)
                # Link a single hypothetical open position to the account's
                # conservative liquidation mark. This is NOT an assumed fill.
                linkage=None
                if row['quantity_base'] is not None and all(isinstance(b,StreamBook) for b in books):
                    q=D(row['quantity_base']);q0=before[symbol][0]
                    if q0 is not None and sizes[3]['cost'] is not None and sizes[3]['cost'].get('displayed_fillable'):
                        account=PaperAccount({('mexc','USDT'):5000,('lighter','USD_quote'):5000},anchor)
                        quotes=[]
                        for b,asset,sign,fee in zip(books,('USDT','USD_quote'),(1,-1),(10,4)):
                            # Entry mid is an explicit counterfactual basis, not
                            # executable entry; exits use displayed side/depth.
                            e=PaperEvent('hypothetical:'+b.venue,'fill',b.venue,asset,symbol,b.clock.utc_ns,b.clock,
                                          'post-hoc held book illustration',quantity=q*sign,price=str(b.mid),fee=None)
                            account.post(e,at)
                            x=liquidation_quote(b,q*sign,fee,at,anchor)
                            if x['gross_close_quote'] is not None:
                                quotes.append(CloseMark(b.venue,asset,symbol,q*sign,x['gross_close_quote'],x['fee_quote'],
                                                        b.clock,b.source_time_ns,'held displayed close only'))
                        linkage=account.snapshot(at,quotes)
                        if any(a['nav'] is not None for a in linkage['accounts']):raise ValueError('unknown entry fees cannot yield known net NAV')
                yield {'symbol':symbol,'grid_second':grid,'delay_ms':delay,'asof_mono_ns':at,
                       'reference_reserve_cost':row['cost'],'readiness':ready,'sizes':sizes,
                       'counterfactual_account_linkage':linkage,'execution_ready':False,
                       'actual_fills':0,'prospective_days':0}


def report(lane=LANE,out=None):
    verify(lane);config=json.loads((lane/'fixtures.json').read_text());anchor=FrameClock(**config['anchor'])
    with tempfile.TemporaryDirectory(prefix='R318-offline-') as d:
        scratch=Path(d)
        cases=[run_case(c,anchor,scratch) for c in config['cases']]
        funding=funding_case(config['funding'],anchor,scratch)
        fees=fee_cases(config['fee_statement'],anchor,scratch)
        operations=operations_cases(config['operations'],anchor,scratch)
    rows=list(held_rows());counts=Counter(r['readiness']['state'] for r in rows)
    complete=sum(s['state']=='conditional' for r in rows for s in r['sizes'])
    base=next(c for c in cases if c['name']=='closed_and_reversed')['snapshot']
    result={**base,'registry_id':'R318','scope':'invented engine validation plus post-hoc already-seen R316 quote diagnostics; NO actual paper PnL',
            'predictive_trials':0,'prospective_days':0,'net_return_tested':False,'new_market_requests':0,
            'engine_cases':cases,'funding_integration':funding,'fee_integration':fees,'operations_integration':operations,
            'held_summary':{'rows':len(rows),'sizes_per_row':len(SIZES),'size_cases':len(rows)*len(SIZES),
                            'conditional_displayed_size_cases':complete,'input_states':dict(counts),
                            'capital_quote_equivalent':10000,'per_venue_quote_equivalent':5000,
                            'asset_parity_is_assumed':True,'minimum_delay_is_not_total_execution_latency':True},
            'readiness':{'components':{
                'compte simulé':{'state':'conditional','reasons':['invented engine validation only']},
                'vrais frais du compte':{'state':'unknown','next_evidence':['redacted source-bound owner fee statement and charged fills']},
                'sessions et droits API':{'state':'unknown','next_evidence':['current venue/session/account permission evidence']},
                'index exact du financement Lighter':{'state':'unknown','next_evidence':['pre-update event/proof/API-unit bridge']},
                'collecte historique':{'state':'blocked','reasons':['existing accumulated byte baseline not exact; no renewed allowance']}}},
            'coverage':{'invented_cases':len(cases),'held_book_deadlines':len(rows),'new_paper_days':0},
            'next_evidence':['Prix et profondeur synchronisés, connus à temps','Frais réellement applicables au compte',
                             'Sessions ouvertes et droits API','Index Lighter lié à son événement de financement'],
            'legacy_projection':{'historical_outputs_rewritten_by_this_runner':False,'proxy_positions_imported':False,
                'strict_account_cash_or_nav_from_legacy_proxy':None,
                'reason':'legacy proxy totals cannot certify event/fee/session/executable inputs; missing remains unknown'},
            'data_identity_sha256':sha(lane/'data_inputs.json')}
    result['cost_comparisons']=[{'multiple':c.get('cost_multiple',1),'asset':'USDT',
        'net_pnl':x['realized_net_pnl'],'scope':'invented engine sequence; same capital and prices',
        'fee_assumption':'original10bp MEXC reserve multiplied; no actual fees or strategy inference'}
        for c in config['cases'] if 'cost_multiple' in c
        for x in next(z for z in cases if z['name']==c['name'])['snapshot']['accounts'] if x['venue']=='mexc']
    raw=''.join(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n' for r in rows).encode()
    out=Path(out) if out is not None else lane;out.mkdir(parents=True,exist_ok=True)
    parent.depth.immutable(out/'observations.jsonl.gz',gzip.compress(raw,mtime=0))
    result['observations_sha256']=sha(out/'observations.jsonl.gz')
    verify(lane)
    parent.depth.immutable(out/'results.json',encode(result))
    parent.depth.immutable(out/'account.html',render_report(result).encode())
    parent.depth.immutable(out/'account.txt',render_text(result).encode())
    return out/'results.json'


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path)
    print(report(out=p.parse_args().out))
