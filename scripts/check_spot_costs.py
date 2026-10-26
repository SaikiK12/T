"""Independent exact-rational audit of R325 raw quote cash and capital costs."""
import argparse
from fractions import Fraction as F
import gzip
import hashlib
import json
from math import lcm
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LANE=ROOT/'experiments/spot_perp_costs_v1'


def levels(rows,multiplier=F(1),reverse=False):
    values={}
    for row in rows:
        p,q=F(str(row[0])),F(str(row[1]))*multiplier
        if p<=0 or q<=0:raise ValueError('invalid oracle price/quantity')
        values[p]=values.get(p,F(0))+q
    return sorted(values.items(),reverse=reverse)


def cash(side,q):
    total=F(0)
    for p,n in side:
        take=min(q,n);total+=p*take;q-=take
        if q==0:return total
    return None


def near(a,b):
    if abs(F(str(a))-F(str(b)))>F(1,100_000_000):raise ValueError('raw rational cash/cost differs beyond registered1e-8quote')


def audit(result):
    out=Path(result).parent;r=json.loads(Path(result).read_text());f=json.loads((LANE/'fixtures.json').read_text())
    capture=json.loads((LANE/'evidence/capture.json').read_text());records={a['name']:a for a in capture['records']}
    def raw(name):
        a=records[name]
        if a['http_status']!=200 or not a['complete']:raise ValueError('computed cost used failed source')
        return json.loads(gzip.decompress((LANE/'evidence'/a['body']).read_bytes()),parse_float=str)
    expected={(i,s) for i in range(3) for s in f['symbols']}
    if {(row['sample'],row['symbol']) for row in r['rows']}!=expected or len(r['rows'])!=9:raise ValueError('dropped/extra fixed pair slot')
    computed=0;models=0;errors=[];hurdles={};journal_rows=0
    for row in r['rows']:
        symbol=row['symbol'];name=str(row['sample'])+'_'+symbol
        if len(row['views'])!=4 or {(v['profile'],v['fee_control']) for v in row['views']}!={(p,t) for p in f['depth_profiles'] for t in f['fee_controls']}:
            raise ValueError('dropped fixed profile/fee control')
        for v in row['views']:
            if v['executable_pair_eligible'] or v['net_market_return'] is not None:raise ValueError('diagnostic became executable return')
            if not v['costs']:
                if not v['conditional_calculation_reasons'] or v['cost_account'] is not None:raise ValueError('silent successful inactivity')
                errors.extend(v['conditional_calculation_reasons']);continue
            q=F(row['illustrative_base_quantity']);m=raw(symbol+'_perp_rules')['data']
            sm=[x for x in raw('spot_rules')['symbols'] if x.get('symbol')==symbol+'USDT']
            if len(sm)!=1:raise ValueError('oracle spot symbol identity')
            sm=sm[0]
            if sm.get('status')!='1' or sm.get('isSpotTradingAllowed') is not True or sm.get('tradeSideType')!=1 or 'MARKET' not in sm.get('orderTypes',[]):
                raise ValueError('numeric cost despite blocked spot public state')
            if m.get('apiAllowed') is not True or type(m.get('state')) is not int or m['state']!=0:raise ValueError('numeric cost despite blocked perpetual public state')
            a,b=records[name+'_spot'],records[name+'_perp']
            for rec in (a,b):
                lag=rec['received_mono_ns']-rec['started_mono_ns']
                if not 0<=lag<=2_000_000_000 or abs(rec['received_utc_ns']-rec['started_utc_ns']-lag)>50_000_000:
                    raise ValueError('local latency/clock gate bypass')
            if abs(a['received_mono_ns']-b['received_mono_ns'])>1_000_000_000:raise ValueError('local receipt skew gate bypass')
            sb=raw(name+'_spot');pb=raw(name+'_perp')['data'];cs=F(str(m['contractSize']))
            sides=[levels(sb['asks']),levels(sb['bids'],reverse=True),levels(pb['asks'],cs),levels(pb['bids'],cs,True)]
            sides[2:]=[s[:m['marketOrderMaxLevel']] for s in sides[2:]]
            mids=[(sides[i][0][0]+sides[i+1][0][0])/2 for i in (0,2)]
            pa=cs*F(str(m['volUnit']));sp=F(1,10**sm['baseAssetPrecision']);den=lcm(pa.denominator,sp.denominator)
            step=F(lcm(pa.numerator*(den//pa.denominator),sp.numerator*(den//sp.denominator)),den)
            expected_q=(F(f['reference_mid_leg_budget'])/max(mids)//step)*step
            if q!=expected_q:raise ValueError('size/control policy changed from fixed mid budget/grid')
            if v['profile']=='top_only':sides=[side[:1] for side in sides]
            fills=[cash(side,q) for side in sides]
            if None in fills:raise ValueError('numeric cost for unfillable fixed size')
            buy,sell,pbuy,psell=fills
            if q<F(str(sm['baseSizePrecision'])) or min(buy,sell)<F(str(sm['quoteAmountPrecisionMarket'])) or max(buy,sell)>F(str(sm['maxQuoteAmountMarket'])):
                raise ValueError('raw minimum/maximum failed')
            sr,pr=(F(0),F(0)) if v['fee_control']=='zero_charge' else (F(str(sm['takerCommission'])),F(str(m['takerFeeRate'])))
            cross=buy-sell+pbuy-psell;fees=(buy+sell)*sr+(pbuy+psell)*pr
            if buy*(1+sr)>5000 or q*mids[1]+psell*pr>5000:raise ValueError('segregated capital exceeded')
            for got,wanted in zip(v['hypothetical_fill_cash'],fills):near(got,wanted)
            near(v['crossing_quote'],cross);near(v['commission_quote'],fees)
            if len(v['costs'])!=3:raise ValueError('missing stress scenario')
            for k,tier in zip((1,2,3),v['costs']):
                if tier['multiple']!=k:raise ValueError('cost tier drift')
                near(tier['required_gross_quote_to_break_even'],k*(cross+fees))
                near(tier['break_even_one_leg_bp'],k*(cross+fees)/(q*sum(mids)/2)*10000)
                near(tier['cost_on_total_capital_bp'],k*(cross+fees)/10000*10000)
                computed+=1
            model=v['cost_account'];models+=1
            near(model['known_four_fill_price_fee_component'],-cross-fees)
            if model['snapshot']['combined_nav'] is not None or model['funding_cash'] is not None or not model['snapshot']['perp']['unresolved_events']:
                raise ValueError('missing funding erased')
            if F(model['snapshot']['initial_total_segregated_capital'])!=10000:raise ValueError('capital denominator drift')
            hurdles.setdefault(symbol,[]).append(v['costs'][0]['break_even_one_leg_bp'])
    packed=json.loads(gzip.decompress((out/'journals.json.gz').read_bytes()))
    if len(packed)!=2*models:raise ValueError('journal inventory differs')
    for name,text in packed.items():
        if (out/name).read_text()!=text:raise ValueError('packed journal differs from native')
        previous='0'*64
        for i,line in enumerate(text.splitlines()):
            row=json.loads(line);digest=row.pop('sha256')
            encoded=json.dumps(row,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
            if row['sequence']!=i or row['previous_sha256']!=previous or hashlib.sha256(encoded).hexdigest()!=digest:raise ValueError('broken append-only model chain')
            previous=digest;journal_rows+=1
    if computed!=r['computed_conditional_cost_tiers'] or r['market_net_return'] is not None or r['new_prospective_strategy_days']:
        raise ValueError('reported counts or inference scope drift')
    return {'registry_id':'R325','fixed_pair_slots':9,'fixed_control_cells':36,'fixed_tier_slots':108,
            'audited_computed_cost_tiers':computed,'cost_account_models':models,'journal_files':len(packed),'journal_rows':journal_rows,
            'raw_rational_arithmetic_matches_within_quote_tolerance':'1e-8','missing_cost_reasons':sorted(set(errors)),
            'market_profitability_validated':False,'new_prospective_strategy_days':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('result',type=Path)
    print(json.dumps(audit(p.parse_args().result),sort_keys=True,indent=2))
