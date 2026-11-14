# R330: this close-level probability model adds no edge

The preselected rule is **NULL_INACTIVE**: it declines all 178 validation
opportunities. Zero PnL comes from inactivity. Its conditional probabilities
also score slightly worse than a simple historical frequency on the same cases.
Every active comparison loses at the registered 2x/3x costs. Nothing here
establishes positive expected executable return or new prospective evidence.

Round verdict PARTIAL describes the completed probability/accounting component;
it does not promote the preselected policy. The exact method is M412 /
OWN26-LEVEL-PROBABILITY. Other support, intrabar, flow and calibration variants
remain open rather than being declared tested by this result.

## What was frozen and tested

Research code, finite specification and eight held input identities were
committed/pushed at **c4893c0** before model statistics. PREREG SHA-256:
`0cb237666df7d3c1326228e3f6b258d71a0981c1a0327e5ac6edbc2b87f2f48c`.
Training-only model and records were committed/pushed at **caf9343** before
calibration/validation. Model SHA-256:
`b87e34fe8a42ae9fc36223c3329c0143f060f82074acec78606b37af26a83db3`.
No parameters, threshold, feature, symbol, model or winner changed afterward.

Fixed BTC control, ETH, SOL and WIF; 72-hour prior CLOSE extrema, excluding the
decision close; proximity within 0.25 sigma12 at 00:00 UTC; entry delayed one
hour. Labels are entry-relative hourly-close continuation, reversal, or a
12-hour timeout. Prices overshooting a barrier use their observed close. This
definition supplies a reproducible hourly proxy; actual intrabar support
crossing, first-touch freshness, order flow and execution require other inputs.
M323/R306 MSNR, M203 pivots/fractals and M044 flow meta-labels retain their own
exact scopes and verdicts.

All historical dates/assets had already been read by other project studies.
Temporal fitting separation prevents this model from learning the later rows;
it does not turn the archive into a new unseen sample.

| Window | Daily asset opportunities | Qualified events | Break / rebound / timeout |
|---|---:|---:|---:|
| Training, May–August 2025 | 492 | 116 | 16 / 26 / 74 |
| Calibration, September–December 2025 | 488 | 101 | 21 / 19 / 61 |
| Validation, January–September 2026 | 1,092 | 178 | 43 / 36 / 99 |

All 2,072 opportunities remain in the compact observations, including days far
from a level. The independent oracle reconstructed 395 close-grid labels. These
fixed four MEXC assets have complete needed proxy paths/funding certificates for
their qualified events. This does not cure R311's different 117-pair/Lighter
execution gaps or certify any historical close as executable.

## Probability is separate from payoff and reliability

Global probabilities use three class counts with a fixed pseudocount. The
conditional model adds only approach/recede cells, shrunk toward that global
frequency. Training had **115 approach events and one recede event**. The latter
fails the predeclared minimum of 20; its probability stays unknown. The remaining
conditional forecast is almost constant, so it supplies little new information.

Class payoff magnitudes are learned separately from hit frequencies. Each policy
uses the same fixed 2x decision cost plus a 0.25-sigma reserve. That reserve is a
heuristic, not a measured confidence bound. Both probability policies abstain
throughout both later windows; thresholds were not relaxed to create trades.

| Paired probability comparison | Calibration | Validation |
|---|---:|---:|
| Common labeled cases | 97 | 177 |
| Conditional minus global Brier loss | +0.00077950 | +0.00116844 |

Positive means worse. Unpaired averages are misleading here: validation has
177 conditional forecasts versus 178 global forecasts. On the **same 177**
validation labels, conditional Brier is 0.60610433 versus global 0.60493589.

The conditional model predicts about **14.0% continuation**, whereas 24.3% of
those validation cases continue; timeout prediction is 63.4% versus 55.9%
observed. These are empirical frequencies with dependent/sparse observations,
not calibrated confidence intervals. Fixed reliability bins retain event/day/
14-day-block counts. Joint 14-day circular shifts are dependence diagnostics,
not valid exchangeable-null p-values. No significance, calibrated uncertainty,
or program-wide multiplicity control is claimed; R321's failed acceptance stays.

## One common capital account and explicit costs

Each alternative uses **one 10,000-USDT account across four coins**, with 500-USDT
entry notional per coin and at most 2,000 initial gross. Same quantities,
decisions and exits at all three cost tiers. A chronological 3x cash shadow
admits entries for every tier using 100% entry-notional reserves. There is no
leverage increase, short-sale principal credit or sum of four 10,000 accounts.
Marked gross, intrahorizon maintenance/liquidation and realized risk equivalence
remain unverified.

Costs are a single **8-bp-per-side execution/fee proxy**, applied to entry and
exit notional at 1x/2x/3x. No second spread is added. Funding uses signed base
quantity and each event's traded-close notional, not verified fair/index cash.
An interval needs both adjacent cycle fields to certify the exact funding gap.
Admitted unknown inventory/cash persists and stops new risk; an unentered
candidate's missing outcome cannot poison the account. All failures/inactivity
remain represented.

Validation proxy totals in USDT, on the same initial capital:

| Fixed policy | 1x | 2x | 3x |
|---|---:|---:|---:|
| Preselected conditional probability | 0.00 | 0.00 | 0.00 |
| Global-frequency probability control | 0.00 | 0.00 | 0.00 |
| Always follow continuation | +53.86 | **−88.73** | −231.32 |
| Always trade the rebound | −339.03 | −481.62 | −624.21 |
| Long on the same event times | +93.23 | −49.36 | −191.95 |
| Cash | 0.00 | 0.00 | 0.00 |

At 2x, the continuation control is **+201.46 price −5.02 funding −285.18 cost =
−88.73**. Its 1x gain does not establish an executable edge. The long control
does better on this same validation sample; continuation adds no demonstrated
benefit to it. Calibration continuation totals are −215.11/−295.73/−376.34;
the calibration rebound control's +53.89 at 1x also becomes negative at 2x/3x.

WIF contributes 199.79 of the continuation book's 201.46 gross price gain;
the remaining three coins contribute approximately 1.68 combined. This
concentration is retained, not removed or converted into a post-hoc WIF-only
winner. No such new variant was run. Full daily risk/decomposition and all
per-coin totals are in the result, with `matched_empirical_risk=false`.

All 122 calibration and 273 validation days remain in each proxy account,
including zero-activity days. Complete proxy arithmetic does not verify owner
fees, first-seen quotes/depth, lot/rule vintages, fills, sessions or fair funding
notionals. `actual_executable_net` and calibrated uncertainty remain null.

## Audit failure, correction and reproducibility

The first frozen independent checker **failed**: its entry-notional guard
compared signed quantity times price to positive 500, rejecting shorts. The
original checker and [failure](original_audit_failure.json) remain intact; no
original PASS is claimed and financial outputs were not recalculated or changed.

Audit-only code **45e7985**, frozen before its corrected historical invocation,
changes that one guard to compare **absolute** entry notional, plus the named
checker identity. The [correction](audit_correction.md) binds new code/tests and
the original result hash. Two new tests exercise the entire invented long/short
protocol and literal source-diff scope; the old checker fails that fixture.
No new scientific strategy variant or new research outcome is introduced.

The corrected independent raw-source/Fraction oracle passes **2,072 causal
signals, 395 close-grid labels, 36 shared accounts and 7,533 financial events**
(2,511 closed-position repetitions across policies/costs, not independent
opportunities). It imports no production label/probability/account calculations.
Three result artifacts reproduce byte for byte with zero network, including
through the common `lab account --levels` entry point. Compact accounts export
is 1,169,113 bytes; observation export 34,726; result 139,793.

Full discovery before research freeze: **1,404 tests, two skips, 191.605 s**.
After the audit-only regression: **1,406 tests, two skips, 196.843 s**. The
pre-freeze independent peer review covers 26 literal checks at the exact
financial-component hash; runner cutoffs, actual source fitting and the whole
system were not peer certified. Its three discovered capital/unknown-state
defects and pre-freeze fixes remain in [financial review](financial_review.md).

Six conservatively counted fixed policies, two probability models and 36
window/cost/account cells are distinct counts. Program trials become
**9,478,976**; no confidence or market-eligibility claim bypasses that adaptive
history. Original frozen files, old source objects/aliases and registry prefix,
R311/R321 verdicts and owner-100 coverage remain intact. M412 stays PARTIAL with
this exact null scope; M244 stays BLOCKED.

## Source work and remaining input constraint

R329's bounded venue read is completed as source evidence: three static GETs,
656,276 bytes, 42 enumerated mechanics. BTC_USDC/ETH_USDC are Coinbase-routed;
public Standard 5-bp taker is a conditional scenario, not native zero fees or
owner entitlement. Settled-fund/collateral constraints, asynchronous fills and
a conflicting USDC_USDT example are retained. No same-venue carry portfolio,
current capture or original M244 strategy was executed.

One additional official probability-calibration guide: 72,417 bytes, all main
sections read, scoring/reliability/calibration alternatives enumerated; linked
example code/papers remain unread. Four static attempts total **728,693 bytes**.
Full version/access/read-unread limits are in [sources](sources.json); full
copyrighted pages/tables are not mirrored.

No new market acquisition. The old historical allowance stays **7,757/8,000
requests, reported 229.85/250 MiB spent**, exact remaining bytes unknown. No
reset, large data/weights, account/secret access, trade, money movement, strategy
activation, merge/closure, or permanent execution/delivery guarantee.

The simple approach/recede feature gives almost no usable partition. Further
confidence work needs informative, causally available inputs and its own finite
protocol; actual level-touch/flow questions require synchronized trades/books,
and executable net evidence needs first-seen depth, fees and fair/index values.
This screen does not authorize a new prospective candidate. **Zero new
prospective strategy days** were created.

With the eight pinned held inputs available, use fresh output paths:

```sh
python -m lab account --levels --out /fresh/output
python scripts/audit_level_probability.py /fresh/output
```

The original eight raw caches are hash-pinned, not promised recoverable from a
later API revision. Training reproduction uses `scripts/run_level_probability.py
--fit --out /another/fresh/output`; do not replace the committed model.
