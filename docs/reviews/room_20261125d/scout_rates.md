# Scout: rates plumbing in crypto (room 20261125d)

Scope: fixed-rate funding swaps (Pendle Boros), DeFi stablecoin borrow rates (Aave), Ethena's USDe/sUSDe yield, and perp funding on centralized venues. Read-only. Nothing traded, no accounts, no wallets.

## 0. What the lab already has (read, not re-derived)

- M480 (`registry/methods.csv`, line 387): Boros lock measured. "R412: the lock holds (oracle 99.7-99.96% of venue events, median |realized-locked| 0 bp, p95 <= 3.6 bp APR) but locked-T-bill is +2.1 pts (HL) / +0.1 (Binance) on notional and below the T-bill after an indicative spot+perp round trip."
- R413 (`registry/rounds.csv`, line 199) is the forward paper lock, RUNNING, PENDING, 2 trials, first read at 4 settled K0 locks or 2027-10-01.
- M478 (line 385): Aave v3 USDC/USDT borrow rates captured from DefiLlama 2026-11-12; "the free endpoint stopped 2026-11-13". Exchange earn rates "not found". So the DeFi borrow leg is held only up to 2026-11-12.
- M481 (line 386 region): sUSDe as benchmark only; "Ethena docs say sUSDe is not offered to EU/EEA residents (verified by re-fetch)".
- M508 (line 415): Pendle PT markets BLOCKED; 112 of 668 Ethereum factory markets return 404 from the public API.
- M535 (line 442) and R488 (line 275): USDe supply change vs Hyperliquid funding. R488 result NULL (verdict NULL, 2 trials). So the simple "Ethena mints move funding" link is already tested and dead at weekly resolution.
- `docs/reviews/mechanism_map.md` line 10: "Floor venues: P + clamp(0.01% − P, ±0.05%) per 8 h ... Floorless: Kraken (premium only), Deribit (±0.025% dead zone), Bitfinex (±0.05% dead zone)."
- `docs/DATA_SOURCES.md`: no Boros entry matched the grep on "boros" (the data is documented in `docs/provenance/boros_hist.json`, fetched 2026-11-06, 242 markets listed, 115 monthly folders in `data/boros/hist/`).
- Only one PREREG uses Boros data (R412/R413, `experiments/boroslock_v1`, `experiments/boroslock_fwd`). I did not open those journals (hard rule).

## 1. Primary-source facts (quotes verified this session)

Hyperliquid funding (fetched https://hyperliquid.gitbook.io/hyperliquid-docs/trading/funding):
- Formula: "Funding Rate (F) = Average Premium Index (P) + clamp (interest rate - Premium Index (P), -0.0005, 0.0005)"
- Interest term: "For consistency with CEXs, interest rate component is predetermined at 0.01% every 8 hours, which is 0.00125% every hour"
- Settlement: "The funding rate on Hyperliquid is paid every hour."

Boros settlement (docs.pendle.finance, fetched in part via search summary; formula text not verified verbatim, see section 5):
- Fixed APR is "the average implied APR of the filled order" (from search summary of https://docs.pendle.finance/boros-docs/about-boros/funding-rate-settlement; NOT quoted verbatim, the fetch returned empty).
- Underlying rate: "fetches the funding rate from the relevant CEX or perp DEX at each epoch, and it goes to the FIndex Oracle" (search summary of the same page; unverified wording).
- Intervals "match the underlying perp venue" (same summary).

Ethena (fetched https://docs.ethena.fi/protocol-overview/risks/funding-risk):
- Reserve fund: "An Ethena reserve fund exists and will step in on occasions when the combined revenue between LST assets, such as stETH, the funding rate for a short perpetual position, the basis from short dated futures as well as potential rewards from holding liquid stables, is negative."
- Backing shift: "In periods of low or negative funding, more of the backing assets of USDe will be shifted into liquid stables earning approximately the U.S Treasury rate." (paraphrased in the fetch; treat the quote as the fetch's extraction)
- sUSDe: "Ethena does not pass on any negative revenue to users who stake USDe for sUSDe."
- No reserve size in the official page. Third-party 2024 figures (CryptoQuant: covers extreme funding if USDe cap below $4bn; a summary says $3bn) are old and unverified here.

Aave v3 borrow (WebSearch summary of docs.aave.com; direct fetch failed on redirect/404):
- Two-slope piecewise-linear variable borrow rate in utilization U with optimal U_opt, slope 1 below, slope 2 above. Parameters set via PoolConfigurator.setReserveInterestRateData. NOT quoted verbatim; I could not fetch the live page. Treat as assumed.

Boros-side pinning check (ran, see section 2): the lab's floor of 10.95%/yr is `0.0000125 x 8760 = 0.1095` per hour, the same value as Hyperliquid's floor term above.

## 2. Numbers I ran

- Hyperliquid public info API, `metaAndAssetCtxs` (POST https://api.hyperliquid.xyz/info), read this session: BTC funding 0.0000125/h (= 10.95%/yr, exactly the floor), ETH funding 0.0000066351/h (about 5.8%/yr, below floor, so the premium is negative and the clamp is inside the band).
- Boros `data/boros/hist/market-data/10-HYPERLIQUID-BTC-31OCT2025` (716 hourly rows, Oct 2025): midApr min 6.44%, max 12.79%; share of hours within 1 bp of 10.95%: **4.5%**. The first hour sits exactly at 0.10948661861873331.
- Boros `market-data/101-BINANCE-ETHUSDT-25SEP2026` (4,265 rows): midApr min 0.18%, max 7.81%; share within 1 bp of 10.95%: 0%.
- Boros `settlement/10-HYPERLIQUID-BTC-31OCT2025` (716 rows): last settlementApr = 0.1095 on 2025-10-31, i.e. the settlement prints the floor exactly.
- Boros API `POST https://api-boros.pendle.finance/apis/v1/markets` returned HTTP 404 (a GET may work; not tested). The lab's `boros_hist.json` says the list was fetched on 2026-11-06 from that URL.

Reading: the floor is printed exactly in settlements (on HL), but the Boros mid does not pin to it (4.5% of hours). The fixed price is not "the floor"; it is an order-book price that moves with demand. So a naive "Boros is pinned to the clamp" story is refuted on this data.

## 3. Three refined candidate questions

### Q1. Does the HL funding floor make the Boros HL fixed receiver's income a non-market transfer, and is that gap priced?
- Hypothesis: On HL, the hourly settlement equals max-type floor income (10.95%) while P is in band, so a fixed-receive position on HL pools collects a rate the market only partly prices (mid 4.5% of hours near floor).
- Opposite: the order book already prices the floor; mid is a noisy forecast of the settled floor and the apparent gap is just the lock's noise (R412 says median |realized-locked| 0 bp, so the lock holds).
- Payer and rule: longs on HL pay the floor. Quote (HL funding docs): "predetermined at 0.01% every 8 hours." The payer is whoever holds the long side of the floor-band; the fixed-pay side is the one that must pay 10.95% while P sits in band.
- Why not known: R412 measured the lock and the T-bill gap (+2.1 pts HL). It did not split the HL floor-band hours from premium-driven hours. Mechanism map row 10 says the floor "is the source" but no PREREG tests the mid against the floor band.
- Data held: `data/boros/hist/market-data/10-HYPERLIQUID-BTC-31OCT2025` and the other HL folders; settlement folders. Test: share of settled hours at exactly 0.1095 vs P in [-0.04%, +0.06%] (floor-band), by coin and year.
- Cheapest decisive observation: 0 euros, one script over existing zips (under 1 hour). Kill: floor-band hours settle at 0.1095 but mid is not systematically above or below it by more than 1 bp in the same hours (then the order book prices the floor and there is no gap).
- Value if true: a fixed-pay leg on HL would be a known floor payer; for a French retail owner with about 10k EUR on Hyperliquid, a lock is only useful if the mid is below the floor-band income. Expected value small; a Boros DeFi wallet is not needed for this leg (HL is a centralized-like perp DEX reachable with the owner's own account, owner decides).
- My probability it is true: 0.3. One line: the floor is printed exactly, but 4.5% of hours near 10.95 means the mid mostly does not sit at it, which is evidence against a simple pin.

### Q2. Does Aave USDC utilization above its kink coincide with negative-basis or high-funding episodes (basis traders as forced borrowers)?
- Hypothesis: when venue funding is high, basis traders borrow USDC on Aave to fund spot legs; Aave utilization rises and crosses the kink, so slope-2 borrow rates spike. The payer is the leveraged basis trader paying the slope-2 rate.
- Opposite: lending utilization on Aave is driven by idle-supply and collateral demand, uncorrelated with perp funding; the kink is a loan-demand story, not a funding story.
- Payer and rule: the borrower pays the two-slope rate above U_opt (Aave docs, WebSearch summary, not quoted verbatim; see section 5).
- Why not known: M478 captured Aave USDC/USDT borrow rates from DefiLlama 2026-11-12 "captured ... committed in experiments/carryhurdle_v1/raw/" and "the free endpoint stopped 2026-11-13". It used them as a hurdle, not as a regressor on funding. The series is 1 day to 3 months, too short for a kink study. Ethena's sUSDe was benchmark only (M481).
- Data held: M478's DefiLlama capture (`experiments/carryhurdle_v1/raw/`) only; I did not open journals. Public API needed: Aave's own on-chain/subgraph reserve data for USDC utilization, and Hyperliquid funding (held via the info API). Not tested this session.
- Cheapest decisive observation: one public API call for USDC utilization history (test: endpoint plus field `utilization` or `totalBorrow/totalSupply`), joined to HL BTC hourly funding. Hours: 3 to 5. Euros: 0.
- Kill: rank correlation between daily utilization change and HL mean funding below 0.1 at weekly resolution, both signs (then the kink is not driven by funding). The lab's R488 already killed the Ethena-supply version at weekly resolution (NULL), so this must use a different payer (borrowers, not minters).
- Value if true: a borrow rate spike is a financing cost for basis carry; a French retail owner cannot borrow on Aave from a bank account, and a DeFi leg needs the owner's self-custody wallet. That is the owner's decision; I do not recommend it.
- My probability it is true: 0.2. One line: the R488 NULL on the Ethena-supply version suggests the funding-to-lending link is weak; the kink mechanism is real but the regressor is unproven.

### Q3. Does Ethena's "backing shift to T-bill" when funding is low or negative make a predictable T-bill-linked supply of duration, and does the reserve fund absorb a payer that Boros fixed-receivers should be pricing?
- Hypothesis: when funding turns low or negative, Ethena moves backing into liquid stables (T-bill rate). Its short-perp hedges shrink, so the short-perp payer disappears and the funding level for shorts falls further. Boros fixed-pay (receiving negative funding) should be underpriced in those episodes because the reserve fund is an unpriced absorber of negative revenue.
- Opposite: the reserve fund and backing shift do not change perp hedge size enough to move funding; Boros prices negative funding as fully as any other funding; the reserve fund is small (no official size; third-party figures are 2024 and unverified).
- Payer and rule: Ethena's reserve fund steps in when combined revenue is negative (quote in section 1). sUSDe holders are shielded: "Ethena does not pass on any negative revenue to users who stake USDe for sUSDe." So the negative-funding payer is the reserve fund (and USDe holders through backing), not sUSDe stakers.
- Why not known: M535/R488 tested USDe supply change against next-week HL funding and was NULL. Nobody tested the negative-funding regime (the lab's data has funding negative only in the ETH case above). The reserve-fund trigger is a clamp-like rule (negative combined revenue), so the sign-conditional test is new.
- Data held: `data/` has HL hourly funding for BTC and ETH (fetched in M535 `experiments/usdeflow_v1/raw/`, not opened here); Boros settlement folders for HL and Binance ETH (`data/boros/hist/settlement`). Test: Boros settlementApr conditional on HL funding < 0 (by coin, year), compared with the T-bill rate. Public API: HL info (tested live, works).
- Cheapest decisive observation: count hours with HL funding < 0 per year for BTC and ETH from the public info API (one `fundingHistory` request per coin; field `fundingRate`), 0 euros, under 1 hour. Kill: negative-funding hours fewer than 2% of hours in the window (no regime to study), or Boros settlement equals HL funding exactly in those hours (no mispricing).
- Value if true: a negative-funding regime is where fixed-pay on Boros is paid by the reserve-fund side; for the owner, the relevant leg is a Boros or HL position, not sUSDe (sUSDe is not offered to EU/EEA residents, M481).
- My probability it is true: 0.15. One line: the mechanism is real (official docs say the reserve fund steps in), but the official page gives no size and the regime may be too rare on these venues to pay.

## 4. Observations that change the picture (for the reflection, not a trade)

- The clamp shapes a payer on HL: while P is in the floor band, the 10.95% floor is paid by longs. But the Boros mid is near the floor in only 4.5% of Oct 2025 BTC hours (section 2). The lab's "clamp is a payer" story needs the fixed side to price it, and in this market it mostly does not.
- Ethena's reserve fund is a designed absorber of negative funding; it is a payer that the lab has not measured. The official docs say it exists; size is unknown.
- Settlement clock: Boros settles on each venue's own interval (HL hourly, per the Boros docs summary). A Boros fixed receiver therefore pays and receives hourly on HL and at 8h on Binance: a clock mismatch the lab can exploit only if it measures both.

## 5. What was not checked (weakest links)

- Boros formula text, settlement cadence and oracle wording: taken from the search summary; the gitbook pages redirected (HTTP 307) and the docs.pendle page returned an empty body. Not verified verbatim.
- Aave v3 borrow formula: search summary only; the docs pages redirected or returned 404. No quote.
- Ethena reserve size: none found on the official page; third-party 2024 numbers are unverified.
- Boros market list: POST returned 404; the GET endpoint was not tested. The data in `data/boros/hist/` (fetched 2026-11-06) is the only Boros source used.
- The DeFi borrow series (DefiLlama) stopped on 2026-11-13; no fresh Aave series was pulled.
- Owner's suitability: a DeFi leg (Boros, Aave, sUSDe) needs a self-custody wallet and, for sUSDe, EU/EEA is excluded per M481. Whether to use a wallet is the owner's decision.
- I did not open any experiments/*/journal/ or run recursive greps over experiments/.
- I did not check whether Boros lists HL pools to EU residents; not verified.
