# PREREG: atlas_mtf (R195), multi-timeframe confluence: fast signals under the symbol's slower state

Freeze with `lab.prereg.freeze()` before the first real-data statistic. After that this file is never edited; a changed
idea is a new lane.

- **Registry id:** R195
- **Owner (single writer):** the session that froze it
- **Code:** `scripts/run_context_atlas.py --lane atlas_mtf --families mtf --base 1h`, `lab/atlas.py` (`run`, `lift_stats`)

## What the author had seen
atlas_v1 main+clock (directional 1 h mean-reversion cells replicate; cross-sectional ones do not), maker_v1 and pack_v1
(per-trade gains of directional cells are mostly market exposure). The context atlas (R192) discovery passes for clock,
crowd and market contexts were running; their thresholds and lists had not been computed or read. No 4 h / 24 h state
has been crossed with a 1 h signal before.

## Question
Traders read a fast signal against the slower picture: a 1 h oversold coin in a 24 h uptrend (a pullback) is not the
same trade as one in a 24 h downtrend (a falling knife). For each 1 h signal, which slower states of the same symbol
(4 h and 24 h trend, position in range, RSI, market structure, volatility and volume regime, funding and premium)
amplify, damp or reverse it, and do those lifts hold on later data?

## Signals and contexts
- Base: the main-tensor views computed on 1 h bars that are not time-only, all bins, h in {1, 4, 12, 24, 72}, raw and
  excess, as in atlas_v1.
- Contexts (18, family "mtf"), the same symbol's bins of: ret[7]@24h/z30, ret[30]@24h/z30, ema_ratio[21]@24h/z30,
  ema_ratio[55]@24h/z30, ema_cross[21,55]@24h/z30, donch[50]@24h/fix, rsi[14]@24h/fix, struct[5,state]@24h/fix,
  atrp[14]@24h/z30, volz[24]@24h/z30, fund[0]@24h/z30, prem[0]@24h/z30, ret[30]@4h/z180, ema_ratio[55]@4h/z180,
  ema_cross[21,55]@4h/z180, donch[50]@4h/fix, rsi[14]@4h/fix, struct[5,state]@4h/fix.

## Everything else as atlas_ctx (R192)
Periods (discovery 2021-2023, validation 2024-2025H1, holdout not read), the lift statistic, one shifted-returns placebo
per context, thresholds per (family, measure, h) at estimated FDR 0.10 with at least 5 real cells, the filters
(support >= 1%, share >= 2%, lift days >= 100), CL and CCE definitions, the frozen list and its validation, the
replication rule and the decision rule (SIGNAL family: >= 20 replicated CLs, rate >= 25% and >= 2x the placebo
baseline; CONFIRMED in-sample, gross, if the family is SIGNAL).

## Multiplicity
Trials = the number of real discovery lift cells that pass the filters, logged to the registry.

## Expectations (written before running)
Mean reversion on 1 h will be stronger in 24 h uptrends (buying pullbacks) and weaker or reversed in 24 h downtrends;
high-volatility regimes will amplify the size of the bounce; funding extremes will damp longs when funding is high.
Many lifts will be found in discovery; perhaps a third will replicate.
