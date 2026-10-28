"""High-rate feed recorder (M427-M429 data): BTC and ETH top of book and trades at 100 ms on Binance USDT and USDC
perps, Bybit USDT perps and Hyperliquid, into data/hft/. Public websockets only; paper only; it places nothing.

Why 100 ms: every feed reaches this container 50-500 ms after the venue's own event time (docs/DIRECTION.md, measured
2026-10-28: Binance about 55 ms, Bybit about 100 ms, Hyperliquid about 480 ms), so anything that moves faster than
that cannot be acted on from here. 100 ms buckets keep exactly the part of a cross-venue lead that is executable, at a
tenth of the rows. Each bucket with at least one update is one row holding the last quote, the number of updates, the
local-minus-event delay of that update and its offset inside the bucket; trade rows hold the buy and sell aggressor
counts, quantities and the extreme price each side printed (the trade-through price a passive order would need).
Quiet buckets have no row: forward-fill the book, treat a missing trade row as no trades. Hyperliquid's public trade
stream names both wallets of every fill; those fills are kept one row each (kind "fills", users as the feed sends
them, documented as buyer then seller and still to be checked against the side before use). Order placements and
cancels, the flow the anticipatory queue idea needs, are not on the public channels read here and are not recorded.

Point-in-time data: the clock starts when the recorder does. Every 10 minutes it writes part files
(data/hft/_parts/<book|trades|fills>/<date>/); `ensure` merges a finished day's parts into
data/hft/<book|trades|fills>/<date>.parquet. data/hft/sessions.csv logs each connection so gaps are known;
data/hft/status.json holds the last flush. One writer: the recorder holds data/hft/recorder.lock.

Disk is the binding constraint (a few GB free). The recorder stops, and `ensure` will not start it, when data/hft holds
`MAX_GB` or the disk has less than `MIN_FREE_GB` free, a floor above the tape recorder's so that the older recorders
keep writing first.

usage: python scripts/record_hft.py          ensure: start the recorder if it is not running, merge finished days
       python scripts/record_hft.py run      the recorder itself, in the foreground
       python scripts/record_hft.py status   rows and MB per kind and day, and the last sessions
"""
import asyncio
import csv
import fcntl
import json
import math
import os
import shutil
import signal
import ssl
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "hft"
PARTS = OUT / "_parts"
COINS = ("BTC", "ETH")
BUCKET_MS = 100
FLUSH_S = 600
MIN_FREE_GB = 2.5
MAX_GB = 0.6
CA = "/root/.ccr/ca-bundle.crt"
BINANCE_BOOK = "wss://fstream.binance.com/public/stream?streams="      # bookTicker moved to /public in 2026
BINANCE_TRADE = "wss://fstream.binance.com/market/stream?streams="     # aggTrade to /market
BYBIT = "wss://stream.bybit.com/v5/public/linear"
HYPERLIQUID = "wss://api.hyperliquid.xyz/ws"
QUOTES = ("USDT", "USDC")
BOOK_COLS = ["t", "v", "s", "bid", "bq", "ask", "aq", "n", "lag", "ro"]
TRADE_COLS = ["t", "v", "s", "nb", "qb", "hb", "ns", "qs", "ls", "lag"]
FILL_COLS = ["t", "s", "side", "px", "sz", "buyer", "seller", "tid", "lag"]
KINDS = {"book": (BOOK_COLS, ["t", "v", "s"]), "trades": (TRADE_COLS, ["t", "v", "s"]),
         "fills": (FILL_COLS, ["tid"])}            # frame columns, and the columns that identify a row
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def free_gb():
    return shutil.disk_usage(ROOT).free / 1e9


def hft_gb(out=OUT):
    return sum(f.stat().st_size for f in out.rglob("*.parquet")) / 1e9


def full(out=OUT):
    """Why the recorder must not write, or ""."""
    if free_gb() < MIN_FREE_GB:
        return f"disk below {MIN_FREE_GB} GB free"
    if hft_gb(out) >= MAX_GB:
        return f"data/hft reached its {MAX_GB} GB cap"
    return ""


def utc_day(ms):
    return time.strftime("%Y-%m-%d", time.gmtime(ms / 1000))


class Buckets:
    """Coalesces ticks into BUCKET_MS buckets per (venue, symbol); `drain` returns the finished ones.

    The bucket is the local receive time rounded down, so rows from different venues share one clock. A quote with a
    missing or non-positive side, or a crossed one, is dropped; a book row keeps the last valid quote of its bucket."""

    def __init__(self):
        self.open = {"book": {}, "trades": {}}          # (venue, symbol) -> the row of its current bucket
        self.done = {"book": [], "trades": []}
        self.fills = []
        self.late = 0                                   # ticks that arrived after a local clock step back

    def bucket(self, kind, key, t):
        """The open row of `key` if it is bucket t, else None after closing an older one; a newer one is late."""
        cur = self.open[kind].get(key)
        if cur is not None and t < cur[0]:
            self.late += 1
            return False
        if cur is not None and cur[0] != t:
            self.done[kind].append(self.open[kind].pop(key))
            return None
        return cur

    def on_book(self, venue, sym, bid, bq, ask, aq, ev_ms, rx_ms):
        if not (bid > 0 and ask > 0 and bq >= 0 and aq >= 0 and bid <= ask):
            return
        t = int(rx_ms // BUCKET_MS * BUCKET_MS)
        cur = self.bucket("book", (venue, sym), t)
        if cur is False:
            return
        n = cur[7] + 1 if cur is not None else 1
        lag = int(round(rx_ms - ev_ms))
        self.open["book"][(venue, sym)] = [t, venue, sym, bid, bq, ask, aq, n, lag, int(rx_ms - t)]

    def on_trade(self, venue, sym, price, qty, sell, ev_ms, rx_ms):
        if not (price > 0 and qty > 0):
            return
        t = int(rx_ms // BUCKET_MS * BUCKET_MS)
        cur = self.bucket("trades", (venue, sym), t)
        if cur is False:
            return
        if cur is None:
            cur = self.open["trades"][(venue, sym)] = [t, venue, sym, 0, 0.0, math.nan, 0, 0.0, math.nan, 0]
        if sell:
            cur[6] += 1
            cur[7] += qty
            cur[8] = price if math.isnan(cur[8]) else min(cur[8], price)
        else:
            cur[3] += 1
            cur[4] += qty
            cur[5] = price if math.isnan(cur[5]) else max(cur[5], price)
        cur[9] = int(round(rx_ms - ev_ms))

    def on_fill(self, sym, side, px, sz, buyer, seller, tid, ev_ms, rx_ms):
        if px > 0 and sz > 0:
            self.fills.append([int(ev_ms), sym, side, px, sz, buyer, seller, int(tid), int(round(rx_ms - ev_ms))])

    def drain(self, now_ms=None):
        """(book, trade, fill frames): every finished bucket and every fill; with now_ms, buckets still open at that
        time stay, and with None everything is returned. Each row is returned once."""
        cut = None if now_ms is None else int(now_ms // BUCKET_MS * BUCKET_MS)
        frames = []
        for kind, cols in (("book", BOOK_COLS), ("trades", TRADE_COLS)):
            rows, self.done[kind] = self.done[kind], []
            for key in [k for k, r in self.open[kind].items() if cut is None or r[0] < cut]:
                rows.append(self.open[kind].pop(key))
            frames.append(pd.DataFrame(sorted(rows, key=lambda r: r[0]), columns=cols))
        fills, self.fills = self.fills, []
        frames.append(pd.DataFrame(sorted(fills, key=lambda r: (r[0], r[7])), columns=FILL_COLS))
        return tuple(frames)


def binance(m, kind):
    """Events of one combined-stream message: ("book", venue, sym, bid, bq, ask, aq, ev_ms) or
    ("trade", venue, sym, price, qty, sell, ev_ms)."""
    d = m.get("data") or {}
    if kind == "book" and d.get("e") == "bookTicker":
        return [("book", "binance", d["s"], float(d["b"]), float(d["B"]), float(d["a"]), float(d["A"]),
                 d.get("E") or d["T"])]
    if kind == "trade" and d.get("e") == "aggTrade":
        return [("trade", "binance", d["s"], float(d["p"]), float(d["q"]), bool(d["m"]), d["T"])]
    return []


class BybitBook:
    """Bybit's depth-1 stream sends a snapshot and then deltas that may carry one side only; keep each side."""

    def __init__(self):
        self.q = {}

    def __call__(self, m):
        if not str(m.get("topic", "")).startswith("orderbook.1.") or "data" not in m:
            return []
        d = m["data"]
        q = self.q.setdefault(d["s"], {"b": None, "a": None})
        if m.get("type") == "snapshot":
            q["b"] = q["a"] = None
        for side in ("b", "a"):
            lv = [(float(p), float(s)) for p, s in d.get(side, [])]
            if lv:
                q[side] = lv[0] if lv[0][1] > 0 else None
        if q["b"] is None or q["a"] is None:
            return []
        return [("book", "bybit", d["s"], q["b"][0], q["b"][1], q["a"][0], q["a"][1], m["ts"])]


def hyperliquid(m):
    """bbo -> a book event; trades -> one ("fill", coin, side, px, sz, buyer, seller, tid, ev_ms) each."""
    if m.get("channel") == "trades":
        return [("fill", t["coin"], t["side"], float(t["px"]), float(t["sz"]), t["users"][0], t["users"][1], t["tid"],
                 t["time"]) for t in m["data"] if len(t.get("users") or ()) == 2]
    if m.get("channel") != "bbo":
        return []
    d = m["data"]
    bid, ask = (d.get("bbo") or [None, None])[:2]
    if not bid or not ask:
        return []
    return [("book", "hyperliquid", d["coin"], float(bid["px"]), float(bid["sz"]), float(ask["px"]), float(ask["sz"]),
             d["time"])]


def write_parts(frames, now_ms, parts=PARTS):
    """One parquet per (kind, UTC day) of the drained rows; returns the rows written."""
    n = 0
    stamp = time.strftime("%H%M%S", time.gmtime(now_ms / 1000)) + f"-{os.getpid()}"
    for kind, df in zip(KINDS, frames):
        if df.empty:
            continue
        for days, g in df.groupby(df.t // 86_400_000):
            day = utc_day(int(days) * 86_400_000)
            d = parts / kind / day
            d.mkdir(parents=True, exist_ok=True)
            tmp = d / f".{stamp}.tmp"
            g.to_parquet(tmp, index=False, compression="zstd")
            tmp.rename(d / f"{stamp}.parquet")
            n += len(g)
    return n


def compact(now_ms=None, parts=PARTS, out=OUT):
    """Merge each finished day's parts (the day ended at least 30 minutes ago) into its daily file, with any rows that
    file already holds; the parts are removed only after the daily file is read back with every merged row."""
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    done = []
    for d in sorted(parts.glob("*/*")):
        kind, day = d.parts[-2:]
        if pd.Timestamp(day, tz="UTC").value // 10**6 + 86_400_000 + 1_800_000 > now_ms:
            continue
        files = sorted(d.glob("*.parquet"))
        dst = out / kind / f"{day}.parquet"
        frames = ([pd.read_parquet(dst)] if dst.exists() else []) + [pd.read_parquet(f) for f in files]
        if not frames:
            d.rmdir()
            continue
        df = pd.concat(frames, ignore_index=True).sort_values(["t"] + KINDS[kind][1][1:], kind="stable",
                                                              ignore_index=True)
        df = df.drop_duplicates(subset=KINDS[kind][1], keep="last", ignore_index=True)
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_suffix(".tmp")
        df.to_parquet(tmp, index=False, compression="zstd")
        if len(pd.read_parquet(tmp, columns=["t"])) != len(df):
            raise RuntimeError(f"{dst}: read-back row count differs; parts kept")
        tmp.replace(dst)
        for f in files:
            f.unlink()
        for f in d.glob(".*.tmp"):        # a part interrupted mid-write holds no row the recorder still has
            f.unlink()
        d.rmdir()
        done.append((kind, day, len(df)))
    return done


class Recorder:
    def __init__(self, coins=COINS, out=OUT):
        self.coins, self.out = coins, out
        self.b = Buckets()
        self.stop = asyncio.Event()
        self.msgs, self.connected, self.rows, self.why_stopped = {}, {}, 0, ""
        self.ctx = ssl.create_default_context(cafile=CA) if Path(CA).exists() else ssl.create_default_context()

    def session(self, name, t0, n, reason):
        p = self.out / "sessions.csv"
        new = not p.exists()
        with open(p, "a", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            if new:
                w.writerow(["stream", "start_utc", "end_utc", "seconds", "messages", "ended_by"])
            w.writerow([name, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)),
                        time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), round(time.time() - t0), n, reason])

    def feed(self, ev, rx):
        getattr(self.b, "on_" + ev[0])(*ev[1:], rx)

    async def stream(self, name, url, subs, parse, ping=None):
        import websockets
        delay = 1.0
        while not self.stop.is_set():
            t0, n, reason = time.time(), 0, "stopped"
            try:
                async with websockets.connect(url, ssl=self.ctx, open_timeout=20, close_timeout=2,
                                              max_size=2**23) as ws:
                    for s in subs:
                        await ws.send(json.dumps(s))
                    self.connected[name] = True
                    keep = asyncio.create_task(self.pinger(ws, ping)) if ping else None
                    closer = asyncio.create_task(self.close_on_stop(ws))
                    try:
                        async for raw in ws:
                            n += 1
                            rx = time.time() * 1000
                            for ev in parse(json.loads(raw)):
                                self.feed(ev, rx)
                            if self.stop.is_set():
                                break
                        else:
                            reason = "stopped" if self.stop.is_set() else "closed by server"
                    finally:
                        closer.cancel()
                        if keep:
                            keep.cancel()
            except Exception as e:
                reason = f"{type(e).__name__}: {e}"[:200]
            self.connected[name] = False
            self.msgs[name] = self.msgs.get(name, 0) + n
            self.session(name, t0, n, reason)
            if self.stop.is_set():
                break
            delay = 1.0 if time.time() - t0 > 300 else min(delay * 2, 60.0)
            log(f"{name}: {reason}; reconnecting in {delay:.0f} s")
            try:
                await asyncio.wait_for(self.stop.wait(), delay)
            except asyncio.TimeoutError:
                pass

    async def close_on_stop(self, ws):
        await self.stop.wait()
        await ws.close()

    @staticmethod
    async def pinger(ws, msg, every=20):
        while True:
            await asyncio.sleep(every)
            await ws.send(json.dumps(msg))

    def flush(self, final=False):
        now = int(time.time() * 1000)
        frames = self.b.drain(None if final else now)
        why = full(self.out)
        if why:
            self.why_stopped = f"{why}; {sum(len(f) for f in frames)} rows not written"
            log(self.why_stopped)
            self.stop.set()
        else:
            self.rows += write_parts(frames, now, self.out / "_parts")
        status = {"updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "pid": os.getpid(),
                  "coins": list(self.coins), "bucket_ms": BUCKET_MS, "rows_written": self.rows,
                  "late_events": self.b.late, "messages": self.msgs, "connected": self.connected,
                  "free_gb": round(free_gb(), 2), "hft_gb": round(hft_gb(self.out), 3),
                  "stopped": self.why_stopped or (final and "shutdown") or ""}
        tmp = self.out / ".status.tmp"
        tmp.write_text(json.dumps(status, indent=1) + "\n")
        tmp.replace(self.out / "status.json")

    async def flusher(self):
        while not self.stop.is_set():
            try:
                await asyncio.wait_for(self.stop.wait(), FLUSH_S)
            except asyncio.TimeoutError:
                self.flush()

    async def main(self):
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self.stop.set)
        syms = [(c + q).lower() for c in self.coins for q in QUOTES]
        jobs = [
            self.stream("binance_book", BINANCE_BOOK + "/".join(f"{s}@bookTicker" for s in syms), (),
                        lambda m: binance(m, "book")),
            self.stream("binance_trades", BINANCE_TRADE + "/".join(f"{s}@aggTrade" for s in syms), (),
                        lambda m: binance(m, "trade")),
            self.stream("bybit", BYBIT, [{"op": "subscribe", "args": [f"orderbook.1.{c}USDT" for c in self.coins]}],
                        BybitBook(), ping={"op": "ping"}),
            self.stream("hyperliquid", HYPERLIQUID,
                        [{"method": "subscribe", "subscription": {"type": k, "coin": c}}
                         for c in self.coins for k in ("bbo", "trades")],
                        hyperliquid, ping={"method": "ping"}),
            self.flusher(),
        ]
        log(f"recording {', '.join(self.coins)} at {BUCKET_MS} ms: Binance {'/'.join(QUOTES)} book and trades, "
            f"Bybit USDT, Hyperliquid book and fills")
        await asyncio.gather(*jobs)
        self.flush(final=True)
        log(f"stopped: {self.rows} rows written; {self.why_stopped or 'shutdown'}")


def lock(out=OUT):
    """The recorder's lock file, held for its lifetime; None when another recorder holds it."""
    out.mkdir(parents=True, exist_ok=True)
    f = open(out / "recorder.lock", "a+")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        f.close()
        return None
    return f


def run():
    held = lock()
    if held is None:
        log("another recorder holds data/hft/recorder.lock")
        return 0
    held.truncate(0)
    held.write(f"{os.getpid()}\n")
    held.flush()
    asyncio.run(Recorder().main())
    return 0


def ensure():
    for kind, day, n in compact():
        log(f"merged {kind} {day}: {n:,} rows")
    held = lock()
    if held is None:
        st = OUT / "status.json"
        log("recorder running" + (f"; {json.loads(st.read_text()).get('rows_written', 0):,} rows this run"
                                 if st.exists() else ""))
        return 0
    held.close()
    why = full() or (free_gb() < MIN_FREE_GB + 0.3 and f"{free_gb():.1f} GB free, below {MIN_FREE_GB + 0.3} GB")
    if why:
        log(f"not started: {why}")
        return 0
    logf = open(OUT / "recorder.log", "a")
    subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "run"], cwd=ROOT, stdout=logf,
                     stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
    log("recorder started")
    return 0


def status():
    rows = []
    for f in sorted(OUT.glob("*/*.parquet")):
        rows.append((f.parts[-2], f.stem, len(pd.read_parquet(f, columns=["t"])), f.stat().st_size / 1e6, "daily"))
    for d in sorted(PARTS.glob("*/*")):
        files = list(d.glob("*.parquet"))
        rows.append((*d.parts[-2:], sum(len(pd.read_parquet(f, columns=["t"])) for f in files),
                     sum(f.stat().st_size for f in files) / 1e6, f"{len(files)} parts"))
    for r in rows:
        print(f"{r[0]:7s} {r[1]}  {r[2]:>10,} rows  {r[3]:8.1f} MB  {r[4]}")
    p = OUT / "sessions.csv"
    if p.exists():
        print(open(p).read().splitlines()[0])
        print("\n".join(open(p).read().splitlines()[1:][-8:]))
    st = OUT / "status.json"
    if st.exists():
        print(st.read_text())
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "ensure"
    sys.exit({"run": run, "ensure": ensure, "status": status}[cmd]())
