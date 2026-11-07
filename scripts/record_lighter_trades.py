"""Lighter public trade and best-quote stream for the commodity perps (M441, M443): every trade with both account ids,
who was the maker, each side's position and entry value before the fill, the margin fraction and the fee charged, plus
the best bid and ask on change. Lighter's public websocket (`?readonly=true`, no key, no login) sends these fields; the
REST recentTrades call gives the same fields but shares the machine's Lighter rate limit with record_lighter_book.py, so
the stream is used. Paper only; it places nothing.

Markets are looked up by id (WTI 145, NATGAS 158, BRENTOIL 159 on 2026-10-28). Account ids are the public numbers in
the stream; nothing here links an account to a person. `liq` is 1 for a liquidation trade. Prices and sizes are floats
parsed from Lighter's decimal strings; `tfee` and `mfee` are Lighter's integers (1e-6 of notional: a liquidation shows
10000 for 1%, ordinary trades 28-266, which is 0.28-2.66 bp, so fees differ by account and are not a market constant).

Layout: data/lighter_trades/<kind>/<SYMBOL>/<YYYY-MM-DD>/<HHMMSS>-<pid>.parquet every FLUSH_S, kinds `trade` and
`quote`. Trades are de-duplicated by trade id (the subscribe message repeats recent ones); a gap in the stream is
visible as a jump in `status.json` message gaps and in sessions.csv. It stops writing under MIN_FREE_GB free or MAX_MB
stored.

usage: python scripts/record_lighter_trades.py [ensure|run|status]
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
from lab import data  # noqa: E402

OUT = data.ROOT / "lighter_trades"
RUN = data.ROOT / "logs"
URL = "wss://mainnet.zklighter.elliot.ai/stream?readonly=true"
MARKETS = {"WTI": 145, "NATGAS": 158, "BRENTOIL": 159}
CA = "/root/.ccr/ca-bundle.crt"
FLUSH_S = 300
MIN_FREE_GB = 2.5
MAX_MB = 400
SEEN_MAX = 200_000
COLS = {
    "trade": ["t", "trade_id", "T", "tx_us", "block", "liq", "px", "sz", "ask_acct", "bid_acct", "maker_ask", "tfee",
              "mfee", "tpos", "tentry", "timf", "tsign", "mpos", "mentry", "mimf"],
    "quote": ["t", "upd", "nonce", "bid", "bq", "ask", "aq"],
}
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def num(x, default=float("nan")):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


class Tape:
    def __init__(self):
        self.rows = {}
        self.seen = {}
        self.quote = {}
        self.stat = {"n": {}, "dup": 0, "parse_err": 0, "max_gap_ms": {}, "unknown_market": 0}
        self.last = {}
        self.by_id = {v: k for k, v in MARKETS.items()}

    def put(self, kind, sym, row):
        self.rows.setdefault((kind, sym), []).append(row)
        k = f"{kind}:{sym}"
        self.stat["n"][k] = self.stat["n"].get(k, 0) + 1

    def gap(self, key, t_us):
        prev = self.last.get(key)
        self.last[key] = t_us
        if prev is not None and (t_us - prev) // 1000 > self.stat["max_gap_ms"].get(key, 0):
            self.stat["max_gap_ms"][key] = (t_us - prev) // 1000

    def trade(self, sym, d, t_us, liq):
        i = int(d["trade_id"])
        seen = self.seen.setdefault(sym, set())
        if i in seen:
            self.stat["dup"] += 1
            return
        seen.add(i)
        if len(seen) > SEEN_MAX:
            seen.clear()                    # a repeat after a clear is a duplicate row, dropped at analysis
        self.gap(("trade", sym), t_us)
        self.put("trade", sym, (
            t_us, i, int(d["timestamp"]), int(d.get("transaction_time", -1)), int(d.get("block_height", -1)), int(liq),
            num(d["price"]), num(d["size"]), int(d.get("ask_account_id", -1)), int(d.get("bid_account_id", -1)),
            int(bool(d.get("is_maker_ask"))), int(d.get("taker_fee", -1)), int(d.get("maker_fee", -1)),
            num(d.get("taker_position_size_before")), num(d.get("taker_entry_quote_before")),
            int(d.get("taker_initial_margin_fraction_before", -1)), int(bool(d.get("taker_position_sign_changed"))),
            num(d.get("maker_position_size_before")), num(d.get("maker_entry_quote_before")),
            int(d.get("maker_initial_margin_fraction_before", -1))))

    def feed(self, m, t_us):
        """One websocket message: trade batches (ordinary and liquidation) and quote updates."""
        kind, ch = str(m.get("type", "")), str(m.get("channel", ""))
        mid = int(ch.split(":")[1]) if ":" in ch else -1
        sym = self.by_id.get(mid)
        if kind.endswith("/trade") or kind.endswith("/ticker"):
            if sym is None:
                self.stat["unknown_market"] += 1
                return
        if kind.endswith("/trade"):
            for d in m.get("trades") or []:
                self.trade(sym, d, t_us, False)
            for d in m.get("liquidation_trades") or []:
                self.trade(sym, d, t_us, True)
        elif kind.endswith("/ticker"):
            q = m["ticker"]
            row = (num(q["b"]["price"]), num(q["b"]["size"]), num(q["a"]["price"]), num(q["a"]["size"]))
            if self.quote.get(sym) != row:
                self.quote[sym] = row
                self.gap(("quote", sym), t_us)
                self.put("quote", sym, (t_us, int(q.get("last_updated_at", -1)), int(m.get("nonce", -1))) + row)

    def drain(self):
        rows, self.rows = self.rows, {}
        return rows


def utc_day(us):
    return time.strftime("%Y-%m-%d", time.gmtime(us / 1e6))


def write_parts(rows, now, out=OUT):
    n = 0
    stamp = time.strftime("%H%M%S", time.gmtime(now)) + f"-{os.getpid()}"
    for (kind, sym), r in rows.items():
        if not r:
            continue
        df = pd.DataFrame(r, columns=COLS[kind])
        for day, g in df.groupby(df.t // 86_400_000_000, sort=False):
            d = out / kind / sym / utc_day(int(day) * 86_400_000_000)
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
        return f"data/lighter_trades reached {MAX_MB} MB"
    return ""


def load(kind, sym, day, out=OUT):
    """All rows of one UTC day in arrival order (file order), or None."""
    files = sorted((out / kind / sym / day).glob("*.parquet"))
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True) if files else None


def ssl_context():
    try:
        if Path(CA).exists():
            return ssl.create_default_context(cafile=CA)
    except OSError:
        pass
    return ssl.create_default_context()


class Recorder:
    def __init__(self, out=OUT):
        self.out = out
        self.tape = Tape()
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
                                              max_size=2**23) as ws:
                    for mid in MARKETS.values():
                        for ch in ("trade", "ticker"):
                            await ws.send(json.dumps({"type": "subscribe", "channel": f"{ch}/{mid}"}))
                    self.connected = True
                    closer = asyncio.create_task(self.close_on_stop(ws))
                    try:
                        async for raw in ws:
                            n += 1
                            t = time.time_ns() // 1000
                            try:
                                self.tape.feed(json.loads(raw), t)
                            except (KeyError, ValueError, TypeError, IndexError):
                                self.tape.stat["parse_err"] += 1
                            if self.stop.is_set():
                                break
                        else:
                            reason = "stopped" if self.stop.is_set() else "closed by server"
                    finally:
                        closer.cancel()
            except Exception as e:  # noqa: BLE001
                reason = f"{type(e).__name__}: {e}"[:200]
            self.connected = False
            self.msgs += n
            self.session(t0, n, reason)
            if self.stop.is_set():
                break
            delay = 1.0 if time.time() - t0 > 300 else min(delay * 2, 60.0)
            log(f"lighter trades: {reason}; reconnecting in {delay:.0f} s")
            try:
                await asyncio.wait_for(self.stop.wait(), delay)
            except asyncio.TimeoutError:
                pass

    async def close_on_stop(self, ws):
        await self.stop.wait()
        await ws.close()

    def flush(self, final=False):
        rows = self.tape.drain()
        self.why = full(self.out)
        if self.why:
            log(f"lighter trades: {self.why}; {sum(len(r) for r in rows.values())} rows not written")
            self.stop.set()
        else:
            self.rows += write_parts(rows, time.time(), self.out)
        st = self.tape.stat
        status = {"updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "pid": os.getpid(),
                  "connected": self.connected, "messages": self.msgs, "rows_written": self.rows,
                  "rows_by_stream": st["n"], "duplicates": st["dup"], "parse_err": st["parse_err"],
                  "unknown_market": st["unknown_market"],
                  "max_gap_ms": {f"{k[0]}:{k[1]}": v for k, v in st["max_gap_ms"].items()},
                  "stored_mb": round(used_mb(self.out), 1), "stopped": self.why or (final and "shutdown") or ""}
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
        self.out.mkdir(parents=True, exist_ok=True)
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self.stop.set)
        log(f"lighter trades: recording {'/'.join(MARKETS)} trades with account ids and best quotes")
        await asyncio.gather(self.stream(), self.flusher())
        self.flush(final=True)
        log(f"lighter trades: stopped; {self.rows} rows written")


def lock():
    RUN.mkdir(parents=True, exist_ok=True)
    f = open(RUN / "lighter_trades.lock", "a+")
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
            log("lighter trades: recorder running")
            return 0
        held.close()
        why = full()
        if why:
            log(f"lighter trades: not started: {why}")
            return 0
        RUN.mkdir(parents=True, exist_ok=True)
        with open(RUN / "lighter_trades.log", "a") as f:
            subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "run"], cwd=ROOT, stdout=f,
                             stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
        log("lighter trades: recorder started")
        return 0
    held = lock()
    if held is None:
        log("lighter trades: another recorder holds data/logs/lighter_trades.lock")
        return 1
    held.truncate(0)
    held.write(f"{os.getpid()}\n")
    held.flush()
    asyncio.run(Recorder().main())
    return 0


if __name__ == "__main__":
    sys.exit(main())
