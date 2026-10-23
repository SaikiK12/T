# PREREG: nagel_v1 (R308). The 1-day cross-sectional reversal only after market stress (M325)

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R308, in the Claude block R300-R319 claimed on issue #7 on 2026-10-22.
- **Method: M325.**
  - **The reel:** in the owner's reel DbIlAc1g0LM (`docs/REELS_TRANSCRIPT.md`, reel 17), Tom Costello says crypto
    market makers run a short-volatility book and pull quotes when volatility jumps.
  - **The literature:** Nagel (2012, RFS, "Evaporating Liquidity") reads short-term reversal returns as the pay for
    providing liquidity. He finds them highest when the VIX is high.
  - **The lane:** the few who still provide liquidity after a crypto stress day should be paid. It tests the 1-day
    reversal only on the day after such a stress day.
- **Owner (single writer):** the Claude session that froze it.
- **Code:** `scripts/run_nagel.py`, tested on synthetic panels in `tests/test_run_nagel.py`:
  - the stress triggers use past rows only, in both directions;
  - the measures read the top 50 only;
  - the cost tiers;
  - the reversal legs, gross and cost;
  - the minimum leg size;
  - the trial count, and that the baselines are never picked.

  It calls `verify()` on this file first, then checks every input's sha256 (the `inputs` block).
- **Data:** `data/daily/panel.parquet`, one row per (day, Binance perp), 2021-01-02..2026-09-30. It gives close, the
  day's return, funding, open interest and the 30-day volume rank. The panel holds no reserved row.
- **Execution mode: API.** Each traded day opens and closes 10-30 names a leg.
- **Gate: 0, on seen data.** A pass earns a place in a reserved batch (2020 rows for about 80 perps) and a forward
  paper lane, not a confirmation.

## What the author has seen
- **R245 (`xsrev_v1`):** the 1-day reversal inside liquidity terciles of the top 50 over 2021-23, NULL. Liquid coins
  lost −8.9 bp/day gross, −17.5 net (t −3.73); illiquid −1.6 gross, −13.6 net. Its validation was never computed.
- **R300 (`intrars_v1`):** the first UTC hour reverses in both windows (post hoc), on hourly bars.
- **R303 (`capit_v1`):** a long top-50 basket after breadth or cascade days. The cascade measure is this lane's
  `oi`, with a fixed −8% threshold and a median-return filter.
  - The basket beat its drift in validation: breadth h5 +254 bp per event over 59 days (t 1.55), cascade h2 +171
    over 22.
  - Deep-dip longs hedged with the basket lost in 2024-26.
  - Its trigger dates (24 + 59 breadth, 31 + 22 cascade) are in its summary, which the author has read.
- **M218:** the index reversal in high VIX had t 1.94, then −0.05 out of sample.
- **R306 (`msnr_v1`)** with `lab.stress`: the 4-hour level fade (a liquidity-providing rule) lost 109 average days
  in the three FTX days.
- **The plumbing run of this script** (counts only; it reads rows up to D, no exit):

  | Measure | Stress days, discovery | Stress days, validation |
  |---|---|---|
  | `mvol` | 67 | 121 |
  | `disp` | 84 | 147 |
  | `oi` | 45 | 98 |

  - Overlap: `mvol`&`disp` 85 days, `mvol`&`oi` 58, `disp`&`oi` 24.
  - Median leg size: 10 names in the top 50, 30 in the top 150.
  - Panel: 2,098 days.
  - Discovery has fewer stress days because its first 180 rows have no baseline and 2021 set a high bar.
- **No reversal book's return** was computed on 2024-26 rows, or on any stress-day subset, before this freeze.

## The family (8 trials)
- **Decision row D:** signals use rows up to D. The entry is at row D's close and the exit at row D+1's close
  (R299's `targets`). A perp with no close on row D+1 exits at 0, as in R299-R305.
- **The book:**
  - Take row D's top-`top` perps by 30-day volume, with a close and a return on row D. It needs at least 25 names.
  - Long the fifth with the lowest row-D return; short the fifth with the highest. Equal weight.
  - Gross = mean long (return − funding paid) − mean short (return − funding paid), on one unit a leg.
  - Cost = each leg's mean round-trip cost by volume rank on row D. The API tiers per side are 6 bp (rank ≤ 20),
    8 bp (≤ 50), 12 bp (≤ 100) and 20 bp (beyond). Costs are reported at 1x, 2x and 3x.
- **Stress measures** on row D, over the top 50 by volume with at least 30 names:
  - `mvol`: the mean absolute return;
  - `disp`: the cross-sectional standard deviation of returns;
  - `oi`: the change in summed open interest from row D−1 to row D over the perps with both (R303's cascade measure).
- **A stress day:** the measure is at or above the 90th percentile of its previous 365 rows (at least 180 defined).
  For `oi` it is at or below the 10th percentile, because a fall is stress.
- **Books:**
  - decided: universe {top 50, top 150} × stress {`mvol`, `disp`, `oi`} = 6, trading only on stress days;
  - reported and counted, never picked: the same reversal on every day, per universe = 2.

**Windows:** decision days 2021-01-01..2023-12-31 (discovery) and 2024-01-01..2026-09-30 (validation), whose exit
row is inside the window (R301's `window_mask`).

## Statistics
- **The decided series:** the net return per traded day, at 1x.
- **The t:** Newey-West on a calendar grid of days, with untraded days as gaps, lag 5 (R303's `event_stats`). With
  fewer than 10 days there is no t, and the book cannot be picked.
- **Reported per book and window, at 1x/2x/3x and gross:**
  - days, mean (bp per traded day), t, median, hit rate;
  - the mean without the 10 best days, and the 10 best days' share of the sum;
  - each leg's mean and the mean cost.
- **Nagel's contrast, reported:** for each stress book, the same universe's book on the non-stress days.
- **For the pick:** `lab.stress.report` on its day series.

## Decision
- **The pick:** the stress book with the highest discovery net 1x t, among those with a positive discovery mean.
  The two every-day books are never picked.
- **It passes** only if, in validation, all three hold:
  1. net 1x t ≥ 2.0;
  2. the net 2x mean is positive;
  3. the net 1x mean without its 10 best days is positive.
- **Verdict:** PARTIAL (gate 0) if the pick passes, else NULL. Validation is read once. No second pick.
- **What a NULL means:** by this rule, the next-day reversal after a crypto stress day does not pay net of API costs
  on the top 50 or top 150 in 2024-26.

## Power
- **Validation** has 98-147 stress days per measure. Assumed, not measured: a top-50 reversal spread on a stress
  day has a standard deviation of 3-6%.
- **t = 2** over 120 days at a 4.5% standard deviation needs a mean of about 80 bp per traded day. The cost at 1x is
  about 30 bp a day in the top 50, and more in the top 150.
- **The lane detects** only a large liquidity premium. A NULL does not rule out a smaller one.

## Known limits
- **Seen data:** the lanes above read these years; R303's trigger days overlap this lane's `oi` days.
- **Fills:** the book trades at row D's close. After a stress day, spreads are wider than the tiers assume. The 2x
  and 3x rows stand in for that.
- **Free exits:** a perp delisted between D and D+1 exits at 0 (no loss, no cost).
- **Prices:** Binance only; MEXC is not checked here.

## Outputs
- `results/summary.json`: every book and window, the contrasts, the pick's stress report, the stress dates and the
  input hashes.
- `results/days.csv`: every traded day of every book, with legs, gross and cost.
- `run.log`
- FINDINGS.md with 1x/2x/3x costs, read against `registry.program_trials()`.

## Inputs (frozen)

```inputs
b44a28f0f009b00ce481adf66e6bb0b3fb93981a523fc1eaf4c47fad13ef27f6  data/daily/panel.parquet
96053b6a8ba4e22469acfa4da4fb59f1d56e610e5b18460a50e40e82da8d4a6f  lab/inference.py
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508  lab/prereg.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
49acc5ddc694d6ee28192faa90ce1d75d0bb19f5fd20ce57ec166d5a030c4f6e  lab/stress.py
ce7686546c5b1dd33864ff2aa23980fdc685e3b37b8bde45683f742ce3018e98  scripts/run_capit.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
d3cb4b35879bb491245e94a64931cfda2f9e77a79c781fb45342618cad02a82d  scripts/run_lotcap.py
a96ba3034440e83fb90c3211cef6388229ef4b04af1c6bc93c772672412caca3  scripts/run_mlrank.py
4037fa725c3b53259f8479ddfde00695edb187791a010f2fd9c9f80d40d326a8  scripts/run_qbasis.py
6c28a11a0df2bfa1c54bb4ac961b3b09c22d9ae01943098f49d17b66b1c632f2  scripts/run_nagel.py
```
