# FINDINGS: weekendlink_v1 (R244). BTC's weekend move and the first US session of the week

**Verdict: NULL.** Trading QQQ or SPY in the direction of BTC's weekend move, from the first session's open to its
close, lost a little: -1.1 and -3.6 bp per trade, t -0.14 and -0.62. BTC's weekend move is strongly tied to the
**opening gap** (correlation +0.46 for QQQ), and that gap is already in the open price.

- **Registry row:** R244 (trials 2). Program trials after it: 9,471,953.
- **Gate:** 0.
- **Reproduce:** prereg sha 08007964, frozen in commit cc10674 before the run. Run `python scripts/run_weekendlink.py`
  (seconds).
- **Origin:** queue M198. NQ futures were replaced by QQQ/SPY because Yahoo's futures bars cannot place the Monday
  open in time.

## Numbers (discovery 2020-01..2023-12, 208 first sessions each)

| Rule | Net bp/trade 1x / 2x / 3x | t (1x) | Hit rate | Corr of the gap with BTC's weekend move (slope) | Corr of the session with it (slope) |
|---|---|---|---|---|---|
| WKND-QQQ | -1.1 / -3.1 / -5.1 | -0.14 | 52% | **+0.46** (0.12) | +0.07 (0.02) |
| WKND-SPY | -3.6 / -5.6 / -7.6 | -0.62 | 49% | **+0.40** (0.10) | +0.02 (0.00) |

Per year at 1x (bp/trade):
- QQQ: 2020 +8.4, 2021 -7.2, 2022 -6.5, 2023 +0.9.
- SPY: 2020 +5.3, 2021 -7.4, 2022 -9.4, 2023 -3.0.

For comparison, holding QQQ long for every first session made +20.6 bp per session (t 2.57), and SPY +11.4 (t 1.95).
This is a description of 2020-2023, not a tested rule.

## Cost sensitivity
2 bp per trade at 1x. The rules lose before cost (gross -1.1 + 2 = +0.9 bp for QQQ), so cost does not decide.

## Reading
- **The link M198 described is real but untradeable here.**
  - A 1% BTC weekend move goes with about a 0.12% QQQ opening gap.
  - Once the ETF opens, the BTC move has nothing left to say about the session (correlation +0.07).
- A rule that could act on it would have to trade before the cash open: NQ futures from Sunday 18:00 New York, or
  QQQ pre-market. That needs futures or pre-market bars this lab does not hold. With the gap already priced at the
  open, such a rule would also be a bet on something faster than Yahoo daily data shows.

## Not checked
- NQ/ES futures with timed Sunday-evening opens (CME data needed).
- Pre-market QQQ.
- The reverse direction: Friday equity close predicting BTC's weekend.
- Thresholds on the size of the BTC move.
- 2025-07 onward (the crypto holdout, spent).
