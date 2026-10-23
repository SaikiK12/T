# FINDINGS: auction_v1 (R290). Session anchors carry no more structure than random clocks, and no auction rule trades

**Verdict: NULL, with no anchor effect.**
- **Anchor test:** p 0.36 over the 165 three-anchor sets.
- **Trading test:** rc_p 0.43; the selected variant's validation t is −0.96.
- **Trials:** 60, gate 0.
- **Read:** frozen PREREG a1ca38d0, run 2026-10-21 22:17 UTC, `scripts/run_auction.py`, inputs checked.
- **Program trials** after this round: 9,478,555 (`registry.program_trials()`).

## What was tested
Five textbook auction rules on 1-minute bars of the BTC, ETH and SOL perps, each with prior-session levels from the
volume profile (5 bp bins) or session VWAP bands:

| Rule | What it does |
|---|---|
| **VA80** | value-area re-entry: open outside the prior value area, two accepted half-hours inside, go to the far edge |
| **IB60** | follow the first close beyond the first hour's range |
| **OR15** | follow the first close beyond the first 15 minutes' range |
| **VWAP2** | fade the first close beyond VWAP ± 2 SD |
| **NPOC** | after an hour, go toward an untouched prior POC |

- **Sides and holds:** each rule in its textbook direction ("book") and against it ("anti"), held 60 or 240 minutes.
- **Anchors:** 3 real (00:00 UTC, 09:30 New York, 08:00 London) give the 60 trials. 8 placebo clocks drawn with
  seed 290 run the same rules as the null.
- **Cost:** API on Lighter, 2/4/6 bp per side; MEXC's API (8.5 bp) reported.
- **Windows:** discovery 2021-04..2023, validation 2024-01..2026-09.

## Anchor test (do real sessions carry structure?)

| | |
|---|---|
| Rank sum of the real set, S | 190 (chance 180) |
| Permutation p | 0.36 (165 sets) |
| Mean rank of each real anchor among 11 (6 is chance) | 00:00 UTC 7.2, New York 7.6, London 4.2 |

London ranks below chance. New York ranks 11th of 11 (the most structure) on three of ten rule-holds:
- IB60 h240;
- VWAP2 h60;
- VWAP2 h240.

That is not enough across the family. **The frozen answer is no:** on these five rules, a real session start behaves
like an arbitrary clock.

## Trading test

| | Discovery | Validation | Validation halves |
|---|---|---|---|
| j* = NY_VWAP2_anti_h60 (follow the first break of VWAP ± 2 SD after the New York open, 60 min) | +6.39 bp/day at 1x, NW t 2.50, studentized 2.21 | t −0.96 | −5.78 / +2.23 bp/day |
| Reality check | rc_p 0.43 (95% null max 3.12) | | |

**j* at each cost, validation, bp/day:**

| 1x (2 bp/side) | 2x (4 bp) | 3x (6 bp) | MEXC API (8.5 bp) |
|---|---|---|---|
| −2.13 | −5.98 | −9.83 | −14.65 |

- **j*'s gross per trade:** +10.6 bp in discovery, +1.8 bp in validation. Its break-even fell from 5.3 to 0.9 bp per
  side.
- **By year at 1x (bp/day):** 2021 +6.1, 2022 +6.1, 2023 +6.9, 2024 −5.6, 2025 +2.3, 2026 −3.5.
- **By coin, gross per trade over the whole sample:** BTC +2.6, ETH +6.0, SOL +10.4 bp.
- **Concentration:** its five best days are 68% of its summed net.

**The six best real variants in discovery, net at 1x / 2x / 3x / MEXC API in bp/day:**

| Variant | Discovery gross/trade | Discovery 1x / 2x / 3x / API | Disc. t | Validation gross/trade | Validation 1x / 2x / 3x / API | Val. t |
|---|---|---|---|---|---|---|
| NY_VWAP2_anti_h60 | +10.6 | +6.39 / +2.48 / −1.43 / −6.32 | 2.50 | +1.8 | −2.13 / −5.98 / −9.83 / −14.64 | −0.96 |
| NY_IB60_book_h240 | +15.2 | +10.83 / +6.98 / +3.12 / −1.70 | 2.30 | +5.0 | +0.94 / −2.94 / −6.82 / −11.67 | 0.22 |
| NY_IB60_book_h60 | +8.7 | +4.52 / +0.66 / −3.19 / −8.01 | 1.81 | +2.9 | −1.09 / −4.97 / −8.85 / −13.70 | −0.41 |
| U00_OR15_anti_h240 | +12.5 | +8.54 / +4.55 / +0.56 / −4.42 | 1.72 | +9.3 | +5.27 / +1.27 / −2.72 / −7.72 | 1.68 |
| NY_VWAP2_anti_h240 | +12.4 | +8.20 / +4.28 / +0.37 / −4.52 | 1.71 | −1.4 | −5.20 / −9.05 / −12.89 / −17.71 | −1.40 |
| U00_OR15_anti_h60 | +8.9 | +4.88 / +0.89 / −3.09 / −8.08 | 1.43 | +3.5 | −0.45 / −4.45 / −8.44 / −13.44 | −0.27 |

Only 11 of 60 real variants are positive at 1x in discovery (18%), and 12 of 60 in validation (20%).

## Gross by rule, textbook side, mean over anchors (bp per trade)

| Rule, hold | Real, disc. | Placebo, disc. | Real, valid. | Placebo, valid. |
|---|---|---|---|---|
| IB60, 60 | +2.6 | −4.6 | +0.0 | −1.3 |
| IB60, 240 | +6.5 | −3.9 | −2.4 | −2.5 |
| OR15, 60 | −3.4 | −0.5 | −1.7 | +0.2 |
| OR15, 240 | −7.5 | −0.7 | −2.0 | +1.2 |
| VWAP2, 60 | −4.4 | +2.8 | −0.4 | +1.1 |
| VWAP2, 240 | −7.0 | +1.6 | +3.5 | +0.3 |
| VA80, 60 | +0.2 | −2.3 | +0.2 | +2.6 |
| VA80, 240 | +1.9 | −5.6 | −1.6 | +5.2 |
| NPOC, 60 | −0.5 | −0.3 | −2.8 | +0.9 |
| NPOC, 240 | +2.0 | +0.6 | −3.9 | −1.0 |

**How often each rule fires** (per coin, about 2,100 sessions): IB60, OR15 and VWAP2 almost every session; NPOC on
about 70%; VA80 on about 14% (300-400 trades per anchor and coin).

## What this does and does not show
- **It shows** that the textbook auction rules, read mechanically on 1-minute bars, do not trade:
  - no variant survives the reality check;
  - the discovery pick loses at every cost in validation.
- **It shows** that a real session start is not special for these rules. The rank test puts the three real anchors
  at chance.
- **It does not show** that auction levels are useless as a map of where orders sit (M307, the depth and stop-run
  check). That needs the tape and depth recorders, not bars.
- **It does not test** other readings. One tick, one acceptance rule, a 60-minute IB, weekend sessions included.
  A trader's discretionary use (context, confluence, refusal of bad setups) is not captured.
- **Post hoc, a seed at most:**
  - In 2021-23, breaks after the New York open tended to continue: IB60 follow t 3.35 and 3.13, and following VWAP2
    t 4.0. The real anchors had 3 of 30 rule-holds with gross |t| ≥ 3, against 1 of 80 for the placebos.
  - In 2024-26 the IB60 follow is +2.9 / +5.0 bp per trade (t 1.07 / 1.14), and following VWAP2 is +1.8 / −1.4 bp.
  - The best discovery variant of all 220 was a placebo: 11:04 UTC, IB60 anti, h60, net t 3.22. It fell to 0.30 in
    validation.
  - That fits US-hours momentum in crypto that decayed after 2023. It is not a session-level effect, and nothing
    here licenses trading it.

## Next
- M305 is TESTED (NULL). Session levels on bars leave the queue. M207 is closed as superseded.
- **M306** (absorption and exhaustion) is better tested on the 1 s tape than on bar delta, after a few weeks of
  recording.
- **M308** (dealer positioning from Deribit taker flow) is next, once the trade-history download finishes. It is the
  family with a forced-trading mechanism (`docs/AUCTION_AND_FLOW.md`, section 7).
