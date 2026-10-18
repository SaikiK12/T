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

## Rule or search space
The closed list of features, parameters and horizons. For a search: the stages and the beam size.

## Splits and cost
Splits from `lab/config.py` (program version ___). Cost: ___ with sensitivity at 2x and 3x.

## Gates
Thresholds for discovery, validation and holdout, written as numbers.

## Null
How it is built, replicas, seed, and the verdict rule (SIGNAL or NOISE).

## Multiplicity
Trials this lane will run (the number goes in the registry). Program trials so far: ___.

## Stop rules
What ends the lane, and what is not allowed after seeing results (no new features, no new splits).
