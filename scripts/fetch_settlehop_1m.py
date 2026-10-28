"""R356's minute bars around R354's primary hops: Binance and Lighter 1-minute bars from T - 2 h to T + 1 h.

- Binance: USD-M 1-minute klines, the public daily files of data.binance.vision, each checked against its published
  sha256 (.CHECKSUM), for every UTC day the windows touch. data/settlehop_1m/binance/<symbol>/<day>.parquet.
- Lighter: 1-minute candles from the public API (carrylane's client and its machine-wide lock), one call a hop, fields
  as scripts/fetch_venue_history.py maps them (o/h/l/c, volume v, quote volume V). Only bars that had closed when they
  were fetched are kept. data/settlehop_1m/lighter/<symbol>/<T ms>.parquet.
- docs/provenance/settlehop_1m.json: sources, the script, the time, and every file's sha256.

The hops are R354's frozen primary book (experiments/settlehop_pred_v1/results/hops.csv.gz, Binance + Lighter at
θ 0.5%). The script prints counts only; it computes no price change.
usage: python -I scripts/fetch_settlehop_1m.py [--plumbing]
"""
import argparse
import csv
import hashlib
import io
import json
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import carrylane  # noqa: E402

H, MIN, DAY = 3_600_000, 60_000, 86_400_000
HOPS = ROOT / "experiments" / "settlehop_pred_v1" / "results" / "hops.csv.gz"
BOOK = "binance+lighter th0.5%"
SYMBOLS = ROOT / "experiments" / "settlehop_v1" / "symbols.csv"
LIGHTER_IDS = ROOT / "data" / "lighter_hist" / "contracts.csv"
OUT = ROOT / "data" / "settlehop_1m"
PROV = ROOT / "docs" / "provenance" / "settlehop_1m.json"
BV = "https://data.binance.vision/data/futures/um/daily/klines/{s}/1m/{s}-1m-{d}.zip"
BEFORE, AFTER = 2 * H, H + MIN                   # the window around T: [T - 2 h, T + 1 h + 1 min)
KCOLS = ["t", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "count", "taker_buy_volume",
         "taker_buy_quote_volume", "ignore"]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def hops():
    """R354's primary hops: [(Binance symbol, Lighter symbol, Lighter market id, T ms)]."""
    h = pd.read_csv(HOPS)
    h = h[h.book == BOOK]
    lt = {r["key"]: r["lighter"] for r in csv.DictReader(open(SYMBOLS, newline=""))}
    ids = {r["symbol"]: int(r["market_id"]) for r in csv.DictReader(open(LIGHTER_IDS, newline=""))}
    return [(c, lt[c], ids[lt[c]], int(t)) for c, t in zip(h.coin, h["T"])]


def days_of(T):
    a, b = T - BEFORE, T + AFTER - 1
    return sorted({time.strftime("%Y-%m-%d", time.gmtime(x / 1000)) for x in range(a // DAY * DAY, b + 1, DAY)
                   if x <= b} | {time.strftime("%Y-%m-%d", time.gmtime(b / 1000))})


def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except Exception:  # noqa: BLE001
            if k == tries - 1:
                raise
            time.sleep(2 ** (k + 1))


def binance_day(sym, day):
    """One day's 1-minute klines, checked against the published sha256: DataFrame of the archive's columns."""
    url = BV.format(s=sym, d=day)
    blob = get(url)
    want = get(url + ".CHECKSUM").decode().split()[0]
    got = hashlib.sha256(blob).hexdigest()
    if got != want:
        raise ValueError(f"{url}: sha256 {got} != published {want}")
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        (name,) = z.namelist()
        text = z.read(name).decode()
    rows = [r for r in csv.reader(io.StringIO(text)) if r and r[0].strip().lstrip("-").isdigit()]   # drops a header
    df = pd.DataFrame(rows, columns=KCOLS[:len(rows[0])])
    out = pd.DataFrame({"t": df.t.astype("int64")})
    if out.t.iloc[0] > 10 ** 14:                                          # microseconds -> ms
        out["t"] = out.t // 1000
    for c in ("open", "high", "low", "close", "volume", "quote_volume"):
        out[c] = df[c].astype(float)
    out["count"] = df["count"].astype("int64")
    return out.drop_duplicates("t").sort_values("t", ignore_index=True), want


def lighter_window(mid, T, now):
    rows = carrylane._lighter("candles", market_id=mid, resolution="1m", start_timestamp=T - BEFORE,
                              end_timestamp=T + AFTER, count_back=0).get("c") or []
    df = pd.DataFrame({"t": [int(r["t"]) for r in rows],
                       **{k: [float(r.get(c, 0.0)) for r in rows] for k, c in (("open", "o"), ("high", "h"),
                                                                                ("low", "l"), ("close", "c"),
                                                                                ("volume", "v"),
                                                                                ("quote_volume", "V"))}})
    df = df[(df.t >= T - BEFORE) & (df.t < T + AFTER) & (df.t + MIN <= now)]
    return df.drop_duplicates("t").sort_values("t", ignore_index=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true", help="count the files and bars on disk; fetch nothing")
    a = ap.parse_args(argv)
    hs = hops()
    need = sorted({(s, d) for s, _, _, T in hs for d in days_of(T)})
    log(f"{len(hs)} hops on {len({h[0] for h in hs})} coins; {len(need)} Binance coin-days")
    if a.plumbing:
        return plumbing(hs)
    published = {}
    for s, d in need:
        p = OUT / "binance" / s / f"{d}.parquet"
        if p.exists():
            continue
        df, want = binance_day(s, d)
        p.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(p, index=False)
        published[p.relative_to(ROOT).as_posix()] = want
    log(f"Binance: {len(published)} new day files")
    now = int(time.time() * 1000)
    for s, lsym, mid, T in hs:
        p = OUT / "lighter" / lsym / f"{T}.parquet"
        if p.exists():
            continue
        df = lighter_window(mid, T, now)
        p.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(p, index=False)
    files = sorted(OUT.rglob("*.parquet"))
    old = json.loads(PROV.read_text()) if PROV.exists() else {}
    zips = {**old.get("binance_zip_sha256", {}), **published}
    PROV.write_text(json.dumps({
        "folder": "data/settlehop_1m",
        "source": {"binance": "https://data.binance.vision USD-M daily 1m klines (each zip checked against its "
                              ".CHECKSUM sha256)",
                   "lighter": "https://mainnet.zklighter.elliot.ai/api/v1/candles resolution 1m (lab.carrylane)"},
        "script": "python -I scripts/fetch_settlehop_1m.py",
        "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hops": f"{HOPS.relative_to(ROOT).as_posix()} book {BOOK!r}: {len(hs)} hops",
        "window": "Binance: whole UTC days touching [T - 2 h, T + 1 h + 1 min); Lighter: [T - 2 h, T + 1 h + 1 min)",
        "files": len(files), "bytes": sum(f.stat().st_size for f in files),
        "binance_zip_sha256": zips,
        "file_hashes": [{"path": f.relative_to(ROOT).as_posix(), "sha256": sha(f)} for f in files],
    }, indent=1) + "\n")
    log(f"wrote {PROV.relative_to(ROOT)}: {len(files)} files")
    return plumbing(hs)


def plumbing(hs):
    """Counts only: files present, bars per window, and windows missing a bar at the minutes R356 reads."""
    nb = sum(1 for _ in (OUT / "binance").rglob("*.parquet")) if (OUT / "binance").exists() else 0
    nl = sum(1 for _ in (OUT / "lighter").rglob("*.parquet")) if (OUT / "lighter").exists() else 0
    log(f"on disk: {nb} Binance day files, {nl} Lighter windows")
    short = {"binance": 0, "lighter": 0}
    for s, lsym, _, T in hs:
        pl = OUT / "lighter" / lsym / f"{T}.parquet"
        if pl.exists():
            short["lighter"] += int(len(pd.read_parquet(pl, columns=["t"])) < (BEFORE + AFTER) // MIN)
        ts = []
        for d in days_of(T):
            pb = OUT / "binance" / s / f"{d}.parquet"
            if pb.exists():
                ts += pd.read_parquet(pb, columns=["t"]).t.tolist()
        n = sum(1 for t in ts if T - BEFORE <= t < T + AFTER)
        short["binance"] += int(n < (BEFORE + AFTER) // MIN)
    log(f"windows with fewer than {(BEFORE + AFTER) // MIN} one-minute bars: {short}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
