# PREREG: tlteom_v1 (R473). The end-of-month Treasury rally on TLT, priced for trade.xyz's TLT perp

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R473
- **Owner (single writer):** Claude, this session (cloud container, 2026-11-12)
- **Date registered (UTC):** 2026-11-12

Method M528 (new). Owner request of 2026-11-12: no idea is shelved without web research and a power check on the
longest free history. Found while R472 (M522) waited for its data; it uses the same xyz TLT perp.

## Question
- Treasury coupon securities rise in the last days of each month and are flat at other times. Hartley and Schwarz
  link this to month-end purchases by insurers and index funds, concentrated in the securities that join the
  Treasury index at month end.
- Does a long TLT position over the last three trading days of each month still earn after their sample (1990-2018),
  net of trade.xyz's TLT perp cost and funding?
- xyz:TLT is open to French residents and ran in growth mode (0.9 bp taker) on 2026-11-12. That is why the trade is
  reachable at all.

## Source, read by the author
- **Full text [A]:** Hartley and Schwarz, "Predictable End-of-Month Treasury Returns" (Rodney L. White Center working
  paper 17-19, 2019), fetched as a PDF and read on 2026-11-12: introduction, Sections 2.2-2.3, Tables 1-5.
- **Their sample:** 1990-2018; modelled zero-coupon 2-, 5- and 10-year notes; excess over the repo rate.
- **Size at 10 years (Table 1, the last t days, percent a month, se in brackets):**
  - t = 1: 0.14 (0.03); t = 2: 0.20 (0.04); t = 3: 0.25 (0.05); t = 5: 0.28 (0.06).
  - All other days: t = 3 gives 0.07 (0.13), not significant.
- **Sharpe (Table 3, annualized from 12 holdings a year):** 0.85, 0.87 and 0.88 at t = 1, 2 and 3. The text says
  about 1 after costs.
- **Stability (Table 4, five-year windows, t = 2):** positive in every window; 2015-2019 is smaller but significant.
  A Bai-Perron test finds no break.
- **Mechanism:** insurers' net Treasury purchases peak on the last day of the month, in the bonds added to the
  benchmark index. A New York Fed note (Dyer, Fleming and Shachar, Liberty Street Economics, 2024-09-24, read on
  2026-11-12) finds benchmark note and bond volume about 46% higher on the last trading day of the month since 2020.
  It links this to asset managers who track indices rebalanced at month end.

## Public reports on TLT, seen before this freeze (summaries only, no data)
- CXO Advisory (2019) summarized the paper. It said a separate CXO test found that TLT since mid-2002 does not
  corroborate it. That test is paywalled and was not read.
- SentimentTrader (from a search summary; the post was not opened): TLT held only on the last five trading days of
  each month since 2002 turned $1 into $2.85. All other days turned $1 into $0.83.
- A Substack note (Beyond Passive, data to 2025-06): the long TLT Sharpe is near 1.0 at two to three days before
  month end. No split by period.
- A Substack note (Valuelytica) compares 2003-2022 with 2016-2025. In the later window the positive returns are
  concentrated in the final trading days, and the middle of the month turned negative. A commenter reports a flat
  2023-2024 and a recovery in 2025.
- **So U below is not unseen by the public.** Bloggers have looked at TLT through 2025 without publishing a
  post-2018 test. Only forward evidence is clean; this gate decides whether that forward lane is worth running.

## What the author has seen
- The paper's tables and the reports above.
- No TLT or IEF price, and no statistic of this rule on any data. R472's fetch of TLT (data/rebalfront, 02:59 UTC)
  has not been opened.

## Data (fetched after this freeze)
- `scripts/fetch_tlteom.py --start 2002-06-01 --end 2026-11-12`:
  - Yahoo's public chart endpoint, daily TLT and IEF bars (close, and the dividend-adjusted close), raw JSON kept.
    The parser is R471's frozen `parse_chart`.
  - Output: `data/tlteom/`, with a sha256 manifest. Provenance: `docs/provenance/tlteom.json`.

## Rule (constants in `scripts/run_tlteom.py`)
- **Window:** for each complete month, buy at the close three trading days before the month's last trading day and
  sell at the last trading day's close.
  - That holds the last three daily returns, as in the paper's t = 3.
  - The month in progress at the end of the data does not count.
- **Return:** TLT's close-to-close price change. A perp on TLT tracks the price, not the total return. Yahoo's close
  is not adjusted for dividends, and TLT normally goes ex-dividend on a month's first trading day, outside the window.
- **Cost:**
  - One round trip is 2 × 2.9 bp = 5.8 bp: xyz growth-mode taker 0.9 bp plus 2 bp slippage, per leg.
  - 2x and 3x subtract two and three round trips.
  - Funding: the long pays 5.5%/yr over the calendar days held at every cost multiple. That is R470's median
    funding on xyz stock perps; TLT's own funding is not checked.

## Samples and decision (gate 0)
- **R, replication:** month-ends 2002-08 .. 2018-12 (197), inside the paper's sample.
  - R holds if the gross mean is above zero at t >= 2.0.
- **U, decision:** month-ends 2019-01 .. 2026-10 (94), after the paper's sample.
- **Verdicts:**
  - **INCONCLUSIVE:** U has fewer than 80 months.
  - **NULL:** R fails, or U's 1x net mean is at or below zero.
  - **PASS:** R holds, and U's 1x net mean is above zero at t >= 1.0, and its 2x net mean is above zero.
  - **PARTIAL:** R holds and U's 1x net mean is above zero, but PASS fails.
- The t-statistic is the plain one on monthly returns; the holdings do not overlap.
- **PASS earns a forward paper lane** under a new id: xyz:TLT, with a ticket frozen at each entry close, the exit at
  the month's last close, and costs and funding from the xyz recorders. Nothing else follows from this gate; it is not
  evidence for real money.

## Power (stated before the read, from public figures; no data read)
- **Assumptions:**
  - TLT's daily sd is about 0.95%, so a three-day hold has an sd of about 165 bp.
  - TLT's duration (about 16.5) is about 1.7 times a 10-year zero's. The paper's 25 bp at t = 3 would be about 40 bp
    on TLT if the effect scales with duration. The public TLT reports imply about 30-40 bp a month over five days.
- **R (197 months):** at 35 bp gross, E[t] is about 3.0 and P(t >= 2) about 0.84.
- **U (94 months):**
  - Cost at 1x: 5.8 bp, plus funding of about 6.8 bp (about 4.5 calendar days held), so about 12.6 bp.
  - At 35 bp gross (net 22), E[t] is about 1.3 and P(PASS) about 0.6.
  - At 25 bp gross (net 12), E[t] is 0.7 and P about 0.38.
  - At 0 gross, P(t >= 1) is about 0.04, the chance of a false PASS.
- **Why t >= 1.0:** a PASS buys only a forward paper lane, as in R472. U cannot reach t 2 with fair power unless the
  effect is undiminished.

## Reported, not deciding
For R and U:
- gross, net at 1x, 2x and 3x, and net 1x with funding at 0% and 11%/yr;
- the dividend-adjusted gross;
- windows t = 1, 2, 3 and 5 (gross and net 1x);
- IEF over the same window (gross and net 1x), as a check of the maturity gradient;
- the rest of the month (dividend-adjusted, from the previous month-end close to the entry close);
- U's gross mean by calendar year.

Each row gives the mean, sd, t, annualized Sharpe, hit rate and extremes.

## Trials and reading
- One trial: one frozen rule (TLT, t = 3, long). Program trials: 9,785,248 before this lane, 9,785,249 after.
- Read against `registry.program_trials()` and next to R472 (M522), whose CalMod leg also trades bonds against
  stocks in the last week of the month.

## Limits
- **ETF, not the perp:** xyz:TLT's history is too short for a test. Its funding, oracle at the 16:00 close and
  book depth at month end are assumed.
- **Funding:** 5.5%/yr is a stock-perp median. A long-TLT crowd could pay more at month end.
- **Closes:** an order fills near, not at, the 16:00 New York close, and the perp's oracle after 16:00 is xyz's own.
- **Dividends:** if an ex-dividend date falls inside a window, the price return shows the drop and the perp would
  pay it. The dividend-adjusted gross is reported to show the difference.
- **Public knowledge:** the effect is widely published. Crowding could have moved it earlier in the month, which this
  window would miss.
- **Yahoo's terms:** the endpoint is unofficial. Raw responses and hashes are kept so the read can be reproduced.

## Code
```inputs
1ee9ea072d0d48e3cacb16a006d668290e2ff19bfbc0c784a46bbc740f633fef  scripts/run_tlteom.py
17a385241a7ad076878e9a5f3e4b3b6e486c5a6f6a3ab2a1ad71cac7d80fe19d  scripts/fetch_tlteom.py
a9b8f9b607bd7f0f357c4f38ae6545074d0bbfc3f9d6720e1f4b95dfcfa9ab82  tests/test_tlteom.py
14c57f1aed3a392a3cdae5a906512cb68cf60e9d3ca0458f6192cf608519e3ee  scripts/run_xyzwknd.py
214ff732638a0ec29a1be56d54fb2ee1d341067cd01a8cf2f73196b8542b2d47  scripts/fetch_cryptomon.py
```

## Stop rules
- One run after the fetch. Nothing is retuned afterwards; a changed idea is a new lane.
- No orders, no money, no credentials. The run writes only `experiments/tlteom_v1/results/`.
