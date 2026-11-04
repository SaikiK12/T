"""Invented durable paper admission/receipt/close demo; no market files or orders.

usage: python scripts/demo_paper_session.py --demo
Temporary fixture journals are removed with their temporary directory. Nothing
is written to a live account, data folder or historical lane.
"""
import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lab.paper_account import PaperEvent, CloseMark
from lab.paper_controls import RiskPolicy
from lab.paper_session import PaperSession, EntryIntent
from lab.stream_quotes import FrameClock, NS


def demo():
    anchor = FrameClock(1_790_000_000 * NS, 10 * NS)
    at = lambda n: FrameClock(anchor.utc_ns + n * NS, anchor.mono_ns + n * NS)
    balances = {('invented', 'USDT'): 1000}
    policy = RiskPolicy('invented-session-demo')
    proposal = EntryIntent(intent_id='entry-one', venue='invented', asset='USDT', symbol='FIXTURE',
        quantity_base=2, reference_price=100, expected_gross_quote=10, round_trip_cost_quote=1,
        error_bound_quote=1, error_calibrated=True)
    with tempfile.TemporaryDirectory() as d:
        with PaperSession(d, balances, anchor, policy, contract_version='fixture-v1') as session:
            admission = session.propose_entry(proposal, asof=at(1).mono_ns, clock=at(1), complete=True,
                session_open=True, fee_inputs_known=True, expected_contract_version='fixture-v1', mode='fixture')
            no_fill = len(session.account.accepted_events) == 0
        with PaperSession(d, balances, anchor, policy, contract_version='fixture-v1') as session:
            pending = session.status(at(1).mono_ns)['pending_intents']
            opened = PaperEvent('explicit-open', 'fill', 'invented', 'USDT', 'FIXTURE', at(1).utc_ns,
                at(1), 'invented supplied receipt', quantity=2, price=100, fee='.2')
            session.record_receipt(opened, at(1).mono_ns, intent_id='entry-one')
            duplicate = session.record_receipt(opened, at(1).mono_ns, intent_id='entry-one')
            quote = CloseMark('invented', 'USDT', 'FIXTURE', 2, 202, '.202', at(2), at(2).utc_ns,
                              'invented supplied liquidation quote')
            marked = session.status(at(2).mono_ns, [quote])['snapshot']
            plan = session.plan_close('invented', 'USDT', 'FIXTURE', exit_price=101,
                                       fee_rate_fraction='.001', asof=at(2).mono_ns)
            closed = PaperEvent('explicit-close', 'fill', 'invented', 'USDT', 'FIXTURE', at(2).utc_ns,
                at(2), 'invented supplied close receipt', quantity=plan['quantity_base'],
                price=plan['exit_price'], fee=plan['estimated_fee_quote'])
            session.record_receipt(closed, at(2).mono_ns)
            final = session.status(at(2).mono_ns)['snapshot']
        with PaperSession(d, balances, anchor, policy, contract_version='fixture-v1') as session:
            identical = session.status(at(2).mono_ns)['snapshot'] == final
    return {'input_scope': 'invented fixture only; supplied prices/fees are not authenticated',
            'intent_admitted': admission['intent_admitted'], 'admission_created_no_fill': no_fill,
            'pending_after_restart': pending, 'duplicate_financial_status': duplicate['financial_receipt']['status'],
            'marked_snapshot': marked, 'close_plan': plan, 'final_snapshot': final,
            'reopened_identical': identical, 'actual_order_allowed': False, 'activation_allowed': False,
            'new_prospective_paper_days': 0, 'market_profitability_validated': False}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--demo', action='store_true', help='run only the invented fixture')
    args = p.parse_args(argv)
    if not args.demo: p.error('--demo is required; no market or live-account mode exists')
    print(json.dumps(demo(), indent=2))
    return 0


if __name__ == '__main__': raise SystemExit(main())
