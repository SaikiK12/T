"""Best quote, trades and reference prices of the 24/7 commodity and index perps on Hyperliquid (HIP-3 `xyz` dex) and
Kraken Futures, plus Binance's own TradFi perps, side by side (M443 WTI cross-venue residual, M447 reopen
re-anchoring, M449 funding persistence, M321 index-perp reopen convergence, M444 EIA second-stage flow). Public
websockets, no key, no login; paper only, it places nothing.

Why a recorder: Lighter's WTI, NATGAS and BRENTOIL are in record_lighter_trades.py. These two venues add the deep WTI
book (xyz:CL, about 290 million dollars a day) and the thin one (Kraken PF_WTIOILUSD, wide quotes), and both publish a
reference price next to their own: Hyperliquid's `oraclePx` and Kraken's `index`. While the CME reference is open they
follow it; while it is closed they are the price discovery. The first full closure that this machine records is
2026-10-30 21:00 UTC to 2026-11-01 23:00 UTC, and tomorrow's 14:30 UTC natural-gas storage release is inside the data.

Hyperliquid (wss://api.hyperliquid.xyz/ws): `bbo` (best bid and ask with size and order count), `trades` (price, size,
side, trade id and the two wallet addresses as sent), `activeAssetCtx` (oracle, mark, mid, funding, premium, impact
prices, open interest). Kraken (wss://futures.kraken.com/ws/v1): `ticker` (bid, ask and sizes, last, index, mark, funding
and its prediction, premium, open interest) and `trade`. Binance USD-M (wss://fstream.binance.com): `bookTicker`,
`aggTrade` and `markPrice@1s` (mark, index, estimated settle, funding, next funding time) for CLUSDT, BZUSDT, NATGASUSDT,
XAUUSDT, QQQUSDT and SPYUSDT, whose 1-minute history from 2026-04-01 is in the public archive. Rows are written on change,
stamped with the local receive time (microseconds) and the venue's own time. Binance quotes keep the first update in
each 100 ms bucket (CLUSDT alone sends about 40 a second); trades are kept whole.

Layout: data/commodity_perps/<kind>/<SYMBOL>/<YYYY-MM-DD>/<HHMMSS>-<pid>.parquet every FLUSH_S, kinds `hlbbo`, `hltrade`,
`hlctx`, `krtick`, `krtrade`, `bnbook`, `bnagg`, `bnmark`. Trades are de-duplicated by trade id; Kraken's `trade_snapshot` (history sent on subscribe)
is not stored. A gap shows in status.json `max_gap_ms` and in sessions.csv. It stops writing under MIN_FREE_GB free or
MAX_MB stored.

usage: python scripts/record_commodity_perps.py [ensure|run|status]
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
sys.path.insert(0, str(ROOT / "scripts"))
from lab import data  # noqa: E402
from record_lighter_trades import num, ssl_context, utc_day  # noqa: E402

OUT = data.ROOT / "commodity_perps"
RUN = data.ROOT / "logs"
HL_URL = "wss://api.hyperliquid.xyz/ws"
KR_URL = "wss://futures.kraken.com/ws/v1"
HL_COINS = ("CL", "NATGAS", "BRENTOIL", "GOLD", "SP500", "XYZ100")      # xyz:<name>
KR_PRODUCTS = ("PF_WTIOILUSD", "PF_NATGASUSD", "PF_BRENTOILUSD", "PF_XAUUSD", "PF_SPYXUSD", "PF_QQQXUSD")
BN_PUBLIC = "wss://fstream.binance.com/public/stream?streams="       # bookTicker
BN_MARKET = "wss://fstream.binance.com/market/stream?streams="       # aggTrade and markPrice
BN_SYMBOLS = ("CLUSDT", "BZUSDT", "NATGASUSDT", "XAUUSDT", "QQQUSDT", "SPYUSDT")
BN_BUCKET_US = 100_000
FLUSH_S = 300
HL_PING_S = 30
MIN_FREE_GB = 2.5
MAX_MB = 4000
SEEN_MAX = 100_000
COLS = {
    "hlbbo": ["t", "T", "bid", "bq", "bn", "ask", "aq", "an"],
    "hltrade": ["t", "T", "tid", "side", "px", "sz", "u0", "u1"],
    "hlctx": ["t", "funding", "oi", "oracle", "mark", "mid", "premium", "ibid", "iask"],
    "krtick": ["t", "T", "bid", "bq", "ask", "aq", "last", "index", "mark", "oi", "fund", "fund_pred", "rel_fund",
               "rel_fund_pred", "next_fund_ms", "premium", "suspended"],
    "krtrade": ["t", "T", "uid", "side", "type", "seq", "qty", "px"],
    "bnbook": ["t", "T", "u", "bid", "bq", "ask", "aq"],
    "bnagg": ["t", "T", "aid", "px", "q", "nq", "maker_buyer"],
    "bnmark": ["t", "T", "mark", "index", "settle", "funding", "next_fund_ms"],
}
VENUES = ("hl", "kraken", "bn_public", "bn_market")
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def level(x):
    """(price, size, count) of one Hyperliquid bbo side; NaN when that side is empty."""
    if not x:
        return float("nan"), float("nan"), 0
    return num(x.get("px")), num(x.get("sz")), int(x.get("n", 0))


class Tape:
    def __init__(self):
        self.rows = {}
        self.seen = {}
        self.last_row = {}
        self.last_t = {}
        self.last_bucket = {}
        self.stat = {"n": {}, "dup": 0, "parse_err": 0, "max_gap_ms": {}, "unknown": 0}

    def put(self, kind, sym, row):
        if not sym:
            self.stat["unknown"] += 1           # a message with no symbol never becomes a file path
            return
        self.rows.setdefault((kind, sym), []).append(row)
        k = f"{kind}:{sym}"
        self.stat["n"][k] = self.stat["n"].get(k, 0) + 1

    def changed(self, kind, sym, key, t_us):
        """True when `key` differs from the last one kept for (kind, sym); records the gap between kept rows."""
        k = (kind, sym)
        if self.last_row.get(k) == key:
            return False
        self.last_row[k] = key
        prev = self.last_t.get(k)
        self.last_t[k] = t_us
        if prev is not None and (t_us - prev) // 1000 > self.stat["max_gap_ms"].get(f"{kind}:{sym}", 0):
            self.stat["max_gap_ms"][f"{kind}:{sym}"] = (t_us - prev) // 1000
        return True

    def fresh(self, kind, sym, ident):
        seen = self.seen.setdefault((kind, sym), set())
        if ident in seen:
            self.stat["dup"] += 1
            return False
        seen.add(ident)
        if len(seen) > SEEN_MAX:
            seen.clear()                    # a repeat after a clear is a duplicate row, dropped at analysis
        return True

    def hl(self, m, t_us):
        """One Hyperliquid websocket message."""
        ch, d = m.get("channel"), m.get("data")
        if ch == "bbo":
            sym = d["coin"].split(":")[-1]
            b, a = d["bbo"]
            row = level(b) + level(a)
            if self.changed("hlbbo", sym, row, t_us):
                self.put("hlbbo", sym, (t_us, int(d["time"])) + row)
        elif ch == "trades":
            for x in d:
                sym = x["coin"].split(":")[-1]
                if self.fresh("hltrade", sym, x["tid"]):
                    u = x.get("users") or ["", ""]
                    self.put("hltrade", sym, (t_us, int(x["time"]), int(x["tid"]), x["side"], num(x["px"]),
                                              num(x["sz"]), u[0], u[1]))
        elif ch == "activeAssetCtx":
            sym = d["coin"].split(":")[-1]
            c = d["ctx"]
            ip = c.get("impactPxs") or [None, None]
            row = (num(c.get("funding")), num(c.get("openInterest")), num(c.get("oraclePx")), num(c.get("markPx")),
                   num(c.get("midPx")), num(c.get("premium")), num(ip[0]), num(ip[1]))
            if self.changed("hlctx", sym, row, t_us):
                self.put("hlctx", sym, (t_us,) + row)
        elif ch not in ("subscriptionResponse", "pong"):
            self.stat["unknown"] += 1

    def kraken(self, m, t_us):
        """One Kraken Futures websocket message."""
        feed, sym = m.get("feed"), m.get("product_id")
        if m.get("event"):                       # subscribe acks carry the feed name too
            if m["event"] not in ("subscribed", "info"):
                self.stat["unknown"] += 1
            return
        if feed == "ticker":
            row = (num(m.get("bid")), num(m.get("bid_size")), num(m.get("ask")), num(m.get("ask_size")),
                   num(m.get("last")), num(m.get("index")), num(m.get("markPrice")), num(m.get("openInterest")),
                   num(m.get("funding_rate")), num(m.get("funding_rate_prediction")),
                   num(m.get("relative_funding_rate")), num(m.get("relative_funding_rate_prediction")),
                   int(m.get("next_funding_rate_time", -1)), num(m.get("premium")), int(bool(m.get("suspended"))))
            if self.changed("krtick", sym, row, t_us):
                self.put("krtick", sym, (t_us, int(m.get("time", -1))) + row)
        elif feed == "trade":
            if self.fresh("krtrade", sym, m["uid"]):
                self.put("krtrade", sym, (t_us, int(m["time"]), m["uid"], m.get("side", ""), m.get("type", ""),
                                          int(m.get("seq", -1)), num(m["qty"]), num(m["price"])))
        elif feed not in ("trade_snapshot", "heartbeat", None):
            self.stat["unknown"] += 1

    def binance(self, m, t_us):
        """One Binance combined-stream message (bookTicker, aggTrade or markPriceUpdate)."""
        d = m.get("data", m)
        e, sym = d.get("e"), d.get("s")
        if e == "bookTicker":
            if t_us // BN_BUCKET_US == self.last_bucket.get(sym):
                return
            row = (num(d["b"]), num(d["B"]), num(d["a"]), num(d["A"]))
            if self.changed("bnbook", sym, row, t_us):
                self.last_bucket[sym] = t_us // BN_BUCKET_US
                self.put("bnbook", sym, (t_us, int(d["T"]), int(d["u"])) + row)
        elif e == "aggTrade":
            if self.fresh("bnagg", sym, d["a"]):
                self.put("bnagg", sym, (t_us, int(d["T"]), int(d["a"]), num(d["p"]), num(d["q"]), num(d.get("nq")),
                                        int(bool(d["m"]))))
        elif e == "markPriceUpdate":
            row = (num(d["p"]), num(d["i"]), num(d["P"]), num(d["r"]), int(d["T"]))
            if self.changed("bnmark", sym, row, t_us):
                self.put("bnmark", sym, (t_us, int(d["E"])) + row)
        else:
            self.stat["unknown"] += 1

    def drain(self):
        rows, self.rows = self.rows, {}
        return rows


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
        return f"data/commodity_perps reached {MAX_MB} MB"
    return ""


def load(kind, sym, day, out=OUT):
    """All rows of one UTC day in arrival order (file order), or None."""
    files = sorted((out / kind / sym / day).glob("*.parquet"))
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True) if files else None


def hl_subscriptions():
    for c in HL_COINS:
        for t in ("bbo", "trades", "activeAssetCtx"):
            yield {"method": "subscribe", "subscription": {"type": t, "coin": f"xyz:{c}"}}


def bn_url(base, streams):
    return base + "/".join(f"{sym.lower()}@{st}" for sym in BN_SYMBOLS for st in streams)


def no_subscriptions():
    return ()


def kr_subscriptions():
    for feed in ("ticker", "trade"):
        yield {"event": "subscribe", "feed": feed, "product_ids": list(KR_PRODUCTS)}


class Recorder:
    def __init__(self, out=OUT):
        self.out = out
        self.tape = Tape()
        self.stop = asyncio.Event()
        self.rows = 0
        self.msgs = {v: 0 for v in VENUES}
        self.connected = {v: False for v in VENUES}
        self.why = ""

    def session(self, venue, t0, n, reason):
        p = self.out / "sessions.csv"
        new = not p.exists()
        with open(p, "a", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            if new:
                w.writerow(["venue", "start_utc", "end_utc", "seconds", "messages", "ended_by"])
            w.writerow([venue, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)),
                        time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), round(time.time() - t0), n, reason])

    async def stream(self, venue, url, subs, handler, ping=None):
        import websockets
        delay = 1.0
        while not self.stop.is_set():
            t0, n, reason = time.time(), 0, "stopped"
            try:
                async with websockets.connect(url, ssl=ssl_context(), open_timeout=20, close_timeout=2,
                                              max_size=2**23) as ws:
                    for s in subs():
                        await ws.send(json.dumps(s))
                    self.connected[venue] = True
                    tasks = [asyncio.create_task(self.close_on_stop(ws))]
                    if ping:
                        tasks.append(asyncio.create_task(self.pinger(ws, ping)))
                    try:
                        async for raw in ws:
                            n += 1
                            self.msgs[venue] += 1
                            t = time.time_ns() // 1000
                            try:
                                handler(json.loads(raw), t)
                            except (KeyError, ValueError, TypeError, IndexError):
                                self.tape.stat["parse_err"] += 1
                            if self.stop.is_set():
                                break
                        else:
                            reason = "stopped" if self.stop.is_set() else "closed by server"
                    finally:
                        for task in tasks:
                            task.cancel()
            except Exception as e:  # noqa: BLE001
                reason = f"{type(e).__name__}: {e}"[:200]
            self.connected[venue] = False
            self.session(venue, t0, n, reason)
            if self.stop.is_set():
                break
            delay = 1.0 if time.time() - t0 > 300 else min(delay * 2, 60.0)
            log(f"commodity perps {venue}: {reason}; reconnecting in {delay:.0f} s")
            try:
                await asyncio.wait_for(self.stop.wait(), delay)
            except asyncio.TimeoutError:
                pass

    async def close_on_stop(self, ws):
        await self.stop.wait()
        await ws.close()

    async def pinger(self, ws, message):
        while True:
            await asyncio.sleep(HL_PING_S)
            await ws.send(json.dumps(message))

    def flush(self, final=False):
        rows = self.tape.drain()
        self.why = full(self.out)
        if self.why:
            log(f"commodity perps: {self.why}; {sum(len(r) for r in rows.values())} rows not written")
            self.stop.set()
        else:
            self.rows += write_parts(rows, time.time(), self.out)
        st = self.tape.stat
        status = {"updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "pid": os.getpid(),
                  "connected": self.connected, "messages": self.msgs, "rows_written": self.rows,
                  "rows_by_stream": st["n"], "duplicates": st["dup"], "parse_err": st["parse_err"],
                  "unknown_messages": st["unknown"], "max_gap_ms": st["max_gap_ms"],
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
        log(f"commodity perps: recording Hyperliquid xyz:{'/'.join(HL_COINS)}, Kraken {len(KR_PRODUCTS)} products and "
            f"Binance {'/'.join(BN_SYMBOLS)}")
        await asyncio.gather(
            self.stream("hl", HL_URL, hl_subscriptions, self.tape.hl, ping={"method": "ping"}),
            self.stream("kraken", KR_URL, kr_subscriptions, self.tape.kraken),
            self.stream("bn_public", bn_url(BN_PUBLIC, ("bookTicker",)), no_subscriptions, self.tape.binance),
            self.stream("bn_market", bn_url(BN_MARKET, ("aggTrade", "markPrice@1s")), no_subscriptions,
                        self.tape.binance),
            self.flusher())
        self.flush(final=True)
        log(f"commodity perps: stopped; {self.rows} rows written")


def lock():
    RUN.mkdir(parents=True, exist_ok=True)
    f = open(RUN / "commodity_perps.lock", "a+")
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
            log("commodity perps: recorder running")
            return 0
        held.close()
        why = full()
        if why:
            log(f"commodity perps: not started: {why}")
            return 0
        RUN.mkdir(parents=True, exist_ok=True)
        with open(RUN / "commodity_perps.log", "a") as f:
            subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "run"], cwd=ROOT, stdout=f,
                             stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
        log("commodity perps: recorder started")
        return 0
    held = lock()
    if held is None:
        log("commodity perps: another recorder holds data/logs/commodity_perps.lock")
        return 1
    held.truncate(0)
    held.write(f"{os.getpid()}\n")
    held.flush()
    asyncio.run(Recorder().main())
    return 0


if __name__ == "__main__":
    sys.exit(main())
