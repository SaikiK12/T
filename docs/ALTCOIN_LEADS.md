# Altcoin-specific leads: research brief (2026-10-19)

Written by a research subagent and filed by the lab. Web sources were mostly read at abstract level. Nothing here was
run on lab data. Grades: A = replicated, peer-reviewed; B = peer-reviewed, single study; C = working paper or book;
D = practitioner. Each rule below is a candidate; it must be pre-registered, counted against
`registry.program_trials()`, and reported at 1x/2x/3x costs.

## Already covered by the lab (do not re-test as is)
- Alt beta to BTC: pack_v1 (R194) finds the long-alt book has beta 1.0, and a BTC hedge costs 18.3%/yr.
- Funding cross-section, OI vs price, premium, taker imbalance and volume are in the atlas (R185), and all were dead in
  2024-25.
- Breadth and dispersion contexts are in atlas_ctx (R192); BTC time-series momentum is itsm_v1 (R203).
- Data limits:
  - Prices are hourly only, so minute lead-lag and 5-minute MAX cannot be reproduced.
  - There is no market cap or supply data, so dominance, size and sector sorts need outside point-in-time data.

## Candidates

| # | Angle | Main sources (grade) | Rule on lab data | Kind, horizon |
|---|---|---|---|---|
| 1 | Cross-coin "seesaw" lead-lag | Jia, Wu, Yan & Liu, *J. Empirical Finance* 74 (2023), doi:10.1016/j.jempfin.2023.101428 (B). Guo, Sang, Tu & Wang, *JEDC* 163 (2024) (B; minute data). Kurihara & Matsumoto, *APFM* (2026), doi:10.1007/s10690-026-09589-z (B; abstract only) | For alt i: D(-i,t) = mean hourly log return of the top-5 coins by volume, excluding i. g_i = slope of r(i,t) on D(-i,t-1) over 720 h. Score = -g_i x D(-i,t). Quintile long-short; 4 h overlapping slices (primary), 1 h (secondary) | cross-sectional, 1-4 h |
| 2 | Low minus high beta | Frazzini & Pedersen, *JFE* 111 (2014) (A, equities). Sila, Mark, Kristoufek & Weber, *Financial Innovation* 11 (2025), doi:10.1186/s40854-025-00777-w (B; past beta explains only ~20% of future beta) | Weekly beta on BTC over 90 daily closes. Long the 10 lowest-beta coins, short the 10 highest, beta-neutral, hold 7 days. Gate: pre-registered beta persistence | cross-sectional, weekly |
| 3 | Residual momentum by liquidity tier | Blitz, Huij & Martens, *J. Empirical Finance* 18 (2011) (A, equities). Fieberg et al., *Quant. Finance* 23 (2023) (B). Kozlowski, Puleo & Zhou, *AEL* 28 (2021) (B) | Monthly. Regress each alt's daily return on the equal-weight top-50 ex-i over days t-365..t-1. Score = sum of residuals t-365..t-31 divided by residual std. Quintile long-short, hold 30 days, separately for liquidity ranks 1-10 and 11-50. Must beat plain 30-day momentum | cross-sectional, monthly |
| 4 | MAX / lottery sign contest | Ozdamar, Akdeniz & Sensoy, *Financial Innovation* 7 (2021), doi:10.1186/s40854-021-00291-9 (B; positive). Bali, Cakici & Whitelaw, *JFE* 99 (2011) (A, equities; negative). Yadav, *SEF* (2025), doi:10.1108/SEF-07-2024-0461 (C) | Weekly: MAX = maximum of 168 hourly log returns, residualised on ln(30-day quote volume). Two arms with opposite signs, quintiles, hold 7 days | cross-sectional, weekly |
| 5 | Perp premium orthogonal to funding | Chi, Hao, Hu & Ran, *J. Futures Markets* 43 (2023), doi:10.1002/fut.22425 (B; expiry-futures basis, majors) | Weekly: 7-day mean premium index, residualised cross-sectionally on 7-day mean funding. Long top quintile, short bottom, hold 7 days | cross-sectional, weekly |
| 6 | Correlation-cluster rotation (sector proxy) | Moskowitz & Grinblatt, *J. Finance* 54 (1999) (A, equities); no crypto sector paper found | Monthly: average-linkage clusters on 90-day correlations of the top 50 ex-BTC. Long the best cluster, short the worst by 30-day return, hold 30 days | cluster, monthly |
| 7 | Alt-season regime (ETH/BTC trend) | Practitioner only (D) | Sign of the 60-day ETH/BTC log change sets alts vs BTC. Few regime episodes | time series, daily |
| 8 | Pairs within clusters | Gatev, Goetzmann & Rouwenhorst, *RFS* 19 (2006) (A/B, equities). Crypto pairs lose after costs in recent work (B/C) | Engle-Granger, z-score entry at 2 and exit at 0 | pairs, days |

Ranked to pre-register first: 1, 2, 3, 4, 5. Not recommended now: 6 (no crypto evidence), 7 (proxy problem), 8 (costs).

## Lab note
Item 1 is the most direct answer to "other coins' charts lead": it asks whether the big coins' last hour predicts each
alt's next hours, using only the hourly klines already in the archive. The literature finds the effect at minute
horizons, so the hourly version may be weak; the 4 h slice primary keeps costs near the flow books'.
