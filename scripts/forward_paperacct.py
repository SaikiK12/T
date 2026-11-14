"""paperacct_fwd (R415): a $10,000 paper account run like a real one, as set out in experiments/paperacct_fwd/PREREG.md.

The account opens on 2026-11-07 with equal capital in three pots: carry, flow and events. Each pot holds the family
value that R285 (scripts/forward_xbook.py, frozen) writes to experiments/xbook_fwd/journal/book_days.csv. That value
is the lanes' own paper net at their measured costs. A pot compounds daily and is never rebalanced, so no money moves
between venues. A day with no value leaves the pot as idle cash at 0%. A pot that falls to half its opening amount is
closed for good and its cash is kept. The 2x and 3x accounts use R285's 2x columns and their linear extension.

Derived each tick: journal/statement.csv, journal/status.json and journal/statement.md (in French, for the owner).
Append-only: journal/decisions.csv, one row per look reached. Paper only: no order, no key, no network.

usage: python scripts/forward_paperacct.py [--today YYYY-MM-DD]
"""
import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg, stats  # noqa: E402

LANE = ROOT / "experiments" / "paperacct_fwd"
BOOK = ROOT / "experiments" / "xbook_fwd" / "journal" / "book_days.csv"
OPEN = "2026-11-07"
CAPITAL = 10_000.0
FAMILIES = ("carry", "flow", "events")
STOP = 0.5                       # a pot at or below half its opening amount is closed
LOOKS = (180, 365)               # account days up to the last final day
BAR, NW = 2.24, 10               # one-sided 1.25%: two looks
MAX_DD = -0.25
MS = (1, 2, 3)
DEC_COLS = ["look", "days", "first", "last", "balance_1x", "balance_2x", "balance_3x", "nw_t", "max_dd", "verdict",
            "decided_at"]
log = lambda *a: print(time.strftime("%H:%M:%S", time.gmtime()), *a, flush=True)


def family_returns(book, m):
    """Daily family values at cost multiple m: 1x as written, 2x from the _2x columns, 3x = 1x + 2 (2x - 1x)."""
    out = {}
    for f in FAMILIES:
        v1 = pd.to_numeric(book[f], errors="coerce")
        v2 = pd.to_numeric(book[f + "_2x"], errors="coerce")
        out[f] = v1 if m == 1 else v2 if m == 2 else v1 + 2 * (v2 - v1)
    return pd.DataFrame(out, index=book.index)


def account(book, m=1, capital=CAPITAL, stop=STOP):
    """Pots compound on their family's daily value, missing = 0; a pot closes for good once it is <= stop x opening."""
    R = family_returns(book, m).fillna(0.0)
    pot0 = capital / len(FAMILIES)
    pots = {f: pot0 for f in FAMILIES}
    closed = {f: None for f in FAMILIES}
    rows = []
    for d, r in R.iterrows():
        for f in FAMILIES:
            if closed[f] is None:
                pots[f] = pots[f] * (1.0 + r[f])
                if pots[f] <= stop * pot0:
                    closed[f] = d
        rows.append({"day": d, **{f"pot_{f}": pots[f] for f in FAMILIES}, "balance": sum(pots.values())})
    out = pd.DataFrame(rows).set_index("day") if rows else pd.DataFrame(
        columns=[f"pot_{f}" for f in FAMILIES] + ["balance"])
    return out, closed


def daily_return(balance, capital=CAPITAL):
    prev = balance.shift(1)
    prev.iloc[:1] = capital
    return balance / prev - 1.0


def max_dd(balance, capital=CAPITAL):
    eq = pd.concat([pd.Series([capital]), balance.reset_index(drop=True)])
    return float((eq / eq.cummax() - 1).min()) if len(balance) else 0.0


def statement(book, open_day=OPEN):
    """The account from open_day: one row per book day, with the 1x pots and the 1x/2x/3x balances."""
    b = book.copy()
    b["day"] = b["day"].astype(str)
    b = b[b["day"] >= open_day].drop_duplicates("day", keep="last").set_index("day").sort_index()
    acc = {m: account(b, m) for m in MS}
    s = acc[1][0].copy()
    for f in FAMILIES:
        s[f"r_{f}"] = pd.to_numeric(b[f], errors="coerce")
    s["balance_2x"] = acc[2][0]["balance"]
    s["balance_3x"] = acc[3][0]["balance"]
    s["final"] = b["final"].astype(str).str.lower().eq("true") if len(b) else pd.Series(dtype=bool)
    s["pnl_day"] = s["balance"].diff().fillna(s["balance"] - CAPITAL) if len(s) else s["balance"]
    return s, acc[1][1]


def official(s):
    """Days up to the last final day: the record decisions are read on. Later days are provisional."""
    if not len(s) or not s["final"].any():
        return s.iloc[:0]
    last = s.index[s["final"].to_numpy()].max()
    return s.loc[:last]


def read_look(o, look):
    """Verdict at a look on the official days. GAIN needs all four; LOSS if the 1x balance is not above capital."""
    x = o.iloc[:look]
    r = daily_return(x["balance"])
    t = float(stats.newey_west_t(r.to_numpy(), NW)[2]) if len(r) > NW + 1 and r.std() > 0 else float("nan")
    dd = max_dd(x["balance"])
    b1, b2, b3 = float(x["balance"].iloc[-1]), float(x["balance_2x"].iloc[-1]), float(x["balance_3x"].iloc[-1])
    gain = b1 > CAPITAL and b2 > CAPITAL and t >= BAR and dd >= MAX_DD
    verdict = "GAIN" if gain else "LOSS" if b1 <= CAPITAL else ("CONTINUE" if look < LOOKS[-1] else "NOT_SHOWN")
    return {"look": look, "days": len(x), "first": x.index[0], "last": x.index[-1], "balance_1x": round(b1, 2),
            "balance_2x": round(b2, 2), "balance_3x": round(b3, 2), "nw_t": t, "max_dd": dd, "verdict": verdict}


def decide(o, past):
    """Looks reached and not yet written, in order; none after a GAIN or a LOSS."""
    done = {int(r["look"]) for r in past}
    if any(r["verdict"] in ("GAIN", "LOSS") for r in past):
        return []
    out = []
    for look in LOOKS:
        if look in done or len(o) < look:
            continue
        d = read_look(o, look)
        out.append(d)
        if d["verdict"] != "CONTINUE":
            break
    return out


def summary(x):
    if not len(x):
        return None
    r = daily_return(x["balance"])
    return {"days": len(x), "last": x.index[-1], "balance": round(float(x["balance"].iloc[-1]), 2),
            "return_pct": round((float(x["balance"].iloc[-1]) / CAPITAL - 1) * 100, 3),
            "balance_2x": round(float(x["balance_2x"].iloc[-1]), 2),
            "balance_3x": round(float(x["balance_3x"].iloc[-1]), 2),
            "max_dd_pct": round(max_dd(x["balance"]) * 100, 3),
            "best_day": round(float(x["pnl_day"].max()), 2), "worst_day": round(float(x["pnl_day"].min()), 2),
            "pots": {f: round(float(x[f"pot_{f}"].iloc[-1]), 2) for f in FAMILIES},
            "hit_days_pct": round(float((r > 0).mean()) * 100, 1)}


def french(st):
    o, p = st["official"], st["provisional"]
    lines = ["# Relevé du compte papier (R415)", "",
             f"Mis à jour : {st['updated']}. Capital de départ : 10 000 $ fictifs, ouvert le {OPEN}.",
             "Aucun ordre réel. Chaque poche reprend le résultat papier net des lanes, à leurs coûts mesurés.", ""]
    if p is None:
        lines += ["Le compte n'a pas encore de jour de marché."]
    for name, x in (("Solde officiel (jours définitifs)", o), ("Solde provisoire (jours récents, peut changer)", p)):
        if x is None:
            continue
        lines += [f"## {name}", "",
                  f"- Au {x['last']} : **{x['balance']:,.2f} $** ({x['return_pct']:+.2f} %), sur {x['days']} jours.",
                  f"- Avec des frais doublés : {x['balance_2x']:,.2f} $ ; triplés : {x['balance_3x']:,.2f} $.",
                  f"- Pire baisse depuis un sommet : {x['max_dd_pct']:.2f} %. Meilleur jour {x['best_day']:+,.2f} $, "
                  f"pire jour {x['worst_day']:+,.2f} $.",
                  "- Poches : " + ", ".join(f"{k} {v:,.2f} $" for k, v in x["pots"].items()) + ".", ""]
    closed = [f for f, d in st["closed"].items() if d]
    if closed:
        lines += ["Poches fermées (perte de moitié) : " + ", ".join(f"{f} le {st['closed'][f]}" for f in closed) + ".",
                  ""]
    lines += [f"Prochaine lecture : à {st['next_look']} jours officiels." if st["next_look"] else "Lectures terminées."]
    return "\n".join(lines) + "\n"


def read_csv_rows(p):
    if not p.exists() or not p.stat().st_size:
        return []
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", default=None, help="UTC day, for tests")
    a = ap.parse_args()
    sha = prereg.verify(LANE / "PREREG.md")
    from scripts.run_clockflow import check_inputs
    check_inputs(LANE / "PREREG.md")
    now = pd.Timestamp(a.today, tz="UTC") if a.today else pd.Timestamp.now(tz="UTC")
    j = LANE / "journal"
    j.mkdir(parents=True, exist_ok=True)
    book = pd.read_csv(BOOK) if BOOK.exists() and BOOK.stat().st_size else pd.DataFrame(
        columns=["day", "final"] + [f + s for f in FAMILIES for s in ("", "_2x")])
    book = book[book["day"].astype(str) < now.strftime("%Y-%m-%d")]
    s, closed = statement(book)
    o = official(s)
    s.to_csv(j / "statement.csv", float_format="%.6f")
    past = read_csv_rows(j / "decisions.csv")
    new = decide(o, past)
    if new:
        p = j / "decisions.csv"
        head = not p.exists() or not p.stat().st_size
        with open(p, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=DEC_COLS)
            if head:
                w.writeheader()
            for d in new:
                w.writerow({**d, "decided_at": now.isoformat()})
                log(f"look {d['look']}: {d['verdict']}")
    looks_done = {int(r["look"]) for r in past} | {d["look"] for d in new}
    ended = any(r["verdict"] in ("GAIN", "LOSS") for r in past + new)
    st = {"updated": now.strftime("%Y-%m-%dT%H:%MZ"), "prereg_sha256": sha, "open": OPEN, "capital": CAPITAL,
          "official": summary(o), "provisional": summary(s), "closed": {f: closed[f] for f in FAMILIES},
          "decisions": past + [{**d, "decided_at": now.isoformat()} for d in new],
          "next_look": None if ended else next((k for k in LOOKS if k not in looks_done), None)}
    (j / "status.json").write_text(json.dumps(st, indent=1, default=str) + "\n")
    (j / "statement.md").write_text(french(st))
    log(f"account: {len(s)} days, {len(o)} official; balance "
        f"{st['provisional']['balance'] if st['provisional'] else CAPITAL:,.2f}")


if __name__ == "__main__":
    main()
