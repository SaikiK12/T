# FINDINGS: risk_limits_v1 (R526). Two entry filters remove the design gap's tail for free; the hourly stop does not earn its place

**Verdict: PASS by the frozen rule.** Every limit is ADOPTED, and "all" has a delay-1 worst day of −1.57%.

- **Read the verdict with the drawdown table below.** The rule compared each limit with the delayed base, which holds
  the LUNA loss. So a limit that hurts at the base timing could still pass. The hourly stop is one: it passes by the
  rule but worsens drawdowns.
- **Registry:** R526, 6 trials. Program trials become 9,785,787.
- **Reproduce.** The PREREG (sha aa61a161) was frozen in commit 3d90c25f before any limit was computed on real data.
  - `run_risk_limits.py run` ran once on 2026-11-23 (about 6 minutes).
  - The base book reproduced R525's daily nets on all 12 pairs (tolerance 1e-12) before any limit was read.

## The portfolios (%/yr on book capital, 2021-01..2026-09)
- **P12** holds all 12 pairs; **P4** holds the 4 pairs whose legs both have hourly bars (Bitfinex and Deribit against
  Binance and Gate).
- **Delay** is R525's audit stress: entries decided on day d−1's windows, made at day d.
- **Slip** adds 1% per leg on stopped trades.

| Portfolio | Limit | Delay | 1x | 2x | 3x | 1x + slip | Sharpe | NW t | Max DD | Worst day |
|---|---|---|---|---|---|---|---|---|---|---|
| P12 | base | 0 | +7.77 | +6.70 | +5.62 | | 5.50 | 11.96 | −0.73% | −0.63% |
| P12 | base | 1 | +4.57 | +3.29 | +2.01 | | 0.74 | 1.68 | −15.09% | −14.33% |
| P12 | agree | 0 | +7.80 | +6.73 | +5.66 | | 5.69 | 12.57 | −0.69% | −0.43% |
| P12 | agree | 1 | +7.17 | +5.90 | +4.63 | | 5.45 | 11.97 | −0.77% | −0.41% |
| P12 | agree 5% | 0 / 1 | +7.74 / +7.13 | | | | 5.62 / 5.31 | | −0.71 / −0.82% | −0.43 / −0.46% |
| P4 | base | 0 | +5.80 | +4.75 | +3.70 | | 3.44 | 7.99 | −2.75% | −1.00% |
| P4 | base | 1 | +1.36 | +0.09 | −1.18 | | 0.15 | 0.34 | −22.79% | −21.48% |
| P4 | agree | 0 / 1 | +5.96 / +5.35 | +4.91 / +4.09 | +3.86 / +2.83 | | 3.71 / 3.45 | 8.73 / 8.07 | −2.64 / −2.69% | −0.54 / −0.54% |
| P4 | **active** | 0 / 1 | **+5.92 / +5.39** | +4.95 / +4.25 | +3.97 / +3.12 | | **4.59 / 4.30** | 9.84 / 9.35 | **−0.69 / −0.62%** | −0.50 / −0.43% |
| P4 | stop | 0 / 1 | +5.12 / +4.33 | +4.04 / +3.04 | +2.96 / +1.74 | +4.83 / +4.06 | 2.43 / 2.18 | 5.58 / 5.30 | **−5.83 / −5.20%** | −1.67 / −1.57% |
| P4 | stop 20% | 0 / 1 | +5.00 / +4.19 | | | +4.86 / +4.06 | 2.44 / 2.04 | | −5.04 / −4.76% | −1.67 / −1.57% |
| P4 | all | 0 / 1 | +5.41 / +4.96 | +4.42 / +3.81 | +3.42 / +2.66 | +5.20 / +4.74 | 3.29 / 3.16 | 8.14 / 7.72 | −1.86 / −1.75% | −1.67 / −1.57% |

## What each limit does (per pair in `results/report.json`)
- **agree** (legs within 2% at entry).
  - It blocks the trades that broke the hedge:
    - LUNA on bitfinex+gate under the delay (legs 5x apart at entry);
    - ANC on bitfinex+binance (−188% of a leg, May 2022).
  - With the delay, P12 goes from +4.57 to +7.17%/yr and its worst day from −14.3% to −0.41%.
  - At the base timing it costs nothing: +7.80 against +7.77.
  - **Where it costs:** kraken+hyperliquid falls from +22.0 to +18.7%/yr (567 blocked entries), because Kraken's daily
    last-trade closes on thin coins are often stale.
- **active** (each leg printed in 20 of the 24 hours before entry, hourly pairs only).
  - It is the best single limit on P4: Sharpe 3.44 → 4.59, max drawdown −2.75% → −0.69%, return slightly up.
  - It removes Bitfinex's stale legs: bitfinex+binance +3.5 → +5.4%/yr, max DD −6.9% → −1.9%; bitfinex+gate
    +4.3 → +5.6%/yr.
  - **Where it costs:** on Deribit's thin perps, which do not print every hour, it gives up about a quarter of the
    return (deribit+binance +6.8 → +5.1%/yr). It also lowers their drawdown.
- **stop** (hourly 10% ratio stop when both legs print, 7-day bar).
  - **On Bitfinex it whipsaws.** 44 of 48 stops on bitfinex+binance, and 44 of 49 on bitfinex+gate, were back within
    10% 24 hours later.
  - **Some stops "fill" at outlier prints:** GALA −166% and POL −131% of a leg. A real order book would not give
    those prices. A stop on last-trade hourly closes takes a thin venue's bad prints as fills.
  - Max drawdown on P4 doubles (−2.75% → −5.83%).
  - **On Deribit, whose prints are cleaner,** it helps slightly: deribit+binance +6.8 → +7.2%/yr, with 12 of 13 stops
    reverting.
  - **"all" is worse than active alone** (Sharpe 3.29 against 4.59), because of the stop.

## What it means for a live book
1. **Entry filters carry the protection; adopt both.**
   - **Price agreement at entry,** computed live on order-book mids and normalized by the legs' usual ratio, so
     that 1000x contracts (1000PEPE against PEPE) are not blocked.
   - **Printing activity,** or a two-sided book with depth on both legs (the forward lanes already walk the books).
2. **Do not add the hourly stop on last-trade prices.**
   - The engine's daily 20% blowout and dead-leg exits stay.
   - If a stop is used live, it must act on book mids and executable prices, with a threshold wider than ordinary
     cross-venue noise. That variant is untested.
3. **The 5% cap per coin** is already the book (K = 20).
4. **Tail measured:** with both entry filters, the worst day in 5.7 years is about −0.4 to −0.6% of book capital at
   1x, delay or not. At the 2.5x of the stake note, that is about −1.5%.

## What could invalidate this
- **Post hoc design.** The limits were chosen after seeing LUNA. agree at 5% gives the same answer as at 2%, so the
  conclusion does not hang on the threshold.
- **Last-trade data on thin venues** drives both the stop's whipsaw and agree's cost on Kraken. Live mids could make
  the stop better and agree cheaper; neither is measured.
- **Coverage.** active and the stop cover only 4 pairs. Kraken, KuCoin and Hyperliquid are daily bars in this
  archive (Hyperliquid's hourly history starts 2026-04).
- **One stress.** The one-day delay is the only timing stress. A halted venue with no prints at all is handled by
  the engine's dead-leg exit, which values the stale leg at its last print.

## Pre-mortem against outcome
| Prediction before the freeze | What happened |
|---|---|
| 1. The stop fires on noise | Yes: 92% of Bitfinex stops reverted within 24 h |
| 2. The stop cannot act when it matters | Partly: on LUNA, agree and active blocked the entry first |
| 3. agree removes the edge | No overall (+7.80 against +7.77); yes on kraken+hyperliquid (−15%) |
| 4. Hourly gaps disable the stop | Not checked by year; the stop counts are 10-53 per pair |
| 5. Overfitting to LUNA | agree at 5% and the stop at 20% give the same conclusions |
