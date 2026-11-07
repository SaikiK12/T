# PREREG: tapelag_lighter_v2 (R348). R347's zero-fee Lighter scalps, rerun after a crash before any statistic

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R348
- **Method:** M425, as R347.
- **Owner (single writer):** the Claude session that froze it. R348 was claimed on issue #7 before the freeze.
- **Date registered (UTC):** 2026-10-27
- **Code:** `scripts/run_tapelag_lighter_v2.py`, tested by `tests/test_tapelag_lighter_v2.py`. It imports R347's
  frozen `scripts/run_tapelag_lighter.py` unchanged.

## What happened to R347
- R347 (`experiments/tapelag_lighter_v1`, PREREG sha256 `d70ff9f3…cf2a`) was frozen and pushed in `baaec34`.
- Its run stopped at 14:12 UTC with a `TypeError` in its summary. Under pandas 3, a coin-day with no trade gave an
  empty trade table with untyped (object) columns. The concatenated net column stayed object, and `nlargest`
  refused it.
- The run had printed only the input check, the book costs and the bucket count (151 buckets of 300 s). No
  statistic was computed, printed or read. Its log is `experiments/tapelag_lighter_v1/run.log`.
- R347's files stay unchanged, and its registry row records the crash with 0 trials.

## The one change
`typed()` casts each coin-day's trade table to numbers before the concatenation (s, e, x and side to integers, the
rest to floats). Everything else is R347's frozen code, called as it is:
- the stretches, grids, deviation, book costs, trade simulation, summary, bootstrap and decision rule;
- the constants, days, coins and trial grid.

`tests/test_tapelag_lighter_v2.py` runs the whole pipeline on an invented tape where ten coins have no rows, which is
R347's crash case.

## Rule, trials, test and decision
Exactly R347's PREREG, frozen in `experiments/tapelag_lighter_v1/PREREG.md` and listed in the inputs below:
- 6 trials: θ ∈ {0.5, 1, 2} bp beyond a round trip at the measured $1k book cost, × H ∈ {5, 30} s.
- Primary: θ = 1 bp, H = 5 s.
- Fill one full second after the signal. Fee 0.
- The studentized circular block bootstrap on 5-minute bucket sums (blocks of 6, 2,000 draws, seed 347).
- PASS, PARTIAL or NULL by R347's four conditions and its family rule.
- What a PASS or PARTIAL earns: R347's confirmation lane on the sealed tape days 2026-10-27..2026-11-09.

## Multiplicity
- 6 trials, the same six as R347. R347 is recorded with 0 trials, because it computed no statistic.
- Program trials: 9,479,005 on this branch, and 9,479,022 counting Codex's R338-R346 on PR #56. R348 adds 6.

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
d70ff9f31c8e2fd772bcad6c558cdf3e93795470016eb3a5c6fea0b6f399cf2a  experiments/tapelag_lighter_v1/PREREG.md
0129268d967c3ec41d9a82f9e40658231df7baee9ac0d6ac65c6a32dab641d78  experiments/tapelag_lighter_v1/PREREG.sha256
79231f8007fe958b9272feb836db3d64184feca9b89a007a65fa566f4cec18d1  scripts/run_tapelag_lighter.py
2443040db2bc404e424afee69f81ae6e859529a03014faaababb683aada8c52a  tests/test_tapelag_lighter.py
7826b1429c4307eb7089b422faf8dcd91f131e28af0cf8c3c1b22ae922d52011  scripts/run_tapelag_lighter_v2.py
b323f32a6053ac30af551ed56a5e013c219fc9f9be2a8f7ab0087da2c6e7d49d  tests/test_tapelag_lighter_v2.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508  lab/prereg.py
```
