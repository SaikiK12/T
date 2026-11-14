# FINDINGS: tradlead_v1 (R261). Does the last hour of TradFi perps lead crypto?

**Verdict: NULL.** All 12 selected books failed discovery (2026-01..05), so validation 2026-06..09 was not read.
- **The best book was EQ/TS/24, flat:** -0.13 bp/day at 1x (t -0.08). It follows the equity leader for 24 h.
- **Eight of the 12 books lost money at t below -1.4.** Those are the 1 h and 4 h holds, and costs explain the losses.
- **TradFi and crypto move together within the hour; there is no next-hour lead.**
  - Same-bar correlation with the crypto market: +0.34 (EQ) and +0.12 (CMD).
  - Correlation with the next bar: -0.007 (EQ) and -0.000 (CMD).

- **Registry row:** R261 (trials 24). Program trials on this branch after it: 9,472,061.
- **Id:** R261, claimed on issue #7 before the freeze.
- **Gate:** 0, exploratory: all data lies in the program's spent holdout (Binance TradFi perps start in 2025-12).
- **Reproduce:** prereg sha 488f1746, frozen in commit 02350a6 before the run. Run `python scripts/run_tradlead.py`
  (under a minute). It used `missing="raise"`, which raised nothing.
- **Origin:** queue M004, a proxy for the "news moves TradFi first" claim (rDbW).

## Leader and crypto market, hourly correlations (discovery, descriptive)

| Leader | Signal hours | Trigger hours (\|z\| >= 1) | Same bar: all / 13-20 UTC / other | Next bar: all / 13-20 UTC / other |
|---|---|---|---|---|
| CMD (XAU, XAG, CL, BZ) | 3,624 | 721 | +0.12 / +0.11 / +0.13 | -0.000 / -0.039 / +0.024 |
| EQ (QQQ, NVDA, TSLA, INTC, MU, MRVL, SNDK, NBIS) | 2,722 | 482 | +0.34 / +0.39 / +0.31 | -0.007 / -0.048 / +0.029 |

- When the US market is open, the equity perps and crypto correlate +0.39 within the hour, about 15% of shared
  variance. Both react to the same news in the same hour.
- After that hour, nothing carries over. During US cash hours the next-bar sign is slightly negative, a small reversal.
  It is within noise: about 1,000 hours give a standard error near 0.03.

## Selected books (discovery 2026-01..05, 151 days; sign picked on the 1x mean)

| Book | Sign | Gross bp/day | Cost bp/day 1x | Net bp/day 1x / 2x / 3x | NW t 1x | Mean gross exposure |
|---|---|---|---|---|---|---|
| CMD/TS/1 | follow | +12.2 | 56.5 | -44.4 / -100.9 / -157.4 | -4.38 | 0.20 |
| CMD/TS/4 | follow | +3.2 | 14.2 | -11.0 / -25.2 / -39.4 | -3.11 | 0.12 |
| CMD/TS/24 | follow | +1.6 | 2.5 | -1.0 / -3.5 / -6.1 | -0.45 | 0.06 |
| CMD/XS/1 | fade | +12.2 | 116.0 | -103.8 / -219.9 / -335.9 | -5.36 | 0.40 |
| CMD/XS/4 | fade | +15.6 | 29.3 | -13.7 / -42.9 / -72.2 | -1.57 | 0.25 |
| CMD/XS/24 | fade | +2.4 | 5.3 | -2.9 / -8.1 / -13.4 | -0.57 | 0.13 |
| EQ/TS/1 | fade | +1.7 | 38.0 | -36.3 / -74.3 / -112.3 | -3.25 | 0.13 |
| EQ/TS/4 | follow | +4.3 | 9.8 | -5.5 / -15.3 / -25.1 | -1.44 | 0.08 |
| **EQ/TS/24** | follow | +1.5 | 1.7 | **-0.1** / -1.8 / -3.4 | -0.08 | 0.05 |
| EQ/XS/1 | follow | +13.0 | 78.8 | -65.8 / -144.5 / -223.3 | -2.58 | 0.27 |
| EQ/XS/4 | follow | +3.2 | 20.4 | -17.2 / -37.6 / -57.9 | -2.06 | 0.17 |
| EQ/XS/24 | fade | +0.6 | 3.4 | -2.8 / -6.2 / -9.7 | -0.55 | 0.09 |

- **Every selected gross is positive by construction.** Picking the better sign makes the gross at least zero, so
  gross is no evidence here.
- **Signs flip between holds.** CMD/XS fades the leader while CMD/TS follows it, and EQ/TS fades at 1 h but follows
  at 4 and 24 h. No consistent direction.
- **Per month at 1x:**
  - CMD/TS/24 ranges from -6.5 to +3.6 bp/day, three of five months negative.
  - EQ/TS/24 ranges from -2.0 to +3.3; only May was positive.
- Beta to the crypto market is about 0 for every book (|beta| <= 0.09). Residual t matches raw t.
- Max drawdowns above 100% in `books.csv` are sums of daily returns, not compounded. They mean the 1 h books lost more
  than their unit exposure over five months.

## Cost sensitivity
- **Cost decides the short holds.** At 1 h, the books pay 38-116 bp/day against 2-13 of gross.
- **At 24 h, cost (1.7-5.3 bp/day at 1x) is still larger than gross (0.6-2.4).** Every book is negative at 2x and 3x.

## Reading
- A one-hour lead from TradFi perps to crypto is not in the 2026 data.
  - What exists is a shared reaction within the same hour (EQ +0.34), which a bar-close rule cannot trade.
  - Catching it would need sub-hour data and execution before crypto reprices. That is a latency trade, which the lab
    cannot test with 1 h bars.
- **For the owner:** watching gold or the NASDAQ to call crypto's next hour is not supported. The co-movement is
  real, but it is simultaneous.
- **Read against the program:** 9,472,061 trials. No book came near t 2 in either direction of profit.

## Not checked
- **Minute bars:** a lead inside the hour, e.g. 5-15 minutes after a US macro release.
- **Event-conditioned triggers:** CPI or FOMC hours only, or the US cash open.
- **Single leaders:** gold alone, or QQQ alone.
- **The validation window 2026-06..09:** unread, as the PREREG requires. It remains usable for a new lane on this
  question.
- **The holdout:** not applicable, because every window here was already inside it.
