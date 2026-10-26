#!/usr/bin/env python3
"""R259: fixed-cohort funding bounds and necessary isolated collateral; no fills."""
import argparse
import json
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lab import prereg
from scripts import unlock_market_data as data
from scripts import unlocks_daily_check as prices

LANE = ROOT / 'experiments/unlocks_funding_bounds_v1'
DAY, HOUR, AMBIGUITY, CLOCK_TOLERANCE = prices.DAY, 3600000, 15000, 60000
FEE = .001  # 10 bp per filled notional per side; stress convention, not measured MEXC costs.


def verify(raw, auxiliary):
    spec = prereg.verify(LANE / 'PREREG.md')
    text = (LANE / 'PREREG.md').read_text()
    if re.findall(r'Runner SHA-256: `([0-9a-f]{64})`', text) != [data.sha(Path(__file__).read_bytes())]:
        raise ValueError('Frozen runner changed')
    inputs = json.loads((LANE / 'INPUTS.json').read_text())
    if re.findall(r'Inputs SHA-256: `([0-9a-f]{64})`', text) != [data.sha((LANE / 'INPUTS.json').read_bytes())]:
        raise ValueError('Frozen input inventory changed')
    checks = [(Path(raw) / 'manifest.json', inputs['price_manifest_sha256']),
              (Path(auxiliary) / 'manifest.json', inputs['auxiliary_manifest_sha256'])]
    checks += [(ROOT / name, digest) for name, digest in inputs['repo_files'].items()]
    for path, digest in checks:
        if data.sha(path.read_bytes()) != digest:
            raise ValueError('Frozen input changed: ' + str(path))
    prices.verify()
    data.verify()
    return spec, inputs


def load_auxiliary(raw):
    # The exact complete acquisition manifest is pinned by verify() before values load.
    data.validate(raw)
    manifest = json.loads((Path(raw) / 'manifest.json').read_text())
    marks, funding = {}, {}
    for record in manifest['archives']:
        blob, _ = data.verify_pair(raw, record)
        rows = data.parse(blob, record)
        if record['kind'] == 'markPriceKlines':
            target = marks.setdefault(record['symbol'], {})
            for row in rows:
                if row[0] in target:
                    raise ValueError('Overlapping mark observations')
                target[row[0]] = row
        else:
            funding.setdefault(record['symbol'], []).extend(rows)
    for symbol, rows in funding.items():
        rows.sort(key=lambda r: r[0])
        funding[symbol] = (np.array([r[0] for r in rows], dtype=np.int64), rows)
    return marks, funding


def funding_bound(series, marks, entry_time, exit_time, entry_price, cash_sign):
    """Bound q*mark*rate, with an optional charge near either holding boundary."""
    if cash_sign not in (-1, 1) or not np.isfinite(entry_price) or entry_price <= 0 or exit_time <= entry_time:
        raise ValueError('Invalid leg')
    if series is None:
        return {'complete': False, 'reason': 'no funding series'}
    times, rows = series
    left = int(np.searchsorted(times, entry_time - AMBIGUITY, side='left'))
    right = int(np.searchsorted(times, exit_time + AMBIGUITY, side='right'))
    if left == 0 or right == len(times):
        return {'complete': False, 'reason': 'missing funding boundary anchor'}
    # interval_hours on the later record describes its preceding settlement interval.
    for i in range(left, right + 1):
        if abs(int(times[i] - times[i - 1]) - rows[i][1] * HOUR) > CLOCK_TOLERANCE:
            return {'complete': False, 'reason': 'funding gap or recorded interval mismatch'}
    lower = upper = positive_credit_upper = 0.
    optional = 0
    for t, interval, rate in rows[left:right]:
        mark = marks.get(t // DAY * DAY)
        if mark is None:
            return {'complete': False, 'reason': 'missing funding-day mark candle'}
        lo, hi = sorted((cash_sign * rate * mark[3] / entry_price,
                         cash_sign * rate * mark[2] / entry_price))
        if not entry_time + AMBIGUITY < t < exit_time - AMBIGUITY:
            lo, hi = min(0., lo), max(0., hi)
            optional += 1
        lower += lo
        upper += hi
        positive_credit_upper += max(0., hi)
    return {'complete': True, 'reason': '', 'lower': lower, 'upper': upper,
            'positive_credit_upper': positive_credit_upper,
            'settlements': right - left, 'optional_settlements': optional}


def mark_peak(marks, day):
    # Include mark at entry and every later holding day; mark volume is irrelevant.
    entry = marks.get(day - 7 * DAY)
    path = [marks.get(day - k * DAY) for k in range(6, -1, -1)]
    if entry is None or any(r is None for r in path):
        return None
    return max([entry[4]] + [r[2] for r in path])


def net_bounds(gross, exit_entry_ratios, funding, cost_multiple):
    if cost_multiple not in (1, 2, 3):
        raise ValueError('Unregistered cost multiple')
    cost = FEE * cost_multiple * sum(1 + x for x in exit_entry_ratios)
    result = {'price_only': gross - cost, 'lower': None, 'upper': None}
    if all(f['complete'] for f in funding):
        result['lower'] = gross + sum(f['lower'] for f in funding) - cost
        result['upper'] = gross + sum(f['upper'] for f in funding) - cost
    return result


def collateral_floor(peak, entry_price, funding, cost_multiple):
    if peak is None or not funding['complete']:
        return None
    # Gift ALL possible positive credits before the peak; omit debits, exit fees and
    # maintenance margin. Even this optimistic cash requirement is a necessary floor.
    return max(0., peak / entry_price - 1 - funding['positive_credit_upper'] + FEE * cost_multiple)


def conditional_screen(rows):
    complete = [r for r in rows if r['variant'] == 'short' and r['funding_complete']]
    if len(complete) < 30:
        return {'status': 'INSUFFICIENT', 'checks': {}, 'registry_verdict': 'PARTIAL'}
    net = np.array([r['net_lower_1x'] for r in complete])
    days = [r['day_ms'] for r in complete]
    t = prices.summary(net, days)['cluster_t']
    half = len(net) // 2
    totals = {}
    for r, x in zip(complete, net):
        totals[r['perp']] = totals.get(r['perp'], 0.) + x
    top3 = sorted(totals, key=lambda k: (-totals[k], k))[:3]
    rest = net[[r['perp'] not in top3 for r in complete]]
    checks = {'lower_means_positive_at_all_costs': all(np.mean([r[f'net_lower_{k}x'] for r in complete]) > 0 for k in (1, 2, 3)),
              'lower_1x_week_t_ge2': t is not None and t >= 2,
              'lower_1x_halves_positive': bool(net[:half].mean() > 0 and net[half:].mean() > 0),
              'lower_1x_without_top3_positive': bool(len(rest) and rest.mean() > 0)}
    passed = all(checks.values())
    return {'status': 'PASS' if passed else 'FAIL', 'checks': checks,
            'registry_verdict': 'PARTIAL' if passed else 'NULL', 'n': len(complete),
            'halves_lower_1x': [float(net[:half].mean()), float(net[half:].mean())],
            'top3_removed': top3, 'without_top3_lower_1x': float(rest.mean()) if len(rest) else None,
            'meaning': 'Conditional retrospective accounting screen; clustered t on bounds is descriptive, not a test of executable PnL.'}


def evaluate(bars, marks, funding, source_events):
    cohort = source_events[(source_events.venue == 'binance') & (source_events.window == 'archive')
                           & source_events.check.isin(['verified', 'unverified'])].sort_values(['day_ms', 'perp'])
    records, excluded = [], []
    for event in cohort.to_dict('records'):
        symbol, day = event['perp'], int(event['day_ms'])
        short = prices.price(bars, symbol, day)
        if short is None:
            excluded.append({**event, 'reason': 'R258 exact price endpoints unavailable/nontraded'})
            continue
        entry_time, exit_time = day - 6 * DAY - 1, day + DAY - 1
        f = funding_bound(funding.get(symbol), marks.get(symbol, {}), entry_time, exit_time, short['entry'], 1)
        peak = mark_peak(marks.get(symbol, {}), day)
        r = {'variant': 'short', 'perp': symbol, 'day': event['day'], 'day_ms': day,
             'entry_price': short['entry'], 'exit_price': short['exit'], 'gross': short['gross'],
             'funding_complete': f['complete'], 'funding_reason': f['reason'],
             'funding_lower': f.get('lower'), 'funding_upper': f.get('upper'),
             'settlements': f.get('settlements'), 'optional_settlements': f.get('optional_settlements'),
             'mark_peak': peak, 'mark_adverse': peak / short['entry'] - 1 if peak is not None else None,
             'positive_credit_upper': f.get('positive_credit_upper')}
        for k in (1, 2, 3):
            n = net_bounds(short['gross'], [short['exit'] / short['entry']], [f], k)
            r.update({f'price_only_{k}x': n['price_only'], f'net_lower_{k}x': n['lower'], f'net_upper_{k}x': n['upper'],
                      f'optimistic_collateral_floor_{k}x': collateral_floor(peak, short['entry'], f, k)})
        records.append(r)
        btc = prices.price(bars, 'BTCUSDT', day)
        if btc is None:
            b = {'complete': False, 'reason': 'BTC exact price endpoints unavailable/nontraded'}
        else:
            b = funding_bound(funding.get('BTCUSDT'), marks.get('BTCUSDT', {}), entry_time, exit_time, btc['entry'], -1)
        pair = {'variant': 'btc_hedged', 'perp': symbol, 'day': event['day'], 'day_ms': day,
                'funding_complete': f['complete'] and b['complete'],
                'funding_reason': '; '.join(x['reason'] for x in (f, b) if not x['complete'])}
        for k in (1, 2, 3):
            if btc is None:
                n = {'price_only': None, 'lower': None, 'upper': None}
            else:
                n = net_bounds(short['gross'] - btc['gross'],
                               [short['exit'] / short['entry'], btc['exit'] / btc['entry']], [f, b], k)
            pair.update({f'price_only_{k}x': n['price_only'], f'net_lower_{k}x': n['lower'], f'net_upper_{k}x': n['upper']})
        records.append(pair)
    stats = []
    for variant in ('short', 'btc_hedged'):
        all_rows = [r for r in records if r['variant'] == variant]
        complete = [r for r in all_rows if r['funding_complete']]
        for scope, subset, fields in [('all_priceable', all_rows, ['price_only']),
                                      ('complete_funding', complete, ['price_only', 'net_lower', 'net_upper'])]:
            for field in fields:
                for k in (1, 2, 3):
                    available = [r for r in subset if r[f'{field}_{k}x'] is not None]
                    stats.append({'variant': variant, 'scope': scope, 'quantity': field, 'cost_multiple': k,
                                  **prices.summary([r[f'{field}_{k}x'] for r in available], [r['day_ms'] for r in available])})
    shorts = [r for r in records if r['variant'] == 'short']
    shared = {(r['perp'], r['day_ms']) for r in records if r['variant'] == 'btc_hedged' and r['funding_complete']}
    matched = [r for r in shorts if (r['perp'], r['day_ms']) in shared]
    for field in ('price_only', 'net_lower', 'net_upper'):
        for k in (1, 2, 3):
            stats.append({'variant': 'short_on_hedge_cohort', 'scope': 'complete_funding', 'quantity': field,
                          'cost_multiple': k,
                          **prices.summary([r[f'{field}_{k}x'] for r in matched], [r['day_ms'] for r in matched])})
    screen = conditional_screen(records)
    risk = {}
    for k in (1, 2, 3):
        key = f'optimistic_collateral_floor_{k}x'
        available = [r for r in shorts if r[key] is not None]
        maximum = max(available, key=lambda r: r[key]) if available else None
        risk[str(k)] = {'measured': len(available), 'unknown': len(shorts) - len(available),
                       'required_collateral_over_20pct': sum(r[key] > .2 for r in available),
                       'required_collateral_over_50pct': sum(r[key] > .5 for r in available),
                       'required_collateral_over_100pct': sum(r[key] > 1 for r in available),
                       'max_floor': maximum[key] if maximum else None,
                       'max_event': {s: maximum[s] for s in ('perp', 'day', 'entry_price', 'mark_peak', 'positive_credit_upper')} if maximum else None}
    result = {'verdict': screen['registry_verdict'], 'trials': 2, 'gate': 0, 'source_events': len(cohort),
              'r258_priceable': len(shorts), 'price_excluded': len(excluded),
              'complete_short_funding': sum(r['funding_complete'] for r in shorts),
              'full_r258_cohort_funding_status': 'OBSERVED' if shorts and all(r['funding_complete'] for r in shorts) else 'INCONCLUSIVE_MISSING_WINDOWS',
              'conditional_screen': screen, 'isolated_collateral_necessary_floor': risk,
              'interpretation': 'Spent, retrospectively selected Binance events; signed funding/mark bounds and notional fee stress, not executed fills, a self-financing portfolio, exact liquidation, MEXC evidence or fresh prospective evidence.'}
    return records, excluded, stats, result


def run(raw, auxiliary, out):
    out = Path(out)
    if out.exists():
        raise FileExistsError('Fresh output directory required; preserve earlier outcomes')
    spec, inputs = verify(raw, auxiliary)
    bars, _, _ = prices.load(raw)
    marks, funding = load_auxiliary(auxiliary)
    records, excluded, stats, result = evaluate(bars, marks, funding, pd.read_csv(prices.EVENTS))
    if result['source_events'] != 530 or result['r258_priceable'] != 421:
        raise ValueError('Fixed R258 cohort changed')
    out.mkdir(parents=True)
    for name, rows in [('events.csv', records), ('excluded.csv', excluded), ('summary.csv', stats)]:
        pd.DataFrame(rows).to_csv(out / name, index=False, lineterminator='\n')
    data.put_json(out / 'verdict.json', result)
    data.put_json(out / 'manifest.json', {'prereg_sha256': spec, 'runner_sha256': data.sha(Path(__file__).read_bytes()),
        'inputs_sha256': data.sha((LANE / 'INPUTS.json').read_bytes()), 'source_manifests': {k: v for k, v in inputs.items() if k.endswith('manifest_sha256')},
        'numpy': np.__version__, 'pandas': pd.__version__, 'outputs': {p.name: data.sha(p.read_bytes()) for p in sorted(out.iterdir())}})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, default=Path('/workspace/quant-small-data/unlocks_daily_v1'))
    parser.add_argument('--auxiliary', type=Path, default=data.DEFAULT_RAW)
    parser.add_argument('--out', type=Path, default=LANE / 'results')
    args = parser.parse_args()
    print(json.dumps(run(args.raw, args.auxiliary, args.out), sort_keys=True))


if __name__ == '__main__':
    main()
