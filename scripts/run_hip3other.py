"""R476 hip3other_v1, frozen in experiments/hip3other_v1/PREREG.md: R475's rule on the other HIP-3 deployers.

The book, marks, costs, samples and verdict are R475's frozen code (`scripts/run_hip3stock.py`), called unchanged:
5 slots, enter at >= 12%/yr trailing 28-day funding, exit below 6%/yr, M = 1/3, from 2026-01-16. A (weeks ending by
2026-07-22) decides; B (to 2026-11-06) is reported. Only the universe differs: every HIP-3 dex but xyz.

usage: python scripts/run_hip3other.py [--data data/hip3other]
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
import run_hip3stock as hs  # noqa: E402  (frozen in R475)
from run_xyzwknd import frozen_inputs  # noqa: E402  (frozen in R462)

LANE = ROOT / "experiments" / "hip3other_v1"
DATA = ROOT / "data" / "hip3other"
REGISTRY = "R476"
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


def by_dex(trades):
    """Trades and why they closed, per deployer."""
    if not len(trades):
        return {}
    t = trades.assign(dex=trades["ticker"].str.split("_").str[0])
    return {d: {"trades": int(len(g)), "names": int(g["ticker"].nunique()),
                "why": {k: int(v) for k, v in g["why"].value_counts().items()}} for d, g in t.groupby("dex")}


def run(lane=LANE, data=DATA, check=True):
    if check:
        digest = prereg.verify(lane / "PREREG.md")
        log(f"PREREG verified {digest[:12]}; {len(frozen_inputs(lane / 'PREREG.md'))} inputs match")
    log(f"data files verified: {hs.verify_data(data)}")
    markets, bill, dropped = hs.load(data)
    log(f"markets {len(markets)}; dropped {len(dropped)}: {dropped}")
    res = lane / "results"
    res.mkdir(parents=True, exist_ok=True)
    out = {"registry": REGISTRY, "markets": sorted(markets), "dropped": dropped, "variants": {}}
    if not markets:
        out.update({"state": "INCONCLUSIVE", "text": "no market passed the filters"})
        (res / "summary.json").write_text(json.dumps(out, indent=1) + "\n")
        log(out["state"], out["text"])
        return out["state"]
    first = max(min(d for mk in markets.values() for d in mk.days), hs.BOOK_START)
    for name, params in hs.VARIANTS.items():
        daily, trades = hs.book(markets, bill, params, first, hs.END)
        wk = hs.weekly(daily)
        a, b = wk[wk["last"] <= hs.A_END], wk[wk["last"] > hs.A_END]
        ta, tb = trades[trades["closed"] <= hs.A_END], trades[trades["closed"] > hs.A_END]
        out["variants"][name] = {"params": params, "A": hs.stats(a, ta), "B": hs.stats(b, tb),
                                 "all": hs.stats(wk, trades), "by_dex": by_dex(trades)}
        daily.to_csv(res / f"daily_{name}.csv", index=False)
        wk.to_csv(res / f"weekly_{name}.csv", index=False)
        trades.to_csv(res / f"trades_{name}.csv", index=False)
    state, text = hs.verdict(out["variants"]["decide"]["A"])
    out.update({"state": state, "text": text})
    (res / "summary.json").write_text(json.dumps(out, indent=1, default=float) + "\n")
    log(state, text)
    return state


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DATA))
    a = ap.parse_args()
    run(data=Path(a.data))


if __name__ == "__main__":
    main()
