"""Lighter's public market_stats stream for the oil perps (M462): index, mark, mid, best bid and ask, last trade, the
funding fields and open interest, as Lighter sends them (about one message a second per market). BRENTOIL's index is
documented to move from the front to the next ICE month in five daily 20% steps at 23:59 London on business days 5-9;
this recorder keeps the index and the book around those steps. WTI is recorded as a control. Paper only: the public
websocket (`?readonly=true`, no key, no login); it places nothing.

Layout: data/lighter_index/<SYMBOL>/<YYYY-MM-DD>/<HHMMSS>-<pid>.parquet every FLUSH_S, plus status.json and
sessions.csv. `t` is the receive time in microseconds, `ts` Lighter's message stamp in milliseconds. Prices are floats
parsed from Lighter's decimal strings. `kind` is 0 for a message as received and 1 for the once-a-second snapshot of
the latest message while connected (Lighter sends market_stats on change only). It stops writing under MIN_FREE_GB free or MAX_MB stored.

`record_lighter_trades.py` is a frozen input of eventlag_fwd, so this is a separate recorder that only reuses its
helpers.

usage: python scripts/record_lighter_index.py [ensure|run|status]
"""
import asyncio
import csv
import fcntl
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402
from scripts.record_lighter_trades import URL, num, ssl_context, utc_day  # noqa: E402

OUT = data.ROOT / "lighter_index"
RUN = data.ROOT / "logs"
MARKETS = {"BRENTOIL": 159, "WTI": 145}
FLUSH_S = 300
MIN_FREE_GB = 2.5
MAX_MB = 200
PING_S = 20
COLS = ["t", "ts", "index", "mark", "mid", "bid", "ask", "last", "funding_rate", "current_funding_rate",
        "funding_ts", "oi", "kind"]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


class Book:
    def __init__(self):
        self.rows = {}
        self.stat = {"n": {}, "parse_err": 0, "unknown_market": 0, "max_gap_ms": {}}
        self.last = {}
        self.latest = {}
        self.by_id = {v: k for k, v in MARKETS.items()}

    def feed(self, m, t_us):
        """One websocket message; only market_stats rows for MARKETS are kept."""
        if not str(m.get("type", "")).endswith("market_stats"):
            return
        st = m.get("market_stats")
        if not isinstance(st, dict):
            return
        for r in [st] if "market_id" in st else st.values():
            sym = self.by_id.get(int(r.get("market_id", -1)))
            if sym is None:
                self.stat["unknown_market"] += 1
                continue
            prev = self.last.get(sym)
            self.last[sym] = t_us
            if prev is not None and (t_us - prev) // 1000 > self.stat["max_gap_ms"].get(sym, 0):
                self.stat["max_gap_ms"][sym] = (t_us - prev) // 1000
            row = (t_us, int(m.get("timestamp", -1)), num(r.get("index_price")), num(r.get("mark_price")),
                   num(r.get("mid_price")), num(r.get("best_bid_price")), num(r.get("best_ask_price")),
                   num(r.get("last_trade_price")), num(r.get("funding_rate")), num(r.get("current_funding_rate")),
                   int(r.get("funding_timestamp") or -1), num(r.get("open_interest")), 0)
            self.latest[sym] = row
            self.rows.setdefault(sym, []).append(row)
            self.stat["n"][sym] = self.stat["n"].get(sym, 0) + 1

    def sample(self, t_us):
        """Lighter sends market_stats on change only: while connected, one snapshot row a second per market from the
        latest message (kind 1), so a gap in the data means a disconnect, not a quiet book."""
        for sym, row in self.latest.items():
            self.rows.setdefault(sym, []).append((t_us,) + row[1:-1] + (1,))

    def drain(self):
        rows, self.rows = self.rows, {}
        return rows


def write_parts(rows, now, out=OUT):
    n = 0
    stamp = time.strftime("%H%M%S", time.gmtime(now)) + f"-{os.getpid()}"
    for sym, r in rows.items():
        if not r:
            continue
        df = pd.DataFrame(r, columns=COLS)
        for day, g in df.groupby(df.t // 86_400_000_000, sort=False):
            d = out / sym / utc_day(int(day) * 86_400_000_000)
            d.mkdir(parents=True, exist_ok=True)
            tmp = d / f".{stamp}.tmp"
            g.reset_index(drop=True).to_parquet(tmp, index=False, compression="zstd")
            tmp.rename(d / f"{stamp}.parquet")
            n += len(g)
    return n


def used_mb(out=OUT):
    return sum(f.stat().st_size for f in out.rglob("*.parquet")) / 1e6 if out.exists() else 0.0


def full(out=OUT, free_gb=None):
    free = shutil.disk_usage(ROOT).free / 1e9 if free_gb is None else free_gb
    if free < MIN_FREE_GB:
        return f"disk below {MIN_FREE_GB} GB free"
    if used_mb(out) >= MAX_MB:
        return f"data/lighter_index reached {MAX_MB} MB"
    return ""


def load(sym, day, out=OUT):
    """All rows of one UTC day in arrival order, or None."""
    files = sorted((out / sym / day).glob("*.parquet"))
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True) if files else None


class Recorder:
    def __init__(self, out=OUT):
        self.out = out
        self.book = Book()
        self.stop = asyncio.Event()
        self.rows, self.msgs, self.connected, self.why = 0, 0, False, ""

    def session(self, t0, n, reason):
        p = self.out / "sessions.csv"
        new = not p.exists()
        with open(p, "a", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            if new:
                w.writerow(["start_utc", "end_utc", "seconds", "messages", "ended_by"])
            w.writerow([time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)),
                        time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), round(time.time() - t0), n, reason])

    async def stream(self):
        import websockets
        delay = 1.0
        while not self.stop.is_set():
            t0, n, reason = time.time(), 0, "stopped"
            try:
                async with websockets.connect(URL, ssl=ssl_context(), open_timeout=20, close_timeout=2,
                                              max_size=2**22) as ws:
                    for mid in MARKETS.values():
                        await ws.send(json.dumps({"type": "subscribe", "channel": f"market_stats/{mid}"}))
                    self.connected = True
                    closer = asyncio.create_task(self.close_on_stop(ws))
                    pinger = asyncio.create_task(self.ping(ws))
                    try:
                        async for raw in ws:
                            n += 1
                            try:
                                self.book.feed(json.loads(raw), time.time_ns() // 1000)
                            except (KeyError, ValueError, TypeError, AttributeError):
                                self.book.stat["parse_err"] += 1
                            if self.stop.is_set():
                                break
                        else:
                            reason = "stopped" if self.stop.is_set() else "closed by server"
                    finally:
                        closer.cancel()
                        pinger.cancel()
            except Exception as e:  # noqa: BLE001 - logged in sessions.csv, then reconnect
                reason = f"{type(e).__name__}: {e}"[:200]
            self.connected = False
            self.book.latest.clear()
            self.msgs += n
            self.session(t0, n, reason)
            if self.stop.is_set():
                break
            delay = 1.0 if time.time() - t0 > 300 else min(delay * 2, 60.0)
            log(f"lighter index: {reason}; reconnecting in {delay:.0f} s")
            try:
                await asyncio.wait_for(self.stop.wait(), delay)
            except asyncio.TimeoutError:
                pass

    async def ping(self, ws):
        """Lighter's application-level ping (as forward_settlelit sends); the server closes quiet sessions."""
        while True:
            await asyncio.sleep(PING_S)
            await ws.send(json.dumps({"type": "ping"}))

    async def close_on_stop(self, ws):
        await self.stop.wait()
        await ws.close()

    def flush(self, final=False):
        rows = self.book.drain()
        self.why = full(self.out)
        if self.why:
            log(f"lighter index: {self.why}; {sum(len(r) for r in rows.values())} rows not written")
            self.stop.set()
        else:
            self.rows += write_parts(rows, time.time(), self.out)
        st = self.book.stat
        status = {"updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "pid": os.getpid(),
                  "connected": self.connected, "messages": self.msgs, "rows_written": self.rows,
                  "rows_by_market": st["n"], "parse_err": st["parse_err"], "unknown_market": st["unknown_market"],
                  "max_gap_ms": st["max_gap_ms"], "stored_mb": round(used_mb(self.out), 1),
                  "stopped": self.why or (final and "shutdown") or ""}
        tmp = self.out / ".status.tmp"
        tmp.write_text(json.dumps(status, indent=1) + "\n")
        tmp.replace(self.out / "status.json")

    async def sampler(self):
        while not self.stop.is_set():
            try:
                await asyncio.wait_for(self.stop.wait(), 1.0)
            except asyncio.TimeoutError:
                if self.connected:
                    self.book.sample(time.time_ns() // 1000)

    async def flusher(self):
        while not self.stop.is_set():
            try:
                await asyncio.wait_for(self.stop.wait(), FLUSH_S)
            except asyncio.TimeoutError:
                self.flush()

    async def main(self):
        self.out.mkdir(parents=True, exist_ok=True)
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self.stop.set)
        log(f"lighter index: recording {'/'.join(MARKETS)} market_stats")
        await asyncio.gather(self.stream(), self.flusher(), self.sampler())
        self.flush(final=True)
        log(f"lighter index: stopped; {self.rows} rows written")


def lock():
    RUN.mkdir(parents=True, exist_ok=True)
    f = open(RUN / "lighter_index.lock", "a+")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        f.close()
        return None
    return f


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    cmd = (argv or ["ensure"])[0]
    if cmd == "status":
        st = OUT / "status.json"
        print(st.read_text() if st.exists() else "no status yet")
        return 0
    if cmd == "ensure":
        held = lock()
        if held is None:
            log("lighter index: recorder running")
            return 0
        held.close()
        why = full()
        if why:
            log(f"lighter index: not started: {why}")
            return 0
        with open(RUN / "lighter_index.log", "a") as f:
            subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "run"], cwd=ROOT, stdout=f,
                             stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
        log("lighter index: recorder started")
        return 0
    held = lock()
    if held is None:
        log("lighter index: another recorder holds data/logs/lighter_index.lock")
        return 1
    held.truncate(0)
    held.write(f"{os.getpid()}\n")
    held.flush()
    asyncio.run(Recorder().main())
    return 0


if __name__ == "__main__":
    sys.exit(main())
