"""Extra feature tensors next to data/research/bins.npy, same [V, T, S] int8 layout and binning conventions.

  clock: the market clocks of lab/sessions.py (same for every symbol)
  flow:  open interest, long/short ratios, taker ratio (metrics) and order-book depth (bookDepth) views

usage: python scripts/build_extra_views.py clock|flow
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab import data, flowfeat, sessions  # noqa: E402

root = data.ROOT / "research"
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)
which = sys.argv[1]
meta = json.loads((root / "meta.json").read_text())
t = np.load(root / "t.npy")
T, S = len(t), len(meta["symbols"])

if which == "clock":
    names = list(sessions.CLOCKS)
    out = np.lib.format.open_memmap(root / "bins_clock.npy", mode="w+", dtype=np.int8, shape=(len(names), T, S))
    for i, n in enumerate(names):
        c = sessions.codes(t, n).astype(np.int8)
        out[i] = c[:, None]
        log(n, "codes", np.unique(c).tolist())
else:
    elig = np.load(root / "elig.npy")
    specs = flowfeat.specs()
    out = np.lib.format.open_memmap(root / "bins_flow.npy", mode="w+", dtype=np.int8, shape=(len(specs), T, S))
    names = flowfeat.build(t, meta["symbols"], elig, specs, out, log)
out.flush()
(root / f"meta_{which}.json").write_text(json.dumps({"names": names, "shape": list(out.shape)}))
log("done", which, out.shape)
