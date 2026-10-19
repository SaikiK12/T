import unittest

import pandas as pd

from lab import copylead


def accounts(rows):
    return pd.DataFrame(rows, columns=["hour_utc", "address", "account", "time_ms"])


def positions(rows):
    return pd.DataFrame(rows, columns=["hour_utc", "address", "account", "coin", "szi", "time_ms"])


def ms(value):
    return pd.Timestamp(value).value // 1_000_000


class StrictSnapshotTests(unittest.TestCase):
    expected = (("a", "a"), ("b", "b"))

    def test_exact_snapshot_is_available(self):
        a = accounts([
            ("2026-01-01T10:00:00Z", "A", "A", ms("2026-01-01T10:00:10Z")),
            ("2026-01-01T10:00:00Z", "B", "B", ms("2026-01-01T10:00:10Z")),
        ])
        p = positions([
            ("2026-01-01T10:00:00Z", "A", "A", "BTC", 1.0, ms("2026-01-01T10:00:10Z")),
            ("2026-01-01T10:00:00Z", "B", "B", "ETH", -2.0, ms("2026-01-01T10:00:10Z")),
        ])
        out = copylead.strict_rebuild(p, "2026-01-01T10:00:00Z", accounts=a,
                                      expected_accounts=self.expected,
                                      cutoff_ms="2026-01-01T10:01:00Z")
        self.assertTrue(out.availability.available)
        self.assertEqual(out.availability.reason, "ok")
        self.assertEqual(set(out.positions.coin), {"BTC", "ETH"})
        self.assertTrue(out.positions.state_fresh.all())
        self.assertFalse(out.positions.state_stale.any())

    def test_missing_hour_is_stale_and_excludes_future_state(self):
        a = accounts([
            ("2026-01-01T10:00:00Z", "A", "A", ms("2026-01-01T10:00:10Z")),
            ("2026-01-01T12:00:00Z", "A", "A", ms("2026-01-01T12:00:10Z")),
        ])
        p = positions([
            ("2026-01-01T10:00:00Z", "A", "A", "BTC", 1.0, ms("2026-01-01T10:00:10Z")),
            ("2026-01-01T12:00:00Z", "A", "A", "BTC", 2.0, ms("2026-01-01T12:00:10Z")),
        ])
        out = copylead.strict_rebuild(p, "2026-01-01T11:00:00Z", accounts=a,
                                      expected_accounts=(("a", "a"),))
        self.assertFalse(out.availability.available)
        self.assertEqual(out.availability.reason, "missing_hour")
        self.assertEqual(out.availability.missing_accounts, (("a", "a"),))
        self.assertEqual(float(out.positions.szi.iloc[0]), 1.0)
        self.assertTrue(bool(out.positions.state_stale.iloc[0]))
        self.assertEqual(out.availability.future_position_rows, 1)

    def test_late_server_time_requires_explicit_later_cutoff(self):
        late = ms("2026-01-01T10:07:00Z")
        a = accounts([("2026-01-01T10:00:00Z", "A", "A", late)])
        p = positions([("2026-01-01T10:00:00Z", "A", "A", "BTC", 1.0, late)])
        early = copylead.strict_rebuild(p, "2026-01-01T10:00:00Z", accounts=a,
                                        expected_accounts=(("a", "a"),))
        self.assertFalse(early.availability.available)
        self.assertEqual(early.availability.reason, "late_server_time")
        self.assertEqual(len(early.positions), 0)
        on_time = copylead.strict_rebuild(p, "2026-01-01T10:00:00Z", accounts=a,
                                          expected_accounts=(("a", "a"),), cutoff_ms=late)
        self.assertTrue(on_time.availability.available)
        self.assertEqual(float(on_time.positions.szi.iloc[0]), 1.0)

    def test_account_change_and_close_use_current_account_timestamp(self):
        a = accounts([
            ("2026-01-01T10:00:00Z", "A", "A", ms("2026-01-01T10:00:01Z")),
            ("2026-01-01T10:00:00Z", "B", "B", ms("2026-01-01T10:00:01Z")),
            ("2026-01-01T11:00:00Z", "A", "A", ms("2026-01-01T11:00:01Z")),
            ("2026-01-01T11:00:00Z", "B", "B", ms("2026-01-01T11:00:01Z")),
        ])
        p = positions([
            ("2026-01-01T10:00:00Z", "A", "A", "BTC", 1.0, ms("2026-01-01T10:00:01Z")),
            ("2026-01-01T10:00:00Z", "B", "B", "ETH", -1.0, ms("2026-01-01T10:00:01Z")),
            ("2026-01-01T11:00:00Z", "A", "A", "BTC", 2.0, ms("2026-01-01T11:00:01Z")),
            ("2026-01-01T11:00:00Z", "B", "B", "ETH", 0.0, float("nan")),
        ])
        out = copylead.strict_rebuild(p, "2026-01-01T11:00:00Z", accounts=a,
                                      expected_accounts=self.expected,
                                      cutoff_ms="2026-01-01T11:01:00Z")
        self.assertTrue(out.availability.available)
        self.assertEqual(out.positions[["account", "coin", "szi"]].to_records(index=False).tolist(),
                         [("a", "BTC", 2.0)])
        self.assertTrue(out.positions.state_fresh.all())


if __name__ == "__main__":
    unittest.main()
