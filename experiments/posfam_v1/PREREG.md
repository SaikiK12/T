# PREREG: posfam_v1 (R211), which half of top-vs-crowd carries the edge? The unused top-account ratio

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R211
- **Owner (single writer):** the session that froze it
- **Code:** `scripts/run_posfam.py`, `lab/flowfeat.load`, `lab/features.bins_xs`, `lab/slices.py`

## Why
Binance's archive has three positioning ratios: top traders by position (top_ls_sum), top traders by account
(top_ls_count) and all accounts (ls_count). The lab's strongest lead, top_vs_crowd = log(top_ls_sum) - log(ls_count),
splits exactly into
- **whale_vs_top** = log(top_ls_sum) - log(top_ls_count): the top traders' *money* against their *headcount* (a few
  large positions leaning one way), and
- **topacct_vs_crowd** = log(top_ls_count) - log(ls_count): the top accounts' headcount against the crowd's.
A third, **top_acct** = log(top_ls_count), is the top-account ratio alone.

## What the author had seen
Every result of top_vs_crowd, top_ls and crowd_ls (atlas_v1 R185, flow72 R196-R198, forward R200: 18 days). top_ls_count
has never been loaded into any feature or statistic (`lab/flowfeat.METRIC_COLS` omits it). Because the two halves sum
to top_vs_crowd, whose holdout (2025-07..2026-09) is known (+71%/yr as a book), the holdout here is **not clean**: the
residual against the top_vs_crowd book is reported for that reason.

## Books
For each feature f in (whale_vs_top, topacct_vs_crowd, top_acct): cross-sectional xs8 bins among eligible coins
(`features.bins_xs(f, elig, 8)`, top 50, as top_vs_crowd); bin 0 opens **short** 72 h slices, bin 7 opens **long**
72 h slices: 6 books. Size 1 / (72 x K), K = the book's mean slices opened per hour over 2021-01-01..2023-12-31;
universe hedge; tier costs; funding. As R197.

## Stages
1. **Discovery** 2021-01-01..2023-12-31: a book passes if its daily net at 1x has NW t (lag 10) >= 2 and its 2x mean
   is positive.
2. **Validation** 2024-01-01..2025-06-30, stage-1 passers only: pass if the 1x mean is positive with t >= 1.5.
3. **Holdout** 2025-07-01..2026-09-30, stage-2 passers only, computed in the same run (slices warmed up from 72 h
   before): **CONFIRMED** if the 1x mean is positive with NW t >= 2. Books that fail a stage are not computed on later
   windows.

## Reported (not decided on)
2x and 3x; per year; correlation of each book's daily net with the top_vs_crowd book (bin 0, short, same
construction, K 2.418) and the intercept of a regression on it (NW t), per window; gross and cost.

## Multiplicity
Trials = 6. Program trials before: 9,471,695.

## Expectations
top_vs_crowd's edge comes from top traders' positions disagreeing with the crowd; a guess is that the whale half
(positions vs accounts) carries more of it. Short side stronger than long, as in every flow lane. If a book confirms,
its forward test needs a live top_ls_count journal (the endpoint keeps about 28 days).
