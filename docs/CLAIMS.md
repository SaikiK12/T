# Claims to test

From the 2026-10-19 sweep (`docs/SOURCES.md`). Each claim becomes a pre-registered lane before any statistic, per
AGENTS.md. Grades: **A** audited or verifiable, **B** published study, **C** self-reported, **D** marketing.
Data: **have** = in `data/` (klines_1h with taker volume, metrics_1h, fundingRate, premiumIndexKlines_1h, bookDepth_1h);
**scrapeable** = a tested public endpoint with enough history to backtest; **live-only** = must be collected forward;
**missing** = not available without the owner (large download or credentials).
Default mechanics unless stated: Binance USD-M perps, top 50 by trailing 30-day quote volume at each hour, signal at
bar t, entry at the open of t+1, the lab's tier costs plus exact funding, results at 1x, 2x and 3x costs, read against
`registry.program_trials()`.

## Table

| id | Claim | Source | Grade | Mechanical rule on Binance perps | Data | Lane | Strongest reason it may be false |
|---|---|---|---|---|---|---|---|
| C01 | Order-book scalping (holds of 1 s to 5 min, following large participants' flow) is profitable | T. El Marhri, [FNH 2015](https://www.fnh.ma/articles/entretien-plongee-dans-le-monde-du-scalping); Krechendo course pages | D | Feasibility bound before any strategy: on aggTrades of the 10 most liquid perps (2024), a "large print" is a trade whose notional is in the top 0.1% of the trailing 24 h; enter in its direction at the next trade (taker) or at the touch (maker, filled only on a trade-through); exit after 60 s and 300 s; report gross bp per trade against a taker round trip (about 8-10 bp) and a maker round trip (about 4 bp) | missing (aggTrades, large: owner's yes) | scalp_bound_v1 | Sub-5-minute edges measured on Binance are 0.5-1.3 bp against 5 bp costs (Kim & Hansen; Kitron & Wengrowicz); under 1% of day traders are reliably profitable (Barber et al.); his "record" is single contest sessions |
| C02 | Following top copy-trading leads earns money | Binance/OKX/Bitget leaderboards; Bitget "93% of futures copiers profitable" | C/D | Daily forward snapshot of Binance `query-list` (180D, PUBLIC). Weekly at Mon 00 UTC: eligible = tenure >= 180 d, AUM >= USD 100k, MDD <= 30%; pick the top 20 by 30D **PnL** (not ROI). (A) persistence: picks' next-7D ROI minus the eligible median. (B) tradable: hourly `lead-data/positions`, net notional per coin across picks; when >= 2 picks agree, trade that direction at the next hour open, exit when the net sign flips or after 72 h, universe-hedged | live-only; position-history backfill about 4.5 months, survivors only | copylead_v1 | Lists hold only live portfolios; ROI rewards tiny bases; the #1 lead by 90D ROI had copier PnL of USD -378k; copying raises risk-taking (Apesteguia et al. 2020) |
| C03 | Fade the copy crowd: coins the copied leads are long underperform | Finfluencers (+1.2%/month against "antiskilled" advice); the lab's top-vs-crowd | B (equities) / C | Hourly crowd score per coin = sum over leads with visible positions of sign(position) x currentCopyCount, ranked across the top 50; short the top decile and long the bottom decile as overlapping 72 h slices (flow72_v2 construction), universe-hedged | live-only | copyfade_v1 | Visible positions are a small self-selected subset with notional tiny against OI; may only re-measure top-vs-crowd |
| C04 | On-chain top traders keep winning, and mirroring them pays | Hyperliquid leaderboard; "whale tracking" accounts | C (numbers A, persistence untested) | Daily snapshot of `stats-data.../leaderboard`: eligible accountValue >= USD 1 M and month volume >= USD 10 M; top 50 by month PnL. (A) persistence: rank correlation of month PnL/accountValue with the next 30 days. (B) mirror: hourly `clearinghouseState` of the picks; for coins listed on Binance, hold the sign of their aggregate net notional when >= 3 agree, exit on a flip or after 72 h, BTC-hedged | live-only (userFillsByTime gives a capped, survivor-only backfill) | hlwhale_v1 | Selection on today's PnL; big PnL comes from a few levered directional bets (one known whale lost USD 100 M in a week); in a trend, "persistence" is beta |
| C05 | The liquidity-provision side wins | Hyperliquid HLP vault: +USD 138.8 M since 2023-05 (on-chain) | A for HLP | Already tested as limit entries (maker_v1 R193, pack_v1 R194). A new lane only as two-sided quoting on bookTicker with queue and adverse-selection modelling | have (R193); bookTicker archive from 2023-05 | covered (maker_v1) | HLP earns liquidation-backstop flow and pays no taker fees; its APR is now 3.4%; 6,395 of 9,478 user vaults closed |
| C06 | Top traders positioned against the crowd predict returns, and this replicates on other venues' data | Lab R198 (top_vs_crowd alone, holdout t 2.72); vendor claims (sharpe.ai) | B-/C | Same definition as flow72's top_vs_crowd, computed from Gate `contract_stats` (top_lsr_size vs lsr_account, 1 h, 180 days) and OKX Rubik (top-trader position ratio vs account ratio per contract, about 55 days); positions on Binance returns of the same coins, 72 h slices, universe-hedged. Also report the correlation of each venue's signal with Binance's | scrapeable now (Gate 180 d, OKX ~55 d) | topcrowd_xvenue_v1 | The 180 days fall inside the lab's spent holdout (to 2026-09): only October 2026 onward is fresh; venue definitions of "top trader" differ and are undocumented; signals are correlated, so this is not independent proof |
| C07 | Liquidation imbalance predicts a reversal (cascades overshoot) | trading folklore; CONCEPTS ("no liquidation feed") | D | Per coin-hour, L = (long_liq_usd - short_liq_usd) / open_interest_usd from Gate; if L >= the 95th percentile of the coin's trailing 30 days, long the Binance perp at the next hour open and exit 12 h later (mirror for short squeezes), universe-hedged; compare with the atlas OI-drop proxy | scrapeable (Gate, 180 d); Binance `forceOrder` stream live-only | liq_v1 | Gate is a small venue; its liquidations may not represent Binance's; the atlas OI proxy may already hold the effect; same holdout overlap as C06 |
| C08 | High aggregate carry predicts crashes | Schmeling, Schrimpf, Todorov 2023 (BIS WP 1087) | B | Daily market carry = median annualized funding over the top 50 (trailing 3 days). When it is in the top decile of its trailing 365 days: short BTC perp for 7 days (or cut gross long exposure of any book). Outcome: frequency of a BTC -20% move within 30 days, conditional vs unconditional, and the overlay's PnL | have | carrycrash_v1 | Few independent crashes in 2021-2026 (perhaps 5-8): almost no power; carry compressed since 2024 (Borri et al.) |
| C09 | Perp-spot deviations are bounded and mean-revert; a simple arbitrage has a high Sharpe | He, Manela, Ross, von Wachter; Ackerer, Hugonnier, Jermann | B | Hourly per coin: premium = premiumIndexKlines close. When premium > c (c = round trip of both legs) short perp + buy spot; exit when premium <= 0 or after 72 h; record funding received; no reverse leg (no spot borrow data) | have (premium, funding); spot klines: check carry_v1's cache | basis_v1 | Same trade as carry_v1 with a different trigger; deviations shrank as markets matured; doubles capital and costs |
| C10 | Bars driven by takers reverse at 15 minutes (90% of 183 Binance pairs) | Kitron & Wengrowicz 2026 | B | 15-minute klines: if the bar's taker imbalance is in the top decile and agrees with its return, place a limit order against it at close +- 0.5 x ATR(15 m), valid one bar; exit after 1-4 bars | have the 1 h analog (atlas, maker_v1); 15 m klines are a small archive download | rev15_maker_v1 (optional) | The authors say it is not tradable after costs; the lab's hourly reversal cells also fail costs per trade |
| C11 | Quarter-hour opening order imbalance predicts 4-12 h returns | Kim & Hansen 2026 | B | aggTrades: imbalance in the first 10 s after :00/:15/:30/:45; trade its sign; hold 4, 8, 12 h; six majors | missing (aggTrades) or live websocket | qhour_v1 | About 0.5 bp at short horizons; 4 of 6 contracts significant; likely arbitraged by faster players |
| C12 | BTC hour-of-day seasonality: 21-23 UTC strongest, 03-04 UTC weakest, Friday best | Quantpedia (Gemini 2015-2022) | C | Long BTC perp 21:00 to 23:00 UTC daily, flat otherwise; Friday-only variant | have | covered (atlas_v1 clock views: null) | The lab's atlas found clocks alone predict nothing; Baur et al. found no consistent pattern; two trades a day cost about 10 bp |
| C13 | Intraday time-series momentum: the day's first period predicts its last | Shen, Urquhart, Wang 2022 (*Financial Review*) | B | Day = 00-24 UTC. At 23:00 UTC go long BTC if the 00:00-01:00 return > 0, else short; exit at 24:00. Variant: the day starts at the hour of lowest 30-day average volume. Run on BTC, ETH and the top 10 separately | have | itsm_v1 | Conflicts with the lab's "day open" mean reversion (79-100% replicate); they used 30-minute bars and a volume clock; one round trip a day costs about 10 bp against an unknown gross |
| C14 | Cross-sectional momentum over 1-2 weeks, reversal from 4 weeks | Dobrynskaya 2023; Liu, Tsyvinski, Wu 2022 | B | Weekly: rank the top 50 by 7-day return, long top quintile, short bottom quintile, hold 7 days. Reversal: rank by 28-day return, long losers, short winners, hold 28 days. Equal weight | have | xsmom_v1 (check the atlas momentum views first) | Their samples include coins down to USD 1 M cap, where the effect concentrates; the atlas found cross-sectional selection strong in 2021-2023 and gone in 2024-2025 |
| C15 | A prop challenge has negative EV for the average buyer; a zero-edge pass rate is capped by barrier math | FPFX via Finance Magnates (7% of 300k accounts paid, mean payout about 4% of plan); Topstep 2025 disclosure; FTMO price; lab R144 (random start about USD -80) | B/C | Simulator with exact rule sets: HyroTrader 2-step and 1-step, FTMO 2-step and 1-step (with the 50% best-day rule), CFT 1-phase (6% trailing), Topstep 50K (USD 2,000 EOD trailing, locking at start). Inputs: (a) zero-edge baseline: random-direction BTC/ETH perp trades with stop and target of k x ATR(1 h), risk per trade 0.25-3% of the account, daily limits on equity at each firm's reset hour, taker fees; (b) the flow72 slice book's hourly PnL, block-bootstrapped by week. Outputs: P(pass), P(first payout), E[payout after split], EV = P(payout) x E[payout] + refund - fee, days to pass | have | propfirm_v1 (builds on R143, R144 and the planned `lab/propfirm.py`) | Rules change and firms keep discretion (HyroTrader reviews can remove profits); demo fills are not our fills; payouts after the first are unknown; firms fail (The Funded Trader, My Forex Funds) |
| C16 | A challenge is a cheap call option: with a real but volatile edge, buying challenges beats risking own capital | Inference from rule shapes (R144 `challengeoption`) | C | Same simulator: (i) own capital trading the flow book at fractional-Kelly sizes vs (ii) repeated challenges (re-buy after failure) trading the same signal scaled to each firm's limits. Metric: expected net USD per month and the probability of losing the own-capital stake | have | propfirm_v1 (part B) | The flow book's max drawdown (27% in-sample, 47% on holdout) against 5-10% limits forces about 5x smaller size, so payouts shrink; 40-55% consistency rules penalize a lumpy book |
| C17 | Daily loss and profit limits improve results | Krechendo course ("define your daily gain and loss limit"); prop-firm daily limits | D | Overlay on the flow72 slice book and on the top atlas cells: when day-to-date PnL <= -x (x = 0.5, 1, 2% of equity) or >= +y (y = 1, 2, 4%), close everything and stay flat until 00:00 UTC; compare mean, Sharpe and max DD with the same trades unfiltered | have | daylimit_v1 | Optional stopping: with independent daily PnL, stops cannot raise the expectation, only reshape the distribution; the x, y grid is a search and its trials count |
| C18 | The Coinbase premium (US spot bid) leads BTC | crypto social media | D | Hourly prem = Coinbase BTC-USD close / (Binance BTCUSDT spot close x USDT-USD from Coinbase) - 1; z-score over 30 days; z > 2: long BTC perp 24 h; z < -2: short | scrapeable (Coinbase hourly since 2015) + have | cbprem_v1 | Likely contemporaneous with US-hours flow and the USDT basis rather than leading; heavily mined in public |
| C19 | An extreme retail long/short ratio is contrarian (ratio > 3 marks a top) | vendor pages (sharpe.ai) | D | Per coin: global account L/S ratio >= the 95th percentile of the trailing 90 days: short for 72 h, universe-hedged | have (metrics) | covered (atlas_v1 flow views, flow72) | The atlas found flow-based selection mostly gone in 2024-2025; the crowd ratio alone is weaker than top vs crowd |
| C20 | Base rate: almost everyone who day-trades loses; persistent winners are under 1% | Barber et al. 2014; Chague et al. 2019; Topstep 0.71% to Live | A/B | Not a rule: the prior for every trader claim here (C01-C04) is a few percent at most | - | - | Different populations (Taiwan equities, Brazilian futures, CME props); no crypto study shows a better base rate |
| C21 | Lead-trader returns are mostly leverage times market beta, not skill | inference; Apesteguia et al. 2020 | C | From Binance position-history of current leads (about 4.5 months): rebuild each lead's daily PnL from closed positions; regress on BTC and the equal-weight top-50 index; share of variance explained; intercept t-stats against a sign-shuffled null | backfill (survivors only) + live | copylead_v1 (part A) | Only closed positions are visible (no mark-to-market); survivors only; 4.5 months is one regime |
| C22 | ROI rankings are dominated by small accounts, so ROI is not money | Binance query-list (USD 47,859 PnL = 9,572% ROI; copiers USD -378k) | A (platform numbers, descriptive) | In copylead_v1: rank correlation of ROI with PnL, share of the top 100 by ROI with AUM < USD 10k, copier PnL by ROI decile | live | copylead_v1 (descriptive) | Partly true by construction; it describes the list, not anyone's future returns |
| C23 | The variance risk premium (implied minus realized volatility) predicts index returns | Bollerslev, Tauchen, Zhou 2009 (*RFS*, equities) | B (equities) | Daily: VRP = Deribit DVOL - 30-day realized vol of the perp; long BTC (ETH) when above its trailing-365-day median, short below; daily and weekly; tercile variant | scrapeable (Deribit DVOL hourly from 2021-03) + have | vrp_v1 | Equity evidence is monthly-quarterly; one or two assets give few independent bets |

## Prop-firm economics, worked through

**Zero-edge ceiling.** For a driftless random walk with continuous monitoring, no costs and no daily limit:
the chance of gaining *a* before losing a static *b* is b/(a+b); before suffering a trailing drawdown *d* it is
exp(-a/d) (the running maximum at the first drawdown of size d is exponential with mean d).

| Rule set | Zero-edge pass ceiling | Observed |
|---|---|---|
| FTMO 2-step, HyroTrader 2-step (10% then 5%, 10% static) | 0.50 x 0.667 = 0.33 | FPFX industry average about 14% |
| CFT 2 phases (8% then 5%, 10%) | 0.556 x 0.667 = 0.37 | - |
| HyroTrader 1-step (10%, 6%; static assumed) | 0.375 (0.19 if trailing) | - |
| HyroTrader zero-step (10%, 5%) | 0.33 | - |
| CFT 1 phase (10%, 6% trailing) | exp(-10/6) = 0.19 | - |
| FTMO 1-step (10%, 10% EOD trailing) | about exp(-1) = 0.37 | - |
| Topstep 50K (USD 3,000 target; USD 2,000 EOD trailing, locks at start) | exp(-1) x 2/3 = 0.25 | 16.8% per Combine (2025) |

Daily loss limits, fees and consistency rules lower every ceiling. Observed pass rates sit below the zero-edge ceilings,
which suggests (inference, untested) that the average buyer trades worse than a coin flip after costs or breaks a daily
limit. C15 measures it with exact rules.

**EV per attempt for the average buyer.**
- FTMO 100k 2-step: fee EUR 540. With FPFX's averages (7% reach a payout, mean payout about 4% of plan = USD 4,000):
  0.07 x 4,000 = USD 280, plus the fee refund 0.07 x 540 = about EUR 38, so **EV is about -EUR 220 to -260** per
  attempt (TradeInformer's same arithmetic: about EUR 258k paid per EUR 540k of fees per 1,000 buyers). Whether the 4%
  is before or after the split is not stated.
- Topstep 50K standard path (third-party prices): USD 49 a month plus USD 149 at activation. At 16.8% pass per Combine
  (one Combine per billing month assumed, resets ignored), a funded account costs about 49 / 0.168 + 149 = **USD 441**.
  With 33.3% of funded participants ever paid, break-even needs a mean payout of about **USD 1,320** per paid
  participant. Topstep does not publish the mean payout, and its percentages mix accounts and participants, so the
  sign is unknown.
- Why firms survive: the funded trader keeps 80-90% of gains while losses only end the account, an option worth money
  even at zero edge. Firms offset it with fees, consistency rules, minimum days, payout caps and buffers (Topstep moves
  the loss limit to USD 0 after the first payout), and payouts are paid from fee income (HyroTrader's FAQ says its
  revenue comes from challenge fees).
- For us: a challenge only makes sense for a signal whose drawdown fits inside 5-10% at a size that still pays.
  The flow book's drawdowns (27-47%) mean scaling it down about 5x (C16).

## Already covered by the lab

C05 (maker_v1, pack_v1), C12 (atlas_v1 clocks: null), C19 (atlas_v1 flow views, flow72), funding carry itself
(carry_v1, carry_holdout: confirmed and regime-bound, matching Borri et al.'s Sharpe falling to negative in 2025).
Do not re-run them as new lanes without a changed question.

## The five to test first

1. **C06 topcrowd_xvenue_v1.** Cheap (Gate 180 days, OKX about 55 days, both scrapeable now), and it tests the lab's
   best lead on independent positioning data. Treat the overlap with the spent holdout honestly: discovery only, and
   start a forward collection of all three venues now.
2. **C15/C16 propfirm_v1.** Uses data the lab has, finishes the planned `lab/propfirm.py`, and answers a practical
   question: is a crypto prop challenge (HyroTrader/Breakout/CFT on Binance-like perps) a better route to stake size
   than own capital for the flow book?
3. **C02/C21/C22 copylead_v1.** Start the daily snapshot scraper now (Binance list, details, positions), since the
   test needs forward data. Meanwhile, use the 4.5-month position histories (labelled survivor-only) to measure whether
   lead PnL is more than beta.
4. **C07 liq_v1.** Adds liquidations, the one order-flow type the archive lacks (Gate, 180 days hourly), and checks it
   against the atlas OI proxy.
5. **C13 itsm_v1.** A published, cheap test whose prediction (intraday momentum) contradicts the lab's own day-open
   mean reversion; either answer is informative.
