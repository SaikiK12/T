# QuantData: what each metric measures, the crypto version we hold, and what is worth testing

Written 2026-10-21 for the owner's ask ("recherche à propos de QuantData pour tous les metrics"). Sources:
- QuantData's own pages: quantdata.us, the API reference at quantdata.us/api/docs, and the help center at
  help.quantdata.us;
- the papers cited inline.

Nothing here was bought, and no QuantData data was used. The one statistic in this file is R291 (VPIN), from a frozen
PREREG.

## The short answer
- **What QuantData is.** A retail terminal for **US options order flow**:
  - founded 2020 in Orlando;
  - $74.99 a month, or $62.50 billed yearly;
  - a CME futures add-on at $74.99, or $119.99 bundled with options;
  - an API, plus an MCP server so AI agents can query it.

  It licenses exchange data (OPRA for options), recomputes about 30 views of it, and resells them to many
  subscribers.
- **It publishes no evidence that any metric predicts anything.** Its Net Drift guide says to use the tool "for
  insight only" and shows single-day SPY examples. That is normal for the category (Unusual Whales, Cheddar Flow,
  SpotGamma, MenthorQ). They sell views, not track records.
- **In crypto we can build its core metrics ourselves, for free, with better inputs and longer history:**
  - Deribit's history server gives every BTC and ETH option trade since late 2016, with the exchange's own
    aggressor side;
  - QuantData guesses the side from where the trade printed against the bid and ask;
  - QuantData's API offers "365+ days" of history.

  The terminal itself is not the edge. The question is whether any metric predicts perp moves, and that is testable
  here.
- **The reel the owner sent with it (VPIN, "toxic order flow") was tested tonight: NULL** (R291, below).

## 1. The metrics, mapped

QuantData's tool list comes from its home page, and the endpoint list from its API reference. Definitions are
QuantData's where it gives them. The status column points to `registry/methods.csv` and `registry/rounds.csv`.

**Order flow and premium**

| QuantData tool | What it computes | Crypto version | Held | Status in the lab |
|---|---|---|---|---|
| **Options Order Flow** (consolidated: blocks, splits, sweeps; "golden sweeps" over $1M) | US option trades, with the side guessed from the bid/ask print | Deribit trades, with the taker side exact and blocks flagged | Hourly flow per option since 2016; blocks trade by trade (`data/deribit_trades`, downloading) | Sweeps across exchanges have no crypto analogue, because options trade mostly on one venue. Large prints: M311 |
| **Net Drift** | Cumulative call and put premium by "sentiment": ask-side calls and bid-side puts bullish, and the reverse bearish; midpoint trades unassigned | Signed premium from Deribit taker sides | Yes (premium × imbalance per option-hour) | **M313 (new, QUEUED)** |
| **Net Flow** | Call and put premium (or volume) per interval | Same | Yes | M313 |
| **Gainers / Losers** | Tickers ranked by bullish against bearish premium | Only BTC and ETH have deep option books, so there is no cross-section | n/a | Not pursued |

**Dealer exposure**

| QuantData tool | What it computes | Crypto version | Held | Status in the lab |
|---|---|---|---|---|
| **Options Exposure** (DEX, GEX, VEX, CHEX by strike and expiry) | Greek-weighted exposure per strike. The API's sign: long calls and short puts are positive delta. Units per $1 or per 1% move | `lab/exposure.py` (Black-76, checked against Binance's greeks to a median 0.06%), with positions estimated from taker flow | Yes | M300, **M308 (next: R292)**, M309, M310 |
| **Heat Map** (30+ metrics) | Strike × expiry grid of greeks, IV, bid/ask and prices | The same grid from M308's positions | Yes | Display only |
| **Interval Map** | How delta, gamma, vanna and charm exposure build and decay through the day | Hourly taker positions (`exposure.taker_positions`) | Yes, hourly | M308 |

**Volatility, open interest and max pain**

| QuantData tool | What it computes | Crypto version | Held | Status in the lab |
|---|---|---|---|---|
| **Volatility Drift** | Per minute: "adjusted realized vol" against the IV of at-the-money options at the nearest expiry | 1-minute realized vol; Deribit trade IV per option-hour; DVOL; BVOL | Yes | IV minus RV as timing: R209 NULL (M138). BVOL change: M174 |
| **Volatility Skew**, **Term Structure**, **IV Rank** | The IV surface; IV percentile | Deribit trade IV by strike and expiry; the chain recorder; DVOL percentile | Yes | M099, M174 |
| **Max Pain**, **Max Pain Over Time** | The strike that minimizes option holders' payout | Needs open interest by strike. Trades cannot give it, because a trade can open or close | Only from 2026-10-21 (chain recorder) | M175, M289 |
| **Open Interest** (by strike, expiry, change, over time) | Open interest snapshots | Chain recorder, hourly | From 2026-10-21 | M175 |
| **Market Share** | Each exchange's share of option volume | Deribit against OKX, Binance and CME | Not needed | Not a signal |

**Equities, news and futures**

| QuantData tool | What it computes | Crypto version | Held | Status in the lab |
|---|---|---|---|---|
| **Dark Flow**, **Dark Pool Levels**, prints (with "phantom" prints flagged) | US off-exchange equity prints and the price levels where they cluster | No public off-exchange tape exists in crypto. The closest is Deribit block trades | Blocks, yes | M311 |
| **News** (with sentiment), **Exchange Notifications**, **Market Map** | Headlines and halts | Binance, Upbit and MEXC notice recorders; the delisting and monitoring-tag lanes | Yes | R267-R272. LLM labels need an API key (M312) |
| **Futures:** Footprint, DOM, Depth Map, Order Flow (CME book) | Book and trade views | `orderflow.delta_profile` (footprint), the 1 s tape recorder, and the MEXC and Lighter book recorders | Weeks of tape | M264, M307 |
| **API and MCP** | Programmatic access for agents | `scripts/terminal.py` design (`docs/AUCTION_AND_FLOW.md` section 5) | n/a | Plan only |

**From the reel, not QuantData**

| Metric | What it computes | Crypto version | Held | Status in the lab |
|---|---|---|---|---|
| **VPIN** ("toxic flow") | Mean \|buy − sell\| / volume over equal-volume buckets | `orderflow.vpin`, with the taker side exact per minute | Yes | **R291 NULL** |

## 2. Critique: what holds, and what does not

1. **"Sentiment" from the bid/ask print is a guess.**
   - An ask-side call can be:
     - a hedge;
     - a short covering (a closing trade);
     - one leg of a spread;
     - a dealer's inventory move.
   - QuantData's own bid-ask article says heavy activity alone does not reveal a thesis.
   - Deribit's taker flag removes the side guess, but not the open-or-close question.
2. **The academic result behind "follow the options flow" needs data these tools do not have.**
   - Pan and Poteshman (2006, RFS) found that stocks with low put-call ratios beat high ones by about 40 bp the next
     day. They counted only volume from buyers **opening** new positions, from proprietary CBOE data.
   - Signed or unsigned flow without that flag is mostly contemporaneous (Easley, O'Hara and Srinivas 1998), or its
     predictive power is fleeting (Blau, Nguyen and Whitby 2014).
   - On Deribit, Alexander, Deng, Feng and Wan (arXiv 2109.02776) find directional information in out-of-the-money
     trades, strongest in the 2021 bubble. That is why M313 has an OTM variant.
3. **The dealer sign is a convention, not a measurement.**
   - QuantData's API defines exposure signs by position (long calls and short puts are positive delta). It does not
     say how it knows who is long; open interest does not tell.
   - The usual tools assume customers buy calls and sell puts. Crypto option buyers are often the reverse (call
     overwriters sell calls).
   - M308 estimates the sign from taker flow instead. It is the lab's main advantage over a terminal.
4. **"Dark pool levels" as support and resistance has no test behind it.** A level where large prints happened is
   remembered after the fact. M311 asks the testable version: do Deribit block prints lead the perp?
5. **Max pain** is open-interest arithmetic. Pinning exists in equities on expiry days for heavily optioned stocks,
   and it is small. In crypto, R289's Friday settlement fade kept about +20 bp gross per trade. That is too small and
   too rare to trade on its own (`experiments/clockflow_v1/FINDINGS.md`).
6. **The business model is not a signal.**
   - The cost is one licensed feed. It is resold to many subscribers at $75 a month.
   - The newest channel is the API and MCP for AI agents, which is the "council" idea sold as a data source.
   - Its value to a user is time saved and things not missed, the same lesson as Bloomberg's
     (`docs/AUCTION_AND_FLOW.md` section 5).
   - For our market (crypto perps) a subscription would add nothing we cannot rebuild. For US indices (NQ/ES) it
     would be a different question; see question 1 in `docs/AUCTION_AND_FLOW.md` section 8.

## 3. The reel's metric, tested: VPIN (R291, NULL)
**The claim** (instagram.com/reel/DevaMerNUk_): market makers track VPIN to see informed traders coming, and pull
their quotes before a crash or a spike.

**The test**, frozen before any number:
- BTC, ETH and SOL perps, 1-minute bars;
- VPIN from Binance's exact taker split, and from bulk volume classification (the papers' guess), 50 buckets a day;
- added to a HAR volatility model with relative volume and hour of day;
- fitted on 2021-04..2023, read on 2024-01..2026-09.

**Result** (`experiments/vpin_v1/FINDINGS.md`):
- **Exact VPIN makes the 1-hour volatility forecast worse out of sample:** Diebold-Mariano t −12.5, MSE −0.9%. Its
  coefficient is even negative on BTC and ETH, because true one-sidedness falls when volatility rises.
- **BVC-VPIN is mostly volume** (correlation 0.53-0.59). That is Andersen and Bondarenko's critique, now seen in
  crypto.
- **As a crash alarm,** plain relative volume separates hours with a move over 4 standard deviations about 40x, top
  decile against bottom. VPIN manages 3x.
- M085 is TESTED and leaves the queue.

**What stays true:** the adverse selection of maker fills is real (R193; arXiv 2502.18625). Measure it with paper
markouts on the recorded tape (M227), not with VPIN.

## 4. What converges into the lab
- **Code:** `lab/orderflow.py` gains `volume_buckets`, `vpin` and `bvc_buy`, all tested. `lab/exposure.py` already
  covers DEX, GEX, VEX and CEX.
- **Lanes, in order:**
  1. **R292 `dealerflow_v1` (M308), NULL.** Dealer gamma from Deribit taker flow adds nothing to a daily HAR
     volatility forecast (DM t −1.23) and does not sign next-day hourly autocorrelation. Dealers are short gamma on
     76-92% of days, and the hedge they need is 0.05-0.13% of a day's perp volume per 1% move.
  2. **R295 `optflow_v1` (M313 and M311), NULL.** Neither net drift (signed option premium: all, OTM, or without
     blocks) nor block or screen delta flow leads the BTC or ETH perp over 1, 4 or 24 hours out of sample. Gross edges
     are a few bp per trade, against 17 bp of API round trip. The unusual-hour variant and the call/put line cross
     were not in the family.
  3. **R296 `charm_expiry_v1` (M309, M303's dose, M317), NULL.** R289's Friday settlement reversal does not grow
     with the position expiring near the money. The dealers' delta in expiring options moves the perp neither inside
     the 07:30-08:00 window nor in the two hours after it.
  4. **M310:** vanna after FOMC. Few events, so low power.
- **A crypto "QuantData"** costs nothing extra once M308 and M313 exist:
  - net drift, exposure by strike, the interval map, volatility drift and blocks;
  - point-in-time, with history back to 2016;
  - it is a section of the terminal design.

  It gets built only if one of the lanes above finds something worth watching. A dashboard of untested metrics is
  what QuantData already sells.
