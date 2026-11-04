"""Run an invented funding-notional sign-flip demo; never reads market files."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab.funding_notional import FundingTerm, audit_notional  # noqa: E402


def demo():
    term = FundingTerm(venue='invented', symbol='FIXTURE', asset='USDT', event_id='invented-settlement',
                       funding_ns=2, rate='-0.003', rate_unit='fraction', rate_stage='settled',
                       settlement_price='200', value_basis='settlement_mark',
                       source_identity='invented arithmetic fixture, not a market observation',
                       eligible=True, payment_kind='regular')
    return audit_notional(venue='invented', symbol='FIXTURE', asset='USDT', quantity_base='1',
                          entry_price='100', exit_price='100', entry_ns=1, exit_ns=3, events=[term],
                          round_trip_cost_quote='0.4', expected_value_basis='settlement_mark', schedule_complete=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true', required=True, help='explicitly select invented inputs only')
    parser.parse_args(argv)
    print(json.dumps(dict(input_scope='invented fixture only; no historical reanalysis', audit=demo()), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
