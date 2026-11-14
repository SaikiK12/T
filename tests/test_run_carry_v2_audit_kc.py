"""R438 runner: R437's audit over R279's two KuCoin books, on synthetic inputs (no archive read)."""
import tomllib
import unittest
from pathlib import Path

from scripts import run_carry_v2_audit as base
from scripts import run_carry_v2_audit_kc as r

ROOT = Path(__file__).resolve().parent.parent


class KcAuditTests(unittest.TestCase):
    def spec(self):
        return tomllib.loads((ROOT / "experiments" / "xfund_kd_v1" / "spec.toml").read_text())

    def test_runs_only_this_lanes_books_and_restores_r437s(self):
        u1, u2 = base.synthetic(self.spec(), nd=200, n=6)
        before = list(base.BOOKS)
        out, daily, trades = r.audit(u1, u2, {**self.spec(), "start": "2021-01-01", "recent_from": "2021-04-01"},
                                     log=lambda m: None)
        self.assertEqual([x["book"] for x in out], ["gate+kucoin L14d th5% K20", "binance+kucoin L14d th5% K20"])
        self.assertEqual([x["forward"] for x in out], ["R279 A", "R279 B"])
        self.assertEqual(base.BOOKS, before)
        for x in out:
            want = (x["v2_nw_t_1x"] >= base.T_MIN and x["v2_mean_2x"] > 0 and x["v2_half1_bp"] > 0
                    and x["v2_half2_bp"] > 0)
            self.assertEqual(x["survives"], bool(want))

    def test_books_are_r277s_frozen_rule(self):
        spec = self.spec()
        for s, l, th, k, _ in r.BOOKS:
            self.assertIn(s.split("+"), spec["sets"])
            self.assertEqual((l, th, k), (spec["lookbacks"][0], spec["thresholds"][0], spec["slots"][0]))

    def test_plumbing_reads_no_v2_return(self):
        u1, u2 = base.synthetic(self.spec(), nd=120, n=4)
        out, daily, _ = r.audit(u1, u2, {**self.spec(), "start": "2021-01-01", "recent_from": "2021-03-01"},
                                plumbing=True, log=lambda m: None)
        self.assertFalse(any(k.startswith("v2_ann") or k == "survives" for x in out for k in x))
        self.assertEqual(daily, [])


if __name__ == "__main__":
    unittest.main()
