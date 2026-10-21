# The owner's TikToks, and what traders from trading firms say on long, little-watched shows (2026-10-21)

The owner's ask: watch three TikToks, dig for deep videos with few views by people who worked at trading firms, find
the best things to trade (news "like a Bloomberg" included), and stop relying on one strategy. This note says what the
media says, where the lab already tested the same idea, and what is new. Nothing here is a result: every idea below is a
claim until a frozen lane tests it.

## The three links (two videos)
`vm.tiktok.com/ZGdCbbYU8` and `vm.tiktok.com/ZGdCbBNnE` resolve to the same video. Download: yt-dlp 2026.10.10 with
browser impersonation, no login. Speech: faster-whisper "small" on CPU. Media stayed in the session scratchpad.

**1. @hyperbolic.ai, 2026-10-19, 96 s, 56.7k views: Jordi Visser** (former president and CIO of Weiss
Multi-Strategy Advisers, a $4B fund).
- He sets up five AI agents, each with one job:
  - one on fundamentals and company news;
  - one on X (sentiment, bull and bear cases, catalysts);
  - one on technicals;
  - two more he does not detail.
- His own filter, verbatim: "I only care about them if they're above the 200 day moving average and the 200 day moving
  average is pointed upward. Then what I want to look for is situations where the rate of change has reset... I want
  to be riding a trend that lasts for three months."
- And: "just paper trade for a period of time, develop a process."
- The caption adds a Brazilian day-trader study: 97% of those who kept going 300 days or more lost money.

**2. @ojrenick (Stay Solvent), 2026-10-20, 280 s, 26.8k views: VIX and VVIX.**
- On Friday 2026-10-16, VIX rose to 22 (highest since June) and VVIX to 120 (highest since April).
- The VIX futures curve went into backwardation (front month above the next).
- Cboe's weekly commentary called it "a scramble for downside hedges".
- His claim: "VIX is a mean reverting asset... the combination of VIX and the VIX futures curve for moments of extreme
  blowout and panic... just don't often last". In other words, a short-term bottom signal for stocks.
- Rule of 16: VIX 16 means about a 1% daily move in the S&P 500.

## The dig
**YouTube.**
- `scripts/dig_videos.py search` ran 52 queries: people from Jane Street, Citadel, Optiver, SIG, Jump, DRW, Two Sigma,
  HRT, Wintermute, GSR and others; news and event trading; mechanisms such as basis, funding, liquidations, VIX term
  structure and order books.
- That found 1,242 videos. `pick` kept 159 that are at least 15 minutes long, have at most 30,000 views and name a firm,
  a role or a mechanism. 47 of them name a firm.
- The list is in `data/videos/pick.csv`. Lowest views first: "Options Talk w/Wintermute" (26 views), GSR's Joshua
  Riezman (50), GSR's Alex Taaffe (97), "From Goldman's Algo Desk to a Crossover Fund" (220), Wintermute's Yoann
  Turpin (447), DRW's Don Wilson (764), ex-Jane Street Agustin Lebron (941), ex-Renaissance Robert Frey (1,012).
- **YouTube refuses caption downloads from this machine** (HTTP 429 and "Sign in to confirm you're not a bot"). Search
  works; captions need a logged-in browser, which this lab does not use.

**Podcasts.** The same people are on podcast feeds, and several feeds publish full transcripts.
- `scripts/dig_podcasts.py` reads 23 shows (10,586 episodes, in `data/videos/episodes.csv`):
  - Odd Lots (1,288 transcripts);
  - Top Traders Unplugged (350 transcripts);
  - Volatility Views;
  - Flirting with Models;
  - Chat With Traders;
  - Odds on Open;
  - Rekt Radio;
  - Empire, Unchained and others.
- 165 transcripts were read by keyword (`python scripts/dig_videos.py grep --words ...`).
- Six crypto episodes without a transcript are being transcribed locally (`scripts/transcribe_audio.py`):
  - a Wintermute trader;
  - the 2025-10-10 liquidation cascade;
  - Doug Colkitt on liquidations;
  - an ex-Jane Street trader on finding edge;
  - Jane Street's Thomas Uhm on crypto versus equities;
  - an ex-Citadel quant.

## What the practitioners say, and where the lab stands on it
| # | Claim (source) | Where the lab is | Status |
|---|---|---|---|
| 1 | **One strategy is the wrong unit.** "The thing that really matters is the correlation": with average sleeve Sharpe 0.75, pairwise correlation 10% caps a multi-PM book near 2.4, and 20% near 1.6 (Odd Lots, "The Math That Explains How Multi-Strategy Hedge Funds Make Money", 2024-10-07). | R228 and R253 mixed books A, B and X2, which are all the same flow family: NULL. No book yet combines different families. | **New lane M281** (below) |
| 2 | **A crypto multi-PM fund runs arbitrage across venues, cash-and-carry and funding; 90% of its volume is maker, with rebates.** CME basis was still 11-12% annualized at times in 2024-25 (Top Traders Unplugged OI14, Nickel Digital). | R275 cross-venue carry is the lab's strongest gate-0 result and runs forward (R278, R279). Dated-futures basis is held (`data/coinm_1h`, M170). MEXC has 0 maker fee. | Building (2020 batch) |
| 3 | **Regional premiums**: Korea traded up to 50% over the world and Japan 15% in 2017-18. The barrier was banking, not finding it (Odd Lots with Sam Bankman-Fried, 2021). | Korean premium per coin as a factor: R282 NULL (M268). An arbitrage needs KRW banking, which the owner does not have. | Tested (factor NULL) |
| 4 | **Narratives and news pegs drive small coins; stop runs** wick below a recent range low, then pump; cut a trade at once if it does not react (Odd Lots, "What a 'Degen' Crypto Trader Really Does All Day", 2024). | ICT sweep detectors: confirmed gross, NULL net (R185-R187, M110). The Wyckoff spring (sweep plus reclaim) is still untested (M208). | Queue M208 |
| 5 | **Trend pullback (Visser):** above a rising 200-day average, after the rate of change resets near zero, held about 3 months. Trend has worked over 137 years of data (Top Traders Unplugged SI416). | Daily trend lanes were NULL net: R229 (six coins), R242 (vol-managed, full universe). Visser's entry, a pullback inside a long trend with a 3-month hold and low turnover, was not one of them. | **New lane M277** |
| 6 | **VIX panic bottom (Stay Solvent):** VVIX spike plus VIX above VIX3M marks a short-term low. | VIX-spike reversal lanes were NULL out of sample: R239 and R241 (M197, M218, M226). Short vol in contango: R241, t 1.7-2.4 in every window but 45-66% drawdowns (M224). VVIX and the curve shape as triggers are untested; Cboe history now held (`data/cboe`). | **New lane M278**, low prior |
| 7 | **Headlines whipsaw; markets often look through them** (Odd Lots, "This Is How Big Money Is Trading the War in Iran", 2026-03-26: futures up despite a rejected ceasefire). | M096 (news leads price) was BLOCKED for lack of an archive. Headline history cannot be backfilled honestly, so the recorder started today (`data/news`, 22 feeds, first-seen times). | **Recording, M279** |
| 8 | **Exchange listing notices** move coins (TheTie 2026: front-loaded). | Binance notices: R271 family. OKX's API keeps only about 100 recent listing notices, so the recorder keeps them from today. | **Recording, M280** |

## What could be the best things to trade (ranked by evidence, not by how good the story sounds)
1. **Cross-venue funding carry** (R275, forward R278/R279, 2020 batch C1): many coins, market-neutral, paid by a known
   mechanism, maker-friendly.
2. **Event shorts with point-in-time notices**: unlocks (R265/R266), delistings (R267/R268), Monitoring Tag
   (R269/R270), announcements (R271/R272). Each is small; together they are many uncorrelated bets.
3. **A cross-family book of 1 and 2** (M281). This is the owner's "one strategy limits us".
   - With N sleeves of Sharpe S at pairwise correlation ρ, the book's Sharpe is S·√(N / (1 + (N−1)ρ)).
   - At S = 0.75 and ρ = 0.1:
     - ten sleeves give 1.72;
     - the days needed for an expected t of 2 fall from about 2,600 to about 490.
   - It only works with sleeves whose own expected net is positive: ten nulls add up to a null.
4. **Slow trend pullback** (M277) and **VIX panic** (M278): testable now on 2001-2026 index and 2021-26 crypto history.
   Both have low priors from R229/R242 and R239/R241, and both are cheap in trades.
5. **Headline reaction** (M279, M280): needs about 90 days of recording before a frozen family can read it.

## What not to take from these videos
- 97% of persistent day traders lost money (Visser's caption), and the Odd Lots "degen" trader describes fast discretion.
  The lab's scalping axis (#73) stays an option, judged on MEXC order-book costs (R224).
- An AI agent reading news is a monitoring tool, not an edge. The edge, if any, is in the rule it applies. That rule is
  what a frozen lane tests.

## Files
- **Code:** `scripts/dig_videos.py` (search, pick, subs, grep), `scripts/dig_podcasts.py` (episodes, text),
  `scripts/transcribe_audio.py`, `scripts/record_news.py`, `scripts/fetch_cboe.py`.
- **Data (gitignored):** `data/videos/` holds hits, picks, episodes and transcripts. `data/news/` holds the headline
  record. `data/cboe/` holds the vol curve.
- **Rows:** `registry/methods.csv` M277-M281.
