"""scripts/run_llpstake.py (R447): the LLP-plus-hedged-LIT-stake book on a synthetic data layout, offline."""
import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_llpstake", ROOT / "scripts" / "run_llpstake.py")
ls = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ls)
D, H = ls.DAY, 3_600_000
T0 = ls.rx.ms("2026-03-01")


def write_csv(p, cols, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def layout(root, days=8, spot=None, perp=None, high=None, rate=0.0, llp_step=0.0003, skip_llp=(), skip_fund=()):
    """Bars from T0 - 1 day; LLP stamps at 20:00 on each day; `rate` an hour on each day's 24 hours."""
    spot = spot or [2.0] * (days + 1)
    perp = perp or list(spot)
    high = high or [x * 1.01 for x in perp]
    for name, closes, highs in (("spot", spot, spot), ("perp", perp, high)):
        write_csv(root / "lit" / f"{name}_candles_1d" / "all.csv", ["ts", "open", "high", "low", "close"],
                  [{"ts": T0 + (k - 1) * D, "open": c, "high": h, "low": c, "close": c}
                   for k, (c, h) in enumerate(zip(closes, highs))])
    write_csv(root / "lit" / "perp_funding" / "all.csv", ["ts", "rate"],
              [{"ts": T0 + k * D + j * H, "rate": rate} for k in range(days) if k not in skip_fund for j in range(24)])
    write_csv(root / "vaults" / "llp" / "share_prices" / "all.csv", ["ts", "share_price"],
              [{"ts": T0 + k * D + 20 * H, "share_price": (1 + llp_step) ** k} for k in range(-1, days)
               if k not in skip_llp])


class Book(unittest.TestCase):
    def test_flat_lit_price_earns_llp_stake_and_funding_on_the_whole_capital(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d), rate=0.00001)
            daily = ls.run(d, "2026-03-01", "2026-03-05")
            cap = 10 + 2.0 + 1.0 * 2.0
            self.assertEqual(len(daily), 5)
            for _, r in daily.iterrows():
                self.assertAlmostEqual(r.capital, cap)
                self.assertAlmostEqual(r.llp, 10 * 0.0003 / cap)
                self.assertAlmostEqual(r.stake, 2.0 * 0.06 / 365 / cap)
                self.assertAlmostEqual(r.funding, 2.0 * 24 * 0.00001 / cap)
                self.assertAlmostEqual(r.price, 0.0)
                self.assertAlmostEqual(r.net_1x, r.gross - (0.0040 * 2.0 + 0.0010 * 10) / 365 / cap)
                self.assertEqual((r.missing, r.forced), (0, 0))

    def test_the_short_cancels_the_stake_and_the_basis_is_kept(self):
        with tempfile.TemporaryDirectory() as d:
            spot = [2.0, 2.2, 1.8, 2.5, 2.5, 2.5]
            perp = [2.0, 2.21, 1.8, 2.5, 2.5, 2.5]
            layout(Path(d), days=5, spot=spot, perp=perp)
            daily = ls.run(d, "2026-03-01", "2026-03-03")
            self.assertAlmostEqual(daily.price.iloc[0] * daily.capital.iloc[0], 0.2 - 0.21)
            self.assertAlmostEqual(daily.price.iloc[1] * daily.capital.iloc[1], -0.4 + 0.41)
            self.assertAlmostEqual(daily.capital.iloc[1], 10 + 2.2 + 2.21)      # weights at the previous close
            self.assertAlmostEqual(daily.naked_1x.iloc[2] * (10 + 1.8),
                                   10 * 0.0003 + 1.8 * 0.06 / 365 + 0.7 - (0.0020 * 1.8 + 0.0010 * 10) / 365)

    def test_a_spike_liquidates_the_short_and_loses_its_margin(self):
        with tempfile.TemporaryDirectory() as d:
            perp = [2.0, 2.0, 3.0, 3.0]
            high = [2.02, 2.02, 2.0 * 2 / 1.2 + 0.01, 3.0]
            layout(Path(d), days=3, spot=list(perp), perp=perp, high=high)
            daily = ls.run(d, "2026-03-01", "2026-03-02")
            self.assertEqual(list(daily.forced), [0, 1])
            self.assertAlmostEqual(daily.price.iloc[1] * daily.capital.iloc[1], 1.0 - 2.0)

    def test_missing_inputs_are_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d), skip_llp=(2,), skip_fund=(3,))
            daily = ls.run(d, "2026-03-01", "2026-03-05")
            self.assertEqual(list(daily.missing), [0, 0, 1, 1, 0])
            self.assertAlmostEqual(daily.llp.iloc[2], 0.0)
            self.assertAlmostEqual(daily.llp.iloc[3] * daily.capital.iloc[3], 10 * (1.0003 ** 2 - 1))

    def test_last_day_is_the_last_one_every_input_covers(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d), days=6)
            self.assertEqual(ls.last_day(d), "2026-03-06")          # bars, stamps and full funding days to 03-06
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(ls.last_day(d))


class Reads(unittest.TestCase):
    def test_gate0_stops_only_below_zero(self):
        self.assertEqual(ls.decide_gate0({"1x": {"excess_ann": -0.001}}), "NULL (stop)")
        self.assertEqual(ls.decide_gate0({"1x": {"excess_ann": 0.0}}), "CONTINUE to gate 1")


class PreregAgreement(unittest.TestCase):
    def test_constants_match_the_prereg_text(self):
        text = (ROOT / "experiments" / "llpstake_v1" / "PREREG.md").read_text()
        self.assertEqual((ls.USDC_PER_LIT, ls.STAKE_APR, ls.MARGIN_K, ls.MAINT), (10.0, 0.06, 1.0, 0.20))
        for s in ("10 USDC in LLP", "6%/yr", "margin equal to its notional", "maintenance margin of 20%",
                  "40 bp of the stake's value", "10 bp of the LLP deposit", "4.0%/yr on capital",
                  "2026-01-15..2026-11-10", "(2027-02-08)", "(2027-05-09)"):
            self.assertIn(s, text)
        self.assertEqual((ls.COST_STAKE_RT, ls.COST_LLP_RT, ls.HURDLE_ANN), (0.0040, 0.0010, 0.04))
        self.assertEqual(ls.WINDOWS["gate0"], ("2026-01-15", "2026-11-10"))
        self.assertEqual(ls.LOOKS, ls.rx.LOOKS)


if __name__ == "__main__":
    unittest.main()
