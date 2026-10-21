# FINDINGS: xvfac_v1 (R276). Cross-venue factors are NULL; only the reference (Binance funding level) clears the bar

**Verdict: PARTIAL by the mechanical rule, NULL on the question.** None of the five cross-venue factors clears the
reality check. The registry row reads PARTIAL only because the reference factor, bn_fund_3d, passes. The PREREG
says the reference "on its own earns nothing either way", so nothing from this family goes further.

- **Sample:** 18 series (6 factors × 24 / 72 / 168 h). 2,069 dates, 700 coins, the top 150 by Binance volume each day.
- **Costs:** 7 bp per side.
- **Registry:** R276, 18 trials. Program trials become 9,478,319.
- **Reproduce:**
  - prereg sha 38936694, frozen in commit b44b526 before any forward return was read;
  - `python scripts/qx_run.py experiments/xvfac_v1` at that commit;
  - the factor table rebuilds byte for byte.
- **Reality check:** the null's 95th percentile for max |t| is 4.94 (blocks of 7 dates).

## The cross-venue factors (rank IC, NW t; long-short is top minus bottom quintile, bp per day)
| Factor | Best h | Rank IC | t | RC p | LS bp (t) | 24 h book, long the side the IC favors: net %/yr at 1x / 2x / 3x |
|---|---|---|---|---|---|---|
| fund_gap_3d (Binance minus Gate funding, 3 d) | 72 | -0.015 | -4.24 | 0.124 | -5.6 (-0.41) | -3.0 / -28.1 / -53.2 |
| fund_gap_7d | 72 | -0.011 | -3.07 | 0.432 | +4.4 (+0.30) | -7.9 / -22.4 / -36.9 |
| hl_fund_gap_3d (Binance minus Hyperliquid) | 168 | -0.023 | -3.15 | 0.406 | -60.4 (-2.19) | +28.5 / +3.1 / -22.3 |
| price_gap_dev (Binance rich to Gate vs its norm) | 24 | -0.007 | -2.74 | 0.563 | +1.2 (+0.25) | -77.3 / -150.2 / -223.1 |
| vshare_chg (volume moving to Gate) | 24 | -0.003 | -1.38 | 0.986 | +8.1 (+1.82) | -45.3 / -61.0 / -76.7 |

- **The 24 h book** is the PREREG's: s × LS - 2 × m × 7 bp × (top + bottom turnover), with s the sign of the 24 h
  rank IC.
  - Only hl_fund_gap_3d is positive at 2x, and it fails the reality check (p 0.41 at its best horizon).
  - Turnover kills price_gap_dev: 1.43 of the book a day.
- **Cost parity** (Codex's review on #7):
  - The pass rule charges 2 × 7 bp × the mean turnover. The engine's net also charges the first day's entry.
  - Recomputed from the engine's complete paid cost (its gross minus its net), every factor's 24 h net moves by at
    most 0.02 bp a day: bn_fund_3d +10.43 / +4.68 / -1.07.
  - No decision changes.
- **Rank ICs point one way.** Every funding-gap IC is negative: when Binance pays more than Gate or Hyperliquid, the
  Binance perp does slightly worse, net of funding. That is the direction a crowding story predicts. The size is
  0.01-0.02 rank IC, below the family's noise.

## The reference
- **bn_fund_3d** (Binance funding over 3 days):
  - rank IC -0.038 at 168 h (t -6.14, RC p 0.0095) and -0.023 at 72 h (RC p 0.026);
  - quintile means at 24 h are monotone: +13.0 / +11.8 / +3.7 / -0.4 / -3.1 bp per day, net of the funding a long
    pays;
  - long the bottom quintile and short the top nets +10.4 / +4.7 bp per day at 1x / 2x;
  - at 3x it is about -1.0 bp per day: turnover is 0.23 + 0.18 a day, so 3x costs about 17 bp a day.
- **This conflicts with R190.** R190's funding carry made about 1.3%/yr. Here the long-low / short-high funding
  quintile book makes about 38%/yr net at 1x on paper (59%/yr before costs).
- **Differences to reconcile:**
  - the universe (top 150 by volume, against R190's);
  - the return (net of funding paid, versus price only);
  - the weighting (quintiles, against R190's book);
  - the horizon.
- **This is a candidate idea, not a finding.** It goes to the queue as M263: a cross-sectional funding-level book,
  net of funding, with its own frozen lane. The lane must disclose this result as seen. Its first job is the
  reconciliation with R190 on the same days.

## Reading
- **Against program trials (9,478,319):** the cross-venue factors are noise-level. The best non-reference |t| (4.24)
  is below the family null (4.94), let alone the program.
- **Pre-committed:** no cross-venue factor passed, so there is no screen lane, no reserved-batch entry and no KuCoin
  replication. M262 is TESTED: NULL.
- **What this rules out:**
  - the funding gap between venues predicts the Binance perp's next days;
  - so do the Binance-Gate price gap and the shift of volume to Gate;
  - each rank IC is at most 0.02 in size, at this universe and these horizons.
- **What R275 shows instead:** the funding gap is worth collecting directly (carry on both venues). It is not worth
  using to predict one venue's price.
