"""Source-typed same-venue spot/inverse carry input and capital model.

R329 routed spot books are public; trades/charts are not used. Market quotes
are not fills, owner fee proof, account entitlement or liquidation attestation.
"""
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction as F

from lab.dated_carry import response, rules as dated_rules, book as dated_book, local_pair_flags
from lab.inverse_cash import rational, walk
from lab.inverse_offer import coverage, terminal_hurdle
from lab.executable_quotes import Receipt

NS = 1_000_000_000


@dataclass(frozen=True)
class VenueSpot:
    instrument: str
    coin: str
    step: F
    tick: F
    route: str
    active: bool
    public_taker_hint: F | None


def spot_rules(payload, coin):
    p = response(payload); name = coin+'_USDC'
    if (p.get('instrument_name') != name or p.get('kind') != 'spot'
            or p.get('base_currency') != coin or p.get('quote_currency') != 'USDC'
            or p.get('counter_currency') != 'USDC' or rational(p.get('contract_size'), positive=True) != 1
            or type(p.get('is_active')) is not bool):
        raise ValueError('exact spot base/USDC identity, amount convention and public status required')
    flags = (p.get('is_csr'), p.get('is_cbe_routed'))
    if flags == (True, True) and all(type(x) is bool for x in flags): route = 'Coinbase-routed'
    elif flags == (None, None) and 'is_csr' not in p and 'is_cbe_routed' not in p: route = 'native'
    else: raise ValueError('routing flags contradictory or unsupported by cached query contract')
    step = rational(p['min_trade_amount'], positive=True)  # R329-S39: minimum AND amount increment.
    tick = rational(p['tick_size'], positive=True)
    hint = None if p.get('taker_commission') is None else rational(p['taker_commission'], nonnegative=True)
    return VenueSpot(name, coin, step, tick, route, p['is_active'], hint)


def validate_ticks(levels, metadata):
    p = response(metadata); tick = rational(p['tick_size'], positive=True)
    steps = p.get('tick_size_steps', [])
    if type(steps) is not list: raise ValueError('explicit tick step list required')
    parsed = [(rational(s['above_price'], nonnegative=True), rational(s['tick_size'], positive=True)) for s in steps]
    if any(a[0] >= b[0] for a,b in zip(parsed, parsed[1:])): raise ValueError('ordered tick thresholds required')
    for price, _ in levels:
        effective = tick
        for above, step in parsed:
            if price > above: effective = step
        if price % effective: raise ValueError('source price off declared tick grid')


def spot_book(payload, metadata, rules, receipt):
    p = response(payload)
    if not isinstance(receipt, Receipt) or p.get('instrument_name') != rules.instrument or type(p.get('timestamp')) is not int:
        raise ValueError('typed spot publication/first-seen identity required')
    sides = []
    for field, direction in (('bids','sell'),('asks','buy')):
        raw = p.get(field)
        if type(raw) is not list or not 1 <= len(raw) <= 5: raise ValueError('finite five-level spot book required')
        levels = [(rational(x[0], positive=True), rational(x[1], positive=True)) for x in raw if type(x) is list and len(x) == 2]
        if len(levels) != len(raw) or any(q % rules.step for _,q in levels): raise ValueError('spot amount off base increment')
        walk(levels, min(q for _,q in levels), side=direction, unit='base')
        validate_ticks(levels, metadata); sides.append(levels)
    if sides[0][0][0] >= sides[1][0][0]: raise ValueError('crossed spot book')
    if not 946684800_000_000_000 <= p['timestamp']*1_000_000 <= receipt.received_utc_ns:
        raise ValueError('invalid/future spot publication time')
    return {'bids': sides[0], 'asks': sides[1], 'publication_ns': p['timestamp']*1_000_000, 'state': p.get('state')}


def current_flags(receipts, publications, decision):
    if (len(receipts) != len(publications) or type(decision) is not int
            or any(not isinstance(r,Receipt) for r in receipts)
            or any(type(p) is not int for p in publications)):
        raise ValueError('exact typed receipt/publication scope required')
    if not receipts: return ['no_book_receipts']
    last = max(receipts, key=lambda r:r.received_mono_ns); target = last.received_utc_ns+decision-last.received_mono_ns
    flags = []
    for r, publication in zip(receipts, publications):
        if decision-r.started_mono_ns > 2*NS or r.received_mono_ns-r.started_mono_ns > 2*NS:
            flags.append('joint_request_or_body_age_over_2s')
        if decision-r.received_mono_ns > NS or r.received_mono_ns > decision:
            flags.append('joint_receive_skew_over_1s_or_future')
        if abs((r.received_utc_ns-r.started_utc_ns)-(r.received_mono_ns-r.started_mono_ns)) > 50_000_000:
            flags.append('clock_step_over_50ms')
        if not -100_000_000 <= target-publication <= 2*NS:
            flags.append('publication_age_over_2s_or_future')
        if abs((r.received_utc_ns-last.received_utc_ns)-(r.received_mono_ns-last.received_mono_ns)) > 50_000_000:
            flags.append('cross_receipt_clock_step_over_50ms')
    return sorted(set(flags))


def prepare(coin, face_target, profile, spot_metadata, spot_payload, spot_receipt,
            future_metadata, future_payload, future_receipt, *, expiry_ns, spot_rate, future_rate, future_source_identity):
    if profile not in ('full','top_only'): raise ValueError('registered depth control required')
    sr = spot_rules(spot_metadata, coin)
    dr = dated_rules(future_metadata, coin+'-25DEC26', coin, expiry_ns, future_source_identity)
    sb = spot_book(spot_payload, spot_metadata, sr, spot_receipt); fb = dated_book(future_payload, dr, future_receipt)
    for side in ('bids','asks'): validate_ticks(fb[side], future_metadata)
    flags = local_pair_flags(spot_receipt, future_receipt, fb['publication_ns'])
    if not sr.active or not dr.active or sb['state'] != 'open' or fb['state'] != 'open': flags.append('public_market_not_open')
    if max(spot_receipt.received_utc_ns, future_receipt.received_utc_ns) >= expiry_ns: flags.append('expiry_not_future')
    srate = max(rational(spot_rate, nonnegative=True), sr.public_taker_hint or F(0))
    frate = max(rational(future_rate, nonnegative=True), dr.public_taker_rate or F(0))
    if 3*srate >= 1 or 3*frate >= 1: raise ValueError('invalid three-times fee reserve')
    face = (rational(face_target, positive=True)//dr.contract.face_step_usd)*dr.contract.face_step_usd
    if face < dr.contract.minimum_face_usd: raise ValueError('target_below_inverse_minimum')
    mid_f = (fb['bids'][0][0]+fb['asks'][0][0])/2; mid_s = (sb['bids'][0][0]+sb['asks'][0][0])/2
    whole, _ = walk(fb['bids'], face, side='sell', unit='USD_face')
    stressed = [(mid_f-3*(mid_f-p), q) for p,q in whole]
    if any(p <= 0 for p,_ in stressed): raise ValueError('stressed_inverse_price_nonpositive')
    worst_a = sum((q/p for p,q in stressed), F(0))
    required_gross = worst_a*(1+3*frate)/(1-3*srate)
    base = -((-required_gross)//sr.step)*sr.step
    n = None if profile == 'full' else 1
    inverse, _ = walk(fb['bids'][:n], face, side='sell', unit='USD_face')
    spot, _ = walk(sb['asks'][:n], base, side='buy', unit='base')
    walk(sb['bids'][:n], base, side='sell', unit='base')  # current capacity only, no future exit promise.
    reserve = sum((q*(mid_s+3*(p-mid_s)) for p,q in spot), F(0))*(1+3*srate)
    return {'coin':coin,'spot_instrument':sr.instrument,'future_instrument':dr.contract.instrument,
        'route':sr.route,'spot_step':sr.step,'face_step':dr.contract.face_step_usd,'face_usd':face,
        'spot_base':base,'spot_fills':spot,'inverse_fills':inverse,'spot_mid_usdc':mid_s,
        'future_mid_usd':mid_f,'spot_rate':srate,'future_rate':frate,'reserve_usdc':reserve,
        'spot_publication_ns':sb['publication_ns'],'future_publication_ns':fb['publication_ns'],
        'input_flags':sorted(set(flags)),'public_input_usable':not flags,
        'expiry_ns':expiry_ns,'source_effective_age_verified':False,'actual_order_allowed':False}


def projection(plan, multiple, fee_control, fee_asset):
    if multiple not in (1,2,3) or fee_control not in ('public_standard','zero_charge') or fee_asset not in ('base','quote'):
        raise ValueError('registered cost/fee/debit controls required')
    paid = fee_control == 'public_standard'
    sf = plan['spot_rate']*multiple if paid else F(0); fr = plan['future_rate']*multiple if paid else F(0)
    spot = [(plan['spot_mid_usdc']+multiple*(p-plan['spot_mid_usdc']),q) for p,q in plan['spot_fills']]
    inverse = [(plan['future_mid_usd']-multiple*(plan['future_mid_usd']-p),q) for p,q in plan['inverse_fills']]
    if any(p <= 0 for p,_ in inverse): raise ValueError('stressed inverse price nonpositive')
    a = sum((q/p for p,q in inverse), F(0)); principal = sum((p*q for p,q in spot), F(0))
    fee = a*fr; b = plan['spot_base']*(1-sf) if fee_asset == 'base' else plan['spot_base']
    spent = principal if fee_asset == 'base' else principal*(1+sf)
    return {'spot_fills':spot,'inverse_fills':inverse,'inverse_entry_cost_coin':a,
        'entry_fee_coin':fee,'net_spot_coin':b,'spot_rate':sf,'future_rate':fr,
        'initial_spend_usdc':spent,'coverage':coverage(b,a,fee),'actual_expected_net':None}
