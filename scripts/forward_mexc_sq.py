"""mexc_fwd_sq (R218): the agreement-squared flow book on MEXC prices and funding, one bar late, as set out in
experiments/mexc_fwd_sq/PREREG.md. Reads R200's journal; appends to its own journal.

usage: python scripts/forward_mexc_sq.py   (after scripts/forward_tick.py)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import forward_mexc as fm  # noqa: E402
import forward_tick as ft  # noqa: E402
from lab import prereg, slices, stats  # noqa: E402

LANE = ROOT / "experiments" / "mexc_fwd_sq"
J = LANE / "journal"
MATCH = 0.997 / 1.413                                  # R217: X2's gross exposure matched to book A's on 2021-23


def main():
    fm.log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    J.mkdir(parents=True, exist_ok=True)
    st = fm.load()
    if st["D"] == 0:
        return
    k = sum(st["ind"][c].astype(np.float64) for c in ft.BOOKS["A"])
    unit = MATCH / (ft.HOLD * ft.K)
    P = slices.positions(k ** 2, ft.HOLD, 0, st["D"] * 24, unit, -1)
    s = fm.score(st, {"X2": (P, ft.BOOKS["A"])}, J, gate_book="X2", ref=None)
    if s:
        mine, a = (pd.read_csv(p / "tickets.csv") for p in (J, fm.J))
        a = a[a.book == "A"].set_index("day")
        for kind in ("replay", "ontime"):
            x = mine[mine.kind == kind].set_index("day")
            common = x.index.intersection(a.index)
            if len(common) >= 3:
                d = (x.net.reindex(common) - a.net.reindex(common)).values
                s[f"vs_R215_A_{kind}"] = {"days": len(d), "x2_total": float(x.net.reindex(common).sum()),
                                          "a_total": float(a.net.reindex(common).sum()),
                                          "diff_mean_bp_day": float(d.mean() * 1e4),
                                          "diff_t_nw10": float(stats.newey_west_t(d, 10)[2]) if len(d) >= 20
                                          else None}
        (J / "status.json").write_text(json.dumps(s, indent=1, default=float))
        fm.log(json.dumps({key: {x: v[x] for x in ("days", "total", "total_2x", "total_3x") if x in v}
                           for key, v in s.items() if isinstance(v, dict) and "days" in v}))


if __name__ == "__main__":
    main()
