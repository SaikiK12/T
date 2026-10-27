# Venue structure: following the prop trader's lead (2026-10-21)

The most useful single comment in `docs/COMMENT_DIG.md` came from an ex-crypto prop trader. Their team's best month
was $6B of volume. They tried "pretty much everything", and only three things made money:
- exchange rebate and VIP programs;
- pure latency arbitrage;
- obscure arbitrage, such as on-chain AMMs against exchange futures.

"Nothing based on OHLC worked." The owner asked to follow that lead. This note maps the three edges to what a $10k
account with public data can reach. It also records the first measurements and sets out the plan.

Nothing here is a strategy result. The cost numbers are descriptive measurements from public order books, the kind
of cost QA that `docs/GATES.md` allows outside a PREREG. One hour of books is not a cost model. The recorder below
builds one.

## The three edges, for this owner

| Edge | What the prop team had | What the owner can reach | Lab |
|---|---|---|---|
| Rebate and VIP programs | $6B/month of volume, which earns maker rebates and the top fee tiers | No rebate tier: Hyperliquid pays rebates only above 0.5% of all maker volume, and Binance's VIP tiers start in the millions. **But zero-fee venues exist in 2026.** Lighter charges 0/0 to its default accounts, API included, and Paradex charges 0/0 to retail (UI) orders. That is better than a rebate tier for a small account | M292 (fee map below), `scripts/record_lighter_book.py` |
| Pure latency arbitrage | colocation, microseconds | Not reachable from a cloud container. What can be reached is lead-lag over seconds to minutes between venues, which is slow information flow, not latency arbitrage | M264 and M293, on `data/tape` (recording since 2026-10-21 06:35 UTC) |
| Obscure arbitrage (AMM against futures) | on-chain execution, inventory on both sides | The one-sided version: trade the perp toward the pool price, no on-chain leg | M288, `scripts/record_dex_prices.py` (every 5 minutes) |

## Fee map (published schedules, read 2026-10-21)

Per side, in basis points of notional.

| Venue | Account | Maker | Taker | Conditions | Source |
|---|---|---|---|---|---|
| Lighter | Standard (default, app or API) | 0 | 0 | 300 ms delay on taker orders, cancels and modifies; makers have no delay. 60 requests a minute. TWAP orders 1 bp | [trading fees](https://docs.lighter.xyz/trading/trading-fees.md), [account types](https://apidocs.lighter.xyz/docs/account-types), [rate limits](https://apidocs.lighter.xyz/docs/rate-limits) |
| Lighter | Plus (opt-in) | 0.5 | 0.5 | 300 ms taker, 200 ms maker and cancel; 4,000 orders a minute | same |
| Lighter | Premium (opt-in) | 0.4 | 2.8 | 140 ms taker, 0 ms maker and cancel; LIT staking discounts up to 30% | same |
| Paradex | Retail (UI orders) | 0 | 0 | perps, spot and options | [trading fees](https://docs.paradex.trade/trading/trading-fees.md) |
| Paradex | Pro (API orders) | 0.3 | 4.5 | taker from 4.2 bp at $1M per 14 days; at least 1.75 bp after discounts | same |
| Hyperliquid | Tier 0 (under $5M per 14 days) | 1.5 | 4.5 | rebates need at least 0.5% of all maker volume; HIP-3 perps in growth mode pay 90% less | [fees](https://hyperliquid.gitbook.io/hyperliquid-docs/trading/fees) |
| MEXC | web (manual) | 0 on 1,106 of 1,200 contracts | 0-4, mostly 2 | manual orders only (about 15 a day for one person) | `docs/MEXC_EDGES.md` |
| MEXC | API, since 2026-06-01 | 6 | 8 | any frequency | `docs/GATES.md` |

**What this changes.** The lab has priced every automated (API) lane at MEXC's 6/8 bp. On the same coins, Lighter's
Standard account removes the fee, and what is left is the spread and the book.

## First Lighter measurement (one snapshot, 2026-10-21 16:30 UTC)

`scripts/record_lighter_book.py` read 200 active Lighter perps: the best bid and ask, and the cost per side of a
$1k and a $10k market order walked through the shown book.

Every market had a 0 maker and 0 taker fee in Lighter's own market data. The cost per side, by 24 h volume:

| 24 h volume | Markets | Median half-spread | Median $1k | Median $10k |
|---|---|---|---|---|
| over $100M | 2 (BTC, ETH) | 0.01 bp | 0.01 bp | 0.14 bp |
| $10M-100M | 18 | 0.33 | 0.39 | 0.68 |
| $1M-10M | 33 | 0.73 | 1.01 | 1.78 |
| $100k-1M | 57 | 2.29 | 3.64 | 7.49 |
| under $100k | 87 | 9.12 | 12.51 | 25.72 |

Many of the liquid markets are equity, index and commodity perps (SPY, QQQ, NVDA, XAU, WTI), not crypto.

**Against MEXC on the same coins and the same hour.** 27 coins are in both the MEXC cost recorder (R224) and the
Lighter snapshot. MEXC's books are tighter: the median cost of $1k is 0.66 bp per side on MEXC and 1.96 bp on
Lighter, and of $10k it is 1.07 against 3.56. The fee decides the comparison:

| Route | $1k per side, median of the 27 coins |
|---|---|
| MEXC web (manual, 0-2 bp taker) | about 0.7-2.7 bp |
| MEXC API (8 bp taker) | about 8.7 bp |
| Lighter Standard API (0 fee) | about 2.0 bp, plus the 300 ms delay |

For a rule that has to run by API, Lighter costs about a quarter of MEXC on these coins. For a few manual orders a
day, MEXC web stays the cheapest.

**Against R287's break-even.** R287 (`pcares_v1`, hourly PCA residual reversion) was NULL. Its steadiest variants
needed a cost of at most 2.7-3.5 bp per side, against the 7 it was charged. Of R287's 50-coin universe (the Binance
top 50 by volume in 2026-09), 37 coins trade on Lighter:
- median $1k cost 2.2 bp per side; 62% of the 37 at or below 2.7 bp;
- median $10k cost 4.0 bp per side; 22% at or below 2.7 bp.

So the gap that killed R287 is about the size of the gap between MEXC API and Lighter. That does not revive R287:
- its pass rule was frozen;
- its windows have been read;
- a re-priced version would be a new lane, at gate 0;
- it would need Lighter's own prices, not Binance's.

The point is wider. **Rules that died on taker costs between 2 and 8 bp per side are worth a second look at a 0-fee
venue,** if they trade coins with deep Lighter books.

## Plan

1. **Cost model (running).** `scripts/record_lighter_book.py` runs from `scripts/forward_all.sh` every hour. After
   two weeks there is a cost per coin, hour of day and size. Until then, the one-snapshot numbers above are not to
   be used as a cost.
2. **Lighter history (running since 2026-10-21 16:52 UTC).** `scripts/fetch_venue_history.py lighter` fetches the
   hourly funding, daily and hourly candles of all 240 Lighter perps since launch (2025-01-17) into
   `data/lighter_hist`. It shares a lock with the book recorder, so the two stay under Lighter's 60 requests a minute
   together. This is data collection only; nothing is computed on it before a frozen PREREG.
3. **Low-fee re-pricing lane (after 1 and 2).** One frozen family PREREG that re-runs the API-mode rules that died on
   cost at Lighter's measured cost: R287's variants and the hourly books whose break-even sat near the cost they were
   charged (merge_v1 at 0.4-1.0x, posimpulse_v1 near 2x). It runs on Lighter's own hourly prices, at gate 0 (the
   windows are read), with a forward paper lane on Lighter if anything clears. The 300 ms delay is modelled as one
   extra second of price movement against each taker fill.
4. **Lighter in cross-venue carry.** Lighter pays funding every hour. Add it as a venue to the xfund family
   (R275/R277/R278) in a new lane once its funding history is held. When one venue is Lighter, two of a carry
   trade's four legs pay no fee.
5. **Tape lead-lag (M264, M293): the reachable form of latency arbitrage.** MEXC's API fee (16 bp a round trip) is
   far above any move over a few seconds, so the venue that matters is Lighter: no fee and a BTC half-spread of about
   0.01 bp, but a 300 ms delay on taker orders that protects its makers. The question is whether Lighter's book is
   still stale after the delay when Binance has moved. `scripts/record_tape.py` now also records Lighter's best bid
   and offer (stamped in microseconds by its matching engine, about 20-30 ms to receipt here) and trades for the same
   12 coins, through the read-only websocket. **It starts at the recorder's next restart:** the running recorder
   (since 2026-10-21 15:19 UTC) was not stopped. The PREREG is frozen before the tape is read against price changes,
   after an R-id claim in `docs/ROOM.md`. Fills are assumed at the Lighter book one full second after the signal
   second, which is more pessimistic than the 300 ms delay.
   **Result (R348, 2026-10-27): NULL.** One second after the basis leaves its 5-minute median, Lighter's mid has
   nothing left to move toward Binance's (gross −0.03 to +0.32 bp a trade over 6 trials), so each trade loses its
   0.7-1.0 bp book cost; primary 1x −0.77 bp a trade, t −3.43
   ([FINDINGS](../experiments/tapelag_lighter_v2/FINDINGS.md)). The taker form is closed; the maker form, a
   Premium account and order-flow signals were not tested.
6. **Pool prices for M288 (recording since 2026-10-21).** GeckoTerminal's free history answers 429 from this machine,
   so there is no backfill and the clock starts now. `scripts/record_dex_prices.py` maps each MEXC USDT perp to its
   most traded DexScreener pool (same symbol, at least USD 50k of liquidity and USD 10k a day of volume, price within
   1% of the perp, or 3% when none is that close; a symbol alone is not enough, because impostor tokens share
   tickers). A daemon then reads every mapped pool and MEXC's ticker every 5 minutes, and seals one file per UTC
   hour. The map is rebuilt weekly. Rows carry the route: coins with a Binance perp are open, MEXC-only coins are
   reserved (`docs/GATES.md`) and are read only by a frozen batch. The first question, frozen before the data is
   read: does the pool-perp gap at a 5-minute snapshot predict the perp's move over the next 5-60 minutes, net of
   MEXC's cost? A DexScreener price is the pool's last trade, so a quiet pool's price is stale: the PREREG has to
   require recent pool volume.
7. **Prop firms.** A firm's commission and swap decide the same question. `lab/propfirm.py` now charges a per-side
   cost and a daily swap when it is given a gross return stream and its turnover (Breakout: 4 bp per side plus 3.3 bp
   a day). See `docs/PROP_FIRMS.md`.

## What was not checked
- Whether Lighter's shown book is the whole book. Hidden or RPI-style orders would make the real cost lower, and
  fading quotes would make it higher. Only paper markouts against later prices can tell.
- Lighter's taker delay in practice: 300 ms is the documented figure.
- Withdrawal, bridge and deposit costs for each venue, and venue risk. Lighter and Paradex are on-chain venues; an
  account there needs a wallet and a bridge, and nothing here was opened (AGENTS.md rule 5).
- The Paradex retail fee applies to UI orders. Any API strategy pays the Pro schedule.
