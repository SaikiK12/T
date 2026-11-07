# FINDINGS: er_v1 (R293). Tomorrow's efficiency is barely predictable, the reel's 15 features add nothing over today's efficiency, and the gate does not rescue a losing trend rule

**Verdict: NULL.**
- **Trials:** 3, gate 0.
- **Read:** frozen PREREG abb449c5, run 2026-10-22 01:31 UTC, `scripts/run_effratio.py`, 11 inputs checked.
- **Program trials** after this round: 9,478,562 (`registry.program_trials()`).

## What was tested
**The claim** (the owner's reel, instagram.com/reel/DeF5_5yPtDb):
- a logistic regression on 15 measurements of recent price behaviour predicts the next day's efficiency ratio;
- a gate that skips predicted chop days improved "almost every performance metric" of an NQ strategy;
- the improvement held on two unseen years.

**The crypto version:**
- **Efficiency ratio:** of each UTC day, on 5-minute closes, for the BTC, ETH and SOL perps.
- **Features:** the reel's 15, each known at the day's close.
- **Model:** one pooled logistic regression, fitted on 2021-04..2023 and read on 2024-01..2026-09.
- **The gate:** applied to one trend rule fixed in advance. Follow the 00:00→01:00 UTC move from 01:01 until 24:00,
  with manual-web cost of 3 bp per side and funding charged.

## Result

**1. Is tomorrow's efficiency predictable? Barely, and only through persistence.**

| | Discovery | Validation |
|---|---|---|
| AUC, 15 features | 0.568 | **0.537** (day-block CI 0.512-0.562) |
| AUC, today's ER and its 20-day mean only | | **0.536** |
| AUC per coin, BTC / ETH / SOL | | 0.557 / 0.523 / 0.535 |
| Rows (coin-days) | 2,964 | 3,000 (base rate 0.500) |

- The forecast clears the PREREG's bar (AUC ≥ 0.53, CI above 0.5), so it is "predictable" by the rule.
- The other 13 features add 0.001 of AUC over the two-feature baseline. The reel's model is plain efficiency
  persistence with extra inputs.
- AUC 0.537 means a random efficient day outranks a random chop day 54% of the time.

**2. Does the gate improve a trend rule? No. The rule loses, and the gate picks worse trades.**

| Book (validation 2024-01..2026-09) | Trades | Gross bp per trade | Net bp/day at 1x / 2x / 3x | MEXC API | NW t (1x) | Halves at 1x |
|---|---|---|---|---|---|---|
| Ungated | 3,009 | −12.3 | −18.3 / −24.3 / −30.2 | −29.2 | −2.25 | −21.0 / −15.0 |
| **Gated** (forecast > 0.5) | 1,578 | **−15.6** | −11.3 / −14.4 / −17.6 | −17.1 | −2.13 | −10.5 / −12.3 |

- **Discovery** (2021-04..2023): ungated −17.8 bp per trade (t −1.93); gated −26.1 (t −2.45).
- **Gate lift:** −3.3 bp per trade in validation, and −8.3 in discovery. Skipping predicted chop days removed the
  better trades.
- The gated book loses less per day only because it trades half as often.

**Gross per trade by forecast tercile** (cuts from discovery):

| Forecast tercile | Discovery | Validation |
|---|---|---|
| Low (predicted chop) | −6.9 | −7.1 |
| Mid | −36.1 | −5.9 |
| High (predicted efficient) | −13.8 | **−23.2** |

The reel's mechanism (efficient days pay a trend trade) would need the high tercile to be best. In validation it is the
worst, and the order is not monotone in discovery.

**3. The fitted weights look like the reel's.**
- 12 of 15 signs agree with the weights shown in the reel. The 3 that disagree are the variance ratio, the chop run
  and the 20-day mean ER.
- In both, recent efficiency enters negatively and recent chop shares positively. Efficiency mean-reverts a little
  from day to day: after chop, slightly more trend.
- The weights are small, at most 0.11 per standard deviation here.

## Post hoc (not decided on): the first hour reverses
- **The trend rule lost in both windows,** so its mirror (fade the first UTC hour until 24:00) would have grossed
  about +17.8 bp per trade in discovery and +12.3 in validation.
- **From the frozen outputs** (fade net = −follow net − 4 × cost × trades / 3), the fade's net per day would be:

  | Window | 1x | 2x | 3x | API |
  |---|---|---|---|---|
  | Discovery | +11.7 | +5.8 | −0.2 | |
  | Validation | +6.3 | +0.3 | −5.7 | negative |

  It survives only at the cheapest cost.
- **It fits what the lab already saw:**
  - R185's atlas: day-open mean reversion replicated in 79% of cells, gross;
  - R203: the last hour leans against the first on a volume clock.
- **But it is picked after reading both windows, and R290 found the 00:00 UTC anchor no more special than random
  clocks.** It is queued as **M315**, to be read only on unseen data:
  - the 2020 reserved sample in the next batch (batch 1 is frozen);
  - or a forward paper lane, frozen before its first day.

## What this does and does not show
- **It shows** that on BTC, ETH and SOL perps over 2021-2026:
  - the next UTC day's efficiency ratio is only weakly predictable;
  - the reel's 15 measurements carry no more than today's efficiency and its 20-day mean;
  - gating a first-hour trend rule on that forecast makes each trade worse, not better.
- **It does not test** the reel's own NQ strategy, US session hours, or its exact feature formulas, which the reel
  does not show. The trader's NQ result may be real for that strategy. The claim that the method carries over to
  crypto perps does not hold with this rule.
- **It does not test** other gate thresholds, other target cuts, other trend rules, or a non-UTC day.
- **A weak efficiency forecast is still a regime input** (AUC 0.54, like a persistence filter). Any use costs its own
  trials in its own lane.

## Costs
- **Manual web:** 3 / 6 / 9 bp per side at 1x / 2x / 3x, in the table.
- **MEXC API:** 8.5 bp per side, in the table.
- Both books lose at every cost level.

## Next
- **M314 is TESTED (NULL)** and leaves the queue.
- **M315** (first-hour fade) is QUEUED for unseen data only, as above.
