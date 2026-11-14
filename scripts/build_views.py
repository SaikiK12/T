"""Build the point-in-time research universe and the int8 feature-bin tensor, and save them under data/research/."""
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab import data, features, panel, research  # noqa: E402

out = data.ROOT / "research"
out.mkdir(exist_ok=True)
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)

log("loading panel")
p = panel.load_panel()
live = ~np.isnan(p["close"])
p = p.columns(np.flatnonzero(live.any(axis=0)))      # drop symbols with no bar inside the window
log(f"panel {p.T} x {p.S}")
u = research.make_universe(p, elig_top=50, col_top=50)
log(f"universe: {u.p.S} columns, eligible per hour: median {int(np.median(u.elig.sum(1)))}, max {int(u.elig.sum(1).max())}")
specs = features.default_specs()
log(f"{len(specs)} feature specs")
bins = np.lib.format.open_memmap(out / "bins.npy", mode="w+", dtype=np.int8, shape=(len(specs), u.p.T, u.p.S))
bins, names = features.views(u.bank, specs, u.elig, log, out=bins)
bins.flush()
log("saving")
np.save(out / "ret.npy", u.ret)
np.save(out / "cmat.npy", u.cmat)
np.save(out / "elig.npy", u.elig)
np.save(out / "rank.npy", u.rank)
np.save(out / "close.npy", u.p["close"])
np.save(out / "t.npy", u.p.t)
json.dump({"symbols": u.p.symbols, "names": names, "start": panel.START, "end": data.END}, open(out / "meta.json", "w"))
log(f"done: bins {bins.shape} {bins.nbytes / 1e9:.2f} GB")
