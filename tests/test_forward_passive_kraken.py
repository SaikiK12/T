import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts import forward_passive_kraken as fp

H, M5 = fp.H_MS, fp.M5_MS


def source(root, tickets):
    lane = root / "lane"
    (lane / "journal").mkdir(parents=True)
    pd.DataFrame([{"run": t["run"], "day": t["day"], "book": "A", "kind": "ontime", "exits": 0, "entries": 1,
                   "held": 1, "ready": "{}"} for t in tickets]).drop_duplicates().to_csv(
        lane / "journal" / "decisions.csv", index=False)
    pd.DataFrame([{"run": t["run"], "day": t["day"], "book": "A", "action": t["action"], "coin": t["coin"],
                   "long": t["long"], "short": t["short"], "spread_ann": "1", "forced": "false", "kind": "ontime",
                   "close_long": "1", "close_short": "1", "fill_long": "", "fill_short": ""} for t in tickets]).to_csv(
        lane / "journal" / "tickets.csv", index=False)
    sym = root / "symbols.csv"
    pd.DataFrame({"key": ["X", "Y"], "kraken": ["PF_XUSD", "PF_YUSD"], "hyperliquid": ["X", "Y"]}).to_csv(sym,
                                                                                                        index=False)
    return {"R509": (lane, sym)}


class Snapshot(unittest.TestCase):
    def test_sides_snapshot_and_eval(self):
        run = "2026-11-21T00:31:00Z"
        t0 = fp.iso_ms(run)
        tickets = [{"run": run, "day": "2026-11-21", "action": "enter", "coin": "X", "long": "kraken",
                    "short": "hyperliquid"},
                   {"run": run, "day": "2026-11-21", "action": "exit", "coin": "Y", "long": "kraken",
                    "short": "hyperliquid"},
                   {"run": run, "day": "2026-11-21", "action": "drop", "coin": "X", "long": "kraken",
                    "short": "hyperliquid"}]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "out"
            src = source(root, tickets)
            book = lambda s: ([[99.9, 1e6]], [[100.1, 1e6]])
            self.assertEqual(fp.snapshot(src, book, now_ms=t0 + 60_000, lane=out), 2)      # the drop is skipped
            self.assertEqual(fp.snapshot(src, book, now_ms=t0 + 60_000, lane=out), 0)      # once only
            snaps = {r["coin"]: r for r in fp._rows(out / "journal" / "snapshots.csv")}
            self.assertEqual(snaps["X"]["side"], "buy")
            self.assertEqual(snaps["Y"]["side"], "sell")                                 # exiting a Kraken long
            self.assertEqual(snaps["X"]["late"], "false")

            def fetch(tick, sym, res, start, end):
                n = (end - start) // M5
                if tick == "trade":                                   # X trades through 99.9; Y never above 100.1
                    low = [99.8] + [100.0] * (n - 1) if sym == "PF_XUSD" else [100.0] * n
                    return pd.DataFrame({"t": [start + i * M5 for i in range(n)], "low": low, "high": [100.0] * n,
                                         "open": [100.0] * n, "volume": [1.0] * n})
                return pd.DataFrame({"t": [start, start + 6 * H], "low": [100.0, 99.0], "high": [100.0, 99.0],
                                     "open": [100.0, 99.0], "volume": [0.0, 0.0]})   # the mark falls 1% by 6 h
            self.assertEqual(fp.evaluate(now_ms=t0 + 8 * H, lane=out, fetch=fetch), 4)
            ev = {(r["coin"], r["h"]): r for r in fp._rows(out / "journal" / "evaluations.csv")}
            x = ev[("X", "1")]
            self.assertEqual(x["filled"], "true")
            self.assertAlmostEqual(float(x["passive_bp"]), (99.9 / 100 - 1) * 1e4 + fp.MAKER_BP, places=3)
            y6 = ev[("Y", "6")]
            self.assertEqual(y6["filled"], "false")
            walk = 10.0                                             # (100.1 / 100 - 1) on the sell side
            self.assertAlmostEqual(float(y6["passive_bp"]), -1 * (99.0 / 100 - 1) * 1e4 + walk + fp.TAKER_BP,
                                   places=3)

    def test_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            base = fp.iso_ms("2026-11-21T00:31:00Z")
            recs = [{"lane": "R509", "run": "r", "day": "d", "action": "enter", "coin": "X", "symbol": "S",
                     "side": "buy", "late": "false", "snap_ms": base + i * 86_400_000, "h": 1, "filled": "true",
                     "passive_bp": "-5", "taker_bp": "20", "saving_bp": str(25 + (i % 3)), "eval_utc": ""}
                    for i in range(35)]
            fp._append("evaluations.csv", fp.EVAL_COLS, recs, out)
            self.assertEqual(fp.read(out, 1)["verdict"], "PASS")
            self.assertEqual(fp.read(out, 6)["verdict"], "RUNNING")


if __name__ == "__main__":
    unittest.main()
