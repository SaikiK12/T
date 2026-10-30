"""Join segregated simulated spot inventory and linear-futures capital once.

Spot principal is spent, futures notional is reserved. No transfer, FX parity,
cross-wallet margin, guessed fee, executable fill or paper admission is inferred.
"""
from fractions import Fraction as F

from lab.paper_account import PaperAccount
from lab.spot_cash import SpotCashAccount


def snapshot(spot, perp, market, perp_symbol, asof, *, spot_marks=(), perp_marks=()):
    if not isinstance(spot,SpotCashAccount) or not isinstance(perp,PaperAccount):
        raise ValueError('separate typed cash/inventory and futures accounts required')
    if spot.anchor!=perp.anchor or market not in spot.markets:
        raise ValueError('explicit common clock and known spot market required')
    # No undeclared cross-currency conversion or third wallet aggregation.
    if len(perp.initial)!=1 or next(iter(perp.initial))[1]!=spot.quote_asset:
        raise ValueError('one separate futures wallet in the same quote asset required')
    s=spot.snapshot(asof,spot_marks);p=perp.snapshot(asof,perp_marks)['accounts'][0]
    if any(key[2]!=perp_symbol and q for key,(q,_) in perp.positions.items()):
        raise ValueError('unrelated futures inventory cannot disappear from pair risk')
    if any(m!=market and q for m,q in spot.holdings.items()):
        raise ValueError('unrelated spot inventory cannot disappear from pair risk')
    key=(*next(iter(perp.initial)),perp_symbol)
    q=F(perp.positions.get(key,(0,0))[0])
    capital=spot.initial+sum(F(v) for v in perp.initial.values())
    flows=spot.flows+sum(F(v) for v in perp.flows.values())
    nav=None if s['nav'] is None or p['nav'] is None else F(s['nav'])+F(p['nav'])
    net=None if nav is None else nav-capital-flows
    pending=s['holdings_available'] is None or p['cash'] is None
    base_gap=None if pending else spot.holdings[market]+q
    return {'simulation_only':True,'quote_asset':spot.quote_asset,'spot':s,'perp':p,
            'initial_total_segregated_capital':str(capital),'external_flows':str(flows),
            'combined_nav':None if nav is None else str(nav),
            'combined_net_pnl':None if net is None else str(net),
            'return_on_total_capital':None if net is None or not capital else str(net/capital),
            'net_base_exposure':None if base_gap is None else str(base_gap),
            'spot_principal_reserved_again':False,'cross_wallet_transfers':False,
            'cash_sum_is_not_nav':True,'actual_order_allowed':False,
            'certified_market_return':None,'new_prospective_paper_days':0}
