"""R370's data: CME Globex trades (Databento) and Binance USD-M aggregated trades around 60 EIA releases and their placebo days.

- windows: experiments/cmelead_v1/windows.csv, one row per (release, day) = the release instant T and the same clock time on
  the placebo days of scripts/run_eventlag.py (gas T-2 d and T-3 d, crude T-1 d and T-2 d), each [T - 310 s, T + 75 s].
  The releases are experiments/eventdrift_v1/events.csv (R368's 60 releases, 2026-04-01 .. 2026-10-22).
- CME: Databento dataset GLBX.MDP3, schema trades, CL.v.0 (crude) and NG.v.0 (gas), the front month by volume, stored as the
  raw CSV+zstd the API returns under data/databento/cmelead/ with its manifest (price quoted before each pull, bytes,
  sha256). Every pull is refused above 5 cents, and the whole lane above TOTAL_CAP_USD, using the free get_cost endpoint.
- Binance: data.binance.vision daily aggTrades of CLUSDT and NATGASUSDT, each zip checked against its published sha256, only
  the windows kept: data/cmelead/binance/<SYMBOL>/<anchor ms>.parquet (t in ms, price, qty, buyer_maker, agg_id).
- docs/provenance/cmelead.json: both sources, every zip's sha256, every file's size and sha256.

The key is read from /root/.config/databento/env by scripts/fetch_databento.py and goes nowhere else. This script computes no
price change; it only counts rows.
usage: python -I scripts/fetch_cmelead.py windows | plan | fetch | provenance
"""
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_databento as fd  # noqa: E402
import fetch_settle_ticks as st  # noqa: E402

EVENTS = ROOT / "experiments" / "eventdrift_v1" / "events.csv"
LANE = ROOT / "experiments" / "cmelead_v1"
WINDOWS = LANE / "windows.csv"
CME_DIR = ROOT / "data" / "databento" / "cmelead"
BN_DIR = ROOT / "data" / "cmelead" / "binance"
PROV = ROOT / "docs" / "provenance" / "cmelead.json"
BEFORE_MS, AFTER_MS = 310_000, 75_000
DAY_MS = 86_400_000
PLACEBO_DAYS = {"ngs": (2, 3), "wpsr": (1, 2)}
CME_ROOT = {"ngs": "NG.v.0", "wpsr": "CL.v.0"}
BN_SYMBOL = {"ngs": "NATGASUSDT", "wpsr": "CLUSDT"}
ARCHIVE_START = "2026-04-01"                     # first day of the CLUSDT / NATGASUSDT aggTrades archive
PER_PULL_USD = 0.05
TOTAL_CAP_USD = 2.0
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


def iso(ms):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ms / 1000))


def windows():
    e = pd.read_csv(EVENTS)
    rows = []
    for r in e.itertuples():
        for kind, back in [("event", 0)] + [(f"placebo-{b}d", b) for b in PLACEBO_DAYS[r.event]]:
            anchor = int(r.release_ms) - back * DAY_MS
            rows.append({"event": r.event, "release_ms": int(r.release_ms), "kind": kind, "anchor_ms": anchor,
                         "lo_ms": anchor - BEFORE_MS, "hi_ms": anchor + AFTER_MS, "cme": CME_ROOT[r.event],
                         "binance": BN_SYMBOL[r.event]})
    return pd.DataFrame(rows)


def cme_params(w):
    return {"dataset": "GLBX.MDP3", "symbols": w.cme, "stype_in": "continuous", "schema": "trades", "start": iso(w.lo_ms),
            "end": iso(w.hi_ms)}


def cme_file(w):
    p = cme_params(w)
    stem = "_".join([p["dataset"], p["symbols"], p["schema"], p["start"], p["end"]]).replace(":", "")
    return CME_DIR / f"{stem}.csv.zst"


def spent():
    m = CME_DIR / "manifest.csv"
    return float(pd.read_csv(m).quoted_usd.sum()) if m.exists() else 0.0


def plan(w, key):
    todo = [r for r in w.itertuples() if not cme_file(r).exists()]
    total = sum(fd.quote(cme_params(r), key) for r in todo)
    log(f"{len(w)} windows, {len(todo)} CME pulls to make, quoted ${total:.3f}, already spent ${spent():.3f}, "
        f"cap ${TOTAL_CAP_USD:.2f}")
    return total


def pull(r, key):
    if spent() > TOTAL_CAP_USD:
        raise SystemExit(f"stopped: ${spent():.3f} spent is above the lane cap ${TOTAL_CAP_USD:.2f}")
    fd.fetch(cme_params(r), key, CME_DIR, PER_PULL_USD)


def fetch_cme(w, key, workers=6):
    todo = [r for r in w.itertuples() if not cme_file(r).exists()]
    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(lambda r: pull(r, key), todo))
    log(f"CME: {len(todo)} windows pulled, total spent ${spent():.4f}")


def fetch_binance(w):
    zips = json.loads(PROV.read_text()).get("binance_zips", {}) if PROV.exists() else {}
    for sym in sorted(w.binance.unique()):
        ws = w[w.binance == sym]
        todo = [r for r in ws.itertuples() if not (BN_DIR / sym / f"{r.anchor_ms}.parquet").exists()
                and iso(r.lo_ms)[:10] >= ARCHIVE_START]          # earlier placebo days have no Binance file; the runner counts them
        parts = {r.anchor_ms: [] for r in todo}
        days = sorted({iso(ms)[:10] for r in todo for ms in (r.lo_ms, r.hi_ms)})
        for d in days:
            df, want, nbytes = st.binance_day(sym, d)
            zips[f"{sym}/{d}"] = {"sha256": want, "bytes": nbytes}
            for r in todo:
                if d in (iso(r.lo_ms)[:10], iso(r.hi_ms)[:10]):
                    parts[r.anchor_ms].append(df[(df.t >= r.lo_ms) & (df.t <= r.hi_ms)])
            del df
        for r in todo:
            x = pd.concat(parts[r.anchor_ms], ignore_index=True).drop_duplicates("agg_id").sort_values(["t", "agg_id"], ignore_index=True)
            p = BN_DIR / sym / f"{r.anchor_ms}.parquet"
            p.parent.mkdir(parents=True, exist_ok=True)
            x.to_parquet(p, index=False)
        log(f"Binance {sym}: {len(todo)} windows")
    return zips


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def provenance(zips):
    cme = sorted(CME_DIR.glob("*.csv.zst"))
    bn = sorted(BN_DIR.rglob("*.parquet"))
    man = pd.read_csv(CME_DIR / "manifest.csv") if (CME_DIR / "manifest.csv").exists() else pd.DataFrame()
    body = {
        "folders": ["data/databento/cmelead", "data/cmelead/binance"],
        "sources": ["Databento historical API, dataset GLBX.MDP3, schema trades, CL.v.0 and NG.v.0 (continuous, volume roll); "
                    "the raw CSV+zstd files are kept",
                    "https://data.binance.vision USD-M daily aggTrades CLUSDT, NATGASUSDT (each zip checked against its "
                    ".CHECKSUM sha256; the zips are not kept, only the windows)"],
        "script": "python -I scripts/fetch_cmelead.py fetch",
        "windows": WINDOWS.relative_to(ROOT).as_posix(), "windows_sha256": sha(WINDOWS),
        "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "databento_spent_usd": round(float(man.quoted_usd.sum()), 6) if len(man) else 0.0,
        "databento_files": len(cme), "databento_bytes": sum(f.stat().st_size for f in cme),
        "binance_zips": dict(sorted(zips.items())),
        "binance_files": len(bn), "binance_bytes": sum(f.stat().st_size for f in bn),
        "file_hashes": [{"path": f.relative_to(ROOT).as_posix(), "sha256": sha(f)} for f in cme + bn],
    }
    body["combined_sha256"] = hashlib.sha256("".join(h["sha256"] for h in body["file_hashes"]).encode()).hexdigest()
    PROV.write_text(json.dumps(body, indent=1) + "\n")
    log(f"wrote {PROV.relative_to(ROOT)}: {len(cme)} CME files, {len(bn)} Binance files, ${body['databento_spent_usd']:.4f} spent")


def main(argv=None):
    cmd = (argv or sys.argv[1:] or [""])[0]
    if cmd == "windows":
        w = windows()
        LANE.mkdir(parents=True, exist_ok=True)
        w.to_csv(WINDOWS, index=False, lineterminator="\n")
        log(f"{len(w)} windows -> {WINDOWS.relative_to(ROOT)}")
        return 0
    w = pd.read_csv(WINDOWS)
    if cmd == "plan":
        plan(w, fd.read_key())
        return 0
    if cmd == "fetch":
        key = fd.read_key()
        fetch_cme(w, key)          # every pull is quoted first and refused above PER_PULL_USD; the lane stops above the cap
        zips = fetch_binance(w)
        provenance(zips)
        return 0
    if cmd == "provenance":
        provenance(json.loads(PROV.read_text()).get("binance_zips", {}) if PROV.exists() else {})
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
