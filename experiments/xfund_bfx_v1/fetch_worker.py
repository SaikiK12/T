"""One of n parallel R507 fetch workers: the frozen fetch function on a disjoint subset (k::n) of the pairs that have
no receipt yet, with the frozen arguments (window, pace, pairs_all.csv)."""
import sys
sys.path.insert(0, "/home/user/T")
import pandas as pd
from scripts import fetch_bitfinex_history as fb
from scripts.run_xfund_bfx import DATA

k, n = int(sys.argv[1]), int(sys.argv[2])
pl = pd.read_csv(DATA / "pairs_all.csv")
done = {p.stem for p in (DATA / "receipts").glob("*.json")}
todo = [b for b in pl.base if b not in done]
mine = todo[k::n]
print(f"worker {k}/{n}: {len(mine)} of {len(todo)} pairs: {' '.join(mine)}", flush=True)
fb.fetch("2021-01-01", "2026-10-01", mine, DATA, 0.9, log=lambda *x: print(*x, flush=True),
         pairs_file=DATA / "pairs_all.csv")
