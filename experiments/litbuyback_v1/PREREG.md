# PREREG: litbuyback_v1 (R486). Does Lighter's LIT buyback share predict LIT's next week?

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R486
- **Owner (single writer):** Kiro coder agent, session on `claude/websearch-organization-and-maintenance` (2026-11-13)
- **Date registered (UTC):** 2026-11-13

Method M537 (queued UNTESTED on 2026-11-13 by the HLP/LLP/LIT intake, `research/intake/hlp_llp_lit_20261113.md`).
Lighter spends its maker and taker fee revenue on a daily 24-hour TWAP that buys LIT (SRC1113-001). This file is
frozen before any statistic that relates the buyback to a later LIT price or return.

## Question
Is the day-t buyback in USDC, as a share of LIT's own traded value that day, rank-correlated with LIT's return over
the next 7 days on Lighter's LIT perp beyond a circular-shift null, and does a weekly long-or-flat book on it beat
holding LIT perp long after costs and funding?

**The prior expects NULL:** the flow is public and announced, it runs at about 0.3% to 0.6% of LIT's daily
turnover, and the sample is about 300 days of one token.

## What the author has seen
- `research/intake/hlp_llp_lit_20261113.md` (frozen R484 input): the monthly buyback USDC against maker plus taker
  fees (within 1.8% from February to September, 114% in January, 137% in October); the buyback at about $2.1m to
  $4.1m a month, roughly 0.3% to 0.6% of LIT's daily turnover (median daily quote volume perp $16.0m, spot $5.4m);
  the eight largest buyback days (2026-10-29, 01-15, 01-12, 01-11, 10-28, 01-05, 02-05, 01-21), noted there as
  falling at or near LIT's drawdown troughs, a same-period observation that was not tested; LIT's price path
  (-73.97% from 2026-01-07 to 03-30, then +331% from the close low to 11-10, and -48.99% from 09-23 to 10-29),
  monthly LIT returns and monthly funding sums.
- R447 (`experiments/llpstake_v1/`): LIT perp and spot candles and funding to 2026-11-10; R484 (`experiments/
  llphouse_v1/`): LIT reported as a non-deciding asset after LLP's extreme days.
- Plumbing only, before this freeze: the runner's loaders read lit/ at the pinned commit and printed counts and date
  ranges (perp 313 daily bars 2026-01-02..2026-11-10, spot 314 from 2026-01-01, funding 7,485 hours on 313 days, 10
  days with fewer than 24 hours, 2026-01-02 has 6; buyback 316 days 2025-12-30..2026-11-10, no gap). The unit tests
  use synthetic series and read the real buyback body's first and last day only.
- **No correlation, return, lag statistic or book result relating the buyback to LIT's price has been computed.**

## Universe
One asset: LIT, on Lighter's LIT perp (market id 120) and LIT/USDC spot (market id 2049) per `lit/meta.json`.
Single venue, the venue's own token; no cross-section, so no survivorship question.

## Data (frozen inputs)
- **Buyback:** Lighter `exchangeMetrics?period=all&kind=buyback_usdc` (SRC1113-006), body
  `research/intake/hlp_llp_lit_20261113/em_buyback_usdc_all.json`. Daily points stamped 00:00 UTC; read as the
  buyback of the UTC day that starts at the stamp, in USDC (units UNVERIFIED in Lighter's docs, as the intake says).
  `em_buyback_all.json` (LIT bought) and `em_volume_all.json` are hashed below but not used: exchangeMetrics volume is
  exchange-wide (about $2.3bn on 2026-11-12, against LIT perp quote volume in the tens of millions), so it is not
  LIT's traded value.
- **LIT:** the data branch `claude/okx-xperp-data` (scripts/record_lit_hedge.py) at the pinned commit below, read with
  `git ls-tree` and `git cat-file` (the main worktree is never switched):
  `lit/perp_candles_1d/<date>.csv` and `lit/spot_candles_1d/<date>.csv` (ts = 00:00 UTC open of the 1D bar, close,
  quote_volume) and `lit/perp_funding/<date>.csv` (hourly; `rate` = +rate_pct/100 when direction is long, i.e. +
  when longs pay, the convention R447's `scripts/run_llpstake.py` uses).
- **Gate-0 data commit:** `0364bbc63ec3bc4d7cc135ff4b060cabf8127062` (origin/claude/okx-xperp-data on 2026-11-13,
  committed 2026-11-13T03:42:09Z). Trees the runner checks: `lit` 1a377a6aaa39e065aa3a4ecac69329a3fabd4f65,
  `lit/perp_candles_1d` 6363224ed40d96438abff4b6f151375a7a2d4da2, `lit/spot_candles_1d`
  d57125a278544aa6e919db70a57db84bb9a28323, `lit/perp_funding` 52362e744c3229230305808d1708db27757b6234.
- **Sample end 2026-11-10.** LIT prices after that day sit inside R447's forward window (from 2026-11-11) and are not
  read: the runner reads only files whose date name is on or before 2026-11-10 and refuses any row stamped at or
  after 2026-11-11 00:00 UTC; buyback points after 2026-11-10 are dropped.
- The runner verifies this file (`prereg.verify`), every line of the inputs block, the pinned commit's tree hashes,
  then reads the data.

```inputs
4d8cd583e9044dfe4135962d5ff8aaaab65802d2fe3a53c059ae08be2acf0560 research/intake/hlp_llp_lit_20261113/em_buyback_all.json
ae74d59262ab5c87d486eb562267adce22fbc866bf2b2ca9cdce66c884400c48 research/intake/hlp_llp_lit_20261113/em_buyback_usdc_all.json
e4c43d573c86bbd3a91c055193ec55a19458e0554c08a3f0180f3bf03ecbc407 research/intake/hlp_llp_lit_20261113/em_volume_all.json
fa4a7f275add053f5189b29d2370a7a4fe2518bce773bbdc6fb0fe89cd800c5f scripts/run_litbuyback.py
```

## Feature lineage and point-in-time availability

| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| s_t = buyback_usdc_t / (perp qv_t + spot qv_t) | buyback_usdc data; candle quote_volume | Lighter exchangeMetrics; Lighter LIT perp and LIT/USDC spot; USDC | UTC day t, 00:00 to 24:00 | the day's point is complete at 24:00 UTC; body fetched 2026-11-13 08:23 UTC | At the close of t (the entry), only just: see caveat | latest-vintage (one body fetched 2026-11-13) | NaN if any part is missing; no fill |
| sbar_t | s over t-6..t | as above | 7 days ending t | computed | yes, same as s_t | latest-vintage | NaN unless all 7 present |
| med_t | sbar over t-60..t-1 | as above | 60 days before t | computed | yes | latest-vintage | NaN unless all 60 present; block skipped |
| r_t (7d) | perp close | Lighter LIT perp, USDC | close(t+7)/close(t) - 1, 1D bar closes | recorded by scripts/record_lit_hedge.py | target, not a decision input | forward-captured recordings | NaN if either close is missing |
| funding paid | perp_funding rate | Lighter LIT perp, fraction of notional per hour | hours stamped on days t+1..t+7 | recorded hourly | cost of the hold | forward-captured | a missing hour counts 0 (reported as funding_hours) |

**Caveat (timing):** the entry is at the close of day t, the same moment day t's buyback total is complete. The
intake calls the metric "public with one day's lag"; if the day's point is published later than 24:00 UTC, the book
is optimistic by that lag. The buyback body is one fetch on 2026-11-13: a later revision of a past day is not
visible.

## Rule
- **Signal:** s_t as above, with denominator LIT perp quote volume plus LIT/USDC spot quote volume on day t (both are
  on lit/).
- **Target:** r_{t+1..t+7} = LIT perp close(t+7) / close(t) - 1.
- **Days:** t from 2026-01-02 (the later of the first buyback day 2025-12-30 and the first perp candle 2026-01-02)
  to 2026-11-03, so t+7 <= 2026-11-10; every t with both s_t and r finite.
- **Primary statistic (trial 1):** Spearman rank correlation rho(s_t, r_{t+1..t+7}) (average ranks for ties).
- **Null:** circular shift of s against r over the paired series of n days: s rolled by k for every k in
  [14, n - 14], rho_k each. p_two = share of |rho_k| >= |rho|; p_one = share of rho_k >= rho.
- **Book (trial 2):** non-overlapping 7-day blocks starting at b = 2026-01-02 + 7j, b <= 2026-11-03. At b, with
  sbar_b (mean of s over b-6..b) and med_b (median of sbar over b-60..b-1), long the LIT perp from the close of b to
  the close of b+7 if sbar_b > med_b, else flat (0 return, no cost). Blocks without med_b (fewer than 60 prior sbar
  values) or without both closes are skipped.
- **Net of a long block:** close(b+7)/close(b) - 1 minus the funding paid by the long (sum of hourly `rate` over
  hours stamped on UTC days b+1..b+7, + when longs pay) minus the round trip: 20 bp at 1x, 40 bp at 2x, 60 bp at 3x
  (10 bp a leg a side, as R447 prices the LIT perp).
- **Benchmark (reported, and the comparison in G3):** always long over the same blocks, same funding and costs.

## Gates
- **G1:** rho > 0 and p_one < 0.05.
- **G2:** book mean net per block at 2x > 0 with simple t (mean / (sd / sqrt(blocks)), flat blocks counted as 0)
  >= 2.
- **G3:** book mean net per block at 1x > the always-long benchmark's mean net per block at 1x.
- **Verdict:** **SIGNAL (gate 0)** if G1, G2 and G3 all pass, else **NULL**. The rounds registry has no SIGNAL
  verdict: SIGNAL is recorded as PARTIAL (gate 0, in-sample, not confirmed), NULL as NULL.

## Reported, deciding nothing (not trials)
- rho of s_t with the 1-day target close(t+1)/close(t) - 1 (t to 2026-11-09) and its circular-shift p.
- The change signal s_t - s_{t-7} against the 7-day target, with its circular-shift p.
- Book and benchmark at 1x/2x/3x, block counts (total, long), book gross, minimum funding hours in a block, the
  share's median and 10th/90th percentiles, n of the correlation.

## Multiplicity
**Trials: 2** (the correlation and the book), as R484 counted its two deciding books and no reported variant.
Program trials before this round: 9,785,289 (`registry.program_trials()`); 9,785,291 with it. A gate-0 in-sample
read of one token over about 300 days; any p near 0.05 is weak against the program total.

## What a result earns
- **NULL:** M537 is marked tested. Another denominator, horizon or threshold is a new lane with a new id.
- **SIGNAL:** a forward paper lane (new PREREG, new id) on days after 2026-11-10 read from the recorder, with the
  buyback fetched daily so its publication time is known. Not a go-real signal. The insider unlock from 2026-12-29
  (about 11 to 23 times the buyback) changes the flow the signal sits in.

## Stop rules
One run of `scripts/run_litbuyback.py`. No new features, horizons, denominators, thresholds or samples after seeing
any result. A crash fixed after the freeze is documented in FINDINGS with the changed sha.
