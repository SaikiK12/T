"""xfund_fwd (R278): R275's cross-venue funding carry books forward on paper, as set out in
experiments/xfund_fwd/PREREG.md. Paper only: nothing here can place an order.

Each run:
1. Data. Refreshes, for every coin of the frozen R275 table that a book can trade, the venues' hourly closes (Hyperliquid:
   daily) and funding settlements into data/xfund_fwd/<venue>/{prices,funding}/<symbol>.parquet. A file is seeded once
   from the archive (rows from WARM on), then extended from the public APIs; API rows replace archive rows on overlap and
   the differences are counted in status.json. Only closed bars are kept.
2. Days. For each day D whose 00:00 UTC has passed and is not yet in the journal: books the interval D - 1 -> D for the
   pairs held, then decides exits and entries at day D with lab.xfund (the line-for-line twin of qx spread; R275's
   trades and daily net are reproduced exactly on the archive, see the PREREG). Waits (exits without writing) while a
   venue's closes for day D are missing, up to READY_WAIT_H hours after 00:00.
3. Tickets. Every entry and exit is appended to journal/tickets.csv with day D's closes and, on an on-time tick, the
   venues' live mid prices at the moment of the decision (the paper fill). Days are appended to journal/days.csv.

Accounting (both reported; `net` is the decided one):
- close: R275's own, day D close to day D + 1 close, funding of day D + 1, 7 / 14 / 21 bp per leg per side.
- fill: the same plus the gap between each ticket's live mid and day D's close, on both legs, booked on the interval
  that starts at D. A replayed or late ticket has no live fill and books the close.

usage: python scripts/forward_xfund.py [--no-fetch]        (parity with R275: scripts/xfund_parity.py)
"""
import argparse
import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, live, mexc, prereg, xfund  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402

LANE = ROOT / "experiments" / "xfund_fwd"
J = LANE / "journal"
SYMBOLS = ROOT / "experiments" / "xfund_v1" / "symbols.csv"
DATA = data.ROOT / "xfund_fwd"
DAY, H = xfund.DAY, xfund.H
WARM = "2026-08-01"                 # the daily axis starts here; data before it is not read
ON_TIME = "2026-10-22"              # the first day whose decisions are ticketed live
READY_WAIT_H = 6
COSTS = (0.0007, 0.0014, 0.0021)
CORR = (30, 0.9, 20)
STALE_DAYS = 3                      # a leg not fresh on this many days in a row closes (forced)
# book -> (venue set, lookback days, entry threshold, slots, why it is here)
BOOKS = {"A": ("gate+hyperliquid", 14, 0.05, 20, "R275's best passing book by 1x t"),
         "B": ("binance+mexc", 14, 0.10, 20, "R275's best passing book with a MEXC leg"),
         "C": ("gate+mexc", 7, 0.10, 20, "post hoc: R275's best MEXC book by annual net")}
NAMES = ["binance", "gate", "hyperliquid", "mexc"]
# venue -> (archive prices folder, archive volume column, archive funding folder, bar hours)
ARCHIVE = {"binance": ("klines_1h", "volume", "fundingRate", 1),
           "gate": ("gate_hist/open/candlesticks_1h", "vol_contracts", "gate_hist/open/funding_applies", 1),
           "hyperliquid": ("hyperliquid/candles_1d", "volume", "hyperliquid/funding", 24),
           "mexc": ("mexc_hist/klines_1h", "vol", "mexc_hist/funding", 1)}
GATE = "https://api.gateio.ws/api/v4/futures/usdt"
HL = "https://api.hyperliquid.xyz/info"
TICKET_COLS = ["run", "day", "book", "action", "coin", "long", "short", "spread_ann", "forced", "kind",
               "close_long", "close_short", "fill_long", "fill_short"]
DAY_COLS = ["day", "book", "kind", "run", "held", "legs", "gross", "funding", "fill_adj", "net", "net_2x", "net_3x",
            "net_close", "net_close_2x", "net_close_3x"]
DEC_COLS = ["run", "day", "book", "kind", "exits", "entries", "held", "ready"]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)
ms = lambda s: int(pd.Timestamp(s, tz="UTC").value // 10**6)
day_str = lambda t0, d: str((pd.Timestamp(t0, unit="ms", tz="UTC") + pd.Timedelta(days=d)).date())


# ---------------------------------------------------------------- venue clients (public endpoints only)

def _json(url, body=None, tries=5):
    delay, err = 1.0, None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, json.dumps(body).encode() if body is not None else None,
                                         {"Content-Type": "application/json", "User-Agent": "lab-paper/1"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            err = e
            if e.code in (400, 404):
                break
        except (OSError, ValueError) as e:
            err = e
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"{url}: {err}")


def gate_prices(sym, start, end):
    out, s = [], start // 1000
    while s < end // 1000:
        e = min(end // 1000, s + 1999 * 3600)
        rows = _json(f"{GATE}/candlesticks?" + urllib.parse.urlencode(
            {"contract": sym, "interval": "1h", "from": s, "to": e}))
        out += rows or []
        s = e + 3600
    df = pd.DataFrame(out)
    if df.empty:
        return pd.DataFrame(columns=["t", "close", "vol_contracts"])
    return pd.DataFrame({"t": df.t.astype(np.int64) * 1000, "close": df.c.astype(float),
                         "vol_contracts": df.v.astype(float)})


def gate_funding(sym, start, end):
    """Gate returns the newest settlements first, at most 1000 a call: pages walk back from `end`."""
    out, e = [], end // 1000
    while e >= start // 1000:
        rows = _json(f"{GATE}/funding_rate?" + urllib.parse.urlencode(
            {"contract": sym, "limit": 1000, "from": start // 1000, "to": e}))
        if not rows:
            break
        out += rows
        low = min(int(r["t"]) for r in rows)
        if len(rows) < 1000 or low <= start // 1000:
            break
        e = low - 1
    df = pd.DataFrame(out)
    if df.empty:
        return pd.DataFrame(columns=["t", "rate"])
    return pd.DataFrame({"t": df.t.astype(np.int64) * 1000, "rate": df.r.astype(float)})


def hl_prices(coin, start, end):
    rows = _json(HL, {"type": "candleSnapshot", "req": {"coin": coin, "interval": "1d", "startTime": start,
                                                         "endTime": end}})
    df = pd.DataFrame(rows or [])
    if df.empty:
        return pd.DataFrame(columns=["t", "close", "volume"])
    return pd.DataFrame({"t": df.t.astype(np.int64), "close": df.c.astype(float), "volume": df.v.astype(float)})


def hl_funding(coin, start, end):
    out, s = [], start
    while s < end:
        rows = _json(HL, {"type": "fundingHistory", "coin": coin, "startTime": s, "endTime": end})
        if not rows:
            break
        out += rows
        last = int(rows[-1]["time"])
        if last <= s or len(rows) < 500:
            break
        s = last + 1
    df = pd.DataFrame(out)
    if df.empty:
        return pd.DataFrame(columns=["t", "rate"])
    return pd.DataFrame({"t": df.time.astype(np.int64), "rate": df.fundingRate.astype(float)})


def binance_prices(sym, start, end):
    df = live.fetch_klines(sym, start, end)
    return df[["t", "close", "volume"]].astype({"t": np.int64, "close": float, "volume": float})


def mexc_prices(sym, start, end):
    df = mexc.fetch_klines(sym, start, end)
    return df[["t", "close", "vol"]].astype({"t": np.int64, "close": float, "vol": float})


def mexc_funding(sym, start, end):
    return mexc.funding_history(sym, start, end)[["t", "rate"]]


CLIENTS = {"binance": (binance_prices, lambda s, a, b: live.funding_history(s, a, b), 4),
           "gate": (gate_prices, gate_funding, 4),
           "hyperliquid": (hl_prices, hl_funding, 2),
           "mexc": (mexc_prices, mexc_funding, 4)}


def mids():
    """Live mid prices per venue symbol, one bulk request per venue: {venue: {symbol: mid}}."""
    out = {}
    try:
        out["binance"] = {r["symbol"]: (float(r["bidPrice"]) + float(r["askPrice"])) / 2
                          for r in live.get("fapi/v1/ticker/bookTicker")}
    except Exception as e:                 # noqa: BLE001 - a venue that fails gives no fill; the close is booked
        log("binance mids failed", e)
    try:
        out["gate"] = {r["contract"]: (float(r["highest_bid"]) + float(r["lowest_ask"])) / 2
                       for r in _json(f"{GATE}/tickers") if r.get("highest_bid") and r.get("lowest_ask")}
    except Exception as e:                 # noqa: BLE001
        log("gate mids failed", e)
    try:
        out["hyperliquid"] = {k: float(v) for k, v in _json(HL, {"type": "allMids"}).items()}
    except Exception as e:                 # noqa: BLE001
        log("hyperliquid mids failed", e)
    try:
        out["mexc"] = {r["symbol"]: (float(r["bid1"]) + float(r["ask1"])) / 2 for r in mexc.get("ticker")
                       if r.get("bid1") and r.get("ask1")}
    except Exception as e:                 # noqa: BLE001
        log("mexc mids failed", e)
    return out


def listed():
    """Live contract lists: {venue: set of symbols}; a venue that fails is left out (no forced exit from it)."""
    out = {}
    for v, fn in {"binance": lambda: set(live.perpetuals()),
                  "gate": lambda: {r["name"] for r in _json(f"{GATE}/contracts") if not r.get("in_delisting")},
                  "hyperliquid": lambda: {u["name"] for u in _json(HL, {"type": "meta"})["universe"]
                                          if not u.get("isDelisted")},
                  "mexc": lambda: set(mexc.contracts(refresh=True).symbol)}.items():
        try:
            out[v] = fn()
        except Exception as e:             # noqa: BLE001
            log(f"{v} contract list failed", e)
    return out


# ---------------------------------------------------------------- the forward data root

def table():
    t = pd.read_csv(SYMBOLS, dtype=str).fillna("")
    need = {v for b in BOOKS.values() for v in b[0].split("+")}
    return t, need


def path(venue, kind, sym):
    return DATA / venue / kind / f"{sym}.parquet"


def merge(old, new, now_ms, bar_ms=None):
    """Old rows plus new ones (new wins on the same t), closed bars only; (frame, rows that changed on overlap)."""
    if bar_ms is not None and len(new):
        new = new[new.t + bar_ms <= now_ms]
    changed = 0
    if old is not None and len(old) and len(new):
        both = old.merge(new, on="t", suffixes=("_o", "_n"))
        c = [x[:-2] for x in both.columns if x.endswith("_o")]
        for k in c:
            a, b = both[f"{k}_o"].to_numpy(float), both[f"{k}_n"].to_numpy(float)
            changed += int((~np.isclose(a, b, rtol=1e-9, atol=1e-12, equal_nan=True)).sum())
    df = pd.concat([x for x in (old, new) if x is not None and len(x)]) if (old is not None and len(old)) or len(new) \
        else new
    return df.drop_duplicates("t", keep="last").sort_values("t", ignore_index=True), changed


def seed(venue, kind, sym, cols):
    """Archive rows from WARM on for one file, or None."""
    p_dir, vol, f_dir, _ = ARCHIVE[venue]
    p = data.ROOT / (p_dir if kind == "prices" else f_dir) / f"{sym}.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    df = df[df.t.astype(np.int64) >= ms(WARM)][cols].astype({"t": np.int64})
    if kind == "funding":
        df["t"] = df.t - df.t % H
        df = df.drop_duplicates("t", keep="last")
    return df.reset_index(drop=True)


def refresh(now_ms, fetch=True):
    """Bring every needed (venue, symbol) file up to now. Returns per-venue counts and failures."""
    t, need = table()
    jobs = sorted({(v, s) for v in need for s in t[v] if s})
    stats = {v: {"files": 0, "failed": [], "changed_on_overlap": 0} for v in need}

    def one(job):
        v, s = job
        bar = ARCHIVE[v][3] * H
        vol = ARCHIVE[v][1]
        pf, ff = path(v, "prices", s), path(v, "funding", s)
        old_p = pd.read_parquet(pf) if pf.exists() else seed(v, "prices", s, ["t", "close", vol])
        old_f = pd.read_parquet(ff) if ff.exists() else seed(v, "funding", s, ["t", "rate"])
        changed = 0
        try:
            if fetch:
                pfn, ffn, _ = CLIENTS[v]
                start_p = max(ms(WARM), int(old_p.t.max()) - 2 * DAY) if old_p is not None and len(old_p) else ms(WARM)
                start_f = max(ms(WARM), int(old_f.t.max()) - 2 * DAY) if old_f is not None and len(old_f) else ms(WARM)
                new_p = pfn(s, start_p, now_ms)
                new_f = ffn(s, start_f, now_ms)
                new_f = new_f.astype({"t": np.int64})
                new_f = new_f.assign(t=new_f.t - new_f.t % H)
                new_f = new_f[new_f.t <= now_ms].drop_duplicates("t", keep="last")
                old_p, c1 = merge(old_p, new_p, now_ms, bar)
                old_f, c2 = merge(old_f, new_f, now_ms)
                changed = c1 + c2
            for p, df in ((pf, old_p), (ff, old_f)):
                if df is not None and len(df):
                    p.parent.mkdir(parents=True, exist_ok=True)
                    df.to_parquet(p, index=False)
            return v, s, changed, None
        except Exception as e:             # noqa: BLE001 - one coin's failure leaves its file as it was
            return v, s, 0, str(e)[:200]

    by = {v: [j for j in jobs if j[0] == v] for v in need}
    with ThreadPoolExecutor(len(by)) as outer:
        def venue(v):
            with ThreadPoolExecutor(CLIENTS[v][2]) as ex:
                return list(ex.map(one, by[v]))
        for res in outer.map(venue, sorted(by)):
            for v, s, changed, err in res:
                stats[v]["files"] += 1
                stats[v]["changed_on_overlap"] += changed
                if err:
                    stats[v]["failed"].append(s)
    return stats


def universe(nd):
    """lab.xfund.Universe over the forward root, days 0..nd - 1 from WARM, venues in NAMES order."""
    t, need = table()
    t0 = ms(WARM)

    def load(row):
        out = []
        for v in NAMES:
            s = row[v].strip()
            if v not in need or not s:
                out.append(None)
                continue
            out.append(xfund.load_daily(path(v, "prices", s), path(v, "funding", s), ARCHIVE[v][1], ARCHIVE[v][3],
                                        t0, nd))
        return out

    with ThreadPoolExecutor(8) as ex:
        series = list(ex.map(load, [r for _, r in t.iterrows()]))
    return xfund.Universe(t.key.tolist(), NAMES, series, t0, nd, *CORR), t


def ready(u, need, d):
    """{venue: share of its coins fresh on day d over the share fresh on day d - 1}."""
    out = {}
    for j, v in enumerate(NAMES):
        if v not in need:
            continue
        s = [x[j] for x in u.series if x[j] is not None]
        prev = sum(bool(x.fresh[d - 1]) for x in s)
        out[v] = round(sum(bool(x.fresh[d]) for x in s) / prev, 3) if prev else 0.0
    return out


# ---------------------------------------------------------------- journal

def rows(name):
    p = J / name
    if not p.exists() or not p.stat().st_size:
        return []
    with p.open(newline="") as f:
        return list(csv.DictReader(f))


def append(name, cols, recs):
    if not recs:
        return
    p = J / name
    new = not p.exists() or p.stat().st_size == 0
    J.mkdir(parents=True, exist_ok=True)
    with open(p, "a", newline="") as f:
        w = csv.DictWriter(f, cols, lineterminator="\n")
        if new:
            w.writeheader()
        w.writerows(recs)


def journal():
    """(decisions, tickets, days) that belong to a completed run: a row counts only if a decision row of the same book
    and day carries its run stamp. A run appends tickets, then days, then decisions, so a run cut short leaves rows
    without a decision, and they are ignored."""
    dec = rows("decisions.csv")
    ok = {(r["book"], r["day"], r["run"]) for r in dec}
    tk = [r for r in rows("tickets.csv") if (r["book"], r["day"], r["run"]) in ok]
    dy = [r for r in rows("days.csv") if (r["book"], r["day"], r["run"]) in ok]
    return dec, tk, dy


def rebuild(t, tickets):
    """Each book's open pairs, replayed from its tickets in journal order (the journal is the book)."""
    key = {k: i for i, k in enumerate(t.key)}
    books = {b: xfund.Book([NAMES.index(v) for v in s.split("+")], l, th, k) for b, (s, l, th, k, _) in BOOKS.items()}
    for r in tickets:
        bk = books[r["book"]]
        if r["action"] == "enter":
            bk.open.append(xfund.Position(key[r["coin"]], NAMES.index(r["long"]), NAMES.index(r["short"]),
                                          (ms(r["day"]) - ms(WARM)) // DAY, float(r["spread_ann"])))
        elif r["action"] in ("exit", "drop"):
            bk.open = [p for p in bk.open if t.key[p.coin] != r["coin"]]
    return books


def fill_adj(r):
    """The ticket's live-fill gap against day D's closes on the pair (long minus short), per unit of one leg's notional."""
    try:
        cl, cs, fl, fs = (float(r[k]) for k in ("close_long", "close_short", "fill_long", "fill_short"))
    except (TypeError, ValueError):
        return 0.0
    if not all(np.isfinite([cl, cs, fl, fs])) or min(cl, cs, fl, fs) <= 0:
        return 0.0
    if r["action"] in ("enter", "inherit"):
        return (cl / fl - 1) - (cs / fs - 1)          # the long bought at fl and the short sold at fs, marked from closes
    return (fl / cl - 1) - (fs / cs - 1)              # exit: the long sold at fl, the short bought back at fs


def day_row(b, d_label, kind, run, held, g, f, prev):
    """The interval ending at d_label for book b, from its tickets of the day before (`prev`)."""
    k = BOOKS[b][3]
    legs_close = 2.0 * sum(r["action"] in ("enter", "exit", "drop") for r in prev)    # R275's own state machine
    legs = 2.0 * sum(r["action"] in ("enter", "exit", "inherit") for r in prev)        # the paper book's trades
    adj = sum(fill_adj(r) for r in prev if r["action"] != "drop")
    fill = [(g + adj - c * legs) / (2.0 * k) for c in COSTS]
    close = [(g - c * legs_close) / (2.0 * k) for c in COSTS]
    return {"day": d_label, "book": b, "kind": kind, "run": run, "held": held, "legs": legs,
            "gross": f"{g / (2 * k):.10f}", "funding": f"{f / (2 * k):.10f}", "fill_adj": f"{adj / (2 * k):.10f}",
            **{n: f"{v:.10f}" for n, v in zip(("net", "net_2x", "net_3x"), fill)},
            **{n: f"{v:.10f}" for n, v in zip(("net_close", "net_close_2x", "net_close_3x"), close)}}


def tick(now_ms=None, fetch=True, mids_fn=None, listed_fn=None):
    now_ms = now_ms or int(time.time() * 1000)
    t0 = ms(WARM)
    D = (now_ms - t0) // DAY                          # the last 00:00 UTC that has passed
    dec, tk, _ = journal()
    done = max((ms(r["day"]) - t0) // DAY for r in dec) if dec else None
    if done is not None and done >= D:
        log(f"day {day_str(t0, D)} already decided")
        return None
    stats = refresh(now_ms, fetch)
    u, t = universe(D + 1)
    need = {v for b in BOOKS.values() for v in b[0].split("+")}
    rd = ready(u, need, D)
    late_h = (now_ms - (t0 + D * DAY)) / H
    if min(rd.values()) < 0.9 and late_h < READY_WAIT_H:
        log(f"waiting for day {day_str(t0, D)} closes: {rd}")
        status(stats, rd, waiting=True)
        return None
    books = rebuild(t, tk)
    on = (ms(ON_TIME) - t0) // DAY
    if done is None:                                 # first run: each book replays from its window start
        starts = {b: xfund.window_start(u, bk.vset, bk.lookback) for b, bk in books.items()}
    else:
        starts = {b: 0 for b in books}
    first = min(starts.values()) if done is None else done + 1
    run = pd.Timestamp(now_ms, unit="ms", tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
    fills = (mids_fn or mids)() if D >= on else {}
    gone = (listed_fn or listed)() if D >= on else {}
    prev_tk = {}
    for r in tk:
        prev_tk.setdefault((r["book"], r["day"]), []).append(r)
    out_t, out_d, out_dec = [], [], []
    for d in range(first, D + 1):
        kind = "replay" if d < on else ("ontime" if d == D and late_h <= READY_WAIT_H + 1 else "late")
        label = day_str(t0, d)
        for b, bk in books.items():
            if d < starts[b]:
                continue
            # 1. the interval d - 1 -> d, for a book that decided at d - 1
            pl = day_str(t0, d - 1)
            pk = next((r["kind"] for r in out_dec if (r["book"], r["day"]) == (b, pl)), None) or \
                next((r["kind"] for r in dec if (r["book"], r["day"]) == (b, pl)), None)
            if pk is not None:
                g, f = bk.interval(u, d - 1)
                out_d.append(day_row(b, label, pk, run, len(bk.open), g, f, prev_tk.get((b, pl), [])))

            # 2. decisions at day d
            def forced_fn(p, dd):
                a, h = u.series[p.coin][p.lo], u.series[p.coin][p.hi]
                stale = lambda x: dd >= STALE_DAYS - 1 and not x.fresh[dd - STALE_DAYS + 1: dd + 1].any()
                delisted = kind != "replay" and any(v in gone and t.loc[p.coin, v] not in gone[v]
                                                    for v in (NAMES[p.lo], NAMES[p.hi]))
                return bool(stale(a) or stale(h) or delisted)

            mine = []

            def ticket(action, p, forced=False):
                lv, sv = NAMES[p.lo], NAMES[p.hi]
                ls, ss = t.loc[p.coin, lv], t.loc[p.coin, sv]
                cl, cs = u.series[p.coin][p.lo].close[d], u.series[p.coin][p.hi].close[d]
                fl = fills.get(lv, {}).get(ls) if kind == "ontime" else None
                fs = fills.get(sv, {}).get(ss) if kind == "ontime" else None
                mine.append({"run": run, "day": label, "book": b, "action": action, "coin": t.key[p.coin],
                             "long": lv, "short": sv, "spread_ann": f"{p.spread_in:.6f}",
                             "forced": str(bool(forced)).lower(), "kind": kind, "close_long": f"{cl:.10g}",
                             "close_short": f"{cs:.10g}", "fill_long": "" if fl is None else f"{fl:.10g}",
                             "fill_short": "" if fs is None else f"{fs:.10g}"})

            first_live = kind != "replay" and not any(r["book"] == b and r["kind"] != "replay" for r in dec + out_dec)
            ex = bk.exits(u, d, forced_fn)
            for p, forced in ex:                      # on the first live day a replayed pair that exits was never held
                ticket("drop" if first_live else "exit", p, forced)
            if first_live:
                for p in bk.open:                     # the first live day takes over the replayed pairs at its prices
                    ticket("inherit", p)
            en = bk.entries(u, d)
            for p in en:
                ticket("enter", p)
            out_t += mine
            prev_tk[(b, label)] = mine
            out_dec.append({"run": run, "day": label, "book": b, "kind": kind, "exits": len(ex), "entries": len(en),
                            "held": len(bk.open), "ready": json.dumps(rd, sort_keys=True)})
    append("tickets.csv", TICKET_COLS, out_t)
    append("days.csv", DAY_COLS, out_d)
    append("decisions.csv", DEC_COLS, out_dec)
    status(stats, rd, books=books, t=t, D=D)
    log(f"decided {first}..{D} ({day_str(t0, first)}..{day_str(t0, D)}): {len(out_t)} tickets, {len(out_d)} day rows")
    return D


def status(stats, rd, waiting=False, books=None, t=None, D=None):
    s = {"lane": "xfund_fwd", "rid": "R278", "updated": pd.Timestamp.now(tz="UTC").isoformat(), "waiting": waiting,
         "ready": rd, "data": {v: {**x, "failed": len(x["failed"]), "failed_some": x["failed"][:10]}
                               for v, x in stats.items()}}
    if books is not None:
        _, _, dy = journal()
        dd = pd.DataFrame(dy)
        for b, bk in books.items():
            x = dd[dd.book == b] if len(dd) else pd.DataFrame(columns=DAY_COLS + ["run"])
            on = x[x.kind != "replay"]
            f = lambda col, y: float(y[col].astype(float).sum()) if len(y) else 0.0
            r = on.net.astype(float).to_numpy() if len(on) else np.zeros(0)
            cum = np.concatenate([[0.0], np.cumsum(r)])
            s[b] = {"set": BOOKS[b][0], "lookback": BOOKS[b][1], "threshold": BOOKS[b][2], "slots": BOOKS[b][3],
                    "why": BOOKS[b][4],
                    "held_now": [{"coin": t.key[p.coin], "long": NAMES[p.lo], "short": NAMES[p.hi],
                                  "spread_in": round(p.spread_in, 4)} for p in bk.open],
                    "scored_days": int(len(on)), "late_days": int((on.kind == "late").sum()),
                    "total": f("net", on), "total_2x": f("net_2x", on), "total_3x": f("net_3x", on),
                    "total_close": f("net_close", on),
                    "nw_t": newey_west_t(r, 10)[2] if len(r) > 2 else None,     # monitoring; the PREREG decides
                    "max_drawdown": float((cum - np.maximum.accumulate(cum)).min()),
                    "replay_days": int((x.kind == "replay").sum()), "replay_total": f("net", x[x.kind == "replay"])}
        s["last_day"] = day_str(ms(WARM), D)
    J.mkdir(parents=True, exist_ok=True)
    (J / "status.json").write_text(json.dumps(s, indent=1, default=str))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-fetch", action="store_true", help="use the forward root as it is (dry runs)")
    a = ap.parse_args()
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    tick(fetch=not a.no_fetch)


if __name__ == "__main__":
    main()
