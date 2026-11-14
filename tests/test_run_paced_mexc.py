"""scripts/run_paced_mexc.py: spacing and 510 retries of MEXC's public client, offline."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_paced_mexc", ROOT / "scripts" / "run_paced_mexc.py")
pm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pm)
MexcError = pm.mexc.MexcError
LIMIT = "funding_rate/history: 510 Endpoint rate limit exceeded. Resource: /api/v1/contract/funding_rate/history"


class Clock:
    def __init__(self):
        self.t, self.slept = 100.0, []

    def sleep(self, s):
        self.slept.append(s)
        self.t += s

    def now(self):
        return self.t


class Paced(unittest.TestCase):
    def test_retries_a_510_then_returns_the_same_value(self):
        c, calls = Clock(), []

        def get(path, params=None):
            calls.append(path)
            if len(calls) < 3:
                raise MexcError(LIMIT)
            return {"path": path, "params": params}

        g = pm.paced(get, gap=0.25, waits=(5, 15, 45), sleep=c.sleep, clock=c.now)
        self.assertEqual(g("kline/BTC_USDT", {"a": 1}), {"path": "kline/BTC_USDT", "params": {"a": 1}})
        self.assertEqual(len(calls), 3)
        self.assertEqual([s for s in c.slept if s >= 1], [5, 15])

    def test_other_errors_and_the_last_510_are_raised(self):
        c = Clock()

        def bad(path):
            raise MexcError("detail: 1002 Contract not exist")

        with self.assertRaises(MexcError):
            pm.paced(bad, sleep=c.sleep, clock=c.now)("detail")
        self.assertEqual([s for s in c.slept if s >= 1], [])

        def limited(path):
            raise MexcError(LIMIT)

        with self.assertRaises(MexcError):
            pm.paced(limited, waits=(5, 15, 45), sleep=c.sleep, clock=c.now)("x")
        self.assertEqual([s for s in c.slept if s >= 1], [5, 15, 45])

    def test_requests_are_spaced(self):
        c, stamps = Clock(), []
        g = pm.paced(lambda p: stamps.append(c.now()), gap=0.25, sleep=c.sleep, clock=c.now)
        for _ in range(4):
            g("x")
        self.assertTrue(all(b - a >= 0.25 - 1e-12 for a, b in zip(stamps, stamps[1:])))

    def test_rate_limit_text(self):
        self.assertTrue(pm.is_rate_limited(MexcError(LIMIT)))
        self.assertFalse(pm.is_rate_limited(MexcError("kline/X: 1510 something")))


if __name__ == "__main__":
    unittest.main()
