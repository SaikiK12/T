# FINDINGS: cmelead_v1 (R370). Binance's crude and gas perps do not lag CME after an EIA release

**Verdict by the frozen rule: INCONCLUSIVE (gate 0), 16 trials, 2 decisions. Substantively a NULL for the lag: at every
latency of 0.5 s and above, Binance had already covered most of CME's move.** The lag filter (Binance has covered at most half
of the move) kept 0 of 24 gas trades and 1 of 21 crude trades at the decision latency of 1 s; at 0.5 s it kept 1 of 23 and
2 of 20. The rule needs 6 lag-filtered trades a type, so it cannot rule; the table below is why. It is not a PnL, it does not
touch R369, and it does not say anything about a lag shorter than 0.5 s.

Frozen run of 2026-10-29 01:20 UTC. PREREG sha `52be6b6c5d73`, 8 inputs and the data digest `5e1cb22a3985` re-checked by the
runner. Program trials 9,479,173 before, 9,479,189 after (`registry.program_trials()`). Databento spend: $0.6649 for 180
windows (`docs/provenance/cmelead.json`).

## What was tested
- 30 crude (WPSR) and 30 natural-gas storage releases, 2026-04-01 .. 2026-10-22. Leader: CME front-month trades (Databento,
  `CL.v.0`, `NG.v.0`, the exchange's event time). Follower: Binance CLUSDT and NATGASUSDT aggregated trades. All 60 release
  windows were valid; 116 of the 120 placebo windows (the four others fall before Binance's archive begins).
- Rule: the first CME trade at least 8 bp (crude) or 20 bp (gas) from its pre-release median at t*; a Binance taker order L
  seconds later; skip if CME has fallen back below the threshold; keep the trade if Binance's last print has covered at most
  half of CME's displacement; entry at the first matching taker print within 1 s, exit at T + 60 s. One cost unit = 10 bp.

## The decision cells (L = 1 s, lag-filtered)

| Cell | Valid releases | Trades | Mean gross (bp) | p Holm | Net 1x / 2x / 3x (bp) |
|---|---|---|---|---|---|
| D1 crude (`wpsr`) | 30 | 1 | +2.5 | 1.00 | -7.5 / -17.5 / -27.5 |
| D2 gas storage (`ngs`) | 30 | 0 | n/a | 1.00 | n/a |

PASS needed 10 valid releases, 6 trades, a Holm p of 0.05 or less and a mean above 20 bp. With 1 and 0 trades the rule returns
INCONCLUSIVE.

## Why there are no lag-filtered trades: Binance moves with CME
`c` is the share of CME's displacement that Binance's last print shows at the decision time; the filter keeps c <= 0.5.
Releases with a scored trade ("ok"), quantiles of c:

| Type | L | Releases | c: 10 / 25 / 50 / 75 / 90 % | c <= 0.5 | c > 1 |
|---|---|---|---|---|---|
| Gas | 0.5 s | 23 | 0.64 / 0.77 / 0.88 / 1.03 / 1.15 | 1 (4%) | 35% |
| Gas | 1 s | 24 | 0.69 / 0.78 / 0.87 / 1.04 / 1.14 | 0 | 33% |
| Gas | 2 s | 22 | 0.82 / 0.85 / 0.99 / 1.08 / 1.15 | 0 | 41% |
| Crude | 0.5 s | 20 | 0.58 / 0.71 / 0.90 / 0.98 / 1.12 | 2 (10%) | 20% |
| Crude | 1 s | 21 | 0.64 / 0.73 / 0.91 / 1.00 / 1.30 | 1 (5%) | 24% |
| Crude | 2 s | 16 | 0.77 / 0.83 / 0.96 / 1.02 / 1.08 | 0 | 38% |

Binance's perps are at 0.9 of CME's move when CME's own first trade at the threshold appears, and in a third of the gas
releases they have gone past it (c > 1). They move at the same time as CME, not after it. That is consistent with
makers on a 24/7 venue repricing from the same screens; it is the opposite of a stale quote.

Two details of the clock, both reported, none decided on:
- **Gas:** CME's first trade 20 bp from its reference comes 1.04-1.08 s after the nominal 10:30:00 in at least 75% of the
  releases (10th percentile 0.45 s). The market reacts about a second after the stamp; D at that moment has a median of
  47 bp. R369's gas decision is therefore taken at about T + 2 s.
- **Crude:** t* is 0.00-0.04 s after T in a quarter of the releases and 1.06-2.7 s in the rest. The first group are moves
  that were already 8 bp from the 50-second median at T: noise, not the report (see the placebo).

## The unfiltered cells (reported, not decided on)
Every scored trade, whatever Binance had done, entered at the first taker print within 1 s:

| Type | L | Trades | Mean gross | SD | MDE80 | p | Net 1x / 2x / 3x |
|---|---|---|---|---|---|---|---|
| Gas | 0.5 s | 23 | +6.1 | 49.6 | 29.0 | 0.28 | -3.9 / -13.9 / -23.9 |
| Gas | 1 s | 24 | +1.4 | 44.4 | 25.4 | 0.44 | -8.6 / -18.6 / -28.6 |
| Gas | 2 s | 22 | +5.3 | 41.3 | 24.6 | 0.28 | -4.7 / -14.7 / -24.7 |
| Gas | 5 s | 21 | +3.0 | 39.8 | 24.3 | 0.37 | -7.0 / -17.0 / -27.0 |
| Crude | 0.5 s | 20 | -8.2 | 26.4 | 16.5 | 0.91 | -18.2 / -28.2 / -38.2 |
| Crude | 1 s | 21 | -6.0 | 27.7 | 16.9 | 0.83 | -16.0 / -26.0 / -36.0 |
| Crude | 2 s | 16 | -3.5 | 18.3 | 12.8 | 0.77 | -13.5 / -23.5 / -33.5 |
| Crude | 5 s | 14 | -2.7 | 16.0 | 12.0 | 0.73 | -12.7 / -22.7 / -32.7 |

Nothing is above zero by a margin that matters, nothing pays one cost unit (10 bp), and the MDEs (12-29 bp) show that a
drift of 10 bp would have been invisible. Status counts at L = 1 s: gas 24 scored, 4 reverted, 2 without a fill; crude 21
scored, 7 reverted, 2 without a fill.

## The placebo (same clock time, days without that release; reported only)
- **Gas:** CME crossed 20 bp in 5 and 3 of 29 placebo days (against 30 of 30 release days); none gave a scored trade.
  The gas threshold is specific to the release.
- **Crude:** CME crossed 8 bp in 24 and 27 of 29 placebo days (against 30 of 30). The crude threshold is crossed on most
  ordinary days within a minute of 14:30 UTC, so a crude "crossing" is mostly not news. Scored placebo trades: 13 and 14,
  mean gross +1.7 and +2.9 bp, 1 lag-filtered each. The release adds no visible edge over the ordinary days.

## What this changes
- **Closed (for 2026-04..10, at 0.5 s and above):** Binance's CLUSDT and NATGASUSDT as lagging followers of CME at EIA
  releases. M444/M443 loses its CME-to-Binance form; no live CME feed is worth buying for it.
- **R369 is unchanged** (frozen; its rule, calendar and runner are not edited). It asks about Lighter, which could still lag
  Binance and Hyperliquid, but R370 says that any such lag would be Lighter's own, not a delay inherited from CME. Two
  readings for R369's FINDINGS, noted in `experiments/eventlag_fwd/NOTES.md`: its gas crossing happens about 1.05 s after T,
  and its crude threshold (8 bp) is crossed on most ordinary days, so its crude cell is a generic lag test, not an
  event test.
- **Open:** in a third of the gas releases Binance is past CME at the time of CME's threshold trade (c > 1). Whether Binance
  *leads* CME there is not tested (a new row in the queue). It would need a CME-side follower, which the owner would have
  to trade through a futures broker (not a perp venue), and the same CME data that cost $0.66 here.

## Limits
- Trade prints, not quotes; the entry is the first matching taker print within 1 s, which can sit in the follower's own
  catch-up. A real order meets a book this read does not see.
- Two exchange clocks, not aligned with each other: a lead or lag of tens of milliseconds is not resolved.
- 30 releases a type in one regime; the thresholds came from minute bars. Reading "INCONCLUSIVE" as "no lag" rests on the c
  table, which is descriptive.
- Binance's real fee for the owner's account (5 bp a side is an assumption) does not matter here: nothing was above zero
  gross by 10 bp.
