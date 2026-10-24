# R309: fixed carry–spot mix does not improve the carry parent

**Verdict: NULL. One candidate trial.** The 50/50 initial-capital mix remains profitable at all three cost
tiers, but fails three of its five frozen gates. It lowers spot risk while substantially diluting carry;
the passive-substitution control also has a higher point-estimate Sharpe. No portfolio is promoted.

Frozen and pushed at `5059417` before the first calculation; PREREG SHA-256
`0beb128cd5ed3b47dc4a7b4ac4ba4949194ed9acdcb6cf6228287658fb9630d2`.
Only the prescribed archived accounts were read. All results are exploratory on spent history, not new
out-of-sample evidence. Program trials after this round: **9,478,758**.

## Capital and money, not a standardized strategy score

Exactly457 UTC days, 2025-07-01 through2026-09-30. Spot compounds within its own account; carry adds PnL on
its fixed initial reference notional. The two pockets never transfer cash or rebalance into each other.
Unallocated cash earns0. A conservative initial carry-inventory entry charge is included at each tier.
Both source-account NAVs and all portfolio NAVs stay positive; that does not establish margin feasibility.

**Historical model PnL per10,000 initial capital**, with both parent models' existing fees and final exits:

| Book | 1x PnL | 2x PnL | 3x PnL | 1x Sharpe | 1x max drawdown |
|---|---:|---:|---:|---:|---:|
| **50% carry +50% spot trend, candidate** | **+274.72** | **+145.22** | **+16.32** | **0.610** | **3.20%** |
| 50% carry +50% risk-matched passive | +306.77 | +228.36 | +149.94 | 0.722 | 3.18% |
| 50% carry +50% idle cash | +406.56 | +330.66 | +254.76 | 5.886 | 0.10% |
| Carry alone | +813.11 | +661.31 | +509.51 | 5.927 | 0.20% |
| Spot trend alone | -263.67 | -370.87 | -476.88 | -0.253 | 12.71% |
| Risk-matched passive alone | -199.57 | -204.60 | -209.63 | -0.199 | 11.78% |
| Plain spot trend, diagnostic | -947.47 | -1,178.11 | -1,402.86 | -0.358 | 29.52% |
| Full passive spot, diagnostic | -2,851.95 | -2,876.34 | -2,900.64 | -0.130 | 70.02% |
| Cash, no-exposure control | 0 | 0 | 0 | 0 (display convention) | 0% |

At2x/3x the candidate drawdown is3.94%/4.86%, versus0.22%/0.40% for carry alone and13.45%/14.19% for trend.
This is a particular initial50/50 allocation; it does not exclude every other mixture. No alternate weight
was searched or selected after this result. Comparators are controls, not additional candidate trials.

## What fees explain

| Component per10,000 | 1x | 2x | 3x |
|---|---:|---:|---:|
| Candidate gross, including funding | +404.93 | +405.05 | +405.18 |
| Candidate funding component (already in gross) | +451.57 | +451.57 | +451.57 |
| Candidate costs | 130.21 | 259.83 | 388.86 |
| Candidate net | +274.72 | +145.22 | +16.32 |
| Carry-alone gross, including funding | +964.91 | +964.91 | +964.91 |
| Carry-alone costs | 151.80 | 303.60 | 455.40 |
| Spot-trend-alone gross | -155.06 | -154.81 | -154.56 |
| Spot-trend-alone costs | 108.62 | 216.05 | 322.32 |

Costs consume32.2% of candidate gross at1x and96.0% at3x. But the added trend pocket loses BEFORE fees too.
Cheaper execution alone cannot rescue that pocket on this window. Carry's1x modeled funding contribution
is903.14, included in its964.91 gross; these are not two separate profit credits. Gross spot changes slightly
between tiers because R229 resimulated self-financing quantities at each fee, rather than repricing one path.

## Frozen decision and paired uncertainty

| Gate | Outcome |
|---|---|
| Candidate1x Sharpe above BOTH parents by0.15 | FAIL:0.610 versus carry5.927 and trend-0.253 |
| Both paired Sharpe lower bounds above0 | FAIL against carry; passes against trend |
| Sharpe above carry +risk-matched passive | FAIL:0.610 versus0.722 |
| Drawdown no greater than trend | PASS:3.20% versus12.71% |
| Total profit positive at2x and3x | PASS:+145.22 /+16.32 per10,000 |

Paired circular-block bootstrap,5,000 draws, primary30-day blocks:

| Comparator | Candidate minus comparator Sharpe | Conditional95% interval |
|---|---:|---:|
| Carry | -5.317 | [-8.089,-2.896] |
| Trend | +0.863 | [+0.481,+1.579] |
| Carry +risk-matched passive | -0.112 | [-1.130,+1.012] |
| Carry +idle cash | -5.276 | [-8.046,-2.868] |

The10/60-day sensitivities do not change those interval signs. The passive-substitution interval spans zero:
its higher point estimate is not proof of a superior population Sharpe. Paired dollar-PnL uncertainty also
spans zero against all four comparators; those profit intervals do not establish a positive mean advantage.
In particular, subtracting the passive blend cancels the common carry sleeve exactly and only compares
the two spot contributions. All such intervals are conditional historical diagnostics, without program-wide
selection correction, not probabilities of live success.

## Reproduction and interpretation

- Runner: `python scripts/run_capital_mix.py --out /a/fresh/directory`.
- `inputs.json` pins13 files; `results/manifest.json` records their hashes, software and all result hashes.
- Five result artifacts reproduce byte-for-byte in a fresh directory, including compressed daily accounts.
- The extra carry entry charge is5.5/11/16.5bp of carry initial capital, because its anchor holds20 pairs.
- Interval normalization is essential: carry CSV END date minus1day equals spot candle OPEN date. Raw carry
  July2..October1 matches spot July1..September30 and retains both models' final exits. A literal-date join
  would be wrong. This source-contract issue was found and fixed BEFORE freezing or outcomes.
- Invented-input tests cover account identities, cost/funding normalization, initial/final fees, actual
  portfolio returns, UTC alignment, missing/duplicate dates, insolvency, frozen inputs and immutable outputs.
- Final full suite:937 tests pass in176.2seconds, two existing archive-dependent skips. All19 targeted
  account/runner tests pass. Metadata integrity:0 errors, the prior13 legacy/import and5 source warnings remain.
- Independent reconstruction from archived spot compounding and carry sums, without the new account helper,
  matches saved daily fields within5e-12 and reproduces the primary bootstrap. No blocking review finding.

The new reusable `lab.capital.segregated` supplies a common capital denominator for future eligible sleeves.
The immediate economic conclusion is to retain the existing carry paper question and reject this specified
spot addition; the result supplies no reason to accelerate trading, buy leverage, or substitute a prop account.
R229's NULL, R285's frozen cross-family forward book and R294's MEXC+Lighter paper lane remain unchanged.

**Limits:** both source models use historical close proxies. Carry preserves known stale-leg and
constant-notional crash biases, lacks intraday mark/margin/collateral/fill verification, and has a slightly
optimistic1x MEXC cost assumption. Spot uses six selected surviving Binance coins, not a broad MEXC universe.
Zero-interest cash is not an actual money-market or index-fund benchmark. Prop rules/eligible instruments and
index futures were not simulated. Positive modeled equity and high historical carry Sharpe do not establish
executable PnL, safety or expected returns. No new data, prospective paper day, trade or gate admission.
