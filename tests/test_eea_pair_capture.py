"""Raw acquisition controls on invented API bytes in temporary directories only."""
import fcntl
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lab.eea_pair_capture import PAIRS, SOURCES, capture, public_get, schema_counts, usage
from scripts import record_eea_pair

START=1794009600*10**9  # 2026-11-07, invented test clock
HOUR=3600*10**9


class CaptureTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out=Path(self.temp.name)/"capture"
        self.config=dict(start_ns=START,end_ns=START+7*24*HOUR,max_requests=1351,
                         response_cap=4096,metadata_response_cap=8192,
                         max_body_bytes=16*1024**2,max_stored_bytes=8*1024**2,
                         reobservation_delay_seconds=3)
        self.now=START+60*10**9
        self.calls=[]
        self.sleeps=[]
        self.objects={"kraken_metadata":dict(result="success",instruments=[
            dict(symbol=k,base=b,quote="USD",contractSize=1,marginSchedules={"europa":{"retail":[{"initialMargin":.1}]}})
            for _,_,k,b,_ in PAIRS])}
        for key,c,k,b,size in PAIRS:
            self.objects[key+"_cde_product"]=dict(product_id=c,product_type="FUTURE",quote_currency_id="USD",base_increment="1",
                future_product_details=dict(venue="cde",contract_root_unit=b,contract_size=size,funding_rate="0",funding_time="unknown",contract_expiry="2089-12-30T16:00:00Z"))
            self.objects[key+"_cde_book"]=dict(pricebook=dict(product_id=c,bids=[dict(price="99",size="1")],asks=[dict(price="101",size="2")]))
            self.objects[key+"_kraken_ticker"]=dict(result="success",ticker=dict(symbol=k,fundingRate="0",relativeFundingRate="0"))
            self.objects[key+"_kraken_book"]=dict(result="success",orderBook=dict(bids=[[99,1]],asks=[[101,1]]))

    def fetch(self,url,limit):
        self.calls.append(url)
        name=next(n for n,u in SOURCES.items() if u==url)
        return 200,json.dumps(self.objects[name]).encode(),"application/json"

    def run_capture(self,fetch=None,sleeper=None):
        return capture(self.out,self.config,fetch=fetch or self.fetch,wall_ns=lambda:self.now,mono_ns=lambda:1234,
                       sleeper=sleeper or self.sleeps.append,
                       provenance=dict(prereg_sha256="synthetic"))

    def test_raw_bodies_receipts_and_zero_rates_are_preserved(self):
        r=self.run_capture()
        self.assertEqual((r["state"],r["requests"]),("CAPTURED",13))
        self.assertIsNone(r["funding_cash"])
        self.assertIsNone(r["pnl"])
        self.assertEqual(r["provenance"]["prereg_sha256"],"synthetic")
        self.assertTrue(r["counts"]["btc_cde_product"]["funding_rate_present"])
        self.assertFalse(r["counts"]["btc_cde_product"]["funding_is_verified_settled_cash"])
        events=[json.loads(x) for x in (self.out/"requests.jsonl").read_text().splitlines()]
        self.assertEqual(len(events),26)
        for end in events[1::2]:
            raw=gzip.decompress((self.out/"packets"/end["body"]).read_bytes())
            self.assertEqual(hashlib.sha256(raw).hexdigest(),end["body_sha256"])
        self.assertEqual(usage(self.out/"requests.jsonl")[0],13)

    def test_reobservations_wait_once_and_preserve_changed_book(self):
        def after_first_group(seconds):
            self.assertEqual(len(self.calls),9)
            self.sleeps.append(seconds)
            self.objects["btc_cde_book"]["pricebook"]["bids"]=[]
        r=self.run_capture(sleeper=after_first_group)
        self.assertEqual(self.sleeps,[3])
        self.assertEqual(r["counts"]["btc_cde_book"]["bid_rows"],1)
        self.assertEqual(r["counts"]["btc_cde_book_delayed"]["bid_rows"],0)
        from collections import Counter
        counts=Counter(self.calls)
        self.assertEqual([n for n in counts.values() if n==2],[2]*4)
        self.assertEqual(counts[SOURCES["btc_cde_product"]],1)

    def test_window_can_end_during_reobservation_delay(self):
        def end_window(seconds):
            self.now=self.config["end_ns"]
        r=capture(self.out,self.config,fetch=self.fetch,wall_ns=lambda:self.now,
                  mono_ns=lambda:1234,sleeper=end_window)
        self.assertEqual((r["state"],r["requests"]),("WINDOW_ENDED",9))
        self.assertNotIn("btc_cde_book_delayed",r["counts"])

    def test_same_hour_never_calls_twice(self):
        self.run_capture();self.calls=[]
        self.assertEqual(self.run_capture()["state"],"HOUR_ALREADY_RESERVED")
        self.assertEqual(self.calls,[])

    def test_hour_boundary_keeps_integer_nanosecond_precision(self):
        self.now=START+HOUR-1
        self.assertEqual(self.run_capture()["hour"],"20261107T00")
        self.now+=1
        r=self.run_capture()
        self.assertEqual((r["hour"],r["requests"]),("20261107T01",12))

    def test_daily_metadata_reused_only_after_success(self):
        self.run_capture();self.calls=[];self.now+=HOUR
        r=self.run_capture()
        self.assertEqual(r["requests"],12)
        self.assertNotIn(SOURCES["kraken_metadata"],self.calls)
        self.assertEqual(r["kraken_metadata_packet"],"20261107T00")

    def test_transient_metadata_failure_does_not_count_as_success(self):
        self.run_capture(lambda u,l:(503,b'{}',"application/json"))
        self.assertFalse((self.out/"STOPPED.json").exists())
        self.now+=HOUR
        self.assertEqual(self.run_capture()["requests"],13)
        self.assertEqual(self.calls[0],SOURCES["kraken_metadata"])

    def test_block_status_stops_without_retries_or_new_hour_calls(self):
        seen=[]
        def denied(url,limit):
            seen.append(url);return 451,b'{}',"application/json"
        self.assertEqual(self.run_capture(denied)["state"],"FAILED")
        self.assertEqual(len(seen),1)
        self.now+=HOUR
        self.assertEqual(self.run_capture(denied)["state"],"STOPPED")
        self.assertEqual(len(seen),1)

    def test_request_budget_is_accumulated_between_hours(self):
        self.config["max_requests"]=14
        self.run_capture();self.now+=HOUR
        self.assertEqual(self.run_capture()["state"],"BUDGET_STOP")
        self.assertEqual(usage(self.out/"requests.jsonl")[0],14)
        self.assertEqual(len(self.calls),14)

    def test_unfinished_request_keeps_full_body_reservation(self):
        self.out.mkdir();p=self.out/"requests.jsonl"
        p.write_text(json.dumps(dict(event="START",request_id="old",reserved_body_bytes=12345))+"\n")
        self.assertEqual(usage(p),(1,12345))
        self.config["max_body_bytes"]=12345+8192
        self.assertEqual(self.run_capture()["state"],"BUDGET_STOP")
        self.assertEqual(self.calls,[])

    def test_outside_window_never_creates_or_calls(self):
        self.now=START-1
        self.assertEqual(self.run_capture()["state"],"OUTSIDE_FROZEN_WINDOW")
        self.assertFalse(self.out.exists())
        self.now=self.config["end_ns"]
        self.assertEqual(self.run_capture()["requests"],0)

    def test_existing_writer_is_respected(self):
        self.out.mkdir()
        with (self.out/"writer.lock").open("a+b") as handle:
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.assertEqual(self.run_capture()["state"],"WRITER_BUSY")
        self.assertEqual(self.calls,[])

    def test_body_overflow_is_retained_and_stops(self):
        r=self.run_capture(lambda u,l:(200,b'x'*(l+1),"application/json"))
        self.assertEqual(r["state"],"FAILED")
        self.assertTrue((self.out/"STOPPED.json").exists())
        self.assertEqual(usage(self.out/"requests.jsonl"),(1,8193))

    def test_html_response_stops(self):
        self.run_capture(lambda u,l:(200,b'<html>challenge</html>',"text/html"))
        self.assertTrue((self.out/"STOPPED.json").exists())

    def test_identity_change_and_missing_funding_stay_distinct(self):
        self.objects["btc_cde_product"]["future_product_details"]["funding_rate"]=""
        r=self.run_capture()
        self.assertFalse(r["counts"]["btc_cde_product"]["funding_rate_present"])
        self.now+=HOUR
        self.objects["btc_cde_product"]["future_product_details"]["contract_size"]="1"
        self.assertEqual(self.run_capture()["state"],"FAILED")
        self.assertTrue((self.out/"STOPPED.json").exists())

    def test_empty_book_is_recorded_as_empty(self):
        self.objects["btc_cde_book"]["pricebook"].update(bids=[],asks=[])
        r=self.run_capture()
        self.assertEqual(r["counts"]["btc_cde_book"],dict(bid_rows=0,ask_rows=0))
        self.assertIsNone(r["pnl"])

    def test_corrupt_journal_is_never_repaired(self):
        self.out.mkdir();p=self.out/"requests.jsonl";p.write_text('{"cut":')
        with self.assertRaises(ValueError):self.run_capture()
        self.assertEqual(p.read_text(),'{"cut":')
        self.assertEqual(self.calls,[])

    def test_private_or_unrelated_url_rejected_before_network(self):
        with patch('lab.eea_pair_capture.build_opener',side_effect=AssertionError('network')):
            for url in ['https://api.coinbase.com/api/v3/brokerage/accounts','https://api.exchange.fairx.net/rest/funding-rate?symbol=BIPZ30','https://eea.okx.com/api/v5/public/instruments']:
                with self.assertRaises(ValueError):public_get(url,100)

    def test_default_cli_is_inactive(self):
        with patch.object(record_eea_pair,'capture',side_effect=AssertionError('capture')):
            self.assertEqual(record_eea_pair.main([]),0)

    def test_nonobject_response_fails_closed(self):
        with self.assertRaises(ValueError):schema_counts('kraken_metadata',[])


if __name__=="__main__":
    unittest.main()
