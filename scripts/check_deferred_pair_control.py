"""R361 independent arithmetic and R360 retained failure/account evidence.

Only standard-library modules and the frozen independent R360 checker are used;
no production account, pricing, state, risk or controller function is imported.
"""
import argparse
from fractions import Fraction as F
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
LANE = ROOT / 'experiments/deferred_pair_control_v1'
SOURCE = ROOT / 'experiments/live_pair_controls_v1'
PARENT = ROOT / 'experiments/incremental_pair_control_v1'


def helper():
    spec = importlib.util.spec_from_file_location('_r361_private_independent', Path(__file__).with_name('check_incremental_pair_control.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_money(core, config, c=None):
    h = helper(); c = c or h.Check()
    c.eq(core['registry_id'],'R359','original control identity')
    c.eq(len(core['cells']),36,'all fixed cost cells')
    c.eq(core['prospective_strategy_days'],0,'no qualified new strategy days')
    c.eq(core['full_net_pnl'],None,'no fabricated complete net')
    receipts={r['stage']:r for r in core['online_receipts']}
    quantities={};outcomes=[]
    for cell in core['cells']:
        for key in ('full_net_pnl','funding_cash','full_account_nav','actual_expected_net'):
            c.eq(cell[key],None,key+' remains unknown')
        c.eq(cell['price_fee_fx_scenario'],{'USDC':'1','USDT':'1'},'original explicit FX scenario')
        c.eq(cell['cost_multiple'] in (1,2,3),True,'fixed cost tiers')
        accounts=cell['price_fee_only_native_snapshot']['accounts']
        c.eq({(a['venue'],a['asset']) for a in accounts},
             {('mexc','USDT'),('lighter','USDC')},'separate native assets')
        for account in accounts:
            c.near(account['initial_cash'],F(config['capital_per_venue']),'full segregated capital')
        if cell['closed_price_fee_subtotal'] is None:continue
        symbol,direction,k=cell['symbol'],cell['direction'],cell['cost_multiple']
        q=F(cell['quantity']);c.eq(q>0,True,'original positive quantity')
        identity=symbol,direction
        if identity in quantities:c.eq(q,quantities[identity],'same quantity at all costs')
        quantities[identity]=q;total=F(0)
        entry=receipts['entry_execution']['views'][symbol]['books']
        exit_=receipts['exit_execution']['views'][symbol]['books']
        for venue,signed,a,b in zip(('mexc','lighter'),(-direction*q,direction*q),entry,exit_):
            pa,pb=h.sweep(a,signed),h.sweep(b,-signed)
            # The frozen contract supplies a descriptive binary-float midpoint
            # converted to decimal text as the stress anchor. Preserve THAT
            # input convention; do not substitute a different exact mean.
            ma=F(str((float(a['bids'][0][0])+float(a['asks'][0][0]))/2))
            mb=F(str((float(b['bids'][0][0])+float(b['asks'][0][0]))/2))
            pa,pb=ma+k*(pa-ma),mb+k*(pb-mb)
            fees=q*(pa+pb)*F(config['fees_bp'][venue])*k/10000
            gross=signed*(pb-pa);expected=gross-fees
            native=next(r for r in accounts if r['venue']==venue)
            c.near(native['realized_price_pnl'],gross,'independent native price change')
            c.near(native['fees_paid'],fees,'independent all entry/exit fees')
            c.near(native['known_realized_net_component'],expected,'independent native price-fee component')
            c.near(native['known_cash_component'],F(config['capital_per_venue'])+expected,'native cash conservation')
            c.eq(native['positions'],[],'exit flattens original inventory')
            close=cell['exit'][venue]
            c.near(close['quantity'],-signed,'exact opposite exit quantity')
            c.eq(close['model_action_clock'],receipts['exit_execution']['decision_clock'],'old action clock')
            c.eq(close['source_first_seen_clock'],b['clock'],'old quote clock')
            total+=expected
        c.near(cell['closed_price_fee_subtotal'],total,'independent closed component')
        c.near(cell['funding_needed_to_break_even'],-total,'funding break-even component only')
        outcomes.append({'id':cell['id'],'quantity':cell['quantity'],
            'closed_price_fee_subtotal':cell['closed_price_fee_subtotal'],
            'funding_needed_to_break_even':cell['funding_needed_to_break_even']})
    return c,outcomes


def retained_r360(c, h, config, expected, old_files):
    manifest = json.loads((PARENT / 'retained_outputs.json').read_text())
    data = (PARENT / manifest['packed_file']).read_bytes()
    c.eq(hashlib.sha256(data).hexdigest(), manifest['packed_sha256'], 'R360 failure pack identity')
    with tarfile.open(fileobj=io.BytesIO(gzip.decompress(data)), mode='r:') as tar:
        members = {m.name:tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
    c.eq({p:hashlib.sha256(b).hexdigest() for p,b in members.items()}, manifest['sha256'], 'R360 complete retained inventory')
    c.eq(json.loads(members['failure.json'])['scope_closed'], True, 'R360 finite scope stopped')
    c.eq(manifest['timing_receipts_available'], False, 'no invented missing R360 measurements')
    count = 0
    for prefix in sorted(p.rsplit('/',1)[0] for p in members if p.endswith('/core_result.json')):
        raw = members[prefix+'/core_result.json']
        c.eq(raw, expected, 'R360 old report remains exact after budget failure')
        check_money(json.loads(raw), config, c)
        files = {p.split('/online/',1)[1]:b for p,b in members.items() if p.startswith(prefix+'/online/')}
        c.eq(files, old_files, 'R360 every original native/receipt byte')
        count += 1
    c.eq(count, 10, 'all old fixed profile runs retained')
    return {'registry_id':'R360', 'status':'PARTIAL_BUDGET_STOP', 'retained_profile_runs':count,
            'complete_results_and_38_native_files_each_exact':True, 'old_timing_data_recovered':False}


def run(directory, out):
    out.mkdir(exist_ok=False)
    h = helper(); c = h.Check()
    for path, expected in json.loads((LANE/'input_identity.json').read_text())['sha256'].items():
        c.eq(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(), expected, 'bound input:'+path)
    benchmark = json.loads((directory/'benchmark.json').read_text())
    c.eq(benchmark['registry_id'], 'R361', 'new outer validation identity')
    c.eq(benchmark['new_alpha_variants'], 0, 'no new predictive trial')
    c.eq(benchmark['new_prospective_tickets'], 0, 'no new first-seen proof')
    c.eq(len(benchmark['runs']), 10, 'fixed five paired repetitions')
    c.eq(benchmark['depth_equivalence']['comparisons'], 896, 'all 64prefix comparisons completed')
    expected = (SOURCE/'results.json').read_bytes()
    old_files = {p.name:p.read_bytes() for p in (SOURCE/'evidence/online').iterdir() if p.is_file()}
    config = json.loads((SOURCE/'config.json').read_text())
    parent = retained_r360(c,h,config,expected,old_files)
    outcomes = None
    for r in benchmark['runs']:
        path = directory/f"{r['repetition']:02d}_{r['profile']}"
        c.eq(json.loads((path/'measurement.json').read_text()), r, 'durable measured run receipt')
        raw = (path/'core_result.json').read_bytes()
        c.eq(raw, expected, 'exact old complete account/receipt report')
        c.eq(hashlib.sha256(raw).hexdigest(), r['core_result_sha256'], 'report hash')
        files = {p.name:p.read_bytes() for p in (path/'online').iterdir() if p.is_file()}
        c.eq(set(files), set(old_files), 'all old native/receipt files retained')
        for name,data in files.items():
            c.eq(data, old_files[name], 'exact old native/receipt bytes')
            c.eq(hashlib.sha256(data).hexdigest(), r['journal_and_receipt_sha256'][name], 'measured hash')
        c, outcomes = check_money(json.loads(raw), config, c)
        c.eq(r['preprocessing']['n'],2352,'every receive service measured including tail')
        for stage, old in zip(r['stages'], json.loads(raw)['online_receipts']):
            c.eq(stage['original_on_time'], old['on_time'], 'original lateness unchanged')
            c.eq(stage['original_issued_clock'], old['issued_clock'], 'original issued clock unchanged')
            c.eq(stage['timeliness_reclassified'], False, 'no offline timing rescue')
            c.eq(stage['processing_and_io_ns'] > 0,True,'positive actual local service sample')
    result = {'registry_id':'R361','status':'PASS','checks':c.n,'parent_R360':parent,
        'benchmark_sha256':hashlib.sha256((directory/'benchmark.json').read_bytes()).hexdigest(),
        'all_ten_new_reports_and_38_files_each_exact':True,'closed_components':outcomes,
        'money_oracle':'independent frozen Fraction level sweep, fees, fixed q and native capital',
        'independent_venue_parser':False,'actual_expected_net':None,'full_net_pnl':None,
        'new_prospective_tickets':0,'new_alpha_variants':0}
    with (out/'audit.json').open('xb') as f:f.write(h.encoded(result))
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();result=run(args.run,args.out)
    print(json.dumps({'registry_id':'R361','status':result['status'],'checks':result['checks']}))
