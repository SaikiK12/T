# PREREG: vt_fwd (R225), R217's volatility target applied forward to the MEXC flow books

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R225
- **Owner (single writer):** the session that froze it
- **Code:** `scripts/forward_vt.py`
- **Source:** R217 (sizing_v1). Its R1 volatility target left Sharpe about flat and cut maximum drawdown in every
  window:
  - book A: 24/26/47% to 15/23/27% (discovery / validation / holdout);
  - book B: 11/16/16% to 5/12/10%.
  - R217 called it "a risk tool, not an edge", worth applying to any live size.
  - It has never run on forward data.
- **Why:** this is a refinement tried on paper. The flow books are the largest edges in the archive and also the most
  volatile (A's holdout drawdown was 47%). If the owner ever sizes one by hand, this lane gives the multiplier to use
  each day, and checks forward whether it keeps its promise.
- **Trials:** 3 (books A, B, X2). Nothing here changes a frozen lane's decision.

## What the author had seen
- R217's full results, including the holdout and the daily series in `experiments/sizing_v1/results/daily.npz`.
- The replay tickets of R215 (A, B) and R218 (X2) for 2026-10-01..18.
- No multiplier has been computed on forward days.

## Books and history
- **Books:**
  - A and B are read from R215's tickets (`experiments/mexc_fwd/journal/tickets.csv`).
  - X2 is read from R218's tickets (`experiments/mexc_fwd_sq/journal/tickets.csv`).
  - All three are MEXC prices and funding with tier costs, one bar late, crypto only.
- **History used by the rule:**
  - First, R217's constant-size daily net for the same book: `A_C0`, `B_C0` and `X2` in `daily.npz`. That is Binance,
    crypto only, one-hour delay, 1x costs, 2021-01-01..2026-09-30.
  - Then the lane's own ticket days in date order, replay and on-time alike, using `net` (1x).
  - The archive and forward books share the same unit and scale (X2 is matched to A's 2021-23 gross exposure in both).
    Their venues differ (Binance archive, MEXC forward); this is stated, not corrected.

## Rule (R217's R1, unchanged)
- sigma_hat = the EWMA standard deviation (half-life 30 days) of the daily net through day d - 1.
- sigma_star = the standard deviation of all daily nets through day d - 1.
- m_d = clip(sigma_star / sigma_hat, 0, 2).
- R217 set m = 1 before 90 days of history. The archive gives more than 2,000 days, so that never binds here.

## Scaled book
- **Daily net:** net_vt_d = m_d x net_d - |m_d - m_(d-1)| x gross_exposure_d x 8 bp.
  - The second term is the cost of resizing every open position at the day's start.
  - gross_exposure_d is the ticket's mean gross exposure.
  - 8 bp is the tier cost for ranks 21-50.
- **At 2x and 3x:** m_d x net_2x_d (or net_3x_d) minus 2x (or 3x) the resize cost.
- **Approximation, stated:** R217 rescaled the hourly positions inside the slice engine. Scaling the day's net is the
  same up to the hedge's share of the resize cost.

## Journal and status
- **Journal:** `journal/days.csv`, one row per book and day, appended once and never rewritten. Columns: day, book,
  kind, m, net, net_vt, net_vt_2x, net_vt_3x, resize_cost.
- **`journal/status.json`, per book:**
  - **m_next:** the multiplier for the next day, from history through the last ticketed day.
  - For on-time days, scaled and unscaled side by side:
    - total, total at 2x and 3x;
    - annualized Sharpe;
    - maximum drawdown of the cumulative sum;
    - mean m.

## Decision (at 365 on-time days, the horizon of R221's final look)
- For each book, the volatility target **KEEPS ITS PROMISE** when both hold:
  - the scaled book's maximum drawdown is below the unscaled book's;
  - its Sharpe is at least the unscaled Sharpe minus 0.2.
- Otherwise it **DOES NOT**.
- The verdict is about risk only. Whether a book makes money is decided by R215, R218 and R221.

## Known limits, stated in advance
- About 2,100 archive days dominate sigma_star, so m mostly tracks recent volatility against the archive's long-run
  level, not the forward book's own.
- One year of forward days is a weak test of drawdown, a tail statistic.
