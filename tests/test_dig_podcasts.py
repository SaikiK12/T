import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def module():
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("dig_podcasts", ROOT / "scripts" / "dig_podcasts.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


RSS = b"""<?xml version="1.0"?>
<rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:podcast="https://podcastindex.org/namespace/1.0">
<channel><title>Show</title>
<item><title>Funding Rate Arbitrage With an Ex-Jane Street Trader</title><guid>ep-1</guid>
<pubDate>Wed, 21 Oct 2026 09:00:00 GMT</pubDate><itunes:duration>1:02:05</itunes:duration>
<enclosure url="https://cdn/ep1.mp3" type="audio/mpeg"/>
<podcast:transcript url="https://t/ep1.html" type="text/html"/>
<podcast:transcript url="https://t/ep1.json" type="application/json"/>
<description>&lt;p&gt;Basis, carry and news.&lt;/p&gt;</description></item>
<item><title>Gardening</title><guid>ep-2</guid><itunes:duration>3725</itunes:duration></item>
</channel></rss>"""


class DigPodcastsTest(unittest.TestCase):
    def setUp(self):
        self.m = module()

    def test_episodes_parse_and_prefer_json_transcript(self):
        rows = self.m.parse_episodes("show", RSS)
        self.assertEqual(len(rows), 2)
        a, b = rows
        self.assertEqual(a["transcript"], "https://t/ep1.json")
        self.assertEqual(a["transcript_type"], "application/json")
        self.assertEqual(a["duration_s"], 3725)
        self.assertEqual(b["duration_s"], 3725)
        self.assertEqual(a["pub_utc"], "2026-10-21T09:00:00Z")
        self.assertEqual(a["audio"], "https://cdn/ep1.mp3")
        self.assertEqual(a["summary"], "Basis, carry and news.")
        self.assertEqual(b["transcript"], "")
        self.assertNotEqual(a["key"], b["key"])
        self.assertEqual(a["key"], self.m.key("show", "ep-1"))

    def test_score_and_choice(self):
        import pandas as pd
        df = self.m.score(pd.DataFrame(self.m.parse_episodes("show", RSS)))
        self.assertGreaterEqual(df.mech.iloc[0], 3)          # funding, arbitrage, basis, carry, news
        self.assertGreaterEqual(df.firm.iloc[0], 1)          # jane street
        self.assertEqual(df.mech.iloc[1], 0)
        self.assertEqual(list(self.m.chosen(df, 5).title), [df.title.iloc[0]])
        self.assertEqual(len(self.m.chosen(df, 5, match="gardening")), 0)   # mech >= 1 still applies

    def test_transcript_formats(self):
        js = json.dumps({"segments": [{"body": "Funding"}, {"body": "is"}, {"body": "positive."}]}).encode()
        self.assertEqual(self.m.transcript_text(js, "application/json"), "Funding is positive.")
        srt = b"1\n00:00:02,730 --> 00:00:04,430\nSpeaker 1: Hello there.\n\n2\n00:00:04,890 --> 00:00:07,240\nSpeaker 2: Basis.\n"
        self.assertEqual(self.m.transcript_text(srt, "application/srt"), "Hello there. Basis.")
        html = b"<p><cite>Host:</cite><time>00:53</time></p><p>Carry &amp; trend.</p>"
        self.assertEqual(self.m.transcript_text(html, "text/html"), "Carry & trend.")

    def test_seconds(self):
        self.assertEqual(self.m.seconds("62:05"), 3725)
        self.assertEqual(self.m.seconds("1:02:05"), 3725)
        self.assertIsNone(self.m.seconds(""))
        self.assertIsNone(self.m.seconds(None))


if __name__ == "__main__":
    unittest.main()
