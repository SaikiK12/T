"""R438 carry_v2_audit_kc_v1: R277's two KuCoin carry books (forward on paper as R279 A and B) re-run on the M468
engine (lab/xfund_v2), as set out in experiments/carry_v2_audit_kc_v1/PREREG.md.

R437 ran this accounting audit on R275's seven headline books; R279's KuCoin books were not in it. This runner reuses
R437's frozen runner (scripts/run_carry_v2_audit.py: load, stats, run_book, audit, synthetic) unchanged and only
swaps in the book list, R277's spec and R277's frozen daily output for the v1 parity check:
  v1  lab/xfund. Its 1x daily net must equal R277's results/daily.csv to 1e-9 for both books, or the run stops.
  v2  lab/xfund_v2, as in R437 (fresh = any traded bar in the day, fixed-quantity legs, no price gain on an
      unobserved interval, blowout exits at a 20% move of the legs' price ratio, dead legs closed; no mark files).

usage: python scripts/run_carry_v2_audit_kc.py --plumbing   (v1 parity and coverage only; no v2 statistic)
       python scripts/run_carry_v2_audit_kc.py --run        (once, after the freeze)
       python scripts/run_carry_v2_audit_kc.py --dry        (synthetic universe, writes nowhere in the repo)
"""
import argparse
import json
import sys
import time
import tomllib
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402
from lab import xfund as v1  # noqa: E402
from lab import xfund_v2 as v2  # noqa: E402
from scripts import run_carry_v2_audit as base  # noqa: E402

LANE = ROOT / "experiments" / "carry_v2_audit_kc_v1"
RUN277 = ROOT / "experiments" / "xfund_kd_v1"
# R277's two replicating sets, each run with R275's best rule; both are forward on paper (R279).
BOOKS = [
    ("gate+kucoin", 14, 0.05, 20, "R279 A"),
    ("binance+kucoin", 14, 0.05, 20, "R279 B"),
]


def audit(u1, u2, spec, eng_daily=None, plumbing=False, log=print):
    """R437's audit over this lane's books (base.audit reads the module-level BOOKS)."""
    saved = base.BOOKS
    base.BOOKS = BOOKS
    try:
        return base.audit(u1, u2, spec, eng_daily, plumbing=plumbing, log=log)
    finally:
        base.BOOKS = saved


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--plumbing", action="store_true")
    g.add_argument("--run", action="store_true")
    g.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    spec = tomllib.loads((RUN277 / "spec.toml").read_text())
    if a.dry:
        u1, u2 = base.synthetic(spec)
        out, daily, trades = audit(u1, u2, {**spec, "start": "2021-01-01", "recent_from": "2021-08-01"})
        print(json.dumps({"books": len(out), "daily_rows": len(daily), "trades": len(trades),
                          "survives": [r["survives"] for r in out]}))
        return
    if a.run:
        from scripts.run_clockflow import check_inputs
        prereg.verify(LANE / "PREREG.md")
        check_inputs(LANE / "PREREG.md")
    need = {v for s, *_ in BOOKS for v in s.split("+")}
    t = time.time()
    u1 = base.load(spec, v1, need)
    u2 = base.load(spec, v2, need)
    print(f"loaded {len(u1.keys)} coins x {len(u1.names)} venues, {u1.nd} days ({time.time() - t:.0f}s)", flush=True)
    eng = pd.read_csv(RUN277 / "results" / "daily.csv")
    out, daily, trades = audit(u1, u2, spec, eng, plumbing=a.plumbing, log=lambda m: print(m, flush=True))
    if a.plumbing:
        print(json.dumps(out, indent=1, default=float))
        return
    res = LANE / "results"
    res.mkdir(exist_ok=True)
    pd.DataFrame(out).to_csv(res / "books.csv", index=False, float_format="%.10g")
    pd.DataFrame(daily, columns=["book", "engine", "date", "net_1x", "net_2x", "net_3x"]).to_csv(
        res / "daily.csv", index=False, float_format="%.10g")
    pd.DataFrame(trades).to_csv(res / "trades_v2.csv", index=False, float_format="%.10g")
    report = {"rid": "R438", "trials": len(BOOKS), "books": out,
              "survive_count": int(sum(r["survives"] for r in out)),
              "forward_books_surviving": {r["forward"]: r["survives"] for r in out}}
    (res / "report.json").write_text(json.dumps(report, indent=1, default=float))
    print(json.dumps({k: report[k] for k in ("survive_count", "forward_books_surviving")}))


if __name__ == "__main__":
    main()
