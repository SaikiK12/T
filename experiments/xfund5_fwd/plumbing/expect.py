"""R440 plumbing (before the freeze): the five-venue book on R439's archive under lab/xfund (v1, the forward lanes'
accounting), for the PREREG's expectations and power table. Seen data only (R439 read it on v2).

usage: python experiments/xfund5_fwd/plumbing/expect.py > experiments/xfund5_fwd/plumbing/expect.out
"""
import sys
import time
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lab import xfund as v1  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402
from scripts import run_carry_v2_audit as base  # noqa: E402

BOOK = ("binance+gate+hyperliquid+mexc+kucoin", 14, 0.10, 20)


def window_pass(n1, n2, w):
    """Share of w-day windows meeting R390's three PASS conditions, and the worst drawdown inside any window."""
    ok, worst = [], 0.0
    for i in range(0, len(n1) - w + 1):
        a, b = n1[i:i + w], n2[i:i + w]
        _, _, t = newey_west_t(a, 10)
        c = np.cumsum(a)
        dd = float(np.min(c - np.maximum.accumulate(np.maximum(c, 0))))
        worst = min(worst, dd)
        ok.append(t >= 2.5 and b.sum() > 0 and dd > -0.03)
    return float(np.mean(ok)), worst


def main():
    spec = tomllib.loads((ROOT / "experiments" / "carry5_v1" / "spec.toml").read_text())
    t = time.time()
    u = base.load(spec, v1, set(BOOK[0].split("+")))
    print(f"loaded {len(u.keys)} coins x {len(u.names)} venues, {u.nd} days ({time.time() - t:.0f}s)")
    rows, trades, nets = base.run_book(u, v1, *BOOK, spec["costs"])
    day0 = pd.Timestamp(spec["start"])
    days = pd.to_datetime([day0 + pd.Timedelta(days=int(d)) for d in rows.day.to_numpy()])
    n1, n2 = nets[1], nets[2]
    _, mu, tt = newey_west_t(n1, 10)
    c = np.cumsum(n1)
    dd = float(np.min(c - np.maximum.accumulate(np.maximum(c, 0))))
    forced = int(sum(bool(x["forced"]) for x in trades))
    print(f"v1 {BOOK}: trades {len(trades)}, days {len(n1)} {days.min().date()}..{days.max().date()}")
    print(f"  1x {mu * 1e4:+.2f} bp/day ({mu * 365 * 100:+.2f}%/yr), NW t {tt:.2f}, sd {n1.std(ddof=1) * 1e4:.1f} bp; "
          f"2x {n2.mean() * 365 * 100:+.2f}%/yr; 3x {nets[3].mean() * 365 * 100:+.2f}%/yr; max DD {dd * 100:.2f}%; forced {forced}")
    for name, m in (("2025-01..2026-09", days >= pd.Timestamp("2025-01-01")), ("2021-01..2026-09", days >= days.min())):
        a, b = n1[m], n2[m]
        p90, w90 = window_pass(a, b, 90)
        p180, w180 = window_pass(a, b, 180)
        print(f"  {name} ({m.sum()} days): mean {a.mean() * 1e4:+.2f} bp/day ({a.mean() * 365 * 100:+.1f}%/yr); "
              f"90-day windows passing {p90:.0%}; 180-day {p180:.0%}; worst DD in any window {min(w90, w180) * 100:.2f}%")
    # the worst trough and the trades around it
    i = int(np.argmin(c - np.maximum.accumulate(np.maximum(c, 0))))
    j = int(np.argmax(c[:i + 1])) if i else 0
    print(f"  worst trough {days[j].date()} -> {days[i].date()}")
    pd.DataFrame({"date": days.date, "net_1x": n1, "net_2x": n2, "net_3x": nets[3]}).to_csv(
        Path(__file__).with_name("v1_daily.csv"), index=False, float_format="%.10g")


if __name__ == "__main__":
    main()
