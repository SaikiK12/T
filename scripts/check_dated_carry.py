"""Independent stdlib/Fraction audit of every R327 value and packed cash row.

No production price/depth/payoff/account module is imported. This checks the
registered conditional model, not deployed payout or executable profitability.
"""
import argparse
from fractions import Fraction as F
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LANE=ROOT/'experiments/dated_carry_v1'


def load(p):return json.loads(Path(p).read_text(),parse_float=F)
def unpack(v):return F(v['numerator'],v['denominator'])


def read_chain(raw):
    assert raw.endswith('\n'),'incomplete cash chain'
    rows=[];previous='0'*64
    for seq,line in enumerate(raw.splitlines()):
        r=json.loads(line);digest=r.pop('sha256')
        encoded=json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        assert hashlib.sha256(encoded).hexdigest()==digest
        assert r['sequence']==seq and r['previous_sha256']==previous
        previous=digest;rows.append(r['event'])
    return rows


def audit(path):
    path=Path(path);result=load(path);fixture=load(LANE/'fixtures.json')
    capture=load(LANE/'evidence/capture.json');rec={r['name']:r for r in capture['records']}
    packed=json.loads(gzip.decompress((path.parent/'journals.json.gz').read_bytes()))
    def raw(name):
        r=rec[name];assert r['http_status']==200 and r['complete']
        body=(LANE/'evidence'/r['body']).read_bytes()
        assert hashlib.sha256(body).hexdigest()==r['body_sha256']
        return json.loads(gzip.decompress(body),parse_float=F)
    def consume(levels,amount):
        left=amount;used=[]
        for price,size in levels:
            take=min(left,F(size));used.append((F(price),take));left-=take
        assert not left,'fixed displayed quantity unsupported'
        return [(p,n) for p,n in used if n]
    rows=result['rows'];assert len(rows)==4
    assert result['market_expected_net'] is None and result['actual_executable_admissions']==0
    assert result['new_prospective_strategy_days']==0 and result['predictive_strategy_trials']==0
    checked=0;unknown=0;models=0;ownership_links=[]
    for row in rows:
        assert len(row['controls'])==6
        if row['plan'] is not None:
            coin=row['coin'];name=row['instrument'];meta=raw(coin+'_instrument')['result']
            sb=raw(coin+'_spot');db=raw(coin+'_dated')['result']
            sr=next(s for s in raw('spot_rules')['symbols'] if s['symbol']==coin+'USDT')
            step=F(meta['min_trade_amount']);face=(F(fixture['target_USD_face'])//step)*step
            fm=(F(db['bids'][0][0])+F(db['asks'][0][0]))/2
            sm=(F(sb['bids'][0][0])+F(sb['asks'][0][0]))/2
            full=consume(db['bids'],face)
            q0=sum((n/(fm-3*(fm-p)) for p,n in full),F(0))*(1+3*F(fixture['standard_future_taker_rate']))
            quantum=F(1,10**sr['baseAssetPrecision']);q=-((-q0)//quantum)*quantum
            cap=None if row['profile']=='full' else 1
            future=consume(db['bids'][:cap],face);spot=consume(sb['asks'][:cap],q)
            plan=row['plan'];assert F(plan['initial_coin'])==q and F(plan['face_usd'])==face
            assert F(plan['hedge_coin'])==sum((n/p for p,n in future),F(0))
            assert not plan['executable_admission'] and plan['future_net_usdt'] is None
        for cell in row['controls']:
            assert len(cell['terminal_worlds'])==9
            if row['plan'] is not None:
                primary=cell['primary_future_result']
                assert primary['actual_net_usdt'] is None and primary['conditional_net_usdt'] is None
                assert primary['terminal'] is None and primary['coin_counted_once']
                assert not primary['executable_admission']
            else:assert cell['primary_future_result'] is None
            for world in cell['terminal_worlds']:
                r=world['conditional']
                if r is None:
                    assert row['input_error'] is not None and world['uncomputed_reason'];unknown+=1;continue
                k=cell['cost_multiple'];paid=cell['fee_control']=='public_standard'
                fee_s=F(sr['takerCommission'])*k if paid else F(0)
                fee_d=F(fixture['standard_delivery_rate'])*k if paid else F(0)
                a=sum((n/(fm-k*(fm-p)) for p,n in future),F(0))
                fee_e=a*F(fixture['standard_future_taker_rate'])*k if paid else F(0)
                spend=sum((n*(sm+k*(p-sm)) for p,n in spot),F(0))*(1+fee_s)
                x=fm*F(world['delivery_price_scale']);ratio=F(world['exit_USDT_per_delivery_USD_ratio'])
                residual=q-fee_e-a;coin_end=face*(1-fee_d)/x+residual
                proceeds=coin_end*x*ratio*(1-fee_s);net=proceeds-spend
                expected={'initial_spend_usdt':spend,'idle_cash_usdt':10000-spend,'conditional_net_usdt':net,
                          'conditional_net_on_total_capital':net/10000,'residual_unhedged_coin':residual,
                          'same_initial_coin_passive_net_usdt':q*x*ratio*(1-fee_s)-spend,
                          'break_even_exit_ratio':spend/(coin_end*x*(1-fee_s))}
                for key,value in expected.items():assert F(r[key])==value,(coin,key)
                assert F(r['terminal']['coin_after_delivery'])==coin_end
                assert r['actual_net_usdt'] is None and not r['executable_admission']
                assert F(r['total_initial_capital_usdt'])==10000 and residual>=0
                checked+=1
            models+=len(cell['models'])
            for model in cell['models']:
                assert model['combined_market_nav'] is None and model['constructed_clocks']
                assert model['remaining_unearmarked_spot_coin']=='0'
                paths=list(model['journal_sha256']);assert len(paths)==2
                ownership_links.append((next(n for n in paths if n.endswith('-spot.jsonl')),
                                        next(n for n in paths if n.endswith('-inverse.jsonl')),model))
    journal_rows=0;balances={}
    for name,raw_text in packed.items():
        events=read_chain(raw_text);journal_rows+=len(events);config=events[0]
        if name.endswith('-inverse.jsonl'):
            initial=unpack(config['initial_coin']);cash=initial;lots=[];fees=F(0);pnl=F(0)
            for e in events[1:]:
                assert e['kind']=='inverse_model_attempt';p=e['payload'];price=unpack(p['price_usd_per_coin'])
                fee=unpack(p['fee_coin']);fees+=fee
                if p['kind']=='open':lots.append((unpack(p['signed_face_usd']),price))
                else:
                    delta=sum((n*(1/entry-1/price) for n,entry in lots),F(0));cash+=delta;pnl+=delta
                    lots=[] if p['kind']=='delivery' else [(n,price) for n,_ in lots]
                cash-=fee
            assert not lots
            balances[name]=(initial,cash,fees,pnl)
        else:
            cash=F(config['initial_cash']);coin=F(0)
            for e in events[1:]:
                p=e['payload'];assert p['kind']=='fill' and p['fee_asset']=='USDT'
                q=F(p['quantity']);cash-=q*F(p['price'])+F(p['fee_amount']);coin+=q
            balances[name]=(cash,coin)
    for sp,ip,model in ownership_links:
        for name,digest in model['journal_sha256'].items():
            assert hashlib.sha256(packed[name].encode()).hexdigest()==digest
        cash,base=balances[sp];initial,end,fees,pnl=balances[ip]
        assert base==initial==F(model['initial_spot_coin_earmarked_as_same_inverse_collateral'])
        assert cash==F(model['idle_cash_usdt']) and end==F(model['inverse']['coin_cash'])
        assert fees==F(model['inverse']['fees_coin']) and pnl==F(model['inverse']['realized_price_pnl_coin'])
    assert checked+unknown==216
    assert result['computed_scenarios']==checked and result['constructed_inverse_models']==models
    assert len(packed)==2*models
    return {'registry_id':'R327','conditional_scenarios_checked':checked,'uncomputed_scenarios_retained':unknown,
            'constructed_models_checked':models,'native_journals_checked':len(packed),'chained_rows_checked':journal_rows,
            'exact_fraction_equalities':True if checked else None,'actual_cash_or_expected_return_verified':False,
            'public_payoff_serialization_verified':False,'new_prospective_strategy_days':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('result',type=Path)
    args=p.parse_args();value=audit(args.result)
    target=args.result.parent/'audit.json'
    with target.open('x') as h:h.write(json.dumps(value,sort_keys=True,indent=2)+'\n')
    print(json.dumps(value,sort_keys=True))
