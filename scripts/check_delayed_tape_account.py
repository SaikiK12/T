"""Independent stdlib source-clock, bucket, cost and native-account checker."""
import argparse
import csv
from datetime import datetime, timezone
from collections import defaultdict
from decimal import Decimal as D
from fractions import Fraction as F
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
LANE=ROOT/'experiments/delayed_tape_account_v1'
OLD=ROOT/'experiments/warm_values_v1/evidence'


def load(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes(),parse_float=D)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


class Checks:
    def __init__(self):self.count=0
    def eq(self,a,b,label):
        self.count+=1
        if a!=b:raise AssertionError(label+': '+str(a)[:120]+' != '+str(b)[:120])
    def yes(self,x,label):self.eq(x,True,label)


def chain(content,c):
    previous='0'*64;out=[]
    c.yes(content.endswith('\n'),'complete native journal tail')
    for i,line in enumerate(content.splitlines()):
        row=json.loads(line);digest=row.pop('sha256')
        c.eq(row['sequence'],i,'journal sequence');c.eq(row['previous_sha256'],previous,'predecessor')
        text=json.dumps(row,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        c.eq(hashlib.sha256(text).hexdigest(),digest,'journal hash');previous=digest;out.append(row['event'])
    return out


def audit(out):
    c=Checks();spec=LANE/'PREREG.md'
    c.eq(sha(spec),(LANE/'PREREG.sha256').read_text().strip(),'frozen spec')
    for n in ('code_inputs.json','inputs.json','config.json','sources.json'):
        c.yes(sha(LANE/n) in spec.read_text(),'bound '+n)
        c.eq(subprocess.check_output(['git','show','HEAD:'+str((LANE/n).relative_to(ROOT))],cwd=ROOT),(LANE/n).read_bytes(),'committed '+n)
    for n in ('code_inputs.json','inputs.json'):
        for p,h in load(LANE/n)['sha256'].items():c.eq(sha(ROOT/p),h,'input '+p)
    result=load(out/'results.json.gz');cfg=load(LANE/'config.json');summary=load(LANE/'source/R348_summary.json')
    with gzip.open(OLD/'mexc.jsonl.gz','rt') as h:frames={x['number']:x for x in map(json.loads,h)}
    metadata=load(OLD/'metadata.json')['metadata'];anchor=load(OLD/'anchor.json')
    packets=0;complete=0
    for profile in result['timing']:
        accepted=[e for e in profile['receipts'] if e['status']=='accepted']
        by_key=defaultdict(list);previous={};ofi=defaultdict(float)
        for e in accepted:
            number=int(e['source_identity'].split('-')[2]);frame=frames[number];payload=json.loads(frame['raw']);d=payload['data']
            c.eq(payload['channel'],'push.depth.full','actual native depth source')
            coin=payload['symbol'][:-5];stamp=d.get('cts') if d.get('cts') is not None else payload.get('ts')
            c.eq(e['source_ms'],int(stamp),'own source timestamp')
            c.eq(e['symbol'],coin,'symbol identity')
            c.eq(e['first_seen_clock'],{'utc_ns':frame['utc_ns'],'mono_ns':frame['mono_ns']},'original first-seen clock')
            c.eq(e['observed_clock'],e['first_seen_clock'],'unique frame first receipt')
            key=(coin,int(stamp)//1000*1000)
            bids=sorted(d['bids'],key=lambda x:float(x[0]),reverse=True);asks=sorted(d['asks'],key=lambda x:float(x[0]))
            size=float(metadata[coin]['mexc']['contractSize'])
            # Native DepthLevel.base_quantity multiplies float level volume by float size.
            cur=(float(bids[0][0]),float(bids[0][1])*size,float(asks[0][0]),float(asks[0][1])*size)
            if coin in previous:
                pb,pbs,pa,pas=previous[coin];b,bs,a,az=cur
                ofi[key]+=(bs if b>=pb else 0)-(pbs if b<=pb else 0)-(az if a<=pa else 0)+(pas if a>=pa else 0)
            previous[coin]=cur;by_key[key].append((e,cur))
        for p in profile['packets']:
            packets+=1;complete+=int(p['complete']);row=p['row'];key=(p['symbol'],p['second_ms']);group=by_key.pop(key)
            c.eq(p['source_identities'],[e['source_identity'] for e,_ in group],'every contributing first-seen identity')
            max_clock=max((e['first_seen_clock'] for e,_ in group),key=lambda x:x['mono_ns'])
            c.eq(p['max_received_clock'],max_clock,'maximum contributing receive clock')
            for field,value in zip(('bid','bid_sz','ask','ask_sz'),group[-1][1]):
                c.yes(abs(float(row[field])-value)<=1e-12*max(1,abs(value)),'last source book '+field)
            c.eq(row['n'],len(group),'update count')
            c.yes(abs(float(row['ofi'])-ofi[key])<=1e-10*max(1,abs(ofi[key])),'independent OFI contributions')
            c.eq(row['bid_sz5'],None,'unreceived optional full5 feature remains unknown')
            c.eq(row['ask_sz5'],None,'unreceived optional full5 feature remains unknown')
            final=p['finalized_clock'];c.yes(final['mono_ns']>=max_clock['mono_ns'],'no pre-receipt finalization')
            last_frame=max(frames.values(),key=lambda f:f['mono_ns'])
            if final['mono_ns']==last_frame['mono_ns']:
                c.eq(final,{'mono_ns':last_frame['mono_ns'],'utc_ns':last_frame['utc_ns']},'original terminal receipt clock')
            else:
                c.eq(final['utc_ns']-anchor['utc_ns'],final['mono_ns']-anchor['mono_ns'],'constructed timer clock mapping')
            end=(p['second_ms']+1000)*10**6
            c.eq(p['finalization_after_second_end_ns'],final['utc_ns']-end,'separate finalization delay')
            mature=final['utc_ns']>=end+2000*10**6
            if not mature:c.yes('terminal_bucket_before_settlement_grace' in p['reasons'],'terminal uncertainty retained')
            c.eq(p['complete'],not bool(p['reasons']),'complete exactly when no quality reason')
            c.eq(p['at_exchange_second_end']['finalized_feature_known'],False,'no final aggregate known at exchange-second end')
            c.eq(p['legacy_availability']['finalized_feature_known'],None,'legacy arrival not invented')
            c.eq(p['actual_execution_ready'],False,'no actual execution attestation')
            c.eq(p['processing_clock_kind'],'constructed_replay_schedule_not_measured_production','constructed processing label')
        c.eq(dict(by_key),{},'all accepted groups retained')
    cells={(x['policy'],x['cost_multiple']):x for x in result['reported_cost_intervals']}
    c.eq(len(cells),18,'all six old variants and all costs')
    for policy,tr in summary['trials_detail'].items():
        for k in (1,2,3):
            cell=cells[policy,k];point=F(tr[str(k)+'x']['per_trade_bp']);delta=F(1,2000);scale=F(cfg['hypothetical_mid_notional'])*tr['trades']/10000
            c.eq(list(map(F,cell['published_mean_bp_interval'])),[point-delta,point+delta],'rounded published mean interval')
            c.eq(list(map(F,cell['completed_subset_published_proxy_quote_interval'])),[(point-delta)*scale,(point+delta)*scale],'known-subset old-convention proxy')
            c.eq(cell['missing_exit_count'],tr['skips']['exit_quote'],'unknown exits retained')
            c.eq(cell['full_policy_account_pnl'],None,'no full policy account from a summary')
            c.eq(cell['first_seen_input_clocks_verified'],False,'no source clock claim')
            c.eq(cell['trade_export_received'],True,'new explicit UTF8 input received')
    manifests=load(LANE/'source/hashes.json')['files']
    for item in manifests:
        p=LANE/'source'/item['file'];c.eq(sha(p),item['sha256'],'producer UTF8 hash')
        c.eq(p.stat().st_size,item['bytes'],'producer UTF8 length')
    for model in result['completed_subset_accounts']:
        policy=model['policy'];k=model['cost_multiple']
        with (LANE/'source'/('trades_'+policy+'.csv')).open(newline='') as h:rows=list(csv.DictReader(h))
        c.eq(len(rows),summary['trials_detail'][policy]['trades'],'exact saved row count')
        events=[];pnls=[];oldnets=[]
        for i,row in enumerate(rows):
            side=int(row['side']);g,ce,cx=map(F,(row['gross'],row['c_e'],row['c_x']))
            ratio=1+side*g/10000;entry=100*(1+side*k*ce/10000);exit=100*ratio*(1-side*k*cx/10000)
            pnl=side*10*(exit-entry);pnls.append(pnl);oldnet=g-k*(ce+cx);oldnets.append(oldnet)
            c.yes(abs(F(row['net'+str(k)])-oldnet)<=F(1,10**10),'saved floating proxy versus exact serialized components')
            c.eq(F(model['per_trade_exact_pnl'][i]),pnl,'exit-midpoint crossing cash')
            c.eq(F(model['per_trade_exact_bp'][i]),pnl*10,'same midpoint notional')
            c.eq(F(model['per_trade_old_proxy_bp'][i]),oldnet,'old return convention')
            start=int(datetime.fromisoformat(row['day']).replace(tzinfo=timezone.utc).timestamp())*10**9
            en=start+(int(row['e'])+1)*10**9;ex=start+(int(row['x'])+1)*10**9
            events.extend([(en,1,row['coin'],i,entry),(ex,0,row['coin'],i,exit)])
        events.sort(key=lambda x:x[:4]);cash=F(10000);open_rows={};blocked=[];peak=F(0);audit=[]
        for at,phase,coin,i,price in events:
            locked=sum((10*v for v in open_rows.values()),F(0))
            if phase==1:
                if cash-locked<10*price:
                    blocked.append(i);audit.append((i,'open','blocked_initial_notional_capital',at,None,None));continue
                open_rows[i]=price
            elif i in open_rows:
                cash+=int(rows[i]['side'])*10*(price-open_rows.pop(i))
            else:continue
            after=sum((10*v for v in open_rows.values()),F(0));peak=max(peak,after)
            audit.append((i,'open' if phase else 'close','applied',at,cash,after))
        c.eq(model['blocked_rows'],blocked,'one shared capital cannot be reused')
        c.eq(F(model['peak_entry_notional_reservation']),peak,'peak entry capital floor')
        c.eq(len(model['event_audit']),len(audit),'full completed-subset event chronology')
        for actual,expected in zip(model['event_audit'],audit):
            i,phase,status,at,money,locked=expected
            c.eq((actual['row'],actual['phase'],actual['state'],actual['time_ns']),(i,phase,status,at),'native event identity and ordering')
            if money is not None:
                c.eq(F(actual['cash_after']),money,'native shared account cash')
                c.eq(F(actual['locked_after']),locked,'native notional reserved once')
        snap=model['completed_subset_native_snapshot']
        c.eq(F(snap['cash']),cash,'final native cash from independent tickets')
        c.eq(F(snap['realized_net_pnl']),cash-10000,'whole initial capital denomination')
        c.eq(open_rows,{},'completed subset flat only')
        c.eq(model['whole_policy_pnl'],None,'unlocated unknown exits never turn into full policy cash')
        c.eq(model['original_first_seen_clocks_available'],False,'exchange-grid model clock not source first-seen')
        c.eq(model['actual_expected_net'],None,'no prospective expectancy')
    packed=load(out/'journals.json.gz')
    c.eq(len(packed),12,'six native account/risk journal pairs')
    for path,content in packed.items():c.eq((out/path).read_text(),content,'persisted native journal matches pack')
    for case in result['native_cases']:
        k=case['cost_multiple'];gap=case['missing_exit'];prefix='native-'+str(k)+'-'+str(int(gap))+'/'
        events=chain(packed[prefix+'account.jsonl'],c);risk=chain(packed[prefix+'risk.jsonl'],c)
        c.eq(len(events),2 if gap else 3,'missing exit never produces a fictitious close')
        c.eq(len(risk),2,'one persistent risk observation')
        a=case['snapshot']['accounts'][0];c.eq(F(a['initial_cash']),F(10000),'same full capital')
        if gap:
            c.eq(a['nav'],None,'unknown exit means unknown NAV')
            c.eq(F(a['cash']),F(10000),'open principal not a cash loss or gain')
            c.eq(F(a['locked_capital']),F(1000)+F(k,25),'entry-notional reserve retained')
            c.eq(len(a['positions']),1,'unknown open exposure retained')
            c.eq(case['risk']['model_new_entries_allowed'],False,'risk stops after unknown exit')
        else:
            expected=-F(2*k,25)
            c.eq(F(a['realized_net_pnl']),expected,'exact supplied crossing loss once')
            c.eq(F(a['nav']),10000+expected,'closed native account identity')
            c.eq(a['positions'],[],'known close flat')
        c.eq(case['risk']['automatic_flatten_performed'],False,'no invented risk close')
        c.eq(case['all_prices_clocks_zero_fees_invented'],True,'fixture provenance')
        c.eq(case['actual_r348_account_replayed'],False,'no borrowed trading evidence')
    for key,value in [('all_R348_six_utf8_exports_received',True),('original_compressed_exports_received',False),('R348_full_trade_or_capital_reproduction',False),('new_predictive_variants',0),('new_prospective_strategy_days',0),('activation_allowed',False),('actual_executable_expected_net',None),('new_market_requests',0)]:c.eq(result[key],value,key)
    outc={'registry_id':'R350','status':'PASS','checks':c.count,'profile_packets':packets,'complete_profile_packets':complete,'cost_cells':18,'native_cases':6,'actual_r348_account_reproduced':False}
    with (out/'audit.json').open('x') as h:json.dump(outc,h,sort_keys=True,indent=2);h.write('\n')
    return outc


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True,type=Path)
    print(json.dumps(audit(p.parse_args().out),indent=2))
