# PREREG: tapelag_lighter_v1 (R347). Zero-fee scalps on Lighter, traded toward Binance's quote

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R347
- **Method:** M425, a zero-fee venue's quote lag. Trade Lighter toward Binance when their basis moves away from its
  recent level by more than a round trip's cost. It is the reachable form of latency arbitrage in
  `docs/VENUE_STRUCTURE.md` item 5, related to M264 (order-flow scalps on recorded top-of-book).
- **Owner (single writer):** the Claude session that froze it. R347 and M425 were claimed on issue #7 (comment
  6444090277) before the freeze. Codex holds R338-R346 and M413-M424 on its draft PR #56.
- **Date registered (UTC):** 2026-10-27
- **Code:** `scripts/run_tapelag_lighter.py`, tested by `tests/test_tapelag_lighter.py`.

## Why
**The owner (2026-10-26, 2026-10-27):** an edge must trade as short-hold futures, "scalping futures to do quick
money", and the lab must find one that pays.

**Fast to confirm.** The lab's daily books need years of forward days to reach t = 2. A rule that trades hundreds of
times a day can confirm in days. That needs a venue where a few bp a round trip is not eaten by fees.

**Lighter's default (Standard) account** pays 0 maker and 0 taker fees, API orders included
(`docs/VENUE_STRUCTURE.md`). A taker order, cancel or modify waits 300 ms before it reaches the book. That delay
protects Lighter's makers from faster traders. The question is whether Lighter's quote is still off Binance's after
it.

**R337 closed the hourly level model on Lighter** (NULL). The cost there was the book walk. Here the cost is the same
book walk, but the holds are seconds.

## Question
For 12 coins, take seconds when Lighter's mid sits further from Binance's than its recent level by more than a round
trip's cost. Buy (or sell) Lighter at its book one full second later, and close H seconds after that. Fee 0, cost the
measured book walk. Does the net per trade exceed zero, by a one-sided test calibrated under a dependent null, on 1-s
tape nobody has read against price changes?

## Data (all already held; nothing is downloaded)
- **Tape:** `data/tape/{binance,lighter}/book/{2026-10-21,2026-10-22,2026-10-26}.parquet`, sealed day files of
  `scripts/record_tape.py` (`lab/tape.py`).
  - One row per (coin, second) that had an update: the last best bid and ask with their sizes. `s` is the second's
    start on the exchange's clock. Lighter's matching engine stamps its updates in microseconds.
  - Coins: BTC, ETH, SOL, XRP, DOGE, BNB, SUI, ADA, LINK, AVAX, LTC, TRX. They are Binance USD-M perps and Lighter
    perps.
  - The recorder dropped its connections at container restarts, so coverage is patchy.
  - The trade files and MEXC's tape are not read.
- **Connections:** `inputs/sessions.csv`, a copy of the 158 rows of `data/tape/sessions.csv` that ended before
  2026-10-27. Each row is one connection and why it ended. The recorder appends to the original, so the copy is
  frozen.
- **Book cost:** the 20 hourly snapshots of `scripts/record_lighter_book.py` in `data/recorders/lighter_book/`
  (2026-10-21 16:00 .. 2026-10-26 21:00, with gaps), the same files R337 used.
  - Each row gives one market's cost from the mid of a $1k market buy and a $1k market sell walked through the shown
    book.

## Read before the freeze (no price after any signal)
`--plumbing` read coverage, quotes, sizes, lags and signal counts. Its one return statistic is the unconditional SD
of Lighter's mid change over 5 and 30 s, read for the power section.
- **Connected, both venues:**

  | Day | Hours |
  |---|---|
  | 2026-10-21 | 1.33 |
  | 2026-10-22 | 6.65 |
  | 2026-10-26 | 4.00 |

  Lighter's stream started on 2026-10-21 at 20:15.
- **Receive lag** (exchange stamp to this machine): median 47-89 ms, p99 500-600 ms, on both venues.
- **The basis moves little.** |dev| has a median of 0.3-1.0 bp, a p99 of 1.2-3.8 bp and a p99.9 of 1.8-5.5 bp.
- **The design changed on this.**
  - The first draft traded |dev| ≥ 3, 6 or 12 bp, and those almost never happen.
  - Lighter's alt books cost 0.8-4.1 bp a side, more than the basis moves. So the threshold is now cost-relative.
  - A size rule ($1k at the touch) became a cost rule. BTC's touch is often a few dollars, but its $1k walk is
    0.27 bp.
- **Per coin:**

  | Coin | Lighter half-spread, median bp | $1k walk, bp a side | SD 5 s / 30 s, bp | Signal episodes, θ 0.5 / 1 / 2 |
  |---|---|---|---|---|
  | BTC | 0.01 | 0.27 | 1.33 / 3.25 | 658 / 159 / 37 |
  | ETH | 0.21 | 0.23 | 1.88 / 4.61 | 921 / 309 / 52 |
  | SOL | 0.15 | 0.30 | 2.02 / 5.01 | 1,398 / 153 / 26 |
  | XRP | 0.68 | 0.77 | 2.03 / 5.02 | 54 / 17 / 3 |
  | DOGE | 1.83 | 1.95 | 2.07 / 5.33 | 2 / 2 / 0 |
  | BNB | 0.75 | 0.81 | 1.26 / 3.12 | 14 / 2 / 0 |
  | SUI | 1.71 | 2.00 | 2.89 / 7.24 | 6 / 4 / 4 |
  | ADA | 2.99 | 2.72 | 2.59 / 6.60 | 7 / 2 / 1 |
  | LINK | 1.68 | 1.65 | 2.38 / 6.24 | 2 / 2 / 1 |
  | AVAX | 1.22 | 1.63 | 2.78 / 6.80 | 8 / 4 / 3 |
  | LTC | 3.98 | 4.10 | 1.95 / 5.30 | 2 / 2 / 2 |
  | TRX | 1.67 | 1.59 | 0.59 / 1.45 | 1 / 1 / 1 |
  | **All** | | | | **3,073 / 657 / 130** |

  An episode is a run of consecutive seconds that meet the signal rule below.

## The rule
For each coin and each second s of a day:
1. **Connection:**
   - A venue is connected over a stretch of seconds in which it sent an update for some coin at least every 5 s.
   - A new stretch starts after each connection end in `inputs/sessions.csv`.
   - A coin's quote at the end of second t is its last update at or before t in the same stretch. Before its first
     update in the stretch, it is unknown.
   - A quote is valid when 0 < bid < ask.
2. **Basis:**
   - d(s) = 10,000 ln(Lighter mid / Binance mid).
   - ref(s) = the median of d over s-300..s-1, from at least 200 valid seconds.
   - dev(s) = d(s) - ref(s).
3. **Cost of one side at second t:** c(t) = max(Lighter's quoted half-spread at t, the coin's $1k walk). The walk is
   the median over the snapshots of the mean of the buy and sell costs, with a floor of 0.1 bp.
4. **Signal:**
   - dev(s) ≤ -(θ + 2 c(s)): Lighter is cheap by more than a round trip plus θ, so buy.
   - dev(s) ≥ θ + 2 c(s): sell.
5. **Entry:** at the end of second e = s + 1, at Lighter's mid ± c(e). That is a full second after the signal second,
   where Lighter imposes 300 ms. The quote at e must be valid; otherwise the signal is skipped.
6. **Exit:** at the end of second x = e + H, at Lighter's mid ∓ c(x).
   - If the quote at x is not valid, the trade is dropped and counted (the position existed, its price is unknown).
7. **One position per coin.** A coin takes no new signal before x + 1.
8. **Funding:** a hold that spans the top of an hour, when Lighter's funding settles, is skipped and counted.
9. **Net per trade, bp:** gross = side × 10,000 (mid(x)/mid(e) - 1). At kx: net = gross - k (c(e) + c(x)), for
   k = 1, 2, 3.

## Trials (6)
- **Grid:** θ ∈ {0.5, 1, 2} bp × H ∈ {5, 30} s.
- **Primary, fixed now:** θ = 1 bp, H = 5 s.
- **Reported for every trial:**
  - trades, gross, cost, and net at 1x/2x/3x per trade;
  - a trade's 5-minute bucket (by its signal second) and the bucket-sum Newey-West t (lag 3);
  - the 1x mean by coin, day and side;
  - the 1x mean on trades with $1k at the touch at entry;
  - entry delays of 2 s and 3 s, as sensitivity.
  - Neither the touch subset nor the delays is a trial or a gate.

## Test
- **The series:** for each trial, the sum of 1x net per 5-minute bucket, over every bucket with at least one second
  in which some coin had a valid dev. A bucket with no trade is 0.
- **The test:** a studentized circular block bootstrap.
  - Blocks of 6 buckets (30 minutes), 2,000 draws, seed 347.
  - All six trials are resampled together, each with its mean removed.
- **Outputs:**
  - each trial's one-sided p of mean > 0;
  - a family-wise p: the share of draws whose largest t over the six trials reaches that trial's t.

## Decision
**PASS (gate 1, research, on an unread sample)** only if all hold for the primary:
1. bootstrap one-sided p ≤ 0.05 at 1x;
2. the 2x mean per trade is positive;
3. the trimmed bucket mean (10 buckets removed at each end) is positive at 1x;
4. the 1x mean per trade is positive on at least 2 of the 3 coins with the most trades.

**PARTIAL:** the primary fails, but some trial has a family-wise p ≤ 0.05 and a positive 2x mean.

**NULL:** otherwise.

**Reported, not decided:** the mean without the two coins with the largest net sums (`docs/GATES.md`). Most trades
will be BTC, ETH and SOL, so an edge in those books is still tradable even if it fails this.

**What a PASS or PARTIAL earns:** a confirmation lane with a new id.
- It freezes this runner unchanged, with the sealed tape days from 2026-10-27 through 2026-11-09 as its inputs.
- It reads the passing trial once: one-sided bootstrap p ≤ 0.05 and a positive 2x mean.
- Only then would a paper execution design on Lighter's real order rules (gate 2) be drafted.

**What a NULL means:** at a 1-second resolution, Lighter's quote does not stay off Binance's long enough to pay its
book cost. That closes the taker form of this idea. The tape keeps recording for other questions.

## Power
- **Primary:** about 657 signal episodes in about 12 connected hours. The SD of a trade is about 1.3-2.0 bp (BTC,
  ETH and SOL over 5 s).
- **Detectable effect:** with half the trades effectively independent (signals cluster in time and across coins),
  80% power at a one-sided 5% needs a mean of about 0.25 bp a trade.
- A mean of 0.25 bp a trade is 25 cents on $10k: small, but repeated hundreds of times a day.
- A smaller true edge makes this read a futility screen. The confirmation lane would then hold about 1,300 primary
  trades for each fully recorded day.

## Known limits
- **Thin sample:** about 12 hours over 3 days.
- **Timing:**
  - One-second buckets. A fill one full second later is more pessimistic than 300 ms when Lighter's quote is
    catching up, and can be more optimistic when it is moving away.
  - The two venues' clocks are taken as aligned. Each stamps its own events.
- **Cost:** from 20 snapshots, not from the book at the moment of the trade.
  - Thin moments cost more. 2x and 3x stand in for that.
  - No queue, no partial fills, and nothing above $1k.
- **Fair price:** Binance's mid is taken as fair. A move that is Binance's alone shows up as a loss.

## Evidence lineage and admission
- **Canonical method:** M425 (new), related M264.
- **Parent rounds:** none on this data. R337 shares the Lighter book snapshots, used here only as costs.
- **Decision group:** M425's zero-fee quote-lag decision, which this lane alone feeds.
- **Samples seen:** none of the tape has been read against price changes by anyone. The plumbing above read signal
  counts, quotes, sizes and lags.
- **Fresh sample:** the 3 sealed days. The confirmation sample (2026-10-27 onward) does not exist yet.
- **`docs/GATES.md`** sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`.
  - Met: a dependent-null calibrated one-sided test, the trimmed mean, the leave-two-coins-out mean (reported), and
    a stated power.
  - Not met: strict on-time forward days. This is an unread archive sample, which `docs/GATES.md` lets count for
    gate 1.

## Multiplicity
- 6 trials (θ × H).
- Program trials: 9,479,005 on this branch after R337, and 9,479,022 counting Codex's R338-R346 on PR #56. R347 adds
  6.

## Inputs (sha256, path)
```inputs
fdc1d02f1671d793a7263ee33e7b881017e4c13d16277737929da509329108f1  data/tape/binance/book/2026-10-21.parquet
f41acb94963194aeb677d7ac21fb15632835ad4abb0b6e1ca2dac7812010b597  data/tape/binance/book/2026-10-22.parquet
d33ab971f501a41c282ae67bb5fe8d8f222d1437a54ee3e02ca854633c0b21fa  data/tape/binance/book/2026-10-26.parquet
a4b8839a433135b917992a4f111f7a3c32fc21df188f6812fd9f3542f0735669  data/tape/lighter/book/2026-10-21.parquet
4e29666cb43a90300c5204706f944fbfaef2c1b54248bd1996e33aa83925a21e  data/tape/lighter/book/2026-10-22.parquet
8397f29667c394bde732afea7b70f523bb72462f3c998ce9f3992594ca95874b  data/tape/lighter/book/2026-10-26.parquet
b853885e3b7f5b11919b41bd870fab87448d5d0812e170baeb06ac766453c695  experiments/tapelag_lighter_v1/inputs/sessions.csv
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
79231f8007fe958b9272feb836db3d64184feca9b89a007a65fa566f4cec18d1  scripts/run_tapelag_lighter.py
2443040db2bc404e424afee69f81ae6e859529a03014faaababb683aada8c52a  tests/test_tapelag_lighter.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508  lab/prereg.py
```
