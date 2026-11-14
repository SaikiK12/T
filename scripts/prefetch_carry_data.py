"""Refresh the data roots of the forward carry lanes, without ticking them: data only, no journal write.

A lane's tick refreshes its data only when it has a day to decide. A new host (a GitHub runner with an empty cache)
would therefore build every data file from the public APIs at the moment of its first decision. This script builds or
extends them ahead of time, with the lanes' own refresh code, so that the decision tick only adds the last hours.

Lanes: R278 (scripts/forward_xfund.py, its own frozen copy), R279, R294, R390, R440 (lab.carrylane).
Paper only: public endpoints, no key, no order.

usage: python scripts/prefetch_carry_data.py [LANE ...]      (default: all five)
"""
import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SCRIPTS = {"R278": "forward_xfund.py", "R279": "forward_xfund_kc.py", "R294": "forward_xfund_lt.py",
           "R390": "forward_xfund_bg.py", "R440": "forward_xfund5.py"}


def load(rid):
    f = ROOT / "scripts" / SCRIPTS[rid]
    spec = importlib.util.spec_from_file_location(f"lane_{rid}", f)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def refresher(mod):
    """The lane's own data refresh: Lane.refresh for lab.carrylane lanes, the module's refresh for R278."""
    lane = getattr(mod, "LANE", None)
    if lane is not None and hasattr(lane, "refresh"):
        return lane.refresh
    return mod.refresh


def main(argv=None):
    rids = (argv if argv is not None else sys.argv[1:]) or list(SCRIPTS)
    bad = [r for r in rids if r not in SCRIPTS]
    if bad:
        raise SystemExit(f"unknown lanes {bad}; known: {list(SCRIPTS)}")
    failed = []
    for rid in rids:
        t = time.time()
        try:
            stats = refresher(load(rid))(int(time.time() * 1000))
            short = {v: {"files": s["files"], "failed": len(s["failed"])} for v, s in stats.items()}
            print(f"{rid}: {json.dumps(short)} in {time.time() - t:.0f} s", flush=True)
        except Exception as e:          # noqa: BLE001 - one lane's failure must not stop the others
            failed.append(rid)
            print(f"{rid}: FAILED after {time.time() - t:.0f} s: {type(e).__name__}: {str(e)[:300]}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
