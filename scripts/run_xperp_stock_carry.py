"""xperp_stock_v1 (R442, M501): OKX Europe stock X-Perp carry. Short the X-Perp, hold the same US-listed stock at an EU
broker, names picked each day by trailing realized funding. Rule, universe, costs, windows and decision are in
experiments/xperp_stock_v1/PREREG.md.

The book's arithmetic (funding sums, impact lookup, summary, the gate-1 decision) is R441's, imported from the frozen
scripts/run_xperp_carry.py. This file changes three things: the universe (a fixed allowlist of US single stocks), the
hedge price (the X-Perp's own underlying index, `uly`, carried over closed-market days) and the action days (entries and
ordinary exits only at 00:00 UTC Tuesday to Saturday, after a US weekday session).

Reads the layout written by scripts/record_okx_xperp.py. Paper only: it reads files and writes results; no order.

usage: python scripts/run_xperp_stock_carry.py --data DIR --window gate0|forward [--until YYYY-MM-DD] [--out DIR]
       python scripts/run_xperp_stock_carry.py --data DIR --window forward --status      (no decision: a progress read)
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
_spec = importlib.util.spec_from_file_location("run_xperp_carry", ROOT / "scripts" / "run_xperp_carry.py")
rx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rx)

LANE = ROOT / "experiments" / "xperp_stock_v1"
DAY = rx.DAY
# ---- the frozen rule (PREREG "Rule"); tests/test_run_xperp_stock_carry.py checks these against the PREREG text
LOOKBACK_D, ENTER_ANN, EXIT_ANN, SLOTS = rx.LOOKBACK_D, rx.ENTER_ANN, rx.EXIT_ANN, rx.SLOTS     # 7 d, 10%, 5%, 10
MIN_VOL_USD, LEVER, HURDLE_ANN, NW_LAG = rx.MIN_VOL_USD, rx.LEVER, rx.HURDLE_ANN, rx.NW_LAG    # $100k, 2x, 4%, 10
FEE_BP = {"xperp": 5.0, "stock": 10.0}     # OKX EEA taker on the X-Perp; broker commission and FX on the stock
DEFAULT_IMPACT_BP = 5.0                    # per leg and side: the stock leg always, the X-Perp when no snapshot is held
STALE_DAYS = 4                             # mark and hedge: the latest close at or before D, within 4 days
ACTION_WEEKDAYS = (1, 2, 3, 4, 5)          # D falls on Tue..Sat (Mon = 0): D - 1 day was a US weekday
WINDOWS = {"gate0": ("2026-08-20", "2026-11-10"), "forward": ("2026-11-11", None)}
LOOKS = {90: "2027-02-08", 180: "2027-05-09"}
# US exchange-listed common stocks and ADRs among the 92 stock X-Perps listed on 2026-11-10 (PREREG "Universe").
STOCKS = ("AAOI AAPL ADBE ALAB AMAT AMD AMZN APP ARM ASML ASTS AVGO AXTI BE BMNR COHR COIN CRCL CRDO CRWV DDOG DELL "
          "FLNC GEV GLW GOOGL GPRO HOOD IBM INTC IONQ IREN KO LITE LLY LUNR MARA META MRNA MRVL MSFT MSTR MU NBIS "
          "NFLX NOW NVDA OKTA ON ONDS ORCL PANW PENG PLTR QCOM RKLB SMCI SNDK TSLA TSM USAR WDC").split()


def load(data):
    """Funding, candles (mark, trade, index), books, and the stock X-Perp listings by day ({instId: (ticker, uly)})."""
    data = Path(data)
    f, cd, books, _ = rx.load(data)
    c = rx.read_dir(data / "index_1d")
    cd["index_1d"] = c.assign(ts=c.ts.astype("int64")) if len(c) else c
    listings = {}
    for p in sorted((data / "instruments").glob("*.json")):
        ins = json.loads(p.read_text())["instruments"]
        listings[p.stem] = {i["instId"]: (i["ctValCcy"], i["uly"]) for i in ins
                            if str(i.get("instCategory")) == "3" and i.get("ruleType") == "xperp"
                            and i["ctValCcy"] in STOCKS}
    return f, cd, books, listings


def run(data, start, end, books_ok=True):
    f, cd, books, listings = load(data)
    mark, idx = rx.closes(cd["mark_1d"]), rx.closes(cd["index_1d"])
    vol = rx.closes(cd["trade_1d"], "vol_quote") if len(cd["trade_1d"]) else {}
    by_inst = {k: g.sort_values("t") for k, g in f.groupby("instId")}
    first_listing = listings[min(listings)] if listings else {}
    if not books_ok:
        books = pd.DataFrame()

    def listed(d):
        lab = rx.day_label(d)
        keys = [k for k in listings if k <= lab]
        return listings[max(keys)] if keys else first_listing

    def last_close(table, key, d):
        """The latest close at or before d, within STALE_DAYS (a closed market or a paused X-Perp keeps its price)."""
        for k in range(STALE_DAYS + 1):
            v = table.get((key, d - k * DAY))
            if v is not None:
                return v
        return None

    def trailing(inst, d):
        g = by_inst.get(inst)
        if g is None or g.t.min() > d - LOOKBACK_D * DAY:
            return None
        w = g[(g.t > d - LOOKBACK_D * DAY) & (g.t <= d)]
        return float(w.rate.sum()) * 365 / LOOKBACK_D if len(w) else None

    def funding(inst, a, b):
        g = by_inst.get(inst)
        return 0.0 if g is None else float(g[(g.t > a) & (g.t <= b)].rate.sum())

    def cost_bp(inst, action, d, m):
        xs = "sell" if action == "enter" else "buy"
        imp = rx.impact(books, inst, "xperp", xs, d)
        tot = FEE_BP["xperp"] + (DEFAULT_IMPACT_BP if imp is None else max(imp, 0.0))
        tot += FEE_BP["stock"] + DEFAULT_IMPACT_BP
        return tot * m

    w = 1.0 / (SLOTS * (1 + 1 / LEVER))
    held, rows, trades = {}, [], []
    t0, t1 = rx.ms(start), rx.ms(end)
    for d in range(t0, t1 + DAY, DAY):
        lst = listed(d)
        act = pd.Timestamp(d, unit="ms", tz="UTC").weekday() in ACTION_WEEKDAYS
        # 1. book the interval d - 1 day -> d for the names held since d - 1 day
        fund = price = 0.0
        forced = []
        for inst, (uly, _) in list(held.items()):
            a, b = d - DAY, d
            fund += w * funding(inst, a, b)
            m0, m1 = last_close(mark, inst, a), last_close(mark, inst, b)
            h0, h1 = last_close(idx, uly, a), last_close(idx, uly, b)
            if None in (m0, m1, h0, h1):
                forced.append(inst)
            else:
                price += w * (-(m1 / m0 - 1) + (h1 / h0 - 1))
        # 2. decide at d: forced exits any day; ordinary exits and entries on action days only
        sig = {i: trailing(i, d) for i in lst}
        exits = [i for i in held if i in forced or i not in lst
                 or (act and (sig.get(i) is None or sig[i] < EXIT_ANN))]
        cost = {m: 0.0 for m in (1, 2, 3)}
        for i in exits:
            for m in cost:
                cost[m] += w * cost_bp(i, "exit", d, m) / 1e4
            trades.append({"day": rx.day_label(d), "instId": i, "uly": held[i][0], "action": "exit",
                           "forced": i in forced or i not in lst, "signal_ann": sig.get(i), "entered": held[i][1]})
            del held[i]
        entries = []
        if act:
            cands = []
            for i, s in sig.items():
                if i in held or s is None or s < ENTER_ANN:
                    continue
                uly = lst[i][1]
                if (i, d) not in mark or last_close(idx, uly, d) is None or vol.get((i, d), 0.0) < MIN_VOL_USD:
                    continue
                cands.append((-s, i, uly))
            for _, i, uly in sorted(cands)[: max(0, SLOTS - len(held))]:
                held[i] = (uly, rx.day_label(d))
                entries.append(i)
                for m in cost:
                    cost[m] += w * cost_bp(i, "enter", d, m) / 1e4
                trades.append({"day": rx.day_label(d), "instId": i, "uly": uly, "action": "enter", "forced": False,
                               "signal_ann": sig[i], "entered": rx.day_label(d)})
        gross = fund + price
        rows.append({"day": rx.day_label(d), "held": len(held), "entries": len(entries), "exits": len(exits),
                     "forced": len(forced), "funding": fund, "price": price, "gross": gross,
                     "net_1x": gross - cost[1], "net_2x": gross - cost[2], "net_3x": gross - cost[3]})
    return pd.DataFrame(rows), pd.DataFrame(trades)


def decide_gate0(s):
    """Gate 0 decides only a stop."""
    e1 = s["1x"]["excess_ann"]
    return "NULL (stop)" if e1 is None or e1 < 0 else "CONTINUE to gate 1"


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
    pinned = rx.check_inputs(LANE / "PREREG.md")
    if a.window == "gate0" and rx.data_head(a.data) != pinned:
        raise SystemExit(f"gate 0 reads the data branch at {pinned} only; {a.data} is at {rx.data_head(a.data)}")
    start, end = WINDOWS[a.window]
    if a.window == "forward":
        _, cd, _, _ = load(a.data)
        last = rx.day_label(int(cd["mark_1d"].ts.max()) + DAY) if len(cd["mark_1d"]) else start
        end = a.until or last
    daily, trades = run(a.data, start, end, books_ok=(a.window == "forward"))
    rep = {"window": a.window, "start": start, "end": end, **rx.summary(daily)}
    if a.window == "gate0":
        rep["decision"] = decide_gate0(rep)
    elif not a.status:
        n = rep["days"]
        look = max((k for k in LOOKS if n >= k), default=None)
        rep["decision"] = rx.decide(rep, look) if look else f"no look reached ({n} scored days)"
    out = Path(a.out) if a.out else LANE / "results" / (a.window + ("_status" if a.status else ""))
    rx.write(out, daily, trades, rep)
    print(json.dumps(rep, indent=1, default=float))


if __name__ == "__main__":
    main()
