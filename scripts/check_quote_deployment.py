"""Read-only R429 canonical-state receipt/hash audit; never invokes a native writer or scores PnL."""
import argparse,gzip,hashlib,json,subprocess
from pathlib import Path
from datetime import datetime,timezone

p=argparse.ArgumentParser();p.add_argument('--ref',default='origin/codex/quant-runtime-state');p.add_argument('--out',required=True);a=p.parse_args()
root=Path.cwd();ref=a.ref

def blob(name):return subprocess.check_output(['git','show',ref+':'+name])
def sha(raw):return hashlib.sha256(raw).hexdigest()
manifest_raw=blob('manifest.json');m=json.loads(manifest_raw)
assert m['active_contract']=='R429','not selected R429'
names=list(m['files'])
proc=subprocess.Popen(['git','cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
out,_=proc.communicate(('\n'.join(ref+':state/'+n for n in names)+'\n').encode());assert proc.returncode==0
files={};offset=0
for name in names:
 end=out.index(b'\n',offset);head=out[offset:end].split();assert len(head)==3 and head[1]==b'blob',name
 size=int(head[2]);start=end+1;raw=out[start:start+size];assert len(raw)==size and out[start+size:start+size+1]==b'\n';offset=start+size+1
 assert sha(raw)==m['files'][name]['sha256'],name
 files[name]=raw
assert offset==len(out)
ops='data/operations/quant_quote_scope_v1/'
previous='data/operations/quant_participant_v1/'
lane=root/'experiments/paper_quote_scope_v1'
base=files[ops+'aux_baseline.jsonl']; frozen=(lane/'aux_baseline_at_registration.jsonl').read_bytes();assert base.startswith(frozen)
assert files['data/recorders/participant_windows_v1/events.jsonl']==(lane/'r428_source_events_at_registration.jsonl').read_bytes()
current=files.get(ops+'network/aux/requests.jsonl',b'');combined=base+current
starts={};ends={};contents={}
for line in combined.splitlines():
 row=json.loads(line);event=row['event']
 if event=='START':assert row['id'] not in starts;starts[row['id']]=row
 elif event=='END':assert row['id'] in starts and row['id'] not in ends;ends[row['id']]=row
assert set(starts)==set(ends)=={str(i) for i in range(len(starts))}
charged=sum(r['charged_bytes'] for r in ends.values());assert charged>=16384014 and charged<=16777216
new_wire=0
for line in current.splitlines():
 row=json.loads(line)
 if row['event']!='CONTENT':continue
 rid=row['id'];wire=gzip.decompress(files[ops+'network/aux/'+row['stored_wire']])
 assert len(wire)==row['wire_bytes'] and sha(wire)==row['wire_sha256']
 assert sha(wire)==ends[rid]['body_sha256']
 assert row['content_encoding'] in ('','identity','gzip')
 decoded=gzip.decompress(wire) if row['content_encoding']=='gzip' else wire
 assert len(decoded)==row['content_bytes'] and sha(decoded)==row['content_sha256']
 contents[rid]=row;new_wire+=len(wire)
views=[]
for line in files.get(ops+'network/aux/quote_views.jsonl',b'').splitlines():
 view=json.loads(line);assert view['native_lookback_days']==400 and view['source_body_unchanged'] is True
 matched=[r for rid,r in contents.items() if starts[rid]['url']==view['physical_url'] and r['content_sha256']==view['body_sha256']]
 assert matched,'unmatched quote-view/content receipt';views.append(view)
report=json.loads(files[ops+'latest.json']);native={};prefixes=0
for rid,folder in [('R413','boroslock_fwd'),('R406','lockcarry_fwd2')]:
 prefix='experiments/'+folder+'/journal/'
 status=json.loads(files[prefix+'status.json'])
 native[rid]={k:status.get(k) for k in ['updated','ticks','locks','settled']}
 for suffix in ['offers.csv','locks.csv','settlements.csv','tbill.csv']:
  name=prefix+suffix
  if name in files:
   before=subprocess.run(['git','show','d2e61e73a8d88c8901885cdc19c99c59a850fd02:state/'+name],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
   if before.returncode==0:assert files[name].startswith(before.stdout),name;prefixes+=1
packet_paths=sorted(n for n in names if n.startswith('data/recorders/eea_pair_capture_v1/packets/') and n.endswith('/packet.json'))
last_packet=packet_paths[-1];packet=json.loads(files[last_packet])
receipt=dict(state='SELECTED_NATIVE_RECEIPTS_AUDITED',accessed_utc=datetime.now(timezone.utc).isoformat(),
 state_commit=subprocess.check_output(['git','rev-parse',ref],text=True).strip(),manifest_sha256=sha(manifest_raw),
 active_contract=m['active_contract'],prereg_sha256=m['quote_scope_prereg_sha256'],verified_manifest_hashes=len(names),
 inherited_aux_baseline_sha256=sha(base),inherited_prefix_preserved=True,all_requests_paired=True,
 cumulative_aux_calls=len(starts),cumulative_aux_charged_bytes=charged,remaining_original_aux_bytes=16777216-charged,
 original_aux_max_bytes=16777216,original_aux_max_calls=4096,no_reset=True,
 new_wire_content_pairs_verified=len(contents),new_encoded_body_bytes=new_wire,quote_view_receipts=views,
 native_journal_prefixes_verified=prefixes,native_status=native,
 native_dispatch={k:report.get(k) for k in ['state','run_id','hour','tasks','health']},
 native_recovery_observed=all(datetime.fromisoformat(s['updated'].replace('Z','+00:00')).strftime('%Y%m%dT%H')==report['hour'] for s in native.values()) and len(views)>0,
 latest_r419_packet=dict(path=last_packet,sha256=sha(files[last_packet]),state=packet.get('state'),
   source_http_requests=packet.get('requests'),body_bytes=packet.get('body_bytes')),
 r428_source_block_unchanged=True,source_http_requests_by_this_audit=0,predictive_trials=0,
 costs={'1x':'N/A','2x':'N/A','3x':'N/A'},settled_income_proven=False)
Path(a.out).write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k not in ['quote_view_receipts','native_dispatch']},indent=2))
