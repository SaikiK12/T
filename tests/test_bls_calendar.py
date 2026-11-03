"""Schedule parsing and journal revision contracts; no market outcomes."""
import calendar
import csv
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import bls_calendar as bls,record_tradfi_calendar as rc


def event(uid='a',start='DTSTART;TZID=US-Eastern:20261106T083000',title='Employment Situation',extra=''):
    return f'BEGIN:VEVENT\r\nUID:{uid}\r\n{start}\r\nSUMMARY:{title}\r\nSEQUENCE:1\r\n{extra}END:VEVENT\r\n'


def feed(*events): return ('BEGIN:VCALENDAR\r\nVERSION:2.0\r\n'+''.join(events)+'END:VCALENDAR\r\n').encode()


class BlsTests(unittest.TestCase):
    def test_eastern_standard_summer_and_utc_are_not_floating(self):
        raw=feed(event(),event('b','DTSTART;TZID=America/New_York:20260702T083000'),
                 event('c','DTSTART:20261110T133000Z','Consumer Price Index'))
        out=bls.parse(raw,'2026-01-01')
        self.assertEqual(out['a']['etime'][2],'2026-11-06T13:30:00Z')
        self.assertEqual(out['b']['etime'][2],'2026-07-02T12:30:00Z')
        self.assertEqual(out['c']['etime'][2],'2026-11-10T13:30:00Z')
        self.assertIn('scheduled',out['a']['etime'][0])

    def test_folded_text_quotes_and_escapes_preserve_source_meaning(self):
        raw=feed(event(title='Long "title: quoted"\\, and\\; continued\r\n text\\nsecond line'))
        item=bls.parse(raw,'2026-01-01')['a']
        self.assertEqual(item['fields']['title'],'Long "title: quoted", and; continuedtext\nsecond line')

    def test_date_only_floating_unknown_and_dst_edge_clocks_stay_unknown(self):
        raw=feed(event('date','DTSTART;VALUE=DATE:20261106'),
                 event('float','DTSTART:20261106T083000'),
                 event('zone','DTSTART;TZID=Unknown/Zone:20261106T083000'),
                 event('fall','DTSTART;TZID=US-Eastern:20261101T013000'),
                 event('spring','DTSTART;TZID=US-Eastern:20260308T023000'))
        out=bls.parse(raw,'2026-01-01')
        self.assertTrue(all(not v['etime'][2] for v in out.values()))
        self.assertEqual(out['fall']['fields']['clock_state'],'ambiguous_or_nonexistent')

    def test_future_scope_is_eastern_and_uid_remains_the_revision_key(self):
        out=bls.parse(feed(event('past','DTSTART:20261103T020000Z'),event()),'2026-11-03')
        self.assertEqual(set(out),{'a'})
        changed=bls.parse(feed(event(start='DTSTART;TZID=US-Eastern:20261109T083000')),'2026-11-03')
        self.assertEqual(set(changed),{'a'})
        self.assertNotEqual(out['a']['fields']['dtstart'],changed['a']['fields']['dtstart'])

    def test_incomplete_duplicate_recurring_or_malformed_calendars_fail_whole_poll(self):
        cases=[b'<html>blocked</html>',feed(event())[:-20],feed(event(),event()),
               feed(event(extra='RRULE:FREQ=MONTHLY\r\n')),feed(event(start='DTSTART:20261399T083000')),
               feed(event()).replace(b'UID:a\r\n',b''),feed(event()).replace(b'END:VEVENT',b'END:VALARM'),
               feed(event())+feed(event('second')),feed(event(start='DTSTART;TZID=UTC:20261106T083000Z'))]
        for raw in cases:
            with self.subTest(raw=raw[:60]),self.assertRaises(ValueError): bls.parse(raw,'2026-01-01')

    def test_timezone_rules_are_not_mistaken_for_event_recurrence(self):
        zone='BEGIN:VTIMEZONE\r\nTZID:US-Eastern\r\nBEGIN:DAYLIGHT\r\nRRULE:FREQ=YEARLY\r\nEND:DAYLIGHT\r\nEND:VTIMEZONE\r\n'
        self.assertEqual(set(bls.parse(feed(zone,event()),'2026-01-01')),{'a'})

    def test_journal_baseline_revision_failure_and_rollover_preserve_history(self):
        src=next(s for s in rc.SOURCES if s.name=='bls_calendar')
        t0=calendar.timegm((2026,11,3,15,0,0))
        with tempfile.TemporaryDirectory() as d:
            journal=rc.ej.Journal(Path(d))
            with patch.object(rc.ej,'http_get',return_value=feed(event())):
                result=rc.ej.poll_one(journal,src,t0,force=True)
            self.assertEqual(result['status'],'ok')
            before=journal.events.read_bytes()
            revised=feed(event(start='DTSTART;TZID=US-Eastern:20261109T083000'))
            with patch.object(rc.ej,'http_get',return_value=revised):
                self.assertEqual(rc.ej.poll_one(journal,src,t0+21600,force=True)['status'],'ok')
            with journal.events.open(newline='') as f: rows=list(csv.DictReader(f))
            self.assertEqual(rows[0]['event'],'baseline')
            self.assertTrue(any(r['event']=='change' and r['field']=='dtstart' for r in rows))
            revision=journal.events.read_bytes();self.assertTrue(revision.startswith(before))
            with patch.object(rc.ej,'http_get',return_value=b'not a calendar'):
                self.assertEqual(rc.ej.poll_one(journal,src,t0+43200,force=True)['status'],'error')
            self.assertEqual(journal.events.read_bytes(),revision)
            # A valid future list excludes expired old events from gone coverage.
            covered=rc.fetch_bls
            with patch.object(rc.ej,'http_get',return_value=feed(event('later','DTSTART;TZID=US-Eastern:20261204T083000'))):
                _,scope=covered(calendar.timegm((2026,11,10,15,0,0)))
            self.assertFalse(scope({'schedule_day':'2026-11-09'}))
            self.assertTrue(scope({'schedule_day':'2026-12-04'}))


if __name__=='__main__': unittest.main()
