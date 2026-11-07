# FINDINGS: msnr_v1 (R306). Malaysian support and resistance loses: every book is negative in both windows

**Verdict by the frozen rules: NULL** (gate 0, on seen data). No book has a positive discovery mean, so there is no
pick and nothing goes forward.
- **Trials:** 24 (12 crypto books decided on, 12 secondary books reported and counted). Program total after this
  round: 9,478,721 (`registry.program_trials()`).
- **Read:** frozen PREREG cf41e8d3, frozen and pushed in aead6cf before the run. Run 2026-10-22 16:27-16:31 UTC with
  `scripts/run_msnr.py`. The PREREG verified, all 14 inputs and both file trees matched their frozen hashes.
- **Source:** the owner's reel DejYIVkhcLQ, a prop firm's skit that mocks the method (`docs/REELS_TRANSCRIPT.md`,
  reel 15). The rules are LuxAlgo's and DanielM's TradingView definitions (PREREG). The skit was right.

## Crypto, decided on (bp per day of the equal-weight cohort of that day's entries; t is Newey-West)

Discovery 2021-01..2023-12, validation 2024-01..2026-09. Costs: each coin's API tier per side (6 or 8 bp in the top
50), so about 14.4 bp a round trip at 1x.

| Book | Discovery net 1x (t) | Validation net 1x / 2x / 3x (t at 1x) | Validation bp per trade, 1x | Validation trades |
|---|---|---|---|---|
| `fade age30 t24` | −19.0 (−2.8) | −21.8 / −36.2 / −50.6 (−3.0) | −22.2 | 37,260 |
| `fade age30 t72` | −31.9 (−2.3) | −62.1 / −76.5 / −91.0 (−4.4) | −63.0 | 15,277 |
| `fade age30 bracket` | −11.8 (−2.0) | −29.7 / −44.1 / −58.5 (−5.4) | −38.2 | 37,755 |
| `fade age180 t24` | −14.4 (−2.1) | −18.9 / −33.4 / −47.8 (−2.6) | −20.9 | 37,835 |
| `fade age180 t72` | −19.7 (−1.4) | −56.2 / −70.7 / −85.2 (−3.8) | −62.5 | 15,383 |
| `fade age180 bracket` | −7.3 (−1.2) | −23.6 / −38.0 / −52.5 (−4.3) | −34.3 | 39,088 |
| `break age30 t24` | −27.0 (−2.8) | −16.1 / −30.5 / −44.9 (−1.9) | −16.5 | 27,496 |
| `break age30 t72` | −25.5 (−1.3) | −6.7 / −21.1 / −35.6 (−0.4) | −12.4 | 13,288 |
| `break age30 bracket` | −18.8 (−2.2) | −11.0 / −25.5 / −39.9 (−1.5) | −9.1 | 29,791 |
| `break age180 t24` | −29.9 (−3.2) | −16.7 / −31.1 / −45.5 (−2.0) | −14.6 | 27,993 |
| `break age180 t72` | −20.7 (−1.1) | −13.1 / −27.6 / −42.0 (−0.7) | −14.8 | 13,413 |
| `break age180 bracket` | −21.4 (−2.5) | −10.8 / −25.2 / −39.6 (−1.5) | −6.8 | 30,468 |

**Before costs** (per trade, from `results/trades.csv.gz`; funding is under 2 bp a trade in every book):

| Book | Gross, discovery | Gross, validation |
|---|---|---|
| fade t24 (age 30 / 180) | −0.6 / +1.8 | −7.9 / −6.9 |
| fade t72 | −17.8 / −13.2 | −48.7 / −49.5 |
| fade bracket | −5.6 / −4.9 | −25.1 / −21.2 |
| break t24 | −13.4 / −13.2 | −0.9 / +1.2 |
| break t72 | −5.7 / +0.6 | +3.1 / +0.9 |
| break bracket | −1.5 / −1.4 | +7.1 / +9.4 |

- **Fading a fresh level has no gross edge, and loses more the longer it is held.** At 24 hours it is about 0 gross
  in 2021-23 and −7 bp in 2024-26. At 72 hours it is −13 to −18 bp, then −49 bp. Price that comes back to a level
  tends to go through it, not bounce.
- **Following a break is about 0 gross.** The validation bracket books' +7 to +9 bp per trade are half the round-trip
  cost and come after a discovery window at −1.5. This is a post-hoc read of a NULL lane and is not a lead. A new lane
  would need data nobody has read.
- **Both sides lose per trade.** Validation 1x per trade, A-level (resistance) / V-level (support) trades: fade t24
  −19.5 / −24.5, fade bracket −22.5 / −52.1, break bracket −26.2 / +11.5.
  - The summary's `sides_valid_1x` day means (fade age30 t24: A +39.3, V +18.5) are not a profit. Each is the mean of
    days, and on most days one side has only a handful of trades. Busy days, when dozens of coins hit their levels
    together, hold most trades and lose. The per-trade means above are the read.

## Secondary set, reported and counted, not decided on (2021-01..2026-09, 8.5 bp a side)

Binance gold, silver and PAXG perps, and MEXC FX, metal, index, oil, gas and QQQ perps (17 instruments, mostly
2025-26).

| Book | Net 1x / 2x / 3x bp per day (t at 1x) | bp per trade, 1x | Trades |
|---|---|---|---|
| `fade age30 t24` | −25.8 / −42.8 / −59.8 (−9.6) | −25.0 | 3,554 |
| `fade age30 t72` | −13.9 / −30.9 / −47.9 (−1.8) | −16.2 | 1,505 |
| `fade age30 bracket` | −19.5 / −36.5 / −53.5 (−6.7) | −22.2 | 3,914 |
| `fade age180 t24` | −24.5 / −41.5 / −58.5 (−9.1) | −25.3 | 3,611 |
| `fade age180 t72` | −20.0 / −37.0 / −54.0 (−2.3) | −14.0 | 1,512 |
| `fade age180 bracket` | −20.6 / −37.6 / −54.6 (−7.2) | −23.6 | 4,086 |
| `break age30 t24` | −19.9 / −36.9 / −53.9 (−5.8) | −21.1 | 2,741 |
| `break age30 t72` | −15.3 / −32.3 / −49.3 (−1.9) | −23.1 | 1,341 |
| `break age30 bracket` | −11.7 / −28.7 / −45.7 (−3.6) | −12.2 | 3,157 |
| `break age180 t24` | −19.6 / −36.6 / −53.6 (−5.9) | −21.8 | 2,782 |
| `break age180 t72` | −11.3 / −28.3 / −45.3 (−1.3) | −21.0 | 1,350 |
| `break age180 bracket` | −11.2 / −28.2 / −45.2 (−3.3) | −9.8 | 3,213 |

- Gross per trade is −8 to +7 bp across the 12 books, against 17 bp of round-trip cost. By source, gross per trade:
  Binance +0.7, MEXC FX and metals −2.7, MEXC indices and commodities −5.7.
- FX and gold are where the method is sold. It loses there too.

## Stress days (`lab.stress`, M324; whole 2021-26 day series at 1x, report only)

| Days | `fade age30 t24` (bp) | In mean days | `break age30 t24` (bp) | In mean days |
|---|---|---|---|---|
| All 2,091 days, mean | −20.3 | 1 | −22.0 | 1 |
| LUNA (4 d), sum | −1,259 | −62 | +5,174 | +235 |
| FTX (3 d), sum | −2,202 | −109 | +990 | +45 |
| 2024-08-05 carry unwind | −739 | −36 | +113 | +5 |
| 2025-10-10 liquidations (2 d) | +621 | +31 | −792 | −36 |

- The fade is short volatility in the way the Costello reel describes (reel 17). It gave back 109 average days in the
  three FTX days and has its worst day on 2022-05-11 (LUNA, −3,622 bp). It loses on ordinary days as well, so the
  crash days are not what makes it a loser.
- The break books win the big crash days and lose on the rest.

## Read against the program
- **Against 9,478,721 trials:** nothing to read. No book has a positive mean in either window. The best validation
  book, `break age30 t72` (−6.7 bp/day, t −0.4), is still negative.
- **Against its priors:** this matches R243 (pivot and level rules on 4-hour and daily bars, NULL), R246 (round
  numbers and ICT levels, NULL) and R263 (5,472 chart strategies). Chart levels on liquid crypto perps carry no
  edge at these costs. The lab will not test more level-drawing variants without a new reason.
- **For prop firms:** a challenge account traded with MSNR rules would have paid about 15-60 bp a trade to its spread
  and fees. The skit's joke is right.

## Files
- `results/summary.json`: every book and window at 1x/2x/3x, the side split, the secondary set, input hashes.
- `results/trades.csv.gz` (12 MB, not committed; its sha256 is in `results/hashes.json`, and the frozen run rebuilds
  it): every crypto trade (book, entry and exit time, side, gross, funding, cost per side, level kind A/V, symbol).
- `results/secondary_trades.csv`: every secondary trade.
- `run.log`: the run.
