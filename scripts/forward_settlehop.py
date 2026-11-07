"""R355 settlehop_fwd: R354's settlement hop, forward on paper, on the funding rate a trader sees, hedged on Lighter.

R354 (gate 0, a frozen PASS) rebuilt Binance's next funding rate from its premium index an hour before each 4 h or 8 h
settlement T. It held the side of the venue S that receives the lump from T - 1 h to T + 1 h, hedged with the opposite
side on hourly Lighter. This lane runs the same rule on the live displayed rate of MEXC (decided) and Gate (reported),
so every hop is on days no lane has read. Paper only: public endpoints, no account, no key. Nothing here can place an
order.

`tick` (run at hh:00:20 UTC by `run`):
1. **Exits:** every open hop whose T + 1 h has passed is closed at both venues' books: a walked $1k market order on
   each leg.
2. **Entries:** T is the next full hour, decided once, at most 10 minutes after T - 1 h. For every MEXC and Gate perp
   settling at T on a 4 or 8 h cycle and listed on Lighter as a crypto perp under the same base:
   - F is the venue's displayed rate. h is Lighter's last hourly settlement at or before T - 1 h, at most 2 h old.
   - e = F - 2h and d = sign(e); +1 means short S and long Lighter.
   - Candidates with |e| >= 0.3% must pass R353's 30-day identity check on daily closes.
   - They are then entered at both books, largest |e| first, up to 5 per venue, until 10 minutes after T - 1 h. A
     book that cannot fill $1k within its shown depth skips the hop.
   - Every candidate with |e| >= 0.2% is logged (signals.csv), and every decision gets one row per venue
     (decisions.csv).
3. **Scores:** a hop exited at least 20 minutes ago is scored. Each venue's settlements in (entry, exit] are taken
   from its own history.
4. **Status:** status.json, with the PREREG's decision and lab.gate.go_real on the primary book.

**Path:** while a hop is open, `run` also logs each leg's bulk quotes every minute (path.csv): MEXC and Gate bid, ask
and mark; Lighter last trade and mark. Each hop's adverse excursion is read from it at scoring. It is reported only.

Start: the forward loop's hourly task runs this script with no argument (`ensure`), which starts `run` detached when no
writer holds the journal lock (log: data/logs/settlehop_fwd.log). After a container restart the journal resumes; hours
the daemon missed are late and excluded.
usage: python scripts/forward_settlehop.py [ensure] | run | tick | status
"""
import argparse
import contextlib
import csv
import fcntl
import json
import math
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import carrylane, gate, mexc, prereg  # noqa: E402
from settlehop_rule import (DAY, H, H_LIVE, INTERVALS, LOG_E, MIN, ON_TIME_S, SCORE_AFTER, SLOTS,  # noqa: E402
                            THETAS, canon, daily_closes, decide_stats, last_settled, leave_two_coins_out,
                            lighter_crypto, primary, same_coin, score, side_fill, signal, theta_book, trimmed,
                            verdict)   # the rule, fixed

LANE = ROOT / "experiments" / "settlehop_fwd"
JOURNAL = LANE / "journal"
REGISTRY = "R355"
VENUES = ("mexc", "gate")                 # S venues; MEXC is decided, Gate is reported
DECIDE_AT_S = 20                          # the tick runs 20 s after the hour
GATE = carrylane.GATE
LOG = ROOT / "data" / "logs" / "settlehop_fwd.log"
FILES = {
    "decisions": ["decided_ms", "T", "late_s", "venue", "settling", "on_lighter", "logged", "candidates", "entered",
                  "error"],
    "signals": ["decided_ms", "T", "venue", "symbol", "lighter", "F", "F_cap", "cycle_h", "h_prev", "h_prev_t", "e",
                "d", "binance_F", "same", "corr", "rank", "status"],
    "tickets": ["hop", "action", "ms", "T", "venue", "symbol", "lighter", "market_id", "d", "e", "F", "h_prev",
                "theta_book", "s_bid", "s_ask", "s_fill", "s_usd", "h_bid", "h_ask", "h_fill", "h_usd",
                "fee_s_bp", "fee_h_bp", "late_s", "thin"],
    "path": ["ms", "hop", "s_bid", "s_ask", "s_mark", "h_last", "h_mark"],
    "scored": ["hop", "venue", "symbol", "lighter", "T", "d", "e", "theta_book", "entry_ms", "exit_ms", "on_time",
               "gross_mid", "fund", "fund_s", "fund_h", "n_s", "n_h", "s_rates", "h_rates", "book_cost", "fee_web",
               "fee_api", "net1_web", "net2_web", "net3_web", "net1_api", "net2_api", "net3_api", "mae_s", "mae_h",
               "mae_pair", "path_n"],
}
log = lambda *a: print(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), *a, flush=True)


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
        raise SystemExit("another settlehop_fwd writer holds the journal lock")
    try:
        yield
    finally:
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()


def open_hops(tickets):
    done = {t["hop"] for t in tickets if t["action"] == "exit"}
    return [t for t in tickets if t["action"] == "enter" and t["hop"] not in done]


# ------------------------------------------------------------------------------------------------------ venues
def mexc_settling(T):
    """MEXC crypto USDT perps settling at T on a 4 or 8 h cycle:
    {symbol: (base, F, cycle, contract size, taker fee bp, the cap on F's side)}."""
    tab = mexc.contracts(refresh=False)
    tab = tab[(tab.type == 1) & (tab.state == 0)]
    meta = {r.symbol: r for r in tab.itertuples()}
    out = {}
    for x in mexc.get("funding_rate"):
        s, m = x.get("symbol"), meta.get(x.get("symbol"))
        if m is None or x.get("nextSettleTime") is None:
            continue
        cyc = int(x.get("collectCycle") or 0)
        if abs(int(x["nextSettleTime"]) - T) <= MIN and cyc in INTERVALS:
            F = float(x["fundingRate"])
            cap = x.get("minFundingRate") if F < 0 else x.get("maxFundingRate")
            out[s] = (m.base, F, cyc, float(m.contract_size), float(m.taker or 0) * 1e4,
                      float(cap) if cap is not None else math.nan)
    return out


def gate_settling(T):
    out = {}
    for c in carrylane._json(f"{GATE}/contracts"):
        if c.get("in_delisting") or not c.get("funding_next_apply"):
            continue
        cyc = int(c.get("funding_interval") or 0) // 3600
        if abs(int(c["funding_next_apply"]) * 1000 - T) <= MIN and cyc in INTERVALS and c["name"].endswith("_USDT"):
            F = float(c["funding_rate"])
            lim = c.get("funding_rate_limit")
            out[c["name"]] = (c["name"][:-5], F, cyc, float(c["quanto_multiplier"]),
                              float(c.get("taker_fee_rate") or 0) * 1e4,
                              math.copysign(float(lim), F) if lim not in (None, "") else math.nan)
    return out


def lighter_markets():
    """Active Lighter crypto perps by canonical base: {canon: (symbol, market_id, taker fee bp)}."""
    out = {}
    for d in carrylane._lighter_details():
        if d.get("status") == "active" and lighter_crypto(d):
            out.setdefault(canon(d["symbol"]), (d["symbol"], int(d["market_id"]), float(d.get("taker_fee") or 0) * 1e4))
    return out


def lighter_fundings(market_id, a, b):
    """[(ms, signed rate per settlement)] in [a, b], signed as the archive (positive: longs pay)."""
    rows = carrylane._lighter("fundings", market_id=market_id, resolution="1h", start_timestamp=a // 1000,
                              end_timestamp=b // 1000, count_back=0).get("fundings") or []
    return sorted((int(x["timestamp"]) * 1000, (1.0 if x["direction"] == "long" else -1.0) * float(x["rate"]) / 100)
                  for x in rows)


def binance_rates():
    """Binance's displayed rate for Lighter's coins, as Lighter's funding-rates endpoint reports it (logged only)."""
    try:
        rows = carrylane._lighter("funding-rates").get("funding_rates") or []
    except Exception as e:  # noqa: BLE001 - a log column only
        log("funding-rates failed", e)
        return {}
    return {canon(r["symbol"]): float(r["rate"]) for r in rows if r.get("exchange") == "binance"}


def book_mexc(symbol, size):
    d = mexc.get(f"depth/{symbol}", {"limit": 100})
    lv = lambda xs: [(float(x[0]), float(x[1]) * size) for x in xs or []]
    return {"bids": lv(d.get("bids")), "asks": lv(d.get("asks"))}


def book_gate(symbol, size):
    d = carrylane._json(f"{GATE}/order_book?" + urllib.parse.urlencode({"contract": symbol, "limit": 100}))
    lv = lambda xs: [(float(x["p"]), float(x["s"]) * size) for x in xs or []]
    return {"bids": lv(d.get("bids")), "asks": lv(d.get("asks"))}


def book_lighter(market_id):
    d = carrylane._lighter("orderBookOrders", market_id=market_id, limit=100)
    lv = lambda xs: [(float(x["price"]), float(x["remaining_base_amount"])) for x in xs or []]
    return {"bids": lv(d.get("bids")), "asks": lv(d.get("asks"))}


def closes_mexc(symbol, end_ms):
    df = mexc.fetch_klines(symbol, end_ms // H * H - 32 * DAY, end_ms // H * H)
    return daily_closes(zip(df.t.tolist(), df.close.tolist()))


def closes_gate(symbol, end_ms):
    df = carrylane.gate_prices(symbol, end_ms // H * H - 32 * DAY, end_ms // H * H)
    return daily_closes(zip(df.t.tolist(), df.close.tolist()))


def closes_lighter(symbol, end_ms):
    df = carrylane.lighter_prices(symbol, end_ms // H * H - 32 * DAY, end_ms // H * H)
    return daily_closes(zip(df.t.tolist(), df.close.tolist()))


SETTLING = {"mexc": mexc_settling, "gate": gate_settling}
BOOK = {"mexc": book_mexc, "gate": book_gate}
CLOSES = {"mexc": closes_mexc, "gate": closes_gate}


def s_funding(venue, symbol, a, b):
    if venue == "mexc":
        df = mexc.funding_history(symbol, a - H, b + H)
    else:
        df = carrylane.gate_funding(symbol, a - H, b + H)
    return sorted(zip(df.t.astype("int64").tolist(), df.rate.astype(float).tolist()))


# --------------------------------------------------------------------------------------------------------- tick
def best(book):
    return book["bids"][0][0], book["asks"][0][0]


def retry(fn, tries=3, wait=5.0):
    """A read retried, `wait` s apart: an exit or an entry should not wait an hour for one failed request."""
    for k in range(tries):
        try:
            return fn()
        except Exception:  # noqa: BLE001
            if k == tries - 1:
                raise
            time.sleep(wait)


def enter_hops(now_ms, T):
    """The decision for settlement T: log the candidates, check, rank and enter, venue by venue. Each venue's tickets
    and signals are written before its decision row, so a crash cannot leave a decided venue without its tickets.
    Returns the number of hops entered."""
    deadline = T - H + ON_TIME_S * 1000
    settling, errors = {}, {}
    for venue in VENUES:
        try:
            settling[venue] = retry(lambda: SETTLING[venue](T))
        except Exception as e:  # noqa: BLE001 - a venue that fails is logged and skipped
            errors[venue] = f"settling: {e}"
    lm, bn = {}, {}
    if any(settling.values()):
        try:
            lm = retry(lighter_markets)
        except Exception as e:  # noqa: BLE001
            for v in settling:
                errors[v] = f"lighter markets: {e}"
        bn = binance_rates()
    hcache, total = {}, 0
    for venue in VENUES:
        dec = {"decided_ms": now_ms, "T": T, "late_s": round((now_ms - (T - H)) / 1000), "venue": venue,
               "settling": len(settling.get(venue, {}))}
        if venue in errors:
            append("decisions", [{**dec, "error": errors[venue][:200]}])
            continue
        both = {s: v for s, v in settling[venue].items() if canon(v[0]) in lm}
        cands, sigs = [], []
        for s, (base, F, cyc, size, fee, cap) in sorted(both.items()):
            lsym, mid_, fee_h = lm[canon(base)]
            if mid_ not in hcache:
                try:
                    hcache[mid_] = last_settled(retry(lambda: lighter_fundings(mid_, T - 3 * H, now_ms), 2, 2.0),
                                                T - H)
                except Exception as e:  # noqa: BLE001
                    log("lighter fundings failed", lsym, e)
                    hcache[mid_] = (None, math.nan)
            t_h, h = hcache[mid_]
            row = {"decided_ms": now_ms, "T": T, "venue": venue, "symbol": s, "lighter": lsym, "F": F, "F_cap": cap,
                   "cycle_h": cyc, "binance_F": bn.get(canon(base), "")}
            if t_h is None or (T - H) - t_h > H_LIVE:
                if abs(F) >= LOG_E:
                    sigs.append({**row, "status": "no live Lighter rate"})
                continue
            e, d = signal(F, h)
            row.update({"h_prev": h, "h_prev_t": t_h, "e": e, "d": d})
            if abs(e) >= min(THETAS):
                cands.append((abs(e), s, size, fee, lsym, mid_, fee_h, row))
            elif abs(e) >= LOG_E:
                row["status"] = f"below {min(THETAS):.1%}"
            if abs(e) >= LOG_E:
                sigs.append(row)
        cands.sort(key=lambda x: -x[0])
        new = []
        for rank, (ae, s, size, fee, lsym, mid_, fee_h, row) in enumerate(cands, 1):
            row["rank"] = rank
            if len(new) >= SLOTS:
                row["status"] = "slots full"
                continue
            if clock_ms() > deadline:
                row["status"] = "past the on-time window"
                continue
            try:
                ok, c = same_coin(retry(lambda: CLOSES[venue](s, now_ms)), retry(lambda: closes_lighter(lsym, now_ms)),
                                  now_ms)
            except Exception as e:  # noqa: BLE001
                row["status"] = f"identity read failed: {e}"[:120]
                continue
            row["same"], row["corr"] = ok, (round(c, 4) if math.isfinite(c) else "")
            if not ok:
                row["status"] = "identity check failed"
                continue
            if not size > 0:                              # NaN-safe: a contract without a size is not walked
                row["status"] = "no contract size"
                continue
            try:
                bs, bh = retry(lambda: BOOK[venue](s, size)), retry(lambda: book_lighter(mid_))
            except Exception as e:  # noqa: BLE001
                row["status"] = f"book read failed: {e}"[:120]
                continue
            ms_ = clock_ms()
            if ms_ > deadline:
                row["status"] = "past the on-time window"
                continue
            d = row["d"]
            if not (bs["bids"] and bs["asks"] and bh["bids"] and bh["asks"]):
                row["status"] = "empty book"
                continue
            sp, sg, sthin = side_fill(bs, buy=d < 0)
            hp, hg, hthin = side_fill(bh, buy=d > 0)
            if sthin or hthin:
                row["status"] = "book too thin for $1k"
                continue
            row["status"] = "entered"
            (sb, sa), (hb, ha) = best(bs), best(bh)
            new.append({"hop": f"{venue}:{s}:{T}", "action": "enter", "ms": ms_, "T": T, "venue": venue, "symbol": s,
                        "lighter": lsym, "market_id": mid_, "d": d, "e": row["e"], "F": row["F"],
                        "h_prev": row["h_prev"], "theta_book": theta_book(row["e"]), "s_bid": sb, "s_ask": sa,
                        "s_fill": sp, "s_usd": round(sg, 2), "h_bid": hb, "h_ask": ha, "h_fill": hp,
                        "h_usd": round(hg, 2), "fee_s_bp": fee, "fee_h_bp": fee_h,
                        "late_s": round((ms_ - (T - H)) / 1000), "thin": ""})
        append("tickets", new)
        append("signals", sigs)
        append("decisions", [{**dec, "on_lighter": len(both), "logged": len(sigs), "candidates": len(cands),
                              "entered": len(new)}])
        total += len(new)
    return total


def contract_size(venue, symbol):
    if venue == "mexc":
        tab = mexc.contracts(refresh=False)
        return float(tab.set_index("symbol").contract_size.get(symbol, math.nan))
    return next((float(c["quanto_multiplier"]) for c in carrylane._json(f"{GATE}/contracts") if c["name"] == symbol),
                math.nan)


def exit_hops(now_ms, tickets):
    """Close every open hop whose T + 1 h has passed. A failed read is retried at once, then at the next tick."""
    new = []
    for t in open_hops(tickets):
        if now_ms < int(t["T"]) + H:
            continue
        try:
            size = retry(lambda: contract_size(t["venue"], t["symbol"]))
            bs = retry(lambda: BOOK[t["venue"]](t["symbol"], size))
            bh = retry(lambda: book_lighter(int(t["market_id"])))
        except Exception as e:  # noqa: BLE001 - retried at the next tick, and the exit is then late
            log("exit failed", t["hop"], e)
            continue
        if not size > 0:
            log("exit: no contract size", t["hop"])
            continue
        if not (bs["bids"] and bs["asks"] and bh["bids"] and bh["asks"]):
            log("exit book empty", t["hop"])
            continue
        ms_ = clock_ms()
        d = int(t["d"])
        sp, sg, sthin = side_fill(bs, buy=d > 0, complete=False)
        hp, hg, hthin = side_fill(bh, buy=d < 0, complete=False)
        (sb, sa), (hb, ha) = best(bs), best(bh)
        new.append({**{k: t[k] for k in ("hop", "T", "venue", "symbol", "lighter", "market_id", "d", "e", "F",
                                         "h_prev", "theta_book", "fee_s_bp", "fee_h_bp")},
                    "action": "exit", "ms": ms_, "s_bid": sb, "s_ask": sa, "s_fill": sp, "s_usd": round(sg, 2),
                    "h_bid": hb, "h_ask": ha, "h_fill": hp, "h_usd": round(hg, 2),
                    "late_s": round((ms_ - (int(t["T"]) + H)) / 1000), "thin": "s" * sthin + "h" * hthin})
    return new


def score_hops(now_ms, tickets):
    done = {r["hop"] for r in read("scored")}
    exits = {t["hop"]: t for t in tickets if t["action"] == "exit"}
    path = read("path")
    new = []
    for t in tickets:
        if t["action"] != "enter" or t["hop"] in done or t["hop"] not in exits:
            continue
        x = exits[t["hop"]]
        if now_ms < int(x["ms"]) + SCORE_AFTER:
            continue
        a, b = int(t["ms"]), int(x["ms"])
        try:
            sr = s_funding(t["venue"], t["symbol"], a, b)
            hr = lighter_fundings(int(t["market_id"]), a - H, b + H)
        except Exception as e:  # noqa: BLE001 - retried at the next tick
            log("funding read failed", t["hop"], e)
            continue
        on_time = int(t["late_s"]) <= ON_TIME_S and int(x["late_s"]) <= ON_TIME_S
        new.append({**{k: t[k] for k in ("hop", "venue", "symbol", "lighter", "T", "d", "e", "theta_book")},
                    "entry_ms": a, "exit_ms": b, "on_time": on_time,
                    **score(t, x, sr, hr, [p for p in path if p["hop"] == t["hop"]])})
    return new


def _finite(v, nd=6):
    return round(float(v), nd) if v is not None and math.isfinite(float(v)) else None


def status(now_ms=None, write=True):
    """The lane's state; `tick` writes it to status.json, the `status` command only prints it."""
    now_ms = now_ms or clock_ms()
    tickets, scored, decs = read("tickets"), read("scored"), read("decisions")
    prim = primary(scored)
    state, text = verdict(prim, now_ms)
    nets = [float(r["net1_web"]) for r in prim]
    mu, t = decide_stats(nets, [r["T"] for r in prim])
    g = gate.go_real(nets, [r["T"] for r in prim])

    def book(venue, th):
        rs = [r for r in scored if r["venue"] == venue and float(r["theta_book"]) >= th * 100 - 1e-9
              and str(r["on_time"]) == "True"]
        out = {"scored": len(rs)}
        for col in ("net1_web", "net2_web", "net3_web", "net1_api"):
            v = [float(r[col]) for r in rs]
            out[col] = _finite(np.mean(v)) if v else None
        out["hit_web"] = _finite(np.mean([float(r["net1_web"]) > 0 for r in rs]), 3) if rs else None
        return out

    s = {"registry": REGISTRY, "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_ms / 1000)),
         "state": state, "decision": text, "scored": len(prim),
         "mean_net": _finite(mu),
         "mean_net_2x": _finite(np.mean([float(r["net2_web"]) for r in prim])) if prim else None,
         "t_cr1": _finite(t, 3),
         "trimmed10": _finite(trimmed(nets)),
         "leave_two_coins_out": _finite(leave_two_coins_out(nets, [r["symbol"] for r in prim])),
         "go_real": {"pass": g["pass"], "n": g["n"], "mean": _finite(g["mean"]), "hit": _finite(g["hit"], 3),
                     "worst": _finite(g["worst"]), "n_clusters": g["n_clusters"], "checks": g["checks"]},
         "tickets": sum(1 for x in tickets if x["action"] == "enter"), "open": len(open_hops(tickets)),
         "decisions": len(decs), "decision_errors": sum(1 for x in decs if x.get("error")),
         "late_decisions": sum(1 for x in decs if int(x["late_s"] or 0) > ON_TIME_S),
         "books": {f"{v} th{th * 100:.1f}%": book(v, th) for v in VENUES for th in THETAS}}
    if write:
        JOURNAL.mkdir(parents=True, exist_ok=True)
        (JOURNAL / "status.json").write_text(json.dumps(s, indent=1) + "\n")
    return s


def tick(now_ms=None):
    now_ms = now_ms or clock_ms()
    tickets = read("tickets")
    out = exit_hops(now_ms, tickets)
    append("tickets", out)
    tickets += out
    T = (now_ms // H + 1) * H
    decided = {int(r["T"]) for r in read("decisions")}
    if T not in decided and now_ms - (T - H) <= ON_TIME_S * 1000:
        n = enter_hops(now_ms, T)
        tickets = read("tickets")
        log(f"decision T {time.strftime('%m-%d %H:%M', time.gmtime(T / 1000))}: {n} entered")
    append("scored", score_hops(now_ms, tickets))
    return status(now_ms)


def path_once(now_ms=None):
    """One minute's bulk quotes for every open hop."""
    hops = open_hops(read("tickets"))
    if not hops:
        return 0
    now_ms = now_ms or clock_ms()
    q = {}
    try:
        if any(h["venue"] == "mexc" for h in hops):
            q["mexc"] = {x["symbol"]: (x.get("bid1"), x.get("ask1"), x.get("fairPrice")) for x in mexc.get("ticker")}
        if any(h["venue"] == "gate" for h in hops):
            q["gate"] = {x["contract"]: (x.get("highest_bid"), x.get("lowest_ask"), x.get("mark_price"))
                         for x in carrylane._json(f"{GATE}/tickers")}
        lt = {int(d["market_id"]): (d.get("last_trade_price"), d.get("mark_price"))
              for d in carrylane._lighter_details()}
    except Exception as e:  # noqa: BLE001 - a missed minute is a gap in a reported path
        log("path read failed", e)
        return 0
    rows = []
    for h in hops:
        s = q.get(h["venue"], {}).get(h["symbol"], (None, None, None))
        l = lt.get(int(h["market_id"]), (None, None))
        rows.append({"ms": now_ms, "hop": h["hop"], "s_bid": s[0], "s_ask": s[1], "s_mark": s[2], "h_last": l[0],
                     "h_mark": l[1]})
    append("path", rows)
    return len(rows)


def run():
    """The lane's scheduler: a tick at hh:00:20, and the path every minute while a hop is open."""
    with writer_lock():
        log("settlehop_fwd run started")
        try:
            tick()
        except Exception as e:  # noqa: BLE001 - the next hour retries
            log("tick failed", e)
        while True:
            now = time.time()
            nxt = (now // 3600 + 1) * 3600 + DECIDE_AT_S
            while time.time() < nxt - 1:
                if open_hops(read("tickets")):
                    path_once()
                time.sleep(max(1.0, min(60 - time.time() % 60 + 5, nxt - time.time())))
            check()                       # a changed PREREG or rule stops the lane here, loudly
            try:
                s = tick()
                log("tick", s["state"], s["decision"], "open", s["open"], "tickets", s["tickets"])
            except Exception as e:  # noqa: BLE001 - the next hour retries; exits and scores are idempotent
                log("tick failed", e)


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
        log("settlehop_fwd running:", s.get("decision", "no status yet"))
        return 0
    fcntl.flock(f, fcntl.LOCK_UN)
    f.close()
    check()                                   # never start a lane whose PREREG or rule changed
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a") as out:
        subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "run"], cwd=ROOT, stdout=out,
                         stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
    log("settlehop_fwd started; log", LOG)
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
