"""passive_kraken_fwd (R514): R513's passive-entry measure, forward, on the Kraken legs R509 and R512 actually trade.

Paper only: it reads R509's and R512's journals, Kraken's public book and charts, and writes only
experiments/passive_kraken_fwd/journal/.

Each run, after the carry lanes' tick in claude-carry-paper.yml:
1. **Snapshot.** For every new completed ticket of R509 or R512 with a Kraken leg (enter, inherit or exit; not drop),
   it records Kraken's live book now:
   - the best bid and ask, the mid;
   - the side the Kraken leg trades (buy for a long entry or a short exit; sell otherwise);
   - the $1,000 walk on that side;
   - the snapshot time.
   A snapshot taken more than 30 minutes after the ticket's run is kept but marked `late`.
2. **Evaluate.** For each snapshot at least 6 h old and not yet evaluated, it reads Kraken's 5-minute trade candles
   and 1-minute mark candles after the snapshot, then for H = 1 h and 6 h:
   - **The passive order** rests at the best bid (buy) or best ask (sell) from the snapshot.
   - **Filled** when a 5-minute candle with volume > 0, closing in (t, t + H], trades strictly through it. Cost: the
     signed gap between the limit and the mid, plus the 2 bp maker fee.
   - **Otherwise a taker order at t + H.** Cost: side x (mark_{t+H} / mid_t - 1) + the $1,000 walk + 5 bp.
   - **saving** = (walk + 5 bp) - passive cost, in bp per leg-side.

**The read** (`--read`, decided by the PREREG):
- The series is each snapshot day's mean saving at H = 1 h over on-time snapshots (not `late`).
- PASS at 30 or more days if the mean is above 0 and its Newey-West t (lag 5) is at least 2.0.
- FAIL at 30 days if the mean is at or below 0. Otherwise RUNNING until 60 days, then FAIL.

usage: python scripts/forward_passive_kraken.py [--no-eval] [--read]
"""
import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import kraken  # noqa: E402

LANE = ROOT / "experiments" / "passive_kraken_fwd"
SOURCES = {"R509": (ROOT / "experiments" / "xfund_eea_fwd", ROOT / "experiments" / "xfund_eea_v1" / "symbols.csv"),
           "R512": (ROOT / "experiments" / "xfund_eea3_fwd", ROOT / "experiments" / "xfund_kaster_v1" / "symbols.csv")}
CHARTS = "https://futures.kraken.com/api/charts/v1"
MAKER_BP, TAKER_BP = 2.0, 5.0
HORIZONS_H = (1, 6)
LATE_MIN = 30
H_MS, M5_MS, M1_MS = 3_600_000, 300_000, 60_000
SNAP_COLS = ["lane", "run", "day", "book", "action", "coin", "symbol", "side", "ticket_ms", "snap_ms", "late", "bid",
             "ask", "mid", "walk_1000_bp"]
EVAL_COLS = ["lane", "run", "day", "action", "coin", "symbol", "side", "late", "snap_ms", "h", "filled", "passive_bp",
             "taker_bp", "saving_bp", "eval_utc"]


def _rows(path):
    p = Path(path)
    if not p.exists() or not p.stat().st_size:
        return []
    with p.open(newline="") as f:
        return list(csv.DictReader(f))


def _append(name, cols, recs, lane=LANE):
    if not recs:
        return
    p = Path(lane) / "journal" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    new = not p.exists() or p.stat().st_size == 0
    with p.open("a", newline="") as f:
        w = csv.DictWriter(f, cols, lineterminator="\n")
        if new:
            w.writeheader()
        w.writerows(recs)


def completed_tickets(folder):
    dec = _rows(Path(folder) / "journal" / "decisions.csv")
    ok = {(r["book"], r["day"], r["run"]) for r in dec}
    return [r for r in _rows(Path(folder) / "journal" / "tickets.csv") if (r["book"], r["day"], r["run"]) in ok]


def kraken_side(t):
    """The side the Kraken leg trades, or None if the ticket has no Kraken leg or is a drop."""
    if t["action"] == "drop" or "kraken" not in (t["long"], t["short"]):
        return None
    return kraken.sides(t["action"], t["long"], t["short"])["kraken"]


def iso_ms(s):
    return kraken.iso_ms(s)


def snapshot(sources=SOURCES, books=None, now_ms=None, lane=LANE):
    books = books or kraken.kraken_book
    done = {(r["lane"], r["run"], r["book"], r["action"], r["coin"]) for r in _rows(Path(lane) / "journal" /
                                                                                       "snapshots.csv")}
    out = []
    for name, (folder, symbols) in sources.items():
        table = pd.read_csv(symbols).set_index("key")
        for t in completed_tickets(folder):
            side = kraken_side(t)
            key = (name, t["run"], t["book"], t["action"], t["coin"])
            if side is None or key in done:
                continue
            sym = table.loc[t["coin"], "kraken"]
            try:
                bids, asks = books(sym)
            except Exception as e:             # noqa: BLE001 - a failed book is skipped and retried next run
                print(f"book {sym} failed: {e}")
                continue
            if not bids or not asks:
                continue
            now = now_ms or int(time.time() * 1000)
            mid, _, walk = kraken.side_fill(bids, asks, side, 1000)
            tms = iso_ms(t["run"])
            out.append({"lane": name, "run": t["run"], "day": t["day"], "book": t["book"], "action": t["action"],
                        "coin": t["coin"], "symbol": sym, "side": side, "ticket_ms": tms, "snap_ms": now,
                        "late": str(now - tms > LATE_MIN * 60_000).lower(), "bid": bids[0][0], "ask": asks[0][0],
                        "mid": mid, "walk_1000_bp": "" if walk is None else f"{walk:.4f}"})
            done.add(key)
    _append("snapshots.csv", SNAP_COLS, out, lane)
    return len(out)


def get(url, tries=5):
    delay, err = 1.0, None
    for _ in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "curl/8.5.0"}),
                                        timeout=60) as r:
                return json.loads(r.read())
        except (urllib.error.URLError, OSError, ValueError) as e:
            err = e
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"{url}: {err}")


def charts(tick, sym, res, start, end):
    d = get(f"{CHARTS}/{tick}/{sym}/{res}?from={start // 1000}&to={end // 1000}")
    time.sleep(0.3)
    c = d.get("candles") or []
    return pd.DataFrame({"t": [int(x["time"]) for x in c], "low": [float(x["low"]) for x in c],
                         "high": [float(x["high"]) for x in c], "open": [float(x["open"]) for x in c],
                         "volume": [float(x["volume"]) for x in c]})


def evaluate_one(s, trades, marks, h):
    """One snapshot row and its candles: (filled, passive_bp, taker_bp)."""
    t0, mid = int(s["snap_ms"]), float(s["mid"])
    sgn = 1 if s["side"] == "buy" else -1
    limit = float(s["bid"]) if sgn == 1 else float(s["ask"])
    walk = float(s["walk_1000_bp"]) if s["walk_1000_bp"] not in ("", None) else 21.0 - TAKER_BP
    taker = walk + TAKER_BP
    end = t0 + h * H_MS
    tr = trades[(trades.volume > 0) & (trades.t >= t0) & (trades.t + M5_MS <= end)]
    filled = bool((tr.low < limit).any()) if sgn == 1 else bool((tr.high > limit).any())
    if filled:
        return True, sgn * (limit / mid - 1) * 1e4 + MAKER_BP, taker
    m = marks[marks.t <= end]
    mid_h = float(m.open.iloc[-1]) if len(m) else mid
    return False, sgn * (mid_h / mid - 1) * 1e4 + taker, taker


def evaluate(now_ms=None, lane=LANE, fetch=charts):
    now = now_ms or int(time.time() * 1000)
    done = {(r["lane"], r["run"], r["action"], r["coin"], r["h"]) for r in _rows(Path(lane) / "journal" /
                                                                                  "evaluations.csv")}
    out = []
    for s in _rows(Path(lane) / "journal" / "snapshots.csv"):
        t0 = int(s["snap_ms"])
        if t0 + max(HORIZONS_H) * H_MS + M5_MS > now:
            continue
        todo = [h for h in HORIZONS_H if (s["lane"], s["run"], s["action"], s["coin"], str(h)) not in done]
        if not todo:
            continue
        trades = fetch("trade", s["symbol"], "5m", t0, t0 + max(HORIZONS_H) * H_MS + M5_MS)
        marks = fetch("mark", s["symbol"], "1m", t0, t0 + max(HORIZONS_H) * H_MS + M1_MS)
        for h in todo:
            filled, passive, taker = evaluate_one(s, trades, marks, h)
            out.append({"lane": s["lane"], "run": s["run"], "day": s["day"], "action": s["action"], "coin": s["coin"],
                        "symbol": s["symbol"], "side": s["side"], "late": s["late"], "snap_ms": t0, "h": h,
                        "filled": str(filled).lower(), "passive_bp": f"{passive:.4f}", "taker_bp": f"{taker:.4f}",
                        "saving_bp": f"{taker - passive:.4f}",
                        "eval_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    _append("evaluations.csv", EVAL_COLS, out, lane)
    return len(out)


def read(lane=LANE, h=1):
    from lab.stats import newey_west_t
    ev = pd.DataFrame(_rows(Path(lane) / "journal" / "evaluations.csv"))
    if ev.empty:
        return {"days": 0, "verdict": "RUNNING"}
    ev = ev[(ev.h.astype(int) == h) & (ev.late == "false")]
    ev["d"] = pd.to_datetime(ev.snap_ms.astype("int64"), unit="ms").dt.date
    g = ev.groupby("d").saving_bp.apply(lambda x: x.astype(float).mean())
    rep = {"days": int(len(g)), "leg_sides": int(len(ev)), "fill_rate": float((ev.filled == "true").mean()) if len(ev)
           else None}
    if len(g) >= 3:
        _, mu, t = newey_west_t(g.to_numpy(float), 5)
        rep.update({"mean_saving_bp": float(mu), "nw_t": float(t)})
    if len(g) < 30:
        rep["verdict"] = "RUNNING"
    elif rep["mean_saving_bp"] > 0 and rep["nw_t"] >= 2.0:
        rep["verdict"] = "PASS"
    elif rep["mean_saving_bp"] <= 0 or len(g) >= 60:
        rep["verdict"] = "FAIL"
    else:
        rep["verdict"] = "RUNNING"
    return rep


def main():
    from lab.prereg import verify
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-eval", action="store_true")
    ap.add_argument("--read", action="store_true")
    a = ap.parse_args()
    if a.read:
        print(json.dumps({"H1": read(h=1), "H6 (reported)": read(h=6)}, indent=1))
        return
    verify(LANE / "PREREG.md")
    print("snapshots", snapshot())
    if not a.no_eval:
        print("evaluations", evaluate())


if __name__ == "__main__":
    main()
