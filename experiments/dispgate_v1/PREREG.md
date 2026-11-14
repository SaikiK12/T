# PREREG: dispgate_v1 (R260). Halve the flow books in high-dispersion alt bear markets

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R260 (claimed on issue #7)
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_dispgate.py`. It reuses `build()`, `describe()` and the window dates from `scripts/run_regime.py`
  (R233), unchanged.
  - Books A, B and X2 are rebuilt as in R217. They must equal R217's `daily.npz` (max |diff| < 1e-12) before anything
    else is computed.
- **Queue:** M003 (dispersion or breadth gate on flow books); rule #7 of `docs/SIZING_EVIDENCE.md`.
- **Gate:** 0 (screen).

## What the author has seen
- **R217 (sizing_v1):** confidence-scaled multipliers on A/B/X2. No rule gained +0.3 Sharpe in both windows.
- **R233 (regime_v1):** trend x volatility regimes. A, B and X2 each made money at 2x in all four regimes in
  discovery, so no gate was selected. MIX gained +0.12 Sharpe in validation (0.15 was required).
- **R228 / R253:** static allocations across A/B/X2, NULL.
- No dispersion statistic has been computed on these books. The rule comes from the momentum-crash literature (Daniel
  and Moskowitz 2016; Barroso and Santa-Clara 2015; Stivers and Sun 2010), where it cuts exposure when dispersion is
  high in down markets.
- The flow books are short-side, crowd-fading books, not momentum. Whether the rule helps them is open.

## Rule (daily, decided from data through the previous day)
- **Daily coin returns:** r[d, s] = the sum of `u.ret` over day d's 24 rows, for eligible crypto coins (as `build()`).
- **Dispersion:** disp[d] = the cross-sectional standard deviation (ddof 0) of r[d, ·] over eligible crypto coins, on
  days with at least 10 such coins.
- **D30[d]:** the mean of disp over days d-30..d-1.
- **Top tercile:** D30[d] >= the 2/3 quantile of all D30 values from earlier days, which needs at least 180 earlier
  values; otherwise undefined.
- **Alt index:** a[d] = the equal-weight mean of r[d, ·] over eligible crypto coins other than BTCUSDT and ETHUSDT.
  A90[d] = the sum of a over days d-90..d-1.
- **Multiplier:** m[d] = 0.5 when D30[d] is in the top tercile and A90[d] < 0, else 1. Undefined inputs (warm-up)
  give m = 1.
- **Gated book:** the book's hourly positions on day d times m[d]. `slices.run` as R233, which means:
  - hedged;
  - tier costs at 1x/2x/3x;
  - `missing="legacy"`, required for parity with R217.

  Resizing is charged as turnover.

## Variants (3 trials) and controls
- G-A, G-B, G-X2: each book gated. The control is the same book at constant size.

## Decision (per variant)
- **Discovery 2021-01..2023-12:** the gated book's Sharpe (1x) minus the control's must be > 0. The rule has no
  fitted parameter, so discovery is a test too.
- **Validation 2024-01..2025-06:** pass if all hold:
  - Sharpe gain at 1x >= 0.15;
  - 2x mean > 0;
  - max drawdown at 1x <= the control's.
- **Holdout:** not read (spent at program level).

## Reported (not decided on)
- Share of days with m = 0.5 per window, the number of separate gate episodes, and their dates.
- Per window and cost level:
  - mean, NW t, Sharpe, max DD, per year;
  - the paired daily difference (gated minus control) with its NW t.
- The control's mean on gated days versus other days, to show whether those days are the books' bad days.

## Multiplicity
- Trials = 3.
- Program trials before: 9,472,034 (after R256 and Codex's R253).

## Expectations
- **The gate will be on rarely:** the 2022 bear market, and perhaps the 2024-25 alt decline.
- **Halving size on those days changes Sharpe only if the books' mean on those days differs from their mean
  elsewhere.**
  - R233 found the books profitable in falling high-volatility regimes (DH: A t 2.20, X2 t 2.57).
  - So the gate more likely removes profit than loss.
- **Most likely:** NULL. Plausibly with a negative discovery gain.
