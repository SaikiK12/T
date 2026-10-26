import asyncio
import gzip
import json
from pathlib import Path
import tempfile
import unittest

from lab.acquisition_budget import BudgetJournal,BudgetLimits
from lab.stream_quotes import FrameClock,NS
from scripts.probe_spot_perp import stream,subscriptions,ATTEMPT_SECONDS,CONNECTION_BYTES
import time


class SpotCaptureTests(unittest.TestCase):
    def test_fixed_public_subscriptions_have_no_accounts_or_orders(self):
        self.assertEqual(len(subscriptions('spot')[0]['params']),3)
        self.assertEqual(len(subscriptions('perp')),3)
        with self.assertRaises(ValueError):subscriptions('private')

    def test_denial_is_one_attempt_and_durable_no_retry(self):
        class Denied(Exception):
            response=type('Response',(),{'status_code':403,'body':b'public route denied'})()
        calls=[]
        class C:
            async def __aenter__(self):raise Denied()
            async def __aexit__(self,*args):pass
        def connector(*args,**kwargs):calls.append((args,kwargs));return C()
        async def probe(out,budget):
            stop=asyncio.Event();anchor=FrameClock(time.time_ns(),time.monotonic_ns())
            r=await stream('spot',out,anchor,budget,stop,connector=connector)
            self.assertTrue(stop.is_set());self.assertEqual(r['http_status'],403)
            with self.assertRaises(ValueError):await stream('spot',out,anchor,budget,stop,connector=connector)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);b=BudgetJournal(out/'budget.jsonl','fake-test',BudgetLimits(2,2*CONNECTION_BYTES,2*ATTEMPT_SECONDS*NS,ATTEMPT_SECONDS*NS))
            asyncio.run(probe(out,b));self.assertEqual(len(calls),1)
            self.assertEqual(b.status()['requests_charged'],1)
            self.assertEqual((out/'spot-handshake-body.bin').read_bytes(),b'public route denied')
            self.assertEqual(calls[0][1]['max_size'],128*1024)

    def test_binary_receipt_preserved_before_decoding(self):
        class C:
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
            async def send(self,payload):self.sent=json.loads(payload)
            async def recv(self):
                if getattr(self,'done',False):raise ConnectionError('end of fake receipt')
                self.done=True;return b'\x0a\x01x'
        async def probe(out,b):
            return await stream('spot',out,FrameClock(time.time_ns(),time.monotonic_ns()),b,asyncio.Event(),connector=lambda *a,**kw:C())
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);b=BudgetJournal(out/'budget.jsonl','fake-test',BudgetLimits(2,2*CONNECTION_BYTES,2*ATTEMPT_SECONDS*NS,ATTEMPT_SECONDS*NS))
            r=asyncio.run(probe(out,b));self.assertEqual(r['messages'],1)
            f=json.loads(gzip.decompress((out/'spot.jsonl.gz').read_bytes()))
            self.assertTrue(f['binary']);self.assertEqual(f['payload'],'CgF4')
            self.assertGreater(f['clock']['mono_ns'],0);self.assertNotIn('normalized_source_time',f)


if __name__=='__main__':unittest.main()
