# PREREG: forcedswitch_v1 (R388). Binance's forced hourly switch as a natural experiment

Freeze with `lab.prereg.freeze()` before the scored run. Never edited afterwards; a change is a new lane.

- **Registry id:** R388
- **Claim:** Claude block R380-R389, claimed on issue #7 on 2026-11-02.
- **Method:** M461 (web-deep SRC1103-010).
- **Gate:** 0 (archive), on data other lanes have read. No forward evidence comes from this lane.

## Why
- Since 2025-05-02 08:00 UTC, Binance moves a perp to hourly settlement after a print at its cap or floor. The paying
  side then pays the same capped rate every hour, not every 4 or 8 hours: 4-8 times the carry.
- The prediction is that the payers (almost always shorts at a floor) cover faster. A post-rule switch print would
  then be followed by a stronger move against them than a pre-rule print of the same size.

## Events (`scripts/run_forcedswitch.py`, funding rates only)
- **Universe:** every symbol in `data/fundingRate` with a `data/klines_1h` file (901).
- **Read window:** settlements are read with a load filter of [2022-09-29, 2026-10-01), stamps rounded to the hour.
  No 2020 row and no post-archive row is read.
- **An event:** a settlement T that closes an interval of 4 h or more, with |rate| ≥ 1.99%, and T + 26 h < 2026-10-01.
  - Each symbol has one episode per 24 h; the first print opens it.
- **Eras:**
  - **pre:** T before the rule.
  - **post_switched:** after the rule, with the next settlement 1 h later.
  - **post_not_switched:** after the rule, with a longer next gap. Reported only.
- **Plumbing counts, before this freeze (no price read):**

| Era | Episodes | Coins | Floor prints | Cap prints | Span |
|---|---|---|---|---|---|
| pre | 176 | 100 | 172 | 4 | 2022-10-03 to 2025-04-29 |
| post_switched | 211 | 159 | 207 | 4 | 2025-05-06 to 2026-09-25 |
| post_not_switched | 8 | 8 | 7 | 1 | 2025-06 to 2026-09 |

## Rule
- **Direction:** d = −sign(rate), so a floor print is a long.
- **Entry:** the open of the 1 h bar opening at T + 1 h. This is after the switch is visible (T + 15 min) and causal.
- **Exit:** the open of the bar at entry + h, or the previous bar's close if that bar is missing, for h ∈ {4, 8, 24}.
- **Trials:** 3. The primary is h = 8.
- **Funding:** −d × each settlement of the symbol stamped in (entry, exit].
- **Net:** gross + funding − m × 40 bp, with m = 1, 2, 3. This is R273's round-trip cost on these coins, unchanged.

## Decision (primary h = 8)
PASS needs all six checks; otherwise NULL.

| # | Check | Bar |
|---|---|---|
| 1 | post_switched − pre mean gross. Its t uses the two eras' symbol-day clustered SEs. | > 0, t ≥ 2.0 |
| 2 | post_switched 2x mean net | > 0 |
| 3 | post_switched 3x mean net | > 0 |
| 4 | post_switched 1x mean net in each half by time | > 0 |
| 5 | GATES' trimmed mean (10 each side) of the post_switched 1x net | > 0 |
| 6 | GATES' leave-two-coins-out mean of the post_switched 1x net | > 0 |

## Reported, not decided on
- h = 4 and h = 24.
- 1x/2x/3x for every era.
- Funding share, hit rates, post_not_switched, and missing prices.

## Confounds stated now
- **Era.** 2022-25 against 2025-26 differ in market regime, listings and liquidity.
- **Caps changed before the rule** on some alts. The 1.99% bar keeps prints of the same size, not the same cap state.
- **Seen data.** R273 (fundext_v1), M261 and M458 read onsets of extreme negative funding on every Binance perp.
  R387 read Lighter minute prices around post-rule hourly settlements on 9 coins. So this split is gate 0 only.
- **A PASS earns a forward paper lane** on live switch prints (new id), with R364-style live cost checks.

## What the author has seen before this freeze
- R273's PREREG and FINDINGS (its cost and NULL).
- The web-deep switch counts.
- The plumbing counts above.
- Not read: any price, return or funding sum for these events.

## Multiplicity
- Trials: 3. The primary decides.
- Program trials before this lane: 9,784,326 (`registry.program_trials('registry/rounds.csv')` on 2026-11-03).

## Code and inputs
- `python -I scripts/run_forcedswitch.py`. It verifies this PREREG and the inputs below before reading any price.

```inputs
903ee29328bc3dafae60df2460e47d32c6197951db99e65c11f4438ffcb473c4  scripts/run_forcedswitch.py
bea20ba88c511261038f9e1e4fadca258cd37349ad9fc9f4b911f5feb4ca146c  scripts/settlehop_rule.py
```
