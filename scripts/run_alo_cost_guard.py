"""Run exactly four constructed ALO-accounting cases after frozen input checks."""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

from lab.paper_account import PaperEvent
from lab.prereg import verify
from lab.stream_quotes import FrameClock, ReferencePrice, NS
from scripts.alo_cost_guard import RequestCounts, evaluate

BASE = Path('experiments/alo_cost_guard_v1')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', required=True)
    args = p.parse_args()
    verify(BASE / 'PREREG.md')
    spec = (BASE / 'PREREG.md').read_text()
    expected = re.search(r'^Code/input manifest sha256: ([0-9a-f]{64})$', spec, re.M)
    manifest_path = BASE / 'code_inputs.json'
    if not expected or hashlib.sha256(manifest_path.read_bytes()).hexdigest() != expected.group(1):
        raise ValueError('manifest does not match frozen specification')
    manifest = json.loads(manifest_path.read_text())
    for name, digest in manifest.items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest:
            raise ValueError('frozen input or code changed: ' + name)
    data = json.loads((BASE / 'fixtures.json').read_text())
    anchor = FrameClock(data['clock_anchor_utc_ns'], data['clock_anchor_mono_ns'])
    def clk(offset):
        return FrameClock(anchor.utc_ns + offset, anchor.mono_ns + offset)
    results = []
    for case in data['cases']:
        counts = RequestCounts(*case['counts'])
        if case['fill'] is None:
            fill = before = after = None
        else:
            f = case['fill']
            fill = PaperEvent(case['id'], 'fill', 'hl', 'USDC', 'BTC', clk(NS).utc_ns,
                              clk(NS), 'constructed fixture', quantity=Decimal(f['quantity']),
                              price=Decimal(f['price']), fee=None)
            before = ReferencePrice('hl', 'BTC', clk(NS-1), clk(NS-1).utc_ns,
                                    Decimal(f['initial_mid']), 'validated_bbo_mid')
            after = ReferencePrice('hl', 'BTC', clk(2*NS), clk(2*NS).utc_ns,
                                   Decimal(f['horizon_mid']), 'validated_bbo_mid')
        for multiple in (1, 2, 3):
            row = evaluate(counts, fill, before, after, anchor=anchor,
                asof=clk(2*NS).mono_ns, horizon_ns=data['horizon_ns'],
                max_age_ns=data['max_initial_age_ns'], max_lag_ns=data['max_horizon_lag_ns'],
                capital=data['capital_usd'], entry_fee_bps=data['entry_fee_bps'],
                exit_fee_bps=data['hypothetical_passive_exit_fee_bps'],
                paid_action_usd=data['hypothetical_paid_action_usd'],
                extra_cost_usd=data['extra_cost_usd'], multiple=multiple)
            results.append({'case': case['id'], **row})
    out = {'scope': 'invented and optimistic midpoint-exit counterfactual; not return evidence',
           'strategy_trials': 0, 'prospective_days': 0, 'cells': results}
    with Path(args.out).open('x', encoding='utf-8') as handle:
        json.dump(out, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')


if __name__ == '__main__':
    main()
