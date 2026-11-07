import unittest

import numpy as np
import pandas as pd

from lab import coverage, daily


def panel_columns():
    """lab/daily.py's column table, with {v} and {k} expanded to every venue."""
    out = []
    for name, *_ in daily.COLUMNS:
        if "{v}" in name:
            out += [name.format(v=v) for v in daily.VENUES]
        elif "{k}" in name:
            out += [name.format(k=k) for k in daily.KOREAN]
        else:
            out.append(name)
    return out


class LabelTest(unittest.TestCase):
    def test_every_survivor_venue_column_is_flagged(self):
        cols = panel_columns()
        bad = coverage.survivor_columns(cols)
        for v in ("kucoin", "kraken", "mexc", "hyperliquid"):
            self.assertIn(f"{v}_gap", bad)
            self.assertIn(f"{v}_fund_gap", bad)
        for c in ("mexc_premium", "upbit_rel", "bithumb_rel", "upbit_qvol", "n_venues"):
            self.assertIn(c, bad)
        for c in ("close", "fund", "oi_usd", "basis", "gate_gap", "gate_fund_gap", "dydx_fund", "rank_qvol30",
                  "age_days", "mcap"):
            self.assertNotIn(c, bad)
        self.assertEqual(coverage.clean_columns(cols) + bad, [c for c in cols if c not in bad] + bad)
        self.assertEqual(set(coverage.SURVIVOR_VENUES) | {"gate", "dydx"},
                         set(daily.VENUES) | set(daily.KOREAN))


class CoverageTest(unittest.TestCase):
    def test_a_survivor_only_column_shows_the_gap(self):
        days = pd.date_range("2022-01-01", "2023-12-31", freq="D")
        rows = []
        for i in range(6):
            stop = days[-1] if i % 3 else days[200 + 100 * i]           # P00 and P03 stop trading
            for d in days[days <= stop]:
                rows.append({"day": d, "perp": f"P{i}", "close": 1.0, "gate_gap": 0.0,
                             "kucoin_gap": 0.0 if i % 3 else np.nan})
        df = pd.DataFrame(rows)
        out = coverage.coverage_by_survival(df, ["gate_gap", "kucoin_gap"])
        self.assertEqual(out["gate_gap"][2022], (1.0, 1.0))
        self.assertEqual(out["kucoin_gap"][2022], (1.0, 0.0))
        close = df.pivot(index="day", columns="perp", values="close")
        self.assertEqual(coverage.dead_perps(close), {"P0", "P3"})


if __name__ == "__main__":
    unittest.main()
