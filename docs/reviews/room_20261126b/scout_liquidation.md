# Scout: liquidation engines and the vaults that absorb them (2026-11-26)

Family: liquidation engines and vaults (HLP, LLP, ADL). Read-only. No orders, accounts or downloads.

## 0. What the lab already knows

Method rows (registry/methods.csv):
- M285 (line 257): HLP as a yardstick. Notes: "A yardstick, not a rule: the backstop's fills are privileged."
- M265 (line 240): leverage and liquidation check on R275's carry legs. Notes: "mark-based liquidation remains untested."
- M176 (line 177): OI-drop plus wick cascade fade. Tested in R252 (NULL). Notes: "the OI-drop plus wick form is untested" for R206's neighbour; R252 itself is NULL.
- M286 (line 258): post-cascade basket. Tested in R303 (NULL).
- M140 (line 141) and R206 (NULL): Gate liquidation fade, "long cascades continue (long leg gross -2 to -11 bp/day)".
- M153 (line 154) and R193/R194 (NULL): maker entries as HLP-style liquidity provision. Unhedged +31.5%/yr is market beta (R194).
- M177 (line 178): insurance fund / ADL recorder, BLOCKED ("no test for months").
- M051 (line 52): TradFi tracking, BLOCKED (not this family).
- M069, M070, M079, M209: blocked or untested; no liquidator-vault content.
- Rounds R454 (registry/rounds.csv:241), R455 (:242), R456 (:243): HLP and LLP inventory signals, pre-registered on counts only ("Frozen before any HLP size, share or return was read (counts only: 7 child vaults, 354 position rows)"). No verdict yet. R456 cost read: "Hyperliquid tier-0 fee 4.5 bp + $1k slippage".
- R446 (:233) and R447 (:234): HLP and LLP held as deposits; RUNNING, PENDING.
- R280 (registry/rounds.csv, row R280): leverage on carry legs; DATA_PASS; "every book has legs liquidated at 1x under isolated margin".

Data check, run here:
- docs/DATA_SOURCES.md:24 lists `data/hyperliquid/vaults` (HLP vaultDetails). That folder does NOT exist in this checkout (`ls` failed). M285's "held" status is not verified locally.
- `data/hyperliquid/candles_1h` has 235 files; `data/hyperliquid/funding` has 235 files.
- `data/markPriceKlines_1h` exists (Binance mark klines, per DATA_SOURCES.md:35). parquet could not be read here (pyarrow missing), so columns were not checked.
- HLP child-vault position snapshots (scripts/record_hlp_positions.py, from R454) are written to a separate branch, not to this checkout.

Conclusion from the lab rows: cascade and wick proxies on traded prices are dead (R206, R252, R303). Nobody has tested the flow of a takeover itself, or the trigger on mark price. M265 names that gap.

## 1. Primary sources (what the rules say)

Hyperliquid, GitBook wiki (https://hyperliquid-co.gitbook.io/wiki/architecture/hypercore/dex/clearinghouse/liquidations), via WebFetch (a summarising tool; wording should be checked on the page):
- Backstop trigger: "Triggers when account equity drops below 2/3 of maintenance margin".
- Mark price: liquidations use mark price "rather than instantaneous book price for robust liquidation triggers".
- Partial: "Only 20% liquidated initially to avoid overwhelming the order book" (positions over $100K), then "30-second cooldown after partial liquidation".
- Unwind price: not stated in any page I could fetch.
- ADL: "A trader's account value or isolated position value becomes negative, creating potential bad debt." Ranking: "ranked by unrealized PnL and leverage used". Price: "Positions are closed at the previous oracle price against the underwater trader."

Hyperliquid, official docs (https://hyperliquid.gitbook.io/hyperliquid-docs/trading/liquidations.md), via WebFetch:
- "If the account equity drops below 2/3 of the maintenance margin without successful liquidation through the book" starts the backstop.
- "During backstop liquidation, the maintenance margin is not returned to the user."
- No text on ADL or the insurance fund on this page.

Hyperliquid incident log, JELLY, 2025-03-26 (https://hyperliquid-co.gitbook.io/wiki/introduction/roadmap/incident/2025-26-03), via WebFetch:
- "Liquidator vault capped to small percentage of total HLP balance with isolated collateral." (no number)
- "Triggers when Liquidator losses exceed threshold, preventing automatic collateral sharing between component vaults." (no number)
- "All JELLY positions were settled at the opening price of $0.0095, and the pair was delisted."

Lighter docs (https://docs.lighter.xyz/trading/liquidations-and-llp-insurance-fund.md), via WebFetch. This is the page the official site pointed to; the older URL returned 404:
- Full liquidation: "If a user goes below the close-out margin requirement, the LLP closes all of the user's positions."
- Partial: "the liquidation engine first cancels all of the open orders of the user", then IoC sells "at the zero price".
- Fee: "the liquidation engine takes up to 1% liquidation fee and sends it to LLP (insurance fund)."
- Takeover limit: "the LLP takes it over only if doing so would keep the LLP's total account value above the Initial Margin Requirement."
- Takeover order: ascending unrealized PnL. Takeover price and unwind rule: not stated.
- ADL: "the exchange initiates auto-deleveraging (ADL) for the bankrupt account's positions."

Gaps that matter for the question: neither venue states the price at which a vault takes a position, nor how fast it unwinds. That is the one input the forced-flow question needs, and it must be observed, not read.

Note on sources: every quote above came through WebFetch's summary. Before any use in a rule, each must be re-checked byte-for-byte on the page.

## 2. Public API test (run once)

- Endpoint: POST https://api.hyperliquid.xyz/info with `{"type":"userFills","user":"0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"}` (the HLP address the lab's own script uses, scripts/describe_hlp_llp_lit.py).
- Result: HTTP OK, body `[]` (empty list, 2 bytes). So the `liquidation` field on fills could NOT be verified on this address. The endpoint is reachable; the field is untested.
- Saved to scratchpad only (hlp_fills.json).

## 3. Three candidate questions

### Q1. Does a liquidator takeover leave a one-sided flow that a retail trader can fade?
- Hypothesis: when HLP's liquidator child vault takes a large long (or short) in a coin, the price drifts against the vault's exit direction over 1-6 h, because the vault must sell (or buy) into the book.
- Opposite: the vault unwinds through its own market making and other makers absorb it at once. Any drift is already in the first hour, and net of 4.5 bp fee plus $1k slippage (R456) nothing is left.
- Payer and rule: the liquidator vault, by the backstop rule above ("Positions that are below 2/3 of the maintenance margin can be taken over by the liquidator vault"; trigger at 2/3 of maintenance margin).
- Why not known: R454 is an inventory share, pre-registered, counts only, with no verdict. R252 and R303 used traded-price cascade proxies and were NULL, not takeover events. M285 says the backstop's fills are "privileged" and not a rule.
- Data: the HLP position snapshots are on the claims branch (from R454), not local; the candles are local (data/hyperliquid/candles_1h, 235 files). Takeover events would come from snapshot diffs of child-vault net size, from about 2026-11-15 onward. Pre-period: none.
- Cheapest decisive observation: once R454's snapshots reach about 2 weeks, mark hours where one child vault's net size in a coin moves by more than X% of open interest in one hour. Measure the 1-6 h return in the direction of the exit, against random hours in the same coins. Hours: about 2 h of code on existing snapshots; more data needed before a result.
- Kill result: the mean 1-6 h return in the exit direction is not above the random-hour placebo (same coins, same hour of day), or it is below the 4.5 bp fee plus slippage per leg.
- Value for a French owner with about 10k EUR: small. Events are rare and the fee alone is 4.5 bp per leg. It is only worth pursuing as a confirmation of R454, not as a standalone book.
- My probability it is true: 0.15. Market makers in the book would normally take this flow first, and the lab's cascade tests were NULL.

### Q2. Does Lighter's LLP refusal or ADL create a forced seller that a retail trader can take the other side of?
- Hypothesis: when a bankrupt account's positions are ADL'd on Lighter (because LLP cannot take them under the Initial Margin rule), the ADL counterparties and the coin see a one-sided forced close at the bankruptcy price. The price drifts for hours after, in the direction of the ADL.
- Opposite: ADL is rare (see below), so the coins with ADL are illiquid and reverse at once. The forced flow is too small to matter against a whole book.
- Payer and rule: LLP's Initial Margin test ("the LLP takes it over only if doing so would keep the LLP's total account value above the Initial Margin Requirement") and ADL "for the bankrupt account's positions". The payer is the ADL'd winner, not the vault.
- Why not known: M177 (insurance fund / ADL recorder) is BLOCKED, "no test for months". R446 and R447 hold LLP as a deposit, not as a flow signal. R455 (LLP inventory) is pre-registered and counts only.
- Count the chances first: on Hyperliquid, ADL on cross margin fired "for the first time in over two years" (October 2025, secondary source, Substack/wublock; not primary). Lighter's ADL frequency is not in the docs I could read. If Lighter's ADL is also a few events a year, the sample is too small for any test before a multi-year window. That is the kill, unless the frequency is much higher.
- Data: none held for ADL events. Lighter public API exists (data/lighter_hist, data/recorders/lighter_book, hourly from 2026-10-21). ADL fills are not confirmed to be exposed by Lighter's public API; this is untested.
- Cheapest decisive observation: count ADL events on Lighter from the public trade tape in data/lighter_trades (trade/{market}), if the tape marks forced fills. Hours: 1-2 h. If fewer than about 20 events over the held history, stop.
- Kill result: under about 20 events in the held window, or no price effect over 1-24 h against random hours.
- Value for a French owner with about 10k EUR: low. Lighter is reachable, but the event is rare and the ADL'd account is usually a loser's counterparty, so a retail taker would have to be in the right coin at the right minute.
- My probability it is true: 0.05. The events are rare and the lab's cascade tests were NULL.

### Q3. Do liquidations trigger on mark price, so that the cascade test has to use mark rather than traded prices?
- Hypothesis: liquidation triggers are set by mark price, so the forced flow occurs when mark crosses a liquidation cluster, not when a traded wick does. Cascade proxies on traded prices (M176, R252) therefore sit at the wrong moment. Re-timing the same event on mark price gives a cleaner sign.
- Opposite: the traded and mark prices move together in liquidation events (they do on liquid perps), so the timing change is within noise and the earlier NULL is a real NULL.
- Payer and rule: the mark-price trigger. Hyperliquid wiki: liquidations use mark price "rather than instantaneous book price for robust liquidation triggers". Binance mark klines are held locally (data/markPriceKlines_1h, Binance USD-M, 2020 to 2026-09-30; DATA_SOURCES.md:35).
- Why not known: M265 (line 240) names it: "mark-based liquidation remains untested." R280 and R206 used traded or OHLC prices. R252 used a traded wick (ATR wick). No row re-times a cascade on mark.
- Data: held. data/markPriceKlines_1h (hourly mark OHLC) and data/metrics_1h (OI, per M176). Mark klines end 2026-09-30, which limits the forward window; the discovery window is 2020-2026.
- Cheapest decisive observation: take R252's rule exactly as written in its PREREG (not the journal). Re-define the trigger as a mark-price move of the same size, and recount the events. Compare the counts and the 4 h and 24 h returns with the traded-price version. Hours: about 3 h; no new data. Read the PREREG only (registry path), never the journal.
- Kill result: the mark-based events are the same events as the traded ones (overlap above about 90%), or the mark-based 4 h and 24 h returns are not above the random-hour placebo at the same cost. In either case, drop the timing idea.
- Value for a French owner with about 10k EUR: modest. If it works it refines an existing family rather than opening a new payer, and the fee and slippage are the same as in R252 (0.04-0.21 bp/day per R252).
- My probability it is true: 0.10. R252's ALL/24 was t 1.93 but post hoc market-wide, and the mark and traded prices are usually within a few bp in liquid coins.

## 4. What I did not check

- Hyperliquid's and Lighter's official pages are in part unreachable: several URLs returned 404 through WebFetch. The exact unwind price for HLP takeovers and the ADL ranking price (oracle or mark) are not confirmed on a primary page. The sources disagree on this (oracle in the wiki; mark in a third-party doc).
- The insurance-fund draw condition is in dispute between secondary sources and not in the primary pages I could read.
- JELLY's HLP outcome is disputed: OneKey says HLP ended with a surplus; Earnpark says HLP came through only after validators stepped in. Not used in any probability.
- The HLP vault data folder (data/hyperliquid/vaults) is missing in this checkout. The M285 yardstick cannot be re-run here.
- The userFills test returned an empty list for the HLP address; the `liquidation` field is untested.
- No parquet was read (pyarrow missing), so no held-data number is quoted in this report.

## 5. Next step for the lab (not done here)

- Confirm the HLP vault folder (docs/DATA_SOURCES.md:24) exists on the data branch before anyone cites M285 as held.
- Re-check the WebFetch quotes above on the live pages before any rule moves. Three of them carry an unverified exact wording.
- Q3 is the cheapest of the three and needs no new data; Q1 needs about two weeks more of R454 snapshots.
