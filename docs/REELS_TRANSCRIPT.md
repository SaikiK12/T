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
