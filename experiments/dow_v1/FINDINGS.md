# FINDINGS: dow_v1 (registered R256; the frozen PREREG says R254). Day-of-week effects on the S&P 500, world indices, the US dollar, BTC and crypto

**Verdict: NULL.** All 5 selected weekday books stopped at discovery.
- **Selection:** in each market, discovery picked the weekday with the largest |alpha t| at s = +1.
- **Picks:** SPY Friday, indices Friday, USD Friday, BTC Thursday and crypto Monday. All were picked short; see the
  disclosure below.
- **After the sign was set**, no pick reached alpha t 1; the best was crypto Monday short, t 0.84.
- No validation or holdout window was read for a decided book. The validation table below is descriptive.

- **Registry row:** R256 (trials 29). Program trials on this branch after it: 9,472,031.
- **Id:**
  - The PREREG text declares R254. Codex claimed R254 on issue #7 first, so this lane is registered as R256.
  - `REGISTRY_REASSIGNMENT.json` records the move; the frozen text is unchanged.
- **Gate:** 0.
- **Reproduce:** prereg sha eae0368e, frozen in commit 45223d8 before the run. Run `python scripts/run_dow.py`
  (about 1 minute).
- **Origin:** queue M219, the day-of-week part (Halloween and pre-holiday were R239).

## Disclosed after the run: the selection rule favoured short picks
- The PREREG selects on the s = +1 book at 1x, which includes its cost. That cost lowers every long-day alpha by the
  same amount: about 0.4 bp/day on Yahoo markets and 1.7-2.1 on crypto.
- So days with a slightly negative gross alpha look stronger than days with an equally positive one. Then the short
  book pays the cost again.
- **Rechecked on gross alphas (cost added back):**
  - Four of the five picks are unchanged. USD would pick Tuesday instead of Friday.
  - The largest gross |t| in any market is 1.21 (BTC Thursday), so nothing reaches 2.
- So the flaw changes no verdict. A future selection rule should rank gross alphas.

## Selected books (discovery; per unit of the market, held on the chosen weekday only)

| Book | Window | Net bp/day 1x / 2x / 3x | Alpha bp/day 1x (t) | 2x alpha | Beta | Cost 1x | Mean return on that day |
|---|---|---|---|---|---|---|---|
| SPY Friday short | 2001-12 | +0.21 / -0.19 / -0.59 | +0.50 (0.60) | +0.10 | -0.15 | 0.40 | -3.1 bp (605 Fridays) |
| Indices Friday short | 2001-12 | +0.05 / -0.35 / -0.75 | +0.35 (0.56) | -0.05 | -0.16 | 0.40 | -2.2 bp (625) |
| USD Friday short | 2006-12 | -0.02 / -0.43 / -0.83 | -0.29 (-0.51) | -0.69 | -0.21 | 0.40 | -1.9 bp (346) |
| BTC Thursday short | 2021-23 | +1.68 / -0.05 / -1.79 | +2.57 (0.72) | +0.83 | -0.16 | 1.74 | -42.6 bp (156) |
| Crypto Monday short | 2021-23 | +2.22 / +0.12 / -1.98 | +4.96 (0.84) | +2.86 | -0.20 | 2.10 | -19.6 bp (156) |

Per year (bp/day, 1x):
- SPY Friday short alpha: 2001 +4.4 and 2010 +3.3; within ±1.9 in the other ten years.
- Indices Friday short alpha: 2001 +3.7 and 2010 +3.1; within ±1.9 otherwise.
- Crypto Monday short net: 2021 +2.5, 2022 +1.7, 2023 +2.5. Steady sign, but t 0.34.
- BTC Thursday short net: 2021 -0.4, 2022 +1.0, 2023 +4.5.

## Weekday table (alpha t at s = +1, 1x; descriptive)

| Market | Window | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|---|---|---|---|---|---|---|---|---|
| SPY | 2001-12 | -0.72 | 0.40 | 0.06 | -0.40 | -1.56 | | |
| SPY | 2013-19 | **-2.36** | 0.10 | 0.29 | -0.39 | -0.45 | | |
| Indices | 2001-12 | -0.85 | -0.17 | -0.37 | 0.43 | -1.82 | | |
| Indices | 2013-19 | **-2.10** | -0.60 | 0.34 | -1.01 | 0.08 | | |
| USD | 2006-12 | -0.73 | -0.52 | -0.81 | -0.78 | -0.89 | | |
| USD | 2013-19 | 1.40 | **-2.55** | -1.21 | -1.90 | -1.68 | | |
| BTC | 2021-23 | -0.70 | -0.04 | 0.34 | -1.69 | -0.61 | -0.94 | -0.09 |
| BTC | 2024-25 H1 | 0.88 | -1.88 | 0.65 | -0.99 | -0.26 | -0.89 | -1.04 |
| Crypto | 2021-23 | -1.55 | -0.01 | -0.14 | -0.86 | 0.46 | 0.03 | -0.60 |
| Crypto | 2024-25 H1 | 0.38 | **-2.32** | 0.96 | -1.39 | 0.28 | 0.59 | -0.99 |

- The alphas include the long book's cost. That pushes every cell slightly negative, which is why USD is negative
  everywhere.
- **Monday on US and world indices:**
  - Negative in both windows: SPY -0.72 then -2.36; indices -0.85 then -2.10.
  - The two series overlap: SPY tracks ^GSPC, one of the ten indices.
  - Adding the cost back moves the 2013-19 values to t -1.83 (SPY) and -1.46 (indices).
  - This is the old Monday effect's sign, weak and not selected by the rule.
- **The selected days did not repeat:**
  - Discovery's strongest days (Friday on indices, Thursday on BTC, Monday on crypto) are not the strongest in the
    later windows.
  - Crypto Monday flips from -1.55 to +0.38.
- Four of 29 descriptive cells are beyond |t| 2 in the later windows. Chance alone gives about 1.5, so this is not
  evidence.

## Cost sensitivity
- **Yahoo markets:** 1 bp per side, traded one day a week, costs 0.4 bp/day at 1x.
  - Every Yahoo book is negative or near zero at 2x.
- **Crypto:** tier costs on a daily round trip are 1.7-2.1 bp/day at 1x.
  - Both crypto books are about flat at 2x and negative at 3x.
- **Weekday trading turns the book over every week, so cost is the first thing to kill any weekday effect.**

## Reading
- No weekday effect survives selection in any of the five markets.
- **The Friday short's alpha comes from two years.**
  - 2001 and 2010 carry all of it, on both SPY and the indices.
  - Without those two years, SPY's Friday-short alpha averages negative.
- Crypto weekday averages are large in bp (±20-90 bp a day), but so is the noise. With 156 weeks, a weekday needs
  about 20+ bp of alpha to reach t 2, and none did.
- **Read against the program:** 9,472,031 trials on this branch.

## Not checked
- Weekend gaps: Friday close to Monday open, and crypto's Saturday-Sunday as one block.
- Time-of-day within the weekday.
- FX in London time.
- The holdout, which no book reached.
- A gross-alpha selection rule (would need a new lane).
