"""R364 settlelit_fwd: R363's Lighter settlement scalp, forward on paper, on Binance's live predicted funding rate.

R363 (gate 0, PASS by its frozen rule, recorded PARTIAL) held a position on Lighter against the side that received a
deep Binance funding lump, from the last trade before T to the last trade before T + 1 min, paying Lighter's own
settlement at T: +23.4 bp a hop at 1x on 134 hops R356 never read. This lane runs that trade on settlements no lane
has read, with paper fills walked through Lighter's live book. Paper only: public websockets and endpoints, no
account, no key. Nothing here can place an order.

For each 4 h settlement T (00/04/08/12/16/20 UTC), the rule in scripts/settlelit_fwd_rule.py:
1. **Decision window,** T - 1 h - 5 min to T - 1 h + 20 s: Binance's `!markPrice@arr` stream (each perp's predicted
   rate r and next funding time) and Lighter's `market_stats/all` stream (each market's last hourly settlement and
   mid). Lighter's market list is read once over REST. At T - 1 h + 20 s up to 5 hops are selected, each only when
   walking its quantity both ways on Lighter's REST book costs at most 10 bp (signals.csv, one decisions.csv row).
2. **Book window,** T - 7 min to T + 6 min, for the selected hops: Lighter's `order_book`, `trade` and `market_stats`
   channels and Binance's markPrice@1s and aggTrade streams for the coin. The book is kept in memory (each update must
   chain on the last nonce, or the stream reconnects for a fresh snapshot) and recorded each second, 25 levels a side,
   with the trades, to data/settlelit_fwd/<T>/ (recordings.csv holds each file's sha256). Paper walks of the hop's
   fixed base quantity run on the live book: the entry side at T - 5 min and T - 10 s (the primary entry), the exit
   side at T + 60 s (the primary exit), T + 2 min and T + 5 min (tickets.csv).
3. **Exits always close:** an exit the stream cannot finish by T + 6 min, or one owed after a restart, walks Lighter's
   REST book (100 levels) once a minute until it fills.
4. **Score,** 20 minutes after the exit: Lighter's settlements in the hold, from its funding history (scored.csv).
5. **Status** every minute: status.json, with the PREREG's decision and lab.gate.go_real on the primary book.

Start: the forward loop's hourly task runs this script with no argument (`ensure`), which starts `run` detached when no
writer holds the journal lock (log: data/logs/settlelit_fwd.log). After a restart the journal resumes: a book window
still ahead is run, an entry whose instant passed is missed, and an owed exit is walked on the REST book, late.
usage: python scripts/forward_settlelit.py [ensure] | run | status | score
"""
import argparse
import asyncio
import contextlib
import csv
import fcntl
import gzip
import hashlib
import io
import json
import math
import re
import ssl
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import carrylane, gate, prereg  # noqa: E402
import settlelit_fwd_rule as rule  # noqa: E402  the rule, fixed

LANE = ROOT / "experiments" / "settlelit_fwd"
JOURNAL = LANE / "journal"
DATA = ROOT / "data" / "settlelit_fwd"
LOG = ROOT / "data" / "logs" / "settlelit_fwd.log"
REGISTRY = "R364"
CA = "/root/.ccr/ca-bundle.crt"
BINANCE = "wss://fstream.binance.com/market/stream?streams="          # markPrice and aggTrade, as record_tape.py
LIGHTER_WS = "wss://mainnet.zklighter.elliot.ai/stream?readonly=true"   # read-only: the plain URL answers 400 here
DEPTH = 25                                                              # levels a side recorded each second
PING_S = 15
H, MIN, SEC = rule.H, rule.MIN, rule.SEC
FILES = {
    "decisions": ["decided_ms", "T", "late_s", "first_ms", "binance", "settling", "eligible", "on_lighter", "logged",
                  "candidates", "selected", "error"],
    "signals": ["decided_ms", "T", "symbol", "lighter", "market_id", "r", "r_ms", "first_ms", "mark", "h", "h_t", "e",
                "d", "l_mid", "ratio", "fee_bp", "feed_r8", "q", "rt_bp", "rank", "status"],
    "tickets": ["hop", "kind", "T", "symbol", "lighter", "market_id", "d", "e", "r", "q", "fee_bp", "at_ms", "ms",
                "late_ms", "live", "book_ms", "bid", "ask", "mid", "fill", "filled", "levels", "parts", "thin",
                "source", "b_r", "b_mark", "status"],
    "scored": ["hop", "T", "symbol", "lighter", "d", "e", "r", "theta_book", "entry_ms", "exit_ms", "exit_late_ms",
               "exit_source", "on_time", "rates", "fund_missing", "gross_mid", "fund", "n_fund", "book_cost", "fee",
               "net1", "net2", "net3"] + [f"{rule.NAMES[a]}_{rule.NAMES[b]}" for a, b in rule.VARIANTS],
    "recordings": ["hop", "T", "kind", "path", "rows", "bytes", "sha256"],
}
REC = {   # recorded per hop, one gzip csv each
    "book": ["ms", "book_ms", "side", "level", "price", "size"],
    "trades": ["ts", "trade_id", "price", "size", "is_maker_ask", "type"],
    "stats": ["ms", "mark", "index", "mid", "bid", "ask", "last", "funding_rate", "funding_timestamp",
              "current_funding_rate", "open_interest"],
    "bmark": ["E", "p", "i", "r", "T"],
    "bagg": ["T", "a", "p", "q", "m"],
}
HOP_KEYS = ("hop", "T", "symbol", "lighter", "market_id", "d", "e", "r", "q", "fee_bp")
log = lambda *a: print(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), *a, flush=True)


def clock_ms():
    return int(time.time() * 1000)


def fixed_inputs(prereg_path):
    """{path: sha256} from the PREREG's ```fixed block: the files the lane may not decide without."""
    block = re.search(r"```fixed\n(.*?)```", Path(prereg_path).read_text(), re.S).group(1)
    return {rel: want for want, rel in (line.split() for line in block.strip().splitlines())}


def check(lane=LANE):
    """The PREREG and every fixed file must be unchanged since the freeze; the lane does not decide otherwise."""
    prereg.verify(lane / "PREREG.md")
    bad = [rel for rel, want in fixed_inputs(lane / "PREREG.md").items() if prereg.sha256_file(ROOT / rel) != want]
    if bad:
        raise prereg.PreregError(f"fixed inputs changed since the freeze: {bad}")


# ----------------------------------------------------------------------------------------------------- journals
def path_of(name):
    return JOURNAL / f"{name}.csv"


def read(name):
    p = path_of(name)
    if not p.exists():
        return []
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def append(name, rows):
    """Append-only: rows are added under the file's fixed header, never rewritten. A missing column is written empty;
    a column outside the header raises."""
    if not rows:
        return
    p = path_of(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    new = not p.exists()
    with open(p, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FILES[name], lineterminator="\n", extrasaction="raise")
        if new:
            w.writeheader()
        w.writerows(rows)


@contextlib.contextmanager
def writer_lock():
    """One writer for the lane's journal; a second process exits."""
    JOURNAL.mkdir(parents=True, exist_ok=True)
    f = open(JOURNAL / ".writer.lock", "a")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        f.close()
        raise SystemExit("another settlelit_fwd writer holds the journal lock")
    try:
        yield
    finally:
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()


def tickets_by_hop(tickets=None):
    out = {}
    for t in read("tickets") if tickets is None else tickets:
        out.setdefault(t["hop"], {})[t["kind"]] = t
    return out


def entered(kinds):
    return kinds.get("in10", {}).get("status") == "entered"


# ------------------------------------------------------------------------------------------------- the decision
def on_binance_all(msg, seen, meta):
    """One `!markPrice@arr` message into seen {symbol: [next funding time, first event time, r, r's time, mark]}. A
    symbol whose next funding time changes starts again from this event."""
    data = msg.get("data", msg) if isinstance(msg, dict) else msg
    if not isinstance(data, list):
        return 0
    n = 0
    for x in data:
        try:
            s, tn, e, r, p = x["s"], int(x["T"]), int(x["E"]), float(x["r"]), float(x["p"])
        except (KeyError, TypeError, ValueError):
            continue
        cur = seen.get(s)
        if cur is None or cur[0] != tn:
            seen[s] = [tn, e, r, e, p]
        else:
            cur[2], cur[3], cur[4] = r, e, p
        meta["first_ms"] = min(meta.get("first_ms") or e, e)
        n += 1
    return n


def on_lighter_stats(msg, stats):
    """A market_stats message (all markets, or one) into stats {market_id: latest row}."""
    ms = msg.get("market_stats") if isinstance(msg, dict) else None
    if not isinstance(ms, dict):
        return
    for r in [ms] if "market_id" in ms else ms.values():
        try:
            stats[int(r["market_id"])] = r
        except (KeyError, TypeError, ValueError):
            continue


def select(T, now_ms, seen, stats, details, first_ms=None, feed=None, cost_of=None):
    """The decision for T, from the window's two streams and Lighter's market list: (signals rows, the decision row,
    the selected hops). feed {market_id: rate}: Binance's rate as Lighter's funding-rates feed shows it (8 h terms),
    logged beside r and never decided on. cost_of(market_id, q): the rule's round trip of q on Lighter's book, read
    only for a candidate that reaches the cost gate (Lighter's REST book in the daemon); none, or an error, selects
    nothing."""
    dec = {"decided_ms": now_ms, "T": T, "late_s": round((now_ms - (T - H)) / 1000), "first_ms": first_ms or "",
           "binance": len(seen), "settling": sum(1 for v in seen.values() if int(v[0]) == T), "error": ""}
    if first_ms is None or first_ms > T - H - rule.SINCE_MARGIN:
        dec["error"] = "window opened after T - 1 h - 60 s: cycles not observed"
    el = rule.eligible(T, seen)
    lm = {}
    for d in details or []:
        if d.get("status") == "active" and rule.lighter_crypto(d):
            lm.setdefault(rule.canon(d["symbol"]), d)
    rows, cands, on = [], [], 0
    for s, r, r_ms, first, mark in el:
        d = lm.get(rule.canon(rule.binance_base(s)))
        if d is None:
            continue
        on += 1
        mid_ = int(d["market_id"])
        st = stats.get(mid_) or {}
        l_mid = rule.lighter_mid(st)
        row = {"decided_ms": now_ms, "T": T, "symbol": s, "lighter": d["symbol"], "market_id": mid_, "r": r,
               "r_ms": r_ms, "first_ms": first, "mark": mark, "l_mid": l_mid if math.isfinite(l_mid) else "",
               "ratio": round(l_mid / mark, 6) if math.isfinite(l_mid) and mark > 0 else "",
               "fee_bp": float(d.get("taker_fee") or 0) * 1e4, "feed_r8": (feed or {}).get(mid_, "")}
        h_t, h = rule.lighter_h(st, T)
        if h_t is None:
            if abs(r) >= rule.LOG_E:
                rows.append({**row, "status": "no live Lighter rate"})
            continue
        e, dd = rule.signal(r, h)
        row.update({"h": h, "h_t": h_t, "e": e, "d": dd})
        if abs(e) >= rule.THETA - 1e-15:
            cands.append(row)
        elif abs(e) >= rule.LOG_E:
            rows.append({**row, "status": f"below {rule.THETA:.1%}"})
    cands.sort(key=lambda x: (-abs(x["e"]), x["symbol"]))
    hops, used = [], set()
    late = now_ms > T - H + rule.ON_TIME
    for rank, row in enumerate(cands, 1):
        row["rank"] = rank
        if late:
            row["status"] = "late decision"
        elif not rule.same_price(row["l_mid"] or math.nan, row["mark"]):
            row["status"] = "identity: Lighter's mid not within 5% of Binance's mark"
        elif row["market_id"] in used:
            row["status"] = "Lighter market already selected"
        elif len(hops) >= rule.SLOTS:
            row["status"] = "slots full"
        else:
            row["q"] = rule.USD / row["l_mid"]
            try:
                rt = float(cost_of(row["market_id"], row["q"])) if cost_of else math.nan
            except Exception:  # noqa: BLE001 - logged as a candidate without a book
                rt = math.nan
            row["rt_bp"] = round(rt * 1e4, 2) if math.isfinite(rt) else ("" if math.isnan(rt) else "inf")
            if math.isnan(rt):
                row["status"] = "no book at the decision"
            elif rt == math.inf:
                row["status"] = "book cannot hold q"
            elif rt > rule.MAX_RT:
                row["status"] = f"book cost above {rule.MAX_RT:.2%}"
            else:
                row["status"] = "selected"
                used.add(row["market_id"])
                hops.append({"hop": f"{row['symbol']}:{T}", **{k: row[k] for k in HOP_KEYS[1:]}})
        rows.append(row)
    dec.update({"eligible": len(el), "on_lighter": on, "logged": len(rows), "candidates": len(cands),
                "selected": len(hops)})
    return rows, dec, hops


def selected_hops(T):
    """The hops selected for T, rebuilt from signals.csv (after a restart)."""
    out = []
    for r in read("signals"):
        if int(r["T"]) == T and r["status"] == "selected":
            out.append({"hop": f"{r['symbol']}:{T}", "T": T, "symbol": r["symbol"], "lighter": r["lighter"],
                        "market_id": int(r["market_id"]), "d": int(r["d"]), "e": float(r["e"]), "r": float(r["r"]),
                        "q": float(r["q"]), "fee_bp": float(r["fee_bp"])})
    return out


# --------------------------------------------------------------------------------------------------------- books
class Gap(Exception):
    """An order-book update that does not chain on the last nonce: the stream reconnects for a fresh snapshot."""


class Book:
    """One Lighter market's book from its order_book channel: a snapshot, then deltas (size 0 removes a level), each
    delta's begin_nonce equal to the last nonce."""

    def __init__(self):
        self.bids, self.asks = {}, {}
        self.nonce, self.live, self.ms = None, False, None

    @staticmethod
    def _levels(xs):
        out = {}
        for x in xs or []:
            try:
                out[float(x["price"])] = float(x["size"])
            except (KeyError, TypeError, ValueError):
                continue
        return out

    def snapshot(self, ob, ts):
        self.bids = {p: s for p, s in self._levels(ob.get("bids")).items() if s > 0}
        self.asks = {p: s for p, s in self._levels(ob.get("asks")).items() if s > 0}
        self.nonce, self.live, self.ms = ob.get("nonce"), True, ts

    def update(self, ob, ts):
        if not self.live or self.nonce is None or ob.get("begin_nonce") != self.nonce:
            self.live = False
            raise Gap(f"nonce {ob.get('begin_nonce')} after {self.nonce}")
        for side, new in ((self.bids, ob.get("bids")), (self.asks, ob.get("asks"))):
            for p, s in self._levels(new).items():
                if s > 0:
                    side[p] = s
                else:
                    side.pop(p, None)
        self.nonce, self.ms = ob.get("nonce"), ts

    def levels(self, buy):
        """Best first: the asks rising for a buy, the bids falling for a sell."""
        return sorted(self.asks.items()) if buy else sorted(self.bids.items(), reverse=True)

    def best(self):
        bid = max(self.bids) if self.bids else math.nan
        ask = min(self.asks) if self.asks else math.nan
        return bid, ask


def rest_cost(market_id, q):
    """The cost gate at the decision: the rule's round trip of q on Lighter's REST book (100 levels a side)."""
    b = retry(lambda: rest_book(market_id), 2, 2.0)
    return rule.round_trip(b.levels(False), b.levels(True), q)


def rest_book(market_id):
    """Lighter's REST book (100 levels a side), as a live Book."""
    d = carrylane._lighter("orderBookOrders", market_id=market_id, limit=100)
    b = Book()
    lv = lambda xs: [{"price": x["price"], "size": x["remaining_base_amount"]} for x in xs or []]
    b.snapshot({"bids": lv(d.get("bids")), "asks": lv(d.get("asks"))}, clock_ms())
    return b


class Recording:
    """The window's raw rows, kept in memory as tuples in REC's column order and written once the window ends."""

    def __init__(self, T, hops):
        self.T, self.hops = T, {h["hop"]: h for h in hops}
        self.rows = {(h["hop"], k): [] for h in hops for k in REC}

    def add(self, hop, kind, row):
        if (hop, kind) in self.rows:
            self.rows[(hop, kind)].append(tuple(row.get(c) for c in REC[kind]))

    def write(self, root=None):
        """One gzip csv a hop and kind (gzip time 0, so the bytes depend on the rows only): recordings rows."""
        out = []
        folder = (root or DATA) / str(self.T)
        for (hop, kind), rows in self.rows.items():
            if not rows:
                continue
            if kind == "trades":                               # a reconnect sends the recent trades again
                rows = list({(r[1], r[0]): r for r in rows}.values())
            buf = io.StringIO()
            w = csv.writer(buf, lineterminator="\n")
            w.writerow(REC[kind])
            w.writerows(rows)
            raw = gzip.compress(buf.getvalue().encode(), mtime=0)
            folder.mkdir(parents=True, exist_ok=True)
            p = folder / f"{self.hops[hop]['lighter']}_{kind}.csv.gz"
            p.write_bytes(raw)
            out.append({"hop": hop, "T": self.T, "kind": kind,
                        "path": str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p), "rows": len(rows),
                        "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
        return out

    def sample(self, books, by_market, now_ms):
        for mid_, b in books.items():
            if not b.live:
                continue
            rows = self.rows[(by_market[mid_]["hop"], "book")]
            for side, levels in (("bid", b.levels(False)[:DEPTH]), ("ask", b.levels(True)[:DEPTH])):
                for k, (p, s) in enumerate(levels):
                    rows.append((now_ms, b.ms, side, k, p, s))


def on_lighter(msg, books, rec, by_market, now_ms):
    """One message of the book window's Lighter connection. Raises Gap when a book loses its chain."""
    ty, ch = msg.get("type", ""), msg.get("channel", "")
    try:
        mid_ = int(str(ch).split(":")[1])
    except (IndexError, ValueError):
        return
    hop = by_market.get(mid_)
    if hop is None:
        return
    if ty in ("subscribed/order_book", "update/order_book"):
        ob = msg.get("order_book") or {}
        if ty.startswith("subscribed"):
            books[mid_].snapshot(ob, msg.get("timestamp"))
        else:
            books[mid_].update(ob, msg.get("timestamp"))
    elif ty in ("subscribed/trade", "update/trade"):
        for key in ("trades", "liquidation_trades"):
            for t in msg.get(key) or []:
                rec.add(hop["hop"], "trades", {"ts": t.get("timestamp"), "trade_id": t.get("trade_id"),
                                               "price": t.get("price"), "size": t.get("size"),
                                               "is_maker_ask": t.get("is_maker_ask"), "type": t.get("type")})
    elif ty.endswith("market_stats"):
        st = msg.get("market_stats") or {}
        st = st if "market_id" in st else st.get(str(mid_), st.get(mid_, {}))
        rec.add(hop["hop"], "stats", {"ms": now_ms, "mark": st.get("mark_price"), "index": st.get("index_price"),
                                      "mid": st.get("mid_price"), "bid": st.get("best_bid_price"),
                                      "ask": st.get("best_ask_price"), "last": st.get("last_trade_price"),
                                      "funding_rate": st.get("funding_rate"),
                                      "funding_timestamp": st.get("funding_timestamp"),
                                      "current_funding_rate": st.get("current_funding_rate"),
                                      "open_interest": st.get("open_interest")})


def on_binance_sym(msg, marks, rec, by_symbol):
    d = msg.get("data") if isinstance(msg, dict) else None
    if not isinstance(d, dict):
        return
    hop = by_symbol.get(d.get("s"))
    if hop is None:
        return
    if d.get("e") == "markPriceUpdate":
        try:
            marks[d["s"]] = (float(d["r"]), float(d["p"]))
        except (KeyError, TypeError, ValueError):
            return
        rec.add(hop["hop"], "bmark", {"E": d.get("E"), "p": d.get("p"), "i": d.get("i"), "r": d.get("r"),
                                      "T": d.get("T")})
    elif d.get("e") == "aggTrade":
        rec.add(hop["hop"], "bagg", {"T": d.get("T"), "a": d.get("a"), "p": d.get("p"), "q": d.get("q"),
                                     "m": d.get("m")})


# --------------------------------------------------------------------------------------------------------- walks
def ticket(hop, kind, at, **kw):
    return {**{k: hop[k] for k in HOP_KEYS}, "kind": kind, "at_ms": at, **kw}


def entry_walk(hop, off, book, mark, now_ms):
    """A walk of the hop's quantity on the entry side at T + off (off < 0). The primary (T - 10 s) enters when the
    book is live, the shown depth holds the whole quantity, and the walk comes before T - 1 s."""
    at, kind = hop["T"] + off, rule.NAMES[off]
    primary = off == rule.PRIMARY[0]
    b_r, b_mark = mark if mark else ("", "")
    row = ticket(hop, kind, at, ms=now_ms, late_ms=now_ms - at, b_r=b_r, b_mark=b_mark, source="ws")
    if book is None or not book.live:
        return {**row, "live": 0, "status": "no live book" + (": not entered" if primary else "")}
    bid, ask = book.best()
    if not (bid > 0 and ask > 0):
        return {**row, "live": 1, "book_ms": book.ms, "bid": bid, "ask": ask,
                "status": "one-sided book" + (": not entered" if primary else "")}
    px, got, used = rule.walk(book.levels(rule.side(hop["d"], entry=True)), hop["q"])
    thin = got < hop["q"] * (1 - 1e-9)
    row.update({"live": 1, "book_ms": book.ms, "bid": bid, "ask": ask, "mid": (bid + ask) / 2, "fill": px,
                "filled": got, "levels": used, "parts": 1, "thin": int(thin)})
    if not primary:
        return {**row, "status": "thin" if thin else "walked"}
    if thin:
        return {**row, "status": "thin: not entered"}
    if now_ms >= hop["T"] - SEC:
        return {**row, "status": "too late: not entered"}
    return {**row, "status": "entered"}


class Exit:
    """An exit walk of the hop's whole quantity at T + off, finished over later books (each second, then Lighter's REST
    book each minute) when the shown depth is short. Nothing fills beyond a shown book."""

    def __init__(self, hop, off):
        self.hop, self.off, self.kind, self.at = hop, off, rule.NAMES[off], hop["T"] + off
        self.left, self.paid, self.parts, self.levels = float(hop["q"]), 0.0, 0, 0
        self.first_ms = self.mid = self.bid = self.ask = self.book_ms = None
        self.source, self.thin = "ws", 0

    def step(self, book, now_ms, source="ws"):
        """Walk what is left on this book; True when the whole quantity has filled."""
        if book is None or not book.live:
            return False
        if self.mid is None:
            bid, ask = book.best()
            if not (bid > 0 and ask > 0):                  # a one-sided book gives no mid: the next one is tried
                return False
            self.bid, self.ask = bid, ask
            self.mid, self.first_ms, self.book_ms = (bid + ask) / 2, now_ms, book.ms
        px, got, used = rule.walk(book.levels(rule.side(self.hop["d"], entry=False)), self.left)
        if got > 0:
            self.paid += px * got
            self.left -= got
            self.parts += 1
            self.levels += used
        self.source = source
        if self.left > self.hop["q"] * 1e-9:
            self.thin = 1
            return False
        self.done_ms = now_ms
        return True

    def row(self, mark=None):
        b_r, b_mark = mark if mark else ("", "")
        q = float(self.hop["q"])
        late = self.first_ms - self.at
        return ticket(self.hop, self.kind, self.at, ms=self.done_ms, late_ms=late, live=1, book_ms=self.book_ms,
                      bid=self.bid, ask=self.ask, mid=self.mid, fill=self.paid / q, filled=q, levels=self.levels,
                      parts=self.parts, thin=self.thin, source=self.source, b_r=b_r, b_mark=b_mark,
                      status="walked" if late <= rule.ENTRY_LATE and self.source == "ws" else "walked late")


# ------------------------------------------------------------------------------------------------------- scoring
def lighter_fundings(market_id, a, b):
    """[(ms, signed rate per settlement)] in [a, b], signed positive when longs pay (R355's reader)."""
    rows = carrylane._lighter("fundings", market_id=market_id, resolution="1h", start_timestamp=a // 1000,
                              end_timestamp=b // 1000, count_back=0).get("fundings") or []
    return sorted((int(x["timestamp"]) * 1000, (1.0 if x["direction"] == "long" else -1.0) * float(x["rate"]) / 100)
                  for x in rows)


def walked(t):
    """A walk row's {"ms", "mid", "fill"} when it filled the whole quantity, else None."""
    if not t or t.get("status") not in ("entered", "walked", "walked late"):
        return None
    try:
        out = {"ms": int(float(t["ms"])), "mid": float(t["mid"]), "fill": float(t["fill"])}
    except (KeyError, TypeError, ValueError):
        return None
    return out if all(math.isfinite(v) for v in (out["mid"], out["fill"])) else None


def due(now_ms, tickets=None):
    """Entered hops whose primary exit is at least 20 minutes old and not yet scored: [(hop, its walks)]."""
    done = {r["hop"] for r in read("scored")}
    return [(hop, k) for hop, k in tickets_by_hop(tickets).items()
            if hop not in done and entered(k) and "out60" in k
            and now_ms >= int(float(k["out60"]["ms"])) + rule.SCORE_AFTER]


def score_hop(hop, k, rates, now_ms):
    """One hop's scored row from its walks and Lighter's settlements [(ms, rate)] around T, or None while the
    settlement in the hold is not yet in Lighter's history (after 24 h: funding 0, flagged)."""
    ent, ext = k["in10"], k["out60"]
    e0, x0 = walked(ent), walked(ext)
    if not (e0 and x0):
        return None
    T = int(ent["T"])
    held = [(t, r) for t, r in rates if e0["ms"] < t <= x0["ms"]]
    missing = not held
    if missing and now_ms < T + rule.FUND_WAIT:
        return None
    d, fee = int(ent["d"]), float(ent["fee_bp"])
    row = {**{c: ent[c] for c in ("hop", "T", "symbol", "lighter", "d", "e", "r")},
           "theta_book": rule.theta_book(float(ent["e"])), "entry_ms": e0["ms"], "exit_ms": x0["ms"],
           "exit_late_ms": int(float(ext["late_ms"])), "exit_source": ext["source"],
           "on_time": int(float(ent["late_ms"])) <= rule.ENTRY_LATE,
           "rates": " ".join(f"{t}:{r:.6g}" for t, r in held), "fund_missing": int(missing),
           **rule.leg(d, e0, x0, rates, fee)}
    for a, b in rule.VARIANTS:
        ea, xb = walked(k.get(rule.NAMES[a])), walked(k.get(rule.NAMES[b]))
        row[f"{rule.NAMES[a]}_{rule.NAMES[b]}"] = rule.leg(d, ea, xb, rates, fee)["net1"] if ea and xb else ""
    return row


def fundings_for(k):
    T = int(k["in10"]["T"])
    return lighter_fundings(int(k["in10"]["market_id"]), T - 2 * H, T + 2 * H)


def score_due(now_ms, tickets=None):
    """Scored rows for every hop due (the `score` command; the daemon does the same a minute at a time)."""
    new = []
    for hop, k in due(now_ms, tickets):
        try:
            row = score_hop(hop, k, fundings_for(k), now_ms)
        except Exception as e:  # noqa: BLE001 - retried next time
            log("funding read failed", hop, e)
            continue
        if row:
            new.append(row)
    return new


def _finite(v, nd=6):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return round(v, nd) if math.isfinite(v) else None


def status(now_ms=None, write=True):
    """The lane's state; the daemon writes it to status.json every minute, the `status` command only prints it."""
    now_ms = now_ms or clock_ms()
    tickets, scored, decs = read("tickets"), read("scored"), read("decisions")
    prim = rule.primary(scored)
    state, text = rule.verdict(prim, now_ms)
    nets = [float(r["net1"]) for r in prim]
    mu, t = rule.decide_stats(nets, [r["T"] for r in prim])
    g = gate.go_real(nets, [r["T"] for r in prim])
    k = tickets_by_hop(tickets)
    mean = lambda rs, c: _finite(np.mean([float(r[c]) for r in rs])) if rs else None

    def book(rows):
        return {"scored": len(rows), "net1": mean(rows, "net1"), "net2": mean(rows, "net2"), "net3": mean(rows, "net3"),
                "hit": _finite(np.mean([float(r["net1"]) > 0 for r in rows]), 3) if rows else None}

    variants = {}
    for a, b in rule.VARIANTS:
        c = f"{rule.NAMES[a]}_{rule.NAMES[b]}"
        v = [float(r[c]) for r in prim if r.get(c) not in ("", None)]
        variants[c] = {"n": len(v), "net1": _finite(np.mean(v)) if v else None}
    s = {"registry": REGISTRY, "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_ms / 1000)),
         "state": state, "decision": text, "scored": len(prim),
         "mean_net": _finite(mu), "mean_net_2x": mean(prim, "net2"), "mean_net_3x": mean(prim, "net3"),
         "t_cr1": _finite(t, 3), "trimmed10": _finite(rule.trimmed(nets)),
         "leave_two_coins_out": _finite(rule.leave_two_coins_out(nets, [r["symbol"] for r in prim])),
         "go_real": {"pass": g["pass"], "n": g["n"], "mean": _finite(g["mean"]), "hit": _finite(g["hit"], 3),
                     "worst": _finite(g["worst"]), "n_clusters": g["n_clusters"], "checks": g["checks"]},
         "decisions": len(decs), "decision_errors": sum(1 for x in decs if x.get("error")),
         "selected": sum(int(x["selected"] or 0) for x in decs),
         "tickets": sum(1 for x in k.values() if entered(x)),
         "open": sum(1 for x in k.values() if entered(x) and "out60" not in x),
         "not_entered": sum(1 for x in k.values() if "in10" in x and not entered(x)),
         "rest_exits": sum(1 for x in k.values() if x.get("out60", {}).get("source") == "rest"),
         "books": {"primary th0.3%": book(prim),
                   "th0.5%": book([r for r in prim if float(r["theta_book"]) >= 0.5]),
                   "all scored": book(scored)},
         "variants (1x, primary hops)": variants}
    if write:
        JOURNAL.mkdir(parents=True, exist_ok=True)
        (JOURNAL / "status.json").write_text(json.dumps(s, indent=1) + "\n")
    return s


# ------------------------------------------------------------------------------------------------------- daemon
def ssl_ctx():
    return ssl.create_default_context(cafile=CA) if Path(CA).exists() else ssl.create_default_context()


async def sleep_until(ms):
    while True:
        left = (ms - clock_ms()) / 1000
        if left <= 0:
            return
        await asyncio.sleep(min(left, 30))


async def ws_loop(url, subs, handler, stop_ms, name, ping=None, on_drop=None):
    """A websocket read until stop_ms, reconnecting (1 s, doubling to 10 s) after any error or a Gap."""
    import websockets
    delay = 1.0
    while clock_ms() < stop_ms:
        try:
            async with websockets.connect(url, ssl=ssl_ctx(), open_timeout=15, close_timeout=2,
                                          max_size=2**24) as ws:
                for s in subs:
                    await ws.send(json.dumps(s))
                pinged = time.time()
                while clock_ms() < stop_ms:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), max(0.1, min(5.0, (stop_ms - clock_ms()) / 1000)))
                    except asyncio.TimeoutError:
                        raw = None
                    if ping and time.time() - pinged > PING_S:
                        await ws.send(json.dumps(ping))
                        pinged = time.time()
                    if raw is not None:
                        handler(json.loads(raw))
                return
        except Exception as e:  # noqa: BLE001 - a dropped stream reconnects; its gap is in the recording
            log(f"{name}: {type(e).__name__}: {e}"[:200])
            if on_drop:
                on_drop()
        await asyncio.sleep(max(0.0, min(delay, (stop_ms - clock_ms()) / 1000)))
        delay = min(delay * 2, 10.0)


def retry(fn, tries=3, wait=5.0):
    for k in range(tries):
        try:
            return fn()
        except Exception:  # noqa: BLE001
            if k == tries - 1:
                raise
            time.sleep(wait)


def feed_rates():
    """Binance's rate for each Lighter market as Lighter's public funding-rates feed reports it, in 8 h terms (the
    trigger named in the claim; logged beside Binance's own rate)."""
    rows = carrylane._lighter("funding-rates").get("funding_rates") or []
    return {int(r["market_id"]): float(r["rate"]) for r in rows if r.get("exchange") == "binance"}


async def decision_window(T):
    """T - 1 h - 5 min to T - 1 h + 20 s: both streams, Lighter's market list, then select()."""
    seen, stats, meta = {}, {}, {}
    stop = T - H + rule.DECIDE_AT
    bt = asyncio.create_task(ws_loop(BINANCE + "!markPrice@arr", [], lambda m: on_binance_all(m, seen, meta), stop,
                                     "binance markPrice"))
    lt = asyncio.create_task(ws_loop(LIGHTER_WS, [{"type": "subscribe", "channel": "market_stats/all"}],
                                     lambda m: on_lighter_stats(m, stats), stop, "lighter market_stats",
                                     ping={"type": "ping"}))
    details, err, feed = None, "", {}
    try:
        details = await asyncio.to_thread(retry, carrylane._lighter_details)
    except Exception as e:  # noqa: BLE001 - the decision is logged with its error
        err = f"lighter details: {e}"[:200]
    try:
        feed = await asyncio.to_thread(feed_rates)
    except Exception as e:  # noqa: BLE001 - a logged column only
        log("funding-rates feed failed", e)
    await asyncio.gather(bt, lt)
    rows, dec, hops = await asyncio.to_thread(select, T, clock_ms(), seen, stats, details, meta.get("first_ms"),
                                              feed, rest_cost)        # the cost gate reads REST books
    if err:
        dec["error"] = "; ".join(x for x in (dec["error"], err) if x)
    append("signals", rows)
    append("decisions", [dec])
    log(f"decision T {time.strftime('%m-%d %H:%M', time.gmtime(T / 1000))}: {dec['binance']} Binance perps, "
        f"{dec['eligible']} on a 4/8 h cycle at T, {dec['on_lighter']} on Lighter, {dec['candidates']} candidates, "
        f"{len(hops)} selected {dec['error']}")
    return hops


async def book_window(T, hops):
    """T - 7 min to T + 6 min for the selected hops: books, trades and Binance's marks recorded, and the paper walks.
    Returns the exits it could not finish (owed to the REST book)."""
    await sleep_until(T + rule.BOOK_FROM)
    stop = T + rule.BOOK_TO
    rec = Recording(T, hops)
    by_market = {h["market_id"]: h for h in hops}
    by_symbol = {h["symbol"]: h for h in hops}
    books = {m: Book() for m in by_market}
    marks = {}

    def drop():
        for b in books.values():
            b.live = False

    subs = [{"type": "subscribe", "channel": f"{c}/{m}"} for m in by_market for c in ("order_book", "trade",
                                                                                         "market_stats")]
    lt = asyncio.create_task(ws_loop(LIGHTER_WS, subs, lambda m: on_lighter(m, books, rec, by_market, clock_ms()),
                                     stop, "lighter books", ping={"type": "ping"}, on_drop=drop))
    streams = "/".join(f"{s.lower()}@markPrice@1s/{s.lower()}@aggTrade" for s in by_symbol)
    bt = asyncio.create_task(ws_loop(BINANCE + streams, [], lambda m: on_binance_sym(m, marks, rec, by_symbol), stop,
                                     "binance marks"))

    async def sampler():
        while clock_ms() < stop:
            rec.sample(books, by_market, clock_ms())
            await asyncio.sleep(1.0 - time.time() % 1.0)

    done = tickets_by_hop()
    owed = []

    async def exits(off):
        await sleep_until(T + off)
        live = [Exit(h, off) for h in hops if entered(done.get(h["hop"], {})) and rule.NAMES[off] not in
                done.get(h["hop"], {})]
        while live:
            now = clock_ms()
            for x in list(live):
                if x.step(books.get(x.hop["market_id"]), now):
                    append("tickets", [x.row(marks.get(x.hop["symbol"]))])
                    live.remove(x)
            if not live or now >= stop:
                break
            await asyncio.sleep(1.0)
        owed.extend(x for x in live if x.off == rule.PRIMARY[1])

    async def entries():
        for off in rule.ENTRIES:
            at = T + off
            todo = [h for h in hops if rule.NAMES[off] not in done.get(h["hop"], {})]
            if clock_ms() > at + rule.ENTRY_LATE:       # the daemon was down at the instant
                rows = [ticket(h, rule.NAMES[off], at, ms=clock_ms(), late_ms=clock_ms() - at, live=0, source="ws",
                               status="missed: daemon down" + (": not entered" if off == rule.PRIMARY[0] else ""))
                        for h in todo]
            else:
                await sleep_until(at)
                rows = [entry_walk(h, off, books.get(h["market_id"]), marks.get(h["symbol"]), clock_ms()) for h in todo]
            append("tickets", rows)
            for r in rows:
                done.setdefault(r["hop"], {})[r["kind"]] = r

    tasks = [lt, bt, asyncio.create_task(sampler())]
    await entries()
    await asyncio.gather(*(exits(off) for off in rule.EXITS))
    await asyncio.gather(*tasks)
    append("recordings", rec.write())
    return owed


def owed_exits(now_ms):
    """Entered hops without a primary exit once their book window is over (a restart, or a stream that never
    recovered): each is walked on the REST book."""
    out = []
    for hop, k in tickets_by_hop().items():
        if entered(k) and "out60" not in k and now_ms >= int(k["in10"]["T"]) + rule.BOOK_TO:
            t = k["in10"]
            h = {"hop": hop, "T": int(t["T"]), "symbol": t["symbol"], "lighter": t["lighter"],
                 "market_id": int(t["market_id"]), "d": int(t["d"]), "e": float(t["e"]), "r": float(t["r"]),
                 "q": float(t["q"]), "fee_bp": float(t["fee_bp"])}
            out.append(Exit(h, rule.PRIMARY[1]))
    return out


def rest_exit_step(x, book):
    """One REST walk of what an exit still owes; True when it has filled (its ticket is then written)."""
    if x.step(book, clock_ms(), source="rest"):
        append("tickets", [x.row()])
        log("exit on the REST book", x.hop["hop"])
        return True
    return False


async def housekeeping(state):
    """Every minute: owed exits on the REST book, scores, status. Journals are read and written on the loop's thread;
    only the REST reads run in a worker thread."""
    while True:
        try:
            now = clock_ms()
            owed = {x.hop["hop"]: x for x in state["owed"]}
            for x in owed_exits(now):
                owed.setdefault(x.hop["hop"], x)
            keep = []
            for x in owed.values():
                try:
                    b = await asyncio.to_thread(retry, lambda: rest_book(x.hop["market_id"]), 2, 2.0)
                except Exception as e:  # noqa: BLE001 - tried again next minute
                    log("REST book failed", x.hop["hop"], e)
                    b = None
                if not (b and rest_exit_step(x, b)):
                    keep.append(x)
            state["owed"] = keep
            rows = []
            for hop, k in due(clock_ms()):
                try:
                    rates = await asyncio.to_thread(fundings_for, k)
                except Exception as e:  # noqa: BLE001 - retried next minute
                    log("funding read failed", hop, e)
                    continue
                row = score_hop(hop, k, rates, clock_ms())
                if row:
                    rows.append(row)
            append("scored", rows)
            if rows or len(keep) < len(owed) or clock_ms() - state.get("status_ms", 0) >= H:
                s = status(clock_ms())                  # on a change, else hourly: the panel reads its age
                state["status_ms"] = clock_ms()
                if rows:
                    log("scored", len(rows), s["state"], s["decision"])
        except Exception as e:  # noqa: BLE001 - next minute retries
            log("housekeeping failed", e)
        await asyncio.sleep(60 - time.time() % 60 + 2)


def next_T(now_ms):
    """The first 4 h settlement whose decision instant (T - 1 h + 20 s) is still ahead."""
    return ((now_ms + H - rule.DECIDE_AT) // rule.STEP + 1) * rule.STEP


async def daemon():
    log("settlelit_fwd run started")
    state = {"owed": []}
    house = asyncio.create_task(housekeeping(state))
    while True:
        now = clock_ms()
        decided = {int(r["T"]) for r in read("decisions")}
        T = max(decided, default=0)
        if T and now < T + rule.BOOK_TO and selected_hops(T):       # a restart inside a decided window
            state["owed"] += await book_window(T, selected_hops(T))
            status()
            continue
        T = next_T(now)
        while T in decided:
            T += rule.STEP
        await sleep_until(T - H - rule.WINDOW)
        await asyncio.to_thread(check)                  # a changed PREREG or rule stops the lane here, loudly
        try:
            hops = await decision_window(T)
        except Exception as e:  # noqa: BLE001 - the decision is logged; the next settlement is tried
            log("decision failed", e)
            append("decisions", [{"decided_ms": clock_ms(), "T": T, "late_s": "", "error": f"{e}"[:200]}])
            continue
        status()
        if hops:
            state["owed"] += await book_window(T, hops)
            status()
        if house.done():
            house = asyncio.create_task(housekeeping(state))


def run():
    """The lane's daemon, in the foreground."""
    with writer_lock():
        asyncio.run(daemon())


def ensure():
    """The forward loop's task: start the daemon when no writer holds the journal lock; otherwise report it running."""
    JOURNAL.mkdir(parents=True, exist_ok=True)
    f = open(JOURNAL / ".writer.lock", "a")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        f.close()
        try:
            s = json.loads((JOURNAL / "status.json").read_text())
        except (OSError, ValueError):
            s = {}
        log("settlelit_fwd running:", s.get("decision", "no status yet"))
        return 0
    fcntl.flock(f, fcntl.LOCK_UN)
    f.close()
    check()                                   # never start a lane whose PREREG or rule changed
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a") as out:
        subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "run"], cwd=ROOT, stdout=out,
                         stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
    log("settlelit_fwd started; log", LOG)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", default="ensure", choices=["ensure", "run", "status", "score"])
    a = ap.parse_args(argv)
    if a.cmd == "ensure":
        return ensure()
    if a.cmd in ("run", "score"):
        check()
    if a.cmd == "run":
        run()
    elif a.cmd == "score":
        with writer_lock():
            append("scored", score_due(clock_ms()))
            print(json.dumps(status(), indent=1))
    else:
        print(json.dumps(status(write=False), indent=1))


if __name__ == "__main__":
    main()
