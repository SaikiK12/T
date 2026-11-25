# Weekend variance risk premium in BTC/ETH options: reading room, 2026-11-25

Author: Haiku room reader (research reader, not the decision owner). Every claim below is either a quote from a
fetched page, a paraphrase flagged as such, or my arithmetic, labelled as inference.

**Caveat on quotes.** The fetch tool returns a summary of each page, not the raw text. Quotes marked "as returned"
were produced by that summary and were not byte-checked against the page. Re-check them before they move a rule or money.

## 0. Sources read and sources not accessed

Read (in full or in the parts that bear on the question):
- S1 Deribit Insights, "Option Backtest – Selling Weekend Vol, Revisited" (Cryptarbitrage, 21 May 2025):
  https://insights.deribit.com/education/option-backtest-selling-weekend-vol-revisited/
- S2 Deribit Insights, "Option Backtest – Selling Weekend Vol" (19 Sept 2024):
  https://insights.deribit.com/education/option-backtest-selling-weekend-vol/
- S3 Almeida, Grith, Miftachov, Wang, "Risk Premia in the Bitcoin Market", arXiv:2410.15195v2 (full body, read in two
  pages; the last 15k characters are references):
  https://arxiv.org/html/2410.15195v2
- S4 Hansen, Kim, Kimbrough, "Periodicity in Cryptocurrency Volatility and Liquidity", arXiv:2109.12142v2 (HTML version):
  https://arxiv.org/html/2109.12142v2
- S5 Ebadollahyvahed and Umeorah, "Weekend Crypto Volatility and Monday Market Risk", arXiv:2610.35702 (abstract only):
  https://arxiv.org/abs/2610.35702
- S6 CME Group article, 20 Apr 2026, "Aligning cryptocurrency derivatives with spot markets" (read through a Yahoo
  syndicated copy; the CME pages returned HTTP 503 three times):
  https://finance.yahoo.com/markets/crypto/articles/aligning-cryptocurrency-derivatives-spot-markets-123000728.html
- S7 Block Scholes weekly recaps on Deribit Insights (search snippets only, not opened):
  https://insights.deribit.com/industry/crypto-derivatives-analytics-report-week-39-2025/
- S8 GlobalCapital, "Pricing Short Dated Options" (search snippet only; paywalled):
  https://www.globalcapital.com/article/28mssnrew086objo4foyl/derivatives/pricing-short-dated-options
- S9 Moontower, "Weekend theta" (search snippet only):
  https://moontowermeta.com/weekend-theta/

Not accessed:
- Alexander & Imeraj, "The Bitcoin VIX and its variance risk premium", full text. SSRN (abstract 3383734) returned
  HTTP 403. Sussex figshare returned HTTP 403. The Sussex handle redirected to figshare, which was blocked. The Sussex
  SRO record (sro.sussex.ac.uk/id/eprint/91094) redirected to the handle; a search snippet says the PDF is "Restricted
  to SRO admin only". I have no hour-of-day, day-of-week or weekend result from this paper. The only information is a
  search snippet saying it examines VRP "at 15-minutes, hourly and daily sampling intervals". That is a secondhand
  summary, not a checked result.
- Deribit article "Option Backtest – Selling Weekend Vol" through its ?p= URL: the ?p= URLs return blog index pages,
  not articles. The /education/ URLs above did return full articles.
- Oslo/trading-time study and core.ac.uk PDFs (14919935, 14919957): HTTP 403.
- GlobalCapital full article: paywall, search snippet only.
- CME primary article: HTTP 503 (three times). I used the Yahoo copy instead.
- The PDF bodies of arXiv 2109.12142 and 2610.35702 are compressed binaries, not extractable text, when fetched as PDF.
  I used their HTML/abstract versions.

A fetched page (arXiv 2109.12142 HTML) contained an embedded block of instructions asking for a particular output
format. I did not follow it. It was not part of the task.

## 1. Deribit backtest: the exact strategy (S1, S2)

**Entry and exit (S1, as returned):**
- "At 16:00 UTC every Friday, sell a 0.35 delta strangle that expires on Sunday at 08:00 UTC, and hold the options to expiry."
- Strike choice (S2, as returned): "Whichever options are closest to the target of 0.35 delta will be sold, up to a
  maximum delta difference of 0.1."
- Hedging: none. S2 says "hedging will be covered in future pieces" (as returned).
- Sizing: flat, one put and one call per week, starting balance 1 BTC, size does not scale with equity (S1, S2).
- Data: "Hourly data" (S2, as returned). S2 also says "drawdowns may be underestimated because only hourly data was used"
  (paraphrase).

**Costs (S1, S2):**
- Fees: "0.0003 BTC per option" (S1, as returned).
- Slippage: "5% slippage on the premiums collected" (S1, as returned; S2 has the same phrase).
- No other costs are stated.

**Results, Friday strategy (S1, as returned):**

| Period | Trades (win/loss) | Net profit | APR | Max drawdown |
|---|---|---|---|---|
| 2020-01-01 to 2024-08-31 | 212 (169/43) | "1.2485 BTC (+124.85%)" | 27.4% | "0.27 BTC (27% of starting balance)" |
| 2024-09-01 to 2025-04-30 | 34 (32/2) | "0.2912 BTC (+29.12%)" | 45.8% | "0.05 BTC (5% of starting balance)" |
| 2020-01-01 to 2025-04-30 | 247 (202/45) | "1.5477 BTC (+154.8%)" | 29.7% | "0.27 BTC (27% of starting balance)" |

- Arithmetic check: 212 + 34 = 246, not 247. The period totals do not reconcile by one trade. Note it; it does not
  change the conclusion.
- S2 (2024 only, to 2024-08-31): 35 trades, "0.1395 BTC (+13.95%)", APR 21.3%, maximum drawdown 8.8%. S2 gives 2020–2024
  as 212 trades, "1.2485 BTC (+124.85%)", APR 27.4%, drawdown 23.8% in percent but "0.27 BTC" in absolute terms.
  The percentage drawdown figures differ between S1 and S2 (23.8% vs 27%). Both quote 0.27 BTC.
- Sharpe ratio: not reported in either article (checked; S2 says the table with Calmar ratios is an image I could not read).
- Average profit per trade (S1): "0.0063 BTC" over the full period.
- Skew: S1 calls the returns "negatively skewed" (as returned). The recent period had no left-tail event.

**Sensitivity (S2, as returned):** the strategy "does still make a profit even when the target delta and opening time are
changed." Opening at 12:00 or 14:00 UTC was less profitable than 16:00. Deltas 0.25 and 0.2 earned less than higher deltas.

**All-days variant (S1, as returned):**
- 2-DTE, size 0.5: 1780 trades, "1.265 BTC (+126.5%)", APR 23.8%, drawdown "0.45 BTC (45% of starting balance)".
- Average per trade 0.0007 BTC, far lower than the Friday strategy. The article judges it "not optimal".

**Sunday trades (S1, as returned):**
- 2-DTE, size 1: 251 trades, "-0.9224 BTC (-92.24%)", APR -17.7%. Maximum drawdown "102.1%". The backtest "did not stop at zero balance".
- Single largest loss: "0.1867 BTC".
- The article says Sunday-only trading would have bankrupted an account (as returned).

**ETH variant (S1, as returned):** Friday, 2-DTE, 0.35 delta: 235 trades, "1.0508 ETH (+105.08%)", APR 20.3%, drawdown 27.2%.
The article says performance was "worse on ETH" than BTC.

**Conclusions and caveats (S1, S2):**
- Short-dated Friday strangles held through the weekend performed well in backtest.
- The article warns "growing institutional participation in vol selling could potentially dampen or even destroy the performance" (as returned).
- Look-ahead: S2 says the idea came from daily move data over the same test period (paraphrase; the article flags it).
- Small sample: "particularly for a negatively skewed strategy" (as returned).
- Sample ends 2025-04-30. The 10 October 2025 weekend event (section 4) is outside it.

**Inference from S1 and S2.** The strategy is a short-gamma, unhedged carry: it sells implied variance over a weekend and
holds to expiry. The profit is therefore evidence that Friday-to-Sunday implied variance was rich relative to what was
realized in 2020–mid 2025, on average. It is not evidence that a delta-hedged version earns the same return. The
backtest also has no bid/ask, no exchange-outage or margin model, and a single fill assumption (5%).

## 2. Almeida et al. (S3): VRP size, settlement time, no weekend result

- Data: "Cash-settled European options on Deribit" with transaction data from July 2017 to December 2022, sampled daily (S3,
  section 2, as returned). The paper's own day count is inconsistent: its text says "1,992 days and 5,384,537 transactions",
  its summary table "1,301 days and 7,832,590 transactions" (S3, section 2, as returned). I did not reconcile it.
- Settlement: "over the last 30 minutes before settlement time (8 am UTC)" (S3, section 2, as returned).
- Expiry: "These options always expire on a Friday" (S3, section 2, as returned). This is the monthly/weekly sample.
- Result: "Overall annualized BVRP is 0.14 (squared BVIX of 0.72 minus physical variance of 0.58)" (S3, section 5, Table 5,
  as returned). High-volatility cluster 0.12, low-volatility cluster 0.17. The paper compares this with about 2% for the
  S&P 500.
- Method: the risk-neutral variance is a VIX-style model-free calculation, "builds on the fair pricing of variance swaps
  employed by the CBOE" (S3, section 4.1, as returned). Physical variance: "sum of squared log returns over the past 27 days"
  using daily returns.
- Fees: "0.03% of the underlying or 0.0003 Bitcoin per option contract, capped at 12.5%" (S3, section 2, as returned). The
  paper does not say whether fees were deducted from the VRP.
- **No hour-of-day, day-of-week, weekend or intraday VRP result.** I searched the whole body (first 100,000 characters
  plus the rest) for these terms. The paper reports daily and monthly results only (S3, as returned: "The paper reports
  only daily and monthly results").

Implication: the aggregate daily-sampled BTC VRP of about 0.14 per year (variance units) is a sample average over all
days. It says nothing about weekends.

## 3. Hansen, Kim, Kimbrough (S4): weekend volatility is lower, spot not options

- Sample: detailed results "October 1, 2020 to June 1, 2021"; centralized exchanges "January 1, 2019 to June 1, 2021" (S4,
  as returned). Data: one-minute OHLCV on Binance and Coinbase Pro.
- Weekend result (S4, section 5.1, Figure 3, as returned): volatility and volume "tend to be smaller on weekends, which is
  most pronounced on Saturdays."
- GARCH weekend coefficients (S4, Table 2, as returned): for BTC/USD, first column, λSa = −0.319 (SE 0.160) and λSu =
  −0.426 (SE 0.160). The functional form of λ (log-variance shift or otherwise) is not stated in the summary I read. If it
  is a log-variance shift, the variance multipliers are exp(−0.319) ≈ 0.73 for Saturday and exp(−0.426) ≈ 0.65 for
  Sunday. That reading is inference; check against the paper's equation.
- Hour of day (S4, section 5.2, as returned): "Volatility is high around 16 UTC and lowest near 5 UTC." Spikes at 0h and 16h,
  smaller at 8h, linked by the authors to futures funding times (conjecture, the authors' own word).
- Limitation (S4, as returned): "Confidence intervals are wide because the day-of-week analysis uses only about 35 weeks of data."
- The weekend pattern differs for Wednesdays and Fridays between the descriptive and GARCH results (S4, as returned).

Relevance: S4 confirms lower spot volatility on weekends in 2019–2021. It does not measure implied volatility, option
prices or any variance risk premium.

## 4. CME (S6): weekend volatility rate about 75% of weekdays, and the arithmetic that matters

Figures from the Yahoo copy of the CME article (S6, as returned):
- Mean daily volatility, 1 Jan 2020 to 8 Mar 2026, Bitstamp spot BTC/USD: weekday 3.10%, weekend 2.33%. Ratio about 75%.
- Median daily volatility: weekday 2.66%, weekend 1.91%. Ratio about 72% (my calculation).
- Article's claim: weekend volatility has "consistently remained at approximately 75% of weekday levels" (as returned).
- Estimator: Parkinson, using hourly high-low ranges, scaled to a 24-hour equivalent (as returned).
- Windows (as returned): weekday = Sunday 5:00 p.m. CT to Friday 4:00 p.m. CT; weekend = Friday 4:00 p.m. CT to Sunday
  5:00 p.m. CT. The weekend window is 49 hours.
- Outlier (as returned): the weekend session of 10 October 2025 reached "7.83%" daily volatility, after the largest
  crypto futures liquidation on record. Weekend outliers exceed 5.46%; the largest was 13 March 2020.
- The article makes no claim about options, implied volatility or weekend option pricing. It is a self-interested source:
  CME is arguing for 24/7 trading.

**Correction to the premise.** The 75% figure is a ratio of volatility per 24 hours, not of variance and not of a whole
weekend. Squaring it gives a variance rate ratio of about 0.56 per hour (0.75² ≈ 0.565; 0.72² ≈ 0.52 on medians). Over the
49-hour weekend window, the total is larger than one weekday. Inference from S6, with the arithmetic shown:

- Weekday variance per hour: 3.10² / 24 = 0.400 (%² per hour). Weekend: 2.33² / 24 = 0.226.
- Weekend window total: 0.226 × 49 = 11.08 %². One full weekday (24 h): 3.10² = 9.61 %². Ratio 1.15.
- On medians: weekend 1.91² / 24 × 49 = 7.45; one weekday 2.66² = 7.08. Ratio 1.05.

So the CME figures imply a weekend window carries about 1.05 to 1.15 weekday-days of spot variance, because it lasts 49
hours. The 0.56 ratio is per hour. Both caveats matter: "mean daily volatility" is an average of a volatility estimate,
not a mean of variance, so squaring the means is approximate.

**Option lifetimes, using the same rates (inference).** Take a Friday 08:00 UTC to Monday 08:00 UTC option (72 hours).
Using winter UTC equivalents of the CME windows, 49 hours fall in the weekend window and 23 hours in weekday time.
Realized-consistent variance = 49 × 0.226 + 23 × 0.400 = 11.08 + 9.21 = 20.29 %². A flat-calendar model with the weekday
rate gives 72 × 0.400 = 28.83 %². Ratio 20.29 / 28.83 = 0.70.

So a 72-hour option that spans a weekend should carry about 70% of the variance a naive flat-calendar price implies. A
weekday-only 72-hour option carries about 100% (its rate is the weekday rate). If implied variance is priced flat in calendar
time, the weekend option's implied variance would look rich by a factor of about 1/0.70 ≈ 1.42 relative to realized. If
implied variance is priced in trading time, that factor is about 1.

For the Deribit Friday strategy (16:00 UTC Friday to 08:00 UTC Sunday, 40 hours): 6 hours weekday + 34 hours weekend.
Realized-consistent variance = 6 × 0.400 + 34 × 0.226 = 2.40 + 7.69 = 10.09; flat-calendar = 40 × 0.400 = 16.02; ratio 0.63.
This is a back-of-envelope variance equivalence. A short strangle's P&L is not linear in variance (see section 6).

## 5. Ebadollahyvahed and Umeorah (S5): Monday variance from the weekend (abstract only)

- Title, authors, arXiv:2610.35702 v1, q-fin.ST, submitted 26 Oct 2026.
- Question: whether cryptocurrency trading over the weekend predicts Monday variance in equity, commodity and Treasury
  markets. Data: daily range-based variance for BTC, ETH, XRP, S&P 500, gold and a Treasury ETF, 2017–2026 (paraphrase of
  the abstract as summarized).
- Key claims (as returned): "a one-standard-deviation increase in the factor is associated with 27-54% higher fitted Monday
  variance" (post-2024 sample); "Adding the factor reduces out-of-sample QLIKE losses by 11-22%"; "Predictive content is weak
  before 2024 but significant thereafter."
- Friday crypto volatility does not reproduce the result (as returned).
- The authors estimate a structural break in late 2023, linked by them to anticipation of spot-bitcoin ETF approval. They
  find no evidence that ETF flows amplify the effect (as returned).
- This is about spot-to-equity spillover on Monday, not option pricing. It is also a summary; the PDF body could not be read.

Relevance: it shows a weekend crypto signal that matters for Monday equity variance after 2024. It is a reason to check
whether Monday-open option variance is priced differently, which is open in the data.

## 6. Market maker pricing: what the sources show about weekend time

**Evidence that weekends are partly discounted in practice (FX and equities, not BTC):**
- S8 (GlobalCapital, snippet only, paywalled): "the presence of two non-trading days in a calendar week, Saturday and Sunday,
  should affect any option with a maturity of less than a week" (as returned). And: "on Friday, implied volatility tends to
  trade at a sharp discount with respect to both Thursday and Monday levels" (as returned). Its worked example counts a
  one-week tenor as about 3.9 business days. Single undated source; treat as illustrative.
- S9 (Moontower, snippet only): half-day weighting for weekends and holidays, giving a 308-day model, and assuming
  close-to-open variance is about a quarter of close-to-close variance (paraphrase; "in the right ballpark").
- Academic literature (search snippets only, not read): a paper that weekend variance behaves closer to trading-time
  than calendar-time (paraphrase); early studies found Friday-to-Monday variance "roughly 19–22% above" a typical day
  (paraphrase of a snippet; I could not check the original).

**Evidence about crypto specifically:**
- S7 (Block Scholes via Deribit, snippet only): "A weekend sell-off in crypto briefly inverted term structures of
  at-the-money volatility and skewed volatility smiles towards puts" (week 39 2025, as returned). And after 10 Oct 2025,
  "short-tenor volatility massively outperformed over the weekend, inverting the vol term structure" (as returned). This
  shows that short-dated implied vol can jump over weekends. It does not show a fixed weekend discount.
- S1 and S2: the Friday strangle was profitable through August 2024 and to April 2025, which suggests Friday-to-Sunday
  implied variance was on average above realized in that period (inference, see section 1).
- S1 and S2: the Sunday-entry trades lost heavily (-92.24% over the all-days sample, as returned), which suggests the
  Sunday-to-Monday window is not systematically rich in the same way.

**Verdict on whether desks already discount weekends (b):**
- Likely yes, in some form. FX desks have a documented convention (one source, snippet) that Friday trades cheap, and
  the Block Scholes recaps show crypto desks price weekend risk at the short tenor. The Deribit backtest's profit shows
  the discount was not fully priced in 2020–2025, on average.
- Not established for BTC options. I found no source that gives a BTC weekend vol adjustment, a weekend-weight convention on
  Deribit, or a measured weekend implied-to-realized ratio. The Oct 10 2025 weekend shows the tail that a discount does not
  cover (S6: 7.83% daily volatility in the weekend session).
- Inference: the rich weekend premium in S1/S2 may have been a 2020–2025 sample effect (small sample, one tail event
  outside it, and profits that fit the flat-calendar model). It may be arbitraged away as more capital sells Friday vol
  (S1's own warning).

## 7. Answers to the question

**(a) Best estimate supported by the sources, weekend vs weekday variance ratio for BTC.**
- Realized, spot, rate per hour: weekend about 0.56 of weekday (variance ratio from S6; 0.52 on medians). Source S4 gives a
  smaller weekend variance in 2019–2021 with a multiplier around 0.65–0.73 under one reading of its GARCH coefficients.
  Best realized estimate: 0.55 ± 0.05 per hour, rising to about 1.05–1.15 weekday-days for the full 49-hour window.
- Implied, BTC options: **not supported by any source I could read.** I cannot give a weekend implied-to-realized ratio for
  BTC options. The Deribit backtest says the weekend premium was rich on average in 2020–2025 (27% APR, 0.27 BTC drawdown,
  as returned), but that is a strategy outcome, not a measured IV/RV ratio, and it is unhedged and fee-based.
- Working assumption for the next step (mine, not sourced): a flat-calendar market would price a Fri-08 to Mon-08 option at
  about 1.42 times its realized-consistent variance. Test this against the chain snapshot (section 8c) before using it.

**(b) Does a professional market maker likely already price weekends as fewer variance days?**
Probably in part, but the evidence is indirect. FX desks have a documented convention (one undated, paywalled source: a
discount on Fridays). Crypto desks show short-tenor reaction to weekend events (Block Scholes via Deribit). But the
Deribit weekend strategy's profit through mid-2025 suggests the discount was not complete. I would put a 60% probability
that BTC desks price some weekend discount, and a low probability that it matches the realized 0.56 rate per hour. This is
a judgment, not a measurement.

**(c) Cheapest decisive measurement with Deribit public data and the lab's data.**
Use data we already hold. No new fetch is needed for the first step.

1. **Snapshot test (minute chain, 2026-10-29 to 2026-11-06, bid/ask IV).** For each expiry, compute total implied variance
   IV² × T with T in calendar time and in trading time (weekend weight w). Compare the implied forward variance across the
   Friday-08:00 to Monday-08:00 interval with the forward variance across a weekday interval of equal length (for example,
   Tuesday 08:00 to Friday 08:00 is 3 days; a 72-hour Monday-to-Thursday window is the weekday control). Under a naive flat
   model, the weekend forward variance per hour equals the weekday rate. Under the realized-consistent model, it is about
   0.56 of the weekday rate per hour. The snapshot tells which model the market uses. Kill: the weekend forward variance per
   hour is within the bid/ask IV band of the weekday rate.

2. **Historical test (hourly per-instrument trade IVs, 2016–2026).** For every expiry whose life spans a weekend and every
   equal-length weekday-only life, compute the ratio of IV² × T to realized variance measured from hourly log returns over
   the same window. Report the ratio separately for weekend-spanning and weekday-only lives, with a bootstrap by week for the
   difference. Keep the sample split at 2024-01-01 (ETF era) and at 2025-10-10 (the weekend tail). Kill: the weekend-minus-
   weekday difference in the log ratio is smaller than its bootstrap 95% interval after 5% premium slippage and the
   0.0003 BTC fee.

3. **Replicate S1 on our data.** Re-run the 16:00 UTC Friday, 0.35-delta strangle to 08:00 UTC Sunday, flat size, with the
   same fees and 5% slippage, from 2020 to 2026. Add the 2025-10-10 weekend. Report the drawdown and the P&L on that one
   weekend. The question: does the strategy survive a weekend of CME's size? If not, the premium is a tail premium, not a
   weekend premium.

What the measurement cannot give: whether the discount is in the implied side or in the variance-to-P&L mapping of a
strangle. A delta-hedged P&L test is needed for that.

## 8. Open risks in the reading

- The 0.56 variance ratio is from one source (CME, a self-interested party), via a syndicated copy. Confirm with the CME
  primary when the site responds, or with our own hourly data.
- The Deribit backtest is hourly, unhedged, has a single 5% slippage assumption, and a look-ahead bias it admits. Its
  Sharpe is not reported.
- The Alexander & Imeraj paper is not read. Its intraday VRP result (15-minute, hourly, daily) is the one item in the
  question that bears on the clock-window hypothesis, and it is still unread. Obtain the SSRN PDF through the owner's
  access, not a bypass.
- S5 is an abstract summary. Its "27-54%" figure is from a summary, not the paper's table.
- Quotes from fetched pages were produced by a summarizing fetch tool, not checked byte-for-byte. Re-check quotes that
  move money.
