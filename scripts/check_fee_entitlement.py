"""Independent stdlib R345 serialization/fee/capital-envelope checker.

Imports no production selector, cost, financial-account or report functions.
"""
import argparse
import csv
from decimal import Decimal
from fractions import Fraction as F
import gzip
import hashlib
import heapq
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1];LANE=ROOT/'experiments/fee_entitlement_v1'
H=3600000;DAY=24*H;GRID0=1609459200000;D0=18993;D1=20727


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(),parse_float=Decimal)
def wire(x):
    if isinstance(x,F):return str(x)
    if isinstance(x,dict):return {k:wire(v) for k,v in x.items()}
    if isinstance(x,(tuple,list)):return [wire(v) for v in x]
    return x


class Check:
    def __init__(self):self.count=0
    def eq(self,a,b,label):
        self.count+=1
        if a!=b:raise AssertionError(label+': '+str(a)[:160]+' != '+str(b)[:160])
    def num(self,a,b,label):self.eq(None if a is None else F(a),b,label)


def number(s):
    try:return F(s)
    except (ValueError,TypeError,ZeroDivisionError):return None


def raw_rows(config):
    table=read(ROOT/config['cost_table'])['costs'];expected=[];excluded={};seen=set()
    with gzip.open(ROOT/config['saved_events'],'rt') as h:
        for i,e in enumerate(csv.DictReader(h)):
            s=e['symbol'];t=int(e['t']);reason='outside_original_entry_window' if not D0<=t//DAY<D1 else 'outside_published_cost_cohort' if s not in table else None
            if reason:excluded[reason]=excluded.get(reason,0)+1;continue
            meta=table[s];mid=F(meta['median_half_spread_bp']);reported=F(meta['one_way_bp']);radius=F(1,2000)
            low=max(F(1),mid-radius,reported-radius)/10000;high=min(max(F(1),mid+radius),reported+radius)/10000
            if high<low:raise AssertionError('inconsistent rounded table')
            a,b=number(e['E_sigma']),number(e['sig']);edge=None if a is None or b is None else a*b
            if edge is None:status='inactive_missing_prediction';side=0
            else:
                side=(edge>0)-(edge<0)
                status='certain' if abs(edge)>4*high else 'inactive' if abs(edge)<=4*low else 'ambiguous'
            ident=s+':'+str(t);end=int(e['exit'])
            if ident in seen or (t-GRID0)%H or not 1<=end-(t-GRID0)//H<=12:raise AssertionError('event identity/grid')
            seen.add(ident);expected.append({'id':ident,'source_row':i,'symbol':s,'contract':meta['contract'],'t':t,'entry_ms':t+H,
                'exit_ms':GRID0+(end+1)*H,'g':number(e['g']),'edge':edge,'cost_lo':low,'cost_hi':high,
                'PZ_status':status,'PZ_side':side,'settlement_asset_verified':False,'api_zero_entitlement_verified':False})
    expected.sort(key=lambda e:(e['entry_ms'],e['symbol']))
    previous={}
    for e in expected:
        if e['t']<previous.get(e['symbol'],0):raise AssertionError('original decision-bar gap')
        previous[e['symbol']]=e['exit_ms']
    return expected,excluded


def choice(e,policy):return (e['PZ_side'],e['PZ_status']) if policy=='PZ' else (1 if policy=='THROUGH' else -1,e['PZ_status'])


def exposure_max(entries,policy,fee,notional,only_certain):
    active=[];reserved=F(0);count_max=0;reserve_max=F(0)
    for i,e in enumerate(entries):
        side,status=choice(e,policy)
        if not side or status not in (('certain',) if only_certain else ('certain','ambiguous')):continue
        while active and active[0][0]<=e['entry_ms']:
            _,_,old=heapq.heappop(active);reserved-=old
        required=notional+6*notional*(e['cost_hi']+F(fee)/10000)
        heapq.heappush(active,(e['exit_ms'],i,required));reserved+=required
        count_max=max(count_max,len(active));reserve_max=max(reserve_max,reserved)
    return count_max,reserve_max


def audit(out):
    c=Check();spec=(LANE/'PREREG.md').read_text();c.eq(sha(LANE/'PREREG.md'),(LANE/'PREREG.sha256').read_text().strip(),'freeze')
    for name in ('code_inputs.json','inputs.json','fixtures.json','sources.json'):
        c.eq(sha(LANE/name) in spec,True,'bound '+name)
        p=LANE/name;c.eq(subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT),p.read_bytes(),'committed '+name)
    for name in ('code_inputs.json','inputs.json'):
        for path,digest in read(LANE/name)['sha256'].items():c.eq(sha(ROOT/path),digest,'identity '+path)
    config=read(LANE/'fixtures.json');result=read(out/'results.json');expected,excluded=raw_rows(config)
    saved=[json.loads(line) for line in gzip.decompress((out/'events.jsonl.gz').read_bytes()).splitlines()]
    c.eq(len(saved),len(expected),'retained events')
    for a,b in zip(saved,expected):c.eq(a,wire(b),'source row '+b['id'])
    c.eq(result['excluded_counts'],excluded,'original noncohort rows retained upstream')
    c.eq(result['event_rows'],len(expected),'event count');identities=[];frontiers=[];notional=F(config['entry_notional']);capital=F(config['capital'])
    for p in config['policies']:
        sure=[e for e in expected if choice(e,p)[1]=='certain' and choice(e,p)[0]]
        maybe=[e for e in expected if choice(e,p)[1]=='ambiguous' and choice(e,p)[0]]
        gsum=sum((choice(e,p)[0]*e['g'] for e in sure),F(0)) if all(e['g'] is not None for e in sure) else None
        for k in config['cost_multiples']:
            frontiers.append((p,k));row=next(x for x in result['fee_frontiers'] if x['policy']==p and x['cost_multiple']==k)
            c.eq(row['certain_count'],len(sure),'frontier cohort');c.eq(row['ambiguous_count'],len(maybe),'frontier ambiguities')
            for key,cost in (('certain_cohort_additional_fee_bp_lo','cost_hi'),('certain_cohort_additional_fee_bp_hi','cost_lo')):
                value=None if not sure or gsum is None else 10000*(gsum-F(2*k)*sum((e[cost] for e in sure),F(0)))/(2*k*len(sure))
                c.num(row[key],value,key)
            c.eq(row['whole_policy_threshold_known'],not maybe and gsum is not None,'whole-policy threshold scope')
            c.eq(row['actual_owner_fee_bp'],None,'no fee proof')
        for f in config['additional_fee_bp']:
            lower_count,lower_reserve=exposure_max(expected,p,f,notional,True);upper_count,upper_reserve=exposure_max(expected,p,f,notional,False)
            for k in config['cost_multiples']:
                identities.append((p,f,k));row=next(x for x in result['cost_cells'] if (x['policy'],x['additional_fee_bp'],x['cost_multiple'])==(p,f,k))
                low=F(0);high=F(0);missing=0
                for e in expected:
                    side,status=choice(e,p)
                    if not side or status in ('inactive','inactive_missing_prediction'):continue
                    if e['g'] is None:missing+=1;continue
                    candidates=[side*e['g']-2*k*(cost+F(f)/10000) for cost in (e['cost_lo'],e['cost_hi'])]
                    if status=='ambiguous':candidates.append(F(0))
                    low+=min(candidates);high+=max(candidates)
                low=None if missing else low*notional;high=None if missing else high*notional
                for name,value in (('proxy_quote_total_lo',low),('proxy_quote_total_hi',high),('proxy_quote_per_calendar_day_lo',None if low is None else low/(D1-D0)),('proxy_quote_per_calendar_day_hi',None if high is None else high/(D1-D0))):c.num(row[name],value,name)
                for name,key in (('proxy_mean_per_trade_bp_lo','cost_hi'),('proxy_mean_per_trade_bp_hi','cost_lo')):
                    value=None if not sure or gsum is None else (gsum-2*k*(sum((e[key] for e in sure),F(0))+F(f)/10000*len(sure)))*10000/len(sure)
                    c.num(row[name],value,name)
                c.eq(row['certain_count'],len(sure),'certain entries');c.eq(row['ambiguous_count'],len(maybe),'ambiguous entries');c.eq(row['missing_active_payoff_count'],missing,'missing payoffs not zero')
                c.num(row['same_initial_capital'],capital,'whole capital once');c.num(row['entry_notional_scale'],notional,'fixed scale');c.eq(row['days'],D1-D0,'all inactive days included')
                exp=row['exposure']
                for name,value in (('maximum_certain_count',lower_count),('maximum_possible_count',upper_count),('original_notional_floor_certain',lower_count*notional),('original_notional_floor_possible',upper_count*notional),('three_times_roundtrip_reserve_ceiling_certain',lower_reserve),('three_times_roundtrip_reserve_ceiling_possible',upper_reserve)):c.num(exp[name],value,name)
                c.eq(exp['marked_risk_and_actual_capital_sufficiency'],None,'no invented marked risk');c.eq(exp['actual_account_nav'],None,'not an account return')
                c.eq([x['annual_scenario'] for x in row['cash_comparisons']],config['cash_annual_scenarios'],'all cash controls')
                for cash in row['cash_comparisons']:
                    value=capital*F(cash['annual_scenario'])*F(D1-D0,365);c.num(cash['same_capital_simple_interest'],value,'benchmark whole capital')
                    c.num(cash['conditional_excess_lo'],None if low is None else low-value,'excess lower');c.num(cash['conditional_excess_hi'],None if high is None else high-value,'excess upper')
                c.eq(row['actual_executable_expected_net'],None,'no expected gain');c.eq(row['new_strategy_activation_allowed'],False,'no activation')
    c.eq([(x['policy'],x['additional_fee_bp'],x['cost_multiple']) for x in result['cost_cells']],identities,'all27cells')
    c.eq([(x['policy'],x['cost_multiple']) for x in result['fee_frontiers']],frontiers,'all9frontiers')
    doc=result['documentation_fee_view'];c.eq(doc['published_taker_decimal'],'0','literal public example')
    c.eq(doc['conditional_fraction_hypothesis_bp'],None,'decimal scaling not assumed');c.eq(doc['owner_entitlement_verified'],False,'example not owner')
    c.eq(doc['opportunity_fee_bp'],None,'example cannot supply fee');c.eq('outside_published_fixed_period' in doc['flags'],True,'old example not current')
    probe=result['native_guard'];c.eq(probe['before']['rows'][0]['conditional_batch_inclusion'],True,'invented positive control')
    c.eq(probe['after']['rows'][0]['conditional_batch_inclusion'],False,'public-zero guard')
    c.eq(probe['after']['account_before'],probe['after']['account_after'],'no forecast cash')
    c.eq('cost:fee_unknown' in probe['after']['rows'][0]['reasons'],True,'actual native fee reason')
    for key,value in (('registry_id','R345'),('diagnostic_variants',9),('new_market_or_history_requests',0),('new_prospective_strategy_days',0),('actual_executable_expected_net',None),('activation_allowed',False),('paper_account_credited',False),('raw_R336_reproduction_claimed',False)):c.eq(result[key],value,key)
    receipt=read(LANE/'source_receipts.json');c.eq(receipt['attempts_used'],2,'finite source attempts');c.eq(receipt['body_bytes'],70442,'actual source bytes');c.eq(receipt['budget_closed'],True,'source budget closed')
    c.eq(receipt['redirects_followed'],0,'no redirects');c.eq(receipt['retries'],0,'no retries');c.eq(receipt['actual_private_account_fee_market_history_requests'],0,'no actual fee endpoint')
    for row in receipt['records']:c.eq(row['url'].startswith('https://www.mexc.com/api-docs/'),True,'static documentation only')
    return {'registry_id':'R345','status':'PASS','independent_checks':c.count,'event_rows':len(expected),'cost_cells':len(identities),'fee_frontiers':len(frontiers),'actual_executable_expected_net':None}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    print(json.dumps(audit(parser.parse_args().out),sort_keys=True,indent=2))
