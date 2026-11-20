# PREREG: xfund_kokx_v1 (R515). R275's carry book on Kraken + OKX Europe X-Perps, two MiFID-regulated venues with the funding design gap

Freeze with `lab.prereg.freeze()` before any Kraken-OKX spread is computed. Never edited afterwards.

- **Registry id:** R515
- **Owner (single writer):** the Claude session that froze it. `scripts/run_xfund_kokx.py` is the only writer of
  `experiments/xfund_kokx_v1/results/` and `data/okx_kokx_v1/`.
- **Date registered (UTC):** 2026-11-20

**Methods:** M556 (new: R508's design gap on a pair where both venues are regulated in the EEA). Carry, candidate C13.
- **Paper only:** held public data; nothing can place an order.

## Why
- **The owner, 2026-11-20:** "continue".
- **The 2026-11-20 reading round.** ESMA's 2026 statement makes retail crypto perps likely CFDs, so the first stake is
  capped at 2:1. And Moore & Christin's 30% one-year closure rate argues for regulated venues.
- **R508/R511's legs:** Hyperliquid and Aster, which are authorised nowhere.
- **OKX Europe X-Perps:**
  - MiFID, open to EEA retail per OKX;
  - their funding has the 0.01%/8 h interest term (`formulaType` withRate in the recordings);
  - their median funding was about 10%/yr in R430's snapshot.
- **The question.** Kraken has no interest term. So Kraken + OKX could carry R508's design gap with both legs
  regulated.

## Question
Does R275's book, unchanged, earn a positive net return at R275's costs on Kraken + OKX Europe X-Perps,
2026-08-10..2026-11-15?
- This is gate 0 on short, partly seen history.
- A PASS earns a forward paper lane on this pair (a new id), with measured costs and a sequential monitor.

## Data
- **Kraken:** `data/kraken_hist/open` (rebuilt 2026-11-17..18). Funding is hourly and relative; daily candles.
- **OKX:** the recorder's data branch `claude/okx-xperp-data` at commit 4d5d5c0c6825c8ea2464b79c081c4065f7838a70
  (2026-11-20 10:42 UTC), extracted with `git archive` into `data/okx_branch_20261120/`.
  - Funding prints from 2026-08-10: `funding/*.csv`, rate per print, settling every 4 h or 8 h.
  - Daily trade candles: `trade_1d/*.csv`, closes and quote volume.
  - The listing: `instruments/*.json`.
- **Pinned.** `data_manifest.json` pins the sha256 of the 182 Kraken files and 323 OKX day files used.
- **Universe:** Kraken `open` contracts paired with OKX crypto X-Perps (instCategory 1) by R508's name rule; 91 coins
  (`symbols.csv`). Survivorship: today's listings on both venues.

## Rule
- **R275's rule by `lab.xfund`**, R508's spec values:
  - lookback 14 days, entry 5%/yr, 20 slots;
  - correlation guard 30 days, ≥ 0.9, 20 observations;
  - daily bars on both venues;
  - 7 / 14 / 21 bp a leg.
- **Fees today:** Kraken taker 5 bp; OKX Europe taker 5 bp (lab fee map, not re-read).
- **Secondary (reported):** entry at 10%/yr.

## Decision: R391's rule, as in R507, R508 and R511
- **UNREADABLE:** fewer than 60 book days.
- **PASS:** all of these hold:
  - the one-sided NW p (lag 10) of the 1x daily net is at most 0.05;
  - the 2x mean is above 0;
  - the 10% trimmed mean is above 0;
  - the mean without the two best coins is above 0.
- **FAIL:** otherwise.

## Power
- The window gives about 65 book days after the lookback and the guard's 20 days.
- At R508's Sharpe of about 7, t ≈ 3. At a third of it, t ≈ 1 and the book FAILs or is barely readable.
- A FAIL here is weak evidence; a PASS is a reason for the forward lane, not a result in itself.

## What the author has seen
- **OKX:**
  - R430 read OKX funding prints, 2026-08-06..11-09, and reported a cross-section (M490: median about 10.4%/yr).
  - R443 read the OKX-Hyperliquid spread over 83 days (-3.05%/yr reported).
  - On 2026-11-20 the session printed one funding row (0G, 2026-11-19, after the window) and the instrument listing.
- **Kraken:** R508 read the funding and prices of 82 of these 91 coins.
- **Never computed:** the Kraken-OKX spread.

## Trials
- **This round:** 1.
- **Program trials:** 9,785,755 before, 9,785,756 after.

## Inputs
| File | sha256 |
|---|---|
| `scripts/run_xfund_kokx.py` | 12c1b1a8c87e2378369343f522d1de7aa3e3c13a3d8c26a30907db529b2330d0 |
| `tests/test_xfund_kokx.py` | b5ad267f23d1985326e4e53711eb996aeec3f6a0ec00b51d7c9445d8462ee191 |
| `scripts/run_xfund_eea.py` | 4749ebbdca13106471c4f582e7b59a4e3f0ac893c388d46181e07615d618f9e5 |
| `scripts/run_xfund_bfx.py` | 62c1c214856c80b5006527824778815069cf341b740bb5d48c4d646364d30b79 |
| `lab/xfund.py` | d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d |
| `lab/stats.py` | bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 |
| `experiments/xfund_kokx_v1/symbols.csv` | ae64bdca729faf7dc0b772169d1f918e3757d8d00936416f7aa99c678d5eccb7 |
| `experiments/xfund_kokx_v1/data_manifest.json` | bce3a8069c326c5de4605dad90b8b4d2d1e3ea4dbf350502b4f4c938d898ba6c |
