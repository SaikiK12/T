"""Hourly on-chain pool prices next to the MEXC perp price of the same coin, for M288 (DEX-CEX gap; the prop trader's
"on-chain AMMs against exchange futures", docs/VENUE_STRUCTURE.md). Public DexScreener and MEXC endpoints, no keys.
Paper only. The free history route (GeckoTerminal) answers 429 from this machine, so the clock starts here.

Two steps:
- `map` (weekly; the hourly run starts it in the background once the map is a week old): for every MEXC USDT perp,
  search DexScreener by the base symbol (1000PEPE -> PEPE, x1000; then "$WIF"-style when the plain search finds
  nothing) and keep, among pools whose base token has that symbol (letters and digits only, any case), at least
  USD 50k of liquidity and USD 10k of 24 h volume, and a USD price within 1% of the perp's fair price at the
  multiplier (3% when none is that close), the one with the most 24 h volume. A symbol match alone is not enough:
  impostor tokens share tickers, and their prices are far off. Volume ranks better than liquidity, which some pools
  inflate (a Solana "AERO" pool showed USD 883M against the real Base pools' few million). Written to
  data/recorders/dex_prices/map.csv with the route (open: the coin has a Binance perp; reserved: MEXC-only,
  docs/GATES.md).
- `run` (a daemon; the default `ensure`, called hourly from forward_all.sh, starts it when none holds its lock): every
  5 minutes, a snapshot of every mapped pool (30 pairs per request) and, in the same second, MEXC's ticker for the
  perp. An AMM pool's gap to the perp closes in minutes, so an hourly snapshot would see little of it. The snapshots
  of one UTC hour go to data/recorders/dex_prices/<YYYY-MM-DD>/<HH>.parquet.part, which is renamed to .parquet when
  the hour ends (the digest skips .part files, so each hour is digested once, sealed). Lock, log and status are in
  data/logs/dex_prices.*. Data collection only.

usage: python scripts/record_dex_prices.py [ensure|run|once|status|map]
"""
import fcntl
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, mexc  # noqa: E402
from scripts.squeeze_events import binance_perp  # noqa: E402

OUT = data.ROOT / "recorders" / "dex_prices"
DS = "https://api.dexscreener.com/latest/dex"
MIN_LIQ_USD = 50_000
MIN_VOL_USD = 10_000
GAPS = (0.01, 0.03)                         # price tiers: a pool within 1% of the perp beats a busier one at 1-3%
PACE_S = 0.25                                # DexScreener allows 300 requests a minute on these endpoints
MAP_DAYS = 7                                 # map age that starts a rebuild; a rebuild takes 10-20 minutes
POLL_S = 300
RUN = data.ROOT / "logs"                     # lock, log and status, outside the digested folder
COLS = ["ts", "symbol", "base", "mult", "route", "chain", "dex", "pair", "token", "price_usd", "liquidity_usd",
        "vol_m5", "vol_h1", "vol_h24", "buys_h1", "sells_h1", "change_m5", "change_h1", "mexc_fair", "mexc_last",
        "mexc_bid", "mexc_ask", "mexc_ms"]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def http(url):
    req = urllib.request.Request(url, headers={"User-Agent": "lab/1", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def split(symbol):
    """('PEPE', 1000) from 1000PEPE_USDT; ('BTC', 1) from BTC_USDT."""
    base = symbol[:-5]
    m = re.match(r"^(10+)([A-Z].*)$", base)
    return (m.group(2), int(m.group(1))) if m else (base, 1)


def norm(sym):
    return re.sub(r"[^A-Z0-9]", "", str(sym).upper())


def best_pool(pairs, base, mult, fair):
    """The most traded pair whose base token is `base`, deep and active enough and priced within the first GAPS tier
    that has one, or None."""
    ok = []
    for p in pairs or []:
        liq = (p.get("liquidity") or {}).get("usd") or 0
        vol = (p.get("volume") or {}).get("h24") or 0
        try:
            px = float(p.get("priceUsd") or "nan") * mult
        except ValueError:
            continue
        if norm((p.get("baseToken") or {}).get("symbol")) == norm(base) and liq >= MIN_LIQ_USD \
                and vol >= MIN_VOL_USD and fair > 0:
            ok.append((abs(px / fair - 1), vol, p))
    for gap in GAPS:
        tier = [x for x in ok if x[0] <= gap]
        if tier:
            return max(tier, key=lambda x: x[1])[2]
    return None


def build_map(get=http, tick=None, pace=PACE_S):
    tick = tick if tick is not None else pd.DataFrame(mexc.get("ticker"))
    tick = tick[tick.symbol.str.endswith("_USDT") & (tick.fairPrice.astype(float) > 0)]
    perps = {p.stem for p in (data.ROOT / "klines_1h").glob("*.parquet")}
    rows = []
    for sym, fair in zip(tick.symbol, tick.fairPrice.astype(float)):
        base, mult = split(sym)
        p = None
        for q in (base, "$" + base):
            try:
                p = best_pool(get(f"{DS}/search?q={urllib.parse.quote(q)}").get("pairs"), base, mult, fair)
            except Exception as e:  # noqa: BLE001 - one symbol failing does not stop the map
                log(f"dex map: {sym} ({q}) failed: {e}")
            time.sleep(pace)
            if p is not None:
                break
        if p is None:
            continue
        rows.append({"symbol": sym, "base": base, "mult": mult,
                     "route": "open" if binance_perp(sym[:-5], perps) else "reserved", "chain": p["chainId"],
                     "dex": p.get("dexId"), "pair": p["pairAddress"], "token": p["baseToken"]["address"],
                     "liquidity_usd": p["liquidity"]["usd"], "gap_at_map": float(p["priceUsd"]) * mult / fair - 1})
    return pd.DataFrame(rows)


def snapshot(mp, get=http, tick=None, pace=PACE_S):
    ts = int(time.time() * 1000)
    tick = tick if tick is not None else pd.DataFrame(mexc.get("ticker"))
    t = tick.set_index("symbol")
    rows = []
    for chain, g in mp.groupby("chain"):
        for i in range(0, len(g), 30):
            part = g.iloc[i:i + 30]
            try:
                pairs = get(f"{DS}/pairs/{chain}/{','.join(part.pair)}").get("pairs") or []
            except Exception as e:  # noqa: BLE001
                log(f"dex prices: {chain} batch failed: {e}")
                continue
            finally:
                time.sleep(pace)
            by = {p["pairAddress"].lower(): p for p in pairs}
            for r in part.itertuples():
                p = by.get(r.pair.lower())
                if p is None or r.symbol not in t.index:
                    continue
                m = t.loc[r.symbol]
                v, tx, ch = p.get("volume") or {}, (p.get("txns") or {}).get("h1") or {}, p.get("priceChange") or {}
                rows.append({"ts": ts, "symbol": r.symbol, "base": r.base, "mult": r.mult, "route": r.route,
                             "chain": chain, "dex": p.get("dexId"), "pair": r.pair, "token": r.token,
                             "price_usd": float(p.get("priceUsd") or "nan"),
                             "liquidity_usd": (p.get("liquidity") or {}).get("usd"), "vol_m5": v.get("m5"),
                             "vol_h1": v.get("h1"), "vol_h24": v.get("h24"), "buys_h1": tx.get("buys"),
                             "sells_h1": tx.get("sells"), "change_m5": ch.get("m5"), "change_h1": ch.get("h1"),
                             "mexc_fair": float(m.fairPrice), "mexc_last": float(m.lastPrice),
                             "mexc_bid": float(m.bid1), "mexc_ask": float(m.ask1), "mexc_ms": int(m.timestamp)})
    return pd.DataFrame(rows, columns=COLS)


def refresh_if_stale(mp_path, now=None, popen=subprocess.Popen):
    """Start one background rebuild of a map older than MAP_DAYS; the snapshot keeps using the old map meanwhile."""
    now = time.time() if now is None else now
    lock = mp_path.with_name("map.lock")
    if not mp_path.exists() or now - mp_path.stat().st_mtime < MAP_DAYS * 86400 \
            or (lock.exists() and now - lock.stat().st_mtime < 3 * 3600):
        return None
    lock.touch()
    log_path = ROOT / "experiments" / "recorders" / "tick.log"     # not next to the map: the digest reads that folder
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a") as f:
        return popen([sys.executable, str(Path(__file__).resolve()), "map"], cwd=ROOT, stdout=f,
                     stderr=subprocess.STDOUT, start_new_session=True)


def hour_path(ts_s, out=OUT):
    t = time.gmtime(ts_s)
    return out / time.strftime("%Y-%m-%d", t) / f"{time.strftime('%H', t)}.parquet"


def _write(df, path):
    tmp = path.with_name(path.name + ".w.part")
    df.to_parquet(tmp, index=False)
    tmp.replace(path)


def add(df, ts_s, out=OUT):
    """Append one snapshot to its hour's .part file."""
    part = hour_path(ts_s, out).with_name(hour_path(ts_s, out).name + ".part")
    part.parent.mkdir(parents=True, exist_ok=True)
    _write(pd.concat([pd.read_parquet(part), df], ignore_index=True) if part.exists() else df, part)
    return part


def seal(now_s, out=OUT):
    """Rename the .part file of every hour that has ended; returns the sealed paths."""
    cur, done = hour_path(now_s, out), []
    for part in sorted(out.glob("*/*.parquet.part")):
        final = part.with_name(part.name[:-len(".part")])
        if final == cur:
            continue
        if final.exists():                                  # an hour written before the daemon: keep both
            _write(pd.concat([pd.read_parquet(final), pd.read_parquet(part)], ignore_index=True), final)
            part.unlink()
        else:
            part.replace(final)
        done.append(final)
    return done


def run(stop, out=OUT, get=http, poll_s=POLL_S, status=None):
    mp_path, mp, seen = out / "map.csv", None, None
    while not stop.is_set():
        t0 = time.time()
        try:
            for p in seal(t0, out):
                log(f"dex prices: sealed {p.relative_to(out)} ({len(pd.read_parquet(p))} rows)")
            if mp_path.exists() and mp_path.stat().st_mtime != seen:
                seen, mp = mp_path.stat().st_mtime, pd.read_csv(mp_path)
            if mp is None:
                log("dex prices: no map yet (run with `map`)")
            else:
                refresh_if_stale(mp_path)
                df = snapshot(mp, get=get)
                if len(df):
                    add(df, t0, out)
                if status:
                    tmp = status.with_name(status.name + ".tmp")
                    tmp.write_text(json.dumps({"updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                               "pid": os.getpid(), "poll_s": poll_s, "pools_mapped": len(mp),
                                               "pools_read": len(df)}))
                    tmp.replace(status)
        except Exception as e:  # noqa: BLE001 - a bad poll waits for the next one
            log(f"dex prices: poll failed: {e}")
        stop.wait(max(1.0, poll_s - (time.time() - t0)))


def lock():
    RUN.mkdir(parents=True, exist_ok=True)
    f = open(RUN / "dex_prices.lock", "a+")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        f.close()
        return None
    return f


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    cmd = (argv or ["ensure"])[0]
    OUT.mkdir(parents=True, exist_ok=True)
    mp_path = OUT / "map.csv"
    if cmd == "map":
        try:
            mp = build_map()
            tmp = mp_path.with_name("map.csv.part")
            mp.to_csv(tmp, index=False)
            tmp.replace(mp_path)
        finally:
            mp_path.with_name("map.lock").unlink(missing_ok=True)
        log(f"dex map: {len(mp)} perps mapped ({(mp.route == 'open').sum()} open) -> {mp_path.relative_to(ROOT)}")
        return 0
    if cmd == "status":
        st = RUN / "dex_prices_status.json"
        print(st.read_text() if st.exists() else "no status yet")
        return 0
    if cmd == "ensure":
        held = lock()
        if held is None:
            log("dex prices: recorder running")
            return 0
        held.close()
        with open(RUN / "dex_prices.log", "a") as f:
            subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "run"], cwd=ROOT, stdout=f,
                             stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
        log("dex prices: recorder started")
        return 0
    held = lock()
    if held is None:
        log("dex prices: another recorder holds data/logs/dex_prices.lock")
        return 1
    if cmd == "once":
        df = snapshot(pd.read_csv(mp_path))
        print(df.describe().T.to_string() if len(df) else "nothing read")
        return 0
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    log(f"dex prices: recording every {POLL_S} s")
    run(stop, status=RUN / "dex_prices_status.json")
    log("dex prices: stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
