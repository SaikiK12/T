"""Independent stdlib R346 raw journal, marked collateral and margin oracle.

No production financial, risk, reporting or selector module is imported.
The same supplied market inputs and interpretation are not independent evidence
of actual venue liquidation behavior or positive expected return.
"""
import argparse
from decimal import Decimal
from fractions import Fraction as F
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LANE = ROOT / 'experiments/carry_risk_v1'
PARENT = ROOT / 'experiments/same_venue_carry_v2'
RAW = ROOT / 'experiments/same_venue_carry_v1/evidence'


def load(path):
    b = path.read_bytes()
    return json.loads(gzip.decompress(b) if path.suffix == '.gz' else b, parse_float=Decimal)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Checks:
    def __init__(self):
        self.n = 0

    def eq(self, a, b, label):
        self.n += 1
        if a != b:
            raise AssertionError(label + ': ' + str(a)[:180] + ' != ' + str(b)[:180])

    def yes(self, a, label):
        self.eq(a, True, label)

    def num(self, a, b, label):
        self.eq(None if a is None else F(a), b, label)


def chain(content, c):
    previous = '0' * 64
    events = []
    c.yes(content.endswith('\n'), 'complete journal tail')
    for i, line in enumerate(content.splitlines()):
        row = json.loads(line)
        sha = row.pop('sha256')
        c.eq(row['sequence'], i, 'sequence')
        c.eq(row['previous_sha256'], previous, 'predecessor')
        canonical = json.dumps(row, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        c.eq(hashlib.sha256(canonical).hexdigest(), sha, 'chain hash')
        events.append(row['event'])
        previous = sha
    return events


def rational_wire(x):
    return F(x['numerator'], x['denominator'])


def inverse(events, c):
    cfg = events[0]
    cash = initial = rational_wire(cfg['initial_coin'])
    face, numerator = F(0), F(0)
    for attempt in events[1:]:
        c.eq(attempt['kind'], 'inverse_model_attempt', 'parent inverse operation')
        e = attempt['payload']
        c.eq(e['kind'], 'open', 'parent only hypothetical opening fills')
        c.eq(e['simulation_only'], True, 'no actual fill certification')
        q, price, fee = rational_wire(e['signed_face_usd']), rational_wire(e['price_usd_per_coin']), rational_wire(e['fee_coin'])
        c.yes(q < 0 and price > 0 and fee >= 0, 'explicit short/fee/price units')
        numerator += q / price
        face += q
        cash -= fee
    return {'coin': cfg['contract']['coin'], 'initial': initial, 'cash': cash,
            'face': face, 'numerator': numerator, 'expiry_ns': cfg['contract']['expiry_ns'],
            'anchor_ns': cfg['anchor']['utc_ns']}


def spot(events, c):
    cfg = events[0]
    cash = F(cfg['initial_cash'])
    held = {coin: F(0) for coin in cfg['markets'].values()}
    c.eq(cash, 10000, 'same whole capital')
    c.eq(cfg['quote_asset'], 'USDC', 'quote asset')
    for attempt in events[1:]:
        c.eq(attempt['kind'], 'spot_model_attempt', 'spot operation')
        e = attempt['payload']
        c.eq(e['kind'], 'fill', 'spot fill')
        q, p, fee = F(e['quantity']), F(e['price']), F(e['fee_amount'])
        coin = cfg['markets'][e['market']]
        c.yes(q > 0 and p > 0 and fee >= 0, 'spot buy fee units')
        held[coin] += q
        cash -= q * p
        if e['fee_asset'] == coin:
            held[coin] -= fee
        else:
            c.eq(e['fee_asset'], 'USDC', 'quote fee identity')
            cash -= fee
    return cash, held


def check_leg(view, a, m, s, ix, denominator, c):
    equity = a['cash'] + a['numerator'] - a['face']/m
    c.eq(view['coin'], a['coin'], 'coin identity')
    c.num(view['coin_cash'], a['cash'], 'coin cash unchanged')
    c.num(view['signed_face_usd'], a['face'], 'signed face')
    c.num(view['unrealized_coin'], a['numerator']-a['face']/m, 'unrealized coin')
    c.num(view['coin_equity'], equity, 'total equity once')
    c.num(view['marked_value_usdc'], equity*s, 'coin-equity conversion')
    c.num(view['future_mark_over_index'], m/ix, 'mark index basis')
    c.eq(view['outside_documented_default_ten_percent_band'], abs(m/ix-1)>F(1,10), 'default band advisory')
    c.eq(view['denominator_control'], denominator, 'explicit denominator assumption')
    c.eq(view['actual_risk_ready'], False, 'no actual risk admission')
    c.eq(view['actual_executable_close_usdc'], None, 'no executable close assertion')
    margin = view['margin']
    c.eq(margin['actual_venue_margin_certified'], False, 'no venue attestation')
    if denominator == 'unknown':
        for k in ('initial_coin','maintenance_coin','initial_buffer_coin','maintenance_buffer_coin','initial_covered','maintenance_covered'):
            c.eq(margin[k], None, 'withheld unknown denominator '+k)
        c.eq(margin['reason'], 'inverse_conversion_denominator_unknown', 'unknown reason')
        return equity*s, None, None
    c.yes(abs(a['face']) <= 2250000, 'exact USD flat-segment domain')
    c.yes(a['expiry_ns']-a['anchor_ns'] > 1800*10**9, 'outside expiry transition')
    # Direct exact percentage reconstruction, not a production margin function.
    base = abs(a['face']) / (ix if denominator=='index' else m)
    im, mm = base/F(25), base*F(2,75)
    c.num(margin['initial_coin'], im, 'exact IM in settlement coin')
    c.num(margin['maintenance_coin'], mm, 'exact MM not rounded table')
    c.num(margin['initial_buffer_coin'], equity-im, 'IM buffer')
    c.num(margin['maintenance_buffer_coin'], equity-mm, 'MM buffer')
    c.eq(margin['initial_covered'], equity>=im, 'conditional IM comparison')
    c.eq(margin['maintenance_covered'], equity>=mm, 'conditional MM comparison')
    return equity*s, equity>=im, equity>=mm


def check_total(total, values, cash, complete, c):
    nav = cash + sum((x[0] for x in values), F(0)) if complete else None
    c.num(total['marked_nav_usdc'], nav, 'whole capital marked NAV')
    c.num(total['pnl_from_initial_usdc'], None if nav is None else nav-10000, 'PnL against full capital')
    c.num(total['return_on_all_initial_capital'], None if nav is None else nav/10000-1, 'whole capital return')
    for label, offset in [('conditional_initial_covered',1),('conditional_maintenance_covered',2)]:
        states = [x[offset] for x in values]
        expected = None if not complete else (False if False in states else None if None in states else True)
        c.eq(total[label], expected, 'tri-state segregated coverage')
    c.eq(total['actual_marked_nav_usdc'], None, 'no actual marked account')
    c.eq(total['actual_risk_ready'], False, 'no risk permission')


def audit(out):
    c = Checks()
    spec = LANE/'PREREG.md'
    c.eq(digest(spec), (LANE/'PREREG.sha256').read_text().strip(), 'frozen spec')
    for name in ('code_inputs.json','inputs.json','fixtures.json','source_review.json','margin_contract.json'):
        c.yes(digest(LANE/name) in spec.read_text(), 'bound '+name)
    for name in ('code_inputs.json','inputs.json'):
        for p, sha in load(LANE/name)['sha256'].items():
            c.eq(digest(ROOT/p), sha, 'exact identity '+p)
    for name in ('PREREG.md','PREREG.sha256','code_inputs.json','inputs.json','fixtures.json','margin_contract.json','source_review.json'):
        c.eq(subprocess.check_output(['git','show','HEAD:'+str((LANE/name).relative_to(ROOT))],cwd=ROOT),
             (LANE/name).read_bytes(), 'committed '+name)
    cfg, contract = load(LANE/'fixtures.json'), load(LANE/'margin_contract.json')
    c.num(contract['maximum_face_usd'], F(75000000), 'source inverse USD maximum')
    c.num(contract['flat_share'], F(3,100), 'source exact plateau share')
    c.num(contract['start_leverage'], F(25), 'source plateau leverage')
    c.num(contract['maintenance_share_of_initial'], F(2,3), 'source exact MM/IM')
    receipts = load(LANE/'source_receipts.json')
    c.eq(receipts['requests'], 3, 'closed bounded source GET count')
    c.eq(receipts['scope_closed'], True, 'closed source scope')
    c.eq(sum(x['bytes'] for x in receipts['records']), 266298, 'actual source bytes')
    c.eq([x['sha256'] for x in receipts['records']], contract['source_sha256'], 'received source identities')
    r, parent = load(out/'results.json.gz'), load(PARENT/'results.json.gz')
    old_journals, copied = load(PARENT/'journals.json.gz'), load(out/'journals.json.gz')
    c.eq(copied, old_journals, 'all original journals byte content unchanged')
    events = {}
    for name, content in old_journals.items():
        events[name] = chain(content, c)
        c.eq((out/name).read_text(), content, 'native read-only replay content')
    c.eq(len(events), 132, 'preserved parent journal count')
    cap = load(RAW/'capture.json')
    records = {x['name']:x for x in cap['records']}
    pubs = {}
    for coin in cfg['coins']:
        rec = records[coin+'_future_book']
        c.eq(digest(RAW/rec['body']), rec['body_sha256'], 'raw market body')
        raw = load(RAW/rec['body'])['result']
        pubs[coin] = (F(raw['mark_price']), F(raw['index_price']))
        c.num(r['source_publications'][coin]['mark_usd'], pubs[coin][0], 'source mark')
        c.num(r['source_publications'][coin]['index_usd'], pubs[coin][1], 'source index')
        c.eq(r['source_publications'][coin]['historical_snapshot_not_current'], True, 'old batch not fresh quote')
    portfolios = {x['id']:x for x in parent['portfolios']}
    new_models = {x['id']:x for x in r['models']}
    worlds = {(x['model'], x['coin_price_scale'], x['common_future_mark_factor'], x['denominator_control']):x for x in r['worlds']}
    frontiers = {(x['model'], x['coin_price_scale'], x['loss_floor_fraction']):x for x in r['frontiers']}
    c.eq(len(worlds), len(r['worlds']), 'no duplicate states')
    c.eq(len(frontiers), len(r['frontiers']), 'no duplicate frontiers')
    c.eq(len(new_models), 48, 'all parent model cells')
    c.eq(len(worlds), 2400, 'finite full stress grid')
    c.eq(len(frontiers), 720, 'finite loss-floor grid')
    numeric = 0
    for old in parent['models']:
        mid = old['id']; new = new_models[mid]; prefix='states/'+mid+'/'
        cash, held = spot(events[prefix+'spot.jsonl'], c)
        states = {coin:inverse(events[prefix+coin+'-inverse.jsonl'], c) for coin in old['ownership']}
        plans = {x['coin']:x['plan'] for x in portfolios[old['portfolio']]['decisions'] if x['plan'] is not None}
        c.num(new['cash_usdc'], cash, 'shared cash')
        c.eq(new['source_input_complete'], old['source_input_complete'], 'original incomplete state preserved')
        residual, harmonic = F(0), F(0)
        for coin, a in states.items():
            c.eq(a['initial'], held[coin], 'same purchased coin is collateral once')
            c.num(new['initial_owned_coin'][coin], a['initial'], 'passive matched initial coin')
            s = F(plans[coin]['spot_mid_usdc'])
            residual += (a['cash']+a['numerator'])*s
            harmonic += -a['face']*s/pubs[coin][0]
        c.num(new['residual_spot_value_usdc'], residual, 'residual coefficient')
        c.num(new['reciprocal_mark_value_usdc'], harmonic, 'harmonic coefficient')
        for denom in cfg['denominator_controls']+['unknown']:
            view = new['source_snapshot_views'][denom]; values=[]
            c.eq({v['coin'] for v in view['legs']}, set(states), 'complete original source leg scope')
            for v in view['legs']:
                coin=v['coin']; m,ix=pubs[coin]
                values.append(check_leg(v,states[coin],m,F(plans[coin]['spot_mid_usdc']),ix,denom,c))
            check_total(view['portfolio'],values,cash,old['source_input_complete'],c)
        for scale in cfg['coin_price_scales']:
            sf=F(scale)
            for beta in cfg['common_future_mark_factors']:
                bf=F(beta)
                for denom in cfg['denominator_controls']:
                    world=worlds[mid,scale,beta,denom]; values=[]
                    c.eq(world['kind'],'fixed_conditional_state_not_market_path','no historical path assertion')
                    c.eq({v['coin'] for v in world['legs']},set(states),'complete stress leg scope')
                    for v in world['legs']:
                        coin=v['coin']; m,ix=pubs[coin]
                        values.append(check_leg(v,states[coin],m*sf*bf,F(plans[coin]['spot_mid_usdc'])*sf,ix*sf,denom,c))
                    check_total(world['portfolio'],values,cash,old['source_input_complete'],c)
                    nav=cash+residual*sf+harmonic/bf
                    c.num(world['portfolio']['marked_nav_usdc'],nav if old['source_input_complete'] else None,'separate closed-form NAV')
                    passive=cash+sum((a['initial']*F(plans[coin]['spot_mid_usdc'])*sf for coin,a in states.items()),F(0))
                    c.num(world['matched_spot_only_control_usdc'],passive if old['source_input_complete'] else None,'same deployed capital passive control')
                    c.num(world['cash_control_usdc'],F(10000),'cash reference full capital')
                    c.eq(world['actual_expected_net'],None,'no expected-return claim')
                    numeric+=int(old['source_input_complete'])
            for loss in cfg['loss_floor_fractions']:
                f=frontiers[mid,scale,loss]['conditional_boundary']
                if not old['source_input_complete']:
                    c.eq(f,None,'incomplete frontier withheld');continue
                target=F(10000)*(1-F(loss));gap=target-cash-residual*sf
                c.num(f['target_usdc'],target,'loss target')
                if gap<=0:
                    c.eq(f['all_positive_factors_meet_floor'],True,'constant-part floor coverage')
                    c.eq(f['maximum_common_future_mark_factor'],None,'no finite maximum when constant covers')
                else:
                    c.num(f['maximum_common_future_mark_factor'],harmonic/gap,'exact mark-factor boundary')
                    boundary=F(f['maximum_common_future_mark_factor'])
                    c.eq(cash+residual*sf+harmonic/boundary,target,'boundary substitutes to floor')
                    c.yes(cash+residual*sf+harmonic/(boundary*F(1001,1000))<target,'adverse side fails floor')
    c.eq(r['historical_price_path_replayed'],False,'no missing historical-data replay')
    c.eq(r['historical_acquisition_requests_unchanged'],7757,'old acquisition not reset')
    c.eq(r['actual_margin_certification'],None,'no actual margin certificate')
    c.eq(r['actual_executable_expected_net'],None,'actual net remains unknown')
    c.eq(r['new_prospective_strategy_days'],0,'zero prospective strategy days')
    c.eq(r['predictive_trials'],0,'zero new predictors')
    c.eq(r['activation_allowed'],False,'no activation')
    result={'registry_id':'R346','status':'PASS','checks':c.n,'conditional_states':len(worlds),
            'numeric_states':numeric,'incomplete_states':len(worlds)-numeric,'loss_frontiers':len(frontiers),
            'preserved_parent_journals':len(old_journals),'actual_risk_ready':False}
    with (out/'audit.json').open('x') as h:
        json.dump(result,h,sort_keys=True,indent=2);h.write('\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True,type=Path)
    print(json.dumps(audit(p.parse_args().out),indent=2))
