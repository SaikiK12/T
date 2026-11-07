"""scripts/record_listings.py and the shared scripts/event_journal.py engine: parsers, the journal diff (baseline / new /
change / gone / back), per-interval idempotency, the shrink and disk guards, ensure/run wiring. Offline: no network."""
import calendar
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import event_journal as ej  # noqa: E402
import record_listings as rl  # noqa: E402

T0 = calendar.timegm((2026, 11, 2, 12, 0, 0))


def mexc(rows):
    return json.dumps({"success": True, "code": 0, "data": [
        {"symbol": s, "state": st, "type": 1, "priceUnit": 0.1, "volUnit": 1, "contractSize": 0.0001, "minLeverage": 1,
         "maxLeverage": lev, "takerFeeRate": 0.0002, "makerFeeRate": 0, "openingTime": 0, "isHidden": False,
         "preMarket": False, "apiAllowed": True, "appraisal": 0, "createTime": ct, "openInterest": 123.0}
        for s, st, lev, ct in rows]}).encode()


def gate(rows):
    return json.dumps([{"name": n, "status": st, "in_delisting": dl, "type": "direct", "order_price_round": "0.01",
                        "order_size_min": 1, "leverage_min": "1", "leverage_max": "50", "funding_interval": fi,
                        "taker_fee_rate": "0.00075", "maker_fee_rate": "-0.0001", "is_pre_market": False,
                        "quanto_multiplier": "1", "enable_circuit_breaker": False, "config_change_time": 1,
                        "create_time": 1758124000, "launch_time": lt, "mark_price": "5"}
                       for n, st, dl, fi, lt in rows]).encode()


class ParserTests(unittest.TestCase):
    def test_mexc_fields_and_listing_time(self):
        (k, it), = rl.parse_mexc(mexc([("BTC_USDT", 0, 500, 1591242684000)])).items()
        self.assertEqual(k, "BTC_USDT")
        self.assertEqual(it["etime"], ("createTime", "1591242684000", "2020-06-04T03:51:24Z"))
        self.assertEqual((it["fields"]["status"], it["fields"]["max_lev"], it["fields"]["hidden"]), ("0", "500", "false"))
        for volatile in ("openInterest", "taker_fee", "maker_fee"):  # never compared (MEXC fee fields flap per request)
            self.assertNotIn(volatile, it["fields"])

    def test_mexc_error_reply_is_refused(self):
        with self.assertRaises(ValueError):
            rl.parse_mexc(b'{"success": false, "code": 510}')

    def test_gate_seconds_and_launch_field(self):
        it = rl.parse_gate(gate([("AAA_USDT", "trading", False, 28800, 1758124392)]))["AAA_USDT"]
        self.assertEqual(it["etime"], ("launch_time", "1758124392", "2025-09-17T15:53:12Z"))
        self.assertEqual((it["fields"]["funding_interval"], it["fields"]["in_delisting"]), ("28800", "false"))
        it = rl.parse_gate(gate([("AAA_USDT", "trading", False, 28800, 0)]))["AAA_USDT"]
        self.assertEqual(it["etime"][0], "create_time")

    def test_hyperliquid_main_and_hip3(self):
        raw = json.dumps([{"universe": [{"name": "BTC", "szDecimals": 5, "maxLeverage": 40, "marginTableId": 56},
                                        {"name": "OLD", "szDecimals": 1, "maxLeverage": 3, "isDelisted": True}]},
                          {"universe": [{"name": "xyz:TSLA", "szDecimals": 3, "maxLeverage": 10, "growthMode": "enabled"}]}]).encode()
        out = rl.parse_hyperliquid(raw)
        self.assertEqual(set(out), {"BTC", "OLD", "xyz:TSLA"})
        self.assertEqual((out["BTC"]["fields"]["dex"], out["xyz:TSLA"]["fields"]["dex"]), ("main", "xyz"))
        self.assertEqual(out["OLD"]["fields"]["is_delisted"], "true")
        self.assertEqual(out["BTC"]["etime"], ("", "", ""))           # Hyperliquid publishes no listing time

    def test_other_venues(self):
        k = json.dumps({"code": "200000", "data": [{"symbol": "XBTUSDTM", "status": "Open", "type": "FFWCSX",
                                                     "firstOpenDate": 1585555200000, "tickSize": 0.1, "lotSize": 1,
                                                     "maxLeverage": 125, "fundingRateGranularity": 28800000}]}).encode()
        self.assertEqual(rl.parse_kucoin(k)["XBTUSDTM"]["fields"]["funding_interval"], "28800000")
        d = json.dumps({"markets": {"BTC-USD": {"ticker": "BTC-USD", "status": "ACTIVE", "tickSize": "1",
                                                "stepSize": "0.0001", "initialMarginFraction": "0.02"}}}).encode()
        self.assertEqual(rl.parse_dydx(d)["BTC-USD"]["fields"]["status"], "ACTIVE")
        o = json.dumps({"code": "0", "data": [{"instId": "BTC-USD-SWAP", "state": "live", "listTime": "1535424203000",
                                                "tickSz": "0.1", "lever": "100", "upcChg": []}]}).encode()
        it = rl.parse_okx(o)["BTC-USD-SWAP"]
        self.assertEqual((it["fields"]["status"], it["fields"]["upcoming"], it["etime"][2]),
                         ("live", "[]", "2018-08-28T02:43:23Z"))
        b = json.dumps({"code": "00000", "data": [{"symbol": "BTCUSDT", "symbolStatus": "normal", "launchTime": "",
                                                    "openTime": "1700000000000", "maxLever": "150"}]}).encode()
        self.assertEqual(rl.parse_bitget(b)["BTCUSDT"]["etime"], ("openTime", "1700000000000", "2023-11-14T22:13:20Z"))
        l = json.dumps({"code": 200, "order_book_details": [
            {"symbol": "ETH", "market_id": 0, "market_type": "perp", "status": "active", "created_at": "1763659438438",
             "market_config": {"hidden": False, "trading_hours": ""}}]}).encode()
        it = rl.parse_lighter(l)["ETH"]
        self.assertEqual((it["fields"]["hidden"], it["fields"]["market_id"], it["etime"][2]),
                         ("false", "0", "2025-11-20T17:23:58Z"))


class Rec(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name) / "listings"
        self.j = ej.Journal(self.dir)
        self.reply = {}
        self.calls = []

        def fake_get(url, body=None, timeout=30, headers=None):
            self.calls.append(url)
            for v, u in rl.URL.items():
                if u == url:
                    if isinstance(self.reply[v], Exception):
                        raise self.reply[v]
                    return self.reply[v]
            raise AssertionError(url)

        p = mock.patch.object(ej, "http_get", fake_get)
        p.start()
        self.addCleanup(p.stop)
        self.sources = [s for s in rl.SOURCES if s.name in ("mexc", "gate")]

    def events(self):
        with open(self.dir / "events.csv", newline="") as f:
            return list(csv.DictReader(f))

    def polls(self):
        (p,) = self.dir.glob("polls_*.csv")
        with open(p, newline="") as f:
            return list(csv.DictReader(f))

    def run_pass(self, t, **kw):
        # Zero-latency fixture: observation and completion occur at t as well.
        with mock.patch.object(ej.time, "time", return_value=t):
            return ej.poll_all(self.j, self.sources, now_s=t, pace=0, **kw)


class JournalTests(Rec):
    def test_baseline_then_nothing_twice(self):
        self.reply = {"mexc": mexc([("BTC_USDT", 0, 500, 1591242684000), ("ETH_USDT", 0, 200, 1591242684000)]),
                      "gate": gate([("BTC_USDT", "trading", False, 28800, 1700000000)])}
        out = self.run_pass(T0)
        self.assertEqual([(s["source"], s["status"], s["baseline"]) for s in out], [("mexc", "ok", 2), ("gate", "ok", 1)])
        n = len(self.events())
        self.assertEqual(n, 3)
        again = self.run_pass(T0 + 30)                                  # same 300 s / 900 s bucket: no request at all
        self.assertEqual([s["status"] for s in again], ["skip", "skip"])
        self.assertEqual(len(self.calls), 2)
        forced = self.run_pass(T0 + 60, force=True)                     # re-polled, nothing differs: nothing written
        self.assertEqual([s["status"] for s in forced], ["ok", "ok"])
        self.assertEqual(len(self.events()), n)
        for r in self.events():
            self.assertEqual(r["event"], "baseline")
            self.assertEqual(r["poll_utc"], "2026-11-02T12:00:00Z")
            self.assertEqual(r["src_field"], "symbol" if r["source"] == "mexc" else "name")
            self.assertIn("status", json.loads(r["snapshot"]))
            self.assertEqual(r["poll_ms"], str(T0 * 1000))

    def test_new_change_gone_back(self):
        self.reply = {"mexc": mexc([("BTC_USDT", 0, 500, 1), ("OLD_USDT", 0, 50, 1)]),
                      "gate": gate([("BTC_USDT", "trading", False, 28800, 1700000000)])}
        self.run_pass(T0)
        # next bucket: NEW listed (exchange says 12:03), BTC leverage cut, OLD dropped from the list
        t1 = T0 + 900                                                # a new bucket for both sources
        self.reply["mexc"] = mexc([("BTC_USDT", 0, 100, 1), ("NEW_USDT", 0, 25, (T0 + 180) * 1000)])
        self.reply["gate"] = gate([("BTC_USDT", "trading", True, 3600, 1700000000)])
        self.run_pass(t1)
        ev = [r for r in self.events() if r["poll_utc"] != "2026-11-02T12:00:00Z"]
        got = {(r["source"], r["key"], r["event"], r["field"], r["old"], r["new"]) for r in ev}
        self.assertEqual(got, {("mexc", "NEW_USDT", "new", "", "", ""), ("mexc", "OLD_USDT", "gone", "", "", ""),
                               ("mexc", "BTC_USDT", "change", "max_lev", "500", "100"),
                               ("gate", "BTC_USDT", "change", "in_delisting", "false", "true"),
                               ("gate", "BTC_USDT", "change", "funding_interval", "28800", "3600")})
        new = next(r for r in ev if r["event"] == "new")
        self.assertEqual((new["event_time_field"], new["event_time_utc"]), ("createTime", "2026-11-02T12:03:00Z"))
        self.assertEqual(new["poll_utc"], "2026-11-02T12:15:00Z")
        chg = next(r for r in ev if r["field"] == "max_lev")
        self.assertEqual(chg["src_field"], "maxLeverage")
        gone = next(r for r in ev if r["event"] == "gone")
        self.assertEqual(json.loads(gone["snapshot"])["max_lev"], "50")      # last known raw values
        # OLD returns later
        self.reply["mexc"] = mexc([("BTC_USDT", 0, 100, 1), ("NEW_USDT", 0, 25, 1), ("OLD_USDT", 0, 50, 1)])
        self.run_pass(t1 + 300)
        self.assertEqual([r["event"] for r in self.events() if r["key"] == "OLD_USDT"], ["baseline", "gone", "back"])
        n = len(self.events())
        self.run_pass(t1 + 600)                                              # unchanged list: no rows
        self.assertEqual(len(self.events()), n)
        st = self.j.state()["mexc"]
        self.assertTrue(all(v["present"] for v in st.values()))
        self.assertEqual(st["BTC_USDT"]["fields"]["max_lev"], "100")

    def test_state_is_rebuilt_from_the_journal_alone(self):
        self.reply = {"mexc": mexc([("A_USDT", 0, 10, 1)]), "gate": gate([("A_USDT", "trading", False, 28800, 1)])}
        self.run_pass(T0)
        for p in self.dir.glob("polls_*.csv"):                       # losing the poll log must not duplicate events
            p.unlink()
        self.run_pass(T0 + 10)
        self.assertEqual(len(self.events()), 2)

    def test_retired_and_added_fields(self):
        def src(names, extra=""):
            items = {"K": {"fields": {n: "1" for n in names}, "etime": ("", "", "")}}
            return ej.Source("s", 300, lambda now: (items, None), "id", {n: n for n in names})
        for i, s in enumerate((src("ab"), src("a"), src("ac"))):      # spec drops b, then adds c
            ej.poll_all(self.j, [s], now_s=T0 + 300 * i, pace=0)
        got = [(r["event"], r["field"], r["old"], r["new"]) for r in self.events()]
        self.assertEqual(got, [("baseline", "", "", ""), ("change", "c", "", "1")])    # no change row for retired b

    def test_shrunk_list_writes_no_gone_rows(self):
        rows = [(f"C{i}_USDT", 0, 10, 1) for i in range(10)]
        self.reply = {"mexc": mexc(rows), "gate": gate([("A_USDT", "trading", False, 28800, 1)])}
        self.run_pass(T0)
        self.reply["mexc"] = mexc(rows[:3])                           # a truncated reply, not 7 delistings
        out = self.run_pass(T0 + 300)
        self.assertEqual(out[0]["status"], "error")
        self.assertIn("shrank", out[0]["error"])
        self.assertFalse([r for r in self.events() if r["event"] == "gone"])
        self.assertEqual([p["ok"] for p in self.polls() if p["source"] == "mexc"], ["1", "0"])

    def test_error_is_logged_and_retried_with_a_cap(self):
        self.reply = {"mexc": OSError("boom"), "gate": gate([("A_USDT", "trading", False, 28800, 1)])}
        out = self.run_pass(T0)
        self.assertEqual((out[0]["status"], out[1]["status"]), ("error", "ok"))
        self.assertEqual(self.run_pass(T0 + 10)[0]["status"], "skip")     # inside the retry wait
        self.assertEqual(self.run_pass(T0 + 70)[0]["status"], "error")    # second try
        self.assertEqual(self.run_pass(T0 + 140)[0]["status"], "error")   # third try
        self.assertEqual(self.run_pass(T0 + 200)[0]["status"], "skip")    # MAX_TRIES reached for this bucket
        self.reply["mexc"] = mexc([("A_USDT", 0, 10, 1)])
        self.assertEqual(self.run_pass(T0 + 300)[0]["status"], "ok")      # next bucket works
        self.assertTrue(all(r["error"] for r in self.polls() if r["ok"] == "0"))

    def test_only_and_disk_guard(self):
        self.reply = {"mexc": mexc([("A_USDT", 0, 10, 1)]), "gate": gate([("A_USDT", "trading", False, 28800, 1)])}
        out = self.run_pass(T0, only={"gate"})
        self.assertEqual([s["source"] for s in out], ["gate"])
        with mock.patch.object(ej, "MIN_FREE_GB", 1e9):
            out = self.run_pass(T0 + 300)
        self.assertEqual(out[0]["status"], "stopped")
        self.assertEqual(len(self.calls), 1)


class CliTests(Rec):
    def test_run_once_twice_and_ensure(self):
        self.reply = {v: b"" for v in rl.URL}
        self.reply["mexc"] = mexc([("A_USDT", 0, 10, 1)])
        only = ["--only", "mexc"]
        with mock.patch.object(rl, "OUT", self.dir), mock.patch.object(ej, "PACE_S", 0):
            self.assertEqual(rl.main(["run", "--once"] + only), 0)
            first = self.events()
            self.assertEqual(rl.main(["run", "--once"] + only), 0)
            self.assertEqual(self.events(), first)
            with mock.patch.object(ej.subprocess, "Popen") as popen:
                self.assertEqual(rl.main(["ensure"]), 0)              # lock free: starts `run`
                self.assertEqual(popen.call_args[0][0][-1], "run")
                held = ej.lock(self.dir)
                popen.reset_mock()
                self.assertEqual(rl.main(["ensure"]), 0)              # a daemon holds it: nothing started
                popen.assert_not_called()
                self.assertEqual(rl.main(["run", "--once"] + only), 1)   # one writer per file
                held.close()
        self.assertTrue((self.dir / "status.json").exists())


if __name__ == "__main__":
    unittest.main()
