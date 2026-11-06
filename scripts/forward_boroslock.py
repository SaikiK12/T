"""boroslock_fwd (R413): Boros funding locks forward on paper, as set out in experiments/boroslock_fwd/PREREG.md. The
rule is scripts/boroslock_fwd_rule.py. R412 showed historically that a lock at the best bid delivered its locked APR;
this lane checks it on live order books, live fees and real settlements, before any real money.

Each run (the forward task graph runs it every hour the host is up):
1. Settles every open paper lock whose maturity has passed, once Boros's settlement files and the venue's funding
   cover its whole life (Hyperliquid: public info API; Binance: data.binance.vision monthly archive).
2. Prices the lock that $10k would sell now in every live BTC/ETH single-venue Binance/Hyperliquid market, walking
   the order book's bids, and appends one row per market to journal/offers.csv.
3. Opens a paper lock in each book (K0, K1) for a coin with none open when the book's rule picks an offer.
4. Writes journal/status.json.
Append-only journals: offers.csv, locks.csv, settlements.csv, tbill.csv. Public endpoints only; places nothing.

usage: python scripts/forward_boroslock.py
"""
import io
import json
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
import boroslock_fwd_rule as rule  # noqa: E402
import forward_lockcarry2 as lc  # noqa: E402  (R406's frozen T-bill and journal helpers, reused as is)
import lockcarry_rule  # noqa: E402

LANE = ROOT / "experiments" / "boroslock_fwd"
J = LANE / "journal"
API = "https://api-boros.pendle.finance/apis/v1"
HIST = "https://historical-data.boros.finance"
HL = "https://api.hyperliquid.xyz/info"
BNV = "https://data.binance.vision/data/futures/um/monthly/fundingRate"
OFFER_COLS = ["t", "market", "venue", "coin", "token", "maturity", "tau_days", "best_bid", "best_ask", "book_bid",
              "fill_apr", "locked", "tbill", "excess", "carry", "fills_capacity", "oi", "floating_apr", "sync_lag_s"]
LOCK_COLS = ["book", "market", "venue", "coin", "token", "t0", "maturity", "tau_days", "period", "fee", "fill_apr",
             "locked", "tbill", "excess", "carry"]
SETTLE_COLS = ["book", "market", "venue", "coin", "t0", "maturity", "tau_days", "settled_at", "locked", "venue_sum",
               "boros_sum", "diff_bp", "fidelity_apr", "realized", "misses", "tbill_paid_ann", "excess_1x",
               "excess_2x", "excess_3x"]
log = lambda *a: print(time.strftime("%H:%M:%S", time.gmtime()), *a, flush=True)


def get(url, data=None, timeout=30):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "lab/1", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def scope(m):
    """The market as a dict if it is a live single-venue BTC/ETH market on Binance/Hyperliquid, else None."""
    md, im = m["metadata"], m["imData"]
    venue = im["symbol"].split("-")[0]
    if md.get("isSpreadMarket") or venue not in rule.VENUES or md.get("underlyingSymbol") not in rule.COINS:
        return None
    return {"id": m["marketId"], "market": f"{m['marketId']}-{im['symbol']}", "venue": venue,
            "coin": md["underlyingSymbol"], "token": m["tokenId"], "maturity": int(im["maturity"]),
            "taker": int(m["config"]["takerFee"]) / 1e18, "settle": int(m["extConfig"]["settleFeeRate"]) / 1e18,
            "period": int(m["extConfig"]["paymentPeriod"]), "data": m.get("data") or {}}


def live_markets(fetch=get):
    out, tok = [], None
    for _ in range(20):
        j = json.loads(fetch(f"{API}/markets?isMatured=false&limit=100" + (f"&resumeToken={tok}" if tok else "")))
        out += j.get("results") or []
        tok = j.get("resumeToken")
        if not tok or not j.get("results"):
            break
    return [s for s in map(scope, out) if s]


def prices(fetch=get):
    return {a["tokenId"]: float(a["usdPrice"]) for a in json.loads(fetch(f"{API}/assets"))["results"]
            if a.get("usdPrice")}


def offers(now_s, tbill, fetch=get):
    px, out = prices(fetch), []
    for mk in live_markets(fetch):
        try:
            ob = json.loads(fetch(f"{API}/markets/order-book?marketId={mk['id']}&tickSize={rule.TICK}&includeAmm=true"))
        except (OSError, ValueError) as e:
            log(f"{mk['market']}: order book failed {e}")
            continue
        bids = rule.levels(ob.get("long") or {})
        o = rule.offer(mk, bids, px.get(mk["token"]), now_s, tbill)
        if o is None:
            continue
        d = mk["data"]
        o.update(t=now_s, market=mk["market"], venue=mk["venue"], coin=mk["coin"], token=mk["token"],
                 maturity=mk["maturity"], period=mk["period"], fee=mk["taker"] + mk["settle"], tbill=tbill,
                 best_bid=d.get("bestBid"), best_ask=d.get("bestAsk"), book_bid=bids[0][0] if bids else None,
                 oi=d.get("notionalOI"), floating_apr=d.get("floatingApr"),
                 sync_lag_s=now_s - int((ob.get("syncStatus") or {}).get("timestamp") or now_s))
        out.append(o)
    return out


def months(t0, t1):
    a, b = time.gmtime(t0), time.gmtime(t1)
    y, m, out = a.tm_year, a.tm_mon, []
    while (y, m) <= (b.tm_year, b.tm_mon):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def zipped_lines(body):
    with zipfile.ZipFile(io.BytesIO(body)) as z:
        return [line for n in z.namelist() for line in z.read(n).decode().splitlines() if line.strip()]


def boros_settlements(market, t0, t1, fetch=get):
    """[(ts, settlementApr)] over the months of [t0, t1]; None if a month is not published yet."""
    out = []
    for ym in months(t0, t1):
        try:
            body = fetch(f"{HIST}/settlement/{market}/{ym}.ndjson.zip")
        except OSError:
            return None
        out += [(int(r["timestamp"]), float(r["settlementApr"])) for r in map(json.loads, zipped_lines(body))]
    return sorted(set(out))


def venue_funding(venue, coin, t0, t1, fetch=get):
    """[(ts s, rate per period)] covering [t0, t1]; None until the data reaches t1."""
    out = []
    if venue == "HYPERLIQUID":
        start = t0 * 1000
        for _ in range(100):
            body = json.dumps({"type": "fundingHistory", "coin": coin, "startTime": start}).encode()
            rows = json.loads(fetch(HL, data=body))
            if not rows:
                break
            out += [(int(round(int(r["time"]) / 60000)) * 60, float(r["fundingRate"])) for r in rows]
            last = int(rows[-1]["time"])
            if last // 1000 >= t1 or len(rows) < 2:
                break
            start = last + 1
    else:
        for ym in months(t0, t1):
            try:
                body = fetch(f"{BNV}/{coin}USDT/{coin}USDT-fundingRate-{ym}.zip")
            except OSError:
                return None
            for line in zipped_lines(body):
                f = line.split(",")
                if f[0].isdigit():
                    out.append((int(round(int(f[0]) / 60000)) * 60, float(f[2])))
    out = sorted(set(out))
    return out if out and out[-1][0] >= t1 else None


def settle_due(now_s, series, fetch=get, j=None):
    j = j or J
    done = {(r["book"], r["market"], r["t0"]) for r in lc.rows(j / "settlements.csv")}
    out = []
    for lk in lc.rows(j / "locks.csv"):
        t0, T = int(lk["t0"]), int(lk["maturity"])
        if (lk["book"], lk["market"], lk["t0"]) in done or now_s < T + 7200:
            continue
        try:
            b = boros_settlements(lk["market"], t0, T, fetch)
            v = venue_funding(lk["venue"], lk["coin"], t0, T, fetch)
        except (OSError, ValueError, KeyError) as e:
            log(f"settle {lk['market']} failed: {e}")
            continue
        if b is None or v is None or not any(t > T for t, _ in b):
            continue                               # wait until the maturity settlement and the venue data exist
        s = rule.settle(lk, b, v)
        tau = float(lk["tau_days"])
        paid = lc.tbill_paid(series, t0 * 1000, T * 1000)
        paid_ann = paid * 365 / tau if paid is not None else None
        ex = {f"excess_{m}x": rule.excess_ann(s["realized"], float(lk["fee"]), paid_ann, tau, m)
              if paid_ann is not None else None for m in (1, 2, 3)}
        out.append({**{k: lk[k] for k in ("book", "market", "venue", "coin", "t0", "maturity", "tau_days", "locked")},
                    "settled_at": now_s, **s, "tbill_paid_ann": paid_ann, **ex})
    lc.append(j / "settlements.csv", SETTLE_COLS, out)
    return out


def open_locks(offs, j=None):
    j = j or J
    settled = {(r["book"], r["market"], r["t0"]) for r in lc.rows(j / "settlements.csv")}
    held = {(r["book"], r["coin"]) for r in lc.rows(j / "locks.csv")
            if (r["book"], r["market"], r["t0"]) not in settled}
    new = []
    for bk, floor in rule.BOOKS.items():
        for coin in rule.COINS:
            if (bk, coin) in held:
                continue
            o = rule.choose([x for x in offs if x["coin"] == coin], floor)
            if o:
                new.append({"book": bk, "t0": o["t"], **o})
    lc.append(j / "locks.csv", LOCK_COLS, new)
    return new


def status(j=None):
    j = j or J
    offs, locks, sets = lc.rows(j / "offers.csv"), lc.rows(j / "locks.csv"), lc.rows(j / "settlements.csv")
    best = {}
    for o in offs:
        best[(o["t"], o["coin"])] = max(best.get((o["t"], o["coin"]), -9.0), float(o["carry"]))
    b = list(best.values())
    done = {(s["book"], s["market"], s["t0"]) for s in sets}
    out = {"ticks": len({o["t"] for o in offs}), "locks": len(locks), "settled": len(sets),
           "share_best_carry_ge_0": sum(x >= 0 for x in b) / len(b) if b else None,
           "share_best_carry_ge_1pct": sum(x >= 0.01 for x in b) / len(b) if b else None,
           "open": [{k: r[k] for k in ("book", "market", "locked", "carry")} for r in locks
                    if (r["book"], r["market"], r["t0"]) not in done],
           "settlements": [{k: s[k] for k in ("book", "market", "diff_bp", "misses", "excess_1x")} for s in sets],
           "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    j.mkdir(parents=True, exist_ok=True)
    (j / "status.json").write_text(json.dumps(out, indent=1))
    return out


def main(fetch=get, now_s=None):
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12], "; inputs", lc.verify_inputs(LANE / "PREREG.md"))
    now_s = now_s or int(time.time())
    series = lc.tbill_series(now_s * 1000, j=J)
    tb = lockcarry_rule.tbill_asof(series, now_s * 1000)
    for s in settle_due(now_s, series, fetch):
        log(f"settled {s['book']} {s['market']}: diff {s['diff_bp']:.2f} bp, {s['misses']} oracle misses")
    if tb is None:
        log("no T-bill value known: no offers, no locks")
        status()
        return 0
    try:
        offs = offers(now_s, tb, fetch)
    except (OSError, ValueError, KeyError) as e:
        log(f"market list failed: {e}")
        offs = []
    lc.append(J / "offers.csv", OFFER_COLS, offs)
    for lk in open_locks(offs):
        log(f"paper lock {lk['book']} {lk['market']}: locked {lk['locked'] * 100:.2f}%/yr, "
            f"carry {lk['carry'] * 100:.2f}%/yr over T-bill {tb * 100:.2f}%")
    s = status()
    log(f"{len(offs)} offers; {s['locks']} locks, {s['settled']} settled")
    return 0


if __name__ == "__main__":
    sys.exit(main())
