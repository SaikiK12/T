"""R502 cmecarry_v2 (R501's rule; R501 crashed at its first summary before any statistic): CME bitcoin (and ether)
futures against the Binance perp, a funding-versus-basis carry.

The trade: hold one leg on the CME dated future and the opposite leg on the Binance USDT perp, same coin, same dollar
notional. Long the future and short the perp earns the perp's funding and pays the future's basis as it converges; the
reverse earns the basis and pays the funding. Each CME settlement day the signal is

    s = f7 - b    (both in %/yr)
    f7 = the perp's funding over the last 7 days, annualized (sum of rates x 365 / 7)
    b  = (F / P - 1) x 365 / tau, F the held future's settlement, P the perp's price at the same minute, tau the days to
         that future's final settlement

and the position is +1 (long future, short perp) when s >= 10, -1 (short future, long perp) when s <= -10, and is
closed when |s| < 5 (an opposite signal flips it). The held future is the front month while it has at least 14 days to
expiry, else the second month (a held position rolls: two CME sides).

CME specifics carried into the numbers:
- marks are CME daily settlements (statistics stat_type 3) at 15:00 Chicago time, paired with the Binance 1h close
  ending at that minute (20:00 or 21:00 UTC with US daylight time);
- expiry by the contract rule: the last Friday of the contract month (the preceding business day when that Friday is a
  holiday), final settlement at 16:00 London (CME CF reference rate);
- costs per contract, not per dollar: MBT (0.1 BTC) and MET (0.1 ETH) fees per side, so cost in bp falls as price
  rises; plus half the measured top-of-book spread (bbo-1m, the hour before settlement on the second Wednesday of
  each month), or one tick when unmeasured;
- MBT exists from 2021-05-03 and MET from 2021-12-06; before that only the 5 BTC and 50 ETH contracts, reported apart;
- until 2026-05-29 CME crypto closed at weekends: no decision without a settlement, positions are carried through.

Paper research only: nothing here can place an order.

    python scripts/run_cmecarry_v2.py fetch    # reuses R501's pulls (files present are skipped)
    python scripts/run_cmecarry_v2.py run      # PREREG must verify
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
LANE = ROOT / "experiments" / "cmecarry_v2"
DATA = ROOT / "data" / "databento" / "cmecarry"
CHI, LON, UTC = ZoneInfo("America/Chicago"), ZoneInfo("Europe/London"), dt.timezone.utc

ENTER, EXIT = 10.0, 5.0
ROLL_DAYS = 14
FUND_DAYS = 7
BINANCE_BP = 5.5                  # taker 5 bp (base tier) + 0.5 bp of book
HURDLE_PCT = 4.13                 # R275's T-bill hurdle, as the carry lanes use it
NW_LAG = 10
COINS = {
    "BTC": {"micro": "MBT", "micro_units": 0.1, "micro_fee": 2.50, "micro_start": "2021-05-03",
            "big_units": 5.0, "big_fee": 7.00, "tick": 5.0, "stats_start": "2020-01-01"},
    "ETH": {"micro": "MET", "micro_units": 0.1, "micro_fee": 0.60, "micro_start": "2021-12-06",
            "big_units": 50.0, "big_fee": 7.00, "tick": 0.5, "stats_start": "2021-02-01"},
}
PRIMARY = ("BTC", "2021-05-03", "2026-09-30")
EARLY = {"BTC": ("2020-01-08", "2021-04-30"), "ETH": ("2021-02-15", "2021-12-03")}
END = "2026-09-30"
# Fridays in 2020-2026 on which CME or London was closed (a last Friday on these moves expiry to the day before).
HOLIDAY_FRIDAYS = {"2020-04-10", "2020-07-03", "2020-12-25", "2021-04-02", "2021-12-24", "2021-12-31", "2022-04-15",
                   "2023-04-07", "2024-03-29", "2025-04-18", "2026-04-03", "2026-07-03", "2026-12-25"}


# ---------- calendar ----------

def last_friday(year, month):
    d = dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)
    while d.weekday() != 4:
        d -= dt.timedelta(days=1)
    while d.isoformat() in HOLIDAY_FRIDAYS or d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def front_expiries(day):
    """Rule expiries of the front (c.0) and second (c.1) monthly contracts trading on `day`."""
    e0 = last_friday(day.year, day.month)
    if day > e0:
        y, m = (day.year + (day.month == 12), day.month % 12 + 1)
        e0 = last_friday(y, m)
    y, m = (e0.year + (e0.month == 12), e0.month % 12 + 1)
    return e0, last_friday(y, m)


def settle_utc(day):
    return dt.datetime(day.year, day.month, day.day, 15, 0, tzinfo=CHI).astimezone(UTC)


def expiry_utc(day):
    return dt.datetime(day.year, day.month, day.day, 16, 0, tzinfo=LON).astimezone(UTC)


def second_wednesday(year, month):
    d = dt.date(year, month, 1)
    while d.weekday() != 2:
        d += dt.timedelta(days=1)
    return d + dt.timedelta(days=7)


# ---------- data ----------

def _read_zst_csv(path):
    import pyarrow as pa
    import pyarrow.csv as pc
    return pc.read_csv(pa.input_stream(str(path), compression="zstd")).to_pylist()


def settlements(rows):
    """{date: {instrument_id: price}} and {date: (c0_id, c1_id)} from statistics rows (settlement, last publication)."""
    best, labels = {}, defaultdict(Counter)
    for r in rows:
        if int(r["stat_type"]) != 3 or int(r["update_action"]) != 1 or r["ts_ref"] is None:
            continue
        day = r["ts_ref"].date() if hasattr(r["ts_ref"], "date") else dt.date.fromisoformat(str(r["ts_ref"])[:10])
        key = (day, int(r["instrument_id"]))
        if key not in best or r["ts_recv"] > best[key][0]:
            best[key] = (r["ts_recv"], float(r["price"]))
        labels[day][(str(r["symbol"])[-3:], int(r["instrument_id"]))] += 1
    px = defaultdict(dict)
    for (day, iid), (_, p) in best.items():
        px[day][iid] = p
    chain = {}
    for day, c in labels.items():
        c0 = [i for (lab, i), _ in c.most_common() if lab == "c.0"]
        c1 = [i for (lab, i), _ in c.most_common() if lab == "c.1"]
        if c0 and c1 and c0[0] in px[day] and c1[0] in px[day]:
            chain[day] = (c0[0], c1[0])
    return dict(px), chain


def binance(coin):
    import pandas as pd
    k = pd.read_parquet(ROOT / f"data/klines_1h/{coin}USDT.parquet")
    close = dict(zip((k["t"] // 1000).astype(int), k["close"].astype(float)))      # bar open (s) -> close
    f = pd.read_parquet(ROOT / f"data/fundingRate/{coin}USDT.parquet")
    pairs = sorted(zip((f["t"] / 1000.0).tolist(), f["rate"].astype(float).tolist()))
    ts, cum = [t for t, _ in pairs], [0.0]
    for _, r in pairs:
        cum.append(cum[-1] + r)
    return close, (ts, cum)


def spreads(coin):
    """{(YYYY-MM, 'c.0'|'c.1'): median half-spread in bp} from the bbo-1m samples."""
    out = defaultdict(list)
    for path in sorted(DATA.glob(f"*{COINS[coin]['micro']}.c.0*bbo-1m*.csv.zst")):
        for r in _read_zst_csv(path):
            b, a = r.get("bid_px_00"), r.get("ask_px_00")
            if b is None or a is None or not (0 < b < a):
                continue
            mid = (a + b) / 2
            out[(r["ts_recv"].strftime("%Y-%m"), str(r["symbol"])[-3:])].append((a - b) / 2 / mid * 1e4)
    return {k: statistics.median(v) for k, v in out.items() if len(v) >= 30}


# ---------- the rule ----------

def step(w, s, enter=ENTER, exit_=EXIT):
    if s >= enter:
        return 1
    if s <= -enter:
        return -1
    if w == 1 and s < exit_:
        return 0
    if w == -1 and s > -exit_:
        return 0
    return w


def fund_sum(fund, lo, hi):
    """Sum of funding rates with settlement time in (lo, hi]; fund = (sorted times, prefix sums)."""
    from bisect import bisect_right
    ts, cum = fund
    return cum[bisect_right(ts, hi)] - cum[bisect_right(ts, lo)]


def build(coin, px, chain, close, fund, half, start, end, micro=True, k=1.0, enter=ENTER, exit_=EXIT):
    """Daily rows (decision day D -> next settlement day) with signal, position, gross and net returns."""
    spec = COINS[coin]
    units, fee = (spec["micro_units"], spec["micro_fee"]) if micro else (spec["big_units"], spec["big_fee"])
    days = []
    for day in sorted(chain):
        if not (start <= day.isoformat() <= end):
            continue
        t = settle_utc(day)
        p = close.get(int(t.timestamp()) - 3600)
        if p is None:
            continue
        e0, e1 = front_expiries(day)
        c0, c1 = chain[day]
        tau0 = (expiry_utc(e0) - t).total_seconds() / 86400
        if tau0 >= ROLL_DAYS:
            h, tau, lab = c0, tau0, "c.0"
        else:
            h, tau, lab = c1, (expiry_utc(e1) - t).total_seconds() / 86400, "c.1"
        f = px[day][h]
        lo = t.timestamp() - FUND_DAYS * 86400
        f7 = fund_sum(fund, lo, t.timestamp()) * 365 / FUND_DAYS * 100
        b = (f / p - 1) * 365 / tau * 100
        hs = half.get((day.strftime("%Y-%m"), lab))
        half_bp = hs if hs is not None else spec["tick"] / f * 1e4
        cme_bp = fee / (units * f) * 1e4 + half_bp
        days.append({"day": day, "t": t, "p": p, "h": h, "lab": lab, "f": f, "tau": tau, "f7": f7, "b": b,
                     "s": f7 - b, "cme_bp": cme_bp, "half_measured": hs is not None})
    rows, w_prev, h_prev, cme_prev = [], 0, None, None
    for i, d in enumerate(days[:-1]):
        nxt = days[i + 1]
        w = step(w_prev, d["s"], enter, exit_)
        f_next = px[nxt["day"]].get(d["h"])
        if f_next is None:
            raise SystemExit(f"{coin}: held contract {d['h']} has no settlement on {nxt['day']}")
        fr = fund_sum(fund, d["t"].timestamp(), nxt["t"].timestamp())
        gross = w * ((f_next / d["f"] - 1) - (nxt["p"] / d["p"] - 1) + fr)
        if h_prev is None or d["h"] == h_prev:
            cme_sides_cost = abs(w - w_prev) * d["cme_bp"]
            roll = False
        else:
            cme_sides_cost = abs(w_prev) * cme_prev + abs(w) * d["cme_bp"]
            roll = w_prev != 0 and w != 0
        cost = k * (cme_sides_cost + abs(w - w_prev) * BINANCE_BP) / 1e4
        rows.append({"day": d["day"].isoformat(), "next": nxt["day"].isoformat(), "w": w, "lab": d["lab"],
                     "tau": round(d["tau"], 3), "f7": round(d["f7"], 4), "b": round(d["b"], 4),
                     "s": round(d["s"], 4), "cme_bp": round(d["cme_bp"], 4), "half_measured": d["half_measured"],
                     "funding": fr, "gross": gross, "cost": cost, "net": gross - cost, "roll": roll,
                     "trade": w != w_prev})
        w_prev, h_prev, cme_prev = w, d["h"], d["cme_bp"]
    if rows and w_prev != 0:                                   # close at the window's end
        last = days[-1]
        rows[-1]["cost"] += k * (abs(w_prev) * last["cme_bp"] + abs(w_prev) * BINANCE_BP) / 1e4
        rows[-1]["net"] = rows[-1]["gross"] - rows[-1]["cost"]
    return rows


def summarize(rows):
    from lab.stats import newey_west_t
    if not rows:
        return {}
    years = (dt.date.fromisoformat(rows[-1]["next"]) - dt.date.fromisoformat(rows[0]["day"])).days / 365.25
    net = [r["net"] for r in rows]
    gross = [r["gross"] for r in rows]
    t = newey_west_t(net, NW_LAG)[2] if len(net) > NW_LAG + 2 else float("nan")   # (n, mean, t)
    return {"start": rows[0]["day"], "end": rows[-1]["next"], "intervals": len(rows), "years": round(years, 3),
            "ann_net_pct": round(sum(net) / years * 100, 3), "ann_gross_pct": round(sum(gross) / years * 100, 3),
            "nw_t": round(float(t), 3), "share_in_position": round(sum(1 for r in rows if r["w"]) / len(rows), 4),
            "trades": sum(1 for r in rows if r["trade"]), "rolls": sum(1 for r in rows if r["roll"]),
            "long_future_share": round(sum(1 for r in rows if r["w"] == 1) / len(rows), 4),
            "mean_cme_bp": round(statistics.mean(r["cme_bp"] for r in rows), 3),
            "measured_spread_share": round(sum(1 for r in rows if r["half_measured"]) / len(rows), 4)}


def by_year(rows):
    out = defaultdict(list)
    for r in rows:
        out[r["day"][:4]].append(r)
    res = {}
    for y, rs in sorted(out.items()):
        s = summarize(rs)
        s["mean_f7"] = round(statistics.mean(r["f7"] for r in rs), 3)
        s["mean_b"] = round(statistics.mean(r["b"] for r in rs), 3)
        res[y] = s
    return res


def expiry_check(chain):
    """Rule expiry of each front contract against the day the data's front contract changed."""
    days = sorted(chain)
    bad = []
    for d1, d2 in zip(days, days[1:]):
        if chain[d1][0] != chain[d2][0]:
            e0, _ = front_expiries(d1)
            if not (d1 <= e0 < d2):
                bad.append((d1.isoformat(), d2.isoformat(), e0.isoformat()))
    return bad


# ---------- fetch ----------

def _get(p, max_usd):
    from scripts import fetch_databento as fd
    stem = "_".join([p["dataset"], p["symbols"].replace(",", "+"), p["schema"], p["start"], p["end"]]).replace(":", "")
    if (DATA / f"{stem}.csv.zst").exists():
        return 0.0
    _, usd = fd.fetch(p, fd.read_key(), DATA, max_usd)
    return usd


def fetch():
    spent = 0.0
    base = {"dataset": "GLBX.MDP3", "stype_in": "continuous"}
    for coin, spec in COINS.items():
        spent += _get(dict(base, symbols=f"{coin}.c.0,{coin}.c.1", schema="statistics",
                           start=f"{spec['stats_start']}T00:00:00Z", end="2026-10-02T00:00:00Z"), 0.20)
        y, m = int(spec["micro_start"][:4]), int(spec["micro_start"][5:7])
        while (y, m) <= (2026, 9):
            day = second_wednesday(y, m)
            t = settle_utc(day)
            spent += _get(dict(base, symbols=f"{spec['micro']}.c.0,{spec['micro']}.c.1", schema="bbo-1m",
                               start=(t - dt.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                               end=t.strftime("%Y-%m-%dT%H:%M:%SZ")), 0.02)
            y, m = (y + (m == 12), m % 12 + 1)
    print(f"quoted total this call: ${spent:.4f}")


# ---------- run ----------

def check_inputs(prereg=None):
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


def coin_data(coin):
    rows = []
    for path in sorted(DATA.glob(f"*{coin}.c.0+{coin}.c.1_statistics_*.csv.zst")):
        rows += _read_zst_csv(path)
    px, chain = settlements(rows)
    close, fund = binance(coin)
    return px, chain, close, fund, spreads(coin)


def run():
    from lab.prereg import verify
    verify(LANE / "PREREG.md")
    check_inputs()
    report = {"rule": {"enter": ENTER, "exit": EXIT, "roll_days": ROLL_DAYS, "fund_days": FUND_DAYS,
                       "binance_bp": BINANCE_BP, "coins": COINS, "hurdle_pct": HURDLE_PCT}}
    res = LANE / "results"
    res.mkdir(parents=True, exist_ok=True)
    nets = {}
    for coin in COINS:
        px, chain, close, fund, half = coin_data(coin)
        c = report[coin] = {"expiry_rule_mismatches": expiry_check(chain), "spread_months": len(half),
                            "median_half_spread_bp": {lab: round(statistics.median(v for (m, l), v in half.items()
                                                                                   if l == lab), 3)
                                                      for lab in ("c.0", "c.1") if any(l == lab for _, l in half)}}
        start = COINS[coin]["micro_start"]
        for k in (1.0, 2.0, 3.0):
            rows = build(coin, px, chain, close, fund, half, start, END, k=k)
            c[f"micro_{int(k)}x"] = summarize(rows)
            if k == 1.0:
                nets[coin] = rows
                c["by_year_1x"] = by_year(rows)
                c["since_2024_1x"] = summarize([r for r in rows if r["day"] >= "2024-01-01"])
                with (res / f"{coin.lower()}_daily.csv").open("w", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
                    w.writeheader()
                    w.writerows(rows)
        e0, e1 = EARLY[coin]
        c["early_big_contract_1x"] = summarize(build(coin, px, chain, close, fund, half, e0, e1, micro=False))
        c["big_contract_same_window_1x"] = summarize(build(coin, px, chain, close, fund, half, start, END,
                                                           micro=False))
        for en, ex in ((5.0, 2.5), (20.0, 10.0), (0.0, 0.0)):
            c[f"thresholds_{en:g}_{ex:g}_1x"] = summarize(build(coin, px, chain, close, fund, half, start, END,
                                                               enter=en, exit_=ex))
    coin, s0, s1 = PRIMARY
    p = report[coin]["micro_1x"]
    if p["ann_net_pct"] >= HURDLE_PCT and p["nw_t"] >= 2.0:
        verdict = "CARRY_PASS"
    elif p["ann_net_pct"] > 0:
        verdict = "CARRY_WEAK"
    else:
        verdict = "CARRY_NULL"
    report["verdict"] = verdict
    both = defaultdict(list)
    for c_, rows in nets.items():
        for r in rows:
            both[r["day"]].append(r["net"])
    common = sorted(d for d, v in both.items() if len(v) == 2)
    if common:
        yrs = (dt.date.fromisoformat(common[-1]) - dt.date.fromisoformat(common[0])).days / 365.25
        report["btc_eth_half_half_1x_ann_net_pct"] = round(sum(sum(both[d]) / 2 for d in common) / yrs * 100, 3)
    (res / "report.json").write_text(json.dumps(report, indent=1, default=str))
    print(json.dumps({"verdict": verdict, "BTC": report["BTC"]["micro_1x"], "ETH": report["ETH"]["micro_1x"]},
                     default=str))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("fetch", "run"))
    a = ap.parse_args(argv)
    return fetch() if a.cmd == "fetch" else run()


if __name__ == "__main__":
    main()
