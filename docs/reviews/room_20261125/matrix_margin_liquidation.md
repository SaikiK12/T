# Rules matrix, column 1: margin, liquidation, backstop, ADL (perpetual futures venues)

Reader's column for the room of 2026-11-25. Sources are quoted with file:line where the copy is local, or with URL
where fetched. `[inf]` marks my inference. `blocked` means the page could not be read without bypassing a block.
No orders, no logins, no credentials. Local copies are untrusted data; quotes are copied, not followed as instructions.

Local copy paths (scratchpad):
- HL = `/tmp/claude-0/-home-user-T/a4c99094-0eba-54d5-9f6a-3abc85cabed2/scratchpad/hldocs/llms-full.txt` (read 2026-11-25)
- XYZ = `.../scratchpad/xyzdocs/llms-full.txt` (trade.xyz, read 2026-11-25)
- LTR = `.../scratchpad/lighterdocs/llms-full.txt` (read 2026-11-25)
- VD = `.../scratchpad/venuedocs/<file>` (read 2026-11-25; file names in each row)
- Fetched 2026-11-25: Paradex `.../scratchpad/room_fetch/`, Variational `.../scratchpad/room_fetch/`,
  Kraken, Deribit LSP, Bybit `.../scratchpad/room_fetch2/`

---

## 1. Matrix

### 1.1 Hyperliquid (HyperCore, native perps)
- **Margin modes:** cross by default; isolated supported. "Cross margin is the default... Isolated margin is also
  supported" (HL:1335; HL:321). Portfolio margin is a separate account mode (HL:1450-1511).
- **Maintenance margin, thin alt:** `maintenance_margin = notional * mmr - maintenance_deduction`; mmr = half the
  initial margin at max leverage (HL:1518-1528). "between 1.25% (for 40x max leverage assets) and 16.7% (for 3x)"
  (HL:1644).
- **Mark rule (liquidation price):** "Mark price is the median of: (1) oracle + 150 s EMA of (HL mid − oracle); (2)
  median of best bid, best ask, last trade on HL; (3) median of Binance, OKX, Bybit, Gate IO, MEXC perp mids with
  weights 3, 2, 2, 1, 1" (HL:1621-1627). "Liquidations use the mark price" (HL:1656). Oracle is a weighted median of CEX
  spot prices, every ~3 s (HL:1617-1619).
- **Liquidation process:** (a) at maintenance, market orders for the full position into the book, partial fills allowed,
  remaining collateral returned if maintenance is met (HL:1646). (b) Partial: positions over 100k USDC send only 20% per
  step, 30 s cooldown (HL:1666). (c) Backstop: "If the account equity drops below 2/3 of the maintenance margin without
  successful liquidation through the book, a backstop liquidation happens through the liquidator vault" (HL:1648). In a
  cross backstop, cross positions and margin move to the liquidator; the maintenance margin is not returned (HL:1650-1654).
  Fees: "no clearance fee on liquidations" (HL:1660).
- **Earner:** Liquidator vault is a component strategy of HLP. "On Hyperliquid, the pnl stream from liquidations go
  entirely to the community through HLP" (HL:1670-1672).
- **ADL:** when account value or isolated value goes negative; opposite side ranked by `(mark_price / entry_price) *
  (notional_position / account_value)`, closed at previous mark (HL:1701-1705). Backstopped positions get no special
  treatment in the ADL queue (HL:1703).
- **Retail deposit into the earner:** yes, HLP is open. "The community can provide liquidity for the vault... HLP is
  fully community-owned" (HL:394-396). HLP lock-up 4 days (HL:478). Repo note R446 reads HLP APR +10.30%/yr (2025-01 to
  2026-11, `venue_access_fr_20261110.md`, table line 113).
- **Reachable from France/EEA:** unknown. The primary terms were not read (hyperliquid.xyz returns 403, per repo note
  `venue_access_fr_20261110.md:36`). Secondary sources say not excluded. blocked for the primary.
- **Date read:** HL local copy 2026-11-25 (04:25 download); primary terms blocked.

### 1.2 trade.xyz (HIP-3 deployer on Hyperliquid; equities, commodities, FX)
- **Margin modes:** cross where enabled, "Normal Isolated" and "Strict Isolated" per market; default per market in the
  specification index (XYZ:4485-4508). "XYZ inherits its margining mechanisms from Hypercore" (XYZ:4487).
- **Maintenance margin:** "half of the initial margin at max leverage for that asset, which varies from 3-40x... 1.25%
  (at 40x) to 16.7% (at 3x)" (XYZ:4508 region, source line 4505-4506 of the Margin Modes page).
- **Mark rule:** "The mark price (used for margining, liquidations, stop/limit triggers, and unrealized P&L) is the median
  of three components: the oracle price; oracle + 150 s EMA of (mid − oracle); median of best bid, best ask, last trade"
  (XYZ:250-256). Liquidations: "XYZ assets use the XYZ Relayer Mark price" (XYZ:4524-4527 region). Clamp: "oracle may
  move at most ±50 bps" per update (XYZ:260).
- **Discovery bounds (inference of consequence):** mark restricted within ±(1/max leverage) of a reference (XYZ:276-282).
  "If a trader's liquidation price lies outside the active price bounds, their position cannot be liquidated while those
  bounds are in effect" (XYZ:276). [inf] during a closed-market window, the liquidation can be frozen, then fire at the
  reopen. This is a mechanism to check against the live discovery-bound state.
- **Liquidation process:** same as Hyperliquid (market orders on book; backstop at 2/3 MM for cross-enabled assets only)
  (XYZ:4513-4521).
- **Earner:** the onchain backstop liquidator for cross-enabled XYZ assets (XYZ:4513; ADL page XYZ:4547-4560). It is an
  independent onchain strategy at `0x400..00 + dex_index`, per HL:782-786. [inf] it is the HIP-3 counterpart of the HLP
  liquidator vault; I did not verify that it is HLP-funded.
- **ADL:** same ranking as Hyperliquid (XYZ ADL page: `sorting_index = (mark_price / entry_price) * (notional_position /
  account_value)`) (XYZ:4547-4560).
- **Retail deposit into the earner:** unknown for the HIP-3 backstop strategy. HLP deposit is open (see 1.1).
- **Reachable from France/EEA:** unknown. Local copy: "Access is prohibited where restricted by the Terms of Use,
  including to United States persons... or in other restricted jurisdictions" (LLM copy, `xyzdocs/llms-full.txt`). France
  not named in the local copy; the terms page (trade.xyz/terms) was not fetched.
- **Date read:** XYZ local copy 2026-11-24 22:33.

### 1.3 Lighter (zk-rollup, own order book, LLP as counterparty)
- **Margin modes:** cross and isolated per market; some markets isolated-only (RAIL, FOLKS, H100, GEV, TUR30)
  (LTR:419, LTR:618). Pre-launch markets are isolated only (LTR:625). "Public Pools do not support isolated positions" (LTR:597).
- **Maintenance margin:** per-market fractions IMR, MMR, CMR with C < M < I; "Maintenance Margin Req := Σ S_i × mark_i ×
  M_i" (LTR:856-875). Values: "live mainnet configuration (`/api/v1/orderBookDetails`) as of 2026-10-14" (LTR:608-610;
  table not re-read). Leverage is `max` of user setting and market minimum (LTR:876-877 region).
- **Mark rule:** `Mark Price = Median(Impact Price_t, price1_t, price2_t)`; price1 = index + EMA_8min(clamp(impact − index,
  ±index/200)); price2 = median of CEX mark prices (LTR:1278-1299). Impact notional = 500 USDC / IMF (LTR:1282).
  Index from Chainlink, Stork, Pyth (LTR:1305).
- **Liquidation process (LTR:881-913):**
  1. Pre-liquidation: AV below IMR, above MMR; only risk-reducing actions (LTR:886-887).
  2. Partial: orders cancelled, then positions closed by IoC limit orders at a "zero price" for the full position; stop
     once the account is above MMR (LTR:890). "If the user gets filled at a better price than the zero price, the
     liquidation engine takes up to 1% liquidation fee and sends it to LLP (insurance fund)" (LTR:890, text cut at
     line end; the 1% cap is quoted).
  3. Full: below CMR, "the LLP closes all of the user's positions by taking them over in ascending order of unrealized
     PnL" (LTR:910).
  4. ADL: only when the bankrupt account is negative and the LLP cannot cover; ranks by leverage and unrealised PnL
     (LTR:911-913). "ADL does not decrease the health of any account" (LTR:913).
  - Prelaunch: fee 1% and IoC; ADL directly below CMR (LTR:633-639).
- **Earner:** LLP (Lighter Liquidity Pool) is the counterparty and insurance fund (LTR:856; LTR:922-924).
- **Retail deposit into the earner:** restricted. "The LLP is now exclusively accessible to LIT stakers. For every 1 LIT
  staked, participants may deposit up to 10 USDC" (LTR:94-96). 5-minute withdrawal cooldown (LTR:601).
- **Reachable from France/EEA:** not excluded per repo note (terms dated 29 Dec 2025 restrict US, CA, UK, CN, KP, RU, UA,
  CU, IR, VE, SD, BY, MM, SY; France and EU not named) (`venue_access_fr_20261110.md:37`). Not verified on the primary
  terms page.
- **Date read:** LTR local copy 2026-11-25 00:29.

### 1.4 Paradex (StarkNet appchain; Paraclear; cross and portfolio margin)
- **Margin modes:** cross margin; portfolio margin exists as a separate mode (portfolio-margin page fetched but not read
  in full, 23 KB; [inf] same MMR approach applied at portfolio level). Source: https://docs.paradex.trade/risk/cross-margin-requirement.md
- **Maintenance margin:** "MMF Factor is currently set to 50% for all perpetual futures. This means that Net MMR is half
  of the Net IMR" (cross-margin-requirement.md; section "Maintenance Margin Requirement"). MMR also includes "Fee
  Provision = Taker Fee × Position Value". Example MMF = 1% (liquidations.md example).
- **Mark rule:** `Mark Price = Spot Oracle Price × (1 + Fair Basis)`; spot oracle from Pyth and Stork. Fair Basis blends
  the external median (Binance, Bybit, OKX, Hyperliquid, Lighter basis) with an internal liquid basis, weighted by an
  on-venue liquidity score w that ramps over 30 minutes (mark-price-calculation.md).
- **Liquidation process (liquidations.md):** triggered when Margin Ratio > 100% at the periodic Health Check. Partial:
  "All positions are reduced by the same fraction called Liquidation Share", a multiple of 20%, chosen so the margin
  ratio falls below 90%. Penalty = Liquidation Share × Liquidation Fee × MMR, with Liquidation Fee = 70%. "The liquidated
  positions as well as the liquidation penalty are transferred over to the Insurance Fund." Full liquidation if the
  remaining collateral cannot pay the penalty.
- **Insurance Fund:** "closes the acquired positions in the market, incurring any losses from adverse price movements"
  (liquidations.md). "When Paradex Insurance Fund is bankrupt... Socialized Losses will occur as a last level"
  (liquidations.md). Balance public at https://api.prod.paradex.trade/v1/insurance.
- **ADL:** Paradex's deleveraging page is about order cancellation, not position ADL. "If Account Value < Account IMR,
  Account Deleveraging kicks in... orders that do not offset an open position... are canceled" (deleveraging.md). No
  position-ADL rule found in the fetched pages.
- **Retail deposit into the earner:** not stated. [inf] the Insurance Fund is not a user vault.
- **Reachable from France/EEA:** unknown. Not found in the local or fetched pages.
- **Date read:** Paradex pages fetched 2026-11-25 (4 of 5 risk pages, portfolio margin not read in full).

### 1.5 Velocity (formerly Drift, Solana; cross-margin per subaccount)
- **Local copy note:** `docs.drift.trade.txt` is the Velocity Protocol docs ("docs.velocity.exchange"), 99 pages. Caveat:
  the Drift name is historical; the rules quoted are Velocity's current text.
- **Margin modes:** cross within one subaccount only; "Each subaccount is its own margin silo" (VD docs.drift.trade.txt:1037).
- **Maintenance margin:** `Maintenance Margin Requirement = Σ(position notional × maintenance margin ratio)`; liquidation
  when `Maintenance Health Ratio < 1.0` (VD:998-1015).
- **Mark / liquidation price:** liquidators close perp positions "at the oracle price" (VD table line 1063). Maintenance
  check uses the oracle. Mark TWAP is a separate input to funding (VD:805).
- **Liquidation process:** "Partial by design: the liquidator takes liquidatorFee, with separate ifLiquidationFee..."
  (VD:1063); reduce until above maintenance (VD:1063). Liquidation fills skip the post-fill margin check (VD:1030).
- **Bankruptcy waterfall (VD liquidation-and-bankruptcy page, lines 13336-13375):**
  - Step 0: estate pays first (recover perp claims, setoff quote deposit, forfeit unfundable claims).
  - Tranche 1: market's in-transit insurance fee (perp).
  - Tranche 2: shared Insurance Fund vault. "A Speculative, Highly Speculative or Isolated market draws nothing from the
    Insurance Fund, ever" (VD:12551); shared fund "covers the rest, but only up to... $1,000,000 across the market's whole
    life" (VD:12563).
  - Tranche 3: AMM fee-provision clawback (capped at cumulative provision).
  - Socialized: "through a bump to both cumulative funding rates, so longs and shorts both pay" (VD:13375 region).
- **Earner:** the Insurance Fund is "100% staker-owned... no protocol-owned share" (VD:459; VD:12508-12512).
- **Retail deposit into the earner:** yes, stake the IF per market. "Staking supplies first-loss capital... in exchange a
  staker receives that market's share of the protocol's fee revenue" (VD:12579). Stake page exists at
  docs.velocity.exchange/protocol/insurance-fund/insurance-fund-staking (linked, not read).
- **ADL:** not found as a position-ADL mechanism in the local text. Socialization through funding is the stated last tranche.
- **Reachable from France/EEA:** unknown. Not read.
- **Date read:** VD docs.drift.trade.txt local copy 2026-11-25 08:25.

### 1.6 Extended (StarkEx; cross margin with a vault asset)
- **Margin modes:** unified margin; up to 10 trading accounts per wallet, each with independent margin (VD
  docs.extended.exchange.txt:168).
- **Maintenance margin:** `Maintenance Margin Requirement (per position) = Abs(Position Size × Mark Price) ×
  Maintenance Margin Rate`; Margin Ratio = Σ MMR / Equity (VD:403-407). Margin calls at Margin Ratio 66% and 80%
  (VD:410-413).
- **Mark rule:** "Liquidations are triggered using independent external oracle mark prices" (VD:61). Liquidation is at
  the position's "Bankruptcy Price" (VD:425).
- **Liquidation process (VD:417-440):**
  1. Liquidate the vault asset "XVS" in up to 5 steps of 20%, min $1,000 (the asset name "XVS" is not defined in the
     local copy; flagged).
  2. Perpetual positions: largest unrealised loss first; order-book markets FOK in 20% steps at Bankruptcy Price, then one
     full FOK at 5% worse. RFQ markets: 1-second steps at Bankruptcy Price ± margin requirement.
  3. Spot assets.
  4. Deleverage (ADL) if equity < 0 and the position "cannot be liquidated through the order book at an acceptable price".
- **Earner:** not stated in the local copy beyond "Liquidate XVS"; the XVS vault page is linked
  (`extended.exchange/extended-resources/vault`), not read.
- **Retail deposit into the earner:** unknown.
- **Reachable from France/EEA:** unknown. The page refers to "Restricted Countries" and "Eligibility and jurisdictional
  restrictions apply" (VD:397-399). List not in the local copy.
- **Date read:** VD docs.extended.exchange.txt local copy 2026-11-25 08:25.

### 1.7 edgeX (v2; Stork and multi-CEX oracle)
- **Margin modes:** cross margin and isolated; up to 20 trading accounts per wallet (VD edgex-1.gitbook.io.txt:582).
- **Maintenance margin:** "In cross margin mode, a position is liquidated when the available balance reaches zero and the
  position margin drops to the maintenance margin level" (VD edgex:731). Maintenance rate not read.
- **Mark rule / liquidation price:** "edgeX employs Oracle Price to prevent liquidations triggered by low liquidity or
  market manipulation" (VD:731). Oracle is "a proprietary, natively aggregated Multi-CEX Oracle framework... establishes
  exact liquidation" (VD:291); earlier version: Stork (VD:145).
- **Liquidation process:** as above (VD:729-731); no step-by-step partial rule read.
- **ADL (VD edgex ADL Rules):** "Auto-Deleveraging (ADL)... When a position goes bankrupt... the system auto-deleverage
  eligible profitable Counterparty Positions." Ranking: "The protocol uses the Unrealized Profit of Counterparty Positions
  as the primary ADL ranking metric. The higher the Unrealized Profit, the higher the ADL ranking" (VD edgex ADL Rules).
  Tie-break by ROI or leverage.
- **Earner:** the eStrategy vault: "APR comes from AMM income, liquidation fees" (VD edgex:345). Vault deposits open to
  users (VD edgex:329-337).
- **Retail deposit into the earner:** yes, as a vault depositor (VD edgex:329-345; eStrategy). Withdrawal rule: "if the
  initial margin is insufficient, a proportional amount of all open positions is closed" (VD edgex:337).
- **Reachable from France/EEA:** unknown. Not read.
- **Date read:** VD edgex-1.gitbook.io.txt local copy 2026-11-25 08:25.

### 1.8 Variational (Omni; peer-to-peer, OLP as counterparty)
- **Margin modes:** cross and isolated on certain markets (margin page, fetched 2026-11-25). "Cross margin mode...
  Upon crossing the 100% maintenance margin threshold, liquidations may occur on any position in cross margin mode" (margin
  page). Platform-wide margin requirements on all pools.
- **Maintenance margin:** "As a general rule, the maintenance margin requirement is half that of the initial margin
  requirement" (margin page). Trigger "maintenance margin >= 100%" (liquidation page).
- **Mark rule:** "Maintenance margin is calculated by marking to market all positions using a very fast EMA of the mark
  price" (liquidation page, fetched 2026-11-25).
- **Liquidation process (liquidation page):** partial; "partial liquidations reduce maintenance margin by 1.5 × MM −
  balance... bring the account to 50% maintenance margin". Liquidation price = quote + penalty: "ask + 0.5% (for a
  short) or bid − 0.5% (for a long)". Auto-liquidation is on for all settlement pools: "positions will start to be forcefully
  closed if the pool balance falls below the maintenance margin requirements" (liquidation page).
- **Earner:** the OLP (Omni Liquidity Provider) is the only maker, and is itself subject to margin and liquidation (OLP page).
  "Initially, the Variational team has provided seed capital for OLP. Once the system's stability is proven... we intend to
  open it up to user deposits via a community vault" (OLP page, fetched 2026-11-25).
- **ADL:** "OLP being liquidated is the functional equivalent of... Automatic Deleveraging (ADL)... When positions are
  auto deleveraged, the user's position is closed at the settlement price plus a liquidation reward. The user gains the
  liquidation penalty, as OLP is liquidated" (ADL page, fetched 2026-11-25).
- **Retail deposit into the earner:** not yet. The OLP is seed-capital only; the community vault is announced for later.
- **Reachable from France/EEA:** unknown. The competition excludes "persons resident or located in the United Kingdom, the
  European Economic Area" (`docs.variational.io.txt`, campaign terms). That is the trading competition only, not the
  platform terms; the restricted-jurisdictions page was not fetched.
- **Date read:** Variational pages fetched 2026-11-25.

### 1.9 Aster (Aster Pro orderbook perps; separate Aster V1/DEX section)
- **Margin modes:** cross and isolated; risk tiers "larger positions require higher margin and offer lower leverage"
  (VD docs.asterdex.com.txt:2821-2826).
- **Maintenance margin:** not read (tier table not in the local copy).
- **Mark rule (Pro):** "Mark price: calculated based on a combination of funding data and a basket of prices from multiple
  spot exchanges... used to determine unrealized PnL and trigger liquidations" (asterdex:2824). Last-trade protection: "If
  the latest trade price deviates more than 5% from the mark price and no new trade occurs within 5 seconds, the contract
  price is replaced with the current mark price" (asterdex:2812).
- **Mark rule (V1 section, on-chain):** "For liquidation, the system uses the median oracle price weighted by validator
  stake" (VD asterdex:1740). Two different rules in one doc; the mechanism for each product is not reconciled here.
- **Liquidation process:** "Liquidation risk is limited to that specific position" (asterdex:1772). Pro liquidations
  page only partially read.
- **Earner:** not found. The vault that holds positions is "Vault... the 100ASTER is permanently burned" (asterdex:1139)
  (a separate product; not the perp liquidation pool).
- **ADL:** ADL warning tooltip and ADL notifications exist (asterdex:2409, 2634). Ranking not found.
- **Retail deposit into the earner:** unknown.
- **Reachable from France/EEA:** unknown for perps. The local copy lists "France (FR)" among restricted countries, but that
  list is attached to **prediction trading** only (asterdex:7225-7227), not to the perps.
- **Date read:** asterdex local copy 2026-11-25 08:25.

### 1.10 dYdX v4 (Cosmos appchain; on-chain order book)
- **Margin modes:** cross margin; subaccounts.
- **Maintenance margin:** "maintenance margin fraction (MMF)" (dydx local copy, example at line 4960).
- **Mark / liquidation price:** "historical oracle prices (spot prices used to compute funding and process liquidations)"
  (dydx:1298).
- **Liquidation process:** liquidation orders at "liquidation order prices (up to a max spread from the oracle)" (dydx:4956).
- **Insurance Fund:** "covers insufficient collateral by adjusting liquidation order prices (up to a max spread from the
  oracle) to improve their chances of filling" (dydx:4956).
- **ADL (dYdX local text, older):** "If an account's value turns negative, deleveraging occurs immediately against randomly
  chosen offsetting positions, which may reduce the expected profits of offsetting accounts" (dydx:4941). **Possibly
  stale**; the current ADL ranking was not checked.
- **Earner:** the insurance fund (not stated who holds claims).
- **Retail deposit into the earner:** unknown.
- **Reachable from France/EEA:** unknown. The repo note says "dYdX's terms were not checked" (`venue_access_fr_20261110.md:58`).
- **Date read:** dydx local copy 2026-11-25 08:25.

### 1.11 Kraken (Kraken Derivatives, global and EEA schedules)
- **Margin modes:** Multi-M (cross) and isolated; "Would a liquidation of my cross-margined position(s) affect my isolated
  margin position(s)... If your PnL... causes your liquidation threshold to be met but... your isolated-margined position(s)
  will not be directly affected" (Kraken FAQ, fetched 2026-11-25: support.kraken.com/be/articles/4402283092244).
- **Maintenance margin (EEA retail, repo note):** Class E, Level I (positions $0-250,000): 10x, initial 10%, **maintenance 5%**;
  Level II 5x (20%/10%); Level III 3.33x (30%/15%); Level IV 2x (50%/25%) (`answers_20261124.md` §1, from Kraken support
  "Derivatives margin schedule & maximum leverage for EEA clients", read 2026-11-24). The API retail schedule (50%/25%) is
  another entity's (same note).
- **Mark rule:** "A liquidation is triggered when the portfolio value of a derivatives margin wallet falls below the
  maintenance margin required... The estimated liquidation price... represents the mark price that, when reached..."
  (Kraken FAQ). The premium/discount cap "1%" is from a search summary (secondary; `mechanism_map.md` row "Mark price"
  states the same from Kraken docs). 
- **Liquidation process:** "When Multi-M Margin Account Equity falls below maintenance margin but above the liquidation
  margin threshold, a Partial Liquidation will be initiated" (Kraken FAQ). "Kraken Derivatives does not offer margin calls
  or any warnings" (Kraken FAQ). Fees by full vs partial (Kraken FAQ; fee schedule not read).
- **Insurance fund / backstop:** not found in the Kraken FAQ fetched. The search summary cites an old MTF page with a
  "liquidity provider assignment" backstop (secondary; dated; not read in full).
- **ADL:** not found in the FAQ read.
- **Earner:** not identified.
- **Retail deposit into the earner:** not applicable (no earner found).
- **Reachable from France/EEA:** yes for an EEA client schedule exists (the EEA page exists in the repo note; `answers_20261124.md`
  §1). The Kraken EEA contract list covers the coins held (updated 2026-06-29, per the same note).
- **Date read:** Kraken FAQ 2026-11-25; EEA schedule 2026-11-24 (repo note).

### 1.12 Deribit (options and perpetuals; LSP and ADL)
- **Margin modes:** Standard Margin and Portfolio Margin accounts (`docs.deribit.com/articles/lsp-api-guide.md`, fetched
  2026-11-25).
- **Maintenance margin:** not read (support page blocked; see below).
- **Mark rule (secondhand, search summary of Deribit blog):** "index price plus a 30-second EMA of (perpetual fair price −
  index price)"; "a limit on how fast the mark price can move" (insights.deribit.com; not fetched). Liquidation reference is
  the mark (Deribit blog, search summary).
- **Liquidation process and LSP (LSP guide, fetched 2026-11-25):** "Deribit's Liquidity Support Program (LSP) transfers
  liquidated positions to designated participant accounts before falling back to auto-deleveraging (ADL)." Order: (1) LSP
  transfer at "a small spread to the reference price"; (2) ADL "against a counterparty instead"; (3) standard
  order-book liquidation (LSP guide, section "What Happens When Your Position Is Liquidated"). A "commission" is charged on
  the liquidated account.
- **Earner:** LSP participants (designated accounts, "Participation is arranged directly with Deribit; there is no public API
  to self-enroll") (LSP guide).
- **ADL:** "ADL only applies to perpetuals that do not have an option series listed in the same currency pair." Transfer
  price = reference adjusted by a small spread against the liquidated position (LSP guide).
- **Insurance fund:** search summary (help center, secondary): liquidation fees "go into this fund"; blog says it covers
  negative equity after failed liquidations. Help center **403** (blocked; not bypassed).
- **Retail deposit into the earner:** no public route (LSP participants arranged by Deribit).
- **Reachable from France/EEA:** unknown. Support page blocked (403).
- **Date read:** LSP guide fetched 2026-11-25; help center blocked.

### 1.13 Bybit (USDT and USDC perps)
- **Margin modes:** cross and isolated (secondary; not read).
- **Mark rule:** "liquidation is triggered when the Mark Price hits the Liquidation Price" (search summary, Bybit help center).
  Insurance fund page example: "When the mark price hits 65,000 USDT, the position will be liquidated and settled at 64,000
  USDT, regardless of the current market price" (Bybit Insurance Fund page, fetched 2026-11-25).
- **Liquidation process:** "When a position is liquidated, it will always be settled at the bankruptcy price... The balance
  of the insurance fund will increase or decrease depending on the difference between the final executed price and the
  bankruptcy price" (Bybit Insurance Fund page).
- **Insurance fund:** "a reserve pool maintained by Bybit, funded by Bybit contributions and excess margin from liquidated
  positions closed at prices better than the bankruptcy price" (Bybit ADL page, fetched 2026-11-25). "Some trading pairs
  have shared insurance fund pools, while others have isolated pools" (Bybit ADL page).
- **ADL trigger (Bybit ADL page, fetched):** "ADL will be triggered when the drawdown of a single trading pair over the past 8
  hours reaches or exceeds the 8H PnL Drawdown Trigger Line of the insurance fund's highest balance during that period."
  Worked example: highest balance 20,000 USDC, trigger 30%, stop 25%; ADL stops when the drawdown is at or below 25%.
- **ADL ranking (Bybit ADL page, fetched):** "The ADL ranking is based on the leveraged return. Accounts with higher
  leveraged returns are ranked higher." "Opposing positions that are at a loss may still be selected, but those in profit are
  given priority."
- **Earner:** the insurance fund (Bybit-funded).
- **Retail deposit into the earner:** no (Bybit-funded; no public deposit route found).
- **Reachable from France/EEA:** unknown (not read).
- **Date read:** Bybit ADL and Insurance Fund pages fetched 2026-11-25.

### 1.14 OKX (perpetual, portfolio margin)
- **Margin modes:** cross, isolated, and portfolio margin (search summary; OKX help center redirect not followed).
- **Maintenance margin (portfolio):** "under portfolio margin, the maintenance margin is not calculated based on the maintenance
  margin requirement, but is determined based on the loss value under extreme stress test scenarios" (search summary of OKX
  "Tiered maintenance margin ratio rules"; secondary).
- **Mark rule:** not read.
- **Liquidation process:** "OKX generally takes over the account and uses the security fund to liquidate the position with the
  highest margin, and... has the full discretion to determine when to use security funds" (search summary; secondary).
- **Security Fund:** "OKX calls it a 'Security Fund'... not an insurance policy, a custodial protection fund, or a guarantee"
  (search summary; secondary). Owner: OKX.
- **ADL:** "the last resort to protect these OKX security funds by deleveraging opposing profitable or highly leveraged positions"
  (search summary, OKX ADL page; secondary; the page redirect was not followed).
- **Retail deposit into the earner:** no.
- **Reachable from France/EEA:** yes for OKX Europe X-Perps (repo note: "OKX's own X-Perps guide says they are open to all 30 EEA
  countries, so France is included", `venue_access_fr_20261110.md:64`). Availability "may vary"; OKX Europe terms not read (404).
- **Date read:** search summaries 2026-11-25; primary page not read (redirect not followed).

### 1.15 Binance (USD-M futures)
- **Margin modes:** not read (FAQ blocked).
- **Mark rule (search summary of Binance FAQ):** "Liquidation is triggered once the mark price reaches a position's
  liquidation price." Fast markets can fill worse than the calculated level (example in the FAQ: 17,000 mark, 17,006 liq,
  fill at 17,100) (search summary; FAQ blocked).
- **Insurance fund (search summary, Binance intro FAQ):** "Its only purpose is to cover any difference between the bankruptcy
  price and the execution price of the liquidation order" (secondary).
- **ADL:** "the final step in the liquidation process and occurs only if the Futures Insurance Funds are unable to accept a
  bankrupt futures position" (search summary, secondary).
- **Retail deposit into the earner:** no.
- **Reachable from France/EEA:** no for Binance, per repo note: "Stopped serving France on 1 Jul 2026... Binance had no MiCA
  licence" (`venue_access_fr_20261110.md:35`, secondary press report).
- **Date read:** Binance FAQ returned an access challenge (202) and is **blocked**; the summary is from search.

### 1.16 Bitfinex (derivatives)
- **Status:** **not read.** The search returned no Bitfinex derivatives margin or ADL page. The repo note has only funding
  dead-zone data (`mechanism_map.md:10`). Blocked by absence of a primary source. Next step: fetch the Bitfinex derivatives
  documentation page directly.

---

## 2. Disagreements and transfers

Each item states who pays, the barrier, and the cheapest observation that sizes it. Quotes are from section 1.

### T1. Backstop vault paid by liquidations, open to retail (Hyperliquid HLP)
- **Who pays:** cross-margin traders whose account reaches 2/3 of maintenance without a book exit. "During backstop
  liquidation, the maintenance margin is not returned to the user" (HL:1654). The liquidator earns the margin buffer.
- **Who earns:** HLP, which is open to public deposit (HL:394-396). "On most venues, this profit goes to the exchange operator
  or privileged market makers... On Hyperliquid, the pnl stream from liquidations go entirely to the community through HLP"
  (HL:1672).
- **Barrier:** HLP lock-up 4 days (HL:478); the vault's risk is the other side of the liquidations. The vault also
  market-makes and takes the other side of the book (HL:394).
- **Cheapest observation:** HLP vault equity and PnL history by month, split by liquidation-tagged fills, from the public
  info API. Repo already reads HLP APR +10.30%/yr in 2025-2026 (`venue_access_fr_20261110.md:113`), so the split is the
  missing piece [inf].

### T2. LLP takes liquidation fees and bankruptcies; retail deposit gated by LIT stake (Lighter)
- **Who pays:** liquidated accounts pay "up to 1% liquidation fee... to LLP" (LTR:890), and take the zero-price fills.
- **Who earns:** LLP, the sole liquidity provider for RWAs and the counterparty for liquidation (LTR:922-924).
- **Barrier:** "LLP is now exclusively accessible to LIT stakers. For every 1 LIT staked... up to 10 USDC" (LTR:94-96).
  [inf] the effective cap is tiny for a retail allocation; the staked-LIT gate is the binding constraint.
- **Cheapest observation:** `orderBookDetails` liquidation_fee and the LLP account's fills in the liquidation tag (public API);
  the repo's R446 used LLP APR (+69.26%/yr 2025-2026 per `venue_access_fr_20261110.md:114`). The 2025 figure is
  dominated by a few events [inf]; split it by liquidation-tagged PnL before trusting it.

### T3. Mark rules that diverge from other venues; the earlier liquidation pays
- **Mechanism:** each venue has its own mark (HL median of CEX and book; Paradex spot × (1 + fair basis); Lighter median of
  impact, index EMA, and CEX; Variational fast EMA; Drift liquidates at oracle; Extended uses "independent external oracle
  mark prices"; edgeX uses oracle; Aster Pro uses a spot basket). The liquidation is at that venue's mark.
- **Who pays:** the over-levered long (or short) on the venue whose mark moves first or further. Repo `mechanism_map.md:13`:
  on 2025-10-10, "Kraken's mark low averaged −43.8% over 126 coins (Binance prints −65% to −69%)". The gap in marks is the
  transfer [inf]: a long on the venue with the shallower mark dip survives where the same long on Binance is liquidated.
- **Barrier:** holding accounts on more than one venue. The cross-venue account is the only way to avoid the trigger
  (repo: `stake_dhl_20261123.md`, the two-venue lane).
- **Cheapest observation:** per-venue mark series (1-min), taken from the public mark-price kline endpoints already in
  `scratchpad/cmp_*` files (e.g., `cmp_hyperliquid.txt`, `cmp_kraken_hist.txt`), compared on the 2025-10-10 window: the
  minimum mark on each venue vs the Binance minimum. A venue whose mark dips less than Binance's is the one the long
  account is safe on.

### T4. ADL hits profitable traders by different ranking rules
- **Rules:** Hyperliquid ranks by `(mark/entry) × (notional/account value)` (HL:1703); Bybit ranks by leveraged return, profit
  first (Bybit ADL page); edgeX ranks by unrealized profit, then ROI or leverage (edgeX ADL Rules); Deribit runs LSP first,
  then ADL (LSP guide); Variational ADL is the OLP being liquidated, with the user receiving the penalty (ADL page); dYdX
  older text "randomly chosen" (dydx:4941).
- **Who pays:** the profitable, most levered side of the same contract when a bankrupt position appears. Hyperliquid states
  "backstopped positions have no special treatment in the ADL queue" (HL:1703).
- **Barrier:** holding a position in the contract. The loss arrives at the bankrupt price, not the market price (Bybit ADL
  page: "settle affected positions at the bankruptcy price").
- **Cheapest observation:** count ADL events per venue per year. Bybit exposes the insurance-fund balance and its history
  through its API (Bybit ADL page, "You can also access Bybit's insurance pool data through the API"). Hyperliquid
  settlement records are onchain (XYZ ADL page). For a sizing number, multiply ADL frequency by the position share of
  profitable, high-return accounts.

### T5. Insurance fund that retail can stake (Velocity/Drift) vs funds that are not open to retail
- **Who pays:** stakers absorb bad debt before socialization. Velocity: "There is exactly one tranche between a perp bad debt
  and the shared vault" (VD:13386 region) and the shared vault is capped at $1M lifetime per tier B (VD:12563).
- **Who earns:** stakers, through "that market's share of the protocol's fee revenue" (VD:12579).
- **Barrier:** staker is first-loss on bad debt in that market; the cap limits both losses and fees. Paradex's Insurance Fund
  is not a retail vault (no deposit route described; paradex liquidations.md).
- **Cheapest observation:** Velocity insurance-fund balance time series and bankruptcy draws; Paradex insurance balance via
  `api.prod.paradex.trade/v1/insurance`. Then compare fee revenue to draws over 2025-2026.

### T6. OLP as counterparty: the market maker is also the liquidated side
- **Who pays:** the OLP's capital, when it is liquidated. "The user gains the liquidation penalty, as OLP is liquidated and
  therefore penalized" (Variational ADL page).
- **Barrier:** OLP is seed-capital only; the community vault is announced, not open (OLP page). Retail cannot yet take the
  OLP side.
- **Cheapest observation:** when the community vault opens, its drawdown in ADL events. Until then, the OLP's own
  liquidation events are not public in the local docs.

### T7. Maintenance schedules differ by client entity (Kraken)
- **Mechanism:** Kraken EEA Class E retail is 5% maintenance at 10x (answers note §1); the API retail schedule is 25%
  maintenance at 2x (`stake_dhl_20261123.md:78`). The same coin on the same venue has a 5x difference in the buffer by entity.
- **Who pays:** the EEA client holding high leverage relies on the 5% schedule. The buffer is the difference between the
  two (see the Kraken lane in `stake_dhl_20261123.md`, 1.5x at 5% maintenance).
- **Barrier:** the EEA contract list, and the Level I position cap (positions over $250,000 step up to Level II).
- **Cheapest observation:** Kraken's maintenance rate per level, from the EEA schedule page, and an account-level check of
  the margin ratio on the EEA side before the next move.

---

## 3. Open items (what was not read, and why)

- Hyperliquid primary terms: blocked (403; repo note). France status unknown.
- Deribit help center: blocked (403). Mark, maintenance and insurance rules are from the LSP guide and a search summary.
- Binance FAQ: blocked (202 challenge). Summary from search only.
- OKX help center: redirect not followed. Summary from search only.
- Bitfinex: no primary source found by search; not read.
- Paradex portfolio margin page: 23 KB, not read in full.
- Velocity insurance-fund-staking page: linked, not read.
- Extended XVS vault page: linked, not read. The term "XVS" in the Extended liquidation steps is not defined in the local copy.
- Aster V1 vs Pro liquidation rules: two different mark and liquidation rules appear in the same doc; not reconciled.
- All geographic access: only Binance (secondary press), Lighter (terms dated 29 Dec 2025, France not named), OKX Europe (guide)
  and Kraken EEA (repo note) have a France/EEA reading. Others unknown.

Weakest link: the mark-divergence observation (T3) rests on a repo note's 2025-10-10 figures; the per-venue mark series
have not been compared in this column.
