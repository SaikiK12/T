# FINDINGS: usdeflow_v1 (R488, M535)

**Verdict: NULL.** The weekly log change in USDe circulating supply does not predict the next week's change in
Hyperliquid funding. BTC rho -0.031 (circular p one-sided 0.696), ETH rho -0.085 (p 0.870); n 147 weeks each. G1
fails for both coins and G2 fails (BTC first half negative, ETH both halves negative). Both signs are negative and
neither is distinguishable from the null (p_neg 0.304 and 0.130). The negative sign is not evidence for the
hedge-impact model (Lorig, WS0033): the change target d = f(t+1) - f(t) puts a coefficient of 1 on f(t) while
funding's lag-1 rank autocorrelation is only about 0.7, and w co-moves with f(t) (rho +0.47 BTC, +0.61 ETH), so the
design pulls rho(w, d) toward zero or below without any impact mechanism. For ETH, rho(w, f(t+1)) - rho(w, f(t)) is
-0.057, which accounts for most of the observed -0.085. (Corrected after review 2026-11-13-122155.)

Run 2026-11-13 12:04 UTC, one run of `scripts/run_usdeflow.py`: PREREG sha 5e0e0896, 7 frozen inputs matched, raw
manifest fetched 2026-11-13T12:02:01Z (103 bodies, all HTTP 200, manifest sha256 5b53072c...). Output:
`results/weekly.csv`, `results/report.json`, `run.log`.

## Data as read
- Supply: DefiLlama stablecoin 146, field `tokens[].circulating.peggedUSD`, 1,064 daily points 2023-12-11 to
  2026-11-08 (points from 2026-11-09 dropped). The first week with supply above $100m at its start is the week of
  2024-01-08 (S_end of the prior week $110.1m). Weekly w: median -0.03%, 10th percentile -4.76%, 90th +13.84%.
- Funding: Hyperliquid BTC and ETH, 25,031 hourly settlements each, 2024-01-01 to 2026-11-08. Every sample week has
  at least 167 of 168 hours (minimum 150 required); no week dropped.
- Sample: weeks t 2024-01-08 to 2026-10-26 (147 rows); target weeks t+1 end by 2026-11-08.

## Decision (BTC and ETH decide jointly; trials 2)

| Coin | n | rho(w(t), d(t)) | p_one (rho_k >= rho) | p_neg | p_two | shifts | first half (n 73) | second half (n 74) |
|---|---|---|---|---|---|---|---|---|
| BTC | 147 | -0.031 | 0.696 | 0.304 | 0.616 | 138 | -0.060 | +0.041 |
| ETH | 147 | -0.085 | 0.870 | 0.130 | 0.225 | 138 | -0.033 | -0.161 |

- G1 (rho > 0 and p_one < 0.05, both coins): **fail**. G2 (both halves > 0, both coins): **fail**. Verdict NULL,
  recorded as NULL.
- Read against `registry.program_trials()`: 9,785,299 with this round's 2 trials. Nothing here approaches even its
  own null, so the program total does not change the reading.

## Reported, deciding nothing
- **Next-week funding level** f(t+1): BTC rho +0.481, ETH +0.551, circular p 0.000 (none of 138 shifts as large).
  **Post hoc** (computed after the run from `results/weekly.csv`, no decision): the concurrent rho(w(t), f(t)) is
  +0.473 (BTC) and +0.608 (ETH), and weekly mean funding has a Spearman lag-1 autocorrelation of 0.707 (BTC) and
  0.687 (ETH). So supply grows in weeks when funding is already high, and funding persists. Most of the level
  correlation is concurrent, but not all of it: the partial rank correlation of w(t) with f(t+1) given f(t) is
  +0.237 (BTC) and +0.235 (ETH), positive, in the PREREG's tested direction. It is post hoc, decides nothing and was
  not tested against any null; it is computed by `scripts/posthoc_usdeflow_v1.py` (output `results/posthoc.json`).
  The change target does not remove f(t): it subtracts it with a coefficient of 1, which is the wrong weight when
  funding's autocorrelation is about 0.7. Whether w predicts next-week funding beyond this week's funding (a
  residualized target) is an open question this lane did not test; it would be a new lane with a new id. (This
  paragraph was corrected after review 2026-11-13-122155; the earlier text said the level correlation carried no
  information beyond this week's funding, which the committed `weekly.csv` contradicts.)
- **Sunday-stamp variant** (S_end on the Sunday of week t): BTC rho -0.030 (p_one 0.710), ETH -0.101 (p_one 0.906,
  p_neg 0.094); halves BTC -0.061 / +0.039, ETH -0.071 / -0.164. Same reading.
- **Carry-book spread proxy** (mean daily v2 net of the six forward books in week t+1, fraction of book capital;
  141 paired weeks, t 2024-01-08 to 2026-09-14; four books before May 2025, when R278 B and R278 C start):

| Cost | Mean daily net | x 365 | rho(w(t), proxy(t+1)) | p_one | p_two | Mean, weeks w > 0 (71) | Mean, weeks w <= 0 (70) |
|---|---|---|---|---|---|---|---|
| 1x | 0.0438% | 15.98% | +0.127 | 0.189 | 0.356 | 0.0408% | 0.0468% |
| 2x | 0.0396% | 14.45% | +0.114 | 0.205 | 0.394 | 0.0366% | 0.0426% |
| 3x | 0.0354% | 12.92% | +0.101 | 0.227 | 0.455 | 0.0324% | 0.0384% |

  The books earned slightly less in weeks after USDe inflows than after outflows at every cost level (about 0.006
  points a day, 2.2 points a year at 2x), and the rank correlation is not distinguishable from the null. There is
  no timing rule here for the carry books.

## Costs
A predictor test, not a book: 1x/2x/3x costs do not apply to the statistic. The proxy is reported at its 1x/2x/3x
nets above (R437/R438 cost grid).

## Limits (stated before the run, unchanged)
- Supply is DefiLlama's latest vintage, one body; its daily snapshot time is not documented.
- Supply is not hedge size: stable backing carries no hedge and its share moved over the sample.
- Hyperliquid is not named as an Ethena hedge venue in any page read; this is a downstream market. Binance, Bybit,
  OKX and Deribit funding were not tested.
- BTC and ETH funding move together, so the two trials are far from independent.

## Not checked
- Ethena's own position sizes per venue (app.ethena.fi positions dashboard not read; not keyless-documented).
- Lags other than one week, other targets, and the hedge-size series. Each would be a new lane with a new id.

## What it earns
M535 is marked TESTED (NULL). No forward lane follows.
