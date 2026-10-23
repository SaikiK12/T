"""Top-of-book and trade tape, one row per (venue, coin, second), for order-flow research on 1-60 s horizons (M264).

The raw streams are too large to keep: Binance's bookTicker alone sends about 1,400 updates a second for 12 coins. So
the recorder (scripts/record_tape.py) keeps, for every second that had an update, what a short-horizon study needs:
- book: the last best bid and ask with their sizes (and, on MEXC, the size on the top 5 levels), the order-flow
  imbalance summed over the second's updates (Cont, Kukanov and Stoikov 2014), the update count and the worst receive
  lag;
- trades: buyer- and seller-initiated quantity and counts, notional, and the first, last, lowest and highest price.

Sizes are in coins (MEXC contracts times the contract size), prices in USDT, `s` is the second's start in ms on the
exchange's clock and `sym` the base coin (BTC), the same on both venues. A second is final once the recorder's clock
is `SETTLE_MS` past its end; an event for a second already written is counted in `late` and dropped. History cannot be
backfilled: the record starts when the recorder does, and data/tape/sessions.csv lists every connection with its gap.
"""
import math

import pandas as pd

from lab.mexc_depth import parse_depth_levels

SETTLE_MS = 2_000
BOOK = ("s", "sym", "bid", "bid_sz", "ask", "ask_sz", "bid_sz5", "ask_sz5", "ofi", "n", "lag_ms")
TRADES = ("s", "sym", "buy_qty", "sell_qty", "buy_n", "sell_n", "notional", "px_first", "px_last", "px_min", "px_max")


def ofi(prev, cur):
    """Order-flow imbalance of one top-of-book update, in coins: size added at or above the old best bid minus size
    added at or below the old best ask (Cont, Kukanov and Stoikov 2014, eq. 2). prev and cur are (bid, bid_sz, ask,
    ask_sz)."""
    pb, pbs, pa, pas = prev
    b, bs, a, as_ = cur
    return ((bs if b >= pb else 0.0) - (pbs if b <= pb else 0.0)
            - (as_ if a <= pa else 0.0) + (pas if a >= pa else 0.0))


class Tape:
    """Buckets book and trade events per (venue, sym, second) until `drain` hands them out."""

    def __init__(self, settle_ms=SETTLE_MS):
        self.settle_ms = settle_ms
        self.prev = {}                     # (venue, sym) -> the last (bid, bid_sz, ask, ask_sz)
        self.book, self.trades = {}, {}    # (venue, sym, s) -> running row
        self.done = {}                     # venue -> every second before this is written
        self.seen = set()
        self.late = 0

    def reset(self, venue):
        """After a reconnect the first update has no predecessor: its imbalance is not counted."""
        self.prev = {k: v for k, v in self.prev.items() if k[0] != venue}

    def _second(self, venue, t_ms):
        self.seen.add(venue)
        s = int(t_ms) // 1000 * 1000
        if s < self.done.get(venue, -1):
            self.late += 1
            return None
        return s

    def on_book(self, venue, sym, t_ms, bid, bid_sz, ask, ask_sz, recv_ms, bid_sz5=math.nan, ask_sz5=math.nan):
        s = self._second(venue, t_ms)
        if s is None:
            return
        cur = (bid, bid_sz, ask, ask_sz)
        e = ofi(self.prev[venue, sym], cur) if (venue, sym) in self.prev else 0.0
        self.prev[venue, sym] = cur
        lag = int(recv_ms - t_ms)
        r = self.book.get((venue, sym, s))
        if r is None:
            self.book[venue, sym, s] = [bid, bid_sz, ask, ask_sz, bid_sz5, ask_sz5, e, 1, lag]
        else:
            r[:6] = [bid, bid_sz, ask, ask_sz, bid_sz5, ask_sz5]
            r[6] += e
            r[7] += 1
            r[8] = max(r[8], lag)

    def on_trade(self, venue, sym, t_ms, price, qty, side):
        """side +1 when the buyer took liquidity, -1 when the seller did."""
        s = self._second(venue, t_ms)
        if s is None:
            return
        r = self.trades.get((venue, sym, s))
        if r is None:
            r = self.trades[venue, sym, s] = [0.0, 0.0, 0, 0, 0.0, price, price, price, price]
        if side > 0:
            r[0] += qty
            r[2] += 1
        else:
            r[1] += qty
            r[3] += 1
        r[4] += price * qty
        r[6] = price
        r[7] = min(r[7], price)
        r[8] = max(r[8], price)

    def drain(self, now_ms=None):
        """{venue: (book DataFrame, trades DataFrame)} of the seconds that are final at now_ms (all of them when
        None), sorted by (s, sym); they leave the buffer and later events for them count as late."""
        cut = math.inf if now_ms is None else now_ms - self.settle_ms - 1000
        out = {}
        for store, cols, i in ((self.book, BOOK, 0), (self.trades, TRADES, 1)):
            keys = [k for k in store if k[2] <= cut]
            for k in keys:
                out.setdefault(k[0], ([], []))[i].append((k[2], k[1], *store.pop(k)))
        if now_ms is not None:
            for v in self.seen:
                self.done[v] = max(self.done.get(v, -1), (int(cut) // 1000 + 1) * 1000)
        frames = {}
        for v, (b, t) in out.items():
            frames[v] = (pd.DataFrame(b, columns=BOOK).sort_values(["s", "sym"], ignore_index=True),
                         pd.DataFrame(t, columns=TRADES).sort_values(["s", "sym"], ignore_index=True))
        return frames


def combine(df, kind):
    """Merge rows that share (s, sym), as two recorder runs can both write the second of a restart: the later row's
    book state, summed imbalance, counts and quantities, the first and last price in file order. df in file order."""
    if not df.duplicated(["s", "sym"]).any():
        return df.sort_values(["s", "sym"], ignore_index=True)
    if kind == "book":
        how = {c: "last" for c in ("bid", "bid_sz", "ask", "ask_sz", "bid_sz5", "ask_sz5")}
        how.update(ofi="sum", n="sum", lag_ms="max")
    else:
        how = {c: "sum" for c in ("buy_qty", "sell_qty", "buy_n", "sell_n", "notional")}
        how.update(px_first="first", px_last="last", px_min="min", px_max="max")
    out = df.groupby(["s", "sym"], sort=True, as_index=False).agg(how)
    return out[list(BOOK if kind == "book" else TRADES)]


def binance(msg, kind):
    """Events from one Binance USD-M combined-stream message: ("book", sym, t, bid, bid_sz, ask, ask_sz) for
    bookTicker, ("trade", sym, t, price, qty, side) for aggTrade (m true: the buyer was the maker, so a sell)."""
    d = msg.get("data") or {}
    sym = str(d.get("s", ""))[:-4]
    if kind == "book" and d.get("e") == "bookTicker":
        return [("book", sym, d["T"], float(d["b"]), float(d["B"]), float(d["a"]), float(d["A"]))]
    if kind == "trade" and d.get("e") == "aggTrade":
        return [("trade", sym, d["T"], float(d["p"]), float(d["q"]), -1 if d["m"] else 1)]
    return []


def mexc(msg, sizes):
    """Events from one MEXC contract push: push.depth.full (top 5 levels, sizes in contracts) and push.deal (T 1 a
    taker buy, 2 a taker sell). sizes: {"BTC_USDT": contract size in coins}; unknown symbols give no event."""
    ch, symbol = msg.get("channel"), msg.get("symbol")
    cs = sizes.get(symbol)
    if cs is None or ch not in ("push.depth.full", "push.deal"):
        return []
    sym = symbol[:-5]
    d = msg.get("data")
    if ch == "push.depth.full":
        try:
            bids = parse_depth_levels(d.get("bids") or [])
            asks = parse_depth_levels(d.get("asks") or [])
            return [("book", sym, msg.get("ts", d.get("cts")), bids[0].price,
                     bids[0].base_quantity(cs), asks[0].price, asks[0].base_quantity(cs),
                     sum(level.base_quantity(cs) for level in bids[:5]),
                     sum(level.base_quantity(cs) for level in asks[:5]))]
        except (AttributeError, TypeError, ValueError):
            # Bad or incomplete snapshots must not become plausible zero-depth observations.
            return []
    deals = d if isinstance(d, list) else [d]
    return [("trade", sym, x["t"], float(x["p"]), x["v"] * cs, 1 if x["T"] == 1 else -1) for x in deals]


def lighter(msg, names):
    """Events from one Lighter websocket message: update/ticker (best bid and offer, stamped in microseconds by the
    matching engine) and update/trade (trades and liquidations; is_maker_ask true means the buyer took liquidity).
    names: {market_id: base coin}; other markets give no event. The trade snapshot sent on subscribing is skipped: its
    prints are older than the connection."""
    kind, ch = msg.get("type", ""), str(msg.get("channel", ""))
    try:
        sym = names.get(int(ch.split(":")[1]))
    except (IndexError, ValueError):
        return []
    if sym is None:
        return []
    if kind in ("update/ticker", "subscribed/ticker"):
        t = msg.get("ticker") or {}
        a, b = t.get("a") or {}, t.get("b") or {}
        if not a.get("price") or not b.get("price"):
            return []
        return [("book", sym, int(t.get("last_updated_at", msg.get("last_updated_at", 0))) // 1000,
                 float(b["price"]), float(b["size"]), float(a["price"]), float(a["size"]))]
    if kind == "update/trade":
        prints = (msg.get("trades") or []) + (msg.get("liquidation_trades") or [])
        return [("trade", sym, int(x["timestamp"]), float(x["price"]), float(x["size"]),
                 1 if x.get("is_maker_ask") else -1) for x in prints]
    return []
