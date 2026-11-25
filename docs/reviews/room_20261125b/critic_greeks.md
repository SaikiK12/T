# Critic on the Greeks reflection (2026-11-25)

Scope: `docs/reviews/reflection_20261125_greeks.md` and register rows O1-O6 in `docs/reviews/open_questions.md`.
Not opened: `experiments/*/journal/`, `data/deribit_trades`, no recursive grep of `experiments/`. I read one
experiment file directly: `experiments/dealerflow_v1/FINDINGS.md:50-58`. Web facts carry a URL. Where I only saw a
search summary and not the page, I say so.

## Bottom line
- The forward-vol arithmetic is right. "Saturday is priced right" is a choice of test, not a finding. The page's own
  table gives a variance gap of about 1.65x.
- O3b "fits my prediction" is wrong by the page's own threshold. The snapshot gives 77-80%; the prediction needed 90%.
- The SPX kill (O1) uses an overnight window that the room's own summary of the paper says does not hold the price
  effect. Its 4-6 bp is not a result.
- The TSLA Fermi uses a $40bn daily volume that 20 recent sessions contradict (about $13bn). "Alive" also uses an
  all-expiry numerator, while the pin mechanism needs the expiring-day gamma, which is below O2's own 2% line at $40bn.
- R292's 0.13% is confirmed, but it is a median. The same registry row reports a snapshot about 30 times larger.

## 1. Forward vols (checked, fine)
Variance additivity, T in calendar days, sigma in %.
- Thu 08:09 snapshot: Thu→Fri = 29.40 (direct). Fri→Sat = sqrt((29.6²·1.99 − 29.4²·0.99)/1.00) = sqrt(887.8) = 29.80.
  Sat→Sun = sqrt((26.3²·2.99 − 29.6²·1.99)/1.00) = sqrt(324.7) = 18.02.
- Fri 08:09 snapshot: Fri→Sat = 42.40 (direct). Sat→Sun = sqrt((33.3²·1.99 − 42.4²·0.99)/1.00) = sqrt(426.9) = 20.66.
  Sun→Mon = sqrt((33.0²·2.99 − 33.3²·1.99)/1.00) = sqrt(1049.4) = 32.39.
- All six match the page's table (`reflection_20261125_greeks.md:114-115`).
- Straddle premium, 0.7979·σ·√(1/365): 18.02 → 75.2 bp; 20.66 → 86.3 bp; 32.39 → 135.3 bp.
  - Error (minor): "straddle 75-88 bp" (`reflection_20261125_greeks.md:126`) should read 75-86 bp.
  - Weak: "134 bp" (`reflection_20261125_greeks.md:132`) should be 135.
- Weak: the table rests on two snapshots of mark IV, with no bid/ask.

## 2. Is premium vs mean |r| the right test? (error in method)
- Saturday, 2025-26: mean |r| = 81 bp (`reflection_20261125_greeks.md:122`) against premium 75-86 bp. Ratio 0.94-1.08.
- The same Saturday: close-to-close vol 24.9% (`reflection_20261125_greeks.md:123`). Read as √365 annualized, that is
  a daily sd of 130 bp. A normal distribution would give E|r| = 0.7979 × 130 = 104 bp. The observed 81 bp gives a
  ratio of 0.78. So Saturday returns are fat-tailed: a few large moves lift the sd, not the mean absolute move.
- Consequence. The straddle price is an E|r| quantity and says "fair". Forward vol is a variance quantity and says
  realized/implied = (24.9/19.4)² = 1.65. The page reports the first and not the second.
- The 0.7979 conversion assumes normal returns. With a 0.78 ratio, it is off by about 20% here. This is a method error,
  not only a reading error.
- The right comparison depends on the trade:
  (a) Straddle held to expiry, unhedged (what the page tests): for each day, the at-the-money premium from trades in the
      same hour, against that window's |r|. Report mean and median of (|r| − premium), with SE clustered by week and a
      bootstrap. Two snapshots against a 2023-26 average is not this test.
  (b) Delta-hedged or variance exposure: compare the implied variance with realized variance (sum of squared hourly
      returns, or close-to-close) day by day.
  (c) Tradable prices: buy at the ask, sell at the bid. The "half-spread of 7.5-10 bp" (`reflection_20261125_greeks.md:129`)
      does not say whether it is in bp of spot or of premium.
  (d) Regime: 2023-24 and 2025-26 separately, and with the largest two or three weekend moves removed. The page itself
      names a fat-tail window (`reflection_20261125_greeks.md:143-144`, "the 2025-10-10 Friday-night crash").
- Fine: 0.7979 is the right normal-equivalent constant for an ATM straddle, since E|X| = √(2/π)·σ.

## 3. Square-root impact for SPX charm (weak; the kill is not established)
- Arithmetic (Y = 1, σ = 70 bp, Q = $0.30bn), impact = σ·√(Q/V):
  V = 29bn → 7.1 bp; 45bn → 5.7 bp; 53bn → 5.3 bp; 82bn → 4.2 bp. The page's "4-6 bp" (`reflection_20261125_greeks.md:81-82`)
  matches the 2024-26 volumes only. Fine.
- Y is never stated. A search summary (no page opened, https://mfe.baruch.cuny.edu/wp-content/uploads/2012/09/Chicago2016OptimalExecution.pdf)
  calls the pre-factor "of order one". Say which value is used.
- Window. σ and V are both overnight, so the law is applied consistently. The window itself is the problem:
  - The page's window ends at 09:00 New York (`reflection_20261125_greeks.md:75`, "16:00-09:00 New York, median").
    A search summary of Cboe's SOQ document (https://cdn.cboe.com/resources/spx/Settlement_of_Standard_AM_Settled_SP_500_Index_Options.pdf)
    says the SOQ uses the opening trade prices of the constituents. The PDF was not readable by my fetch.
    So the window stops before the open that sets the price.
  - The room's own summary of the paper says: "The "3rd Friday Price Spike" is confined to the a.m. settlement window."
    (`room_20261125b/options_literature.md:136`). The page measures overnight and so misses where the paper puts the effect.
- "Could it be larger?" Not shown. If the flow trades in a window that is a share f of overnight volume, and σ is held at
  70 bp, impact is 1/√f larger: f = 0.05 → 19-32 bp; f = 0.10 → 13-22 bp. But a 30-minute window has a smaller σ, about
  √(0.5/17) ≈ 0.17 of the overnight σ under random-walk scaling. That offsets much of the gain. The auction is also a single
  print, not a continuous market, so the square-root form is not obviously right. The direction is open. Measure it.
- Test: ES volume and price move in 08:00-09:30 New York against the overnight total. `reflection_20261125_greeks.md:33`
  says ES hourly bars are held. Hourly bars cannot split 09:00 from 09:30, so minute bars are needed.
- Error in the kill rule: "Worth under 2%/yr on notional" (`open_questions.md:21`) is a return on notional, not a risk-adjusted
  value. Per trade, with a 70 bp sd and 1.5 bp cost: at 5 bp edge, Sharpe 0.05 per trade and 0.17 a year over 12 trades; at
  18 bp, 0.24 per trade and 0.82 a year. Decide on that Sharpe against the lab's bar.
- Fine: 12 chances a year (monthly 3rd Fridays), 59 holdout events, SE 70/√59 = 9.1 bp, "nearly tripled" (82/29 = 2.8).

## 4. TSLA gamma Fermi
- Formula (fine): dollar gamma per 1% per contract = Γ·S²·0.01·100. At S = 397.5 this is 158,006 per unit of Γ.
- Sanity (fine): at 30 days, at the money, 45-60% vol, Γ = 0.0058-0.0078, so $0.9-1.2k per contract per 1%. The $2.4bn
  needs about 2M at-the-money-equivalent contracts. Register O2 gives 5.95M contracts (`open_questions.md:22`), so it is plausible.
- Error (input): $40bn of daily volume is "not measured" (`reflection_20261125_greeks.md:96`). The Investing.com
  historical table (https://www.investing.com/equities/tesla-motors-historical-data, fetched 2026-11-25) lists 20 sessions,
  for example "Nov 05, 2026 | 343.69 | 79.68M" and "Oct 29, 2026 | 403.30 | 22.86M".
  - Mean 34.7M shares, median 29.7M. At prices of 345-404 that is $13.1bn mean and $11.5bn median per day.
  - $40bn needs about 101M shares a day at $397.5.
  - A search summary of Tickeron (https://tickeron.com/blogs/tesla-tsla-gains-37-33-in-2025-strong-earnings-and-key-catalysts-point-to-further-upside-11388/)
    says "98 million shares a day in 2025". Low confidence, and not read on the page.
  - The Investing.com 3-month page (https://www.investing.com/pro/NASDAQGS:TSLA/explorer/volume_avg_3m) returned only "InvestingPro" to my fetch.
- With $13bn, gross is 17-19% of daily volume (mean) or 20-22% (median), and net is 6-8%. The direction is unchanged, but the
  register number is off by about 3x.
- Error (numerator mixing): "15-45 times crypto's" (`reflection_20261125_greeks.md:97`) compares net to net (2%/0.13% = 15x)
  and gross to net (6%/0.13% = 46x). Compare like with like.
- Error (main, numerator): pinning and squeezes act through the expiring series. Register O2 gives "$0.7bn expiring that day"
  (`open_questions.md:22`). At $40bn that is 1.75%, below the register's own 2% test. At $13bn it is 5.4%. So "alive" depends on
  an unmeasured volume and on which numerator is used. The page quotes the all-expiry gross.
- Weak: the threshold moved. `reflection_20261125_greeks.md:102` says "below about 0.5%, stop"; O2 says "above 2%". Pick one and say why.
- Weak: "calls-minus-puts" is a sign convention (dealers long calls, short puts), not a measured dealer position. The page's own
  argument (`reflection_20261125_greeks.md:98-99`, retail buys calls, so dealers are short calls) points to dealers short gamma,
  which is the amplifying state. The page leaves the sign open. Say which way it points and what that implies.
- Weak: gross is an upper bound on hedging, since customers' longs and shorts offset. The honest range is [net, gross].

## 5. R292 0.13% claim (confirmed, with a caveat)
- Confirmed. `registry/methods.csv:280` (row M308) reads: "median net GEX -$20M per 1% (BTC 2024-26) = 0.13% of perp ADV: hedge too small".
  The table behind it is `experiments/dealerflow_v1/FINDINGS.md:50`: "| BTC 2024-26 | 82% | −$20.1M | −0.13% |".
- Error by omission. The same registry row, `registry/methods.csv:280`, reports a single snapshot: "21:00 UTC 2026-10-21 BTC
  gamma notional $467M calls + $166M puts per 1% against about $330M per median hour". Gross $633M against about $15bn a day
  (`experiments/dealerflow_v1/FINDINGS.md:58`, "about $15B a day") is 4.2% of a day per 1%. That is about 30 times the median.
  The top decile in FINDINGS is "1.7%" for a 5% move (`FINDINGS.md:57`), so 0.34% per 1%. The snapshot is about 12 times
  the top decile.
- Denominators differ. $330M per hour × 24 = $7.9bn, not $15bn. The row uses a median hour, FINDINGS uses a mean day.
- So "the hedge is a rounding error" (`FINDINGS.md:55`) holds for the median only. Report the distribution.

## 6. Logic and the better next step

Errors
- E1. O3b "fits my O3b prediction" (`reflection_20261125_greeks.md:149`). The register prediction is "the mean Sunday straddle
  premium is at least 90% of the mean Sunday move" (`open_questions.md:24`). The Friday snapshot gives a Sunday premium of
  135 bp against a move of 169-176 bp (`reflection_20261125_greeks.md:133`), a ratio of 0.77-0.80. That is 34-41 bp of
  underpricing, above the register's 16 bp. The Sunday-to-Tuesday article window is not the O3b window either. Either the
  prediction is already contradicted, or the article's gross gap is not quantified. Neither supports "fits".
- E2. O3a is "answered" from two snapshots (`open_questions.md:23`, "2 snapshots + 2023-26 realized"). The same page says
  one snapshot "is a question, not a finding" (`reflection_20261125_greeks.md:134`). Same standard: O3a is a lead.
- E3. The premise "CME: weekend vol is about 75% of weekdays" (`reflection_20261125_greeks.md:106`, no URL). The page's own table
  gives Saturday 24.9 against a weekday mean of 45.1, which is 55%. Sunday is 45.7, which is 101%. The premise fails for Sunday,
  and Sunday is the open question.
- E4. "The strong form of the idea is dead, settled in ten minutes" (`reflection_20261125_greeks.md:131`). Overclaim; see section 2.

Weak
- W1. The Sunday row is missing from the page's table: realized close-to-close 45.7% against Sun→Mon forward vol 32.4%. Variance
  ratio (45.7/32.4)² = 1.99. Mean |r| 176 bp against premium 135 bp. Both say the snapshot Sunday is cheap.
- W2. The "about 16 bp" straddle cost mixes a half-spread of unstated unit with a fee not checked here (`reflection_20261125_greeks.md:129-130`).
- W3. "CME" and "Deribit quotes calendar time" (`reflection_20261125_greeks.md:106`) have no link.
- W4. The reflection's own lesson, "I found the weekend answer in data we already had" (`reflection_20261125_greeks.md:196`), is an overclaim.

Better next steps, ranked by value over cost
1. Before O3b data are opened, write the snapshot's implication into the register: Sunday premium/move = 0.77-0.80 against a
   0.90 threshold. If the data agree, the prediction was already falsified by the page's own table. If not, the snapshot was
   noise. Either way the test is no longer blind.
2. Replace TSLA's $40bn with the measured 20-session figure now (free, already fetched). Split the numerator by expiry. Redo O2
   with the threshold it names.
3. For O1, stop the overnight-volume kill. Measure ES volume and price in the window the paper locates (the a.m. window,
   08:00-09:30 New York). Decide on Sharpe, not return on notional.
4. For every weekend window, report the mean-|r| test and the variance test side by side, plus the median and the version
   without the top decile.
5. Remove "answered" from O3a.

Fine (checked): the forward-vol arithmetic (section 1); the 0.7979 constant; the TSLA dollar-gamma formula and its sanity
check; the SPX 12-chance and 0.4%/yr arithmetic; the holdout SE of 9 bp; the R292 0.13% quote.
