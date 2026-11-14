"""Inputs for carryhurdle_v1 (R483, M478/M481): import the sealed DefiLlama /chart bodies.

DefiLlama's free yields endpoints (yields.llama.fi/chart/<pool>) stopped on 2026-11-13. The three benchmark bodies were
fetched once at 2026-11-12T23:41:27Z, before any PREREG, and sealed unread outside the repository. Their sha256 were
committed in research/intake/websearch_wave_20261112.md (commit 3eff32c2). This importer makes no network request:
it copies the three .json bodies, their .hdr response headers and the capture's receipt.txt from --src into
--out (experiments/carryhurdle_v1/raw/ by default; `data/` folders are gitignored, these small files are committed),
and refuses to write anything if a body's sha256 or size differs from the intake note's table. The 10.8 MB pools file
in the capture is not copied. <out>/import_receipt.json lists every copied file's sha256, the source URL and capture
clock of each body, and the import clock.

usage: .venv/bin/python scripts/fetch_carryhurdle.py --src /path/to/sealed_chart_20261112 [--out DIR] [--intake FILE]
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "experiments" / "carryhurdle_v1" / "raw"
INTAKE = ROOT / "research" / "intake" / "websearch_wave_20261112.md"
ROW = re.compile(r"\|\s*(https://yields\.llama\.fi/chart/([0-9a-f-]{36}))\s*\|\s*200\s*\|\s*([\d,]+)\s*\|\s*([0-9a-f]{64})\s*\|")
CAPTURED = "2026-11-12T23:41:27Z"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sealed_table(intake):
    """{pool: (url, size, sha256)} from the intake note's capture table."""
    out = {}
    for m in ROW.finditer(Path(intake).read_text()):
        out[m.group(2)] = (m.group(1), int(m.group(3).replace(",", "")), m.group(4))
    if not out:
        raise SystemExit(f"{intake}: no sealed /chart rows found")
    return out


def check(src, table):
    """Raise unless every sealed body in src matches the intake note's size and sha256."""
    src = Path(src)
    for pool, (_, size, want) in table.items():
        body = src / f"{pool}.json"
        if not body.is_file():
            raise SystemExit(f"{body} missing")
        got = sha256(body)
        if got != want or body.stat().st_size != size:
            raise SystemExit(f"{body}: sha256 {got} ({body.stat().st_size} B) != sealed {want} ({size} B)")
        if not (src / f"{pool}.hdr").is_file():
            raise SystemExit(f"{src / (pool + '.hdr')} missing")
    if not (src / "receipt.txt").is_file():
        raise SystemExit(f"{src / 'receipt.txt'} missing")


def run(src, out, intake):
    table = sealed_table(intake)
    check(src, table)
    src, out = Path(src), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    names = [f"{p}{ext}" for p in sorted(table) for ext in (".json", ".hdr")] + ["receipt.txt"]
    for n in names:
        shutil.copyfile(src / n, out / n)
    check(out, table)
    rec = {"source": "yields.llama.fi/chart/<pool>, public, no key; captured once before the PREREG and sealed",
           "captured_utc": CAPTURED, "imported_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "intake_note": str(Path(intake).resolve().relative_to(ROOT)) if Path(intake).resolve().is_relative_to(ROOT)
           else str(intake),
           "bodies": {p: {"url": u, "bytes": s, "sha256": h} for p, (u, s, h) in sorted(table.items())},
           "files": {n: {"sha256": sha256(out / n)} for n in names}}
    (out / "import_receipt.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(f"imported {len(names)} files into {out}; every body matches the intake note")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="the sealed capture folder (or its backup)")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--intake", default=str(INTAKE))
    a = ap.parse_args()
    run(a.src, a.out, a.intake)


if __name__ == "__main__":
    sys.exit(main())
