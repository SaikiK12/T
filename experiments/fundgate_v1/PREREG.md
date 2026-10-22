# PREREG: fundgate_v1 (R297). Does the market's funding response to up days time the crypto market? (M295)

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R297 (Claude block R280-R299, claimed on issue #7 on 2026-10-22 before this freeze).
- **Method M295,** from a Bankless guest (2026-04-14, `docs/COMMENT_DIG.md`): "funding rates on positive days so far
  this year have been lower than funding rates on positive days in 2022, which just kind of confirms to me … this is a
  bear market structure". If longs do not pay up on up days, nobody is chasing the market, and it should do worse.
  The method row also names the opposite reading: a strong funding response means crowded longs, a warning.
- **Owner (single writer):** the Claude session that froze it.
- **Code:** `scripts/run_fundgate.py`, tested on synthetic data in `tests/test_run_fundgate.py`:
  - the trimmed means use the top of the row, and the basket the top of the row before;
  - a row with too few coins is a gap;
  - the slope is OLS over the trailing window, the up-day mean uses up days only, and the z-score reads only the
    past;
  - targets sum the next h rows and stay inside their window;
  - a planted positive effect passes as "claim", a planted negative one as "crowding", and a null does not pass;
    a constant drift is not a slope;
  - the residual on momentum;
  - the gate's positions, switch costs and funding;
  - an end-to-end run on a full-length synthetic panel.

  It calls `verify()` on this file first and checks every input's sha256 against the block below.
- **Execution mode:** decided per book.
  - The basket (50 coins, rebalanced daily) is API only.
  - BTC long/flat is manual web: at most one order a day.
- **Gate:** 0. The daily panel was built 2026-10-21. R282 read its columns cross-sectionally (`pitfac_v1`).
  - R242 (`tsbattery_v1`) and R255 (`cascmkt_v1`) timed the equal-weight top-50 market with other signals.
  - R238 used a per-coin funding slope across coins.
  - No lane has read market-wide funding against the market's next days.

## What the author has seen
- **The guest's claim,** and the method row in `registry/methods.csv`.
- **Market history in broad strokes, as anyone has:** 2021 bull, 2022 bear, 2023-24 recovery. Funding is known to
  run high in bull markets. So neither window is blind in a narrative sense; the test is whether the daily measure
  adds timing.
- **R242, R255, R283 and R284 in full:** market timing on crypto with other signals, all NULL.
- **A plumbing run on the real panel, before this freeze** (`--plumbing`), which printed counts only:
  - 2,098 calendar days from 2021-01-02 to 2026-09-30;
  - the trimmed means are defined on 2,091 days, the basket on 2,090 and BTC on 2,097;
  - a median of 50 coins on both;
  - the first z-scores are on 2021-07-31 (slope) and 2021-07-20 (up-day funding);
  - rows with x and target: 870 / 997 (slope h7, discovery / validation), 824 / 974 (slope h30), 881 / 997
    (up-day h7) and 835 / 974 (up-day h30).

  No signal value, return, product or statistic was printed.

## Inputs (frozen)

```inputs
b44a28f0f009b00ce481adf66e6bb0b3fb93981a523fc1eaf4c47fad13ef27f6  data/daily/panel.parquet
4475f8962fb723e798383c839d6b0cc390c51b373937755a6d6ed2a62663cad6  lab/daily.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
f5c6d428dab534642b5e673cd94efafd38bfccba68cebaa6afac340cf30842f1  scripts/run_fundgate.py
```

## Data
- **The daily point-in-time panel** (`lab/daily.py`): one row per (day, Binance USD-M perp).
  - Row D is the decision at 00:00 UTC of day D. It holds day D-1's return (`ret`) and the funding settled in the 24
    hours ending at 00:00 D (`fund`, a daily rate paid by longs).
  - `rank_qvol30` ranks the trailing 30-row mean quote volume on the row.
  - Rows before 2021 do not exist (reserved, `docs/GATES.md`).
- **The top:** perps with `rank_qvol30` ≤ 50 on the row. This is the same set as the lab's top-50 lanes, decided at
  00:00 with what was known then.

## Inputs on each row D
- **F_D, R_D:** the 10% trimmed means of `fund` and `ret` over the top of row D, using perps with both. The row is a
  gap with fewer than 30.
  - A trimmed mean, not the median: many coins sit at Binance's base rate (0.01% per 8 h), which would freeze a
    median.
- **The two measures,** over rows D-29..D:
  - **slope_D:** the OLS slope of F on R, from rows with both (at least 25);
  - **upfund_D:** the mean F over rows with R > 0 (at least 8).
- **x_D = z-score** of the measure against rows D-365..D-1 (at least 180), clipped at ±3. A high x means funding
  responds to up days more than over the past year.
- **Reported only:**
  - level_D, the mean F over the 30 rows, and its z-score;
  - mom30_D, the basket's summed log return over the 30 rows.

## Targets
- **The basket:** row D+1's return of the equal-weight basket of the top of row D, from perps with a return on row
  D+1. The day is a gap with fewer than 30.
- **y_h on row D:** the sum of log(1 + basket return) over rows D+1..D+h, for h = 7 and 30. It is NaN when one of
  those rows is a gap.
- **b_h:** the same for BTCUSDT (a reported split).
- **A target counts only when row D+h is inside the decision's window.** No discovery target reads a validation day.

## Windows (by decision row)
- **Discovery:** 2021-04-01..2023-12-31. The x values start in late July 2021.
- **Validation:** 2024-01-01..2026-09-30.

## Tests (4 trials: slope h7, slope h30, upfund h7, upfund h30)
In each window:
- x and y are demeaned within the window.
- The statistic is the Newey-West t of the mean of their product, a slope test, over calendar days with gaps as
  zero. The lag is 2h (14 and 60 days), for overlapping targets.

Also reported for each trial and window:
- the slope, the correlation, and a plain t from every h-th row (non-overlapping);
- BTC's t;
- the validation t by year;
- the t given momentum: x is first regressed on mom30 within the window, and the residual is tested.

## Decision
- **A trial passes** when the validation |t| ≥ 2.50 and the discovery t has the same sign.
  - 2.50 is Bonferroni over 4 trials at 5% two-sided.
  - A positive t is the guest's reading ("claim"); a negative t is the crowding reading. Either direction counts.
- **Verdict:** PARTIAL (gate 0) if any trial passes, else NULL.
- **What a pass earns:** a forward paper lane with its own id and PREREG.
  - It goes there only if its reported rule (below), in the passing direction, also beats always long, net at 1x and
    2x, in both windows.
  - It also goes to the next reserved batch, on 2020: funding and price only, through a frozen batch PREREG.
- **A pass is not read as a mechanism** when its t given momentum falls below 2.0. That is written into FINDINGS as
  "momentum in disguise", and no lane follows.

## The rules (reported, and the condition for a lane)
For each measure and each direction:
- **The gate:** long over day D when x_D ≥ 0 ("claim"), or when x_D < 0 ("crowding"); otherwise flat. Flat when
  x_D is NaN.
  - Long earns row D+1's return less the funding longs paid on row D+1.
  - Each switch pays one side.
- **Against:** always long on the same asset, net of funding, no costs.
- **The basket:** API, 8.5 / 17 / 25.5 bp per side (1x / 2x / 3x). The daily rebalancing of either basket book is not
  costed.
- **BTC:** manual web 3 / 6 / 9 bp per side, with API 8.5 bp reported.
- **Reported per window:**
  - annual net, volatility and Sharpe;
  - the maximum drawdown of the summed daily net;
  - time in the market and switches per year;
  - the same for always long;
  - the excess over always long, with its Newey-West t (lag 5).

## Reported (not decided on)
- **By calendar year, 2021-2026 (2026 to September):**
  - mean F, mean F on up days and on down days (bp per day);
  - the share of up days and the year's own slope.

  This checks the guest's premise directly: was up-day funding in 2026 below 2022's?
- **The correlations** among x_slope, x_upfund, x_level and mom30.

## Outputs
- `results/summary.json` (every number above);
- `results/daily.csv` (signals, targets and the market series per day);
- `run.log`, and FINDINGS.md with 1x/2x/3x costs read against `registry.program_trials()`.

## Power (written before the result)
This uses the normal approximation, with n_eff = validation rows / h, against the 2.50 bar in one direction.

| ρ | h7 (n_eff 142) | h30 (n_eff 32) |
|---|---|---|
| 0.1 | 10% | 3% |
| 0.2 | 48% | 9% |
| 0.3 | 90% | 24% |
| 0.4 | >99% | 50% |
| 0.5 | >99% | 79% |

- h7 can find a correlation of 0.3. h30 finds only very large effects.
- A NULL at h30 says little. A NULL at h7 rules out ρ ≥ 0.3 at the weekly horizon.

## Known limits (written before the result)
- **The guest's claim is one year against another.** The test reads a daily, rolling version of it. A claim true
  only at the scale of years cannot be tested with 5.7 years of data.
- **Coins that leave the top keep their return for the day they were held.** A perp that stops trading has no
  return on the next row and drops out of that day's mean, so it exits for free. This is rare in the top 50.
- **The basket book ignores rebalancing costs.** BTC has none.
- **Funding sums mix 8 h, 4 h and 1 h intervals.** Each is a daily rate, so they are comparable.
- **Only Binance funding is used.** MEXC's own funding, the owner's venue, is not.

## Multiplicity
- 4 trials, two-sided Bonferroni. One registry row with 4 trials.
- The result is read against `registry.program_trials()` in FINDINGS.
