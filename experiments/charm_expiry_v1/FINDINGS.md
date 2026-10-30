# FINDINGS: charm_expiry_v1 (R296). Deribit's Friday expiry does not move the BTC or ETH perp in any of three readings

**Verdict: NULL.** M303's dose and M317 are TESTED, and so is M309 (the same dose question, queued from the owner's
term list).
- **Trials:** 5, gate 0.
- **Read:** frozen PREREG ffe040b8 (committed and pushed in d1aa2a1 before the run), run 2026-10-22 03:40 UTC,
  `scripts/run_charmexpiry.py`.
  - 7 inputs matched their frozen hashes.
  - Every Deribit flow file read matched the provenance record.
- **Program trials** after this round: 9,478,593 (`registry.program_trials()`).
- **No pass, and no significant opposite sign.** The largest |t| in validation is 1.55.

## What was tested
**The claim.**
- Deribit's BTC and ETH options expire every Friday at 08:00 UTC, settled on the 30-minute TWAP of its index from
  07:30.
- R289 found that a perp move inside that window tends to reverse after 08:00, but too weakly to pass.
- If expiring options cause it, the effect should scale with the position about to expire, or follow the dealers'
  hedge of it.

**The estimate.** Positions come from every Deribit trade in options expiring that Friday, signed by the taker, with
makers read as dealers (R292's assumption). Three readings, on 143-144 Fridays per coin and window:
- **A, dose (M303 / M309):** does the post-08:00 fade of the 07:30-08:00 move grow with the gross expiring position
  within 2% of the price? The test is a slope, so the fade's own mean (read by R289) does not count. h = 60 and 120
  minutes.
- **B, unwind after expiry (M317):** does the perp move after 08:00 with the dealers' delta in the expiring options?
  A dealer hedged against that delta closes the hedge once the options settle.
- **C, unwind inside the window (M317):** does it move from 07:31 to 07:59 with that delta? That is how a hedger
  would close to match the TWAP.

Discovery is 2021-04..2023-12, and validation 2024-01..2026-09.

## Result

| Trial | Discovery t | Validation t | Validation BTC / ETH | Validation by year 2024 / 2025 / 2026 |
|---|---|---|---|---|
| A h60 (dose on the fade) | −0.13 | +0.13 | −0.48 / +0.39 | +0.60 / +0.04 / −0.94 |
| A h120 | −0.59 | +0.44 | +0.34 / +0.40 | +1.73 / −0.26 / −0.91 |
| B h60 (unwind after 08:00) | +1.55 | −1.55 | −1.42 / −0.92 | −2.70 / +0.27 / −1.36 |
| B h120 | +1.23 | −1.03 | −0.99 / −0.79 | −2.04 / −0.26 / −0.38 |
| C (unwind 07:31-07:59) | −0.61 | +1.32 | +1.52 / +0.80 | +2.63 / +0.45 / −0.10 |

The bar is a validation t ≥ 2.58 (Bonferroni over 5) with a positive discovery t.

- **A: the reversal does not scale with the expiring position.** The slope t is within ±0.6 in both windows and at
  both holds.
- **B: dealers' expiring delta does not lead the perp after 08:00.** It is positive in discovery and negative in
  validation (2024 alone −2.70).
- **C: nor does it lead the window move.** Negative in discovery, +1.32 in validation, carried by 2024 (+2.63).
- **B and C swap signs between the windows.** In 2024 the pattern looked like a hedge closed inside the window and
  then reversed (C up, B down). In 2021-23 it was the opposite. That is not a mechanism.

### The rules

| Rule | Window | Trades (per year) | Gross bp | Net 1x / 2x / 3x bp | API bp | t (1x) | Hit |
|---|---|---|---|---|---|---|---|
| A h60: fade on high-dose Fridays | discovery | 175 (64) | +1.3 | −4.7 / −10.7 / −16.7 | −15.7 | −0.74 | 60% |
| | validation | 156 (57) | +13.8 | +7.8 / +1.8 / −4.2 | −3.2 | 1.63 | 61% |
| A h60: fade on low-dose Fridays | discovery | 109 (40) | +9.1 | +3.1 / −2.9 / −8.9 | −7.9 | 0.38 | 54% |
| | validation | 130 (47) | +0.8 | −5.3 / −11.3 / −17.3 | −16.3 | −1.09 | 55% |
| A h120: fade on high-dose Fridays | discovery | 175 (64) | +2.9 | −3.1 / −9.1 / −15.1 | −14.1 | −0.36 | 60% |
| | validation | 156 (57) | +18.9 | +12.9 / +6.9 / +0.9 | +1.9 | 2.28 | 65% |
| A h120: fade on low-dose Fridays | discovery | 109 (40) | +23.2 | +17.2 / +11.2 / +5.2 | +6.2 | 1.54 | 61% |
| | validation | 130 (47) | +2.4 | −3.6 / −9.6 / −15.6 | −14.6 | −0.52 | 48% |
| B h60 | discovery | 47 (17) | +21.8 | +15.8 / +9.8 / +3.8 | +4.8 | 0.92 | 55% |
| | validation | 35 (13) | −10.1 | −16.1 / −22.1 / −28.1 | −27.1 | −1.64 | 43% |
| B h120 | discovery | 47 (17) | +27.0 | +21.0 / +15.0 / +9.0 | +10.0 | 0.86 | 55% |
| | validation | 35 (13) | −12.0 | −18.0 / −24.0 / −30.0 | −29.0 | −1.30 | 46% |
| C | discovery | 48 (17) | +1.9 | −4.1 / −10.1 / −16.1 | −15.1 | −0.44 | 54% |
| | validation | 34 (12) | +8.8 | +2.8 / −3.2 / −9.2 | −8.2 | 0.43 | 62% |

Costs are manual web, 3 / 6 / 9 bp per side; API is 8.5 bp per side. A trade's t is over trades.

- **The high-dose fade at h120 looks good in validation** (+12.9 bp net at 1x, t 2.28). In discovery the same rule
  nets −3.1 bp. The low-dose fade did the opposite: +17.2 bp in discovery, −3.6 bp in validation.
  - Which Fridays carried R289's reversal changed between the windows, and the expiring position does not predict
    which.
  - This is what the slope test reads (t +0.44). Picking the validation half would be choosing on the result.
- **B and C trade 12-17 times a year** (|x| ≥ 1). No rule is net positive at 1x in both windows.

### Descriptives

| | Fridays | Median expiring options | Median near-money position / ADV | Median \|dealer delta\| / ADV | Dealers net long delta |
|---|---|---|---|---|---|
| BTC discovery | 144 | 56 | 0.23% | 0.13% | 53% of Fridays |
| BTC validation | 143 | 75 | 0.89% | 0.47% | 41% |
| ETH discovery | 144 | 49 | 0.17% | 0.22% | 44% |
| ETH validation | 143 | 67 | 0.29% | 0.22% | 46% |

ADV is the perp's mean daily quote volume over the previous 30 days.

- **The dealers' expiring delta is a fraction of a percent of a day's perp volume:** 0.47% (BTC) and 0.22% (ETH)
  at the median in 2024-26.
  - The two hours after 08:01 carry 6.9% of a Friday's volume (median, both coins, 2024-26).
  - So even if all of the hedge were on Binance and closed then, it would be about 7% (BTC) and 3% (ETH) of that
    volume. The share is computed against the 30-day ADV, not that Friday's own volume.
- **Its sign is close to a coin flip** (41-53% of Fridays long). R292 found the gamma one-sided (short on 76-92% of
  days); the delta is not.

## What this does and does not show
**It shows,** for 2021-2026 BTC and ETH, with positions from taker-signed Deribit trades:
- R289's settlement-window reversal does not grow with the position expiring near the money;
- the dealers' delta in expiring options does not move the Binance perp, inside the TWAP window or in the two hours
  after it.

**It does not test:**
- **Deribit's own index and TWAP.** Prices are Binance perp closes at 07:30 and 08:00.
- **Hedges on Deribit's futures,** where many option dealers hedge. A Deribit-only effect would not show here.
- **Open interest.** Taker positions are net and miss trades between two makers or two takers; the recorder of
  Deribit chains (from 2026-10-21) will hold true open interest for forward Fridays.
- **The 48 hours before expiry** (M289, pinning), and max pain (M175).
- **Black-76 deltas.** The step delta misreads strikes within about 0.4% of the price at 30 minutes to expiry.
- **SOL** (no inverse Deribit options).

## Costs
Manual web at 3 / 6 / 9 bp per side (1x / 2x / 3x), API 8.5 bp. No rule is positive at 1x in both windows.
- The only rule positive at 2x in validation, the high-dose fade, loses at 1x in discovery.

## Read against the program
- 5 trials, each against t 2.58 (Bonferroni over 5). No validation |t| reaches 1.6.
- The program's 9.48M trials do not change a NULL.
- The power was low before the run (72% for a correlation of 0.25). This rules out large effects only.

## Next
- **M303's dose, M309 and M317 are TESTED (NULL).** R289's Friday reversal stays a small, unexplained pattern. It
  does not go to a batch.
- **The three Deribit nulls agree** (R292 gamma, R295 flow direction, R296 expiry). Deribit's dealer and taker
  positions are small next to Binance perp volume, and none of them moves the perp at the scales tested.
- **Still open on options data:**
  - M310 (vanna after FOMC). It has few events, so its power is low.
  - M289 (48 h pinning) and M175 (max pain), on the chain recorder's true open interest. That needs forward
    Fridays.
