"""scripts/record_hl_vaults.py (M507): the vault list and per-vault allTime history on fake answers, offline."""
import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("record_hl_vaults", ROOT / "scripts" / "record_hl_vaults.py")
rv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rv)
T0 = 1_700_000_000_000
A, B, C, K = "0x" + "a" * 40, "0x" + "b" * 40, "0x" + "c" * 40, "0x" + "d" * 40


def summary(a, closed, rel="normal"):
    return {"apr": 9.9, "pnls": [["allTime", ["1"]]],
            "summary": {"vaultAddress": a, "name": a[-3:], "leader": "0xL", "createTimeMillis": T0, "isClosed": closed,
                        "relationship": {"type": rel}, "tvl": "1"}}


def details(av):
    w = {"accountValueHistory": [[T0 + k, str(av * (1 + k))] for k in range(3)],
         "pnlHistory": [[T0 + k, str(float(k))] for k in range(3)]}
    return {"isClosed": False, "allowDeposits": True, "leaderCommission": 0.1, "leaderFraction": 0.2,
            "portfolio": [["day", w], ["allTime", w], ["perpAllTime", w]]}


def read(p):
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


class Record(unittest.TestCase):
    def test_list_history_threshold_and_skips(self):
        calls = []

        def post(body):
            calls.append(body["vaultAddress"])
            return {**details(50_000 if body["vaultAddress"] == A else 100), "isClosed": body["vaultAddress"] == C}

        stats = [summary(A, False), summary(B, False), summary(C, True), summary(K, False, "child")]
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            s = rv.record(out, now_ms=T0 + 10, stats_get=lambda url: stats, hl_post=post, pause=0)
            self.assertEqual((s["vaults"], s["fetched"], s["kept"], s["skipped_child"]), (4, 3, 1, 1))
            idx = read(out / "index.csv")
            self.assertEqual(len(idx), 4)
            self.assertNotIn("apr", idx[0])                                   # summaries of returns are not kept
            h = read(rv.hist_path(out, A))
            self.assertEqual([r["pnl"] for r in h], ["0.0", "1.0", "2.0"])  # allTime only, merged by ts
            self.assertFalse(rv.hist_path(out, B).exists())                   # peak below the threshold
            calls.clear()
            s2 = rv.record(out, now_ms=T0 + 20, stats_get=lambda url: stats, hl_post=post, pause=0)
            self.assertEqual(s2["skipped_closed"], 1)                         # C closed and already fetched closed
            self.assertNotIn(C, calls)
            self.assertEqual(s2["rows_changed"], 0)
            self.assertEqual(read(out / "index.csv")[0]["first_seen_ms"], str(T0 + 10))

    def test_unfetched_vaults_go_first_and_the_budget_stops_the_run(self):
        stats = [summary(A, False), summary(B, False)]
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            rv.record(out, now_ms=T0, stats_get=lambda url: stats, hl_post=lambda b: details(50_000), pause=0, limit=1)
            order = []
            rv.record(out, now_ms=T0 + 1, stats_get=lambda url: stats,
                      hl_post=lambda b: order.append(b["vaultAddress"]) or details(50_000), pause=0)
            self.assertEqual(order, [B, A])
            s = rv.record(out, now_ms=T0 + 2, stats_get=lambda url: stats, hl_post=lambda b: details(1), pause=0,
                          budget_s=-1)
            self.assertEqual((s["fetched"], s["left"]), (0, 2))


if __name__ == "__main__":
    unittest.main()
