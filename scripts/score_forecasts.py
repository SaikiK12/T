"""Score the lab's written probability forecasts (register Q25; docs/reviews/reflection_20261125_calibration.md).

registry/forecasts.csv is an append-only journal: a `forecast` row is written when the probability is written
(before the outcome), and a `resolve` row is appended when the outcome is known. Rows are never edited.

Columns: row_id, kind (forecast|resolve), forecast_id, written_utc, event, p, source, outcome, note.
- forecast: forecast_id names the forecast (e.g. O3b-sat), p in [0, 1], source = path:line of the written line (its git
  history dates it).
- resolve: forecast_id of an earlier forecast, outcome 1 (the event happened) or 0, source = where the outcome is
  written.
- erratum: a correction to an earlier row's source or event wording, in `note` (rows are never edited).
- void: an earlier forecast that cannot be scored as written (its event is undefined); excluded from the score.

Prints: counts, the Brier score of resolved forecasts, the Brier score of always forecasting their hit rate (the
base-rate reference), and a calibration table by bin.

usage: python scripts/score_forecasts.py [--file registry/forecasts.csv]
"""
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "registry" / "forecasts.csv"
COLS = ["row_id", "kind", "forecast_id", "written_utc", "event", "p", "source", "outcome", "note"]
BINS = ((0.0, 0.3), (0.3, 0.6), (0.6, 1.0001))


def load(path=FILE):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if rows and list(rows[0].keys()) != COLS:
        raise SystemExit(f"{path}: columns must be {COLS}")
    return rows


def check(rows):
    """Errors as strings: duplicate row ids, a resolve before its forecast, bad p or outcome, double resolves."""
    errs, seen_rows, forecasts, resolved = [], set(), {}, set()
    for r in rows:
        if r["row_id"] in seen_rows:
            errs.append(f"duplicate row_id {r['row_id']}")
        seen_rows.add(r["row_id"])
        fid = r["forecast_id"]
        if r["kind"] == "forecast":
            if fid in forecasts:
                errs.append(f"forecast {fid} written twice")
            try:
                p = float(r["p"])
                if not 0 <= p <= 1:
                    raise ValueError
                forecasts[fid] = p
            except ValueError:
                errs.append(f"forecast {fid}: p {r['p']!r} not in [0, 1]")
        elif r["kind"] == "resolve":
            if fid not in forecasts:
                errs.append(f"resolve {fid} has no earlier forecast row")
            if fid in resolved:
                errs.append(f"forecast {fid} resolved twice")
            resolved.add(fid)
            if r["outcome"] not in ("0", "1"):
                errs.append(f"resolve {fid}: outcome {r['outcome']!r} must be 0 or 1")
        elif r["kind"] in ("erratum", "void"):
            if fid not in forecasts:
                errs.append(f"{r['kind']} {fid} has no earlier forecast row")
        else:
            errs.append(f"row {r['row_id']}: kind {r['kind']!r}")
    return errs


def pairs(rows):
    """[(forecast_id, p, outcome)] for resolved forecasts, in forecast order."""
    p = {r["forecast_id"]: float(r["p"]) for r in rows if r["kind"] == "forecast"}
    o = {r["forecast_id"]: int(r["outcome"]) for r in rows if r["kind"] == "resolve"}
    void = {r["forecast_id"] for r in rows if r["kind"] == "void"}
    return [(f, p[f], o[f]) for f in p if f in o and f not in void]


def score(prs):
    n = len(prs)
    if not n:
        return {"n": 0}
    brier = sum((p - o) ** 2 for _, p, o in prs) / n
    hit = sum(o for _, _, o in prs) / n
    ref = sum((hit - o) ** 2 for _, _, o in prs) / n
    # leave-one-out reference: each outcome forecast by the hit rate of the others (the in-sample one is optimistic)
    tot = sum(o for _, _, o in prs)
    loo = sum((((tot - o) / (n - 1)) - o) ** 2 for _, _, o in prs) / n if n > 1 else float("nan")
    bins = []
    for lo, hi in BINS:
        b = [(p, o) for _, p, o in prs if lo <= p < hi]
        if b:
            bins.append((lo, min(hi, 1.0), len(b), sum(p for p, _ in b) / len(b), sum(o for _, o in b) / len(b)))
    return {"n": n, "brier": brier, "hit_rate": hit, "brier_base_rate": ref, "brier_loo_base_rate": loo, "bins": bins}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(FILE))
    a = ap.parse_args()
    rows = load(a.file)
    errs = check(rows)
    if errs:
        print("\n".join(errs))
        return 1
    n_f = sum(r["kind"] == "forecast" for r in rows)
    n_v = len({r["forecast_id"] for r in rows if r["kind"] == "void"})
    s = score(pairs(rows))
    print(f"forecasts {n_f}, resolved {s['n']}, void {n_v}, pending {n_f - s['n'] - n_v}")
    if s["n"]:
        print(f"Brier {s['brier']:.3f}; references: always the hit rate {s['brier_base_rate']:.3f} (in sample, "
              f"optimistic), leave-one-out {s['brier_loo_base_rate']:.3f}, always 0.5 0.250; lower is better")
        print("| p bin | n | mean p | hit rate |\n|---|---|---|---|")
        for lo, hi, n, mp, hr in s["bins"]:
            print(f"| {lo:.1f}-{hi:.1f} | {n} | {mp:.2f} | {hr:.2f} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
