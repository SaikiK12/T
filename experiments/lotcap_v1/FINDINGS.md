# FINDINGS: lotcap_v1 (R298). A cover on the lottery short does not make the book steady, and the age books were partly alphabetical

**Verdict: NULL.** M276 (the cover form) is TESTED.
- **Trials:** 16, gate 0 on seen data.
- **Read:** frozen PREREG cc190d51, committed and pushed in 23ef214 before the run. Run 2026-10-22 07:38 UTC with
  `scripts/run_lotcap.py`.
  - All 6 inputs matched their frozen hashes.
  - It loaded 727 of 727 coins' bars (`bars_digest` e0eb3a22…).
- **Program trials** after this round: 9,478,613 (`registry.program_trials()`).
- **The pick fails.** The best discovery book, age h24 with a 35% cover (discovery t +1.70), has a validation t of
  +1.03 against the 2.0 bar.
- **A flaw found while checking parity.** The age factor ties about 80 coins at its maximum, so the age books' long leg
  in 2021-24 was an alphabetical slice of the older coins. This also applies to R282's age book. See "Parity with
  R282".

## What was tested
R282 found that young, small, heavily traded coins (the "lottery" cluster) do worse than the rest on a typical day, but
its quintile books earned nothing because a few squeezes in the short leg cancel the median. M276 asks whether a
protective cover on each short keeps the median and cuts the tail.

- **Universe:** R282's frozen factor table, the top 150 Binance perps, decided at 00:00 UTC.
- **Books:** long the least lottery-like fifth, short the most.
- **Scores:** age alone, or the cluster of age, size and volume per unit of cap.
- **Holds:** 24 h rebalanced daily, or 168 h rebalanced weekly.
- **Cover on each short:** none, 10%, 20% or 35%. It is close-based: the short closes at the first hourly close that
  far above entry, and stays flat until the next rebalance.
- **Costs and funding:** API costs on turnover and cover exits; funding paid and received.
- **Windows:** discovery 2021-01..2023-12, validation 2024-01..2026-09.

## Result

**The pick: age h24, 35% cover (bp/day; t is Newey-West, lag 5)**

| Window | Gross | Net 1x / 2x / 3x | t at 1x / 2x / 3x | Median day | Without best 10 days | Best 10 days' share | Sharpe | Long leg | Short leg | Covers/day |
|---|---|---|---|---|---|---|---|---|---|---|
| Discovery | +10.6 | +10.2 / +9.7 / +9.3 | +1.70 / +1.63 / +1.56 | +10.3 | +4.9 | 52% | 1.02 | +16.3 | −5.8 | 0.15 |
| Validation | +10.9 | +10.0 / +9.1 / +8.2 | **+1.03** / +0.94 / +0.84 | +20.1 | +1.2 | 88% | 0.63 | +0.4 | +10.5 | 0.40 |

- **The checks:**
  - t ≥ 2.0 at 1x: **fails** (+1.03);
  - a positive 2x mean: passes;
  - a positive mean without the 10 best days: passes (+1.2).
- **The two windows earned in different legs:**
  - In 2021-23 the long leg made the money (+16.3 bp/day) and the short leg lost.
  - In 2024-26 the long leg earned nothing (+0.4) and the short leg made the money (+10.5).
- **Annual scale:** +10 bp/day is about +36%/yr on one unit per leg, at an annual volatility of about 58%.

**All 16 books, net at 1x (bp/day, t)**

| Book | Discovery | Validation | Validation 2x / 3x |
|---|---|---|---|
| age h24, no cover | +9.8 (+1.60) | +2.9 (+0.26) | +2.2 / +1.5 |
| age h24, 10% | +8.7 (+1.54) | +9.2 (+1.05) | +6.1 / +2.9 |
| age h24, 20% | +9.4 (+1.60) | +9.9 (+1.04) | +8.5 / +7.1 |
| **age h24, 35% (pick)** | +10.2 (+1.70) | +10.0 (+1.03) | +9.1 / +8.2 |
| age h168, no cover | +7.3 (+1.07) | −6.8 (−0.42) | −7.2 / −7.7 |
| age h168, 10% | +10.0 (+1.17) | +1.6 (+0.21) | +0.1 / −1.4 |
| age h168, 20% | +9.6 (+1.46) | +6.9 (+0.87) | +5.8 / +4.8 |
| age h168, 35% | +10.4 (+1.64) | +9.7 (+1.09) | +8.9 / +8.2 |
| cluster h24, no cover | −8.8 (−0.99) | +13.0 (+1.24) | +11.7 / +10.5 |
| cluster h24, 10% | −9.3 (−1.23) | +16.4 (+2.07) | +12.9 / +9.4 |
| cluster h24, 20% | −6.1 (−0.76) | +16.2 (+1.92) | +14.2 / +12.2 |
| cluster h24, 35% | −6.5 (−0.78) | +18.1 (+2.08) | +16.6 / +15.2 |
| cluster h168, no cover | −9.1 (−0.88) | +6.8 (+0.48) | +6.2 / +5.6 |
| cluster h168, 10% | +1.1 (+0.14) | +2.3 (+0.32) | +0.7 / −0.9 |
| cluster h168, 20% | −3.2 (−0.41) | +12.4 (+1.73) | +11.3 / +10.2 |
| cluster h168, 35% | −4.2 (−0.50) | +14.2 (+1.82) | +13.3 / +12.5 |

- **The cluster books flipped between windows.** They lost in 2021-23 (t −0.5 to −1.2) and earned in 2024-26 (t up to
  +2.08). This is R282's vol_mcap pattern by year (2021-23 −13.7 / +0.8 / −9.1, 2024-26 +18.9 / +3.2 / +20.0).
  - The rule picks in discovery, so none of them was eligible.
  - Picking the best validation book would be choosing with the answer in hand.
- **Hansen SPA over the 16 books against cash** (weekly grid, 2,000 draws): p 0.147 in discovery (best: the pick)
  and p 0.068 in validation (best: cluster h24, 10%). No window rejects "no book beats cash" at 5%.

### Did the cover do what M276 asked? Only in 2024-26
Covered minus uncovered, paired by day, net 1x (bp/day, t):

| Book | Discovery | Validation | Validation median day |
|---|---|---|---|
| age h24, 10% / 20% / 35% | −1.1 (−0.33) / −0.4 (−0.27) / +0.4 (+0.38) | +6.4 (+1.19) / +7.0 (+1.80) / +7.1 (+2.23) | −5.0 / −0.3 / 0.0 |
| age h168, 10% / 20% / 35% | +2.6 / +2.3 / +3.1 (t ≤ 0.99) | +8.4 / +13.7 / +16.4 (t ≤ 1.50) | −139 / −37 / −10 (per week) |
| cluster h24, 10% / 20% / 35% | −0.5 / +2.7 / +2.3 (t ≤ 1.23) | +3.4 / +3.2 / +5.1 (t ≤ 1.21) | −2.9 / −0.3 / 0.0 |
| cluster h168, 10% / 20% / 35% | +10.2 / +5.9 / +4.9 (t ≤ 1.17) | −4.6 / +5.6 / +7.4 (t ≤ 0.73) | −172 / −80 / −1 (per week) |

- **In 2021-23 the covers changed nothing** (|t| ≤ 1.23). In 2024-26 they added 3-16 bp/day. Only one pair reaches
  t 2: age h24 with a 35% cover, at +2.23.
- **Tight covers cut the median, as R274 found.**
  - A 10% cover fires on 2.6-4.5 shorts a day (of about 23-30) and on 11-15 a week. Each firing books a loss that
    would often have reversed. The paired median is negative.
  - A 35% cover fires 0.15-0.4 times a day and leaves the median alone. It only clips the large squeezes.
- **So a wide cover is the useful form, but its value came from one window.** It does not turn the book into the
  steady median earner M276 hoped for. The pick's median day was +20 bp in validation, but its mean was +10 and its
  10 best days were 88% of the sum.

### Funding cost the short leg in 2024-26
- **The uncovered age h24 book:**
  - +8.7 bp/day on price in validation, but +3.6 gross with funding;
  - shorting young coins paid about 5 bp/day of funding in 2024-26;
  - in 2021-23, funding added about 0.7 bp/day.
- **With covers**, the drag is 2-4 bp/day.

## Parity with R282, and the age-tie flaw
The PREREG asked for the uncovered age h24 book's mean to be checked against R282's +4.35 bp/day gross, with any gap
above 2 bp/day explained before the verdict. The price-only mean here is +9.05 bp/day over 2,092 decisions, so the
gap is 4.7. It has two causes.

**1. R282's spread includes funding.** This lane's gross (with funding) is +6.94 bp/day on the same 2,091 days. In
2025 and 2026 the two series agree day by day.

| Year | R282 spread | This lane, gross with funding | This lane, price only | Day-by-day correlation (gross) |
|---|---|---|---|---|
| 2021 | −11.5 | +14.1 | +12.6 | 0.40 |
| 2022 | +10.2 | +9.2 | +9.9 | 0.70 |
| 2023 | +14.7 | +7.1 | +5.7 | 0.88 |
| 2024 | +16.9 | +15.0 | +13.5 | 0.97 |
| 2025 | −8.5 | −9.9 | +1.7 | 1.00 |
| 2026 | +3.9 | +5.9 | +11.3 | 1.00 |

**2. In 2021-24, the long leg was chosen by symbol order.**
- `scripts/pitfac_factors.py` counts every coin trading at the panel's start from 2021-01-02. This was by design: the
  panel does not read reserved 2020 rows. So every coin listed before 2021 has the same, maximum age.
- **The tie at the maximum age:**
  - about 80 coins in 2021, 78 in 2022, 65 in 2023, 41 in 2024, 30 in 2025 and 26 in 2026;
  - the long leg is 16-30 names;
  - so on every day of 2021-24, and on 25% of days in 2025, the tie was larger than the leg.
- **Both lanes break ties by symbol, from opposite ends:**
  - this lane takes the alphabetically first of the tied coins;
  - qx `factors` (`engine/src/factors.rs`, `quantile_of`) puts the alphabetically last of them in its top quantile.
- **So in 2021-24, neither age book's long leg was "the oldest fifth".** Each was a different alphabetical slice of
  the pre-2021 coins.
  - That is why the two books correlate 0.40 in 2021 and 0.97 by 2024.
  - It is why this lane's discovery long leg made +16.3 bp/day and R282's book lost −11.5 in 2021.

**What this does and does not change**
- **The verdict stands.** The rule was frozen, and it fails on its own terms.
- **Had the age pick passed, the tie would have blocked reading it as an age effect.** Its discovery t of 1.70 came
  from the long leg, which was alphabetical.
- **R282's age result:**
  - The rank IC is not affected: ties share their mean rank, so it compares coins listed in 2021 or later with the
    rest.
  - Its quintile book's 2021-24 years are affected, and so is its "passes" verdict on age's book. A note is added to
    R282's FINDINGS.
- **The cluster books are much less exposed.** Their score averages three ranks, so ties at the edge are rare. Their
  window flip is not explained by the tie.
- **The plumbing run missed it.** It printed names per leg, not the size of the tie at the leg's edge. Factor lanes
  should print that before a freeze.

## What this does and does not show
**It shows, for the top 150 Binance perps in 2021-2026:**
- A close-based cover on the lottery-cluster short does not make a quintile book that holds up in both windows. The
  best discovery book has a validation t of 1.03.
- Wide covers (35%) cut the squeezes without cutting the median; tight ones (10%) cut both.
- The cover's gain appeared only in 2024-26.
- The cluster books' sign flips between 2021-23 and 2024-26, as R282's vol_mcap did.

**It does not test:**
- **M276's other form,** rank weights with a per-coin loss cap. That needs its own id.
- **Age with an uncensored listing date.** A Binance onboard date, or a listing calendar that reaches back before
  2021, would break the tie.
- **Whether the shorts could have been opened.** Several of the squeezes came around delisting notices, and the books
  use Binance prices, not MEXC's.
- **Intrabar stop orders.** The rule reads hourly closes only.

## Costs
- **Levels:** API, 8.5 / 17 / 25.5 bp per side.
- **What is charged:** turnover from the previous period's end weights, plus every cover exit.
- **Turnover is low for the age books** (0.04-0.12 of a unit a day without a 10% cover). At 3x, costs take 1-3
  bp/day from them.
- **Tight covers raise turnover.** With a 10% cover, each cost step costs 2-3 bp/day, against 0.3-0.7 without a
  cover.
- **No book's verdict depends on the cost level.**
  - The pick's validation t is 1.03 / 0.94 / 0.84 at 1x / 2x / 3x.
  - The cluster books' best validation t falls from 2.08 at 1x to 1.74 at 3x.

## Read against the program
- **16 trials, one pick, one validation read.** The pick's validation t of 1.03 is far from any bar.
- **The highest validation t in the family** (+2.08, cluster h24 with a 35% cover) belongs to a book that lost in
  discovery. Against 16 trials, let alone 9.48M, it is not evidence.
- **SPA:** p 0.147 and 0.068 per window.
- **Power, written before the run:** a pick with a true annual Sharpe of 0.6 has about 15% power. A large improvement
  (Sharpe ≥ 1.5, 69% power) is unlikely given t 1.03, but not ruled out.

## Next
- **M276 (cover form) is TESTED and NULL.** The rank-weight form would need its own id, and it should not use age
  until its tie is broken.
- **Age needs an uncensored listing date** before any further age lane.
  - Candidates: Binance's `onboardDate` from exchangeInfo, or the listing announcements (R188/R271).
  - The tie also limits the reserved 2020 batch: an archive-based age in 2020 would tie every coin listed before the
    archive starts.
- **Factor lanes should print the tie at each leg's edge** in their plumbing run before a freeze.
- **The cluster's window flip** (−9 bp/day in 2021-23, +13 to +18 in 2024-26) is a regime question, not a lane: R282
  saw it in vol_mcap too.
