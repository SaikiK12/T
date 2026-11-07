"""Daily point-in-time snapshot of the DefiLlama unlock calendar: the emissions index (every token's documented
past and upcoming unlock events, circulating and max supply, price, market cap) as published that day. Calendars are
revised after the fact; these dated copies are what an unlock lane may use for live tickets (OLD_SESSION_EDGES S1
warning). One gzipped file per UTC day, data/recorders/unlocks/<YYYY-MM-DD>.json.gz (gitignored); a second run the
same day writes nothing. Data collection only.

usage: python scripts/record_unlocks.py
"""
import gzip
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from fetch_unlocks import BASE, get_bytes  # noqa: E402
from lab import data  # noqa: E402

OUT = data.ROOT / "recorders" / "unlocks"


def record(fetch=get_bytes, day=None, out=OUT):
    day = day or time.strftime("%Y-%m-%d", time.gmtime())
    path = Path(out) / f"{day}.json.gz"
    if path.exists():
        return path, 0
    raw = fetch(f"{BASE}/emissionsIndex")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    tmp.write_bytes(gzip.compress(raw))
    tmp.replace(path)
    return path, len(raw)


def main():
    path, n = record()
    print(time.strftime("%H:%M:%S"), f"unlocks: {n} bytes -> {path}" if n else f"unlocks: day already recorded ({path})")


if __name__ == "__main__":
    main()
