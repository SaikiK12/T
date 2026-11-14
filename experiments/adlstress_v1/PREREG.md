# PREREG: adlstress_v1 (R487). How much could ADL on 2025-10-10 have cost the carry books, at worst?

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R487
- **Owner (single writer):** Kiro sub-agent, task-adl-stress-usde-flow FEAT-002, branch `claude/websearch-organization-and-maintenance`
- **Date registered (UTC):** 2026-11-13

Method M534 (ADL stress bound on the audited carry books), lens 5 (red team on current leads). Gate 0 on seen carry
rows; only the venues' 2025-10-10 candles are new.

## Question
If, on 2025-10-10, every pair's profitable leg on a venue documented to have run ADL that day had been closed, and the
other leg had stayed naked from the day's best to its worst print and then been re-hedged at one extra round trip,
would the loss exceed one month of each forward carry book's v2 net at 2x costs?

**Why it matters for the best-PnL objective.** R483 found three of these books beat sUSDe at 2x. Their daily nets use
last-trade marks and contain no ADL event, so the tail they carry on a crash day is unpriced. A bound below one
month of net means ADL on that day could not have undone the books' edge over a year; a bound above it means the
reported net omits a risk of the same order as the edge.

**This is a bound, not an estimate.** Per-account ADL incidence is not public keyless (Chitra, arXiv 2512.01112:
Binance's account-level ADL data is not public). The bound assumes every eligible pair was hit, the ADL'd leg's
gain offsets nothing and the naked leg's loss is the full high-low range. No liquidation cap is applied: the engine
(`lab/xfund_v2.py`) defines no margin, so a margin-capped variant is not modeled.

## Universe
- Trades: `experiments/carry_v2_audit_v1/results/trades_v2.csv` (R437, seven books) and
  `experiments/carry_v2_audit_kc_v1/results/trades_v2.csv` (R438, two books), engine v2 (fixed quantity
  q = 1 / entry price per leg, one unit of entry notional per leg).
- Pairs exposed over the UTC day D = 2025-10-10: `entry_day <= D < exit_day`. Engine timing (`lab/xfund_v2.py`,
  `lab/xfund.py`): day d's instant is 00:00 UTC; a pair entered on day d holds over d -> d + 1 and a pair exiting on
  day d is closed at 00:00 UTC of d. 174 pairs. **Deviation from the plan, stated before any candle:** the plan's
  `entry_day <= D <= exit_day` (177 pairs) also counts the 3 pairs closed at 00:00 UTC on D, which were flat during
  the day. It is reported as the inclusive variant (S1, S1B, S2 at 2x), not used for decisions.
- Nine books, all reported; book capital = 2 x K units of entry notional, K = 20 (`lab.xfund.net`:
  `(gross - cost x legs) / (2 x slots)`).
- Current-survivor-only symbol lists (R275, R277); a delisted market may have no public candle (filled, counted).

## Data
- Candles, public and keyless, fetched once after this freeze by `scripts/fetch_adlstress.py` into
  `experiments/adlstress_v1/raw/` with `raw/manifest.json` (each request, HTTP status, sha256 of every body):
  - Gate USDT futures `api.gateio.ws/api/v4/futures/usdt/candlesticks` (1d, 1h);
  - KuCoin futures `api-futures.kucoin.com/api/v1/kline/query` (1440, 60);
  - MEXC contract `contract.mexc.com/api/v1/contract/kline/{symbol}` (Day1, Min60);
  - Hyperliquid `api.hyperliquid.xyz/info` candleSnapshot (1d, 1h);
  - Binance USD-M from `data.binance.vision` monthly 1d and daily 1h zips (fapi.binance.com answers 451 here).
- Per leg (venue, coin), symbols from `experiments/xfund_v1/symbols.csv` and `experiments/xfund_kd_v1/symbols.csv`:
  daily bars from two days before the leg's earliest entry_day to 2025-10-11, and 1h bars for 2025-10-09 and
  2025-10-10. 246 legs, 653 requests, a few MB.
- ADL venue evidence: `research/intake/adl_venues_20261113.md` (WS0027-WS0032), fixed before this freeze.
- **Seen before this freeze:** all trades, daily nets, books.csv statistics and FINDINGS of R437/R438/R483; the pair
  counts per book on D; the symbol maps. A plumbing run of `scripts/run_adlstress.py` on an empty manifest (no
  candle, out-of-repo output) checked that the code runs and showed only cost terms. **No candle, price or high-low
  range of any venue for any date was read.** General knowledge: BTC and ETH fell about 10-20% intraday on D and thin
  coins more than 50% (SRC1112-010), so S2 bounds are expected to be large.

## Feature lineage and point-in-time availability
| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| Exposed pair | entry_day, exit_day | R437/R438 v2 trades | entry_day <= D < exit_day | committed 2026-11-10 | seen rows | current survivors | none |
| D candle (o, h, l, c) | venue candle | each venue's perp, quote units | UTC 2025-10-10 00:00-24:00: the 1d bar if every daily bar of the leg opens at 00:00 UTC, else the 1h bars of D (>= 20 of 24) | fetched 2026-11-13 after this freeze | after the fact (a stress bound, not a signal) | latest vintage of each venue's API | missing: other leg's venue candle for the coin, else the book's largest (H - L) / H on D; counted |
| Profitable leg | o, c of D on the short venue (long venue if missing) | as above | close < open: short; else long | as above | n/a | as above | both missing: the leg on an ADL venue is assumed hit (the long is naked if both are) |
| Entry price P_e | the leg venue's close at 00:00 UTC of entry_day | as above | daily bar ending at that instant (or latest bar, daily or 1h, ending at or before it, within 3 days) | as above | n/a | last trade, not the mark the engine uses where held (stated, not repaired) | missing: notional fill below |
| Naked notional N | ref / P_e, ref = H (naked long) or L (naked short) | units of the leg's entry notional | D | computed | n/a | n/a | fills in order: close of 2025-10-09 / P_e on the naked venue, then on the other venue, else N = 1; counted |

## Rule (the bound, `scripts/run_adlstress.py`)
- Per exposed pair and scenario ADL set A:
  - profitable leg = short if the short venue's D close < D open, else long;
  - if the profitable leg's venue is not in A: loss 0;
  - else the other leg is naked: r = (H - L) / H (naked long) or (H - L) / L (naked short) of the naked venue's D
    candle; price loss = r x N = (H - L) / P_e, i.e. the leg's fixed quantity times the day's full range;
  - re-hedge cost = 2 x c x N, c = 7, 14, 21 bp per side (1x, 2x, 3x), the lab's grid;
  - loss_c = r x N + 2 x c x N.
- Book bound_c = 100 x sum of loss_c over the book's exposed pairs / (2 x 20), percent of book capital.
- Scenarios (fixed from the intake note before this freeze):
  - **S1 (decides): A = {hyperliquid}**, the only venue documented (Hyperliquid fill data in arXiv 2603.15963 and
    arXiv 2512.01112).
  - S1B (reported): A = {hyperliquid, binance}; Binance is named by one study only.
  - S2 (reported, absolute worst case): A = all five venues.
- Reported beside each bound: months of 2x net (bound / (v2_ann_cx_pct / 12)), share of the annual net, pairs
  stressed, candle and notional fills, the book's realized v2 2x net on 2025-10-10 and 2025-10-11 (from daily.csv),
  per-venue daily alignment counts, the inclusive-universe bound.

## Splits and cost
No split, no search. Costs 7/14/21 bp per side (1x/2x/3x); 2x decides, compared with the 2x annual net from
`books.csv` (`v2_ann_2x_pct`). 1x and 3x bounds are compared with the 1x and 3x nets and reported.

## Gates (decision, frozen)
- **Deciders (6):** `gate+hyperliquid L14d th5% K20` (R278 A), `binance+mexc L14d th10% K20` (R278 B),
  `gate+mexc L7d th10% K20` (R278 C), `binance+gate L14d th10% K20` (R390 A), `gate+kucoin L14d th5% K20` (R279 A),
  `binance+kucoin L14d th5% K20` (R279 B). Not deciding: `binance+hyperliquid L14d th10% K20`,
  `binance+gate+hyperliquid+mexc L14d th10% K20`, `hyperliquid+mexc L3d th5% K20`.
- **Per decider:** SURVIVES if the S1 bound at 2x < v2_ann_2x_pct / 12 (one month of 2x net); EXPOSED otherwise.
- **Lane:** PASS if all six SURVIVE; PARTIAL if 3-5; NULL (EXPOSED) if fewer than 3. Registry: PASS = CONFIRMED,
  PARTIAL = PARTIAL, NULL = NULL.
- Known before any candle: under S1 only pairs with a Hyperliquid leg can be stressed, so R278 B, R278 C, R390 A,
  R279 A and R279 B have an S1 bound of 0 by construction and SURVIVE; R278 A decides PASS vs PARTIAL. The S1 verdict
  therefore mostly restates the documentation gap. S2 is the informative number and is reported with an S2 call per
  book (same threshold, no decision).

## Null
None: the bound is deterministic (no seed). The verdict is the frozen threshold above.

## Multiplicity
- Trials: **6** (one per decider). S1B, S2, the inclusive variant, 1x/3x and the three non-forward books add none.
- Program trials before this lane: 9,785,291 (`registry.program_trials`). A bound is not a return test; it does not
  select anything.

## Evidence lineage and admission
- Canonical method id: M534. Parent rounds: R275, R277, R278, R279, R390, R437, R438, R483.
- `docs/GATES.md` SHA-256 at registration: e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926. Gate-0
  risk bound; not a gate pass, admits nothing to real money, changes no forward lane's frozen rule.
- No across-family selection control; the result is exploratory.
- Not priced: ADL on Bybit or OKX (no book uses them), venue failure, collateral haircuts, liquidation of a leg,
  exchange outages that blocked re-hedging longer than the day, and a second ADL day.
- **Order:** this PREREG is frozen and the R487 registry row appended in one commit; `scripts/fetch_adlstress.py`
  runs only after that commit; the raw bodies and manifest are committed; then the runner runs once.

## Stop rules
One run. No new scenario, universe, fill rule, cost or threshold after reading candles. A failed input check is
reported; a changed input is a new lane. Post-hoc diagnostics may go in FINDINGS, labelled post hoc, with no decision.

```inputs
edea115675f786f7a31818664d26b7fce7e55a0eb9ef5498289477ea443bcc1e scripts/fetch_adlstress.py
691f7bad4873fdeff91d04f249a7b9cd8264fd665667c0fbf2caa5a1932f132d scripts/run_adlstress.py
0bdf84bc917d31c79a8e087bae0cba48ac553af06b7e92701412bf21aacc3d6f tests/test_run_adlstress.py
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508 lab/prereg.py
7358e80991eac666348f2ce79a6281443fee6a1d89529cb612806b24034cbe1f experiments/carry_v2_audit_v1/results/trades_v2.csv
94882fda5ef12ec8f3af2aee71be33bff12b970bfde1f5bfc578cf3139dcdcd0 experiments/carry_v2_audit_v1/results/books.csv
3de6b7f29a3a3d786474b3e48444b004357c6cf2e78715e1d963f9ffe6f5fa08 experiments/carry_v2_audit_v1/results/daily.csv
e097316edff6d54ae227f0a1d3348879afcba591c3783579a456ef12f9a22c46 experiments/carry_v2_audit_kc_v1/results/trades_v2.csv
39843179c24d1a65babc44323da2038df8a8ecc14a6b94c8bdc3d89d5a08c677 experiments/carry_v2_audit_kc_v1/results/books.csv
8a803454b473f2fdfdbf41eff19085f053c9f208518b928cf21561a17b47004e experiments/carry_v2_audit_kc_v1/results/daily.csv
78201a341b9fc498b67f4893f1dd30d67d790d94ca8257a4b1a2ce8f569ab8e0 experiments/xfund_v1/symbols.csv
15c8054f7e10f921bd9a797fbf2b9ac927c99fdfbc2388a54199be0cace6fb3b experiments/xfund_kd_v1/symbols.csv
4a0fc05103cf9b2127a84b32e05b444ba5286743341d0c7ef9230e79ece23f75 research/intake/adl_venues_20261113.md
```
