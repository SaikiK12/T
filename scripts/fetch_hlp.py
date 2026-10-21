"""Hyperliquid's HLP vault (the exchange's community liquidity vault: market making, liquidations, a share of fees),
measured from its public history (POST api.hyperliquid.xyz/info, vaultDetails, no keys). It is a passive yardstick for
the lab's books: what a deposit earned without any rule of ours. Saves the raw answer to
data/hyperliquid/vaults/HLP_<YYYY-MM-DD>.json and prints step returns, compounded per year, Sharpe and drawdown.

The history is coarse (about two weeks per step over all time, a day per step over the last month). A step's return is
its pnl change over the account value at the step's start, so deposits and withdrawals inside a step blur it a little,
and a drawdown inside a step is not seen. Measurement only; nothing here deposits or trades.

usage: python scripts/fetch_hlp.py [--file saved.json]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import data  # noqa: E402

HLP = "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"
OUT = data.ROOT / "hyperliquid" / "vaults"


def steps(portfolio, key):
    """Step returns of one history (allTime, month, ...): pnl change over the previous account value."""
    p = dict(portfolio)[key]
    av = pd.Series({pd.to_datetime(t, unit="ms"): float(v) for t, v in p["accountValueHistory"]})
    pnl = pd.Series({pd.to_datetime(t, unit="ms"): float(v) for t, v in p["pnlHistory"]})
    prev = av.shift(1)
    r = pnl.diff() / prev.where(prev > 0)
    return r.replace([np.inf, -np.inf], np.nan).dropna()


def summary(r):
    if len(r) < 2:
        return {"steps": int(len(r))}
    days = r.index.to_series().diff().dt.total_seconds().median() / 86400
    eq = (1 + r).cumprod()
    span = (r.index[-1] - r.index[0]).days + days
    return {"from": str(r.index[0].date()), "to": str(r.index[-1].date()), "steps": int(len(r)),
            "step_days": round(float(days), 2),
            "annual_return": float(eq.iloc[-1] ** (365 / span) - 1),
            "sharpe": float(r.mean() / r.std(ddof=1) * np.sqrt(365 / days)),
            "max_drawdown_seen": float((eq / eq.cummax() - 1).min()), "negative_steps": int((r < 0).sum()),
            "by_year": {str(y): float((1 + g).prod() - 1) for y, g in r.groupby(r.index.year)}}


def main(file=None):
    if file:
        d = json.loads(Path(file).read_text())
    else:
        import fetch_hyperliquid_history as fh
        d = fh.post({"type": "vaultDetails", "vaultAddress": HLP})
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / f"HLP_{time.strftime('%Y-%m-%d', time.gmtime())}.json").write_text(json.dumps(d))
    out = {"name": d.get("name"), "apr_now": d.get("apr"),
           "all_time_from_2024": summary(steps(d["portfolio"], "allTime").loc["2024-01-01":]),
           "last_month": summary(steps(d["portfolio"], "month"))}
    print(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    main(ap.parse_args().file)
