# FINDINGS: xyzns_wknd_v1 (R464), trade.xyz index, commodity and FX perps over the weekend

**Verdict: NULL. R462's weekend fade does not carry over to trade.xyz's 14 non-stock markets.** M520 is closed in this
form.

- **Both decision cells are flat in sample A**, the sample that decides:
  - |W| ≥ 25 bp: +2.7 bp per market-weekend, p 0.86;
  - |W| ≥ 50 bp: +1.9 bp, p 0.93.
- **Costs make both lose.** The 1x nets are -4.4 and -4.1 bp.
- **Sample B (6 weekends) is strongly positive** (+75 and +102 bp, p 0.09). By the frozen rule it cannot rescue A.
- **The stock-perp result stays as it was.** R462 is unchanged and R463 still decides it forward. This lane says the
  overshoot is not a general trade.xyz weekend effect in A; it is at most a stock-perp effect. R432 found the same
  NULL on Binance's index and commodity perps.

Run: `python scripts/run_xyzns.py`, 2026-11-11, after the freeze (PREREG sha256 `34d4400a`, commit `98f70dc9`).
- The PREREG verified and its 10 inputs matched.
- 28 bar and funding files matched `data/xyz_ns/manifest.json` (`results/run.log`).
- The bars were fetched after the freeze by the frozen `scripts/fetch_xyz_ns.py bars`. Provenance is in
  `docs/provenance/xyz_ns.json`: 14 markets, hourly candles from 2026-04-17 (the API's 5,000-candle limit) or the
  market's listing, to 2026-11-09 23:00 UTC, no holes.
- **Events:** A 228 market-weekends (13 markets; HO was listed in October), B 83 (14 markets).
- **Skipped:**
  - 56 holiday market-weekends;
  - 22 where the market was listed less than 7 days before Friday (HO; GBP before late May);
  - 3 unpriced.

## Decision cells
`all` markets, exit X1 (two hours after the Sunday reopen), bp per market-weekend, fade side. g = price + funding,
before trading costs.

| cell | n A | wk A | mean A | sd A | hit A | p A | Holm | MDE80 | unit | net 1x/2x/3x (A) | n B | wk B | mean B | p B |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D1 θ 25 | 122 | 18 | +2.7 | 105 | 54% | 0.86 | 1.00 | 27 | 7.1 | -4.4 / -11.5 / -18.7 | 40 | 6 | +75.3 | 0.09 |
| D2 θ 50 | 78 | 17 | +1.9 | 107 | 49% | 0.93 | 1.00 | 34 | 6.0 | -4.1 / -10.1 / -16.1 | 22 | 6 | +102.3 | 0.09 |

- Both cells have A's sample sizes (≥ 60 events over ≥ 10 weekends), so the lane is not INCONCLUSIVE.
- Neither Holm p is below 0.05, so neither is PASS or PARTIAL.
- **Power:** the MDE80 is 27-34 bp, so an effect the size of R462's (+42 bp) would most likely have been seen. An
  effect of 10 bp, the size R432's slopes imply, could still be there unseen, but it would not clear 2 cost units.
- **Read against the program's 9,785,142 trials,** a NULL here needs no correction.

## Diagnostics (not decided on; 38 more cells in `results/cells.csv`)
- **By class** (sample A, exit X1, |W| ≥ 50 bp unless stated):

  | class | median \|W\| (θ 0) | n | mean | p | note |
  |---|---|---|---|---|---|
  | metal | 34 bp | 29 | +28.1 | 0.22 | the only class with a fade-signed mean above 2 units; not significant |
  | energy | 119 bp | 40 | -12.2 | 0.70 | the weekend move slightly continues |
  | index | 24 bp | 8 | -28.2 | 0.03 | 8 events over 6 weekends; follows rather than fades |
  | fx | 7 bp | 1 | - | - | FX weekend moves are tiny |

- **FX at θ 0:** +7.9 bp, n 49 over 18 weekends, hit 71%, sd 16 bp, p 0.0001 in A; +5.5 bp in B (p 0.06).
  - This is one cell of 40; a Bonferroni bound over the 40 cells is p 0.004. Against the program's trials it is not
    a discovery.
  - It clears 1 cost unit (5.8 bp) but not 2 (net 1x / 2x / 3x +2.1 / -3.7 / -9.5).
  - Median |W| is 7 bp and the mean gain is about |W|: the weekend drift is given back in full. Two sources fit, and
    last trades cannot separate them: the external FX market barely moves at the weekend, so the internal drift is
    noise; or the last trade bounces across a thin weekend spread.
  - Only 4 FX events in A reach |W| ≥ 25 bp, so the trade is small and rare.
  - It does not reopen M520 (stop rule), and no lane is queued for it.
- **Exit at Monday 10:00 (X2):** means are larger and far noisier (sd 180-280 bp); no cell is significant.
- **Slope of the E→X1 move on W.** Computed after the run, not pre-registered.
  - A: +0.01, no give-back at all.
  - B: -1.27, a large reversal over only 6 weekends.
  - The A/B contrast matches the decision cells. October-November 2026 weekends reverted strongly, in these markets
    and in R462's stocks (R462's B: +36 bp).
- **Funding** is negligible: the mean f_x1 is +0.5 bp in A.

## Costs
- **One unit** (R462's): growth-mode markets 2 × 0.9 bp + 4 bp of slippage = 5.8 bp; GOLD 22 bp (not eligible for
  growth mode).
- The mean unit is 7.1 bp at θ 25 and 6.0 bp at θ 50.
- Slippage is assumed. These books were not recorded before 2026-11-11.

## What this changes
- **M520 closes as NULL.** Its parent M515 (stock perps) is unaffected.
- **M447** (re-anchoring of commodity perps at the CME reopen) gets a note: on xyz in A, nothing reverts by reopen
  + 2 h.
- **R459** (oil on Lighter, forward) keeps running as frozen. On xyz in A, the energy cells continued slightly rather
  than reverting; that is a different venue and exit.
- **No forward lane is earned.** The B strength and the FX θ 0 cell are recorded as observations only. Fresh weekends
  in R463 (stocks) are the lab's live test of the weekend overshoot.
