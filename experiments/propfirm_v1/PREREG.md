# PREREG: propfirm_v1 (R202), what the lab's return streams are worth inside prop-firm rules

Freeze with `lab.prereg.freeze()` before the first simulation. Never edited afterwards; a change is a new lane.

- **Registry id:** R202
- **Owner (single writer):** the session that froze it
- **Code:** `lab/propfirm.py` (rules presets, bootstrap, evaluation), `scripts/run_propfirm.py`

## Question
Is a prop-firm challenge a better route to stake size than own capital for what the lab has found, and what would a
stream need for a challenge to pay? This is an economic translation of streams already measured, not a new test of
market returns.

## What the author had seen
All the input streams' own results (flow72_v2, flow72_holdout, carry_v1/holdout), the firm rules and published pass and
payout rates collected in `docs/SOURCES.md` section 3, and the unit tests of `lab/propfirm.py` (a zero-drift walk
under symmetric 10%/10% barriers passes about half the time and, with funded payouts, has positive expected payouts:
the challenge is an option). No stream has been run through any firm preset.

## Inputs (daily net returns as fractions of capital at the book's own scale, 1x costs)
- `flowA_hold`: flow72 combined book, universe hedge, holdout 2025-07..2026-09 (457 days) — primary
- `flowA_hold_top10`: the same with the practical top-10 hedge
- `tvc_hold`: top_vs_crowd alone, universe hedge, holdout
- `flowA_ins`, `tvc_ins`: the same books in-sample 2021-2025H1 (1,642 days)
- `carry_ins`: carry_v1 primary daily
- `zero_*`: each holdout stream demeaned (same volatility and tails, zero edge): the rules' option value alone

## Rule sets (`lab.propfirm.PRESETS`)
hyro_2step, hyro_1step, ftmo_2step, ftmo_1step, cft_1phase, cft_2phase, breakout_pro (crypto or CFD firms; our books
could be traded on their perps, the alt-short flow book only where enough coins are listed) and topstep_50k (CME
futures: a benchmark for the zero-edge streams only; the crypto books cannot trade there). Assumptions where a firm did
not state a rule are written next to each preset.

## Method
For each stream x firm, scales 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.75, 1, 1.5, 2 (multiples of the stream's returns),
4,000 bootstrap runs, 5-day blocks, evaluation horizon 365 days, funded period 180 days, seed 0. Reported per pair: the
scale with the highest expected value (or the highest break-even fee when the fee is unknown), pass probability,
probability of at least one payout, median days to pass, failures by rule, expected payout per attempt in USD, EV
after the fee and activation, and the break-even fee. Also, for own capital: the stream's annualized mean, Sharpe, max
drawdown and the fraction of Kelly at which its max drawdown equals 10%.

## Decision (descriptive lane)
No pass/fail on markets. The answer recorded in FINDINGS and `docs/MAP.md`: for each primary (holdout) stream, the
firms where EV after fee is positive at the best scale, the margin over the zero-edge stream, and whether own capital
or challenges give more expected USD per month for a given risk of losing the stake. A stream whose own evidence is
NOT CONFIRMED stays a hypothesis whatever its prop-firm EV.

## Multiplicity
Trials = 0 new return hypotheses (all streams are already counted). The scale search is reported as a best-of-10 per
pair; its optimism is noted.

## Expectations (written before running)
Daily limits (3-5%) and static drawdowns (5-10%) force the flow book down to a fraction of its natural scale (its max
drawdown was 27-47%); at that size it rarely reaches a 10% target within a year. top_vs_crowd alone (max DD 16% on
the holdout) fits better. The zero-edge streams may show positive gross option value under symmetric rules, which the
published pass rates (14-17%) do not reflect for real buyers.
