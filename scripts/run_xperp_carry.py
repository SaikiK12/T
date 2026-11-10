"""xperp_carry_v1 (R441, M490): OKX Europe alt X-Perp carry book, short the X-Perp and long OKX EEA spot, picked each
day by trailing realized funding. Rule, costs, windows and decision are in experiments/xperp_carry_v1/PREREG.md.

Reads the layout written by scripts/record_okx_xperp.py (a checkout of the data branch claude/okx-xperp-data, or any
folder with the same layout). Paper only: it reads files and writes results; it places no order.

usage: python scripts/run_xperp_carry.py --data DIR --window gate0|forward [--until YYYY-MM-DD] [--out DIR]
       python scripts/run_xperp_carry.py --data DIR --window forward --status      (no decision: a progress read)
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab.stats import newey_west_t  # noqa: E402

LANE = ROOT / "experiments" / "xperp_carry_v1"
DAY = 86_400_000
# ---- the frozen rule (PREREG "Rule"); tests/test_run_xperp_carry.py checks these values against the PREREG text
LOOKBACK_D = 7
ENTER_ANN = 0.10            # enter when trailing realized funding, annualized, is at least 10%/yr
EXIT_ANN = 0.05             # exit when it falls below 5%/yr
SLOTS = 10
MIN_VOL_USD = 100_000       # the X-Perp's previous UTC day traded at least $100k (entries only)
LEVER = 2.0                 # X-Perp margin N / L; spot fully paid: capital = N (1 + 1 / L)
FEE_BP = {"xperp": 5.0, "spot": 10.0}     # OKX EEA regular taker fees, per side (M484 note)
DEFAULT_IMPACT_BP = 5.0     # per leg and side when no book snapshot of the last 24 h is held
HURDLE_ANN = 0.04
NW_LAG = 10
WINDOWS = {"gate0": ("2026-08-20", "2026-11-10"), "forward": ("2026-11-11", None)}
LOOKS = {90: "2027-02-08", 180: "2027-05-09"}       # the 90th and 180th scored forward days


def ms(s):
    return int(pd.Timestamp(s, tz="UTC").value // 10**6)


def day_label(t):
    return str(pd.Timestamp(t, unit="ms", tz="UTC").date())


# ---------------------------------------------------------------- data

def read_dir(folder):
    files = sorted(Path(folder).glob("*.csv"))
    if not files:
        return pd.DataFrame()
    return pd.concat([pd.read_csv(f, dtype={"instId": str}) for f in files], ignore_index=True)


def load(data):
    data = Path(data)
    f = read_dir(data / "funding")
    rate = pd.to_numeric(f.realizedRate, errors="coerce")
    f = pd.DataFrame({"instId": f.instId, "t": f.fundingTime.astype(np.int64),
                      "rate": rate.fillna(pd.to_numeric(f.fundingRate, errors="coerce"))})
    candles = {}
    for k in ("mark_1d", "trade_1d", "spot_1d"):
        c = read_dir(data / k)
        candles[k] = c.assign(ts=c.ts.astype(np.int64)) if len(c) else c
    books = read_dir(data / "books")
    listings = {}
    for p in sorted((data / "instruments").glob("*.json")):
        ins = json.loads(p.read_text())["instruments"]
        listings[p.stem] = {i["instId"]: i["ctValCcy"] for i in ins if str(i.get("instCategory")) == "1"}
    return f.drop_duplicates(["instId", "t"]), candles, books, listings


def closes(c, col="c"):
    """{(instId, close day ms): value}: the 1Dutc candle opened at ts closes at ts + 1 day."""
    if not len(c):
        return {}
    return dict(zip(zip(c.instId, c.ts + DAY), c[col].astype(float)))


def spot_of(base, spot_ids):
    for q in ("USDC", "EUR"):
        if f"{base}-{q}" in spot_ids:
            return f"{base}-{q}"
    return None


def impact(books, inst, kind, side, t):
    """Measured $1k market-order cost in bp from mid, from the latest snapshot in the 24 h before t, else None."""
    if not len(books):
        return None
    b = books[(books.instId == inst) & (books.kind == kind)]
    b = b[(b.ts.astype(np.int64) <= t) & (b.ts.astype(np.int64) > t - DAY)]
    if not len(b):
        return None
    v = b.sort_values("ts").iloc[-1][f"{side}_1k_bp"]
    return None if pd.isna(v) else float(v)


# ---------------------------------------------------------------- the book

def run(data, start, end, books_ok=True):
    f, cd, books, listings = load(data)
    mark, spot = closes(cd["mark_1d"]), closes(cd["spot_1d"])
    vol = closes(cd["trade_1d"], "vol_quote") if len(cd["trade_1d"]) else {}
    spot_ids = set(cd["spot_1d"].instId) if len(cd["spot_1d"]) else set()
    by_inst = {k: g.sort_values("t") for k, g in f.groupby("instId")}
    first_listing = listings[min(listings)] if listings else {}
    if not books_ok:
        books = pd.DataFrame()

    def listed(d):
        lab = day_label(d)
        keys = [k for k in listings if k <= lab]
        return listings[max(keys)] if keys else first_listing

    def trailing(inst, d):
        g = by_inst.get(inst)
        if g is None or g.t.min() > d - LOOKBACK_D * DAY:          # needs a full lookback of prints
            return None
        w = g[(g.t > d - LOOKBACK_D * DAY) & (g.t <= d)]
        return float(w.rate.sum()) * 365 / LOOKBACK_D if len(w) else None

    def funding(inst, a, b):
        g = by_inst.get(inst)
        return 0.0 if g is None else float(g[(g.t > a) & (g.t <= b)].rate.sum())

    def cost_bp(inst, sp, action, d, m):
        xs, ss = ("sell", "buy") if action == "enter" else ("buy", "sell")
        tot = 0.0
        for kind, iid, side in (("xperp", inst, xs), ("spot", sp, ss)):
            imp = impact(books, iid, kind, side, d)
            tot += FEE_BP[kind] + (DEFAULT_IMPACT_BP if imp is None else max(imp, 0.0))
        return tot * m

    w = 1.0 / (SLOTS * (1 + 1 / LEVER))          # one slot's notional over book capital
    held, rows, trades = {}, [], []
    t0, t1 = ms(start), ms(end)
    for d in range(t0, t1 + DAY, DAY):
        lst = listed(d)
        # 1. book the interval d - 1 day -> d for the names decided at d - 1 day
        fund = price = 0.0
        forced = []
        for inst, (sp, _) in list(held.items()):
            a, b = d - DAY, d
            fund += w * funding(inst, a, b)
            m0, m1, s0, s1 = mark.get((inst, a)), mark.get((inst, b)), spot.get((sp, a)), spot.get((sp, b))
            if None in (m0, m1, s0, s1):
                forced.append(inst)                  # a missing close: the interval books funding only, then out
            else:
                price += w * (-(m1 / m0 - 1) + (s1 / s0 - 1))
        # 2. decide at d: exits, then entries
        sig = {i: trailing(i, d) for i in lst}
        exits = [i for i in held if i in forced or i not in lst or sig.get(i) is None or sig[i] < EXIT_ANN]
        cost = {m: 0.0 for m in (1, 2, 3)}
        for i in exits:
            for m in cost:
                cost[m] += w * cost_bp(i, held[i][0], "exit", d, m) / 1e4
            trades.append({"day": day_label(d), "instId": i, "spot": held[i][0], "action": "exit",
                           "forced": i in forced, "signal_ann": sig.get(i), "entered": held[i][1]})
            del held[i]
        cands = []
        for i, s in sig.items():
            if i in held or s is None or s < ENTER_ANN:
                continue
            sp = spot_of(lst[i], spot_ids)
            if sp is None or (i, d) not in mark or (sp, d) not in spot or vol.get((i, d), 0.0) < MIN_VOL_USD:
                continue
            cands.append((-s, i, sp))
        entries = []
        for _, i, sp in sorted(cands)[: max(0, SLOTS - len(held))]:
            held[i] = (sp, day_label(d))
            entries.append(i)
            for m in cost:
                cost[m] += w * cost_bp(i, sp, "enter", d, m) / 1e4
            trades.append({"day": day_label(d), "instId": i, "spot": sp, "action": "enter", "forced": False,
                           "signal_ann": sig[i], "entered": day_label(d)})
        gross = fund + price
        rows.append({"day": day_label(d), "held": len(held), "entries": len(entries), "exits": len(exits),
                     "forced": len(forced), "funding": fund, "price": price, "gross": gross,
                     "net_1x": gross - cost[1], "net_2x": gross - cost[2], "net_3x": gross - cost[3]})
    return pd.DataFrame(rows), pd.DataFrame(trades)


# ---------------------------------------------------------------- report

def summary(daily):
    h = HURDLE_ANN / 365
    out = {"days": int(len(daily)), "first": daily.day.iloc[0] if len(daily) else None,
           "last": daily.day.iloc[-1] if len(daily) else None}
    for m in ("1x", "2x", "3x"):
        x = daily[f"net_{m}"].to_numpy(float)
        n, mu, t = newey_west_t(x - h, NW_LAG)
        out[m] = {"net_ann": float(np.mean(x) * 365) if len(x) else None,
                  "excess_ann": float(mu * 365) if n else None, "nw_t_excess": t}
    x = daily.net_1x.to_numpy(float)
    cum = np.cumsum(x)
    out["max_dd"] = float((cum - np.maximum.accumulate(np.maximum(cum, 0))).min()) if len(x) else None
    tot = x.sum()
    out["top10_day_share"] = float(np.sort(x)[::-1][:10].sum() / tot) if tot > 0 else None
    out["funding_ann"] = float(daily.funding.mean() * 365) if len(x) else None
    out["price_ann"] = float(daily.price.mean() * 365) if len(x) else None
    out["avg_held"] = float(daily.held.mean()) if len(x) else None
    out["forced_exits"] = int(daily.forced.sum()) if len(x) else 0
    sd = float(np.std(x - HURDLE_ANN / 365, ddof=1)) if len(x) > 1 else float("nan")
    out["sd_daily"] = sd
    # detectable annual excess at t 2.5 with 80% power: (2.5 + 0.84) sd / sqrt(n) a day
    out["detectable_ann"] = {str(k): float((2.5 + 0.84) * sd / np.sqrt(k) * 365) for k in (90, 180)}
    return out


def decide(s, look):
    """The PREREG's decision at a look (90 or 180 scored forward days)."""
    e1, t1, e2 = s["1x"]["excess_ann"], s["1x"]["nw_t_excess"], s["2x"]["excess_ann"]
    ok_dd = s["max_dd"] is not None and s["max_dd"] > -0.05
    if look == 90:
        if e1 is not None and e1 >= 0.03 and t1 >= 2.0 and e2 > 0 and ok_dd:
            return "EARNED (continue to the 180-day look)"
        if e1 is None or e1 < 0:
            return "NULL (stop)"
        return "CONTINUE (no decision at 90 days)"
    if e1 is not None and e1 >= 0.03 and t1 >= 2.5 and e2 > 0 and ok_dd:
        return "CONFIRMED"
    return "NULL"


def write(out, daily, trades, rep):
    out.mkdir(parents=True, exist_ok=True)
    daily.to_csv(out / "daily.csv", index=False, lineterminator="\n")
    trades.to_csv(out / "trades.csv", index=False, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    (out / "report.json").write_text(json.dumps(rep, indent=1, default=float) + "\n")


def check_inputs(prereg_path):
    """Every file in the PREREG's inputs block still hashes to its frozen sha256; returns the gate-0 data commit."""
    import re
    from lab import prereg
    text = Path(prereg_path).read_text()
    block = re.search(r"```inputs\n(.*?)```", text, re.S).group(1)
    for line in block.strip().splitlines():
        want, rel = line.split()
        got = prereg.sha256_file(ROOT / rel)
        if got != want:
            raise prereg.PreregError(f"{rel}: sha256 {got} != frozen {want}")
    return re.search(r"Gate-0 data commit:\*\* `([0-9a-f]{40})`", text).group(1)


def data_head(data):
    import subprocess
    r = subprocess.run(["git", "-C", str(data), "rev-parse", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--window", choices=sorted(WINDOWS), required=True)
    ap.add_argument("--until", help="last day of a forward read (default: the last day the data covers)")
    ap.add_argument("--status", action="store_true", help="forward progress read: no decision")
    ap.add_argument("--out")
    a = ap.parse_args()
    from lab import prereg
    prereg.verify(LANE / "PREREG.md")
    pinned = check_inputs(LANE / "PREREG.md")
    if a.window == "gate0" and data_head(a.data) != pinned:
        raise SystemExit(f"gate 0 reads the data branch at {pinned} only; {a.data} is at {data_head(a.data)}")
    start, end = WINDOWS[a.window]
    if a.window == "forward":
        f, cd, _, _ = load(a.data)
        last = day_label(int(cd["mark_1d"].ts.max()) + DAY) if len(cd["mark_1d"]) else start
        end = a.until or last
    daily, trades = run(a.data, start, end, books_ok=(a.window == "forward"))
    rep = {"window": a.window, "start": start, "end": end, **summary(daily)}
    if a.window == "forward" and not a.status:
        n = rep["days"]
        look = max((k for k in LOOKS if n >= k), default=None)
        rep["decision"] = decide(rep, look) if look else f"no look reached ({n} scored days)"
    out = Path(a.out) if a.out else LANE / "results" / (a.window + ("_status" if a.status else ""))
    write(out, daily, trades, rep)
    print(json.dumps(rep, indent=1, default=float))


if __name__ == "__main__":
    main()
