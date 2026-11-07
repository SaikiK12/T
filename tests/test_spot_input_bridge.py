from decimal import Decimal as D
import json
import unittest
from lab.spot_input_bridge import spot_rules,mexc_book
from lab.spot_quote_costs import illustrative_quantity
from tests.test_spot_quote_costs import info,metadata,books


class SpotInputBridgeTests(unittest.TestCase):
    def test_explicit_zero_minimum_is_not_zero_trade_or_inferred_step(self):
        source=info(baseSizePrecision='0');r=spot_rules('BTCUSDT',source)
        self.assertEqual(r.minimum_base,0);self.assertIsNone(r.lot_step_base)
        self.assertEqual(source['symbols'][0]['baseSizePrecision'],'0')
        q,step=illustrative_quantity(r,metadata(),100)
        self.assertGreater(q,0);self.assertEqual(step,D('.001'))
        self.assertIsNone(spot_rules('BTCUSDT',info(baseSizePrecision=None)).minimum_base)
        for bad in ('-1',False):
            with self.assertRaises(ValueError):spot_rules('BTCUSDT',info(baseSizePrecision=bad))

    def test_decimal_wire_prices_keep_contract_quantity_and_reject_boolean(self):
        s,_=books();source=json.loads('{"success":true,"data":{"bids":[[101.25,10,1]],"asks":[[102.75,20,1]],"version":1}}',parse_float=D)
        result=mexc_book('BTC_USDT',source,metadata(marketOrderMaxLevel=5),s.receipt)
        self.assertEqual(result.bids[0].price,101.25);self.assertEqual(result.bids[0].size,.01)
        self.assertIsInstance(source['data']['bids'][0][0],D)
        source['data']['bids'][0][0]=False
        with self.assertRaises(ValueError):mexc_book('BTC_USDT',source,metadata(marketOrderMaxLevel=5),s.receipt)


if __name__=='__main__':unittest.main()
