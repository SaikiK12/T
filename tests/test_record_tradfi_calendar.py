"""scripts/record_tradfi_calendar.py: halt feed, earnings calendar, Fed calendar and Treasury parsers; revision and
scoping behaviour through the shared journal. Offline: no network."""
import calendar
import csv
import datetime
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import event_journal as ej  # noqa: E402
import record_tradfi_calendar as rc  # noqa: E402

T0 = calendar.timegm((2026, 11, 2, 15, 0, 0))          # Monday 10:00 ET


def halts(resumed=False):
    r = ("<ndaq:ResumptionDate>11/02/2026</ndaq:ResumptionDate><ndaq:ResumptionQuoteTime>15:45:39</ndaq:ResumptionQuoteTime>"
         "<ndaq:ResumptionTradeTime>16:00:00</ndaq:ResumptionTradeTime>") if resumed else (
         "<ndaq:ResumptionDate /><ndaq:ResumptionQuoteTime /><ndaq:ResumptionTradeTime />")
    return ('﻿<?xml version="1.0" encoding="utf-8"?><rss version="2.0" xmlns:ndaq="http://www.nasdaqtrader.com/">'
            "<channel><item><title>VCIG</title><pubDate>Mon, 02 Nov 2026 05:00:00 GMT</pubDate>"
            "<ndaq:HaltDate>11/02/2026</ndaq:HaltDate><ndaq:HaltTime>15:45:39.206</ndaq:HaltTime>"
            "<ndaq:IssueSymbol>VCIG</ndaq:IssueSymbol><ndaq:IssueName>VCI Global Ltd Ord</ndaq:IssueName>"
            "<ndaq:Market>NASDAQ</ndaq:Market><ndaq:ReasonCode>LUDP</ndaq:ReasonCode><ndaq:PauseThresholdPrice />"
            f"{r}</item></channel></rss>").encode("utf-8")


def as_of(d):
    x = datetime.date.fromisoformat(d)
    return f"{x:%a}, {x:%b} {x.day}, {x.year}"


def earnings(date, as_of, syms, slot="time-after-hours"):
    return json.dumps({"data": {"asOf": as_of, "rows": [
        {"symbol": s, "name": s + " Inc", "time": slot, "fiscalQuarterEnding": "Sep/2026", "epsForecast": "$1.00",
         "noOfEsts": "5", "lastYearRptDt": "11/04/2025", "marketCap": "$1"} for s in syms]}}).encode()


FED = json.dumps({"events": [
    {"type": "FOMC", "month": "2026-12", "days": "9", "title": "FOMC Press Conference", "time": "2:30 p.m."},
    {"type": "Speeches", "month": "2026-11", "days": "6", "title": "Discussion", "time": "12:15 p.m.", "location": "X"},
    {"type": "Speeches", "month": "2026-11", "days": "6", "title": "Discussion", "time": "3:00 p.m."},   # same title twice
    {"type": "Stat", "month": "2026-11", "days": "3, 10, 17", "title": "H.4.1", "time": ""},
    {"type": "Stat", "month": "2026-09", "days": "2", "title": "Old", "time": "4:30 p.m."}]}).encode("utf-8-sig")

TREAS = json.dumps([{"cusip": "912797VH7", "securityType": "Bill", "securityTerm": "6-Week",
                     "securityDescription": "6-Week Bill", "announcementDate": "2026-10-29T00:00:00",
                     "competitiveAuctionCloseDate": "2026-11-03T00:00:00", "competitiveAuctionCloseTime": "11:30 AM",
                     "offeringAmount": "100000000000", "updatedTimestamp": "2026-10-29T11:01:51"}]).encode()


class ParserTests(unittest.TestCase):
    def test_halts_with_bom_and_et_to_utc(self):
        (k, it), = rc.parse_halts(halts()).items()
        self.assertEqual(k, "VCIG|11/02/2026|15:45:39.206")
        self.assertEqual(it["etime"], ("ndaq:HaltDate+ndaq:HaltTime", "11/02/2026 15:45:39.206", "2026-11-02T20:45:39Z"))
        self.assertEqual((it["fields"]["reason"], it["fields"]["resume_trade"]), ("LUDP", ""))

    def test_halt_summer_time_offset(self):
        self.assertEqual(rc.et_to_utc("10/30/2026", "09:30:00", ("%m/%d/%Y %H:%M:%S",)), "2026-10-30T13:30:00Z")

    def test_earnings_date_must_match_as_of(self):
        ok = rc.parse_earnings(earnings("2026-11-03", "Tue, Nov 3, 2026", ["AMD", "AMGN"]), "2026-11-03")
        self.assertEqual(set(ok), {"2026-11-03|AMD", "2026-11-03|AMGN"})
        self.assertEqual(ok["2026-11-03|AMD"]["fields"]["time"], "time-after-hours")
        self.assertNotIn("marketCap", ok["2026-11-03|AMD"]["fields"])
        with self.assertRaisesRegex(ValueError, "asOf"):
            rc.parse_earnings(earnings("x", "Mon, Nov 2, 2026", ["AMD"]), "2026-11-03")
        self.assertEqual(rc.parse_earnings(b'{"data": {"asOf": "Sat, Nov 7, 2026", "rows": null}}', "2026-11-07"), {})

    def test_earn_dates_are_the_next_weekdays_in_eastern_time(self):
        self.assertEqual(rc.earn_dates(T0), ["2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06"])
        self.assertEqual(rc.earn_dates(calendar.timegm((2026, 11, 7, 3, 0, 0))), ["2026-11-06", "2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12"])   # Fri 22:00 ET

    def test_fed_calendar_window_duplicates_and_clock(self):
        out = rc.parse_fed(FED, "2026-11")
        self.assertEqual(len(out), 4)                                   # September is outside the window
        self.assertEqual(out["Speeches|2026-11|6|Discussion|1"]["etime"][2], "2026-11-06T17:15:00Z")
        self.assertIn("Speeches|2026-11|6|Discussion|2", out)
        self.assertEqual(out["FOMC|2026-12|9|FOMC Press Conference|1"]["etime"][2], "2026-12-09T19:30:00Z")
        self.assertEqual(out["Stat|2026-11|3, 10, 17|H.4.1|1"]["etime"][2], "")      # multi-day list: no clock claimed

    def test_treasury_close_time(self):
        (k, it), = rc.parse_treasury(TREAS).items()
        self.assertEqual((k, it["etime"][2]), ("912797VH7", "2026-11-03T16:30:00Z"))
        self.assertEqual(it["fields"]["offering_amount"], "100000000000")


class Rec(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name) / "cal"
        self.j = ej.Journal(self.dir)
        self.reply = {}
        self.calls = []

        def fake_get(url, body=None, timeout=30, headers=None):
            self.calls.append(url)
            key = url if url in self.reply else url.split("?")[0] if url.split("?")[0] in self.reply else None
            if key is None:
                raise AssertionError(url)
            return self.reply[key]

        for p in (mock.patch.object(ej, "http_get", fake_get), mock.patch.object(ej, "PACE_S", 0)):
            p.start()
            self.addCleanup(p.stop)

    def events(self):
        with open(self.dir / "events.csv", newline="") as f:
            return list(csv.DictReader(f))

    def run_pass(self, t, names, **kw):
        with mock.patch.object(ej.time, "time", return_value=t):
            return ej.poll_all(self.j, [s for s in rc.SOURCES if s.name in names], now_s=t, pace=0, **kw)


class JournalTests(Rec):
    def test_halt_resumption_is_a_change_row_and_second_run_is_silent(self):
        self.reply = {rc.URL["nasdaq_halts"]: halts()}
        self.run_pass(T0, {"nasdaq_halts"})
        self.reply[rc.URL["nasdaq_halts"]] = halts(resumed=True)
        self.run_pass(T0 + 300, {"nasdaq_halts"})
        ev = self.events()
        self.assertEqual([(r["event"], r["field"], r["old"], r["new"], r["src_field"]) for r in ev],
                         [("baseline", "", "", "", "ndaq:IssueSymbol+HaltDate+HaltTime"),
                          ("change", "resume_date", "", "11/02/2026", "ndaq:ResumptionDate"),
                          ("change", "resume_quote", "", "15:45:39", "ndaq:ResumptionQuoteTime"),
                          ("change", "resume_trade", "", "16:00:00", "ndaq:ResumptionTradeTime")])
        self.run_pass(T0 + 600, {"nasdaq_halts"})
        self.run_pass(T0 + 601, {"nasdaq_halts"}, force=True)
        self.assertEqual(len(self.events()), 4)
        self.reply[rc.URL["nasdaq_halts"]] = halts().replace(b"<item>", b"<x>").replace(b"</item>", b"</x>")   # next day: empty
        out = self.run_pass(T0 + 900, {"nasdaq_halts"})
        self.assertEqual(out[0]["status"], "ok")                         # an empty halt feed is legitimate; no `gone` rows
        self.assertEqual(len(self.events()), 4)

    def test_earnings_new_move_and_scope(self):
        dates = rc.earn_dates(T0)
        url = lambda d: rc.URL["nasdaq_earnings"].format(date=d)

        def serve(by_date):
            self.reply = {url(d): earnings(d, as_of(d), by_date.get(d, [])) for d in dates}
        serve({"2026-11-03": ["AMD", "AMGN"], "2026-11-05": ["AAA"]})
        self.run_pass(T0, {"nasdaq_earnings"})
        self.assertEqual(len(self.calls), len(dates))                    # one request per weekday
        self.assertEqual(sorted(r["key"] for r in self.events()), ["2026-11-03|AMD", "2026-11-03|AMGN", "2026-11-05|AAA"])
        # AAA moves from the 5th to the 6th, AMD's slot changes; the first day (a Monday) rolls out of scope next day
        serve({"2026-11-03": ["AMD", "AMGN"], "2026-11-06": ["AAA"]})
        self.reply[url("2026-11-03")] = earnings("2026-11-03", "Tue, Nov 3, 2026", ["AMD", "AMGN"], slot="time-pre-market")
        self.run_pass(T0 + 21600, {"nasdaq_earnings"})
        got = {(r["key"], r["event"], r["field"], r["new"]) for r in self.events()[3:]}
        self.assertEqual(got, {("2026-11-05|AAA", "gone", "", ""), ("2026-11-06|AAA", "new", "", ""),
                               ("2026-11-03|AMD", "change", "time", "time-pre-market"),
                               ("2026-11-03|AMGN", "change", "time", "time-pre-market")})
        n = len(self.events())
        later = T0 + 2 * 86400                                           # Wednesday: Mon and Tue left the polled window
        dates2 = rc.earn_dates(later)
        self.reply = {url(d): earnings(d, as_of(d), []) for d in dates2}
        self.reply[url("2026-11-06")] = earnings("2026-11-06", "Fri, Nov 6, 2026", ["AAA"])
        self.run_pass(later, {"nasdaq_earnings"})
        self.assertEqual(len(self.events()), n)                          # 11-03 rows are out of scope, not `gone`

    def test_fed_and_treasury_changes(self):
        self.reply = {rc.URL["fed_calendar"]: FED, rc.URL["treasury_auctions"]: TREAS}
        self.run_pass(T0, {"fed_calendar", "treasury_auctions"})
        self.assertEqual(len(self.events()), 4 + 1)
        fed2 = json.loads(FED.decode("utf-8-sig"))
        fed2["events"][1]["time"] = "1:00 p.m."
        self.reply[rc.URL["fed_calendar"]] = json.dumps(fed2).encode()
        t = json.loads(TREAS)
        t[0]["offeringAmount"] = "90000000000"
        self.reply[rc.URL["treasury_auctions"]] = json.dumps(t).encode()
        self.run_pass(T0 + 21600, {"fed_calendar", "treasury_auctions"})
        got = [(r["source"], r["field"], r["old"], r["new"], r["src_field"]) for r in self.events()[5:]]
        self.assertEqual(sorted(got), [("fed_calendar", "time", "12:15 p.m.", "1:00 p.m.", "time"),
                                       ("treasury_auctions", "offering_amount", "100000000000", "90000000000",
                                        "offeringAmount")])
        self.run_pass(T0 + 43200, {"fed_calendar", "treasury_auctions"}, force=True)
        self.assertEqual(len(self.events()), 7)


class CliTests(Rec):
    def test_run_once_twice(self):
        self.reply = {rc.URL["nasdaq_halts"]: halts()}
        with mock.patch.object(rc, "OUT", self.dir):
            self.assertEqual(rc.main(["run", "--once", "--only", "nasdaq_halts"]), 0)
            first = self.events()
            self.assertEqual(rc.main(["run", "--once", "--only", "nasdaq_halts"]), 0)
        self.assertEqual(self.events(), first)
        self.assertEqual(len(self.calls), 1)


if __name__ == "__main__":
    unittest.main()
