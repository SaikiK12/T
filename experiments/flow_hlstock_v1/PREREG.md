# PREREG: flow_hlstock_v1 (R451). R200's flow books on stock, index and commodity perps on Hyperliquid's xyz

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a changed idea is a new lane.

- **Registry id:** R451
- **Owner (single writer):** the Claude session that froze it, on `claude/yo-9a1k5w`.
  - `scripts/run_flow_hlstock.py` is the only writer of `experiments/flow_hlstock_v1/journal/` and `results/`
    (the journal's README.md, written once at registration, excepted).
  - From the forward start it runs in `.github/workflows/claude-flow-paper.yml`, right after R448.
- **Date registered (UTC):** 2026-11-11

**Methods:** M126 (book A, three flow cells) and M127 (book B, top_vs_crowd alone).
- Parents: R197, R198, R200 (forward on Binance), R216 (crypto/TradFi split), R448 (crypto on Hyperliquid).
- **Paper only:** public endpoints, no account, no key; nothing in the code can place an order.

## Question
Do R200's flow books, restricted to the stock, index and commodity perps ("TradFi") that Hyperliquid's xyz markets
list, earn a positive net return on xyz's own hourly closes and funding, at the lab's tier costs (never below xyz's
fee) and at 2x and 3x?

## Why this lane
- **Where the profit was.** R216 found that R200's forward gain came mostly from Binance's TradFi perps:
  - book B's replay gain of 2026-10-01..18 (+9.7%) was all TradFi;
  - TradFi carried 49% of book A's.
- **Why not crypto.** R448 found that the crypto part on Hyperliquid's coins is small (A +4.9 bp/day, t 0.91; B
  negative).
- **The venue.** Binance is closed to the owner from France. Hyperliquid's xyz dex (HIP-3, deployed by trade.xyz)
  lists 122 markets, mostly US stocks, indices and commodities.
  - Hyperliquid needs no account and no KYC.
  - trade.xyz's terms (trade.xyz/terms, read 2026-11-11) restrict the US, Canada, the UK, sanctioned territories and
    "certain other jurisdictions we may designate". France is not named.
- **This is the execution check of R200's actual source of gain on a venue the owner can reach.** The signal is
  unchanged: Binance's public ratios.

## What the author has seen
- **The parent lanes:**
  - R197, R198 and R216 in full, including R216's TradFi split of R200's 2026-10-01..18 replay. R448's gate 0
    (crypto only).
  - R200's forward totals through 2026-11-09 on Binance prices: A +31.0% and B +13.3% over 40 days, not split by
    TradFi after 10-18.
- **xyz, structure only:**
  - its market list (122 live);
  - which of R200's 24 TradFi symbols map to it (16 by base, 5 more by the aliases below, 3 unmapped);
  - that `xyz:TSLA` has 5,001 hourly candles from 2026-04-16 and hourly funding;
  - the fee schedule (docs.trade.xyz/perpetuals/mechanics/fees.md: standard HIP-3 fees are "2x the usual fees on
    validator-operated perp markets", taker 0.090% at tier 0; growth mode, if enabled, cuts them by 90% or more);
  - the terms above;
  - the oracle and trading-hours notes: stock prices are external 24/5, with an internal session at weekends, as
    summarized by a helper.
  - the gate-0 fetch's log: 1,009 hourly rows per mapped coin, and the last two rows of `xyz_TSLA.csv` (two
    prices and funding rates of 2026-11-10 23:00 and 2026-11-11 00:00; no return).
- **Not seen:** any return on xyz prices, any R200 TradFi return after 2026-10-18 split from the crypto ones, and any
  R200 hour from 2026-11-12 on.

## Data
- **Signal (gate 0):** R200's journal rows of 2026-10-01..2026-11-10 (`experiments/flow72_fwd2/journal/signals.csv`).
  - They are copied by `--window fetch` to `data/r200_signals.csv` and pinned below.
  - The hours of 2026-10-01..18 were computed on 2026-10-19 from the same public history (R200's own catch-up);
    gate 0 enters one bar late regardless.
- **Signal (forward):** R200's journal (`signals.csv` and `ticks.csv`), written live by `scripts/forward_tick.py`, read
  as R200 wrote it.
- **Prices (gate 0):** `data/xyz_<COIN>.csv`, xyz's hourly closes and funding from Hyperliquid's public
  `candleSnapshot` and `fundingHistory`, 2026-09-30..2026-11-11 00:00. Also `data/xyz_coins.json`, the market list on
  the fetch date. All are fetched by `--window fetch` and pinned below.
- **Prices (forward):** the same endpoints at run time. Every closed hour is appended to `journal/hl/<YYYY-MM>.csv`,
  and rows are never rewritten.
- **TradFi list:** R216's `experiments/venue_gap_v1/results/tradfi_symbols.json` (pinned).

## Rule
R448's rule and frozen functions (`scripts/run_flow_hl.py`, imported unchanged), with these changes:
- **Universe:** R200's eligible symbols that are in R216's TradFi list and map to a live xyz coin.
  - The mapping is `xyz:<base>`, or one of five fixed aliases: XAU→GOLD, XAG→SILVER, BZ (Brent)→BRENTOIL,
    SPY→SP500, SAMSUNG→SMSN. No other alias.
  - QQQ, SKHYNIX and SOXS are unmapped. The unmapped count is reported.
- **Tradable at row t:** eligible, mapped, and xyz has a close for row t. Gate 0 also requires the close of row
  t + 1.
- **Slices, books, hedge, entry:** as R448.
  - A short slice of 1 / (72 x 9.316) is held 72 hours.
  - Book A = the three cells; book B = top_vs_crowd.
  - The hedge is long the equal-weighted basket of the tradable xyz coins.
  - Entry: gate 0 one bar late; forward, at R448's `entry_lag`.
- **Return:** xyz close[t+1] / close[t] − 1, less the funding a long pays at the settlement stamped in hour t + 1
  (`hl_returns`).
- **Costs:** the lab's tier cost by Binance rank (6/8/12/20 bp one way), **never below 9 bp one way** (xyz's
  standard taker fee). It is charged on every change of position and of the hedge, at 1x, 2x and 3x.
- **Missing prices:** a held coin with no close earns nothing that hour (the legacy rule, as R215/R448).

## Gate 0: 2026-10-01..2026-11-10 (41 days), exploratory
- No slice carries in (R200's journal starts on 2026-10-01).
- **Decision, per book:** CONTINUE if the 1x mean daily net on xyz is above 0, else NULL. Gate 0 cannot earn
  anything: R200 and R216 read these days on Binance's prices.
- **Reported, not decided on:**
  - the same coins and slices on Binance's closes from R200's journal (no funding: the journal has none), and every
    TradFi symbol on Binance;
  - 2x and 3x; gross, cost and hedge; funding received;
  - coverage and the correlation with the same-coin Binance book;
  - the trimmed mean, leave-two-coins-out and the top contributors.

## Gate 1: forward from 2026-11-12 00:00 UTC (R448's gate 1, unchanged)
- One ticket per book per complete UTC day (`journal/tickets.csv`, appended), with per-coin gross in
  `journal/coins.csv`.
- **Counted days:** strict on-time days only (every one of R200's 24 hours computed within 60 minutes of its close).
- **Futility screen at 90 counted days, per book:** NULL if the mean 1x net of the first 90 is 0 or below.
- **Final read at 365 counted days, per book:** PASS if all of these hold:
  - the mean 1x net of the first 365 is above the threshold;
  - the 2x mean is above 0;
  - the trimmed mean (10 best and 10 worst days removed) is above 0.

  NULL otherwise. The threshold is the upper 2.5% quantile of a 365-day mean under the null: gate 0's daily 1x xyz
  net for the same book, its mean removed, in blocks of 10 days (20,000 draws, seed 448).
- **Stop rule:** a book whose cumulative net falls 0.5 below its running peak is stopped and NULL.

## Decision group and what a PASS means
- This lane shares its cells with R200, R214, R215, R218, R225 and R448, so it is not a new chance on the signal.
  It is the France-reachable execution check of R200's TradFi part.
- An owner stake would need R200 to pass on the signal **and** this lane to pass on xyz's prices. Then
  `lab.gate.go_real()` and the owner's decision apply (AGENTS.md rules 5 and 6). A PASS here authorizes nothing by
  itself.

## Power
- Not computed before the freeze: it needs the TradFi books' daily sd on xyz, which is a return.
- Gate 0 reports each book's daily sd. FINDINGS gives the counted days a 365-day read needs at gate 0's mean.
- The 41-day gate-0 null is short. The bootstrap threshold rests on it, as R448's rests on 183 days.

## Multiplicity
Trials = 2 (books A and B, one rule each). Program trials before: 9,784,995 (9,784,997 after). There is no
across-family correction: a pass stays conditional on R200's.

## Limits
- **Off-hours prices:** xyz's stock prices outside US hours come from its oracle's fallback and its own book, not
  from a stock exchange. Binance's TradFi perps trade around the clock too, so the signal and the price share that
  property.
- **Fees:** standard HIP-3 fees are assumed (9 bp taker). Growth mode would cut them, but it was not checked per
  market. Depth on xyz was not measured.
- **Coverage:** the hedge basket is the tradable xyz coins: stocks, indices and commodities together, as R200's
  books mix them.
- **Gate 0 is short and seen.** Its 41 days decide only whether the books stop.
- **Jurisdiction:**
  - trade.xyz's terms do not name France, and Hyperliquid's terms as read before (R444-R446) do not exclude it.
  - Equity-linked perps sold to EU retail may fall under rules no venue term covers.
  - This is not legal advice; the owner checks.

## Stop rules
No new cells, venues, coins, aliases or windows after a result. A changed idea is a new lane.

```inputs
cecfa25866aa5873128f1e97b71f74fbeefbf00b9c2c261550062b07d4e61335 scripts/run_flow_hlstock.py
0c9b45bd4675d1f7177d09741fb1e65888214a9a30f4461f254310f6b45485f3 scripts/run_flow_hl.py
faed14bdef8e4fb302f60f472479fb83088f9108a10a3b94fdb93ce92fcc401d tests/test_run_flow_hlstock.py
4b255a4da93acc25eacd06ed19659118485802577efbe2ccc97cca353d539a1f lab/slices.py
66ac88bdf3034e11401d18e1dac09e7379d59cbb0654332e4d1458200fca0a27 lab/engine.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 lab/stats.py
af7b1a0fbf99471720f765ece0b16734b88247aa84feb7f21137103500d983ea experiments/venue_gap_v1/results/tradfi_symbols.json
e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926 docs/GATES.md
```

Gate 0's input files (they stay out of git as lane data; the forward runs check the block above):

```inputs-gate0
d0e27596a4a59060ca91188144d62532a98b7b4e087e8f46658c08ef462c86cf experiments/flow_hlstock_v1/data/r200_signals.csv
28b4db0f1b2dbbe3a53055be7c55e16c38e8843695cf154bc7c791ded1252885 experiments/flow_hlstock_v1/data/xyz_BRENTOIL.csv
c93c7317cf0bb27b13a1c56f356468327279491c493ae7552f014a5091be1faa experiments/flow_hlstock_v1/data/xyz_CL.csv
27557d6cc2a33fcebd226cc9ef93c883b5a453ba74b88c9020d9e4ddd092ea2d experiments/flow_hlstock_v1/data/xyz_CRCL.csv
a99b906f827a12b7a479020dd2be39d73c34f374f6c55700595460610f57c862 experiments/flow_hlstock_v1/data/xyz_DRAM.csv
11dbd4493a89e978a0cfb5ceadc6ada161f2afb9568b3bb16eda4c835412f7c1 experiments/flow_hlstock_v1/data/xyz_EWY.csv
c6d27b6ef76c7722ef25ac27b8f348181e6407744fb45399399ecf53c5d18f7f experiments/flow_hlstock_v1/data/xyz_GOLD.csv
19c927024d1a9d341fdc9d7775474535c27df548cfbe7e2ad90b5d6152aeca1f experiments/flow_hlstock_v1/data/xyz_GOOGL.csv
ea6c34c40828a9305f711793d1ce349a0c447fa22c6910f7d52a7072fe41995f experiments/flow_hlstock_v1/data/xyz_INTC.csv
9534e4d76b9e65e4147c9dd3b18f295b951af7340cd6abc4d133cc49e586b257 experiments/flow_hlstock_v1/data/xyz_KORU.csv
702d01971850dc39b599d66dab5788a8d6973956f71c12fd85de410c140a38a7 experiments/flow_hlstock_v1/data/xyz_MSTR.csv
e40a3be17da1e23ff740532f526792333b55b1ce5c4aa32569c2d1bf5cecdc5a experiments/flow_hlstock_v1/data/xyz_MU.csv
239624d8f5019d9276833a6a740dd69d95915185665790a004df207beea826c8 experiments/flow_hlstock_v1/data/xyz_NVDA.csv
a1ad12f742e05db09ae79aac3e4ce18c353af690e440262dd191b1396ca8e0ca experiments/flow_hlstock_v1/data/xyz_SILVER.csv
5782f676e24bfc1eaecceee5375c5a04b90716d09a16517997f2083c18527f43 experiments/flow_hlstock_v1/data/xyz_SKHY.csv
66913619ea03b415c6da9fb510aa0c41f0ceca4b184e15bd7be1c60a20aa41bc experiments/flow_hlstock_v1/data/xyz_SMSN.csv
12e16d313b9b5feb1786ab8c87ec426c9d7051f166c64b0dae203249d79bf669 experiments/flow_hlstock_v1/data/xyz_SNDK.csv
4bfb8730251a7b0ad89c45ba3eb81048e6dfd7e746fbef254153ca840c9cc98d experiments/flow_hlstock_v1/data/xyz_SNXX.csv
603159ba4866ea241796f2cfee99319dc9f287004370849b806b4303c1cbde75 experiments/flow_hlstock_v1/data/xyz_SOXL.csv
e7fcd7fef3de46bcf4d89690729eca1d717c9d28ec9a073df2c2b0e236a9e0ba experiments/flow_hlstock_v1/data/xyz_SP500.csv
9a2bd9ef935db3ba9195791ba17f0eecc4d523963f224189acd48c4e311ddd3d experiments/flow_hlstock_v1/data/xyz_SPCX.csv
247421d321e6944c9bf499240d4c2a68c32a021abbfa2b7f13afbb86ada8e501 experiments/flow_hlstock_v1/data/xyz_TSLA.csv
3270b0d080e7489f9b04805f32ecf12ea14aef691b13f513b680c2f93b28aa39 experiments/flow_hlstock_v1/data/xyz_coins.json
```
