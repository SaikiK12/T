"""R500 carrycost_hist_v2 (R499's question, costs derived at fetch time): what R390's C14 book (binance+gate, R275's v1 engine) would have paid at each of its real
entries and exits, 2021-07..2026-09, on the venues' recorded order books instead of the flat 7 bp a leg a side.

Gate leg (exact hour): Gate's public bulk archive keeps every USDT perp's order book hour by hour
(`futures_usdt/orderbooks/YYYYMM/<CONTRACT>-YYYYMMDDHH.csv.gz`: a `set` snapshot at the hour start, then `make` (add)
and `take` (remove) deltas; size > 0 is a bid, size < 0 an ask, in contracts). The book is replayed for 00:00-01:00
UTC of the event day and sampled at each minute boundary. Contracts become coins through Gate's quanto multiplier
(R499's frozen `gate_multipliers.csv`). The hour file is reduced to its per-side costs as soon as it is read and is never
stored: the session's disk allowance could not hold about 3 GB of raw hours (why R499 was superseded).

Binance leg (proxy): Tardis.dev's free first-day-of-month files (`binance-futures/book_snapshot_25`, no key). Only the
first 15 minutes of the event month's first day are read (the stream is closed after 00:15 UTC) and sampled the same way.
Raw files stay under /data (git-ignored; Tardis's terms bar redistribution). Only per-event costs, which are
aggregates over 15 or 60 minutes, are written to the lane.

The cost of an order of N dollars on one side is the walk of the book from the mid: (VWAP / mid - 1) x 1e4 for a
buy and (1 - VWAP / mid) x 1e4 for a sell. An event's cost is the median over the minute samples that could fill it
(Gate: at least 30 of 60; Binance: at least 8 of 15), else it is unmeasured. Fees are added after: Gate 7.5 bp, Binance 5 bp (taker, base tier).

Paper research only: nothing here can place an order.

    python scripts/run_carrycost_hist_v2.py fetch    # download and reduce (resumable, capped at 4.5 GB transferred)
    python scripts/run_carrycost_hist_v2.py run      # costs, book net and the verdict (PREREG must verify)
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import statistics
import sys
import threading
import time
import zlib
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
LANE = ROOT / "experiments" / "carrycost_hist_v2"
DATA = ROOT / "data" / "carrycost_hist_v2"
OLD = ROOT / "data" / "carrycost_hist"          # R499's interrupted fetch: raw Gate hours and 60-minute Binance samples
BOOK = "binance+gate L14d th10% K20"
SLOTS = 20
SIZES = (250, 1000, 5000)
FEE_BP = {"gate": 7.5, "binance": 5.0}
FLAT_BP = 7.0                      # the archive's cost per leg per side (1x)
HURDLE_PCT = 4.13                  # R275's T-bill hurdle, as R437 used it
WINDOW = ("2021-07-01", "2026-09-30")
MIN_SAMPLES = 30
BIN_MINUTES, BIN_MIN = 15, 8
HOWS = ("median", "snap0", "best")
BYTE_CAP = 4_500_000_000
GATE_URL = "https://gateio-public-data.s3.amazonaws.com/futures_usdt/orderbooks/{ym}/{sym}-{ymd}00.csv.gz"
TARDIS_URL = "https://datasets.tardis.dev/v1/binance-futures/book_snapshot_25/{y}/{m}/01/{sym}.csv.gz"
UA = {"User-Agent": "research-client/1.0"}


def _rows(path):
    with Path(path).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------- order-book arithmetic ----------

def walk(levels, notional):
    """VWAP of filling `notional` dollars through [(price, qty_coins), ...] in priority order; None if too thin."""
    left, coins = float(notional), 0.0
    for p, q in levels:
        if p <= 0 or q <= 0:
            continue
        take = min(left, p * q)
        coins += take / p
        left -= take
        if left <= 1e-9:
            return notional / coins
    return None


def cost_bp(bids, asks, side, notional):
    """One-side cost in bp of mid for a market order of `notional` dollars; None when the book cannot fill it."""
    if not bids or not asks:
        return None
    bb, ba = bids[0][0], asks[0][0]
    if bb >= ba:
        return None
    mid = (bb + ba) / 2.0
    v = walk(asks if side == "buy" else bids, notional)
    if v is None:
        return None
    return (v / mid - 1.0) * 1e4 if side == "buy" else (1.0 - v / mid) * 1e4


def event_cost(samples, side, notional, how="median", min_n=MIN_SAMPLES):
    """Aggregate over minute samples: 'median' (primary), 'snap0' (the first sample) or 'best' (the lowest)."""
    vals = [cost_bp(b, a, side, notional) for b, a in samples]
    if how == "snap0":
        return vals[0] if vals else None
    ok = [v for v in vals if v is not None]
    if len(ok) < min_n:
        return None
    return statistics.median(ok) if how == "median" else min(ok)


# ---------- Gate: replay an hourly archive file ----------

def gate_samples(lines, hour_start, mult, minutes=60):
    """Replay Gate's hourly order-book rows (ts, action, price, size, id, n) and return the book at each minute
    boundary hour_start + 60 m, m = 0..minutes-1, as (bids desc, asks asc) with quantities in coins."""
    bids, asks = defaultdict(float), defaultdict(float)
    out, m = [], 0

    def snap():
        b = sorted(((p, q * mult) for p, q in bids.items() if q > 1e-12), reverse=True)
        a = sorted((p, q * mult) for p, q in asks.items() if q > 1e-12)
        return b, a

    for line in lines:
        parts = line.strip().split(",")
        if len(parts) < 4:
            continue
        ts, act, p, s = float(parts[0]), parts[1], float(parts[2]), float(parts[3])
        while m < minutes and ts > hour_start + 60 * m:
            out.append(snap())
            m += 1
        book = bids if s > 0 else asks
        if act == "set":
            book[p] = abs(s)
        elif act == "make":
            book[p] += abs(s)
        elif act == "take":
            book[p] -= abs(s)
            if book[p] <= 1e-12:
                book.pop(p, None)
    while m < minutes:
        out.append(snap())
        m += 1
    return out


# ---------- Binance: first hour of a Tardis book_snapshot_25 file ----------

def tardis_samples(lines, day_start, minutes=60):
    """Rows of Tardis book_snapshot_25 (header first; timestamp in microseconds) -> the book at each minute boundary.
    Minute 0 is the first snapshot at or after day_start when none precedes it. Stops reading after the hour."""
    it = iter(lines)
    header = next(it).strip().split(",")
    ti = header.index("timestamp")
    ai = [(header.index(f"asks[{k}].price"), header.index(f"asks[{k}].amount")) for k in range(25)
          if f"asks[{k}].price" in header]
    bi = [(header.index(f"bids[{k}].price"), header.index(f"bids[{k}].amount")) for k in range(25)
          if f"bids[{k}].price" in header]
    end = day_start + 60 * minutes
    out, m, last = [], 0, None

    def parse(row):
        def side(ix):
            lv = []
            for pi, qi in ix:
                if row[pi] and row[qi]:
                    lv.append((float(row[pi]), float(row[qi])))
            return lv
        return side(bi), side(ai)

    for line in it:
        row = line.strip().split(",")
        if len(row) <= ti:
            continue
        ts = int(row[ti]) / 1e6
        while m < minutes and ts > day_start + 60 * m:
            out.append(last if last is not None else parse(row))
            m += 1
        if ts >= end:
            break
        last = parse(row)
    while m < minutes and last is not None:
        out.append(last)
        m += 1
    return out


# ---------- events ----------

def load_events(root=ROOT):
    """Every entry and exit of the C14 book in R275's v1 trade list, with the side each venue trades."""
    syms = {r["key"]: r for r in _rows(root / "experiments/xfund_v1/symbols.csv")}
    ev = []
    for r in _rows(root / "experiments/xfund_v1/results/trades.csv"):
        if r["strategy"] != BOOK:
            continue
        for kind, day in (("entry", r["entry"]), ("exit", r["exit"])):
            if not day:
                continue
            buy_long = kind == "entry"
            side = {r["long"]: "buy" if buy_long else "sell", r["short"]: "sell" if buy_long else "buy"}
            ev.append({"day": day, "coin": r["coin"], "kind": kind, "gate_sym": syms[r["coin"]]["gate"],
                       "binance_sym": syms[r["coin"]]["binance"], "gate_side": side["gate"],
                       "binance_side": side["binance"]})
    ev.sort(key=lambda e: (e["day"], e["coin"], e["kind"]))
    return ev


def multipliers(root=ROOT):
    """Gate quanto multipliers (coins per contract) for every C14 contract, fetched once from Gate's public contract
    endpoint on 2026-11-17 (delisted contracts included) and frozen with the lane."""
    return {r["name"]: float(r["quanto_multiplier"]) for r in _rows(
        root / "experiments/carrycost_hist_v1/gate_multipliers.csv") if r["quanto_multiplier"]}


def order_key(s):
    return hashlib.sha256(s.encode()).hexdigest()


# ---------- fetch ----------

_lock = threading.Lock()


def _manifest_add(row):
    path = DATA / "manifest.csv"
    with _lock:
        new = not path.exists()
        with path.open("a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["kind", "key", "url", "status", "bytes", "sha256", "fetched_utc"])
            if new:
                w.writeheader()
            w.writerow(row)


def _done_keys():
    path = DATA / "manifest.csv"
    if not path.exists():
        return {}
    return {(r["kind"], r["key"]): r for r in _rows(path)}


def gate_metrics(raw_gz, day, mult):
    """Per-side event costs from one raw Gate hour file (bytes, gzip): {side: {how_size: bp or None}}."""
    hour = datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp()
    lines = gzip.decompress(raw_gz).decode().splitlines()
    smp = gate_samples(lines, hour, mult)
    return {side: {f"{how}_{n}": event_cost(smp, side, n, how) for how in HOWS for n in SIZES}
            for side in ("buy", "sell")}


def fetch_gate(sym, day, sess, mults=None):
    ym, ymd = day[:4] + day[5:7], day.replace("-", "")
    url = GATE_URL.format(ym=ym, sym=sym, ymd=ymd)
    old = OLD / "gate" / f"{sym}-{ymd}00.csv.gz"
    got, raw, met = 0, None, None
    mult = (mults or multipliers()).get(sym)
    if old.exists():
        try:
            raw = old.read_bytes()
            met = gate_metrics(raw, day, mult) if mult else None
        except (OSError, EOFError, zlib.error, UnicodeDecodeError):
            raw = None                            # a copy cut short when R499's fetch stopped: fetch it again
    if raw is None:
        r = sess.get(url, headers=UA, timeout=60)
        if r.status_code != 200:
            return {"status": r.status_code, "bytes": 0, "sha256": ""}
        raw, got = r.content, len(r.content)
        try:
            met = gate_metrics(raw, day, mult) if mult else None
        except (OSError, EOFError, zlib.error, UnicodeDecodeError):
            return {"status": "bad_file", "bytes": got, "sha256": hashlib.sha256(raw).hexdigest()}
    out = DATA / "gate" / f"{sym}-{ymd}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(met))
    if old.exists():
        old.unlink()                              # R499's raw copy, reduced and released
    return {"status": 200, "bytes": got, "sha256": hashlib.sha256(raw).hexdigest()}


def fetch_binance(sym, month, sess):
    """Stream the first 15 minutes of the month's first-day Tardis file; keep the 15 minute samples (derived) only."""
    y, m = month[:4], month[5:7]
    url = TARDIS_URL.format(y=y, m=m, sym=sym)
    day_start = datetime(int(y), int(m), 1, tzinfo=timezone.utc).timestamp()
    out = DATA / "binance" / f"{sym}-{month}.json.gz"
    old = OLD / "binance" / f"{sym}-{month}.json.gz"
    if old.exists():                              # R499's 60 one-minute samples: the first 15 are this lane's
        try:
            samples = json.loads(gzip.decompress(old.read_bytes()))[:BIN_MINUTES]
        except (OSError, EOFError, zlib.error, ValueError):
            samples = None                        # cut short: fetch it again
        old.unlink()
        if samples is not None:
            blob = gzip.compress(json.dumps(samples).encode())
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(blob)
            return {"status": 200, "bytes": 0, "sha256": hashlib.sha256(blob).hexdigest()}
    r = sess.get(url, headers=UA, timeout=120, stream=True)
    if r.status_code != 200:
        r.close()
        return {"status": r.status_code, "bytes": 0, "sha256": ""}
    d = zlib.decompressobj(31)
    got, buf, lines, done = 0, b"", [], False
    for chunk in r.iter_content(65536):
        got += len(chunk)
        buf += d.decompress(chunk)
        *full, buf = buf.split(b"\n")
        for ln in full:
            lines.append(ln.decode())
            if len(lines) > 1:
                ti = lines[0].split(",").index("timestamp")
                parts = lines[-1].split(",")
                if len(parts) > ti and parts[ti].isdigit() and int(parts[ti]) / 1e6 >= day_start + 60 * BIN_MINUTES:
                    done = True
                    break
        if done:
            break
    r.close()
    samples = tardis_samples(lines, day_start, BIN_MINUTES) if len(lines) > 1 else []
    blob = gzip.compress(json.dumps(samples).encode())
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(blob)
    return {"status": 200, "bytes": got, "sha256": hashlib.sha256(blob).hexdigest()}


def fetch(workers=6):
    ev = [e for e in load_events() if WINDOW[0] <= e["day"] <= WINDOW[1]]
    jobs = {}
    for e in ev:
        jobs[("gate", f"{e['gate_sym']}|{e['day']}")] = (fetch_gate, e["gate_sym"], e["day"])
        jobs[("binance", f"{e['binance_sym']}|{e['day'][:7]}")] = (fetch_binance, e["binance_sym"], e["day"][:7])
    done = _done_keys()
    todo = sorted((k for k in jobs if k not in done), key=lambda k: (k[0] != "gate", order_key(k[0] + k[1])))
    mults = multipliers()
    spent = sum(int(r["bytes"] or 0) for r in done.values())
    print(f"{len(jobs)} files, {len(done)} done, {len(todo)} to fetch, {spent / 1e6:.0f} MB already transferred")
    state = {"bytes": spent, "n": 0}

    def one(k):
        if state["bytes"] >= BYTE_CAP:
            return
        fn, sym, when = jobs[k]
        sess = requests.Session()
        for attempt in range(3):
            try:
                res = fn(sym, when, sess, mults) if fn is fetch_gate else fn(sym, when, sess)
                break
            except requests.RequestException as exc:
                res = {"status": f"error:{type(exc).__name__}", "bytes": 0, "sha256": ""}
                time.sleep(2 ** attempt)
        if str(res["status"]).startswith("error"):
            return          # not recorded: retried on the next fetch
        with _lock:
            state["bytes"] += res["bytes"]
            state["n"] += 1
            if state["n"] % 200 == 0:
                print(f"  {state['n']} fetched, {state['bytes'] / 1e6:.0f} MB", flush=True)
        _manifest_add({"kind": k[0], "key": k[1], "url": "", "status": res["status"], "bytes": res["bytes"],
                       "sha256": res["sha256"], "fetched_utc": datetime.now(timezone.utc).isoformat()})

    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(one, todo))
    print(f"done: {state['bytes'] / 1e6:.0f} MB transferred in total")


# ---------- run ----------

def _gate_metrics(sym, day):
    path = DATA / "gate" / f"{sym}-{day.replace('-', '')}.json"
    return json.loads(path.read_text()) if path.exists() else None


def _binance_samples(sym, month):
    path = DATA / "binance" / f"{sym}-{month}.json.gz"
    if not path.exists():
        return None
    return [(list(map(tuple, b)), list(map(tuple, a))) for b, a in json.loads(gzip.decompress(path.read_bytes()))]


def measure(events, mults):
    rows, bcache = [], {}
    for e in events:
        gm = _gate_metrics(e["gate_sym"], e["day"])
        key = (e["binance_sym"], e["day"][:7])
        if key not in bcache:
            bcache[key] = _binance_samples(*key)
        bs = bcache[key]
        row = {k: e[k] for k in ("day", "coin", "kind", "gate_side", "binance_side")}
        for how in HOWS:
            for n in SIZES:
                g = gm[e["gate_side"]][f"{how}_{n}"] if gm else None
                b = event_cost(bs, e["binance_side"], n, how, BIN_MIN) if bs else None
                row[f"gate_{how}_{n}"] = "" if g is None else round(g, 4)
                row[f"binance_{how}_{n}"] = "" if b is None else round(b, 4)
        rows.append(row)
    return rows


def allin(row, venue, how, n, k=1.0):
    """Walk (scaled by k for the cost-sensitivity rows) plus the venue's taker fee, in bp."""
    v = row[f"{venue}_{how}_{n}"]
    return None if v == "" else k * float(v) + FEE_BP[venue]


def book_net(root, events_rows, how, n, k=1.0):
    """Daily net of the v1 book with each event charged its measured all-in cost (Gate + Binance legs); events with a
    missing leg take that leg's median measured all-in cost in the same calendar year (imputed)."""
    by_year = defaultdict(lambda: {"gate": [], "binance": []})
    for r in events_rows:
        for v in ("gate", "binance"):
            c = allin(r, v, how, n, k)
            if c is not None:
                by_year[r["day"][:4]][v].append(c)
    med = {y: {v: (statistics.median(x[v]) if x[v] else None) for v in x} for y, x in by_year.items()}
    cost_day, imputed = defaultdict(float), {"gate": 0, "binance": 0}
    for r in events_rows:
        tot = 0.0
        for v in ("gate", "binance"):
            c = allin(r, v, how, n, k)
            if c is None:
                c = med[r["day"][:4]][v]
                imputed[v] += 1
            tot += c
        cost_day[r["day"]] += tot / 1e4
    daily = [x for x in _rows(root / "experiments/carry_v2_audit_v1/results/daily.csv")
             if x["book"] == BOOK and x["engine"] == "v1" and WINDOW[0] <= x["date"] <= WINDOW[1]]
    nets, flat = [], {"1x": [], "2x": [], "3x": []}
    for i, x in enumerate(daily):
        n1, n2 = float(x["net_1x"]), float(x["net_2x"])
        gross = 2 * n1 - n2                       # gross / (2 K)
        legs = (n1 - n2) * 2 * SLOTS / (FLAT_BP / 1e4)
        c = cost_day.get(x["date"], 0.0)
        if i == len(daily) - 1:                   # closing legs at the end of the archive: imputed, last year
            closes = legs / 2 - sum(1 for r in events_rows if r["day"] == x["date"])
            y = x["date"][:4]
            c += max(closes, 0) * (med[y]["gate"] + med[y]["binance"]) / 1e4
        nets.append(gross - c / (2 * SLOTS))
        flat["1x"].append(n1)
        flat["2x"].append(n2)
        flat["3x"].append(float(x["net_3x"]))
    return nets, flat, imputed


def summarize(nets):
    if not nets:
        return {}
    mu = statistics.mean(nets)
    return {"days": len(nets), "mean_bp_day": round(mu * 1e4, 4), "ann_pct": round(mu * 365 * 100, 3)}


def check_inputs(prereg=None):
    """Every `path` | sha256 row of the PREREG's input table must match the file on disk; refuse to run otherwise."""
    import re
    text = Path(prereg or LANE / "PREREG.md").read_text(encoding="utf-8")
    pairs = re.findall(r"\|\s*`([^`]+)`\s*\|\s*([0-9a-f]{64})\s*\|", text)
    if not pairs:
        raise SystemExit("no input hashes in the PREREG")
    for path, digest in pairs:
        got = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        if got != digest:
            raise SystemExit(f"{path} changed since the freeze: {got} != {digest}")
    return pairs


def run():
    from lab.prereg import verify
    verify(LANE / "PREREG.md")
    check_inputs()
    events = [e for e in load_events() if WINDOW[0] <= e["day"] <= WINDOW[1]]
    rows = measure(events, multipliers())
    res = LANE / "results"
    res.mkdir(parents=True, exist_ok=True)
    with (res / "events.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    report = {"events": len(rows), "window": WINDOW, "fees_bp": FEE_BP, "flat_bp": FLAT_BP, "hurdle_pct": HURDLE_PCT}
    for how in HOWS:
        for n in SIZES:
            cov = {v: sum(1 for r in rows if r[f"{v}_{how}_{n}"] != "") for v in ("gate", "binance")}
            g = [allin(r, "gate", how, n) for r in rows if r[f"gate_{how}_{n}"] != ""]
            b = [allin(r, "binance", how, n) for r in rows if r[f"binance_{how}_{n}"] != ""]
            nets, flat, imp = book_net(ROOT, rows, how, n)
            per_leg = (statistics.mean(g) + statistics.mean(b)) / 2 if g and b else None
            cell = {
                "measured": cov, "imputed": imp,
                "gate_allin_mean_bp": round(statistics.mean(g), 3) if g else None,
                "gate_allin_median_bp": round(statistics.median(g), 3) if g else None,
                "binance_allin_mean_bp": round(statistics.mean(b), 3) if b else None,
                "binance_allin_median_bp": round(statistics.median(b), 3) if b else None,
                "per_leg_side_mean_bp": round(per_leg, 3) if per_leg is not None else None,
                "multiple_of_flat": round(per_leg / FLAT_BP, 3) if per_leg is not None else None,
                "net": summarize(nets), "flat": {m: summarize(v) for m, v in flat.items()},
                "by_year": {y: summarize([v for v, x in zip(nets, _dates()) if x[:4] == y])
                            for y in sorted({d[:4] for d in _dates()})},
                "since_2024": summarize([v for v, x in zip(nets, _dates()) if x >= "2024-01-01"]),
            }
            report[f"{how}_{n}"] = cell
    for k in (2.0, 3.0):
        nets_k, _, _ = book_net(ROOT, rows, "median", 1000, k)
        report["median_1000"][f"net_walk_{k:.0f}x"] = summarize(nets_k)
    p = report["median_1000"]
    miss = {v: round(1 - p["measured"][v] / len(rows), 4) for v in ("gate", "binance")}
    ann = p["net"]["ann_pct"]
    verdict = "COST_OK" if ann >= HURDLE_PCT else ("COST_BINDS" if ann > 0 else "COST_KILLS")
    incomplete = miss["gate"] > 0.20 or miss["binance"] > 0.50
    report["verdict"] = verdict + (" (INCOMPLETE: Gate over 20% or Binance over 50% of events imputed)"
                                   if incomplete else "")
    report["share_events_missing_primary"] = miss
    (res / "report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({k: report[k] for k in ("events", "verdict", "share_events_missing_primary")}))
    print(json.dumps(report["median_1000"], indent=1))


def _dates():
    return [x["date"] for x in _rows(ROOT / "experiments/carry_v2_audit_v1/results/daily.csv")
            if x["book"] == BOOK and x["engine"] == "v1" and WINDOW[0] <= x["date"] <= WINDOW[1]]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=["fetch", "run", "plan"])
    a = ap.parse_args(argv)
    if a.cmd == "plan":
        ev = [e for e in load_events() if WINDOW[0] <= e["day"] <= WINDOW[1]]
        print(len(ev), "events;", len({(e["gate_sym"], e["day"]) for e in ev}), "gate files;",
              len({(e["binance_sym"], e["day"][:7]) for e in ev}), "binance coin-months")
    elif a.cmd == "fetch":
        fetch()
    else:
        sys.path.insert(0, str(ROOT))
        run()


if __name__ == "__main__":
    main()
