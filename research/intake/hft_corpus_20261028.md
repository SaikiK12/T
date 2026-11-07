# HFT and crypto-microstructure corpus (owner upload, 2026-10-28)

An index of 46 sources the owner uploaded as `hft_crypto_microstructure_research_corpus.md`. It is an index, not a
copy of any work. The machine record is [`source_catalog_hft_20261028.csv`](source_catalog_hft_20261028.csv)
(ids `SRC28-001` to `SRC28-046`, same columns as the other catalogs plus `claim_type`, `ingest_order`, `pages`).
Ids `SRC28-047` to `SRC28-054` are not corpus entries: they are what the targeted check of the owner's second pasted
review turned up (see the addendum at the end).
This page holds what a CSV cell cannot: exact read scope, what the fetched pages changed, and why the work order is
what it is. It is evidence, not a second queue; the live queue is `registry/methods.csv`.

## Exact read scope

| Scope | Count | Which |
|---|---|---|
| Index entry only (title, authors, page count, one-line use); text not opened | 37 | All eight books (2,760 pp), all other papers, the Binance market-data/stream docs, the Binance archive, the Bybit orderbook doc, Hyperliquid latency, Linux timestamping, both SSRN crypto papers |
| Index entry plus one bounded page fetch on 2026-10-28, fixed questions only | 7 | Binance RPI FAQ, Bybit RPI orderbook, Bybit create-order, Bybit all-liquidation, OKX changelog, OKX historical data, Hyperliquid historical data |
| Index entry plus the public abstract page | 2 | Zhai (arXiv 2608.04373), Albers et al. (Oxford repository) |

- Two SSRN pages (7370002, 7415499) answered HTTP 403, so even their abstracts were not seen.
- The OKX changelog fetch covered the first 100,000 of 594,918 characters. The corpus mentions low-latency-channel
  changes; none appeared in that portion, so it stays unconfirmed.
- No book or paper body was read. No equation, effect size or result from any of them is used anywhere in this
  project yet. The known pages sum to 3,347 (checked from the catalog); the 2,760 for the core books is the same sum.

## Claim labels

Every catalog row carries one of the four labels the corpus asks for: `published result`, `working-paper result`,
`exchange rule`, `new hypothesis`. They follow the kind of link the owner listed (journal or book, preprint or
repository, venue documentation). The Linux kernel page is platform documentation and is labelled `exchange rule`
for want of a fifth label. Whether a listed preprint was later published was not checked, except Albers et al., whose
repository page gives *Quantitative Finance* 25(6), 919-947 (24 June 2025). A `new hypothesis` appears only in a queue
row (M434, M435), never as a catalog label, because nothing here has been tested.

## What the fetched pages changed

| Fact (page, 2026-10-28) | Effect |
|---|---|
| Binance RPI: matches only non-algorithmic orders, never API orders; fills last at its price level; excluded from API depth and book-ticker streams; trades flagged `IsRPITrade`; selected USD-M symbols (`PermissionSets` has RPI); extra RPI commission | M432 stated these as unconfirmed; now sourced. An API taker cannot hit RPI size, so M433's fill model must exclude it |
| Bybit: `rpiTakerAccess=true` lets Market or Limit IOC/FOK orders match RPI quotes; RPI time-in-force is for assigned market makers | The two venues differ, so a cross-venue simulator needs a rule per venue |
| Bybit `orderbook.rpi.{symbol}`: level 50 at 100 ms, price plus non-RPI size plus RPI size | Not recorded today; Binance `rpiDepth` is the only RPI-inclusive book on the raw tape |
| Bybit `allLiquidation.{symbol}`: 500 ms push; USDT, USDC and inverse contracts; fields `T s S v p`; `S=Buy` means a long was liquidated | New M435; no history exists to backfill, so `scripts/record_raw.py` now records BTC and ETH (`liq` rows) |
| OKX changelog: `bbo-rpi-tbt` channel added 2026-10-27; ELP renamed RPI and `books-rpi` with `seqId/prevSeqId` on 2026-07-28; checksum deprecated 2026-06-23 | OKX websockets still reset from this container; nothing recorded |
| OKX historical page: trades from Sep 2021, candles Jul 2023, funding Mar 2022, "high-resolution L2" from Mar 2023; book granularity and cost not stated | Candidate venue for replicating a surviving mechanism; a download needs the owner's yes (rule 5) |
| Hyperliquid historical page: `l2Book` snapshots and asset contexts in `hyperliquid-archive`, fills in `hl-mainnet-node-data`; requester pays transfer; about monthly uploads, no timeliness guarantee, possible gaps | Not a free route: another transfer decision for the owner, separate from the dropped Zenodo archive |
| Zhai (arXiv, 40 pp, v3 23 Aug 2026): wallet informativeness persists; informative wallets improve out-of-sample one-second return prediction. The abstract names "a decentralized exchange", not Hyperliquid | Supports M429's question; the Hyperliquid link is unconfirmed |
| Albers et al.: live market orders fill worse than the book implies; marketable limits can fail to fill; abstract gives no magnitudes | Read the body before trusting any fill simulator |

## Queue changes

- Added M434 (quote-currency fair value, features for M430) and M435 (forced-liquidation flow, now recording). Both are untested hypotheses with their own falsification paths in the row notes.
- Extended the M430, M431, M432 and M433 notes with the fetched facts above. No alias rows: these are catalog
  entries, not source-method records. No trials were added and no market data was read.

## Order of work

The pasted ranking was M434, M435, M430, M431, replication of any survivor on OKX historical L2, M433, ML last.
It is kept as the dependency order of the experiments. The working order differs on one point, set by what cannot be
recovered later:

1. Record what has no history: M435's liquidation feed, done (recording since 2026-10-28 21:03 UTC; a 100 s probe saw
   no BTC or ETH print, so the payload shape is the documented one, unconfirmed). M434 needs nothing new, because the
   implied USDC/USDT rate comes from books already on the raw tape.
2. Freeze one M430 PREREG after at least 3 recorded windows, with M434's features declared in advance and power taken
   from hourly blocks (roughly 4 a day at 4 h of tape). No outcome is read before that.
3. M431 for any M430 survivor, against the measured round trip (about 250 ms through the agent proxy).
4. Replicate a survivor on OKX historical L2 (the owner's yes for the download). Then M433. Machine learning only
   after the simple baselines (OFI, micro-price, queue imbalance) show positive net value out of sample.

R367 stays as registered. Its 100 ms stale-quote screen runs once on or after 2026-11-02 and does not decide the
rest of this family either way.

## Earning an experiment

Reading a paper does not earn a strategy. A source earns one finite experiment only when a card
([`templates/research_card.md`](../../templates/research_card.md)) names a mechanism, inputs observable with our data,
a causal decision timestamp and a falsification condition. Until a source is actually read, its catalog row says
index only and no card exists.

## Addendum: targeted check of the second pasted review (2026-10-28)

The owner's second paste argued for targeted research only (living venue facts, frontier-paper watch, own empirical
work) and gave several specific claims. Each was checked once, with bounded searches or one page fetch. A search
summary is the search tool's own digest of results; no paper body was opened. "Not found" means these searches did not
surface it; it does not show the claim is false.

| Pasted claim | What was run | Outcome | Use in the repo |
|---|---|---|---|
| Binance counts quick cancels against API traders (invalid-cancellation rule) | Fetched the quantitative-rules FAQ (page dated 2026-08-31) | Confirmed. Orders cancelled under 5 s count as invalid; ban at a ratio of 0.99 with at least 5,000 such orders in a 10-minute cycle per symbol (SRC28-047) | M427 and M433 notes: count our own sub-5 s cancels; it does not bind at probe scale |
| Binance liquidity-provider thresholds of $100M futures and $20M spot | Searched, and read the FAQ's exemption criteria | Not confirmed. The FAQ's exemption is a different test (above 25,000,000,000 USD of 30-day futures volume, or the liquidity-provider or options-market-maker programs) | Not used |
| 125 million fills show touch-joining passive fills lose 0.39, 0.84 and 0.46 bp at 10 s on Binance, Bybit and Hyperliquid (September 2026) | Several searches, standard and extended; later a targeted search | First pass: no source found (wrong, see next). Later pass found Gatto, SSRN 7461901 (SRC28-057): about 125.8 million simulated last-in-queue fills with 10 s pre-fee markouts of -0.839 bp (Bybit), -0.391 (Binance), -0.458 (Hyperliquid), entry leg only; seen in search results only, the SSRN page answers 403 so the body was not read. Simulated and last-in-queue, so a pessimistic bound for joining the back of the queue, not real fills. Also from summaries only: arXiv 2502.18625 (live Binance, 232,897 minimum maker orders) and arXiv 2608.18195 (about half a tick at the best price in a simulation) | Not used as a hurdle or a number. M433 keeps the design hurdle (beat a touch-join baseline estimated from our own tape) and reports every simulated fill under back-, random- and front-cancel allocations |
| Stanford/Columbia Hyperliquid paper: about $1.11 billion of front-end losses and reversing taker-flow impact | Searches | Not found. Nearest: arXiv 2608.04373 (Zhai) and arXiv 2606.15715 (TWAP orders on Hyperliquid) | Not used |
| Ten wallets cause 90.5% of maker adverse-selection loss in an on-chain options book | Searches | Not found. A summary of a 2026 wallet-markout paper (probably Zhai) reports 86.9% of 2,314 active aggressive wallets trading again in the next ten days: persistence, not concentration of maker loss | Not used. The wallet-by-side-by-size-by-state idea is a hypothesis in M429's note |
| Binance leads Hyperliquid for BTC at 2, 5 and 10 s | Searches | Direction supported by two sources (Research Square rs-10147582 on a 5 s grid; Arrakis about 800 ms). The 2, 5 and 10 s figures were not found | Leads only (SRC28-053, 054). A 5 s grid cannot say anything about a sub-second lead |
| August 2026 multi-quote price-discovery paper | Not searched again in this pass; SSRN 7370002 in the corpus answered 403 | Unchanged | M434 keeps it as an unseen prior |

What this changed in the queue: M427, M429 and M433 notes only. No new method id and no trial was added: the pasted
research tree (M434, M435, raw best-bid-and-offer price discovery, probability of the target transition before a
reversal, markout given a hypothetical fill, toxicity stand-down, delay value, realistic maker execution, machine
learning last) is the dependency order already set out above, with M430 as the transition-probability label. The one
addition is a reporting rule for M430 and M433: a hypothetical fill (R367's strict trade-through rule) is reported
next to the touch-join baseline at the same moments, so a filter that only selects less toxic touches is not read as
alpha. The suggested effort split (about 70% own data, 20% targeted web, 10% infrastructure) is a rough guide, not a rule.

## Addendum 2026-10-28 (third owner paste): Kraken, RPI, phase

New rows M436 (Bybit RPI toxicity), M437 (Kraken order-event queue laboratory), M438 (intra-second phase, declared
before any outcome) and M439 (Kraken execution economics). Sources `SRC28-055` to `SRC28-059` hold the exact scope.
What was run, and what it supports:

- Kraken's public History v3 order and execution events: no key, retention probed to 2022-03-22 on PF_XBTUSD and
  PF_ETHUSD with 3-event requests; one 120 s PF_XBTUSD window (48,174 events, 204 executions) joined cleanly: every
  execution matched a maker-order fill update within 3 ms and no uid was duplicated. Open points are in M437
  (same-millisecond ties, a starting state for an order-level book, gaps at depth). Nothing larger was downloaded.
- Kraken's public fee schedule: 2 bp maker and 5 bp taker at the base tier, -1 bp maker only at 1 billion dollars of
  volume on the schedule used by the stablecoin perps. Those perps (PF_USDTUSD, PF_USDCUSD) traded 2,283 and 5,206
  dollars in 24 h in one snapshot, so the apparent -1 bp is not an earnable rebate.
- Bybit RPI: RPI size exists on spot majors and on BTCPERP and ETHPERP, not on the linear USDT perps; no RPI-flagged
  trade in a 45 s run. OKX's RPI channels were probed once and the connection was reset; not retried.
- Priority order the owner's review asks for: Kraken queue laboratory first, then USDC/USDT, forced flow
  (continuation versus exhaustion), RPI toxicity, touch transition, latency frontier, intra-second phase; M433 stays
  blocked until something survives. The recorder now holds the data for all but the Kraken order events.

## Addendum 2026-10-28 (fourth owner paste): option expiry, Lighter WTI identity, EIA, WASDE, 0DTE

New rows M440-M446. The paste numbered its branches M439-M445; the repo ids are the next free ones, and each row's note
carries the paste's number. Mapping: option expiry = M440 (paste M444); Lighter participant identity = M441
(paste M445); weekend WTI direction = M442 (paste M442, downgraded: status N/A, superseded by M443); WTI cross-venue
residual = M443 (paste M441); EIA natural gas and crude = M444 (paste M439 and M440, one row); USDA wheat = M445
(paste M443, blocked on consensus data); 0DTE SPX to ES = M446 (blocked on OPRA). Sources `SRC28-060` and
`SRC28-061` hold the live checks. What was run:

- Two forward recorders started on 2026-10-28, both public and paper only: `scripts/record_option_expiry.py` (BTC
  option chain once a minute, 06:45-10:15 UTC, from 2026-10-29) and `scripts/record_lighter_trades.py` (WTI, NATGAS,
  BRENTOIL trades with both account ids, from 22:29 UTC). Neither computes a statistic. The first option-expiry
  window is 2026-10-29; 2026-10-30 08:00 UTC is a monthly expiry (34% of 397,715 BTC option open interest in one
  chain snapshot), the largest size test the recorder will see this week.
- Lighter's public trade stream carries the account ids, the maker side, each side's position, entry value and margin
  before the fill, and a per-side fee integer; observed fees are 0.28-2.66 bp by account and 1% on liquidations, and the
  market listing shows 0.0000, so the pasted "about 2 bp maker, 5 bp taker" is not what the stream shows. The
  markout `side * 1e4 * ln(mid(t+h) / price)` and a past-only per-account EWMA are offline analysis, not recorder code.
- Kraken lists PF_WTIOILUSD, PF_NATGASUSD and PF_BRENTOILUSD, but `record_raw.py` stores prices in hundredths and
  cannot hold their 0.001 and 0.0001 ticks without a per-product scale; not recorded yet.
- Deribit serves the current chain only (no open-interest history), so the M440 state variable (expiring ATM open
  interest over total BTC open interest) exists only from the first recorded snapshot. The summary carries no Greeks;
  they are computed offline. Dealer gamma is not inferred from open interest times gamma. Earlier Friday-only
  open-interest and charm tests (R289, R296; M303, M309, M317) were NULL; M440 differs in covering every expiry and
  in conditioning on the expiring share.

Reported in the paste and still not read or checked: the 1,224-settlement study (volatility jump is time-of-day
seasonality), the September 2026 partial match, the HIP-3 oracle and TradeXYZ pricing-band mechanics, the 0DTE
gamma-conditioned paper, the leveraged-ETF closing-momentum and Treasury-auction papers, and the negative after-cost
evidence behind the weekend-WTI downgrade. M442 carries that evidence label. The Energy Journal study, the EIA
schedules, the 2026 liquidity-paper abstract and the current Estimize page/documentation are now boundedly checked in
the M444 addendum below. Historical CME futures, OPRA and point-in-time consensus data are not held. Power for M440
(sigma 80 bp, effect 15 bp, about 220 expiry days) is an assumption, not a measurement.

## Addendum 2026-10-28 (fifth owner paste): event mechanisms in place of generic chart rules

Four more reviews, ending "Now WE need to produce edges data pnl". They recommend structural mechanisms (EIA crude and
natural-gas second-stage drift, USDA wheat, 24/7 WTI venue disagreement and its re-anchoring at the CME reopen, the
CME-reopen convergence of index and gold perps, 0DTE flow, an MNQ noise-band replication, FX after macro releases,
conditional dealer-gamma closing momentum, cross-venue funding carry on tokenised assets) and prop-firm wrappers as
arithmetic, and say to kill generic ORB, RSI, MACD and OHLCV rules. Queue: M444, M443, M321, M445, M446 updated; new
rows M447-M453 (reopen re-anchoring, MNQ replication, RWA funding carry, FX second stage, gamma closing momentum,
prop-wrapper arithmetic, Databento MBO slices). Sources `SRC28-062` to `SRC28-064` hold the live checks and the EIA
schedules. What was run:

- **Data.** `scripts/record_commodity_perps.py` (daemon since 2026-10-28 23:56 UTC) records Hyperliquid xyz, Kraken and
  Binance commodity and index perps at tick level, 24/7. `scripts/fetch_tradfi_perps.py` fetched Binance's TradFi perp
  one-minute archive from 2026-04-01 (published SHA-256 checked per file; `docs/provenance/tradfi_perps.json`).
- **One lane, R368 `eventdrift_v1`** (M444's cheap form): continuation of the first minute after 60 EIA releases on
  CLUSDT and NATGASUSDT, frozen before any return was read. **NULL, underpowered** (26 trials): crude after a falling
  first minute reversed by 8.1 bp over five minutes (14 events), gas storage moved -0.1 bp (29 events), against a 12 bp
  round trip and a minimum detectable size of 15.6 and 20.5 bp. No cell paid a taker cost. See
  `experiments/eventdrift_v1/FINDINGS.md`.
- **A second lane, R369 `eventlag_fwd`** (M444/M443's tick-level form), frozen before the first release it scores: a forward paper lane that, at each of 19 EIA
  releases to 2026-12-31, tests whether Lighter's displayed quote lags a 20 bp (gas) or 8 bp (crude) jump on Binance or Hyperliquid and whether a taker
  there earns the catch-up by T + 60 s. 24 trials counted, first read when each type has 8 valid events (about 2026-12-23). Nothing is traded.
- **Not run, by rule.** The JFE crude result, a 0DTE paper, a NY Fed replication that is reported to have killed the
  ES European-open drift, the prop-firm rules and fee schedules, and a Databento credit were reported in review and
  remain unread or unverified. The Energy Journal gas paper is now boundedly read below; its separate 2026 SSRN
  liquidity abstract is abstract-only. The review's suggested allocation (about 35%
  crypto microstructure, 30% CME events, 25% 24/7 TradFi perps, 10% replication and prop) is the author's, not a
  measurement. The review's "next five registrations" (EIA petroleum, EIA gas, WTI cross-venue residual, WTI
  re-anchoring, USDA wheat) map to M444 (R368 for the cheap form), M443 and M447, with wheat blocked on data (M445).
- **Owner decisions this leaves.** Databento (account and key, M453) and CME minute data for M448/M450; a check of
  Binance, Kraken and Hyperliquid availability and fees for a French resident before any calibration order; whether
  the 20-release forward replication of R368 (about five months) is worth waiting for or the budget goes to order-book
  data now.

## Targeted 2026-10-29 source check for M444 (four new sources; no new trial)

This source-only pass adds catalog rows `SRC28-065`–`SRC28-068` and cards for them. It also records a bounded read of
the already-catalogued official schedule source `SRC28-064`. The accepted 2021 Energy Journal manuscript was read in
sections II, III.A–B, IV, V.C and VI, plus Table 8 and Table A.3; the rest of its appendix was not read. Dani's 2026
SSRN paper was read at abstract scope only. The official EIA schedule tables, one public Estimize WK43 page captured
before release, and Estimize's public data dictionary were checked. No trial, new statistic, market outcome or data
acquisition was run for this pass.

The 2021 paper's “more than half” headline is the share of the full-sample annualized NG return associated with
announcement days in 2003–2018; it is not evidence of a current positive long edge. The sample has 699 gas-report
days. Table A.3 shows no announcement/non-announcement mean difference in 2014–2018 (−0.05% versus −0.14%,
`p=0.642`). The paper's short-before/cover-after strategy earns 12.01% annualized after bid/ask and full overnight
funding costs across the full sample, but −0.97% in its post-2011 sample (Sharpe −0.17, `p=0.843`). The historical
inputs are Bloomberg and Thomson Reuters Tick History; the implementation does not model modern queue position,
latency or market impact. These results argue against copying its old rule into a current perp.

The 2026 liquidity-paper abstract reports five-minute near-mid depth depletion after 29 petroleum and 31 gas releases,
but its four controls per release were not Wednesdays or Thursdays. The abstract therefore cannot separate release
effects from the 10:30 weekday clock, and does not establish a profitable event entry. Full methods, results and data
remain unread. EIA confirms the usual Thursday 10:30 Eastern gas schedule and Wednesday 10:30 Eastern petroleum
schedule, with listed holiday exceptions; the 2026-10-29 gas event converts to 14:30 UTC and the next petroleum
event on 2026-11-04 converts to 15:30 UTC after the US clock change.

At approximately 00:20 UTC, Estimize's public WK43 page displayed nine estimates and consensus 58.06 before the
scheduled release. Its rendered page did not expose the indicator unit, so this is not yet a validated Bcf surprise
input. The data dictionary describes point-in-time consensus snapshots and API/history access, but no historical
Bloomberg forecast vintage or licensed Estimize history is held. The existing repo record says R368's cheap
minute-bar continuation form is NULL and underpowered; R369 is already frozen as Claude's forward tick-level paper
lane. This pass leaves M444 PARTIAL, adds zero trials, and changes neither round nor lane. In this checkout there is
no local market-data directory, and `docs/PANEL.md` still marks the R369 receipt UNKNOWN/UNVERIFIED; the cross-venue
collector's coverage cannot be independently confirmed here.


## Additional M444 consensus snapshot (2026-10-29; no new trial)

Before the scheduled 14:30 UTC gas-storage release, Trading Economics displayed a 75 Bcf survey consensus and a 77 Bcf prior value; actual and its separate TEForecast model field were blank. Its API docs distinguish the consensus Forecast from its own model and require authenticated access for snapshots. Estimize separately displayed 58.06 from nine estimates, but its public page did not expose the indicator unit. The 16.94 displayed-unit difference is not yet a verified forecast disagreement. `SRC28-069` and its card preserve the retrieval time and access boundary. R368 does not use either forecast; R369 is unchanged.
