# FINDINGS: xsrev_v1 (R245). Short-term reversal inside liquidity terciles

**Verdict: NULL.** No reversal book made money in discovery (2021-2023).
- The 1-day books lost heavily: -17.5 bp/day (t -3.73) among liquid coins and -13.6 (t -3.30) among illiquid ones.
  Most of that is cost.
- The 7-day books were flat (illiquid) or negative (liquid).

Validation was not computed and the holdout was not read.

- **Registry row:** R245 (trials 4). Program trials after it: 9,471,957.
- **Gate:** 0.
- **Reproduce:** prereg sha 78d5649f, frozen in commit 74af449 before the run. Run `python scripts/run_xsrev.py`
  (about a minute).
- **Origin:** queue M008, M181.

## Numbers (discovery; reversal side: long the losers, short the winners within the tercile; xs4 bins)

| Book | Net bp/day 1x / 2x / 3x | NW t (1x) | Gross / cost (1x) | K | Trimmed (1x) |
|---|---|---|---|---|---|
| r1d/LIQ (24 h hold) | -17.5 / -26.1 / -34.7 | -3.73 | -8.9 / 8.6 | 8.9 | -14.5 |
| r1d/ILLIQ (24 h hold) | -13.6 / -25.7 / -37.8 | -3.30 | -1.6 / 12.1 | 8.9 | -11.8 |
| r7d/LIQ (168 h hold) | -6.2 / -7.5 / -8.8 | -1.57 | -4.9 / 1.3 | 8.9 | -5.5 |
| r7d/ILLIQ (168 h hold) | -0.0 / -2.1 / -4.1 | -0.01 | +2.0 / 2.0 | 8.9 | +1.2 |

Per year at 1x (bp/day):
- r1d/LIQ: 2021 -19.8, 2022 -12.3, 2023 -20.3.
- r1d/ILLIQ: -17.2, -9.4, -14.4.
- r7d/LIQ: -4.1, -9.9, -4.7.
- r7d/ILLIQ: -3.7, +1.9, +1.7.

## Cost sensitivity
- **A 24 h reversal book turns over its whole position every day.** That costs 8.6 bp/day in the liquid tercile and
  12.1 in the illiquid one at 1x, more than any gross here.
- The 7-day books cost 1.3-2.0 bp/day. Even at zero cost, only r7d/ILLIQ is positive (+2.0 gross).

## Reading
- **The literature's sign pattern shows up, but too weakly to trade.** At 7 days:
  - reversal is mildly positive gross among the illiquid third (+2.0 bp/day);
  - momentum holds among the liquid third (the reversal book's gross is -4.9);
  - the difference, ILLIQ minus LIQ, is +6.2 bp/day net.

  That matches Ficura (2023) in direction.
- **At 1 day, liquid coins continue** (reversal gross -8.9, so momentum +8.9 before costs). This is consistent with
  R243, where overbought/oversold fades lost.
- **A mirror, the 1-day momentum among liquid coins, was not pre-registered.** It would gross about +8.9 bp/day
  against about 8.6 of cost, so it would be close to zero net at 1x and negative at 2x. Not worth a lane on its own.

## Not checked
- Maker execution of the reversal books (R169/R170's old xsrevmaker idea; R193 found simple maker fills
  adverse-selected).
- Other lookbacks (3 d) and holds.
- Terciles on a wider universe than the top 50 (the illiquid third here is still a top-50 coin).
- The holdout.
