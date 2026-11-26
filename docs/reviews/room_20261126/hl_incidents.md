# Hyperliquid incidents 2024-01 to 2026-11: tail risk for a holder of perps or USDC

Date: 2026-11-26. Reader: research room (Haiku). Scope: public sources only (web pages, DefiLlama public API,
Hyperliquid public docs). No account, order, wallet or login. `experiments/*/journal/` not opened.

## Method and limits (read first)
- Search for incidents from 2024-01 to 2026-11. Verified by a page fetch are marked [F]. Items marked [S] come only
  from search-result summaries, not from a fetched page. Treat [S] as a lead.
- No verified 2024 Hyperliquid loss incident was found. One 2024 claim (North Korea-linked losses, 794K) comes from a
  single blog and is not counted.
- `status.hyperliquid.xyz` did not resolve from this session (not in the allowed network). Its incident history is
  NOT checked. Hyperliquid's own X posts were not reached either. Official statements below are quoted via media.
- Kraken listings: I did NOT check which of these coins Kraken lists. This matters for question (a).
- Bridge TVL is DefiLlama's daily series (`api.llama.fi/protocol/hyperliquid-bridge`, free, no key). It has one point a
  day, so no hour-level pre-signal can be read from it.

## Incident list (UTC)

| # | Date (UTC) | Event | Loss / holder outcome | Status |
|---|---|---|---|---|
| 1 | 2025-03-12 (time not given) | Large ETH long (about 160,000 ETH, about $15.2M USDC margin) liquidated at about $1,915; HLP took the position | HLP lost about $4.2M | [F] secondary (Cryptopolitan) |
| 2 | 2025-03-26, shortly after 12:50 | JELLY: HLP held a short (398,191,926 JELLY, entered at $0.011282); validators delisted and force-settled | HLP unrealized loss up to about $13.5M; final profit about $0.7M (sources differ) | [F] primary + CoinDesk |
| 3 | 2025-08-26 late (day, no time) | XPL pre-market hyperp spiked about 2.5x; shorts liquidated on Hyperliquid only | About $17M of short liquidations; HLP result disputed (sources range from a loss of about $12M to a gain) | [F] The Block |
| 4 | 2025-10-10, about 21:16-21:27 | ADL cascade across the market: about $2.1bn of positions closed "in 12 minutes" | Profitable opposite-side accounts were closed at the previous mark; amounts differ by study | [F] arXiv + Hyperliquid docs |
| 5 | 2025-11-12 (day, no time) | POPCAT: 19 wallets built about a $30M long on $3M collateral, then pulled the bid wall; HLP took over and lost about $4.9M. USDC Arbitrum bridge paused for hours | HLP bad debt about $4.9M-$5M; withdrawals resumed within hours | [F] Decrypt; [S] PANews, Arkham |
| 6 | 2026-04-09 (day; year per most outlets) | FARTCOIN: four linked wallets built about a $15M long; liquidation forced ADL onto HLP | HLP lost about $1.5M in 24h | [F] PANews (short quote) |
| 7 | 2026-05-28 (Thu, afternoon US; no UTC time) | SPACEX-USDH pre-IPO perp (run by Ventuals, a HIP-3 deployer): bad offchain data made the price fall 45% (2,277 to 1,254) in about 30 minutes | 484 users liquidated (The Block count; other counts 405); about $1.5-1.7M notional; compensation promised | [F] The Block |
| 8 | 2026-07-27, about 23:00 (one source) | SK Hynix perp (XYZ/trade.xyz, HIP-3): thin Korean premarket print passed to the oracle; price down about 17.9% | 960 long positions liquidated (about $57M); ADL took $10.8M from 100 profitable shorts; Hyperliquid says the oracle "operated according to its programmed design" | [F] CryptoPotato; [F] HokaNews quote |
| 9 | About July 2025 (exact date not verified) | Frontend / API outage, about 27-37 min, trading blocked; chain kept producing blocks | No loss stated | [S] Cryptopolitan |

Not counted: Binance's own HYPE withdrawal freeze (Nov 2026) is a Binance event. Abraxas leaving Hyperliquid is a
trader decision. Neither is a Hyperliquid incident.

### Details and quotes

**1. ETH whale, 2025-03-12.** Source: https://www.cryptopolitan.com/hyperliquid-losing-liquidity-whale-eth-trade/
- "Hyperliquid's community vault lost $4.2M after an aggressive trader closed a 160,000 ETH long position."
- Article time 13:42 UTC. The position was taken over at about $1,915.

**2. JELLY, 2025-03-26.** Primary: https://hyperliquid-co.gitbook.io/wiki/introduction/roadmap/incident/2025-26-03
- "On March 26, 2025, shortly after 12:50 UTC, Hyperliquid, a decentralized trading platform, fell victim to an attack targeting the JELLY token."
- "HLP now held a short position of 398,191,926 JELLY, entered at $0.011282."
- "After evidence of suspicious market activity, the validator set convened and voted to delist JELLY perps." and "A decentralized vote was held, with all validators approving within 2 minutes."
- "All JELLY positions were settled at the opening price of $0.0095, and the pair was delisted."
- "JELLY long position holders refunded by Foundation at advantageous settlement price (0.037555)."
- Loss: CoinDesk, https://www.coindesk.com/markets/2025/03/26/hyperliquid-delists-jellyjelly-after-vault-squeezed-in-usd13m-tussle, "HLP's unrealized PNL temporarily stood at negative $13.5 million." The settlement at $0.0095 was against about $0.50 on DEX oracles (CoinDesk).
- Final: about $0.7M profit on the HLP short (secondary, CryptoBriefing and others). Not confirmed on-chain here.

**3. XPL pre-market, 2025-08-26/27.** Source: https://www.theblock.co/post/368486/hyperliquid-new-safeguards-following-whale-driven-xpl-pre-market-liquidations
- Hyperliquid, abridged: "The robust mark price formula for hyperps correctly prevented an instant spike, … before triggering liquidations."
- Safeguard: "a new hard cap will limit hyperp mark prices to 10x the 8-hour exponential moving average".
- Liquidation figure $17.67M is from PANews citing Coinglass (search summary). HLP's P&L: conflicting; not established.
- Binance and Bitget pre-market prices did not spike (The Block/PANews summaries).

**4. ADL, 2025-10-10.**
- arXiv 2512.01112, https://arxiv.org/abs/2512.01112: "ADL was used repeatedly to close $2.1 billion of positions in 12 minutes." and "This comparison also suggests that Binance overutilized ADL far more than Hyperliquid."
- Window: 21:16-21:27 UTC, from an academic reconstruction (search summary; the lab's own intake cites 21:16-21:21 from arXiv 2603.15963). Not checked on a fetched page here.
- Hyperliquid docs, https://hyperliquid.gitbook.io/hyperliquid-docs/trading/auto-deleveraging (fetched): "the users on the opposite side of the position are ranked by unrealized pnl and leverage used"; "Those traders' positions are closed at the previous mark price against the now underwater user".
- Founder Jeff Yan's post (about 19 October, secondhand via Odaily, https://www.odaily.news/en/newsflash/453002) says ADL produced "hundreds of millions" of profit for users. Not read at source.
- Cost estimates differ: a Gauntlet-linked claim of about $650M excess loss (https://protos.com/outdated-algorithm-caused-650m-excess-losses-on-hyperliquid-report/, [S]) against a model giving about $45-52M. Model-dependent, not Hyperliquid figures.

**5. POPCAT, 2025-11-12.** Primary-ish: https://decrypt.co/348355/hyperliquid-paused-some-withdrawals-popcat-trader-scrutiny [F]
- Notice shared by users: "USDC deposits and withdrawals from the Arbitrum bridge are paused for maintenance."
- Discord admin: "The Arbitrum bridge is temporarily paused. Other deposits and withdrawals should be unaffected."
- Arkham: "$5M of bad debt on POPCAT to Hyperliquid's Hyperliquidity Provider (HLP)."
- PANews, https://panews.io/articles/01d15a9a-93e2-4c35-8f91-9690b4376898 [S]: "Due to the lack of liquidity, HLP was forced to take over the position, ultimately resulting in a $4.9 million bad debt loss." Attacker: 19 wallets, about $3M, about $30M long.
- Withdrawals back within hours (search summary, Conor Grogan). The USDC bridge held about $4.5bn, per one analyst [S].
- Only the Arbitrum USDC bridge was paused. No user loss of funds was reported.

**6. FARTCOIN, 2026-04-09.** PANews, https://panews.io/articles/019d70b7-8366-718b-845b-6565b12f4691 [F]
- "HLP lost approximately $1.5 million in the past 24 hours."
- "In a low-liquidity environment, the attackers triggered a "suicidal" liquidation, forcing the ADL mechanism to activate."
- Date given as April 9 (no year in the article). Cryptotimes URL gives 2026/04/09: https://www.cryptotimes.io/2026/04/09/fartcoin-drops-13-after-failed-manipulation-attempt-on-hyperliquid/ [S].

**7. SPACEX-USDH, 2026-05-28.** The Block, https://www.theblock.co/post/402991/ventuals-to-compensate-traders-after-pre-ipo-spacex-perps-plunge-45-on-hyperliquid [F]
- Ventuals: "incorrect data returned by an offchain data provider"; it is "evaluating the impact it had on affected users for appropriate compensation."
- Price 2,277 to 1,254, then about 2,174. 484 users liquidated (The Block); other outlets say 405 users and 1,393 positions.
- Ventuals operates the market, so this is a deployer's oracle, not Hyperliquid's core oracle. A Hyperliquid-side liability is unclear.

**8. SK Hynix, 2026-07-27.** CryptoPotato, https://cryptopotato.com/one-bad-price-960-liquidations-inside-sk-hynix-flash-crash-on-hyperliquid/ [F]: 960 accounts, about $57M liquidated, $17.3M realized losses; ADL: "$10.8 million in gains across 100 accounts" against profitable shorts; time 11pm UTC from a MarketAlpha post.
- HokaNews, https://www.hokanews.com/2026/07/hyperliquid-sk-hynix-perpetual-contract.html [F]: "the oracle system itself operated according to its programmed design."
- A thin trade on Nextrade (Korea) was relayed to the oracle; price recovered within about two minutes.

## (a) How many would have cost a hedged position more than 5%?

Answer: **none confirmed** in these ~3 years, with one unquantified exception (ADL, 2025-10-10). This is a lower bound from what I could find, not a count of all cases.

Mechanism. A hedge is long on one venue and short on the other, on the same coin. It loses when one leg closes at a price the other does not follow. On Hyperliquid three mechanisms do this:
1. **Forced settlement or delisting of a coin** (JELLY: settled at $0.0095 vs about $0.045 on Binance and about $0.50 on DEX oracles). A long on Hyperliquid receives the settlement price. A short on the other venue keeps the market price. The gap is the loss. JELLY was refunded to longs at $0.037555. For a short on Hyperliquid, this was a gain. Kraken did not list JELLY as far as I know (not checked).
2. **ADL at the previous mark** (2025-10-10). A profitable leg is cut at the previous mark. The hedge then becomes naked on the other venue for the rest of the window. Size: not measured here. This is the one mechanism that can hit a majors hedge (BTC/ETH), since ADL ran across the whole book that night.
3. **HL-only price spike or oracle error** (XPL, SPACEX-USDH, SK Hynix, FARTCOIN, POPCAT). These events moved the Hyperliquid mark, not the other venue. For a carry hedge, the Hyperliquid leg is what gets liquidated or ADL'd. Loss > 5% only if (a) that coin is listed on both venues and (b) the position is hit. Neither is verified for these coins on Kraken.

Count, with the two tests:
- Coin also on Kraken and hit on Hyperliquid: none verified (POPCAT, FARTCOIN, XPL, ETH whale: listing on Kraken not checked; ETH is listed on Kraken but the HLP took the whale's position, not the hedged leg).
- Majors (BTC/ETH) and ADL 2025-10-10: possible; loss size not measured here. I cannot give a number without Kraken and Hyperliquid candles for 21:00-21:30 UTC on that day. This is the first thing to test.

So: **0 confirmed, 1 unquantified (ADL on majors).** I would not state a count below 1 without that measurement.

## (b) Did a public signal come before them?

Bridge TVL, DefiLlama, daily (fetched 2026-11-26 with `curl -s https://api.llama.fi/protocol/hyperliquid-bridge`).
Scripts (scratchpad, not in the repo): `/tmp/claude-0/-home-user-T/a4c99094-0eba-54d5-9f6a-3abc85cabed2/scratchpad/bridge_window.py`
(event windows, output in `bridge_window.out`) and `.../scratchpad/bridge_base.py` (base rates). Core logic:

```python
pts = sorted((p["date"], p["totalLiquidityUSD"]) for p in j["tvl"])   # daily, 2023-06-09 to 2026-11-25
def at(t): return pts[bisect.bisect_right(ts, t) - 1]                  # last point at or before t
chg = lambda x, y: (x[1]/y[1] - 1) * 100
# d-1->d0 uses the day before the event; d-7->d0 is 7 days; d0->d+1 is the day after
```

| Event (UTC day) | d-1 to d0 | d-7 to d0 | d0 to d+1 |
|---|---|---|---|
| ETH whale 2025-03-12 | -1.36% | -3.15% | -6.81% |
| JELLY 2025-03-26 | -0.33% | -0.62% | -8.33% |
| XPL 2025-08-26 | -5.19% | +5.10% | +1.58% |
| ADL 2025-10-10 | -0.48% | +0.64% | -11.34% (crash day; confounded) |
| POPCAT 2025-11-12 | -1.66% | +0.59% | -1.21% |
| FARTCOIN 2026-04-09 | -0.90% | +1.36% | -1.58% |
| SPACEX-USDH 2026-05-28 | +0.04% | +4.69% | -0.05% |
| SK Hynix 2026-07-27 | +0.79% | +1.00% | -0.19% |

Base rate over 909 daily changes, 2024-06 to 2026-11: a one-day fall of 1% or more on 11.9% of days; of 5% or more on
0.8% of days (about 7 days). The 24h before XPL (-5.19%) is in that tail. Other pre-event falls are ordinary.

**Answer (b):** No consistent pre-signal. Three of eight events (ETH whale, XPL, POPCAT) had a daily fall of 1% or more
in the day before, close to the 11.9% base rate, so no edge. XPL's -5.19% is the one rare day before an event, but it is one case and the
TVL resolution is daily. The largest post-event falls (JELLY, ADL, ETH whale) show that bridge TVL reacts after the
event, not before it, so it is not an early warning.

Other public signals not measured (lead only): HYPE price, funding spikes and HLP drawdown. These were not pulled
here. Funding and HLP history are available from Hyperliquid's public `info` API (`type: "metaAndAssetCtxs"`,
`type: "fundingHistory"`), which answered in this session (`api.hyperliquid.xyz/info`). Not used yet.

## Open items (what would change this report)
1. Kraken listing check for each coin in the table (public Kraken instruments API). Needed for (a).
2. ADL 2025-10-10 on BTC/ETH: pull Hyperliquid candles and Kraken candles 21:00-21:30 UTC, measure the leg gap.
3. Hyperliquid's status page and X for 2025-11-12 and 2026-04-09 (blocked here; quotes above are secondhand for those).
4. Hourly signals (funding and HLP history) for the 24h before each incident.
