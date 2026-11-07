"""Run the real adapters/checker on a completely synthetic temporary API corpus."""
from pathlib import Path
import tempfile
import json
import gzip
import hashlib
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from scripts import run_kraken_carry as runner, check_kraken_carry as checker


def enc(x):
    return (json.dumps(x, default=str)+"\n").encode()


class IntegrationTest(unittest.TestCase):
    def test_synthetic_two_asset_cash_depth_and_tamper(self):
        with tempfile.TemporaryDirectory() as td:
         root=Path(td);source=root/'source';lane=root/'lane';source.mkdir();lane.mkdir();(lane/'results').mkdir();(root/'registry').mkdir()
         (root/'registry/rounds.csv').write_text('id,date,lane,title,status,verdict,trials,prereg_sha,path,notes\nR1,2026-01-01,x,x,REGISTERED,PENDING,2,,x,x\n')
         start=1767225600;end=start+2*86400;symbols={'xbt':{'base':'BTC','perp':'PF_XBTUSD','spot':'XXBTZUSD'},'eth':{'base':'ETH','perp':'PF_ETHUSD','spot':'XETHZUSD'}}
         spec={'instruments':symbols,'capitals':['10000','25000','50000','100000'],'start':'2026-01-01T00:00:00Z','end':'2026-01-03T00:00:00Z','spot_taker':'.008','perp_taker':'.0005','historical_slip_per_side':'.0001','annual_hurdle_assumption':'.04'}
         margins={'retail':[{'numNonContractUnits':0,'initialMargin':'.1','maintenanceMargin':'.05'},{'numNonContractUnits':30000000,'initialMargin':'.2','maintenanceMargin':'.1'}]}
         instruments=[];pairs={};bodies={};missing=start+3600
         for key,cfg in symbols.items():
          instruments.append(dict(symbol=cfg['perp'],type='flexible_futures',base=cfg['base'],quote='USD',contractSize=1,tradeable=True,marginSchedules={'europa':margins,'europa_crypto':margins},contractValueTradePrecision=4,maxRelativeFundingRate='.005'))
          pairs[cfg['spot']]=dict(quote='ZUSD',status='online',lot_multiplier=1,lot_decimals=8,ordermin='.0001',costmin='.5')
          iso=lambda t:datetime.fromtimestamp(t,timezone.utc).isoformat().replace('+00:00','Z')
          bodies[f'kraken_{key}_funding']={'result':'success','rates':[dict(timestamp=iso(t),fundingRate='.01' if t%7200==0 else '-.005',relativeFundingRate='.0001') for t in range(start,end,3600) if t!=missing]}
          bodies[f'kraken_{key}_spot']={'error':[],'result':{cfg['spot']:[[t,str(100+(t-start)//86400),'110','90','100','100','2',2] for t in range(start,end+86400,86400)]}}
          rows=[dict(time=t*1000,open='101',high='102',low='100',close='101',volume=1) for t in range(start,end+3600,3600)]
          bodies[f'kraken_{key}_mark']={'candles':rows[:24],'more_candles':True}
          bodies[f'kraken_{key}_mark_tail']={'candles':rows[24:],'more_candles':False}
          bodies[f'kraken_{key}_trade']={'candles':[dict(time=t*1000,open='101' if t<end else '104',high='110',low='100',close='103',volume=1) for t in range(start,end+86400,86400)],'more_candles':False}
          bodies[f'kraken_{key}_funding_gap_index_{missing}']={'candles':[dict(time=t*1000,high='105') for t in [missing-3600,missing,missing+3600]],'more_candles':False}
          bodies[f'kraken_{key}_spot_depth']={'error':[],'result':{cfg['spot']:{'bids':[['99.9','5000',start]],'asks':[['100.1','5000',start]]}}}
          bodies[f'kraken_{key}_perp_depth']={'result':'success','orderBook':{'bids':[['100.9','5000']],'asks':[['101.1','5000']]}}
         bodies['kraken_instruments']={'result':'success','instruments':instruments}
         bodies['kraken_spot_pairs']={'error':[],'result':pairs}
         receipts=[]
         for name,body in bodies.items():
          raw=enc(body);fn=name+'.json.gz';(source/fn).write_bytes(gzip.compress(raw,mtime=0))
          receipts.append(dict(name=name,status=200,body=fn,sha256=hashlib.sha256(raw).hexdigest(),received_mono_ns=1000000000 if name.endswith('spot_depth') else 1000000001))
         (source/'acquisition.json').write_bytes(enc({'requests':receipts}));(source/'gap_acquisition.json').write_bytes(enc({'requests':[]}))
         (lane/'cases.json').write_bytes(enc(spec));(lane/'inputs.json').write_bytes(enc({'sha256':{}}));(lane/'PREREG.md').write_text('synthetic test only\n')
         sha=hashlib.sha256((lane/'PREREG.md').read_bytes()).hexdigest();(lane/'PREREG.sha256').write_text(sha+'\n')
         with patch.object(runner,'ROOT',root),patch.object(runner,'SOURCE',source):r=runner.measure(spec)
         r['prereg_sha256']=sha;(lane/'results/report.json').write_bytes(enc(r))
         with patch.object(checker,'ROOT',root),patch.object(checker,'SOURCE',source),patch.object(checker,'LANE',lane):checker.main()
         check=json.loads((lane/'results/check.json').read_text());assert check['verdict']=='PASS'
         r['historical_replays'][0]['counterfactual_net_lower']='123456789';(lane/'results/report.json').write_bytes(enc(r))
         with patch.object(checker,'ROOT',root),patch.object(checker,'SOURCE',source),patch.object(checker,'LANE',lane):
          try:checker.main()
          except ValueError:pass
          else:self.fail('tamper accepted')
