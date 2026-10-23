"""Diagnostic for carry_fwd (R220): do Binance and MEXC settle the same funding on the same coins? Compares trailing 72 h
funding APR per hour over the forward grid for symbols mapped to a MEXC crypto contract, and lists which coins have a
spot pair on each venue. Reads no carry return. Writes experiments/carry_fwd/venue_check.json.

usage: python scripts/check_carry_venues.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import forward_carry as fc  # noqa: E402
from lab import carry  # noqa: E402


def main():
    g = fc.journal_grid()
    b, m = fc.venue_binance(g), fc.venue_mexc(g)
    ab, am = carry.trailing_apr(b["fund"], fc.LOOK), carry.trailing_apr(m["fund"], fc.LOOK)
    r = slice(fc.LOOK, None)
    mapped = [j for j, s in enumerate(g["syms"]) if np.isfinite(m["fund"][:, j]).any()
              and np.isfinite(b["fund"][:, j]).any()]
    gap = np.abs(ab[r][:, mapped] - am[r][:, mapped])
    out = {"run_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "hours": int(gap.shape[0]), "symbols_compared": len(mapped),
           "apr_gap_median": float(np.nanmedian(gap)), "apr_gap_p95": float(np.nanpercentile(gap, 95)),
           "apr_gap_max": float(np.nanmax(gap)),
           "spot_binance_only": sorted(s for s in g["syms"] if b["pair"][s] and not m["pair"][s]),
           "spot_mexc_only": sorted(s for s in g["syms"] if m["pair"][s] and not b["pair"][s]),
           "spot_both": int(sum(1 for s in g["syms"] if b["pair"][s] and m["pair"][s]))}
    (fc.LANE / "venue_check.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
