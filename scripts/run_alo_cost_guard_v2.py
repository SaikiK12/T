"""Run the finite R366 correction against unchanged invented R365 inputs."""
import argparse
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

from lab.paper_account import PaperEvent
from lab.prereg import verify
from lab.stream_quotes import FrameClock, ReferencePrice, NS
from scripts.alo_cost_guard import RequestCounts, evaluate as old
from scripts.alo_cost_guard_v2 import TerminalEvidence, evaluate

BASE = Path('experiments/alo_cost_guard_v2')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    verify(BASE / 'PREREG.md')
    m = re.search(r'^Code/input manifest sha256: ([0-9a-f]{64})$', (BASE/'PREREG.md').read_text(), re.M)
    manifest = BASE/'code_inputs.json'
    if not m or hashlib.sha256(manifest.read_bytes()).hexdigest() != m.group(1):
        raise ValueError('manifest hash mismatch')
    for name, digest in json.loads(manifest.read_text()).items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest:
            raise ValueError('frozen input or code changed: ' + name)
    config = json.loads((BASE/'inputs.json').read_text())
    data = json.loads(Path(config['original_fixtures']).read_text())
    anchor = FrameClock(data['clock_anchor_utc_ns'], data['clock_anchor_mono_ns'])
    scope = tuple(config['account_scope'])
    def clk(offset):
        return FrameClock(anchor.utc_ns + offset, anchor.mono_ns + offset)
    def marks(case):
        f = case['fill']
        if f is None:
            return None, None, None
        fill = PaperEvent(case['id'], 'fill', *scope, clk(NS).utc_ns, clk(NS),
                          'constructed fixture', quantity=Decimal(f['quantity']),
                          price=Decimal(f['price']), fee=None)
        before = ReferencePrice(scope[0], scope[2], clk(NS-1), clk(NS-1).utc_ns,
                                Decimal(f['initial_mid']), 'validated_bbo_mid')
        after = ReferencePrice(scope[0], scope[2], clk(2*NS), clk(2*NS).utc_ns,
                               Decimal(f['horizon_mid']), 'validated_bbo_mid')
        return fill, before, after
    def evidence(fill, counts, **changes):
        t = config['terminal_event_offset_ns']
        kw = dict(source_identity=config['terminal_source'], venue=scope[0], asset=scope[1], symbol=scope[2],
                  order_id='fixture-order' if counts.accepted else None, occurred_ns=clk(t).utc_ns, clock=clk(t),
                  complete_fill_history=config['history_complete'],
                  fill_event_ids=(fill.event_id,) if fill else (),
                  final_filled_quantity=fill.quantity if fill else Decimal(0),
                  reported_counts=counts, clock_uncertainty_ns=0, clock_bound_source='constructed exact clock',
                  action_and_extra_costs_prepaid=config['costs_prepaid'])
        return TerminalEvidence(**{**kw, **changes})
    def params(multiple=1):
        return dict(anchor=anchor, asof=clk(2*NS).mono_ns, horizon_ns=data['horizon_ns'],
                    max_age_ns=data['max_initial_age_ns'], max_lag_ns=data['max_horizon_lag_ns'],
                    capital=data['capital_usd'], entry_fee_bps=data['entry_fee_bps'],
                    exit_fee_bps=data['hypothetical_passive_exit_fee_bps'],
                    paid_action_usd=data['hypothetical_paid_action_usd'],
                    extra_cost_usd=data['extra_cost_usd'], multiple=multiple)
    cells = []
    for case in data['cases']:
        counts = RequestCounts(*case['counts'])
        fill, before, after = marks(case)
        for multiple in (1, 2, 3):
            row = evaluate(counts, evidence(fill, counts), fill, before, after,
                           account_scope=scope, **params(multiple))
            cells.append({'case': case['id'], 'multiple': multiple, **row})
    # These deliberately retain old false scores alongside new guarded states.
    c = RequestCounts(1, 0, 0, 0, 0, 1, True)
    f, a, b = marks({'id':'audit','fill':{'quantity':'2','price':'100','initial_mid':'100.1','horizon_mid':'100.2'}})
    k = params()
    k.update(capital='1000', entry_fee_bps='1', exit_fee_bps='1', paid_action_usd='.001', max_age_ns=10, max_lag_ns=10)
    def probe(name, counts, ev, fill, first, later, kw):
        def run(which):
            try:
                if which == 'v1':
                    out = old(counts, fill, first, later, **kw)
                else:
                    out = evaluate(counts, ev, fill, first, later, account_scope=scope, **kw)
                return {'status':out['status'], 'component_usd':out.get('component_usd')}
            except ValueError as exc:
                return {'status':'REJECTED', 'reason':str(exc)}
        return {'name':name,'v1':run('v1'),'v2':run('v2')}
    late = replace(a, clock=FrameClock(a.clock.utc_ns, f.clock.mono_ns+10_000_000))
    regressions = [probe('quote_received_late', c, evidence(f, c), f, late, b, k)]
    delayed = replace(f, clock=clk(NS+40_000_000))
    after_economic = replace(a, clock=FrameClock(a.clock.utc_ns, anchor.mono_ns+NS+10_000_000))
    regressions.append(probe('quote_after_economic_fill', c, evidence(delayed, c), delayed, after_economic, b, k))
    inconsistent = replace(a, clock=FrameClock(a.clock.utc_ns, anchor.mono_ns+980_000_000))
    regressions.append(probe('inconsistent_source_receipt_clock', c, evidence(f, c), f, inconsistent, b, k))
    nofill = RequestCounts(0, 10, 0, 0, 10, 0, True)
    regressions.append(probe('asof_before_anchor', nofill, evidence(None, nofill), None, None, None, {**k,'asof':0}))
    cancel = RequestCounts(1, 0, 0, 1, 1, 0, True)
    regressions.append(probe('cancel_partial_history_unknown', cancel, evidence(None, cancel, complete_fill_history=False), None, None, None, k))
    costly = RequestCounts(1, 9, 0, 0, 10, 1, True)
    regressions.append(probe('prepaid_capital_shortfall', costly, evidence(f, costly), f, a, b, {**k,'capital':'200.02'}))
    short = replace(f, quantity=Decimal('-2'))
    deep_loss = replace(b, price=Decimal('300'))
    regressions.append(probe('end_capital_insolvent', c, evidence(short, c), short, a, deep_loss,
                             {**k,'capital':'200','entry_fee_bps':'0','exit_fee_bps':'0'}))
    regressions.append(probe('no_fill_capital_exhausted', nofill, evidence(None, nofill), None, None, None,
                             {**k,'capital':'.01'}))
    if [r['name'] for r in regressions] != config['regressions']:
        raise AssertionError('unregistered regression set')
    output = {'scope':'constructed midpoint exits and attested fixtures, not market PnL',
              'strategy_trials':0,'prospective_days':0,'cells':cells,'adversarial':regressions}
    with Path(args.out).open('x', encoding='utf-8') as handle:
        json.dump(output, handle, sort_keys=True, indent=2, allow_nan=False)
        handle.write('\n')


if __name__ == '__main__':
    main()
