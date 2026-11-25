# PREREG: carry_meta_v1 (R531). An ML meta-label filter on the design-gap carry book

Freeze with `lab.prereg.freeze()` before `scripts/run_carry_meta.py run`. Never edited afterwards.

- **Registry id:** R531
- **Owner (single writer):** the Claude session that froze it. `scripts/run_carry_meta.py` is the only writer of
  `experiments/carry_meta_v1/results/`.
- **Date registered (UTC):** 2026-11-26
- **Methods:** M564 (new): meta-labeling on a payer family.
- **Paper only.**

## Why
- **The owner, 2026-11-25:** "sois plus précise dans les stratégies, framework directement ou ML". The lab's ML
  rounds so far (R299, R304, R332, the "mlrank" family) tried to predict returns in the cross-section, a pattern
  family, and failed or were invalidated. This round puts ML where the lab's evidence is strongest: the carry family
  (decided pass share 64%, `scripts/base_rates.py`). The model does not choose the side. It only filters the entries
  of a rule that already pays.
- **The question.** R525's book (R275's rule on 12 floorless × floor venue pairs) earned +7.77%/yr at 1x, NW t 11.96,
  over 2021-2026 (`experiments/gap_breadth_v1/FINDINGS.md:14-15`). Its yearly level fell from +13.7% (2021) to +2.2%
  (2025). Can a secondary model, trained only on the past, tell which entries will not pay, and so lift the book's
  net out of sample?
- **The field.** López de Prado's meta-labeling: "the role of the secondary ML algorithm is to determine whether a
  positive from the primary (side decision) model is true or false". Purged validation removes training labels whose
  span overlaps the test span, and an embargo is added. The number of trials must be reported. Read by the room:
  `docs/reviews/room_20261126/ml_reading.md`. Joubert (2022) and the book's chapters were not available legally, so
  the design rests on the two SSRN/author papers and a practitioner summary.

## Data (held; nothing is downloaded)
- R525's frozen spec and loader: `experiments/gap_breadth_v1/spec.toml`, `scripts/run_carry_v2_audit.py`, over
  `lab.xfund_v2`.
- 2021-01-01..2026-09-30, 882 coins, 7 venues:
  - floorless: Kraken, Bitfinex, Deribit;
  - floor: Binance, Gate, Hyperliquid, KuCoin.
- **Seen before.** R525's pair-level and portfolio-level daily nets, and the regime study of cycle 8 (the book pays
  after BTC rallies). The trade-level outcomes that this round labels have never been tabulated, and no feature below
  uses the BTC regime. That keeps the design away from the one fact already mined from this panel.

## Rule (`scripts/run_carry_meta.py`)
- **Primary book: unchanged.** R275's rule (L14d th5% K20, correlation guard 30 d ≥ 0.9 on 20 observations) on each
  of the 12 pairs. `FilterBook` without a model reproduces `v2.Book` exactly; the equivalence is checked before the
  freeze.
- **Label:** a trade of the unfiltered book is 1 if price P&L + funding P&L − 4 × 14 bp > 0, at 2x costs over its life
  (rule exit), else 0.
- **Features at the entry day d** (data up to d only):
  - s14 = the 14-day funding spread, %/yr;
  - ds14 = s14 minus the same spread 14 days earlier;
  - fvol = the 14-day standard deviation of the daily funding difference, annualized;
  - basis = log of the long leg's value over the short leg's;
  - fresh14 = the share of the last 14 days on which both legs traded;
  - two dummies for the floorless venue (Bitfinex, Deribit; Kraken is the base).
- **Model:** logistic regression, L2 (C = 1), features standardized on the training set.
- **Walk-forward, purged:**
  - refit at the start of each calendar quarter;
  - train on the unfiltered trades whose exit day is at least 14 days before the quarter (the embargo);
  - the first test quarter is the first from 2024-01-01 with at least 300 training trades;
  - test through 2026-09-30.
- **Filter:** on a test day, a candidate whose probability is below 0.5 is skipped. Its slot stays free for the next
  candidate by spread. Before the first test quarter nothing is filtered.
- **Accounting:** R525's: per pair, `v2.net` at 7/14/21 bp a leg on 20 slots; the portfolio is the mean over the
  pairs live that day.

## Decision (one trial: the logistic model at 0.5)
- On the test days, diff = meta portfolio − frozen portfolio, daily, at 2x costs.
- **PASS needs all three:**
  1. NW t (lag 10) of diff ≥ 2.5;
  2. diff's mean > 0 in every test calendar year (2024, 2025, 2026);
  3. the meta portfolio's mean at 2x > 0.
- Anything else is FAIL. A PASS buys a forward paper lane on R509's live book, not money.
- **Reported, not decided:**
  - 1x and 3x;
  - the share of candidates kept;
  - the label's positive share;
  - per-year levels.

## Supply, break-even and power (`CLAUDE.md` step 4)
- **Supply** (trades of the unfiltered book per entry year, all 12 pairs; counted before the freeze, no P&L looked
  at): 2021 301, 2022 729, 2023 1,005, **2024 1,178, 2025 1,805, 2026 (to Sep) 1,742**.
  - About 2,000 trades train the first model (2024 Q1), and 12 test quarters follow, with about 4,700 test-period
    entries before filtering.
  - Equivalence checked: on Kraken+Hyperliquid, `FilterBook` without a model gives the same daily rows as `v2.Book`
    (`equals` True) and the same 206 trades.
- **Break-even.** The filter costs nothing per trade. It earns only if the skipped entries lose on average at 2x and
  their slots go to better trades.
  - The frozen book's 2024-26 level is about +2-10%/yr. A filter that removes the worst fifth of entries, if those
    lose about 1% each, would add on the order of +1%/yr.
- **Power.** The diff series is far less noisy than either book, because most days hold the same positions. A lift of
  +1%/yr against a diff SD of about 3-5%/yr over about 2.7 years gives an expected t of 1.0-1.7, so power at 2.5 is
  low, perhaps 15-30%. **I accept low power:** a FAIL with a positive diff says "too small to prove", and the decision
  bar is set to avoid a false lift, not to find a small one.

## Forecast (Ioannidis; logged in `registry/forecasts.csv` as R531-pass)
- **Base rates:** carry family 64% decided passes; the lab's ML family 0% (R299, R304, R332).
- **Prior that a 5-feature filter adds real value** to an already-selective rule: about 0.25.
- **Power** about 0.25.
- **P(PASS)** ≈ 0.25 × 0.25 + 0.75 × 0.01 ≈ **0.07.**
- **Why run it at under 10%.** The owner asked for ML done directly, and this is the cheapest honest ML test the lab
  can run on its best family: data held, about an hour of compute. A null here tells the lab where ML does not help,
  which saves the next ten ML ideas.

## Pre-mortem: "it failed because…"
1. **Most candidates score above 0.5,** because most trades are profitable at 2x, so the filter rarely acts and the
   diff is about zero. Likely: the report shows the share kept.
2. **Freed slots go to worse candidates,** so a trade-level gain is lost at the book level. Possible: the decision is
   at the book level on purpose.
3. **The 2025-26 decay changes what predicts,** so models fitted on 2021-23 mislead. Possible: quarterly refits on an
   expanding window soften it, but do not cure it.
4. **A look-ahead bug in a feature.** Each uses data up to d only (`features()`), and the equivalence check guards
   the book. A reviewer reads `features()` before the run.
5. **Overlapping labels leak across the quarter boundary.** The purge on exit day and a 14-day embargo address it.
   Trades longer than the embargo are already excluded by the exit-day rule.

## Trials
- **This round:** 1 (logistic at 0.5). Program trials rise by 1.

## Inputs
| File | sha256 |
|---|---|
| `scripts/run_carry_meta.py` | 889c83dafcc451268ef3c61ab69dd47ed27fa9aa013a4c54d327fc2e3778952d |
| `tests/test_carry_meta.py` | 42194ac0acc52817709b2dd45fceba0750dd77395ae40ff194546fd18b423476 |
| `lab/xfund_v2.py` | fa85ef56885a1d6736dd92e73f8bce44e97ce9ee001739526caef86ae1ba62cd |
| `lab/xfund.py` | d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d |
| `scripts/run_carry_v2_audit.py` | 1ba92fe3df40a0eac920e47c69ac4b7b9024750d4ba13f94edcfbe8f4550b7e5 |
| `experiments/gap_breadth_v1/spec.toml` | fec0e888ef64efa4547fade7f5b2015f5503f708687ad83d9ba818b3ad6617a6 |
| `lab/stats.py` | bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 |
| `lab/prereg.py` | 3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508 |
