# Auction, order flow and options positioning: the owner's 21 terms, what the lab holds, and what is worth testing

Written 2026-10-21 for the owner's message listing 21 trading terms. They asked for:
- as much data as possible for them;
- our own method, built critically, including the things that look absurd but may make sense;
- the repeatable parts converged into the lab with good names;
- "our own Bloomberg", and how Bloomberg makes money;
- an AI-agent council;
- and to question things together rather than just execute.

Nothing in this file is a return result. Every claim about edges points to a registered round, and every new test
below is a plan that needs a frozen PREREG first (AGENTS.md rule 1). The data checks reported here (greeks against
Binance's own, open-interest size, gamma notional against volume) are integrity and scale checks, not statistics on
returns.

## The short answer

**The 21 terms are three families, split by what information they use.**

| Family | Terms | Information beyond price bars | Lab's prior |
|---|---|---|---|
| **A. Auction market theory** | TPO, VWAP and SD bands, POC, VAL, VAH, initial balance, opening range, auction market theory, HVN, LVN, volume profile | None: they are transforms of open, high, low, close and volume | Low. 5,472 bar rules (R263), ICT levels (R246) and round numbers (R246, M230) are NULL |
| **B. Order flow** | Order flow, delta, CVD, absorption, exhaustion, delta profile, "dark pool" | Who was aggressive: taker buys against taker sells | Some life: taker imbalance is a confirmed gross edge in the atlas (R185); flow books A and B are the lab's best survivors |
| **C. Options positioning** | Gamma (GEX), delta (DEX), vanna (VEX) and charm (CEX) exposure | Who holds options and must hedge them | Untested. It is the most mechanical family, with equity evidence, but the dealers' side was unknown until today |

**What was built today**
- **Code** (all tested):
  - `lab/auction.py`: VWAP bands, volume and TPO profiles, POC and value area, HVN/LVN, initial balance;
  - `lab/orderflow.py`: delta, CVD, delta profile, absorption, exhaustion;
  - `lab/exposure.py`: Black-76 greeks; GEX, DEX, VEX and CEX; gamma profile, zero-gamma level, walls.
- **Binance options history** (`data/binance_options/`):
  - hourly greeks and open interest for every BTC, ETH, BNB, XRP and DOGE option, 2023-05-18 to 2023-10-23;
  - the BVOL implied-volatility index per minute, 2023-06-20 to 2026-10-20 (26 days missing).
  - Our greeks reproduce Binance's published ones to a median 0.06% (550,000 option-hours).
- **Every Deribit BTC and ETH option trade since late 2016** (`data/deribit_trades/`, downloading). Each trade carries the
  taker's side, and block trades are flagged. It gives two things:
  - an estimate of who is short gamma, from data instead of a guess;
  - the "dark pool" prints of crypto.

**What I would bet on.** Family C, measured from Deribit trade flow, used as a regime switch: should intraday
order-flow signals (family B) be faded or followed? Family A gets one cheap, placebo-controlled family to settle it.
The reasons are below.

## 1. The terms, one line each

| Term | What it is | In code | Data held |
|---|---|---|---|
| **TPO** (time price opportunity) | Market Profile's count of time periods in which price traded at each level | `auction.tpo_profile` | Binance 1m klines BTC/ETH/SOL 2021-26; 1h klines for all perps |
| **VWAP** | Volume-weighted average price since an anchor | `auction.vwap_bands` | same |
| **SD bands** | VWAP plus or minus k volume-weighted standard deviations of price since the anchor | `auction.vwap_bands` | same |
| **POC** (point of control) | The price bin with the most volume (or TPOs) | `auction.value_area` | same |
| **VAL / VAH** | Bottom and top of the value area: the 70% of volume around the POC, grown toward the bigger neighbour | `auction.value_area` | same |
| **Initial balance** | High and low of the session's first hour | `auction.initial_balance` | same |
| **"Another form of initial balance"** | The opening range: the same idea over 5-30 minutes (my reading; see question 2) | `auction.initial_balance(minutes=...)` | same |
| **Auction market theory** | Dalton's frame: price auctions up and down to find where two-sided trade happens (value), and leaves value when one side is in control | the module as a whole | — |
| **HVN / LVN** | High- and low-volume nodes: peaks (accepted prices) and gaps (rejected prices) of the profile | `auction.nodes` | same |
| **Volume profile** | Volume by price over a window; each bar's volume spread evenly from its low to its high | `auction.volume_profile` | same; finer from the tape (`data/tape`, 1 s, from 2026-10-21) |
| **Order flow** | Who traded aggressively (market orders) against whom (resting orders) | `lab/orderflow.py` | kline taker-buy volume; 1 s tape; Deribit option trades with side |
| **Delta** | Taker buys minus taker sells in a bar; from klines 2 × taker_buy − volume | `orderflow.delta` | same |
| **CVD** | The running sum of delta, reset per session or not | `orderflow.cvd` | same |
| **Delta profile** | Delta by price bin: where buyers or sellers were the aggressors | `orderflow.delta_profile` | same |
| **Absorption** | Heavy aggression with little price move: a passive player takes the other side | `orderflow.absorption` | same; refills on the 1 s tape are the better measure |
| **Exhaustion** | A new price extreme on weaker aggression | `orderflow.exhaustion` | same |
| **Dark pool** | Off-exchange equity venues that print trades afterwards. Crypto has no regulated dark pools. Its analogs are OTC desks (not public), Deribit block trades (now held) and Coinbase versus Binance spot flow (R210 NULL) | `fetch_deribit_trades.py` keeps every block trade | `data/deribit_trades/*/blocks/` |
| **Gamma exposure (GEX)** | Dollars of delta dealers must trade per 1% move: sign × gamma × OI × F² × 0.01 | `exposure.exposures`, `gamma_profile`, `zero_gamma`, `walls` | Deribit chain hourly from 2026-10-21; Binance 2023; Deribit trades since late 2016 |
| **Delta exposure (DEX)** | Dealers' delta notional: sign × delta × OI × F | `exposure.exposures` | same |
| **Charm exposure (CEX)** | How dealers' delta drifts per day as time passes, nothing else moving | `exposure.exposures` | same |
| **Vanna exposure (VEX)** | How dealers' delta changes when implied vol moves one point | `exposure.exposures` | same, plus DVOL and BVOL |

## 2. Why the three families deserve different weights

**A is old information in a new shape.**
- Every term in A is computed from the same bars the lab has already searched hardest. 5,472 chart rules, including
  VWAP and Bollinger on 1 h to 1 d bars, failed (R263).
- What A could still add is a claim about where other traders put their orders: "everyone watches the POC". That is
  testable, but not best as a PnL rule (section 3, point 2).
- The one genuinely new part is resolution. Profiles on 1-minute or 1-second data, anchored to real sessions, have
  never been run here.

**B carries information bars do not.**
- A kline's taker-buy volume is the exchange's own record of trade sides, not a guess from the bar's shape.
- The lab's taker-imbalance features replicated as gross edges (R185). Flow books A and B, the best survivors, are
  built on positioning and flow.
- Intraday flow (1-minute delta, absorption, exhaustion) has not been tested here. The quarter-hour paper (C11) is
  the nearest evidence, and it is about 0.5 bp at short horizons against about 5 bp taker costs.

**C is the only family with a mechanism that forces someone to trade.**
- A dealer who is short gamma must buy as price rises and sell as it falls, whatever they think. A dealer who is long
  gamma does the opposite.
- Equity evidence:
  - intraday momentum is stronger when dealer gamma is negative (Baltussen, Da, Lammers and Martens 2021);
  - prices pin to large strikes at expiry (Ni, Pearson and Poteshman 2005).
- **The size is real in crypto too.** On the 21:00 UTC Deribit snapshot (one snapshot, 2026-10-21), BTC options
  carried about $467M of call and $166M of put gamma notional per 1% move. A median hour of Binance's BTCUSDT perp
  traded about $330M in September 2026. So full delta-hedging of a 1% move would be about one hour of Binance perp
  volume. That is a dose worth testing, not a rounding error.

## 3. Critique: what is absurd, and what looks absurd but may make sense

1. **Sessions in a market that never closes.** IB, opening range, daily VWAP and TPO all need a session start. Crypto
   has none, so every anchor is a choice. But some clocks do move crypto:
   - 00:00 UTC (daily candles, funding at 00/08/16 UTC);
   - 08:00 UTC (Deribit expiry);
   - 09:30 New York (ETF flows, US equities);
   - 08:00 London.

   **The test is an anchor placebo.** Compute the same levels from the real anchors and from random clock times fixed
   in advance. If real anchors behave no differently from random ones, the session is noise in crypto. The answer is
   useful either way, and no single rule can answer it.
2. **"Levels work because everyone watches them."** If that is true, it should show where orders are, not only in
   PnL:
   - resting depth should cluster at prior-day POC, VAH, VAL and IB edges more than at placebo prices;
   - price should overshoot and reverse through them (stop runs) more than through placebo prices.

   The MEXC depth recorder (R224) and the 1 s tape can measure both. A mechanism check like this is cheaper and
   harder to fool than a PnL backtest. If it fails, every PnL rule built on these levels is unmotivated.
3. **Volume profiles from hourly bars invent resolution.** Spreading an hour's volume evenly over its range is a
   guess. On 1-minute bars it is close; on the tape it is exact. Only 1-minute and tape profiles should be tested.
4. **VWAP bands are Bollinger bands with volume weights.** Fading ±2 SD is the R263 Bollinger family on another
   anchor. Only intraday, session-anchored bands are new.
5. **Absorption and exhaustion are stories told after the chart.** A trader who sees absorption at VAL and a bounce
   remembers it, and forgets the times price went straight through. The mechanical versions in `lab/orderflow.py`
   have free knobs (window, k, m), so they must be tested as one family with multiplicity built in. A trader's
   favourite setting is not enough.
6. **Kline delta loses the order of trades.** "Footprint" charts show delta at each price inside a bar. That needs
   the tape (Binance aggTrades, recorded live from 2026-10-21). History would be a large download.
7. **"Dark pool" is borrowed from equities.**
   - Crypto's real off-book flow is OTC desks, which publish nothing.
   - Deribit block trades are negotiated off the book and printed afterwards. They are now held, and give a free
     test of whether block prints lead price.
   - The Coinbase premium (US buyers against offshore) was NULL (R210).
8. **The GEX sign is a guess, and the vendors know it.**
   - Every GEX chart assumes dealers are long calls and short puts. That is the equity story: customers sell calls
     against stock and buy puts for protection.
   - In crypto, customers often buy calls. Yield vaults sold calls in 2021-22, then faded.
   - The money in GEX is mostly in selling GEX: SpotGamma-style subscriptions and the gamma-heatmap course in the
     owner's reel (M300).

   **The fix is the Deribit trade history.** Takers' net buying of each option since listing is the takers' net
   position, and the makers hold the opposite. If makers are mostly dealers (the usual reading, still an assumption),
   that measures the dealers' side instead of assuming it.
9. **The Binance 2023 option history is a small venue.** Its BTC open interest was about $191M (median hour, 2023).
   Deribit's BTC open interest today is $33.5B (2026-10-21 21:00 UTC). Deribit was also much larger in 2023, though I
   did not check by how much. So GEX from Binance's 2023 book measures Binance's customers, not the market's dealers.
   It is a code-validation set and a weak exploratory sample, nothing more.
10. **Charm and vanna are real flows, with few events.**
    - Charm moves dealers' delta as expiry approaches, with nothing else changing. That points straight at R289's
      Friday finding: moves in Deribit's 07:30-08:00 UTC settlement window reverse by about 15-20 bp afterwards. It
      was too small to pass the test, but it is consistent with hedges being unwound at expiry.
    - Vanna rallies are the claim that an implied-vol crush after an event lets dealers who are short puts buy back
      hedges.
    - Both happen a few dozen times a year, so each test has a few dozen events, and the dose (expiring gamma,
      vanna × IV change) must be in the PREREG.
11. **Costs decide intraday ideas before signals do.**
    - A 1-minute rule with a 3 bp gross edge pays 6-8 bp a side as an API taker on MEXC. On a 0-fee maker contract it
      pays only the spread.
    - Every intraday family here reports its break-even cost first, and is tested at the cost of the venue it would
      actually run on:
      - MEXC manual web 0 / 2-4 bp;
      - the 1,106 MEXC contracts with 0 maker fee;
      - Lighter.
    - The adverse-selection warning (maker fills are picked off, arXiv 2502.18625) still applies.
12. **The 24 h market gives crypto auction theory one thing equities lack.** There is no overnight gap, so "value
    migration" (today's value area against yesterday's) is continuous and measurable every hour. This is unexploited,
    and it is a cheap feature for family A, not a reason to believe in it.

## 4. What converges into the lab

**Code: one module per family, pure functions, causal (a value at bar t uses bars through t).**
- `lab/auction.py`: `session_ids`, `vwap_bands`, `spread`, `volume_profile`, `tpo_profile`, `value_area`, `nodes`,
  `initial_balance`.
- `lab/orderflow.py`: `delta`, `cvd`, `delta_profile`, `absorption`, `exhaustion`.
- `lab/exposure.py`: `greeks`, `exposures`, `by_strike`, `gamma_profile`, `zero_gamma`, `walls`. The recorder keeps
  its own `gex()` for the hourly digest.

**Data**

| Folder | What | Span |
|---|---|---|
| `data/klines_1m` | BTC, ETH, SOL 1-minute bars with taker-buy volume | 2020-26; pre-2021 reserved |
| `data/tape` | 1 s top of book and trade sides, Binance and MEXC, 12 coins | live from 2026-10-21 |
| `data/binance_options/eoh` | hourly option rows with greeks and OI | 2023-05..10 |
| `data/binance_options/bvol` | BVOL index per minute | 2023-06-20..2026-10-20 |
| `data/deribit_trades` | every BTC/ETH option trade as hourly signed flow; block trades whole | 2017-now, downloading |
| `data/recorders/deribit_chain` | hourly OI, IV and prices of every Deribit option | live from 2026-10-21 |

**Methods rows:**
- M305-M312 are new (`registry/methods.csv`);
- M099, M174, M179, M207 and M300 are updated, because their data is now held.

**Planned lanes.** Each gets its id claimed on #7 and a frozen PREREG first.

| Name | Question | Data | When |
|---|---|---|---|
| `auction_v1` (R290, **NULL**: anchor test p 0.36, trading rc_p 0.43; `experiments/auction_v1/FINDINGS.md`) | Do session anchors matter? Value-area re-entry, IB and opening-range break, VWAP-band fade and follow, naked-POC return, absorption and exhaustion filters; real anchors against placebo anchors, on 1-minute BTC/ETH/SOL | held | now |
| `levels_depth_v1` | Does resting depth cluster, and do stop runs reverse, at auction levels more than at placebo prices? | MEXC depth, tape | after about 2 weeks of tape |
| `vpin_v1` (R291, **NULL**: exact-side VPIN worsens volatility forecasts, DM t −12.5; `experiments/vpin_v1/FINDINGS.md`) | Does order-flow toxicity (VPIN) forecast realized volatility beyond volume? From the owner's reel; QuantData's metrics are mapped in `docs/QUANTDATA.md` | held | done |
| `dealerflow_v1` (R292) | Does taker-flow positioning (dealer gamma by strike) predict next-day realized volatility and the sign of intraday autocorrelation? This is a mechanism check before any PnL | Deribit trades, 1m klines | when the download ends |
| `charm_expiry_v1` | Does R289's Friday reversal scale with expiring gamma? (dose-response) | Deribit trades, 1m klines | after `dealerflow_v1` |
| `blocks_v1` | Do Deribit block prints lead BTC/ETH perp returns over 1-24 h? | Deribit blocks | when the download ends |

## 5. Our own Bloomberg

**How Bloomberg makes money.** Bloomberg L.P. does not trade. It is private, so these figures are approximate public
estimates, not checked here: about $12-13B a year in revenue, most of it from roughly 325,000 terminals at roughly
$25-30k a seat a year. Smaller lines:
- data feeds and enterprise licences (B-PIPE, data licence);
- trading and order-management software;
- indices (licensed to funds that track them);
- news and media.

The moat is not any single dataset:
- **aggregation and normalization:** every market in one place, cleaned, with history;
- **the network:** chat between traders on every desk;
- **workflow:** analysts' models, alerts and order tickets all live in it, so leaving is costly.

**What that means for us**
1. A terminal saves time and catches things. It does not create an edge. Bloomberg's own customers lose money every
   day.
2. **What compounds is history nobody else kept.** Bloomberg's archive is its moat. Ours is the recorders: wallet
   status, the Deribit chain, MEXC depth and next funding, DEX prices, the tape and the notices. None of these can be
   bought later. That is why "all data possible" matters most for the point-in-time data, and the recorders come
   before more history downloads.
3. **The network piece already exists in miniature:** issue #7, the room where Claude and Codex trade calls.
4. **Selling the data is possible in principle**, as Kaiko and Tardis do. But venue terms often forbid
   redistribution, and it is not the owner's goal. Not pursued.

**The terminal design.** `scripts/terminal.py <COIN>` would give one page per coin, every field point-in-time:
- **prices:** last price on each venue, and gaps against Binance (MEXC, Gate, KuCoin, Lighter, Hyperliquid, DEX
  pools);
- **funding and positioning:** funding now and next on each venue; basis; open interest; long/short ratios;
- **options** (BTC, ETH): GEX profile, zero-gamma level, call and put walls, 25-delta skew, DVOL/BVOL, and block
  prints in the last 24 h;
- **auction:** yesterday's POC, VAH and VAL; today's VWAP and bands; IB and opening range; value migration;
- **order flow:** today's CVD, and the latest absorption and exhaustion flags;
- **events:** wallet deposit and withdrawal status, notices, unlock calendar;
- **lab state:** open paper tickets on the coin, and which lanes hold it.

Most fields already exist in `lab/daily.py`'s panel, the recorders and the dashboard. The terminal is a join, not new
research. It is also the input a council would read (next section).

## 6. The AI-agent council

**The idea.** Several LLM agents (price, volatility, news, a risk manager, a judge) debate and then take a position.
Published versions such as TradingAgents (arXiv 2412.20138) report good backtests, but over a few months.

**Problems that are structural, not fixable by better prompts**
1. **Backtests are contaminated.** The model was trained on text written after the backtest period, so it may "know"
   what happened next to an asset or event. Masking tickers helps a little, not enough. Only forward decisions, made
   after the model's training cutoff, count.
2. **News latency.** Machines price headlines in milliseconds to seconds. An LLM council takes seconds to minutes,
   and its news feed is slower still. It cannot win a race on news that is already public.
3. **Not reproducible.** Model versions change, and sampling varies. A lane must pin the model, freeze the prompts
   (hash them like a PREREG) and log every input.
4. **Cost and statistical power.** Each decision costs several API calls, and a daily lane needs hundreds of
   decisions to say anything (the same arithmetic as in `docs/DIRECTION.md`).

**Where an LLM can genuinely help**
- **Reading slow text that markets price slowly:**
  - exchange notices (the lab parses them with rules today);
  - token unlock and governance documents;
  - Korean exchange notices;
  - court and regulator filings.

  Here an LLM is a feature extractor: text in, a label out. Its labels can be tested like any feature, forward-only
  or on text dated after its cutoff.
- **Research triage.** Turning reels, talks and comments into falsifiable method rows is what this session already
  does (`docs/TRADER_TALKS.md`, `docs/COMMENT_DIG.md`).

**A proposal, if the owner wants it**
- **`council_fwd`:** a forward paper lane.
  - Each hour, the council reads the terminal snapshot for BTC, ETH and SOL and writes a ticket before the outcome:
    direction, size from −1 to 1, and its reasoning.
  - Prompts are frozen and hashed, and the model is pinned.
  - It is compared against simple baselines, always flat and 24 h momentum, net of manual-web costs.
- **It needs an API key, which is a credential, so only the owner can set it up.** It would run from
  `scripts/forward_all.sh`. The cost is a few dollars a day at hourly decisions.
- **Without a key,** the only "council" is this session. Its judgment is not frozen, and it sees outcomes before
  writing the next ticket, so it is not a valid lane.

## 7. My own method from all this

1. **Settle family A once, cheaply, with the anchor placebo** (R290 `auction_v1`, run 2026-10-21: **NULL**).
   - Real session starts (00:00 UTC, the New York open, the London open) were no more structured than eight random
     clocks: rank-permutation p 0.36.
   - No auction rule traded. The discovery pick, following VWAP-band breaks after the New York open, lost in
     2024-26.
   - A random clock (11:04 UTC) produced the best discovery result of all, and it vanished too.
   - So session levels leave the queue as signals. They remain open only as a liquidity map (M307).
2. **Measure the dealers before trading them.** Build taker-flow positioning from the Deribit history. First check
   the mechanism, which needs no PnL: is realized volatility higher, and intraday autocorrelation positive, when
   estimated dealer gamma is negative? Only if it is does a regime rule follow: fade order-flow extremes in long
   gamma, follow them in short gamma.
3. **Treat levels as a liquidity map for execution, not as signals.** Even if no level predicts direction, knowing
   where depth sits cuts the cost of every other lane's orders. That is where a small trader's edge is real.
4. **Run intraday ideas only where fees are near zero.** MEXC 0-fee maker contracts and Lighter, with the adverse
   selection measured from paper markouts.

## 8. Questions for the owner

1. **How do you use these tools today?** Which market (BTC perps, altcoins, NQ/ES?), which timeframe, and one rule
   you actually trade, for example "absorption at VAL, target POC". A rule you trade is worth more than ten from
   videos, and it would be its own pre-registered lane.
2. **"Another form of initial balance":** do you mean the opening range (the first 5-30 minutes), a different session
   start (London, New York, Asia), or a weekly or monthly balance?
3. **The AI council:** do you want a forward-only `council_fwd` lane? It needs an API key that you set up yourself
   (I cannot handle credentials), and it costs a few dollars a day.
4. **The GEX sign:** have you seen GEX levels work, and on what? If it was on SPX or NQ, the crypto version is a
   transfer test, and I would frame it that way.
5. **The macro calendar (M290):** the CPI and NFP calendars are blocked from this container (BLS 403, FRED bot
   check). Shall I run the FOMC-only version, whose dates are in `lab/sessions.py`?
