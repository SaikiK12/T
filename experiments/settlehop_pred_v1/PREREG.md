# PREREG: settlehop_pred_v1 (R354). The settlement-window hop on a point-in-time predicted rate

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R354
- **Method:** M267 (settlement-window cross-venue carry), its predicted-rate form. R353 tested its last-settled-rate
  form (NULL).
- **Owner (single writer):** the Claude session that froze it. R354 is claimed on issue #7 before the freeze.
- **Date registered (UTC):** 2026-10-27
- **Code:** `scripts/run_settlehop_pred.py`, tested by `tests/test_settlehop_pred.py` (7 tests on invented premium,
  funding and files).
  - It imports R353's frozen runner `scripts/run_settlehop.py` unchanged for bars, funding, the hop, the identity
    check, costs, the book and the decision. R353's 17 tests cover that code.
  - The runner calls `verify()` on this file first. It checks every input below, recomputes the Lighter cost bands from
    the listed snapshots, and checks every data file against `data_files.csv` as it loads it.
- **Gate:** 0. R353 read the prices and funding around these venues' extreme settlements; many of this lane's hops will
  be R353's hops. The premium index has not been read for funding by any lane.
- **Execution mode:** API on both venues: two orders an hour before the settlement and two an hour after. MEXC web
  is reported, not decided on.

## Why this lane
- **The owner's format:** a short-hold perp trade, not a long hold.
- **R353's finding** (gate 0, NULL):
  - **The hedge works.** Across venues, the S perp was not repriced by its funding lump in the two hours around it.
    The price part gave back 0-26% of the lump S paid.
  - **The signal failed.** S's last settled rate forecast only about a third of the next lump. When the hourly venue
    moved first, the next lump went against the hop.
- **What a trader sees.** An hour before a settlement, every venue displays the rate it will settle. No history file
  holds that displayed rate.
- **Binance's formula** (its funding page, fetched 2026-10-27,
  `https://www.binance.com/en/support/faq/introduction-to-binance-futures-funding-rates-360033525031`):

      Funding Rate (F) = [Average Premium Index (P) + clamp(interest rate - Premium Index (P), 0.05%, -0.05%)] / (8 / N)

  - The interest rate is 0.01% per 8 hours, and N is the funding interval in hours.
  - P averages the interval's premium index samples, taken every 5 seconds and weighted 1, 2, ..., n so that later
    samples count more.
  - The lab holds Binance's hourly premium index bars for 896 perps (`data/premiumIndexKlines_1h`). So the rate known
    an hour before T can be rebuilt from bars that had closed by then.

## What the author has seen
- **R353 in full,** including its after-run tables: price slopes, lump ratios, direction, interval, year and the
  crash day.
- **Binance's funding page,** as quoted above. Its cap is ±2% for most USDⓈ-M perps and 0.75 × the maintenance
  margin ratio for some majors.
- **One premium file** (BTCUSDT, the first week of 2025), to check hourly stamps and units: fractions, with a median
  |close| of 0.035%.
- **Plumbing** (`--plumbing`; counts only, with no return and no rate settled after the entry):

  | Pair | Coins | Eligible settlements with a prediction | e ≥ 0.3% | e ≥ 0.5% | Entry bars traded (e ≥ 0.3%) | Span |
  |---|---|---|---|---|---|---|
  | Binance + Lighter | 114 | 214,446 | 352 | 135 | 352 | 2025-01-17..2026-09-30 |
  | MEXC + Lighter | 107 | 189,269 | 332 | 126 | 332 | 2025-04-28..2026-09-30 |
  | Gate + Lighter | 114 | 197,355 | 331 | 157 | 329 | 2025-01-17..2026-09-30 |

- **Not computed:** the predicted rate against any settled rate, and any return of a hop chosen by it.

## Inputs (frozen)

```inputs
64e87553239835ebbab85638e2503062fabbbeb67f996cca8ada80d5b02ba9ce  scripts/run_settlehop_pred.py
009145b050e50f4394499e318737fe4ef86a00ef21136fb327658d4072c86829  scripts/run_settlehop.py
7783c8e57a94bdfd9510888246d4bf79c9ee1b8dbc7c5d8b1ae785cb8e2253fe  tests/test_settlehop_pred.py
c1a56b86965711c6dd8316582392267a5a7a664bcf0241564005b8935f77cc43  tests/test_settlehop.py
aa34e5e4586bdc5f2adf4bb744cf1a6c78f6e72627565e950763465a2e4c94b3  experiments/settlehop_v1/symbols.csv
79d7d5dd081bd08272d2616d6b35c66a7402f018fb2aa96d9d60f7b286e67a00  experiments/settlehop_pred_v1/data_files.csv
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508  lab/prereg.py
55e45182aade91c169b5a58b94ea9c831a64bc7753828fd276b7c94ed26e8de6  docs/provenance/klines_1h.json
84a3aadbf5ac0439b99209714c85ab0484b775f1258701835a64029c1ec3e4de  docs/provenance/fundingRate.json
5fb2f74b0ffbfde94f9a73830b728e22387bce12475802fba01ac42fb7898c55  docs/provenance/mexc_hist.json
e496f80737a33ccffd3be5fb2d119310d91930021f7477338e124290950563c0  docs/provenance/gate_hist.json
b393a5e3ffa81a1877ce59222cef5b9909e9e1db9f972552689e7922abeb3838  docs/provenance/premiumIndexKlines_1h.json
e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926  docs/GATES.md
018b8828832002e964e233b31ccd8ae9272af87c47171fc3e43732722b952767  data/recorders/lighter_book/2026-10-21/16.parquet
1284f3672e174920b4f6af25dc1095d5bea0cbd39efe7ec5b6aae5111487a10e  data/recorders/lighter_book/2026-10-21/17.parquet
ba4a0c875759cd9d5db59594d85969722c4ac857b06f5b0c20b446a0b014a44b  data/recorders/lighter_book/2026-10-21/20.parquet
6514c2eb6a4ecc064b14fe228b1d83ee01a60760e37038f6c1b4d1c377a03423  data/recorders/lighter_book/2026-10-21/21.parquet
576842018e81c3c93682c0432acd4cc88777dfe2ea2391c5ba9f641f5f847a85  data/recorders/lighter_book/2026-10-21/22.parquet
eddcd4702e7cf637315c501b7d37c38c998608cdfaa96ff1aab72df702a135c3  data/recorders/lighter_book/2026-10-22/01.parquet
083d9cd01d429c7c7c31ae7c0efe46709979ebf56af7b01f7ac9b98a8b46e662  data/recorders/lighter_book/2026-10-22/02.parquet
20f4a1f4ff48915b44628342c84a305bb330140f5c86360791413a136d55f42e  data/recorders/lighter_book/2026-10-22/03.parquet
9f96bde04596e8651160a2864bb503775f4e8e6d3cc14e47af883af7a7a26015  data/recorders/lighter_book/2026-10-22/04.parquet
268e67eadcb1ff0142a9f8193032aa4b252831d88cd87bd53a8f6dd82f5478ad  data/recorders/lighter_book/2026-10-22/06.parquet
836ba014871b3c96cd8de513b736656b501183b278d05ab3d4d1d9a666ad2799  data/recorders/lighter_book/2026-10-22/07.parquet
efa5ac591926382a48b5408c3808624de0cf18a1a7449e8f7c8cd588cb44d2e3  data/recorders/lighter_book/2026-10-22/08.parquet
2a083da836c53d81bf1ba49d8bf5d0560ac455b57719afa13b201d247e62ebd0  data/recorders/lighter_book/2026-10-22/09.parquet
5b62a82119e4c0d0f673c28caad36d6c1051ab187dec7b2b29e02049f64509af  data/recorders/lighter_book/2026-10-22/12.parquet
f3e234bd8a0a60e16805c2c53871df45320a0ac2342814839c8dbef423331377  data/recorders/lighter_book/2026-10-22/16.parquet
eee352fd1121da860e79813e818a3525a57071691c0420e77da81bf71ba61cc3  data/recorders/lighter_book/2026-10-22/17.parquet
c613bfc07d7538bf9c84ddfd80d1cc08628aa1ba64f23eaa65844efdf1460f7e  data/recorders/lighter_book/2026-10-26/15.parquet
902bef3fbe372f28ebae617632a49d5594fdc886acf3963498b301579ba4fc1c  data/recorders/lighter_book/2026-10-26/16.parquet
c0e66e6682af7c153ee16f6b2ef9902e0cfbe34bdc4e6627af8b9cc99b2c2951  data/recorders/lighter_book/2026-10-26/17.parquet
0730b033bf2fcbaa82c31662f26cc1b72aae2387f58f4aa78e3e06128f454512  data/recorders/lighter_book/2026-10-26/21.parquet
7651c354d606a712327a306e66d2a41e236a2177bad2b6287fc518c0a901034e  data/recorders/lighter_book/2026-10-27/14.parquet
39918004ee5dbef235302a3bea8a7cd293bed137483d2f578563b662a74e7b58  data/recorders/lighter_book/2026-10-27/15.parquet
```

## Data
- **As R353,** for MEXC, Binance, Gate and Lighter: the same folders, columns and `symbols.csv`, 261 rows without
  TradFi.
- **Binance's hourly premium index bars:** `data/premiumIndexKlines_1h/<Binance perp>.parquet`, columns t (open time,
  ms), open, high, low and close.
- **Rows read:** [2021-01-01, 2026-10-01) in every file, filtered by the parquet reader. The premium reader starts at
  2021-01-01, so 2020 (reserved) is never loaded. Only Binance perps and the `open/` folders are read, so the reserved
  MEXC-only coins and long tails are never read.
- **Data identity:** `data_files.csv` lists the sha256 of each of the 1,071 files the run reads (121 of them premium
  files). A changed or missing file stops the run.

## The rule
For each pair (S, H) with H = Lighter, and each coin with a key on both:
- **Settlements:** every S settlement T whose interval, the gap from the previous S settlement, is 4 or 8 hours (the
  intervals the venues use; other gaps are missing rows or schedule changes).
- **H must be settling,** as in R353: H's last settlement at or before T − 1 h is at most 2 hours old.
- **The predicted S rate F̂,** known at T − 1 h, from Binance's premium bars of the same coin:
  - **Hours:** the interval's m hours (m = 4 or 8) open at T − m h, ..., T − 1 h. Hour h weighs 2h − 1, the linear
    sample weights summed over the hour.
  - **Hours 1..m−1** have closed by T − 1 h. Each counts at the mean of its open, high, low and close.
  - **Hour m** has not closed. It counts at the close of hour m − 1, the last premium published.
  - **Missing bars:** without the bar opening at T − 2 h there is no prediction. Any other missing hour is left out and
    the weights renormalized.
  - **The rate:** P̂ is the weighted mean, and F̂ = [P̂ + clamp(0.01% − P̂, −0.05%, +0.05%)] × m / 8. No cap is
    applied: a capped settlement only lowers the lump paid.
  - **On MEXC and Gate,** whose displayed rates are in no file, Binance's premium for the same coin over S's own
    interval stands in for S's own premium.
- **Signal:** e_signed = F̂ − 2·h_prev, with h_prev as in R353 (H's last hourly rate at or before T − 1 h).
  - d = sign(e_signed): +1 means short S and long H.
  - e = |e_signed|.
- **Everything else is R353's frozen code:**
  - eligibility;
  - entry at the close of the bar ending T − 1 h, with both entry bars traded;
  - exit at the last traded close at or before the bar ending T + 1 h;
  - funding over (T − 1 h, T + 1 h], with both H settlements present;
  - the 30-day identity check;
  - at most 5 hops per settlement, largest e first;
  - net = d·(ret_H − ret_S) + d·(F_S − F_H) − 2·(c_S + c_H).
- **θ:** 0.3% or 0.5%.

## Costs (a side, 1x), as R353
- **MEXC and Binance API:** 8.5 bp. **Gate:** 7 bp.
- **Lighter (fee 0):** by the hop's trailing 24 h Lighter volume band, as R353 (26.67 / 7.27 / 4.17 / 1.09 / 0.51 /
  0.26 bp), checked against the same 22 snapshots.
- **2x and 3x:** every cost doubled and tripled. **Reported only:** MEXC web at 3 bp a side.

## Books and trials
- **Pairs:** Binance + Lighter, MEXC + Lighter, Gate + Lighter.
  - dYdX is left out: R353's identity check kept only 1-15 hops in each dYdX book.
- **θ:** 0.3%, 0.5%. **6 books, 6 trials.**
- **The primary book is Binance + Lighter at θ 0.5%,** fixed here before any return. On Binance the prediction uses
  the venue's own formula and premium; on MEXC and Gate it is a proxy.
- **Book:** R353's: 5 equal slots, a hop's net counted on the UTC day of T, the calendar from the first to the last
  eligible settlement with a prediction, idle days 0. Halves are two equal runs of days.

## Decision (the primary book only), as R353
**PASS** if all four hold:
1. the Newey-West t (lag 5) of the 1x daily net is ≥ 2.0;
2. the 2x daily mean is > 0;
3. the 1x daily mean is > 0 in both halves;
4. without the coin with the largest summed 1x net (all its hops removed), the 1x daily mean is > 0.

**NULL** otherwise. A PASS is recorded as PARTIAL (gate 0).

**What each verdict earns:**
- **PASS:**
  - A forward paper lane with a new id, frozen before its first day. It runs on MEXC + Lighter with MEXC's displayed
    rate from the ticker recorder: the owner's venue, at no loss of point-in-time honesty.
  - The reserved MEXC-only and Gate long-tail coins become a batch-2 candidate.
  - No money moves: that needs paper to show a net gain, then `lab.gate.go_real()` and the owner.
- **NULL:** M267 is closed on hourly bars in both forms. Carry stays a days-long hold (R294).

**Power (approximate, written before any return):**
- R353's Binance + Lighter θ 0.5% hops had a standard deviation of 76 bp. With about 110-135 primary hops, a t of 2
  needs about +14 bp a hop net, and 80% power about +20.
- **If the prediction captures most of the lump** (60-75 bp at θ 0.5%), with R353's price part (about −11 bp), two
  hours of H (about −13) and the cost (about 20), the net is about +15 to +30 bp a hop. That is near the bar.
- **If it captures R353's third,** the book loses as R353's did.

## Reported (not decided on)
- **Every book:** all of R353's statistics (hops, coins, mean e, funding and price parts, price before and after T,
  gross, cost, net 1x/2x/3x, hit, trimmed net, daily means and t, halves, best coin, stale exits, the hop closed at T,
  MEXC web).
  - Plus the forecast S lump signed for the hop (F̂·d) against the lump S paid.
- **Family:** how many of the 6 books reach a 1x NW t of 2.39 (Bonferroni, one-sided 5% over 6) and of 2.0.
- **After the run, from `hops.csv.gz`:** the forecast against the paid lump, by interval, by direction, by year, the
  hops shared with R353, and the largest hops.
- **Read against** `registry.program_trials()`: 9,479,081 on this branch before this lane and 9,479,087 after it (or
  9,479,104 counting #56's R338-R346).

## Outputs
`experiments/settlehop_pred_v1/results/`:
- `summary.json`: the verdict, the checks, the family counts, the costs and the input hashes;
- `books.csv`: every book's statistics;
- `hops.csv.gz`: every taken hop of every book;
- `daily.csv.gz`: each book's daily net at 1x/2x/3x.

FINDINGS.md is written after the run, with 1x/2x/3x costs.

## Evidence lineage and admission
- **Method:** M267.
- **Parents:**
  - R353 (the same hop on the last settled rate; NULL, the signal failed and the hedge held);
  - R223 (single-venue settlement capture, NULL);
  - R275, R277 and R288 (cross-venue carry and its data).
- **Decision group:** this lane decides M267's predicted-rate form on hourly bars.
- **Samples:**
  - seen: every price and funding row here (gate 0);
  - fresh: the forward recorders after a future freeze, and the reserved MEXC-only and Gate long-tail coins.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa…a926`.

## Known limits (written before the result)
- **Hourly bars:** as R353. The exit after T carries one more hour of basis noise. The hop closed at T is reported
  only as a bound.
- **The predicted rate is rebuilt, not recorded:**
  - an hour's mean is taken as the mean of its open, high, low and close, not the 720 samples;
  - the last hour is assumed to stay at the last close;
  - the interval is taken from the gap between settlements;
  - Binance's cap and any special clamp are not applied.
- **MEXC and Gate** settle from their own premiums. Binance's is a proxy, so their books test the transfer too.
- **Costs, execution, margin, sign and units:** as R353 (flat API levels, October 2026 Lighter books by band, both legs
  at the same hourly close, no legging, margin or liquidation model).
- **Same coin:** as R353, a 30-day correlation of 0.9 can still pass a contract that later diverges.
