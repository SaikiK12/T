# Perp-vault per-coin inventory: the free archive that unblocks M510/M511 gate-0 (intake, 2026-11-14)

Owner asked for work that improves results. A read-only research subagent (S3) probed the HLP/LLP vault APIs and the
public archives on 2026-11-14. This page records what it found, what it verified, and the one decision it needs. It
feeds M510 (`hlpinv_v1`, R454) and M511 (`llpinv_v1`, R455). It is not evidence of a return and no backtest was run.

**Labels:** [A] author re-checked; [V] read on the fetched page by the helper; [S] snippet only; [U] not read.

## The claim
The venue APIs keep **no per-coin inventory history** — HLP `userFills` caps at 2000 rows (about 21 min for an
active child) and `userFillsByTime` with any older `startTime` returns 0; Lighter `aggregatedTrades` retains about
two weeks. So R454/R455 can only run **forward** from 2026-11-12. **[V]**

But the history **is** in the free **AWS Public Blockchain** archive, keyless:
- HLP: `hyperliquid/mainnet/node_fills_by_block/hourly/YYYYMMDD/HH.lz4` (LZ4 JSON-lines), **2025-07-27 .. 2026-11-13**,
  ~1 GB/day compressed. Per-coin open interest: `hyperliquid/mainnet/asset_ctxs/YYYYMMDD.csv.lz4`, 2023-05-20+.
- LLP: `lighter/core/mainnet/trades/date=YYYY-MM-DD/trades.parquet`, **2025-01-17 .. 2026-11-12** (per-market
  inventory usable from **2025-05-02**, when `*_position_size_before` stops being null). Hourly OI:
  `lighter/core/mainnet/open_interest_hourly/...`.

## What was verified [A]
- HLP: chaining `startPosition + side*sz` in file order for child `0x010461...` on 2026-11-12 12:00 gave **0
  mismatches over 5,537 steps**.
- LLP: chaining `position_size_before + (bid?+size:-size)` sorted by trade `id` gave **0 mismatches** on 3 days
  (2026-10-15, 2026-03-15, 2026-11-12).
- Live snapshot endpoints work keyless for both venues; they give current positions only.

## The blocker (owner-only)
A full pull is a **large download** and needs the owner's explicit yes (AGENTS.md hard rule 5): LLP tens of GB over
18 months; HLP about **470 GB**. No pull was made. Without it, M510/M511 stay forward-only (R454/R455 unchanged).
With it, each lane gets a gate-0 backtest of about 15.5 (HLP) / 18 (LLP) months, ~1.3-1.5x longer than the 365-day
forward look, so strictly better powered (detectable annual Sharpe about 2.5 / 2.3 at 80% power).

## Honest limits [V]
- **HLP survivorship:** the child-vault list is **undated**; a child added later is missing from early history, so
  early inventory may be undercounted. Unquantified.
- **Reflexivity:** the vault is a large part of its venue's liquidity and can move the price it would predict;
  capacity is small exactly where a cross-sectional book trades. LLP BTC share measured about -0.008% (negligible),
  but large in small markets.
- **Units:** Lighter parquet `size`/`price` are scaled ints (BTC 1e6 / 1e5); scaling may vary per market and must be
  calibrated or the inventory share is wrong by orders of magnitude.
- **Analogy only:** the cited market-microstructure literature (Ho-Stoll 1981; Amihud-Mendelson 1980;
  Grossman-Miller 1988; Evans-Lyons 2002) is equities/FX, not crypto perps. The repo's own dealer-flow family
  (R292 `dealerflow_v1`, M308) was NULL, so this is a lead, not a prior.

## Sources
READ: `registry/{methods,rounds}.csv` (M510, M511, M536, M505; R454, R455, R456, R484, R446, R292);
`experiments/{hlpinv_v1,llpinv_v1}/{PREREG,README}.md`; `research/intake/hlp_llp_lit_20261113.md`;
`docs/AUCTION_AND_FLOW.md`; `registry/data_manifest.csv`; live keyless probes of `api.hyperliquid.xyz/info` and
`mainnet.zklighter.elliot.ai/api/v1/*`; AWS archive schemas + sample validation.
UNREAD: vault `journal/` (absent); full HLP fills archive (sampled only); Lighter `export` (auth-gated, not called).
