"""Run a lane script with MEXC's public client paced: at most one request every 0.25 s across threads, and a request
that MEXC refuses with code 510 ("Endpoint rate limit exceeded ... scope: IP") is retried after 5, 15 and 45 s.

Why: on GitHub's shared runners R220 (scripts/forward_carry.py) fetches about 300 MEXC series in a burst of four
threads after R215 and R218 used the same IP. MEXC answers some of them 510, lab/mexc.py raises at once on any
unsuccessful body, and R220 then writes nothing (runs 42933784241 and 42939724639). The lane script and lab/mexc.py
run unchanged (lab/mexc.py is pinned by experiments/paper_quote_scope_v1/inputs.json); only the module's `get` is
wrapped in this process, so every value fetched is the same as an unpaced fetch that succeeds.

usage: python scripts/run_paced_mexc.py SCRIPT [ARGS...]
"""
import runpy
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import mexc  # noqa: E402

GAP_S = 0.25                    # minimum spacing between two MEXC requests, all threads together
WAITS_S = (5, 15, 45)           # retries after a 510 refusal


def is_rate_limited(err):
    return " 510 " in f" {err} "


def paced(get, gap=GAP_S, waits=WAITS_S, sleep=time.sleep, clock=time.monotonic):
    """`get` spaced by `gap` seconds across threads and retried after each wait in `waits` on a 510 refusal."""
    lock = threading.Lock()
    last = [float("-inf")]

    def call(*a, **k):
        for wait in (0,) + tuple(waits):
            if wait:
                sleep(wait)
            with lock:
                d = last[0] + gap - clock()
                if d > 0:
                    sleep(d)
                last[0] = clock()
            try:
                return get(*a, **k)
            except mexc.MexcError as e:
                if not is_rate_limited(e) or wait == waits[-1]:
                    raise
                print(time.strftime("%H:%M:%S"), "MEXC 510, retrying:", str(e)[:80], flush=True)
        raise AssertionError("unreachable")

    return call


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    script = Path(sys.argv[1]).resolve()
    mexc.get = paced(mexc.get)
    sys.argv = [str(script)] + sys.argv[2:]
    sys.path.insert(0, str(script.parent))
    runpy.run_path(str(script), run_name="__main__")


if __name__ == "__main__":
    main()
