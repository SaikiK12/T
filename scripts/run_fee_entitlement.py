"""R345 finite fee-survival envelopes on saved, already-seen R336 proxy events.

Not an exact R336 reproduction, historical fill simulation or portfolio NAV.
"""
import argparse
import csv
from decimal import Decimal
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lab import prereg
from lab.fee_entitlement import rounded_cost_interval,membership,payoff_interval,fee_view,bind_opportunity_fee
from tests.test_opportunity_value import fixture,batch_case

LANE=ROOT/'experiments/fee_entitlement_v1'
H=3600000;DAY=24*H;GRID0=1609459200000;D0=18993;D1=20727


def plain(x):
    if isinstance(x,(F,Decimal)):return str(x)
    if isinstance(x,dict):return {k:plain(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [plain(v) for v in x]
    return x
def encode(x):return (json.dumps(plain(x),sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def save(p,x):
    with p.open('xb') as handle:handle.write(encode(x))


def verify():
    spec=(LANE/'PREREG.md').read_text();prereg.verify(LANE/'PREREG.md')
    for n in ('code_inputs.json','inputs.json','fixtures.json','sources.json'):
        if prereg.sha256_file(LANE/n) not in spec:raise ValueError('unbound '+n)
    c=json.loads((LANE/'code_inputs.json').read_text())
    if c['python_version']!=list(sys.version_info[:3]):raise ValueError('runtime drift')
    for m in (c,json.loads((LANE/'inputs.json').read_text())):
        for path,digest in m['sha256'].items():
            if prereg.sha256_file(ROOT/path)!=digest:raise ValueError('input drift '+path)
    for name in ('PREREG.md','PREREG.sha256','code_inputs.json','inputs.json','fixtures.json','sources.json'):
        p=LANE/name
        if subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)!=p.read_bytes():raise ValueError('freeze not committed')
    return json.loads((LANE/'fixtures.json').read_text())


def nullable(value):
    try:return F(value)
    except (ValueError,TypeError,ZeroDivisionError):return None


def prepare_rows(events,costs):
    rows=[];excluded={};seen=set()
    for serial,e in enumerate(events):
        sym=e['symbol'];t=int(e['t']);day=t//DAY
        reason='outside_original_entry_window' if not D0<=day<D1 else 'outside_published_cost_cohort' if sym not in costs else None
        if reason:excluded[reason]=excluded.get(reason,0)+1;continue
        z=int(e['exit']);row=(t-GRID0)//H
        if (t-GRID0)%H or not 1<=z-row<=12:raise ValueError('original decision/exit grid violated')
        opened=t+H;closed=GRID0+(z+1)*H;ident=sym+':'+str(t)
        if ident in seen:raise ValueError('duplicate saved event')
        seen.add(ident)
        a,b=nullable(e.get('E_sigma')),nullable(e.get('sig'));edge=None if a is None or b is None else a*b
        lo,hi=rounded_cost_interval(costs[sym]);status=membership(edge,(lo,hi));side=0 if edge is None or not edge else (1 if edge>0 else -1)
        rows.append({'id':ident,'source_row':serial,'symbol':sym,'contract':costs[sym]['contract'],'t':t,'entry_ms':opened,'exit_ms':closed,
            'g':nullable(e.get('g')),'edge':edge,'cost_lo':lo,'cost_hi':hi,'PZ_status':status,'PZ_side':side,
            'settlement_asset_verified':False,'api_zero_entitlement_verified':False})
    rows.sort(key=lambda r:(r['entry_ms'],r['symbol']))
    ends={}
    for r in rows:
        # Preserve R336.check_grid's stricter decision-BAR-open gap exactly.
        if r['t']<ends.get(r['symbol'],0):raise ValueError('overlapping saved event')
        ends[r['symbol']]=r['exit_ms']
    return rows,excluded


def selected(row,policy):
    # Controls use exactly the primary's possible/certain event slots, with
    # identical size and holding time. They do not gain more exposure by trading
    # all parent events. This is a new matched diagnostic, not old R336 controls.
    return (row['PZ_side'],row['PZ_status']) if policy=='PZ' else ((1 if policy=='THROUGH' else -1),row['PZ_status'])


def exposure(rows,policy,fee_bp,notional):
    """Necessary original-notional exposure / cost floors only; no marked NAV.

Close time excluded; exits precede entries at equal model clocks. Rounded
uncertain membership is relaxed independently for conservative outer bounds.
"""
    events={};fee=F(fee_bp)/10000
    for r in rows:
        side,status=selected(r,policy)
        if not side or status not in ('certain','ambiguous'):continue
        reserve=notional*(1+6*(r['cost_hi']+fee))
        for key,sign in ((r['entry_ms'],1),(r['exit_ms'],-1)):
            delta=events.setdefault(key,[0,0,F(0),F(0)])
            delta[0]+=sign if status=='certain' else 0;delta[1]+=sign
            delta[2]+=sign*reserve if status=='certain' else 0;delta[3]+=sign*reserve
    current=[0,0,F(0),F(0)];maximum=list(current)
    for _,change in sorted(events.items()):
        current=[a+b for a,b in zip(current,change)];maximum=[max(a,b) for a,b in zip(maximum,current)]
    if current!=[0,0,F(0),F(0)]:raise ValueError('open interval accounting did not terminate')
    return {'maximum_certain_count':maximum[0],'maximum_possible_count':maximum[1],
        'original_notional_floor_certain':maximum[0]*notional,'original_notional_floor_possible':maximum[1]*notional,
        'three_times_roundtrip_reserve_ceiling_certain':maximum[2],'three_times_roundtrip_reserve_ceiling_possible':maximum[3],
        'marked_risk_and_actual_capital_sufficiency':None,'profits_reinvested':False,'actual_account_nav':None}


def evaluate(rows,config):
    cells=[];frontiers=[];notional=F(config['entry_notional']);capital=F(config['capital']);days=D1-D0
    for policy in config['policies']:
        certain=[r for r in rows if selected(r,policy)[1]=='certain' and selected(r,policy)[0]]
        ambiguous=[r for r in rows if selected(r,policy)[1]=='ambiguous' and selected(r,policy)[0]]
        complete=all(r['g'] is not None for r in certain)
        gross=sum((selected(r,policy)[0]*r['g'] for r in certain),F(0)) if complete else None
        c_lo=sum((r['cost_lo'] for r in certain),F(0));c_hi=sum((r['cost_hi'] for r in certain),F(0))
        for k in config['cost_multiples']:
            frontiers.append({'policy':policy,'cost_multiple':k,'certain_count':len(certain),'ambiguous_count':len(ambiguous),
                'certain_cohort_additional_fee_bp_lo':None if not certain or gross is None else (gross/(2*k)-c_hi)/len(certain)*10000,
                'certain_cohort_additional_fee_bp_hi':None if not certain or gross is None else (gross/(2*k)-c_lo)/len(certain)*10000,
                'whole_policy_threshold_known':not ambiguous and complete,'actual_owner_fee_bp':None})
        for f in config['additional_fee_bp']:
            floor=exposure(rows,policy,f,notional)
            for k in config['cost_multiples']:
                lower=F(0);upper=F(0);missing=0
                for r in rows:
                    side,status=selected(r,policy);lo,hi=payoff_interval(r['g'],side,status,(r['cost_lo'],r['cost_hi']),f,k)
                    if lo is None:missing+=1
                    else:lower+=lo;upper+=hi
                lo=None if missing else notional*lower;hi=None if missing else notional*upper
                cells.append({'policy':policy,'additional_fee_bp':f,'cost_multiple':k,'certain_count':len(certain),
                    'ambiguous_count':len(ambiguous),'missing_active_payoff_count':missing,
                    'proxy_quote_total_lo':lo,'proxy_quote_total_hi':hi,
                    'proxy_quote_per_calendar_day_lo':None if lo is None else lo/days,
                    'proxy_quote_per_calendar_day_hi':None if hi is None else hi/days,
                    'proxy_mean_per_trade_bp_lo':None if not certain or gross is None else (gross-2*k*(c_hi+F(f)/10000*len(certain)))/len(certain)*10000,
                    'proxy_mean_per_trade_bp_hi':None if not certain or gross is None else (gross-2*k*(c_lo+F(f)/10000*len(certain)))/len(certain)*10000,
                    'same_initial_capital':capital,'entry_notional_scale':notional,'days':days,
                    'cash_comparisons':[{'annual_scenario':a,'same_capital_simple_interest':capital*F(a)*F(days,365),
                        'conditional_excess_lo':None if lo is None else lo-capital*F(a)*F(days,365),
                        'conditional_excess_hi':None if hi is None else hi-capital*F(a)*F(days,365)} for a in config['cash_annual_scenarios']],
                    'exposure':floor,'actual_executable_expected_net':None,'new_strategy_activation_allowed':False,
                    'aggregation':'uncapped original-entry-notional proxy; dependent rounding outer envelope, not account return or confidence interval'})
    return cells,frontiers


def native_probe(config):
    o=fixture();before=batch_case([o]);sample=config['invented_public_metadata']
    view=fee_view(sample,instrument=o.symbol,source_identity=prereg.sha256_file(LANE/'fixtures.json'),origin='public_contract_metadata',
        rate_unit='fraction',received_utc_ns=o.clock.utc_ns,asof_utc_ns=o.clock.utc_ns)
    def modify(inputs):
        patch=bind_opportunity_fee(inputs['market_reports'][o.opportunity_id],view)
        inputs['market_reports'][o.opportunity_id]=patch['market_report'];inputs['fees_bp'][o.opportunity_id]=patch['fee_bp']
        inputs['risk_inputs']['fee_inputs_known']=patch['risk_fee_inputs_known']
    after=batch_case([o],mutate=modify)
    return {'scope':'invented positive forecast/book, not R336 historical or actual funding cash',
        'before':before,'after':after,'source_fee_view':view,'financial_journal_unchanged_verified_by_native_helper':True}


def report(out):
    config=verify()
    if out.exists():raise ValueError('fresh output required')
    out.mkdir(parents=True)
    parent=json.loads((ROOT/config['cost_table']).read_text(),parse_float=Decimal)
    with gzip.open(ROOT/config['saved_events'],'rt') as h:rows,excluded=prepare_rows(csv.DictReader(h),parent['costs'])
    cells,frontiers=evaluate(rows,config)
    example=json.loads((LANE/'documentation_example.json').read_text(),parse_float=Decimal)
    doc_view=fee_view(example,instrument='BTC_USDT',source_identity=config['fee_document_sha256'],origin='official_documentation_example',
        rate_unit='unknown',received_utc_ns=config['source_received_utc_ns'],asof_utc_ns=config['source_received_utc_ns'])
    result={'registry_id':'R345','verdict':'PARTIAL','policies':config['policies'],'primary':config['primary'],'diagnostic_variants':9,
        'control_scope':'same PZ certain/ambiguous event slots, entry notional and holding times; not R336 all-event controls',
        'event_rows':len(rows),'excluded_counts':excluded,'cost_cells':cells,'fee_frontiers':frontiers,'documentation_fee_view':doc_view,
        'native_guard':native_probe(config),'missing_parent_inputs':json.loads((LANE/'parent_availability.json').read_text()),
        'new_market_or_history_requests':0,'new_prospective_strategy_days':0,'actual_executable_expected_net':None,
        'activation_allowed':False,'paper_account_credited':False,'raw_R336_reproduction_claimed':False,
        'source_limits':['Binance close/funding proxy is not MEXC execution','Oct2026 cohort/fees are not historical entitlement',
            'published cost medians rounded; shared-contract ambiguity retained as outer bounds',
            'fee scenarios are original-entry-notional conventions; actual exit notional/fee asset/units unknown',
            'terminal outcome totals are not marked NAV or causal reinvestment capital','statistical uncertainty/multiplicity not calibrated; no p-value or confidence claim']}
    save(out/'results.json',result)
    with (out/'events.jsonl.gz').open('xb') as h:h.write(gzip.compress(b''.join((json.dumps(plain(r),sort_keys=True,separators=(',',':'))+'\n').encode() for r in rows),mtime=0))
    verify();return {'events':len(rows),'cells':len(cells),'frontiers':len(frontiers),'actual_expected_net':None}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    print(json.dumps(report(parser.parse_args().out),indent=2))
