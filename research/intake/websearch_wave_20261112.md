# Web search wave 2026-11-12: carry red team and the passive-yield hurdle

Source and mechanics intake, 2026-11-12, lens 5 (red team on the surviving carry family), with lens 6+7 only
where a public keyless dataset exists today. Run under [`docs/WEB_SEARCH.md`](../../docs/WEB_SEARCH.md); ledger
rows WS0002 to WS0008 in [`registry/web_searches.csv`](../../registry/web_searches.csv); catalog
[`source_catalog_websearch_20261112.csv`](source_catalog_websearch_20261112.csv) (SRC1112-001 to SRC1112-014);
cards in [`cards/`](cards/) for SRC1112-001 (which also covers -002 to -006), -007, -008, -009 and -010.

No return, APY statistic, trial or verdict is computed here. The only market-history bytes touched are the three
DefiLlama `/chart` bodies described under "Sealed capture"; of those, only the keys and the timestamp column were
read. Costs 1x/2x/3x: N/A (sources and mechanics only), not zero.

## Why this wave
The lab's only edge family that survives its own audits is cross-venue funding carry
([R437](../../experiments/carry_v2_audit_v1/FINDINGS.md), [R438](../../experiments/carry_v2_audit_kc_v1/FINDINGS.md):
+6 to +18%/yr on book capital at 1x, NW t 3.5 to 9.6, forward lanes deciding). Two questions bear on the
best-net-PnL objective: what can still break those books live (red team), and do they beat the passive yields that
harvest the same payer (M481, sUSDe) or lend the same dollars (M478, Aave USDC). R437/R438 compared only against the
4.13% T-bill hurdle.

## Dedupe (before searching)
`lab websearch seen` and `lab find` found nothing for sUSDe, Ethena, defillama, "funding arbitrage", "crypto carry",
Manela, "Fundamentals of perpetual", 2603.15963, 2605.11263 or 2605.05089. Hits built on:
- [SRC1103-022](source_catalog_webdeep_20261103.csv) (Galaxy, 2025-10-10 cascade: USDe about 0.65 on Binance, ADL on
  several venues). Not re-read; cited as already verified on 2026-11-03.
- SRC26-011 (Aave liquidations help page): unrelated to supply rates, not re-read.
- [idea wave 7](idea_wave7_20261111.md) section 5 and alias `IW7-PERP-SPOT-PAPER`: He, Manela, Ross and von Wachter,
  abstract only. This wave reads the full text sections listed below.
- M136 (R207 NULL, carry predicts crashes), M192 (stablecoin supply, BLOCKED), M468-M470, M475, M478, M481, M512.

## Primary source register and read scope
All accessed 2026-11-12 between 23:20 and 23:59 UTC with curl or web_fetch on public keyless pages. No login,
paywall, bot check or key was bypassed. "Read" means the exact scope in the third column and nothing more.

| Id | Source | Read scope and the statement used | Fetch |
|---|---|---|---|
| SRC1112-001 | [DefiLlama API docs](https://api-docs.defillama.com/): page bundle `assets/api-specifications-uhVzZ1Dc.js`, [llms.txt](https://api-docs.defillama.com/llms.txt), and the repo spec [`defillama-openapi-free.json` at 01415ef178](https://raw.githubusercontent.com/DefiLlama/api-docs/01415ef178/defillama-openapi-free.json) | Partial: info banner, yields tag description, `/pools` and `/chart/{pool}` path objects. "The free yield endpoints `/pools` and `/chart/{pool}` shut down on **November 13, 2026**"; the same data stays on the paid API plan at `/yields/v1/...`; pool ids unchanged. `/chart` schema: `timestamp`, `tvlUsd`, `apy`, `apyBase`, `apyReward`. llms.txt (same site) still lists the free routes without the warning. | FETCHED_PARTIAL; VERIFIED by a second fetch of the repo spec through a different tool and host |
| SRC1112-002 | [yields.llama.fi/pools](https://yields.llama.fi/pools) (live, 200, 10,807,215 bytes, 23:41:10 UTC, sha256 d51d1ab6...) | Metadata of ethena-usde and aave-v3 Ethereum stable pools only (pool, project, symbol, poolMeta, underlyingTokens, tvlUsd rounded, count). APY fields not read. | FETCHED_PARTIAL |
| SRC1112-003 | [yields.llama.fi/chart/{pool}](https://yields.llama.fi/chart/66985a81-9c51-46ca-9977-42b4fe7bc6df) for three pools | Bodies saved unread (see Sealed capture). Read: keys, row count, timestamps, null counts, and whether `apy` equals `apyBase` row by row. No APY or TVL value was printed or summarised. | FETCHED_PARTIAL (sealed) |
| SRC1112-004 | [DefiLlama yield-server, `ethena-usde` adaptor at 322ddd46](https://github.com/DefiLlama/yield-server/blob/322ddd46e7fd4b2b4221e502730a041d4fce3b76/src/adaptors/ethena-usde/index.js), `utils.aprToApy`, path history and diffs of 7d987365d2 and d58559b311 | Full file (65 lines). `apyBase` = (latest `RewardsReceived` amount x 3 x 365) / tvlUsd x 100, then `aprToApy(apr, 52)` = ((1 + apr/100/52)^52 - 1) x 100. 2025-04-08 (7d987365d2): TVL price key changed from USDe to sUSDe. Earlier commit titles only: 2024-02-22 "ethena compound apr", 2024-03-15 "ethena use previous weeks rewards", 2024-03-18 "ethena switch to 8h reward calculation". | FETCHED_FULL (file); titles only for older commits |
| SRC1112-005 | [DefiLlama yield-server, `aave-v3` adaptor at 322ddd46](https://raw.githubusercontent.com/DefiLlama/yield-server/322ddd46e7fd4b2b4221e502730a041d4fce3b76/src/adaptors/aave-v3/index.js) | Partial: lines 23-64 (data providers, `ethereumMarkets` = {lido: "Prime Instance", horizon: "Aave Horizon Market"}) and 200-255 (pool object). Core Ethereum market rows get `poolMeta` null; `apyBase` = liquidityRate / 1e27 x 100. Umbrella rows (lines 414-462) carry `poolMeta` "Umbrella". | FETCHED_PARTIAL; VERIFIED by re-fetch via raw.githubusercontent with web_fetch |
| SRC1112-006 | [aave-v3-origin at 8305565a](https://github.com/aave-dao/aave-v3-origin/tree/8305565ae342f1773c42cd2e4593f175fe5968a0): `ReserveLogic.sol`, `MathUtils.sol`; [Aave V3 docs llms-full](https://aave.com/docs/aave-v3/llms-full.txt) | Code: `getNormalizedIncome` and `_updateIndexes` accrue supply with `calculateLinearInterest(rate, t) = 1 + rate x dt / SECONDS_PER_YEAR`, `SECONDS_PER_YEAR = 365 days`; borrow uses compounded interest. Docs: "Interest Rates" section and the ReserveData table (`currentLiquidityRate`: "The current supply rate. Expressed in ray"). | FETCHED_PARTIAL |
| SRC1112-007 | Ethena docs (GitBook, `.md` routes): [Staking USDe](https://docs.ethena.fi/technical-design/staking-usde), [Rewards Mechanism](https://docs.ethena.fi/protocol-overview/rewards-mechanism), [Staking Key Functions](https://docs.ethena.fi/technical-design/staking-usde/staking-key-functions), [Reserve Fund](https://docs.ethena.fi/protocol-overview/reserve-fund), [Protocol Revenue](https://docs.ethena.fi/backing-assets/protocol-revenue), [Funding Risk](https://docs.ethena.fi/protocol-overview/risks/funding-risk), [Exchange Failure Risk](https://docs.ethena.fi/protocol-overview/risks/exchange-failure-risk) | Seven full pages (charts not viewed). "The acquisition of sUSDe is not offered to persons with their habitual residence or registered office in the European Union or the European Economic Area." Rewards are paid every 8 hours, vest linearly over 8 hours, relate to the previous week, and differ from "a number that's just based on the most recent 8 hourly payment ... as seen on some data aggregator sites". Rewards are positive or zero; the Reserve Fund bears negative revenue; its revenue share is currently 0%. Cooldown is settable up to 90 days. | FETCHED_FULL per page; the EEA and aggregator statements VERIFIED by a second web_fetch |
| SRC1112-008 | He, Manela, Ross, von Wachter, [Fundamentals of Perpetual Futures, arXiv 2212.06888v7](https://arxiv.org/html/2212.06888v7) (2026-09-17) | Partial: abstract; section 1; 4.1 (data: Binance hourly, BTC ETH BNB DOGE ADA, 2020 to 2024-03-11); 4.3 text and Table 5-7 captions; 4.4 text, Table 8 values and the drawdown paragraph. Not read: sections 2-3 proofs, 5, 6, appendices. | FETCHED_PARTIAL |
| SRC1112-009 | Schmeling, Schrimpf, Todorov, [Crypto carry, BIS WP 1087](https://www.bis.org/publ/work1087.htm) (April 2023), [PDF](https://www.bis.org/publications/working-paper-1087-crypto-carry.pdf) | Landing page abstract and "Focus/Contribution/Findings" summary; PDF pages 1 and 21-24 (printed 18-21: cash-and-carry strategy, margins, Table 5 and 6 discussion). Not read: the rest. | FETCHED_PARTIAL |
| SRC1112-010 | Campbell, Hey, Moallemi, Nutz, [Risk-Based Auto-Deleveraging, arXiv 2603.15963v2](https://arxiv.org/html/2603.15963v2) (2026-07-16) | Partial: abstract; section 4 introduction; 4.1 "The ADL Event" and "Data sources". 2025-10-10 Hyperliquid: realized ADL notional $2.047bn on a 75-coin universe, in bursts within 21:16-21:21 UTC; waves $176.9m, $93.3m, $386.6m; BTC, ETH, SOL fell about 10-20% intraday, thinner coins more than 50%. Not read: proofs, 4.2-4.3 results, appendices. | FETCHED_PARTIAL |
| SRC1112-011 | [Hyperliquid docs, Auto-deleveraging](https://hyperliquid.gitbook.io/hyperliquid-docs/trading/auto-deleveraging) | Full page: opposite-side users ranked by `(mark_price / entry_price) * (notional_position / account_value)`; closed at the previous mark price against the underwater user. | FETCHED_FULL |
| SRC1112-012 | Lorig, [Optimal Control of the Ethena Yield-Bearing Stablecoin, arXiv 2605.11263v2](https://arxiv.org/abs/2605.11263) | Abstract only (arXiv API). Models stETH long plus ETH perp short; permanent impact of Ethena's own hedging compresses the basis. | FETCHED_PARTIAL (abstract) |
| SRC1112-013 | Krestenko et al., [Dynamic Collateral Control for Permissionless Spot Perpetual Basis Trading, arXiv 2605.05089](https://arxiv.org/abs/2605.05089) | Abstract only: realized execution wedges are significant and worse when selling the basis; backtest performance "predominantly explained by the funding environment". | FETCHED_PARTIAL (abstract) |
| SRC1112-014 | Public Ethereum RPC archive probe (one `eth_getBalance` of the zero address at block 20,000,000) | ethereum-rpc.publicnode.com: "Archive requests require a personal token"; rpc.ankr.com: API key required; eth.llamarpc.com: bot check page (not bypassed); cloudflare-eth.com: internal error. No keyless archive route found. | BLOCKED |

Searched and not read: exchange "earn" stablecoin rates (Binance api.binance.com answers 451 here; no other venue's
earn page was opened). arXiv API title searches for "funding rate arbitrage", "auto-deleveraging", "basis trade",
Ethena/USDe returned the papers above; nothing else relevant by title.

## Verified claims (independent re-fetch)
1. **DefiLlama's free `/pools` and `/chart/{pool}` shut down on 2026-11-13** (no hour stated). First seen in the
   docs bundle by curl; re-fetched as the repo's `defillama-openapi-free.json` at commit 01415ef178 (2026-11-12
   10:54 UTC) with web_fetch: same text. VERIFIED. llms.txt on the same site does not carry the warning, so the
   docs disagree with each other; the spec is the more specific source. A keyless replacement was not found
   (SRC1112-014). This changes FEAT-003's design: the "fetch after freeze" step cannot be run after the shutdown.
2. **sUSDe is not offered to EU/EEA residents.** Read by curl on the `.md` route, re-fetched by web_fetch on the
   HTML route: same sentence. VERIFIED. For a France-resident owner sUSDe is a benchmark of what the payer's money
   earns elsewhere, not an investable alternative. No legal determination is made here.
3. **The Aave v3 Core-market USDC pool is `aa70268e-4b52-42bf-a116-608b370f9501`.** It is the only aave-v3 Ethereum
   USDC row with `poolMeta` null and underlying native USDC (0xA0b8...eB48); the adaptor sets `poolMeta` null only for
   the core `ethereum` market (lido = "Prime Instance", horizon = "Aave Horizon Market", Umbrella rows wrap the stata
   token). Re-fetched the adaptor via raw.githubusercontent with web_fetch: same mapping. VERIFIED.
4. **DefiLlama's sUSDe `apyBase` is a one-payment annualisation**, which Ethena itself says differs from its
   published APY. Code (SRC1112-004) and Ethena's Rewards Mechanism page agree; the page was re-fetched. VERIFIED.

## Sealed capture of the benchmark bodies
Because of claim 1, the three `/chart` bodies were fetched once at 2026-11-12T23:41:27Z, before the shutdown and
before FEAT-003's PREREG. They are stored outside the repo, unread, at `/projects/sandbox/sealed_chart_20261112/`
(with the response headers and `receipt.txt`). FEAT-003 should copy them into its lane only after its freeze
commit, and its runner should refuse any body whose hash differs from these:

| Pool | URL | HTTP | Bytes | sha256 |
|---|---|---|---|---|
| sUSDe (ethena-usde) | https://yields.llama.fi/chart/66985a81-9c51-46ca-9977-42b4fe7bc6df | 200 | 160,643 | 4ad057baa24c7d6b18b02d7b66ca8f6832405127017e7ab19832ca8635073d06 |
| Aave v3 Core USDC | https://yields.llama.fi/chart/aa70268e-4b52-42bf-a116-608b370f9501 | 200 | 218,392 | 007e634e247ae349cd4c89b10b28a3b14b7f5a3a5229ed694adae1a377aaf87d |
| Aave v3 Core USDT (report only) | https://yields.llama.fi/chart/f981a304-bb6c-45b8-b0c5-fd2f515ad23a | 200 | 217,283 | 40bfab15bfda45d6a1cb00dd2baef6b5f8c4d1e9779b60a2de627802204babc7 |
| `/pools` snapshot (metadata) | https://yields.llama.fi/pools | 200 | 10,807,215 | d51d1ab62b645b1943985e1c523496f4def00d8b02223afd2595610218fc7876 |

This is a deviation from FEAT-003's planned order (freeze, then fetch). The order that matters under hard rule 1
holds: the bytes are fixed and hashed here, in a commit that precedes any PREREG, and no statistic of them has
been computed or read. If FEAT-003 prefers a live fetch, it must first check whether the free endpoint still
answers; the paid `/yields/v1/` route needs a key and is out of scope.

## Pre-specified inputs for FEAT-003 (R483 carryhurdle_v1)
- **Endpoint and response.** `GET https://yields.llama.fi/chart/{pool}` returns
  `{"status": "success", "data": [{timestamp, tvlUsd, apy, apyBase, apyReward, il7d, apyBase7d, pricePerShare}]}`.
  In all three captured bodies `apyReward`, `apyBase7d`, `il7d` and `pricePerShare` are null in every row, and
  `apy` equals `apyBase` in every row.
- **Pools.** Decider benchmark sUSDe `66985a81-9c51-46ca-9977-42b4fe7bc6df` (ethena-usde, Ethereum, poolMeta
  "7 days unstaking", underlying USDe 0x4c9E...8B3). Report-only Aave v3 Core USDC
  `aa70268e-4b52-42bf-a116-608b370f9501`; optional report-only Aave v3 Core USDT
  `f981a304-bb6c-45b8-b0c5-fd2f515ad23a`. Not these: `6f00d46b-...` (Umbrella stake token), `effcb4a4-...` (Prime),
  `27296bf9-...` (Horizon), `29932dea-...` (sUSDe supplied to Aave).
- **Field and units.** `apyBase`, percent per year (equal to `apy` in these bodies).
- **History and day convention.** One row per UTC date, no missing or duplicate dates. sUSDe: 1001 rows,
  2024-02-16T23:01:19Z to 2026-11-12T23:01:33Z. Aave USDC: 1376 rows from 2023-02-06T23:01:24Z. Aave USDT: 1369 rows
  from 2023-02-13T23:01:01Z. 996 of 1001 sUSDe stamps (1363 of 1376 Aave USDC) fall in the 23:00 UTC hour; the rest
  at 11, 16, 19, 21 or 22 h. So the row dated D is a snapshot near the end of UTC day D.
  - Causal alignment: the book's net for UTC date D is compared with the rate from the row dated D-1, the last
    snapshot before D starts. Same-day alignment would use a rate observed 23 hours into D.
  - Missing-day rule: drop D when the D-1 row is absent; never fill. None is absent in the capture.
- **What each value means (conversion must follow the field, not the label).**
  - Aave: `apyBase` = `liquidityRate` / 1e27 x 100. The contract accrues supply at that rate as simple interest
    on a 365-day year between index updates, so this is an APR. Daily simple rate: `apyBase / 100 / 365`.
    Applying `(1 + APY/100)^(1/365) - 1` would treat it as an APY and understate it slightly.
  - sUSDe: `apyBase` = weekly-compounded annualisation of the latest 8-hour `RewardsReceived` payment over TVL.
    Its inverse is `apr = 52 x ((1 + apyBase/100)^(1/52) - 1)`, so the daily rate is `apr / 365`.
    `(1 + apyBase/100)^(1/365) - 1` is a close approximation. FEAT-003 must freeze one of the two.
  - The value is a spot rate at the snapshot, not the realised daily change of the sUSDe:USDe exchange rate.
    Ethena pays rewards a week after the period they relate to.
- **Known breaks in the sUSDe series (from code history; not checked against the data).**
  - Before 2025-04-08 the adaptor priced TVL with the USDe price instead of the sUSDe price. Since sUSDe trades
    above 1 USDe, this understates TVL and inflates `apyBase` by the same ratio, if the rows were not recomputed.
  - Before 2024-03-18 the method changed twice.
  - Suggested report-only split for FEAT-003: rows from 2025-04-09 onward. The decision window is FEAT-003's call,
    made before reading.
- **Window.** Book dates end 2026-09-30. sUSDe overlap starts 2024-02-17 (rate from the 02-16 row). Aave USDC
  overlap starts 2023-02-07. Book start dates differ (gate+kucoin 2021-01-22; gate+hyperliquid 2023-05-25).
- **Risk not in any APY series.**
  - sUSDe: USDe depeg (about 0.65 on Binance on 2025-10-10, SRC1103-022, venue-specific); a 7-day cooldown
    (admin can set up to 90 days); sanctions freezing; and the EEA restriction above.
  - Aave: contract and oracle risk, and withdrawal limits at high utilisation. Aave's docs on the latter were not
    read here.

## Red team: live failure modes of the carry books (R437 seven books, R438 two books)
Pairs open on 2025-10-10 are counted from the committed `results/trades_v2.csv` of both lanes (entry on or before
and exit on or after that date). This is an exposure count, not a P&L number.

| Failure mode | Source | Priced by the archive? | Measurable now? |
|---|---|---|---|
| ADL of the profitable leg in a crash, leaving the other leg naked | SRC1112-011 (ranking and close at previous mark); SRC1112-010 ($2.047bn ADL on Hyperliquid within 21:16-21:21 UTC on 2025-10-10); SRC1103-022 (ADL on several venues) | No. Daily last-trade marks, no ADL events. Every book held 14-21 pairs that day; gate+hyperliquid (R278 A) had 19 of 21 pairs short on Hyperliquid, hyperliquid+mexc 20 of 21, binance+hyperliquid 17 of 20 | Partly. A stress bound from committed trades_v2 plus public daily high/low candles of the long-leg venue (new M534). ADL incidence per account is not public keyless (SRC1103-001 fill limits) |
| Forced liquidation of a leg before convergence (margin spikes, no cross-margin across venues) | SRC1112-009: at 10x leverage the CME futures leg "would have been liquidated in more than half of the months"; a 10% rise in carry predicts a 44% rise in short-futures liquidations. SRC1112-008 (Table 8): max drawdowns up to 3.90% (BTC) and 13.90% (DOGE); liquidation also depends on leverage, maintenance margin and margining regime (section 4.4) | No. Books are scored at 1x book capital with no per-venue margin model | Not on committed data: trades_v2 has per-trade P&L, not the per-leg price path |
| Venue insolvency or withdrawal halt | SRC1112-007 Exchange Failure Risk (Ethena limits exposure to one daily settlement cycle via off-exchange settlement; FTX named) | No. The books post margin on Gate, MEXC, KuCoin, Binance, Hyperliquid with no off-exchange settlement | Scenario only (lose one venue's posted margin); no public keyless data prices it |
| Funding interval or cap changes | WS0001 (three contradicted claims on HL cap and Binance hourly switch) | Yes for history (realised funding); not for future changes | Already in the data |
| Spot or borrow leg unavailable | SRC1112-008 (long-spot-only variant) | N/A: both legs are perps | N/A |
| Collateral depeg or haircut | SRC1103-022 (USDe 0.65, wBETH and BNSOL -80 to -90% on Binance) | No. Margin assumed at par in USDT/USDC | Not here; USDT/USDC depeg sources were not read |
| Opportunity cost: a passive token harvests the same payer | SRC1112-007 (revenue from funding and basis, lending, RWA, stablecoin rewards; Reserve Fund absorbs negative revenue; rewards never negative) | No. R437/R438 compare with a 4.13% bill only | **Yes**: R483 on committed daily nets plus the sealed DefiLlama capture (FEAT-003) |
| Edge decay and crowding | SRC1112-008 (deviations fall about 22 points a year; funding is a minor and shrinking share of the strategy's return); SRC1112-012 (the hedger's own impact compresses the basis) | Partly: R437 halves show R278 A falling from +5.13 to +1.49 bp/day | Already reported; the forward lanes decide |

Costs: SRC1112-008's highest fee tier is 6.75 bp spot plus 1.44 bp perp per side, plus half the effective spread.
That is below the lab's 7, 14 and 21 bp per leg, so the lab's cost grid is not the weak point. That paper's
Sharpe ratios (Table 8, high tier with spread: BTC 3.27, ETH 4.45) come from hourly convergence trades on one
venue, mostly price convergence, and are not comparable with the lab's daily cross-venue funding books.

## Deduction
- Two failure modes are measurable today on committed data plus public keyless bytes. The opportunity cost
  (FEAT-003, R483) is the first, and its benchmark bytes are already sealed. The ADL stress bound (M534) is the
  second.
- The others are not measurable from here:
  - Forced liquidation needs per-leg price paths.
  - Venue failure and collateral depeg are scenarios.
  - Interval and cap changes are already in the realised funding.
- The sUSDe comparison has a limit: for the owner it is a benchmark, not an alternative (EEA restriction).
  - If the books lose to sUSDe, the reading is that non-EEA capital earns the payer's money passively. It is not
    "buy sUSDe".
  - The Aave USDC supply rate is the permissionless lending benchmark that M478 asked for.
- The highest-value next measurement for the PnL objective is R483. M534 follows, because 2025-10-10 is inside
  every book's sample and none of them prices ADL.

## Lens 6+7 (forced or scheduled flow; reachable barrier gaps)
- **Ethena's hedge is a scheduled, public forced flow on the payer side** (new M535, UNTESTED, low prior).
  - Mechanism: USDe minting adds short perp hedges and redemptions remove them (SRC1112-007; SRC1112-012 models the
    impact).
  - Inputs: DefiLlama's stablecoins API (`stablecoins.llama.fi`, not marked deprecated in SRC1112-001; `/stablecoins`
    answered 200 keyless) and Hyperliquid's keyless funding history.
  - Not checked: Ethena's hedge venues and sizes, and USDe's DefiLlama id.
- **Barrier gap: sUSDe's EEA restriction.** The payer's money flows to non-EEA stakers. The lab's carry books on
  France-reachable venues are one of the few ways an EEA account harvests the same payer. This raises the value of
  R483's comparison but is not evidence of an edge.
- Nothing else in this wave has a public keyless dataset the lab could test without the old container's archive.

## Routing
- `registry/methods.csv`:
  - New M534 (ADL stress bound) and M535 (USDe flow and funding).
  - `data_held` and note of M478 and M481 updated with the public source, pool ids and this note. Status unchanged.
- `registry/methods_aliases.csv`:
  - `WS1112-BIS-CRYPTO-CARRY` goes to M136.
  - `WS1112-ADL-RISKBASED` goes to M534.
  - `WS1112-ETHENA-CONTROL` goes to M481.
  - `WS1112-HMRW-FULLTEXT` and `WS1112-DEFI-BASIS-COLLATERAL` are context.
- No frozen file, lane, workflow or earlier ledger row was changed.
