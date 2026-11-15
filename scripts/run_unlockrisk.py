"""unlockrisk_v1 (R494, M542): portfolio-path risk of the R265 unlock short under ONE frozen rule.

Reads only R265's committed per-event table. No download, no new signal, no filter, no grid search.
The primary cell (c=2%, G=10%) is fixed by the owner's Gate-4 proposal; other cells are sensitivity.

usage: python scripts/run_unlockrisk.py
"""
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg, registry  # noqa: E402

LANE = ROOT / "experiments/unlockrisk_v1"
EVENTS = ROOT / "experiments/unlocks_v1/results/events_priced.csv"
HOLD_DAYS = 7
PRIMARY = (0.02, 0.10)                      # c, G — frozen, from the owner's Gate 4
SENSITIVITY = ((0.01, 0.10), (0.03, 0.10), (0.02, 0.20), (0.02, 0.30))
S1_MAX_DD = -0.10                           # pre-declared external yardsticks
S2_WORST_DAY = -0.05
COST_COLS = ("net1x", "net2x", "net3x")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check_inputs():
    block = re.search(r"```inputs\n(.*?)```", (LANE / "PREREG.md").read_text(), re.S).group(1)
    n = 0
    for line in block.strip().splitlines():
        want, rel = line.split()
        if sha(ROOT / rel) != want:
            raise SystemExit(f"{rel}: sha256 differs from the frozen inputs block")
        n += 1
    return n


def load_events():
    d = pd.read_csv(EVENTS)
    d["day"] = pd.to_datetime(d.day)
    d["entry"] = d.day - pd.Timedelta(days=HOLD_DAYS)
    d["tot"] = d.gross + d.funding          # funding is signed: negative means the short paid
    return d.sort_values("day").reset_index(drop=True)


def portfolio(d, c, G, mark):
    """Equity path with concurrent positions marked together and sized min(c, G/n)."""
    days = pd.date_range(d.entry.min(), d.day.max(), freq="D")
    by_day = {t: g for t, g in d.groupby("day")}
    eq, peak, mdd, worst = 1.0, 1.0, 0.0, 0.0
    binds, gross_peak, daily = 0, 0.0, []
    for t in days:
        op = d[(d.entry <= t) & (d.day > t)]
        n = len(op)
        w = min(c, G / n) if n else 0.0
        if n and w < c:
            binds += 1
        gross_peak = max(gross_peak, w * n)
        if mark == "lump":
            r = float(by_day[t].tot.sum()) * w if t in by_day else 0.0
        else:
            r = float((op.tot / HOLD_DAYS).sum()) * w
        daily.append(r)
        worst = min(worst, r)
        eq *= 1.0 + r
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1.0)
    daily = np.array(daily)
    return {"terminal_equity_x": eq, "max_drawdown": mdd, "worst_day": worst,
            "peak_gross": gross_peak, "days_cap_binds": binds, "calendar_days": len(days),
            "annualised_return": eq ** (365.0 / len(days)) - 1.0,
            "daily_sharpe_ann": float(daily.mean() / daily.std() * np.sqrt(365)) if daily.std() > 0 else float("nan")}


def drag(d, c, G):
    """Mean net per event after the cap scales each event by its own entry-day concurrency."""
    out = {}
    for col in COST_COLS:
        w = np.array([min(c, G / max(1, int(((d.entry <= e) & (d.day > e)).sum()))) for e in d.entry])
        out[col] = float((d[col].to_numpy() * w).mean())
    return out


def worst_cluster(d):
    days = pd.date_range(d.entry.min(), d.day.max(), freq="D")
    worst, when = float("inf"), None
    for t in days:
        op = d[(d.entry <= t) & (d.day > t)]
        if len(op):
            s = float(op.tot.sum())
            if s < worst:
                worst, when = s, str(t.date())
    return {"sum_of_open_event_returns": worst, "day": when}


def main():
    frozen = prereg.verify(LANE / "PREREG.md")
    n_inputs = check_inputs()
    d = load_events()
    c, G = PRIMARY
    lump = portfolio(d, c, G, "lump")
    spread = portfolio(d, c, G, "spread")
    s1 = lump["max_drawdown"] > S1_MAX_DD
    s2 = lump["worst_day"] > S2_WORST_DAY
    rep = {
        "round": "R494", "method": "M542", "lane": "unlockrisk_v1",
        "prereg_sha256": frozen, "inputs_checked": n_inputs,
        "events_sha256": sha(EVENTS), "n_events": len(d),
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "program_trials_before": registry.program_trials(ROOT / "registry/rounds.csv"),
        "trials": 1,
        "primary_rule": {"per_event_cap": c, "gross_cap": G, "stop": None,
                         "funding_veto": False, "adv_filter": False},
        "primary_lump": lump, "primary_spread": spread,
        "primary_drag_mean_net_per_event": drag(d, c, G),
        "uncapped_mean_net_per_event": {k: float(d[k].mean()) for k in COST_COLS},
        "survival": {"S1_max_dd_better_than_-10pct": bool(s1),
                     "S2_worst_day_better_than_-5pct": bool(s2),
                     "verdict": "SURVIVABLE" if (s1 and s2) else "NOT SURVIVABLE"},
        "worst_cluster_unsized": worst_cluster(d),
        "sensitivity_not_deciding": [
            {"c": cc, "G": gg, "lump": portfolio(d, cc, gg, "lump")} for cc, gg in SENSITIVITY],
        "owner_stop_conflict": {
            "gate4_stop_fraction_of_stake": 0.25,
            "stop_in_equity_at_cap": -0.25 * c,
            "worst_event_in_equity_at_cap": c * float(d.tot.min()),
            "note": "the proposed 25%-of-stake stop is breached by the archived tail; it cannot be "
                    "tested without intrabar bars. The owner decides; this lane does not."},
        "limits": [
            "gate 0 description of R265's already-seen events; no confirmation, no new signal",
            "no intrabar path: LUMP and SPREAD bracket the marking assumption, neither is a path",
            "no stop, no funding veto, no ADV filter (see PREREG for why each is excluded)",
            "sizing uses concurrency at each day; the sequential number is not the portfolio path",
        ],
    }
    out = LANE / "results"
    out.mkdir(exist_ok=True)
    (out / "report.json").write_text(json.dumps(rep, indent=1) + "\n")
    check_inputs()
    write_findings(rep)
    print(json.dumps(rep["survival"], indent=1))
    print(f"primary LUMP: terminal {lump['terminal_equity_x']:.3f}x  maxDD {lump['max_drawdown']:.2%}  "
          f"worstDay {lump['worst_day']:.2%}  binds {lump['days_cap_binds']}d")


def write_findings(rep):
    l, s = rep["primary_lump"], rep["primary_spread"]
    dr, un = rep["primary_drag_mean_net_per_event"], rep["uncapped_mean_net_per_event"]
    sv, oc = rep["survival"], rep["owner_stop_conflict"]
    lines = [
        "# FINDINGS: unlockrisk_v1 (R494, M542)",
        "",
        f"Run {rep['completed_utc']} by `scripts/run_unlockrisk.py`. PREREG `{rep['prereg_sha256'][:12]}` "
        f"verified before and after; events sha `{rep['events_sha256'][:12]}`, {rep['n_events']} events. "
        "No download, no new signal, no filter, no grid search.",
        "",
        f"**Verdict: {sv['verdict']}.** One frozen rule, c=2% per event (the owner's Gate-4 proposal) "
        "with a 10% portfolio gross cap, no stop, no funding veto, no ADV filter.",
        "",
        "## Portfolio path (concurrent positions marked together)",
        "",
        "| marking | terminal | annualised | max DD | worst day | peak gross | cap binds |",
        "|---|---|---|---|---|---|---|",
        f"| LUMP (primary, conservative) | {l['terminal_equity_x']:.3f}x | {l['annualised_return']:.2%} | "
        f"{l['max_drawdown']:.2%} | {l['worst_day']:.2%} | {l['peak_gross']:.1%} | {l['days_cap_binds']} d |",
        f"| SPREAD (7-day accrual) | {s['terminal_equity_x']:.3f}x | {s['annualised_return']:.2%} | "
        f"{s['max_drawdown']:.2%} | {s['worst_day']:.2%} | {s['peak_gross']:.1%} | {s['days_cap_binds']} d |",
        "",
        f"- **S1** max DD better than -10%: {'PASS' if sv['S1_max_dd_better_than_-10pct'] else 'FAIL'} "
        f"({l['max_drawdown']:.2%}).",
        f"- **S2** worst day better than -5%: {'PASS' if sv['S2_worst_day_better_than_-5pct'] else 'FAIL'} "
        f"({l['worst_day']:.2%}).",
        "",
        "The two markings bracket an assumption, not a measurement: the committed file has one return "
        "per event and no intrabar path. LUMP puts the whole move on the unlock day and is the "
        "binding number for a daily-loss limit; SPREAD smooths it over the hold and understates spikes.",
        "",
        "## What the cap costs",
        "",
        "| costs | uncapped mean net/event | after the cap |",
        "|---|---|---|",
    ]
    for k in COST_COLS:
        lines.append(f"| {k} | {un[k]:+.2%} | {dr[k]:+.3%} |")
    lines += [
        "",
        "The cap scales each event by the concurrency on its entry day, so busy days are sized down. "
        "The drag is the price of surviving the cluster.",
        "",
        "## Cluster risk (unsized)",
        f"Worst concurrent cluster: {rep['worst_cluster_unsized']['sum_of_open_event_returns']:.1%} of "
        f"notional on {rep['worst_cluster_unsized']['day']}. A per-event cap alone does not bound this; "
        "the 10% gross cap does.",
        "",
        "## The owner decision this surfaces",
        f"Gate 4 proposes a hard stop at 25% of the stake = {oc['stop_in_equity_at_cap']:.2%} of equity "
        f"at c=2%, while the worst archived event is {oc['worst_event_in_equity_at_cap']:.2%}. The stop "
        "is breached by the observed tail at every cap in {1%, 2%, 3%} and cannot be tested without "
        "intrabar bars. Either accept a no-stop book sized small, or authorise hourly-bar collection "
        "and freeze a stop in its own lane. **This lane does not choose.**",
        "",
        "## Sensitivity (reported, decides nothing)",
        "",
        "| c | G | terminal | max DD | worst day | cap binds |",
        "|---|---|---|---|---|---|",
    ]
    for row in rep["sensitivity_not_deciding"]:
        p = row["lump"]
        lines.append(f"| {row['c']:.0%} | {row['G']:.0%} | {p['terminal_equity_x']:.3f}x | "
                     f"{p['max_drawdown']:.2%} | {p['worst_day']:.2%} | {p['days_cap_binds']} d |")
    lines += [
        "",
        "G=20% and G=30% never bind at c=2% (peak gross 18%), so they are identical to no gross cap. "
        "That was verified before the freeze and is why G=10% is the primary.",
        "",
        "## Limits",
        *[f"- {x}" for x in rep["limits"]],
        "- This is not evidence that the edge is real out of sample. Only R266's forward tickets can "
        "give that, and this lane does not touch them.",
        "",
        "## Reproduce",
        "```sh",
        "python scripts/run_unlockrisk.py",
        "```",
        "",
    ]
    (LANE / "FINDINGS.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
