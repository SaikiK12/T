"""R371 usopen_fwd: R300's "us10 n3 follow" forward on paper, as set out in experiments/usopen_fwd/PREREG.md.

Each NYSE trading day, at 10:00 New York (D), the daemon ranks the Binance USDT perps, takes the three strongest and three
weakest of the top 50 by their move since 00:00 UTC and writes the ticket within two minutes of D; the position is flat at
00:00 UTC. Two books come out of every ticket (scripts/usopen_rule.py is the rule, fixed by the PREREG):
  B  R300's own universe priced on Binance hourly closes at R300's API cost: R300 continued on days nobody had read.
  M  the same rule among the coins that also have an open MEXC crypto perp, filled at the open of the one-minute bar three
     minutes after D and three minutes after 24:00 UTC, at the day's measured web fee and half-spreads: what a person could
     do by hand. M is the book the lane decides on.
Paper only: public endpoints, no account, no key. Nothing here can place an order.

`tick` (the daemon runs it every 30 s, every 5 s around the hour; the forward loop's task runs `ensure`):
1. Warm the Binance bar cache in the five minutes before D, then write the ticket in [D, D + 2 min]. A ticket not written
   by then is a "missed" row; the day is not made up.
2. Score every ticket whose exit minute passed 20 minutes ago: prices, funding and costs from history, once.
3. status.json.
Journals (append-only, experiments/usopen_fwd/journal/): tickets.csv, legs.csv, signals.csv, scored.csv, skipped.csv.

usage: python scripts/forward_usopen.py [ensure] | run | tick | status
"""
import argparse
import concurrent.futures as cf
import contextlib
import csv
import fcntl
import json
import math
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import data, gate, live, mexc, prereg  # noqa: E402
import usopen_rule as rule  # noqa: E402

LANE = ROOT / "experiments" / "usopen_fwd"
JOURNAL = LANE / "journal"
LOG = data.ROOT / "logs" / "usopen_fwd.log"
TICKS = data.ROOT / "recorders" / "mexc_ticker"
REGISTRY = "R371"
H, MIN, DAY = rule.H, rule.MIN, rule.DAY
START_MS = pd.Timestamp("2026-10-29", tz="UTC").value // 10**6      # the first day the lane may ticket
WARM_MS = 5 * MIN                                                   # the bar cache is warmed this long before D
READY_MS = 3000                                                     # the bar that closed at D needs a moment to be served
SCORE_AFTER_MS = 20 * MIN                                           # a ticket is scored this long after its exit minute
FILES = {
    "tickets": ["ticket", "day_ms", "d_ms", "frozen_ms", "frozen_at", "late_s", "status", "n_b", "n_m", "note"],
    "legs": ["ticket", "book", "side", "symbol", "contract", "rank", "sig", "c_s", "c_e", "taker", "bid", "ask"],
    "signals": ["ticket", "symbol", "rank", "sig", "c_s", "c_e", "vol"],
    "scored": ["ticket", "book", "day_ms", "price", "funding", "gross", "cost_1x", "net_1x", "net_2x", "net_3x",
               "longs", "shorts", "stopped", "spread_flag", "scored_at"],
    "skipped": ["ticket", "book", "reason", "detail", "noted_at"],
}
log = lambda *a: print(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), *a, flush=True)
iso = lambda ms: pd.Timestamp(int(ms), unit="ms", tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


def clock_ms():
    return int(time.time() * 1000)


def fixed_inputs(prereg_path):
    """{path: sha256} from the PREREG's ```fixed block: the files the lane may not tick without."""
    block = re.search(r"```fixed\n(.*?)```", Path(prereg_path).read_text(), re.S).group(1)
    return {rel: want for want, rel in (line.split() for line in block.strip().splitlines())}


def check(lane=LANE):
    """The PREREG and every fixed file must be unchanged since the freeze; the lane does not tick otherwise."""
    prereg.verify(lane / "PREREG.md")
    bad = [rel for rel, want in fixed_inputs(lane / "PREREG.md").items() if prereg.sha256_file(ROOT / rel) != want]
    if bad:
        raise prereg.PreregError(f"fixed inputs changed since the freeze: {bad}")


# ----------------------------------------------------------------------------------------------------- journals
def path_of(name, journal=None):
    return (journal or JOURNAL) / f"{name}.csv"


def read(name, journal=None):
    p = path_of(name, journal)
    if not p.exists():
        return []
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def append(name, rows, journal=None):
    """Append-only under the file's fixed header; a column outside the header raises."""
    if not rows:
        return
    p = path_of(name, journal)
    p.parent.mkdir(parents=True, exist_ok=True)
    new = not p.exists()
    with open(p, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FILES[name], lineterminator="\n", extrasaction="raise")
        if new:
            w.writeheader()
        w.writerows(rows)


@contextlib.contextmanager
def writer_lock(journal=None):
    """One writer for the lane's journal; a second process exits."""
    j = journal or JOURNAL
    j.mkdir(parents=True, exist_ok=True)
    f = open(j / ".writer.lock", "a")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        f.close()
        raise SystemExit("another usopen_fwd writer holds the journal lock")
    try:
        yield
    finally:
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()


def ticket_id(day_ms):
    return pd.Timestamp(int(day_ms), unit="ms", tz="UTC").strftime("U%Y%m%d")


# ------------------------------------------------------------------------------------------------------ data access
def fetch_frames(D, symbols=None, workers=8):
    """{symbol: hourly bars with open time in [D - 720 h, D)} for every Binance USDT perp trading now, from the shared
    bar cache (only the bars it lacks are requested). A symbol that fails to load is left out and logged."""
    syms = symbols or live.perpetuals()

    def one(s):
        try:
            return s, live.klines_cached(s, D - rule.WINDOW * H, D)
        except live.LiveError as e:
            log("klines failed", s, e)
            return s, None

    with cf.ThreadPoolExecutor(workers) as ex:
        out = dict(ex.map(one, syms))
    return {s: b for s, b in out.items() if b is not None and len(b)}


def mexc_table():
    t = mexc.contracts()
    return t[(t.type == 1) & (t.state == 0)].reset_index(drop=True)


def bulk_quotes():
    """{contract: (bid1, ask1)} from one public request; empty when it fails (the ticket records no quote then)."""
    try:
        return {x["symbol"]: (x.get("bid1"), x.get("ask1")) for x in mexc.get("ticker")}
    except Exception as e:  # noqa: BLE001 - the quotes are an audit field, not an input
        log("ticker failed", e)
        return {}


def half_spread(ms, contract, ticks=TICKS):
    """Half the relative bid-ask spread in the ticker recorder's file for the UTC hour of ms, or None."""
    ts = pd.Timestamp(int(ms), unit="ms", tz="UTC")
    p = Path(ticks) / ts.strftime("%Y-%m-%d") / f"{ts:%H}.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p, columns=["symbol", "t_bid1", "t_ask1"])
    r = df[df.symbol == contract]
    if r.empty or not (r.t_bid1.iloc[0] > 0 and r.t_ask1.iloc[0] > 0):
        return None
    b, a = float(r.t_bid1.iloc[0]), float(r.t_ask1.iloc[0])
    return (a - b) / (a + b)


def mexc_open(contract, ms, tries=5):
    """(minute_ms, open) of the first one-minute bar at or after ms and within 5 minutes of it, else (None, None)."""
    d = mexc.get(f"kline/{contract}", {"interval": "Min1", "start": int(ms) // 1000, "end": int(ms) // 1000 + 5 * 60})
    if not d or not d.get("time"):
        return None, None
    for t, o in zip(d["time"], d["open"]):
        if int(t) * 1000 >= ms and float(o) > 0:
            return int(t) * 1000, float(o)
    return None, None


# ------------------------------------------------------------------------------------------------------- decision
def book_rows(ticket, book, longs, shorts, cs, cmap=None, table=None, quotes=None):
    rows = []
    by = cs.set_index("symbol")
    taker = dict(zip(table.symbol, table.taker)) if table is not None else {}
    for side, names in (("long", longs), ("short", shorts)):
        for s in names:
            r = by.loc[s]
            c = (cmap or {}).get(s, "")
            q = (quotes or {}).get(c, (None, None))
            rows.append({"ticket": ticket, "book": book, "side": side, "symbol": s, "contract": c or "",
                         "rank": int(r["rank"]), "sig": float(r.sig), "c_s": float(r.c_s), "c_e": float(r.c_e),
                         "taker": taker.get(c, "") if c else "", "bid": q[0], "ask": q[1]})
    return rows


class StaleBars(RuntimeError):
    """The bar that closed at D is not served yet for most symbols: nothing is written, the next tick retries."""


def decide(now_ms, day_ms, D, *, frames=None, table=None, quotes=None, journal=None):
    """Write the day's ticket (and legs, signals) once. Returns the ticket row."""
    tid = ticket_id(day_ms)
    frames = frames if frames is not None else fetch_frames(D)
    fresh = sum(1 for b in frames.values() if (b.t == D - H).any())
    if not frames or fresh < 0.8 * len(frames):
        raise StaleBars(f"{fresh} of {len(frames)} symbols have the bar that closed at {iso(D)}")
    table = table if table is not None else mexc_table()
    cs_b = rule.cross_section(frames, day_ms, D)
    cmap = mexc.map_symbols(list(frames), table)
    mframes = {s: f for s, f in frames.items() if cmap.get(s)}
    cs_m = rule.cross_section(mframes, day_ms, D)
    pb, pm = rule.pick(cs_b), rule.pick(cs_m)
    base = {"ticket": tid, "day_ms": day_ms, "d_ms": D, "frozen_ms": now_ms, "frozen_at": iso(now_ms),
            "late_s": round((now_ms - D) / 1000, 1), "n_b": pb[2] if pb else len(cs_b), "n_m": pm[2] if pm else len(cs_m)}
    status = "ok" if pb and pm else "no_book_b" if not pb else "no_book_m"
    note = "" if status == "ok" else f"eligible B {base['n_b']} M {base['n_m']} < {rule.MIN_NAMES}"
    row = {**base, "status": status, "note": note}
    legs = []
    if pb:
        legs += book_rows(tid, "B", pb[0], pb[1], cs_b)
    if pm:
        q = quotes if quotes is not None else bulk_quotes()
        legs += book_rows(tid, "M", pm[0], pm[1], cs_m, {s: cmap[s] for s in cmap if cmap[s]}, table, q)
    sig = cs_b[(cs_b["rank"] <= rule.TOP) & cs_b.sig.notna()]
    append("tickets", [row], journal)
    append("legs", legs, journal)
    append("signals", [{"ticket": tid, "symbol": r.symbol, "rank": int(r["rank"]), "sig": float(r.sig),
                        "c_s": float(r.c_s), "c_e": float(r.c_e), "vol": float(r.vol)} for _, r in sig.iterrows()],
           journal)
    return row


# ---------------------------------------------------------------------------------------------------------- scoring
def exit_ms_of(day_ms):
    return int(day_ms) + DAY


def b_leg(leg, D, X, bars, fund):
    """Book B leg: entry c_e, exit the last traded hourly close in [D, X) (entry if none), funding settled in [D, X)."""
    w = bars[(bars.t >= D) & (bars.t < X) & (bars.quote_volume > 0)].sort_values("t")
    entry = float(leg["c_e"])
    exit_, stopped = (float(w.close.iloc[-1]), False) if len(w) else (entry, True)
    f = fund[(fund.t >= D) & (fund.t < X)]
    return {"ret": exit_ / entry - 1.0, "fund": float(f.rate.sum()), "stopped": stopped}


def m_leg(leg, D, X, open_at, funding_of, spread_of):
    """Book M leg: filled at the open of the minute bar after D + 3 min and X + 3 min, funding settled in (entry, exit],
    cost = two taker fees plus the half-spread of both fills. None (with the reason) when a price is missing."""
    c = leg["contract"]
    em, entry = open_at(c, D + rule.ENTRY_LAG_MIN * MIN)
    xm, exit_ = open_at(c, X + rule.EXIT_LAG_MIN * MIN)
    if entry is None or exit_ is None:
        return None, f"{c}: no one-minute bar for {'entry' if entry is None else 'exit'}"
    f = funding_of(c, (em // H + 1) * H, xm // H * H + 1)
    se, sx = spread_of(em, c), spread_of(xm, c)
    flag = se is None or sx is None
    se = rule.SPREAD_FALLBACK if se is None else se
    sx = rule.SPREAD_FALLBACK if sx is None else sx
    taker = float(leg["taker"]) if str(leg["taker"]) not in ("", "nan") else 0.0
    return {"ret": exit_ / entry - 1.0, "fund": float(f.rate.sum()), "cost": rule.leg_cost(taker, se, sx),
            "flag": flag, "stopped": False}, ""


def default_bars(sym, D, X):
    return live.fetch_klines(sym, D, X)


def default_funding_b(sym, D, X):
    return live.funding_history(sym, D, X)


def default_funding_m(contract, a, b):
    return mexc.funding_history(contract, a, b)


def score_ticket(now_ms, t, legs, *, bars_of=default_bars, funding_b=default_funding_b, open_at=mexc_open,
                 funding_m=default_funding_m, spread_of=half_spread, journal=None):
    """Score both books of one ticket. Returns (scored rows, skipped rows); the caller appends them."""
    D, X, tid, day_ms = int(t["d_ms"]), exit_ms_of(t["day_ms"]), t["ticket"], int(t["day_ms"])
    out, skipped = [], []
    stamp = iso(now_ms)
    for book in ("B", "M"):
        mine = [x for x in legs if x["ticket"] == tid and x["book"] == book]
        if not mine:
            skipped.append({"ticket": tid, "book": book, "reason": "no_legs", "detail": t["status"], "noted_at": stamp})
            continue
        res = {"long": [], "short": []}
        why, stopped, flag = "", 0, False
        for leg in mine:
            if book == "B":
                try:
                    bars = bars_of(leg["symbol"], D - H, X)
                    fund = funding_b(leg["symbol"], D, X)
                except Exception as e:  # noqa: BLE001 - retried by the next tick
                    return None, f"{leg['symbol']}: {e}"
                if bars is None or fund is None:
                    return None, f"{leg['symbol']}: no data"
                r = b_leg(leg, D, X, bars, fund)
            else:
                try:
                    r, why = m_leg(leg, D, X, open_at, funding_m, spread_of)
                except Exception as e:  # noqa: BLE001 - retried by the next tick
                    return None, f"{leg['contract']}: {e}"
                if r is None:
                    break
                flag = flag or r["flag"]
            stopped += int(r["stopped"])
            res[leg["side"]].append(r)
        if why:
            skipped.append({"ticket": tid, "book": book, "reason": "unpriced", "detail": why, "noted_at": stamp})
            continue
        price, fund = rule.book_return(res["long"], res["short"])
        gross = price + fund
        cost = (rule.api_cost(1) if book == "B"
                else rule.web_cost([x["cost"] for x in res["long"]], [x["cost"] for x in res["short"]]))
        nets = {k: gross - k * cost for k in (1, 2, 3)}
        names = lambda side: "|".join(x["symbol"] for x in mine if x["side"] == side)
        out.append({"ticket": tid, "book": book, "day_ms": day_ms, "price": price, "funding": fund, "gross": gross,
                    "cost_1x": cost, "net_1x": nets[1], "net_2x": nets[2], "net_3x": nets[3],
                    "longs": names("long"), "shorts": names("short"), "stopped": stopped, "spread_flag": flag,
                    "scored_at": stamp})
    return (out, skipped), ""


# ------------------------------------------------------------------------------------------------------------ status
def _finite(v, nd=6):
    return round(float(v), nd) if v is not None and math.isfinite(float(v)) else None


def book_stats(scored, book):
    rs = sorted((r for r in scored if r["book"] == book), key=lambda r: int(r["day_ms"]))
    days = [int(r["day_ms"]) for r in rs]
    n1 = [float(r["net_1x"]) for r in rs]
    n2 = [float(r["net_2x"]) for r in rs]
    s = rule.summarize(days, n1, n2)                 # descriptive, on every scored day
    s["verdict"] = rule.decision(days, n1, n2)[1]    # read once at day 125 / 500, then kept
    s["mean_net_3x"] = float(np.mean([float(r["net_3x"]) for r in rs])) if rs else None
    s["mean_gross"] = float(np.mean([float(r["gross"]) for r in rs])) if rs else None
    s["mean_cost"] = float(np.mean([float(r["cost_1x"]) for r in rs])) if rs else None
    s["go_real"] = gate.go_real(n1, days) if rs else None
    return s


def status(now_ms=None, write=True, journal=None):
    now_ms = now_ms or clock_ms()
    tickets, scored, skipped = read("tickets", journal), read("scored", journal), read("skipped", journal)
    b, m = book_stats(scored, "B"), book_stats(scored, "M")
    g = m["go_real"]
    settled = {r["ticket"] for r in scored + skipped if r["book"] == "M"}
    s = {"registry": REGISTRY, "updated": iso(now_ms), "state": "running", "decision": m["verdict"],
         "scored": m["n"], "tickets": len(tickets), "open": sum(1 for t in tickets if t["status"] == "ok"
                                                                 and t["ticket"] not in settled),
         "mean_net": _finite(m["mean"]), "mean_net_2x": _finite(m.get("mean_2x")), "t_nw": _finite(m["t"], 3),
         "mean_wo_best10": _finite(m["mean_wo_best"]), "hit": _finite(m["hit"], 3),
         "go_real": None if g is None else {"pass": g["pass"], "n": g["n"], "mean": _finite(g["mean"]),
                                            "hit": _finite(g["hit"], 3), "worst": _finite(g["worst"]),
                                            "n_clusters": g["n_clusters"], "checks": g["checks"]},
         "book_b": {k: _finite(v, 6) if isinstance(v, float) else v for k, v in b.items() if k != "go_real"},
         "book_m": {k: _finite(v, 6) if isinstance(v, float) else v for k, v in m.items() if k != "go_real"},
         "missed": sum(1 for t in tickets if t["status"] == "missed"),
         "no_book": sum(1 for t in tickets if t["status"].startswith("no_book")),
         "unpriced_m": sum(1 for r in skipped if r["book"] == "M" and r["reason"] == "unpriced")}
    if write:
        j = journal or JOURNAL
        j.mkdir(parents=True, exist_ok=True)
        (j / "status.json").write_text(json.dumps(s, indent=1) + "\n")
    return s


# --------------------------------------------------------------------------------------------------------- tick
_warmed = set()


def tick(now_ms=None, journal=None):
    now_ms = now_ms or clock_ms()
    have = {t["ticket"] for t in read("tickets", journal)}
    for day_ms, D in rule.decision_days(now_ms - DAY):
        tid = ticket_id(day_ms)
        if day_ms < START_MS or tid in have or now_ms < D - WARM_MS:
            continue
        if now_ms < D:
            if tid not in _warmed:
                _warmed.add(tid)
                log(f"warmed {len(fetch_frames(D))} symbols before D {iso(D)}")
            continue
        if now_ms < D + READY_MS:
            continue
        if now_ms > D + rule.TICKET_DEADLINE_MS:
            append("tickets", [{"ticket": tid, "day_ms": day_ms, "d_ms": D, "frozen_ms": now_ms, "frozen_at": iso(now_ms),
                                "late_s": round((now_ms - D) / 1000, 1), "status": "missed", "n_b": "", "n_m": "",
                                "note": f"no ticket within {rule.TICKET_DEADLINE_MS // 1000} s of D"}], journal)
            log(f"missed {tid}")
            continue
        try:
            row = decide(now_ms, day_ms, D, journal=journal)
        except StaleBars as e:
            log(f"{tid} deferred: {e}")
            continue
        log(f"ticket {tid} {row['status']} B {row['n_b']} M {row['n_m']} late {row['late_s']} s")
    legs = read("legs", journal)
    for t in read("tickets", journal):
        if t["status"] != "ok" or now_ms < exit_ms_of(t["day_ms"]) + rule.EXIT_LAG_MIN * MIN + SCORE_AFTER_MS:
            continue
        settled = {r["book"] for r in read("scored", journal) + read("skipped", journal) if r["ticket"] == t["ticket"]}
        if settled >= {"B", "M"}:
            continue
        res, err = score_ticket(now_ms, t, legs, journal=journal)
        if res is None:
            log(f"score {t['ticket']} deferred: {err}")
            continue
        out = [r for r in res[0] if r["book"] not in settled]
        skipped = [r for r in res[1] if r["book"] not in settled]
        append("scored", out, journal)
        append("skipped", skipped, journal)
        log(f"scored {t['ticket']}: " + ", ".join(f"{r['book']} net {float(r['net_1x']) * 1e4:+.0f} bp" for r in out)
            + (f"; skipped {[(r['book'], r['reason']) for r in skipped]}" if skipped else ""))
    return status(now_ms, journal=journal)


def run():
    """The lane's scheduler: a tick every 30 s on the wall clock."""
    with writer_lock():
        log("usopen_fwd run started")
        while True:
            check()                       # a changed PREREG or rule stops the lane here, loudly
            try:
                s = tick()
                if s["scored"] and int(time.time()) % 3600 < 30:
                    log("status", s["decision"], "scored", s["scored"], "tickets", s["tickets"])
            except Exception as e:  # noqa: BLE001 - the next tick retries; scoring is idempotent, a missed D is logged
                log("tick failed", repr(e))
            near_d = time.time() % 3600 < 150 or time.time() % 3600 > 3300      # D is on the hour: tick faster around it
            step = 5 if near_d else 30
            time.sleep(step - time.time() % step + 0.5)


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
        log("usopen_fwd running:", s.get("decision", "no status yet"))
        return 0
    fcntl.flock(f, fcntl.LOCK_UN)
    f.close()
    check()                                   # never start a lane whose PREREG or rule changed
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a") as out:
        subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "run"], cwd=ROOT, stdout=out,
                         stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
    log("usopen_fwd started; log", LOG)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", default="ensure", choices=["ensure", "run", "tick", "status"])
    a = ap.parse_args(argv)
    if a.cmd == "ensure":
        return ensure()
    if a.cmd in ("run", "tick"):
        check()
    if a.cmd == "run":
        run()
    elif a.cmd == "tick":
        with writer_lock():
            print(json.dumps(tick(), indent=1))
    else:
        print(json.dumps(status(write=False), indent=1))


if __name__ == "__main__":
    main()
