# Stablecoin plumbing scout (room 20261126b)

Scout: Haiku, 2026-11-26. Family: stablecoin plumbing. Nothing traded, no accounts, no wallets.

## 0. What the lab already has (read first)

- `registry/methods.csv:193` M192, "Stablecoin supply weekly z-score -> market", BLOCKED: "Griffin-Shams vs the VoxEU rebuttal. Low prior."
- `registry/methods.csv:74` M073: "Galaxy's 10/10 post-mortem: USDe about 0.65 on Binance 21:42-21:51 UTC ... Binance's redemption-based pricing was not in place in time." Verdict in the row: no registry row, OLD U4 trap, fewer than 10 episodes.
- `registry/rounds.csv:247` R460 (M512), USDT mints as a BTC signal: "DONE NULL"; "D1 24h n 201: mean +23.1 bp vs placebo +6.2, Holm p 0.40"; net at 1x/2x/3x "+6.6/-3.4/-13.4". MDE80 65 bp, so underpowered.
- `registry/rounds.csv:275` R488 (M535), USDe supply change vs next-week Hyperliquid funding: "DONE NULL". Gates were rho > 0 with p < 0.05 on BTC and ETH.
- `registry/rounds.csv:270` R483 (M478/M481): sUSDe and Aave USDC as the carry hurdle, verdict "CONFIRMED". Used as a benchmark only.
- `registry/methods.csv:388` M481: "Ethena docs say sUSDe is not offered to EU/EEA residents (verified by re-fetch), so for the owner it is a benchmark, not an alternative."
- `docs/reviews/venue_access_fr_20261110.md:35` (Binance row): "Stopped serving France on 1 Jul 2026." Reports only; the row says the ESMA register was not checked.

Lab reading: the USDe supply-flow channel (R488) and USDT mint channel (R460) are already NULL. Anything new here has to be a rule with a forced clock, not a flow.

## 1. Primary sources read (exact quotes)

- Binance support, EEA non-MiCA stablecoin delisting, https://www.binance.com/en/support/articles/bcaa1f68d6a6450099056ff694ad6c46: "From 2025-03-31 23:59 (UTC) onwards" spot pairs "will be fully delisted, you will no longer be able to trade these pairs." Margin: "any non-MiCA compliant Margin trading pairs will be fully delisted for EEA users" from "2025-03-27 07:00 (UTC)". Holdings: "convert any remaining non-MiCA compliant stablecoin holdings (e.g. USDT) to USDC, EURI, or EUR." Withdrawals: "you will be able to withdraw or deposit non-MiCA Compliant Stablecoins at any time."
- Kraken support, https://support.kraken.com/hc/en-us/articles/stablecoin-offerings-for-eea-clients (fetched 2026-11-26; page says "Last updated: October 29, 2026"): "The following stablecoins are now delisted in the EEA:" then lists Tether (USDT), Tether EURt (EURT), PayPal USD (PYUSD), TrueUSD, DAI, USDS and others. "The above assets cannot be traded in the regions outlined below, and can only be deposited or withdrawn from Kraken." Holdings conversion date and target asset: not stated on the page.
- MiCA Article 49, ESMA Single Rulebook, https://www.esma.europa.eu/publications-and-data/interactive-single-rulebook/mica/article-49-issuance-and-redeemability-e: "shall redeem it, at any time and at par value"; "Without prejudice to Article 46, the redemption of e-money tokens shall not be subject to a fee." Article 46 text not read.
- Ethena docs, funding risk, https://docs.ethena.fi/protocol-overview/risks/funding-risk: "In periods of low or negative funding, more of the backing assets of USDe will be shifted into liquid stables"; "An Ethena reserve fund exists and will step in on occasions when the combined revenue". The redemption process itself is not on the official page I could reach. Secondary sites describe it (burn, unwind short, return collateral); treat that as unverified.
- Hyperliquid USDH, The Block, https://theblock.co/post/401233/coinbase-hyperliquid-official-deployer-usdc (fetched): "USDH will sunset over time as USDC expands its role within the Hyperliquid ecosystem."; "users will continue to be able to redeem USDH for USDC or fiat without fees"; Native Markets will "ensure the migration to USDC is complete before USDH is sunsetted." No sunset date in the article.
- Kraken EEA USDT delisting in 2025: Kraken's 2025 announcement, reported by Cointelegraph and DL News (search snippets only, not fetched). Binance and Kraken both cited MiCA.
- ESMA statements on the end of transitional periods (2026-04 and 2026-06 PDFs): the PDFs were compressed and not readable here. The 1 July 2026 date rests on search snippets and on the lab's venue note. Flagged as not verified from primary text.

## 2. Measurements run (one call each, public endpoints)

- Kraken public ticker, `https://api.kraken.com/0/public/Ticker?pair=USDTEUR`: ask 0.9105, bid 0.9104, 24h volume 1,863,407 (base units shown as USDT). Same call for `USDCEUR`: ask 0.9117, bid 0.9116, 24h volume 1,640,585. `EURCEUR`: bid 1.0000, ask 1.0001. One snapshot, no timestamp in the response. Mid gap USDT/EUR vs USDC/EUR about -11 bp at this instant. No depth beyond top of book, no fees, no fills.
- Binance public API `api/v3/ticker/price`: returned "Service unavailable from a restricted location". Not bypassed. Binance cannot be used from this container and no Binance number is reported.
- Hyperliquid `spotMetaAndAssetCtxs` (public info endpoint): the USDH/USDC row shows dayNtlVlm 0.0, markPx 0.0128, midPx 0.0564. That is not a $1 stablecoin price. The same mapping also gives USDT0/USDC markPx 0.0824, which is also implausible. So the index-to-name mapping in my quick script is unverified and no USDH price is reported. Fix before any use.

## 3. Candidate questions

### Q1. EEA forced sale of USDT: a predictable USDT/EUR discount on venues still open to the seller?

- **Hypothesis:** EEA holders who had to leave USDT by the 2025 and 2026 deadlines sold into USDT/EUR, so USDT/EUR trades below USDC/EUR on venues that still list both, and the gap is largest near each deadline.
- **Opposite:** Holders migrated early and arbitrageurs with non-EEA accounts (Kraken global, others) closed the gap within a day, so no gap remains after the deadlines.
- **Payer and rule:** EEA clients. Rule: Binance "From 2025-03-31 23:59 (UTC) onwards ... fully delisted"; Kraken "can only be deposited or withdrawn from Kraken." The forcing clock is the delisting date, not a flow.
- **Why not known in the lab:** no registry row covers stablecoin pairs (grep of methods.csv and rounds.csv, rows above). R460 and R488 test flows, not the delisting clock.
- **Data held or API:** Kraken public ticker, tested above (USDTEUR, USDCEUR). Need a time series; not held.
- **Cheapest decisive observation:** poll the Kraken global ticker and order book (USDTEUR, USDCEUR) every 5 minutes for 7 days, record top of book and depth at 0.1% from mid, around 2026-12-01 (no deadline known then). Cost: 0 euros. Hours: about 1 hour a day of polling. Decisive if the gap, after top-of-book fees, exceeds 2x round trip with depth for 1000 EUR.
- **Kill result:** gap under 5 bp at 1000 EUR depth, or gap closes in under 1 hour after each observation.
- **Value for a French retail owner with about 10k EUR:** low. The seller pool is EEA; the French client cannot trade USDT/EUR on an EEA venue (Kraken list above; Binance stopped serving France, `docs/reviews/venue_access_fr_20261110.md:35`). A non-EEA account would be the owner's decision and needs a legal read first. A wallet is needed for any DEX route; that is the owner's decision.
- **My probability:** 5%. The forcing clock has passed for both venues, and the snapshot gap (about -11 bp) is a single observation with no depth or timestamp.

### Q2. USDe below $1 when funding turns negative: a predictable, capturable gap between secondary price and redemption value?

- **Hypothesis:** When funding goes negative, Ethena must unwind shorts to honor redemptions, so secondary USDe trades below $1 on venues without a redemption-anchored price (the Galaxy event, M073), and a redeemer can close the gap.
- **Opposite:** Whitelisted minters arbitrage in seconds (the official reserve fund and insurance buffer protect the peg), so any depeg is a few basis points and gone before a retail client can act. The redemption path itself is closed to retail.
- **Payer and rule:** Ethena's reserve and redeemers. Rule: "In periods of low or negative funding, more of the backing assets of USDe will be shifted into liquid stables"; "An Ethena reserve fund exists and will step in." The redemption mechanics are only secondary-sourced here, so unverified.
- **Why not known in the lab:** M073 (Galaxy event, `registry/methods.csv:74`) and R488 (`registry/rounds.csv:275`, NULL) cover the event and the supply channel. M481 (`registry/methods.csv:388`) notes sUSDe is not offered to EU/EEA residents. No row prices the redemption gap.
- **Data held or API:** DefiLlama USDe series used by R488 (supply, not price). Secondary DEX prices not tested here. Not held.
- **Cheapest decisive observation:** for the 2026-11-03 window in M073 only, get minute prices for USDe on one public DEX pool and the same window's Binance USDe quote (only if reachable from a permitted location, which it is not here). Cost: 0 euros, about 2 hours. Decisive if the sub-$1 window exceeds 30 bp for more than 10 minutes with depth above 5k USD.
- **Kill result:** depegs below 1% revert within minutes, or the redemption route is closed to the owner (it is, in EU/EEA by M481). Either way, no retail capture.
- **Value for a French retail owner with about 10k EUR:** very low. Minting and redemption need a KYC account and a wallet (the owner's decision). sUSDe is not offered in the EEA.
- **My probability:** 4%. The mechanism is real, but the capturing party is a whitelisted minter, and R488 already shows the flow channel is NULL.

### Q3. USDH sunset: does a fee-free redemption promise pin USDH/USDC to par, or does a holder discount open into the sunset?

- **Hypothesis:** USDH will sunset with no date, and holders who want out before the date sell USDH at a discount on Hyperliquid spot, so the USDH/USDC gap widens until a sunset date is set, then closes as redemption for USDC is fee-free.
- **Opposite:** Redemption is "without fees" to onboarded users, so minters arbitrage any discount to par at once, and the gap stays within a few bp; the only holders left are those who cannot mint.
- **Payer and rule:** USDH holders who must exit. Rule: "USDH will sunset over time as USDC expands its role within the Hyperliquid ecosystem."; "users will continue to be able to redeem USDH for USDC or fiat without fees." Minting is restricted to onboarded market makers and approved users (listing page, secondary: rwa.xyz / OKX snippets, unverified).
- **Why not known in the lab:** no registry row covers USDH. R445 (`registry/rounds.csv:232`) uses Hyperliquid spot-against-perp with USDC, not USDH. No USDH price was ever measured here.
- **Data held or API:** Hyperliquid `spotMetaAndAssetCtxs` returns a USDH/USDC row, but my probe gave a price (0.0128 mark, 0.0564 mid, zero 24h volume) that is not a $1 stablecoin, and the index mapping is unverified. So no price series is held or trusted yet.
- **Cheapest decisive observation:** fix the token-to-pair mapping (check against the Hyperliquid web UI's USDH/USDC market name), then record the USDH/USDC mid and 24h volume daily for 14 days. Cost: 0 euros, about 30 minutes to fix, 5 minutes a day. Decisive if a discount above 20 bp persists for more than 3 days with volume above 10k USD a day.
- **Kill result:** volume stays at zero (no market to trade), or the mark stays within 5 bp of par (redemption pins it). Either kills the trade.
- **Value for a French retail owner with about 10k EUR:** low to moderate, and only if a Hyperliquid account or wallet is used (the owner's decision). A holder must mint or buy USDH, so the discount is a forced exit cost for holders, not a free gain for a retail buyer who cannot redeem.
- **My probability:** 10%. A sunset without a date is a real forced seller, but the redemption promise, the thin market and the missing mint right for retail all point to no tradable gap.

## 4. Unverified and flagged

- The 1 July 2026 ESMA date and the "unlicensed providers wind down" line: from search snippets, PDFs unreadable here.
- Kraken delisting date: Kraken's page is dated 2026-10-29 in the fetch; the search snippet said 2026-04-13. The list of delisted coins came from the fetch.
- Ethena redemption mechanics: secondary sources only.
- USDH sunset date: none found. Hyperliquid probe mapping: unverified (see section 2).
- Binance data: blocked from this container (restricted location). Not bypassed.

## 5. What I would do next (not run)

- Q1 needs a 7-day public ticker and depth recording (cheap, but the payer clock has passed, so probability is low).
- Q3 needs the Hyperliquid token-to-pair mapping fixed before any number is quoted.
- Q2 is a known event (M073); not worth a cycle without a new depeg with minute data.
