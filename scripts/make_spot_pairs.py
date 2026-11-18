"""Rebuild data/spot_pairs.json, the perp -> Binance spot USDT pair map read by scripts/fetch_spot.py, lab/daily.py
and scripts/run_carry.py: {perp: {"spot": SPOT, "months": [first YYYY-MM, last YYYY-MM]}}.

Why: the file lived only in the gitignored data/ folder and was lost with the container on 2026-11-17; no script made
it. This one rebuilds it from the public archive.

Rule:
- every spot pair `<BASE>USDT` with monthly 1h klines on data.binance.vision is matched to a perp by the lab's name rule
  (`lab.venues.binance_perp`, multiplier prefixes included);
- when two spot pairs match one perp, the one whose name equals the perp's is kept, then the first by name;
- `months` are the first and last monthly kline files of the spot pair up to `lab.data.END`.

`--perps-from PROVENANCE` keeps only the perps that have a file in a provenance record (docs/provenance/spot_1h.json
lists the 481 the old map held), so a rebuild can be checked file by file against that record.

usage: python scripts/make_spot_pairs.py [--perps-from docs/provenance/spot_1h.json] [--workers 16]
"""
import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, venues  # noqa: E402

SPOT = "data/spot/monthly/klines/"


def spot_symbols():
    _, prefixes = data._list(SPOT)
    return sorted(p.rstrip("/").rsplit("/", 1)[1] for p in prefixes if p.rstrip("/").endswith("USDT"))


def months(sym, end=data.END):
    ms = sorted(m.group(1) for k in data.list_zips(f"{SPOT}{sym}/1h/") if (m := data._DATE.search(k)))
    ms = [m for m in ms if m <= end[:7]]
    return [ms[0], ms[-1]] if ms else None


def build(spots, perps, month_fn, keep=None):
    cands = {}
    for s in spots:
        hit = venues.binance_perp(s[:-4], perps)
        if hit and (keep is None or hit[0] in keep):
            cands.setdefault(hit[0], []).append(s)
    out = {}
    for perp, ss in sorted(cands.items()):
        for s in sorted(ss, key=lambda s: (s != perp, s)):
            m = month_fn(s)
            if m:
                out[perp] = {"spot": s, "months": m}
                break
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--perps-from", type=Path)
    ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args(argv)
    keep = None
    if a.perps_from:
        rec = json.loads(a.perps_from.read_text())
        keep = {Path(f["path"]).stem for f in rec["file_hashes"] if f["path"].endswith(".parquet")}
    spots = spot_symbols()
    perps = venues.binance_perps()
    pre = [s for s in spots if (h := venues.binance_perp(s[:-4], perps)) and (keep is None or h[0] in keep)]
    with ThreadPoolExecutor(a.workers) as ex:
        got = dict(zip(pre, ex.map(months, pre)))
    out = build(pre, perps, got.get, keep)
    (data.ROOT / "spot_pairs.json").write_text(json.dumps(out, indent=1, sort_keys=True))
    missing = sorted(keep - set(out)) if keep is not None else []
    print(json.dumps({"spot_symbols": len(spots), "pairs": len(out), "recorded": len(keep) if keep else None,
                      "recorded_without_pair": missing[:20], "n_recorded_without_pair": len(missing)}))


if __name__ == "__main__":
    main()
