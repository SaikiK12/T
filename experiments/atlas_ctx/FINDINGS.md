# FINDINGS: atlas_ctx (R192), context lifts

**Verdict: CONFIRMED (in-sample, gross).** Three of four context families are SIGNAL by the pre-registered rule (clock,
market, flow); crowd is not, because its placebo baseline is itself high. Most raw (directional) lifts of market-wide
contexts are the context's own market timing, not an interaction; the excess (market-neutral) lifts are interactions
and a few hundred of them carry a validation edge above 1x-3x round-trip costs.

- **Registry row:** R192 (trials: 8,320,806 real discovery lift cells passing the filters)
- **Reproduce:** prereg sha c2fc9afe; `python scripts/run_context_atlas.py discovery|flag|validation|decompose|report
  --lane atlas_ctx --families clock,crowd,market,flow`. Frozen discovery lists sha 386d6042 (the 225 MB csv is not
  committed; `results/validation_hashes.json`). The flag step was first run before the flow discovery had finished
  (three families); it was re-run once with all four before validation, with the same thresholds and code.

## Decision table (discovery 2021-2023 -> validation 2024-2025H1)
| family | confident lifts (CL) | replicate | placebo CL | placebo replicate | SIGNAL |
|---|---|---|---|---|---|
| clock (hour, sessions, opens, expiries, FOMC) | 17,187 | 49.8% | 1,059 | 5.8% | yes |
| crowd (share of coins at extreme lows/highs) | 408,132 | 85.2% | 19,658 | 49.0% | no (< 2x baseline) |
| market (BTC trend/vol, dispersion, breadth) | 321,432 | 70.7% | 22,227 | 10.6% | yes |
| flow (coin's own OI, positioning, taker, book) | 115,453 | 67.7% | 6,581 | 9.2% | yes |

## What the lifts are (exploratory decomposition, not in the PREREG)
A cell's lift = the context's own effect on every tradable coin + the interaction with the signal.
| family, measure | real CL | replicate | interaction replicates | placebo interaction |
|---|---|---|---|---|
| clock raw | 17,118 | 50.0% | 46.8% | 5.7% |
| crowd raw | 381,866 | 88.6% | 4.9% | 3.2% |
| market raw | 317,993 | 71.0% | 4.8% | 1.5% |
| flow raw | 111,845 | 68.6% | 12.7% | 4.2% |
| crowd excess | 26,266 | 36.3% | 36.3% | 3.9% |
| market excess | 3,439 | 45.9% | 45.9% | 2.8% |
| flow excess | 3,608 | 39.4% | 37.5% | 6.7% |

- **Market-wide contexts mostly time the market**: their raw lifts replicate because the context predicts where all
  coins go (e.g. after a flush), and only ~5% survive as interactions. This is why crowd fails the 2x-baseline rule.
- **Clock contexts are interactions, and mostly dampeners**: clocks alone predict nothing (atlas_v1), but they switch
  signals off: of the replicated clock lifts, 8,208 dampen the signal and 353 amplify it.
- **Excess (long the coin vs the market) lifts are interactions**: 36-46% replicate against 3-7% placebo.

## Conditional edges above cost (CCE: amplifier, |cond t| >= tau_cond, validation edge >= k x round trip)
| family | CCE (disc.) | replicate 1x | 2x | 3x | placebo 1x |
|---|---|---|---|---|---|
| clock | 405 | 77 | 56 | 30 | 0 |
| crowd | 79,967 | 68,915 | 56,739 | 44,167 | 1,696 |
| market | 24,596 | 20,764 | 15,204 | 12,952 | 94 |
| flow | 16,205 | 11,290 | 8,321 | 5,825 | 6 |
| **excess only:** crowd / flow / market | 2,114 / 451 / 277 | 452 / 188 / 93 | 153 / 119 / 43 | 62 / 66 / 16 | 2 / 0 / 0 |

Excess CCEs replicated at 1x: 40 at 1 h, 167 at 4 h, 263 at 12 h, 253 at 24 h, 10 at 72 h; median validation edge
17-41 bp against a 14 bp round trip. Examples (validation excess over the horizon): a coin 1 h overbought
(ema_ratio[21] bin 6) when its leverage crowding is lowest (oi_turnover xs8 bin 0): -122 bp over 12 h; a coin far
below its day open when the crowd is most short against its own history (crowd_ls z bin 0): +142 bp over 24 h.

## Cost sensitivity
In the CCE table (1x, 2x, 3x). Directional CCEs carry market exposure; only the excess rows are close to tradable.

## What this does not show
- Atlas means are day-weighted over all hours in the state; per-entry edges are smaller (flow72_v1). A slice book that
  holds the state is the construction that earns the day-weighted mean.
- Most excess CCE states are rare (share of the cell's hours under 10%), so a book of them is thin.
- 8.3 million trials: read every number against the placebo columns, not against a t table.

## Next
A slice-book lane on the replicated excess CCEs of R192 and R195 (fixed list, frozen before the holdout), so the
holdout (unspent for these cells) can say whether held states pay after costs.
