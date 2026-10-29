# The owner's two reels: what the media actually says (2026-10-19)

How it was obtained:
- **Download:** `yt-dlp` 2026.08.19, with no login. The public page itself is a login shell.
- **Speech:** `faster-whisper` "small" on CPU, with audio decoded by ffmpeg.
- **Frames:** extracted at 3 frames per second.
- The files stayed in the session scratchpad and were not committed.

## Reel 1: instagram.com/reel/DcOhWbqm3vK (Git Radar, @git.radar, 2026-08-19, 71.8 s)
- **Caption:** "Production-grade Rust-native trading engine with deterministic event-driven architecture
  https://github.com/nautechsystems/nautilus_trader".
- **Speech** (English, language probability 1.00):
  - "This project, Nautilus Trader, is a high performance engine that handles all the complex math and speed required
    to trade stocks or crypto at a professional level."
  - "It's built in a language called Rust…"
  - "it lets you test your strategy using historical data before you risk a single cent in the real market. It ensures
    that the exact same logic you used for your experiments works perfectly when you start trading with real money."
  - "…it has already earned 26,314 stars…"

## Reel 2: instagram.com/reel/DcgZhLyiZ3o (Filip Gajko, @iclosegreen, 2026-08-26, 6.3 s)
- **Speech:** none. Whisper finds no segments; the track is music.
- **Frames:** one title card, "6 github repos that run a hedge fund from your laptop", over a desk of trading screens.
- **Caption:** it describes six roles, does not name the repositories, and says "comment 'GIT' and i'll send you the
  list". The names go out by direct message, so they cannot be recovered from the media.
- **Roles and the most likely repositories** (inference, matching Codex's `docs/TOOLS_FROM_REELS.md` on
  `codex/forward-lane-completion`):

| Role | Most likely repository |
|---|---|
| Candle foundation model | Kronos |
| scikit-learn portfolio optimizer | skfolio |
| Rust engine | NautilusTrader |
| Market-making bots on 140+ exchanges | Hummingbot |
| Crypto bot with ML retraining | Freqtrade / FreqAI |
| Natural-language research workspace | Vibe-Trading is the closest fit |

- **The caption's one engineering claim worth keeping:** "the ai in these repos never sends orders. it forecasts, the
  optimizer sizes, the engine executes."

# The owner's three reels of 2026-10-21

Obtained the same way: `yt-dlp` without a login, `faster-whisper` "small" on CPU, frames at 3 per second. The media
stayed in the scratchpad. Whisper's mishearings are corrected in brackets.

## Reel 3: instagram.com/reel/DdSBAFqOlg7 (vince.quant, 2026-09-14, 82 s, 1,275 likes, 17 comments)
- **Caption:** every systematic strategy is a function of the past path. Rough path theory describes the path by its
  signature (the sequence of iterated integrals). Hambly and Lyons (2010) proved the signature determines the path,
  and any continuous function of the path is a linear combination of signature terms. So moving-average crossovers,
  RSI, Bollinger bands and the Kalman filter are all close to such a combination. Futter, Horvath and Wiese
  (Quantitative Finance, 2025) make this a portfolio method.
- **Speech:**
  - "Every trading rule is a function of the path… a moving average, an RSI, a Kalman filter, each one designed by
    hand."
  - "Level 1 is where it ended up, level 2 the areas it swept, the shape of a trend, or which of two assets moves
    first."
  - "[Futter], [Horvath] and [Wiese] regressed a momentum strategy on the signature. The R-square climbs from 66% at
    order 1 to 98% at order 11."
  - "The best weights have a closed form, the inverse covariance of the terms times what each contributes to profit…
    with only the constant term it is the plain [Markowitz] portfolio."
  - "The hard part is estimating it: the expected signature is noisy and the paper only tests it on a few ETFs."
- **Lab:** M299 (UNTESTED). The reel is honest about the weak point. The R-squared shows that a signature can
  imitate an indicator, not that the indicator makes money. It is a price-path learner, so it inherits the record of
  R263 (5,472 chart rules, one survivor) and the prop trader's "nothing based on OHLC worked". It goes in as one
  learner in the ML-ranker family, not as its own lane.

## Reel 4: instagram.com/reel/DeuGt7VgpWJ (aleksrosme, 2026-10-20, 47 s, 390 likes, 15 comments)
- **Caption:** "10/20 Break of 713GEX + Call Heavy Premium = 120POINTS Trade".
- **Speech:**
  - "As market opened today we saw SPX staying under negative gamma after respecting this major put spread seller."
  - "QQQ reclaimed [the] 713 [GEX] level for my pre-market plan… QQQ went into [call heavy] premium which confirms
    bullish sentiment."
  - "Looking at the order flow… bunch of sellers trying to step in combined with bullish imbalances… we retest 713 on
    QQQ aligned with [the daily value] area high, which was my confirmation to take this trade for 6R."
- **Frames:** a QQQ chart with a "Net Drift (Premium)" panel and marked GEX levels.
- **Lab:** one winning trade with a discretionary entry (GEX level, option premium, order-flow imbalance, volume
  profile). Nothing here can be counted; the parts that can be measured are M300 (gamma regime and levels) and M264
  (order-flow imbalance).

## Reel 5: instagram.com/reel/DeqPhIDt7j8 (nickelninjatrades, 2026-10-19, 79 s, 679 likes, 119 comments)
- **Caption:** "Comment MISS to get first priority for Gamma Exposure University." The video sells a course and a
  heatmap site.
- **Speech:**
  - "Every morning before I even look at a chart, I pull up the [Gamma] Exposure Heatmap… This map shows me exactly
    where dealers are positioned."
  - "I simply want to wait for price to reach one of my [Gamma] Exposure levels… make sure that the EMA sequence is
    aligned… starts to flag at that major… level… I need volume to come in on the break of the flag."
  - "My [Gamma] Exposure level is my stop-loss and I target the next [Gamma] Exposure level below."
- **Lab:** the rule is concrete enough to test once gamma history exists: wait for a GEX level, require EMA
  alignment, a flag and a volume break, stop at that level and target the next one. "Dealers are positioned" rests
  on an assumption: the heatmap guesses which side dealers hold. M300 keeps the call and put sides apart so either
  convention can be tested.

## What the three reels changed
- **A recorder.** No free archive keeps Deribit open interest by strike over time. `scripts/record_deribit_chain.py`
  now saves the full BTC, ETH and USDC option chains every hour (4,852 options in the first snapshot), and
  `gex()` turns a snapshot into gamma per strike. M175, M289 and M300 can be tested once enough hours accumulate.
  The regime question (a) needs a few months of hours. Expiry pinning needs more: there is one Friday expiry a week,
  and only 12 month-end expiries a year.
- **Two rows:** M299 (signature trading) and M300 (dealer gamma regime and levels).
- **No result.** None of the three reels shows a track record that can be checked.

# The owner's reel of 2026-10-21 (late), sent with "research QuantData"

Obtained the same way: `yt-dlp` without a login, `faster-whisper` "small" on CPU, and frames at 1 per second. The
media stayed in the scratchpad.

## Reel 6: instagram.com/reel/DevaMerNUk_ (julias.algos, 2026-10-21, 53 s, 1,325 likes, 19 comments)
- **Caption:** "What happens when a market maker encounters a trader or algorithm with more information than the
  average trader? Toxic order flow is when a market maker gets picked off, buying right before a crash or selling
  right before a spike."
- **Speech** (English):
  - "Why do high-frequency trading firms spend $300 million just to shave 1 millisecond off their execution time?
    Most people think that HFT firms buy microwave towers just to beat retail traders to the punch. But the reality
    is exactly the opposite. Speed is defense against a concept called order flow toxicity."
  - "Market makers are constantly quoting prices to buy and sell, but sometimes they face informed traders,
    algorithms, or news-driven funds that know something that the market maker doesn't… The market maker gets
    picked off, buying before a crash, or selling before a spike."
  - "To survive, they track a metric called VPIN to track order flow toxicity. When the math shows that informed
    traders are entering the market, then market makers must pull back and cancel their quotes right away."
- **Frames:**
  - the Chicago to New Jersey fiber and microwave routes (6.6 ms against 5 ms);
  - a "retail flow / passive LPs / active LPs / arbitrageurs" meme;
  - an adverse-selection chart ("you buy at 500, price moves lower after execution");
  - the VPIN formula, Σ|V_B − V_S| / Σ V over n volume buckets, with "ranges from 0 to 1";
  - the flash-crash chart of E-mini price against VPIN (Easley, López de Prado and O'Hara).
- **Lab:**
  - Adverse selection is real: maker fills in R193 and arXiv 2502.18625.
  - The metric is not. **R291 `vpin_v1` is NULL.** Built from Binance's exact taker sides, VPIN worsens 1-hour
    volatility forecasts out of sample on BTC, ETH and SOL perps. The papers' bulk-classified VPIN is mostly volume.
    Plain volume flags crash hours far better (about 40x top against bottom decile, against 3x).
  - The reel shows the 2010 chart without the Andersen and Bondarenko rebuttal.
  - Write-up: `experiments/vpin_v1/FINDINGS.md`, `docs/QUANTDATA.md` section 3.

# The owner's four reels of 2026-10-22, sent with the `lse-data` repository

Obtained the same way: `yt-dlp` without a login, `faster-whisper` "small" on CPU, and frames at 1 per second. The
media stayed in the scratchpad.

## Reel 7: instagram.com/reel/Derh59yMyv8 (quant_labde, 2026-10-19, 96 s, 3,761 likes, 47 comments)
- **Caption:** "Are these 90%+ winrate bots actually safe?"
- **Speech** (English):
  - "Bots that almost never lose get sold every day. So I built one and ran it on seven years of gold… Price drops, it
    buys more. Drops again, it doubles up. Then it waits until the whole pile is back in profit. No stop loss."
  - "98.9% of its cycles closed in profit… Then came September 2023. Gold kept falling. The bot kept buying. One
    single cycle. About $820,000 gone… Over seven years, the account was wiped out 14 times."
  - "So I took the doubling out. Same size on every buy. Now 99.9% of cycles won. But the last one never came back.
    When the data ended, it was still open. $140,000 underwater."
  - "Our own NASDAQ bot… wins only 56.4% of its trades, but every trade has a stop. Its worst drawdown since 2019,
    26.6%… A win rate tells you how often you win, not what one loss costs you."
- **Frames:**
  - an XAUUSD M5 grid bot, 2019-2026;
  - "COMBINED BASKET UNDERWATER", with position size stepping 1x → 2x → 3x;
  - the equity curve of 14 wipeouts, each a slow climb then a vertical drop;
  - "GOLD 1,330 → 4,000 in this test";
  - "WIN RATE ≠ SAFETY".
- **Lab:**
  - Nothing new to test. The reel is its own test, and its lesson is already a lab rule:
    - martingale and size escalation are on the prop "never do" list (`docs/PROP_FIRMS.md`);
    - no lane is ranked by win rate;
    - gates read net PnL, the worst drawdown and cost sensitivity (`docs/GATES.md`).
  - Its fair point: even without doubling, a grid with no stop carries an open loss the win rate hides. Here the
    loss was −$140k at the end of the data, after gold tripled.
  - The NASDAQ bot's numbers (56.4%, −26.6%) are shown without costs, a period split or out-of-sample dates. They
    cannot be checked.

## Reel 8: instagram.com/reel/DeF5_5yPtDb (telonicstrading, 2026-10-05, 46 s, 1,069 likes, 1,864 comments)
- **Caption:** "I built a machine learning model that predicts the next day's efficiency ratio. Comment 'MODEL' to
  see what it predicts every day."
  - The 1,864 comments are mostly the word "model". The reel is a sign-up funnel.
- **Speech** (English):
  - "Instead of trying to predict direction, the model predicts the next day's efficiency ratio… A high ratio means
    price moved clean in one direction while a low ratio means price chopped back and forth."
  - "The model makes its predictions with a logistic regression that weights 15 different measurements of how
    price has been moving."
  - "High efficiency days performed the best while the low efficiency days made about a third of the money per
    trade. So I added a gate that skips those low efficiency days entirely and that one change improved almost every
    performance metric… that improvement held on two years of data the models never seen."
- **Frames:** "15 measurements, 15 learned weights", scored from "toward chop" to "toward trend":

  | What the market just did | Weight | What it's been doing lately | Weight |
  |---|---|---|---|
  | realised volatility | −0.204 | days of chop in a row | +0.065 |
  | today's efficiency | −0.198 | 5-day efficiency | +0.044 |
  | 20-day efficiency | −0.036 | 10-day efficiency | +0.013 |
  | variance ratio | −0.101 | 20-day mean efficiency | −0.024 |
  | false-breakout rate | +0.182 | yesterday's efficiency | −0.200 |
  | distance from the 50-day | −0.198 | efficiency 2 days ago | −0.135 |
  | | | change in volatility | −0.119 |
  | | | chop share, 5 days | +0.009 |
  | | | chop share, 10 days | +0.098 |

  No strategy, threshold, AUC, trade count or equity curve is shown.
- **Lab: R293 `er_v1` is NULL** (`experiments/er_v1/FINDINGS.md`).
  - **The setup:**
    - the same 15 measurements on BTC, ETH and SOL perps;
    - a logistic regression fitted on 2021-23 and read on 2024-26;
    - the gate applied to a first-hour trend rule fixed in advance.
  - **The forecast:**
    - tomorrow's efficiency is weakly predictable (AUC 0.537);
    - today's efficiency alone does as well (0.536);
    - our fitted weights agree with the reel's in sign 12 times out of 15.
  - **The gate:** it made each trade worse (−3.3 bp). The rule lost either way.
  - **Post hoc,** the first UTC hour reversed in both windows. That is M315, for unseen data only.

## Reel 9: instagram.com/reel/Dcdew99nERj (datasciencefoundry, 2026-08-25, 175 s, 11,818 likes, 40 comments)
- **Caption:** "These are 8 of the most important supervised machine learning algorithms you should know."
- **Speech** (English): a lesson on film ratings:
  - linear regression ("minimizes the sum of the squared errors");
  - logistic regression ("squashes that weighted sum through an S-curve… log loss");
  - k nearest neighbours;
  - the support vector machine ("the widest margin");
  - the decision tree;
  - the random forest ("averaging them reduces overfitting");
  - gradient boosting ("each new tree corrects the error that is still left");
  - XGBoost ("regularization… handles missing values… trains in parallel");
  - the neural network.
- **Lab:** nothing to test. It is a general lesson with no trading claim. All eight model types are standard:
  - the lab fitted a ridge logistic regression in R293;
  - the old session fitted a ridge and GBM composite (R162, `docs/OLD_SESSION_EDGES.md`).

## Reel 10: instagram.com/reel/DeAhvMBI5ET (machinelearningtogo, 2026-10-02, 112 s, 5,964 likes, 33 comments)
- **Caption:** "Machine Learning from Scratch, part 22: the idea behind XGBoost." Its example is 500 made-up bank
  customers: train on 400, test on 100, 200 rounds at learning rate 0.01.
- **Speech** (English):
  - "XGBoost builds many small decision trees, one after another, and each new tree fixes the mistakes the earlier
    ones still make… After 200 trees the model gets 84 of the 100 new customers right."
  - "XGBoost adds three things on top: a penalty for trees that grow too complicated, smarter steps that also use how
    the slope bends, and an engineering that makes it very fast. That is why it wins so often on table data."
- **Lab:** nothing to test directly.
  - Boosted trees win on tabular data whose signal is stable, like credit and churn.
  - Market returns are mostly noise, with a signal that drifts between years.
  - The old session's rankers found nothing (`docs/OLD_SESSION_EDGES.md`, M042):
    - the 390-cell megascan, 0 of 390 (R161);
    - the ridge and GBM composite, rank IC 0.01-0.04 (R162).
  - A boosted model on the R293 features would be one more trial on the same weak target (AUC about 0.54). It
    would not answer a different question.
  - **If the ML family (M042-M044) is run, it runs as one frozen family with purged walk-forward,** as the plan
    says, with the trial count of every model and setting.

## What the four reels changed
- **One test:** R293, NULL. The reel's method does not carry over to crypto perps with this rule.
- **One new seed:** M315, the first-hour fade, for unseen data only.
- **No new rule:** reel 7's lesson (win rate is not safety) is already in the gates and the prop "never do" list.
- **The two ML lessons** say nothing about markets. The old session's GBM tests stand.
- **The repository** sent with them (`lse-data`) is assessed in `docs/DATA_SOURCES.md`. It is a candidate source
  that needs the owner's key.

# The owner's TikTok and four reels of 2026-10-22 (afternoon)

Obtained the same way. The reels came through `yt-dlp` without a login. Its TikTok extractor failed on this post, so
the video address came from the public page's own data, with the page's cookies. Speech is transcribed with
`faster-whisper` "small" on CPU, and frames are taken every 2 seconds. The media stayed in the scratchpad.

## Reel 11: instagram.com/reel/DXrQvB0EYz7 (hooper.algo.fxx, 2026-04-28, 1,642 likes, 77 comments)
- **Speech:**
  - "This is the Oxford Strat, and this is where I get ideas on how to build algorithms. There are about a hundred on
    this page."
  - "Out of 100 strategies that I build, 93% will be unprofitable, leaving only seven with an actual viable edge. The
    only way to really know is to build hundreds if not thousands."
- **Frames:**
  - the site's "Reviews of trading strategies (public domain)", rated A/B/C/D. Examples: 2-bar narrow range, 3-bar
    momentum, Hikkake, Hook, Oops, narrow range 4/7, TD Sequential, Wyckoff, Keltner 3-phase, Hull and zero-lag
    moving-average filters, Aroon, ADX filters;
  - his MT4 tester listing FX expert advisors: "TokyoRangeBreakout", "FirstXMinBreakout", "EngulfingRoundNumber",
    "DoublePinBar", "GOLDEN WEEKEND".
- **Lab:**
  - **The 7% is the lab's own experience.** About 70% of its rounds are NULL, and nothing has passed gate 1.
  - **Building thousands only works with the multiplicity counted.** R263 tested 5,472 chart strategies as one
    family with a reality check, and the program reads every result against `registry.program_trials()`.
  - **The site is a harvest source** for the plan's "remaining chart and TA rules not in R263". Most of its rules
    are covered by R185, R243 and R263. The pattern rules not yet coded (Hikkake, Oops, NR4/NR7, TD Sequential) go
    into the next chart family as one frozen PREREG, not one by one.

## Reel 12: instagram.com/reel/DYWqgGkOyE1 (deltatrendtrading, 2026-05-15, 5,433 likes, 134 comments)
- **Caption:** "This is what it looks like to begin exploring a trading idea properly, programmatically,
  mathematically."
- **Speech:**
  - The rule: "in regular trading hours only, we mark out the first 15-minute bullish order block, and then on the
    1-minute timeframe, on a tap of that order block, we enter a long trade, targeting a fixed multiple of risk with
    the stop below the bottom of the order block."
  - "Over five years of Nasdaq front-month data… the bootstrapped 95% confidence interval for trade return by day
    spans zero."
  - "If you compare the actual order block timing versus a randomized entry model… a p-value around 0.01 for mean R."
  - "If we instead wait for price to move down to the bottom 25% of the box… with a 1.5R target." The parameters came
    from his training set. "On the test set [from about 2025]: 199 trades, 0.339 mean R per trade… the confidence
    intervals are fully positive."
  - "It drastically underperforms buy and hold."
- **Lab:**
  - **His method is the lab's:** a fixed rule, a null of randomized entries, a bootstrap and a held-out set. His
    test set is small (199 trades), and the 25% entry and 1.5R target were tuned on the training set.
  - **The rule is new to the lab at 1 minute on an index.** R185/R186 tested ICT order blocks on crypto 1h bars:
    gross only, below cost.
  - **It can be traded where the owner trades.** MEXC lists NAS100_USDT, SPX500_USDT and US30_USDT perps, open since
    2026-01-29, with a 0 maker and 2 bp taker fee. The LSE vault holds NAS100, SPX500 and US30 ticks from 2023-02.
    Queued as **M320**, with the M206 opening-range break in the same family.
  - **Unseen days exist:** everything after the reel's date (2026-05-15) is unseen by its author. LSE's index bars
    must first match an independent close (`docs/DATA_SOURCES.md`).
  - **A second lead came from checking the instrument (M321).** These index perps trade through the weekend on a
    Hyperliquid-sourced price while the index and CME futures are closed. Does the perp's move in closed hours
    revert at the reopen? M051 (do TradFi perps track their underlying) can now be tested with LSE's reference ticks.

## Reel 13: instagram.com/reel/DaNNDObtRxN (andreacimi.trading, 2026-06-30, 9,726 likes, 174 comments)
- **Caption:** "Trading strategies tier list w/ market maker."

| Strategy | His tier | Lab |
|---|---|---|
| Opening-range breakout | A, "backed by proper research" | M206 UNTESTED; now in M320's family on index perps |
| VWAP mean reversion | A | M207 TESTED (NULL), M305 R290 NULL |
| Bollinger band mean reversion | D, "lagging" | R243 / R263 NULL |
| VIX mean reversion | S, "if you time it incorrectly, it's going to be extremely painful" | R239/R241 (t 1.94 then −0.05), R283 vixpanic |
| Post-earnings drift | A, "small caps not followed by analysts" | M222: stocks, data not free; not a perp |
| Option premium selling | A, "large funds overpay for protection" | M138 R209 NULL (DVOL timing), M214/M224 (short-vol timing) |
| ICT unicorn | F, "I tested it… there was no edge" | M110: R185-R187 below cost |
| Martingale | D | On the prop "never do" list |
| Reverse martingale (size up winners, cut losers) | common practice | `docs/SIZING_EVIDENCE.md`; R281 confidence-sized carry |
| Trendline bounce | F, "completely discretionary" | No rule to test |

- **Lab:** His A tier is the academic list, and the lab has tested most of it. Only the opening range on a liquid
  index at 1 minute is untested. It is now M320.

## Reel 14: instagram.com/reel/DdRchNXxHKW (max_kelleyy, 2026-09-14, 1,493 likes, 2,621 comments)
- **Caption:** "Trading with AI isn't easy, but these repos will help. Comment 'stack' and I'll send them over." Most
  of the 2,621 comments are the word "stack".
- **Speech and frames:** "five repos to create an AI hedge fund". Four are shown:
  - OpenBB (73k stars, the data layer);
  - Investor Skills by Questflow (about 1.9k stars, "macro theses of top investors as agent skills");
  - TradingAgents by Tauric Research (the agent framework);
  - Vibe-Trading (the execution layer, "13 brokerages").
- **Lab:**
  - **These are tools, not rules (M165).** TradingAgents' own paper tested 3-5 US stocks over one quarter of 2024
    (M102, BLOCKED: it needs a dated news archive).
  - **An LLM's knowledge leaks the future:** a model trained after the test window "knows" the outcome. Any such lane
    runs forward only, with frozen prompts and a pinned model (M312).

## TikTok: tiktok.com/@ojrenick/video/7699222826628238606 (2026-10-21, 119 s, 12.9k plays, 867 likes)
- **Caption:** "upward and onward #stocks #optionstrading". He is the creator of one of the owner's TikToks of
  2026-10-21 (`docs/VIDEO_DIG.md`).
- **Speech:**
  - "New rule number one of trading: ask not why the market is going up. Ask why should the market be down…
    Technicals… we're in an uptrend. Fundamentals, that's earnings… in an uptrend."
  - "We saw a bunch of call buying happen in Tesla, like above the ask, which means they were scrambling to buy calls
    ahead of the report… SpaceX hit above the implied move… those options looked pretty cheap."
  - "That VIX rule of 16 suggests VIX should have been coming down… we were getting less than 1% moves despite the
    VIX being higher."
- **Lab:**
  - **"Ask why it should be down":** a long bias while trend and earnings rise. That is time-series trend, tested
    many times (R284 trendpull, R263). For crypto perps the lab has no earnings analogue.
  - **The rule of 16 is a known identity.** VIX/16 is roughly the S&P's expected daily move in %, because √252 ≈
    15.9. The crypto analogue is DVOL/19.1 (√365).
    - When daily moves stay below it, implied volatility tends to fall. That is the volatility risk premium.
    - The lab measured it (M215) and timed it on Deribit (M138, R209 NULL).
    - It is not new.
  - **Call buying above the ask before a report** is option flow. The lab tested it on Deribit (R295, M311/M313),
    and QuantData-style tests on SPY are possible with LSE's option prints (`docs/QUANTDATA.md`). It is not a perp
    rule.

## What the five clips changed
- **Two new queue rows:**
  - **M320:** the opening order block and opening range on US index perps, at 1 minute.
  - **M321:** the closed-hours gap on MEXC's 24/7 index perps.
  - Both trade on MEXC at 0 / 2 bp. Both need LSE's index ticks and MEXC's index-perp klines.
- **One harvest source:** the Oxford Strat's public-domain pattern list, for the next chart family.
- **No new rule from the tier list, the repos or the TikTok.** Each item maps to a tested or queued row above.

## Reel 15: instagram.com/reel/DejYIVkhcLQ (goatfundedtraderhq, 2026-10-16, 9,008 likes, 142 comments)
- **Who:** Goat Funded Trader, a prop firm. The clip is a skit: a man in a gold mask pitches his method to a panel.
- **Speech:**
  - "I use Malaysian support and resistance… People in Malaysia tweet that."
  - "I go in the four hour, there's a buy and a sell, where the buy has closed, on top of that, and where the sell
    opens, that's my resistance. That strategy makes millions."
  - The panel: "Bunch of BS."
- **Comments:** mostly jokes; "MSNR is the best", "msnr, am trying on that". No numbers and no test.
- **The method (MSNR):** from LuxAlgo's "Malaysian SnR" page and the TradingView script "Malaysian SnR [by DanielM]".
  - **Levels come from candle bodies, not wicks.**
    - **A-level:** the close of a bullish candle followed by a bearish one, a line-chart peak.
    - **V-level:** the reverse, a line-chart valley.
  - **Freshness:** a level is "fresh" until a wick touches it. The method trades the first touch.
  - **Gap levels:** the method also uses gaps between one candle's close and the next one's open. 24/7 perps have
    none.
  - LuxAlgo publishes the rules but no test.
- **Lab:**
  - **It is a testable rule:** fade the first touch of a fresh level, or follow a 4-hour close through it. That is
    **M323**, frozen as **R306 `msnr_v1`**: 12 crypto books (fade or break × a level life of 5 or 30 days × a 24 h,
    72 h or 1:2 ATR bracket exit) on the top 50 Binance perps.
  - **The secondary read** covers Binance gold and silver and MEXC's FX, metal and index perps. It is report only,
    since most of MEXC's index history starts in 2026.
  - **Priors are against it.**
    - R243's pivot breaks and fades lost.
    - R246's round-number levels carried only the generic one-hour reversal.
    - R248 closed the pivot family.
    - R263's 5,472 chart rules found nothing.
  - MSNR's two differences are the body-based level and the freshness rule. R306 tests exactly those.

## Reel 16: instagram.com/reel/DeKFE8OEq-i (iamzarch, 2026-10-06, 388 likes, 28 comments; French)
- **Who:** "The Candidate" by The Finance Games, episode 1, a mock trading interview with buzzers. A candidate is asked
  about the volatility smile.
- **Speech (translated):**
  - "25-delta put, 25-delta call, do you know what that means?"
  - "Which is more expensive in terms of vol? The put costs more than the call."
  - The candidate starts on put-call parity (C − P = S − K·e^(−rT)) and its assumptions: no arbitrage, European
    options.
  - "The smile is fundamental… it has to come at once."
- **Lab:**
  - **The 25-delta risk reversal** is the call's implied vol minus the put's at the same delta. A rich put (negative
    RR) is the equity-index norm.
  - **In BTC the sign changes with the regime.** Calls traded rich in the 2020-21 and 2024 rallies (Amberdata; Coin
    Metrics computes the series).
  - So the skew is information, not a constant. An unreviewed SMU dissertation (2026, Deribit 2021-04..2025-12)
    reports the 25-delta 90-day RR predicting BTC returns: t 3.73 with 13 controls, 1.91 alone.
  - **The lab holds the data to test it:** every Deribit option trade with its implied vol (`data/deribit_trades`,
    BTC from 2016-11, ETH from 2019-03).
    - The hourly 25-delta RR can be built from those trades, with delta from Black-Scholes.
    - That is **M174**, queued as **R307 `rrskew_v1`**: discovery 2021-23, validation 2024-26, no 2020.
  - **Prior:** single-asset timing signals have been NULL here (R209 DVOL, R292 dealer gamma, R295 option flow). The
    expected result is a null.

## Reel 17: instagram.com/reel/DbIlAc1g0LM (oddsonopenpod, 2026-07-23, 8,580 likes, 109 comments)
- **Who:** Tom Costello on the Odds on Open podcast. The on-screen title reads "Ex-Quant PM, Tudor Investment Corp".
- **Caption:** "Everybody in quantitative finance is a genius."
- **Speech:**
  - "A kid from Caltech… builds a high-frequency system, but he doesn't know that a high-frequency market-making
    system has a short volatility bias. Basically a mean reversion system that's betting that everything goes back to
    normal. So when volatility spikes he takes a loss."
  - "That happened to roughly 50% of the market makers in crypto on 10/10 this last year."
  - "Every inefficiency in the market is directly related to somebody else thinking they're going to do better than
    you… understanding their incentives, estimating them, modeling them… The rest is just math."
- **Checked:**
  - **The crash is real.** On 2025-10-10/11 about USD 19 billion of positions were liquidated, the largest
    liquidation in crypto's history. Top-of-book depth fell by more than 90%, and market makers withdrew (FTI
    Consulting; insights4vc).
  - **The "50% of market makers" figure has no source we could find.**
- **Lab:**
  - **The claim is a property of books, so it becomes a report, not a bet.**
    - Every mean-reverting or liquidity-providing book in the lab is short volatility, the fade books and the carry
      books included.
    - **M324** is a stress-day report: each book's PnL on named stress days (2021-05-19, LUNA, FTX, 2024-08-05,
      2025-10-10/11) and on the worst 1% of volatility days, beside its mean.
    - The R304 pick's short leg already shows this kind of tail (COAI, +1,850% in a week).
  - **The other side of his point is a strategy (M325).** When market makers pull quotes, the few who stay are
    paid. Nagel (2012, "Evaporating Liquidity") finds that equity reversal returns rise after stress.
    - In crypto: the 1-day cross-sectional reversal only on the days after market stress, against the same book on
      other days.
    - R245 found the unconditional reversal loses to cost (−17.5 bp/day), so only a stress-day lift would make it
      tradable.
    - Queued for its own id.

## What the three reels changed
- **One frozen lane now:** R306 `msnr_v1` (M323). It runs after the freeze is pushed.
- **Two queued lanes:**
  - **R307 `rrskew_v1`** (M174): the Deribit 25-delta risk reversal as a BTC/ETH signal, from held option trades.
  - **M325:** liquidity provision after stress (Nagel for crypto).
- **One tool:** M324, the stress-day report beside every book's mean (`lab/stress.py`, next).
- **One correction kept on file:** the "50% of crypto market makers lost on 10/10" figure is unsourced. The crash
  itself is documented.
- **Sources:**
  - LuxAlgo, "Malaysian SnR": https://www.luxalgo.com/library/concept/malaysian-snr/
  - TradingView, "Malaysian SnR [by DanielM]": https://it.tradingview.com/script/yqRdpnSH-Malaysian-SnR-by-DanielM
  - Amberdata, "The Smile: why crypto's skew tells a story equity markets never will":
    https://blog.amberdata.io/the-smile-why-cryptos-skew-tells-a-story-equity-markets-never-will
  - Coin Metrics, skew (constant maturity, constant delta):
    https://docs.coinmetrics.io/market-data/market-data-overview/volatility/skew-constant-maturity-constant-delta
  - SMU dissertation (unreviewed): https://ink.library.smu.edu.sg/etd_coll/887
  - FTI Consulting, "The Crypto Crash of October 2025":
    https://www.fticonsulting.com/insights/articles/crypto-crash-october-2025-leverage-met-liquidity
  - insights4vc, "Inside the $19B flash crash": https://insights4vc.substack.com/p/inside-the-19b-flash-crash
  - Nagel, S. (2012), "Evaporating Liquidity", Review of Financial Studies 25(7).

## TikTok: @aleks_rosme, 2026-10-28 QQQ 723 GEX short claim
- **Caption:** “10/28 723QQQ GEX + Failed Buyers = 1:4R 75POINTS Trade.”
- **Partial English caption track (seven cues from 00:00.1 to 00:24.8 of 00:45; not checked against speech):** The public page exposes an `eng-US` `big_caption` track marked `isAutoGen:false` and `isOriginalCaption:true`; the linked VTT separately says “Source: MT” and “Version: 8:big_caption.” These ambiguous labels do not establish human verification. The VTT SHA-256 is `d90339d6c33a737982fbbb7ce09245d4757937a1f9d0e4a49114ea96cc0bf1a0`. It says SPX entered negative-gamma territory with downside GEX magnets, then has a garbled phrase whose literal wording is “respacting” near the 7750 SPX pivot. It then describes NDX/SPX put-heavy premium, QQQ breaking 723 and prior-day RTH value-area high, buyers failing to hold above, and the creator saying this confirmed the trade. No later caption cues cover the remaining 20.2 seconds; the speech is unknown.
- **Frames:** The cover shows an OptionsDepth SPXW/GEX display with the “MM” participant filter, dates 10/28–30 and Gamma 3D. This does not establish the QQQ level’s source or model.
- **Timing check:** The public post timestamp is 15:12:58 UTC (11:12:58 EDT); the Fed statement was scheduled for 14:00 EDT. The “pre-FOMC” label is consistent with the calendar.
- **Lab:** `TT26-04-QQQ-GEX-FAILED-BUYERS` maps to existing M235 as a bearish variation of the earlier bullish 713 reclaim narration. M235 remains BLOCKED. No contract, GEX sign/vendor, option-flow definition, trigger, entry, stop, size, fills or costs are specified; “4R / 75 points” is an unverified creator claim. Zero trials and zero market outcomes.
- **Sources:** [TikTok post](https://www.tiktok.com/@aleks_rosme/video/7701736934955076886); [Fed statement](https://www.federalreserve.gov/newsevents/pressreleases/monetary20261028a.htm); [OptionsDepth FAQ](https://www.optionsdepth.com/faq); [Cboe TBT](https://datashop.cboe.com/enhanced-us-options-trade-by-trade-execution-detail); [Cboe Open-Close](https://datashop.cboe.com/cboe-options-open-close-volume-summary); [OIC open-interest FAQ](https://www.optionseducation.org/referencelibrary/faq/general-information).
