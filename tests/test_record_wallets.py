import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts import record_wallets as rw

HOUR = 3600


def responses(gate_dep=True, kucoin_fail=False):
    """One coin per venue in each venue's own shape; gate_dep switches Gate's ETH-chain deposits."""
    return {
        "bithumb": {"status": "0000", "data": {"BTC": {"withdrawal_status": 1, "deposit_status": 0}}},
        "gate": [{"currency": "usdt", "deposit_disabled": False, "withdraw_disabled": False,
                  "chains": [{"name": "ETH", "deposit_disabled": not gate_dep, "withdraw_disabled": False},
                             {"name": "TRX", "deposit_disabled": False, "withdraw_disabled": True}]}],
        "kucoin": None if kucoin_fail else {"code": "200000", "data": [
            {"currency": "SOL", "chains": [{"chainName": "SOL", "isDepositEnabled": True, "isWithdrawEnabled": False}]},
            {"currency": "NOCHAIN", "chains": None}]},
        "htx": {"code": 200, "data": [{"currency": "eth", "chains": [
            {"chain": "eth", "displayName": "ERC20", "depositStatus": "allowed", "withdrawStatus": "prohibited"}]}]},
        "bitget": {"code": "00000", "data": [{"coin": "BTC", "chains": [
            {"chain": "BTC", "rechargeable": "true", "withdrawable": "false"}]}]},
    }


def getter(resp):
    by_url = {url: name for name, (url, _) in rw.VENUES.items()}

    def get(url):
        r = resp[by_url[url]]
        if r is None:
            raise OSError("down")
        return r
    return get


class RecordWalletsTest(unittest.TestCase):
    def test_each_venue_is_read_into_one_row_per_coin_and_chain(self):
        cur, failed = rw.snapshot(getter(responses()))
        self.assertEqual(failed, [])
        got = {tuple(r) for r in cur[rw.COLS].itertuples(index=False)}
        self.assertEqual(got, {
            ("bithumb", "BTC", "", False, True),
            ("gate", "USDT", "ETH", True, True),
            ("gate", "USDT", "TRX", True, False),
            ("kucoin", "SOL", "SOL", True, False),          # a coin without chains gives no row
            ("htx", "ETH", "ERC20", True, False),
            ("bitget", "BTC", "BTC", True, False),
        })

    def test_changes_are_new_changed_or_gone_and_a_failed_venue_is_not_compared(self):
        prev, _ = rw.snapshot(getter(responses()))
        prev = pd.concat([prev, pd.DataFrame([("gate", "OLD", "ETH", True, True)], columns=rw.COLS)])
        cur, failed = rw.snapshot(getter(responses(gate_dep=False, kucoin_fail=True)))
        self.assertEqual(len(failed), 1)
        ch = rw.changes(prev, cur, 1)
        kinds = {(r.coin, r.chain): r.kind for r in ch.itertuples()}
        self.assertEqual(kinds, {("OLD", "ETH"): "gone", ("USDT", "ETH"): "change"})   # no kucoin "gone" rows
        row = ch[ch.coin == "USDT"].iloc[0]
        self.assertEqual((row.deposit, row.prev_deposit), (False, True))

    def test_run_writes_a_day_snapshot_and_hourly_changes_once_and_keeps_a_failed_venue(self):
        with tempfile.TemporaryDirectory() as d:
            out, state = Path(d) / "recorders" / "wallets", Path(d) / "logs" / "state.parquet"
            t0 = 1792540800                                   # 2026-10-21 00:00 UTC
            first = rw.run(t0, out, state, getter(responses()))
            day = out / "2026-10-21"
            self.assertEqual(first, day / "00.parquet")
            self.assertEqual(len(pd.read_parquet(first)), 0)  # nothing to compare against yet
            self.assertEqual(len(pd.read_parquet(day / "full.parquet")), 6)
            self.assertIsNone(rw.run(t0 + 60, out, state, getter(responses(gate_dep=False))))   # same hour
            second = rw.run(t0 + HOUR, out, state, getter(responses(gate_dep=False, kucoin_fail=True)))
            ch = pd.read_parquet(second)
            self.assertEqual(list(ch.coin), ["USDT"])
            self.assertEqual(list(ch.kind), ["change"])
            kept = pd.read_parquet(state)
            self.assertIn("kucoin", set(kept.venue))           # its last state survives the failed hour
            self.assertFalse(kept[(kept.venue == "gate") & (kept.chain == "ETH")].deposit.iloc[0])
            self.assertFalse(any(p.name.endswith(".part") for p in out.rglob("*")))


if __name__ == "__main__":
    unittest.main()
