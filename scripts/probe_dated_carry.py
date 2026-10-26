"""R327 ONE finite public CURRENT snapshot; no order/account/history requests."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lab.acquisition_budget import BudgetJournal,BudgetLimits
from lab.prereg import sha256_file
from lab.stream_quotes import NS
from scripts.probe_spot_costs import Acquisition as OldAcquisition,fatal
from scripts.run_dated_carry import verify,LANE,save


class Acquisition(OldAcquisition):
    def __init__(self,out):
        self.out=Path(out);self.deadline=time.monotonic_ns()+90*NS
        self.budget=BudgetJournal(self.out/'budget.jsonl','R327/current-dated-spot/one-attempt',
                                 BudgetLimits(7,512*1024,49*NS,7*NS))


def capture(lane=LANE):
    fixtures=verify(lane);out=lane/'evidence';out.mkdir()  # refuses reset, including a failed attempt
    acq=Acquisition(out);records=[];stopped=False
    endpoints=[('spot_rules','https://api.mexc.com/api/v3/exchangeInfo?symbols=BTCUSDT,ETHUSDT')]
    endpoints.extend((coin+'_instrument','https://www.deribit.com/api/v2/public/get_instrument?instrument_name='+name)
                     for coin,name in fixtures['instruments'].items())
    for name,url in endpoints:
        r=acq.get_reserved(acq.reserve(name,url));records.append(r)
        if fatal(r) or acq.budget.status()['violations']:stopped=True;break
    with ThreadPoolExecutor(max_workers=2) as pool:
        for coin,name in fixtures['instruments'].items():
            if stopped:break
            pairs=[(coin+'_spot','https://api.mexc.com/api/v3/depth?symbol='+coin+'USDT&limit=5'),
                   (coin+'_dated','https://www.deribit.com/api/v2/public/get_order_book?instrument_name='+name+'&depth=5')]
            # Reserve both BEFORE dispatch; a failure never refunds the other.
            rs=[acq.reserve(n,u) for n,u in pairs]
            futures=[pool.submit(acq.get_reserved,r) for r in rs]
            results=[f.result() for f in futures];records.extend(results)
            if any(fatal(r) for r in results) or acq.budget.status()['violations']:stopped=True
    save(out/'capture.json',{'registry_id':'R327','records':records,'fatal_stop':stopped,'budget':acq.budget.status(),
          'historical_requests_spent_unchanged':7757,'historical_reported_mib_spent_unchanged':'229.85',
          'scope':'one current snapshot, fixed BTC/ETH Dec25dated; seven public HTTPGET maximum, no retries/redirect/replacement',
          'public_JSONRPC_over_HTTP_is_not_private_account_or_chain_RPC':True,'actual_orders':0})
    save(lane/'data_inputs.json',{'registry_id':'R327','prereg_sha256':sha256_file(lane/'PREREG.md'),
          'code_inputs_sha256':sha256_file(lane/'code_inputs.json'),
          'sha256':{str(p.relative_to(ROOT)):sha256_file(p) for p in sorted(out.iterdir()) if p.is_file()}})
    print('Raw current snapshot sealed. Commit all raw inputs before any economic calculation.')


if __name__=='__main__':capture()
