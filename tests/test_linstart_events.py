"""scripts/linstart_events.py (R485): the linear-start threshold, event day, pure/with_cliff label, spacing and the
OKX symbol check, on synthetic DefiLlama protocol files."""
import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import linstart_events as le  # noqa: E402

DAY = le.DAY
MAX = 1_000_000_000.0


def ts(day, hour=5):
    return int(pd.Timestamp(day, tz="UTC").value // 1_000_000_000) + hour * 3600


def lin(cat, new, prev=0, kind="linear_start"):
    return {"recipient": "x", "category": cat, "unlockType": kind, "previousRatePerWeek": prev, "newRatePerWeek": new,
            "endTimestamp": 0}


def cliff(cat, amount):
    return {"recipient": "x", "category": cat, "unlockType": "cliff", "amount": amount}


def protocol(gecko, events):
    return {"gecko_id": gecko, "supplyMetrics": {"maxSupply": MAX},
            "metadata": {"unlockEvents": [{"timestamp": t, "cliffAllocations": c, "linearAllocations": l}
                                          for t, c, l in events]}}


def write_snapshot(d, protos, index):
    snap = Path(d) / "snap"
    (snap / "protocols").mkdir(parents=True)
    for slug, x in protos.items():
        (snap / "protocols" / f"{slug}.json.gz").write_bytes(gzip.compress(json.dumps(x).encode()))
    rows = [{"gecko_id": g, "maxSupply": MAX, "tokenPrice": [{"symbol": s, "price": p}]} for g, (s, p) in index.items()]
    (snap / "emissionsIndex.json.gz").write_bytes(gzip.compress(json.dumps({"data": rows}).encode()))
    inst = {"data": [{"instId": f"{s}-USDT-SWAP", "settleCcy": "USDT", "ctType": "linear", "state": "live",
                      "ruleType": "normal", "instCategory": "1", "listTime": "1600000000000"}
                     for s in ("AAA", "BBB", "CCC", "DDD")]}
    tick = {"data": [{"instId": "AAA-USDT-SWAP", "last": "1.0"}, {"instId": "BBB-USDT-SWAP", "last": "2.0"},
                     {"instId": "CCC-USDT-SWAP", "last": "50"}, {"instId": "DDD-USDT-SWAP", "last": "1.0"}]}
    (Path(d) / "inst.json").write_text(json.dumps(inst))
    (Path(d) / "tick.json").write_text(json.dumps(tick))
    return snap, Path(d) / "inst.json", Path(d) / "tick.json"


class TestLinearStartDays(unittest.TestCase):
    def test_sums_insider_and_private_sale_starts_only(self):
        x = protocol("a", [(ts("2024-03-01"), [], [lin("insiders", 1_500_000), lin("privateSale", 1_000_000),
                                                    lin("farming", 9e9), lin("insiders", 9e9, 0, "linear_rate_change")])])
        days = le.linear_start_days(x, MAX)
        self.assertEqual(list(days), [le.ms("2024-03-01")])
        inc, frac = days[le.ms("2024-03-01")]
        self.assertEqual(inc, 2_500_000)
        self.assertAlmostEqual(frac, 0.0025)

    def test_previous_rate_is_subtracted(self):
        x = protocol("a", [(ts("2024-03-01"), [], [lin("insiders", 3_000_000, prev=1_000_000)])])
        self.assertAlmostEqual(le.linear_start_days(x, MAX)[le.ms("2024-03-01")][1], 0.002)


class TestEvents(unittest.TestCase):
    def build(self, protos, index):
        with tempfile.TemporaryDirectory() as d:
            snap, inst, tick = write_snapshot(d, protos, index)
            smap, ev = le.build(snap, Path(d) / "out", inst, tick, "2026-11-13")
        return smap, ev

    def test_threshold_day_spacing_label_and_window(self):
        protos = {
            # AAA: crosses 0.25% on 2024-03-01 (event); 2024-03-20 is within 30 days (dropped); 2024-05-01 kept
            "aaa": protocol("a", [(ts("2024-03-01"), [], [lin("insiders", 2_600_000)]),
                                  (ts("2024-03-20"), [], [lin("insiders", 3_000_000)]),
                                  (ts("2024-05-01"), [], [lin("privateSale", 4_000_000)]),
                                  (ts("2024-05-15"), [cliff("insiders", 20_000_000)], [])]),
            # BBB: 0.24% only, no event
            "bbb": protocol("b", [(ts("2024-03-01"), [], [lin("insiders", 2_400_000)])]),
            # DDD: forward start
            "ddd": protocol("d", [(ts("2026-12-29"), [], [lin("insiders", 3_194_000)])]),
        }
        smap, ev = self.build(protos, {"a": ("AAA", 1.0), "b": ("BBB", 2.0), "d": ("DDD", 1.0)})
        self.assertEqual(list(ev.day), ["2024-03-01", "2024-05-01", "2026-12-29"])
        self.assertEqual(list(ev.inst_id), ["AAA-USDT-SWAP", "AAA-USDT-SWAP", "DDD-USDT-SWAP"])
        # 2024-03-01: the 2% cliff on 2024-05-15 is 75 days later -> pure; 2024-05-01: cliff at D+14 -> with_cliff
        self.assertEqual(list(ev.label), ["pure", "with_cliff", "pure"])
        self.assertAlmostEqual(ev.cliff_frac_max.iloc[1], 0.02)
        self.assertEqual(list(ev.window), ["archive", "archive", "forward"])

    def test_cliff_window_edges(self):
        cl = {le.ms("2024-01-01"): (1, 0.01), le.ms("2024-06-01"): (1, 0.5)}
        d = le.ms("2024-01-31")                                # cliff at D-30: inside
        self.assertEqual(le.label_cliff(cl, d), 0.01)
        self.assertEqual(le.label_cliff(cl, d + DAY), 0.0)     # D-31: outside
        d2 = le.ms("2024-05-11")                               # cliff at D+21: inside
        self.assertEqual(le.label_cliff(cl, d2), 0.5)
        self.assertEqual(le.label_cliff(cl, d2 - DAY), 0.0)    # D+22: outside
        self.assertEqual(le.label_cliff({d: (1, 0.009)}, d), 0.0)   # under 1%: not an R265 cliff

    def test_symbol_check_and_exclusion(self):
        protos = {"aaa": protocol("a", []), "ccc": protocol("c", []), "eth": protocol("e", [])}
        smap, _ = self.build(protos, {"a": ("AAA", 1.0), "c": ("CCC", 1.0), "e": ("ETH", 3000.0)})
        chk = dict(zip(smap.slug, smap.check))
        self.assertEqual(chk, {"aaa": "verified", "ccc": "mismatch", "eth": "excluded"})


if __name__ == "__main__":
    unittest.main()
