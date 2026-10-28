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
| 125 million fills show touch-joining passive fills lose 0.39, 0.84 and 0.46 bp at 10 s on Binance, Bybit and Hyperliquid (September 2026) | Several searches, standard and extended | No source found. Related, from summaries only: arXiv 2502.18625 (live Binance, 232,897 minimum maker orders) and arXiv 2608.18195 (about half a tick at the best price in a simulation) | Not used as a number. Kept as a design hurdle in M433: beat a touch-join baseline estimated from our own tape |
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
