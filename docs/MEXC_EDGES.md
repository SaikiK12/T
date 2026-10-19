# MEXC: what the owner's venue changes

Two sources:
- a subagent's research note (2026-10-19), from public MEXC endpoints and sources, about 35 requests;
- this repo's own checks, marked [lab].

Grades:
- **A:** peer-reviewed and replicated;
- **B:** peer-reviewed;
- **D:** own or practitioner observation.

Nothing here is a tested edge. Each rule at the end needs its own frozen PREREG.

## Fees
Read from the public `contract/detail` endpoint on 2026-10-19.

**Web and app orders (1,200 contracts):**

| Contracts | Taker | Maker |
|---|---|---|
| 476 | 2 bp | 0 |
| 546 | 4 bp | 1 bp |
| 20 | 10 bp | 4 bp |
| 4 | 1 bp | 0 |
| 154 | 0 | 0 (`isZeroFeeSymbol`: DOGE, ADA, LINK, AVAX, ARB, OP, APT, ONDO and others) |

- 634 contracts have a maker fee of 0.
- Five are marked `TEMP` (promotional).

**API orders** (MEXC notice of 2026-05-28, effective 2026-06-01, https://www.mexc.com/ro-RO/announcements/api-updates/futures-19):
- The fees are now 6 bp maker and 8 bp taker.
- The rates were 4 / 6 bp before May 2026 and 1 / 5 bp before that.
- The notice says API fees override promotions, so zero-fee contracts are not zero through the API.
- The notice's own example still shows the old rates, so confirm with MEXC before relying on them.

**Spot taker** on the USDT pairs the carry lane uses averages 5.6 bp [lab, R220 status]. MEXC lists 5-8 bp.

**For the lab:**
- The flow books on MEXC (R215, R218) charge Binance tier costs of 6-20 bp one way, fee plus slippage. That is
  conservative for manual web orders and about right for API orders.
- The owner places real orders by hand (AGENTS rule 6), so the web fees apply.

## Funding
- **Cycle.** Every contract the subagent sampled (8 of 1,200) settles every 8 h at 00/08/16 UTC. Caps vary: BTC
  ±0.18% per 8 h, SOL ±0.75%, small alts up to ±3% (D).
- **Same as Binance.** MEXC's settled rates matched Binance's:
  - for BTC, SAND, DOGE and SOL over Sep 17-30, 2026, correlation was 0.9997 or more and the mean gap under 0.02 bp
    (D);
  - across all 58 R200 symbols, the median gap in trailing 72 h APR was 0.0008 [lab, R220 data check].
  - There is no funding spread to harvest between the two venues. Zhivkov (2026, *Mathematics* 14(2):346; B) finds
    that cross-venue funding spreads rarely survive costs.
- **The difference is spot.** MEXC lists USDT spot pairs for small alts that Binance spot does not: AKE, BTW, Q and
  USELESS among the top-50 perps in October 2026.
  - So the confirmed carry (R191) has more coins to hold on MEXC.
  - In R220's replay the MEXC book held a position on 18 of 18 days, and the Binance book on none [lab].
- **Extremes on 2026-10-19** (D):
  - Crypto: SAND -0.25% per 8 h (last five settlements -19 to -113 bp), BTW -0.21%, CT -0.19%.
  - TradFi stock tokens (BMYSTOCK, PWRSTOCK) show about +0.77%.

## Prices, depth and open interest
- **No lead-lag at minute scale.** MEXC perps and Binance spot correlate at 0.955-0.972 at the same minute for DOGE
  and SOL, and at most 0.07 at ±1-3 minutes. Neither venue leads (D, one day). Sub-second lead-lag was not tested.
- **Depth.** Spreads on zero-fee contracts are tight (0.9-2.3 bp), but depth within 0.5% is thin on small names:

  | Contract | Bid depth within 0.5% |
  |---|---|
  | VVV | $37k |
  | JASMY | $112k |
  | APT | $201k |
  | ONDO | $2.4M |

  Size orders to depth, not to the 24 h volume.
- **Volume can be fake.** Crypto wash trading is widespread on unregulated venues: Cong, Li, Tang & Yang, NBER w30783
  (B), found fabricated volume averaging over 70% of reported volume. MEXC is not named. Rank MEXC coins by depth or
  open interest rather than by volume.
- **Open interest and long/short.**
  - MEXC publishes no open interest or long/short history.
  - `ticker.holdVol` looks like open interest in contracts (unit undocumented).
  - A MEXC-native positioning signal would need a recorder that polls every few minutes.
  - The flow books use Binance's ratios, which is fine while the coins are the same.

## Rules to pre-register (not run; each is a new lane)
1. **Maker dip on zero-maker contracts.**
   - **Order:** a buy limit at close x (1 - sigma_24h) for the next hour, filled only when price trades through.
   - **Exit:** after 4 h, or at limit + sigma.
   - **Costs:** web 0 / 2 bp, or API 6 / 8 bp.
   - **Report:** hedged and unhedged results.
   - **Evidence:** R193 found the same entry on Binance-replicated cells gained +20 bp per trade over a taker entry,
     but the book was long-alt beta.
2. **Negative-funding capture around settlement: tested, NULL (R223).** The funding is paid, but the price moves
   against the holder by 1.5-2.3 times the payment. Top 50: long on -0.20% nets -38.5 bp per event.
3. **Day-14 listing short with a stop.** Weak:
   - the Binance listing holdout failed (R189);
   - ICO and cross-listing studies show positive early drift (Benedetti & Kostovetsky 2021; Ante & Meyer 2021; B).
4. **MEXC open-interest recorder.** Poll `ticker` every 5 minutes and append `holdVol`, the last price and the
   funding rate. No trade until 30 days exist and a PREREG is frozen. This needs a process that runs continuously,
   which the 30-minute loop cannot provide.

**Not checked:**
- the Innovation Zone pair list;
- `holdVol` units;
- the side codes in `deals`;
- `collectCycle` beyond 8 contracts;
- the full text of Zhivkov (2026).
