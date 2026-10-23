"""mexc_seq (R221): the sequential decision for the MEXC flow books A, X2 and B, as set out in
experiments/mexc_seq/PREREG.md. Reads R215's and R218's tickets (never writes them); appends each completed look to
results/looks.csv and rewrites results/status.json.

usage: python scripts/forward_seq.py   (after scripts/forward_mexc.py and scripts/forward_mexc_sq.py)
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg, stats  # noqa: E402

LANE = ROOT / "experiments" / "mexc_seq"
OUT = LANE / "results"
SRC = {"A": ("mexc_fwd", "A"), "X2": ("mexc_fwd_sq", "X2"), "B": ("mexc_fwd", "B")}
LOOKS = ((1, 90, "futility", -2.0), (2, 182, "efficacy", 3.558), (3, 365, "final", 2.397))
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def nw(x):
    return float(stats.newey_west_t(x, 10)[2]) if len(x) >= 20 and np.std(x) > 0 else None


def books():
    out = {}
    for b, (lane, name) in SRC.items():
        p = ROOT / "experiments" / lane / "journal" / "tickets.csv"
        t = pd.read_csv(p) if p.exists() else pd.DataFrame(columns=["day", "book", "kind", "net"])
        out[b] = t[(t.book == name) & (t.kind == "ontime")].drop_duplicates("day").sort_values("day")
    return out


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    OUT.mkdir(parents=True, exist_ok=True)
    bk = books()
    lp = OUT / "looks.csv"
    looks = pd.read_csv(lp) if lp.exists() and lp.stat().st_size else pd.DataFrame(columns=["book", "look"])
    done = set(zip(looks.book, looks.look))
    stopped = set(looks.book[looks.decision.isin(["STOP", "PASS", "FAIL"])]) if len(looks) else set()
    new = []
    for b, t in bk.items():
        for k, n, kind, z_bar in LOOKS:
            if (b, k) in done or len(t) < n or b in stopped:
                continue
            x = t.iloc[:n]
            z = nw(x.net.values)
            two = float(x.net_2x.sum())
            if kind == "futility":
                dec = "STOP" if z is not None and z <= z_bar else "CONTINUE"
            else:
                ok = z is not None and z >= z_bar and two > 0
                dec = "PASS" if ok else ("FAIL" if kind == "final" else "CONTINUE")
            new.append({"book": b, "look": k, "days": n, "first_day": x.day.iloc[0], "last_day": x.day.iloc[-1],
                        "z": z, "boundary": z_bar, "total": float(x.net.sum()), "total_2x": two,
                        "total_3x": float(x.net_3x.sum()), "decision": dec,
                        "run_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
            if dec in ("STOP", "PASS", "FAIL"):
                stopped.add(b)
                break
    if new:
        pd.DataFrame(new).to_csv(lp, mode="a", header=not len(looks), index=False)
        log("looks:", new)
    status = {}
    for b, t in bk.items():
        x = t.net.values
        status[b] = {"ontime_days": int(len(x)), "total": float(x.sum()) if len(x) else 0.0,
                     "total_2x": float(t.net_2x.sum()) if len(x) else 0.0,
                     "total_3x": float(t.net_3x.sum()) if len(x) else 0.0, "monitor_t": nw(x),
                     "next_look": next((f"look {k} at {n} days" for k, n, _, _ in LOOKS if len(x) < n), None),
                     "closed": b in stopped}
    for b in ("X2", "B"):
        m = bk[b].set_index("day").net.align(bk["A"].set_index("day").net, join="inner")
        d = (m[0] - m[1]).values
        status[f"{b}_minus_A"] = {"days": int(len(d)), "mean_bp_day": float(d.mean() * 1e4) if len(d) else None,
                                  "t": nw(d)}
    (OUT / "status.json").write_text(json.dumps(status, indent=1, default=float))
    log(json.dumps({b: (status[b]["ontime_days"], status[b]["next_look"]) for b in SRC}))


if __name__ == "__main__":
    main()
