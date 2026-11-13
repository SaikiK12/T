# PREREG: usdeflow_v1 (R488). Does the weekly change in USDe supply predict next week's funding change?

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R488
- **Owner (single writer):** Kiro sub-agent, task-adl-stress-usde-flow FEAT-003, branch `claude/websearch-organization-and-maintenance`
- **Date registered (UTC):** 2026-11-13

Method M535 (USDe net supply change as a predictor of next-week funding), lens 6 (forced or scheduled flow). Low
prior; a null is a result. Prior art: `research/intake/usde_flow_20261113.md` (WS0033-WS0036).

## Question
Is the weekly log change in USDe circulating supply w(t) rank-correlated, beyond a circular-shift null, with the
change in Hyperliquid's mean hourly funding rate from week t to week t+1, for BTC and for ETH?

**Mechanism and sign.** Ethena opens a short perp of about the minted notional on each mint and closes it on
redemption (Ethena docs, WS0034). Lorig (arXiv 2605.11263v2, WS0033) models the hedge's permanent impact as
lowering the basis, which predicts rho < 0. The tested direction, fixed by the plan before any data, is rho > 0:
inflows lead next week's funding up (mint demand chases high and persistent funding). The opposite one-sided p and
the two-sided p are reported beside it and decide nothing; a negative rho with a small p is reported as such, not as a
signal.

## Universe
- Supply: one asset, Ethena USDe, DefiLlama stablecoin id 146 (from `stablecoins.llama.fi/stablecoins`, WS0036).
- Funding: Hyperliquid BTC and ETH perps. Hyperliquid is not named as an Ethena hedge venue in any page read
  (WS0034); its funding is linked to the hedged venues by arbitrage, so this is a downstream read. No cross-section,
  no survivorship question.

## Data
Fetched once after this freeze by `scripts/fetch_usdeflow.py` into `experiments/usdeflow_v1/raw/`, with
`raw/manifest.json` (each request, HTTP status, sha256 of every body); the runner checks every body's sha256.
- `GET https://stablecoins.llama.fi/stablecoin/146` -> `raw/llama/stablecoin_146.json`, one body, DefiLlama's latest
  vintage of the whole daily history. Field: `tokens[].circulating.peggedUSD` (per-day total over chains, point
  stamped 00:00 UTC of its date in seconds); if `tokens` is absent the documented `totalCirculating[].
  totalCirculating` is used; the field used is logged. Points stamped on or after 2026-11-09 are dropped.
- `POST https://api.hyperliquid.xyz/info {"type": "fundingHistory", "coin": BTC|ETH, "startTime", "endTime"}`, paged by
  500 rows from 2024-01-01 00:00 UTC, endTime 2026-11-09 00:00 UTC minus 1 ms -> `raw/hl/<COIN>_funding_<NNN>.json`.
  `fundingRate` is the hourly rate as a fraction of notional, + when longs pay.
- Carry books (seen, committed): `experiments/carry_v2_audit_v1/results/daily.csv` and
  `experiments/carry_v2_audit_kc_v1/results/daily.csv`, engine v2, the six forward books R278 A
  `gate+hyperliquid L14d th5% K20`, R278 B `binance+mexc L14d th10% K20`, R278 C `gate+mexc L7d th10% K20`, R390 A
  `binance+gate L14d th10% K20`, R279 A `gate+kucoin L14d th5% K20`, R279 B `binance+kucoin L14d th5% K20`; daily
  net_1x/net_2x/net_3x as a fraction of book capital, to 2026-09-30.
- **Seen before this freeze.** All carry daily nets, books.csv and FINDINGS of R437/R438/R483/R487. R484
  (`experiments/llphouse_v1/`) fetched Hyperliquid BTC and ETH hourly funding for 2025-01-01..2026-11-10 and reports
  it as small (about 0.003% a trade); this agent did not open those bodies. Lorig's introduction gives USDe's market
  cap path (about $3bn within four months of the February 2024 launch, $9.3bn in August 2025, near $15bn at the
  peak, about $4bn in May 2026). General knowledge: funding was high in early 2024 and around late 2024. Endpoint
  metadata only (WS0036): the USDe id, the response keys, and the first/last timestamps of one 500-row
  fundingHistory page per coin. A plumbing run of the runner on synthetic bodies (out of repo) checked that the code
  runs. **No USDe supply value, no funding rate and no statistic relating them has been read or computed.**

## Feature lineage and point-in-time availability

| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| S_end(t) | tokens[].circulating.peggedUSD | DefiLlama, USDe, USD | the point stamped 00:00 UTC on the Monday that starts week t+1 (decides); the Sunday point of week t (reported) | DefiLlama snapshot time within the day undocumented; fetched once after the freeze | at the start of week t+1 if the snapshot is taken at the stamp; a later snapshot leaks hours of week t+1 (stated; the Sunday variant is a day earlier) | latest-vintage (one body, 2026-11-13) | missing point: w missing, week dropped from the pairs; no fill |
| w(t) | log S_end(t) - log S_end(t-1) | as above | ISO weeks, Monday 00:00 UTC to Monday 00:00 UTC | computed | as S_end(t) | latest-vintage | as above |
| f_c(t) | fundingRate | Hyperliquid, c in {BTC, ETH} perp, fraction per hour | mean of rows stamped in [Monday 00:00, next Monday 00:00) UTC of week t | Hyperliquid settlement, hourly | f(t) known at the end of week t; f(t+1) is the target | forward-captured by the venue, read once | NaN if fewer than 150 of 168 hours |
| d_c(t) | f_c(t+1) - f_c(t) | as above | weeks t and t+1 | computed | target, not a decision input | as above | NaN if either side is NaN |
| proxy_cx(t+1) | daily net_cx of the six books | R437/R438 v2 engine, fraction of book capital per day | per day the mean over books with a row; per week the mean over its 7 days | committed 2026-11-10 | reported outcome only | current-survivor symbol lists (R275/R277) | NaN unless all 7 days present |

## Rule
- **Sample.** Weeks t (ISO, Monday labels) from the first week with S_end(t-1) > $100m to the last week t whose week
  t+1 ends on or before Sunday 2026-11-08 (t <= 2026-10-26), contiguous; a coin's pairs are the weeks in that window
  where w(t) and d_c(t) are both finite.
- **Statistic (per coin).** Spearman rho(w(t), d_c(t)), average ranks.
- **Null.** w circularly shifted against d by every k in [5, n - 5] (shifts within +/-4 weeks excluded), rho_k
  each, as R486 `scripts/run_litbuyback.py` does. p_one = share of rho_k >= rho; reported p_neg = share of rho_k <=
  rho and p_two = share of |rho_k| >= |rho|.
- **Halves.** The coin's pairs in time order split at n // 2; rho in each half.

## Gates
- **G1:** rho > 0 and p_one < 0.05 for BTC and for ETH (both).
- **G2:** both halves have rho > 0 (the full rho's sign under G1) for BTC and for ETH.
- **Verdict:** **SIGNAL (gate 0)** if G1 and G2 pass, else **NULL**. The rounds registry has no SIGNAL verdict:
  SIGNAL is recorded as PARTIAL (in-sample, not confirmed), NULL as NULL.

## Splits and cost
No split beyond the halves; no search. **This is a predictor test, not a book: 1x/2x/3x costs do not apply to the
statistic.** The carry-book spread proxy is reported at its 1x/2x/3x nets (R437/R438 cost grid).

## Reported, deciding nothing (not trials)
- rho of w(t) with the level f_c(t+1), with its circular p (p_one, p_neg, p_two).
- The Sunday-stamp variant of w (S_end on the Sunday of week t) against d_c, with halves.
- Carry proxy at 1x/2x/3x: rho(w(t), proxy_cx(t+1)) with its circular p, the mean daily net (and x 365) over the
  paired weeks, and the mean in weeks with w > 0 against w <= 0.
- n, first and last week, the minimum funding hours in a sample week, w's median and 10th/90th percentiles, the
  supply at the start of the first week.

## Multiplicity
**Trials: 2** (BTC and ETH, both deciding jointly). Program trials before this round: 9,785,297
(`registry.program_trials()`); 9,785,299 with it. About 140 weekly pairs of one flow series: a p near 0.05 is weak
against the program total and the overlap of BTC and ETH funding (highly correlated) makes the two trials far from
independent.

## Evidence lineage and admission
- Canonical method id: M535. Parent rounds: R437, R438 (carry daily nets), R483 (sUSDe comparison), R484 (Hyperliquid
  funding fetched for another question). No parent tested supply against funding.
- `docs/GATES.md` SHA-256 at registration: e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926. Gate-0
  predictor test; admits nothing to real money and changes no forward lane's frozen rule.
- No across-family selection control; the result is exploratory.
- **Caveats stated before any data.** Supply is DefiLlama's latest vintage (a later revision of a past day is not
  visible; DefiLlama's snapshot time is undocumented). Supply is not hedge size: stable backing has no hedge and its
  share moves over time. Hyperliquid is not shown to be an Ethena venue. Week t's funding f(t) is concurrent with
  w(t), so d(t) mixes the concurrent and the next-week response.
- **Order:** this PREREG is frozen and the R488 rounds row appended in one commit; `scripts/fetch_usdeflow.py` runs
  only after that commit; the raw bodies and manifest are committed; then the runner runs once.

## What a result earns
- **NULL:** M535 is marked tested. Another venue, lag, target or the hedge-size series (if Ethena's positions become
  public keyless) is a new lane with a new id.
- **SIGNAL:** a forward paper check on weeks after 2026-11-08 with supply fetched weekly (publication time known).
  Not a book and not a go-real signal.

## Stop rules
One run of `scripts/run_usdeflow.py`. No new lags, targets, thresholds, venues or samples after seeing any result.
A crash fixed after the freeze is documented in FINDINGS with the changed sha.

```inputs
6fa939a0f4b4c4a8f2215171082b410db0ab7d4df4b167102db60b53dd7c14e9 scripts/fetch_usdeflow.py
f060b63412d1c7058603e9453f0e7e008f0b7ca6429bde159f1edb7717868e1f scripts/run_usdeflow.py
9c7dbc6a8592ac64f463ffb929d0e69cab4aade403e00c9d655fcaeb6b6ba2ea tests/test_run_usdeflow.py
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508 lab/prereg.py
3de6b7f29a3a3d786474b3e48444b004357c6cf2e78715e1d963f9ffe6f5fa08 experiments/carry_v2_audit_v1/results/daily.csv
8a803454b473f2fdfdbf41eff19085f053c9f208518b928cf21561a17b47004e experiments/carry_v2_audit_kc_v1/results/daily.csv
3db29618601c5dbe8c96e33c27a1233575aa5e13ee1ec75d325eae21ca99e96c research/intake/usde_flow_20261113.md
```
