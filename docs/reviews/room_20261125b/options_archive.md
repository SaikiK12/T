# Options archive: every option-driven mechanism the lab has touched

Date: 2026-11-25. Author: options archivist (Haiku 5.5, read-only room member). Scope: rounds, methods and data
for options, dealer hedging, gamma, vanna, charm, vomma/volga, skew, implied vol, expiry/pinning, the variance risk
premium (VRP) and GEX. Nothing was run, ordered, downloaded or edited, apart from this file. `experiments/*/journal/`
was not opened.

Citation format: each evidence line is `path:line` followed by an exact quote. Line numbers are from `grep -n` on the
file as it stood today. The quotes were checked with a fixed-string search (see section 7).

## 0. Key facts

- **Option rounds: 14 DONE, 1 abandoned before any statistic (R408).** The DONE rounds are R209, R239, R241, R283,
  R289, R292, R295, R296, R307, R385, R409, R410, R411 and R416. Each is NULL, PARTIAL or DATA_PASS, and none passed a
  trading gate. R239 is a VRP measurement inside a battery. R238 is not an option test (its skew is an equity-return moment).
- **The Deribit option fee is assumed, not measured.** The lab uses 3 bp of the underlying per leg with "maker =
  taker". No stored file holds the option commission. The stored Deribit perp instruments do show maker and taker
  differ (1.5 bp and 3.5 bp).
- **The dealer sign was assumed in every Deribit test** (makers = dealers). The lab never observed dealer
  positions. The taker side is exact, but "maker = dealer" is not.
- **The biggest measured gap is the hedge.** In R409 the frozen cost of one unit of m is 56.2 bp a week on BTC,
  of which 38.8 bp is the hourly hedge fee (69%). The gross premium is +44 bp a week, t 4.66.
- **Data held in this checkout:** option chain snapshots only from 2026-10-21 (about 15 days, BTC/ETH/USDC) and
  BTC-only minute snapshots from 2026-10-29 to 2026-11-06. The Deribit option trade history and the DVOL series are
  not in `data/` here. The manifest marks both REFETCH, so they must be re-fetched before any new test.
- **Not tested at all:** vanna, vomma/volga, the vanna × charm cross around monthly expiries, dealer gamma × perp
  funding, and option-surface relative value. Pinning and max pain are queued only. Details in section 5.

## 1. Round-by-round record

Format: question; data; instants; costs; verdict; why it was null or partial (quoted); what the newer knowledge
changes. Flags: W = wrong instant or anchor; C = cost; S = dealer sign assumed; L = last-trade valuation;
I = in-sample selection; P = mechanism with no named payer.

### R209 vrp_v1: DVOL minus realized vol as a BTC/ETH timing signal (M138)
- Question: does a high implied-minus-realized premium time the perps?
- Data: Deribit DVOL index (data/deribit, REFETCH, absent here); klines. Experiment: `experiments/vrp_v1`.
- Instants: daily. Costs: 1x/2x/3x, "Primary 1x / 2x / 3x: in-sample +7.5 / +6.5 / +5.4 bp/day".
- Verdict: NULL. `registry/rounds.csv:33` "Primary BTC median daily +7.5 bp/day t1.06". `experiments/vrp_v1/FINDINGS.md:3`
  "Verdict: NULL."
- Why null: holdout +1.1 bp/day, and "6/8 variants lose on holdout" (registry) against "7 of 8" in
  `experiments/vrp_v1/FINDINGS.md:36` "In-sample, 7 of 8 variants earn more on long days". The registry and FINDINGS
  disagree on the count; `registry/methods.csv:139` notes it.
- Flags: I (8 variants); P (none named: the lab does not say who pays the premium on the long side); DVOL is an index,
  not a tradable price, so the signal is not a trade by itself.

### R239 fxindex_v1: FX/index battery, including VRP measurement
- Question: does VIX^2/252 minus next-21-day realized variance of the S&P carry a measurable premium, and do VIX
  reversal rules pay?
- Data: Yahoo ^VIX, ^GSPC (M215 row, `registry/methods.csv:216`). Experiment: `experiments/fxindex_v1`.
- Verdict: NULL for the rules; the VRP measurement passed discovery and validation, then failed holdout.
  `registry/rounds.csv:62` "VRP (measurement) passed discovery (t 2.55) and validation (t 5.71), failed holdout t 1.11 (2020)".
- Why partial: the measurement has no trade, and the six rules "fail discovery 2001-12".
- Flags: I (VIXREV-QQQ was a near miss, t 1.94); P (no named payer for the S&P variance premium).

### R241 volrisk_v1: SVXY in VIX contango, and VIXREV-QQQ on 2013-2026
- Question: does short-volatility timing (SVXY when VIX < VIX3M) pay after 2011?
- Data: Yahoo SVXY, ^VIX, ^VIX3M; Cboe VX files (`data/cboe`). Experiment: `experiments/volrisk_v1`.
- Instants: daily close; exit "at the 2018-02-05 open after a 0.28-pt VIX/VIX3M cross" (`registry/rounds.csv:64`).
- Verdict: NULL. `registry/rounds.csv:64` "SVXY-CONTANGO passed discovery 2011-16 (+21.6 bp/day t 2.39)".
- Why null: "holdout 2020-26 +7.5 (+19%/yr) t 1.70, fails t 2; max DD 45-66%, worst day -21.5%".
- Flags: I (the 2018 exit was chosen after seeing the cross); W (the exit uses a cross at a chosen open); P (the lab
  names no payer for the short-volatility carry).

### R283 vixpanic_v1: VIX panic onsets, long SPY/QQQ/BTC 5/10/20 d
- Question: do VIX > VIX3M and VVIX top-5% onsets lead equity or BTC returns?
- Data: `data/cboe` VIX, VIX3M, VVIX (VIX from 1990, VVIX from 2006), Yahoo, Binance klines.
- Verdict: NULL. `registry/rounds.csv:102` "No cell p <= 0.00185". 27 trials.
- Why null: "6 of 27 at p <= 0.05 (correlated cells)"; the best cell is "BOTH-QQQ 10 d +228 bp net, excess +158 bp, p 0.005".
- Flags: I (27 cells; the lead "+158 bp" is in-sample); P (tail-hedge demand is the natural payer, but it is not
  named in the test).

### R289 clockflow_v1: fixed-clock flows, including the Deribit Friday 07:30-08:00 UTC settlement window (M303)
- Question: does a price move inside the Deribit settlement TWAP window reverse after 08:00?
- Data: Binance BTC/ETH/SOL 1-minute bars (`data/`); Deribit chains from 2026-10-21 for the placebo check.
- Instants: 07:30-08:00 and 08:00 onward, Fridays. Costs: "manual web 3 bp/side" (`registry/rounds.csv:107`).
- Verdict: NULL. `registry/rounds.csv:107` "Placebos post hoc only". Settlement rule: "SETTLE rc_p 0.87 (stat 0.82)".
- Why partial: "gross ~+20 bp/trade both windows" but "+0.65 / +0.38 / +0.11 bp a day at 1x / 2x / 3x" (FINDINGS line
  66 region).
- Flags: W (the anchor is Binance's price, not Deribit's index; `experiments/clockflow_v1/FINDINGS.md:95` "Deribit's own
  index and expiry calendar" was not used); I (40 trials, placebos chosen after the run); S (the reversal is
  attributed to dealers without any dealer data).

### R292 dealerflow_v1: dealer gamma from Deribit taker flow (M308)
- Question: does dealer GEX from net taker positions predict next-day realized vol or hourly autocorrelation?
- Data: `data/deribit_trades` (41M BTC/ETH option trades from 2016 to 2026-09, taker side exact; REFETCH, absent here);
  Binance perp klines. Experiment: `experiments/dealerflow_v1`.
- Instants: UTC close GEX vs next UTC day (`experiments/dealerflow_v1/FINDINGS.md:20` "at each UTC close").
- Costs: none, since no trades.
- Verdict: NULL, 4 trials. `registry/rounds.csv:112` "Dealers (makers) short gamma 76-92% of days".
- Why null: "The hedge is a rounding error next to perp volume." (`experiments/dealerflow_v1/FINDINGS.md:55`). "Nothing
  monotone survives into validation." Best validation |t| is 1.23.
- Flags: S (`experiments/dealerflow_v1/FINDINGS.md:106` "Whether makers are dealers." is "the assumption"); I
  (`experiments/dealerflow_v1/FINDINGS.md:91` "It is one of 8 reported variant looks"); W (the open-interest GEX
  that dashboards show is not tested, `experiments/dealerflow_v1/FINDINGS.md:101` "The open-interest GEX that public
  dashboards show").

### R295 optflow_v1: Deribit option flow leading BTC/ETH perps (M311 blocks, M313 net drift)
- Question: does signed option flow lead the perp over 1, 4 or 24 hours?
- Data: Deribit taker-side trades (REFETCH, absent here). Experiment: `experiments/optflow_v1`.
- Instants: hourly flow, 1-24 h perp returns; the taker's side is exact (`experiments/optflow_v1/FINDINGS.md:17`
  "so there is no bid/ask guess").
- Costs: "every validation rule negative at 1x API (8.5 bp/side)" (`registry/rounds.csv:114`); round trip 17 bp.
- Verdict: NULL, 15 trials. `registry/rounds.csv:114` "best validation screen_delta h4 +3.02 but discovery -0.82".
- Why null: gross per trade "+0.3 to +16 bp vs 17 bp round trip" (`registry/rounds.csv:114`).
- Flags: C (17 bp round trip is the API cost; the maker case is open, `experiments/optflow_v1/FINDINGS.md:106` "At 0 fees
  a 4-hour gross of 3.5-7.5 bp could matter"); I (the +3.02 validation t has the wrong discovery sign). The taker
  side is observed, so no S flag on the direction, but the flow is not the dealer's.

### R296 charm_expiry_v1: Friday 08:00 UTC expiry (M303 dose, M309, M317)
- Question: does the expiring position, or the dealers' expiry hedge, move the perp after or inside the window?
- Data: Deribit trades (REFETCH); Binance klines_1m. Experiment: `experiments/charm_expiry_v1`.
- Instants: 07:31-07:59 window and after 08:00, Fridays, on 143-144 Fridays per coin and window
  (`experiments/charm_expiry_v1/FINDINGS.md:22`).
- Costs: "Costs are manual web, 3 / 6 / 9 bp per side" (`experiments/charm_expiry_v1/FINDINGS.md:72`); API 8.5 bp per side.
- Verdict: NULL, 5 trials. `registry/rounds.csv:115` "no pass (bar validation NW t >= 2.58 with a positive discovery t)".
- Why null: "no rule net positive at 1x (3 bp/side) in both windows" (`registry/rounds.csv:115`);
  "The largest |t| in validation is 1.55" (`experiments/charm_expiry_v1/FINDINGS.md:11`).
- Flags: S ("makers read as dealers (R292's assumption)", `experiments/charm_expiry_v1/FINDINGS.md:22`); W (the
  Binance perp, not Deribit's index TWAP, is the price path); C (manual web costs, not the maker fee on options).
  Its positive discovery-to-validation swaps (B and C "swap signs between the windows") are noise-like.

### R307 rrskew_v1: 25-delta risk reversal as a weekly perp timing signal (M174)
- Question: does the 25-delta risk reversal from trades time BTC or ETH?
- Data: every Deribit option trade (trade IV), with the COIN-M basis as the forward (`experiments/rrskew_v1/FINDINGS.md:11`
  "built from every Deribit option trade"; "The forward comes").
- Instants: daily RR, weekly position from Monday 00:00 UTC (`experiments/rrskew_v1/FINDINGS.md:16`).
- Costs: "Manual-web cost is 3 bp per side at 1x" (`experiments/rrskew_v1/FINDINGS.md:16`); "Costs do not matter here."
  (`experiments/rrskew_v1/FINDINGS.md:70`).
- Verdict: NULL, 24 trials. `registry/rounds.csv:126` "pick ETH 30d chg7 follow (disc +103.5 bp/wk t 1.67) fails".
- Why null: "valid +111.7 t 1.49, w/o best 10 -44.5". The best validation t is 2.67 on a book that lost in discovery
  (`experiments/rrskew_v1/FINDINGS.md:76`).
- Flags: L (the RR is built from trade IVs, the last traded vol of each trade, not from quotes); I
  ("ETH 90d z follow valid +194 t 2.67 but disc -24.8 (not pickable, post hoc)" in `registry/rounds.csv:126`);
  P (the dissertation's risk-reversal payer is not named).

### R385 dvolbeta_v1: DVOL-beta sort (M456, sort half only)
- Question: does a coin's beta to DVOL changes sort the perps into returns?
- Data: DVOL (REFETCH, absent here); Binance perps. Experiment: `experiments/dvolbeta_v1`.
- Costs: API 8.5/17/25.5 bp per side (`experiments/dvolbeta_v1/FINDINGS.md:7`).
- Verdict: NULL, 4 books. `registry/rounds.csv:175` "Pick ETH LH (disc net 1x t +0.76)".
- Why null: `registry/rounds.csv:175` "validates at +1.6 bp/day net 1x, t +0.15". `experiments/dvolbeta_v1/FINDINGS.md:20` "the best of the four
  was t +0.76".
- Flags: I (the pick was chosen on discovery); S not relevant; the gamma-weighted option inventory half is not tested
  (`experiments/dvolbeta_v1/FINDINGS.md:8` "the gamma-weighted option inventory half of M456").
  `experiments/dvolbeta_v1/FINDINGS.md:8`, "data/option_expiry` starts 2026-10-29", is the reason it could not be read.

### R408 vrpsell_v1: abandoned, no statistic
- Question: delta-hedged short weekly ATM straddles on Deribit BTC/ETH (M477).
- Verdict: ABANDONED. `registry/rounds.csv:194` "abandoned before any statistic". Trials 0. Continued as R409.

### R409 vrpsell_v2: delta-hedged short weekly ATM straddle (M477)
- Question: is the crypto variance risk premium tradable after costs?
- Data: hourly option flow IVs from Deribit trades (REFETCH, absent here); Binance perp minute prices; a half-spread
  measured on 2026-11-05 (`experiments/vrpsell_v1/costs_measured_20261105.json`).
- Instants: the sale is at the end of the first hour starting at 08:00 UTC on Friday (`experiments/vrpsell_v2/PREREG.md:44`
  (`experiments/vrpsell_v2/PREREG.md:44` "the first hour starting at 08:00"); (`experiments/vrpsell_v2/FINDINGS.md:10` "Every entry used the 08:00 hour.").
- Costs (m = 1): option fee "Option fee (2 legs)" -6.0 bp a week; half-spread -9.8/-11.9; hedge fee -38.8/-39.4;
  cost of one m 56.2/58.8 bp (`experiments/vrpsell_v2/FINDINGS.md:63-67`). The table is a post-hoc diagnostic
  (`experiments/vrpsell_v2/FINDINGS.md:51-53`).
- Verdict: NULL, 2 trials. `registry/rounds.csv:195` "NULL for BTC and ETH: net 1x -12.2 bp/wk (NW t -1.27, 295 weeks)".
- Gross: "Gross (m=0) +44.0/+40.8 bp/wk (t 4.66/3.50)" (`registry/rounds.csv:195`), and "break-even at 0.78x/0.69x of
  frozen costs".
- Why null: "The hedge is 69% (BTC) and 67% (ETH) of the cost." (`experiments/vrpsell_v2/FINDINGS.md:71`).
- Flags:
  - W: the sale is priced at the hour's IV from trade flow, not quotes ("the hour's amount-weighted IV minus one half-spread
    from a single snapshot", `experiments/vrpsell_v2/FINDINGS.md:102`). The entry hour is the same clock as the weekly
    08:00 settlement, which R289 flagged as a reversal window.
  - L: the premium is measured at trade IVs, a last-trade valuation, with one snapshot for the spread.
  - C: the option fee is an assumed 0.03% per leg (`experiments/vrpsell_v2/PREREG.md:56` "0.03% of the underlying per leg").
    The code states "maker = taker" (`scripts/vrpexec_rule.py` "maker = taker"), and `experiments/vrpsell_v2/FINDINGS.md:98` "Deribit's option fee is the same for maker and taker".
    Arithmetic from the table: removing the whole option fee (6.0 bp a week) still leaves the net at about -6 bp a week,
    so the fee assumption does not flip the sign by itself.
  - C: the hedge is on Binance's perp; the hedge fee used is Binance's (`scripts/vrpexec_rule.py:31` "Binance USDT-M VIP0").
  - P: the premium's payer is not named; the lab says it is the impatient buyer, which is an assumption.

### R410 vrpexec_v1: cost levers on the R409 straddle (maker sale, delta bands, maker-first hedge)
- Question: can a maker sale and cheaper hedging recover the premium?
- Data: raw Deribit leg trades for the trade-through replay (REFETCH, absent here). Experiment: `experiments/vrpexec_v1`.
- Instants: as R409. Costs: `scripts/vrpexec_rule.py:28` "OPT_FEE = 3e-4", "Deribit option fee, maker = taker".
- Verdict: NULL, 2 trials, "post-hoc after R409 (disclosed)" (`experiments/vrpexec_v1/FINDINGS.md:3`).
- Why null: "maker sale does harm. It is adversely selected." (`experiments/vrpexec_v1/FINDINGS.md:58`). Net 1x for the
  primary cell "-4.2 (t -0.38, 292 wk) / -14.6 (t -1.07, 289 wk)" (`registry/rounds.csv:197`).
- Hedge: "Maker-first orders cut the fee per coin from 5 to about 2 bp" (`experiments/vrpexec_v1/FINDINGS.md:52`). The best
  hedge cell is "+15.6 t 1.30" (BTC, taker/band20_mk) and "+8.6 t 0.54" (ETH), and it "is negative at 2x"
  (`experiments/vrpexec_v1/FINDINGS.md:79` region). None reaches t 1.5.
- Flags: I (post hoc after R409, and 12 cells); the maker fill is a replay on 1-minute trade-throughs, so it is
  optimistic if anything; S not relevant; C (the hedge fee is Binance's 5/2 bp, not Deribit's 3.5/1.5 bp, from
  `data/deribit_perps/instruments.json:8-9`). The maker sale's fills are adversely selected: "one-leg fills -43/-51 bp
  at 0x" (`registry/rounds.csv:197`).

### R411 dvolvrp_v1: DVOL at day start vs realized vol over the next 30 days (M477 item 41)
- Question: how large is the implied-minus-realized premium in the data?
- Data: DVOL (REFETCH, absent here); Binance perp hourly. Experiment: `experiments/dvolvrp_v1`.
- Verdict: DATA_PASS, a measurement, 0 trials. `experiments/dvolvrp_v1/FINDINGS.md:3` "No decision and no trade."
- Result: "DVOL - next-30d RV: BTC +8.15 vol pts (NW t 5.50, 74% of 1,897 days), ETH +5.54 (t 2.59, 67%)"
  (`registry/rounds.csv:196`). The premium "has been shrinking for five years" (`experiments/dvolvrp_v1/FINDINGS.md:35`).
- Flags: I (none, it decides nothing); the premium is gross of every cost. "A monthly straddle pays the option-side
  costs once a month" (`experiments/dvolvrp_v1/FINDINGS.md:45`) is an untested idea.

### R416 gexfilter_v1: S&P 500 GEX (SqueezeMetrics) as a BTC/ETH volatility predictor (M486)
- Question: does the S&P dealer-gamma rank predict BTC/ETH volatility beyond VIX and own lagged RV?
- Data: `data/squeezemetrics/DIX_20261106.csv` (columns date, price, dix, gex; about 3,903 rows from 2011-05-02 to
  2026-11-05; provenance `docs/provenance/squeezemetrics.json`, `registry/data_manifest.csv:86` "data/squeezemetrics,RECORDED").
- Instants: "Signal one trading day later" (`experiments/gexfilter_v1/FINDINGS.md:27`), for the US session.
- Costs: none, since it is a volatility forecast, not a trade (`experiments/gexfilter_v1/FINDINGS.md:59`).
- Verdict: NULL both coins. `registry/rounds.csv:202` "NULL both coins."
- Why null: "VIX and own lagged RV already carry it" (`registry/rounds.csv:202` "VIX and own lagged RV already carry it"); holdout t -1.30
  for BTC.
- Flags: S ("SqueezeMetrics' GEX is its own estimate." `experiments/gexfilter_v1/FINDINGS.md:55`; the dealer sign is theirs);
  W ("Publication time is unstated." `experiments/gexfilter_v1/FINDINGS.md:57`); I (2 trials, but the IS/HOLD split
  was pre-set).

### R239 and R238, not option tests but adjacent
- R238 xsbattery_v1 uses "IVOL, skew" as equity-return features (`registry/rounds.csv:61`, "Eight cross-sectional features
  (weekly mom/rev, MAX, IVOL, skew ..."). These are return moments, not options. Its skew books "correlate 0.49-0.84" with
  a high-volatility tilt (`registry/rounds.csv:61`).
- R239's VRP measurement is in section R239 above.

### Options-adjacent rounds that are not options
- R335, R405, R406 (locked carry, Binance and Deribit quarterly futures), R501-R506 (CME futures carry), R519-R527
  (Deribit linear perps, funding), R528-R529 (CME momentum and roll). These use futures and perps, not option prices.
  Listed so no one reads them as option tests.

## 2. Methods status (`registry/methods.csv`)

Status is the value in the status column of the row. Line numbers are from `grep -n` on `registry/methods.csv`.

| Method | Line | Status | Subject | Note (quoted) |
|---|---|---|---|---|
| M138 | 139 | TESTED | DVOL minus RV timing | "6 of 8 variants lose per registry, 7 of 8 per FINDINGS" |
| M174 | 175 | TESTED | 25-delta risk reversal and BVOL | "Single asset: expect null." |
| M175 | 176 | QUEUED | Max pain / gamma at Friday expiry | "Practitioner claim only; no academic paper found." |
| M180 | 181 | PARTIAL | MAX, IVOL, realised skew | untested: kurtosis, BTC-residual IVOL |
| M185 | 186 | PARTIAL | Volatility forecast horse race | "Forecast skill is unvalidated." |
| M289 | 261 | QUEUED | Expiry pinning, 48 h before Friday expiry | "Dealers long gamma near a large strike hedge against moves" |
| M300 | 272 | QUEUED | Dealer GEX from the Deribit chain, sign variants | "Replaces the guessed equity sign of M300 with data" (note on M308 at line 280) |
| M303 | 275 | TESTED | Deribit settlement window | (R289, R296) |
| M308 | 280 | TESTED | Dealer positioning from taker flow | "Assumes makers are mostly dealers (not shown)" |
| M309 | 281 | TESTED | Charm into expiry, dose response | "R289 found the reversal positive in both windows" |
| M310 | 282 | QUEUED | Vanna after FOMC | "Few events (8 FOMC a year), so low power" |
| M311 | 283 | TESTED | Block delta flow | (R295 NULL) |
| M313 | 285 | TESTED | Net drift | (R295 NULL) |
| M316 | 288 | QUEUED | Screen-maker short gamma, next-day mean reversion | "Unseen data only" (post hoc from R292) |
| M317 | 289 | TESTED | Expiry hedge unwind | (R296 NULL) |
| M440 | 346 | UNTESTED | Expiry 08:00 two-hour reversal, OI-weighted | forward recording, no result yet |
| M446 | 352 | BLOCKED | 0DTE SPX flow | "Parked behind the data cost, which is the owner's call" |
| M451 | 357 | BLOCKED | Closing momentum with dealer gamma state | options OI or flow by strike not held |
| M456 | 363 | PARTIAL | DVOL-beta sort; gamma inventory as a filter | "A state filter on a strategy that already passes" |
| M477 | 384 | PARTIAL | Crypto VRP and straddles | R408-R411 |
| M486 | 393 | PARTIAL | Equity dealer gamma levels as a crypto vol filter | (R416 NULL) |
| M495 | 402 | BLOCKED | Deribit Block RFQ as a maker | "Why speed does not win" |
| M499 | 406 | QUEUED | SqueezeMetrics DIX overnight | "Power: SPX500 overnight SD 58 bp" |
| M500 | 407 | QUEUED | Cboe SKEW overnight on index perps | "Payer: tail-hedging demand, clearer than DIX" |
| M099 | 100 | QUEUED | Option-surface slope and IV forecasts | "DVOL history is not an option surface." |
| M236 | 300 | BLOCKED | Equity-option dispersion | "Cboe paper gives legs, not a complete timing rule" |
| M237 | 301 | BLOCKED | SPX 0DTE spread scalping | "Description/chapter lead only" |
| M248 | 312 | BLOCKED | Put-call parity arbitrage | no option-chain history held |
| M249 | 313 | BLOCKED | Volatility-regime structures | "OIC/CME sources describe structures" |
| M284 | 298 | BLOCKED | Relative value across the IV surface | "TikTok proposes rich/cheap IV across strike and expiry" |
| M235 | 299 | BLOCKED | QQQ GEX-level reclaim | "One narrated setup" |
| M214 | 215 | TESTED | VIX term-structure carry | (R241 NULL) |
| M215 | 216 | TESTED | VRP measurement, VIX^2 vs S&P RV | "Measurement only; options are paid data." |
| M224 | 225 | TESTED | Short-vol timing (VIX < VIX3M) | (R241 NULL) |
| M278 | 253 | TESTED | VIX panic bottom | (R283 NULL) |
| M197 | 198 | TESTED | VIX spike reversal | (R239, R241 NULL) |
| M560 | 460 | TESTED | Deribit linear perp design gap | not an option test (R519 FAIL) |
| M561 | 461 | TESTED | Cross-venue make on Deribit linear perps | not an option test (R522 FAIL) |

Methods with no row at all, though the subject is an option mechanism: vomma/volga (no row; the sibling
`docs/reviews/room_20261125b/open_questions.md:205` "Vomma (the second derivative of price in volatility) is not tested");
vanna × charm cross; dealer gamma × perp funding (a search of `registry/methods.csv` for both "gamma" and "funding" in one
row returns no hit); option liquidation cascades (no hit).

## 3. Costs: what the lab used, and what is verified

- **Deribit option fee: assumed.** `experiments/vrpsell_v2/PREREG.md:56` "0.03% of the underlying per leg, capped at 12.5%
  of the leg price. Deribit lists `taker_commission`". The stored instrument files hold no option commission. The lab's
  own note says "(assumed from Deribit's fee schedule)" for the delivery fee (`experiments/vrpsell_v2/PREREG.md:59`).
- **Maker = taker for options: assumed.** `experiments/vrpsell_v2/FINDINGS.md:98` "Deribit's option fee is the same for maker
  and taker". Not stored, not checked.
- **Deribit perp fees: measured in a stored file.** `data/deribit_perps/instruments.json:8` «"maker_commission": 0.00015»
  and `:9` «"taker_commission": 0.00035». All 226 perp instruments in that file carry these values (computed here with
  Python: `Counter` over the file gives `(taker_commission, 0.00035): 226` and `(maker_commission, 0.00015): 226`). So on
  perps, maker and taker differ by 2 bp, and the lab's hedge fee (Binance 5/2 bp, `scripts/vrpexec_rule.py:31`) is not
  Deribit's.
- **Online check not done.** I tried the Deribit fee page (`https://www.deribit.com/kb/fees`, no fee text returned) and
  `https://docs.deribit.com/articles/fees` (HTTP 404). The option maker and taker fee is therefore unverified against a
  primary source. This is the first thing to fix before any option maker test.
- **Half-spread:** 0.9 vol points (BTC) and 1.1 (ETH) from six quotes on 2026-11-05
  (`experiments/vrpsell_v2/PREREG.md:54-55`).
- **Manual-web vs API:** manual web 3/6/9 bp per side (R296, R307); API 8.5 bp per side (R295, R296, R307, R385).

## 4. Data inventory (commands run, results)

Commands: `ls`, `find`, `du`, `head`, `wc`, `grep -n`, and `/home/user/T/.venv/bin/python` with pandas for the parquet
schemas, spans and counts. Nothing was written.

| Folder | Present here | Content and span (measured) | Option data? |
|---|---|---|---|
| `data/option_expiry/` | yes | 556 parquet files in 5 day folders; 529,808 rows; BTC only; snapshots from 2026-10-29 06:45 to 2026-11-06 10:14 UTC. Columns: ts, currency, base, instrument, expiry_ms, strike, cp, oi, volume_usd, mark_iv, mark_price, bid, ask, underlying_price, underlying_index, index_price, t_done | Yes: a minute-level BTC chain with bid, ask, mark IV and OI. The best source for expiry-window questions, but only 9 days. |
| `data/recorders/deribit_chain/` | yes | 90 parquet files in 12 day folders; 450,247 rows; currencies BTC, ETH, USDC; 2026-10-21 16:30 to 2026-11-06 14:21 UTC (hourly). Same columns without t_done | Yes: hourly chain with OI and mark IV. About 16 days. |
| `data/squeezemetrics/DIX_20261106.csv` | yes | columns date, price, dix, gex; about 3,903 rows; 2011-05-02 to 2026-11-05 | Index-level GEX from the vendor (S&P 500), not crypto. |
| `data/cboe/` | yes | 13 index series (VIX 1990-01-02 to 2026-11-17, 9,318 rows; VVIX 2006-03-06; SKEW 1990-01-02, 9,272 rows; VIX3M 2009-09-18; VIX6M 2008-01-02; VIX9D, VIX1Y, VIX1D, VXN, VXD, RVX, OVX, GVZ). Daily OHLC. `manifest.json` | Index-level implied vols and SKEW, not option chains. |
| `data/deribit_perps/` | yes | 457 files; hourly prices per coin; `instruments.json` (226 perp instruments, commissions as above) | No. Perps. |
| `data/deribit_perp_trades/` | yes | 68 parquet files, one per coin | No. Perp trades. |
| `data/deribit/` (DVOL index) | NO | manifest `registry/data_manifest.csv:17` "data/deribit,REFETCH" | Yes, DVOL (R209, R411, R385). Absent in this checkout. |
| `data/deribit_trades/` (option trades, taker side, blocks) | NO | manifest `registry/data_manifest.csv:18` "data/deribit_trades,REFETCH"; `docs/provenance/deribit_trades.json:7` «"files": 517»; 232 MB; BTC 2016-11 to 2026-09 and ETH 2019-03 onward per `docs/DATA_SOURCES.md:54` | Yes: the trade history behind R292, R295, R296, R307, R385, R409-R410. Absent here. |
| `data/binance_options/` | NO | manifest `registry/data_manifest.csv:19` "data/binance_options,REFETCH" (provenance `docs/provenance/binance_options.json` exists) | Yes, small: BTC OI about $191M in 2023 (`docs/AUCTION_AND_FLOW.md`, point 9) |
| `data/deribit_atm_windows` | provenance only | `docs/provenance/deribit_atm_windows.json` | not inspected |
| `data/fundingRate/` | yes | perp funding (not options) | the funding side of gamma × funding |

Verified data-source claims in the repo: `docs/provenance/deribit_trades.json` records 517 files; the code reads
`data.ROOT / "deribit_trades"` (`scripts/run_optflow.py:35`). The R292 and R409 runs were done on a machine where those
folders existed. This checkout cannot reproduce them.

Consistency note: `registry/methods.csv:139` says the two DVOL variant counts disagree (6 of 8 vs 7 of 8).

## 5. The NOT-TESTED list

For each: the one-line mechanism; whether the lab holds the data; the cheapest decisive observation. Status of
"data held" is from section 4.

1. **Vanna into perp drift after IV drops (FOMC, CPI).** Mechanism: when implied vol falls, dealers short puts
   (vanna < 0 for short puts) buy back hedges and lift the perp. Registry: M310 QUEUED (`registry/methods.csv:282`).
   Data: partial. FOMC dates in `lab/sessions.py` (per M310 note). DVOL is absent here (REFETCH). Chains are
   present only from 2026-10-21, too short for a 2-3 year test. Cheapest decisive observation: re-fetch DVOL and the
   FOMC list, count the events (about 8 a year, so about 30 in 2023-2026), write the power first, then one pre-registered
   read. The sibling `docs/reviews/room_20261125b/open_questions.md:42` says "NEW (M310 untested)".
2. **Vanna × charm cross around monthly and quarterly expiries.** Mechanism: an expiring monthly with large vanna and charm
   pushes dealers' delta as IV and time move together. Registry: no row (the cross is in no method). Data: no monthly
   option chain history with OI; `data/option_expiry` covers 2026-10-29 to 2026-11-06 and one monthly (2026-10-30 is
   a Friday, but the snapshot count is short); `data/deribit_trades` is REFETCH. Cheapest decisive observation: list the
   monthly and quarterly expiry dates from 2021 (a calendar, no data), then count events against the dose (expiring
   gamma) before any read. A monthly-only split was in M309's text but no monthly result is reported in
   `experiments/charm_expiry_v1/FINDINGS.md`.
3. **Vomma / volga: DVOL's own variance predicting perp realized vol beyond HAR.** Mechanism: a change in the vol
   of implied vol (variance of DVOL) signals dealers' vega and hedge changes. Registry: no row; the sibling Q10 in
   `docs/reviews/room_20261125b/open_questions.md:205`. Data: DVOL absent here (REFETCH); perp klines present.
   Cheapest decisive observation: HAR plus a DVOL-variance term, out of sample from 2023, with the HAR baseline
   reproduced first (`experiments/dealerflow_v1` used the same HAR base; R292's HAR R2 was 0.52 BTC, 0.45 ETH).
4. **Gamma × funding on perps.** Mechanism: when net dealer gamma is short, dealers hedge in the perp and the funding
   rate moves; funding is paid by the crowded side. Registry: no row joins gamma and funding; R292's gamma state and
   the funding series are both present in the lab only separately. Data: funding held (`data/fundingRate/`); dealer
   gamma needs `data/deribit_trades` (REFETCH). Cheapest decisive observation: regress 8-hour funding on R292's
   `short` flag (1 when dealers are short gamma) with the perp's own lagged funding, using only the R292 data window
   (2021-2026). The payer is named: the crowded side pays funding. This is the cleanest untested pair.
5. **Expiry pinning and max pain.** Mechanism: dealers long gamma near a large strike hedge against moves, which pins
   the price into expiry. Registry: M175 and M289 QUEUED, "Practitioner claim only" (M175). Payer: named (dealers long
   gamma). Data: `data/recorders/deribit_chain` (2026-10-21 to 2026-11-06, hourly, OI present) and `data/option_expiry`
   (2026-10-29 to 2026-11-06, minute). Only about 3 weekly expiries are in the window, so the test is not decisive.
   Cheapest decisive observation: keep the recorder running to get 12+ weekly expiries (forward), and pre-register the
   distance-to-strike rule now.
6. **Open-interest GEX (dashboard convention) vs net taker GEX (R292).** Mechanism: the dashboards treat all open
   interest as dealer-held. The R292 note says this is untested by design (`experiments/dealerflow_v1/FINDINGS.md:101`).
   Data: chain OI recorded from 2026-10-21 only. Cheapest decisive observation: a forward read on the recorder with
   the dashboard convention, pre-registered, after 60+ days of data.
7. **Maker-side option straddle sale (fill quality).** Mechanism: a resting sale at the ask gets adverse selection on
   the leg that moves (R410: "one-leg fills -43/-51 bp at 0x"). Payer: the impatient option buyer who lifts the ask.
   Data: minute bid and ask only from 2026-10-29 for BTC (`data/option_expiry`); trade-through replay needs
   `data/deribit_trades` (REFETCH). Cheapest decisive observation: measure, from the minute recorder, how often the
   ask at 08:00 is lifted before the perp moves 10 bp; then decide whether a maker fill is plausible before any
   straddle run.
8. **Monthly straddle, not weekly.** Mechanism: a monthly pays the option-side costs once a month, not weekly; the
   variance premium's daily shrinkage (`experiments/dvolvrp_v1/FINDINGS.md:45`) makes the monthly the natural test.
   Data: DVOL absent here; trades absent here. Cheapest decisive observation: the R411 measurement restricted to
   monthly expiries, then one monthly straddle at the R409 cost structure, with the maker fee assumption tested first.
9. **25-delta risk reversal as a funding predictor.** Mechanism: a high RR (puts expensive) means a crowded hedging
   demand, and the Deribit floorless funding moves. Registry: R307 tested the RR as a perp timing signal only; the
   funding link is Q11 in the sibling file. Data: RR needs trade IVs (`data/deribit_trades`, REFETCH); funding held.
   Cheapest decisive observation: the existing R307 RR series against Deribit's funding, sign and 90-day z, pre-registered.
10. **SKEW (Cboe) as an overnight signal on index perps (M500).** Mechanism: tail-hedging demand moves SKEW; the index
    perp's overnight drift follows it. Data: `data/cboe/SKEW.parquet` held 1990-2026-11-17; `data/mexc_tradfi` index
    perps 2026-01-29 to 2026-10-22 (about 190 overnights, per the M499 note). Power: 12 bp detectable over all nights
    (`registry/methods.csv:407`). Cheapest decisive observation: the frozen one-rule read M500 already describes, on
    the 190 overnights.
11. **DIX as an overnight signal on index perps (M499).** Data: `data/squeezemetrics` DIX from 2011-05 to 2026-11-05
    (held, but the file is the vendor's daily rewrite; the provenance is `docs/provenance/squeezemetrics.json`). Power
    as M500. Cheapest decisive observation: the same 190-overnight read. It is not an option test, so it is listed for
    completeness.
12. **0DTE SPX option flow to the S&P (M446) and closing momentum with dealer gamma state (M451).** Mechanism: the
    dealer gamma state decides whether the last 30 minutes continue or revert. Payer: named (dealers). Data: none
    held (OPRA or a vendor). Parked behind the owner's data-cost call (`registry/methods.csv:352`). Cheapest decisive
    observation: a free public proxy only (the S&P GEX from SqueezeMetrics, already in R416, tested only as a vol
    filter). This is an open question for the owner, not for this room.
13. **Relative value across the IV surface (M284).** Mechanism: rich and cheap implied vol across strike and expiry
    matched by delta. Payer: not named. Data: none held (option chains only from 2026-10-21, and no matched pairs
    over time). Cheapest decisive observation: none until a surface history exists; start the minute chain recorder
    on more expiries.

Also note the unnamed payer cases: the variance premium (R209, R409, R411) has no named payer beyond "impatient
buyers" (an assumption); the short-vol ETF carry (R241) has none; the S&P skew and DIX have tail-hedge and dark-pool
payers (M500, M499).

## 6. Flags by round (summary of section 1)

| Round | Wrong instant or anchor | Costs | Dealer sign assumed | Last-trade valuation | In-sample selection | No named payer |
|---|---|---|---|---|---|---|
| R209 | | | | | yes (8 variants) | yes |
| R241 | yes (2018 exit at a cross) | | | | yes | yes |
| R283 | | | | | yes (27 cells) | |
| R289 | yes (Binance, not Deribit index) | manual 3 bp | yes | | yes (40 trials, placebo post hoc) | |
| R292 | | none | yes | | yes (1 of 8 looks) | |
| R295 | | API 17 bp round trip | no (taker exact) | | yes | |
| R296 | yes (Binance perp for Deribit expiry) | manual 3/6/9 bp | yes | | yes | |
| R307 | | manual 3 bp | | yes (trade IV) | yes (ETH 90d post hoc) | yes |
| R385 | | API 8.5/17/25.5 | | | yes | yes |
| R409 | yes (entry at the weekly 08:00 settlement clock) | option fee assumed; hedge on Binance | no | yes (trade IV, single snapshot) | disclosed | yes (premium) |
| R410 | | Binance hedge fee | | | yes (post hoc, 12 cells) | yes |
| R411 | | none (measurement) | | | no | yes |
| R416 | yes (publication time unstated) | none | yes (vendor sign) | | 2 trials | yes |

## 7. Verification

The quotes in this file were checked against their files with a fixed-string search, one check per quoted line. The
check is in the scratchpad (not in the repo): each `path:line` and quote pair was searched with `grep -F` in the named
file. Every quote not found is listed as a failure; any failure is corrected in this file before handing it over.

## 8. Limits of this archive

- The Deribit option trade history and the DVOL series are absent from this checkout. Every round that used them is
  described from its FINDINGS and registry, not re-read from data.
- The option maker and taker fee is unverified against a primary Deribit source (section 3). Two online attempts failed.
- The chain recorders hold about 16 days and 9 days. No option test on them is decisive yet.
- The dealer sign is the lab's assumption in every Deribit test. Nothing here observes it.
- I did not read any experiment's journal folder, as required.
