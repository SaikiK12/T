# PREREG: reserved_batch1 (R286). The first reserved-sample batch: ten pre-committed candidates, read once

Freeze with `lab.prereg.freeze()` before any reserved row is read. Never edited afterwards; a change is a new batch.

- **Registry id:** R286 (Claude block R280-R299, claimed on issue #7 on 2026-10-21).
- **Gate:** 1, from the reserved samples (`docs/GATES.md`). This is batch 1 of the 4 each sample allows.
- **Owner (single writer):** the session that froze it. It writes only `experiments/reserved_batch1/` (`legs/`,
  `work/`, `results/`).
- **Tokens:** RESERVED-2020-READ RESERVED-GATE-READ RESERVED-MEXC-READ
  - **2020 crypto:** Binance perps, funding, premium and spot bars before 2021-01-01.
  - **Gate:** `data/gate_hist/reserved/`. Only the 2020 rows of the symbols in `experiments/xfund_v1/symbols.csv` are
    used.
  - **MEXC-only coins:** `data/mexc_hist` bars of the contracts of R265's 41 `reserved_mexc` unlock events, and no
    other MEXC-only contract.
  - RESERVED-VENUE-READ is not declared: no KuCoin or dYdX row is read.
- **Code:** `scripts/run_reserved_batch.py --run`, together with the files in the inputs block.
  - It refuses to run before 2026-11-03, without this file frozen, with any input changed, or a second time.
  - Right before the read, it reruns the dry parity: every candidate on the archive must still reproduce its lane's
    frozen numbers. A mismatch refuses the run. This guards the shared code (`lab/`, the qx engine) that the inputs
    block does not pin.
  - It writes `results/batch.json` and `results/decisions.csv`.
- **Read date:** on or after 2026-11-03, once.

## The candidates (all pre-committed by their own lanes before those lanes' results)
Each is its lane's frozen rule, unchanged. Only the sample differs. Costs are each lane's own (1x / 2x / 3x).

| Id | Lane | Rule | Sample read here | Archive result (gate 0) | Unit |
|---|---|---|---|---|---|
| C14 | R275 | Cross-venue funding carry, binance+gate L14d th10% K20 (`carry.toml`) | 2020, Binance + Gate | +10.05%/yr, NW t 5.96, 2,078 days | day |
| C01 | R265 | Unlock short, D-7 close to D close, 20/40/60 bp | `reserved_2020` (30 events), `reserved_mexc` (41), `post_archive` (15), pooled | +3.24%/event, week-cluster t 3.19, 422 events | event |
| C09 | R271 | Pre-listing notice short +168 h, 40/80/120 bp | 2020 notices (23 labelled) | +11.48%/cluster, t 2.03, 45 | event |
| C10 | R271 | Earn-product add short +168 h | 2020 notices (11 in 2020) | +3.85%, t 1.75, 143 | event |
| C11a | R263 | Strategy 330: RSI(14) 10/90 on 1 h bars, long only, top 20 | every 2020 day | discovery t 3.11, validation t 0.02 | day |
| C11b | R263 | The 6-month walk-forward stream, K = 20, over all 5,472 strategies | Jul-Dec 2020 | +1.18 bp/day, t 0.96 | day |
| C12a | R273 | Negative-funding onset (≤ -2%) long +72 h | 2020 onsets | +7.32%, t 2.39, 350; 10% trimmed mean -1.4% | event |
| C12b | R273 | The same, +24 h | 2020 onsets | +4.60%, t 2.03, 350; trimmed -2.3% | event |
| C12c | R273 | Onset ≤ -1% long +24 h | 2020 onsets | +1.26%, t 1.16, 860; trimmed -2.0% | event |
| C12d | R274 | Onset ≤ -0.3% short +168 h, 10% close cover | 2020 onsets | +0.11%, t 0.33, 2,278; trimmed -0.9% | event |

**Left out:** C15 and C16 (R282 coin age and volume/cap). Their archive books have NW t 0.68 and 0.39, and without
their 10 best days the mean is about 0. That is an expected t near 0.3 in one year, too little to be worth α.

**Window details:**
- **Events (C09, C10, C12):** qx `events` from 2020-01-01 to 2021-01-08, so the +168 h exits of late December
  price in early 2021. Events before 2020 have no perp bar and count as no market.
- **2020 funding onsets:** `scripts/reserved_legs.py --start 2020-01-01 --end 2021-01-01`. Its rule is R273's and
  R274's: `tests/test_reserved_legs.py` checks byte parity on 2021-26.
- **C01:** Binance 2020 bars through `lab.panel` and MEXC bars through `mexc_panel`, both behind the tokens. Post-archive
  bars come from `data/binance_recent`, refreshed before the run (the runner refuses if any perp ends before the last
  exit). Same entry, exit, cost and week clustering as R265.
- **C11:** the universe is R263's rule (`lab.research.make_universe(elig_top=50, col_top=50)`) on a 2020 panel. The
  members are the top 20 crypto perps by trailing volume.

## What the author has seen
- **Every candidate's archive result above,** and the full R263, R265, R271, R273, R274 and R275 FINDINGS.
- **Reserved-sample counts from the event lists only:** unlock events by window, R271 notices labelled
  `reserved_2020` by type. No 2020 price, funding, premium or return was read, and no MEXC-only bar, for these
  questions.
- **Disclosed partial reads of 2020 by other work** (`docs/GATES.md`):
  - R244 used BTCUSDT's 2020 weekend moves as a QQQ predictor.
  - The old session's prop-challenge sims (R143/R144) started chase rules in 2020-22.
  - C11a and C11b trade BTC among the top 20, so they are only partly fresh for BTC.
- **The dry run** (`--dry`) reproduced every candidate's frozen archive numbers exactly:
  - the 6 event strategies through qx, at n, mean 1x/2x/3x and t;
  - R265's primary;
  - R275's row;
  - R263's cached nets, for 5 ids including 330, and its decided stream.
- **The rehearsal** (`--rehearse`) ran the `--run` code on archive stand-ins under a throwaway PREREG:
  - 2021 for 2020;
  - archive Binance coins on MEXC prices for the MEXC-only coins;
  - archive 2026 events on `data/binance_recent` for post_archive.

  It completed (exit 0), and its full output was seen. Every number in it is archive data the lanes had already
  read, so it says nothing about the reserved samples:
  - C14 on 2021: 344 days, +11.5%/yr, NW t 6.95;
  - C01 on its stand-ins: 365 events, +2.93%/event, t 2.52;
  - C11a on 2021: t 1.37; C11b on Jul-Dec 2021: t 1.40;
  - C09 3 clusters, C10 20 (t -1.17), C12a-c 1 each, C12d 73 (t -0.32).

  It decided nothing. It set the expected n and E[t] of the power table below, and so the weights.

## Statistics (per candidate, at 1x of its lane's cost)
- **Events (C09, C10, C12):** one observation per cluster, the engine's rule: same type and hour; the mean net of
  its legs.
  - t = mean / (sd / √n); one-sided p from Student t with n − 1 df.
- **C01:** R265's net per event and its ISO-week cluster t; one-sided p from Student t with G − 1 df.
- **Daily (C14, C11a, C11b):** daily net, Newey-West t with lag 10; one-sided p from the normal.
- **Robustness, all at 1x:**
  - the 10% trimmed mean;
  - the leave-two-coins-out mean (the two coins with the largest summed net contribution dropped);
  - the 2x mean.
- **Reported:**
  - 3x;
  - median and hit rate of the event candidates (C01, C09, C10, C12);
  - C01 by window;
  - C14's annual net at 1x/2x/3x;
  - every candidate's n.

## Decision: weighted Bonferroni, one-sided α = 0.05 over the batch
- **Weights** are fixed below (the runner checks this block against its own `ALPHA`).
- **PASS:** one-sided p ≤ the candidate's α, **and** its 10% trimmed mean > 0, **and** its leave-two-coins-out
  mean > 0, **and** its 2x mean > 0.
- **FAIL:** read but not passing.
- **UNREADABLE:** fewer than N_min observations: 8 events or clusters, or 60 days.
  - An unreadable candidate's α moves to the readable ones in proportion to theirs. The total stays 0.05.
  - This is likely for C09 and C12a-c (few 2020 notices and deep onsets; 2021 gave 3 and 1).
- **No other test is decided on.** Nothing is re-run with other parameters.

```alpha
C14 0.0273
C01 0.0147
C09 0.001
C10 0.001
C11a 0.001
C11b 0.001
C12a 0.001
C12b 0.001
C12c 0.001
C12d 0.001
```

## Power (how the weights were set)
**Expected t on the reserved sample** = archive t × √(expected reserved n / archive n) × a shrink for having been
picked. The weights maximise the expected number of passes, Σ Φ(E[t] − z(α_i)), with a floor of 0.001 per
pre-committed candidate.

| Id | Expected n | Shrink | E[t] | α | Power |
|---|---|---|---|---|---|
| C14 | about 330 days (fewer coins than 2021-26: 81 Binance perps) | 0.75 gives 1.8 from the archive's mean year; 2021 alone gave 6.95; set low, at 2.5 | 2.5 | 0.0273 | 0.72 |
| C01 | about 65 priced events (about half of 2020's 30, most of the 41 MEXC, all 15 post_archive) | 0.8 | 1.0 | 0.0147 | 0.12 |
| C09 | about 5-10 clusters (2021 gave 3) | 0.6 | 0.3 | 0.001 | 0.003 |
| C10 | about 8 | 0.6 | 0.25 | 0.001 | 0.002 |
| C11a | 366 days (validation t was 0.02) | 1 | 0.02 | 0.001 | 0.001 |
| C11b | 184 days | 1 | 0.3 | 0.001 | 0.003 |
| C12a-b | 1-15 deep onsets (2021 gave 1) | 0.6 | 0.2-0.25 | 0.001 each | 0.002 |
| C12c | 0-30 (2021 gave 1) | 0.6 | 0.13 | 0.001 | 0.002 |
| C12d | about 60 (2021 gave 73) | 1 | 0.1 | 0.001 | 0.001 |

- **Expected passes:** about 0.85, against 0.60 with equal weights.
- **C14's power** is 0.45 at E[t] 1.8 and 0.94 at 3.5, so the weights do not hinge on its exact E[t].
- **The likely outcome:** C14 and C01 are the only candidates with real power; the rest are read because they were
  promised, not because they can pass.
- **C12's archive edge is in its tail** (negative trimmed means), so it would fail the robustness checks even with a
  small p.

## What a result earns
- **PASS:** a gate-1 confirmation for that candidate. Then:
  - C01 and C09 already have forward lanes (R266, R272). They continue, and the PASS joins their own gate-2 decision.
  - Any other passing candidate gets a new frozen forward paper lane (new id), labelled manual-web or API.
  - The owner places any real stake through `lab.gate.go_real()`, after paper proves a net gain.
- **FAIL or UNREADABLE:** recorded. The candidate is not read on these samples again. Its own lane's verdict stands.
- **The read budget:** this batch spends read 1 of 4 of each of the 2020, Gate and MEXC-only samples.
- **Registry:** one row, R286, with 10 trials. FINDINGS reads the result against `registry.program_trials()`
  (9,478,421 before this batch).

## Inputs (sha256 at the freeze; the runner refuses if any differs)
```inputs
scripts/run_reserved_batch.py dfde1fa42b00d546f34bc0272981e7cb854277a4e55896c1d016d1a9ba51281c
scripts/reserved_legs.py 0f4b4f3e2fb106a1aed502b217491de9c695ac2a5ff138f247bbdad356b962de
scripts/run_unlocks.py 513974db7f83a4ca45fda43109721363d3361f6351a68948241adccc62c0570e
scripts/unlock_events.py cec5b38002b4df24ad35f55b51bcbcb08f91c952bd7013940e2c0b9fd549b5ea
scripts/run_brute5k.py 2be7f2b63f50b9c428db7ce55f36f1b143a9726d8879c6d5d90e17e8aec489d9
experiments/reserved_batch1/carry.toml d049ac04e97f9e65da74549ce4abaab569afbc9fc92f69b4854c125323019afb
experiments/announce_v1/spec.toml 17dd1ef383ab051d9a61ea3780e0ad04e1582aa918a2457efdbc46da8fe1a247
experiments/announce_v1/legs.csv ee98416d8960fbf2322f916f5d7269120b83670d43d2c0197c82979de5215224
experiments/fundext_v1/spec.toml 4634db9e35224c85704068b97cd9e95b69a52ed28e26e60f1e9dca2f92d0e155
experiments/squeeze_v1/spec.toml 05151cde658022a94ae2c2841c87cc6fb93b32fc864262ecf195a854162cad9b
experiments/unlocks_v1/events.csv 24cd0d052bea6dcab1e4f862dad3227348644fb887ba61d14ca56cdb00cd794e
experiments/unlocks_v1/symbol_map.csv 0f924ae96cf137e8a09305aff0c07ec041f3a07cd5417643741e3366aace472b
experiments/xfund_v1/symbols.csv 78201a341b9fc498b67f4893f1dd30d67d790d94ca8257a4b1a2ce8f569ab8e0
experiments/venue_gap_v1/results/tradfi_symbols.json af7b1a0fbf99471720f765ece0b16734b88247aa84feb7f21137103500d983ea
```
