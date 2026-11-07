# PREREG: capit_v1 (R303). Buying capitulation on Binance perps: deep dips under the 25-day average, and the market after a panic day (M302, M286)

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R303, in the Claude block R300-R319 claimed on issue #7 on 2026-10-22.
- **Methods:**
  - **M302** (Takashi Kotegawa, "BNF", from `docs/TRADER_TALKS.md`): buy a perp whose close sits at least X% below
    its 25-day average, hold 1-5 days. Its market variant: buy the top-50 basket on days when an extreme share of
    coins sit at least 20% below their average.
  - **M286** (Rekt Radio #119, `docs/VIDEO_DIG.md`): after a market-wide liquidation day (Binance open interest falls
    and the top-50 median return is low), go long the top-50 perps.
- **Owner (single writer):** the Claude session that froze it.
- **Code:** `scripts/run_capit.py`, tested on synthetic panels in `tests/test_run_capit.py`:
  - the 25-day gap, the dips and the no-exit flag;
  - the breadth and cascade triggers;
  - the basket, the hedged and trigger books, and the costs;
  - the constants and the trial count;
  - an end-to-end run where a planted rebound is found and a null is not;
  - the plumbing run reads no return.

  It calls `verify()` on this file first and checks every input's sha256 against the block below. The hold returns
  and funding come unchanged from `scripts/run_mlrank.py`'s `targets` (R299, frozen); the windows from
  `scripts/run_qbasis.py` (R301, frozen); the weekly grid from `scripts/run_lotcap.py` (R298, frozen).
- **Data:** `data/daily/panel.parquet`, Binance columns only: `close`, `ret`, `fund`, `oi_usd` and `rank_qvol30`.
  Binance klines, funding and metrics were fetched for every archive perp, delisted ones included, so this lane does
  not touch the survivorship leak found in R299's audit (`docs/FEATURE_VINTAGE_INTEGRITY.md`).
- **Execution mode: API.** A dip20 day holds about 20 names (dip40: 4-10) plus a 50-name hedge, and a trigger day
  buys 50 names. That
  is more orders than manual web's ~15 a day.
- **Gate: 0, on seen data.** Neighbouring lanes read these years with related rules (below). A pass earns a place in a
  reserved batch or forward days, not a confirmation.

## What the author has seen
- **R245 (`xsrev_v1`):** 1-day and 7-day reversal inside liquidity terciles of the top 50, NULL. Discovery r1d/LIQ
  −17.5 bp/day (t −3.73), r1d/ILLIQ −13.6 (t −3.30), r7d/ILLIQ about 0.
- **R243 (`chartist_v1`):** Bollinger, stochastic and CCI fades lose in 2021-23 (STOCH/4h alpha t −2.07, CCI −1.7 to
  −1.9).
- **R263 (`brute5k_v1`):** 5,472 chart rules on the top 20, NULL; the mean-reversion families are inside it.
- **R252 (`oiwick_v1`):** per-coin fades of hourly OI drops with long wicks, NULL. Raw long bounce +143 bp over 24 h
  (n 658), mostly market-wide (+23 bp market-adjusted).
- **R206 (`liq_v1`):** fading Gate liquidation spikes, NULL. Long cascades continue at 12 h; short squeezes revert
  below cost.
- **R255 (`cascmkt_v1`):** long the market 24 h after an hour with 3+ cascade triggers, NULL. 15 events, all in 2024;
  the market rose +186 bp over 24 h after them against −8 bp unconditionally; t 1.03.
- **R283 (`vixpanic_v1`):** VIX panic onsets, NULL; BTC had only 10-16 onsets.
- **R274 (`squeeze_v1`) and R302 (`fundxs_v1`):** neither reads price dips; listed because they read the same panel
  years.
- **The plumbing run of this script** (counts only, no return after a decision day):

  | Signal | Days (perp-events), all | Discovery 2021-23 | Validation 2024-26/09 |
  |---|---|---|---|
  | dip20 | 1,459 | 570 (12,311) | 888 (17,068) |
  | dip30 | 1,021 | 262 (3,739) | 758 (6,374) |
  | dip40 | 752 | 120 (1,175) | 631 (2,757) |
  | breadth | 83 | 24 | 59 |
  | cascade | 53 | 31 | 22 |

  The panel has 2,098 days; open interest has coverage from 2021-12-03, so cascades cannot fire in most of 2021.
- **One choice was made from counts.** M302 says the top 2% of the breadth share. At the 98th percentile the
  breadth trigger leaves 7 discovery days, so this lane uses the 95th (24 days). No return was read for either.

## The family (10 trials)
**Common to all books**
- **Decision:** row D of the panel is the decision at 00:00 UTC of day D. Signals use rows up to D.
- **Entry and exit:** entry at row D's close; a hold of h days exits at the last close in rows D+1..D+h and pays the
  funding settled in those rows (a long pays positive funding). A perp with no close in the hold books 0 (R299's
  `targets`); the count is reported.
- **Universe:** the top 150 Binance perps by trailing 30-day quote volume with a close on row D.
- **The basket:** the equal-weight top 50 by the same rank, its h-day return net of the funding a long pays; NaN with
  fewer than 30 names.
- **The 25-day gap:** row D's close over the mean of the closes on rows D−24..D, minus 1. It needs all 25 closes.

**Dip books (6): dip {20, 30, 40% below the average} × hold {1, 5 days}**
- On each day with at least one dip in the top 150: long the dip perps equal-weight and short the top-50 basket, for h
  days.
- Gross per event = the dips' mean (return − funding) minus the basket's.
- **Decided net** = gross − 4 sides × cost (two on each leg).

**Trigger books (4): trigger {breadth, cascade} × hold {2, 5 days}**
- **Breadth:** the share of top-150 perps (with a 25-day average) at least 20% below it. A trigger day needs that share
  at or above its 95th percentile over the previous 365 days (at least 180 of them), and at least 10%.
- **Cascade:** on row D, the top-50 perps' summed open interest against the same perps' on row D−1 is at or below
  −8%, and their median daily return is at or below −5%, with at least 30 perps having both days' open interest.
- On each trigger day: long the top-50 basket for h days.
- **Decided net** = the basket's (return − funding) − 2 sides × cost − the window's drift.
  - **The drift** is the basket's mean h-day return (net of funding) over every decision day of the same window.
    A trigger book earns only what it beats holding the basket on any day.

**Costs:** API, 8.5 / 17 / 25.5 bp per side at 1x / 2x / 3x.

**Windows:** discovery 2021-01-01..2023-12-31, validation 2024-01-01..2026-09-30. An event counts only when its hold
ends inside the window.

## Statistics
- **Per book and window:** events, mean per event (bp), bp/day (the mean over the hold), median, hit rate, the mean
  without the 10 best events, and the 10 best events' share of the sum.
- **The t:** Newey-West on a daily calendar grid (days without an event are gaps), lag max(5, 2h).
- **Fewer than 10 events** in a window: no t, and the book cannot be picked.

## Decision
- **The pick:** the book with the highest discovery net 1x t, among those with a positive discovery mean.
- **It passes** only if, in validation, all three hold:
  1. net 1x t ≥ 2.0;
  2. the net 2x mean is positive;
  3. the net 1x mean without its 10 best events is positive.
- **Verdict:** PARTIAL (gate 0) if the pick passes, else NULL. Validation is read once. No second pick.
- **Exit check (decided now, applied in FINDINGS from `results/events.csv`).** If the pick is a dip book, its
  validation mean is recomputed with every no-exit perp-event booked at −50% instead of 0. If that turns the 1x mean
  negative, the verdict is reported as exit-suspect and earns nothing until explained.
- **What a pass earns:**
  - a place in a reserved batch (2020 rows exist for about 80 perps, so a 2020 read is partial);
  - a forward paper lane with its own id on MEXC prices.
- **What a NULL means:** buying deep dips against the market, and buying the market after breadth or cascade panics,
  do not pay net of API costs on Binance perps in 2024-26 by this rule. M302 and M286 close for this panel.

## Reported (not decided on)
- **Per book and window:** gross and net at 1x/2x/3x; the long leg alone at 1x (2 sides); the hedge's mean; the
  perp-events and no-exit counts; the drift for trigger books.
- **Per calendar year:** events and the decided net 1x per event (triggers use the all-period drift).
- **Hansen SPA and White's reality check** over the 10 books per window: each book's decided net 1x summed onto a
  7-day grid from the panel's first day; 2,000 stationary-bootstrap draws, mean block 4 weeks, seed 303.
- **The trigger days** themselves, and how many dip days are also trigger days.

## Outputs
`results/summary.json`, `results/events.csv`, `run.log`, and FINDINGS.md with 1x/2x/3x costs read against
`registry.program_trials()`.

## Power
- **Dip books:** a per-event effect of 1% with a 6% standard deviation needs about 145 independent events for an
  expected t of 2.0. dip20 and dip30 have more event days than that in each window, dip40 in validation only (120 in
  discovery). Five-day holds overlap, so their effective count is lower.
- **Trigger books:** 22-59 days per window, and overlapping holds. Only a large rebound (about 3% per event over the
  drift) is visible. A NULL there is weak evidence.

## Known limits
- **Seen data:** the lanes above read these years with related rules.
- **A perp with no close in the hold books 0.** Delistings usually fall before they stop; the exit check covers it.
- **The drift uses the whole window** as a benchmark, not as a signal.
- **Prices:** Binance only; MEXC is not checked here.

## Inputs (frozen)

```inputs
b44a28f0f009b00ce481adf66e6bb0b3fb93981a523fc1eaf4c47fad13ef27f6  data/daily/panel.parquet
96053b6a8ba4e22469acfa4da4fb59f1d56e610e5b18460a50e40e82da8d4a6f  lab/inference.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
d3cb4b35879bb491245e94a64931cfda2f9e77a79c781fb45342618cad02a82d  scripts/run_lotcap.py
a96ba3034440e83fb90c3211cef6388229ef4b04af1c6bc93c772672412caca3  scripts/run_mlrank.py
4037fa725c3b53259f8479ddfde00695edb187791a010f2fd9c9f80d40d326a8  scripts/run_qbasis.py
ce7686546c5b1dd33864ff2aa23980fdc685e3b37b8bde45683f742ce3018e98  scripts/run_capit.py
```

## Multiplicity
- **Program trials before this lane:** 9,478,673 in `registry.program_trials()` today (R299-R302 included).
- **10 trials, one pick, one validation read.** One registry row with 10 trials. With R304's 7 the program reaches
  9,478,690.
