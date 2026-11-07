# PREREG: hftlead_v1 (R367). Does a cross-venue lead make a passive quote on Binance's USDC perp worth posting?

- **Registry id:** R367
- **Owner (single writer):** Claude, this session (cloud container, 2026-10-28)
- **Date registered (UTC):** 2026-10-28

Method M427 (selective maker on Binance USDC perps, from the owner's pasted plan of 2026-10-28). Frozen by
`lab.prereg.freeze()` before any fill, markout or other price change of the recordings is computed. After the freeze
this file is never edited; a changed idea is a new lane.

## Question
On Binance's BTCUSDC and ETHUSDC perpetuals, when the Binance USDT or the Bybit mid has moved away from the USDC mid by
more than the last six hours made usual, is a one-second passive quote on the side the lead favours worth more than
two cost units a fill, counting only fills that the recorded trades prove, with the order live 200 or 500 ms after the
decision?

## Why this lane
- The owner pasted a plan (a "cross-venue selective predictive maker" on Binance USDC perps, whose maker fee is 0%
  under a promotion; anticipatory post-only orders on Hyperliquid; a wallet toxicity layer) and said to shift effort
  there. M427-M429 hold the three ideas. M428 and M429's order-level part are blocked by what a public feed shows.
- This is the one part of M427 that public data can bound. Measured from this container on 2026-10-28, the feeds reach
  it 44-55 ms (Binance), 83-100 ms (Bybit) and 310-480 ms (Hyperliquid) after the venue's own event time. A decision
  made on them reaches Binance about 100 ms later. The screen asks only whether a lead that survives that delay exists.
- The 0% maker fee is not an edge: a quote that fills only when the price has already moved through it loses more than
  the fee it saves. The lab's own R193/R194 found simple maker entries adverse-selected, and R347/R348 found Lighter's
  makers close a lead over Binance within a second. A NULL here is the expected result and is recorded as a result.
- A PASS would not be a profit. It would justify asking the owner for small calibration orders (hard rule 5: orders
  need the owner) that measure the true fills and queue, and a forward paper lane under a new id.

## What the author has seen
- **Recordings.** `scripts/record_hft.py` started at 2026-10-28 19:10 UTC. For quality control only, the author has
  looked at row counts, bid-ask spreads, top-of-book sizes, local-minus-event delays, trade counts and connection
  logs of its first minutes (BTC tick 0.0123 bp of price, ETH 0.0425 bp; Binance USDC top-of-book about 0.45 BTC; about
  6.5 USDC trades a second on BTC). **No quote, fill, markout, lead statistic or price change of any recording has
  been computed.**
- **Window.** The lane reads whole UTC days from 2026-10-29. None of them existed when the QC was done.
- **Code.** The rule and runner were exercised only on a synthetic world (a planted 300 ms lead and a world with
  none; `tests/test_hftlead.py`). In it the planted lead pays an order live after 200 ms and pays nothing after
  500 ms, as it should; that says nothing about the real data.
- **Related evidence.** R347/R348 (taker lag scalps on Lighter, 1 s tape, NULL), R193/R194 (maker entries,
  adverse-selected), R349 (PARTIAL). None used these recordings.

## Data
- `data/hft/book/<day>.parquet` and `data/hft/trades/<day>.parquet`, the finished days that `scripts/record_hft.py
  ensure` merged from the recorder's 10-minute parts. Public Binance USD-M websockets (`/public` bookTicker, `/market`
  aggTrade) and Bybit v5 `orderbook.1`, local-receive clock, 100 ms buckets (one row per symbol and bucket with an
  update). Columns used: book `t, v, s, bid, ask`; trades `t, v, s, ls, hb`. Sizes are never read. `t` is the bucket
  start in epoch ms; `ls` is the lowest price at which a sell aggressor traded in the bucket and `hb` the highest at
  which a buy aggressor traded.
- Series: Binance BTCUSDC and ETHUSDC (the quoted book and its trades), Binance BTCUSDT and ETHUSDT, Bybit BTCUSDT
  and ETHUSDT. Hyperliquid and the fills are recorded for other lanes and not read here.
- **Window and run.** Days are 2026-10-29 onward, never past 2026-11-08, never the current UTC day. A day is usable
  when, for both coins, at least 80% of its 864,000 buckets have a USDC, Binance USDT and Bybit mid (a mid is the last
  row, at most 10 buckets old) and USDC trade rows exist. The lane runs once, on or after 2026-11-02 00:30 UTC (after
  `ensure` has merged 2026-11-01), on every usable finished day then; if fewer than 3 days are usable, no outcome is
  computed and the run repeats on each later UTC day until 3 are usable or 2026-11-08 passes (then INCONCLUSIVE).
- The runner writes the sha256 of every file it reads to `results/data_files.csv`. Disk caps the recording at
  `MAX_GB` 0.6 and stops it under 2.5 GB free, so the window may end early; days recorded are the days scored.

## The rule
All times are in the recorder's local-receive clock. A row of bucket k is known at the end of bucket k.
- **Mid and age.** Mid = (bid + ask)/2 of the last row at or before the bucket; a quote older than 10 buckets (1 s) is
  missing.
- **Signal.** For each coin and lead V (`binance_usdt` or `bybit`): d = 1e4 (ln mid_V - ln mid_USDC); x = d minus its
  median over the last 600 buckets (60 s; at least 300 points).
- **Candidates.** Bucket k where |x| is at or above the q-th percentile (q = 95 or 99) of |x| over the six UTC hours
  before k's hour (at least 18,000 valid points in them, else no quote in that hour), x is not 0, and USDC has a bid
  and ask.
- **Quote.** Decided at the end of bucket k; a bid at the USDC best bid of bucket k if x > 0 (the lead is above:
  USDC should rise), an ask at the best ask if x < 0. Live from the start of bucket k + 1 + L for 10 buckets (1 s),
  L = 2 or 5 buckets (200 or 500 ms). Price is not updated while live.
- **Strict fill.** In a live bucket a sell aggressor traded strictly below the bid (a buy aggressor strictly above the
  ask): the price moved through the quote, so a queue of any length was cleared. First such bucket j. **Touch fill:**
  at the quote or through it (every fill the data allows, queue unknown). True fills lie between the two.
- **Markout.** The USDC mid at bucket j + 10 against the quote price, in bp of the quote, positive for a gain (bid:
  mid above price; ask: mid below). No fee, no exit. A fill whose markout mid is missing is dropped and counted.
- **One quote at a time.** After a decision at k no new decision until bucket j + 10 if it filled, else k + L + 10.
  The strict and touch sets are serialised separately.
- **Control.** The same machinery with every USDC bucket a candidate and the side fixed (bid, then ask).
- **Placebo.** The signal and its thresholds circularly shifted by 3,600 to 72,000 buckets (6 minutes to 2 hours),
  10 draws (seed 367), strict fills only.
- **Gross lead (descriptive).** For each rule, the mean of sign(x) times the USDC mid change from bucket k + L to
  k + L + 10, in bp, over the candidates (not serialised).

## Trials
Coin {BTC, ETH} x lead {binance_usdt, bybit} x L {200, 500 ms} x q {95, 99} = **16 rules**. The decision uses
the strict fills only; touch, control, placebo and gross lead are reported, not decided on. Registry trials: 16.
Program trials before: 9,479,107 (9,479,123 after).

## Decision
Per rule, strict fills in whole UTC hours (blocks): mean markout, its t by the ratio estimator over blocks (residuals
of each block's sum about mean x count, H/(H-1) correction), one-sided p from the t distribution with H-1 degrees of
freedom, Holm-adjusted over the 16 rules.
- **PASS:** a rule has at least 300 strict fills, a strict mean above 2 cost units (0.2 bp) a fill, a touch mean above 0
  and a Holm-adjusted p at most 0.05.
- **INCONCLUSIVE:** fewer than 3 usable days, or fewer than 12 of the 16 rules reach 300 strict fills.
- **NULL:** otherwise.

## Costs (1x, 2x, 3x)
One cost unit is 0.1 bp a fill (about 8 BTC ticks, 2 ETH ticks): an allowance for the exit leg, slippage and a fee
that is not 0 once the promotion ends. 1x, 2x, 3x subtract 0.1, 0.2, 0.3 bp from every strict mean; the PASS needs
the 2x mean above 0, so a strict mean above 0.2 bp. The strict mean is also the break-even cost a fill can carry.
For scale (secondary source, a 2025-12-10 notice seen through a search summary, not used by the rule): USDC perp taker
fee 4 bp; the maker fee is 0 under the promotion. A taker form of this signal cannot pay that.

## Reported (not decided on)
Touch means and counts; fill rates; the control's bid and ask means; the placebo mean and spread against the actual;
the gross lead; per-day strict means; coverage by day; stale-mark counts. They explain a result and open nothing.

## Code
```inputs
bcfae129458cedbb633556cf930f422ae0d5d5f5014348bfb4a9ada789bf4715  scripts/hftlead_rule.py
3d24bcbc3f878c711da3d05fa6665f17318013e85c653d67652212995ee91018  scripts/run_hftlead.py
```
The recorder (`scripts/record_hft.py`) is not frozen: only the file format above is. Its sha256 at this freeze is
`ceb169b8e75a1d2382d5d71da947ed0875e2ccecbc360ac63158a71006b8fd99`.

## Evidence lineage and admission
- **Method:** M427 (related: M087, M227, M292, M186). **Parents:** none measured on these recordings.
- **Decision group:** M427's cross-venue-lead form on Binance USDC. One decision (the verdict above); every other
  output is a diagnostic.
- **Samples:** whole UTC days recorded after this lane was claimed; nothing here overlaps an archive any lane read.
- **Gates:** `docs/GATES.md` sha256
  `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`. Met: one decision; dependent blocks (hours);
  multiplicity (Holm over 16); cost sensitivity. Left unmet: gate 1 (a forward, strict on-time sample of real
  fills) and gate 3 (account risk); this lane is a gate-0 screen on a short window. Power: not computed; at BTC's
  trade rate the strict fills number in the thousands a day, so the screen can resolve a few hundredths of a bp and
  the cost units, not the signal, set what counts.

## Stop rules
- The lane ends with the first complete run. Nothing is retuned after it: no other threshold, lead, lag, quote life,
  coin, or window; a changed idea is a new lane.
- INCONCLUSIVE from too few days repeats only as described under Data. A run that scored the rules is final.
- What a PASS earns: a note to the owner asking for calibration orders, and a forward paper lane under a new id with
  its own PREREG. What a NULL earns: M427 closes NULL for BTC/ETH USDC at 200/500 ms from this container.
- No orders, no money, no credentials. The run reads files and writes `experiments/hftlead_v1/results/`.

## Known limits (written before the run)
- Timestamps are the container's receive times: feed delay and clock offset are inside them and cannot be removed.
- A quote is assumed placed at the best price known at the decision, never moved, and not to move the market.
- Queue position, own fills, cancel latency, partial fills, rejects and the real order path are unobserved. The touch
  and strict sets bracket the fills; they do not settle them.
- Markout is to the mid a second after the fill, with no exit and no inventory limit.
- Bucket extremes (`ls`, `hb`) lose the order of trades inside 100 ms.
- A few days is one regime. The fee promotion can end. BTC and ETH only; no other coin or quote asset.
- The recorder may stop (container restarts, disk floor); the usable-day rule is the only repair.
