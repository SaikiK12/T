# Project direction from quant evidence: external literature

**Verdict: partly.** The lab's one holdout-passed edge (funding carry) matches published work, and the most literature-supported family (weekly cross-sectional momentum on liquid perps) is still untested in long-short form. But most search effort (top-trader and flow books, intraday clocks, indicator cells, sub-minute scalping) has little or no net-of-cost published support, and the anomalies the literature finds sit in micro-cap coins that the top-50 universe excludes.

Scope and grade: standard-mode WebSearch (about 13 queries), three page fetches. The icm.edu.pl pages returned HTTP 403, so the Fieberg and Mercik items come from search snippets. Repo facts come from the docs named in the brief. No external result below is a net-of-cost return with 1x/2x/3x figures; where a source gives no cost figure, I say so.

## 1. Matched lanes: published effect, lab tested

- **Funding carry (M134, C08, M136).** Borri, Liu, Tsyvinski, Wu report carry Sharpe 6.45 over the full sample, 4.06 from 2024, and negative in 2025, on Binance BTC ([arXiv:2510.14435](https://arxiv.org/abs/2510.14435); figures cited from `docs/SOURCES.md` §4.3, not re-read). The lab's R191 holdout (+1.45%/yr, t 2.07) and R220 MEXC replay (about zero) fit that decay (`docs/SOURCES.md` §4.3; `docs/METHODS_QUEUE.md` M134). Schmeling, Schrimpf and Todorov say high carry predicts crashes ([BIS WP 1087](https://www.bis.org/publ/work1087.htm)). The lab's R207 found the reverse sign, a null. Cost figures: none in the external sources I read.
- **Simple perp-spot arbitrage.** He, Manela, Ross and von Wachter find crypto perp deviations larger than in FX, comoving across coins and shrinking as markets mature. Their search snippet says a simple arbitrage keeps a high Sharpe even at Binance's highest trading costs ([arXiv:2212.06888](https://arxiv.org/abs/2212.06888)). The number is not in the snippet. The lab has not run this on spot data (M047 BLOCKED). The maturing-market finding implies decay.
- **Daily trend.** Zarattini, Pagani and Barbon's rotating diversified-universe trend (`docs/QUANTPEDIA_RESEARCH_REVIEW.md` §1) was tested only as the six-coin spot version (R229, Sharpe 1.261 vs 1.227 passive). That is a null for the adaptation, not for the paper.
- **Intraday time-series momentum (C13, R203 null).** Shen, Urquhart and Wang report first-half-hour returns predicting last-half-hour returns, attributed to liquidity provision ([Financial Review 2022, doi:10.1111/fire.12290](https://doi.org/10.1111/fire.12290); per `docs/SOURCES.md` §4.4). The lab's hourly BTC version nets -11 to -14 bp/day. Their bars and volume clock differ, so this is not a direct refutation. No cost figure is given in the source I read.
- **Clock effects (C12, R185 null).** Baur et al. find no consistent time-of-day or day-of-week pattern across seven exchanges ([FRL 2019](https://research-repository.uwa.edu.au/en/publications/bitcoin-time-of-day-day-of-week-and-month-of-year-effects-in-retu/)). The lab's null is consistent with that.
- **Token unlocks (M057, M072, R181, R159, R179).** Direction matches the repo's short thesis, but the evidence is vendor-grade. Tokenomist (June 2026) reports 236 unlocks with 72.5% lower one month later, median -16.26% vs BTC and -4.85% vs matched peers (n=221). The effect sits in thin-float tokens; established high-liquidity tokens show no significant effect ([Tokenomist](https://tokenomist.ai/research/do-token-unlocks-crash-prices), grade D). Keyrock's roughly 16,000-event review was reported only secondhand. I found no peer-reviewed crypto unlock study. The lab's R181 in-sample result (t 4.06) is not clean: the old session read the holdout. These are price moves, not net returns, so no cost figures apply.
- **Listing effects (M155, R188 and R189 null).** Listing-announcement studies find positive short-window returns, the opposite sign of the lab's 14-day listing short. Coinbase and Binance listing-day first-day returns are reported at 32.8% and 22.7% in a [working paper by Li et al.](https://loyola.edu/_media/sellinger-business/documents/academics/departments/finance/wealth-management-conference/speakers/J_Li.pdf). An ICO cross-listing study reports 6.51% on the listing day and 9.97% over seven days ([Springer, s10203-021-00323-0](https://link.springer.com/10.1007/s10203-021-00323-0)). Ante (2019, 327 listings) reports 5.7% on the listing day; a blog on the same work gives 7.4%. That paper's source page was not identified. All are gross, spot-exchange, and dated. I found no study of decay.
- **Copy trading (C02, C03, C21, C22).** Copying raises risk-taking in an experiment ([Apesteguia et al., Management Science 2020](https://bse.eu/research/publications/copy-trading)). Under 1% of day traders are reliably profitable after fees ([Barber et al., JFM 2014](https://ideas.repec.org/a/eee/finmar/v18y2014icp1-24.html)). No crypto lead-trader persistence study turned up.

## 2. Lanes with no literature support found

- **Top-trader and flow books (R196 to R221, the largest search).** Two searches found no academic study of exchange top-trader ratios (`docs/SOURCES.md` §4.2). The nearest analogues are commodity and equity studies (Kang, Rouwenhorst and Tang, cited from memory in the repo; Kakhbod et al. on finfluencers). Anastasopoulos et al. (2026) support daily signed-flow predictability across fiat spot markets ([JFM 2026](https://doi.org/10.1016/j.finmar.2026.101047)), but not this feature (`docs/RESEARCH_FRONTIER.md`). The holdout did not confirm the primary combination (R198).
- **Liquidation fade (C07, R206 null).** No published study found. The archive has no liquidation feed.
- **Coinbase premium (C18, R210 null).** The source is social media (grade D). No paper found.
- **Crypto VRP (C23, R209 null).** Bollerslev, Tauchen and Zhou are equity evidence. No crypto paper found.
- **Prop-challenge economics (C15, C16).** Industry data only (`docs/SOURCES.md` §3). It is a sizing question, not a market-edge question.
- **Scalping, quarter-hour flow, 15-minute taker reversal (C01, C10, C11).** The literature finds small gross signals that do not survive costs. Kitron and Wengrowicz report about 1.3 bp gross per trade against a 5 bp round trip ([arXiv:2608.21888](https://arxiv.org/abs/2608.21888)). Kim and Hansen report about 0.5 bp at ten seconds ([arXiv:2607.09426](https://arxiv.org/abs/2607.09426)). Both figures are from the repo docs, not re-read. The lab's MEXC cost is higher than 5 bp (section 5, item 1), so C01 is likely to confirm the null.
- **Chart, ICT and oscillator cells (R185, R171 to R173).** No peer-reviewed support (`docs/CONCEPTS.md` §1). A warning from the literature: about 15,000 technical rules on Bitcoin passed data-snooping adjustments and had no out-of-sample predictability ([Hudson and Urquhart](https://link.springer.com/article/10.1007/s10479-019-03357-1)). The lab's nulls fit this.

## 3. Untried families the literature supports and the data could test

1. **Weekly cross-sectional momentum and reversal, long-short, top-50 perps (C14; M034 PARTIAL).** Dobrynskaya finds momentum to about two weeks and reversal from four weeks, with large weekly rebalancing costs (`docs/SOURCES.md` §4.6, not re-read). Fičura's abstract reports weekly reversal in small illiquid coins and weekly momentum in large liquid coins (t 2.33) ([FFA WP 2023](https://wp.ffu.vse.cz/artkey/wps-202301-0003_impact-of-size-and-volume-on-cryptocurrency-momentum-and-reversal.php); fetched; sample and costs not in the abstract). Fieberg, Liedtke and Zaremba (IRFA 2024, [abstract](https://open.icm.edu.pl/items/2350d455-72e4-4845-a442-9c4024be7fb6/full), snippet only) find momentum in larger coins, substantial costs, most of the alpha from short positions, and gains concentrated in bull markets that fade over time. The lab's R230 and R232 are six-coin spot, long-only. The long-short perp version has not been run. Report short and long legs separately, with funding.
2. **Trend factor (lead, unverified).** Fieberg, Liedtke, Poddig, Walker and Zaremba, "A Trend Factor for the Cross-Section of Cryptocurrency Returns," JFQA forthcoming. I saw the title only. The lab's trend features are hourly (R185). A cross-sectional daily or weekly trend factor on perps would differ from R222's momentum. Read the paper before pre-registering.
3. **Illiquidity sort, by tier (M002; M017 tiers).** Cakici et al. (IRFA 2024) find alpha concentrated in small, volatile, hard-to-trade coins ([doi:10.1016/j.irfa.2024.103244](https://doi.org/10.1016/j.irfa.2024.103244); via `docs/RESEARCH_FRONTIER.md`). Zaremba et al. (IRFA 2021) find daily reversal in illiquid coins and daily momentum in the most liquid ([doi:10.1016/j.irfa.2021.101908](https://doi.org/10.1016/j.irfa.2021.101908)). The anomaly region is where costs are highest, so the test must report net return by tier at 1x/2x/3x, with capacity, not pooled.
4. **Size factor (M093).** Fieberg et al. ("Cryptocurrency factor momentum," Quantitative Finance 2023; search snippet, no link verified) attribute size and volatility anomalies to micro-caps "of negligible economic importance." Not testable here: no market-cap or supply series in the checkout.
5. **Daily signed taker-imbalance cross-section (partly covered).** `klines_1h` carries `taker_buy_volume`, so a daily aggregate is a usable signed-flow proxy on 901 perps. R185 tested the hourly version (1% replicate). Check overlap before pre-registering.

## 4. What the data cannot test

- Micro-cap MEXC history, where the published anomalies sit. The checkout holds about 22 days of MEXC klines for 40 contracts; the history fetch is not run (`docs/METHODS_QUEUE.md`, data section).
- Market cap, supply, FDV, and therefore the size factor.
- Announcement and notice timestamps for listings, delistings and unlocks (M057, M061, M062).
- Trade-level signed flow, full order book and queue effects (aggTrades, bookTicker).
- Spot klines for the top 50, which the basis lane (C09) needs.
- Binance liquidations (Gate only, 180 days).
- Lead-trader positions older than about 4.5 months, which are survivor-only.
- Independent BTC crash events: perhaps 5 to 8 in 2021 to 2026 (`docs/CLAIMS.md` C08).

## 5. Open questions

1. **Cost basis.** `docs/FOUNDATION.md` gives 0.002 per trade. `docs/RESEARCH_FRONTIER.md` cites a modeled 6 bp one-way taker and a listed 8 bp MEXC API taker, from a June 2026 notice that it calls internally inconsistent. Which applies changes which families survive at 1x. I did not re-read the MEXC notice.
2. **Universe.** `docs/CLAIMS.md` sets the default as the top 50 by 30-day quote volume. Confirm the universe R222 and the flow books used. If they exclude the bottom of the 901-perp list, the literature's anomaly region is untested.
3. **Carry net of cost.** Is R191's +1.45%/yr net of fees, and at what 1x/2x/3x?
4. **Repo-cited numbers.** Borri et al., Dobrynskaya, Anastasopoulos et al., Kitron and Wengrowicz, and Kim and Hansen come from the repo docs. I checked only what a search returned. Re-read before quoting in a pre-registration.
5. **Christin et al.** A SEC comment letter ([S7-2026-21](https://www.sec.gov/comments/S7-2026-21/s7202621-1011079-3235289.pdf)) describes a study of 18 coins in which shorting perps against spot earned high realized returns. I did not find the paper. If it exists, it is the closest published perp-basis result. One targeted search would settle it.

## 6. Could not check

- Fieberg et al. (2023, 2024) and Mercik et al. (2025, out-of-sample long-short Sharpe above 1, cost treatment unknown): snippets only, because icm.edu.pl returned 403. No cost figures.
- The trend-factor paper (title only), and the Christin et al. paper (not found).
- Vendor figures (Tokenomist, Keyrock, Streamflow, funding-arbitrage Sharpe ratios such as 23.55): grade C or D, not relied on.
- No peer-reviewed net-of-cost perp study was found. Extended-mode search was not run; standard results were on target but thin on net-of-cost evidence.
- The room (`docs/ROOM.md`, issue #7) was read, not posted to, because this brief was read-only.
