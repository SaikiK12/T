"""xbook_fwd (R285): the cross-family forward book (M281), as set out in experiments/xbook_fwd/PREREG.md. Three families
of running paper lanes, each held at the same archive risk: carry (R278 A/B, R279 A/B), flow (R215 A/B, R218 X2) and
events (R266, R268, R270, R272; each scored ticket booked on its exit day at 1/10 of the family). Reads the other
lanes' journals (never writes them). Derived each tick: journal/book_days.csv and journal/status.json. Append-only:
journal/decisions.csv, one row per look reached. Paper only.

usage: python scripts/forward_xbook.py [--today YYYY-MM-DD]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg, stats  # noqa: E402

EXP = ROOT / "experiments"
LANE = EXP / "xbook_fwd"
START = "2026-10-23"
SD = {"carry": 0.0005196660416284657, "flow": 0.024151067161747936, "events": 0.01271633250070641}
SLOTS = 10
FINAL_LAG = 9                                  # days: the longest event hold is 168 h, scored once its bar closes
LOOKS = (180, 365)
BAR, LAG = 2.5, 10
CARRY = {"R278 A": ("xfund_fwd", "days.csv", "A"), "R278 B": ("xfund_fwd", "days.csv", "B"),
         "R279 A": ("xfund_kc_fwd", "days.csv", "A"), "R279 B": ("xfund_kc_fwd", "days.csv", "B")}
FLOW = {"R215 A": ("mexc_fwd", "tickets.csv", "A"), "R215 B": ("mexc_fwd", "tickets.csv", "B"),
        "R218 X2": ("mexc_fwd_sq", "tickets.csv", "X2")}
EVENTS = {"R266": "unlocks_fwd", "R268": "delist_fwd", "R270": "montag_fwd", "R272": "announce_fwd"}
FAMILIES = ("carry", "flow", "events")
DEC_COLS = ["look", "days", "first", "last", "mean", "nw_t", "sum_2x", "families_positive", "verdict", "decided_at"]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def read(p):
    return pd.read_csv(p) if p.exists() and p.stat().st_size else pd.DataFrame()


def daily_family(exp, sleeves, ontime_only=False):
    """Mean over the family's sleeves of each live day's 1x and 2x net (replay rows dropped), and the sleeve count."""
    parts = []
    for name, (lane, file, book) in sleeves.items():
        d = read(exp / lane / "journal" / file)
        if d.empty:
            continue
        d = d[(d.book == book) & (d.kind != "replay")]
        if ontime_only:
            d = d[d.kind == "ontime"]
        d = d.drop_duplicates("day", keep="last")
        parts.append(pd.DataFrame({"sleeve": name, "day": d.day.astype(str), "net": d.net.astype(float),
                                   "net_2x": d.net_2x.astype(float)}))
    if not parts:
        return pd.DataFrame(columns=["net", "net_2x", "n"])
    x = pd.concat(parts)
    return x.groupby("day").agg(net=("net", "mean"), net_2x=("net_2x", "mean"), n=("sleeve", "size"))


def daily_events(exp):
    """Each event lane's tickets by the UTC day of their primary exit: summed scored 1x and 2x net over SLOTS, the
    number of tickets, and how many are not scored yet."""
    parts = []
    for name, lane in EVENTS.items():
        tk = read(exp / lane / "journal" / "tickets.csv")
        if tk.empty:
            continue
        sc = read(exp / lane / "journal" / "scores.csv")
        sc = sc[["ticket", "net", "net_2x"]] if not sc.empty else pd.DataFrame(columns=["ticket", "net", "net_2x"])
        t = tk[["ticket", "exit_ms"]].drop_duplicates("ticket").merge(sc.drop_duplicates("ticket"), on="ticket",
                                                                     how="left")
        t["day"] = pd.to_datetime(t.exit_ms.astype("int64"), unit="ms").dt.strftime("%Y-%m-%d")
        parts.append(t.assign(lane=name))
    if not parts:
        return pd.DataFrame(columns=["net", "net_2x", "tickets", "unscored"])
    t = pd.concat(parts)
    g = t.groupby("day")
    return pd.DataFrame({"net": g.net.sum() / SLOTS, "net_2x": g.net_2x.sum() / SLOTS, "tickets": g.size(),
                         "unscored": g.net.apply(lambda s: int(s.isna().sum()))})


def book_days(exp, today, ontime_only=False):
    c, f, e = daily_family(exp, CARRY, ontime_only), daily_family(exp, FLOW, ontime_only), daily_events(exp)
    last = (pd.Timestamp(today) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    days = pd.date_range(START, last, freq="D").strftime("%Y-%m-%d") if last >= START else pd.Index([])
    b = pd.DataFrame(index=pd.Index(days, name="day"))
    for fam, x in (("carry", c), ("flow", f)):
        b[fam], b[f"{fam}_2x"], b[f"n_{fam}"] = x.net.reindex(days), x.net_2x.reindex(days), x.n.reindex(days)
    b["events"] = e.net.reindex(days).fillna(0.0)
    b["events_2x"] = e.net_2x.reindex(days).fillna(0.0)
    b["event_tickets"] = e.tickets.reindex(days).fillna(0).astype(int)
    b["unscored"] = e.unscored.reindex(days).fillna(0).astype(int)
    cutoff = (pd.Timestamp(today) - pd.Timedelta(days=FINAL_LAG)).strftime("%Y-%m-%d")
    b["final"] = b.carry.notna() & b.flow.notna() & (b.index <= cutoff)
    b["book"] = sum(b[k] / SD[k] for k in FAMILIES) / len(FAMILIES)
    b["book_2x"] = sum(b[f"{k}_2x"] / SD[k] for k in FAMILIES) / len(FAMILIES)
    b["equal_capital"] = b[list(FAMILIES)].mean(axis=1, skipna=False)
    return b


def summarise(x):
    if len(x) < 2:
        return {"days": int(len(x))}
    eq = np.cumsum(x)
    return {"days": int(len(x)), "mean": float(x.mean()), "nw_t": float(stats.newey_west_t(x, LAG)[2]),
            "max_dd": float(np.min(eq - np.maximum.accumulate(np.append(0.0, eq))[1:]))}


def look(b, n):
    """The decision on the first n scored days, or None before n exist."""
    s = b[b.final]
    if len(s) < n:
        return None
    s = s.iloc[:n]
    t = float(stats.newey_west_t(s.book.values, LAG)[2])
    pos = int(sum(s[k].mean() > 0 for k in FAMILIES))
    ok = t >= BAR and s.book_2x.sum() > 0 and pos >= 2
    if ok:
        verdict = "PASS"
    elif n == LOOKS[-1] or s.book.mean() <= 0:
        verdict = "FAIL"
    else:
        verdict = "CONTINUE"
    return {"look": LOOKS.index(n) + 1, "days": n, "first": s.index[0], "last": s.index[-1],
            "mean": float(s.book.mean()), "nw_t": t, "sum_2x": float(s.book_2x.sum()), "families_positive": pos,
            "verdict": verdict}


def main(exp=EXP, today=None, verify=True):
    lane = exp / "xbook_fwd"
    if verify:
        log("prereg sha", prereg.verify(lane / "PREREG.md")[:12])
    today = today or pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
    j = lane / "journal"
    j.mkdir(parents=True, exist_ok=True)
    b = book_days(exp, today)
    b.to_csv(j / "book_days.csv", float_format="%.10g")
    dec = read(j / "decisions.csv")
    done = set(dec.look.astype(int)) if not dec.empty else set()
    stopped = not dec.empty and dec.verdict.isin(["PASS", "FAIL"]).any()
    new = []
    for n in LOOKS:
        k = LOOKS.index(n) + 1
        if k in done or stopped:
            continue
        r = look(b, n)
        if r is None:
            break
        new.append({**r, "decided_at": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")})
        if r["verdict"] != "CONTINUE":
            break
    if new:
        p = j / "decisions.csv"
        pd.DataFrame(new, columns=DEC_COLS).to_csv(p, mode="a", header=not p.exists() or p.stat().st_size == 0,
                                                   index=False)
        log("decisions", [(r["look"], r["verdict"]) for r in new])
    s = b[b.final]
    o = book_days(exp, today, ontime_only=True)
    o = o[o.final]
    status = {"updated": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ"), "start": START,
              "book_days": int(len(b)), "final_days": int(len(s)), "next_look": next((n for n in LOOKS if n > len(s)),
                                                                                     None),
              "decisions": (read(j / "decisions.csv").to_dict("records") if (j / "decisions.csv").exists() else []),
              "book": summarise(s.book.values), "book_2x_sum": float(s.book_2x.sum()) if len(s) else None,
              "equal_capital": summarise(s.equal_capital.values),
              "families": {k: summarise(s[k].values) for k in FAMILIES},
              "family_corr": s[list(FAMILIES)].corr().round(3).to_dict() if len(s) > 2 else None,
              "ontime_only": summarise(o.book.values),
              "event_tickets": int(b.event_tickets.sum()), "unscored_in_final": int(s.unscored.sum())}
    (j / "status.json").write_text(json.dumps(status, indent=1, default=str))
    log(f"{len(b)} book days, {len(s)} final; next look at {status['next_look']}")
    return status


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--today")
    main(today=ap.parse_args().today)
