# What traders say in comment sections and transcripts (2026-10-21)

The owner's ask: gather quant and trading transcripts and comment sections (Instagram included) and look for good
ideas. This note says where the text came from, what could not be reached, which ideas are new to the lab and which
the lab already tested. Nothing here is a result: an idea is a claim until a frozen lane tests it. Commenters are not
named; their words are paraphrased, and quotes are short.

## What was collected
`scripts/dig_comments.py` (comment sections and forums) and `scripts/dig_podcasts.py` (transcripts) write to
`data/comments/` and `data/videos/` (gitignored). `python scripts/dig_comments.py mine` scores every comment for
mechanism words, a practitioner speaking ("when I was at", "our desk"), specific numbers and votes, and writes one
reading file per source to `data/comments/read/`.

| Source | Route (no login) | Collected | Read |
|---|---|---|---|
| Hacker News | Algolia API, 46 queries (firms, mechanisms, "Ask HN" threads) | 105,495 comments in 400 threads | top 400 ranked |
| Reddit | Arctic Shift archive (reddit.com refuses this machine) | r/algotrading posts paged from 2016 (still paging); 26,963 comments in the 250 most discussed threads of 2016-01 to 2021-02 | top 400 ranked |
| Quant Stack Exchange | Stack Exchange API | 400 top-voted questions, 2,398 posts | top 400 ranked |
| YouTube comments | public Piped mirrors | 1,440 comments under 159 practitioner videos | top 400 ranked |
| TikTok comments | TikTok web API with browser impersonation | 2,069 comments under 30 videos (the owner's two and the top 15 by views of each of the two accounts) | top 400 ranked |
| Podcasts | RSS feeds with published transcripts, plus Jane Street's Signals and Threads pages | 17,971 episodes listed; 270 transcripts held | keyword grep |
| Instagram | reel pages | caption, likes and comment count only | none |

**Reach limits, stated plainly.**
- **Instagram comments are not reachable without a login.** The comment API answers 429 or 403. The embed page has the
  caption and no comments. Public viewer sites (imginn, picuki) answer 403. The lab uses no credentials (AGENTS.md rule
  5), so no Instagram comments were read.
- **YouTube captions** come only through an Invidious mirror that fails most of the time. YouTube comments work.
- **Reddit** is paged month by month through the archive, which is slow (about a minute per month of r/algotrading).
  r/algotrading, r/quant, r/quantfinance and r/highfreqtrading are paged in full. Eleven larger subreddits are searched
  by title words ("strategy", "edge", "arbitrage", "funding", "basis", "AMA", "worked at", "profitable" and others).
  The collector resumes where it stopped.
- New podcast feeds with transcripts: Masters in Business (816 transcripts), Delphi (489), Bankless (1,141), Resolve
  Riffs, and six Signals and Threads episode pages. Feeds without transcripts (Alpha Exchange, Wintermute's, Curious
  Quant, Uncommon Core) were listed but not transcribed.

## What the sources are worth
- **Hacker News is the best source by far.** People who worked at trading firms explain how their desks made money,
  and others argue with them. Most of the ideas below come from HN.
- **Quant Stack Exchange is textbook material.** Good on mechanics (gamma scalping, skew trading, market-making
  control), thin on what makes money. Its practical points (rebate economics, point-in-time data, factor-residual stat
  arb) are already lab rules or rows below.
- **YouTube comments are mostly praise, spam and scam replies.** A few are useful: a cross-venue funding arbitrageur
  who now enters only when the price spread is favourable, and a trader who finds an edge only when BTC funding is
  negative.
- **TikTok comments carry almost no trading content.** Under the owner's two videos and the two accounts' top videos,
  the top-ranked comments are about AI, rockets and politics. This is a result: TikTok comment sections are not worth
  more collection.
- **Podcast transcripts** (Bankless, Delphi, Masters in Business) are mostly market narrative. They gave four concrete
  items (M295-M297 and the unlock remark below).

## Ideas, and where the lab stands

**New rows in `registry/methods.csv` (all UNTESTED):**

| Id | Idea | Source | Data |
|---|---|---|---|
| M288 | DEX-CEX gap on long-tail tokens: trade the perp toward the on-chain pool price | ex-crypto prop trader (HN) | pool history not held |
| M289 | Option-expiry pinning in BTC and ETH toward the largest open-interest strike | index-options PM (HN); options-MM video comments | strike OI history not held |
| M290 | Reactions to scheduled US releases (CPI, NFP, FOMC, weekly EIA report) in crypto perps | practitioners (HN) | calendars public; 1-5 min klines needed |
| M291 | Prediction-market No bias ("Nothing Ever Happens" bot) and the favourite-longshot bias | HN | Polymarket history (public API) |
| M292 | Fee-tier and rebate map: re-price each lab rule at the tier its own volume reaches | ex-crypto prop trader (HN); Quant SE | partly held |
| M293 | A volume burst on another spot venue leads the Binance or MEXC perp | HN (unverified claim) | Bitfinex and Coinbase candles not held |
| M294 | Wallet-suspension premium: the gap when deposits or withdrawals are closed, and its close on reopening | arbitrage-bot builders (HN) | notices held; wallet-status history not held |
| M295 | Funding response to up days as a regime gate | Bankless guest | **tested: R297 NULL** (the guest's 2026 < 2022 premise holds, but it is the funding level and does not time the market) |
| M296 | Pre-market perp price as a forecast of the listing | Bankless | partly held |
| M297 | Post-airdrop supply short (a subset of the listing short) | Bankless, Delphi | airdrop share not held |
| M298 | PCA residual reversion (Avellaneda-Lee) at hourly scale | Quant SE | **tested: R287 NULL** (gross up to 19 bp/day in discovery and 9 in validation; cost 18-76) |

**Reddit (r/algotrading so far) added no new rule.** Its most discussed threads are AMAs (people at HFT and
options market-making firms, a fund quant researcher, a fixed-income PM) and career talk. What it says about trading
the lab already has:
- "Stop predicting prices and trade relationships": spreads, mean reversion, stat arb (one commenter's bank algo desk
  trades only these). See M298 and R250.
- "Rebalancing beats HODL by 234%" (an equal-weight random basket rebalanced hourly): R232 rebalance cadence NULL.
- "Bollinger mean reversion gets destroyed in crypto; breakouts do better": R263 ran 5,472 chart rules, Bollinger
  fades included; only strategy 330 goes on to batch 1.
- Fees decide short horizons: derivatives venues once paid makers 2.5 bp (7.5 bp taker); Binance futures paid
  rebates only above 50,000 BTC a month; Kraken spot charged 26 bp taker and 12 bp maker. Spot fees kill scalping
  (M292, M264). These are dated forum claims, not current fee schedules.

**The most useful single comment.** An ex-crypto prop trader whose team's best month was $6B of volume: they tried
"pretty much everything", and only exchange rebate and VIP programs, pure latency arbitrage and obscure arbitrage (such
as on-chain AMMs against exchange futures) worked. "Nothing based on OHLC worked." The lab's record agrees: 80 rounds
of price-based daily books, nothing through gate 1. M288 and M292 come from this comment, and it is a reason to weight
event, carry and venue-structure lanes over chart rules.

**Already tested or running in the lab:**

| Idea from the comments | Lab |
|---|---|
| Sell index options at 1.8-2 sigma, 45 days out, sized by VIX; buy UVXY puts after vol spikes | R241 (SVXY in contango) NULL; R283 (VIX panic onsets) NULL |
| Cross-exchange spot arbitrage | the gaps have reasons (M294); R205 and R275 cover the perp versions |
| Cross-venue funding arbitrage with a price-spread entry filter | R275 cross-venue funding spread carry (C14 in batch 1), R278 forward |
| "Funding edge only when it is negative" | R273 extreme-funding onsets, long and short, NULL (best: long 72 h after negative funding, t 2.39, reality-check p 0.87); R274 shorts after negative onsets NULL; both in batch 1 (C12a-d) |
| Unlock calendar: low float plus large unlocks means sellers | R265 unlock short (gate 0 pass), R266 forward, C01 in batch 1 |
| Pairs and stat arb | R250 pairs NULL; M298 adds the PCA residual version |
| VPIN and order-flow toxicity | M085 BLOCKED (disputed as mechanical; needs trades data) |
| Pre-FOMC drift | R242 NULL |
| "Look for a change in state, not the state" (ex-Two Sigma) | R234 positioning impulse NULL |
| Prediction-market prices as signals | M098 BLOCKED |
| Equal-weight rebalancing against buy-and-hold | R232 NULL |

**Points for how the lab works (not rules):**
- **Sharpe by style,** from practitioners on HN: HFT 10 and up, mid-frequency 4-5, stat arb 1-2, long-short and macro 0-1.
  A daily crypto book that shows Sharpe 3+ in a backtest is more likely a bug or overfit than an edge.
- **Edges decay fast.** One team went from $500k a day to zero in six months; equity stat arb is said to have died
  after the uptick-rule change. Every forward lane needs a stop rule (the lab's sequential decisions, R221, and M287).
- **Rebates decide market making.** An equity market maker's gross is often under 1 bp before rebates. MEXC's 0-fee
  maker contracts help only a rule with gross edge (arXiv 2502.18625: maker fills are adversely selected).
- **Insider flow on prediction markets.** HN threads document new accounts winning on well-timed geopolitical bets.
  This argues against trading thin prediction markets on public news.

## Next
- Test the cheap held-data rows first. Each one is a frozen family PREREG, with one registry row per run.
  - **M298 is done: R287 `pcares_v1`, NULL** (24 variants, reality check p 1.00). Hourly residuals revert by about
    +9.5 bp a day gross in the steadiest variants, but hourly rebalancing turns the book over 2.6-11 times a day, so the
    break-even cost is at most 3.5 bp per side against 7.
  - **M295 is done: R297 `fundgate_v1`, NULL** (4 trials). Up-day funding was lower in 2026 than in 2022, but it
    tracks the plain funding level, and neither it nor the funding slope leads the market at 7 or 30 days.
  - Next is M290 (once release calendars and 1-5 min klines are fetched).
- Recorders where history cannot be bought: the Deribit option chain (M289, M300) records hourly since 2026-10-21;
  Upbit/Bithumb wallet status (M294) is still to do.
- The prop trader's comment is followed up in `docs/VENUE_STRUCTURE.md`: a fee map, a Lighter book recorder (0 fees
  through the API) and a plan for the three edges.
- Reddit keeps paging in the background; rerun `mine` and add any new idea as a row.
