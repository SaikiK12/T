"""Compare finite invented sizes at1x/2x/3x costs through strict paper admission.

Run with --demo. No market input, data acquisition, orders or persistent writes.
The largest passing evaluated size is not a maximum safe or profitable bet.
"""
import argparse
from decimal import Decimal
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lab.paper_controls import RiskPolicy
from lab.paper_entry_risk import EntryLossPolicy, EntryScenario
from lab.paper_session import EntryIntent, PaperSession
from lab.stream_quotes import FrameClock, NS


def demo():
    anchor = FrameClock(1_790_000_000 * NS, 10 * NS)
    at = FrameClock(anchor.utc_ns + NS, anchor.mono_ns + NS)
    loss_policy = EntryLossPolicy('invented-15-quote-budget',
        (('fixture', 'USDT', 15),), ('half_price_gap',))
    rows = []
    with tempfile.TemporaryDirectory() as directory:
        for q in map(Decimal, ('.1', '.5', '2.5')):
            proposal = EntryIntent(intent_id='fixed-size', venue='fixture', asset='USDT',
                symbol='INVENTED', quantity_base=q, reference_price=100,
                expected_gross_quote=q * 10, round_trip_cost_quote=q * Decimal('.2'),
                error_bound_quote=q * Decimal('.5'), error_calibrated=True)
            stress = EntryScenario(scenario_id='half_price_gap', venue='fixture', asset='USDT',
                symbol='INVENTED', quantity_base=q, entry_price=100, exit_price=50,
                entry_fee_quote=q * Decimal('.1'), exit_fee_quote=q * Decimal('.1'),
                funding_quote=0, extra_loss_quote=0)
            for k in (1, 2, 3):
                with PaperSession(Path(directory) / f'{q}-{k}', {('fixture', 'USDT'): 1000}, anchor,
                        RiskPolicy('invented-risk'), contract_version='invented-v1',
                        entry_loss_policy=loss_policy) as session:
                    result = session.propose_entry(proposal, asof=at.mono_ns, clock=at,
                        complete=True, session_open=True, fee_inputs_known=True,
                        expected_contract_version='invented-v1', mode='fixture',
                        cost_multiple=k, loss_scenarios=[stress])
                    rows.append(dict(quantity_base=str(q), cost_multiple=k,
                        intent_admitted=result['intent_admitted'], reasons=result['reasons'],
                        loss=result['loss_assessment'], fills_created=len(session.account.accepted_events)))
    return dict(scope='invented exact-size inputs only; no validated market edge or execution',
        evaluated_sizes=rows, actual_order_allowed=False, activation_allowed=False,
        new_prospective_paper_days=0)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true')
    args = parser.parse_args(argv)
    if not args.demo:
        parser.error('--demo is required; no market or account mode exists')
    print(json.dumps(demo(), indent=2, allow_nan=False))
    return 0


if __name__ == '__main__': raise SystemExit(main())
