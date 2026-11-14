"""R449 jlphedge_v1: two perp-DEX liquidity-pool tokens held against perp shorts on Hyperliquid.

Book J holds Jupiter's JLP (Solana) and shorts SOL, ETH and BTC; book G holds GMX v2's ETH-USDC GM token (Arbitrum)
and shorts ETH. Each short's size per unit of pool token is an ex-ante rolling regression slope, so what is left is
the pool's fee income minus what it pays winning traders, plus the shorts' funding, minus costs.

  --window fetch          gate-0 data into experiments/jlphedge_v1/data/ (before the freeze; computes nothing)
  --window gate0          the frozen gate-0 read (2024-02-01..2026-11-10)
  --window forward        append tomorrow's hedge tickets (each ticket is written before its day starts)
  --window forward --status   score the forward days so far and apply the gate-1 rule at its look dates

Spec: experiments/jlphedge_v1/PREREG.md. Paper only: nothing here deposits, orders or moves money.
"""
import argparse
import csv
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg, stats  # noqa: E402

LANE = ROOT / "experiments" / "jlphedge_v1"
DATA = LANE / "data"
J = LANE / "journal"
PREREG = LANE / "PREREG.md"
HL_API = "https://api.hyperliquid.xyz/info"
LLAMA = "https://coins.llama.fi/chart/{key}?start={start}&span={span}&period=1d"
H = 3_600_000
DAY = 24 * H

BOOKS = {
    "J": {"name": "JLP", "llama": "solana:27G8MtK7VtTcCHkpASjSDdkWWYfoqT6ggEuKidVJidD4",
          "hedge": ("SOL", "ETH", "BTC")},
    "G": {"name": "GM ETH-USDC", "llama": "arbitrum:0x70d95587d40A2caf56bd97485aB3Eec10Bee6336",
          "hedge": ("ETH",)},
}
COINS = ("SOL", "ETH", "BTC")
FETCH_START = "2023-09-01"
G0 = ("2024-02-01", "2026-11-10")          # booked days of gate 0, inclusive
G0_END_STAMP = "2026-11-11"                # the last midnight gate 0 reads
FWD_START = "2026-11-12"
STAMP_TOL = 60 * 60_000                    # a pool price counts as a midnight's stamp within 60 minutes of it
WINDOW = 60                                # spans in the hedge regression
MIN_SPANS = 40
MAX_AGE_DAYS = 120                         # the regression's spans must end within this many days of the span start
HEDGE_COST = 6e-4                          # per unit of short notional traded, one side, 1x (the lab's top tier)
POOL_RT = 30e-4                            # one round trip of the pool token a year, of its value, 1x
HURDLE = 0.04                              # per year, on capital
NW_LAG = 10
LOOKS = (90, 180)


# ---------------------------------------------------------------- time helpers
def day_ms(day):
    return int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def day_index(day):
    return day_ms(day) // DAY


def label(d):
    return datetime.fromtimestamp(int(d) * DAY / 1000, timezone.utc).strftime("%Y-%m-%d")


def now_ms():
    return int(time.time() * 1000)


# ---------------------------------------------------------------- the rule
def stamps(points, d0, d1):
    """{day index d: price} for each midnight in [d0, d1] that has a pool price within STAMP_TOL of it.
    `points` is a list of (ms, price); the closest point wins."""
    out = {}
    pts = sorted(points)
    ts = np.array([p[0] for p in pts], dtype=np.int64)
    for d in range(d0, d1 + 1):
        m = d * DAY
        i = int(np.searchsorted(ts, m))
        best = None
        for j in (i - 1, i):
            if 0 <= j < len(ts) and abs(int(ts[j]) - m) <= STAMP_TOL:
                if best is None or abs(int(ts[j]) - m) < abs(int(ts[best]) - m):
                    best = j
        if best is not None and pts[best][1] > 0:
            out[d] = float(pts[best][1])
    return out


def spans(stamp, closes, coins):
    """Consecutive usable midnights a < b: the pool's stamp and every hedge coin's close exist at both.
    Returns a list of dicts with a, b, the pool return and each coin's return over (a, b]."""
    days = sorted(d for d in stamp if all(d in closes[c] for c in coins))
    out = []
    for a, b in zip(days[:-1], days[1:]):
        out.append({"a": a, "b": b, "rp": stamp[b] / stamp[a] - 1.0,
                    "rc": np.array([closes[c][b] / closes[c][a] - 1.0 for c in coins])})
    return out


def hedge_ratios(sp, a, window=WINDOW):
    """Short notional per unit of pool value for a position opened at midnight a: OLS slopes (with an intercept) of
    the pool's span returns on the hedge coins' over the last `window` spans that ended by midnight a - 1 day and
    within 2 x `window` days of a; each slope clipped to [0, 1]. None when fewer than 2/3 of `window` qualify.
    The rule's window is 60 (MAX_AGE_DAYS 120, MIN_SPANS 40); 30 and 120 are reported diagnostics only."""
    max_age, min_spans = (MAX_AGE_DAYS, MIN_SPANS) if window == WINDOW else (2 * window, (2 * window) // 3)
    use = [s for s in sp if s["b"] <= a - 1 and s["b"] >= a - max_age][-window:]
    if len(use) < min_spans:
        return None
    y = np.array([s["rp"] for s in use])
    X = np.column_stack([np.ones(len(use)), np.array([s["rc"] for s in use])])
    beta = np.linalg.lstsq(X, y, rcond=None)[0][1:]
    return np.clip(beta, 0.0, 1.0)


def span_funding(fday, coins, a, b):
    """Each coin's summed hourly funding rate over the hours of days a..b-1 (positive: longs pay the shorts)."""
    return np.array([sum(fday[c].get(d, (0.0, 0))[0] for d in range(a, b)) for c in coins])


def book(sp, fday, coins, d0, d1, cmult, ratios=None, window=WINDOW):
    """Per-span results for spans that start on or after midnight d0 and end by d1 + 1 (booked on day b - 1).

    `ratios` maps a start day to forced hedge ratios (forward tickets); otherwise the rule computes them.
    A span with no ratios is booked idle: zero return, the hurdle still charged. A span that does not start where the
    previous booked one ended (a forward day left unscored) enters its hedge afresh."""
    rows, prev, last_b = [], None, None
    for s in sp:
        if s["a"] < d0 or s["b"] - 1 > d1:
            continue
        a, b = s["a"], s["b"]
        h = ratios.get(a) if ratios is not None else hedge_ratios(sp, a, window)
        if last_b != a:
            prev = None
        last_b = b
        n_days = b - a
        row = {"day": b - 1, "a": a, "b": b, "days": n_days, "hurdle": HURDLE * n_days / 365.0}
        if h is None:
            row.update(idle=1, net=0.0, pool=0.0, hedge=0.0, funding=0.0, cost=0.0, capital=1.0,
                       h=np.full(len(coins), np.nan))
            prev = None
        else:
            h = np.asarray(h, float)
            target_prev = np.zeros(len(coins)) if prev is None else prev
            turnover = float(np.abs(h - target_prev).sum())
            f = span_funding(fday, coins, a, b)
            pool, hedge, funding = s["rp"], -float(h @ s["rc"]), float(h @ f)
            cost = cmult * (HEDGE_COST * turnover + POOL_RT * n_days / 365.0)
            capital = 1.0 + float(h.sum())
            row.update(idle=0, pool=pool / capital, hedge=hedge / capital, funding=funding / capital,
                       cost=cost / capital, capital=capital, h=h, net=(pool + hedge + funding - cost) / capital)
            prev = h * (1.0 + s["rc"]) / (1.0 + s["rp"])     # the shorts' notional per unit of pool value at b
        row["excess"] = row["net"] - row["hurdle"]
        rows.append(row)
    return rows


def summary(rows, d0, d1):
    """Annualized net and excess over the days the rows cover (idle spans included, unscored days not), and the NW t
    of the excess on the calendar-day series of [d0, d1], each span's value on its booked day."""
    n_cal = d1 - d0 + 1
    n_days = max(1, sum(r["days"] for r in rows))
    x = np.full(n_cal, np.nan)
    for r in rows:
        x[r["day"] - d0] = r["excess"]
    n, _, t = stats.newey_west_t(x, NW_LAG)
    net = np.array([r["net"] for r in rows])
    eq = np.cumprod(1.0 + net) if len(net) else np.array([1.0])
    dd = float((eq / np.maximum.accumulate(eq) - 1.0).min())
    scored = int(sum(r["days"] for r in rows if not r["idle"]))
    return {"calendar_days": n_cal, "covered_days": n_days if rows else 0, "spans": len(rows), "scored_days": scored,
            "idle_spans": int(sum(r["idle"] for r in rows)),
            "net_pct_yr": float(net.sum() * 365.0 / n_days * 100) if len(net) else float("nan"),
            "excess_pts_yr": float(sum(r["excess"] for r in rows) * 365.0 / n_days * 100) if rows else float("nan"),
            "nw_t": float(t), "nw_n": int(n), "max_dd_pct": dd * 100,
            "worst_span_pct": float(net.min() * 100) if len(net) else float("nan"),
            "worst_day": label(rows[int(net.argmin())]["day"]) if len(net) else ""}


def gate1(s1, s2, s3, look):
    """R446's rule. s1/s2/s3 are summaries at 1x/2x/3x costs over the scored forward days."""
    need_t = 2.0 if look == LOOKS[0] else 2.5
    ok = (s1["excess_pts_yr"] >= 3.0 and s1["nw_t"] >= need_t and s2["excess_pts_yr"] > 0
          and s1["max_dd_pct"] > -5.0)
    if look == LOOKS[0]:
        if ok:
            return "EARNED"
        return "NULL" if s1["excess_pts_yr"] < 0 else "CONTINUE"
    return "CONFIRMED" if ok else "NULL"


# ---------------------------------------------------------------- data
def get_json(url=None, body=None, tries=5):
    delay, err = 2.0, None
    for _ in range(tries):
        try:
            if body is None:
                req = urllib.request.Request(url, headers={"User-Agent": "lab-research/1.0"})
            else:
                req = urllib.request.Request(HL_API, json.dumps(body).encode(),
                                             {"Content-Type": "application/json", "User-Agent": "lab-research/1.0"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read())
        except Exception as e:      # noqa: BLE001 - retried, then raised
            err = e
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"fetch {url or body.get('type')}: {err}")


def fetch_llama(key, start_ms, end_ms):
    """Every DefiLlama daily point of `key` in [start_ms, end_ms), stitched from 365-point windows."""
    pts, s = {}, start_ms // 1000
    while s * 1000 < end_ms:
        j = get_json(LLAMA.format(key=key, start=s, span=365))
        p = j.get("coins", {}).get(key, {}).get("prices", [])
        for x in p:
            pts[int(x["timestamp"]) * 1000] = float(x["price"])
        s += 365 * 86400
        time.sleep(0.5)
    return sorted((t, v) for t, v in pts.items() if start_ms <= t < end_ms)


def fetch_closes(coin, start_ms, end_ms):
    """{day index d: close at midnight d} from Hyperliquid's daily candles that closed by end_ms."""
    c = get_json(body={"type": "candleSnapshot", "req": {"coin": coin, "interval": "1d", "startTime": int(start_ms),
                                                          "endTime": int(end_ms)}})
    return {int(k["t"]) // DAY + 1: float(k["c"]) for k in c if int(k["t"]) + DAY <= end_ms}


def fetch_fday(coin, start_ms, end_ms):
    """{day index d: (summed rate, hours)} of Hyperliquid funding settlements over [start_ms, end_ms)."""
    f, s = {}, int(start_ms)
    while s < end_ms:
        page = get_json(body={"type": "fundingHistory", "coin": coin, "startTime": s, "endTime": int(end_ms)})
        if not page:
            break
        for x in page:
            f[int(x["time"]) // H * H] = float(x["fundingRate"])
        s = int(page[-1]["time"]) + 1
        if len(page) < 500:
            break
        time.sleep(0.3)
    return fday_from(f)


def fday_from(settlements):
    """{hour ms of a settlement: rate} -> {day index: (summed rate, hours)}; a settlement at T pays for the hour before
    it, so it belongs to the UTC day of T - 1 h."""
    out = {}
    for t, r in settlements.items():
        d = (t - H) // DAY
        tot, n = out.get(d, (0.0, 0))
        out[d] = (tot + r, n + 1)
    return out


def write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def fetch_gate0():
    """Gate-0 inputs, fetched once before the freeze. Writes files only; computes no return."""
    s, e = day_ms(FETCH_START), day_ms(G0_END_STAMP)
    for b, spec in BOOKS.items():
        pts = fetch_llama(spec["llama"], s, e + STAMP_TOL + 1)
        write_csv(DATA / f"pool_{b}.csv", ["ms", "price"], pts)
        print(f"pool {b}: {len(pts)} points")
    for c in COINS:
        cl = fetch_closes(c, s - DAY, e)
        write_csv(DATA / f"close_{c}.csv", ["day", "close"], [(label(d), v) for d, v in sorted(cl.items())])
        fd = fetch_fday(c, s, e + H)
        write_csv(DATA / f"funding_{c}.csv", ["day", "rate_sum", "hours"],
                  [(label(d), repr(v[0]), v[1]) for d, v in sorted(fd.items()) if d < day_index(G0_END_STAMP)])
        print(f"{c}: {len(cl)} closes, {len(fd)} funding days")


def read_points(path):
    with open(path) as fh:
        return [(int(r["ms"]), float(r["price"])) for r in csv.DictReader(fh)]


def read_closes(path):
    with open(path) as fh:
        return {day_index(r["day"]): float(r["close"]) for r in csv.DictReader(fh)}


def read_fday(path):
    with open(path) as fh:
        return {day_index(r["day"]): (float(r["rate_sum"]), int(r["hours"])) for r in csv.DictReader(fh)}


def check_inputs(block_name):
    text = PREREG.read_text()
    block = re.search(r"```" + re.escape(block_name) + r"\n(.*?)```", text, re.S).group(1)
    for line in block.strip().splitlines():
        want, rel = line.split()
        got = prereg.sha256_file(ROOT / rel)
        if got != want:
            raise prereg.PreregError(f"{rel}: sha256 {got} != frozen {want}")


# ---------------------------------------------------------------- gate 0
def gate0():
    prereg.verify(PREREG)
    check_inputs("inputs")
    check_inputs("inputs-gate0")
    closes = {c: read_closes(DATA / f"close_{c}.csv") for c in COINS}
    fday = {c: read_fday(DATA / f"funding_{c}.csv") for c in COINS}
    points = {b: read_points(DATA / f"pool_{b}.csv") for b in BOOKS}
    report, daily = gate0_report(points, closes, fday, day_index(FETCH_START), day_index(G0[0]), day_index(G0[1]),
                                 day_index(G0_END_STAMP))
    out_dir = LANE / "results" / "gate0"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "daily.csv", ["book", "day", "days", "idle", "net", "excess", "pool", "hedge", "funding",
                                      "cost", "capital", "h1", "h2", "h3"], daily)
    report["daily_sha256"] = prereg.sha256_file(out_dir / "daily.csv")
    (out_dir / "report.json").write_text(json.dumps(report, indent=1, default=float) + "\n")
    return report


def gate0_report(points, closes, fday, first, d0, d1, last_stamp):
    """The gate-0 read from loaded inputs: report dict and daily rows. Stamps from `first` to `last_stamp`; spans
    booked on d0..d1."""
    report, daily = {"window": [label(d0), label(d1)], "books": {}}, []
    for b, spec in BOOKS.items():
        coins = spec["hedge"]
        st = stamps(points[b], first, last_stamp)
        sp = spans(st, closes, coins)
        res = {}
        for k in (1, 2, 3):
            rows = book(sp, fday, coins, d0, d1, float(k))
            res[f"{k}x"] = summary(rows, d0, d1)
            if k == 1:
                r1 = rows
        verdict = "NULL" if res["1x"]["excess_pts_yr"] < 0 else "CONTINUE"
        live = [r for r in r1 if not r["idle"]]
        n_days = sum(r["days"] for r in r1)
        parts = {p: float(sum(r[p] for r in live) * 365.0 / n_days * 100) for p in ("pool", "hedge", "funding", "cost")}
        H_ = np.array([r["h"] for r in live])
        by_year = {}
        for r in r1:
            y = label(r["day"])[:4]
            by_year.setdefault(y, []).append(r)
        years = {}
        for y, rr in by_year.items():
            ya, yb = max(d0, day_index(f"{y}-01-01")), min(d1, day_index(f"{y}-12-31"))
            years[y] = summary(rr, ya, yb)
        report["books"][b] = {
            "name": spec["name"], "hedge": coins, "verdict_gate0": verdict, "summary": res,
            "parts_pct_yr_1x": parts, "by_year_1x": years,
            "stamps": len(st), "spans": len(sp),
            "hedge_ratio_mean": dict(zip(coins, H_.mean(0).round(4).tolist())) if len(H_) else {},
            "hedge_ratio_min": dict(zip(coins, H_.min(0).round(4).tolist())) if len(H_) else {},
            "hedge_ratio_max": dict(zip(coins, H_.max(0).round(4).tolist())) if len(H_) else {},
            "capital_mean": float(np.mean([r["capital"] for r in live])) if live else float("nan"),
            "unhedged_pool_pct_yr": float(sum(s["rp"] for s in sp if s["a"] >= d0 and s["b"] - 1 <= d1)
                                          * 365.0 / n_days * 100),
            "power": power(r1),
            "diagnostics": diagnostics(sp, fday, coins, d0, d1, live, st),
        }
        for r in r1:
            daily.append([b, label(r["day"]), r["days"], r["idle"], f"{r['net']:.8f}", f"{r['excess']:.8f}",
                          f"{r['pool']:.8f}", f"{r['hedge']:.8f}", f"{r['funding']:.8f}", f"{r['cost']:.8f}",
                          f"{r['capital']:.6f}"] + ([f"{v:.6f}" for v in r["h"]] + ["", "", ""])[:3])
        print(f"{b} ({spec['name']}): gate 0 {verdict}; 1x net {res['1x']['net_pct_yr']:+.2f}%/yr, excess "
              f"{res['1x']['excess_pts_yr']:+.2f} pts, NW t {res['1x']['nw_t']:.2f}, DD {res['1x']['max_dd_pct']:.2f}%")
    return report, daily


def power(rows):
    """The span sd of the 1x excess and the annual excess detectable at t 2.5 with 80% power at 90 and 180 days."""
    x = np.array([r["excess"] for r in rows if r["days"] == 1])
    sd = float(x.std(ddof=1)) if len(x) > 1 else float("nan")
    return {"daily_sd_pct": sd * 100,
            **{f"detectable_pts_yr_{n}d": (2.5 + 0.84) * sd / np.sqrt(n) * 365 * 100 for n in LOOKS}}


def diagnostics(sp, fday, coins, d0, d1, live, st):
    """Reported after the frozen read; they decide nothing."""
    out = {}
    for w in (30, 120):
        out[f"window_{w}_1x"] = summary(book(sp, fday, coins, d0, d1, 1.0, window=w), d0, d1)
    by_a = {s["a"]: s for s in sp}
    net = np.array([r["net"] for r in live])
    rc = np.array([by_a[r["a"]]["rc"] for r in live])
    out["corr_net_with_coin"] = {c: float(np.corrcoef(net, rc[:, i])[0, 1]) for i, c in enumerate(coins)}
    win = [s for s in sp if s["a"] >= d0 and s["b"] - 1 <= d1]
    out["spans_with_unchanged_pool_price"] = int(sum(s["rp"] == 0.0 for s in win))
    out["spans_longer_than_one_day"] = int(sum(s["b"] - s["a"] > 1 for s in win))
    return out


# ---------------------------------------------------------------- forward
TICKET_COLS = ["book", "day", "run_at", "h1", "h2", "h3", "spans_used", "last_end"]


def read_tickets():
    p = J / "tickets.csv"
    if not p.exists():
        return []
    with open(p) as fh:
        return list(csv.DictReader(fh))


def append_tickets(rows):
    p = J / "tickets.csv"
    J.mkdir(parents=True, exist_ok=True)
    new = not p.exists()
    with open(p, "a", newline="") as fh:
        w = csv.DictWriter(fh, TICKET_COLS, lineterminator="\n")
        if new:
            w.writeheader()
        w.writerows(rows)


def stamp_decided(points, d, now):
    """Whether midnight d's stamp is settled: a point within STAMP_TOL exists, or a later point beyond it does,
    or the tolerance has passed by an hour."""
    m = d * DAY
    return any(abs(t - m) <= STAMP_TOL or t > m + STAMP_TOL for t, _ in points) or now > m + STAMP_TOL + H


def forward():
    """Write, for each book, the ticket of day D = today + 1 (the hedge opened at midnight D), from spans that
    ended by today's midnight. A ticket is written once, during day D - 1, and never changed."""
    prereg.verify(PREREG)
    check_inputs("inputs")
    now = now_ms()
    today = now // DAY
    D = today + 1
    if D < day_index(FWD_START):
        print(f"forward starts {FWD_START}: first ticket is written during {label(day_index(FWD_START) - 1)}")
        return
    have = {(t["book"], t["day"]) for t in read_tickets()}
    start = (today - 200) * DAY
    closes = {c: fetch_closes(c, start - DAY, now) for c in COINS}
    rows = []
    for b, spec in BOOKS.items():
        if (b, label(D)) in have:
            continue
        pts = fetch_llama(spec["llama"], start, now)
        if not stamp_decided(pts, today, now) or any(today not in closes[c] for c in spec["hedge"]):
            print(f"{b}: today's stamp or close not settled yet; no ticket this run")
            continue
        sp = spans(stamps(pts, start // DAY, today), closes, spec["hedge"])
        h = hedge_ratios(sp, D)
        hv = [""] * 3 if h is None else [f"{v:.6f}" for v in h] + [""] * (3 - len(h))
        used = [s for s in sp if D - MAX_AGE_DAYS <= s["b"] <= D - 1][-WINDOW:]
        rows.append({"book": b, "day": label(D), "run_at": datetime.fromtimestamp(now / 1000, timezone.utc)
                     .strftime("%Y-%m-%dT%H:%M:%SZ"), "h1": hv[0], "h2": hv[1], "h3": hv[2],
                     "spans_used": len(used), "last_end": label(used[-1]["b"]) if used else ""})
    if rows:
        append_tickets(rows)
    print(f"tickets for {label(D)}: {[r['book'] for r in rows] or 'none new'}")


def status():
    """Score forward days: spans that start at an on-time ticket's midnight (written before it) on or after
    FWD_START, realized from fresh pool prices, Hyperliquid closes and funding. Applies gate 1 at its looks."""
    prereg.verify(PREREG)
    check_inputs("inputs")
    now = now_ms()
    f0 = day_index(FWD_START)
    last = now // DAY - 1
    if last < f0:
        print("no forward day has ended yet")
        return
    start = (f0 - 3) * DAY
    closes = {c: fetch_closes(c, start - DAY, now) for c in COINS}
    fday = {c: fetch_fday(c, start, now) for c in COINS}
    tk = read_tickets()
    out = {"as_of": label(last), "books": {}}
    for b, spec in BOOKS.items():
        coins = spec["hedge"]
        ratios = {}
        for t in tk:
            if t["book"] != b or not t["h1"]:
                continue
            d = day_index(t["day"])
            run = int(datetime.strptime(t["run_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                      .timestamp() * 1000)
            if run < d * DAY:                          # on time: written before the hedge opens
                ratios[d] = np.array([float(t[k]) for k in ("h1", "h2", "h3")[:len(coins)]])
        pts = fetch_llama(spec["llama"], start, now)
        sp = [s for s in spans(stamps(pts, f0 - 3, last + 1), closes, coins) if s["a"] in ratios]
        rows = {k: book(sp, fday, coins, f0, last, float(k), ratios) for k in (1, 2, 3)}
        res = {f"{k}x": summary(rows[k], f0, last) for k in (1, 2, 3)}
        n = res["1x"]["scored_days"]
        res["scored_days"] = n
        res["looks"] = looks(rows, f0)
        out["books"][b] = res
        dec = {L: v["decision"] for L, v in res["looks"].items()} or "no look reached"
        print(f"{b}: {n} scored days, 1x net {res['1x']['net_pct_yr']:+.2f}%/yr, excess "
              f"{res['1x']['excess_pts_yr']:+.2f} pts, NW t {res['1x']['nw_t']:.2f}: {dec}")
    d = LANE / "results" / "forward"
    d.mkdir(parents=True, exist_ok=True)
    (d / "status.json").write_text(json.dumps(out, indent=1, default=float) + "\n")


def looks(rows, f0):
    """Gate 1 at each look reached. A look reads the first spans whose scored days reach it, never later ones; a NULL
    at the first look stops the book. `rows` maps the cost multiple (1, 2, 3) to the book's rows."""
    out = {}
    cum = np.cumsum([r["days"] for r in rows[1] if not r["idle"]])
    live = {k: [r for r in rows[k] if not r["idle"]] for k in rows}
    for L in LOOKS:
        if not len(cum) or cum[-1] < L:
            break
        k_end = int(np.searchsorted(cum, L)) + 1
        end = live[1][k_end - 1]["day"]
        sm = {k: summary(live[k][:k_end], f0, end) for k in (1, 2, 3)}
        out[L] = {"through": label(end), "1x": sm[1], "2x": sm[2], "decision": gate1(sm[1], sm[2], sm[3], L)}
        if L == LOOKS[0] and out[L]["decision"] == "NULL":
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", choices=("fetch", "gate0", "forward"), required=True)
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.window == "fetch":
        if (LANE / "PREREG.sha256").exists():
            raise SystemExit("frozen: gate-0 data are fixed")
        fetch_gate0()
    elif a.window == "gate0":
        gate0()
    elif a.status:
        status()
    else:
        forward()


if __name__ == "__main__":
    main()
