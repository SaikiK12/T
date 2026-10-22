# FINDINGS: nagel_v1 (R308). Buying the losers after a crypto stress day does not pay, and in 2024-26 it lost

**Verdict by the frozen rules: NULL** (gate 0, on seen data). The pick, `top50 mvol`, fails all three validation
checks.
- **Trials:** 8 (6 stress books, plus the every-day reversal per universe). Program total after this round:
  9,478,753 (`registry.program_trials()`).
- **Read:** frozen PREREG 1f377b9e, frozen and pushed in 4ff616d before the run. Run 2026-10-22 16:50 UTC with
  `scripts/run_nagel.py`; all 11 inputs matched their frozen hashes.
- **Source:** M325, from the owner's reel DbIlAc1g0LM (Tom Costello on market makers pulling quotes) and Nagel
  (2012, RFS, "Evaporating Liquidity").

## Result (bp per traded day; t is Newey-West, lag 5, on a calendar grid)

Long the day's worst fifth, short its best fifth, held to the next close. The API cost tiers by volume rank come to
about 29 bp a day in the top 50 and 51 bp in the top 150 at 1x.

| Book | Discovery days | Discovery net 1x (t) | Validation days | Validation net 1x / 2x / 3x (t at 1x) | Validation gross | Without the 10 best days (1x) |
|---|---|---|---|---|---|---|
| **`top50 mvol`** (pick) | 67 | **+48.6 (+0.91)** | 121 | **−63.4 / −92.2 / −121.0 (−0.97)** | −34.6 | −176.7 |
| `top50 disp` | 84 | −20.6 (−0.36) | 147 | +9.4 / −19.6 / −48.6 (+0.13) | +38.4 | −129.9 |
| `top50 oi` | 45 | +26.3 (+0.40) | 98 | −76.5 / −105.3 / −134.0 (−1.62) | −47.7 | −173.1 |
| `top150 mvol` | 67 | −53.7 (−1.68) | 121 | −84.6 / −135.0 / −185.4 (−2.27) | −34.2 | −153.2 |
| `top150 disp` | 84 | −45.7 (−1.40) | 147 | −50.3 / −101.4 / −152.5 (−1.27) | +0.8 | −113.7 |
| `top150 oi` | 45 | −31.7 (−0.90) | 98 | −64.9 / −115.7 / −166.5 (−1.95) | −14.2 | −129.3 |
| `top50 all` (every day, reported) | 1,087 | −36.9 (−3.40) | 1,003 | −12.2 / −41.1 / −70.1 (−0.65) | +16.8 | −40.5 |
| `top150 all` (every day, reported) | 1,087 | −43.0 (−5.89) | 1,003 | −30.2 / −81.3 / −132.5 (−2.77) | +21.0 | −43.2 |

**The pick's checks:** validation t −0.97 (needs ≥ 2.0), 2x mean −92.2 (needs > 0), and −176.7 without the 10 best
days (needs > 0). All three fail.

**Nagel's contrast** (gross bp per day, the same universe's reversal on stress days against all other days):

| Book | Discovery: stress / other | Validation: stress / other |
|---|---|---|
| `top50 mvol` | +77.1 / −13.8 | −34.6 / +23.8 |
| `top50 disp` | +7.9 / −9.5 | +38.4 / +13.1 |
| `top50 oi` | +54.7 / −10.9 | −47.7 / +23.8 |
| `top150 mvol` | −6.3 / +4.3 | −34.2 / +28.6 |
| `top150 disp` | +2.8 / +3.7 | +0.8 / +24.5 |
| `top150 oi` | +16.4 / +3.1 | −14.2 / +24.8 |

## What the result says
- **In 2021-23 the top 50 looked like Nagel.** On the day after a high-volatility or open-interest-crash day, the
  reversal earned +77 / +55 bp gross against −11 to −14 on other days. Its yearly gross on `mvol` days was +29, +143
  and +7 bp.
  - The discovery mean rests on a few days. `top50 mvol`'s median day is −5.9 bp, and without its 10 best days it is
    −86.9.
- **In 2024-26 it turned over.** After high-volatility and open-interest-crash days the losers kept losing: the long
  leg of `top50 mvol` made −68 bp the next day. The reversal lost −35 and −48 bp gross on those days, while it earned
  +24 on ordinary days. Dispersion days still reversed (+38 gross), but less than the cost of 29 bp at 1x plus the
  book's swings: t 0.13.
  - By year (`mvol`, gross): −12 bp in 2024, −68 in 2025, −9 in 2026.
  - The pick's worst days were 2025-09-08 (−3,361 bp), 2025-08-05 (−2,604) and 2025-10-10 (−1,682).
- **Stress days** (`lab.stress` on the pick, all 188 traded days): +1,889 bp over the two FTX days in 2022 and
  −1,085 over 2025-10-10/11. The liquidity provider was paid in the 2022 crashes and run over in the 2025 liquidation
  cascade.
- **The plain 1-day reversal turned positive before costs in 2024-26.** On every day it earned +16.8 bp gross in the
  top 50 and +21.0 in the top 150, against −8.2 and +3.6 in 2021-23 (R245 found −8.9). The cost of 29-51 bp a day
  is two to three times that. This is a post-hoc read of a reported book, not a lead.
- **Costs:** every validation book is negative at 2x and 3x. Only `top50 disp` is above 0 at 1x (+9.4, t 0.13).

## Read against the program
- **Against 9,478,753 trials:** nothing to read. No stress book has a validation t above 0.2, and the pick is
  negative.
- **Against its priors:** this matches R245 (1-day reversal, NULL) and R303 (capitulation dips lost in 2024-26).
  M218's index reversal in high VIX (t 1.94, then −0.05) went the same way out of sample.
- **For the Costello reel:** his warning holds for the lab's books. Providing liquidity right after a crypto stress
  day lost in 2024-26 and in the October 2025 cascade (R306's level fade gave back 109 average days in FTX). The
  turned-around version, that the few who stay are paid, did not hold here.

## Files
- `results/summary.json`: every book and window at 1x/2x/3x and gross, legs and costs, the contrasts, the pick's
  stress report, the stress dates and the input hashes.
- `results/days.csv`: every traded day of every book (legs, gross, cost).
- `run.log`: the run.
