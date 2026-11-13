"""carryhurdle_v1 (R483) follow-up tests from review v1: the runner decides on the frozen cell (engine v2, cost 2x,
benchmark sUSDe, full window) and clips the 2025+ and 2025-04-09+ sub-windows and the 2026-09-30 end correctly.

tests/test_carryhurdle.py is a frozen PREREG input, so these tests live in a separate file. Every non-decision cell
here is built to give a different lane verdict or different calls, so a runner reading the wrong cell fails."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_carryhurdle as fc  # noqa: E402
import run_carryhurdle as rc  # noqa: E402
from lab import prereg  # noqa: E402

POOL_S = "00000000-0000-0000-0000-00000000000a"
POOL_A = "00000000-0000-0000-0000-00000000000b"
SUSDE_APY, AAVE_LO, AAVE_HI = 20.0, 3.65, 7.30
FIRST, SPLIT, END = pd.Timestamp("2024-02-17"), pd.Timestamp("2025-04-09"), pd.Timestamp(rc.END)


def chart(dates, apys):
    return {"status": "success", "data": [
        {"timestamp": f"{d:%Y-%m-%d}T23:01:19.228Z", "tvlUsd": 1.0, "apy": a, "apyBase": a, "apyReward": None,
         "il7d": None, "apyBase7d": None, "pricePerShare": None} for d, a in zip(dates, apys)]}


class Cells(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        t = cls.root = Path(cls.tmp.name)
        # charts run past END so the 2026-09-30 clip is exercised; the Aave row dated 2025-04-08 (serving 04-09)
        # steps from 3.65 to 7.30 %/yr, so a sub-window that is not clipped shows the wrong benchmark mean
        cdates = pd.date_range("2024-02-16", "2026-10-05", freq="D")
        aave = [AAVE_LO if d < SPLIT - pd.Timedelta(days=1) else AAVE_HI for d in cdates]
        src = t / "sealed"
        src.mkdir()
        for pool, apys in ((POOL_S, [SUSDE_APY] * len(cdates)), (POOL_A, aave)):
            (src / f"{pool}.json").write_text(json.dumps(chart(cdates, apys)))
            (src / f"{pool}.hdr").write_text("HTTP/2 200\n")
        (src / "receipt.txt").write_text("synthetic\n")
        sha = {p: hashlib.sha256((src / f"{p}.json").read_bytes()).hexdigest() for p in (POOL_S, POOL_A)}
        size = {p: (src / f"{p}.json").stat().st_size for p in (POOL_S, POOL_A)}
        intake = t / "intake.md"
        intake.write_text("\n".join(
            f"| x | https://yields.llama.fi/chart/{p} | 200 | {size[p]:,} | {sha[p]} |" for p in (POOL_S, POOL_A)))
        pools = {POOL_S: ("susde", "weekly", sha[POOL_S]), POOL_A: ("aave_usdc", "apr", sha[POOL_A])}

        # books: net = sUSDe daily rate + excess + alternating +-0.1 bp noise
        r_s = float(rc.daily_rate([SUSDE_APY], "weekly")[0])
        bdates = pd.date_range("2024-02-01", "2026-10-05", freq="D")
        noise = np.where(np.arange(len(bdates)) % 2 == 0, 1e-5, -1e-5)
        window = (bdates >= FIRST) & (bdates <= END)
        n_a = int((window & (bdates < SPLIT)).sum())
        n_b = int((window & (bdates >= SPLIT)).sum())
        a = 2e-4
        # zero-mean step over the full window: below sUSDe before 2025-04-09, above after (TIES full, BEATS 2025-04-09+)
        step = np.where(bdates < SPLIT, -a, a * n_a / n_b)
        lose = r_s - 5e-4 + noise
        rows = []
        for i, b in enumerate(rc.DECIDERS):
            decide = r_s + (5e-4 if i < 3 else step) + noise
            for eng in ("v1", "v2"):
                # the frozen cell is spelled out, not read from rc, so a changed constant cannot move the data
                nets = {c: (decide if (eng, c) == ("v2", 2) else lose) for c in (1, 2, 3)}
                for j, d in enumerate(bdates):
                    rows.append({"book": b, "engine": eng, "date": f"{d:%Y-%m-%d}",
                                 **{f"net_{c}x": nets[c][j] for c in (1, 2, 3)}})
        books = t / "daily.csv"
        cls.frame = pd.DataFrame(rows)
        cls.frame.to_csv(books, index=False)
        lane = t / "lane"
        lane.mkdir()
        raw = lane / "raw"
        fc.run(src, raw, intake)
        (lane / "PREREG.md").write_text(f"# fake\n\n```inputs\n{prereg.sha256_file(books)} daily.csv\n```\n")
        prereg.freeze(lane / "PREREG.md")
        cls.summ, cls.tab = rc.run(lane, raw, [books], pools, t)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def cell(self, book, engine="v2", cost=2, bench="susde", window="full"):
        t = self.tab
        got = t[(t.book == book) & (t.engine == engine) & (t.cost == cost) & (t.bench == bench) & (t.window == window)]
        self.assertEqual(len(got), 1)
        return got.iloc[0]

    def calls(self, **kw):
        return [self.cell(b, **kw)["call"] for b in rc.DECIDERS]

    def test_decides_on_v2_2x_susde_full(self):
        self.assertEqual([self.summ["deciders"][b]["call"] for b in rc.DECIDERS], ["BEATS"] * 3 + ["TIES"] * 3)
        self.assertEqual(self.summ["verdict"], "PASS")
        self.assertEqual(self.summ["registry_verdict"], "CONFIRMED")

    def test_other_cells_would_decide_differently(self):
        # each wrong engine or cost gives six LOSES (NULL); the right one gives PASS
        for eng in ("v1", "v2"):
            for c in (1, 2, 3):
                if (eng, c) == ("v2", 2):
                    continue
                calls = self.calls(engine=eng, cost=c)
                self.assertEqual(calls, ["LOSES"] * 6, (eng, c))
                self.assertEqual(rc.lane_verdict(calls), "NULL")
        # the wrong benchmark or a sub-window gives different calls for books 3-5
        self.assertEqual(self.calls(bench="aave_usdc")[3:], ["BEATS"] * 3)
        self.assertEqual(self.calls(window="2025-04-09+")[3:], ["BEATS"] * 3)

    def test_subwindow_and_end_clipping(self):
        b = next(iter(rc.DECIDERS))
        f = self.frame[(self.frame.book == b) & (self.frame.engine == "v2")].copy()
        f["date"] = pd.to_datetime(f["date"])
        for win, start in (("full", FIRST), ("2025+", pd.Timestamp("2025-01-01")), ("2025-04-09+", SPLIT)):
            row = self.cell(b, window=win)
            days = len(pd.date_range(start, END, freq="D"))
            self.assertEqual((row["first"], row["last"]), (f"{start:%Y-%m-%d}", rc.END), win)
            self.assertEqual((row["days"], row["dropped_days"]), (days, 0), win)
            want = f[(f.date >= start) & (f.date <= END)]["net_2x"].mean() * 36500
            self.assertAlmostEqual(row["book_ann_pct"], want, places=9, msg=win)
            # the Aave step lands on 2025-04-09: the benchmark mean is the day-weighted mix of the two levels
            hi = len(pd.date_range(max(start, SPLIT), END, freq="D"))
            aave = self.cell(b, bench="aave_usdc", window=win)
            self.assertEqual(aave["first"], f"{start:%Y-%m-%d}")
            self.assertAlmostEqual(aave["bench_ann_pct"], (AAVE_HI * hi + AAVE_LO * (days - hi)) / days, places=9)
        self.assertAlmostEqual(self.cell(b, bench="aave_usdc", window="2025-04-09+")["bench_ann_pct"], AAVE_HI,
                               places=9)

    def test_bill_clipped_to_end(self):
        b = next(iter(rc.DECIDERS))
        row = self.cell(b, bench="bill", window="2025+")
        self.assertEqual((row["first"], row["last"]), ("2025-01-01", rc.END))
        self.assertAlmostEqual(row["bench_ann_pct"], rc.BILL_PCT, places=9)


if __name__ == "__main__":
    unittest.main()
