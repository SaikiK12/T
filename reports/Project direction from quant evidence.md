# Cut the search; measure MEXC costs

**The project is on a wrong path in its search and right to insist on forward proof, and no result on MEXC altcoins has cleared a registered test yet.** The registry holds **77 rounds and 9,472,034 nominal trials**, **54 of them NULL**, and one registered holdout pass: funding carry, at **+1.45% total at 1x, +0.66% at 2x and about -0.12% at 3x** (the 3x figure is my linear extension of the lane's own components). The flow book A misses its holdout bar at every cost (t 1.22 at 1x), and its 19-day MEXC forward replay earns **+4.55% at 1x, +3.63% at 2x and +2.70% at 3x** on a t of 0.84, which cannot be told from zero. The non-fee sources are real but small: carry earns about **1.2% a year** on the book at 1x, its MEXC replay is slightly negative, and maker entry is a descriptive result that no real fill data has tested. The owner's plan for about 5,000 brute-forced strategies or mixes, with Fibonacci and Monte Carlo variants and leverage multipliers, should not run as described, because the holdout it needs is spent, the Fibonacci family is closed, and a leverage sweep changes size and drawdown but not the t-statistic. Any edge that survives must earn its place on on-time days after 2026-10-20, which means waiting into 2027, not searching faster.

## Breadth is the wrong direction, and the venue is unmeasured

The discipline here is real. The integrity note reports 70 of 71 local specs hash-verified and 0 errors, costs are charged by liquidity rank, and losing results are recorded as NULL. The problem is volume. Three atlas rounds, R185, R192 and R195, hold **98.2%** of the nominal trial count ([registry multiplicity note](/home/user/T/research_notes/Project%20direction%20from%20quant%20evidence/registry_multiplicity.md)). Since R213 each round averages under ten trials, but the families now widen into TradFi calendars, FX, pairs and ICT levels, and the program count cannot see that widening. I recomputed the multiplicity bars: two-sided Bonferroni at 5% needs **|t| 5.84** at the 9.47M total and **4.79** on the 29,875 non-atlas trials. The best holdout t in the repo is 2.74, so it clears neither.

The holdout is the larger loss. The program's holdout starts 2025-07-01 ([lab/config.py](/home/user/T/lab/config.py), `VALIDATION_END = 2025-06-30`). About 20 rounds have read it, and at least seven read the flow window ([registry multiplicity note](/home/user/T/research_notes/Project%20direction%20from%20quant%20evidence/registry_multiplicity.md)). The R200 forward text says "a forward period no one has seen", and the project's own [critique](/home/user/T/docs/CRITIQUE.md) concedes that is wrong now that the replay has been read. The clean test is therefore forward. The 90-day decisions for R215, R218 and R220 fall on 2027-01-17 at the earliest.

The venue gap decides the owner's question. The owner trades MEXC alts, yet the checkout holds about 22 days of MEXC klines for 40 contracts, the contract list is today's snapshot and so covers survivors only, and the history fetch has not run ([external literature note](/home/user/T/research_notes/Project%20direction%20from%20quant%20evidence/external_literature.md), section 4). Every archive result is priced on Binance. The engine charges liquidity-tier costs of 6, 8, 12 and 20 bp one way for ranks 1-20, 21-50, 51-100 and beyond ([engine cost matrix](/home/user/T/lab/engine.py)). The flat 0.002 in `config.py` is not used by the lab engine.

## Every survivor is spent, too small, or fails at 2x

The table gives every return at 1x, 2x and 3x, with the t-statistic where the source reports one.

| Result (window) | 1x | 2x | 3x | t at 1x | Status |
|---|---|---|---|---|---|
| Funding carry, R191 (holdout, total) | +1.45% | +0.66% | about -0.12% (derived) | 2.07 (2x: 1.14) | Only registered holdout pass; fails at 2x ([holdout.json](/home/user/T/experiments/carry_holdout/results/holdout.json)) |
| Flow book A, R198 (holdout, bp/day) | 22.7 (+82.9%/yr) | 16.9 (+61.8%/yr) | 11.1 (+40.7%/yr) | 1.22 | Fails; max drawdown 47% ([holdout.csv](/home/user/T/experiments/flow72_holdout/results/holdout.csv)) |
| Top-trader book B, all symbols, R198 (holdout, bp/day) | 19.6 | 18.6 | 17.6 | 2.72 (2x 2.58; 3x 2.44) | Reported, not decided; read by at least six lanes |
| Top-trader book B, crypto only, R216 (holdout, bp/day) | 18.3 | 17.4 | 16.5 | 2.74 | Best of seven series per the scoreboard; holdout spent ([venue gap](/home/user/T/experiments/venue_gap_v1/FINDINGS.md)) |
| Flow book A, crypto only, R216 (holdout, bp/day) | 22.3 | 17.3 | 12.3 | 1.25 | Fails |
| Flow book A, MEXC replay, R215 (19 days, total) | +4.55% | +3.63% | +2.70% | 0.84 (iid, my calculation) | Undecided; hit rate 47% ([tickets](/home/user/T/experiments/mexc_fwd/journal/tickets.csv)) |
| Flow book B, MEXC replay, R215 (19 days, total) | -0.11% | -0.25% | -0.39% | about 0 | Negative on the owner's venue |
| Carry, MEXC replay, R220 (19 days, total) | -0.015% | -0.12% | -0.23% | not reported | Zero, invested every day ([carry_fwd tickets](/home/user/T/experiments/carry_fwd/journal/tickets.csv)) |
| Flow X2, MEXC replay, R218 (19 days, total) | +5.94% | +4.96% | +3.98% | not reported | Chosen after R217, which did not pass ([tick log](/home/user/T/experiments/mexc_fwd_sq/tick.log)) |
| Maker entry, discovery book, R193 (%/yr) | 63 | 44 | 25 | 1.47 | In-sample only; validation +14%/yr at t 0.18 ([maker FINDINGS](/home/user/T/experiments/maker_v1/FINDINGS.md)) |
| Liquidation fade, R206 (bp/day, null) | -35.9 | -76.1 | -116.2 | -1.96 | Null; long cascades continue ([liq FINDINGS](/home/user/T/experiments/liq_v1/FINDINGS.md)) |

The concentration numbers reproduce the lanes' own notes when I recompute them from the saved daily series ([sizing_v1 daily.npz](/home/user/T/experiments/sizing_v1/results/daily.npz)). Book A's top ten holdout days exceed its entire holdout sum (113%), and without them its t is -0.16. Book B's top ten days are 47% of its sum, and without them its t falls to 1.58 with a mean of 9.8 bp/day. Book B's holdout mean of 18.0 bp/day is 3.6 times its in-sample mean of 4.9 bp/day (t 2.64). Book A's holdout mean of 21.9 bp/day is 1.8 times its in-sample 12.0. A window that was read many times and shows the largest effect is the signature of selection, and the repo has no test that separates that from a regime change.

Power is the other constraint. At the replay's dispersion for MEXC book A (daily standard deviation 124 bp), a 90-day test at t of at least 2 passes **about 43%** of the time if the true mean is the replayed 24 bp/day, **about 29%** at the 2x cost, and **about 2%** if the mean is zero. These are iid approximations, and the overlapping 72-hour slices make true power lower. Even a real edge at the replayed size would more often fail the decision than pass it.

The nulls are more trustworthy than the survivors. The integrity note's defects mostly inflate results. Missing returns and funding are zero-filled in the slice engine, so a held coin with a missing bar earns nothing and stays on ([lab/slices.py](/home/user/T/lab/slices.py), line 64, legacy mode), and the note reports that delisted and ineligible coins keep earning. I confirmed the zero-fill in code and did not check the eligibility claim. The one full-pipeline null, R182, returned NOISE: two validation survivors against a null 95th percentile of four, p 0.22 ([registry row R182](/home/user/T/registry/rounds.csv)). Its folder is absent here.

## Funding and basis are the only non-fee sources, and both are small

Carry is the one mechanism with a frozen holdout pass, and it earns in bursts. In the archive it returned about +35% in 2021, -0.1% in 2022, +3.3% in 2023, +8.1% in 2024 and +0.8% in 2025 through June ([carry_v1 FINDINGS](/home/user/T/experiments/carry_v1/FINDINGS.md)). Over the holdout, funding paid +1.44% and basis +0.80% of total capital, costs took -0.79%, and only 25% of capital was invested on average. The top-50 trailing funding averaged **-57% APR** over the window, so positive carry was scarce ([holdout.json](/home/user/T/experiments/carry_holdout/results/holdout.json)). On MEXC the picture is worse. The highest-funding names on the Binance list are equity perps with no spot pair, and **38 of 59** MEXC symbols have a spot pair at all ([carry_fwd status](/home/user/T/experiments/carry_fwd/journal/status.json)). The 19-day MEXC replay returned zero at 1x and slightly negative at 2x and 3x. At 1x, archive carry is worth about **$120 a year per $10,000**, and roughly nothing after 2x costs.

Basis is the least tested of the non-fee sources. The lab's basis term in carry is the premium index, not the traded spot-perp spread ([carry_v1 FINDINGS](/home/user/T/experiments/carry_v1/FINDINGS.md)). The spot-perp arbitrage lane, M047, is blocked because spot klines for the top 50 are absent ([methods queue](/home/user/T/docs/METHODS_QUEUE.md)). The literature points here. He, Manela, Ross and von Wachter find crypto perp deviations larger than in FX, shrinking as markets mature, and a search snippet says simple arbitrage keeps a high Sharpe at Binance's costs ([arXiv:2212.06888](https://arxiv.org/abs/2212.06888)). I did not read the paper, and the snippet gives no cost figure.

Maker inventory is the most interesting descriptive result. At one sigma below the close, a limit entry earns **+23.5 bp per trade net in discovery**, where a market entry loses **3.4 bp** ([maker FINDINGS](/home/user/T/experiments/maker_v1/FINDINGS.md)). But the book built from four discovery-selected cells earns **+14% a year at t 0.18** in validation. Its fill model, a fill when the next bar trades 2 bp through the limit, gives fill rates from 32% to 77% that no real fill record calibrates. MEXC's maker fee averages 0.64 bp with a maximum of 1 bp across the coins in the fee snapshot, below the 2 bp the lane assumes ([mexc_fwd status](/home/user/T/experiments/mexc_fwd/journal/status.json)). That makes the lane conservative on fees and optimistic on fills. Liquidation and cascade lanes are null, and the long side keeps moving against a buyer ([liq FINDINGS](/home/user/T/experiments/liq_v1/FINDINGS.md)).

Capacity caps all of it. Depth within 0.5% of mid on the smaller side has a median of **$1.37M**, a 10th percentile of $109k, and seven of 32 coins below $250k. The thinnest are BTW at $21k and AKE at $23k ([mexc_costs status](/home/user/T/experiments/mexc_costs/journal/status.json)). The repo states no capacity figure ([next search space](/home/user/T/docs/NEXT_SEARCH_SPACE.md), line 20). The owner's own record is a rough check. The repo reports **+$3,591 over 124 fills**, labels it "beta, not edge", and finds **-$39** without the top five fills ([OLD_SESSION_EDGES](/home/user/T/docs/OLD_SESSION_EDGES.md), line 149). The same P&L appears with 61 and 57 trades elsewhere in that file (line 183). The realised record is a realised record, so no 1x/2x/3x split applies.

## The 5,000-strategy plan spends the holdout it needs

The plan is not in the checkout. A search for "Fibonacci", "Monte Carlo" as a plan, and "5,000" finds nothing, so I assessed it as the brief describes it. Measured against the rules, it fails on five counts.

The first is registration. AGENTS requires a frozen specification before any statistic. A 5,000-candidate family can be frozen, but the repo's own rule says a search must state its mechanism, primary outcome, candidate count, windows already viewed and stop rule ([next search space](/home/user/T/docs/NEXT_SEARCH_SPACE.md), line 11). It also says to avoid brute-forcing the earlier 93,000-cell grid, which is the same pattern.

The second is trial accounting. Logging 5,000 rows, or 15,000 with three leverage levels, barely moves the program bar, which stays near 5.8 and moves on the non-atlas count from 4.79 to 4.82. The arithmetic is not the real objection. For 5,000 independent candidates the in-sample bar is |t| 4.42 (4.65 for 15,000), and the strongest in-sample lane, carry at discovery t 3.80, would not clear it.

The third is the holdout. Any search over data after 2025-06-30 spends a window that about 20 rounds have already read. The plan could select only on data before 2025-07, and the winner would then need forward days. That is the same clock as before.

The fourth is the Fibonacci family. The checkout has none, and the nearest closed family is chart patterns: R171-R173 tested 2,671 combinations with 0 passing, and the family was closed ([methods queue, M074](/home/user/T/docs/METHODS_QUEUE.md)). A literature note cites Hudson and Urquhart on about 15,000 Bitcoin technical rules that found no out-of-sample predictability ([Hudson and Urquhart](https://link.springer.com/article/10.1007/s10479-019-03357-1); not re-read). A Fibonacci brute force reruns a family the repo has already closed and needs a new reason to reopen it.

The fifth is the leverage sweep and the Monte Carlo. A constant multiplier scales one return stream, so Sharpe and t do not change, and drawdown and liquidation risk rise. The repo's sizing evidence agrees. The confidence-scaled rule R217 missed its frozen +0.3 bar at +0.15 in discovery ([R218 PREREG](/home/user/T/experiments/mexc_fwd_sq/PREREG.md)), and volatility targeting cut book A's holdout drawdown from 47% to 27% with Sharpe flat ([EDGE_SCOREBOARD](/home/user/T/docs/EDGE_SCOREBOARD.md), line 104). The 1x, 2x and 3x in the rules are cost stresses, not leverage. Liquidation, margin tiers and cross-margin are not modelled ([perp execution and risk](/home/user/T/docs/PERP_EXECUTION_AND_RISK.md)), and leverage would take larger size in the thinnest coins, where depth is $21k to $23k. The repo's Monte Carlo is the null in `lab/nulls.py`, which reruns the whole search on 60 shifted panels. Only tests import it. The scripts use two placebo shifts, so the FDR rests on two draws ([integrity note](/home/user/T/research_notes/Project%20direction%20from%20quant%20evidence/evidence_integrity.md), item 5). Using Monte Carlo to generate candidates is a random search and needs that same full-pipeline null, which has run once.

What the rules allow is narrower: a small frozen family with a stated mechanism, run on pre-2025-07 data, with the full null actually executed, 1x/2x/3x reported, the trial count logged, and leverage treated as a risk overlay with its own gate. As written, the plan produces winners that no clean window can test before 2027.

## Why a survivor would not prove it works now

The question is why any surviving edge would work now rather than before or after. The repo has no persistence mechanism that passes its own tests, and four pieces of evidence argue against assuming one.

Carry shows the time dependence plainly. Its yearly sign and size change, as shown above. Borri, Liu, Tsyvinski and Wu report Sharpe 6.45 for the full sample, 4.06 from 2024 and negative in 2025 on Binance BTC ([arXiv:2510.14435](https://arxiv.org/abs/2510.14435); figures from the literature note, not re-read, and no cost figure).

The best holdout effect is 3.6 times its in-sample effect, so the "now" performance looks like selection plus a read-many window, not a persisting mechanism.

The apparent forward edge on Binance is largely equity exposure. TradFi perps carried **49%** of book A's replay gross. Moving to MEXC crypto cut the replay from +22.5% to +4.7%, and **13.8 of the 17.8 points lost** came from stock and semiconductor perps ([venue gap FINDINGS](/home/user/T/experiments/venue_gap_v1/FINDINGS.md)). A 2026 semiconductor move is not a MEXC altcoin edge.

The venue's costs also moved within hours. The number of coins at a 4 bp taker fee rose from **4 to 21 of 31** between 19:43 UTC on 19 October and 00:42 UTC on 20 October ([depth journal](/home/user/T/experiments/mexc_costs/journal/depth.csv)). The cause is not recorded in the repo.

So the defensible standard for a survivor is that its mechanism is still present and it earned on days no one had read. Only on-time days from 2026-10-20 meet that standard. Before then, performance is what the search selected. After enough on-time days, the first clean read is limited by power, at about 43% at the replayed mean.

## Where the notes disagree, and which source wins

Five notes were written independently, and several disagree. I recomputed the disputed figures from the repo where I could. The table gives the trusted source and why.

| Topic | One source | Other source | Trust | Reason |
|---|---|---|---|---|
| Program trial total | 9,472,034 (registry recount) | 9,472,031 ([EDGE_SCOREBOARD](/home/user/T/docs/EDGE_SCOREBOARD.md), line 3) | 9,472,034 | Computed from the file. The 3-trial gap matches R253 but its cause is unverified |
| "CONFIRMED" rows | 7 rows marked CONFIRMED in the registry | One holdout pass, R191 ([carry FINDINGS](/home/user/T/experiments/carry_holdout/FINDINGS.md)) | FINDINGS | Others are in-sample or validation: carry_v1 says "CONFIRMED in-sample", flow72_v2 says "design check" |
| Holdout window | 2025-07-01 ([FOUNDATION](/home/user/T/docs/FOUNDATION.md), `config.py`) | 2020-01-01 to 2026-10-19 in volrisk_v1 and fxindex_v1 PREREGs | 2025-07-01 | Program rule. The 2020 window includes discovery, so those "holdouts" are not holdouts |
| Lab cost tiers | "6 or 8 bp one way" (economics note prose) | 6/8/12/20 bp in code and in the same note's own table | Code | Prose error for ranks 51 and below |
| MEXC API cost | "measured" median 9.29 bp (two notes) | 8 bp constant plus measured impact ([record_mexc_depth.py](/home/user/T/scripts/record_mexc_depth.py), lines 26 and 97-98) | Code | The fee is an assumption. Only the web figure uses each coin's measured fee, median 4.65 bp |
| R215 cost multiple | 5.9x ([economics note](/home/user/T/research_notes/Project%20direction%20from%20quant%20evidence/forward_and_economics.md)) | 7.6x (position-cost column only, my calculation) | 5.9x | The 1x-to-2x gap includes hedge trading cost, which the slice engine scales by the cost multiple ([slices.py](/home/user/T/lab/slices.py), line 96) |
| R220 carry replay | Registry: 18 days, -0.0006%, 2x -0.09% | Tickets: 19 days, -0.015%, 2x -0.12%, 3x -0.23% | Tickets | The registry text is a stale snapshot |
| R215 replay | Registry: "10-01 to 18", +4.7% | Tickets: 19 days, +4.55% | Tickets | Same reason |
| Book A holdout mean | 22.7 bp/day (R198 output) | 21.9 bp/day (sizing re-run, my 21.85) | R198 output | Owning lane. The 4% gap is unexplained |
| Strict on-time days | One on-time day, 10-19 (late flag = 0) | Zero (DEVIATIONS: hours computed 22-555 minutes after close; GATES: 60 minutes) | Zero | The late flag tests against the freeze date ([forward_tick.py](/home/user/T/scripts/forward_tick.py), lines 28 and 110), not GATES' 60-minute rule |
| R200 decision | DEVIATIONS: 18 replay days count | GATES: replay days never count for new lanes | GATES | This is an owner decision on a grandfathered lane |
| R199 status | Registry: REGISTERED | R200 row and FINDINGS: ABANDONED | ABANDONED | The row was superseded; the registry is append-only |
| R205 | Binance top-vs-crowd t 2.08 over 157 days, could be a second holdout pass | Registry marks NULL; a same-window comparison, not a registered holdout test | NULL | Registry and PREREG governance |

## Conclusion: measure the venue, then test one lane

The project should not run the 5,000-candidate plan, and it should not add rounds on data after 2025-06-30. The next step is measurement before modelling. First, the owner should give the explicit yes that AGENTS requires before a large download, so that MEXC history exists beyond 22 days. Second, the MEXC API cost should be relabelled as an assumed 8 bp fee plus measured impact, and the owner should supply the real fee tier. The 1x-versus-2x choice depends on it, and the repo's own depth file shows taker fees between 0 and 4 bp. Third, the affected results should be rerun after the zero-fill fixes, since no archived result has been recomputed.

Only then should one lane be registered. Carry with a spot leg (M047) is the best-supported non-fee mechanism with a frozen pass, although it earns about $120 a year per $10,000 at 1x and fails at 2x. Weekly long-short momentum on liquid perps is the literature-backed directional alternative. Fičura's abstract reports weekly momentum in large, liquid coins at t 2.33, with the sample and costs not given in the abstract ([FFA working paper 2023](https://wp.ffu.vse.cz/artkey/wps-202301-0003_impact-of-size-and-volume-on-cryptocurrency-momentum-and-reversal.php)). The repo has tested only six-coin, spot, long-only versions. Either lane should log its trial count, run the full null, and report 1x, 2x and 3x.

Two owner decisions come first. R200's 2026-12-29 decision counts 18 replay days, which its DEVIATIONS allow and its GATES forbid for new lanes. R221 decides on crypto-only book B, which was picked as the best holdout t from seven series, and the family of three was set after that pick. The honest expectation is small money. The only non-fee source with a frozen pass is worth about $120 a year per $10,000 at 1x, the flow books carry drawdowns near 47%, and the first clean forward number arrives around January 2027. The binding constraint is not the statistics or the search. Nothing in the repo has been measured on the owner's venue, at the owner's fees, or at the owner's size, and the 5,000-candidate plan would spend the last clean window on that mismatch.

## Not checked

| Item | Why it could not be checked here |
|---|---|
| Market data | `data/` and `cache/` are absent. I did not recompute any return from prices. I used the saved daily series, the journals, the registry and the FINDINGS files |
| Lane folders | `experiments/unlocks_sf`, `unlocks_deep`, `hypermine`, `hypermine_expand`, `funded` and `challengeoption` are absent (R143, R144, R180-R183). The unlock short (R181, t 4.06, confirmed in the registry, holdout read by the old session), the ZRO score and the 364 tickets cannot be verified. This is the strongest result the owner remembers, and it is unverifiable here |
| The 5,000-strategy plan | Not in the checkout. Assessed as the brief describes it |
| Unit tests | The checkout's Python lacks numba and scipy. The notes report 343 passing in a scratch environment. I did not run tests and changed no code |
| Survivor re-runs | I did not re-run any lane. Recomputations used saved series, [reg_check.py](/tmp/claude-0/-home-user-T/62f4d126-48a1-555e-afe1-7e454d28bc35/scratchpad/reg_check.py) and [tickets_check.py](/tmp/claude-0/-home-user-T/62f4d126-48a1-555e-afe1-7e454d28bc35/scratchpad/tickets_check.py) in the scratchpad, and read-only tests |
| Literature | The icm.edu.pl pages returned HTTP 403 (Fieberg, Mercik). The trend-factor paper was seen by title only. The Christin et al. paper was not found. Borri et al., He et al. and Hudson and Urquhart figures come from notes or snippets. No source gave a net-of-cost return with 1x, 2x and 3x figures |
| MEXC fee change | The cause is not in the repo. I checked only the seven depth snapshots |
| Room protocol | I read `docs/ROOM.md` but not issue #7, and I did not post. This was a read-only brief |
| Carry 3x | Derived by linear extension of the 1x and 2x components in `holdout.json`. The lane did not report it |
| Owner's trading record | Taken from a repo note and not verified |
| Lab timing | Whether the zero-latency panel inflates other books beyond the 1-2% delay effect (R213) is not measured |
