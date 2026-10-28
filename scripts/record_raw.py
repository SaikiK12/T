"""Raw-event recorder (M430-M432 data): every Binance USDT/USDC perp top-of-book update and trade, Binance's RPI depth
near the touch, and Bybit's depth-1 stream, one row per message as it reached this container, into data/rawtape/.
Public websockets only; paper only; it places nothing. It runs beside record_hft.py (R367's 100 ms tape), never in
its place, and writes to its own folder.

What it keeps that the 100 ms tape throws away (docs/DIRECTION.md, 2026-10-28 review):
- every update in arrival order, not the last one of a bucket (a lead of 300-1000 ms spans many 10 ms quote changes);
- both exchange stamps, never merged into one lag: Binance T (matching engine) and E (publication) on book and trade
  rows, Bybit cts (matching engine) and ts (publication). `dE` = E - T and `dc` = ts - cts measure the exchange side
  and need no synchronised clocks; local minus E mixes network, local processing and the local clock's offset;
- the local receive time as wall-clock microseconds `t` and `off` = wall minus monotonic microseconds, so the monotonic
  receive time is `t - off` (a jump of `off` is a wall-clock step); rows stay in arrival order;
- Binance aggTrade `nq` (quantity without Retail Price Improvement orders) next to `q`: q - nq is the RPI part;
- Binance `rpiDepth@500ms` diffs for levels within `RPI_BAND_BP` of the same symbol's bookTicker mid (rows `rpilv`,
  one summary row per message in `rpimsg`); that stream includes RPI liquidity and bookTicker does not;
- a websocket ping round trip per connection every 30 s (`rtt`) and a wall/monotonic anchor every second (`clock`).

Layout: data/rawtape/_parts/<kind>/<symbol>/<date>/<stamp>.parquet every FLUSH_S; `ensure` merges a finished day into
data/rawtape/<kind>/<symbol>/<date>.parquet. One file per (kind, symbol) so delta encoding sees one price series.
Integers throughout: prices in hundredths, sizes in thousandths, times in ms or microseconds; `decode` gives floats.
`load(kind, symbol, day)` returns a finished day. Symbols: Binance BTCUSDT ETHUSDT BTCUSDC ETHUSDC, Bybit BTCUSDT
ETHUSDT (kinds "bbo", "trade", "rpimsg", "rpilv" are Binance, "bybit" is Bybit, "clock" and "rtt" use the symbol "all").

Disk is the binding constraint. The recorder stops, and `ensure` will not start it, when data/rawtape holds `MAX_GB`
or the disk has less than `MIN_FREE_GB` free (the same floor as record_hft.py, so the older recorders keep writing
first). `HOURS` limits the market rows to a fixed UTC window chosen before any outcome was read (13:00-17:00, the
busiest hours); the sockets stay open and the `clock` and `rtt` rows run all day.
data/rawtape/status.json holds the last flush with row counts, message gaps, repeated or backwards update ids and
the lossy-rounding counters; data/rawtape/sessions.csv logs each connection.

usage: python scripts/record_raw.py          ensure: start the recorder if it is not running, merge finished days
       python scripts/record_raw.py run      the recorder itself, in the foreground
       python scripts/record_raw.py status   rows and MB per kind and day, and the last sessions
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
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "rawtape"
FLUSH_S = 300
MIN_FREE_GB = 2.5
MAX_GB = 1.2
HOURS = (13, 17)                  # None records all day; (start, end) UTC hours record start <= hour < end
RPI_BAND_BP = 3.0                 # rpiDepth levels kept within this many bp of the same symbol's bookTicker mid
RPI_LEVELS = ("BTCUSDC", "ETHUSDC")     # symbols whose near-touch RPI levels are stored (every symbol gets rpimsg rows)
RTT_EVERY_S = 30
CA = "/root/.ccr/ca-bundle.crt"
BINANCE_PUBLIC = "wss://fstream.binance.com/public/stream?streams="    # bookTicker and rpiDepth
BINANCE_MARKET = "wss://fstream.binance.com/market/stream?streams="    # aggTrade
BYBIT = "wss://stream.bybit.com/v5/public/linear"
BSYMS = ("BTCUSDT", "ETHUSDT", "BTCUSDC", "ETHUSDC")
YSYMS = ("BTCUSDT", "ETHUSDT")
PX, SZ = 100, 1000                # prices in hundredths, sizes in thousandths of a coin
COLS = {
    "bbo": ["t", "off", "u", "T", "dE", "bid", "bq", "sp", "aq"],
    "bybit": ["t", "off", "u", "seq", "ts", "dc", "fl", "bid", "bq", "sp", "aq"],
    "trade": ["t", "off", "a", "T", "dE", "p", "q", "nq", "f", "n", "m"],
    "rpimsg": ["t", "off", "U", "u", "pu", "T", "dE", "nb", "na", "nk"],
    "rpilv": ["t", "sd", "px", "qty"],
    "clock": ["t", "mono"],
    "rtt": ["t", "c", "us"],
}
# columns whose steps are small: delta-encoded
DELTA = {"t", "T", "ts", "u", "U", "pu", "seq", "a", "f", "bid", "bq", "aq", "px", "mono"}
RTT_CONN = {"binance_public": 0, "binance_market": 1, "bybit": 2}
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def free_gb():
    return shutil.disk_usage(ROOT).free / 1e9


def used_gb(out=OUT):
    return sum(f.stat().st_size for f in out.rglob("*.parquet")) / 1e9


def full(out=OUT):
    """Why the recorder must not write, or ""."""
    if free_gb() < MIN_FREE_GB:
        return f"disk below {MIN_FREE_GB} GB free"
    if used_gb(out) >= MAX_GB:
        return f"data/rawtape reached its {MAX_GB} GB cap"
    return ""


def utc_day(us):
    return time.strftime("%Y-%m-%d", time.gmtime(us / 1e6))


def in_window(wall_ns, hours=HOURS):
    if hours is None:
        return True
    h = wall_ns // 3_600_000_000_000 % 24
    a, b = hours
    return a <= h < b if a < b else (h >= a or h < b)


def ssl_context():
    """The agent proxy's CA bundle when this user can read it, else the system default (CI runs as another user)."""
    try:
        if Path(CA).exists():
            return ssl.create_default_context(cafile=CA)
    except OSError:
        pass
    return ssl.create_default_context()


def px(x):
    return int(round(float(x) * PX))


def sz(x):
    return int(round(float(x) * SZ))


class Tape:
    """Rows per (kind, symbol) in arrival order, plus the checks that say whether the feed was clean."""

    def __init__(self):
        self.rows = {}
        self.mid = {}
        self.last = {}
        self.stat = {"lossy": 0, "bad_book": 0, "u_back": {}, "seq_back": 0, "rpi_nomid": 0, "max_gap_ms": {},
                     "n": {}, "q_ne_nq": 0, "trades": 0, "no_nq": 0, "parse_err": 0}

    def put(self, kind, sym, row):
        self.rows.setdefault((kind, sym), []).append(row)
        k = f"{kind}:{sym}"
        self.stat["n"][k] = self.stat["n"].get(k, 0) + 1

    def seen(self, key, t_us):
        """Largest gap between two messages of one stream, in ms."""
        prev = self.last.get(key)
        self.last[key] = t_us
        if prev is not None:
            g = (t_us - prev) // 1000
            if g > self.stat["max_gap_ms"].get(key, 0):
                self.stat["max_gap_ms"][key] = g

    def lossy(self, x, scale):
        if abs(float(x) * scale - round(float(x) * scale)) > 1e-6:
            self.stat["lossy"] += 1

    def u_check(self, key, u):
        prev = self.last.get(("u", key))
        if prev is not None and u <= prev:
            self.stat["u_back"][key] = self.stat["u_back"].get(key, 0) + 1
        self.last[("u", key)] = u

    def binance(self, m, t, off):
        d = m.get("data") or {}
        e, s = d.get("e"), d.get("s")
        if s not in BSYMS:
            return
        if e == "bookTicker":
            bid, ask = px(d["b"]), px(d["a"])
            bq, aq = sz(d["B"]), sz(d["A"])
            if not (bid > 0 and ask >= bid and bq >= 0 and aq >= 0):
                self.stat["bad_book"] += 1
                return
            for v, sc in ((d["b"], PX), (d["a"], PX), (d["B"], SZ), (d["A"], SZ)):
                self.lossy(v, sc)
            self.mid[s] = (bid + ask) / 2 / PX
            self.u_check(("bbo", s), d["u"])
            self.seen(("bbo", s), t)
            self.put("bbo", s, (t, off, d["u"], d["T"], d["E"] - d["T"], bid, bq, ask - bid, aq))
        elif e == "aggTrade":
            q = sz(d["q"])
            nq = sz(d["nq"]) if "nq" in d else -1             # -1: the message carries no RPI split
            self.stat["trades"] += 1
            self.stat["no_nq"] += nq < 0
            self.stat["q_ne_nq"] += nq >= 0 and q != nq
            self.lossy(d["p"], PX)
            self.lossy(d["q"], SZ)
            self.seen(("trade", s), t)
            self.put("trade", s, (t, off, d["a"], d["T"], d["E"] - d["T"], px(d["p"]), q, nq, d["f"],
                                  d["l"] - d["f"] + 1, int(bool(d["m"]))))
        elif e == "depthUpdate":
            mid = self.mid.get(s)
            nk = -1
            if mid is None:
                self.stat["rpi_nomid"] += 1
            else:
                nk = 0
                for sd, side in ((0, d["b"]), (1, d["a"])):
                    for p, q in (side if s in RPI_LEVELS else ()):
                        if abs(float(p) - mid) / mid * 1e4 <= RPI_BAND_BP:
                            self.put("rpilv", s, (t, sd, px(p), sz(q)))
                            nk += 1
            self.put("rpimsg", s, (t, off, d["U"], d["u"], d["pu"], d["T"], d["E"] - d["T"], len(d["b"]),
                                   len(d["a"]), nk))

    def bybit(self, m, t, off):
        topic = str(m.get("topic", ""))
        if not topic.startswith("orderbook.1.") or "data" not in m:
            return
        d = m["data"]
        s = d["s"]
        if s not in YSYMS:
            return
        q = self.last.setdefault(("ybook", s), {"b": None, "a": None})
        fl = 4 if m.get("type") == "snapshot" else 0
        if fl:
            q["b"] = q["a"] = None
        for side, bit in (("b", 1), ("a", 2)):
            lv = [(px(p), sz(z)) for p, z in d.get(side, [])]
            if lv:
                fl |= bit
                q[side] = lv[0] if lv[0][1] > 0 else None
        seq = d.get("seq", 0)
        prev = self.last.get(("seq", s))
        if prev is not None and seq <= prev and not fl & 4:
            self.stat["seq_back"] += 1
        self.last[("seq", s)] = seq
        if q["b"] is None or q["a"] is None or q["b"][0] > q["a"][0]:
            return
        self.seen(("bybit", s), t)
        dc = m["ts"] - m["cts"] if "cts" in m else -1
        self.put("bybit", s, (t, off, d["u"], seq, m["ts"], dc, fl, q["b"][0], q["b"][1], q["a"][0] - q["b"][0],
                              q["a"][1]))

    def drain(self):
        rows, self.rows = self.rows, {}
        return rows


def frame(kind, rows):
    df = pd.DataFrame(rows, columns=COLS[kind], dtype="int64")
    for c in ("off", "dE", "dc", "fl", "n", "m", "sd", "nb", "na", "nk", "sp", "c"):
        if c in df:
            df[c] = df[c].astype("int32")
    return df


def parquet_args(cols):
    return dict(compression="zstd", compression_level=9, use_dictionary=[c for c in cols if c not in DELTA],
                column_encoding={c: "DELTA_BINARY_PACKED" for c in cols if c in DELTA})


def save(df, path):
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), path, **parquet_args(list(df.columns)))


def write_parts(rows, now, parts):
    """One parquet per (kind, symbol, UTC day) of the drained rows, in arrival order; returns the rows written."""
    n = 0
    stamp = time.strftime("%H%M%S", time.gmtime(now)) + f"-{os.getpid()}"
    for (kind, sym), r in rows.items():
        if not r:
            continue
        df = frame(kind, r)
        for days, g in df.groupby(df.t // 86_400_000_000, sort=False):
            d = parts / kind / sym / utc_day(int(days) * 86_400_000_000)
            d.mkdir(parents=True, exist_ok=True)
            tmp = d / f".{stamp}.tmp"
            save(g.reset_index(drop=True), tmp)
            tmp.rename(d / f"{stamp}.parquet")
            n += len(g)
    return n


def compact(now=None, parts=None, out=OUT):
    """Merge each finished day's parts (the day ended at least 30 minutes ago) in file order into the daily file, after
    any rows it already holds; the parts are removed only after the daily file is read back with every row."""
    parts = parts if parts is not None else out / "_parts"
    now = now if now is not None else time.time()
    done = []
    for d in sorted(parts.glob("*/*/*")):
        kind, sym, day = d.parts[-3:]
        if pd.Timestamp(day, tz="UTC").timestamp() + 86_400 + 1_800 > now:
            continue
        files = sorted(d.glob("*.parquet"))
        dst = out / kind / sym / f"{day}.parquet"
        if not files:
            for f in d.glob(".*.tmp"):
                f.unlink()
            d.rmdir()
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_suffix(".tmp")
        n, writer = 0, None
        try:                                   # one part in memory at a time: a busy day holds tens of millions of rows
            for f in ([dst] if dst.exists() else []) + files:
                tb = pq.read_table(f)
                if writer is None:
                    writer = pq.ParquetWriter(tmp, tb.schema, **parquet_args(tb.schema.names))
                writer.write_table(tb)
                n += tb.num_rows
        finally:
            if writer is not None:
                writer.close()
        if pq.ParquetFile(tmp).metadata.num_rows != n:
            raise RuntimeError(f"{dst}: read-back row count differs; parts kept")
        tmp.replace(dst)
        for f in files:
            f.unlink()
        for f in d.glob(".*.tmp"):
            f.unlink()
        d.rmdir()
        done.append((kind, sym, day, n))
    return done


def load(kind, sym, day, out=OUT):
    """One finished day, rows in arrival order, as integers (see the module header), or None."""
    p = out / kind / sym / f"{day}.parquet"
    return pd.read_parquet(p) if p.exists() else None


def decode(df, kind):
    """Floats and clocks: prices, sizes in coins, `mono_us` = t - off, `ask` for the book kinds."""
    df = df.copy()
    if "off" in df:
        df["mono_us"] = df.t - df.off
    for c in ("bid", "p", "px"):
        if c in df:
            df[c] = df[c] / PX
    if "sp" in df:
        df["ask"] = df.bid + df.sp / PX
    for c in ("bq", "aq", "q", "nq", "qty"):
        if c in df:
            df[c] = df[c] / SZ
    if "nq" in df:
        df.loc[df.nq < 0, "nq"] = float("nan")
    if kind == "trade":
        df["rpi_q"] = (df.q - df.nq).clip(lower=0).where(df.nq >= 0)
    return df


class Recorder:
    def __init__(self, out=OUT, hours=HOURS):
        self.out, self.hours = out, hours
        self.tape = Tape()
        self.stop = asyncio.Event()
        self.msgs, self.connected, self.rows, self.why_stopped = {}, {}, 0, ""

    def session(self, name, t0, n, reason):
        p = self.out / "sessions.csv"
        new = not p.exists()
        with open(p, "a", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            if new:
                w.writerow(["stream", "start_utc", "end_utc", "seconds", "messages", "ended_by"])
            w.writerow([name, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)),
                        time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), round(time.time() - t0), n, reason])

    async def stream(self, name, url, subs, handle, beat=None):
        import websockets
        delay = 1.0
        while not self.stop.is_set():
            t0, n, reason = time.time(), 0, "stopped"
            try:
                async with websockets.connect(url, ssl=ssl_context(), open_timeout=20, close_timeout=2,
                                              max_size=2**23) as ws:
                    for s in subs:
                        await ws.send(json.dumps(s))
                    self.connected[name] = True
                    tasks = [asyncio.create_task(self.pinger(ws, name, beat)),
                             asyncio.create_task(self.close_on_stop(ws))]
                    try:
                        async for raw in ws:
                            n += 1
                            w, mo = time.time_ns(), time.monotonic_ns()
                            if in_window(w, self.hours):
                                t = w // 1000
                                try:
                                    handle(json.loads(raw), t, t - mo // 1000)
                                except (KeyError, ValueError, TypeError):
                                    self.tape.stat["parse_err"] += 1
                            if self.stop.is_set():
                                break
                        else:
                            reason = "stopped" if self.stop.is_set() else "closed by server"
                    finally:
                        for tk in tasks:
                            tk.cancel()
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

    async def pinger(self, ws, name, beat):
        """Protocol ping round trips for the `rtt` rows, and the application heartbeat Bybit asks for."""
        elapsed = 0
        while True:
            await asyncio.sleep(10)
            elapsed += 10
            if beat and elapsed % 20 == 0:
                await ws.send(json.dumps(beat))
            if elapsed % RTT_EVERY_S == 0:
                p0 = time.perf_counter()
                await (await ws.ping())
                us = int((time.perf_counter() - p0) * 1e6)
                self.tape.put("rtt", "all", (time.time_ns() // 1000, RTT_CONN[name], us))

    async def clock(self):
        while not self.stop.is_set():
            self.tape.put("clock", "all", (time.time_ns() // 1000, time.monotonic_ns() // 1000))
            try:
                await asyncio.wait_for(self.stop.wait(), 1.0)
            except asyncio.TimeoutError:
                pass

    def flush(self, final=False):
        now = time.time()
        rows = self.tape.drain()
        why = full(self.out)
        if why:
            self.why_stopped = f"{why}; {sum(len(r) for r in rows.values())} rows not written"
            log(self.why_stopped)
            self.stop.set()
        else:
            self.rows += write_parts(rows, now, self.out / "_parts")
        st = self.tape.stat
        status = {"updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "pid": os.getpid(),
                  "hours": self.hours, "rows_written": self.rows, "messages": self.msgs,
                  "connected": self.connected, "rows_by_stream": st["n"], "max_gap_ms": {
                      f"{k[0]}:{k[1]}": v for k, v in st["max_gap_ms"].items()},
                  "u_back": {f"{k[0]}:{k[1]}": v for k, v in st["u_back"].items()}, "seq_back": st["seq_back"],
                  "bad_book": st["bad_book"], "lossy": st["lossy"], "rpi_nomid": st["rpi_nomid"],
                  "trades": st["trades"], "trades_with_rpi": st["q_ne_nq"], "trades_no_nq": st["no_nq"],
                  "parse_err": st["parse_err"], "free_gb": round(free_gb(), 2),
                  "rawtape_gb": round(used_gb(self.out), 3),
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
        syms = [s.lower() for s in BSYMS]
        jobs = [
            self.stream("binance_public", BINANCE_PUBLIC + "/".join(
                [f"{s}@bookTicker" for s in syms] + [f"{s}@rpiDepth@500ms" for s in syms]), (), self.tape.binance),
            self.stream("binance_market", BINANCE_MARKET + "/".join(f"{s}@aggTrade" for s in syms), (),
                        self.tape.binance),
            self.stream("bybit", BYBIT, [{"op": "subscribe", "args": [f"orderbook.1.{s}" for s in YSYMS]}],
                        self.tape.bybit, beat={"op": "ping"}),
            self.clock(),
            self.flusher(),
        ]
        log(f"recording raw events: Binance {'/'.join(BSYMS)} book, trades (nq), rpiDepth within {RPI_BAND_BP} bp on "
            f"{'/'.join(RPI_LEVELS)}; Bybit {'/'.join(YSYMS)}; hours {self.hours or 'all'}")
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


def parse_hours(arg):
    a, b = arg.split("-")
    return int(a), int(b)


def run(argv=()):
    hours = parse_hours(argv[0]) if argv else HOURS
    held = lock()
    if held is None:
        log("another recorder holds data/rawtape/recorder.lock")
        return 0
    held.truncate(0)
    held.write(f"{os.getpid()}\n")
    held.flush()
    asyncio.run(Recorder(hours=hours).main())
    return 0


def ensure():
    for kind, sym, day, n in compact():
        log(f"merged {kind} {sym} {day}: {n:,} rows")
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
    for f in sorted(OUT.glob("*/*/*.parquet")):
        if f.parts[-4] == "_parts":
            continue
        rows.append((f.parts[-3], f.parts[-2], f.stem, len(pd.read_parquet(f, columns=["t"])), f.stat().st_size / 1e6,
                     "daily"))
    for d in sorted((OUT / "_parts").glob("*/*/*")):
        files = list(d.glob("*.parquet"))
        rows.append((*d.parts[-3:], sum(len(pd.read_parquet(f, columns=["t"])) for f in files),
                     sum(f.stat().st_size for f in files) / 1e6, f"{len(files)} parts"))
    for r in rows:
        print(f"{r[0]:7s} {r[1]:8s} {r[2]}  {r[3]:>11,} rows  {r[4]:8.1f} MB  {r[5]}")
    p = OUT / "sessions.csv"
    if p.exists():
        lines = p.read_text().splitlines()
        print(lines[0])
        print("\n".join(lines[1:][-8:]))
    st = OUT / "status.json"
    if st.exists():
        print(st.read_text())
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "ensure"
    sys.exit({"run": lambda: run(sys.argv[2:]), "ensure": ensure, "status": status}[cmd]())
