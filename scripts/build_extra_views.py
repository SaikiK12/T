"""Extra feature tensors next to data/research/bins.npy, same [V, T, S] int8 layout and binning conventions.

  clock: the market clocks of lab/sessions.py (same for every symbol)
  flow:  open interest, long/short ratios, taker ratio (metrics) and order-book depth (bookDepth) views
  ctx:   market-wide crowding, the share of eligible symbols in the extreme trailing z bucket (below -1.5 or above +1.5)
         of a few return views at that hour, in fixed buckets (same for every symbol). A lone oversold coin and a
         market-wide flush are different situations; this lets a cell tell them apart.

usage: python scripts/build_extra_views.py clock|flow|ctx
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
elif which == "ctx":
    base = ["ret[1]@1h/z720", "ret[3]@1h/z720", "ret[6]@1h/z720", "ret[24]@1h/z720", "ema_ratio[8]@1h/z720"]
    edges = (0.02, 0.05, 0.1, 0.2, 0.35)
    bins = np.load(root / "bins.npy", mmap_mode="r")
    elig = np.load(root / "elig.npy")
    n_el = elig.sum(1)
    names = [f"ctx:{side}:{b}" for b in base for side in ("low", "high")]
    out = np.lib.format.open_memmap(root / "bins_ctx.npy", mode="w+", dtype=np.int8, shape=(len(names), T, S))
    for i, b in enumerate(base):
        x = np.asarray(bins[meta["names"].index(b)])
        for j, code in enumerate((0, 6)):
            share = np.where(n_el > 0, ((x == code) & elig).sum(1) / np.maximum(n_el, 1), np.nan)
            c = np.digitize(share, edges).astype(np.int8)
            c[np.isnan(share)] = -1
            out[2 * i + j] = c[:, None]
            log(names[2 * i + j], "share median", round(float(np.nanmedian(share)), 3),
                "bucket counts", np.bincount(c[c >= 0], minlength=len(edges) + 1).tolist())
else:
    elig = np.load(root / "elig.npy")
    specs = flowfeat.specs()
    out = np.lib.format.open_memmap(root / "bins_flow.npy", mode="w+", dtype=np.int8, shape=(len(specs), T, S))
    names = flowfeat.build(t, meta["symbols"], elig, specs, out, log)
out.flush()
(root / f"meta_{which}.json").write_text(json.dumps({"names": names, "shape": list(out.shape)}))
log("done", which, out.shape)
