from copy import deepcopy
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_dated_carry_v2 as driver
from tests.test_dated_carry import inputs,EXPIRY


class DatedRatioProtocolTests(unittest.TestCase):
    def plan(self):
        m,sm,s,d,r=inputs();rule=driver.rules(m,'BTC-25DEC26','BTC',EXPIRY,'constructed')
        return driver.entry_plan(s,sm,r,d,rule,r)

    def test_every_frozen_literal_enters_typed_terminal_model_exactly(self):
        plan=self.plan();values=[]
        for literal in ('399/400','1','401/400'):
            r=driver.projected_result(plan,cost_multiple=2,fee_control='public_standard',
                     delivery_rate='0.00025',delivery_price=10000,exit_ratio=literal)
            values.append(r['terminal']['usdt_proceeds'])
        self.assertEqual(values[0]/values[1],F(399,400))
        self.assertEqual(values[2]/values[1],F(401,400))
        r=driver.projected_result(plan,cost_multiple=2,fee_control='public_standard',delivery_rate='0.00025')
        self.assertIsNone(r['terminal']);self.assertIsNone(r['actual_net_usdt'])
        for bad in (True,1.0,'0','-1','NaN'):
            with self.assertRaises(ValueError):
                driver.projected_result(plan,cost_multiple=2,fee_control='public_standard',
                        delivery_rate='0.00025',delivery_price=10000,exit_ratio=bad)

    def test_full_finite_driver_on_constructed_sources_before_market_outcomes(self):
        fixture=json.loads((Path(driver.ROOT)/'experiments/dated_carry_v1/fixtures.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);source=base/'source';lane=base/'lane';out=base/'output'
            evidence=source/'evidence';evidence.mkdir(parents=True);lane.mkdir()
            (source/'data_inputs.json').write_text('{}');(lane/'code_inputs.json').write_text('{}')
            records=[];spotmeta={'symbols':[]}
            def add(name,payload,receipt):
                body=name+'.json.gz';raw=json.dumps(payload).encode()
                (evidence/body).write_bytes(gzip.compress(raw,mtime=0))
                records.append({'name':name,'http_status':200,'complete':True,'body':body,
                     'body_sha256':'constructed-source-identity',**vars(receipt)})
            for coin in ('BTC','ETH'):
                m,sm,s,d,r=inputs()
                m['result'].update(instrument_name=coin+'-25DEC26',base_currency=coin,settlement_currency=coin)
                sm['symbols'][0].update(symbol=coin+'USDT',baseAsset=coin)
                spotmeta['symbols'].append(sm['symbols'][0]);d['result']['instrument_name']=coin+'-25DEC26'
                d['result']['bids']=[['10100',1000]];d['result']['asks']=[['10110',1000]]
                add(coin+'_instrument',m,r);add(coin+'_spot',s,r);add(coin+'_dated',d,r)
            add('spot_rules',spotmeta,r)
            (evidence/'capture.json').write_text(json.dumps({'records':records,'constructed_only':True}))
            with patch.object(driver,'SOURCE_LANE',source),patch.object(driver,'verify',return_value=fixture):
                driver.report(lane=lane,out=out)
            result=json.loads((out/'results.json').read_text())
            self.assertEqual(result['computed_scenarios'],216)
            self.assertEqual(result['constructed_inverse_models'],72)
            self.assertEqual(result['new_market_requests'],0)
            self.assertIsNone(result['market_expected_net'])
            self.assertEqual(len(json.loads(gzip.decompress((out/'journals.json.gz').read_bytes()))),144)
            with patch.object(driver,'SOURCE_LANE',source),patch.object(driver,'verify',return_value=fixture):
                with self.assertRaises(ValueError):driver.report(lane=lane,out=out)


if __name__=='__main__':unittest.main()
