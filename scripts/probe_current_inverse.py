"""R340 bounded official sources/metadata then ONE current inverse-book capture.

No private/history/order calls, retry, redirect, replacement or budget reset.
Source HTML stays private; compact receipts and all JSON API bodies are retained.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
import multiprocessing
from pathlib import Path
import sys
import time
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab.acquisition_budget import BudgetJournal, BudgetLimits
from lab.prereg import sha256_file, verify as verify_prereg
from scripts.probe_depth_quotes import metadata_worker

LANE = ROOT/'experiments/current_inverse_v1'
NS = 1_000_000_000
CAP = 512*1024
DOCS = (
    ('coinm_info_doc', 'https://developers.binance.com/docs/derivatives/coin-margined-futures/market-data/rest-api/Exchange-Information'),
    ('coinm_depth_doc', 'https://developers.binance.com/docs/derivatives/coin-margined-futures/market-data/rest-api/Order-Book'),
    ('coinm_mark_doc', 'https://developers.binance.com/docs/derivatives/coin-margined-futures/market-data/rest-api/Index-Price-and-Mark-Price'),
    ('spot_filters_doc', 'https://developers.binance.com/docs/binance-spot-api-docs/filters'),
)
META = (
    ('coinm_info', 'https://dapi.binance.com/dapi/v1/exchangeInfo'),
    ('spot_info', 'https://api.binance.com/api/v3/exchangeInfo?'+urlencode({'symbols': '["BTCUSDT","ETHUSDT"]'})),
)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')


def verify():
    verify_prereg(LANE/'ACQUISITION.md')
    manifest = json.loads((LANE/'acquisition_inputs.json').read_text())
    if sha256_file(LANE/'acquisition_inputs.json') not in (LANE/'ACQUISITION.md').read_text():
        raise ValueError('unbound acquisition closure')
    for path, expected in manifest['sha256'].items():
        if sha256_file(ROOT/path) != expected:
            raise ValueError('acquisition code drift: '+path)


class Acquisition:
    def __init__(self):
        self.evidence = LANE/'evidence'; self.evidence.mkdir(exist_ok=True)
        self.private = ROOT/'.cache/r340-private-sources'; self.private.mkdir(parents=True, exist_ok=True)
        self.deadline = time.monotonic_ns()+180*NS
        self.budget = BudgetJournal(self.evidence/'budget.jsonl', 'R340/one-off-source-and-current-Binance-inputs',
            BudgetLimits(16, 8*1024**2, 128*NS, 8*NS))

    def reserve(self, name, url):
        utc, mono = time.time_ns(), time.monotonic_ns()
        record = self.budget.reserve(name, CAP, 8*NS, now_ns=mono, deadline_ns=self.deadline)
        if not record['dispatch_allowed']:
            raise ValueError('already charged; no second dispatch')
        return dict(name=name, url=url, started_utc_ns=utc, started_mono_ns=mono)

    def get(self, r):
        r = dict(r); body = b''; complete = False
        r.update(http_status=None, error=None)
        ctx = multiprocessing.get_context('spawn'); receiver, sender = ctx.Pipe(duplex=False)
        process = ctx.Process(target=metadata_worker, args=(r['url'], sender, CAP, 6), daemon=True)
        try:
            process.start(); sender.close(); deadline = r['started_mono_ns']+7*NS
            while time.monotonic_ns() < deadline:
                if not receiver.poll(max(0, (deadline-time.monotonic_ns())/NS)):
                    break
                try: kind, value = receiver.recv()
                except EOFError: break
                if kind == 'status': r['http_status'] = value
                elif kind == 'chunk':
                    if not isinstance(value, bytes) or len(body)+len(value) > CAP:
                        raise ValueError('bounded body contract violated')
                    body += value
                elif kind == 'done': complete = True; break
                elif kind == 'error': r['error'] = str(value)[:512]; break
                else: raise ValueError('unexpected worker message')
        except Exception as error:
            r['error'] = type(error).__name__+': '+str(error)[:400]
        finally:
            r.update(received_utc_ns=time.time_ns(), received_mono_ns=time.monotonic_ns())
            if process.pid is not None:
                if process.is_alive(): process.terminate()
                process.join(.2)
                if process.is_alive(): process.kill(); process.join(.2)
            sender.close(); receiver.close()
        doc = r['name'].endswith('_doc')
        path = (self.private if doc else self.evidence)/(r['name']+'.gz')
        with path.open('xb') as handle: handle.write(gzip.compress(body, mtime=0))
        r.update(complete=complete and len(body) < CAP, accepted_body_bytes=len(body),
            body_sha256=hashlib.sha256(body).hexdigest(), raw_body_private=doc,
            body=path.name, redirects=0, retries=0, body_cap_reached=len(body) == CAP)
        self.budget.complete(r['name'], len(body), time.monotonic_ns()-r['started_mono_ns'],
            outcome='success' if r['complete'] and r['http_status'] == 200 else 'failure')
        return r


def capture(phase):
    verify(); acq = Acquisition(); path = acq.evidence/(phase+'.json')
    if path.exists(): raise ValueError('phase already sealed; no scope reset')
    records = []; blocked = []
    if phase == 'sources':
        for name, url in DOCS:
            r = acq.get(acq.reserve(name, url)); records.append(r)
            if r['http_status'] in (301, 302, 303, 307, 308, 403, 429, 451):
                blocked.append(name+':source_access_stop'); break
            if acq.budget.status()['violations']: break
        for name, url in META:
            r = acq.get(acq.reserve(name, url)); records.append(r)
            if r['http_status'] != 200 or not r['complete']:
                blocked.append(name+':unavailable_public_metadata'); break
    else:
        verify_prereg(LANE/'PREREG.md')
        prior = json.loads((acq.evidence/'sources.json').read_text())
        if prior['blocked']:
            blocked += prior['blocked']
        else:
            metadata = json.loads(gzip.decompress((acq.evidence/'coinm_info.gz').read_bytes()))
            contracts = [s for s in metadata['symbols'] if s.get('pair') in ('BTCUSD', 'ETHUSD')
                and s.get('contractType') in ('CURRENT_QUARTER', 'NEXT_QUARTER')]
            if len(contracts) != 4 or len({(s['pair'], s['contractType']) for s in contracts}) != 4:
                blocked.append('fixed_four_contract_scope_unavailable')
            else:
                for coin in ('BTC', 'ETH'):
                    endpoints = [(coin+'_spot', 'https://api.binance.com/api/v3/depth?symbol='+coin+'USDT&limit=20')]
                    endpoints += [(s['symbol']+'_depth', 'https://dapi.binance.com/dapi/v1/depth?symbol='+s['symbol']+'&limit=20')
                        for s in contracts if s['pair'] == coin+'USD']
                    reservations = [acq.reserve(n, u) for n, u in endpoints]
                    with ThreadPoolExecutor(max_workers=3) as pool:
                        results = list(pool.map(acq.get, reservations))
                    records += results
                    if any(r['http_status'] != 200 or not r['complete'] for r in results):
                        blocked.append(coin+':public_book_unavailable'); break
    save(path, {'registry_id': 'R340', 'phase': phase, 'records': records, 'blocked': blocked,
        'budget': acq.budget.status(), 'actual_orders': 0, 'historical_requests_spent_unchanged': 7757,
        'historical_reported_mib_spent_unchanged': '229.85', 'closed_source_batch_reopened': False})
    verify(); print(json.dumps({'phase': phase, 'attempts': len(records), 'blocked': blocked,
        'accumulated_requests': acq.budget.status()['requests_charged']}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('phase', choices=('sources', 'quotes'))
    capture(p.parse_args().phase)
