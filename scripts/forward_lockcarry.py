"""lockcarry_fwd (R405): R335's locked cash-and-carry, forward on paper on Deribit, as set out in
experiments/lockcarry_fwd/PREREG.md. The rule is scripts/lockcarry_rule.py.

Each run (the forward task graph runs it every hour the host is up):
1. Settles every open paper lock whose delivery has passed, from Deribit's published delivery price.
2. Prices the lock that $10k would buy now on every BTC and ETH dated future (USDC spot book, inverse future book,
   Deribit's listed taker fees), and appends one row per contract to journal/offers.csv.
3. Opens a paper lock in each book (H0, H3) for a coin with none open when the book's rule picks an offer.
4. Writes journal/status.json.
Append-only journals: offers.csv, locks.csv, settlements.csv, tbill.csv. Public endpoints only; places nothing.

usage: python scripts/forward_lockcarry.py
"""
import calendar
import csv
import io
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
import lockcarry_rule as rule  # noqa: E402

LANE = ROOT / "experiments" / "lockcarry_fwd"
J = LANE / "journal"
API = "https://www.deribit.com/api/v2/public"
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTB3"
COINS = ("BTC", "ETH")
DEPTH = 50
OFFER_COLS = ["t_ms", "coin", "contract", "expiry_ms", "tau_days", "tbill", "s_avg", "f_avg", "locked_usd",
              "locked_yield", "excess", "fills_capacity"]
LOCK_COLS = ["book", "coin", "contract", "t_ms", "expiry_ms", "tau_days", "tbill", "s_avg", "f_avg", "coins", "q_usd",
             "unhedged_coins", "exit_cost", "locked_usd", "locked_yield", "excess"]
SETTLE_COLS = ["book", "coin", "contract", "t_ms", "expiry_ms", "settled_at_ms", "delivery_price", "coins_end",
               "usd_out", "locked_usd", "diff_bp", "realized_ret", "tbill_paid_ret", "excess_ann"]
log = lambda *a: print(time.strftime("%H:%M:%S", time.gmtime()), *a, flush=True)


def http(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "lab/1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def api(path, get=http):
    return json.loads(get(f"{API}/{path}"))["result"]


def rows(path):
    if not path.exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def append(path, cols, recs):
    if not recs:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists() or path.stat().st_size == 0
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore", lineterminator="\n")
        if new:
            w.writeheader()
        w.writerows(recs)


def tbill_series(now_ms, get=http, j=None):
    """[(t_ms, pct)] from journal/tbill.csv, refreshed from FRED DTB3 at most once a day (new dates appended)."""
    j = j or J
    path = j / "tbill.csv"
    have = [(int(r["t_ms"]), float(r["pct"])) for r in rows(path)]
    fresh = path.exists() and now_ms - path.stat().st_mtime * 1000 < rule.DAY_MS
    if not fresh:
        try:
            text = get(FRED).decode()
            seen = {t for t, _ in have}
            new = []
            for r in csv.DictReader(io.StringIO(text)):
                k = next(iter(r))
                v = r.get("DTB3", "")
                try:
                    t = calendar.timegm(time.strptime(r[k], "%Y-%m-%d")) * 1000
                    pct = float(v)
                except (ValueError, TypeError):
                    continue
                if t not in seen and t >= now_ms - 400 * rule.DAY_MS:
                    new.append({"t_ms": t, "pct": pct})
            append(path, ["t_ms", "pct"], sorted(new, key=lambda r: r["t_ms"]))
            have += [(r["t_ms"], r["pct"]) for r in new]
        except OSError as e:
            log("FRED failed", e)
    return sorted(have)


def book(name, get=http):
    b = api(f"get_order_book?instrument_name={name}&depth={DEPTH}", get)
    return [(float(p), float(q)) for p, q in b.get("bids") or []], [(float(p), float(q)) for p, q in b.get("asks") or []]


def offers(coin, now_ms, tbill, get=http):
    spot = next(i for i in api(f"get_instruments?currency={coin}&kind=spot", get)
                if i["instrument_name"] == f"{coin}_USDC")
    s_bids, s_asks = book(spot["instrument_name"], get)
    out = []
    for i in api(f"get_instruments?currency={coin}&kind=future", get):
        if i.get("settlement_period") == "perpetual" or "PERPETUAL" in i["instrument_name"]:
            continue
        f_bids, _ = book(i["instrument_name"], get)
        args = (s_bids, s_asks, f_bids, float(i["contract_size"]), int(i["expiration_timestamp"]), now_ms,
                float(spot["taker_commission"]), float(i["taker_commission"]))
        o = rule.offer(*args)
        if o is None:
            continue
        o.update(coin=coin, contract=i["instrument_name"], expiry_ms=int(i["expiration_timestamp"]), t_ms=now_ms,
                 tbill=tbill, excess=o["locked_yield"] - tbill,
                 fills_capacity=rule.offer(*args, usd=rule.CAPACITY) is not None)
        out.append(o)
    return out


def delivery_price(coin, expiry_ms, get=http):
    day = time.strftime("%Y-%m-%d", time.gmtime(expiry_ms / 1000))
    data = api(f"get_delivery_prices?index_name={coin.lower()}_usd&count=40", get)["data"]
    return next((float(d["delivery_price"]) for d in data if d["date"] == day), None)


def tbill_paid(series, t0, t1):
    """Simple return the T-bill paid over [t0, t1]: the mean DTB3 dated in that span (else the last before it)."""
    vals = [v for t, v in series if t0 <= t <= t1] or [v for t, v in series if t <= t0][-1:]
    return (sum(vals) / len(vals) / 100.0) * (t1 - t0) / (365 * rule.DAY_MS) if vals else None


def settle_due(now_ms, series, get=http, j=None):
    j = j or J
    done = {(r["book"], r["contract"], r["t_ms"]) for r in rows(j / "settlements.csv")}
    out = []
    for lk in rows(j / "locks.csv"):
        if (lk["book"], lk["contract"], lk["t_ms"]) in done or now_ms < int(lk["expiry_ms"]) + 3_600_000:
            continue
        p = delivery_price(lk["coin"], int(lk["expiry_ms"]), get)
        if p is None:
            continue
        num = {k: float(lk[k]) for k in ("coins", "q_usd", "f_avg", "exit_cost", "locked_usd")}
        s = rule.settle(num, p)
        paid = tbill_paid(series, int(lk["t_ms"]), int(lk["expiry_ms"]))
        tau = float(lk["tau_days"])
        out.append({**{k: lk[k] for k in ("book", "coin", "contract", "t_ms", "expiry_ms", "locked_usd")},
                    "settled_at_ms": now_ms, "delivery_price": p, **s, "tbill_paid_ret": paid,
                    "excess_ann": (s["realized_ret"] - paid) * 365 / tau if paid is not None else None})
    append(j / "settlements.csv", SETTLE_COLS, out)
    return out


def open_locks(now_ms, offs, tbill, j=None):
    j = j or J
    settled = {(r["book"], r["contract"], r["t_ms"]) for r in rows(j / "settlements.csv")}
    held = {(r["book"], r["coin"]) for r in rows(j / "locks.csv")
            if (r["book"], r["contract"], r["t_ms"]) not in settled}
    new = []
    for bk, hurdle in rule.HURDLES.items():
        for coin in COINS:
            if (bk, coin) in held:
                continue
            o = rule.choose([x for x in offs if x["coin"] == coin], tbill, hurdle, rule.PICK[bk])
            if o:
                new.append({"book": bk, **o})
    append(j / "locks.csv", LOCK_COLS, new)
    return new


def status(j=None):
    j = j or J
    offs, locks, sets = rows(j / "offers.csv"), rows(j / "locks.csv"), rows(j / "settlements.csv")
    hours = {}
    for o in offs:
        k = (o["t_ms"], o["coin"])
        if float(o["tau_days"]) >= rule.MIN_DAYS:
            hours[k] = max(hours.get(k, -9.0), float(o["excess"]))
    best = list(hours.values())
    out = {"ticks": len({o["t_ms"] for o in offs}), "locks": len(locks), "settled": len(sets),
           "share_best_excess_ge_0": sum(b >= 0 for b in best) / len(best) if best else None,
           "share_best_excess_ge_3pct": sum(b >= 0.03 for b in best) / len(best) if best else None,
           "open": [{k: r[k] for k in ("book", "coin", "contract", "locked_yield", "excess")} for r in locks
                    if (r["book"], r["contract"], r["t_ms"]) not in {(s["book"], s["contract"], s["t_ms"]) for s in sets}],
           "settlements": [{k: s[k] for k in ("book", "coin", "contract", "diff_bp", "excess_ann")} for s in sets],
           "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (j / "status.json").write_text(json.dumps(out, indent=1))
    return out


def verify_inputs(prereg_path=None):
    """Every '<sha256>  <path>' line of the PREREG must match that file now."""
    import hashlib
    import re
    text = Path(prereg_path or LANE / "PREREG.md").read_text()
    pairs = re.findall(r"^([0-9a-f]{64})  (\S+)$", text, flags=re.M)
    if not pairs:
        raise RuntimeError("PREREG lists no frozen inputs")
    for sha, rel in pairs:
        if hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != sha:
            raise RuntimeError(f"{rel} differs from its frozen sha256")
    return len(pairs)


def main(get=http, now_ms=None):
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12], "; inputs", verify_inputs())
    now_ms = now_ms or int(time.time() * 1000)
    series = tbill_series(now_ms, get)
    tb = rule.tbill_asof(series, now_ms)
    for s in settle_due(now_ms, series, get):
        log(f"settled {s['book']} {s['contract']}: diff {s['diff_bp']:.2f} bp")
    if tb is None:
        log("no T-bill value known: no offers, no locks")
        status()
        return 0
    offs = []
    for coin in COINS:
        try:
            offs += offers(coin, now_ms, tb, get)
        except (OSError, KeyError, StopIteration, ValueError) as e:
            log(f"{coin} failed: {e}")
    append(J / "offers.csv", OFFER_COLS, offs)
    for lk in open_locks(now_ms, offs, tb):
        log(f"paper lock {lk['book']} {lk['contract']}: {lk['locked_yield'] * 100:.2f}%/yr, "
            f"T-bill {tb * 100:.2f}%")
    s = status()
    log(f"{len(offs)} offers; {s['locks']} locks, {s['settled']} settled")
    return 0


if __name__ == "__main__":
    sys.exit(main())
