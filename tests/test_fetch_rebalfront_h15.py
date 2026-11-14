"""scripts/fetch_rebalfront_h15.py: H.15 SDMX archive to FRED's DTB3 CSV layout, and the frozen fetch's FRED call
routed to it without touching the Yahoo calls."""
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_rebalfront_h15 as w  # noqa: E402

XML = """<?xml version="1.0"?>
<message:MessageGroup xmlns:message="m" xmlns:kf="k" xmlns:frb="f">
 <kf:DataSet>
  <kf:Series SERIES_NAME="RIFSGFSM06_N.B"><frb:Obs OBS_STATUS="A" OBS_VALUE="9.99" TIME_PERIOD="1954-01-04" /></kf:Series>
  <kf:Series SERIES_NAME="RIFSGFSM03_N.B">
   <frb:Obs OBS_STATUS="A" OBS_VALUE="1.33" TIME_PERIOD="1954-01-04" />
   <frb:Obs OBS_STATUS="ND" OBS_VALUE="-9999" TIME_PERIOD="1954-01-19" />
   <frb:Obs OBS_STATUS="A" OBS_VALUE="4.00" TIME_PERIOD="2026-11-05" />
  </kf:Series>
 </kf:DataSet>
</message:MessageGroup>"""


def archive(xml=XML):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("H15_data.xml", xml)
    return buf.getvalue()


class TestH15(unittest.TestCase):
    def test_fred_layout(self):
        self.assertEqual(w.dtb3_csv(archive()),
                         b"observation_date,DTB3\n1954-01-04,1.33\n1954-01-19,\n2026-11-05,4.00\n")

    def test_missing_series_stops(self):
        with self.assertRaises(SystemExit):
            w.dtb3_csv(archive(XML.replace("RIFSGFSM03_N.B", "OTHER")))

    def test_fetch_routes_only_fred(self):
        calls = []

        def fake_get(url):
            calls.append(url)
            if url == w.H15_ZIP:
                return archive()
            if url == w.fr.FRED:
                raise AssertionError("FRED must not be contacted")
            return json.dumps({"chart": {"result": []}}).encode()

        with tempfile.TemporaryDirectory() as d, mock.patch.object(w.fr, "get", fake_get), \
                mock.patch.object(w.fr, "parse_chart", lambda js: __import__("pandas").DataFrame(
                    {"date": ["2026-11-05"], "close": [1.0], "adjclose": [1.0]})), \
                mock.patch.object(w.fr.time, "sleep", lambda s: None):
            out = Path(d)
            w.fetch("2026-11-01", "2026-11-06", out)
            self.assertIs(w.fr.get, fake_get)  # the frozen module's get is restored
            self.assertEqual(sum(u == w.H15_ZIP for u in calls), 1)
            self.assertNotIn(w.fr.FRED, calls)
            self.assertEqual((out / "fred" / "DTB3.csv").read_bytes(), w.dtb3_csv(archive()))
            man = json.loads((out / "manifest.json").read_text())
            self.assertIn("fred/DTB3.csv", man["files"])
            self.assertIn("h15/FRB_h15_xml.zip", man["files"])
            self.assertEqual(man["dtb3_from"], w.H15_ZIP)


if __name__ == "__main__":
    unittest.main()
