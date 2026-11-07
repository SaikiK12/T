# PREREG: xvenue_v1 (R205), top traders vs the crowd measured on another venue (Gate)

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R205
- **Owner (single writer):** the session that froze it
- **Code:** `scripts/fetch_gate.py`, `scripts/run_gate_lanes.py xvenue`, `lab/slices.py`, `lab/features.bins_xs`
- **Source claim:** `docs/CLAIMS.md` C06.

## What the author had seen
Binance's top_vs_crowd as a 72 h short slice book: in-sample t 2.72 (book B of R198, reported), +71%/yr on the
2025-07..2026-09 holdout, so **the Binance signal's returns on this lane's window are known**. Gate's data were fetched
(format probed on BTC_USDT); no Gate-based statistic has been computed.

## Data and alignment
Gate `contract_stats` hourly (180 days kept: about 2026-04-22 on), coins of the Binance research universe listed on
Gate. A Gate row stamped X is assigned to Binance row X (known at that bar's close, at most one hour late; never
earlier). Gate top_vs_crowd = log(top_lsr_size) - log(lsr_account) (top traders' position ratio against the
all-account ratio, the analogue of Binance's). Binance returns, eligibility (top 50), tier costs and funding.

## Books (72 h overlapping slices, short, size 1 / (72 x 9.316), universe hedge, as R197)
- **G (primary):** Gate top_vs_crowd xs8 bin 0, ranked among tradable coins with Gate data at the hour.
- B: Binance top_vs_crowd xs8 bin 0 (archive bins), restricted to the same coins: the reference.
- G_only: hours where a coin is in Gate's bin 0 but not in Binance's (what Gate adds).
Window: Binance rows from the first Gate hour + 72 h to 2026-09-30 23:00 (end of the archive).

## Decision
This window is inside the spent flow72 holdout and the Gate signal is expected to correlate with Binance's, so the
lane cannot confirm anything. Recorded: **REPLICATES (discovery level)** if G has a positive daily mean at 1x with NW
t (lag 10) >= 2; **ADDS** if G_only has a positive mean with t >= 2. Otherwise NULL for that question. Either way, a
real test of a Gate-based rule needs forward data (Gate keeps 180 days, so the forward period from 2026-10-01 can be
scored later without a collector).

## Reported
Hourly cross-sectional Spearman correlation of the two signals (mean, quantiles); overlap of the bin-0 sets; 2x and
3x costs; per month.

## Multiplicity
Trials = 3 (G, B on this window, G_only). Program trials 9,471,642 before this lane.

## Expectations
High correlation of the two signals (> 0.5); G positive like B on this window; G_only small and noisy.
