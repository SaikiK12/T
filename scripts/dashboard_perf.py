"""The control room's performance and coverage datasets (docs/BENCHMARK.md build items 2-3), used by dashboard_data.py.

- tearsheets / equity / monthly: lab.tearsheet for every forward paper series (1x net, replay and on-time days,
  labelled) and for the research streams saved on disk (backtests, labelled with their round). The deflated Sharpe
  is taken at the program's trial count, so it is a harsh haircut, not a verdict.
- leaderboard: every registered round in order, with its trial count, the running program total, its best t where a
  family report has one (else the largest t written in its registry note, flagged as parsed), its own reality-check null 95th percentile (qx families), and the best t that pure chance
  reaches among that many independent tries (expected_max_sr(N, 1) in t units). A round's best t only means
  something above both bars.
- coverage: per data folder and subfolder, the first and last bar, files, bars and interior holes, from the
  provenance records (docs/provenance/*.json); recorder folders by their first and last recorded day.
- funding_board: the latest cross-venue funding snapshot (scripts/record_funding_board.py plus the MEXC ticker
  recorder) as the widest spreads first. Descriptive: same ticker is not proven the same coin, and a spread is not
  an edge until a frozen lane prices it.
All values are JSON-safe (no NaN). Read-only on the lab.
"""
import csv
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402
from lab.inference import expected_max_sr  # noqa: E402
from lab.tearsheet import tearsheet  # noqa: E402

EXP = ROOT / "experiments"
ISO_DAY = lambda ms: pd.Timestamp(int(ms), unit="ms", tz="UTC").strftime("%Y-%m-%d")
METRICS = ("days", "total_return", "cagr", "ann_vol", "sharpe", "sortino", "calmar", "max_drawdown", "max_dd_days",
           "current_drawdown", "var95", "cvar95", "tail_ratio", "skew", "excess_kurtosis", "hit_rate", "profit_factor",
           "payoff", "best_day", "worst_day", "losing_streak", "kelly", "t", "ac1", "t_nw", "sharpe_ac", "n_eff",
           "psr", "dsr", "dsr_trials", "dsr_bar_sharpe")


def clean(x):
    if isinstance(x, (float, np.floating)):
        return None if not math.isfinite(x) else float(x)
    if isinstance(x, np.integer):
        return int(x)
    return x


def _codex_stream(lane, key, value, csv="daily.csv"):
    d = pd.read_csv(EXP / lane / "results" / csv, usecols=["cost_multiple", key, "date", "net"])
    d = d[(d[key] == value) & (d.cost_multiple == 1)].sort_values("date")
    return pd.Series(d.net.values, index=pd.to_datetime(d.date))


def _carry_stream():
    z = np.load(EXP / "carry_v1" / "results" / "primary_daily.npz")
    r = np.concatenate([z["discovery"], z["validation"]])         # PREREG splits: 2021-01-01.., 2024-01-01..2025-06-30
    return pd.Series(r, index=pd.date_range("2021-01-01", periods=len(r), freq="D"))


# (series id, round, label, loader) for backtest streams saved on disk
RESEARCH = [
    ("R190 carry", "R190", "Funding carry, primary rule (backtest 2021-01..2025-06, 1x)", _carry_stream),
    ("R229 trend_vol", "R229", "Slow spot trend, vol-scaled (backtest 2022-01..2026-09, 1x)",
     lambda: _codex_stream("slow_trend_v1", "strategy", "trend_vol")),
    ("R229 passive", "R229", "Passive six-coin spot basket, risk-matched (benchmark)",
     lambda: _codex_stream("slow_trend_v1", "strategy", "passive_matched")),
    ("R230 rotation", "R230", "Weekly spot rotation, discovery-selected (backtest, 1x)",
     lambda: _codex_stream("weekly_rotation_v1", "role", "candidate", "selected_daily.csv")),
]


def tearsheets(days, n_trials):
    """(tearsheets, equity, monthly) rows."""
    sheets, equity, monthly = [], [], []
    streams = []
    by_series = {}
    for d in days:
        by_series.setdefault(d["series"], []).append(d)
    for sid, rows in sorted(by_series.items()):
        rows = [r for r in rows if r["net"] is not None]
        if not rows:
            continue
        s = pd.Series([r["net"] for r in rows], index=pd.to_datetime([r["day"] for r in rows]))
        ontime = sum(r["kind"] == "ontime" for r in rows)
        streams.append((sid, rows[0]["round"], f"{rows[0]['group']} · book {rows[0]['book']} (paper)", "forward paper",
                        s, f"{ontime} on-time of {len(rows)} days"))
    for sid, rid, label, load in RESEARCH:
        try:
            streams.append((sid, rid, label, "backtest", load(), "gate 0: in-sample and spent windows"))
        except (OSError, KeyError, ValueError):
            continue
    for sid, rid, label, kind, s, note in streams:
        t = tearsheet(s, n_trials=n_trials)
        m = t["metrics"]
        sheets.append({"series": sid, "round": rid, "label": label, "kind": kind, "note": note,
                       "start": t["curve"][0]["date"] if t["curve"] else None,
                       "end": t["curve"][-1]["date"] if t["curve"] else None,
                       **{k: clean(m.get(k)) for k in METRICS}})
        r6 = lambda v: round(v, 6) if isinstance(v, float) else v
        equity += [{"key": f"{sid}|{c['date']}", "series": sid, "kind": kind, **{k: r6(clean(v)) for k, v in c.items()}}
                   for c in t["curve"]]
        monthly += [{"key": f"{sid}|{x['year']}-{x['month']:02d}", "series": sid, "kind": kind, **x}
                    for x in t["monthly"]]
    return sheets, equity, monthly


NOTE_T = re.compile(r"(?<![A-Za-z])t\s?=?\s?(-?\d+(?:\.\d+)?)(?![\d%x])")


def notes_t(note):
    """The largest t written in a registry note ('t3.80', 't 2.07', 't=-1.2'), or None. Parsed text, approximate."""
    found = [float(m) for m in NOTE_T.findall(note)]
    return max(found) if found else None


def leaderboard(rounds, strategies):
    best, null95 = {}, {}
    for s in strategies:
        if s.get("t") is not None and (s["round"] not in best or s["t"] > best[s["round"]][0]):
            best[s["round"]] = (s["t"], s["strategy"])
    for rep in EXP.glob("*/results/report.json"):
        try:
            r = json.loads(rep.read_text())
        except (OSError, ValueError):
            continue
        if r.get("rc_null_p95") is not None:
            null95[f"experiments/{rep.parent.parent.name}"] = r["rc_null_p95"]
    paths, notes = {}, {}
    with open(ROOT / "registry" / "rounds.csv", newline="") as f:
        for row in csv.DictReader(f):
            paths[row["id"]], notes[row["id"]] = row["path"], row["notes"] or ""
    out, cum = [], 0
    for r in rounds:
        n = int(r["trials"] or 0)
        cum += n
        bt, bs = best.get(r["id"], (None, None))
        out.append({"id": r["id"], "order": r["order"], "date": r["date"], "lane": r["lane"],
                    "verdict": r["verdict"], "status": r["status"], "trials": n, "program_trials": cum,
                    "best_t": clean(bt), "best_strategy": bs, "notes_t": notes_t(notes.get(r["id"], "")),
                    "family_null_p95": clean(null95.get(paths.get(r["id"]))),
                    "chance_bar_t": clean(expected_max_sr(n, 1.0)) if n >= 2 else None,
                    "title": r["title"]})
    return out


def coverage():
    out = []
    for p in sorted((ROOT / "docs" / "provenance").glob("*.json")):
        try:
            prov = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        hourly = prov.get("hourly_coverage") or {}
        subs = dict(prov.get("subfolders") or {})
        for sub in hourly:                                   # nested hourly folders (gate_hist/open/candlesticks_1h)
            if "/" in sub and sub not in subs:
                hit = [r["bytes"] for r in prov.get("file_hashes") or [] if r["path"].startswith(sub + "/")]
                subs[sub] = {"files": len(hit), "bytes": sum(hit)}
        for sub, s in subs.items():
            h = hourly.get(sub) or (hourly.get("") if sub == "." else None) or {}
            out.append({"key": p.stem if sub == "." else f"{p.stem}/{sub}", "folder": p.stem, "subfolder": sub, "files": s.get("files"),
                        "gb": round(s.get("bytes", 0) / 1e9, 3),
                        "first": ISO_DAY(h["first"]) if h.get("first") else None,
                        "last": ISO_DAY(h["last"]) if h.get("last") else None,
                        "bars": h.get("bars"), "holes": h.get("holes"), "files_with_holes": h.get("files_with_holes"),
                        "source": prov.get("source"), "recorded": prov.get("recorded_utc"), "kind": "download"})
    rec = data.ROOT / "recorders"
    if rec.is_dir():
        for d in sorted(x for x in rec.iterdir() if x.is_dir()):
            days = sorted(x.name for x in d.iterdir() if x.is_dir() and x.name[:2] == "20")
            files = sum(1 for x in d.rglob("*") if x.is_file())
            out.append({"key": f"recorders/{d.name}", "folder": "recorders", "subfolder": d.name, "files": files,
                        "gb": round(sum(x.stat().st_size for x in d.rglob("*") if x.is_file()) / 1e9, 3),
                        "first": days[0] if days else None, "last": days[-1] if days else None, "bars": None,
                        "holes": None, "files_with_holes": None, "source": "live recorder (point-in-time)",
                        "recorded": None, "kind": "recorder"})
    return out


def funding_board(top=120):
    rec = data.ROOT / "recorders"
    snaps = sorted((rec / "funding_board").glob("*/*.parquet"))
    if not snaps:
        return []
    from scripts.record_funding_board import board
    snap = pd.read_parquet(snaps[-1])
    mx = sorted((rec / "mexc_ticker").glob("*/*.parquet"))
    mexc = pd.read_parquet(mx[-1]) if mx else None
    b = board(snap, mexc, top=top)
    at = pd.Timestamp(int(snap.recv_ms.iloc[0]), unit="ms", tz="UTC").strftime("%Y-%m-%dT%H:%MZ")
    return [{"key": r["base"], "snapshot_at": at, **{k: clean(v) for k, v in r.items()}}
            for r in b.to_dict("records")]
