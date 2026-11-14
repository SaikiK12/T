"""R472's frozen fetch (scripts/fetch_rebalfront.py) with DTB3 taken from its primary publisher, the Federal Reserve Board.

Why: on 2026-11-12 FRED refused the frozen client, which closed the connection from the cloud container and timed out
after 60 s from a GitHub runner (run 43167744562). curl received the same CSV, so FRED was screening the client.
The frozen client was not altered to get past that. FRED republishes DTB3 from H.15: the series is RIFSGFSM03_N.B,
the 3-month Treasury bill secondary-market rate on a discount basis, business days.

What changes: only the bytes behind the FRED URL. The wrapper downloads the Board's H.15 release archive
(FRB_h15_xml.zip) with the frozen client `fetch_rebalfront.get`. It keeps the zip in data/rebalfront/h15/ and writes
RIFSGFSM03_N.B as data/rebalfront/fred/DTB3.csv in FRED's own layout:
- the header is `observation_date,DTB3`;
- each value is the published string;
- days marked ND are left empty.
Everything else is the frozen `fetch` unchanged: the Yahoo calls, file names, parsing and the sha256 manifest.
On 2026-11-12 the converted file matched FRED's CSV, fetched once with curl's default client as a timing probe, byte
for byte: sha256 f524d6761c4728f2288fd6d8bc0dedb7b95ca0eb7836b9a73c7d6449c508640d, 19,006 rows from 1954-01-04,
801 of them empty. FRED is not contacted again.

usage: python scripts/fetch_rebalfront_h15.py --start 2002-06-01 --end 2026-11-12
"""
import argparse
import io
import json
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_rebalfront as fr  # noqa: E402  (frozen in R472)

H15_ZIP = "https://www.federalreserve.gov/releases/h15/data/FRB_h15_xml.zip"
SERIES = "RIFSGFSM03_N.B"


def dtb3_csv(zip_bytes):
    """FRED-layout CSV bytes of RIFSGFSM03_N.B from the H.15 SDMX archive."""
    root = ET.fromstring(zipfile.ZipFile(io.BytesIO(zip_bytes)).read("H15_data.xml"))
    ser = [e for e in root.iter() if e.tag.endswith("Series") and e.get("SERIES_NAME") == SERIES]
    if len(ser) != 1:
        raise SystemExit(f"{SERIES}: {len(ser)} series in the H.15 archive")
    lines = ["observation_date,DTB3"]
    for o in ser[0]:
        if o.tag.endswith("Obs"):
            ok = o.get("OBS_STATUS") == "A"
            lines.append(f"{o.get('TIME_PERIOD')},{o.get('OBS_VALUE') if ok else ''}")
    return ("\n".join(lines) + "\n").encode()


def fetch(start, end, out=fr.OUT):
    frozen_get = fr.get

    def get(url):
        if url != fr.FRED:
            return frozen_get(url)
        raw = frozen_get(H15_ZIP)
        (out / "h15").mkdir(parents=True, exist_ok=True)
        (out / "h15" / "FRB_h15_xml.zip").write_bytes(raw)
        return dtb3_csv(raw)

    fr.get = get
    try:
        fr.fetch(start, end, out)
    finally:
        fr.get = frozen_get
    man = json.loads((out / "manifest.json").read_text())
    man["source"] = ("query1.finance.yahoo.com/v8/finance/chart (SPY, IEF, TLT) and federalreserve.gov H.15 "
                     f"(FRB_h15_xml.zip, {SERIES} written as fred/DTB3.csv); public, no key")
    man["dtb3_from"] = H15_ZIP
    (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2002-06-01")
    ap.add_argument("--end", required=True)
    a = ap.parse_args()
    fetch(a.start, a.end)


if __name__ == "__main__":
    main()
