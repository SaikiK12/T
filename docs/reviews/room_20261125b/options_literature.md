# Option dealer hedging flows: gamma, charm, vanna, vomma. What the literature shows and what transfers to Deribit

Room: literature reader. Date: 2026-11-25. Scope: legal copies only. Scratch PDFs are under
`/tmp/claude-0/-home-user-T/a4c99094-0eba-54d5-9f6a-3abc85cabed2/scratchpad/optlit/`.
Nothing in `experiments/*/journal/` was opened. No code, data or other file was touched.

## 0. Source status (read this first)

| # | Source | Status | Weakest link |
|---|---|---|---|
| S1 | Ni, Pearson & Poteshman (2005), JFE 78(1), 49-87, "Stock price clustering on option expiration dates" | NOT read in full. JFE is paywalled. The SSRN copy (abstract_id 519044) is blocked (403). Abstract only, plus the description in S8. | Full text, methods and OOS unknown to me. |
| S2 | Pearson, Poteshman & White (2006), "Does option trading have a pervasive impact on underlying stock prices?" | Read in full. It is a PRELIMINARY draft whose cover says "please do not quote or circulate". Internal use only. | Draft, not published; CBOE data ends 2001. |
| S3 | Barbon & Buraschi (Nov 2020), "Gamma fragility", SFI WP 2020/05 | Read in full (St. Gallen repository copy). | Working paper; no OOS test. |
| S4 | Baltussen, Da, Lammers & Martens (2021), "Hedging demand and market intraday momentum", JFE 142, 377-403 | Read in full (author copy, nd.edu). | NGE sign rule is an assumption (see section 2). |
| S5 | Baltussen, Terstegge & Whelan (Sept 2024 version), "The derivative payoff bias" (charm channel) | Read in full (AEA program PDF). | Market-maker positions are a CBOE residual, not observed. |
| S6 | SqueezeMetrics, "Gamma Exposure (GEX)", Mar 2016, rev. Dec 2017 | Read in full (sqzme official download). | Practitioner paper; no statistics beyond one plot. |
| S7 | Herrmann & Muhle-Karbe (arXiv:1704.04524, 2017), "Model uncertainty, recalibration and the emergence of delta-vega hedging" | Read the setup, the main result and the exposure statement (Eq. 1.6). Theory only. | No empirical test. |
| S8 | Golez & Jackwerth (2010 WP; JFE 106(3), 566-585, 2012), "Pinning in the S&P 500 futures" | NOT read in full. Konstanz PDF download timed out twice. Abstract from the search snippet only. | Full text not seen. |
| S9 | Avellaneda & Lipkin (2003), "A market-induced mechanism for stock pinning", QF 3, 417-425 | Read the NYU presentation slides (23 pp). The QF paper was not retrieved. | Slides, not the paper. |
| S10 | Alexander, Deng, Feng & Wan (arXiv:2109.02776 v2, Mar 2022), "Net buying pressure and the information in bitcoin option trades" | Read definitions and the main regression results (Deribit tick data). | No OOS test. |
| S11 | Almeida, Grith, Miftachov & Wang (arXiv:2410.15195 v2, Aug 2025), "Risk premia in the Bitcoin market" | Read data, method and headline premia. Not a dealer-flow paper. | Variance premium only. |
| S12 | Glassnode, taker-flow-based gamma exposure (research.glassnode.com/gamma-exposure, note dated 18 Dec 2025 chart) | Read via fetch. Vendor product. Methodology appendix withheld. | No validation reported. |
| S13 | Shi (2026), Princeton ORFE senior thesis, "0DTE options and intraday volatility" (8 Apr 2026) | Abstract page only. PDF not retrieved. | Abstract-level; S&P 500, not crypto. |
| S14 | Dim, Eraker & Vilkov (2024), "0DTEs: trading, gamma risk and volatility propagation", SSRN 4692190 | BLOCKED. SSRN returns 403 for both the abstract and the paper. Secondary descriptions only (section 3.8). | Not read. |
| S15 | Dalvi & LaFond (NYU Stern, 21 May 2026), "Effects of weekly option introduction..." | Abstract read. Not about dealer gamma. Low relevance. | Off-topic for hedging mechanics. |

Not found: an academic paper on Deribit gamma pinning, Deribit max pain, or a crypto vanna or charm
study. The vanna search returned only practitioner material and the theory in S7. The crypto
max-pain claims are analytics posts and a vendor tracker (CryptoQuant: settlement within 2% of max
pain on 34 of 46 expiries). They are not tested for controls. Treat them as unverified.

## 1. Definitions and hedging signs

Let V be an option value, S the spot, sigma the implied vol, t calendar time, tau = T - t time to expiry.
Greeks are per unit of the option; the dealer's book is the sum over positions (position signs matter).

- Delta: Delta = dV/dS.
- Gamma: Gamma = d2V/dS2 = dDelta/dS.
- Vega: Vega = dV/dsigma.
- Vanna: Vanna = d2V/(dS dsigma) = dDelta/dsigma = dVega/dS. This is "dDelta/dVol".
- Charm: Charm = dDelta/dt = -dDelta/dtau. This is "dDelta/dTime" (S5 defines C = -dDelta/dtau).
- Vomma (volga): Vomma = d2V/dsigma2 = dVega/dsigma.

Forced spot trade for a dealer book with net greeks G_net (sign = the dealer's position). The dealer
keeps total delta at zero by trading spot, so for a small move in the driver:

| Driver | Book delta changes by | Dealer must trade spot by | Sign reading |
|---|---|---|---|
| Spot move dS | Gamma_net * dS | -Gamma_net * dS | Short gamma (Gamma_net < 0): buy after a rise, sell after a fall (amplifies). Long gamma: the reverse (pins). |
| Vol move dsigma | Vanna_net * dsigma | -Vanna_net * dsigma | Net short vanna (< 0) and vol up: buy spot. Vol down: sell spot. |
| Time passes dt | Charm_net * dt | -Charm_net * dt | Net charm negative (delta drifts down) means buying spot as time passes. S5 shows this is the overnight buy before 3rd-Friday expiry. |
| Vol move dsigma | Vomma_net * dsigma changes vega, not delta | No direct spot trade. Vega is re-hedged in options, so the flow lands in the vol surface. | Spot effect only through the delta of the option hedges. |

Checks I made by hand: a dealer long OTM calls has charm < 0 near expiry (its delta decays toward zero),
so it must buy spot as time passes, which is what S5 reports. A short-gamma dealer buys after a rise,
which matches S4's momentum sign.

## 2. Equity sources, one by one

### S1. Ni, Pearson & Poteshman (2005), NOT read in full
- Claim (from the abstract and from S2's description): closing prices of optionable stocks cluster at
  strikes on expiration dates. The authors attribute this to hedge rebalancing by option market makers
  and to price manipulation by firm proprietary traders. Average shift of at least 16.5 bp per
  expiration date (abstract, via OptionMetrics page).
- Sign (from S2, theory section): clustering when delta-hedgers have net purchased option positions at
  expiry, and de-clustering when they have net written ones.
- Identification: CBOE open-interest data (buy/sell by investor type), so the dealer side is observed
  as a residual of customer and firm positions. This is an identity, not a guess, and it is the
  stronger identification in the literature.
- Survived out of sample: not known to me.

### S2. Pearson, Poteshman & White (2006), preliminary draft (internal use only)
- Claim: option market makers' net gamma, built from CBOE customer open interest, is negatively
  related to daily absolute stock returns, for stocks with listed options.
- Identification: the sum of market-maker, customer and firm open interest is zero on each series, so
  NetDelta_MM = -(customer + firm proprietary) is observed (Sec. 3). Gammas from Black-Scholes or
  OptionMetrics IvyDB.
- Key table: Table 2 (p.20). Average coefficient on the change in net gamma is -0.000543, t = -7.62,
  across 2,308 stocks. Standard deviation of MM normalised net gamma is 6.77. One SD shock implies
  -0.000543 * 6.77 = -36.8 bp of absolute return, about 11.8% of the average absolute return of 310 bp.
- Subsamples (Table 4): 1990-1995 and 1996-2001 both negative and significant; magnitude differs.
  This is a split-sample check, not an OOS test.
- Effect size: about 12% of daily absolute return on average.
- OOS: none, and the draft says not to quote it. Use it as a hypothesis source only.

### S3. Barbon & Buraschi (2020 WP), "Gamma fragility"
- Claim: aggregate dealer gamma imbalance in illiquid markets predicts the volatility of daily returns,
  intraday momentum/reversal, and flash-crash-type fragility. Distinct from information and
  funding-liquidity channels.
- Data: OptionMetrics IvyDB, options on about 280 stocks plus indices, 1996-2017. TAQ for intraday
  returns (Sec. II.A, III).
- Proxy (Sec. II.B, Eqs. 1-4): dollar open interest times dollar gamma, summed over strikes and
  maturities, separately for calls and puts. Proxy 1 Gamma_IB1 = (Gamma_call$ - Gamma_put$) / ADV * 100,
  lagged one day. Proxy 1 is their preferred one, because Pan & Poteshman (2006) find that investors
  buy puts and sell calls on S&P 500 and Nasdaq (their footnote 9).
- Sign: the dealer is long calls and short puts. This is the same formula as S4's NGE (see section 2.5).
- Key results: Table II (p.18). The coefficient on lagged Gamma_IB in |R_t| regressions is negative,
  with t from -4.54 to -5.32 depending on fixed effects. One SD of gamma imbalance is associated with
  about 12 bp lower absolute daily return, against a mean absolute return of about 109 bp (about 11%).
  Table VI: the autocorrelation effect peaks at 30-minute returns, about 1% of an SD. Table VII:
  coefficient -12.3 on the daily high-low spread, so one SD is about +15 bp in spread.
- OOS: none reported. The results are in-sample over 1996-2017 and robust to controls.

### S4. Baltussen, Da, Lammers & Martens (2021), JFE
- Claim: the rest-of-day return predicts the last 30 minutes of trading ("market intraday momentum"),
  across 60+ futures from 1974 to 2020. Hedging by option market makers and leveraged-ETF rebalancing
  is a driver, with the S&P 500 test as the direct evidence. Predictability reverts over the next days,
  which fits transitory price pressure, not information (Sec. 1, p.378-380).
- Data: futures prices, 1974-2020 (intraday). S&P 500 options from OptionMetrics (1996-2017) and
  SqueezeMetrics (to May 2020). Leveraged-ETF NAVs from Bloomberg.
- Dealer sign (Sec. 4.1, p.388): "we assume that (i) all traded options are facilitated by
  delta-hedgers, (ii) call options are sold by investors and bought by option market makers, (iii) put
  options are bought by investors and sold by option market makers, (iv) option market makers hedge
  precisely their option deltas." This is an assumption. It is not observed.
- NGE (Eqs. 13-15): NGE_t = sum over calls of Gamma * OI * 100 * S, minus the same over puts, divided
  by market value.
- Key result, Table 7 (p.389): slope of r_LH on r_ROD is 0.0663 (t = 4.78) when lagged NGE < 0 (the
  table scales by 100, so read it as 6.63 x 10^-2), and 0.0082 (t = 1.03) when NGE >= 0. Adjusted R2
  3.58% for the negative-NGE subsample.
- Table 8 (p.389): interaction NGE * r_ROD = -123.04 (t = -3.42) in one specification, with the
  NGE-conditioned slope significant and the same sign under a difference-in-difference control for time.
- Footnote 8 (p.388): NGE is positive on most days. There are 2,930 negative-NGE and 3,158 positive-NGE
  days over 1996-2020. Their own proxy therefore says dealers are net LONG gamma on the majority of days,
  which conflicts with "option market makers are net short gamma" as the working premise.
- Out-of-sample: the general intraday momentum has OOS R2 of 2.88% (Table 2, Panel A, equity futures,
  column 3), with a t of 7.29 for r_ROD. The NGE-conditioned result (Tables 7-8) is in-sample only.
- Costs: at a one-tick cost on S&P 500 futures the net Sharpe stays positive (Sec. 3.5). Other
  markets are not costed. Sharpe ratios in Table 6 run 0.87-1.73 gross.
- Survived: general intraday momentum yes, by sub-period (1974-1999 vs 2000-2020, Table 5). The NGE
  conditioning is untested OOS.

### S5. Baltussen, Terstegge & Whelan (2024), "The derivative payoff bias"
- Claim: S&P 500 options settled on the a.m. Special Opening Quotation (SOQ) on 3rd Fridays
  are biased. The SOQ exceeds the prior close by 18 bp on average on those days (t = 3.5 against
  non-expiry days; Introduction). An overnight drift up into expiry is followed by a reversal at the
  SOQ. The "3rd Friday Price Spike" is confined to the a.m. settlement window. Headline wealth transfer
  of about $3.5bn per year (SPX options only) is their estimate: from call writers to call buyers
  (about $214m a month) and from put buyers to put writers (about $80m a month), Table IV.
- Mechanism tested: "unwinding of delta hedges" is rejected (net delta of expiring options is near
  zero). "Charm" is supported: on 3rd Thursdays, dealers' net charm is large and negative, which implies
  about $280m of equity buying overnight to stay delta-neutral. This matches an overnight order
  imbalance of $306m (Sec. IV-V; Table VIII).
- Dealer positions (data section): the CBOE Open-Close Volume Summary gives buy and sell volume by
  sector for SPX options. Market makers are the residual of "firms" and "customers". OptionMetrics
  greeks. The residual is an identifying assumption, not an observed position.
- Predictability (Table IX, sample 2006-2021, Sec. V and the table): univariate regression of overnight S&P 500
  return on lagged net charm, standardized. Coefficient negative and significant (t = 2.99), R2 about
  3%. Controlling for net gamma and net delta does not change the charm effect. Net delta is
  insignificant. On non-expiry days and on weekends the effect is about zero, which is what a charm
  mechanism predicts (charm is large only near expiry).
- OOS: no holdout. Pre-2003 showed no effect (sample split); the effect is linked to the emergence of
  overnight trading. Block-bootstrapped SEs and Newey-West t-stats in Table IX.
- Effect size: 18 bp on expiry days; charm R2 about 3%.

### S6. SqueezeMetrics GEX (2016, rev. 2017)
- Claim: "GEX" = sum over strikes of Gamma * OI * 100 for calls and -100 for puts. Positive GEX means
  dealers stabilise (buy lows, sell highs). Negative GEX means dealers amplify. The figure plots
  SPX next-day return dispersion against prior-day GEX (p.6), with "exponential" increase in
  volatility below zero.
- Assumptions (p.4-5): (1) all traded options are facilitated by delta-hedgers; (2) calls are sold by
  investors and bought by market makers; (3) puts are bought by investors and sold by market makers;
  (4) market makers hedge precisely to delta. These are the same signs as S4, so the two papers are
  not independent confirmations of the sign.
- Statistics: none. One plot, no regression, no OOS test. The screen "GEX near zero yields excess
  returns" is asserted and not shown (p.7).
- Vanna and charm: not in this paper. I found no SqueezeMetrics vanna or charm white paper.
  Third-party sites describe a "VEX" with a 1%-spot / -10%-IV rule. I could not confirm it from a
  primary source, so do not use it.

### S7. Herrmann & Muhle-Karbe (arXiv 2017), theory on vanna and volga
- Claim: with a Black-Scholes model recalibrated to a liquid vanilla, delta-vega hedging is
  asymptotically optimal for small uncertainty aversion. The correction depends on the vegas, gammas,
  vannas and volgas of the non-traded and traded options (abstract; Theorem 4.5).
- Exposure statement (Eq. 1.6, Sec. 1): net cash gamma, net cash vanna and net volga of the
  delta-vega hedged book. A short net gamma position is exposed to high spot vol. A short net vanna
  position is exposed to vol-of-vol positively correlated with spot. A short net volga position is
  exposed to vol-of-vol. A long net volga position is not exposed to vol-of-vol.
- Use for us: this is the cleanest statement that vanna exposure is a correlation risk
  (spot vol and vol of vol). It supports the vanna flow channel qualitatively. It is not an
  empirical test.

### S8. Golez & Jackwerth, NOT read in full
- Claim (search snippet, JFE abstract): S&P 500 futures finish closer to the at-the-money strike on
  serial expiration days. Market makers rebalance delta hedges as time decays. Notional shift of at
  least $115m per expiration day. Also reports futures pushed away from the cost-of-carry adjusted
  at-the-money strike ("anti-cross-pinning") just before S&P 500 options expiry.
- Identification and OOS: not read. Do not cite beyond the abstract.

### S9. Avellaneda & Lipkin (2003), slides (read), and the sign conflict
- Mechanism (slides p.10): "Hedgers are net long options, hence long gamma. They sell stock when it
  rises and buy stock when it falls. Since the aggregate amount of stock required is large compared to
  daily trading volume, this drives the stock to the strike price."
- Data check (slide p.21): "Data does not indicate depletion for MM net short. Instead it indicates a
  very slight pinning (unexplained). However, most pinning takes place when MM are net long (consistent
  with model)."
- This is the key sign conflict in the room (section 4.1). Long gamma pins. Short gamma amplifies, as
  in S4 and S6. Both are consistent with the Greek table in section 1.

### S10. Alexander, Deng, Feng & Wan (arXiv 2109.02776 v2), Deribit
- Claim: on Deribit, option implied vol curves respond to net buying pressure, consistent with the
  limits-to-arbitrage hypothesis: market makers charge a premium for the inventory imbalance they
  carry.
- Data: Deribit tick-level BTC options trades, Jan 2017 to Jul 2021 (volume tables). The regression
  uses hourly data over 2019-2021 (the regression section).
- Dealer signal: net buying pressure = delta-weighted difference between buyer-initiated and
  seller-initiated trades. This is a taker-flow measure, not a dealer position. It needs no
  sign assumption about who is a dealer.
- Key result (Table 7): lagged IV coefficient alpha5 is negative and highly significant for ATM, OTM and
  DOTM calls and puts. ATM call alpha5 goes from -0.458 (2019) to -0.395 (2021), a decaying trend.
  Authors note that the "limits-to-arbitrage" effect is consistent across moneyness.
- Other facts: Deribit about 80% of BTC options market (2021, Sec. 2); Jan-Jul 2021 volume about
  USD 103bn; 1-day and 2-day maturities make up about 20% of volume (Sec. 2).
- OOS: none; the decay across years is the only stability check.

### S11. Almeida et al. (arXiv 2410.15195 v2), Bitcoin variance risk premium
- Data: daily BTC prices and options from Deribit, 2014-2022. BVIX from intraday option data, built
  as the CBOE VIX-style variance swap (Appendix A.2).
- Headline: average BVRP about 14% per year, one-month horizon. The S&P 500 variance risk premium
  benchmark in the same paper is about 2% (Bollerslev, Tauchen & Zhou 2009, quoted). Bitcoin return
  premium averages 66% per year.
- Relevance: the variance premium is the cost of vomma/volga-type exposure. No dealer positions are used.

### S12. Glassnode taker-flow gamma (vendor)
- Method: the taker is the end user and the maker is the dealer, so dealer positioning is the mirror
  of cumulative taker flow by strike and maturity. Dealer inventory is converted to gamma exposure with
  greeks and spot. Coverage: BTC, ETH, SOL, XRP, PAXG on Deribit, 10-minute resolution.
- Netting: the note argues that the open-interest heuristic can misreport net dealer exposure when
  offsetting flows make the net close to zero.
- Validation: none reported. The appendix is withheld. The disclaimer calls the analysis "a limited case
  study". The only numbers are the 18 Dec 2025 BTC chart (dominant positive cluster near $86-87k).
- Use: this is the only crypto method I found that signs the dealer from taker flow. It is a vendor
  product, so the method cannot be audited from here.

### S13. Shi (2026), Princeton ORFE thesis, abstract only
- Claim: the canonical gamma-hedging feedback channel does not explain 0DTE intraday volatility. The
  hedging channel adds no meaningful predictive power for intraday variance forecasts (QLIKE and
  correlation), while other option exposures add substantially. Sample: S&P 500 index.
- OOS: a holdout comparison is implied, not described on the page. Verify from the PDF before use.

### S14. Dim, Eraker & Vilkov (2024), SSRN 4692190, BLOCKED
- Secondary descriptions only: high open-interest gamma in 0DTEs is associated with lower realised
  volatility, not amplified volatility; 0DTE carries the largest volatility risk premium of the options
  studied. These do not match S4 and S6, and I could not check the sign of their dealer proxy. Do not
  cite until read.

### S15. Dalvi & LaFond (NYU Stern, May 2026)
- Weekly option introduction raises 0-1DTE trading and market-maker intermediation. It does not test
  gamma flows. Low relevance.

## 3. Synthesis: what the equity evidence says

1. The gamma sign rule is consistent across S1/S9, S4, S3 and S6: long-gamma dealers pin (sell rallies,
   buy dips); short-gamma dealers amplify (buy rallies, sell dips). The effect is strongest near expiry
   for pinning, and across the day for momentum.
2. The best evidence on size is S2 (dealer-signed from CBOE customer data, but a preliminary draft) and
   S3 (12% of absolute daily return per SD of imbalance, in-sample). They agree on order of magnitude:
   roughly a tenth of daily absolute return, in-sample.
3. The timing evidence is strongest for the last 30 minutes before a settlement (S4, S5). S4's
   general momentum passes a sub-period check and a basic OOS R2 (2.88%). Its gamma-conditioned slope
   is in-sample only.
4. Charm is the only channel with a specific, testable date (S5): net charm predicts the overnight
   drift into 3rd-Friday SOQ settlement, with R2 about 3%. It is absent on non-expiry days, which is
   a useful placebo.
5. Vanna and volga have no empirical dealer-flow test I could find. S7 gives the theory of exposure.
6. Every equity result depends on one dealer sign assumption, and S4 and S6 use the same one. S2 is the
   only dealer-signed evidence, and it comes from an identity in the CBOE data. Seek a second, independent
   sign source before believing the size.

## 4. What transfers to crypto (Deribit)

### 4.1 The sign conflict to settle first
Avellaneda & Lipkin (S9) and Ni et al. (S1, via S2) say long-gamma dealers pin. S4, S3 and S6 say
short-gamma dealers amplify. These are one mechanism with opposite signs, so the lab's test must state
the sign of the dealer book before reading any result. The worst error is a sign flip in the proxy.
Check it by reproducing S4's Table 7 on equity data before using it on crypto.

### 4.2 Which flows are forced, and by whom
- Gamma (intraday): Deribit market makers and other option sellers (structured products, covered
  writers) hedge delta mainly in BTC and ETH perps and spot, on several venues. The Deribit tape sees
  only the option leg and part of the hedge.
- Charm (near expiry): Deribit's daily expiries settle at 08:00 UTC (Deribit convention; verify in the
  contract spec). The settlement price is the average over the 30 minutes before 08:00 UTC (S11 text).
  If so, charm flows recur on about 365 days
  per year, not the 12 SPX 3rd-Fridays in S5. This is the largest difference from equities: many more
  chances per year. Supply of chances is the first thing to count.
- Vanna: a vol move (for example DVOL) forces spot trades for dealers net vanna. Crypto vol moves are
  large (S10 notes BTC IV about 5x S&P IV in the sample), so this may be a bigger channel than in
  equities. Not tested in any source I found.
- Vomma/volga: forces option-to-option vega trades (vol surface). The indirect spot effect is second
  order.

### 4.3 What the dealer's net position is, and how anyone can know it
Three ways, none of them observed:
1. Open-interest sign assumption (S4, S6, S3): dealers long calls and short puts. On Deribit this is
   untested. Pan & Poteshman's evidence is for S&P 500 and Nasdaq, not for crypto.
2. Taker-flow sign (S10, S12): dealer position is the opposite of cumulative signed taker trades, delta
   weighted (S10) or gamma weighted (S12). Caveats: block and RFQ trades may not appear on the public
   tape; dealers can be on both sides; and inventory is not the same as cumulative flow, because
   dealers also hedge in other products. The Deribit trade-direction field must be checked in the
   API documentation before use. I did not verify it here.
3. Account-type residual (S5, S2): CBOE gives buy and sell volume by sector. Deribit's public data does
   not give account types, as far as I know. This is the classic route, and I could not replicate it
   for Deribit. Verify.

### 4.4 Size relative to spot and perp volume
- Size of the hedge per 1% move: with net gamma Gamma_net (in BTC per USD of spot) and spot S, a 1%
  move forces a dollar hedge of about 0.01 * S^2 * Gamma_net. The sources give no crypto value for
  Gamma_net, so I did not compute one. The lab must fetch Deribit open interest and greeks, then compute
  it.
- Scale of options: Deribit about USD 103bn traded Jan-Jul 2021 (S10). Perp volume is not measured here.
  I made no ratio claim. Compute options-to-perp volume from fetched data before any sizing.

### 4.5 The cheapest decisive observation
Data needed (named before the search, per CLAUDE.md): Deribit public tick trades for BTC options and
BTC perps (instrument, price, size, taker direction, timestamp); daily open interest and greeks by
strike and expiry; the DVOL index; BTC perp trades; and the 08:00 UTC settlement calendar. Check
`data/` before fetching anything new.

The test, with the sign fixed ex ante:
- Build a lagged daily proxy for net gamma from taker flow (S10 / S12 style) and a charm proxy from the
  same book.
- Prediction (from S4 and S9): when the lagged proxy is negative (short gamma), the return over the last
  30 minutes before 08:00 UTC on the BTC perp is positively related to the rest-of-day return. When it
  is positive, the slope is about zero or negative.
- Placebo: the same regression on days when the expiry set has no charm, and a sign-flipped proxy,
  which must show nothing.
- Vanna version: DVOL change times a vanna proxy predicts the next-day spot return.
- Power and break-even are not computed here. Write them in the PREREG before the freeze.

### 4.6 The main reason it might not work
1. The dealer sign is unknown on Deribit. A wrong sign flips the prediction and nothing else.
2. The hedge lands on perps and other venues, so the Deribit tape sees only part of the flow.
3. Crypto spot is driven by news and 24/7 flows, which may swamp a 30-minute settlement window.
4. The evidence is in-sample, and the one long-run check (S10) shows a decaying coefficient. Crowding
   may already have removed the effect.
5. Costs: perp taker fees and spread at the settlement window may consume a thin edge.

## 5. Pre-mortem (five lines, before any test)
1. It failed because the taker-flow sign is the mirror of the dealer book only when dealers are not on
   both sides, and on Deribit they often are.
2. It failed because the hedge is done in perps on other venues, so the Deribit proxy measures noise.
3. It failed because the 30 minutes before 08:00 UTC contain news-driven flow that dominates the drift.
4. It failed because the equity effect is in-sample and has decayed (S10's alpha5 falls each year).
5. It failed because costs at the settlement window exceed the gross drift.
If any of these is likely, fix the design before freezing.

## 6. Open items and what I did not check
- Ni, Pearson & Poteshman (2005): full text (paywalled; SSRN 519044 blocked).
- Golez & Jackwerth: full text (Konstanz PDF timed out).
- Dim, Eraker & Vilkov (2024): full text (SSRN blocked).
- Shi (2026): PDF and holdout design.
- Avellaneda & Lipkin (2003): QF paper (only the slides were read).
- Deribit: trade-direction field semantics, open-interest and greek history, perp volume, coin-settled
  vs USDC-settled contract spec (changes the dollar mapping).
- Crypto max-pain: no academic source found.
- Glassnode: the appendix is withheld. Their sign claim is unverified.

Files read (scratch): `optlit/nipp/nipp.pdf` (S2), `optlit/bal/bal.pdf` (S4), `optlit/bb/gf.pdf` (S3),
`optlit/aea/aea.pdf` (S5), `optlit/gex/sqz.pdf` (S6), `optlit/arx3/arx.pdf` (S7),
`optlit/avel/slides.pdf` (S9), `optlit/arx1/arx.pdf` (S10), `optlit/arx2/arx.pdf` (S11).
