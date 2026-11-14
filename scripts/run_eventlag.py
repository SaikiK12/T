"""R369 eventlag_fwd runner, frozen in experiments/eventlag_fwd/PREREG.md: at each EIA release, does Lighter still show the
old price after Binance or Hyperliquid has moved, long enough that a taker on Lighter earns the catch-up?

For every release in experiments/eventlag_fwd/events.csv that is at least 15 minutes old and not yet in the journal, reads
the recorded quotes of the three venues around it, scores the rule of scripts/eventlag_rule.py and appends the result to
experiments/eventlag_fwd/journal/ (append-only; an event is scored once). It then rebuilds results/summary.json and
results/cells.csv from the journal. Meant to run every hour (lab/operations.py, task R369); nothing is traded.

usage: python scripts/run_eventlag.py               the frozen lane (verifies the PREREG and every input it lists)
       python scripts/run_eventlag.py --plumbing    quote counts per venue for the due events only; no price is computed
"""
import argparse
import csv
import datetime as dt
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
import eventlag_rule as rule  # noqa: E402

LANE = ROOT / "experiments" / "eventlag_fwd"
REGISTRY = "R369"
CP = ROOT / "data" / "commodity_perps"
LT = ROOT / "data" / "lighter_trades"
SOURCES = {   # event type -> venue -> (folder under its root, symbol)
    "ng": {"binance": (CP / "bnbook", "NATGASUSDT"), "hl": (CP / "hlbbo", "NATGAS"), "lighter": (LT / "quote", "NATGAS")},
    "wpsr": {"binance": (CP / "bnbook", "CLUSDT"), "hl": (CP / "hlbbo", "CL"), "lighter": (LT / "quote", "WTI")},
}
PLACEBO_DAYS = {"ng": (2, 3), "wpsr": (1, 2)}   # same clock time on days with no release of that kind at that time
DUE_AFTER_S = 15 * 60
FIRST_RELEASE = "2026-10-29T14:30:00Z"            # nothing before this instant is scored
PAD_BEFORE_S, PAD_AFTER_S = 310, 75
CELL_COLS = ["event", "release_utc", "kind", "follower", "lag_s", "status", "lead", "s", "t_star_s", "D", "c", "lag_ok",
             "entry", "exit", "size_usd", "gross"]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


def frozen_inputs(prereg_path, root=ROOT):
    """Every file in the PREREG's inputs block must still hash to its frozen sha256."""
    block = re.search(r"```inputs\n(.*?)```", Path(prereg_path).read_text(), re.S).group(1)
    shas = {}
    for line in block.strip().splitlines():
        want, rel = line.split()
        got = prereg.sha256_file(root / rel)
        if got != want:
            raise prereg.PreregError(f"{rel}: sha256 {got} != frozen {want}")
        shas[rel] = got
    return shas


def utc_day(t_us):
    return dt.datetime.fromtimestamp(t_us / 1e6, dt.timezone.utc).strftime("%Y-%m-%d")


def read_quotes(folder, sym, lo_us, hi_us):
    """Quotes with receive time in [lo, hi] from the recorder's parts, sorted, crossed or non-positive quotes dropped."""
    days = sorted({utc_day(lo_us), utc_day(hi_us)})
    frames = [pd.read_parquet(f, columns=["t", "bid", "bq", "ask", "aq"])
              for d in days for f in sorted((Path(folder) / sym / d).glob("*.parquet"))]
    empty = {k: np.array([], dtype=np.int64 if k == "t" else float) for k in ("t", "bid", "ask", "bq", "aq")}
    if not frames:
        return empty
    df = pd.concat(frames, ignore_index=True)
    df = df[(df.t >= lo_us) & (df.t <= hi_us) & (df.bid > 0) & (df.ask >= df.bid) & (df.bq > 0) & (df.aq > 0)]
    df = df.sort_values("t", kind="stable").drop_duplicates(["t", "bid", "ask", "bq", "aq"])
    return {k: df[k].to_numpy() for k in ("t", "bid", "ask", "bq", "aq")}


def load_event(etype, T_us, roots=None):
    lo, hi = T_us - rule.US * PAD_BEFORE_S, T_us + rule.US * PAD_AFTER_S
    return {v: read_quotes(folder, sym, lo, hi) for v, (folder, sym) in (roots or SOURCES)[etype].items()}


def validity(quotes, T_us):
    """'' when every venue has a reference and quotes in the 60 s after T; otherwise the first failing venue and why."""
    for v in rule.VENUES:
        q = quotes[v]
        if not np.isfinite(rule.reference(q, T_us)):
            return f"{v}:no_reference"
        if not ((q["t"] >= T_us) & (q["t"] <= T_us + 60 * rule.US)).any():
            return f"{v}:no_quotes_after"
    return ""


def score_event(etype, release_utc, quotes, T_us, kind="event"):
    """Cell rows for every follower and latency of one event (the primary follower at every latency, the others at the
    decision latency), plus the validity string."""
    bad = validity(quotes, T_us)
    rows = []
    if bad:
        return bad, rows
    plan = [(rule.PRIMARY_FOLLOWER, L) for L in rule.LAGS] + [(f, rule.DECISION_L) for f in rule.REPORT_FOLLOWERS]
    for follower, L in plan:
        r = rule.evaluate(quotes, T_us, etype, follower, L)
        rows.append({"event": etype, "release_utc": release_utc, "kind": kind, "follower": follower, "lag_s": L,
                     **{k: r[k] for k in CELL_COLS[5:]}})
    return "", rows


def due(events, journal_events, now):
    done = {(r["event"], r["release_utc"]) for r in journal_events}
    first = dt.datetime.fromisoformat(FIRST_RELEASE.replace("Z", "+00:00")).timestamp() * 1000
    return [e for e in events.itertuples()
            if e.release_ms >= first and (e.event, e.release_utc) not in done
            and e.release_ms / 1000 + DUE_AFTER_S <= now.timestamp()]


def read_csv_rows(path):
    if not Path(path).exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def append_rows(path, fields, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        if new:
            w.writeheader()
        w.writerows(rows)


def process(lane=LANE, now=None, roots=None, plumbing=False):
    now = now or dt.datetime.now(dt.timezone.utc)
    events = pd.read_csv(lane / "events.csv")
    jdir = lane / "journal"
    todo = due(events, read_csv_rows(jdir / "events.csv"), now)
    for e in todo:
        T_us = int(e.release_ms) * 1000
        quotes = load_event(e.event, T_us, roots)
        if plumbing:
            log(e.event, e.release_utc, {v: len(q["t"]) for v, q in quotes.items()}, validity(quotes, T_us) or "valid")
            continue
        bad, cells = score_event(e.event, e.release_utc, quotes, T_us)
        placebos = []
        if not bad:
            for back in PLACEBO_DAYS[e.event]:
                Tp = T_us - back * 86_400 * rule.US
                pbad, prow = score_event(e.event, e.release_utc, load_event(e.event, Tp, roots), Tp, kind=f"placebo-{back}d")
                if pbad:
                    placebos.append({"event": e.event, "release_utc": e.release_utc, "kind": f"placebo-{back}d",
                                     "follower": rule.PRIMARY_FOLLOWER, "status": f"invalid:{pbad}"})
                else:
                    placebos += [r for r in prow if r["follower"] == rule.PRIMARY_FOLLOWER and r["lag_s"] == rule.DECISION_L]
        append_rows(jdir / "cells.csv", CELL_COLS, [{k: r.get(k, "") for k in CELL_COLS} for r in cells + placebos])
        append_rows(jdir / "events.csv", ["event", "release_utc", "processed_utc", "validity"],
                    [{"event": e.event, "release_utc": e.release_utc, "processed_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                      "validity": bad or "valid"}])
        log(e.event, e.release_utc, bad or "valid", f"{len(cells)} cells, {len(placebos)} placebo rows")
    return len(todo)


def summarize(lane=LANE):
    """Rebuild results/ from the journal: one row per (type, follower, latency, filtered)."""
    ev = pd.DataFrame(read_csv_rows(lane / "journal" / "events.csv"))
    cells = pd.DataFrame(read_csv_rows(lane / "journal" / "cells.csv"))
    res = lane / "results"
    res.mkdir(parents=True, exist_ok=True)
    if ev.empty:
        state, text = rule.verdict([])
        (res / "summary.json").write_text(json.dumps({"registry": REGISTRY, "state": state, "text": text,
                                                      "valid": {}, "processed": 0}, indent=1) + "\n")
        return state
    valid = ev[ev.validity == "valid"].groupby("event").size().to_dict()
    if cells.empty:
        state, text = rule.verdict([])
        (res / "summary.json").write_text(json.dumps({"registry": REGISTRY, "state": state, "text": text, "valid": valid,
                                                      "processed": int(len(ev)), "invalid": int(len(ev))}, indent=1) + "\n")
        return state
    # a crash between the two appends of one event can leave its cells written twice: count each cell once
    live = cells[cells.kind == "event"].drop_duplicates(["event", "release_utc", "follower", "lag_s"]).copy()
    for c in ("gross", "lag_s", "c", "D", "t_star_s"):
        live[c] = pd.to_numeric(live[c], errors="coerce")
    live["lag_ok"] = live.lag_ok.astype(str).eq("True")
    rng = np.random.default_rng(rule.SEED)
    out = []
    for (etype, follower, lag), g in live.groupby(["event", "follower", "lag_s"]):
        for filtered in (True, False):
            tr = g[(g.status == "ok") & (g.lag_ok if filtered else True)]
            x = tr.gross.to_numpy(dtype=float)
            row = {"event": etype, "follower": follower, "lag_s": lag, "lag_filter": filtered,
                   "valid_events": valid.get(etype, 0), "ok_quotes": int((g.status == "ok").sum()), **rule.summarize(x),
                   "p": rule.sign_flip_p(x, rng)}
            for k in rule.COST_MULTS:
                row[f"net_{k}x"] = row["mean"] - k * 2 * rule.FEE_SIDE_BP[follower]
            row["fire_rate"] = len(tr) / max(valid.get(etype, 0), 1)
            out.append(row)
    table = pd.DataFrame(out)
    dec = table[(table.follower == rule.PRIMARY_FOLLOWER) & (table.lag_s == rule.DECISION_L) & table.lag_filter]
    table["decision"] = False
    table["p_holm"] = np.nan
    if not dec.empty:
        table.loc[dec.index, "decision"] = True
        table.loc[dec.index, "p_holm"] = rule.holm(dec.p.fillna(1.0).to_numpy())
    table.to_csv(res / "cells.csv", index=False)
    d = table[table.decision]
    state, text = rule.verdict([{"n": int(r.n), "valid": int(r.valid_events), "mean": r["mean"], "p_holm": r.p_holm}
                                for _, r in d.iterrows()])
    status_counts = live.groupby(["event", "follower", "lag_s", "status"]).size().reset_index(name="n")
    status_counts.to_csv(res / "status_counts.csv", index=False)
    (res / "summary.json").write_text(json.dumps(
        {"registry": REGISTRY, "state": state, "text": text, "valid": valid, "processed": int(len(ev)),
         "invalid": int((ev.validity != "valid").sum()), "decisions": json.loads(d.to_json(orient="records"))},
        indent=1) + "\n")
    return state


def run(lane=LANE, check=True, plumbing=False, now=None, roots=None):
    if check:
        digest = prereg.verify(lane / "PREREG.md")
        inputs = frozen_inputs(lane / "PREREG.md")
        log(f"PREREG verified {digest[:12]}; {len(inputs)} inputs match")
    n = process(lane, now, roots, plumbing)
    if plumbing:
        return "PLUMBING"
    state = summarize(lane)
    log(f"{n} event(s) scored;", state)
    return state


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true")
    a = ap.parse_args()
    run(plumbing=a.plumbing)
