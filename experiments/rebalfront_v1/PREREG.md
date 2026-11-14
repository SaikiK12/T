# PREREG: rebalfront_v1 (R472). Front-running balanced-fund rebalancing on public ETF closes

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R472
- **Owner (single writer):** Claude, this session (cloud container, 2026-11-12)
- **Date registered (UTC):** 2026-11-12

Method M522, idea waves 6 and 8 (`research/intake/idea_wave8_20261112.md`). Owner request of 2026-11-12: no idea is
shelved without web research and a power check on the longest free history.

## Question
- Balanced funds (60/40 and similar) sell stocks and buy bonds after stocks outperform, and the reverse after they
  lag. Harvey, Mazzoleni and Melone (NBER w33554) find that this rebalancing predicts the next day's stock-minus-bond
  return.
- Does their published trading rule still earn, net of the cost of trade.xyz's SP500 and TLT perps, after the span
  they published (to 2023-03-17)?
- Both perps are open to French residents and ran in growth mode (0.9 bp taker) on 2026-11-12. That is why the rule
  is reachable at all.

## Source, read by the author
- **Full text [A]:** the NBER version of 2026-01-14 (SSRN 5122748), fetched as a PDF and read on 2026-11-12:
  Section 1.2, Appendix B, Table 1, Figures 2-3 and Table 6. Section 4 was read in full.
- **Signals (Appendix B):**
  - A simulated 60/40 portfolio of S&P 500 and 10-year Treasury note futures drifts with daily returns:
    w' = w(1 + Rs) / (w(1 + Rs) + (1 - w)(1 + Rb)).
  - **Threshold:** a portfolio for each band d resets to 60% when its weight is d or more from 60%. The signal is the
    drifted weight minus 60%, averaged over d = 0.0%, 0.1%, ..., 2.5% (eq. 2).
  - **Calendar:** the same drift for a portfolio that resets on the last trading day of each month.
- **Size in their sample (1997-09-10 .. 2023-03-17, futures):**
  - next-day stock-minus-bond return on Threshold: -0.4144 (HC se 0.1148);
  - on Calendar × week4 (last five trading days): -0.3029 (HC se 0.0808);
  - adjusted R² 2.4%.
- **Their rule (Section 4, Table 6):**
  - position in (S&P 500 minus 10-year note) = mean(-Threshold / 1.5%, CalMod);
  - CalMod = sign(-Calendar) on the last week of a month, sign(Calendar at day -4) on the next month's first business
    day, 0 otherwise.
  - 10.2%/yr, volatility 9.2%, Sharpe 1.11 gross, skewness 5.2.
  - Sharpe 0.90 without September 2008 - March 2009 and March 2020.
  - "Close to 1" after costs, by one sentence.
- **Later data:** footnote 32 says results through 2025 "become even stronger"; no number is published. The span
  1961-1997 is insignificant (their Table 4).

## What the author has seen
- The paper's tables and figures listed above, and wave 8's reports.
- No SPY, IEF or TLT price, and no statistic of these signals on any data.
- R471's QQQ daily bars, to 2026-11-12, only through its reported cells (Monday sessions against Bitcoin's weekend).
- General knowledge of the 2023-2026 US market path, as for any reader.

## Data (fetched after this freeze)
- `scripts/fetch_rebalfront.py --start 2002-06-01 --end 2026-11-12`:
  - Yahoo's public chart endpoint, daily SPY, IEF and TLT bars with dividend-adjusted closes, raw JSON kept. The
    parser is R471's frozen `parse_chart`.
  - FRED DTB3, the 3-month bill rate, for the equity-only report.
  - Output: `data/rebalfront/`, with a sha256 manifest. Provenance: `docs/provenance/rebalfront.json`.
- **Instruments:** SPY stands for the S&P 500 and IEF (7-10 year Treasuries, from 2002-07-30) for the 10-year note.
  Total returns of both ETFs. Their difference needs no financing, like the futures spread in the paper.

## Rule (constants in `scripts/run_rebalfront.py`)
- **Signals:** exactly as above, from daily adjusted-close returns of SPY (Rs) and IEF (Rb). Every portfolio starts
  at 60% on the first return day.
  - The signal on day t is the pre-reset drifted weight at t's close. Resets triggered at t apply from t + 1.
  - A month counts only once a later month is in the data. The unfinished last month has no month end and no week4.
- **Position:** w_t = 0.5 × (-Threshold_t / 1.5% + CalMod_t) units of (stocks minus bonds), held from close t to
  close t + 1.
  - Day -4 is the month's 4th-last trading day, counting the last day as -1.
  - Sizes are uncapped, as in the paper.
- **Two-leg return (decides):** w_t × (Rs - Rb) on day t + 1.
- **Cost:** one unit is LEG_BP = 2.9 bp a leg for each unit of notional traded: xyz growth-mode taker 0.9 bp plus 2 bp
  slippage.
  - The bond leg trades TLT at 0.45 of IEF's notional (duration about 7.3 against 16.5), so one unit of |Δw| costs
    2.9 × 1.45 = 4.2 bp.
  - 2x and 3x subtract two and three units.
  - Perp funding is not modelled (see Limits).
- **Equity-only return (reported):** w_t × (Rs - bill rate / 252) less 2.9 bp per unit of |Δw|. This is the SP500
  perp alone.

## Samples and decision (gate 0)
- **R, replication:** signal days 2002-09-03 .. 2023-03-17, the paper's published span on ETFs. It checks the
  construction.
  - It needs the Threshold slope and the Calendar × week4 slope, each on the next-day SPY - IEF return, at HC1
    t <= -2.0.
  - Threshold is regressed alone (their eq. 1). Calendar, week4 and Calendar × week4 are regressed together (their
    eq. 3 with N = 5).
- **U, decision:** signal days 2023-03-20 .. 2026-11-11, after the published span.
  - The authors saw through 2025 but published no number; 2026 is unseen by anyone and is reported alone (U2026).
- **Verdicts:**
  - **INCONCLUSIVE:** U has fewer than 800 days.
  - **NULL:** R fails either slope, or U's two-leg mean at 1x is at or below zero.
  - **PASS:** R holds, and U's two-leg mean at 1x is above zero with Newey-West (lag 5) t >= 1.0 and the 2x mean is
    above zero.
  - **PARTIAL:** R holds and U's 1x mean is above zero, but PASS fails.
- **PASS earns a forward paper lane** under a new id: SP500 and TLT on trade.xyz, with tickets frozen at each close
  and costs from the xyz book recorder. Nothing else follows from this gate; it is not evidence for real money.

## Power (stated before the read)
- **R:** the paper's t-statistics are about -3.6 (Threshold) and -3.7 (Calendar × week4) over 25.5 years. R is 20.5
  years, so about -3.2 each is expected if ETFs carry the effect. P(t <= -2.0) is about 0.89 each, about 0.8 jointly.
- **U:** about 3.6 years (about 915 days). With a true net Sharpe S, Newey-West t is about S × √3.6.
  - S = 0.8 (the paper's ex-crisis 0.90, less costs) gives E[t] 1.5, so P(PASS) is about 0.70.
  - S = 0.5 gives E[t] 0.95 and P about 0.48.
  - S = 0 gives P(t >= 1.0) about 0.16, the chance of a false PASS.
- **Why t >= 1.0 and not 2.0:** U cannot reach t 2.0 with fair power at any plausible Sharpe. A PASS here buys only
  a forward paper lane, never real money. The bar keeps the idea open when the post-sample read agrees, and closes
  it when it does not.

## Reported, not deciding
For R, U and U2026:
- both slopes;
- the Calendar slope alone;
- two-leg and equity-only results at gross, 1x, 2x and 3x (mean bp a day, Newey-West t, Sharpe, %/yr, drawdown);
- the Threshold leg and the CalMod leg alone (gross);
- turnover, and the mean and maximum of |w|.

## Trials and reading
- One trial: one frozen rule with the paper's sign. Program trials: 9,785,247 before this lane, 9,785,248 after.
- Read against `registry.program_trials()`.

## Limits
- **ETFs, not futures:** dividends and coupons are in the adjusted closes. IEF holds 7-10 year bonds, not the
  cheapest-to-deliver note. Yahoo's adjustments are its own.
- **Closes:** SPY and IEF both close at 16:00 New York; the futures spread in the paper uses settlement prices. A
  perp order would fill near, not at, the close.
- **Funding:** xyz perps pay or earn funding; the two-leg position nets most of it, but not all.
- **TLT for the bond leg:** a forward lane would trade TLT at the duration ratio. Its fit to IEF is not checked here.
- **Leverage:** |w| can reach several units in a crash month. The paper's skewness 5.2 says much of the return comes
  from such days.
- **CalMod's first-day term** follows our reading of "sign(Calendar Signal_-4)". The CalMod leg is reported alone so a
  different reading can be judged.
- **Yahoo's terms:** the endpoint is unofficial. Raw responses and hashes are kept so the read can be reproduced.

## Code
```inputs
4dfb1b22dab76061603dcbafd9496a3221ac8c397e7b70471d173b0da122dc36  scripts/run_rebalfront.py
43ad16c0cbb948ac855f0c4c492ffa2a9911f0effab96dbc8a380891798ad8d7  scripts/fetch_rebalfront.py
cf42431c0af032f60f9bfef7be990d88abdc6f8da1c2eb6d72af2c63013ad2a1  tests/test_rebalfront.py
14c57f1aed3a392a3cdae5a906512cb68cf60e9d3ca0458f6192cf608519e3ee  scripts/run_xyzwknd.py
214ff732638a0ec29a1be56d54fb2ee1d341067cd01a8cf2f73196b8542b2d47  scripts/fetch_cryptomon.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
```

## Stop rules
- One run after the fetch. Nothing is retuned afterwards; a changed idea is a new lane.
- No orders, no money, no credentials. The run writes only `experiments/rebalfront_v1/results/`.
