# Room audit, 2026-11-25: non-carry rounds re-verified with the closed-market knowledge

Auditor: research room member "other". Repo root: `/home/user/T`. All paths are repo-relative. Line numbers refer to the
files as they stood on 2026-11-25.

## 0. Scope, method, what was not read

- **Population.** `registry/rounds.csv` (309 rounds) joined with `registry/lane_families.csv` on `lane`. The non-carry
  families are calendar 22, xsec 29, flow 26, events 23, charts 24, options 16, micro 13, portfolio 16, reserved 2:
  **171 rounds**. Of these, 25 carry CONFIRMED, PARTIAL or DATA_PASS (`registry/rounds.csv`, verdict column).
- **Verdict column is incomplete.** Most NULL rounds have a blank `verdict` in the registry. NULLs were found by
  keyword in `title` and `notes` (74 rows matched venue, closure, listing, oracle, settlement, funding, liquidation,
  weekend, reopen, holiday, session, close). Where the FINDINGS verdict differs from the registry, I give both.
- **Read in full or in the relevant sections (FINDINGS.md):** R462, R464, R465, R466, R468, R432, R461, R435, R471,
  R337, R336, R330, R349, R304 (mlrank_v2), R332 (mlrank_v3), R299 (mlrank_v1 header), R197, R185, R192, R195, R276,
  R282, R392, R473, R202.
- **Registry row only (no FINDINGS read):** R244, R181, R258, R259, R265, R143, R144, R216, R411. R289, R296 and R348
  appeared in the keyword list only and are not judged here.
- **Read for context:** `docs/reviews/reflection_20261124_closed.md`, `research/intake/oracle_frontiers_20261125.md`,
  `research/intake/nagel_evaporating_20261125.md`, `docs/reviews/mechanism_map.md`, `docs/reviews/approach_20261124.md`
  (not re-read in full; the mechanism-map row was read).
- **Not opened, by rule:** any `experiments/*/journal/`; every forward lane (`*_fwd`, `*_fwd2`, `*_fwd3`, `xyzbal_fwd`,
  `xyzwknd_fwd`, `ltwknd_fwd`, `asiaclose_c`, `usopen_dex_fwd`, `oilwknd_fwd`, etc.); no `run_*_fwd.py`, `run_*_fast.py`
  scripts; no R406, R413 or R419. No experiment script was executed. The only computation was a pandas join of two CSVs.
- **Not verified against primary sources:** the Nagel (2012) bounce figure and the Seo et al. (arXiv 2608.09188) Table 1
  numbers are taken from the lab's intake cards (`nagel_evaporating_20261125.md:24-30`, `oracle_frontiers_20261125.md`).
  The trade.xyz rule quotes come from `reflection_20261124_closed.md` section 7, which cites a fetched `llms-full.txt`
  (not in the repo, so not re-read here).

## 1. Headline findings

1. **R304 (mlrank_v2) PARTIAL is a metrics-presence leak, and its own header denies it.** R332 reruns the same
   family on a panel whose metrics columns are complete: the pick falls from +58.9 to -16.5 bp/day (validation). A
   rule that only asks "does this row have `oi_usd`?" earns +50.3 bp/day net (t 4.47) (`experiments/mlrank_v3/FINDINGS.md:4,8-11,53-55`).
   R304's header still says the leak "never carried it" (`experiments/mlrank_v2/FINDINGS.md:1`). The PARTIAL claim should
   be retired. R299 (mlrank_v1) is also PARTIAL in the registry, but its own FINDINGS says "Not trusted: its inputs leak
   survival" (`experiments/mlrank_v1/FINDINGS.md:3-6`).
2. **R197 (flow72_v2) is labelled CONFIRMED, but the holdout said NOT CONFIRMED.** R197 is a design check whose cells were
   chosen with both periods and after a failed book (R196). Its own text says "Only the holdout can say more"
   (`experiments/flow72_v2/FINDINGS.md:3,32`). The holdout R198 gives t 1.22 < 2 (registry row 17). The propfirm FINDINGS
   already reads it as "NOT CONFIRMED" (`experiments/propfirm_v1/FINDINGS.md:6`). Relabel. The forward R200 is the only
   remaining test, and I did not read it.
3. **The three atlas rounds are CONFIRMED only "in-sample, gross."** R185 (338,240 cells), R192 (8.3M lift cells) and R195
   (643,736 cells) all carry the CONFIRMED label while most edges sit below round-trip cost (R185
   `experiments/atlas_v1/FINDINGS.md:3-4`; R195 `experiments/atlas_mtf/FINDINGS.md:3-4`; R192 `experiments/atlas_ctx/FINDINGS.md:3-4`).
   The placebo replication rates are low (9.1% and 0%), so the replication is informative about the gross signal.
   It still does not establish net edges after costs. Relabel.
4. **The closed-market weekend fade (R462) survives the cost check, but its entry instant is the open question.** At $1k,
   the measured round-trip book cost on Sundays is about 6 bp, against the 5.8 bp unit used (`reflection_20261124_closed.md`
   section 8). The break-even is 42 bp (`experiments/xyzwknd_v1/FINDINGS.md:77`). The decision cell enters at Sunday 19:00,
   before the Blue Ocean anchor returns at 20:05 (`experiments/ltwknd_v1/FINDINGS.md:78-80`). The reversal then happens between
   20:00 and 22:00 (`experiments/ltwknd_v1/FINDINGS.md:72-76`). The depth table skips 19:30-21:30, the hours in which the
   reversal occurs (`reflection_20261124_closed.md` section 8). The entry is at the thinnest hour of the week
   (19 bp at $10k).
5. **The overnight-vs-intraday round (R435) is NULL partly because of the open instant, and that instant is not observed.**
   The MEXC stock perps have hourly bars only, so the open is proxied at 10:00 or 09:00 (`experiments/stock_tugofwar_v1/FINDINGS.md:20`,
   `:93`). The reversal sign appears only at 09:00, which is pre-open (`:57-59`). The reversal book (B2, long bottom ON,
   held open to close) is -0.56 bp gross at 10:00 and +10.4 at 09:00 (`:65-69`). The oracle-network reading predicts the
   reversal at the cash open (09:30), which neither proxy observes.
6. **Balanced design and the closed-market oracle (K2).** The index control R464 is consistent with the mechanism. The
   index and commodity perps are anchored by futures from 18:00, so no reversal is predicted there and none is seen
   (`experiments/xyzns_wknd_v1/FINDINGS.md:3,9-13`). The idiosyncratic component is the one that reverses (`reflection_20261124_closed.md`
   section 2). R462's market-neutral `rel` book earned +55.8 bp against +42.4 raw (`experiments/xyzwknd_v1/FINDINGS.md:52-53`).
   The balanced forward lane R530 was frozen on 2026-11-25 and I did not read it.

## 2. Round table

Columns: verdict = registry / FINDINGS where they differ. Flags: K1 mechanism, K2 closed market, K3 last-trade valuation,
K4 selection, K5 cost, K6 instant or sign. Suggested action: none, re-check, reopen (new lane), retire claim, or relabel.

| round | lane | family | verdict | flags | evidence (path:line) | suggested action |
|---|---|---|---|---|---|---|
| R462 | xyzwknd_v1 | calendar | PARTIAL / PASS gate 0 | K2 closed market; K3 last trades at 19:00 and 22:00; K5 unit 5.8 bp vs measured about 6 bp at $1k, 19 bp at $10k entry; K6 entry precedes anchor return | `experiments/xyzwknd_v1/FINDINGS.md:3,30,63-65,74-82,88-91`; `reflection_20261124_closed.md` section 8 | re-check: entry instant (20:00-21:00) and book cost on the two recorded Sundays; the balanced forward R530 is the live test |
| R465 | ltwknd_v1 | calendar | PARTIAL | K4 not independent of R462 (same event set, correlation 0.96, `:7-8`, `:51-53`); K6 Sample C reverses on Monday pre-market, not Sunday (`:72-88`) | `experiments/ltwknd_v1/FINDINGS.md:3,7-13,72-88` | none for the claim; treat as a venue replication, not new evidence; re-check C's exit instant once the anchor is known |
| R464 | xyzns_wknd_v1 | calendar | NULL | K2 control (anchored index); K6 exit at reopen+2h is after the futures anchor, so no wrong-instant null | `experiments/xyzns_wknd_v1/FINDINGS.md:3,9-13,33-34` | none (keep as the negative control) |
| R432 | weekend_reopen_v1 | calendar | NULL | K4 primary cell seen once before the freeze (`:3-8`); K3 1-min bar closes; K6 exit reopen+15 min, while the slope keeps growing to +60 min and the Monday cash open (`:46-54`); K4 best cells picked from 144 (`:55-64`) | `experiments/weekend_reopen_v1/FINDINGS.md:3-8,46-64,84-86` | reopen (new frozen lane): energy fade with exit at Monday cash open. The equity subset has only 10 trades, so it cannot decide |
| R468 | asiaclose_v1 | calendar | PARTIAL / PASS by rule | K1 payer not stated; K4 A carried by two Hong Kong AI listings (ZHIPU +331 bp, MINIMAX +112 bp, `:44`); without them A p 0.12 (`:50`); K3 "entry bounce ruled out" only shifts W, not the E and X1 valuation (`:51-52`); K2 fade not balanced against the home index or peers | `experiments/asiaclose_v1/FINDINGS.md:3-5,18-27,44-52,58-64` | re-check: peer-residual (balanced) version on the same frozen events; treat B (+9.5 bp, p 0.71, median -0.1) as the verdict. Relabel to decayed |
| R466 | xvwknd_v1 | calendar | PENDING / INCONCLUSIVE | K3 explicitly bounce-biased (`:19-21`); K4 n 55 < 100 floor (`:3-4`); K2 the venues' gap is the oracle network echo (`oracle_frontiers` section "What it changes") | `experiments/xvwknd_v1/FINDINGS.md:3-4,10-21,53-58` | re-check: book walks on both venues at Sunday 19:00 (costs only); new idea: OKX-to-xyz weekend ratio (Seo et al. weight 0.343) |
| R461 | earnperp_v1 | events | NULL | K5 unit 30 bp = 9 bp each way (standard fee, not the 0.9 bp growth-mode fee), plus 10 bp assumed; K2 window inside closed hours (first move from cash close); K4 bmo continuation +80 bp is one of 32 cells, raw p 0.03 (`:38-43`); MDE 127 bp (`:8-9`) | `experiments/earnperp_v1/FINDINGS.md:3-9,33,38-43,57-65` | re-check cost only: D1 at a measured 8-9 bp unit gives about +13 bp, still not significant (p 0.64). The bmo diagnostic needs a new lane, next season mid-Jan 2027 |
| R435 | stock_tugofwar_v1 | calendar | NULL | K6 open proxy 10:00/09:00 on hourly bars (`:20`, `:93`); the sign appears only pre-open (`:57-59`); K2 the ON leg of a 24/7 perp is a closed-market return; K5 MEXC cost 22 bp per day, not the xyz measured cost | `experiments/stock_tugofwar_v1/FINDINGS.md:20,32-38,50-59,65-69,93` | reopen (new id): 09:30 print on 1-min data (not in repo), B2 and the ON-to-ID IC at 09:30 vs 10:00 |
| R471 | cryptomon_v1 | calendar | NULL | K4 three crash Mondays drive the B slope (exploratory, `:50-53`); power weaker than planned (`:32-35`) | `experiments/cryptomon_v1/FINDINGS.md:3,20-35,50-53` | none |
| R244 | weekendlink_v1 | calendar | NULL | K2 BTC weekend move correlates +0.46 with the QQQ opening gap (already priced); registry only | registry row 67 | none (retire) |
| R337 | levels_lighter_v1 | charts | NULL | K5 Lighter measured book: break-even 6.1 bp a side; net -0.1 at 2x (`:4-5`, `:17`) | `experiments/levels_lighter_v1/FINDINGS.md:1-5,17` | none; use as the cost check for R336 |
| R336 | levels_mexc0_v1 | charts | PARTIAL | K5 MEXC zero-fee with half-spread floor 1 bp; the same rule on Lighter's book fails 2x (R337). The PARTIAL is MEXC-only | `experiments/levels_mexc0_v1/FINDINGS.md:1-10`; `experiments/levels_lighter_v1/FINDINGS.md:1-5` | relabel "MEXC only"; check venue reach (`docs/reviews/venue_access_fr_20261110.md`) before any claim |
| R330 | level_probability_v1 | charts | PARTIAL | the preselected rule is NULL_INACTIVE (declines all 178 validation cases); PARTIAL describes an accounting component only (`:3-5`) | `experiments/level_probability_v1/FINDINGS.md:3-5` | relabel "component" (retire as an edge claim) |
| R349 | minflow_v1 | micro | PARTIAL / PASS gate 0 | K4 57 rules; K5 net +2.7 bp a trade at Lighter's measured cost; decay: +0.6 bp since 2025-07, about 0 in 2026 (`:14-16`) | `experiments/minflow_v1/FINDINGS.md:3-15,47` | downgrade to decayed; R351 tests the same rule on nine more coins (registry row 158, not read here) |
| R304 | mlrank_v2 | xsec | PARTIAL | metrics-leak (R332): presence book +50.3 bp (t 4.47); header denies the leak (`:1`) | `experiments/mlrank_v2/FINDINGS.md:1,3,7`; `experiments/mlrank_v3/FINDINGS.md:4,8-11,53-55` | retire claim; check no batch slot uses the gbm h7 pick (R304 `:3`) |
| R299 | mlrank_v1 | xsec | PARTIAL | its own FINDINGS: "not trusted: its inputs leak survival" (`:3-6`) | `experiments/mlrank_v1/FINDINGS.md:3-6` | retire / relabel NULL-leak |
| R332 | mlrank_v3 | xsec | NULL | K4 correct and complete panel; the presence book is the diagnostic | `experiments/mlrank_v3/FINDINGS.md:3-4,8-11` | none (this is the correction) |
| R197 | flow72_v2 | flow | CONFIRMED / PASS design check | K4 cells chosen after R196 and with both periods (`:32`); holdout R198 NOT CONFIRMED (t 1.22, registry row 17) | `experiments/flow72_v2/FINDINGS.md:3,32-33`; registry row 17 | retire CONFIRMED; the forward R200 decides (not read) |
| R185 | atlas_v1 | xsec | CONFIRMED (in-sample, gross) | K4 338,240 cells; most edges below cost (`:3-4`) | `experiments/atlas_v1/FINDINGS.md:3-4,9` | relabel "in-sample gross" |
| R192 | atlas_ctx | xsec | CONFIRMED (in-sample, gross) | K4 8.3M lift cells; "a few hundred" with validation edge above cost | `experiments/atlas_ctx/FINDINGS.md:3-4` | relabel "in-sample gross" |
| R195 | atlas_mtf | xsec | CONFIRMED (in-sample, gross) | K4 643,736 cells; 431 excess edges above 1x cost; 54% replication vs 6.7% placebo | `experiments/atlas_mtf/FINDINGS.md:3-4` | relabel "in-sample gross" |
| R181 | unlocks_deep | events | CONFIRMED (in-sample) | K4 threshold 0.82 chosen in-sample, and forward scores split at it; registry only | registry row 5 | re-check: confirm the forward split uses the frozen 0.82 |
| R265 | unlocks_v1 | events | PARTIAL | K4 replicates the old R179 rule, read by an old session in 2021-26 (not blind, registry row 83); R258 daily-price check t 3.20 (registry row 128) | registry rows 83, 128 | none until forward R266 decides (not read) |
| R259 | unlocks_funding_bounds_v1 | events | PARTIAL | full-cohort funding INCONCLUSIVE; 14 unknown (registry row 129) | registry row 129 | none |
| R473 | tlteom_v1 | calendar | PARTIAL | K5 measured xyz:TLT funding about 4x the assumed 5.5%/yr; net edge gone at that level (`:8-9`) | `experiments/tlteom_v1/FINDINGS.md:1-9` | retire (cost kills it) |
| R392 | reserved_batch3 | reserved | PARTIAL | GLT +0.73%/yr, below cash; C17 p 0.0012 fails alpha 0.001 by a hair (`:3-4`) | `experiments/reserved_batch3/FINDINGS.md:3-4` | relabel NULL on the economic test |
| R276 | xvfac_v1 | xsec | PARTIAL | the book fails; "PARTIAL by the mechanical rule, NULL on the question" (`:1-3`) | `experiments/xvfac_v1/FINDINGS.md:1-3` | relabel NULL |
| R282 | pitfac_v1 | xsec | PARTIAL | age book net t 0.64, vol_mcap 0.39; IC is a median effect, not a book (`:3-7`) | `experiments/pitfac_v1/FINDINGS.md:3-7` | relabel "rank IC only" |
| R202 | propfirm_v1 | portfolio | PARTIAL (descriptive) | K4 best-of-10 sizes optimistic (registry row 25); no new return hypothesis | `experiments/propfirm_v1/FINDINGS.md:1-6` | none |

## 3. Registry labels to fix (the list for the next registry pass)

- Retire: R304 PARTIAL (leak), R299 PARTIAL (its own FINDINGS), R473 PARTIAL (cost).
- Relabel to the FINDINGS verdict: R462 (FINDINGS PASS gate 0, registry PARTIAL), R468 (PASS by rule, registry PARTIAL),
  R349 (PASS gate 0, registry PARTIAL), R466 (INCONCLUSIVE, registry PENDING), R330 (component only), R392 and R276 (NULL on
  the economics), R282 (rank IC only).
- Relabel the CONFIRMED label: R197 (holdout NULL), R185, R192, R195 (in-sample gross).
- Note: R462, R468 and R349 use "recorded PARTIAL" for a gate-0 PASS, a convention stated in their own FINDINGS. I do not
  object to the convention, but a reader filtering on `verdict` will miss the PASS. A fixed label set would prevent this.

## 4. The closed-market class (K2): which rounds touch it, and does balance or a different instant change them?

| class member | rounds | effect of a balanced design | effect of a different reopen or instant |
|---|---|---|---|
| single-stock perps, weekend | R462, R465, R466, R530 (balanced, forward), R463, R467 (forward) | the `rel` book earns more (+55.8 vs +42.4 bp, R462 `:52-53`); the common component is anchored and must come out | the reversal falls at 20:00-22:00 Sunday (R465 `:72-76`); entering at 19:00 buys the thinnest book. An entry at 20:30-21:00 would capture most of the move (40 of 45 bp, inference from R465's table) at a lower cost |
| index, commodity, FX perps, weekend | R464 (NULL), R432 (NULL) | no change; the common component is anchored by futures, so a balanced book removes the signal the lab wants | the futures reopen at 18:00 is the anchor, so the exit at reopen+2h is not the wrong instant. For the energy names the lead is a Monday cash-open exit (R432 `:55-64`) |
| closures in Asia | R468 (A +87.8, B +9.5) | the balanced (peer-residual) version is untested and is the first thing I would run | A reversal at the home exchange's reopen is not measured; the hour-after exit is a guess |
| overnight leg of 24/7 stock perps | R435 (NULL) | the B2 reversal book is the one the oracle thesis predicts; it is negative at 10:00 and only weakly positive at 09:00 | the reversal should fall at the 09:30 print, which no proxy sees |
| earnings on 24/7 perps | R461 (NULL) | hedged with SPX500 changes nothing (D1 +13, D2 -8, `:33`) | the window is inside closed hours; a 09:30-based entry was not tested |
| Lighter zero-fee venue | R336, R337, R465 | R337 is the cost check for the same rule that R336 passes on MEXC | n/a |

Answer to K2. Two of the five closed-market rounds that are tradeable from France (R462, R465) survive the measured cost
check, but both enter or exit at instants the venue's own rule and the Sunday depth data say are wrong by a window. The
index control (R464) and the earnings round (R461) are consistent with the anchor mechanism. The balance and instant
changes are ideas, not findings: none is tested.

## 5. The five most promising things to reopen or re-check

Ranked by expected value times how cheap the decisive observation is.

1. **R462/R465 entry instant (Sunday 20:00-21:00).** Mechanism: the reversal occurs after the external anchor returns at
   Sunday 20:05, and the entry at 19:00 pays the thinnest book (`reflection_20261124_closed.md` section 8;
   `experiments/ltwknd_v1/FINDINGS.md:72-88`). Cheapest decisive observation: book walk cost at a 20:30 entry against 19:00
   on the two recorded Sundays. The depth table never reports 19:30-21:30 (`reflection_20261124_closed.md` section 8).
   This is a cost observation, not a return, so it does not score a forward lane. The return test is a new frozen lane
   with the 20:30 entry, decided after 15 weekends (R463's power is in `reflection_20261124_closed.md` section 9; the balanced
   book's power is in the `mechanism_map.md` row).
2. **R435 open instant (09:30).** Mechanism: the oracle thesis puts the reversal at the cash open, which the 10:00 and 09:00
   proxies cannot see (`experiments/stock_tugofwar_v1/FINDINGS.md:20,93`). Cheapest decisive observation: 1-minute candles for
   the top 30 MEXC stock perps over 2026-04 to 2026-10, then the B2 book and the ON-to-ID IC at 09:30. This is new data (not in
   repo) and a new id, so its trials are counted.
3. **R432 energy exit at the Monday cash open.** The slope gives -0.26 to the cash open and -0.18 at +60 min
   (`experiments/weekend_reopen_v1/FINDINGS.md:46-54`). Energy carries it (+102 bp net at 1x over 16 weekends, the best of a
   144-cell grid, picked after the run, `:55-64`). R432 itself names the cheapest test: MEXC's USOIL and UKOIL hourly history from
   2026-01-30 covers about 9 weekends not yet read for this question (`:84-86`). That is a futility-sized check, not a confirmation.
4. **Retire the R304 leak and audit the panel.** R332 is the decisive check and it is done. The remaining cheapest action is
   to confirm that no other lane on the same daily panel (`pitfac`, `xsbattery`, `fundxs`) uses a metrics-presence column as a
   feature. The check is the presence-only book on each lane's panel, a cost-free diagnostic.
5. **R468 with a peer-residual (balanced) design.** The A effect is two Hong Kong AI listings, and B is flat
   (`experiments/asiaclose_v1/FINDINGS.md:44-52`). The balanced version subtracts the peer median from each perp's closure move.
   The cheapest decisive observation is the residual version on the same frozen events, which is a new trial, and it tests
   whether the A effect is the closure or the listing era. The W-earlier bounce check does not test valuation at E or X1
   (`:51-52`), so the mid-price question remains open.

## 6. Weakest links in this audit

- I read 25 FINDINGS in depth. The other 146 non-carry rounds are judged from their registry rows and notes, which may hide
  a flaw in a round I did not open.
- The Nagel bounce figure and the Seo et al. table are cited from the lab's intake cards, not re-read from the papers.
- The trade.xyz rules are cited from `reflection_20261124_closed.md` section 7. The fetched `llms-full.txt` is not in the repo.
- The 40 of 45 bp capture at a 20:30 entry is my inference from R465's hourly table, not a measured result.
- The overnight leg of R435 is a closed-market return only by inference. The MEXC stock perps' closed hours are not
  documented in the round's own FINDINGS.
- The registry verdicts are incomplete (128 NaN rows in the whole registry), so the NULL list is keyword-based.
