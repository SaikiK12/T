# PREREG: regime_v1 (R233). Does trading the flow books only in some market regimes beat trading them always?

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R233 (claimed on issue #7)
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_regime.py`; it rebuilds books A, B and X2 exactly as R217 (`scripts/run_sizing.py`) and checks
  that its constant-size daily nets equal R217's `results/daily.npz` before anything else.
- **Origin:** the owner's MacroHFT paste (2026-10-20, `docs/METHODS_QUEUE.md`): sub-agents trained per market regime
  (trend x volatility) and a hyper-agent that mixes them. The paste is about reinforcement-learning agents at minute
  frequency. This lane tests the part that can be tested on the books we have: regime-conditional exposure and a
  regime-conditional choice among existing books. It does not train any agent.

## What the author has seen
- Every daily result of A, B and X2 (constant size) in every window, including the holdout (R198, R213, R216, R217,
  R228).
- R217's R4 (half size when dispersion is high and the 90-day index is down) never triggered in discovery.
- No statistic of any book split by the regimes below has been computed.

## Books (as R217)
Crypto contracts only; one-hour delay (R213 d = 1); 72 h slices, unit 1 / (72 x 9.316); universe hedge; tier costs;
funding.
- **A:** slices of top_vs_crowd, taker[24] and taker[4] (xs8 bin 0, short), summed.
- **B:** top_vs_crowd alone.
- **X2:** A with k^2 slices for a coin flagged by k cells, rescaled to A's mean gross exposure over 2021-01..2023-12.

## Market regime of day d (through day d - 1 only)
- `idx[d]` is the equal-weight mean daily return of eligible crypto coins, as R217's index.
- **Trend:** UP when the sum of `idx` over days d-30..d-1 is > 0, else DOWN.
- **Volatility:**
  - `v[d]` is the standard deviation of `idx` over days d-30..d-1.
  - HIGH when `v[d]` is at or above the median of `v` over all earlier days, with at least 180 earlier values. Otherwise
    LOW.
- **Regimes:** UL (up, low vol), UH, DL and DH.
- **Warm-up:** days without a defined regime (the first 30 + 180 days) are traded at full size in every variant, so
  every variant equals its control there.

## Variants
Each variant scales positions by a daily multiplier `m[d]` (`P * m` per hour), as R217 did. Position changes are
charged at tier cost through `slices.run`.

- **G-A, G-B and G-X2 (gates):**
  - For a book, the gate set G is the regimes whose discovery mean 2x daily net of the constant-size book (on the
    days in that regime) is > 0.
  - Then `m[d] = 1` if the regime of day d is in G, else 0.
  - A gate set equal to all 4 regimes, or to none, means no gate was selected. That book's verdict is then NULL with
    no further computation.
- **MIX (the "hyper-agent"):**
  - In each regime, it holds the one book among A, B and X2 with the highest discovery mean 2x daily net in that
    regime.
  - If no book has a positive mean in a regime, it holds nothing on those days.
  - Its control is the book with the highest discovery mean 2x daily net over all days.

## Windows and decision
- **Discovery 2021-01-01..2023-12-31.** It chooses the gates and the MIX table, nothing else.
- **Validation 2024-01-01..2025-06-30.** A variant **passes** when all three hold:
  - its 1x annualized Sharpe exceeds its control's (the same book at constant size) by 0.15 or more;
  - its 2x mean daily net is > 0;
  - its 1x max drawdown is no worse than its control's.
- **Holdout 2025-07-01..2026-09-30.** It is reported only for passers. Its constant-size outcome is known, so it decides
  nothing.
- **A pass** becomes a forward overlay on R215/R218 under a new id, decided on on-time days only. Nothing here is
  confirmed.

## Reported (not decided on)
- Share of days per regime, per window.
- Discovery mean 1x/2x/3x daily net per book and regime, with NW t (lag 10).
- The selected gates and the MIX table.
- Per variant and control, at 1x/2x/3x, per window reached:
  - mean bp/day, NW t (lag 10), Sharpe, max DD;
  - share of days traded and mean gross exposure;
  - per-year means.
- The paired daily difference (variant - control): mean and NW t, per window.

## Multiplicity
- Trials = 4 (G-A, G-B, G-X2, MIX).
- Program trials before: 9,471,889 (after R232).

## Expectations
- **Most likely NULL.**
  - About 880 discovery days with defined regimes split four ways leave about 220 days per cell.
  - At the books' daily noise, that is too few to pick a gate reliably. A gate mostly removes days, and the gross
    exposure it drops costs a round trip each time.
- **Best chance: G-B.** Top-vs-crowd is a crowding signal, and crowding unwinds should pay most in falling, volatile
  markets. That is the regime-dependence of momentum crashes ([Daniel and Moskowitz, JFE
  2016](https://doi.org/10.1016/j.jfineco.2015.12.002)).
