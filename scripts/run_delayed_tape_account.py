"""R350 finalized tape timing, unknown-exit account and reported-cost audit.

Original compressed exports were not received. The later UTF8 copies support
a completed-subset, return-normalized account audit, not original-price fills,
first-seen decisions, recomputed inference or a full-policy account.
"""
import argparse
import csv
from datetime import datetime, timezone
from dataclasses import asdict
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lab import prereg
from lab.causal_tape import CausalTape, legacy_availability
from lab.tape import mexc
from lab.stream_quotes import FrameClock, NS
from lab.paper_account import PaperAccount, PaperEvent
from lab.paper_account import _precision
from lab.paper_controls import PaperRisk, RiskPolicy

LANE=ROOT/'experiments/delayed_tape_account_v1'
OLD=ROOT/'experiments/warm_values_v1/evidence'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes(),parse_float=D)
def plain(x):
    if isinstance(x,(D,F)):return str(x)
    if isinstance(x,dict):return {k:plain(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [plain(v) for v in x]
    if hasattr(x,'item'):return x.item()
    return x
def encoded(x):return (json.dumps(plain(x),sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def save(p,x):
    with p.open('xb') as h:h.write(encoded(x))


def verify():
    p=LANE/'PREREG.md';spec=p.read_text();prereg.verify(p)
    for n in ('code_inputs.json','inputs.json','config.json','sources.json'):
        if sha(LANE/n) not in spec:raise ValueError('unbound input '+n)
        if subprocess.check_output(['git','show','HEAD:'+str((LANE/n).relative_to(ROOT))],cwd=ROOT)!=(LANE/n).read_bytes():
            raise ValueError('committed input required '+n)
    for n in ('PREREG.md','PREREG.sha256'):
        if subprocess.check_output(['git','show','HEAD:'+str((LANE/n).relative_to(ROOT))],cwd=ROOT)!=(LANE/n).read_bytes():raise ValueError('uncommitted spec')
    for n in ('code_inputs.json','inputs.json'):
        for name,h in load(LANE/n)['sha256'].items():
            if sha(ROOT/name)!=h:raise ValueError('frozen identity drift '+name)
    if load(LANE/'code_inputs.json')['python_version']!=list(sys.version_info[:3]):raise ValueError('runtime drift')
    return load(LANE/'config.json')


def replay_frames(interval_seconds, frames, metadata, anchor):
    """CONSTRUCTED periodic processing clocks over original first-seen frames.

    No claim that either timer ran when these messages were collected.
    Terminal processing is at the last original receipt, never a later invented
    wait that could make the final buckets look mature.
    """
    t=CausalTape('mexc','R316-original-connection',anchor)
    sizes={coin+'_USDT':float(m['mexc']['contractSize']) for coin,m in metadata.items()}
    tick=anchor.mono_ns+interval_seconds*NS
    def at(mono):return FrameClock(anchor.utc_ns+mono-anchor.mono_ns,mono)
    last=anchor
    for frame in frames:
        while tick<frame['mono_ns']:
            t.finalize(at(tick));tick+=interval_seconds*NS
        clock=FrameClock(frame['utc_ns'],frame['mono_ns']);last=clock
        payload=json.loads(frame['raw'])
        events=mexc(payload,sizes)
        if not events and payload.get('channel')=='push.depth.full':
            try:t.ingest('book','unknown',0,(),clock,'invalid-R316-'+str(frame['number']))
            except ValueError:pass  # retained invalid-input evidence and persistent stop
        for i,event in enumerate(events):
            kind,symbol,stamp,*values=event
            if kind!='book':continue
            identity='R316-mexc-'+str(frame['number'])+'-'+str(i)
            try:t.ingest(kind,symbol,stamp,tuple(float(v) for v in values[:4]),clock,identity)
            except ValueError:pass  # retain the wrapper's explicit failure, never fabricate a quote
    while tick<=last.mono_ns:
        t.finalize(at(tick));tick+=interval_seconds*NS
    t.finalize(last,terminal=True)
    packets=[]
    for item in t.released:
        p=item.mapping();p['processing_clock_kind']='constructed_replay_schedule_not_measured_production'
        early=item.second_ms*1_000_000+NS
        early_mono=anchor.mono_ns+early-anchor.utc_ns
        p['at_exchange_second_end']=t.readiness(item,early_mono)
        p['at_finalization']=t.readiness(item,item.finalized_clock.mono_ns)
        p['finalization_after_second_end_ns']=item.finalized_clock.utc_ns-early
        p['legacy_availability']=legacy_availability(p['row'])
        packets.append(p)
    return {'interval_seconds':interval_seconds,'packets':packets,'receipts':t.evidence,
            'persistent_quality_flags':sorted(t.flags),'actual_execution_ready':False}


def native_case(out, multiple, missing_exit):
    folder=out/('native-'+str(multiple)+'-'+str(int(missing_exit)));folder.mkdir()
    anchor=FrameClock(1790000000*NS,10*NS);initial={('lighter-model','MODEL_QUOTE'):D(10000)}
    account=PaperAccount(initial,anchor,journal_path=folder/'account.jsonl')
    at=lambda s:FrameClock(anchor.utc_ns+s*NS,anchor.mono_ns+s*NS)
    entry=D(100)*(1+D(multiple)*D('.4')/10000)
    event=PaperEvent('invented-entry','fill','lighter-model','MODEL_QUOTE','TOY',at(1).utc_ns,at(1),
        'invented-constant-mid-not-R348',quantity=D(10),price=entry,fee=D(0),reference_mid=D(100))
    if account.post(event,at(1).mono_ns)['status']!='applied':raise ValueError('native entry rejected')
    if not missing_exit:
        exit_price=D(100)*(1-D(multiple)*D('.4')/10000)
        e=PaperEvent('invented-exit','fill','lighter-model','MODEL_QUOTE','TOY',at(6).utc_ns,at(6),
            'invented-constant-mid-not-R348',quantity=D(-10),price=exit_price,fee=D(0),reference_mid=D(100))
        if account.post(e,at(6).mono_ns)['status']!='applied':raise ValueError('native exit rejected')
    before=(folder/'account.jsonl').read_bytes()
    reopened=PaperAccount(initial,anchor,journal_path=folder/'account.jsonl')
    snap=reopened.snapshot(at(6).mono_ns)
    if (folder/'account.jsonl').read_bytes()!=before:raise ValueError('native replay changed journal')
    risk=PaperRisk(folder/'risk.jsonl',RiskPolicy('R350-invented'),anchor,contract_version='R350',initial_balances=initial)
    stop=risk.observe(snap,asof=at(6).mono_ns,clock=at(6),complete=not missing_exit,
        session_open=True,fee_inputs_known=True,contract_version='R350',expected_contract_version='R350',mode='fixture')
    return {'cost_multiple':multiple,'missing_exit':missing_exit,'snapshot':snap,'risk':stop,
            'all_prices_clocks_zero_fees_invented':True,'actual_r348_account_replayed':False}


@_precision
def normalized_terms(row, multiple):
    """Exact constant100 entry MID normalization, never an actual market price.

    Ten normalized base units give1000 midpoint notional. Exit crossing uses
    its OWN midpoint; source gross-k*(c_e+c_x) instead expresses both costs
    against entry midpoint and omits the small return/cost interaction.
    """
    if multiple not in (1,2,3):raise ValueError('fixed cost multiple required')
    side=int(row['side']);g=D(row['gross']);ce=D(row['c_e']);cx=D(row['c_x'])
    if side not in (-1,1) or any(not x.is_finite() for x in (g,ce,cx)) or min(ce,cx)<0:
        raise ValueError('finite signed return and nonnegative crossing required')
    ratio=1+D(side)*g/10000
    entry=D(100)*(1+D(side)*multiple*ce/10000)
    exit_mid=D(100)*ratio
    exit_price=exit_mid*(1-D(side)*multiple*cx/10000)
    if min(entry,exit_mid,exit_price)<=0:raise ValueError('positive normalized execution prices required')
    quantity=D(side)*10
    pnl=quantity*(exit_price-entry)
    return {'side':side,'quantity':quantity,'entry_price':entry,'exit_mid':exit_mid,
        'exit_price':exit_price,'entry_notional':abs(quantity)*entry,
        'exact_pnl':pnl,'exact_bp_on_entry_mid_notional':pnl*10,
        'old_proxy_bp':g-multiple*(ce+cx),'fee_assumption':D(0),
        'all_absolute_prices_and_base_units_normalized':True}


@_precision
def completed_subset_account(policy, trial, multiple):
    path=LANE/'source'/('trades_'+policy+'.csv')
    with path.open(newline='') as h:rows=list(csv.DictReader(h))
    if len(rows)!=trial['trades']:raise ValueError('published trade count mismatch')
    anchor=FrameClock(int(datetime(2026,10,21,tzinfo=timezone.utc).timestamp())*NS,NS)
    venue,asset='lighter-return-normalized','MODEL_QUOTE'
    account=PaperAccount({(venue,asset):D(10000)},anchor)
    events=[];terms=[];prior={};hold=int(policy.split('_h')[1]);digest=sha(path)
    for i,row in enumerate(rows):
        s,e,x=(int(row[n]) for n in ('s','e','x'));coin=row['coin'];day=row['day']
        if (day not in ('2026-10-21','2026-10-22','2026-10-26') or not 0<=s<e<x<86400
                or e!=s+1 or x!=e+hold or int(row['bucket'])!=(s+1)//300):raise ValueError('frozen signal/hold clock mismatch')
        start=int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp())*NS
        en,ex=start+(e+1)*NS,start+(x+1)*NS
        if en<=prior.get(coin,-1):raise ValueError('same-coin overlap in completed subset')
        prior[coin]=ex
        v=normalized_terms(row,multiple);terms.append(v)
        for at,phase,qty,price,mid in ((en,'open',v['quantity'],v['entry_price'],D(100)),
                                      (ex,'close',-v['quantity'],v['exit_price'],v['exit_mid'])):
            events.append((at,0 if phase=='close' else 1,coin,i,qty,price,mid))
    # Exits precede entries at equal timestamps; no control is selected by PnL.
    events.sort(key=lambda x:x[:4]);opened=set();blocked=set();audit=[];peak=D(0)
    for at,order,coin,i,qty,price,mid in events:
        phase='close' if order==0 else 'open';locked=sum((abs(q)*p for q,p in account.positions.values()),D(0))
        if phase=='open':
            if account.cash[venue,asset]-locked<abs(qty)*price:
                blocked.add(i);audit.append({'row':i,'phase':phase,'state':'blocked_initial_notional_capital','time_ns':at});continue
            opened.add(i)
        elif i not in opened:continue
        clock=FrameClock(at,anchor.mono_ns+at-anchor.utc_ns)
        event=PaperEvent(policy+'-'+str(i)+'-'+phase,'fill',venue,asset,coin,at,clock,
            'R348-normalized-exchange-grid-not-firstseen-'+digest,quantity=qty,price=price,fee=D(0),reference_mid=mid)
        result=account.post(event,clock.mono_ns)
        if result['status']!='applied':raise ValueError('native completed-subset event rejected')
        after=sum((abs(q)*p for q,p in account.positions.values()),D(0));peak=max(peak,after)
        audit.append({'row':i,'phase':phase,'state':'applied','time_ns':at,
                      'cash_after':str(account.cash[venue,asset]),'locked_after':str(after)})
    final=account.snapshot(account.last_asof)['accounts'][0]
    return {'policy':policy,'cost_multiple':multiple,'completed_rows':len(rows),'blocked_rows':sorted(blocked),
        'completed_subset_native_snapshot':final,'peak_entry_notional_reservation':peak,
        'all_completed_subset_trades_funded':not blocked,'per_trade_exact_pnl':[v['exact_pnl'] for v in terms],
        'per_trade_old_proxy_bp':[v['old_proxy_bp'] for v in terms],
        'per_trade_exact_bp':[v['exact_bp_on_entry_mid_notional'] for v in terms],
        'event_audit_sha256':hashlib.sha256(encoded(audit)).hexdigest(),'event_audit':audit,
        'missing_exit_count_from_parent':trial['skips']['exit_quote'],
        'whole_policy_pnl':None,'actual_expected_net':None,'original_first_seen_clocks_available':False,
        'original_compressed_source_verified_directly':False,'native_account_is_return_normalized':True}


def report(out):
    config=verify()
    if out.exists():raise ValueError('fresh output required')
    out.mkdir(parents=True)
    metadata=load(OLD/'metadata.json')['metadata'];anchor=FrameClock(**load(OLD/'anchor.json'))
    with gzip.open(OLD/'mexc.jsonl.gz','rt') as h:frames=[json.loads(line) for line in h]
    frames.sort(key=lambda x:(x['mono_ns'],x['number']))
    timing=[replay_frames(interval,frames,metadata,anchor) for interval in config['processing_interval_seconds']]
    summary=load(LANE/'source/R348_summary.json');costs=[]
    for policy,trial in summary['trials_detail'].items():
        count=trial['trades'];unknown=trial['skips']['exit_quote']
        for k in (1,2,3):
            point=F(trial[str(k)+'x']['per_trade_bp']);half=F(1,2000)
            scale=F(config['hypothetical_mid_notional'])*count/10000
            costs.append({'policy':policy,'cost_multiple':k,'completed_trades':count,'missing_exit_count':unknown,
                'published_mean_bp_interval':[point-half,point+half],
                'completed_subset_published_proxy_quote_interval':[(point-half)*scale,(point+half)*scale],
                'full_policy_account_pnl':None,'actual_expected_net':None,
                'trade_export_received':True,'first_seen_input_clocks_verified':False,
                'note':'published-rounded old convention only; not exact crossing-normalized or capital-reserved account'})
    cases=[native_case(out,k,gap) for k in (1,2,3) for gap in (False,True)]
    completed=[completed_subset_account(policy,trial,k) for policy,trial in summary['trials_detail'].items() for k in (1,2,3)]
    result={'registry_id':'R350','timing':timing,'reported_cost_intervals':costs,'native_cases':cases,
        'completed_subset_accounts':completed,'all_R348_six_utf8_exports_received':True,
        'original_compressed_exports_received':False,'R348_full_trade_or_capital_reproduction':False,
        'primary_retained':summary['primary'],'original_verdict_retained':summary['verdict'],
        'new_predictive_variants':0,'new_prospective_strategy_days':0,'activation_allowed':False,
        'actual_executable_expected_net':None,'new_market_requests':0}
    with (out/'results.json.gz').open('xb') as h:h.write(gzip.compress(encoded(result),mtime=0))
    journals={str(p.relative_to(out)):p.read_text() for p in sorted(out.glob('native-*/*.jsonl'))}
    with (out/'journals.json.gz').open('xb') as h:h.write(gzip.compress(encoded(journals),mtime=0))
    verify()
    return {'timing_profiles':len(timing),'native_cases':len(cases),'old_reported_cost_cells':len(costs),
            'R348_trade_reproduction':False,'actual_expected_net':None}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True,type=Path)
    print(json.dumps(report(p.parse_args().out),indent=2))
