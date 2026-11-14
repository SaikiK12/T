"""scripts/record_dex_vaults.py (M505): HLP snapshots and LLP share prices on fake API answers, offline."""
import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("record_dex_vaults", ROOT / "scripts" / "record_dex_vaults.py")
rv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rv)
T0 = 1_762_000_000_000


def fake_hl(body):
    assert body == {"type": "vaultDetails", "vaultAddress": rv.HLP}
    win = lambda n, step: {"accountValueHistory": [[T0 + k * step, str(100 + k)] for k in range(n)],  # noqa: E731
                           "pnlHistory": [[T0 + k * step, str(float(k))] for k in range(n)], "vlm": "0"}
    return {"name": "Hyperliquidity Provider (HLP)", "vaultAddress": rv.HLP, "leader": "0x1", "isClosed": False,
            "allowDeposits": True, "apr": 0.1,
            "portfolio": [["day", win(3, 1)], ["week", win(4, 2)], ["month", win(5, 3)], ["allTime", win(6, 4)],
                          ["perpWeek", win(2, 5)]]}


def fake_lighter(url):
    assert url.endswith(f"account?by=index&value={rv.LLP_INDEX}")
    s = 1_762_000_000
    return {"code": 200, "accounts": [{"name": "Lighter Liquidity Provider (LLP)", "pool_info": {
        "status": 0, "operator_fee": "0.0000", "total_shares": 10, "operator_shares": 0,
        "share_prices": [{"timestamp": s + k * 86400, "share_price": 1 + k / 1000} for k in range(3)],
        "daily_returns": [{"timestamp": s + k * 86400, "daily_return": 0.001} for k in range(1, 3)]}}]}


def read(p):
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


class Record(unittest.TestCase):
    def test_snapshot_keeps_three_windows_and_llp_merges(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            s = rv.record(out, now_ms=T0 + 10 ** 7, hl_post=fake_hl, lighter_get=fake_lighter)
            self.assertEqual(s["failed"], [])
            self.assertEqual(s["hlp_points"], 4 + 5 + 6)                 # week, month, allTime; day and perp* dropped
            rows = read(out / "hlp" / "snap" / f"{T0 + 10 ** 7}.csv")
            self.assertEqual({r["window"] for r in rows}, {"week", "month", "allTime"})
            self.assertEqual(rows[0].keys(), {"window", "ts", "account_value", "pnl"})
            self.assertEqual(s["llp_share_prices"], 3)
            sp = [r for p in (out / "llp" / "share_prices").glob("*.csv") for r in read(p)]
            self.assertTrue(all(int(r["ts"]) > 10 ** 11 for r in sp))      # seconds stored as ms
            self.assertEqual(json.loads((out / "llp" / "meta.json").read_text())["operator_fee"], "0.0000")
            s2 = rv.record(out, now_ms=T0 + 2 * 10 ** 7, hl_post=fake_hl, lighter_get=fake_lighter)
            self.assertEqual((s2["llp_share_prices"], s2["llp_daily_returns"]), (0, 0))   # idempotent merge
            self.assertEqual(len(list((out / "hlp" / "snap").glob("*.csv"))), 2)        # one snapshot per run

    def test_one_failure_does_not_stop_the_other(self):
        def boom(_):
            raise OSError("down")
        with tempfile.TemporaryDirectory() as d:
            s = rv.record(Path(d), now_ms=T0, hl_post=boom, lighter_get=fake_lighter)
            self.assertEqual(s["failed"], ["hlp"])
            self.assertEqual(s["llp_share_prices"], 3)


if __name__ == "__main__":
    unittest.main()
