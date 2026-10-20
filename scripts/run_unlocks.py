#!/usr/bin/env python3
"""R265 frozen archival replication. No network, reserved sample, orders or schedules."""
import argparse
import hashlib
import gzip
import json
import re
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lab import data, panel, prereg
from scripts import unlock_events as builder

LANE = ROOT / 'experiments/unlocks_v1'
DAY, HOUR = builder.DAY, panel.HOUR
HASHES = {'events.csv': '24cd0d052bea6dcab1e4f862dad3227348644fb887ba61d14ca56cdb00cd794e',
          'symbol_map.csv': '0f924ae96cf137e8a09305aff0c07ec041f3a07cd5417643741e3366aace472b'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_inputs(snapshot, root):
    """Fail closed before event outcomes. Rebuild frozen calendar/map bytes as required."""
    spec = prereg.verify(LANE/'PREREG.md')
    prereg.verify(LANE/'IMPLEMENTATION_NOTES.md')
    declared = re.findall(r'Runner SHA-256: `([0-9a-f]{64})`', (LANE/'IMPLEMENTATION_NOTES.md').read_text())
    if declared != [digest(__file__)]:
        raise ValueError('Runner differs from its frozen implementation declaration')
    for name, expected in HASHES.items():
        if digest(LANE/name) != expected:
            raise ValueError(f'Frozen input hash mismatch: {name}')
    if not Path(snapshot).is_dir() or not (Path(root)/'klines_1h').is_dir():
        raise FileNotFoundError('Original unlock snapshot and hourly archive are required; no download/fallback')
    manifest = json.loads((Path(snapshot)/'manifest.json').read_text())
    for relative, info in manifest['files'].items():
        target = Path(snapshot)/relative
        if target.resolve().is_relative_to(Path(snapshot).resolve()) is False:
            raise ValueError('Unsafe snapshot manifest path')
        if 'error' in info or hashlib.sha256(gzip.decompress(target.read_bytes())).hexdigest() != info['sha256']:
            raise ValueError(f'Calendar manifest mismatch: {relative}')
    if not manifest['files']['emissionsIndex.json.gz']['sha256'].startswith('5600e62e'):
        raise ValueError('Not the frozen calendar index version')
    smap = builder.symbol_map(Path(snapshot), Path(root))
    events = builder.events(Path(snapshot), smap, Path(snapshot).name)
    for name, frame in [('symbol_map.csv', smap), ('events.csv', events)]:
        if frame.to_csv(index=False).encode() != (LANE/name).read_bytes():
            raise ValueError(f'Rebuilt {name} differs from frozen bytes; retain original inputs/software')
    return spec, events


class Prices:
    """Only a supplied 2021+ panel; all priceable entries/exits use positive-volume bars."""
    def __init__(self, p):
        self.p = p
        if len(p.t) == 0 or np.min(p.t) < panel.ms('2021-01-01'):
            raise PermissionError('R265 cannot read reserved pre-2021 panel rows')
        self.columns = {s: j for j, s in enumerate(p.symbols)}
        self.live, self.times = {}, {}
        for s, j in self.columns.items():
            valid = (np.isfinite(p['close'][:, j]) & (p['close'][:, j] > 0)
                     & np.isfinite(p['volume'][:, j]) & (p['volume'][:, j] > 0))
            self.live[s] = np.flatnonzero(valid)
            self.times[s] = p.t[self.live[s]]

    def last(self, symbol, boundary):
        live = self.live.get(symbol, np.array([], dtype=int))
        k = np.searchsorted(self.times.get(symbol, np.array([], dtype=np.int64)), boundary, side='right')-1
        return int(live[k]) if k >= 0 else None

    def trade(self, symbol, day, entry_offset=-7, exit_offset=0):
        entry_time = int(day)+(entry_offset+1)*DAY-HOUR
        exit_time = int(day)+(exit_offset+1)*DAY-HOUR
        if exit_time > self.p.t[-1] or entry_time < self.p.t[0]:
            return None
        a, b = self.last(symbol, entry_time), self.last(symbol, exit_time)
        if a is None or b is None or entry_time-self.p.t[a] > DAY or b < a:
            return None
        j = self.columns[symbol]
        entry, exit = float(self.p['close'][a, j]), float(self.p['close'][b, j])
        rates = self.p['fund_event'][a+1:b+1, j]
        if np.isinf(rates).any():
            raise ValueError('Infinite funding observation')
        funding = float(np.nan_to_num(rates, nan=0.).sum())
        if not np.isfinite(funding):
            raise ValueError('Infinite funding observation')
        return {'gross': 1-exit/entry, 'funding': funding, 'entry': entry, 'exit': exit,
                'entry_bar_ms': int(self.p.t[a]), 'exit_bar_ms': int(self.p.t[b]),
                'delisted_in_hold': bool(b == self.live[symbol][-1] and a <= b
                                         and self.p.t[b] < exit_time)}

    def volume_ratio(self, event):
        day, symbol = int(event['day_ms']), event['perp']
        j = self.columns[symbol]
        end = day-7*DAY-HOUR  # 23:00 of D-8
        a = self.last(symbol, end)
        if a is None or end-self.p.t[a] > DAY:
            return None
        first = day-37*DAY
        selected = (self.p.t >= first) & (self.p.t <= end)
        q = pd.Series(self.p['quote_volume'][selected, j],
                      index=pd.to_datetime(self.p.t[selected], unit='ms', utc=True))
        daily = q.resample('D').sum(min_count=1)
        daily = daily[np.isfinite(daily) & (daily > 0)]
        if len(daily) < 20:
            return None
        return float(event['tokens'])*(float(self.p['close'][a, j])/float(event['mult']))/float(daily.mean())


def statistics(values, days):
    x = np.asarray(values, float)
    if len(x) != len(days) or not np.isfinite(x).all():
        raise ValueError('Nonfinite/misaligned event statistics')
    if not len(x):
        return {'n': 0, 'mean': None, 'cluster_t': None, 'clusters': 0, 'hit_rate': None, 'worst': None}
    groups = pd.to_datetime(np.asarray(days, dtype='int64'), unit='ms', utc=True).isocalendar()
    keys = list(zip(groups.year, groups.week))
    totals = {}
    for key, value in zip(keys, x-x.mean()):
        totals[key] = totals.get(key, 0.)+float(value)
    g = len(totals)
    se = np.sqrt(g/(g-1)*sum(v*v for v in totals.values()))/len(x) if g > 1 else np.nan
    t = float(x.mean()/se) if np.isfinite(se) and se > 0 else None
    return {'n': len(x), 'mean': float(x.mean()), 'cluster_t': t, 'clusters': g,
            'hit_rate': float(np.mean(x > 0)), 'worst': float(np.min(x))}


def random_null(prices, all_events, scored, replications=2000):
    """Keep each event's symbol, with replacement; exclude +/-14d of all kept dates."""
    rng = np.random.default_rng(265)
    admissible, pools = {}, {}
    days = np.arange(panel.ms('2021-02-07'), panel.ms('2026-10-01'), DAY, dtype=np.int64)
    for symbol in sorted({r['perp'] for r in scored}):
        excluded = all_events.loc[all_events.perp == symbol, 'day_ms'].to_numpy(dtype=np.int64)
        eligible = days[np.all(np.abs(days[:, None]-excluded[None, :]) > 14*DAY, axis=1)]
        returns = []
        for day in eligible:
            trade = prices.trade(symbol, day)
            if trade is not None:
                returns.append(trade['gross']-.002)
        if not returns:
            raise ValueError(f'No admissible random dates: {symbol}')
        pools[symbol] = np.asarray(returns)
        admissible[symbol] = len(returns)
    # Event order is fixed (date, symbol); each replication draws one date per event.
    means = np.empty(replications)
    for k in range(replications):
        means[k] = np.mean([pools[r['perp']][rng.integers(len(pools[r['perp']]))] for r in scored])
    observed = np.mean([r['gross']-.002 for r in scored])
    return {'replications': replications, 'seed': 265, 'admissible_count': admissible,
            'observed_mean': float(observed), 'null_mean': float(means.mean()),
            'p': float((1+np.sum(means >= observed))/(replications+1))}


def evaluate(prices, all_events):
    primary = all_events[(all_events.venue == 'binance') & (all_events.window == 'archive')
                         & all_events.check.isin(['verified', 'unverified'])].sort_values(['day_ms', 'perp'])
    scored, excluded = [], []
    for event in primary.to_dict('records'):
        trade = prices.trade(event['perp'], int(event['day_ms']))
        if trade is None:
            excluded.append({**event, 'reason': 'no_market'})
            continue
        scored.append({**event, **trade, 'volume_ratio': prices.volume_ratio(event)})
    if not scored:
        raise ValueError('No priced primary events')
    null = random_null(prices, all_events, scored)
    days = [r['day_ms'] for r in scored]
    gross = np.array([r['gross'] for r in scored])
    net = gross-.002
    half = len(net)//2
    sums = {}
    for r, value in zip(scored, net):
        sums[r['perp']] = sums.get(r['perp'], 0.)+value
    # Alphabetic symbol is the deterministic tie-break, not a return-based rechoice.
    top = sorted(sums, key=lambda s: (-sums[s], s))[:3]
    rest = np.array([r['perp'] not in top for r in scored])
    s = statistics(net, days)
    checks = {'G1_cluster_t_ge_2': s['cluster_t'] is not None and s['cluster_t'] >= 2,
              'G2_null_p_lt_005': null['p'] < .05,
              'G3_halves_positive': half > 0 and net[:half].mean() > 0 and net[half:].mean() > 0,
              'G4_without_top3_positive': bool(rest.any() and net[rest].mean() > 0)}
    summaries = []
    def record(name, values, selected_days):
        for cost in (1, 2, 3):
            summaries.append({'variant': name, 'cost_multiple': cost,
                              **statistics(np.asarray(values)-.002*cost, selected_days)})
    record('primary', gross, days)
    record('including_funding', [r['gross']+r['funding'] for r in scored], days)
    for name, selector in [('dose_1_2', lambda r: .01 <= r['frac_max_supply'] < .02),
                           ('dose_2_5', lambda r: .02 <= r['frac_max_supply'] < .05),
                           ('dose_ge5', lambda r: r['frac_max_supply'] >= .05),
                           ('volume_ge082', lambda r: r['volume_ratio'] is not None and r['volume_ratio'] >= .82),
                           ('volume_lt082', lambda r: r['volume_ratio'] is not None and r['volume_ratio'] < .82),
                           ('verified_only', lambda r: r['check'] == 'verified')]:
        subset = [r for r in scored if selector(r)]
        record(name, [r['gross'] for r in subset], [r['day_ms'] for r in subset])
    for year in sorted({r['day'][:4] for r in scored}):
        subset = [r for r in scored if r['day'].startswith(year)]
        record('year_'+year, [r['gross'] for r in subset], [r['day_ms'] for r in subset])
    for name, start, end in [('D30_D', -30, 0), ('D_D7', 0, 7), ('btc_hedged', -7, 0)]:
        values, ds = [], []
        for r in scored:
            trade = prices.trade('BTCUSDT' if name == 'btc_hedged' else r['perp'], r['day_ms'], start, end)
            if trade is not None:
                # BTC trade.gross is a SHORT return; subtract for the prescribed long hedge.
                values.append(r['gross']-trade['gross'] if name == 'btc_hedged' else trade['gross'])
                ds.append(r['day_ms'])
        record(name, values, ds)
    return scored, excluded, summaries, {'verdict': 'REPLICATES' if all(checks.values()) else 'NULL',
        'gate': 0, 'checks': {k: bool(v) for k, v in checks.items()}, 'trials': 10,
        'random_null': null, 'top3_removed': top, 'first_half_mean': float(net[:half].mean()) if half else None,
        'second_half_mean': float(net[half:].mean()), 'without_top3_mean': float(net[rest].mean()) if rest.any() else None,
        'delisted_in_hold': sum(r['delisted_in_hold'] for r in scored),
        'interpretation': 'Historical event returns, not self-financing/liquidation-aware portfolio PnL'}


def run(snapshot, root, out):
    out = Path(out)
    if out.exists():
        raise FileExistsError('Never overwrite an existing result directory')
    spec, events = verify_inputs(snapshot, root)
    symbols = sorted(set(events.loc[(events.venue == 'binance') & (events.window == 'archive'), 'perp']) | {'BTCUSDT'})
    source_files = [Path(snapshot)/'manifest.json']
    for symbol in symbols:
        for folder in ('klines_1h', 'fundingRate', 'premiumIndexKlines_1h'):
            path = Path(root)/folder/(symbol+'.parquet')
            if path.exists():
                source_files.append(path)
    source_hashes = {str(path): digest(path) for path in source_files}
    p = panel.load_panel(symbols=symbols, root=root, start='2021-01-01')
    scored, excluded, summary, result = evaluate(Prices(p), events)
    if any(digest(path) != expected for path, expected in source_hashes.items()):
        raise ValueError('Source file changed during run; do not publish mixed-vintage outcomes')
    out.mkdir(parents=True)
    pd.DataFrame(scored).to_csv(out/'events.csv', index=False)
    pd.DataFrame(excluded).to_csv(out/'excluded.csv', index=False)
    pd.DataFrame(summary).to_csv(out/'summary.csv', index=False)
    result['prereg_sha256'] = spec
    result['runner_sha256'] = digest(__file__)
    (out/'verdict.json').write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False)+'\n')
    manifest = {'prereg_sha256': spec, 'runner_sha256': digest(__file__),
                'input_hashes': HASHES, 'source_file_hashes': source_hashes,
                'dependency_hashes': {str(path.relative_to(ROOT)): digest(path) for path in
                    (ROOT/'scripts/unlock_events.py', ROOT/'lab/panel.py', ROOT/'lab/prereg.py')}, 'python': sys.version, 'numpy': np.__version__, 'pandas': pd.__version__,
                'outputs': {p.name: digest(p) for p in sorted(out.iterdir())},
                'warning': 'Historical calendar is revised, funding gaps are zero by frozen rule; not live PnL'}
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=data.ROOT)
    parser.add_argument('--snapshot', type=Path)
    parser.add_argument('--out', type=Path, default=LANE/'results')
    args = parser.parse_args()
    result = run(args.snapshot or args.root/'unlocks/2026-10-20', args.root, args.out)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
