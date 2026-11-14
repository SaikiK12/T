"""R348 tapelag_lighter_v2 end to end on an invented tape: coins with no trade, typed tables, a planted lag."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import run_tapelag_lighter as v1
from scripts import run_tapelag_lighter_v2 as v2

DAY = "2026-10-21"


def write_tape(root, n=7200, lag=3, seed=0):
    """BTC and ETH for n seconds from 00:00: Binance a random walk, Lighter the same mid `lag` seconds late. The
    other ten coins have no rows at all, which is the case that crashed R347."""
    rng = np.random.default_rng(seed)
    d0 = v1.day_ms(DAY)
    for venue in ("binance", "lighter"):
        (root / v1.TAPE / venue / "book").mkdir(parents=True, exist_ok=True)
    frames = {"binance": [], "lighter": []}
    for coin, px in (("BTC", 100_000.0), ("ETH", 4_000.0)):
        mid = px * np.exp(np.cumsum(rng.normal(0, 2e-4, n)))
        late = np.r_[np.full(lag, mid[0]), mid[:-lag]]
        s = d0 + np.arange(n) * 1000
        for venue, m in (("binance", mid), ("lighter", late)):
            frames[venue].append(pd.DataFrame({"s": s, "sym": coin, "bid": m * (1 - 1e-6), "bid_sz": 10.0,
                                               "ask": m * (1 + 1e-6), "ask_sz": 10.0, "lag_ms": 50}))
    for venue, fs in frames.items():
        pd.concat(fs).to_parquet(root / v1.TAPE / venue / "book" / f"{DAY}.parquet", index=False)


class Typed(unittest.TestCase):
    def test_an_empty_trade_table_gets_numeric_columns(self):
        t, _ = v1.simulate(np.zeros(10), *[np.full(10, np.nan)] * 4, theta=1.0, hold=5, walk=0.3)
        self.assertEqual(t.dtypes.astype(str).tolist().count("object"), len(t.columns))   # R347's crash input
        t = v2.typed(t)
        self.assertEqual(str(t.net1.dtype), "float64")
        self.assertEqual(str(t.s.dtype), "int64")


class EndToEnd(unittest.TestCase):
    def test_runs_through_the_summary_and_sees_a_planted_lag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tape(root)
            sessions = pd.DataFrame(columns=["stream", "start_utc", "end_utc", "seconds", "messages", "ended_by"])
            walk = {c: 0.1 for c in v1.COINS}
            out, trades = v2.evaluate((DAY,), sessions, walk, root=root)
        json.dumps(out, default=str)
        self.assertIn(out["verdict"], ("PASS", "PARTIAL", "NULL"))
        prim = out["trials_detail"][out["primary"]]
        self.assertGreater(prim["trades"], 100)
        self.assertGreater(prim["gross_bp"], 0)              # Lighter is 3 s late: trading toward Binance pays
        self.assertEqual(set(prim["by_coin_1x"]), {"BTC", "ETH"})
        self.assertEqual(len(trades), v1.TRIALS)


if __name__ == "__main__":
    unittest.main()
