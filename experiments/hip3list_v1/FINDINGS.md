# FINDINGS: hip3list_v1 (R517). Listing-phase carry between HIP-3 dexes does not pay: few entries, and the spreads turn

**Verdict: FAIL (R391's rule on book days, gate 0).**
- The one-sided NW p fails: t 1.31.
- The 2x mean, the trimmed mean and the mean without the two best coins (SMH, XMR) are above 0.

- **Registry:** R517, 1 trial. Program trials become 9,785,760.
- **Reproduce.**
  - The PREREG (sha 2ebf401c) was frozen in commit b29ffdb before the data were fetched.
  - `scripts/fetch_hip3list.py --end 2026-11-20` wrote 160 markets on 10 dexes; 41 had no funding print in the
    window. Provenance: `docs/provenance/hip3list.json`.
  - `run_hip3list.py run` ran once on 2026-11-20. All 9 inputs and 321 data files matched.

## Result: th 20%/yr, K 10, 2025-11-15..2026-11-20
| Cost | Book days (160), %/yr | Calendar days (370), %/yr of book capital |
|---|---|---|
| 1x (7 bp a leg) | +0.84 | +0.36 |
| 2x | +0.26 | +0.11 |
| 3x | −0.31 | −0.14 |

- **Return on capital in use:** +4.7%/yr at 1x, which is about the cash rate.
- **Trades.** 43 eligible listing events gave only 18 trades. The others never reached a 20%/yr spread inside their
  first 21 days, or failed the price check.
  - Mean hold 16 days; exits: 15 by spread, 2 at the phase's end, 1 open.
  - Per trade at 1x: mean +0.42%, 10 of 18 positive.
  - Range: from −1.82% (LRCX, a price gap) to +3.33% (SMH).
- **Why it fails.** Stock-perp spreads in the listing phase are smaller than R516's crypto ones, and several turned
  within days: TSLA, PLTR, AAPL and CRCL lost on funding after entry.
- **Top 10 days hold 247% of the total;** the rest lose.

## What it means
- **The mechanism did not travel.** R516's listing-phase premium came from crypto perps on thin new books. HIP-3
  stock perps list on dexes whose prices follow an oracle every 3 seconds, and whose premia are small. The new books
  do not carry the extremes.
- **Supply was not the problem here** (43 events in 2026): the size of the spread was.

## What this does not show
- **Main-dex crypto against HIP-3 crypto** (HyENA, Felix BTC): out of scope, and HyENA closed in August 2026.
- **Costs.** HIP-3 growth-mode fees are below 7 bp, so 1x may be slightly heavy, but 2x and 3x do not change the
  verdict.
