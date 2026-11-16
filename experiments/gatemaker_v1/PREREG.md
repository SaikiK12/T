# PREREG: gatemaker_v1, what a resting order earns or loses on Gate's USDT perps (hedged-maker lever)

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R497
- **Owner (single writer):** Claude (session claude/yo-9a1k5w)
- **Date registered (UTC):** 2026-11-16
- **Method:** M546, lever 2 of `research/intake/fee_map_20261116.md`.

## Question
On Gate's USDT perpetuals, does an order resting at the touch and hedged 5 seconds after it fills cost at most half of
what a taker pays? It is measured from Gate's public trade tape over 2026-11-02..2026-11-15.
- A resting order pays the maker fee and the 5-second markout.
- A taker pays the effective half-spread and the listed taker fee.

This is a measurement with **0 trials**: it tests no return. It decides one thing only: whether M546 earns a forward
execution lane for the Gate leg of R390's C14 carry book.

## Why
- R495 (PR #100) measured Gate's taker walk at 17.1 / 37.5 / 65.7 bp per side at $1k / $5k / $10k.
- With Gate's listed 7.5 bp taker fee, C14 pays 31.7 bp a leg a side at $5k, against a 26.9 bp break-even.
- A resting order earns the spread instead of paying it, but it is filled most when the price is about to move against
  it. That adverse move has never been measured here.

## Universe
- **Pool:** every USDT perpetual in `GET /api/v4/futures/usdt/contracts` (status `trading`, not `in_delisting`, with a
  positive `quanto_multiplier`) that has a ticker in `GET /futures/usdt/tickers`, at run time.
- **Bands:** 24 h quote volume (`volume_24h_quote`) at run time: [0, 50k), [50k, 500k), [500k, 5M), [5M, inf) USD.
- **Sample:**
  - Sort the pool by name.
  - Then, band by band, draw up to 15 contracts with `random.Random(497).sample`.
  - At most 60 contracts in all.
- **Survivorship:** the sample is today's listing. Contracts delisted during the window are not in it. Volume bands
  are as of the run, not of the window.

## Data
- **Source:** Gate's public `GET /api/v4/futures/usdt/trades?contract=<c>&limit=1000&from=<s>&to=<s>`, newest first,
  paged back by `to` and de-duplicated by trade id.
- **Pages:** at most 30 per window. A window that hits the cap is measured only on the span its pages cover, minus
  the 300 s margin, and is flagged `truncated`.
- **Fields:**
  - `create_time_ms` (seconds, with milliseconds);
  - `size` (signed contracts; positive is read as a taker buy, and is checked below);
  - `price`.
  - Notional = |size| x `quanto_multiplier` x price.
- **Windows:** the same 28 one-hour windows for every contract.
  - Two distinct UTC hours a day, drawn per day with `random.Random(497).sample(range(24), 2)`.
  - Days run from 2026-11-02 to 2026-11-15.
  - Each window is read with 300 s of margin on each side.
- **Not read before this freeze:** no trade in these windows was read by any lane or by this author. The plumbing
  probe on 2026-11-16 read 2 trades each from ACT_USDT at four instants (1, 3, 7 and 30 days back) and 3 recent
  BTC_USDT trades, only for field shapes.
- No key, no account, no order. About 2,000-6,000 public requests, paced at 0.12 s.

## Measurement (per trade in a window's core hour)
1. **Mid proxy** m(t): the mean of the last taker-buy price and the last taker-sell price at or before t, each at most
   300 s old; otherwise none.
   - For the pre-trade mid, only trades strictly before t count.
2. **Effective half-spread** (bp) = D x (p - m(t-)) / m(t-) x 1e4, where D = +1 for a taker buy and -1 for a taker
   sell.
3. **Maker markout** at delta in {1, 5, 60, 300} s (bp) = -D x (m(t + delta) - p) / p x 1e4. It is positive when the
   resting order that the trade filled gained.

## Per contract
- **Weighted means:**
  - notional-weighted (primary) and trade-weighted means of each markout;
  - the notional-weighted effective half-spread.
- **Counts:**
  - the number of core trades and their notional;
  - taker-sell and taker-buy notional per window hour. This is the flow that would fill a resting bid or ask; queue
    position is unknown.
- **Sign check:**
  - Take pairs of adjacent opposite-sign trades within 2 s.
  - Compute the share in which the taker-buy price is at least the taker-sell price.
- A contract **counts** if it has at least 100 core trades.

## Reading rule (frozen)
For each band with at least 8 contracts that count, take medians over its counted contracts:
- **taker cost** = effective half-spread + 7.5 bp (Gate's listed taker fee on every USDT perp);
- **hedged-maker cost** = 2.0 bp − 5-second notional-weighted markout.
  - 2.0 bp is a conservative maker fee. Gate's contract field lists a rebate of −0.75 or −1 bp; the cost at the
    listed rate is reported beside, never decided on.
- The lever **holds** in a band if hedged-maker cost ≤ 0.5 × taker cost.

**Verdict:**
- **INVALID** if the median sign check over contracts is below 0.6 or missing. The tape's sign convention would then
  be wrong, and nothing is read.
- **INSUFFICIENT_DATA** if fewer than 30 contracts count, or no band has 8.
- **LEVER_HOLDS** if it holds in every judged band.
- **PARTIAL** if it holds in some judged bands.
- **LEVER_FAILS** if it holds in none.

**What follows:**
- LEVER_HOLDS or PARTIAL earns M546 a frozen forward execution lane on R390's own Gate contracts, with its own id.
  - That lane would record live books and trade-through fills.
  - It would be reported beside R390 and never change R390's decision.
- LEVER_FAILS closes M546 for Gate at the touch.

## Known limits (stated before the run)
- **The markout is Gate's own outright move.**
  - A hedged leg is exposed only to the Gate-versus-Binance move until the hedge, which is usually smaller.
  - So the hedged-maker cost here is pessimistic.
- **It assumes the resting order is at the touch and filled by every trade there.**
  - Queue position and partial fills are not modelled.
  - A $5k order needs the flow reported per hour.
- **Trade-tape mids carry bid-ask bounce.**
  - The two-sided proxy removes most of it.
  - It is undefined when one side has not traded for 300 s.
- **Two hours a day for 14 days** is a sample, not the whole tape.

## Costs at 1x / 2x / 3x
This lane measures cost; it tests no return. The FINDINGS will report the hedged-maker and taker costs with the
maker fee at the listed rate, at 2 bp, and at 4 bp, in place of the 1x/2x/3x sensitivity.

## Outputs
- `experiments/gatemaker_v1/results/contracts.csv`: one row per sampled contract.
- `experiments/gatemaker_v1/results/windows.csv`: every window's trade count, pages, truncation or error.
- `experiments/gatemaker_v1/results/summary.json`: verdict, band table, sign check, prereg sha.
- `run.log`. No raw tape is committed.

## Stop rules
- One run, without `--limit`, after the freeze is pushed. There is no plumbing run on these windows: the offline tests
  in `tests/test_gatemaker.py` are the plumbing check.
- Nothing is retuned afterwards. A changed idea is a new lane.
- No orders, no money, no credentials.

```inputs
d619df0228705122750d01a6ea75d4e66c6163fd68d3e2fa2fa5c98a2a94d837  scripts/run_gatemaker.py
24ebbec4ba8e9660a9d159a6165dd5b6bd2397d7fbf8d85359c2819c1f339f27  tests/test_gatemaker.py
1f99799cac9032016494eff037d7c765cc553c45101feeb86ad97c4b65f48049  research/intake/fee_map_20261116.md
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508  lab/prereg.py
```
