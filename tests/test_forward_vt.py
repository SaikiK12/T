"""R225 sizing tests use temporary archives and synthetic daily returns only."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from scripts import forward_vt as vt


class ForwardVtTests(unittest.TestCase):
    def archive(self):
        i = np.arange(2099, dtype=float)
        return {"A_C0": 0.001 + 0.002 * np.sin(i * 0.17),
                "B_C0": 0.0015 + 0.001 * np.cos(i * 0.11),
                "X2": 0.0012 + 0.003 * np.sin(i * 0.23)}

    def source(self, n=18):
        days = pd.date_range("2026-10-01", periods=n, freq="D").strftime("%Y-%m-%d")
        rows = []
        for book, base in (("A", 0.001), ("B", -0.0001), ("X2", 0.0015)):
            net = base + np.sin(np.arange(n) * 1.7) * 0.0004
            for idx, day in enumerate(days):
                rows.append({"day": day, "book": book,
                             "kind": "ontime" if day >= "2026-10-20" else "replay",
                             "net": net[idx], "net_2x": 2 * net[idx], "net_3x": 3 * net[idx],
                             "gross_exposure": 0.1 + idx / 1000})
        return pd.DataFrame(rows)

    def test_archive_is_checked_against_committed_r217_summary(self):
        archive = self.archive()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "daily.npz"
            summary_path = Path(d) / "results.csv"
            np.savez_compressed(path, **archive)
            rows = []
            for key, values in archive.items():
                for window, stat in vt.archive_summary(values).items():
                    rows.append({"run": key, "cmult": 1.0, "window": window, **stat})
            pd.DataFrame(rows).to_csv(summary_path, index=False)
            loaded, provenance = vt.load_archive(path, summary_path)
            self.assertEqual(provenance["days"], 2099)
            self.assertEqual(set(loaded), set(vt.ARCHIVE_KEYS))
            self.assertEqual(len(provenance["sha256"]), 64)

    def test_archive_rejects_wrong_length_nan_and_missing_control(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "daily.npz"
            np.savez(path, **{k: np.zeros(2098) for k in vt.ARCHIVE_KEYS})
            with self.assertRaisesRegex(ValueError, "2099"):
                vt.load_archive(path, Path(d) / "absent.csv")
            arrays = self.archive()
            arrays["B_C0"][10] = np.nan
            np.savez(path, **arrays)
            with self.assertRaisesRegex(ValueError, "non-finite"):
                vt.load_archive(path, Path(d) / "absent.csv")
            arrays = self.archive()
            del arrays["X2"]
            np.savez(path, **arrays)
            with self.assertRaisesRegex(ValueError, "missing arrays"):
                vt.load_archive(path, Path(d) / "absent.csv")

    def test_missing_seed_fails_before_forward_journals_are_touched(self):
        path = vt.J / "days.csv"
        before = path.read_bytes()
        with mock.patch.object(vt, "ARCHIVE", Path("/definitely/missing/daily.npz")):
            with self.assertRaisesRegex(SystemExit, "owner's exact artifact"):
                vt.main()
        self.assertEqual(path.read_bytes(), before)

    def test_source_validation_rejects_duplicates_gaps_bad_dates_kind_and_nan(self):
        source = self.source()
        a = source[source.book == "A"].copy()
        self.assertEqual(len(vt.validate_tickets(source, "A")), 18)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            vt.validate_tickets(pd.concat([source, a.iloc[[0]]], ignore_index=True), "A")
        with self.assertRaisesRegex(ValueError, "missing calendar"):
            vt.validate_tickets(source[source.day != "2026-10-03"], "A")
        bad_kind = source.copy()
        bad_kind.loc[bad_kind.book == "A", "kind"] = "ontime"
        with self.assertRaisesRegex(ValueError, "kind disagrees"):
            vt.validate_tickets(bad_kind, "A")
        bad_value = source.copy()
        bad_value.loc[(bad_value.book == "A") & (bad_value.day == "2026-10-02"), "net"] = np.inf
        with self.assertRaisesRegex(ValueError, "non-finite"):
            vt.validate_tickets(bad_value, "A")

    def test_r1_is_causal_and_future_extensions_preserve_prior_multipliers(self):
        source = self.source()
        archive = self.archive()
        first, _ = vt.calculate_book(archive, source, "A", "A_C0")
        extended = pd.concat([source, self.source(20).query("day >= '2026-10-19'")], ignore_index=True)
        # The extension contains the two new days for each book and no duplicate day.
        second, _ = vt.calculate_book(archive, extended, "A", "A_C0")
        np.testing.assert_allclose(first.m, second.m.iloc[:len(first)], rtol=0, atol=0)
        np.testing.assert_allclose(first.net_vt, second.net_vt.iloc[:len(first)], rtol=0, atol=0)

    def test_saved_history_must_match_and_backfills_are_rejected(self):
        source = self.source(5)
        archive = self.archive()
        calculated, _ = vt.calculate_book(archive, source, "A", "A_C0")
        vt.verify_saved_journal(calculated.iloc[:3].copy(), calculated)
        changed_source = source.copy()
        changed_source.loc[(changed_source.book == "A") & (changed_source.day == "2026-10-02"), "net"] *= 2
        changed, _ = vt.calculate_book(archive, changed_source, "A", "A_C0")
        with self.assertRaisesRegex(ValueError, "changed"):
            vt.verify_saved_journal(calculated.iloc[:3].copy(), changed)
        with self.assertRaisesRegex(ValueError, "backfill"):
            vt.verify_saved_journal(calculated.iloc[[0, 2]].copy(), calculated)


if __name__ == "__main__":
    unittest.main()
