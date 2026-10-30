# Concepts: what they are, what the evidence says, and how the lab tests them

Each concept gets a mechanical definition (the only kind a machine can test), the data it needs, the evidence found, and
the feature or module that encodes it. "Evidence" is what independent studies show, not what educators claim.
Where a definition is one reading of a discretionary idea, the variants are part of the search space and are counted
as trials.

## 1. ICT / smart-money concepts

Source of the ideas: Michael Huddleston ("Inner Circle Trader"), later repackaged as "smart money concepts" (SMC).
**Evidence:** no peer-reviewed or independent study found. The one mechanical test located
([StatOasis](https://statoasis.com/overfit/research/ict-backtest-what-survives): daily SPY/QQQ/DIA/IWM, 648 backtests,
no costs, no out-of-sample) had 1 of 32 t-statistics above 2; the best order block reached t = 1.22. Vendor claims
(e.g. "64.8% of FVGs get revisited") give no baseline or test. The honest position: untested on crypto, so test it, with
costs, a placebo and a holdout.

| Concept | Mechanical definition used (`lab/ict.py`) | Features |
|---|---|---|
| Fair value gap (FVG, imbalance) | Bullish: `high[i-2] < low[i]`; bearish mirror. Gap of at least `min_gap` x ATR. Zone dies when a later bar trades through its far edge. Latest zone per side. | `fvg[gap,side,dist|age]` at 1h/4h/1d |
| Order block (OB) | A displacement bar (body at least `impulse` x ATR) marks the last opposite-colour bar in the previous 5 bars; its high-low is the zone; dies on a close through it. | `ob[impulse,side]` |
| Liquidity sweep / stop run | The bar's extreme takes out the last n-bar extreme but it closes back inside. Output: bars since. | `sweep[n,side]` n = 10, 20, 50 |
| Market structure shift (BOS / MSS) | Swing highs/lows by fractal of 2 or 5 bars (known only after confirmation); a close beyond the last swing flips the state. | `struct[fractal,state|since]` |
| Premium / discount, OTE | Position of the close inside the last swing range; retracement of the last up-leg (the 61.8-78.6% band is "optimal trade entry"). | `struct[...,pd]` (bins at 0.382, 0.5, 0.618, 0.786) |
| Previous-day high/low raid | Today's high takes out yesterday's high and closes back below (mirror for lows). Distance to PDH/PDL in prior-day ATR. | `prevday[...]`, `prevday_raid` |
| Asian range | High/low of 00-08 UTC; where price sits in it after 08:00. | `asia` |
| True day open, week open bias | Close relative to the 00:00 UTC open of the day. | `dayopen` |
| Kill zones / sessions | London, New York and Asia hours mapped to UTC; hour-of-day and weekday as raw categories so any window can be found, not assumed. | `hour`, `dow`, `session`, `funding_clock` |
| Power of 3 (accumulate, manipulate, distribute), Judas swing | Not coded as a single rule: it is a sequence of Asia range, sweep of that range, then a move the other way. The search can assemble it from `asia`, `sweep`, `struct` and `hour` conditions (an AND of 2-3). | search |
| SMT divergence | Not yet encoded (needs a correlated pair making different highs/lows). Planned as a cross-symbol feature. | planned |

Academic root for stop runs: stop-loss orders cluster just beyond round numbers and take-profit orders on them, and
rates reverse often at take-profit clusters (Osler, NY Fed
[SR125](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr125.pdf),
[SR150](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr150.pdf); one bank's FX order book,
1999-2000). Whether crypto perps behave alike is an open question; round-number features are a candidate addition.

## 2. Order book and order flow

| Concept | Meaning | Data in the public archive | Status in the lab |
|---|---|---|---|
| Taker imbalance / CVD | Buy-initiated minus sell-initiated volume, cumulative for CVD | Hourly+ klines carry `taker_buy_volume` (so imbalance per bar); aggTrades for finer | `tbi[n]` from klines; finer flow planned |
| Order flow imbalance (OFI) | Change in best bid/ask depth net of trades (Cont-Kukanov-Stoikov) | `bookTicker` from 2023-05, `bookDepth` from 2023-01 (coarse depth bands) | Not used yet: sub-second effects (OOS R-squared about 2% at 100 ms) are far below fees ([thesis](https://dspace.cuni.cz/bitstream/handle/20.500.11956/213492/130479083.pdf?sequence=1&isAllowed=y)) |
| Quarter-hour effect | Activity and imbalance spike at :00/:15/:30/:45; imbalance there predicts returns over the next 4-12 h on Binance perps (4 of 6 contracts significant) but the 10-second effect is about 0.5 bp against a 5 bp taker fee ([Kim & Hansen](https://arxiv.org/html/2607.09426v2)) | aggTrades (large) | Candidate flow lane; needs streamed trade data |
| VPIN / flow toxicity | Volume-synchronized imbalance as a crash predictor | aggTrades | Disputed: [Andersen & Bondarenko](https://papers.ssrn.com/abstract=2062450) find it mostly mechanical in trading intensity. Test empirically only |
| Open interest + price | OI up with price up = new longs; OI up, price down = new shorts; OI drop with a large range = liquidations | `metrics` (5-minute OI, long/short ratios, taker ratio) | Daily files only; fetched for the top symbols on demand |
| Funding and basis | Perp price vs index; funding settles every 8 h (some 4 h or 1 h). Funding predicts returns, strongest in the tails with sign flips ([RobotWealth](https://edgealchemy.robotwealth.com/p/hyperliquid-carry-looks-trendy)); perp convergence trades ([Ackerer et al.](https://arxiv.org/pdf/2212.06888)) | premiumIndexKlines, fundingRate | `prem`, `fund`; funding is also charged in the backtest at the exact settlement events |
| Liquidation cascades | Forced closes feeding price moves | No liquidation feed in the archive | Proxy only: OI drop with range expansion |
| Spoofing, icebergs, queue position | Order-book manipulation and hidden size | Needs full-depth tick data | Out of scope here |

## 3. Prop firms

A prop firm sells an evaluation: you pay a fee, trade a simulated or funded account under rules, and keep a share of
profit if you pass. The edge needed is the one that survives the rules, not just a positive expectancy.

| Rule | Typical range | Variants that matter |
|---|---|---|
| Max drawdown | 8-12% of the account | Static (from the starting balance) vs trailing (from the peak equity) |
| Daily loss limit | 4-6% | Measured on equity (open losses count) or closed balance; resets at a firm-defined hour |
| Profit target | 6-10% per phase | One or two phases |
| Consistency rule | One day or trade may be 30-50% of total profit | Per day or per trade; evaluation only or also funded |
| Other | Minimum trading days, per-trade loss cap (a reviewed crypto firm: about 3% of the account), forced withdrawals | |

Numbers above are from third-party summaries ([Track360](https://www.track360.io/glossary/prop-firm-risk-rules)) and
**conflict between reviewers for the same firm** (one reviewed crypto firm: daily drawdown 4% vs 5%, starting split 70%
vs 80%), so treat them as ranges and read the firm's own terms before using any figure.

**How the lab uses it (`lab/propfirm.py`, planned):** take a strategy's daily net PnL, simulate thousands of complete
evaluations by block bootstrap under an exact rule set, and report pass probability, expected value after the fee and
profit split, and the risk per trade that maximizes it. Earlier lanes R143/R144 found a random start loses about 80 USD
per challenge on average; the module answers what edge and sizing would flip that sign.

## 4. Statistics used to avoid fooling ourselves

| Tool | Why | Where |
|---|---|---|
| Threshold t above 3 for new factors (about 3.25-3.75 with Bonferroni) | Many researchers, many tests ([Harvey-Liu-Zhu](https://www.nber.org/papers/w20592)) | evidence bar |
| Deflated Sharpe | Best of N is biased upward ([Bailey-Lopez de Prado](https://papers.ssrn.com/abstract=2460551)) | `inference.dsr` |
| Probability of backtest overfitting (CSCV) | Does the in-sample winner stay good? ([paper](https://papers.ssrn.com/abstract=2326253)) | `inference.cscv_pbo` |
| SPA / reality check, Model Confidence Set | Does anything beat the benchmark after searching? ([arch docs](https://arch.readthedocs.io/en/latest/multiple-comparison/multiple-comparison-reference.html)) | `inference.spa`, `model_confidence_set` |
| Online FDR (LORD++) | A program that never stops testing needs a budget that earns back on real finds ([Javanmard-Montanari](https://arxiv.org/pdf/1502.06197)) | `inference.lord_plus` |
| Empirical-Bayes shrinkage | The top of a noisy ranking is mostly luck | `inference.eb_shrink` |
| Placebo (circular time shift of returns) | Calibrates the whole search, not one test | `search.shifted_returns`, `search.empirical_fdr` |
| Turnover-matched random selection | Compares a selection policy with chance at equal cost | `policy.random_policies` |

A relevant warning: about 15,000 technical rules on Bitcoin looked significant even after data-snooping adjustments yet
had no out-of-sample predictability for Bitcoin ([Hudson & Urquhart](https://link.springer.com/article/10.1007/s10479-019-03357-1)),
and predictability is local in time ([Timmermann & Granger](https://ideas.repec.org/a/eee/intfor/v20y2004i1p15-27.html)).
That is why the lab judges the process of choosing what currently works, not a rule's full-sample record.
