# R259 — PARTIAL subset screen, full cohort funding inconclusive, material short-tail risk

The fixed unlock short retains a positive historical mean under the daily-archive
funding envelope on **407 of421** R258 priceable events. The other14 remain
unknown, including R258's largest close loss, so the original cohort's funded
mean is **not identified**. Mark data also confirms a cash requirement far beyond
the initial notional on three events. This is an accounting diagnostic, not an
executable strategy, account return, MEXC result or new prospective evidence.

## What was fixed before this run

Claimed on issue#7; code/spec/input hashes frozen and pushed in **92075e9** before
outcome computation (PREREG `f60aeaabbb2cd63a133edf77c485153ac3290b462c936b2011c2942a4963e056`).
Inputs are the already-versioned [#31 package](../../research/datasets/unlock_market_data_v1/README.md),
not a calendar refresh or a new universe. Same530 retrospective events, same421
exact daily-price endpoints and109 retained price exclusions. No new stop, side,
horizon, allocation, leverage or threshold was selected. All study windows in
2021–2026-09 remain spent gate0. Original R265 hourly/snapshot requirements remain unmet here.

Funding cash is signed and proportional to current mark-valued quantity, not a
sum of rates on constant entry notional. The daily-range envelope accounts for
optional charges within15 seconds of either holding boundary. Interval/anchor or
mark gaps stay unknown. Per-side10bp stress is charged on entry AND changing exit
notional at1x/2x/3x; BTC pays both legs. These are modeling assumptions and cost
stresses, not guaranteed settlement cash or measured MEXC fills. See [SOURCES](SOURCES.md).

## Conditional results, preserving the missing windows

All percentages below are per event per unit short-leg entry notional, with
unlimited capital assumed for these arithmetic outcomes. They are not compounded
portfolio PnL. The407-row control is the **same** complete-funding sample.

| Cost multiple | Price-only mean,407 rows | Funded envelope mean,407 rows | Week t on lower envelope |
|---|---:|---:|---:|
| 1x | +3.4458% | +2.6250% to +3.2172% | 2.3795 |
| 2x | +3.2494% | +2.4286% to +3.0209% | 2.1998 |
| 3x | +3.0531% | +2.2323% to +2.8245% | 2.0204 |

The average funding contribution is between **-82.08 and -22.86bp/event** in
this envelope. The lower1x chronological halves are +1.5152%, +3.7293%; removing
the top3 summed-lower-net symbols (EIGEN,ZORA,ZETA) leaves +1.9406%. All four frozen
conditional checks pass, hence PARTIAL. Clustered t on these deliberately adverse
envelopes is descriptive; it is not a calibrated test of real-account PnL.

Of14 unknown shorts,6 lack a funding-day mark candle,7 have a funding gap or a
recorded-interval mismatch, and1 lacks a boundary anchor. Their known price-only
mean at1x is **-2.0060%**, including RIVER2026-01-22 at **-132.6248%** with the
changing-notional fee convention. Omitting them improves the price-only sample;
do not transfer the407-event conclusion to all421. Every unknown/reason remains
in events.csv. The full421 price-only means are +3.2645/+3.0679/+2.8714% at1x/2x/3x;
those figures include no funding. Acquisition completeness did not remove gaps.

The BTC control has405 complete pairs. Compare the unhedged short on **those
exact405 dates**; each pair has twice the short leg's initial gross notional:

| Cost multiple | Matched short lower mean | BTC pair lower mean | BTC pair upper mean | Pair lower week t |
|---|---:|---:|---:|---:|
| 1x | +2.6953% | +2.4852% | +3.0971% | 2.4991 |
| 2x | +2.4991% | +2.0888% | +2.7007% | 2.0990 |
| 3x | +2.3028% | +1.6924% | +2.3043% | 1.6994 |

The hedge does not improve mean in this comparison. No leverage adjustment,
portfolio drawdown reduction or cross-margin rescue was tested or inferred.

## Mark-price cash floor: the short cannot be read as a funded account

The fixed diagnostic gifts every possible positive funding credit before the
worst mark, including future credits; it ignores every debit, maintenance margin,
exit/liquidation fees and tiers. The resulting required isolated cash is only a
**necessary floor**, never sufficient collateral or an exact liquidation price.
407 paths are measured,14 remain unknown.

| Cost multiple | Floor >20% of entry notional | >50% | >100% | Maximum floor / entry notional |
|---|---:|---:|---:|---:|
| 1x | 73 | 12 | 3 | 15.9953x |
| 2x | 74 | 12 | 3 | 15.9963x |
| 3x | 75 | 12 | 3 | 15.9973x |

The three measured1x floors exceeding the initial notional are CYBER2025-08-14 (**1.9463x**),
STRK2025-11-13 (**1.0737x**), and STO2026-04-03 (**15.9953x**).

For STO, entry0.10835 and exit0.14245 conceal a **mark high1.84143**. The model's
funding envelope is -220.0515% to -24.5997% of initial notional, with70 observed
settlements (2 optional). Combined1x terminal arithmetic is **-251.7551% to
-56.3033%**. An ordinary account could be closed much earlier; these are not
attainable account losses/fills. The near16x cash floor already grants positive
funding and omits the negative funding that makes this path worse.

[EXTREME_AUDIT.json](EXTREME_AUDIT.json) records six official source ZIP hashes
and a separate raw-CSV/Decimal recomputation agreeing within1e-12. This confirms
the archive calculation, not a real trade, historical margin tier or future bound.
Contract adjustments and higher-resolution settlement/mark validation remain open.

## Provenance, limits and continuation

12 new synthetic tests and the full386-test suite pass. A second run from the
freshly restored #31 price/auxiliary caches reproduces all five result files
byte-for-byte. The frozen run verifies source manifests and publisher hashes;
no input is silently repaired. Integrity audit:0 errors,15 warnings, including a
new metadata-format warning because the frozen id line lacks the parser's colon;
the explicit R259 row path/SHA match and the frozen text is preserved. The old registry prefix and original R258/R265
frozen/result bytes are preserved. Two logged variants add2 trials: branch total
**9,472,065**, excluding unmerged sibling R257 and unfinished R263/R265. A t near2
does not correct that search history, revised calendars or overlapping events.

No random-date test was repeated: R258's prior null is intact, and this question
concerns accounting. Published daily marks may not contain every internal
settlement mark; timing/interval metadata and cost/fill assumptions remain limits.
Nothing passes gates1–3 or makes this short live-ready. The unresolved next work
is a separately frozen protective-exit/capital model with finer chronology and a
point-in-time MEXC event/paper protocol. Do not tune a stop to these seen tails.
No reserved2020/MEXC outcome, order, credential, model, subagent or PR merge used.

```sh
python scripts/unlocks_funding_bounds.py \
  --raw /restored-cache/prices --auxiliary /restored-cache/auxiliary \
  --out /fresh/r259-results
```

The destination must not exist. Retain INPUTS/PREREG and the acquired versions;
restore commands and software-version caveats are in #31's dataset README.
