"""R359 raw identity/timing and independent Fraction financial reconstruction.

No financial account, quote/pricing, risk or controller functions are imported.
Full-book state equivalence is additionally checked by the separate offline
reproduction using the frozen assembler, not claimed as an independent parser.
"""
import argparse
from fractions import Fraction as F
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANE = ROOT / 'experiments/live_pair_controls_v1'
NS = 1_000_000_000


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


class Check:
    def __init__(self):
        self.n = 0

    def eq(self, a, b, label):
        self.n += 1
        if a != b:
            raise AssertionError((label, a, b))

    def near(self, a, b, label):
        self.n += 1
        if a is None or abs(F(str(a)) - b) > F('1e-65'):
            raise AssertionError((label, a, str(b)))


def journal(c, path):
    previous = '0' * 64
    rows = []
    for i, line in enumerate(path.read_text().splitlines()):
        row = json.loads(line)
        digest = row['sha256']
        base = {k: v for k, v in row.items() if k != 'sha256'}
        c.eq(row['sequence'], i, 'append-only journal sequence')
        c.eq(row['previous_sha256'], previous, 'append-only predecessor')
        c.eq(hashlib.sha256(encoded(base).rstrip(b'\n')).hexdigest(), digest, 'journal hash')
        previous = digest
        rows.append(row)
    return rows


def sweep(book, q):
    left, total = abs(q), F(0)
    for price, size in book['asks' if q > 0 else 'bids']:
        take = min(left, F(str(size)))
        total += take * F(str(price))
        left -= take
        if left == 0:
            return total / abs(q)
    raise AssertionError('a financial fill exceeded actual shown depth')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(exist_ok=False)
    c = Check()
    spec = (LANE / 'PREREG.md').read_bytes()
    c.eq(hashlib.sha256(spec).hexdigest(), (LANE / 'PREREG.sha256').read_text().strip(), 'frozen spec')
    for name in ('code_inputs.json', 'config.json', 'sources.json'):
        c.eq(hashlib.sha256((LANE / name).read_bytes()).hexdigest() in spec.decode(), True, 'bound manifest')
    for p, digest in read(LANE / 'code_inputs.json')['sha256'].items():
        c.eq(hashlib.sha256((ROOT / p).read_bytes()).hexdigest(), digest, 'frozen source/input:' + p)
    identity, result, config = (read(LANE / p) for p in ('evidence_inputs.json', 'results.json', 'config.json'))
    files = {str(p.relative_to(LANE)) for p in (LANE / 'evidence').rglob('*') if p.is_file()}
    c.eq(files, set(identity['sha256']), 'complete sealed evidence inventory')
    for p, digest in identity['sha256'].items():
        c.eq(hashlib.sha256((LANE / p).read_bytes()).hexdigest(), digest, 'sealed capture identity')
    c.eq(hashlib.sha256((LANE / 'results.json').read_bytes()).hexdigest(), identity['result_sha256'], 'sealed online result')
    scope = read(LANE / 'evidence/receipts.json')
    c.eq(scope['scope_state'], 'CLOSED', 'scope cannot renew')
    c.eq(0 <= scope['requests'] <= 7, True, 'metadata request cap')
    c.eq(scope['unused_metadata_slots_closed'], 7 - scope['requests'], 'unused slots close')
    c.eq(len(scope['records']), scope['requests'], 'all attempts retained')
    c.eq(0 <= scope['response_bytes'] <= scope['response_body_read_upper_bound'] <= 2 * 1024**2, True, 'body and uncertain-tail cap')
    c.eq(scope['duration_seconds'] <= 120, True, 'whole collection duration cap')
    c.eq(sum(r['bytes'] for r in scope['records']), scope['response_bytes'], 'body counter')
    c.eq(sum(r['body_read_upper_bound'] for r in scope['records']), scope['response_body_read_upper_bound'], 'uncertain-tail counter')
    denied = False
    start = scope['metadata_window_started_clock']
    for r in scope['records']:
        c.eq(denied, False, 'no new request after denial')
        denied = r.get('http_status') in (401, 403, 429, 451, 503)
        c.eq(0 <= r['started_mono_ns'] - start['mono_ns'] < 20 * NS, True, 'request-start window')
        c.eq(r['received_mono_ns'] >= r['started_mono_ns'], True, 'observed request/receipt causality')
        body = gzip.decompress((LANE / 'evidence' / r['body']).read_bytes())
        c.eq(len(body), r['bytes'], 'raw body size')
        c.eq(hashlib.sha256(body).hexdigest(), r['sha256'], 'raw body digest')
        c.eq(r['bytes'] <= r['body_read_upper_bound'] <= 1024**2, True, 'individual read cap')
    frames = [json.loads(line) for line in gzip.decompress((LANE / 'evidence/first_seen.jsonl.gz').read_bytes()).splitlines()]
    c.eq(len(frames), scope['mirrored_first_seen_frames'], 'every own first-seen frame retained')
    connections = read(LANE / 'evidence/connections.json')
    anchor_path = LANE / 'evidence/anchor.json'
    anchor = read(anchor_path) if anchor_path.exists() else None
    overruns = 0
    for venue in ('mexc', 'lighter'):
        xs = [x for x in frames if x['venue'] == venue]
        c.eq(sum(len(x['raw'].encode()) for x in xs) <= 8 * 1024**2, True, 'stream payload cap')
        c.eq(len(xs) <= 20000, True, 'message cap')
        state = connections.get(venue, {})
        c.eq(state.get('handshake_attempts', 0) <= 1, True, 'one handshake, no reconnect')
        if denied:
            c.eq(state.get('handshake_attempts', 0), 0, 'no stream after source denial')
        parent_path = LANE / 'evidence' / (venue + '.jsonl.gz')
        parents = {} if not parent_path.exists() else {x['number']: x for x in map(json.loads, gzip.decompress(parent_path.read_bytes()).splitlines())}
        c.eq(len(xs), len(parents), 'one mirror per parent frame, no extra receive')
        for f in xs:
            c.eq(len(f['raw'].encode()) <= 256 * 1024, True, 'frame cap')
            c.eq(f['read_started_mono_ns'] <= f['mono_ns'], True, 'actual read start precedes full-body first seen')
            c.eq(f['read_started_mono_ns'] < anchor['mono_ns'] + 65 * NS, True, 'no new receive after read window')
            c.eq(f['mono_ns'] <= parents[f['number']]['mono_ns'], True, 'own earliest receipt precedes parent recording')
            c.eq(f['raw'], parents[f['number']]['raw'], 'exact same underlying frame')
            overruns += f['mono_ns'] > anchor['mono_ns'] + 65 * NS
    expected_ids = {f'{s}_d{d}_k{k}' for s in config['symbols'] for d in config['directions'] for k in config['cost_multiples']}
    c.eq({x['id'] for x in result['cells']}, expected_ids, 'all fixed control variants/costs retained')
    c.eq(len(result['cells']), 36, 'no cell omitted or duplicated')
    c.eq(result['diagnostic_variants'], 12, 'all distinct control variants counted')
    c.eq(result['prospective_strategy_days'], 0, 'no unqualified paper day')
    c.eq(result['full_net_pnl'], None, 'unverified funding cannot become net profit')
    stages = {}
    for receipt in result['online_receipts']:
        stage = receipt['stage']
        stages[stage] = receipt
        d, issued = receipt['decision_clock'], receipt['issued_clock']
        c.eq(d['mono_ns'] <= issued['mono_ns'], True, 'decision before actual persisted issue')
        c.eq(receipt['on_time'], issued['mono_ns'] <= receipt['planned_mono_ns'] + config['deadline_lateness_ns'], 'original lateness rule')
        c.eq(abs((d['utc_ns'] - anchor['utc_ns']) - (d['mono_ns'] - anchor['mono_ns'])) <= 50_000_000, True, 'decision local UTC coherence')
        for venue in ('mexc', 'lighter'):
            prefix = [f for f in frames if f['venue'] == venue and f['mono_ns'] <= d['mono_ns']]
            c.eq(receipt['source_prefixes'][venue]['frames'], len(prefix), 'actual asof frame count')
            c.eq(receipt['source_prefixes'][venue]['sha256'], hashlib.sha256(b''.join(encoded(x) for x in prefix)).hexdigest(), 'no future source frame in snapshot')
        if stage.endswith('_execution'):
            original = stages[stage.replace('_execution', '_decision')]
            c.eq(d['mono_ns'] >= original['issued_clock']['mono_ns'] + 300_000_000, True, 'minimum300ms after persisted original decision')
        for view in receipt['views'].values():
            for book in view['books']:
                if book is None:
                    continue
                c.eq(book['clock']['mono_ns'] <= d['mono_ns'], True, 'book actually received before action')
                c.eq(len(encoded(book)) <= 65536, True, 'full snapshot evidence cap')
    if stages:
        raw = [json.loads(x) for x in (LANE / 'evidence/online/online_receipts.jsonl').read_text().splitlines()]
        c.eq(len(raw), 2 * len(stages), 'separate receipt and actual completion records')
        cash_rows = journal(c, LANE / 'evidence/online/cash_reference.jsonl')
        marks = [r['event']['payload'] for r in cash_rows if r['event'].get('kind') == 'paper_evidence']
        c.eq(len(marks), len(stages), 'each decision hash committed before later stage')
        for i in range(len(stages)):
            payload, completion, proof = raw[2*i], raw[2*i+1], marks[i]
            c.eq(hashlib.sha256(encoded(payload)).hexdigest(), proof['receipt_sha256'], 'durable raw snapshot/quantity hash')
            c.eq(completion['kind'], 'receipt_completion', 'actual completion is not synthesized')
            c.eq(completion['issued_clock'], stages[payload['stage']]['issued_clock'], 'actual issue clock preserved')
    fills = 0
    complete = 0
    for cell in result['cells']:
        for field in ('funding_cash', 'full_net_pnl', 'actual_expected_net'):
            c.eq(cell[field], None, 'missing financial evidence remains unknown:' + field)
        native = cell['price_fee_only_native_snapshot']
        if native is None:
            c.eq(cell['entry']['state'], 'not_started', 'no reconstructed account/ticket before capture')
            continue
        q = {} ; basis = {} ; cash = {v: F(config['capital_per_venue']) for v in ('mexc', 'lighter')}
        fees = {v: F(0) for v in cash}; prices = {v: F(0) for v in cash}
        path = LANE / 'evidence/online' / (cell['id'] + '.jsonl')
        rows = journal(c, path)
        for row in rows:
            event = row['event']
            if event.get('kind') != 'paper_account_attempt':
                continue
            e = event['payload']; fills += 1
            c.eq(e['kind'], 'fill', 'only known price/fee components posted')
            c.eq(e['simulation_only'], True, 'no actual fill claim')
            venue, symbol = e['venue'], e['symbol']
            oldq = q.get(venue, F(0)); newq = F(e['quantity']); px = F(e['price']); fee = F(e['fee'])
            phase = 'entry_execution' if oldq == 0 else 'exit_execution'
            source = stages[phase]; view = source['views'][symbol]
            book = view['books'][0 if venue == 'mexc' else 1]
            c.eq(e['clock'], source['decision_clock'], 'modeled action clock after decision, not backdated quote receipt')
            c.eq(e['occurred_ns'], e['clock']['utc_ns'], 'economic model time equals actual evaluation')
            decided = F(stages['entry_decision']['views'][symbol]['quantity'])
            c.near(abs(newq), decided, 'quantity fixed at original decision')
            c.eq(view['reasons'], [], 'no stale/thin/disconnected/negative-session financial fill')
            mid = F(str(float(book['bids'][0][0]) / 2 + float(book['asks'][0][0]) / 2))
            base = sweep(book, newq)
            stress_price = mid + cell['cost_multiple'] * (base - mid)
            c.near(px, stress_price, 'exact shown-depth cash and fixed cost stress')
            expected_fee = abs(newq) * px * F(config['fees_bp'][venue]) * cell['cost_multiple'] / 10000
            c.near(fee, expected_fee, 'fee on this execution notional')
            if oldq == 0:
                basis[venue] = px
                c.eq(abs(newq) * px + fee <= cash[venue], True, 'separate venue capital at entry')
            else:
                c.near(newq, -oldq, 'exit closes held inventory, not another dollar target')
                gain = oldq * (px - basis[venue]); cash[venue] += gain; prices[venue] += gain
            cash[venue] -= fee; fees[venue] += fee; q[venue] = oldq + newq
        subtotal = F(0)
        for account in native['accounts']:
            v = account['venue']
            c.near(account['known_cash_component'], cash[v], 'native known price/fee cash component')
            c.near(account['realized_price_pnl'], prices[v], 'realized price once')
            c.near(account['fees_paid'], fees[v], 'fee once; no extra spread debit')
            c.near(account['funding_pnl'], F(0), 'no fabricated funding cash post; outer total stays UNKNOWN')
            c.eq(bool(account['positions']), bool(q.get(v, 0)), 'unknown exits preserve quantity')
            if account['positions']:
                c.near(account['positions'][0]['quantity_base'], q[v], 'native open quantity')
            subtotal += (prices[v] - fees[v]) * F(config['fx_scenario'][account['asset']])
        c.eq(cell['price_fee_fx_scenario'], config['fx_scenario'], 'explicit conversion scenario, not implicit stablecoin parity')
        c.near(cell['known_realized_price_fee_component'], subtotal, 'known subtotal over BOTH venue accounts')
        closed = bool(cell['entry'] and cell['entry']['state'] == 'conditional_model') and not any(q.values())
        if closed:
            complete += 1
            c.near(cell['closed_price_fee_subtotal'], subtotal, 'closed known subtotal, not full net')
            c.near(cell['funding_needed_to_break_even'], -subtotal, 'unverified funding hurdle')
        else:
            c.eq(cell['closed_price_fee_subtotal'], None, 'inactive/incomplete is not a completed return')
    audit = {'registry_id': 'R359', 'status': 'PASS', 'checks': c.n, 'cells': 36,
             'native_model_fills': fills, 'closed_price_fee_cells': complete,
             'actual_issued_receipts': len(stages), 'on_time_issued_receipts': sum(r['on_time'] for r in stages.values()),
             'received_after_stream_window_frames_preserved': overruns,
             'diagnostic_variants': 12, 'prospective_strategy_days': 0, 'full_net_pnl': None,
             'scope': 'independent financial/timing/raw identity; source assembly equivalence uses separate frozen-assembler replay'}
    with (out / 'audit.json').open('x') as handle:
        handle.write(encoded(audit).decode())
    print(json.dumps(audit, sort_keys=True))


if __name__ == '__main__':
    main()
