# Panel

Rebuilt 2026-10-20 01:02 UTC by `scripts/panel.py` at the end of each tick. Do not edit by hand.

**Objective.** Find a rule that makes money after MEXC costs on altcoin perpetuals, prove it on paper on days nobody had seen when it was frozen, then hand it to the owner through `lab.gate.go_real()` at small stakes.

## 1. The funnel

Ideas → frozen test → result → forward paper → go_real → owner places small stakes.

| stage | now |
|---|---|
| Ideas in the queue, untested | - |
| Ideas partly tested | - |
| Ideas blocked (data, download, compute) | - |
| Rounds in the registry | 55 (NULL 32, PENDING 11, CONFIRMED 7, PARTIAL 3, DATA_PASS 2) |
| Program trials | 9,471,893 |
| Forward paper lanes running | 8 |
| Strict on-time paper days so far | 0 |
| Passed go_real | none yet |

## 2. Forward paper lanes (the only road to money)

Replay days were scored after the freeze on days the archive did not hold; on-time days are the evidence.

| lane | book | replay | on_time | 2x / 3x | decided by |
|---|---|---|---|---|---|
| R215 mexc_fwd | flow book A on MEXC | 18 d +4.7% | 0 d | - | R221 looks at 90 / 182 / 365 on-time days |
| R215 mexc_fwd | top-vs-crowd on MEXC | 18 d -0.1% | 0 d | - | R221 looks at 90 / 182 / 365 on-time days |
| R218 mexc_fwd_sq | flow book X2 (k squared) on MEXC | 18 d +6.2% | 0 d | - | R221 looks at 90 / 182 / 365 on-time days |
| R220 carry_fwd | funding carry, MEXC | 18 d -0.0% | 0 d | - | 90 on-time days through go_real |
| R220 carry_fwd | funding carry, Binance | 18 d +0.0% | 0 d | - | 90 on-time days through go_real |
| R200 flow72_fwd2 | flow book A, Binance | 18 d +22.2% | 0 d | - | 90 scored days through go_real plus NW t >= 2 |
| R200 flow72_fwd2 | top-vs-crowd, Binance | 18 d +9.7% | 0 d | - | 90 scored days through go_real plus NW t >= 2 |
| R214 flow72_fwd3 | A one bar late | 18 d +22.5% | 0 d | - | same days as R200, a delay check |
| R214 flow72_fwd3 | B one bar late | 18 d +9.7% | 0 d | - | same days as R200, a delay check |

Processing lag of on-time hours: 0 hours, median - min, max - min; days with late hours: none.

## 3. Next in the queue

`registry/methods.csv` is not built yet.

## 4. Waiting on the owner

- Download MEXC public history (about 9.4k requests, `scripts/fetch_mexc_history.py`): carry on MEXC-only coins.
- Install PyTorch CPU and the Kronos-small weights (about 300 MB): R227 Kronos lane (PR #9).

## 5. Latest rounds

| id | lane | status | verdict | trials |
|---|---|---|---|---|
| R225 | vt_fwd | RUNNING | PENDING | 3 |
| R226 | tradesize_v1 | DONE | NULL | 6 |
| R228 | allocation_v1 | DONE | NULL | 30 |
| R229 | slow_trend_v1 | DONE | NULL | 2 |
| R230 | weekly_rotation_v1 | DONE | NULL | 96 |
| R231 | partial_execution_v1 | DONE | NULL | 2 |
| R232 | rebalancing_v1 | DONE | NULL | 3 |
| R233 | regime_v1 | DONE | NULL | 4 |

Details: [MAP](MAP.md), [EDGE_SCOREBOARD](EDGE_SCOREBOARD.md), [METHODS_QUEUE](METHODS_QUEUE.md), [room #7](https://github.com/SaikiK12/T/issues/7).
