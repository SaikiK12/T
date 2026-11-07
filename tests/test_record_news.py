import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent


def module():
    spec = importlib.util.spec_from_file_location("record_news", ROOT / "scripts" / "record_news.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


RSS = b"""<?xml version="1.0"?><rss><channel><title>x</title>
<item><title>Fed Holds Rates</title><link>https://a/1</link><guid>g1</guid>
<pubDate>Wed, 21 Oct 2026 09:57:01 GMT</pubDate><description>&lt;p&gt;Body  text&lt;/p&gt;</description></item>
<item><title>No date</title><link>https://a/2</link></item></channel></rss>"""
ATOM = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Atom one</title><id>tag:1</id>
<link href="https://b/1"/><updated>2026-10-21T08:00:00+02:00</updated><summary>s</summary></entry></feed>"""
OKX = json.dumps({"data": [{"details": [{"title": "OKX to list X", "url": "https://okx/x", "pTime": "1792576800000"}]}]})


class ParseTest(unittest.TestCase):
    def setUp(self):
        self.m = module()

    def test_rss(self):
        a, b = self.m.parse_feed("bloomberg_markets", RSS)
        self.assertEqual((a["id"], a["title"], a["link"], a["pub_utc"], a["summary"]),
                         ("g1", "Fed Holds Rates", "https://a/1", "2026-10-21T09:57:01Z", "Body text"))
        self.assertEqual((b["id"], b["pub_utc"]), ("https://a/2", ""))          # no guid: the link is the id

    def test_atom_and_offset(self):
        (a,) = self.m.parse_feed("decrypt", ATOM)
        self.assertEqual((a["id"], a["link"], a["pub_utc"]), ("tag:1", "https://b/1", "2026-10-21T06:00:00Z"))

    def test_okx_json(self):
        (a,) = self.m.parse_feed("okx_listings", OKX.encode())
        self.assertEqual((a["id"], a["title"], a["pub_utc"]), ("https://okx/x", "OKX to list X", "2026-10-21T10:00:00Z"))


class RecorderTest(unittest.TestCase):
    def test_new_items_once_and_after_restart(self):
        m = module()
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(m, "OUT", Path(tmp)), mock.patch.object(m, "FEEDS", {"bloomberg_markets": "u"}), \
                    mock.patch.object(m, "fetch", return_value=RSS):
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(1) as pool:
                    r = m.Recorder()
                    self.assertEqual(r.poll(pool), 2)
                    self.assertEqual(r.poll(pool), 0)
                    self.assertEqual(m.Recorder().poll(pool), 0)                  # the files remember what was seen
                rows = [json.loads(x) for f in Path(tmp).glob("*.jsonl") for x in f.read_text().splitlines()]
                self.assertEqual(len(rows), 2)
                self.assertEqual(set(rows[0]), {"seen_utc", "feed", "id", "title", "link", "pub_utc", "summary"})


if __name__ == "__main__":
    unittest.main()
