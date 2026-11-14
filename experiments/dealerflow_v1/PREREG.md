# PREREG: dealerflow_v1 (R292). Does dealer gamma, estimated from Deribit taker flow, explain the next day's volatility and its hourly autocorrelation? (M308)

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R292 (Claude block R280-R299, reserved for this lane on issue #7 since 2026-10-21).
- **Method:** M308 (dealer positioning from Deribit taker flow), from the owner's term list (`docs/AUCTION_AND_FLOW.md`,
  `docs/QUANTDATA.md`).
- **Owner (single writer):** the Claude session that froze it.
- **Code:** `scripts/run_dealerflow.py`, tested on synthetic data in `tests/test_run_dealerflow.py`:
  - each option's taker position and IV per day, point in time: a trade in the hour from 00:00 of day D + 1 is not
    known at D's close;
  - the dealer GEX sign and value against `lab/exposure.py`, and the 24-hour variant;
  - the hourly autocorrelation of a trending and a zigzag day;
  - a planted gamma effect on next-day volatility and autocorrelation is found out of sample, and an unrelated
    series is not.

  It calls `verify()` on this file first, and checks every input's sha256 against the block below. It also checks
  every Deribit flow file against its hash in the provenance record.
- **The question (a mechanism check, before any trading rule):**
  1. Does dealer gamma at a day's close explain the next UTC day's realized volatility, beyond a HAR model of
     volatility alone?
  2. Does it explain the sign of the next day's hourly return autocorrelation?

  The textbook story: dealers long gamma hedge against the move (sell rallies, buy dips), which damps volatility
  and makes returns mean-revert. Dealers short gamma hedge with the move, which amplifies it.
- **Execution mode:** none. No trades, no PnL. A pass earns a trading lane (regime switch, M308's second step) with
  its own id and costs.
- **Gate:** 0.
  - The perp bars were read by R289-R291 and R293.
  - No lane has read the Deribit trade history.

## What the author has seen
- **The fetch log and the provenance record:** per month, the counts of trades, block trades, flow rows and
  requests, for BTC (from 2016-11) and ETH (from 2019-03).
- **Flow file layouts:** the column names of one BTC flow file and one BTC block file.
- **Deribit's IV unit** is percent, from its API docs. The runner fails if the median traded IV in the window is not
  between 10 and 300.
- **A plumbing run on the real files, before this freeze:**
  - BTC 5,649,038 flow rows over 94,155 options; ETH 4,073,625 over 91,038;
  - 1,493,750 and 1,235,326 option-days;
  - 1,005 discovery and 1,004 validation days with a defined feature per coin;
  - run time and the counts of defined targets.

  No GEX value, feature value, target or statistic was printed.
- **R291** (`vpin_v1`): strong volatility persistence at 1 hour (HAR R² about 0.65). R291 is hourly; this lane is
  daily, so its HAR fit is new.
- **R289:** on Fridays a move inside Deribit's 07:30-08:00 UTC settlement window reverses. That is about expiry,
  not this lane's daily gamma.
- **R293:** the next day's efficiency ratio is only weakly predictable. No volatility forecast was compared there.
- **The Deribit chain recorder digest** (`experiments/recorders/journal/digests.csv`) holds equity-convention GEX
  from open interest since 2026-10-21. That is after this window, and it uses another sign rule.

## Inputs (frozen)

```inputs
9e2c7fd717811a58bca2fa5816b92b4bf59aaa5d9706c10af2522af04a1c82a0  data/klines_1m/BTCUSDT.parquet
7c7c05b387d59fd3e40555718c28388fb66c737602102297a34de9af9c67da70  data/klines_1m/ETHUSDT.parquet
9ab09b14cc503d6ead4ca14ea16c0e32ed0f428a82b52c0cbf17567797d6a188  docs/provenance/deribit_trades.json
6ca16dedc98b89f2dfee199c2f06936db2b16005aac65493a500f20797ab5abe  lab/exposure.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
2c4e93aa4586f41098ee65e8b097c067d0a368b0d0f49c1c4844628eb176b8f1  scripts/run_vpin.py
5f717e2486dc46b600b53330f2e06653e8d3553f80831d957c9bccb317b49740  scripts/run_effratio.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
1e199500a989cb6d6f655886bd508e2b89c58e1255d8bb8dc8e8eff3a5c9a138  scripts/run_dealerflow.py
```

The Deribit flow files (`data/deribit_trades/{BTC,ETH}/flow/*.parquet`, 258) are pinned through the provenance
record, which holds each file's sha256.

## Data
- **Options:** every Deribit BTC and ETH option trade (inverse options, one coin per contract), reduced to hourly
  flow per option by `scripts/fetch_deribit_trades.py`.
  - A flow row for hour t holds trades in [t, t + 1 h), so it is known at t + 1 h.
  - Rows before 2021 are used only to build the positions of options still alive in the window. No statistic is
    computed on a pre-2021 day.
- **Perps:** Binance USD-M BTCUSDT and ETHUSDT 1-minute bars from 2021-01-01 to 2026-09-30 (`run_vpin.load_bars`;
  2020 is reserved and dropped on load).

## Dealer gamma at the close of UTC day D
- **Taker position of an option:** taker buys minus taker sells (coins), over every hour up to D's close, since its
  first trade. Makers hold the opposite.

  This is the net position of liquidity-taking flow, not of a fixed set of accounts. **Reading the makers as
  dealers is the assumption under test.**
- **Live options:** expiry (08:00 UTC) after D's close; the option's first trade on or before D.
- **IV:**
  - the option's last traded IV (amount-weighted per hour, percent), if it traded within the last 7 days (D − 6
    .. D);
  - else the median of those IVs over options of the same expiry on D;
  - else the option is dropped. The share of open interest dropped is reported.
- **Gamma:** Black-76 (`lab/exposure.py`), with:
  - F = the Binance perp close at D's close;
  - T = time from D's close to expiry, in years;
  - r = 0.
- **GEX_D** = Σ over live options of (−taker position) × gamma × F² × 0.01. That is USD per 1% move, positive when
  dealers are long gamma.
- **Features (2):**
  - **g_D** = GEX_D / ADV_D, where ADV_D is the perp's mean daily quote volume over D − 29 .. D (at least 20 days,
    each with at least 1,200 valid minutes). It is the hedge flow a 1% move asks for, as a share of a day's volume.
  - **short_D** = 1 when GEX_D < 0 (dealers short gamma), else 0.

## Targets, on day D + 1
- **Realized variance** of the 5-minute path (`run_effratio.daily`, 288 steps, at least 270 defined), squared from
  its volatility. The target is y = log of that variance.
- **Hourly autocorrelation:** ac = Σ_{h=2..24} r_h r_{h−1} / Σ_{h=1..24} r_h², over the day's 24 hourly log
  returns (r_1 starts at the previous day's last close; all 24 needed).

## Windows (by the target day D + 1)
- **Discovery:** 2021-04-01 .. 2023-12-31.
- **Validation (out of sample):** 2024-01-01 .. 2026-09-30.

## Tests (4 trials: 2 features × 2 targets)
- **Volatility (per feature):**
  - **HAR base** (OLS, per coin, fitted on discovery): y on a constant, log RV of D, log of the mean RV over D − 4
    .. D (at least 4) and over D − 21 .. D (at least 18), and a weekend flag for D + 1.
  - **The challenger** adds the feature.
  - **On validation:** the Diebold-Mariano t, which is the Newey-West t (lag 5) of the per-day mean across coins of
    e_HAR² − e_challenger²; and the pooled MSE cut, 1 − SSE_challenger / SSE_HAR.
  - **It passes when all hold:**
    - DM t ≥ 2.5;
    - MSE cut ≥ 1%;
    - the discovery coefficient has the predicted sign in both coins (g negative, short positive).
- **Autocorrelation (per feature):**
  - **Statistic:** within a window, the Newey-West t (lag 5) of the per-day sum over coins of (feature − its coin
    mean) × (next-day ac − its coin mean).
  - **It passes when both hold:**
    - the validation t has the predicted sign (g negative, short positive) with |t| ≥ 2.5;
    - the discovery t has the same sign.
- **The bar:** 2.5 is Bonferroni over the 4 trials (two-sided 5%).

## Decision
- **PARTIAL** (M308's mechanism found) if any of the 4 tests passes. What each pass earns:
  - **Volatility:** g or short becomes a regime input that later lanes may use, each in its own lane.
  - **Autocorrelation:** a trading lane with a new id (fade hourly moves when dealers are long gamma, follow them
    when short), with API costs.
- **NULL** if none passes. M308 is then TESTED, and gamma from taker flow does not enter the queue as a regime.
- **A pass with the opposite sign** (significant, but against the story) is recorded as a finding. It is not a
  pass.

## Reported (not decided on)
- **Per coin:** rows, discovery coefficients, validation MSE cut, and the HAR's validation R².
- **By tercile** of g (cuts from discovery) and by short: mean next-day HAR residual and mean next-day ac, in
  discovery and validation.
- **Variants:** GEX without block trades, and without options expiring within 24 hours. For each, the same
  statistics (DM t, MSE cut, coefficients, ac t).
- **Descriptives:** share of short-gamma days, GEX quantiles ($M per 1%), g quantiles, the correlation of g with
  log RV, and the dropped open-interest share.
- **Read against** `registry.program_trials()`.

## Outputs
`experiments/dealerflow_v1/results/`:
- `summary.json`;
- `daily.csv` (per coin and day: HAR terms, GEX, g, short, variants, dropped share, targets, window).

FINDINGS.md is written after the run.

## Known limits (written before the result)
- **Makers are not all dealers, and takers are not all customers.** Market makers also take liquidity, and
  customers post limit orders. The estimate is of liquidity-taking flow's net position.
- **Block trades:** Deribit reports a side per leg, but which party "took" a negotiated block is a convention. The
  variant without blocks shows how much they matter.
- **One venue, one product:** only Deribit's inverse BTC and ETH options. Not covered:
  - USDC-settled options;
  - OKX, Bybit, Binance and CME options.

  Deribit's share of crypto option open interest was large but fell over the window.
- **IV:** traded IVs go stale, and the Black-76 forward is the perp close with r = 0. Gamma near expiry is very
  sensitive to both.
- **The daily UTC close is a convention.** Hedging happens continuously.
- **Options listed before 2016-11 (BTC) or 2019-03 (ETH)** have no positions. They all expired long before 2021.

## Multiplicity
- Trials: 4.
- Program trials before this lane: 9,478,568 (`registry.program_trials()`, 2026-10-22, after R288).
