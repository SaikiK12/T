"""Independent literal cash-flow oracle for R324's fixed constructed accounts."""
import argparse
from fractions import Fraction as F
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def audit(result):
    result=Path(result);out=result.parent
    fixtures=json.loads((ROOT/'experiments/spot_perp_inputs_v1/fixtures.json').read_text())
    summary=json.loads(result.read_text())
    payload=json.loads(gzip.decompress((out/'observations.json.gz').read_bytes()))
    journals=json.loads(gzip.decompress((out/'journals.json.gz').read_bytes()))
    expected={(c['id'],k):c for c in fixtures['cases'] for k in fixtures['cost_multiples']}
    observed={(a['id'],a['cost_multiple']) for a in payload['accounts']}
    if observed!=set(expected) or len(observed)!=len(payload['accounts']):raise ValueError('finite case inventory drift')
    details=[];rows=0
    for name,text in journals.items():
        if hashlib.sha256(text.encode()).hexdigest()!=hashlib.sha256((out/name).read_bytes()).hexdigest():raise ValueError('packed journal differs')
        previous='0'*64
        for sequence,line in enumerate(text.splitlines()):
            row=json.loads(line);digest=row.pop('sha256')
            raw=json.dumps(row,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
            if row['sequence']!=sequence or row['previous_sha256']!=previous or hashlib.sha256(raw).hexdigest()!=digest:
                raise ValueError('journal identity chain mismatch')
            rows+=1;previous=digest
    for a in payload['accounts']:
        c=expected[(a['id'],a['cost_multiple'])];k=a['cost_multiple'];initial=F(fixtures['capital_per_wallet'])
        S0,F0,S1,F1=map(F,c['mid_prices']);h=F(fixtures['half_spread'])*k;rate=F(fixtures['fee_rate'])*k
        buyfee=F(fixtures['base_fee'])*k if c['entry_fee_asset']=='BTC' else 0
        owned=1-buyfee;q=owned if c['hedge']=='net_owned' else F(1)
        entry_quote_fee=(S0+h)*rate if c['entry_fee_asset']=='USDT' else 0
        final=a['final_account'];opening=a['open_account']
        if F(opening['spot']['cash_known_component'])!=initial-S0-h-entry_quote_fee:raise ValueError('spot principal/fee cash identity')
        if F(opening['perp']['known_cash_component'])!=initial-q*(F0-h)*rate:raise ValueError('futures principal wrongly spent')
        if F(opening['perp']['locked_capital'])!=q*(F0-h):raise ValueError('futures reservation differs')
        if c['entry_fee_asset'] not in ('UNKNOWN','MX') and F(opening['net_base_exposure'])!=owned-q:
            raise ValueError('base-commission hedge gap hidden')
        net=None
        if c['entry_fee_asset'] in ('UNKNOWN','MX') or c['funding_quote_per_base'] is None:
            if final['combined_nav'] is not None:raise ValueError('unknown fee/funding became known NAV')
        else:
            funding=q*F(c['funding_quote_per_base'])
            scash=initial-(S0+h)-entry_quote_fee+owned*(S1-h)*(1-rate)
            pcash=initial+q*(F0-h-F1-h)+funding-q*rate*((F0-h)+(F1+h))
            net=scash+pcash-2*initial
            if F(final['spot']['cash'])!=scash or F(final['perp']['cash'])!=pcash:raise ValueError('literal final cash mismatch')
            if F(final['combined_net_pnl'])!=net or F(final['return_on_total_capital'])!=net/(2*initial):
                raise ValueError('net PnL or capital denominator differs')
            gross=(S1-S0)+q*(F0-F1)
            crossing=h*(1+owned+2*q)
            quote_fees=entry_quote_fee+owned*(S1-h)*rate+q*rate*((F0-h)+(F1+h))
            base_fee_value=buyfee*S1
            if gross+funding-crossing-quote_fees-base_fee_value!=net:raise ValueError('economic decomposition double counts/misses cost')
            details.append({'id':c['id'],'cost_multiple':k,'gross_mid_price_pnl':str(gross),'funding':str(funding),
                            'crossing_cost':str(crossing),'quote_commissions':str(quote_fees),
                            'base_commission_exit_mid_value':str(base_fee_value),'net':str(net)})
        if a['cash_control_net_pnl']!='0' or a['reopened_identical'] is not True:raise ValueError('cash/replay control differs')
        if F(final['initial_total_segregated_capital'])!=2*initial:raise ValueError('capital missing/double counted')
    if summary['new_prospective_paper_days'] or summary['market_net_return'] is not None:raise ValueError('fixture promoted to market evidence')
    return {'registry_id':'R324','account_paths':len(observed),'journal_files':len(journals),'journal_rows':rows,
            'literal_cash_and_cost_decomposition':details,'independent_arithmetic_matches':True,
            'market_profitability_validated':False,'scope':'literal supplied cash-flow arithmetic and packed chains only'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('result',type=Path)
    print(json.dumps(audit(p.parse_args().result),sort_keys=True,indent=2))
