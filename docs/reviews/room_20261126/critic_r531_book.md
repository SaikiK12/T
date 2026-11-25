# Critic report, R531 (carry_meta_v1) and STRATEGY_BOOK.md, 2026-11-26

Scope: PREREG, FINDINGS, report.json, scripts/run_carry_meta.py, STRATEGY_BOOK.md, the two cited FINDINGS,
lab/xfund.py, lab/xfund_v2.py, engine/src/spread.rs:204, and trades_unfiltered.csv. Numbers marked "critic check"
are my own recomputation or one-shot descriptive fits on that csv. I did not run the script and did not open any
journal. The sha256 of run_carry_meta.py, xfund_v2.py, xfund.py, spec.toml, stats.py and prereg.py match the PREREG
inputs table, so the code was not edited after the freeze.

## 1. Code: scripts/run_carry_meta.py

OK
- Features use past and present only. `fa, fh = a.window(d, 14), h.window(d, 14)` (line 55), the funding loop stops
  at `d` (line 61), and `va, vh = a.val[d], h.val[d]` (line 63). Funding settled in (d-1, d] is known at d
  (lab/xfund.py:12 docstring).
- The purge is right: `tr = tab[tab.exit_day < s - EMBARGO]` (line 158). Labels use exit information only.
- Only the current quarter's model is used: `s = max(x for x in starts if x <= d)` (line 176).
- Frozen path: `if p is not None:` (line 98) is the only place cs changes. Before the first quarter, FilterBook.entries
  equals xfund_v2.Book.entries (xfund_v2.py:208-223).
- The label is consistent with the engine. Price P&L is per unit of one leg's entry notional
  (xfund_v2.py:165 `ql, qh = 1.0 / p.pl_e, 1.0 / p.ph_e`). Costs are cost x legs, with 2 legs at entry and 2 at exit
  (xfund_v2.py:193 and 204). So 4 x 14 bp is right.

Problems
a. Inherited look-ahead in the exit rule. lab/xfund.py:81 `int(fr[-1]) if len(fr) else -1` sets last_fresh from the
   whole history. xfund_v2.py:124 then exits on `(a.last_fresh < d or h.last_fresh < d)`, so a pair closes the day after
   a leg's final trade, which the book cannot know in real time. The Rust engine does the same (spread.rs:204). It
   touches both books and every label. PREREG pre-mortem item 4 covers features only, so "no look-ahead" is too broad.
   Size not measured (the csv has no exit-reason column).
b. Train and test populations differ. Training uses executed trades (`tabs += trade_table(u, a, tr)`, line 218). The
   scorer sees every candidate while a slot is free (`p = self.scorer(d, [f for _, _, f in ok])`, line 97). The
   "3.2%" is a share of candidate-days, not trades, and one coin can appear on many days.
c. The equivalence check is not in the repo. PREREG says "(`equals` True)". run_carry_meta.py has no such check, and
   tests/test_carry_meta.py has no FilterBook or equals test (grep). I could not reproduce it.
d. 12 models, but 11 test quarters. quarters() runs to `last = day_ts(u, u.nd - 1)` (line 143), and
   scripts/run_carry_v2_audit.py:57 gives nd-1 = 2026-10-01 for end 2026-09-30. The 2026-Q4 model is never used,
   since the replay stops at 2026-09-30 (1,004 days). "12 test quarters" (PREREG) and "12 trimestres" (book) are wrong.
e. Units. `s14 = (fh - fa) * 365.0 / 14` (line 58) is a fraction per year, not %/yr as PREREG line 46 says. Standardized,
   so the model is unaffected; the labels are wrong.
f. Lines 95-96 drop candidates with no features, but only when a model is active. Harmless: candidate() needs the same
   14-day windows (xfund_v2.py:157-166).

## 2. FINDINGS vs report.json

- Every number matches. 1x: 6.49 / 5.32 / -1.17 / t -3.40 (report 6.4916, 5.3198, -1.1718, -3.4047). 2x: 5.19 / 4.84 /
  -0.35 / t -0.97 (5.1896, 4.8424, -0.3472, -0.9743). 3x: 3.89 / 4.37 / +0.48 / t 1.27. Yearly diffs and ML-by-year
  match. 6,760 trades, 1,004 days, 0.4442 positive share, 5,465 of 169,782 (3.2%) all match.
- "12 quarterly models" counts one model that is never used (see 1d).
- "The best 10% of trades earn 123% of the total net": correct. Critic check: the top 676 of 6,760 net2 values sum to
  1.229 times the total (+102.0 in trade units). Top 1% gives 45%, top 5% gives 97%. Mean +151 bp, median -18, p10
  -161, p90 +528 all match.
- Tax arithmetic: 5.19 x 0.686 = 3.56, and 4.84 x 0.686 = 3.32. Minus 1.5 gives +2.1 and +1.8. The arithmetic is right,
  but the inputs are not sourced: the 1.5% cash return is in no file, and the flat 31.4% is applied to an annual book
  return with no loss carry-forward and no check of how French tax treats perpetual futures. Weak point.
- FINDINGS:28 "So the ML book traded less" and "It saved turnover cost" are unsupported. report.json has no meta trade
  count and no turnover.
- FINDINGS:27 "a calibrated logistic model rarely reaches 0.5" is not shown (see 3).

## 3. Is "ML on entries cannot pick a fat right tail" supported? No. It is a story.

What the test shows: at one threshold (0.5), on candidate-days, the book-level difference is -0.35%/yr at 2x (t -0.97).

Critic checks (descriptive, one-shot, not decisions):
- Logistic fit on trades with exit before 2024-01-01 minus 14 days (1,846 trades), tested on the 4,725 entries from
  2024. Test AUC(y) 0.586. 31.7% of test trades have p >= 0.5, which contradicts "rarely reaches 0.5".
- Test trades with p >= 0.5: 1,497 trades, mean +277 bp. The rest: 3,228 trades, mean +24 bp. Top probability quintile:
  +415 bp. So at trade level the score does separate winners. The book-level null then needs its own explanation
  (slot reallocation, the candidate population, day timing). FINDINGS does not discuss this.
- The largest coefficient is s14 (+0.36, standardized). The filter mostly ranks by the rule's own entry variable.
  Spread bins on test trades (fraction/yr): (0.05, 0.10] 2,615 trades at +16 bp; (0.10, 0.20] 925 at +11 bp;
  (0.20, 0.40] 265 at +37 bp; above 0.40, 920 trades at +466 bp. The fat tail is the entries above 40%/yr, mostly
  Kraken (53.6% of p >= 0.5 trades, mean +434 bp). A plain spread cut is the cheap benchmark FINDINGS never runs.
- In-sample univariate AUC(y): s14 0.60, basis 0.40 (0.60 inverted). Spearman(basis, net2) = -0.24, the strongest
  magnitude link among the features. FINDINGS:34 "the entry features do not separate those" is false for magnitude.
- The label is `y = int(net2 > 0)` (line 131). It ignores size. For a right-skewed payoff, a hit-rate model can miss the
  tail by design. Test with a regression or quantile label before calling the tail unpickable.
- Pooled pairs: 49% of trades are Bitfinex (mean +94 bp). Only two venue dummies. Per-venue or interaction effects are
  untested.
- Threshold 0.5 is a convention, not a measured optimum. No rank-based test (top-k share) was run.
- Holding time: top-10% trades have median hold 73 days vs 16 (critic check). That is endogenous, since the exit rule
  keeps winners open. "long-lived wide spreads" describes the book; it is not a cause.

Verdict: the null at this threshold is real. It does not show that entries carry no tail information. Write it as
"not shown".

## 4. STRATEGY_BOOK.md

- Lines 6-7 say the main numbers were "revérifiés sur la page". Not true for A2 and A3 below.
- A1 (lines 41-43): +24.28%, t 7.39, 343 days (xfund_eea FINDINGS:19-23, matches); 97% from coins under $100k a day
  (FINDINGS:12-13, matches); 13.5-16.5 bp (FINDINGS:79, matches); 2-3x (FINDINGS:85, matches); $40-100k (FINDINGS:96).
  Not traced: "usure ... (cycle 8)" (line 46), the decision dates, and the R526 filters (lines 23-26).
- A2 (line 53): "+4,52 %/an à 1x, t 7,02" does not match. gap_breadth FINDINGS:35: "| deribit+hyperliquid | R519 (reported)
  | PASS | +4.4 | +3.4 | +2.3 | 6.69 | −0.85% | 2023-05 |". The book cites R520 over 2023-06..2026-11. Not in the cited
  files. Fix or cite.
- A3 (line 61): "+5,21 %/an à 1x, t 11,94" does not match. FINDINGS:39: "| bitfinex+binance | R507 | PASS | +3.5 | +2.3 | +1.1 |
  2.95 |", and FINDINGS:43-44 "Bitfinex+Binance's +3.5%/yr differs from R507's +5.2%". t 11.94 matches no pair. It is close
  to the portfolio's t 11.96 (FINDINGS:15), so it is probably a transcription error. "environ +3,1 %/an en 2025-26" is
  untraced. Fix before use.
- A4 (lines 69-72): matches FINDINGS:14-15, 21, 78 and 84. But "sans les filtres R526" is not in the FINDINGS. The
  addendum (FINDINGS:91-92) recommends "an hourly divergence stop on each pair". The book (line 26) says "Le stop
  horaire est rejeté". That conflicts and must be resolved.
- Section 0, lines 17-18: "−0,04 (R508 contre R519, 343 jours)" and "Q26 0,35" are untraced. FINDINGS:41 gives a median
  correlation of 0.17 across pairs, not −0.04.
- C (lines 99-107): numbers match the carry_meta FINDINGS. Problems: "12 trimestres" (it is 11); "imprévisibles à
  l'entrée" is stated as a result (not shown, see 3); "On garde la règle" conflicts with line 27-28 ("les lectures de
  décembre, et rien d'autre") and omits that the rule is in sample (FINDINGS:49).
- D: not checked.

## 5. Cleaner than the evidence

- "ML cannot pick the tail" (FINDINGS:42, book C) becomes "not shown at this threshold".
- "3.2% kept" becomes "3.2% of candidate-days; trade share not reported".
- "traded less / saved turnover" is unmeasured.
- "a one-parameter question, not ML" (FINDINGS:39-40) is untested.
- "On garde la règle": the rule is unchanged, and money is decided in December per the book's own rule (lines 27-28).
- A2 and A3 numbers (see 4).

Fine: the PREREG design (purge, embargo, fixed decision rule), the FAIL verdict, the FINDINGS table transcription, the
label-to-engine cost units, and the A1 and A4 numbers.

## Before any claim

1. Replay the walk-forward decision at trade level and per s14 bin: which trades the filter removed, and their net.
2. Run a plain spread-cut benchmark on the same trades.
3. Refit with a size-aware label (net2 regression or quantile).
4. Report the meta book's executed trade count and turnover.
5. Fix A2 and A3, and resolve the stop-rule conflict.
