# PREREG: carry5_v1, one carry book over five venues (R275's four plus KuCoin) on the M468 engine

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R439
- **Owner (single writer):** Claude, session on `claude/yo-9a1k5w` (hunt mode, 2026-11-10)
- **Date registered (UTC):** 2026-11-10

## Question
Does R275's all-four carry rule (L14d, entry threshold 10%/yr, K20), run as one book over five venues (Binance, Gate,
Hyperliquid, MEXC and KuCoin), keep NW t >= 2.5 at 1x, a positive 2x mean and two positive halves on the corrected
M468 engine (`lab/xfund_v2.py`)? And how much does adding KuCoin change it against the same rule on R275's four
venues (paired, reported)?

**Why now.** Carry is the lab's only family that passed gate 0, a blind 2020 read and a long-tail read. R437 and R438
showed it is not an accounting artifact. Today's false-null audit found most other NULLs underpowered; carry is where
the lab has power. The open question for real PnL is how much the family earns when every venue we hold feeds one book.
KuCoin was replicated separately (R277), but never added to a multi-venue book.

## Universe and data
- R275's frozen manifest (`experiments/xfund_v1/symbols.csv`, 867 Binance-listed coins) with R277's KuCoin column
  joined on `key` (`experiments/xfund_kd_v1/symbols.csv`): `experiments/carry5_v1/symbols.csv`, 633 coins with a
  KuCoin symbol. Binance and Gate symbols agree between the two manifests on every shared key (checked at build).
- Current-survivor-only as in R275 and R277. No reserved row: window from 2021-01-01; KuCoin's long tail without a
  Binance perp (reserved by `docs/GATES.md`) is not in the manifest.
- Data exactly as R275 and R277 read them (`experiments/carry5_v1/spec.toml`). Window 2021-01-01 to 2026-09-30. No mark
  prices.
- **Data identity check (binding):** before any statistic of the five-venue book, the runner replays the four-venue
  book with `lab/xfund.py` on this universe and requires its 1x daily net to equal R275's frozen
  `results/daily.csv` to 1e-9. A mismatch stops the run.

## Feature lineage and point-in-time availability
As R437 (`experiments/carry_v2_audit_v1/PREREG.md`): trailing 14-day funding spread settled before 00:00 UTC of the
decision day; fresh = a traded bar ending in the day; identity guard 30 days, >= 20 observations, corr >= 0.9; legs
valued at the last traded close carried to 00:00 UTC, no price gain on an unobserved interval. All available at the
decision time.

## Rule
- **Book (1 trial):** `binance+gate+hyperliquid+mexc+kucoin L14d th10% K20` on `lab/xfund_v2.py` as committed: the
  pair for a coin is the two venues among the five with the widest trailing spread (v1's candidate rule); fixed-quantity
  legs; `dead` and `blowout` (20%) exits; costs 7, 14 and 21 bp per leg (1x, 2x, 3x); returns on total book capital.
- **Paired reference (not a trial):** the same rule on R275's four venues, v2, same universe, same days.
- **Runner:** `scripts/run_carry5.py` (R437's frozen runner functions, unchanged).

## Decision (frozen)
- **SURVIVES** (registry CONFIRMED) when, on the five-venue book's v2 1x daily net: NW t (10 lags) >= 2.5, the 2x mean
  > 0, and both halves' means > 0. **FAILS** (registry NULL) otherwise.
- Reported, not gating: %/yr at 1x/2x/3x, 2025+ bp/day, max drawdown, top-10-day share; the paired daily difference
  against the four-venue reference (mean bp/day, %/yr, NW t); funding, price and cost split; funding on constant entry
  notional (R438's drift diagnostic); exits by reason; the share of trades with a KuCoin leg; pairs by venue.
- **What follows:** if it SURVIVES and the paired difference is positive, a forward paper lane of the five-venue book is
  the next id (its own PREREG). Venue access from France is the owner's to check before any real use.

## Null and multiplicity
- No null is built; the frozen t threshold decides.
- 1 trial. The rule is R275's all-four pick (best of 560 by t), so this inherits that selection. No variant, slot count
  or threshold is tried.
- Program trials before this lane: 9,784,981.

## Evidence lineage
- Methods: M468 (engine), M497 (accounting audit family, R437 and R438), new row M498 (this five-venue book).
- Seen samples: all rows were read by R275 (four venues) and R277 (KuCoin, with Binance and Gate). The five-venue book
  itself has never been run. Gate 0 on seen rows.
- Prior exposure: R437's v2 all-four result (+16.99%/yr, NW t 4.77) and R438's v2 KuCoin books. Plumbing (2026-11-10
  about 13:45 UTC) read only v1 parity and fresh coin-day counts.
- `docs/GATES.md` SHA-256: e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926. Gate 0 only; admits nothing
  to real money.

## Plumbing record (2026-11-10, before the freeze)
`python scripts/run_carry5.py --plumbing`: 867 coins x 5 venues, 2,100 days, loaded in 174 s. v1 four-venue book equals
R275's daily net (max |diff| 5.0e-11, 2,078 days). Fresh coin-days under v2: binance 579,699; gate 631,557;
hyperliquid 167,076; mexc 246,175; kucoin 432,107. The synthetic dry run and 3 runner tests passed.

```inputs
cc04e3aae2fbb2028e4918f0df13f9807196d041e176f8c4d52553a1cfc0df4c scripts/run_carry5.py
d360b83117ed89ac3a144498cfddf680d3b920925ef8c36c8c5668a1b1c6b15b tests/test_run_carry5.py
1ba92fe3df40a0eac920e47c69ac4b7b9024750d4ba13f94edcfbe8f4550b7e5 scripts/run_carry_v2_audit.py
d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d lab/xfund.py
fa85ef56885a1d6736dd92e73f8bce44e97ce9ee001739526caef86ae1ba62cd lab/xfund_v2.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 lab/stats.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba scripts/run_clockflow.py
a35e16f9a12fe5443cd4edfc18c6f293f19d62370fb4b43d4fccd5e077e0900d experiments/carry5_v1/spec.toml
22a91dc96cd04a4ac9dce5914d5fba5485f754088acef74f7efe03f10e8e0328 experiments/carry5_v1/symbols.csv
78201a341b9fc498b67f4893f1dd30d67d790d94ca8257a4b1a2ce8f569ab8e0 experiments/xfund_v1/symbols.csv
15c8054f7e10f921bd9a797fbf2b9ac927c99fdfbc2388a54199be0cace6fb3b experiments/xfund_kd_v1/symbols.csv
790d4a0fae2d0fa51e3c5c8e0d28c9ce7be9c5f037187c39b95959fb68fa8dfc experiments/xfund_v1/results/daily.csv
55e45182aade91c169b5a58b94ea9c831a64bc7753828fd276b7c94ed26e8de6 docs/provenance/klines_1h.json
84a3aadbf5ac0439b99209714c85ab0484b775f1258701835a64029c1ec3e4de docs/provenance/fundingRate.json
e496f80737a33ccffd3be5fb2d119310d91930021f7477338e124290950563c0 docs/provenance/gate_hist.json
72a6204069af064911d82339e7e637079cba343df4e8914f83d88197396a065b docs/provenance/hyperliquid.json
5fb2f74b0ffbfde94f9a73830b728e22387bce12475802fba01ac42fb7898c55 docs/provenance/mexc_hist.json
bc5abe62d763042bd2e01fe88f7b5bf367bdda263200c1cec67486fed19a4b13 docs/provenance/kucoin_hist.json
```
