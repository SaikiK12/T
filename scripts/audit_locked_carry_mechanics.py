"""R407: frozen invented carry mechanics, fixed quantities and independent cash ledger.

No market acquisition, historical/forward scoring, orders or predictive trials.
Run --run after freezing and publishing the protocol. Outputs never overwrite.
"""
import argparse
from dataclasses import asdict
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lab import prereg
from lab.inverse_cash import InverseContract, InverseCashAccount, InverseEvent, rational, wire, unwire, walk
from lab.locked_carry import SpotContract, CarryFees, plan_carry, evaluate_carry
from lab.stream_quotes import FrameClock, NS
from scripts import lockcarry_rule as legacy

LANE = ROOT / 'experiments/locked_carry_mechanics_v1'
ANCHOR = FrameClock(1_790_000_000 * NS, 10 * NS)


def verify():
    digest = prereg.verify(LANE / 'PREREG.md')
    manifest_path = LANE / 'code_inputs.json'
    declared = (LANE / 'PREREG.md').read_text()
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() not in declared:
        raise ValueError('manifest is not bound by the protocol')
    for name, sha in json.loads(manifest_path.read_text()).items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != sha:
            raise ValueError('frozen input changed: ' + name)
    return digest


def exact(value):
    if isinstance(value, F): return wire(value)
    if isinstance(value, dict): return {k: exact(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)): return [exact(v) for v in value]
    return value


def ledger_oracle(plan, bids, k, price, ratio):
    """Post inverse fills/daily realization/delivery to the existing cash engine."""
    buy, entry, delivery, sell = plan.fees.at(k)
    coin = plan.spot_order_base * (1 - buy) if plan.fees.spot_buy_basis == 'base_received' else plan.spot_order_base
    account = InverseCashAccount(plan.future, coin, ANCHOR)
    def post(id, kind, n, p, face=F(0), fee=F(0)):
        at = FrameClock(ANCHOR.utc_ns + n * NS, ANCHOR.mono_ns + n * NS)
        event = InverseEvent(id, kind, plan.future.instrument, at.utc_ns, at,
                             'R407 invented ledger oracle', p, face, fee)
        if account.post(event, at.mono_ns)['status'] != 'applied':
            raise AssertionError('ledger rejected an invented oracle event')
    fills, _ = walk(bids, plan.face_usd, side='sell', unit='USD_face')
    for n, (p, face) in enumerate(fills, 1):
        post('open-' + str(n), 'open', n, p, -face, face / p * entry)
    post('daily', 'daily', 50, 2 * price)
    post('delivery', 'delivery', 100, price, fee=plan.face_usd / price * delivery)
    # Actual sale of a grid quantity; remaining coins are retained, not cash.
    coin_per_sale = 1 + sell if plan.fees.spot_sell_basis == 'base_in_addition' else F(1)
    order = (account.coin / coin_per_sale // plan.spot.step_base) * plan.spot.step_base
    if order < plan.spot.minimum_base or order * price * ratio < plan.spot.minimum_quote:
        order = F(0)
    exit_fee = order * price * ratio * sell if plan.fees.spot_sell_basis == 'quote_received' else F(0)
    spend = plan.spot_order_quote * (1 + buy if plan.fees.spot_buy_basis == 'quote_in_addition' else 1)
    return dict(cash=plan.budget_quote - spend + order * price * ratio - exit_fee,
                dust=account.coin - order * coin_per_sale, ledger_coin=account.coin)


def audit():
    protocol = verify()
    fixtures = json.loads((LANE / 'fixtures.json').read_text())
    results = []
    for case in fixtures['cases']:
        spot = SpotContract('TOY_QUOTE', 'TOY', 'QUOTE', case['spot_step'], case['spot_min'],
                            case['spot_min_quote'], 'R407 invented metadata')
        future = InverseContract('TOY-DATED', 'TOY', case['face_step'], case['face_min'],
                                 ANCHOR.utc_ns + 100 * NS, 'R407 invented metadata')
        out = dict(case=case['id'], input_scope='invented only', expected_error=case.get('expected_error'))
        try:
            fees = CarryFees(**case['fees'], source_identity='R407 invented explicit fee contract')
            p = plan_carry(spot, future, fees, case['spot_asks'], case['future_bids'], case['budget'],
                           sizing_cost_multiple=3)
        except ValueError as exc:
            if not case.get('expected_error'):
                raise
            out.update(state='EXPECTED_BLOCK', reason=str(exc))
            results.append(out)
            continue
        if case.get('expected_error'):
            raise AssertionError('expected incomplete/thin case was not blocked')
        buy, entry, _, _ = fees.at(3)
        available_coin = p.spot_order_base * (1 - buy) if fees.spot_buy_basis == 'base_received' else p.spot_order_base
        assert (1 + entry) * p.inverse_entry_coin_basis <= available_coin
        if p.next_face_coin_requirement is not None:
            assert p.next_face_coin_requirement > available_coin
        out.update(state='CHECKED', fixed_plan=exact(asdict(p)), worlds=[])
        if case.get('legacy_comparison'):
            def floats(book): return [(float(price), float(size)) for price, size in book]
            old = legacy.offer(floats(case['spot_bids']), floats(case['spot_asks']), floats(case['future_bids']),
                               float(case['face_step']), 100 * legacy.DAY_MS, 0,
                               float(fees.spot_buy), float(fees.future_entry), usd=float(case['budget']))
            out['legacy_native_toy'] = dict(face=old['q_usd'], residual_coin=old['unhedged_coins'],
                cash_by_delivery=[dict(price=x, cash=legacy.settle(old, float(x))['usd_out'])
                                  for x in case['delivery_prices']])
        for k in (1, 2, 3):
            for price in case['delivery_prices']:
                ratio = case['exit_ratio']
                row = evaluate_carry(p, cost_multiple=k, delivery_price=price, exit_ratio=ratio,
                    exit_ratio_floor=case['exit_ratio_floor'], delivery_price_ceiling=case['delivery_price_ceiling'])
                row['delivery_price'] = price
                if ratio is not None:
                    oracle = ledger_oracle(p, case['future_bids'], k, rational(price), rational(ratio))
                    assert unwire(row['terminal_proceeds_quote']) == oracle['cash']
                    assert unwire(row['unsold_dust_coin']) == oracle['dust']
                    row['independent_cash_ledger'] = exact(oracle)
                    lower = row['conditional_lower_proceeds_quote']
                    if (lower is not None and row['observed_exit_ratio_satisfies_floor'] is True
                            and row['observed_delivery_price_satisfies_ceiling'] is True):
                        assert oracle['cash'] >= unwire(lower)
                out['worlds'].append(row)
        results.append(out)
    verify()
    return dict(round='R407', prereg_sha256=protocol, results=results,
        predictive_trials=0, prospective_paper_days=0, market_acquisitions=0,
        actual_order_allowed=False, activation_allowed=False,
        scope='exact invented mechanics and legacy formula diagnosis, not market profitability or live fills')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--output', type=Path, default=LANE / 'results.json')
    args = parser.parse_args(argv)
    if not args.run:
        parser.error('--run is required')
    result = audit()
    with args.output.open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.write('\n')
    print('R407: frozen invented payoff/ledger audit completed; no market verdict.')
    return 0


if __name__ == '__main__': raise SystemExit(main())
