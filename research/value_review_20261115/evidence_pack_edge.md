# EVIDENCE PACK: find a REAL edge, 2026-11-15 (coordinator-verified facts only)

## Owner goal
A reproducible positive NET return at executable costs on MEXC altcoin perps, small capital, public
data. The owner explicitly wants an edge found or created, incl. GEX or richer chart data to size
bets with confidence. ~51 registered nulls. Program trials 9,785,317.

## What is ALREADY CLOSED (do not propose these again)
- GEX / dealer gamma: R292 NULL. Crypto dealer net GEX median -$20M per 1% = 0.13% of Binance perp
  ADV -> the hedge is too small to move price. Dealers short gamma 76-92% of days.
- SPX GEX as a BTC/ETH vol filter: R416 NULL, adds <=0.003 to R^2 (t -0.78 / -1.30).
- Expiry pinning / settlement window / charm / delta unwind: R289, R296 NULL (too small, too rare).
- 25-delta risk reversal timing: R307 NULL (24 trials).
- VRP on DVOL: R209, R138 NULL.
- Session-split continuation (imposed UTC cut): R493 NULL this session; rank ICs mildly NEGATIVE.
- ~50 more: chart rules (5472 brute-forced), ICT, round numbers, pairs, lead-lag, MAX, IVOL, skew,
  52w high, momentum, reversal, Amihud, day-of-week, unlocks-as-signal variants, carry variants.
- Costs: MEXC API all-in measured 9.3635 bp/side ($10k). Web taker 2bp, web maker 0 on 1106/1200
  contracts, API maker 6bp. Most gross edges found are 1-15 bp/day: BELOW cost.
- Holdout 2025-07..2026-09 is SPENT at program level. Only never-read windows or on-time forward
  days give clean evidence. No edge has an on-time forward day.

## What SURVIVED
- Funding carry: only out-of-sample confirmed edge, ~1%/yr, passed at 1x only (2x t1.14). Tiny.
- Unlock short (R265): +3.24%/event, 422 events, sign test p1.6e-8, week-bootstrap CI +1.21..+5.24%,
  trimmed mean +4.06% (not tail-driven). Gate 0 only (calendar not point-in-time). R494 this session
  showed it is SURVIVABLE at a 2% cap: 4.22%/yr, max DD -4.62%. Forward lane R266 running.
- Atlas gross conditional cells: replication 47.6% vs placebo 9.1% — real gross, below taker cost.

## THE STRUCTURAL PROBLEM
Almost every failure is the same: a real gross effect of 1-15 bp/day against 9-19 bp/day of cost.
The lab has been hunting DIRECTIONAL signals in the most liquid, most efficient instrument (perps)
at the highest cost tier (API taker).

## DATA ACTUALLY HELD (committed or recorded)
- Binance Vision hourly + 1-min klines incl. taker_buy_volume, quote_volume, count (2020-2026).
- fundingRate per coin; Deribit option TRADES with taker side 2016-11..2026-09 (41M BTC/ETH trades);
  Deribit hourly chain snapshots (OI, mark IV) from 2026-10-21; DVOL/BVOL; Binance EOHSummary hourly
  IV+greeks for 5 coins 2023-05..2023-10; MEXC depth snapshots; multi-venue funding (Gate, KuCoin,
  Hyperliquid, dYdX, Lighter); SqueezeMetrics daily SPX GEX.
- Deribit public API is reachable keyless (1064 live BTC options right now). Binance fapi is 451.

## CONSTRAINTS
No real orders, no money movement, no credentials, no bot-check bypass. Bounded keyless downloads.
Pre-register and freeze before any statistic. Costs at 1x/2x/3x. A null is a result.

## YOUR TASK
Propose the 3 highest-probability paths to an edge that is NOT already closed above. For each:
(a) the economic mechanism and WHO pays you (not just a pattern);
(b) why it survives 9.36 bp/side when 50 similar ideas did not — be quantitative;
(c) the exact data needed and whether it is in the held list;
(d) the cheapest decisive test and its falsifier.
Prefer changing the COST side, the INSTRUMENT, the HOLD horizon, or the DECISION (sizing/selection)
over yet another directional indicator. Explicitly reject anything above that is already closed.
Say plainly if you think no edge is reachable under these constraints. Max 700 words.
