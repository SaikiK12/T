"""R439 runner on a synthetic five-venue universe (no archive read)."""
import tomllib
import unittest
from pathlib import Path

from scripts import run_carry5 as r
from scripts import run_carry_v2_audit as base

ROOT = Path(__file__).resolve().parent.parent


class Carry5Tests(unittest.TestCase):
    def spec(self):
        return tomllib.loads((ROOT / "experiments" / "carry5_v1" / "spec.toml").read_text())

    def test_book_is_r275s_all_four_rule_plus_kucoin(self):
        self.assertEqual(r.REF4[1:], r.BOOK5[1:])
        self.assertEqual(set(r.BOOK5[0].split("+")), set(r.REF4[0].split("+")) | {"kucoin"})
        self.assertEqual([v["name"] for v in self.spec()["venues"]], ["binance", "gate", "hyperliquid", "mexc", "kucoin"])

    def test_dry_run_decision_and_pairing(self):
        u1, u2 = base.synthetic(self.spec(), nd=240, n=8)
        out, daily, trades = r.run(u1, u2, {**self.spec(), "start": "2021-01-01", "recent_from": "2021-05-01"},
                                   log=lambda m: None)
        b5 = out[0]
        want = b5["nw_t_1x"] >= r.T_MIN and b5["mean_2x"] > 0 and b5["half1_bp"] > 0 and b5["half2_bp"] > 0
        self.assertEqual(b5["survives"], bool(want))
        self.assertIn("paired_vs_ref4", b5)
        self.assertEqual({d[0] for d in daily}, {"book5", "ref4"})

    def test_plumbing_reads_no_return(self):
        u1, u2 = base.synthetic(self.spec(), nd=120, n=4)
        out, daily, trades = r.run(u1, u2, {**self.spec(), "start": "2021-01-01", "recent_from": "2021-03-01"},
                                   plumbing=True, log=lambda m: None)
        self.assertEqual(daily, [])
        self.assertFalse(any(k.startswith("ann") or k == "survives" for k in out))


if __name__ == "__main__":
    unittest.main()
