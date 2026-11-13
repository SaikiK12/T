# HLP, LLP and LIT: mechanics, large moves and factors (2026-11-13)

Source and mechanics intake, 2026-11-13 08:20 to 08:30 UTC, continuing the owner's line on Hyperliquid's HLP,
Lighter's LLP and the LIT token (owner, 2026-11-13: "great movements and other factors that are interesting").
Run under [`docs/WEB_SEARCH.md`](../../docs/WEB_SEARCH.md); ledger rows WS0011 to WS0021 in
[`registry/web_searches.csv`](../../registry/web_searches.csv); catalog
[`source_catalog_websearch_20261113.csv`](source_catalog_websearch_20261113.csv) (SRC1113-001 to SRC1113-012);
cards [`cards/SRC1113-001.md`](cards/SRC1113-001.md) and [`cards/SRC1113-006.md`](cards/SRC1113-006.md); raw bodies
with hashes in [`hlp_llp_lit_20261113/`](hlp_llp_lit_20261113/) (`SHA256SUMS`).

**Scope rules kept.**
- Descriptive only. No statistic relates one series to a later value of another series (for example LLP's day
  return against the next day's BTC or LIT return). FEAT-003 (M536) freezes that test first.
- No HLP or LLP return after 2026-11-10 was read (R446/R447 gate-1 windows start 2026-11-11).
- No value in `claude/xyz-books-data` `hlp/` or `llp/` was read (R454/R455 forward inputs).
- Hyperliquid's `vaultDetails` was not called: its body carries HLP's post-2026-11-10 history.
- No trial, verdict or registry round. Costs 1x/2x/3x: N/A (mechanics and description only), not zero.

**Data pinned (FEAT-001).** `claude/okx-xperp-data` at `0364bbc6` (2026-11-13 03:42 UTC), read from a detached
worktree. `claude/hl-vaults-data` at `ed333fff` (HLP history `hist/dfc2/0xdfc24b...df303.csv`). The tables below
come from [`scripts/describe_hlp_llp_lit.py`](../../scripts/describe_hlp_llp_lit.py):

```
python scripts/describe_hlp_llp_lit.py --data <okx-xperp-data worktree at 0364bbc6> \
  --hlp-hist <hl-vaults-data ed333fff hist/dfc2/0xdfc24b077bc1425ad1dea75bcb6f8158e10df303.csv> \
  --metrics research/intake/hlp_llp_lit_20261113 --circulating 250000000
```

## Dedupe (before searching)
- `lab websearch seen`: no hit for LLP, HLP, buyback, unlock, tokenomics, "assistance fund", "insurance fund". "LIT"
  only matched unrelated substrings (literature, split). "lighter" hit SRC28-061 (`docs.lighter.xyz/api`),
  SRC1103-005 (`/api/v1/pnl`), SRC1103-006 (rate limits), SRC1103-014 (futures roll) and SRC1103-015 (funding);
  none covers LIT, LLP, fees or buybacks, so none was re-read.
- `lab find`: LLP gives M505, M506, M511 and lanes R447/R455; HLP gives M153, M285, M466, M505, M510 and
  SRC1103-003/-004 (Hyperliquid vault pages, legacy); LIT gives the R447 hedge recorder and unrelated settle-lit
  lanes. M518 (token buyback coverage, BLOCKED) and M057 (unlock short) were read from `registry/methods.csv`.

## Primary and secondary sources read

| Id | Source | Read scope and the statement used | Fetch |
|---|---|---|---|
| SRC1113-001 | [Lighter docs, LIT Utility](https://docs.lighter.xyz/about-lighter/lit-utility.md) | Full page (2,958 bytes, sha256 0714dfe3...). LLP "exclusively accessible to LIT stakers"; "For every 1 LIT staked, participants may deposit up to 10 USDC into the LLP"; staking "fixed 6% APR", reward LIT "bought from `0xADbE1265C0df1B623A56d324De494Bcb8e8914Ff`"; unstaking "3-day lockup"; "LIT is bought back by the protocol using trading fee revenue. Buybacks are executed via daily 24-hour TWAPs, with the flexibility to use shorter timeframes"; treasury account `0x0000000000000000000000000000000000000000`. | FETCHED_FULL; VERIFIED (planner read it at 08:20 UTC, this agent re-fetched at 08:22 UTC: same statements) |
| SRC1113-002 | Lighter docs, [Liquidations & LLP (Insurance Fund)](https://docs.lighter.xyz/trading/liquidations-and-llp-insurance-fund.md) and [LLP Strategies](https://docs.lighter.xyz/trading/liquidations-and-llp-insurance-fund/llp-strategies.md) | Both pages in full (formulas read, derivation not re-checked). Waterfall: healthy, pre-liquidation, partial liquidation (IoC orders at the "zero price"; "up to 1% liquidation fee" goes to LLP), full liquidation (LLP takes positions over in ascending unrealized PnL while it stays above its initial margin), then ADL ranked by leverage and unrealized PnL. LLP is one account split into strategy buckets (crypto, FX, equities/RWA); losses are isolated per strategy; mapping in `orderBookDetails.strategy_index`. | FETCHED_FULL |
| SRC1113-003 | Lighter docs, [Trading Fees](https://docs.lighter.xyz/trading/trading-fees.md) and [LIT Fee Credits](https://docs.lighter.xyz/trading/trading-fees/lit-fee-credits.md) | Full pages. Standard accounts pay 0 maker / 0 taker on regular orders (1 bp on TWAP and RFQ), 300 ms taker latency. Premium accounts pay 0.40 bp maker / 2.80 bp taker at 0 LIT staked, down to 0.28 / 1.96 bp at 500,000 LIT (30% discount). Plus accounts 0.5 bp. Fee Credits: buy LIT credits toward a tier; "All proceeds ... are distributed to LIT stakers", streamed daily. | FETCHED_FULL |
| SRC1113-004 | Lighter docs, [Public Pools](https://docs.lighter.xyz/trading/public-pools.md) | Full page. No lock-up; "The LLP has a 5-minute withdrawal cooldown on Lighter (`liquidity_pool_cooldown_period = 300000` ms)"; deposits limited by LIT staking. | FETCHED_FULL |
| SRC1113-005 | Lighter API docs: [Info](https://docs.lighter.xyz/api/info.md), [exchangeStats](https://docs.lighter.xyz/api/info/exchangestats.md), [exchangeMetrics](https://docs.lighter.xyz/api/info/exchangemetrics.md), [Fee Credits](https://docs.lighter.xyz/api/fee-credits.md), [List Total Values](https://docs.lighter.xyz/api/explorer-api/stats/list-total-values.md); index [llms.txt](https://docs.lighter.xyz/llms.txt) | Full pages (embedded OpenAPI objects parsed). `GET /api/v1/exchangeMetrics?period=&kind=` with `kind` in volume, maker_fee, taker_fee, liquidation_fee, trade_count, liquidation_count, liquidation_volume, inflow, outflow, transfer_fee, withdraw_fee, open_interest, account_count, active_account_count, tps, **buyback, buyback_usdc**, attribution fees; response `metrics: [{timestamp, data}]`. `exchangeStats` gives only current daily volume per book. Info and Fee Credits pages are one-line stubs. | FETCHED_FULL |
| SRC1113-006 | Lighter mainnet [`exchangeMetrics`](https://mainnet.zklighter.elliot.ai/api/v1/exchangeMetrics?period=all&kind=buyback), `period=all`, ten kinds | Ten keyless JSON bodies, 08:23 UTC, 15 to 30 kB each, saved with hashes. Daily points at 00:00 UTC; `buyback` and `buyback_usdc` from 2025-12-30, the rest from 2025-01-17. `period=d` answers 400 for buyback ("invalid period for the requested metric kind"). Units are not stated in the docs: read as LIT and USDC for buyback, USD for the rest. | FETCHED_FULL (bodies); units UNVERIFIED |
| SRC1113-007 | Lighter mainnet [`orderBookDetails?market_id=120`](https://mainnet.zklighter.elliot.ai/api/v1/orderBookDetails?market_id=120) | Single point, 08:25 UTC: LIT last 3.2105, open_interest 10,906,170.66 (unit not stated; about $35m if LIT), 24 h quote volume $17.9m, fees 0/0 (Standard), liquidation fee 1%, initial / maintenance / close-out margin 20% / 12% / 8%, `strategy_index` 2. | FETCHED_FULL |
| SRC1113-008 | Hyperliquid docs: [Protocol vaults](https://hyperliquid.gitbook.io/hyperliquid-docs/hypercore/vaults/protocol-vaults.md), [Vaults](https://hyperliquid.gitbook.io/hyperliquid-docs/hypercore/vaults.md), [Fees](https://hyperliquid.gitbook.io/hyperliquid-docs/trading/fees.md); index [llms.txt](https://hyperliquid.gitbook.io/hyperliquid-docs/llms.txt) | Protocol vaults and Vaults in full; Fees: opening section, maker-rebate table and the fee-destination paragraph only. HLP "provides liquidity ... through multiple market making strategies, performs liquidations, supplies USDC in Earn, and accrues a portion of trading fees"; 4-day deposit lock-up. Fees go to "HLP, the assistance fund, and deployers"; the assistance fund (`0xfefe...fefe`) "converts trading fees to HYPE in a fully automated manner"; its HYPE "is burned". HLP's fee share is not stated on the pages read. | FETCHED_PARTIAL |
| SRC1113-009 | DefiLlama [emissions/lighter](https://defillama-datasets.llama.fi/emissions/lighter) (and [emissionsProtocolsList](https://defillama-datasets.llama.fi/emissionsProtocolsList)) | Full body (384,204 bytes). Max supply 1,000,000,000 LIT. Seasons 1 and 2 airdrop 250m, cliff on 2025-12-29. Team 259.8m (34.7% of the 750m scheduled) and investors 239.8m (32.0%): **linear unlock from 2026-12-29 for 1,095.7 days**, 1,661,000 + 1,533,000 = 3,194,000 LIT a week. Ecosystem 250m "TBD", not scheduled. No source document is cited in the body. | FETCHED_FULL; secondary; UNVERIFIED |
| SRC1113-010 | CoinGecko [coins/lighter](https://api.coingecko.com/api/v3/coins/lighter?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false) | `market_data` fields only, single point 08:22:55 UTC: price $3.20, market cap $800.9m, FDV $3.145bn, circulating 250,000,000, total supply 981,909,280, max 1,000,000,000, ATH $7.86 on 2025-12-30, ATL $0.7794 on 2026-03-31. Ethereum contract 0x232c...4ee2. | FETCHED_PARTIAL; secondary; UNVERIFIED |
| SRC1113-011 | Lighter primary sources for LIT tokenomics: [blog](https://lighter.xyz/blog) and its [RSS](https://lighter.xyz/blog/rss.xml), [lighter.xyz/tokenomics](https://lighter.xyz/tokenomics), docs [llms.txt](https://docs.lighter.xyz/llms.txt) and [About Lighter](https://docs.lighter.xyz/about-lighter.md), the GitBook `ask` route on LIT Utility | NOT_FOUND. The RSS lists one post (2026-08-19, TradingView charting); /tokenomics is 404; llms.txt has no tokenomics page; the GitBook answer: "The total supply and team/investor vesting schedule aren't specified in the available LIT documentation." | NOT_FOUND |

All fetches were public and keyless (curl), small JSON or markdown. No login, paywall, bot check or key was bypassed.
The GitBook pages end with an "Agent Instructions" block (GitBook boilerplate about its `ask` route); it was treated
as page data, and the `ask` route was used once only as a search for SRC1113-011.

## Moves in the series the lab has already seen (to 2026-11-10)

### LLP daily share price (vaults/llp; read before in R446 and R447)
Daily stamp near 20:00 or 21:00 UTC; 663 one-day returns 2025-01-17 to 2026-11-10, no multi-day gaps. Share price
0.001 to 0.0036564 (+265.6%). Daily sd 1.02%; 479 up days, 184 down; 13 days below -1%, 50 above +1%.

| Largest losses | % | Largest gains | % |
|---|---|---|---|
| 2025-03-03 | -6.73 | 2025-02-03 | +8.92 |
| 2025-02-26 | -6.26 | 2025-02-02 | +7.84 |
| 2025-10-11 | -5.35 | 2025-03-02 | +6.40 |
| 2025-01-21 | -3.95 | 2025-03-11 | +5.60 |
| 2025-02-12 | -3.83 | 2025-02-25 | +5.53 |
| 2025-05-09 | -2.42 | 2025-03-10 | +4.81 |
| 2025-04-01 | -1.82 | 2025-03-06 | +4.67 |
| 2025-03-05 | -1.82 | 2025-03-07 | +4.59 |
| 2025-03-17 | -1.79 | 2025-01-22 | +3.99 |
| 2025-03-14 | -1.32 | 2025-03-12 | +3.97 |

Every one of the 20 largest days is in 2025, and 17 of them in January to March 2025, when Lighter's open interest
was $2m to $80m (SRC1113-006). The day labelled 2025-10-11 runs from 2025-10-10 20:00 to 2025-10-11 20:00 UTC, so it
holds the 2025-10-10 21:16-21:21 UTC cascade (SRC1112-010).

Monthly (%): 2025: Jan +22.69, Feb +44.69, Mar +33.77, Apr +5.63, May +9.37, Jun +6.05, Jul +2.25, Aug +7.85,
Sep +4.02, **Oct -2.26**, Nov +1.35, Dec +0.64. 2026: Jan +0.90, Feb +0.76, **Mar -0.02**, Apr +0.95, May +0.78,
Jun +0.95, Jul +0.95, Aug +1.85, Sep +1.07, Oct +1.03, Nov 1-10 +0.28.

Drawdowns of the share price: -8.94% (peak 2025-03-02, trough 03-05, recovered 03-09); -6.26% (02-25 to 02-26,
recovered 03-02); **-5.35% (2025-10-10 to 10-11, recovered only on 2026-02-05, 117 days)**; -3.95% (01-20 to 01-21);
-3.83% (02-11 to 02-12).

Pool size (single point, not a return): 27,119,924,577 shares in `vaults/llp/meta.json` fetched 2026-11-13, times
the 2026-11-10 share price, is about **$99.2m**. At 10 USDC per LIT that pool needs at least 9.9m LIT staked, 4.0%
of the 250m circulating (SRC1113-010).

### HLP allTime account value and pnl (vaults/hlp first snapshot and hl-vaults-data; read before in M285 and R446)
103 allTime points, 2023-05-10 to 2026-11-10, median step 14 days (first snapshot fetched 2026-11-10 20:30 UTC). The
hl-vaults-data history at `ed333fff` has the same points to 2026-11-08 (102 points) and gives identical steps.
Account value peaked at **$603.9m on 2025-09-03** and was **$149.5m on 2026-11-10** (-75%, mostly withdrawals:
cumulative pnl kept rising to $140.8m). Step return = pnl change over the previous account value.

| Largest losses | % | $ | Largest gains | % | $ |
|---|---|---|---|---|---|
| 2023-12-13 | -4.42 | -0.59m | 2023-08-09 | +35.78 | |
| 2023-07-26 | -4.21 | | 2024-01-10 | +17.84 | |
| 2023-11-01 | -4.05 | -0.35m | 2023-05-24 | +11.15 | |
| 2023-11-15 | -1.79 | | **2025-10-15** | **+9.70** | **+41.4m** |
| 2023-06-07 | -1.15 | | 2023-05-17 | +9.37 | |
| **2025-11-12** | -0.80 | **-4.66m** | 2024-03-20 | +7.17 | +5.0m |
| **2025-03-12** | -0.78 | **-3.96m** | **2026-02-04** | **+7.00** | **+18.8m** |
| 2026-04-15 | -0.51 | -2.28m | 2023-11-22 | +6.27 | |

(Blank $: small, outside the five largest dollar steps.) Five largest dollar gains: 2025-10-15 +$41.4m, 2026-02-04
+$18.8m, 2025-01-29 +$6.0m, 2024-03-20 +$5.0m, 2024-12-11 +$4.0m. By year: 2023 +100.6%, 2024 +79.1%, 2025 +19.0%,
2026 to 11-10 +9.6%. Drawdowns of the compounded steps: -5.77% (2023-10-18 to 11-15), -4.42% (2023-11-29 to 12-13),
-4.21% (2023-07-12 to 07-26), all three in 2023; the largest single-step loss since 2024 is -0.80% (2025-11-12).

**Contrast on the 2025-10-10 crash:** HLP's two-week step to 2025-10-15 was its largest dollar gain (+$41.4m,
+9.7%); LLP lost 5.35% on the same night and took 117 days to recover. Both vaults take over liquidated positions,
so the same crash paid one house and cost the other. Why they differ (HLP's size, its market-making legs, LLP's
take-over rule) is not established here.

### LIT perp on Lighter (lit/; read before in R447)
313 daily closes 2026-01-02 to 2026-11-10. Close 2.6616 to 3.4753. Highest high **5.5632 on 2026-09-24** (close high
5.304 on 09-23); lowest low **0.7783 on 2026-03-31** (close low 0.8065 on 03-30). The 11-10 close is 4.3x the close
low (+331%). CoinGecko's ATH $7.86 on 2025-12-30 predates the candles. Daily sd 6.53%; **42 of 312 days moved more
than 10%**.

| Largest losses | % | Largest gains | % |
|---|---|---|---|
| 2026-01-12 | -21.17 | 2026-06-02 | +19.91 |
| 2026-01-29 | -18.98 | 2026-05-19 | +19.12 |
| 2026-06-04 | -17.59 | 2026-09-03 | +17.13 |
| 2026-05-22 | -16.84 | 2026-08-21 | +17.01 |
| 2026-05-26 | -14.05 | 2026-02-06 | +15.30 |
| 2026-01-25 | -12.66 | 2026-09-16 | +14.54 |
| 2026-01-10 | -12.51 | 2026-01-27 | +13.71 |
| 2026-07-13 | -12.33 | 2026-10-31 | +13.68 |
| 2026-06-10 | -11.99 | 2026-01-05 | +13.31 |
| 2026-10-12 | -11.87 | 2026-06-26 | +13.18 |

Monthly (%): Jan -41.00, Feb -11.86, Mar -37.15, Apr +1.72, May +55.84, Jun +34.26, Jul +11.90, Aug +72.34,
Sep +10.74, Oct -20.21, Nov 1-10 +10.16. Drawdowns: **-73.97% (2026-01-07 to 03-30, recovered 08-21)**, -48.99%
(09-23 to 10-29, not recovered by 11-10), -16.75% (09-08 to 09-15).

Funding (hourly, `rate` signed, + when longs pay): longs paid in every month; sum by month (%): Jan 2.77, Feb 0.70,
Mar 0.49, Apr 0.59, May 1.81, Jun 1.77, Jul 1.07, Aug 1.20, Sep 0.53, Oct 0.65, Nov 1-10 0.15. Plain annualised mean
13.7%/yr over 7,485 hours (R447 reported about 12.3%/yr on notional with its own day convention). Median daily quote
volume: perp $16.0m, LIT/USDC spot $5.4m.

## Lighter exchange metrics (SRC1113-006; first read here, to 2026-11-10)

**Buybacks equal fee revenue.** 316 days 2025-12-30 to 2026-11-10: 19,729,557 LIT bought for $34,854,124 (average
$1.767); median day 46,173 LIT ($84,702). Monthly buyback USDC over maker plus taker fees of the same month:

| Month | LIT bought | USDC | Maker+taker fees | Buyback / fees |
|---|---|---|---|---|
| 2025-12 | 7,422 | 19,441 | 9,385,068 | 0.2% (started 12-30) |
| 2026-01 | 3,360,635 | 6,806,873 | 5,968,857 | 114.0% |
| 2026-02 | 3,378,197 | 5,073,310 | 5,042,099 | 100.6% |
| 2026-03 | 2,821,751 | 3,096,705 | 3,074,675 | 100.7% |
| 2026-04 | 2,231,992 | 2,159,197 | 2,121,416 | 101.8% |
| 2026-05 | 2,023,963 | 2,114,881 | 2,102,987 | 100.6% |
| 2026-06 | 1,808,164 | 2,833,812 | 2,848,201 | 99.5% |
| 2026-07 | 935,802 | 2,126,266 | 2,142,135 | 99.3% |
| 2026-08 | 927,831 | 2,653,182 | 2,609,295 | 101.7% |
| 2026-09 | 597,229 | 2,683,147 | 2,695,885 | 99.5% |
| 2026-10 | 1,278,332 | 4,114,834 | 3,006,938 | 136.8% |
| 2026-11 (1-10) | 358,238 | 1,172,476 | 1,216,669 | 96.4% |

- From February to September the monthly buyback is within 1.8% of fee revenue: Lighter spends its whole maker and
  taker fee income on LIT, as SRC1113-001 says. Liquidation fees are not in that total (they go to LLP, SRC1113-002).
- January (114%) and October (137%) exceed fees. The largest buyback days are 2026-10-29 ($818,846), 01-15 ($812,089),
  01-12 ($633,604), 01-11 ($595,980), 10-28 ($583,350), 01-05 ($512,138), 02-05 ($495,396) and 01-21 ($478,563). The
  late-October days fall at the trough of LIT's -49% drawdown (10-29) and the January days inside its -74% one: a
  same-period observation, not a tested relation.
- Bought so far: 7.89% of the 250m circulating supply. CoinGecko's total supply (981.9m) is 18.1m below max supply,
  close to the LIT bought back; whether bought-back LIT is burned or held is not stated in any source read
  (UNVERIFIED).

**Fees and the exchange are shrinking from their 2025 peak.** Maker plus taker fees: 2025-11 $13.74m, 2026-01
$5.97m, 2026-05 $2.10m, 2026-10 $3.01m. Volume: 2025-11 $292.9bn, 2026-10 $53.8bn. Open interest: peak $2.243bn on
2025-10-08; month-end 2026-03 $670m, 2026-10 $1.035bn.

**Liquidations, the LLP's income and risk.** Liquidation fees by month peak in 2025-10 ($6.29m); 2026 runs $0.63m to
$2.63m a month. Largest liquidation days: 2025-10-10 $377.2m volume and $1.43m fee; 2025-09-22 $85.0m; 2026-02-03
$71.1m; 2026-08-19 $59.9m; 2025-11-03 $57.4m. Largest net outflow day: 2025-10-11 (-$179.0m), then 2026-03-05
(-$155.9m) and 2025-12-31 (-$101.1m).

## Factors found
1. **Buyback TWAP size against LIT.** Fee revenue buys LIT every day: about $2.1m to $4.1m a month in 2026, against a
   $801m market cap (0.3% to 0.5% a month) and against LIT's median daily traded value of about $21m (perp plus
   spot), so the TWAP is roughly 0.3% to 0.6% of daily turnover. It is public with one day's lag and scales with
   fees. New M537.
2. **Insider unlock from 2026-12-29 outsizes the buyback 11 to 23 times** (secondary source; DefiLlama's copy VERIFIED by re-fetch, WS0020): 3,194,000
   LIT a week (about 456,000 a day, $1.46m a day at $3.20) for three years, against 20,000 to 41,000 LIT a day bought
   in September and October ($133,000 a day in October). The first year alone releases about 167m LIT, two thirds of
   today's circulating supply. This is
   a linear start, not a cliff; it does not fall under R265's rule (FEAT-004 section below; M057, M538).
   - For M518 (buyback coverage) it is one token with both histories keyless: buyback from SRC1113-006, schedule from
     SRC1113-009. That does not unblock M518, which needs a cross-section.
3. **Staking reward purchases.** The 6% APR is paid in LIT bought from one named address (SRC1113-001). Its size
   needs the staked total, which no source read gives. Fee Credits proceeds also go to stakers (SRC1113-003).
4. **LLP access demand for LIT.** A $99.2m LLP needs at least 9.9m LIT staked (4.0% of circulating, about $32m).
   If LLP grows, demand for staked LIT grows by 0.1 LIT per USDC; a 3-day unstake lock-up delays exits. This is a
   reason the R447 stake is held, not a measured effect.
5. **LLP as the insurance fund on crash days.** LLP earns up to 1% on liquidations and takes over positions in full
   liquidation, so its worst days are cascade days (2025-10-11 above). Its losses are now isolated per strategy
   bucket (SRC1113-002). M536 asks whether LLP's day return, the house side of the crowd's P&L, predicts the next
   day; FEAT-003 tests it with a frozen PREREG.
6. **Hyperliquid's comparable flow is a burn.** The assistance fund converts fees to HYPE and burns it
   (SRC1113-008); HLP gets "a portion" of fees. Alias to M518 as context; no HYPE series was read.
7. **LIT perp margin.** Initial 20% (5x), maintenance 12%, close-out 8%, liquidation fee 1% (SRC1113-007). With a
   daily sd of 6.5% and 42 days above 10%, R447's 1x-margined short is far from liquidation, but a 5x short is not.

## LIT and HYPE unlocks against R265's rule (FEAT-004, 2026-11-13 09:03 UTC)

**Rule read from the frozen files.** R265 ([`unlocks_v1/PREREG.md`](../../experiments/unlocks_v1/PREREG.md)) and R266
([`unlocks_fwd/PREREG.md`](../../experiments/unlocks_fwd/PREREG.md)) both use `cliff_days` in
[`scripts/unlock_events.py`](../../scripts/unlock_events.py): it sums only `cliffAllocations` whose category is
`insiders` or `privateSale`, per UTC day D, and keeps D when the sum is at least 1% of max supply (14-day spacing).
`linearAllocations` are never read. R266 applies the same function to each token's `unlockEvents` in the daily
emissionsIndex snapshot (`scripts/forward_unlocks.py`, `snapshot_events`).

**Sources and labels.**
- SRC1113-009, DefiLlama [emissions/lighter](https://defillama-datasets.llama.fi/emissions/lighter): re-fetched by a
  second agent at 09:03 UTC, 384,204 bytes, sha256 `605f1fb9...`, byte-identical to the 08:2x copy. **VERIFIED as
  DefiLlama's published schedule** (WS0020). It is still a secondary source with no cited document, and Lighter
  publishes no tokenomics page (SRC1113-011, WS0017, NOT_FOUND), so the schedule itself rests on DefiLlama alone.
- SRC1113-012, DefiLlama [emissions/hyperliquid](https://defillama-datasets.llama.fi/emissions/hyperliquid): 383,701
  bytes, sha256 `f834c1eb...`, saved in [`hlp_llp_lit_20261113/`](hlp_llp_lit_20261113/). Secondary, UNVERIFIED (one
  fetch, WS0021). Not queue-changing: it has no event in the window under any reading.
- Not read: the 23.5 MB emissionsIndex that R266 snapshots (HEAD request only). That the index rows carry the same
  `unlockEvents` as the per-protocol bodies is assumed, not checked.

**Events dated 2026-11-13 to 2027-03-31.**

| Token | Event (DefiLlama) | Type and category | Size | R265 rule | R266 ticket |
|---|---|---|---|---|---|
| LIT | Team 1,661,000 + Investors 1,533,000 LIT a week from 2026-12-29 05:48 UTC to 2029-12-28 | `linear_start`, insiders; `cliffAllocations` empty | 3,194,000 LIT a week = 0.319% of the 1bn max supply a week (0.046% a day); first week 0.32%; first year about 166.7m (16.7%) | **Does not qualify**: no cliff, so `cliff_days` returns no day | No (no event) |
| LIT | Ecosystem 250m | TBD, not scheduled | n/a | No event | No |
| HYPE | none dated in the window. Last dated event 2026-11-06 (179,706 HYPE). Core Contributors cliffs 2026-01-06 to 2026-11-06 are observed HyperLabs transfers, category `Uncategorized`, largest 3,750,000 (0.375%) on 2026-10-07 | cliff, Uncategorized | below 1% even if relabelled insiders | **Does not qualify** | No |
| HYPE | 609.3m TBD (Core Contributors TBD and others) | not scheduled | n/a | No event | No |

The other check items in the plan:
- **First-week tranche:** 0.32% of max supply, under 1%. No single day reaches 1% at 0.046% a day; adding weeks
  together to cross 1% would be a different rule, so it is not done.
- **Size against volume:** at the 2026-11-10 perp close of 3.4753, a week of the LIT stream is about $11.10m. That
  is 0.56 days of the perp's mean daily quote volume over 2026-10-12..2026-11-10 ($19.73m; spot $4.27m), or 8.0% of
  perp volume each day (6.6% of perp plus spot). R181's 0.82-day cut applies to one cliff day's tokens and is not
  applied here. HYPE: N/A (no event).
- **R266's venue:** moot, since R266's rule yields no LIT or HYPE event. Whether MEXC lists a LIT perp was not checked.

**Decision: no lane.** No LIT or HYPE event in 2026-11-13..2027-03-31 falls under R265's rule, so nothing exists that
R266 could miss, and FEAT-004 step 3 (`experiments/litunlock_fwd`) does not apply. Calling a linear stream an unlock
event would change R265's rule, so it is a new idea: **M538** (UNTESTED) in `registry/methods.csv`, the short from
the close of D-7 to the close of D+14 around a first insider `linear_start` of at least 0.25% of max supply a week,
with its kill test written there (archive cross-section on the R265 snapshot first; LIT's own 2026-12-29 start is
one forward instance and decides nothing alone). It would need its own frozen PREREG and round before any return is
read. Notes added on M057, M506 and M537.

## What a large LIT unlock means for R447 (llpstake_v1)

No return, funding sum or price after 2026-11-10 was computed for this section. It reads R447's frozen book
([PREREG](../../experiments/llpstake_v1/PREREG.md)): per 1 LIT staked, 10 USDC in LLP, the LIT held and staked, and a
short of 1 LIT on Lighter's LIT perp margined at 1x. The stream starts on 2026-12-29, inside gate 1's first 90 scored
days (look on 2027-02-08), and runs past the 180-day look (2027-05-09).
- **Stake value against the short.** The stake and the short are the same size in LIT, so a fall in LIT from new
  supply moves both legs by the same amount; only the spot-to-perp basis stays in the book. The unhedged line (R447
  "stake held without the short") carries the full move and decides nothing.
- **Funding sign.** The short earns funding only while longs pay. Longs paid in every month to 2026-11-10 (section
  above). If holders of newly unlocked LIT, or traders front-running it, short the perp, funding can turn negative
  and the short pays. This is the R447 leg most exposed to the unlock, and its PREREG already names a funding regime
  shift on LIT as the lane's main unknown.
- **Liquidation.** R447's check fires on a daily high of 2/1.2 times the previous close (+66.7%). Selling pressure
  from an unlock moves price the other way; the risk stays a short squeeze, as before. A 5x short would be closer.
- **LLP access demand.** LLP needs 0.1 LIT staked per USDC. Unlocked LIT that is staked for LLP access adds deposits,
  which spread LLP's liquidation income over more capital; unlocked LIT that is sold adds supply. Which one dominates
  is not known, and no staked-LIT total is available (unread list below).
- **Lock-up timing.** Unstaking takes 3 days and LLP withdrawal 5 minutes, while the perp short can be closed at once.
  An exit around the unlock would leave the stake unhedged for those 3 days if the short were closed first.
- **Buyback against supply.** The buyback bought 20,000 to 41,000 LIT a day in September and October; the stream adds
  about 456,000 a day, 11 to 23 times more. This matters for M537's flow and the unhedged line, not for the hedged book.

## What stays unread or unverified
- LIT's vesting from a Lighter primary source (NOT_FOUND, SRC1113-011); DefiLlama's schedule cites no source.
- The emissionsIndex body R266 snapshots (23.5 MB, not downloaded); whether MEXC lists a LIT perp.
- Whether bought-back LIT is burned, held by the zero-address treasury or re-used for staking rewards.
- The staked LIT total and the reward address's purchases (no keyless endpoint found; `exchangeMetrics` has no
  staking kind).
- exchangeMetrics units and the day each point covers (read as 00:00-24:00 UTC); the docs do not say.
- HLP's fee share; Hyperliquid's legacy vault pages beyond SRC1103-003; HYPE buyback history.
- Lighter Explorer API stats beyond the List Total Values schema; `exchangeMetrics` with `filter=byMarket`.
- HLP's current TVL (vaultDetails not called, see scope rules); LLP's TVL above is a single point.

## Routing
- `registry/methods.csv`: new **M536** (LLP day return as the house's P&L signal, UNTESTED; FEAT-003) and **M537**
  (LIT buyback TWAP flow, UNTESTED).
- `registry/methods_aliases.csv`: `WS1113-LIT-BUYBACK-COVERAGE` to M518; `WS1113-LIT-INSIDER-UNLOCK` to M057 (FEAT-004
  decides); `WS1113-HYPE-ASSISTANCE-FUND` to M518 (context); `WS1113-LLP-ACCESS-DEMAND` to M506 (context).
- Links: [M285](../../registry/methods.csv), M505 ([R446](../../experiments/dexvault_v1/FINDINGS.md)), M506
  ([R447](../../experiments/llpstake_v1/FINDINGS.md)), M510 ([R454](../../experiments/hlpinv_v1/PREREG.md)), M511
  (R455), M518 ([idea wave 5](idea_wave5_20261111.md)), M057 ([R266](../../experiments/unlocks_fwd/PREREG.md)).
- FEAT-004: ledger WS0020 (SRC1113-009 re-fetch, VERIFIED) and WS0021 (SRC1113-012, HYPE); new **M538** (insider
  linear-start short, UNTESTED, no lane); notes on M057, M506 and M537. `WS1113-LIT-INSIDER-UNLOCK` stays an alias of
  M057: the decision is no R265 event.
- No frozen file, lane, workflow, round row or earlier ledger row was changed.
