# HFT and crypto-microstructure corpus (owner upload, 2026-10-28)

An index of 46 sources the owner uploaded as `hft_crypto_microstructure_research_corpus.md`. It is an index, not a
copy of any work. The machine record is [`source_catalog_hft_20261028.csv`](source_catalog_hft_20261028.csv)
(ids `SRC28-001` to `SRC28-046`, same columns as the other catalogs plus `claim_type`, `ingest_order`, `pages`).
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
