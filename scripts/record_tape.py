"""Order-flow tape recorder (M264): Binance USD-M and MEXC perps' best bid/ask and trades for `COINS`, bucketed to the
second by lab/tape.py, into data/tape/. Paper only: it reads public websockets and places nothing.

Point-in-time data that no archive sells for free: the clock starts when the recorder does. Every 10 minutes it writes
part files (data/tape/_parts/<venue>/<book|trades>/<date>/); `ensure` merges a finished day's parts into
data/tape/<venue>/<book|trades>/<date>.parquet. data/tape/sessions.csv logs each connection (start, end, messages,
why it ended), so gaps are known; data/tape/status.json holds the last flush. One writer: the recorder holds
data/tape/recorder.lock.

Disk: about 34 rows a second over both venues, about 90 MB a day once merged. The recorder stops, and `ensure` will
not start it, when data/tape holds `MAX_TAPE_GB` (about five weeks) or the disk has less than `MIN_FREE_GB` free.
More needs the owner's room on disk, not a code change.

usage: python scripts/record_tape.py          ensure: start the recorder if it is not running, merge finished days
       python scripts/record_tape.py run      the recorder itself, in the foreground
       python scripts/record_tape.py status   rows and MB per venue, kind and day, and the last sessions
"""
import asyncio
import csv
import fcntl
import json
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
sys.path.insert(0, str(ROOT))
from lab import tape  # noqa: E402

OUT = ROOT / "data" / "tape"
PARTS = OUT / "_parts"
COINS = ("BTC", "ETH", "SOL", "XRP", "DOGE", "BNB", "SUI", "ADA", "LINK", "AVAX", "LTC", "TRX")
FLUSH_S = 600
MIN_FREE_GB = 2.0
MAX_TAPE_GB = 3.0
CA = "/root/.ccr/ca-bundle.crt"
BINANCE_BOOK = "wss://fstream.binance.com/public/stream?streams="      # bookTicker moved to /public in 2026
BINANCE_TRADE = "wss://fstream.binance.com/market/stream?streams="     # aggTrade to /market
MEXC = "wss://contract.mexc.com/edge"
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def free_gb():
    return shutil.disk_usage(ROOT).free / 1e9


def tape_gb(out=OUT):
    return sum(f.stat().st_size for f in out.rglob("*.parquet")) / 1e9


def full():
    """Why the recorder must not write, or ""."""
    if free_gb() < MIN_FREE_GB:
        return f"disk below {MIN_FREE_GB} GB free"
    if tape_gb() >= MAX_TAPE_GB:
        return f"data/tape reached its {MAX_TAPE_GB} GB cap"
    return ""


def utc_day(ms):
    return time.strftime("%Y-%m-%d", time.gmtime(ms / 1000))


def write_parts(frames, now_ms):
    """One parquet per (venue, kind, UTC day) of the drained rows; returns the rows written."""
    n = 0
    stamp = time.strftime("%H%M%S", time.gmtime(now_ms / 1000)) + f"-{os.getpid()}"
    for venue, pair in frames.items():
        for kind, df in zip(("book", "trades"), pair):
            if df.empty:
                continue
            for day, g in df.groupby(df.s.map(utc_day)):
                d = PARTS / venue / kind / day
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
    for d in sorted(parts.glob("*/*/*")):
        venue, kind, day = d.parts[-3:]
        if pd.Timestamp(day, tz="UTC").value // 10**6 + 86_400_000 + 1_800_000 > now_ms:
            continue
        files = sorted(d.glob("*.parquet"))
        dst = out / venue / kind / f"{day}.parquet"
        frames = ([pd.read_parquet(dst)] if dst.exists() else []) + [pd.read_parquet(f) for f in files]
        if not frames:
            d.rmdir()
            continue
        df = tape.combine(pd.concat(frames, ignore_index=True), "book" if kind == "book" else "trades")
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_suffix(".tmp")
        df.to_parquet(tmp, index=False, compression="zstd")
        if len(pd.read_parquet(tmp, columns=["s"])) != len(df):
            raise RuntimeError(f"{dst}: read-back row count differs; parts kept")
        tmp.replace(dst)
        for f in files:
            f.unlink()
        for f in d.glob(".*.tmp"):        # a part interrupted mid-write holds no row the recorder still has
            f.unlink()
        d.rmdir()
        done.append((venue, kind, day, len(df)))
    return done


class Recorder:
    def __init__(self, coins=COINS):
        self.coins = coins
        self.tape = tape.Tape()
        self.stop = asyncio.Event()
        self.msgs = {}
        self.connected = {}
        self.rows = 0
        self.why_stopped = ""
        self.ctx = ssl.create_default_context(cafile=CA) if Path(CA).exists() else ssl.create_default_context()
        sizes = {}
        try:
            from lab import mexc
            t = mexc.contracts()
            sizes = {r.symbol: float(r.contract_size) for r in t.itertuples() if r.symbol in {f"{c}_USDT" for c in coins}}
        except Exception as e:             # without contract sizes the MEXC stream cannot be converted to coins
            log(f"MEXC contract sizes unavailable ({type(e).__name__}: {e}); MEXC is not recorded")
        self.sizes = sizes

    def session(self, name, t0, n, reason):
        p = OUT / "sessions.csv"
        new = not p.exists()
        with open(p, "a", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            if new:
                w.writerow(["stream", "start_utc", "end_utc", "seconds", "messages", "ended_by"])
            w.writerow([name, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)),
                        time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), round(time.time() - t0), n, reason])

    async def stream(self, name, venue, url, subs, parse, ping=None):
        import websockets
        delay = 1.0
        while not self.stop.is_set():
            t0, n, reason = time.time(), 0, "stopped"
            try:
                async with websockets.connect(url, ssl=self.ctx, open_timeout=20, close_timeout=2, max_size=2**23) as ws:
                    for s in subs:
                        await ws.send(json.dumps(s))
                    self.tape.reset(venue)
                    self.connected[name] = True
                    keep = asyncio.create_task(self.pinger(ws, ping)) if ping else None
                    closer = asyncio.create_task(self.close_on_stop(ws))
                    try:
                        async for raw in ws:
                            n += 1
                            recv = time.time() * 1000
                            for ev in parse(json.loads(raw)):
                                if ev[0] == "book":
                                    self.tape.on_book(venue, *ev[1:7], recv, *ev[7:])
                                else:
                                    self.tape.on_trade(venue, *ev[1:])
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
    async def pinger(ws, msg, every=15):
        while True:
            await asyncio.sleep(every)
            await ws.send(json.dumps(msg))

    def flush(self, final=False):
        now = int(time.time() * 1000)
        frames = self.tape.drain(None if final else now)
        why = full()
        if why:
            self.why_stopped = f"{why}; {sum(len(b) + len(t) for b, t in frames.values())} rows not written"
            log(self.why_stopped)
            self.stop.set()
        else:
            self.rows += write_parts(frames, now)
        status = {"updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "pid": os.getpid(),
                  "coins": list(self.coins), "mexc_contracts": len(self.sizes), "rows_written": self.rows,
                  "late_events": self.tape.late, "messages": self.msgs, "connected": self.connected,
                  "free_gb": round(free_gb(), 2), "tape_gb": round(tape_gb(), 3),
                  "stopped": self.why_stopped or (final and "shutdown") or ""}
        tmp = OUT / ".status.tmp"
        tmp.write_text(json.dumps(status, indent=1) + "\n")
        tmp.replace(OUT / "status.json")

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
        low = [c.lower() + "usdt" for c in self.coins]
        jobs = [
            self.stream("binance_book", "binance", BINANCE_BOOK + "/".join(f"{s}@bookTicker" for s in low), (),
                        lambda m: tape.binance(m, "book")),
            self.stream("binance_trades", "binance", BINANCE_TRADE + "/".join(f"{s}@aggTrade" for s in low), (),
                        lambda m: tape.binance(m, "trade")),
            self.flusher(),
        ]
        if self.sizes:
            subs = [{"method": m, "param": {"symbol": s, **({"limit": 5} if m == "sub.depth.full" else {})}}
                    for s in sorted(self.sizes) for m in ("sub.depth.full", "sub.deal")]
            jobs.append(self.stream("mexc", "mexc", MEXC, subs, lambda m: tape.mexc(m, self.sizes),
                                    ping={"method": "ping"}))
        log(f"recording {len(self.coins)} coins: Binance book and trades, MEXC {len(self.sizes)} contracts")
        await asyncio.gather(*jobs)
        self.flush(final=True)
        log(f"stopped: {self.rows} rows written; {self.why_stopped or 'shutdown'}")


def lock():
    """The recorder's lock file, held for its lifetime; None when another recorder holds it."""
    OUT.mkdir(parents=True, exist_ok=True)
    f = open(OUT / "recorder.lock", "a+")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        f.close()
        return None
    return f


def run():
    held = lock()
    if held is None:
        log("another recorder holds data/tape/recorder.lock")
        return 0
    held.truncate(0)
    held.write(f"{os.getpid()}\n")
    held.flush()
    asyncio.run(Recorder().main())
    return 0


def ensure():
    for venue, kind, day, n in compact():
        log(f"merged {venue} {kind} {day}: {n:,} rows")
    held = lock()
    if held is None:
        st = OUT / "status.json"
        log("recorder running" + (f"; {json.loads(st.read_text()).get('rows_written', 0):,} rows this run"
                                 if st.exists() else ""))
        return 0
    held.close()
    why = full() or (free_gb() < MIN_FREE_GB + 0.5 and f"{free_gb():.1f} GB free, below {MIN_FREE_GB + 0.5} GB")
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
    for f in sorted(OUT.glob("*/*/*.parquet")):
        venue, kind, day = f.parts[-3], f.parts[-2], f.stem
        rows.append((venue, kind, day, len(pd.read_parquet(f, columns=["s"])), f.stat().st_size / 1e6, "daily"))
    for d in sorted(PARTS.glob("*/*/*")):
        files = list(d.glob("*.parquet"))
        rows.append((*d.parts[-3:], sum(len(pd.read_parquet(f, columns=["s"])) for f in files),
                     sum(f.stat().st_size for f in files) / 1e6, f"{len(files)} parts"))
    for r in rows:
        print(f"{r[0]:8s} {r[1]:7s} {r[2]}  {r[3]:>10,} rows  {r[4]:8.1f} MB  {r[5]}")
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
