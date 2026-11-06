# FINDINGS: boroslock_v1 (R412). A Boros funding lock delivers what it locks; the margin over T-bills is thin

**Verdict: LOCK_HOLDS on Binance and on Hyperliquid, by the PREREG's four checks. A measurement: 0 trials, gate 1.**

- The run: `run.log`, 2026-11-06 01:48 UTC, PREREG `bbbd3b48dab9`, 11 inputs and 551 Boros files matched. One run.
- Results: `results/summary.json`, `results/entries.csv` (3,250 entries) and `results/settlements_by_market.csv`.
- Scope: 67 matured markets (26 Binance, 41 Hyperliquid), BTC and ETH, maturities 2025-09-26 to 2026-09-25.

**The runner's own label for Binance is wrong.** `run.log` prints LOCK_DEVIATES for Binance because of a bug in
`verdict()`: `(median_abs or 1e9) <= 10` treats a median of exactly 0.0 as missing. The PREREG's rule applied to the
runner's own numbers in `summary.json` passes all four checks (table below). The frozen runner is not edited. R413's
code must not use `x or default` on a number.

## The four checks (PREREG decision)

| Check (LOCK_HOLDS needs all four) | Bar | Binance | Hyperliquid |
|---|---|---|---|
| 1. Venue funding events with a Boros settlement | ≥ 99% | 99.96% (2 of 5,513 missed), yes | 99.70% (144 of 48,247), yes |
| 2. Settlements within 1 bp APR of the venue | ≥ 99% | 99.96%, yes | 99.98%, yes |
| 3. Median \|fidelity\| | ≤ 10 bp APR | 0.0, yes | 0.0, yes |
| 4. 95th percentile \|fidelity\| | ≤ 50 bp APR | 0.0, yes | 3.6, yes |

- Fidelity is realized − locked: (venue funding − Boros floating) / τ, over (entry, maturity].
- **Binance:** every entry's fidelity is 0 to floating-point precision (max 2 × 10⁻¹³ bp). Boros copies Binance's
  funding exactly. Its two misses and two off settlements are around listings and moved no entry.
- **Hyperliquid:**
  - mean fidelity is −0.3 bp APR and the worst is 54 bp APR;
  - the BTC mean is +0.9 bp and the ETH mean −1.6 bp.

## Where the Hyperliquid oracle slipped (post-hoc, descriptive)
- **2025-09-09 17:00 to 09-10 06:00 UTC:** 14 hourly settlements were missing on the first BTC market (6).
- **2025-10-10, the crash:** the 22:00 hour was missed. The 23:01 settlement then printed 107% APR (BTC) and −269% (ETH)
  against Hyperliquid's 10.95% and −201% for that hour.
- **Both were in the October 2025 markets.** Entries spanning them deviated by up to 21 bp APR (BTC) and 54 bp (ETH).
- **Every other large single-settlement difference is a market's first paid settlement after listing.**
  - It often follows hours with none, as a catch-up.
  - Market 17 (ETH, 2025-10-17) shows the pattern: it was listed at 02:00, then had 12 missed hours and a first
    settlement at 15:04.
- **The lesson for R413:** a lock is exact only while the oracle runs. A stall or a crash hour moves it by tens of bp
  APR on a short hold. The forward lane must log every missed hour.

## What the lock paid (described, not decided on)
Mean over daily entries, in % a year on notional.

| | Binance | Hyperliquid |
|---|---|---|
| Locked (bid − Boros fees), mean / median | 3.91 / 4.58 | 5.86 / 5.84 |
| Realized | 3.91 | 5.86 |
| Naked funding (short perp, no lock) | 3.34 | 6.59 |
| Naked − locked, 5th / 95th percentile | −5.3 / +3.5 | −4.7 / +4.6 |
| Locked − T-bill, mean / median | +0.08 / +0.72 | +2.07 / +1.98 |
| Share of entries with locked > T-bill | 54% | 78% |
| Share with locked ≥ T-bill + 1% | 47% | 59% |
| Median bid-ask spread at entry | 4.1 bp APR | 7.4 bp APR |

**The lock removes the variance, not the level.**
- Locked against naked swung from −5 to +5 points a year either way.
- On average the lock cost Hyperliquid 0.7 points a year and gained Binance 0.6.
- **By month of entry (Hyperliquid):**
  - the locked rate fell from 10.2% (2025-09) to 3.0% (2026-04);
  - it was back to 7.9% by 2026-09;
  - the T-bill held near 3.7-4.0%.
- The live quote on 2026-11-06 was 8.4-8.7% for BTC.

**Indicative carry against the T-bill, in points a year.**
- Formula: bid − m × Boros fees − m × 0.30% / τ − T-bill.
- The 0.30% is a stated spot-plus-perp round trip (Binance VIP0 taker), not measured.
- The by-hold split is post-hoc, from `entries.csv`.

| Hold to maturity | Binance 1x (share > 0) | 2x | 3x | Hyperliquid 1x (share > 0) | 2x | 3x |
|---|---|---|---|---|---|---|
| 7-30 days | −6.6 (0%) | −13.6 | −20.5 | −4.3 (13%) | −11.3 | −18.3 |
| 30-90 days | −2.1 (18%) | −4.6 | −7.0 | −0.7 (38%) | −3.4 | −6.1 |
| 90+ days | −1.2 (42%) | −2.3 | −3.5 | −0.6 (13%) | −1.6 | −2.7 |
| All | −3.6 (15%) | −7.5 | −11.4 | −2.7 (22%) | −7.7 | −12.7 |

- **Net of an entry and exit on the hedge legs, the average historical lock did not beat a T-bill at 1x.**
- Short holds pay the round trip over too few days.
- Long holds were mostly opened in 2026's low-rate months: at 90+ days the mean locked rate was 4.1% on Hyperliquid
  and 3.6% on Binance.
- **The lock beat the T-bill only when entered at a high locked rate with enough time left.** At today's 8.5% and 49
  days to the December maturity, the same arithmetic gives about +2 points before margin capital. That is a
  calculation, not a measured result.

## Reading
- **The instrument is sound as a lock.**
  - Boros paid the venue's funding on 99.7-99.96% of events.
  - Realized equalled locked to the basis point at the median, on both venues.
  - The "controlled gain" the owner asked for exists mechanically: the income is fixed at entry.
- **The gain is not large.**
  - Locked minus T-bill averaged +2.1 points (Hyperliquid) and +0.1 (Binance) on notional.
  - That is before the spot and perp legs' costs, margin capital and smart-contract risk.
  - After an indicative round trip it averaged below the T-bill.
- **The rule that follows (for R413, to be frozen there):**
  - open a paper lock only when bid − fees − round trip / τ − T-bill clears a stated floor;
  - record the depth at the bid and every missed oracle hour;
  - settle each lock against the venue's actual funding.
- **Program context.** The read is against 9,784,336 program trials. This round adds none and tests no return.

## Limits
These are as stated in the PREREG:
- size at the bid unknown;
- spot and perp fees, basis, margin and liquidation not measured;
- smart-contract, oracle-governance and venue risk not measured, nor jurisdiction;
- overlapping entries, not independent draws;
- a 14-month window.

The oracle-slip and by-hold analyses above are post-hoc and descriptive.
