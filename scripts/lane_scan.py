"""Cross-lane scan: every committed lane summary table normalized into one table of cells, to choose what to refine.

The owner asked (2026-11-17) to search wide across all the old lanes and then refine. This reads every
`experiments/*/results/*.csv` that reports daily net results (`mean_bp_day`), normalizes the label, window, cost
multiple, net, gross, cost, t, days, Sharpe and drawdown columns, attaches the lane's registry rounds, and sorts each
cell into one of five groups:

- robust: net > 0 with t >= 2 at 1x, and still > 0 at 2x (the 2x row, or gross - 2 x cost);
- cost_killed: gross > 0 but net <= 0 at 1x. Candidates for cost levers (maker fills, less turnover, cheaper venue,
  a cost gate);
- underpowered: net > 0 at 1x with t < 2. Candidates for more data or a longer sample;
- weak_negative: net <= 0 and gross unknown, or gross > 0 with net <= 0 when gross is unknown;
- gross_negative: gross <= 0, so no cost lever helps.

**This is a map of seen windows, not evidence.** Every cell was read before; picking the best cell here is selection on
seen data. A refinement is a new registered lane with its trials counted and, where possible, data nobody has read.

    python scripts/lane_scan.py [--out docs/reviews/lane_scan_20261117]
"""
import argparse
import csv
import glob
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LABELS = ("book", "rule", "variant", "strategy", "candidate", "cell", "family", "kind", "name", "signal", "lane",
          "horizon", "pair")
WINDOWS = ("window", "period", "split", "sample")
CMULTS = ("cmult", "cost_multiple", "cost_mult", "k")
TS = ("t_nw10", "t_nw", "nw10_t", "nw_t", "t")
OOS = re.compile(r"valid|holdout|test|oos|reserved|blind|forward|2020", re.I)


def num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def first(row, keys):
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return k, row[k]
    return None, None


def rounds_by_lane(path=ROOT / "registry" / "rounds.csv"):
    out = defaultdict(list)
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            lane = (r.get("path") or "").rstrip("/").split("/")[-1] or r.get("lane", "")
            out[lane].append((r["id"], r.get("status", ""), r.get("verdict", ""), r.get("trials", "")))
    return out


def harvest(files=None):
    """Normalized cells from every summary table with a mean_bp_day column."""
    rows = []
    for path in sorted(files or glob.glob(str(ROOT / "experiments" / "*" / "results" / "*.csv"))):
        try:
            with open(path, newline="", encoding="utf-8") as f:
                rdr = csv.DictReader(f)
                if not rdr.fieldnames or "mean_bp_day" not in [c.strip() for c in rdr.fieldnames]:
                    continue
                data = [{(k or "").strip(): v for k, v in r.items()} for r in rdr]
        except (OSError, UnicodeDecodeError, csv.Error):
            continue
        lane = Path(path).parts[-3]
        for r in data:
            lk, label = first(r, LABELS)
            _, window = first(r, WINDOWS)
            ck, cm = first(r, CMULTS)
            tk, t = first(r, TS)
            rows.append({"lane": lane, "file": Path(path).name, "label": label or "", "window": window or "",
                         "cmult": num(cm) if ck != "k" or num(cm) in (1.0, 2.0, 3.0) else 1.0,
                         "net_bp_day": num(r.get("mean_bp_day")), "gross_bp_day": num(r.get("gross_bp_day")),
                         "cost_bp_day": num(r.get("cost_bp_day")), "t": num(t), "days": num(r.get("days")),
                         "sharpe": num(r.get("sharpe") or r.get("annualized_sharpe") or r.get("sharpe_252")),
                         "max_dd": num(r.get("max_dd") or r.get("max_drawdown"))})
    for r in rows:
        if r["cmult"] is None:
            r["cmult"] = 1.0
    return rows


ANN = ("ann_net_pct", "ann_pct", "annual_net_pct", "net_pct_yr")
JT = ("nw_t", "t_nw", "nw10_t", "t_nw10", "nw_t_1x", "t")
XTOK = re.compile(r"(?:^|[_\-/ .])([123])x(?=$|[_\-/ .])")


def harvest_json(files=None):
    """Cells from report JSONs: every dict holding an annualized net (or bp/day) and a t, labelled by its key path.
    A '_1x' / '_2x' / '_3x' token in the path gives the cost multiple and is removed from the label."""
    rows = []

    def walk(o, path, lane, fname):
        if isinstance(o, dict):
            ann = next((o[k] for k in ANN if isinstance(o.get(k), (int, float))), None)
            bp = o.get("mean_bp_day") if isinstance(o.get("mean_bp_day"), (int, float)) else None
            gross_cell = any(tok.startswith("gross") for tok in re.split(r"[/\[\]]", path.lower()))
            if (ann is not None or bp is not None) and not gross_cell:   # a "gross" branch is not a net result
                net_bp = bp if bp is not None else ann / 3.65
                m = XTOK.search(path)
                label = XTOK.sub("", path)
                gross = o.get("ann_gross_pct")
                rows.append({"lane": lane, "file": fname, "label": label, "window": label,
                             "cmult": float(m.group(1)) if m else 1.0, "net_bp_day": num(net_bp),
                             "gross_bp_day": num(gross / 3.65) if isinstance(gross, (int, float)) else None,
                             "cost_bp_day": num((gross - ann) / 3.65) if isinstance(gross, (int, float)) and ann is not None
                             else None,
                             "t": num(next((o[k] for k in JT if isinstance(o.get(k), (int, float))), None)),
                             "days": num(o.get("days") or o.get("intervals") or o.get("active_days")),
                             "sharpe": num(o.get("sharpe")), "max_dd": num(o.get("max_dd_pct") or o.get("max_drawdown_pct"))})
            for k, v in o.items():
                walk(v, f"{path}/{k}" if path else str(k), lane, fname)
        elif isinstance(o, list):
            for i, v in enumerate(o[:200]):
                walk(v, f"{path}[{i}]", lane, fname)

    for p in sorted(files or glob.glob(str(ROOT / "experiments" / "*" / "results" / "*.json"))):
        try:
            data = json.loads(Path(p).read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError):
            continue
        walk(data, "", Path(p).parts[-3], Path(p).name)
    return rows


def classify(cells):
    """Group each 1x cell, using the same lane/file/label/window's 2x row when there is one."""
    by_key = defaultdict(dict)
    for c in cells:
        by_key[(c["lane"], c["file"], c["label"], c["window"])][c["cmult"]] = c
    out = []
    for key, by_c in by_key.items():
        c1 = by_c.get(1.0) or by_c[min(by_c)]
        net, gross, cost, t = c1["net_bp_day"], c1["gross_bp_day"], c1["cost_bp_day"], c1["t"]
        if net is None:
            continue
        net2 = by_c[2.0]["net_bp_day"] if 2.0 in by_c else (gross - 2 * cost if gross is not None and cost is not None
                                                             else None)
        if gross is not None and gross <= 0:
            grp = "gross_negative"
        elif net > 0 and t is not None and t >= 2 and (net2 is None or net2 > 0):
            grp = "robust"
        elif net > 0:
            grp = "underpowered"
        elif gross is not None and gross > 0:
            grp = "cost_killed"
        else:
            grp = "weak_negative"
        be = round(gross / cost, 2) if gross is not None and cost and cost > 0 else None
        out.append(dict(c1, net_2x_bp_day=net2, group=grp, break_even_cost_multiple=be,
                        oos=bool(OOS.search(c1["window"] or ""))))
    return out


def write(out_dir, cells, groups, lanes):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    keys = ["lane", "file", "label", "window", "oos", "group", "net_bp_day", "net_2x_bp_day", "gross_bp_day",
            "cost_bp_day", "break_even_cost_multiple", "t", "days", "sharpe", "max_dd", "rounds"]
    with open(out_dir / "cells.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for g in sorted(groups, key=lambda g: (g["lane"], g["file"], g["label"], g["window"])):
            w.writerow(dict(g, rounds=" ".join(f"{i}:{v}" for i, _, v, _ in lanes.get(g["lane"], []))))
    summary = defaultdict(lambda: defaultdict(int))
    for g in groups:
        summary[g["group"]]["cells"] += 1
        summary[g["group"]]["oos_cells"] += g["oos"]
    (out_dir / "summary.json").write_text(json.dumps({k: dict(v) for k, v in summary.items()}, indent=1))
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "docs" / "reviews" / "lane_scan_20261117"))
    a = ap.parse_args(argv)
    cells = harvest() + harvest_json()
    groups = classify(cells)
    lanes = rounds_by_lane()
    s = write(a.out, cells, groups, lanes)
    print(json.dumps({"tables": len({(c['lane'], c['file']) for c in cells}), "lanes": len({c['lane'] for c in cells}),
                      "rows": len(cells), "groups": {k: dict(v) for k, v in s.items()}}))


if __name__ == "__main__":
    main()
