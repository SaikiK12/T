# PREREG: <lane name>

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R___
- **Owner (single writer):**
- **Date registered (UTC):**

## Question
One sentence, falsifiable.

## Universe
Manifest file and its sha256. Filter rule. Whether delisted symbols are included.

## Data
Source and venue for every input (backtest data vs trade venue), as-of date, and the data-manifest sha256.

## Feature lineage and point-in-time availability
For every direct and derived feature used to make a decision, fill one row. Include transforms, ranks, aggregates,
normalizations and missingness indicators; a derived feature inherits the weakest vintage/survivorship class of its
parents.

| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

Classify each input as point-in-time, forward-captured, latest-vintage, current-survivor-only or unknown. State the
as-of universe membership rule, including listing/delisting availability and contract replacements. For cross-sectional
features, run lab.coverage's survival comparison and report survivor versus later-delisted coverage and each portfolio
leg's shares. A survivor-only or unknown input blocks a cross-sectional primary score unless point-in-time eligibility
establishes the coverage as available at each decision; otherwise exclude it or keep it diagnostic. A venue-own-universe
lane must state that limit and use a valid forward path. Never treat a missing row or stale value as zero or fresh
without a source-backed rule.

## Rule or search space
The closed list of features, parameters and horizons. For a search: the stages and the beam size.

## Splits and cost
Splits from `lab/config.py` (program version ___). Cost: ___ with sensitivity at 2x and 3x.

## Gates
Thresholds for discovery, validation and holdout, written as numbers.

## Null
How it is built, replicas, seed, and the verdict rule (SIGNAL or NOISE).

## Multiplicity
All generated, failed, skipped and retained variants in this decision family, plus the lane's registry count. Program
trials so far: ___. The raw program sum is bookkeeping, not an effective independent-test count or a cross-family
correction.

## Evidence lineage and admission (future lanes only)
Canonical method ids: ___. Parent rounds, variants and previous inspected outputs: ___.
One decision group this signal feeds (shared diagnostics are not new chances): ___.
Samples already seen by any parent/search: ___. Proposed fresh sample and exact overlap: ___.
Current `docs/GATES.md` SHA-256 and the requirements this lane meets or leaves unmet: ___.
Dependent-null calibration, strict on-time clock, 10-day trimming, leave-two-coins-out and 80%-power calculation: ___.
Across-family selection control or explicit statement that there is none and the result remains exploratory: ___.
For a reserved batch: finite candidates, prior-batch information used, overlap/read budget and scope of error control
across adaptive batches: ___. Within-batch Bonferroni alone is not a program-wide adaptation guarantee.
Report the frozen lane-native verdict separately from current gate admissibility; missing admission evidence blocks
that admission. This section cannot authorize reserved reads or real orders by itself.

## Stop rules
What ends the lane, and what is not allowed after seeing results (no new features, no new splits).
