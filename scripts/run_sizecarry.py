"""sizecarry_v1 (R281): confidence-sized carry books, as set out in experiments/sizecarry_v1/PREREG.md.

For each fixed book (the five forward carry books and the reserved batch's binance+gate book), replays the same pairs
under each sizing score of lab.sizecarry and writes, to experiments/sizecarry_v1/results/:
- summary.csv: per book and score, the annual net on capital at 1x / 2x / 3x cost, t, NW t, max drawdown, notional
  traded per day, the mean largest weight, and the score's difference from the equal book (2x mean, NW t, halves, 3x);
- spa.csv: per book, Hansen's SPA and White's reality check over its five sized variants against the equal book
  (daily net at 2x cost), and the best variant;
- daily.csv: per book and score, the daily net at 1x, 2x and 3x.

Parity guard, before any number is written: each book's `equal` daily net at 1x must equal its engine run's own daily
net (results/daily.csv) within 1e-9. The run aborts otherwise.

usage: nice python scripts/run_sizecarry.py
"""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import inference, prereg, sizecarry, xfund  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402
from scripts.qx_run import inputs, sha  # noqa: E402
from scripts.xfund_parity import load  # noqa: E402

LANE = ROOT / "experiments" / "sizecarry_v1"
OUT = LANE / "results"
# (label, engine run, venue set, lookback, threshold, slots): fixed in the PREREG
BOOKS = [("R278 A", "xfund_v1", "gate+hyperliquid", 14, 0.05, 20),
         ("R278 B", "xfund_v1", "binance+mexc", 14, 0.10, 20),
         ("R278 C", "xfund_v1", "gate+mexc", 7, 0.10, 20),
         ("batch", "xfund_v1", "binance+gate", 14, 0.10, 20),
         ("R279 A", "xfund_kd_v1", "gate+kucoin", 14, 0.05, 20),
         ("R279 B", "xfund_kd_v1", "binance+kucoin", 14, 0.05, 20)]
COSTS = (0.0007, 0.0014, 0.0021)
N_BOOT, BLOCK, SEED = 2000, 10, 281
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def stats(n):
    cum = np.concatenate([[0.0], np.cumsum(n)])
    sd = n.std(ddof=1)
    return {"t": n.mean() / sd * np.sqrt(len(n)) if sd > 0 else np.nan, "t_nw": newey_west_t(n, 10)[2],
            "max_dd_pct": (cum - np.maximum.accumulate(cum)).min() * 100}


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    files, _ = inputs((LANE / "PREREG.md").read_text())
    bad = [f for f, h in files.items() if sha(ROOT / f) != h]
    if bad:
        raise SystemExit(f"inputs changed since the freeze: {bad}")
    log(f"{len(files)} inputs match the frozen hashes")
    OUT.mkdir(parents=True, exist_ok=True)
    summary, spa_rows, daily = [], [], []
    for run_name in dict.fromkeys(b[1] for b in BOOKS):
        mine = [b for b in BOOKS if b[1] == run_name]
        spec, u = load(ROOT / "experiments" / run_name, {v for b in mine for v in b[2].split("+")})
        eng = pd.read_csv(ROOT / "experiments" / run_name / "results" / "daily.csv")
        log(f"{run_name}: {len(u.keys)} coins, {u.nd} days")
        for label, _, s, l, th, k in mine:
            vset = [u.names.index(v) for v in s.split("+")]
            w0 = xfund.window_start(u, vset, l)
            name = f"{s} L{l}d th{round(th * 100)}% K{k}"
            nets = {}
            for kind in sizecarry.SCORES:
                rows = sizecarry.run(u, xfund.Book(vset, l, th, k), w0, kind)
                nets[kind] = [sizecarry.net(rows, k, c).to_numpy() for c in COSTS]
                if kind == "equal":
                    want = eng[(eng.strategy == name) & (eng.cost_multiple == 1)].net.to_numpy()
                    if len(want) != len(nets[kind][0]) or np.abs(nets[kind][0] - want).max() > 1e-9:
                        raise SystemExit(f"parity guard failed on {label} {name}")
                    log(f"{label} {name}: parity OK over {len(want)} days")
                r = {"book": label, "set": s, "strategy": name, "score": kind, "days": len(rows)}
                for m, n in zip((1, 2, 3), nets[kind]):
                    r[f"ann_{m}x_pct"] = 365 * n.mean() * 100
                r.update(stats(nets[kind][0]))
                r["traded_per_day"] = rows.legs.mean()
                r["mean_max_w"] = rows.max_w.mean()
                diff2 = nets[kind][1] - nets["equal"][1]
                half = len(diff2) // 2
                r["diff_2x_bp_day"] = diff2.mean() * 1e4
                r["diff_2x_t_nw"] = newey_west_t(diff2, 10)[2] if kind != "equal" else np.nan
                r["diff_2x_h1_bp"] = diff2[:half].mean() * 1e4
                r["diff_2x_h2_bp"] = diff2[half:].mean() * 1e4
                r["diff_3x_bp_day"] = (nets[kind][2] - nets["equal"][2]).mean() * 1e4
                summary.append(r)
                day0 = pd.Timestamp(spec["start"])
                daily.append(pd.DataFrame({"book": label, "score": kind,
                                           "date": [str((day0 + pd.Timedelta(days=int(d))).date())
                                                    for d in rows.day + 1],
                                           **{f"net_{m}x": n for m, n in zip((1, 2, 3), nets[kind])}}))
                log(f"  {label} {kind}: {r['ann_1x_pct']:+.2f}/{r['ann_2x_pct']:+.2f}/{r['ann_3x_pct']:+.2f} %/yr, "
                    f"NW t {r['t_nw']:.2f}, diff 2x {r['diff_2x_bp_day']:+.3f} bp/day")
            sized = [x for x in sizecarry.SCORES if x != "equal"]
            d = np.column_stack([nets[x][1] - nets["equal"][1] for x in sized])
            p = inference.spa(d, N_BOOT, BLOCK, np.random.default_rng(SEED))
            spa_rows.append({"book": label, "strategy": name, "spa_p": p["consistent"], "rc_p": p["upper"],
                             "stat": p["stat"], "best": sized[p["best"]]})
            log(f"  {label} SPA p {p['consistent']:.4f} (RC {p['upper']:.4f}), best {sized[p['best']]}")
    pd.DataFrame(summary).to_csv(OUT / "summary.csv", index=False, float_format="%.6g")
    pd.DataFrame(spa_rows).to_csv(OUT / "spa.csv", index=False, float_format="%.6g")
    pd.concat(daily).to_csv(OUT / "daily.csv", index=False, float_format="%.8g")
    log(f"wrote {len(summary)} runs")


if __name__ == "__main__":
    main()
