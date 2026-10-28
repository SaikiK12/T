import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch

import pandas as pd

from scripts import dig_talks as dt


class DigTalksTest(unittest.TestCase):
    def test_guest_reads_titles_where_the_person_speaks(self):
        rx = r"\bJohn Arnold\b"
        self.assertTrue(dt.guest("John Arnold - China, Energy Markets", rx))
        self.assertTrue(dt.guest("Energy markets ft. John Arnold", rx))
        self.assertTrue(dt.guest("A chat with John Arnold", rx))
        self.assertFalse(dt.guest("What happened to John Arnold's old desk", rx))
        self.assertTrue(dt.guest("john arnold on gas", rx))
        self.assertFalse(dt.guest("The untold story of John Arnold", rx))

    def test_person_filter_precedes_shared_episode_deduplication(self):
        talks=pd.DataFrame([
            {"person":person,"tier":"A","where":"title","key":"shared",
             "title":"Ed Thorp and Rob Carver on trading","pub_utc":"2024-01-01",
             "transcript":"https://publisher.example/transcript","transcript_type":"text/plain",
             "audio":"","feed":"publisher","duration_s":None}
            for person in ("Ed Thorp","Rob Carver")])
        calls=[]
        def get(url):calls.append(url);return b"A received discussion of trading risk."
        with tempfile.TemporaryDirectory() as temp,patch.object(dt,'SUBS',Path(temp)),patch.object(dt,'log'):
            self.assertEqual(dt.fetch(talks,people='rob',get=get),['shared'])
        self.assertEqual(calls,['https://publisher.example/transcript'])

    def test_windows_merge_overlapping_hits_and_score_numbers_and_first_person(self):
        filler = " ".join(["word"] * 400)
        text = f"{filler} we are a market maker and our edge is the spread of 2 bps {filler} arbitrage {filler}"
        out = dt.windows(text, width=20)
        self.assertEqual(len(out), 2)                       # the two near hits merged; the far one stands alone
        first, second = out
        self.assertIn("market maker", first["text"])
        self.assertGreaterEqual(len(first["cues"]), 2)
        self.assertGreater(first["score"], second["score"])   # more cues, a number and first-person speech
        self.assertLessEqual(second["hi"] - second["lo"], 40)

    def test_priority_puts_feed_transcripts_first_then_one_episode_per_person(self):
        t = pd.DataFrame([
            {"person": "John Arnold", "tier": "A", "where": "title", "key": "a1", "title": "John Arnold on gas",
             "pub_utc": "2024-01-01", "transcript": ""},
            {"person": "John Arnold", "tier": "A", "where": "title", "key": "a2", "title": "John Arnold: markets",
             "pub_utc": "2025-01-01", "transcript": ""},
            {"person": "Cobie", "tier": "B", "where": "title", "key": "c1", "title": "UpOnly with Cobie",
             "pub_utc": "2023-01-01", "transcript": ""},
            {"person": "Cobie", "tier": "B", "where": "summary", "key": "c2", "title": "Weekly rollup",
             "pub_utc": "2022-01-01", "transcript": "https://feed/t.txt"},
        ])
        order = list(dt.priority(t).key)
        self.assertEqual(order[0], "c2")                    # a published transcript costs nothing
        self.assertEqual(order[1:3], ["a2", "c1"])          # each person's best before anyone's second, tier A first
        self.assertEqual(order[3], "a1")


if __name__ == "__main__":
    unittest.main()
