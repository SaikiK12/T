# Critic on the breadth sweep (room 20261125d), 2026-11-25

Scope: triage.md, the four scouts, register rows L1, K1, K2. Numbers come from my own runs: `/tmp/claude-0/-home-user-T/a4c99094-0eba-54d5-9f6a-3abc85cabed2/scratchpad/critic/l1.py` and `l1b.py`, plus a short KRW-USDT probe. Not re-read by me: the Polymarket page, the ANJ order, arXiv 2601.01706, the Upbit PDF, the statute, Q01, Q20, O7d, O7c.

## 1. L1: does the −0.03%/yr hold?
- My run (BTC, 2023-01..2026-09, 1,200 days; daily funding minus next COIN-M quarterly basis, 20-100 days left; 23:00 UTC bars). Spread in %/yr: 2023 +1.77, 2024 −0.53, 2025 −1.72, 2026 −0.30. Day-weighted mean −0.19; positive on 46.3% of days.
- Triage (`triage.md:12`, "1 of 4 years positive" and "−0.03%/yr"; `open_questions.md:21`): +1.96, −0.24, −1.64, −0.21, mean −0.03, positive on 48%.
- Same sign pattern and the same verdict. But the years move 0.2-0.3 points with the bar choice: with 00:00 UTC bars my run gives about +2, 0, −2, 0 (rounded). Quote a range, "−0.2 to 0.0", not "−0.03".
- The pre-registered prediction (mean at least +2%, at least 3 of 4 years positive) fails under every variant I ran.
- "No rent: funding and basis are arbitraged" (`open_questions.md:21`). The data show no excess spread. "Arbitraged" is the mechanism, which I did not observe.
- Premise mismatch: the register question speaks of a "floor venue" with "about 10.95%/yr in calm markets" (`open_questions.md:21`). The test used Binance USD-M. Binance BTC funding in my run: median 6.55%/yr, 5th percentile −2.13%, 95th 16.6%. No 10.95% floor shows there. The floor is Hyperliquid's (registry row R508, `registry/rounds.csv:288`, "Hyperliquid's funding has a 0.01%/8 h interest floor"). Hyperliquid was not tested. Say so.
- Funding by year (my run): 2025 5.3%, 2026 3.2%. The triage says "3-5%/yr in 2025-26" (`open_questions.md:21`), which is fine except 2025 is above 5.
- Is the perp a fair spot proxy? Good on the median, not at the tail. COIN-M perp against Binance BTCUSDT daily close: median −0.03% over the sample; by year −0.01%, −0.02%, −0.03%, −0.10% (2026); 5th/95th percentile −0.15% / +0.10%. A 0.1% gap over 20-100 days is 0.4 to 1.8 points a year, the size of the spreads being tested. My spot-denominator run gives a mean near 0 and 49% positive days, so the verdict survives. The triage should say the spot version agrees.

## 2. The Korean USDT premium and timing
- Upbit's candle time: every row of `data/upbit_hist/reserved/candles_1d/KRW-USDT.parquet` has t at 00:00 UTC (t mod 86,400,000 = 0; first row 2024-06-07). Upbit's "daily close" is the price at 00:00 UTC the next day, which is 09:00 KST. It is not the Seoul FX close.
- Yahoo KRW=X is not in `data/` (a find returned nothing). The triage's 591-day count, the 24.5% of days over 2%, and the 95th percentiles cannot be reproduced here.
- Size of the mismatch: hours to about 17 hours, zero-mean. The file's median absolute daily close change is 0.36% (95th percentile 1.33%), a scale for the daily noise, not a measure of the FX part. Zero-mean noise of that size widens the band; it cannot make a 1.4-point level shift between 2024-25 (+1.4%) and 2026 (−0.04%). The level change is the thing to check: a source or series break in KRW=X at the 2026 boundary is not ruled out, and the triage does not check it.
- First candle: 2024-06-07 open 1289, high 1427, low 1289, close 1412; the next day opens at 1412. The scout's +7.69% on that day (`scout_korea.md:29`) is plausibly this first candle. Drop day one before quoting any extreme.

## 3. The ranking
- K1 is ranked 3rd (`triage.md:24`, "New and reachable"). Its own scout holds no delisted Korean market (`scout_korea.md:17`, "No delisted Korean market is in the held data"), has not checked the aggregator's terms, gives P 20% and "low to medium" value (`scout_korea.md:78`). "New" is wrong for the family: R268 is a running forward test of delisting-notice shorts on MEXC (`registry/rounds.csv:86`, "RUNNING,PENDING"), which the triage does not mention. "Reachable" assumes the owner can trade the global perp; that is not checked (rule 8). Rank K1 below R268's read.
- K2's kill test uses the wrong series. `open_questions.md:23` measures the "USDT/KRW premium over the official rate" against "its 2026 5-95% band". The scout's kill (`scout_korea.md:57`) uses "its 2024-26 90% band (about -0.13% to +0.16%)" of the BTC-level premium, which is near zero by construction (`scout_korea.md:31`). Fix the K2 row before anyone scores it.
- Scout candidate 2 reasons from the same BTC-level series: "the rule is not binding in this window" (`scout_korea.md:68`). The triage says the premium "sits in USDT itself" (`triage.md:17`), so that reasoning does not hold. Its P 10% is not evidence.
- Rates candidate 1 is closed too cleanly. The triage says "Not a rent after costs" (`triage.md:13`) and cites `experiments/boroslock_v1/FINDINGS.md`. That table has no cost line. Its Hyperliquid column reads naked funding 6.59 against locked 5.86 (`FINDINGS.md:49`, `:48`) and "Locked − T-bill, mean / median | +2.07 / +1.98" (`FINDINGS.md:51`). The triage omits the +2.07. "After costs" comes from the registry summary the scout quotes (`scout_rates.md:7`), not from this table. The scout's own question is a different test: "did not split the HL floor-band hours" (`scout_rates.md:56`). Write "R412 measured lock against funding; the floor-band split is open".
- Parked items are right to park. The supply family is all low, and the R529 status is settled as stated: "done: FAIL (NULL)" (`docs/reviews/room_20261125/label_caveats.md:15`). `data/unlocks` is absent (my `ls` failed), as the triage says.
- The prediction parking is sound. Its value for a French owner is near zero (`scout_prediction.md:77`).

## 4. Scout claims the triage uses but did not verify
- FX-act effective date 2026-12-03: a secondary summary; the statute was not opened (`scout_korea.md:42`, "could not open the statute itself"). K2's window depends on it. Flag it on the K2 row.
- Upbit clock (30-day clearing, 30-day withdrawal): the scout's own pdftotext of the policy (`scout_korea.md:35-36`). Not re-read here.
- Polymarket France close-only (`scout_prediction.md:29`) and the ANJ order (`scout_prediction.md:36`): the triage says it read the geoblock page itself. I did not re-fetch it.
- Kalshi France "restricted": from the lab's card, not the PDF (`scout_prediction.md:46`). The triage flags this correctly.
- arXiv 2601.01706, "2-4% on average" (`scout_prediction.md:53`): not read by me, as the triage says.
- R282 "NULL" for the Korean factor (`scout_korea.md:5`; `registry/methods.csv:243`): the R282 row verdict is PARTIAL with a list of RC survivors (`registry/rounds.csv:101`). Check which factor was NULL before citing it.

## 5. Is the triage cleaner than the evidence?
- "−0.03%/yr (1 of 4 years positive)" (`triage.md:12`): the precision is not supported (section 1).
- "No rent: funding and basis are arbitraged" (`open_questions.md:21`): the mechanism is asserted, not observed.
- "The 2026 collapse of the USDT premium" (`triage.md:17`): a one-year level change on a series whose source is unchecked. Say "a 2026 median of −0.04%, source break not ruled out".
- "Closed tonight with data ... R412 already answers it" (`triage.md:29`): partly true (section 3).
- "Parked as knowledge: ... the Korean USDT premium" (`triage.md:27`) while K2 stays open at P 0.25 (`open_questions.md:23`): say "parked as a trade, open as a register row".
- "New and reachable" for K1 (`triage.md:24`): "new" and "reachable" are both unchecked (section 3).

Not checked, outside my brief: Q01 and Q20 ranks (`triage.md:20`, `:22`), O7d and O7c.
