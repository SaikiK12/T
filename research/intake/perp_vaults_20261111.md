# Perp-DEX vaults beyond HLP and LLP: competitors, mechanics, data (intake, 2026-11-11)

The owner asked on 2026-11-11 to look at HLP's and LLP's competitors and methods for better results that a real
deposit would reproduce. Two Haiku readers worked on it the same day: one on competing vaults, one on HLP and LLP
mechanics. This page keeps what they read, what the author checked again, and what nobody read. It feeds M505, M507
and R452 (`experiments/litpoolsel_v1`). It is not evidence of a return.

**Labels:**
- **[A]** checked again by the author: page or endpoint fetched and matched.
- **[V]** read on the fetched page by a helper.
- **[S]** search snippet only.
- **[U]** not found or not read.

## What a depositor gets, and how paper can differ
- **HLP:** "The deposit lock-up period is 4 days" (hyperliquid.gitbook.io, protocol vaults). No leader commission
  (API `leaderCommission` 0) [V]. Withdrawals may slip "as you withdraw and open positions are closed" (legacy
  depositor page) [V]. Seven child vaults: Strategy A, B, X (market making) and Liquidator 1-4 [V, names only].
- **LLP:** deposits only against staked LIT, up to 10 USDC per LIT; 6% fixed APR on the stake; 3-day unstaking
  lockup; 5-minute withdrawal cooldown [V]. Up to 1% liquidation fee goes to LLP. It takes over positions while it
  stays above initial margin, otherwise ADL [V].
- **Lighter's public pools** (docs.lighter.xyz/trading/public-pools) [A]:
  - the operator's fee is "the percentage of profits allocated to the operator upon participant withdrawals";
  - "Public Pools do not impose lockup periods";
  - "LLP deposits are also limited by LIT staking";
  - the minimum operator share caps deposits (example: an operator holding 10,000 USDC at a 10% minimum allows
    90,000 USDC of deposits).
- **Where paper and a real deposit part:**
  - lockups and cooldowns (HLP 4 days, LLP's LIT unstaking 3 days);
  - slippage on exit while positions close;
  - fees charged at withdrawal against the deposit's own gain;
  - the LLP cap in USD moves with LIT's price;
  - losses socialized by liquidation takeover or ADL.
  - Third-party trackers strip deposit and redeem flows, so their P&L differs from the app's [V].

## Loss events (dates matter for any window)
- **HLP:**
  - 2025-03-12 whale liquidation, about $4M [V, The Block].
  - 2025-03-26 JELLY: peak unrealized loss about $10.6-13.5M, settled at about +$0.7M [S, sources disagree].
  - Gained about $40M over the 2025-10-10/11 crash [S].
- **LLP:** lost about 5% (about $21.5M) on 2025-10-10 [S; the fetched article did not contain the figure].

## Competing vaults
| Vault | Mechanism | Lockup / withdrawal | Public history | France in its terms |
|---|---|---|---|---|
| dYdX MegaVault | AMM market making across pairs [V] | On demand, slippage possible; future lockups flagged [V] | **Yes [A]:** `indexer.dydx.trade/v4/vault/v1/megavault/historicalPnl` (equity, totalPnl, netTransfers): 85 daily points from 2026-08-14, or 168 hourly points with `?resolution=hour` | Help center bars the US, Canada, UK, sanctioned countries; France not named [V] |
| Paradex vaults | 1,659 vaults listed (7 protocol, "DIME" strategies) [V] | About 5 minutes after deposit, plus per-vault lockup [V] | No: per-vault endpoints return 401 [V] | [U] (terms 404) |
| Extended (x10) | Market making and liquidations, 50% of net fees [V] | 24 h lockup per deposit; withdrawer bears price impact [V] | No endpoint found [U] | [U] (403) |
| edgeX eLP | Market making, liquidations, fees [S] | 48 h after request [S] | Not probed | Mirror terms bar US and Canada; France not named [V, mirror only] |
| Aster ALP | NAV pool, counterparty [V] | 48 h burn lock [S] | No ALP endpoint [V] | [U] |
| Drift insurance fund | Staked backstop, all revenue to stakers [V] | 13-day cooldown, 90% utilization gate [V] | API unreachable (502) | [U] |
| Avantis (Base) | Junior/senior tranches [S] | [U] | None found | [U] |
| Ostium OLP | Counterparty LP; $23.75M drained 2026-07-15 [S] | Epoch request, 24-48 h [V] | None found | [U] |
| Gains gTokens | Counterparty to all trades [V] | 1-3 epochs after request [V] | None found | [U] |
| Orderly OmniVault | Up to 40% of protocol revenue [V] | 3-hour settlement periods [V] | None found | [U] |
| GRVT GLP, Nado NLP, Bluefin | [S] only | [U] | 403 / 503 | [U] |

- **dYdX MegaVault's size [A]:** equity about $1.9M on 2026-11-11, against about $1.7M on 2026-08-14. The author saw
  its totalPnl move over those 89 days while probing the endpoint. That is a rough level, not a registered read: it
  is in the high single digits a year, below HLP and LLP in 2026 (R446). Any MegaVault lane lists it as seen.
- **APRs:** none of the competitors' published APRs was verified as current. All are [S] and undated.

## Lighter's public pools (checked by the author)
- `publicPoolsMetadata?filter=all`, paged by `index`, lists **347 pools** [A]. The helper counted 247; the author's
  paging found 347.
  - 195 are Lighter's own 1x-3x long/short index pools (master account 4, fee 0).
  - 2 are protocol pools (account type 3): LLP (about $99.7M) and XLP ("Experimental Liquidity Provider", fee 0,
    about $40k). XLP's deposit rules were not found [U].
  - 150 are operator pools: fees of 0-30% of profits; 82 with status 0 and 68 with status 1. Most were created in
    2025-09 and 2025-10. Most hold under $10k; five hold over $400k.
- `account?by=index&value=<pool>` returns `pool_info.share_prices`: one daily point per pool since its start (about
  415 points for pools from 2025-09) [A]. This is the series R452 reads.
- The documented `publicPools` list endpoint returned 403 (CloudFront) to the helper; not bypassed.

## Not read or unresolved
- HLP's deposit cap and minimum; whether the Liquidator child vaults are retired.
- An official Lighter statement on 2025-10-10; whether LLP ever ran ADL.
- What status 1 means for a Lighter pool, and whether deleted pools leave the list.
- Terms for Paradex, Extended, GRVT, Aster, Drift, Avantis, Ostium, Gains, Nado, Orderly and Bluefin.
- Any competitor's share-price history except dYdX MegaVault's equity series.

## Use
- **R452** tests Lighter's operator pools picked by past record, on their own share prices.
- **R450** (Hyperliquid user vaults) waits for its data branch.
- **dYdX MegaVault:** only three months of daily history and a small vault; no lane now.
- The scratch reports (`vault_competitors.md`, `hlp_llp_mechanics.md`) were not kept. This page holds their checked
  content.
