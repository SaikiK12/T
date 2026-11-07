# PREREG: boroslock_v1, does a Boros funding-rate lock deliver the APR it locked?

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R412
- **Owner (single writer):** Claude (session claude/yo-9a1k5w); claimed on #7, comment 6674170087
- **Date registered (UTC):** 2026-11-06
- **Method:** M480 (`docs/IMPROVEMENTS_20261105.md`, item 97)

## Question
On matured Boros (Pendle) BTC and ETH funding-rate markets on Binance and Hyperliquid, 2025-08 to 2026-09, did a lock
taken at the best bid deliver the APR it locked?
- **The lock:** short the venue's perp (receive its funding) and sell YU on Boros at the best bid (pay Boros's
  floating rate, receive the fixed bid). Held to maturity.
- **Why it can be exact:** if Boros's floating settlements equal the venue's funding, the two funding legs cancel and
  the position earns the bid minus Boros's fees, whatever funding does. The audit measures how far that held.
- **Why now:** the owner asked for a gain that is fixed and controlled, not chased. This is the first check that the
  instrument does what it says, before any forward paper lane (R413).

This is a measurement: 0 trials, no trade, no order.

## What was seen before this freeze (gate 1)
- **Format only:** three settlement records, one hourly market-data record of market 2, and the market config fields
  (fees, payment period). No venue funding was compared with them.
- **Live quotes** on 2026-11-06 01:40 UTC from the open API (not historical outcomes): BTC on Hyperliquid 8.4-8.7%,
  Binance 6.2-6.9%; the 3-month T-bill 4.03%.
- **Plumbing, counts only** (`plumbing.log`):
  - 551 Boros files match their recorded hashes.
  - Binance: 26 markets, 5,537 settlements, 1,613 entry days.
  - Hyperliquid: 41 markets, 48,144 settlements, 1,637 entry days.
- **Market list coverage:** the API lists 242 markets with ids 2 to 243, matured ones included; only id 1 is absent.

## Data
- **Boros:** `data/boros/markets.json` and `data/boros/hist/{settlement,market-data}/<id>-<symbol>/<YYYY-MM>.ndjson.zip`,
  written by `scripts/fetch_boros_history.py` on 2026-11-06 from the public `api-boros.pendle.finance` market list and
  `historical-data.boros.finance`. Every file's sha256 is in `docs/provenance/boros_hist.json`; the runner checks all
  of them.
  - settlement: timestamp, settlementApr (the annualized rate Boros settled), per event.
  - market-data: hourly snapshot with bestBid, bestAsk, notionalOI.
- **Venue funding:**
  - Binance: `data/fundingRate/{BTC,ETH}USDT.parquet` (rate per interval, interval_h); to 2026-10-01.
  - Hyperliquid: `data/hyperliquid/funding/{BTC,ETH}.parquet` (hourly rate); to 2026-10-20.
  - Rows before 2025-07-01 are never read (load filter), so no 2020 row is read.
- **T-bill:** `data/macro/ust_3m.parquet` (%), the last value at or before the entry.
- **Scope:** non-spread markets whose venue is Binance or Hyperliquid, underlying BTC or ETH, and whose maturity the
  venue funding data covers. Both Hyperliquid collateral variants are kept (they are separate markets).

## Measures
- **Oracle pairing.** Each Boros settlement is paired with the latest venue funding event in the 10 minutes before it.
  The venue APR is rate × 8760 / interval hours.
  - A first settlement at exactly 0 APR is the listing event and is left out.
  - **Coverage:** the share of venue funding events in a market's life (after its first settlement, up to maturity)
    that have a Boros settlement within 10 minutes after them.
  - **Agreement:** |settlementApr − venue APR| per paired settlement, in bp APR.
- **Entries.** Each day at 04:00 UTC with a non-null best bid and at least 7 days to maturity T. With τ = (T − t0) / 365 d:
  - locked = bestBid − takerFee − settleFeeRate (each market's own config, both as APR);
  - V = Σ venue funding (per-period rates) at events in [t0, T];
  - B = Σ settlementApr × paymentPeriod / 365 d over Boros settlements in (t0, T + 10 min];
  - **fidelity** = (V − B) / τ, and **realized** = locked + fidelity.
  - naked = V / τ: the short perp's funding without the lock.
- **Economics (described, not decided on):**
  - locked − T-bill: mean, median, share > 0 and share ≥ 1%/yr;
  - naked − locked: what locking gave up or saved, ex post;
  - an indicative carry = bestBid − m × Boros fees − m × 0.30% / τ − T-bill, for m = 1, 2, 3. The 0.30% is a stated
    spot and perp round trip at Binance VIP0 taker (2 × (10 + 5) bp), not a measured cost;
  - the median bid-ask spread and open interest at entry, by coin, and by month of entry.

## Decision (per venue, both coins and all markets pooled)
- **LOCK_HOLDS** needs all four:
  1. venue funding events with a Boros settlement ≥ 99%;
  2. paired settlements within 1 bp APR of the venue ≥ 99%;
  3. median |fidelity| ≤ 10 bp APR;
  4. 95th percentile |fidelity| ≤ 50 bp APR.
- **Otherwise LOCK_DEVIATES**, with the failing check and its cause reported.
- **Trials:** 0. Read against `registry.program_trials('registry/rounds.csv')` only as context: no return is tested.
- **A LOCK_HOLDS earns only a forward paper lane** (R413) on live quotes. It is not a real-money step.

## Known limits (stated now)
- **Size at the bid is unknown:** the snapshot gives the best bid, not its depth. The forward lane must record depth.
- **Not measured:**
  - the spot and perp legs' fees, their entry and exit basis, and the perp's liquidation risk;
  - Boros and perp margin: the capital is larger than the notional, so return on capital is below the locked APR;
  - smart-contract, oracle-governance and venue risk, and access from the owner's jurisdiction.
- **Funding timing:** a perp opened at 04:00:00 is assumed to receive Hyperliquid's 04:00 funding, as the Boros
  position receives its 04:00 settlement. Both legs use the same events, so the fidelity does not depend on it.
- **Overlapping entries:** daily entries into the same market share most of their settlements, and markets with the
  same maturity share the same funding. The quantiles describe them; they are not independent draws.
- **A short window:** 14 months, one funding regime per coin and venue.

## Inputs frozen with this file
```inputs
f6a040e5f7c8611cee81ec43486d55375503bb8fe87d1ec22f057b689abaad26  scripts/run_boroslock.py
205d33a842725e9129cb653a032e9c6c6e2fcbfe880ddd25fc6cad5beaffe30c  scripts/fetch_boros_history.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
867afdaf22364dcaf420e8e0719109f1d5f9aa91fa267d3d9a79e0fc72e0757c  tests/test_run_boroslock.py
30efe2b54ecb9f93bc2a3c628262cbf883ba6c53a7fce8eabe9351be734db5c5  docs/provenance/boros_hist.json
227ebefc6399acc1275903be19fd82c83cd3fb077ee6677a4fabf3cbc3207c12  data/boros/markets.json
b1cb8c15d60cc2495a8215e9c081e196c069ebf9a324f0e164a69ebdf2536ae3  data/fundingRate/BTCUSDT.parquet
3b640724ed7ed8985b3b8ce41d5ffb6b3eaea7a6b399389ee50ceb91ef2b2e89  data/fundingRate/ETHUSDT.parquet
4926bbad8b61773dbc71317efe86a7009d4e15a4282dd04cfc9fb1db285fa5da  data/hyperliquid/funding/BTC.parquet
98d3d057f10bca0d85fb891bf5d302d7fd414ea0608f67897e49d955dc41f325  data/hyperliquid/funding/ETH.parquet
bd9fc2ab8a3bb35d1b669f135083e679dc9cebfbbe46544531446af66f108bdd  data/macro/ust_3m.parquet
```
