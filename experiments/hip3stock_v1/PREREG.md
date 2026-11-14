# PREREG: hip3stock_v1 (R475). Does a weekly-selected funding carry on trade.xyz's US-stock perps beat T-bills?

- **Registry id:** R475
- **Owner (single writer):** Claude, this session (cloud container, 2026-11-12)
- **Date registered (UTC):** 2026-11-12

Method M530 (new). Found while looking for other xyz perps whose longs pay well above the base rate, after R474
(M529, the hedged TLT carry). This file is frozen by `lab.prereg.freeze()` before the data are fetched. After the
freeze it is never edited; a changed idea is a new lane.

## Question
- Each week, rank trade.xyz's perps on US-listed stocks by their trailing 28-day mean funding. Short the best
  ones, at most 5 at a time, and hold the same stock at a broker. The price legs cancel; the book keeps the funding
  that the perp longs pay, plus the dividends (perp holders get none, so the short gains the ex-date drop).
- In sample A (2026-01-16 .. 2026-07-22), does this book earn at least 2 points a year above the 13-week T-bill,
  net of trading and transfer costs, with Newey-West t ≥ 2.0 and a positive excess at 2x cost?

## Why this could pay, and why it may not
- **Mechanics (docs.trade.xyz, read 2026-11-12):**
  - Hourly funding is 1/8 × 0.5 × [P + clamp(r − P, ±0.0005)], where P is the impact-price premium over the oracle
    and r = 0.0001 per 8 h. With no premium this is 6.25e-6 an hour (5.475%/yr). The cap is 4% an hour.
  - The 0.5 multiplier applies since 2025-12-19 ("lowers baseline funding to ~5.5% annualized").
  - Corporate actions page: "Perpetual holders do not receive dividends directly. The dividend's economic effect is
    reflected in pricing and funding through arbitrage." Stock splits settle all positions and reopen the market
    on the post-split basis.
  - The US-stock oracle runs 24/5 (Sunday 20:05 ET to Friday 20:00 ET, with a Blue Ocean ATS overnight session).
- **Why longs pay more than base on some names:** a short needs the stock held elsewhere (a broker account plus
  USDC on a DEX). That friction is the reason the carry exists, and it can disappear as soon as more capital crosses.
- **Expected excess on capital** (bill near 3.9%, assumed, not read; costs as below):
  - An active slot holds the stock with 3/4 of its capital and keeps 1/4 as margin. It earns about 0.75 × funding
    + 0.75 × dividend yield − bill − turnover cost, the last about 1.5 points a year at a 6-week mean hold.
  - Funding of 11%/yr on the names held (B's mean, below): about +2.9 points a slot, +2.6 on the book at 4.5 of 5
    slots active. At 8%/yr: about +0.5. At 14%/yr: about +4.6.
- **Related lanes:**
  - R442 (OKX Europe stock X-perps hedged at an EU broker) was NULL on rotation costs.
  - R470 (xyz against Lighter on the same stock) was NULL: the cross-venue spread was thin. That book shorted the
    higher-funding venue against the other perp; this one holds the stock, so the whole xyz funding is kept.
  - R474 (M529) runs the same structure forward on TLT alone.

## What the author has seen
- **Sample B's funding (2026-07-23 .. 2026-11-12), scanned 2026-11-12:**
  - An 8-week scan of every HIP-3 market (mean, median, last two weeks, share of positive hours, open interest, day
    volume).
  - A 16-week scan of xyz markets in four 4-week blocks. On the US-stock names, those at ≥ 12%/yr in one block were
    12 of 50, 8 of 54 and 10 of 55. In the next block they averaged 8.1, 13.8 and 10.6%/yr (medians 7.9, 15.0 and
    10.7), and 25%, 12% and 10% of them fell below 6%/yr.
  - The thresholds here (enter 12, exit 6, 5 slots) were set after that scan. That is why B is reported only.
- **xyz funding in sample A was loaded by earlier lanes, never ranked by its own level:**
  - R470 used xyz stock funding from 2025-12-03 to rank the xyz-minus-Lighter spread. Its FINDINGS report the
    spread's carry (about 7%/yr per deployed slot after 2025-12-19), not per-name xyz levels.
  - R462 (weekend fade) and R466 put xyz funding into weekend returns (+1.1 bp per market-weekend in R462's A).
  - xyz stock-perp prices over A entered R451, R462, R466 and R470.
  - `docs/loop/STATE.md` (2026-11-11) argued against an xyz funding carry from the base rate alone: about 3.7%/yr
    on capital before costs, below a 4% hurdle. This lane tests whether selection beats that.
- **Universe probe (2026-11-12):** xyz's meta lists 122 markets. 72 pass the US-equity filter below; 22 of them
  had funding by 2026-01-16, 31 by 05-01 and 57 by 07-22. 68 are in growth mode and 61 allow 10x.
  - Mark/Yahoo price ratios at 05:50 UTC mostly sat at 0.95-0.99 (an overnight move after the Wednesday close).
  - Two ticker collisions: GOLD (107×, the commodity against Gold.com) and CL (0.86, crude oil against
    Colgate-Palmolive).
- **One 4-hour candle request** for xyz:TSLA: 2,182 candles from its listing (2025-11-13 12:00 UTC) to
  2026-11-12 00:00 UTC, at hours 0, 4, 8, 12, 16 and 20. Only the counts and timestamps were printed.
- **Not read:** any stock price, ^IRX, or per-name xyz funding in A.
- **Code:** the runner was run only on synthetic data (`tests/test_hip3stock.py`, 12 tests).

## Data (`scripts/fetch_hip3stock.py`, run once after this freeze)
- **Universe:** every xyz market in Hyperliquid's meta, delisted ones included. A market stays if Yahoo's chart
  metadata calls its ticker an EQUITY quoted in USD on a US exchange (NMS, NGM, NCM, NYQ, ASE, PCX, BTS).
  ETFs, indices, commodities, FX and non-US names are out. A French retail account cannot buy US ETFs, and the
  other underlyings cannot be held as a stock.
- **xyz:** hourly funding prints and 4-hour candles (with volume) from 2025-10-01 to 2026-11-12.
- **Yahoo:** daily close and adjusted close for each stock, and ^IRX, through R471's frozen parser.
- **Manifest:** sha256 of every file, checked by the runner. Provenance goes in `docs/provenance/hip3stock.json`.
- **Survivorship:** delisted xyz markets are kept. A stock whose ticker Yahoo no longer knows drops out (listed in
  FINDINGS).

## The book (`scripts/run_hip3stock.py`)
- **Calendar:** US trading days with a Yahoo close and a perp candle opening at 20:00 UTC. The book runs from
  2026-01-16, 28 days after the funding change, to 2026-11-06.
- **Identity check:** a market is dropped unless, over its last 60 marks, the median perp/close ratio is within 3%
  and daily log returns correlate at 0.5 or more.
- **Marks:**
  - Stock: Yahoo's close; the price leg uses the adjusted close, so dividends count.
  - Perp: the open of the 4-hour candle starting at 20:00 UTC. That is the US close in summer time and an hour
    before it in winter (2026-01-16 .. 03-06 and from 11-02 on).
- **Decision:** on the last trading day of each ISO week.
  - Score: the mean hourly funding over the 28 days to the 20:00 UTC mark, annualized. It needs 28 days of
    listing and at least 80% of the hours.
  - Exit a held name below 6%/yr or with no score.
  - Enter the highest-scoring names at ≥ 12%/yr into free slots, if the perp/close ratio is within [0.9, 1.1].
- **Slot:** 1/5 of the capital. Stock 1/(1 + M) of it, a short of the same notional, and USDC M/(1 + M) on xyz,
  with M = 1/3. Idle capital earns the bill, so it adds nothing to the excess.
- **Daily:**
  - Funding: every hourly print between marks × units short × the previous perp mark (the venue pays on the oracle).
  - Re-split a slot to the same proportions when the hedge drifts more than 10% or its margin leaves [M/2, 1.5 M].
  - **Liquidation:** if any 4-hour high since the last mark would put margin below maintenance (1/(2 × maximum
    leverage)), the perp's margin is lost and the stock is sold.
  - **Split guard:** a day where perp and stock returns differ by more than 15% books no price change; the units
    are rescaled.
  - A held name with no mark left is closed at its last mark.
- **Costs:**
  - 5 bp of stock traded (commission and spread).
  - Perp: 2.9 bp of notional (0.9 bp taker plus 2 bp slippage) on growth-mode markets, 11 bp otherwise. The flag
    is today's and is applied to all of history.
  - 10 bp of cash moved between the broker and xyz.
  - Entries, exits, re-splits and the final close are all charged. 2x and 3x are reported as extra multiples of
    the realized cost.
- **Bill:** ^IRX (percent) as of each mark, accrued on each active slot's capital by calendar day.
- **Weekly series:** sums by ISO week. Excess = funding + price (including dividends) − cost − bill.
- **Annualized excess** = mean weekly excess × 52, with a Newey-West t at lag 4 (`lab.stats.newey_west_t`).

## Samples and verdict
| Sample | Weeks ending | Role |
|---|---|---|
| A | 2026-01-16 .. 2026-07-22 | decides (about 27 weeks) |
| B | 2026-07-23 .. 2026-11-06 | reported; its funding was scanned before this freeze |

- **PASS:** A's annualized excess ≥ 2.0 points, NW t ≥ 2.0 and the 2x excess > 0.
- **PARTIAL:** A's excess > 0 but short of PASS. **NULL:** A's excess ≤ 0.
- **INCONCLUSIVE:** fewer than 20 weeks with a slot held in A.
- Decided at 1x cost on the `decide` variant (5 slots, enter 12, exit 6).
- **Reported only:**
  - `slots10`: 10 slots of 1/10.
  - `enter20`: enter at 20, exit below 10.
  - Excess after a 15% US withholding tax on dividends; B; the whole span.
- **What each verdict earns:**
  - PASS or PARTIAL with a positive 2x excess: a forward paper lane under a new id, with measured xyz costs.
  - NULL closes M530 in this form.
  - None of them is real money; that needs `lab.gate.go_real()` and the owner, in small stakes.

## Power (stated before any price, bill or A-funding read)
- **Weekly noise:**
  - Funding on the held names moves with the market.
  - Marks: the perp sits at the stock close in summer and an hour off in winter; the error telescopes.
  - Assumed sd of the book's weekly excess: 0.15-0.3% of capital. Over 27 weeks the se of the annualized mean is
    about sd × 52 / √27, i.e. 1.5-3.0 points.
- **PASS probability:**
  - True excess +4.6 (funding 14%/yr): 0.3-0.85.
  - +2.6 (11%/yr): 0.13-0.4.
  - +0.5 (8%/yr): under 0.05.
- **The lane is underpowered against a +2.6 book.** A PARTIAL is the likely outcome if A looks like B. That is why
  a PARTIAL with a positive 2x excess earns a forward lane, not a PASS.

## Trials
- 3 configurations (decide, slots10, enter20); one decides. Registry trials 3.
- Program trials: 9,785,250 before this lane, 9,785,253 after.

## Risks the paper book does not carry (each to be listed in FINDINGS)
- **Venue:** HIP-3 deployer (trade.xyz) and Hyperliquid risk; USDC; the oracle; auto-deleveraging; halts.
- **Corporate actions:** a split settles the short. The paper book only rescales units and does not charge the
  re-entry.
- **Margin path:** 4-hour highs only. In practice margin can be topped up within the day, so the paper
  liquidations are, if anything, too harsh.
- **Capacity:** the paper book has no size. FINDINGS reports the median daily traded notional of the names held.
- **Transfers:** cash moves between a broker and xyz take time; the 10 bp is assumed, not measured.
- **Currency and tax:** the book is in USD against a USD bill. An owner in euros bears EUR/USD unless hedged. US
  dividend withholding is 15% at best (reported); other taxes are out of scope.
- **Fee flag:** growth mode is read today and applied to all of history.

## Code
```inputs
a3f7e3e9b90f6371fe2577617a692068c73fdaa8081a3b5fa84cf68b6110fe77  scripts/run_hip3stock.py
04c45090be4113b9d9cf7d3c21c534ae8200363da3e5d4d55fe5a528801fdb9b  scripts/fetch_hip3stock.py
53ccaeb382362178a06abb3f88c53e009d0670c28b7b77bd3ef67151215a48e6  tests/test_hip3stock.py
14c57f1aed3a392a3cdae5a906512cb68cf60e9d3ca0458f6192cf608519e3ee  scripts/run_xyzwknd.py
214ff732638a0ec29a1be56d54fb2ee1d341067cd01a8cf2f73196b8542b2d47  scripts/fetch_cryptomon.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
```

## Evidence lineage and admission
- **Method:** M530 (new). **Related:** M529/R474, R442, R470.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`.
  - Met: one pre-named decision, trials counted, costs at 1x, 2x and 3x, power stated, public data with hashed
    fetches, a decision sample whose funding was never run through a level rule.
  - Not met: measured stock and xyz costs (assumed here), forward evidence, and account-level risk (venue,
    transfer, FX). A PASS earns a forward lane, not real money.

## Stop rules
- One run after the fetch. Nothing is retuned afterwards; a changed idea is a new lane.
- No orders, no money, no credentials. The run writes only `experiments/hip3stock_v1/results/`.
