# FINDINGS: vpin_v1 (R291). VPIN built from true trade sides adds no volatility forecast, and plain volume flags crash hours better

**Verdict: NULL.** Exact-side VPIN does not forecast BTC, ETH or SOL volatility beyond a HAR model with volume. Out of
sample it makes the forecast worse.
- **Trials:** 4, gate 0.
- **Read:** frozen PREREG fb900f59, run 2026-10-21 22:35 UTC, `scripts/run_vpin.py`, 7 inputs checked.
- **Program trials** after this round: 9,478,559 (`registry.program_trials()`).
- **Costs at 1x/2x/3x:** not applicable, because there are no trades.

## What was tested
The owner's reel (instagram.com/reel/DevaMerNUk_) says market makers track VPIN to see informed traders coming and
pull their quotes before a crash or a spike.

**VPIN:**
- 50 equal-volume buckets per average day, with a point-in-time size;
- the mean |buy − sell| / volume over the last 50 buckets;
- computed from the 1-minute taker split of Binance perps (**exact**), and from bulk volume classification (**BVC**),
  the price-change guess VPIN was built on.

**Question:** does adding VPIN to a HAR model with relative volume and hour of day improve the forecast of the next
hour's (or next day's) realized variance?
- **Fit:** 2021-04..2023.
- **Read:** 2024-01..2026-09, about 24,000 hours per coin.

## Result

| Variant | Discovery VPIN coefficient (t), BTC / ETH / SOL | Validation pooled DM t | Validation MSE cut |
|---|---|---|---|
| **exact, next 1 h (primary)** | −1.97 (−4.3) / −1.12 (−2.7) / +1.21 (+3.9) | **−12.46** | **−0.88%** |
| BVC, next 1 h | −0.85 (−5.8) / −0.77 (−5.1) / −0.17 (−1.0) | +0.19 | +0.01% |
| exact, next 24 h | −0.82 (−0.5) / −0.76 (−0.6) / +4.30 (+4.1) | −10.39 | −3.23% |
| BVC, next 24 h | +0.00 (0.0) / −0.61 (−1.7) / +0.38 (+0.8) | −2.14 | −0.14% |

A negative DM t means the VPIN model forecasts worse than the base. The rule needed all three discovery coefficients
positive, DM t ≥ 2 and an MSE cut of at least 1%. No variant meets any of the three.

**Base model, validation R²:** 0.69 / 0.64 / 0.69 at 1 h, and 0.50 / 0.44 / 0.53 at 24 h. Exact VPIN changes these
by −0.005 to +0.001 at 1 h, except SOL at 24 h (0.53 to 0.47).

## Why: what VPIN is made of here
**Discovery correlations, BTC / ETH / SOL:**

| | Exact VPIN | BVC VPIN |
|---|---|---|
| with log relative volume (24 h) | +0.20 / +0.09 / +0.29 | **+0.58 / +0.53 / +0.59** |
| with log realized variance (24 h) | **−0.26 / −0.39 / +0.13** | +0.21 / +0.07 / +0.30 |
| with each other | +0.59 / +0.51 / +0.39 | |
| mean level | 0.088 / 0.083 / 0.072 | 0.208 / 0.205 / 0.177 |

- **BVC-VPIN is mostly volume.** That is Andersen and Bondarenko's point: its "toxicity" comes from classification
  error that scales with volume and volatility. BVC also more than doubles the measured imbalance (0.21 against 0.09
  for BTC).
- **On BTC and ETH, true one-sidedness falls when volatility rises.** In volatile hours both sides trade hard, so
  each bucket is balanced, and calm hours are the one-sided ones. The coefficient after controls is negative on BTC
  and ETH. That is the opposite of the "toxic flow precedes turmoil" story.
- **Exact VPIN drifts upward:**
  - BTC: 0.075 (2021) → 0.087 → 0.098 → 0.101 → 0.116 → 0.124 (2026);
  - ETH and SOL also rise.

  A coefficient fitted in 2021-23 meets a different level in 2024-26, which is part of why the out-of-sample errors
  grow. This drift is post hoc and not decided on. A likely cause is a change in who provides liquidity on Binance.

## The crash claim (reported, not decided on)
- **Event:** an hour whose |log return| exceeds 4 trailing standard deviations.
- **Deciles:** of the measure known at the hour's start. Decile edges come from discovery per coin, and counts are
  pooled over the three coins.

| Decile | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Exact VPIN, disc. % | 0.51 | 0.51 | 0.60 | 0.65 | 0.69 | 0.72 | 0.96 | 1.09 | 0.84 | 1.51 |
| Exact VPIN, valid. % | 0.31 | 0.38 | 1.03 | 0.30 | 0.77 | 0.59 | 0.59 | 0.60 | 0.82 | 0.96 |
| Relative volume, disc. % | 0.08 | 0.24 | 0.35 | 0.42 | 0.49 | 0.61 | 0.65 | 0.80 | 1.18 | **3.28** |
| Relative volume, valid. % | 0.25 | 0.28 | 0.38 | 0.39 | 0.42 | 0.62 | 0.81 | 0.98 | 1.04 | **2.96** |

**Discovery, top decile against bottom:**
- Exact VPIN separates crash hours by about 3x (1.51% against 0.51%).
- Plain relative volume separates them by about 40x (3.28% against 0.08%).

**Validation:** 44% of the validation hours sit in discovery's top VPIN decile, because of the drift. The rate there
is 0.96%, against 2.96% in the top decile of volume.

**In short:** for "is something about to happen", volume already says it louder.

## What this does and does not show
- **It shows** that VPIN computed from true trade sides gives no volatility forecast beyond volume, recent
  volatility and the hour of day. It is not useful as a crash alarm next to plain volume. This holds on BTC, ETH and
  SOL perps over 2021-2026, at minute resolution.
- **It shows** that the VPIN of the papers (BVC) is largely a volume measure here, which supports the Andersen and
  Bondarenko critique.
- **It does not test** whether market makers do pull quotes when flow is one-sided. That needs quote and depth
  history; the tape and depth recorders have weeks, not years.
- **It does not test** the trade-by-trade order inside a minute, other bucket sizes, or the signed (directional)
  version. Signed taker imbalance is covered by the atlas (R185) and M264.
- **It does not say that order-flow toxicity is unreal.** Adverse selection of maker fills is real: R193 and
  arXiv 2502.18625 found it. This aggregate gauge just does not measure it better than volume does.

## Next
- **M085 is TESTED (NULL)** and leaves the queue. A maker-entry filter (M227) should use measured markouts on the
  recorded tape, not VPIN.
- **Kept for the volatility work:** the HAR with relative volume is a strong base (R² 0.64-0.69 at 1 h). That is the
  bar any later volatility signal (dealer gamma, M308, now R292) has to clear.
