# PREREG: settlehop_v1 (R353). The settlement-window hop: collect one venue's funding lump, hedged on an hourly venue

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R353
- **Method:** M267 (settlement-window cross-venue carry), queued since 2026-10-21 on the owner's fast-profit axis.
- **Owner (single writer):** the Claude session that froze it. R353 is claimed on issue #7 before the freeze.
- **Date registered (UTC):** 2026-10-27
- **Code:** `scripts/run_settlehop.py`, tested by `tests/test_settlehop.py` (17 tests on invented bars, funding and
  snapshots). The runner calls `verify()` on this file first, checks every input below, recomputes the Lighter cost
  bands from the listed snapshots, and checks every data file against `data_files.csv` as it loads it.
- **Gate:** 0. Every venue's hourly prices and funding here were read by R275, R277 and R288 for carry books held for
  days. No lane has read them around single settlements, with a two-hour hold.
- **Execution mode:** API on both venues: two orders an hour before the settlement and two an hour after. MEXC web
  is reported, not decided on.

## Why this lane
- **The owner's format:** a short-hold perp trade ("scalping futures to do quick money"), not a long hold.
- **The structure.** MEXC, Binance and Gate settle funding every 4 or 8 hours, in one lump. Lighter and dYdX settle every
  hour. Hold the receiving side on the lump venue (S) through one settlement, hedged by the other side on the hourly
  venue (H), for one hour on each side of it:
  - the hop receives all of S's lump and pays only two hours of H;
  - the coin's move cancels between the legs.
- **What can take the lump back** is S's price against H's around the settlement. If the S perp jumps by the payment
  once it is made (a no-arbitrage world), the hop keeps about a quarter of the lump, less four sides of cost: a loss.
  If prices ignore the payment, the hop keeps the lump less the cost. The test reads which world the data is in.
- **Speed:** extreme funding is frequent, and a hedged two-hour trade has little noise. A forward paper lane could
  confirm a real edge in months, where a daily book needs years.
- **Earlier evidence:**
  - R223 (single venue, unhedged): the price moved against the payment by more than it paid (−72.3 bp against
    +47.6 per event). That move includes the coin's own trend, which the hedge removes here.
  - R275, R277 and R288 (cross-venue carry, held for days): funding was 96-105% of the gross.

## What the author has seen
- **R223, R275, R277 and R288 in full,** including R288's Lighter sign and units check and R277's dYdX units check and
  crash prints.
- **A funding-only screen** (2026-10-27, before this file; rates only, no price read). It counted the settlements on S
  with an expected two-hour capture e = |r_prev − 2·h_prev| at or above a threshold (as defined below, before the
  TradFi exclusion and the identity check). The most frequent coins at 0.3% included KAITO, BERA, 0G, EDGE, AERGO,
  MOVE, B3, AXS and LA. Counts:

  | Pair | Settlements | e ≥ 0.1% | e ≥ 0.3% | e ≥ 0.5% | e ≥ 1% |
  |---|---|---|---|---|---|
  | MEXC + Lighter | 195,090 | 2,551 | 442 | 163 | 24 |
  | Binance + Lighter | 244,395 | 2,808 | 661 | 262 | 43 |
  | Gate + Lighter | 220,272 | 2,172 | 564 | 266 | 53 |
  | MEXC + dYdX | 455,670 | 10,601 | 1,872 | 884 | 205 |
  | Binance + dYdX | 716,144 | 10,519 | 2,449 | 1,201 | 316 |
  | Gate + dYdX | 685,380 | 8,773 | 2,206 | 1,146 | 365 |

- **Lighter's books:** the 22 hourly snapshots of every Lighter book (2026-10-21..27) by `scripts/record_lighter_book.py`.
  - Each coin's median $1k cost a side was computed; for example KAITO 37.2 bp, EDGE 30.5, BERA 12.5, 0G 12.1, BTC
    0.27, ETH 0.26, SOL 0.31.
  - The medians by 24 h volume band are the costs below.
  - Lighter's hourly quote volume is in USD: BTC's last 24 h to 2026-09-30 sum to $760M (the snapshots show $904M
    a day). KAITO's sum to $3,957 and BERA's to $62,535.
- **Plumbing** (`--plumbing`, after the TradFi exclusion; counts only, no return computed):

  | Pair | Coins | Eligible settlements | e ≥ 0.3% | e ≥ 0.5% | Both entry bars traded (e ≥ 0.3%) | Span |
  |---|---|---|---|---|---|---|
  | MEXC + Lighter | 108 | 190,948 | 435 | 161 | 435 | 2025-04-28..2026-09-30 |
  | Binance + Lighter | 114 | 215,865 | 437 | 170 | 437 | 2025-01-17..2026-09-30 |
  | Gate + Lighter | 116 | 199,587 | 443 | 218 | 426 | 2025-01-17..2026-09-30 |
  | MEXC + dYdX | 197 | 455,857 | 1,871 | 884 | 293 | 2025-04-28..2026-09-30 |
  | Binance + dYdX | 227 | 723,254 | 2,465 | 1,213 | 528 | 2023-10-27..2026-09-30 |
  | Gate + dYdX | 228 | 680,889 | 2,204 | 1,145 | 444 | 2023-10-27..2026-09-30 |

  Most of dYdX's large gaps fall in hours with no dYdX trade: its extreme hourly rates sit on idle markets.
- **Settlement rows in the hold** (row presence only, signals at e ≥ 0.3%): H lacks one of its two settlements for
  1, 2 and 2 signals on the MEXC, Binance and Gate + Lighter pairs, and for none on dYdX. S settles a second time
  inside the hold for 7-38 signals per pair.
- **Not computed in this lab:** any price change around a funding settlement on these venue pairs.

## Inputs (frozen)

```inputs
009145b050e50f4394499e318737fe4ef86a00ef21136fb327658d4072c86829  scripts/run_settlehop.py
c1a56b86965711c6dd8316582392267a5a7a664bcf0241564005b8935f77cc43  tests/test_settlehop.py
aa34e5e4586bdc5f2adf4bb744cf1a6c78f6e72627565e950763465a2e4c94b3  experiments/settlehop_v1/symbols.csv
399a84aeaa9b28221499bfc9ee53ad0cc178421b818ea2736276e71ad979c04e  experiments/settlehop_v1/data_files.csv
af7b1a0fbf99471720f765ece0b16734b88247aa84feb7f21137103500d983ea  experiments/venue_gap_v1/results/tradfi_symbols.json
2892c525929de66c687d92e26df683c58c50b56ad7b16be2639fdd6f325f2b02  scripts/lighter_table.py
ff6d80e23b337ee3c26ae44c718ba5893fb8e988fd23753631ddedd28b03e820  lab/venues.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508  lab/prereg.py
5fb2f74b0ffbfde94f9a73830b728e22387bce12475802fba01ac42fb7898c55  docs/provenance/mexc_hist.json
e496f80737a33ccffd3be5fb2d119310d91930021f7477338e124290950563c0  docs/provenance/gate_hist.json
ebedb4c8f8297c602c9e095764f4c7d728bed40d4cfe8297c5b350c2f80e3a8b  docs/provenance/dydx_hist.json
55e45182aade91c169b5a58b94ea9c831a64bc7753828fd276b7c94ed26e8de6  docs/provenance/klines_1h.json
84a3aadbf5ac0439b99209714c85ab0484b775f1258701835a64029c1ec3e4de  docs/provenance/fundingRate.json
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
- **Venues and files** (hourly bars: open time in ms, close, volume; funding: settlement time, signed rate per
  settlement, positive when longs pay):

  | Venue | Bars | Volume column | Funding | Settles |
  |---|---|---|---|---|
  | MEXC | `data/mexc_hist/klines_1h` | `vol` | `data/mexc_hist/funding` | 8 h (some 4 h, 1 h) |
  | Binance | `data/klines_1h` | `volume` | `data/fundingRate` | 8 h (some 4 h, 1 h) |
  | Gate | `data/gate_hist/open/candlesticks_1h` | `vol_contracts` | `data/gate_hist/open/funding_applies` | 8 h (some 4 h) |
  | Lighter | `data/lighter_hist/open/candles_1h` | `volume` | `data/lighter_hist/open/funding` | 1 h |
  | dYdX | `data/dydx_hist/open/candles_1h` | `volume` | `data/dydx_hist/open/funding` | 1 h |

- **Rows read:** [2021-01-01, 2026-10-01), filtered by the parquet reader. 2020 and the post-archive rows are never
  loaded. The `open/` folders hold only coins with a Binance perp, so the reserved Gate, KuCoin and dYdX long tails
  are never read. The symbol table has only Binance perps, so the reserved MEXC-only coins are never read either.
- **Coins:** `symbols.csv`, built by `--symbols` from `lab.venues` (MEXC, Gate, dYdX keys) and
  `scripts/lighter_table.py` (Lighter keys). Binance perps that Lighter or dYdX lists, without R216's 224 TradFi perps
  (`experiments/venue_gap_v1/results/tradfi_symbols.json`: stocks, ETFs, metals, pre-IPO). 261 rows.
- **Data identity:** `data_files.csv` lists the sha256 of each of the 2,196 files the run reads; a file that changed
  or is missing stops the run.
- **Settlement stamps** are rounded to the nearest hour (Binance writes 16:00:00.002, dYdX 18:00:01).
- **A bar is traded** when its close is finite and positive and its volume finite and positive.

## The rule
For each pair (S, H) and each coin with a key on both:
- **Settlements:** every S settlement T that follows the previous S settlement by 4 to 24 hours (so the lump is at
  least 4 hours' worth).
- **H must be settling:** H's last settlement at or before the entry time T − 1 h is at most 2 hours old.
- **Signal, all known at the entry:**
  - r_prev = S's previous settled rate;
  - h_prev = H's last hourly rate at or before T − 1 h;
  - e_signed = r_prev − 2·h_prev, the funding the hop expects to net over two hours.
  - d = sign(e_signed): +1 means short S and long H; −1 means long S and short H.
  - e = |e_signed|.
- **Eligible:** T − 1 h is at least 31 days after 2021-01-01, and T + 1 h is before 2026-10-01.
- **Entry:** at the close of the bar ending T − 1 h, on both venues. Both bars must be traded, or there is no hop.
- **Exit:** on each venue, at the last traded close at or before the close of the bar ending T + 1 h, and not before
  the entry bar. An exit before the bar ending T + 1 h is flagged stale.
- **Funding:** each venue's settlements in (T − 1 h, T + 1 h]: S's settlement at T, and H's at T and T + 1 h. A leg
  whose exit close is stale is still held, and charged funding, to T + 1 h.
  - H's file must hold both of its settlements in the hold (T and T + 1 h), or there is no hop.
  - If S moved to hourly settlement after T, its settlement at T + 1 h is charged too.
- **Same coin (point in time):** over the 30 daily closes (00:00 UTC) up to the last one at or before the entry, the
  correlation of S's and H's daily returns must reach 0.9 on at least 20 paired days (R275's rule).
- **Taken:** e ≥ θ and the same-coin check passed; at most 5 hops per settlement time, largest e first (then the coin's
  name).
- **Per hop:** net = d·(ret_H − ret_S) + d·(F_S − F_H) − 2·(c_S + c_H).
- **θ:** 0.3% or 0.5%.

## Costs (a side, 1x)
- **MEXC and Binance API:** 8.5 bp (the lab's API level: about 6-8 bp of fee and the book).
- **Gate and dYdX:** 7 bp (R275's and R277's leg).
- **Lighter (fee 0, Standard API):** the median $1k cost a side over the 22 snapshots for coins in the band of the
  hop's trailing 24 h Lighter volume (the 24 bars opening in [T − 25 h, T − 2 h]):

  | 24 h volume | under $10k | $10k-100k | $100k-1M | $1M-10M | $10M-100M | $100M and up |
  |---|---|---|---|---|---|---|
  | bp a side | 26.67 | 7.27 | 4.17 | 1.09 | 0.51 | 0.26 |

- **2x and 3x:** every cost doubled and tripled.
- **Reported only:** MEXC web at 3 bp a side for the MEXC pairs.

## Books and trials
- **Pairs:** MEXC + Lighter, Binance + Lighter, Gate + Lighter, MEXC + dYdX, Binance + dYdX, Gate + dYdX.
- **θ:** 0.3%, 0.5%. **12 books, 12 trials.**
- **The primary book is MEXC + Lighter at θ 0.5%.** It was fixed here before any return:
  - MEXC is the owner's venue and Lighter is the zero-fee one, as in R294's forward lane.
  - At 0.5% the expected capture is above a typical hop's 1x cost (about 25-35 bp) before any price effect.
- **Book:** capital in 5 equal slots. A hop's net counts a fifth on the UTC day of its settlement T.
  - The calendar runs from the first to the last eligible settlement of the pair (at any e).
  - Days without a hop are 0.
- **Halves:** the calendar split into two equal runs of days.

## Decision (the primary book only)
**PASS** if all four hold:
1. the Newey-West t (lag 5, `lab.stats.newey_west_t`) of the 1x daily net is ≥ 2.0;
2. the 2x daily mean is > 0;
3. the 1x daily mean is > 0 in both halves;
4. without the coin with the largest summed 1x net (all its hops removed), the 1x daily mean is > 0.

**NULL** otherwise. A PASS is recorded as PARTIAL (gate 0).

**What each verdict earns:**
- **PASS:** a forward paper lane with a new id, frozen before its first day. It runs on live MEXC and Lighter funding
  and prices from the recorders, where the live trader sees the current predicted rate, not only the last settled
  one. The reserved MEXC-only and Gate long-tail coins on Lighter become a batch-2 candidate. No money moves: that
  needs paper to show a net gain, then `lab.gate.go_real()` and the owner.
- **NULL:** M267 is TESTED. If the price around T takes the lump back, the settlement-window form of cross-venue carry
  is closed, and carry stays a days-long hold (R294).

**Power (approximate, written before any return):**
- The hops' noise is unknown before the run. Two hours of a squeezing small cap across two venues might give about
  150 bp a hop.
- With about 150 primary hops, a t of 2 then needs about +25 bp a hop net, and 80% power about +35 bp.
- **If prices ignore the payment:** the net is about the mean e less the cost, around +40 bp or more at θ 0.5%, which
  the test detects.
- **If S jumps by the payment:** the net is about −25 to −35 bp, which the test shows as clearly negative.
- **A half-way world** (about +10 bp) would read as NULL.

## Reported (not decided on)
- **Every book:**
  - hops, coins and hops a day;
  - mean e, and the funding and price parts per hop;
  - the price part before T (entry to the close at T) and after it;
  - gross, cost, and net at 1x/2x/3x per hop, the hit rate, and the 1%-trimmed 1x net;
  - daily 1x/2x/3x means with their NW t;
  - halves, the best coin and the 1x daily mean without it;
  - stale exits;
  - the hop closed at T (an optimistic bound: no real exit gets the close at T after the payment);
  - MEXC web costs on the MEXC pairs.
- **Family:** how many of the 12 books reach a 1x NW t of 2.64 (Bonferroni, one-sided 5% over 12) and of 2.0.
- **After the run, from `hops.csv.gz`:** by calendar year, by S interval (4 h or 8 h), by direction, and the largest
  hops.
- **Read against** `registry.program_trials()`: 9,479,069 on this branch before this lane, 9,479,081 after it (or
  9,479,098 counting #56's R338-R346).

## Outputs
`experiments/settlehop_v1/results/`:
- `summary.json`: the verdict, the checks, the family counts, the costs and the input hashes;
- `books.csv`: every book's statistics;
- `hops.csv.gz`: every taken hop of every book;
- `daily.csv.gz`: each book's daily net at 1x/2x/3x.

FINDINGS.md is written after the run, with 1x/2x/3x costs.

## Evidence lineage and admission
- **Method:** M267.
- **Parents:**
  - R223 (single-venue settlement capture, NULL);
  - R275, R277 and R288 (cross-venue carry and its data);
  - R315 and R317, which read the venues' funding documents (MEXC's batch inclusion can reach 15 s after the
    nominal time; the hop holds through the whole settlement hour).
- **Decision group:** this lane alone decides M267's settlement-window form. It does not change R294's days-long
  carry lane.
- **Samples:**
  - seen: all the rows here (gate 0);
  - fresh: the forward recorders after a future freeze, and the reserved MEXC-only and Gate/dYdX long-tail coins.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa…a926`.

## Known limits (written before the result)
- **Hourly bars.**
  - A real exit comes seconds after T. Any jump right after the payment is inside the T → T + 1 h move charged
    here, together with one more hour of basis noise and one more H settlement.
  - The close at T, before the payment, is reported only as a bound.
- **The signal uses the last settled S rate,** not the live predicted rate a trader would see. It is conservative
  for the direction, and it may miss rates that move fast.
- **Costs:**
  - flat API levels on MEXC, Binance, Gate and dYdX;
  - Lighter's costs come from October 2026 books, applied to 2025-26 by volume band. A squeezing coin's book may be
    thinner than its band says.
  - 2x and 3x are reported.
- **Execution:**
  - Two venues are entered at the same hourly close; legging risk is not modelled.
  - Funding is charged on entry notional, not mark notional.
  - Margin and liquidation are not modelled: the hold is two hours and both legs are hedged.
- **Sign and units:** Lighter's funding sign is an interpretation that R288 checked against the other venues; R277
  checked dYdX's units.
- **dYdX:** its extreme rates sit mostly on idle hours (plumbing), so its books hold few hops and its prices may
  carry crash prints (R277).
- **Same coin:** a 30-day correlation of 0.9 can still pass a renamed or redenominated contract that later diverges.
