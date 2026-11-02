"""Synthetic event-recorder contracts: no market outcomes or public requests."""
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import record_listings as listings
from scripts import record_tradfi_calendar as calendar

ej = calendar.ej


class Clock:
    def __init__(self, now=1000.0):
        self.now = now
        self.elapsed = 0.0

    def advance(self, seconds):
        self.now += seconds
        self.elapsed += seconds


def item(value="live", **fields):
    return {"fields": {"status": value, **fields}, "etime": ("source_time", "raw", "")}


def earnings(date, symbols):
    as_of = datetime.fromisoformat(date).strftime("%a, %b %d, %Y")
    return json.dumps({"data": {"asOf": as_of, "rows": [{"symbol": s, "time": "after-market"} for s in symbols]}}).encode()


class EventRecorderContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="event_contract_")
        self.folder = Path(self.temp.name)/"events"
        self.journal = ej.Journal(self.folder)
        self.clock = Clock()
        self.wall = patch.object(ej.time,"time",side_effect=lambda: self.clock.now)
        self.mono = patch.object(ej.time,"monotonic",side_effect=lambda: self.clock.elapsed)
        self.net = patch.object(ej,"http_get",side_effect=AssertionError("synthetic tests forbid public requests"))
        self.wall.start(); self.mono.start(); self.net.start()
        self.addCleanup(self.wall.stop); self.addCleanup(self.mono.stop); self.addCleanup(self.net.stop)
        self.addCleanup(self.temp.cleanup)

    def events(self):
        with self.journal.events.open(newline="") as f:
            return list(csv.DictReader(f))

    def polls(self):
        with self.journal.polls_path(1000).open(newline="") as f:
            return list(csv.DictReader(f))

    def source(self, fetch):
        return ej.Source("fixture",3600,fetch,key_field="symbol",src_map={"status":"state"})

    def test_slow_fetch_event_time_is_not_backdated_to_pass_start(self):
        def fetch(_):
            self.clock.advance(45)
            return {"X":item()},None
        scheduled=900
        result=ej.poll_one(self.journal,self.source(fetch),scheduled)
        self.assertEqual(result["status"],"ok")
        self.assertEqual(int(self.events()[0]["poll_ms"]),1045000)
        self.assertEqual(int(self.polls()[0]["poll_ms"]),1045000)
        self.assertEqual(int(self.polls()[0]["bucket"]),scheduled//3600)
        self.assertEqual(int(self.polls()[0]["elapsed_ms"]),45000)

    def test_late_failure_retries_wait_from_failure_completion(self):
        def fail(_):
            self.clock.advance(90)
            raise OSError("invented response failure")
        src=self.source(fail)
        self.assertEqual(ej.poll_one(self.journal,src,1000)["status"],"error")
        self.clock.advance(1)
        self.assertEqual(ej.poll_one(self.journal,src,self.clock.now)["status"],"skip")
        self.assertEqual(len(self.polls()),1)
        self.assertEqual(int(self.polls()[0]["poll_ms"]),1090000)

    def test_backwards_wall_clock_records_error_without_creating_events(self):
        def fetch(_):
            self.clock.now-=1
            self.clock.elapsed+=1
            return {"X":item()},None
        result=ej.poll_one(self.journal,self.source(fetch),1000)
        self.assertEqual(result["status"],"error")
        self.assertIn("clock moved backwards",result["error"])
        self.assertFalse(self.journal.events.exists())
        self.assertEqual(int(self.polls()[0]["elapsed_ms"]),1000)

    def test_completed_bucket_is_idempotent_without_another_fetch(self):
        calls=[]
        src=self.source(lambda now:(calls.append(now) or {"X":item()},None))
        ej.poll_one(self.journal,src,1000)
        before=self.journal.events.read_bytes()
        self.assertEqual(ej.poll_one(self.journal,src,1001)["status"],"skip")
        self.assertEqual(calls,[1000])
        self.assertEqual(self.journal.events.read_bytes(),before)

    def test_baseline_change_gone_and_back_replay_correctly(self):
        observations=[{"X":item()}, {"X":item("halted"),"Y":item()}, {"Y":item()}, {"X":item("live"),"Y":item()}]
        src=self.source(lambda _:(observations.pop(0),None))
        for n in range(4):
            self.clock.now=1000+n*3600
            ej.poll_one(self.journal,src,self.clock.now,force=True)
        rows=self.events()
        self.assertEqual([r["event"] for r in rows],["baseline","change","new","gone","back"])
        self.assertEqual(rows[1]["src_field"],"state")
        self.assertTrue(self.journal.state()["fixture"]["X"]["present"])
        self.assertEqual(self.journal.state()["fixture"]["X"]["fields"]["status"],"live")

    def test_large_shrink_is_not_a_mass_delisting(self):
        initial={str(n):item() for n in range(10)}
        src=self.source(lambda _:(initial,None))
        ej.poll_one(self.journal,src,1000)
        before=self.journal.events.read_bytes()
        src.fetch=lambda _:({"0":item()},None)
        self.assertEqual(ej.poll_one(self.journal,src,1001,force=True)["status"],"error")
        self.assertEqual(self.journal.events.read_bytes(),before)

    def test_source_failures_do_not_turn_existing_items_gone(self):
        src=self.source(lambda _:({"X":item()},None))
        ej.poll_one(self.journal,src,1000)
        before=self.journal.events.read_bytes()
        def fail(_):
            raise ValueError("bad payload")
        src.fetch=fail
        ej.poll_one(self.journal,src,1001,force=True)
        self.assertEqual(self.journal.events.read_bytes(),before)

    def test_cold_start_checks_nearest_existing_ancestor(self):
        folder=Path(self.temp.name)/"missing"/"parents"/"recorder"
        self.assertEqual(ej.disk_problem(folder,ej.Journal(folder)),"")
        self.assertFalse(folder.exists())

    def test_ensure_can_bootstrap_nested_folder_without_spawning_real_process(self):
        folder=Path(self.temp.name)/"missing"/"parents"/"recorder"
        with patch.object(ej.subprocess,"Popen") as spawn:
            self.assertEqual(ej.cli("fixture",folder,[],__file__,["ensure"]),0)
            spawn.assert_called_once()
            spawn.call_args.kwargs["stdout"].close()
        self.assertTrue(folder.exists())

    def test_other_writer_lock_remains_held(self):
        held=ej.lock(self.folder)
        try:
            self.assertIsNone(ej.lock(self.folder))
        finally:
            held.close()

    def seed_earnings(self):
        src=calendar.SOURCES[1]
        dates=["2026-11-03","2026-11-04"]
        old=calendar.parse_earnings(earnings(dates[0],["OLD"]),dates[0])
        old.update(calendar.parse_earnings(earnings(dates[1],[f"OK{i}" for i in range(10)]),dates[1]))
        self.journal.append_events(self.journal.diff(src,old,None,{},1000))
        return src,dates

    def test_wrong_asof_partition_cannot_create_false_gone_events(self):
        src,dates=self.seed_earnings()
        before=self.journal.events.read_bytes()
        def response(url, **_):
            if dates[0] in url:
                return earnings("2026-11-02",[])
            return earnings(dates[1],[f"OK{i}" for i in range(10)])
        with patch.object(calendar,"earn_dates",return_value=dates),patch.object(ej,"http_get",side_effect=response),patch.object(calendar.time,"sleep"):
            result=ej.poll_one(self.journal,src,2000,force=True)
        self.assertEqual(result["status"],"error")
        self.assertIn("asOf",result["error"])
        self.assertEqual(self.journal.events.read_bytes(),before)
        self.assertTrue(self.journal.state()[src.name][dates[0]+"|OLD"]["present"])

    def test_valid_empty_partition_can_remove_a_previously_reported_event(self):
        src,dates=self.seed_earnings()
        def response(url, **_):
            return earnings(dates[0],[]) if dates[0] in url else earnings(dates[1],[f"OK{i}" for i in range(10)])
        with patch.object(calendar,"earn_dates",return_value=dates),patch.object(ej,"http_get",side_effect=response),patch.object(calendar.time,"sleep"):
            result=ej.poll_one(self.journal,src,2000,force=True)
        self.assertEqual(result["status"],"ok")
        self.assertEqual(result["gone"],1)
        self.assertEqual(self.events()[-1]["key"],dates[0]+"|OLD")

    def test_malformed_earnings_partitions_fail_explicitly(self):
        for value in ([],None,{}, {"data":None},{"data":{"asOf":None}},
                      {"data":{"asOf":"Wed, Nov 04, 2026"}},
                      {"data":{"asOf":"Wed, Nov 04, 2026","rows":"bad"}},
                      {"status":{"rCode":400},"data":{"asOf":"Wed, Nov 04, 2026","rows":[]}}):
            with self.subTest(value=value),self.assertRaises(ValueError):
                calendar.parse_earnings(json.dumps(value).encode(),"2026-11-04")

    def test_listing_raw_identity_and_epoch_units_are_preserved(self):
        raw=json.dumps({"success":True,"data":[{"symbol":"ABC_USDT","state":0,"createTime":1700000000123,"priceUnit":"0.0000100"}]}).encode()
        record=listings.parse_mexc(raw)["ABC_USDT"]
        self.assertEqual(record["fields"]["tick"],"0.0000100")
        self.assertEqual(record["etime"][1],"1700000000123")
        self.assertEqual(record["etime"][2],"2023-11-14T22:13:20Z")
        gate=listings.parse_gate(b'[{"name":"ABC_USDT","launch_time":1700000000}]')["ABC_USDT"]
        self.assertEqual(gate["etime"][2],record["etime"][2])

    def test_eastern_calendar_clock_tracks_dst_at_regular_market_times(self):
        winter=calendar.et_to_utc("2026-11-03","13:00",("%Y-%m-%d %H:%M",))
        summer=calendar.et_to_utc("2026-07-01","13:00",("%Y-%m-%d %H:%M",))
        self.assertEqual(winter,"2026-11-03T18:00:00Z")
        self.assertEqual(summer,"2026-07-01T17:00:00Z")


if __name__=="__main__":
    unittest.main()
