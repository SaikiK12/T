"""R326 finite compatibility bridge; original R325 source and failures stay intact.

Zero is an explicit minimum lower bound, never a positive size or lot increment.
Decimal wire fields keep their exact text through the old numeric type boundary.
No cost, clock, permission, lot convention, owner-fee or funding guard is relaxed.
"""
from dataclasses import replace
from decimal import Decimal

from lab.executable_quotes import mexc_book as original_mexc_book
from lab.spot_quote_costs import spot_rules as original_spot_rules,optional_number


def spot_rules(symbol,payload):
    if not isinstance(payload,dict) or not isinstance(payload.get('symbols'),list):
        return original_spot_rules(symbol,payload)
    selected=[(i,m) for i,m in enumerate(payload['symbols']) if isinstance(m,dict) and m.get('symbol')==symbol]
    if len(selected)!=1:return original_spot_rules(symbol,payload)
    i,m=selected[0]
    value=optional_number(m.get('baseSizePrecision'))
    if value!=0:return original_spot_rules(symbol,payload)
    # Reuse all original schema checks without mutating received source data.
    view={**payload,'symbols':list(payload['symbols'])}
    view['symbols'][i]={**m,'baseSizePrecision':None}
    rules=original_spot_rules(symbol,view)
    return replace(rules,minimum_base=Decimal(0))


def mexc_book(symbol,payload,metadata,receipt):
    if not isinstance(payload,dict) or not isinstance(payload.get('data'),dict):
        return original_mexc_book(symbol,payload,metadata,receipt)
    view={**payload,'data':dict(payload['data'])}
    for side in ('bids','asks'):
        rows=payload['data'].get(side)
        if isinstance(rows,list):
            view['data'][side]=[[str(x) if isinstance(x,Decimal) else x for x in row]
                                if isinstance(row,list) else row for row in rows]
    return original_mexc_book(symbol,view,metadata,receipt)
