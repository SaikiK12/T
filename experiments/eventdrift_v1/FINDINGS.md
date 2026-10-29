# FINDINGS: eventdrift_v1 (R368). After an EIA release, Binance's crude and gas perps do not keep moving the way their first minute went

**Verdict: NULL (gate 0), 26 trials, 2 decisions, underpowered.** Neither decision cell shows continuation. Crude
after a falling first minute reversed by 8.1 bp over the next five minutes (14 events, p 0.91 for continuation); gas
storage after any first minute moved -0.1 bp (29 events, p 0.50). Both cells' minimum detectable size (15.6 and 20.5
bp) is above the 12 bp cost unit, so this says "no drift larger than about 15-20 bp was seen in 6 months", not "no
drift". It is not a PnL and it does not support the review's second-stage claim for these instruments.

Frozen run of 2026-10-29 00:08 UTC. PREREG sha `1a21ab87da62`, 7 inputs and the data manifest re-checked by the runner.
Program trials 9,479,123 before, 9,479,149 after (`registry.program_trials()`).

## What was tested
- 30 Weekly Petroleum Status Report releases (Wednesdays) on CLUSDT and 30 Weekly Natural Gas Storage Report releases
  (Thursdays) on NATGASUSDT, 2026-04-01 .. 2026-10-22, from Binance's one-minute archive. All 60 had every bar from
  T-1 to T+10.
- Reaction r0: the first minute after the release. Entry: the open of the next bar, in the direction of r0. Exit: h
  minutes later. Continuation = sign(r0) times the move, before costs. One round trip = 12 bp (1x), 24 bp (2x), 36 bp
  (3x).
- Dropped for having no sign (r0 exactly 0): 2 crude and 1 gas event.

## The decision cells (h = 5 minutes, entry at the next bar's open)

| Cell | Events | Mean continuation (bp) | SD | t | Hit | MDE80 (bp) | p | p Holm | Net 1x / 2x / 3x (bp) |
|---|---|---|---|---|---|---|---|---|---|
| D1 crude, first minute down (`neg`) | 14 | -8.1 | 20.8 | -1.46 | 36% | 15.6 | 0.913 | 1.000 | -20.1 / -32.1 / -44.1 |
| D2 gas storage, any first minute (`all`) | 29 | -0.1 | 39.3 | -0.01 | 62% | 20.5 | 0.504 | 1.000 | -12.1 / -24.1 / -36.1 |

- PASS needed a Holm p of at most 0.05 and a mean above 24 bp. Nothing came close, in either direction of
  significance.
- Late entry (one minute later, close of bar T+1): crude `neg` -11.1 bp (p 0.92), gas `all` -3.2 bp (p 0.70).
- Underpowered: with these spreads the test needed a true mean of about 16 bp (crude `neg`) or 20 bp (gas) to see it 80%
  of the time. A drift of 5-10 bp, which would still not pay a 12 bp round trip, is invisible here.

## All 26 cells
bp of price. `p` is the one-sided sign-flip p for "mean continuation above 0" (exact for 18 events or fewer, 200,000
random flips above that), uncorrected; only the two bold cells were decided on.

| Cell | n | Mean | SD | t | Hit | MDE80 | p | Net 1x / 2x / 3x |
|---|---|---|---|---|---|---|---|---|
| Crude (WPSR), CLUSDT · all · h1 | 28 | +5.6 | 14.6 | +2.04 | 57% | 7.7 | 0.024 | -6.4 / -18.4 / -30.4 |
| Crude (WPSR), CLUSDT · all · h2 | 28 | +7.8 | 20.9 | +1.97 | 57% | 11.0 | 0.028 | -4.2 / -16.2 / -28.2 |
| Crude (WPSR), CLUSDT · all · h5 | 28 | +3.2 | 33.8 | +0.50 | 43% | 17.9 | 0.339 | -8.8 / -20.8 / -32.8 |
| Crude (WPSR), CLUSDT · all · h10 | 28 | -0.7 | 35.0 | -0.11 | 39% | 18.5 | 0.542 | -12.7 / -24.7 / -36.7 |
| Crude (WPSR), CLUSDT · neg · h1 | 14 | +3.0 | 15.8 | +0.70 | 50% | 11.9 | 0.253 | -9.0 / -21.0 / -33.0 |
| Crude (WPSR), CLUSDT · neg · h2 | 14 | +2.6 | 18.4 | +0.53 | 43% | 13.8 | 0.309 | -9.4 / -21.4 / -33.4 |
| **Crude (WPSR), CLUSDT · neg · h5** | 14 | -8.1 | 20.8 | -1.46 | 36% | 15.6 | 0.913 | -20.1 / -32.1 / -44.1 |
| Crude (WPSR), CLUSDT · neg · h10 | 14 | -10.1 | 27.7 | -1.37 | 36% | 20.7 | 0.903 | -22.1 / -34.1 / -46.1 |
| Crude (WPSR), CLUSDT · pos · h1 | 14 | +8.3 | 13.3 | +2.34 | 64% | 9.9 | 0.016 | -3.7 / -15.7 / -27.7 |
| Crude (WPSR), CLUSDT · pos · h2 | 14 | +12.9 | 22.5 | +2.15 | 71% | 16.9 | 0.017 | +0.9 / -11.1 / -23.1 |
| Crude (WPSR), CLUSDT · pos · h5 | 14 | +14.6 | 40.8 | +1.33 | 50% | 30.5 | 0.103 | +2.6 / -9.4 / -21.4 |
| Crude (WPSR), CLUSDT · pos · h10 | 14 | +8.7 | 39.9 | +0.82 | 43% | 29.8 | 0.231 | -3.3 / -15.3 / -27.3 |
| Crude (WPSR), CLUSDT · neg · h5 · late entry | 14 | -11.1 | 27.7 | -1.50 | 36% | 20.7 | 0.922 | -23.1 / -35.1 / -47.1 |
| Gas storage (NGS), NATGASUSDT · all · h1 | 29 | +3.1 | 21.3 | +0.79 | 59% | 11.1 | 0.217 | -8.9 / -20.9 / -32.9 |
| Gas storage (NGS), NATGASUSDT · all · h2 | 29 | -3.1 | 28.8 | -0.57 | 45% | 15.0 | 0.715 | -15.1 / -27.1 / -39.1 |
| **Gas storage (NGS), NATGASUSDT · all · h5** | 29 | -0.1 | 39.3 | -0.01 | 62% | 20.4 | 0.504 | -12.1 / -24.1 / -36.1 |
| Gas storage (NGS), NATGASUSDT · all · h10 | 29 | +9.3 | 48.9 | +1.03 | 55% | 25.4 | 0.157 | -2.7 / -14.7 / -26.7 |
| Gas storage (NGS), NATGASUSDT · neg · h1 | 18 | +4.6 | 20.6 | +0.94 | 61% | 13.6 | 0.184 | -7.4 / -19.4 / -31.4 |
| Gas storage (NGS), NATGASUSDT · neg · h2 | 18 | -0.7 | 30.0 | -0.11 | 39% | 19.8 | 0.542 | -12.7 / -24.7 / -36.7 |
| Gas storage (NGS), NATGASUSDT · neg · h5 | 18 | +3.0 | 37.5 | +0.34 | 67% | 24.7 | 0.366 | -9.0 / -21.0 / -33.0 |
| Gas storage (NGS), NATGASUSDT · neg · h10 | 18 | +14.5 | 46.3 | +1.33 | 72% | 30.6 | 0.100 | +2.5 / -9.5 / -21.5 |
| Gas storage (NGS), NATGASUSDT · pos · h1 | 11 | +0.7 | 23.2 | +0.11 | 55% | 19.6 | 0.459 | -11.3 / -23.3 / -35.3 |
| Gas storage (NGS), NATGASUSDT · pos · h2 | 11 | -6.9 | 27.6 | -0.83 | 55% | 23.3 | 0.769 | -18.9 / -30.9 / -42.9 |
| Gas storage (NGS), NATGASUSDT · pos · h5 | 11 | -5.2 | 43.6 | -0.40 | 55% | 36.8 | 0.651 | -17.2 / -29.2 / -41.2 |
| Gas storage (NGS), NATGASUSDT · pos · h10 | 11 | +0.9 | 54.1 | +0.05 | 27% | 45.7 | 0.482 | -11.1 / -23.1 / -35.1 |
| Gas storage (NGS), NATGASUSDT · all · h5 · late entry | 29 | -3.2 | 33.0 | -0.52 | 52% | 17.1 | 0.696 | -15.2 / -27.2 / -39.2 |

## What the other cells show (reported, not decided on)
- **The releases are visible on these perps** (a post-run diagnostic, not in the PREREG's reported list and not a trial; the
  baseline is every minute from 14:00 to 14:29 UTC on all 210 days, event days included). The median first-minute move is 11.1 bp for crude (a normal minute
  from 14:00 to 14:29 UTC is 4.4 bp) and 48.7 bp for gas (normal 3.5 bp). Gas storage moves the perp by about 14
  times a normal minute in its first minute, and then the five-minute continuation is on average zero.
- **The first minute does not predict the next five.** The correlation of r0 with the 5-minute move is -0.03 (crude)
  and 0.07 (gas).
- **Crude after a rising first minute is the one cell that leans the way a drift would**: +8.3 bp at h1 (p 0.016), +12.9
  at h2 (p 0.017), +14.6 at h5 (p 0.10), 14 events. It is the opposite of the review's claim (there, negative news
  drifts and positive news is absorbed at once). It was not a decision cell. With 26 cells counted the Bonferroni level
  is 0.0019, so none of these survives, and at 1x the best of them nets +2.6 bp at h5 and -3.7 bp at h1. It is a thing to
  look at with fresh events, not a result.
- **Pooled crude** shows +5.6 bp at h1 and +7.8 at h2 (28 events, p 0.024 and 0.028): small, uncorrected, and under
  half of one cost unit.

## Reading it
- No taker form of this signal pays on these perps: the largest mean continuation of any cell, +14.6 bp, is 2.6 bp
  above one cost unit and below it at 2x and 3x.
- The sample is small and one regime (April to October 2026, daylight time). The data are minute bars of a derived-index
  perp, not CME futures, and the news sign is the market's own move, not a surprise against consensus or the API report.
  None of the review's claims about the paper or the firm rules were read or verified here.
- What this closes: M444's cheap form (first-minute continuation of Binance CLUSDT / NATGASUSDT over 1-10 minutes at
  taker cost) is NULL for April-October 2026.
- What it leaves open: tick-level behaviour in the first 30 seconds, a consensus or API surprise sign, and CME
  futures. Those need data the lab does not hold (consensus, CME ticks; owner decisions).

## What is running next
- The same perps are recorded at tick level since 2026-10-28 23:56 UTC (`scripts/record_commodity_perps.py`:
  Hyperliquid xyz:CL / NATGAS, Kraken PF_WTIOILUSD / PF_NATGASUSD, Binance CLUSDT / NATGASUSDT bookTicker, aggTrade and
  mark). The next releases inside that record are gas storage on 2026-10-29 14:30 UTC and crude on 2026-11-04 15:30 UTC.
- **R369 `eventlag_fwd`** (frozen 2026-10-29) is the tick-level follow-up on these same releases: Lighter as a follower of
  Binance and Hyperliquid, scored automatically at each release to 2026-12-31 (first read about 2026-12-23).
- A forward replication of R368's own question would be a new lane with a new id, and would not read a verdict before 20 new releases per
  event type exist (about five months). The crude-up cell above can be named as a hypothesis in its PREREG with the
  direction written down in advance.

## Code, data and reproduction
`scripts/eventdrift_rule.py`, `scripts/run_eventdrift.py`, `scripts/eventdrift_calendar.py`,
`scripts/fetch_tradfi_perps.py`; `python scripts/run_eventdrift.py` re-runs the frozen lane. Results in
`experiments/eventdrift_v1/results/` (`cells.csv`, `events_wpsr.csv`, `events_ngs.csv`, `coverage.csv`, `summary.json`).
Tests: `tests/test_eventdrift.py` (synthetic planted-drift world: the planted drift is found, a world with none is not).
