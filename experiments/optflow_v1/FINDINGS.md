# FINDINGS: optflow_v1 (R295). Signed Deribit option flow does not lead BTC or ETH perp returns over 1-24 hours, and its gross edge is far below API costs

**Verdict: NULL.** M311 and M313 are TESTED for the 1-24 h perp lead.
- **Trials:** 15, gate 0.
- **Read:** frozen PREREG a0ef3e2c (committed and pushed in 058488b before the run), run 2026-10-22 03:22 UTC,
  `scripts/run_optflow.py`.
  - 7 inputs, and all 138 Deribit flow files from 2021-01 to 2026-09, matched their frozen hashes.
- **Program trials** after this round: 9,478,588 (`registry.program_trials()`).
- **No pass, and no significant opposite sign.**

## What was tested
**The claim** (the owner's term list; QuantData's Net Drift and block-print tools):
- **Option flow is informed.** Blocks are crypto's dark-pool prints (M311). Net premium spent on the bullish side
  (call buys, put sells) leads the underlying (M313).
- So signed flow should lead the perp.

**The estimate.** Each Deribit option trade carries the taker's side, so there is no bid/ask guess. Per currency and
hour, five signals:
- delta flow of block trades;
- delta flow of screen trades;
- net drift (signed premium, USD);
- net drift over out-of-the-money options only;
- net drift without blocks.

Each is summed over the last h hours, z-scored on its own previous 720 hours, and read against the Binance perp's
log return over the next h hours (h = 1, 4, 24). Fit on 2021-04..2023-12, read on 2024-01..2026-09.

## Result

| Signal | h | Discovery t | Validation t | Validation BTC / ETH | Validation by year 2024 / 2025 / 2026 |
|---|---|---|---|---|---|
| block_delta (M311) | 1 | **+2.48** | +0.62 | −0.01 / +0.80 | +2.18 / −0.73 / −0.79 |
| block_delta | 4 | +1.27 | +1.27 | −0.49 / +1.95 | +0.55 / +1.38 / +0.12 |
| block_delta | 24 | +1.43 | +0.82 | −0.49 / +1.31 | −0.12 / +1.56 / −0.37 |
| screen_delta | 1 | −0.04 | +1.11 | +0.23 / +1.39 | +0.43 / +0.83 / +0.66 |
| screen_delta | 4 | −0.82 | **+3.02** | +1.79 / +2.78 | +1.28 / +2.88 / +0.97 |
| screen_delta | 24 | −0.39 | −0.32 | −0.30 / −0.24 | −0.77 / +0.23 / −0.11 |
| drift (M313) | 1 | +1.66 | +1.31 | +0.15 / +1.59 | +1.45 / +0.10 / +0.67 |
| drift | 4 | −0.45 | +2.15 | −0.06 / +2.81 | +1.14 / +3.45 / −1.68 |
| drift | 24 | +0.32 | −0.10 | −0.60 / +0.31 | −1.13 / +1.63 / −1.01 |
| drift_otm | 1 | +1.68 | +0.98 | −0.56 / +1.68 | +1.24 / +0.70 / −0.37 |
| drift_otm | 4 | −1.29 | +0.30 | −0.09 / +0.45 | −0.06 / +1.09 / −0.72 |
| drift_otm | 24 | −0.28 | −1.00 | −2.36 / +0.15 | −0.37 / −1.03 / −0.20 |
| drift_screen | 1 | +0.20 | +1.23 | +0.94 / +0.95 | +0.26 / +1.14 / +0.81 |
| drift_screen | 4 | −0.82 | +2.45 | +1.18 / +2.29 | +0.95 / +3.18 / −0.42 |
| drift_screen | 24 | −1.24 | −0.64 | −0.52 / −0.47 | −1.38 / +0.77 / −0.69 |

The bar is a validation t ≥ 2.94 (Bonferroni over 15) with a positive discovery t.

- **Block prints (M311) do not lead the perp out of sample.** The 1-hour block signal had the best discovery t
  (+2.48). It falls to +0.62 in 2024-26, and from 2025 it is negative.
- **Net drift (M313) does not lead it either,** in any form. The OTM-only version, where the literature puts the
  information, is the weakest.
- **The one validation t over the bar fails the sign rule.** Screen delta flow at 4 hours reads +3.02 in 2024-26,
  positive in both coins and every year. But it is −0.82 in 2021-23, so it is not a pass.
  - drift and drift_screen at 4 hours share the pattern (validation +2.15 and +2.45, discovery negative). They are
    largely the same flow measured another way.
  - One validation t above 2.94 among 15 is about what chance gives (5% for the family).
  - It is not logged as a seed, because it has no trade (below).

### The rule: gross edges are a few bp, and a round trip costs 17 bp

| Signal | h | Validation trades | Gross per trade (bp) | Net 1x / 2x / 3x (bp) | t (1x) | Hit rate |
|---|---|---|---|---|---|---|
| block_delta | 1 | 4,922 | +0.5 | −16.5 / −33.5 / −50.5 | −15.8 | 48.0% |
| block_delta | 4 | 2,476 | +2.7 | −14.3 / −31.3 / −48.3 | −4.8 | 50.9% |
| block_delta | 24 | 796 | +13.0 | −4.0 / −21.0 / −38.0 | −0.4 | 49.6% |
| screen_delta | 4 | 3,303 | +3.5 | −13.5 / −30.5 / −47.5 | −5.6 | 49.4% |
| screen_delta | 24 | 896 | +16.0 | −1.1 / −18.1 / −35.1 | −0.1 | 51.3% |
| drift | 4 | 2,407 | +7.5 | −9.5 / −26.5 / −43.5 | −3.0 | 50.8% |
| drift_screen | 4 | 2,631 | +4.6 | −12.4 / −29.4 / −46.4 | −4.3 | 50.6% |
| drift_otm | 24 | 752 | −18.1 | −35.1 / −52.1 / −69.1 | −3.0 | 48.4% |

The rule trades the sign of x when |x| ≥ 1, holds h hours, and does not overlap. The other 7 rows are in
`results/summary.json`, and every one is negative at 1x in validation.

- **No rule is net positive at 1x cost in validation,** so no trial could have earned a lane even with a pass.
- **The largest gross figures are at 24 hours** (+13 to +16 bp per trade, hit rates near 50%). A 24-hour perp move
  has a standard deviation of 242 bp (BTC) and 349 bp (ETH) in 2024-26, so these figures are noise.
- **In discovery,** only block_delta at 24 h nets positive at 1x (+9.0 bp on 804 trades, gross +26 bp). It halves in
  validation and turns negative.

### Descriptives
- **Blocks are a large share of Deribit flow:** 37% of BTC and 27% of ETH traded amount (2021-26). BTC has at least
  one block trade in 64% of hours, ETH in 48%.
- **Delta coverage:** 0.2% of traded amount has no delta (no IV or at expiry).
- **Prices:** 5 (BTC) and 4 (ETH) missing hourly price instants over 2021-26.

## What this does and does not show
**It shows,** for 2021-2026, that Deribit BTC and ETH option flow signed by the taker does not lead the next 1, 4 or
24 hours of the Binance perp out of sample. This holds:
- as block or screen delta, and as signed premium (all, OTM, or without blocks);
- pooled or per coin.

Even its best in-sample forms move a few basis points per trade, against 17 bp of API round-trip cost.

**It does not test:**
- **Leads shorter than an hour,** or within the hour of the trade. A block printed at 10:59 is read at 11:00. The
  tape recorder (M264) is the place for seconds.
- **Unusual-size filters** (premium above k × its trailing mean). M313 listed this as a variant, and it was not in
  the 15.
- **The platform's own read** (the call line crossing the put line).
- **Other venues:** OKX, Bybit, Binance and CME options, and Deribit's USDC options.
- **Opening against closing trades,** which Deribit's public trades do not mark. The equity result (Pan and
  Poteshman) needed open-buy volume.
- **Maker execution.** At 0 fees a 4-hour gross of 3.5-7.5 bp could matter, but makers are adversely selected
  (arXiv 2502.18625), and this lane did not model fills.

## Costs
API at 8.5 / 17 / 25.5 bp per side (1x / 2x / 3x). Every validation rule is negative at 1x, and at 2x and 3x by more.

## Read against the program
- 15 trials, each against t 2.94 (Bonferroni over 15).
- The one validation t above it (+3.02) has a discovery t of the wrong sign, and its rule loses 13.5 bp per trade at
  1x.
- The program's 9.48M trials do not change a NULL.

## Next
- **M311 and M313 are TESTED (NULL)** for the 1-24 h perp lead. Option flow does not enter the queue as a
  directional signal.
- **Still open on the Deribit data:** `charm_expiry_v1`, R289's Friday settlement reversal against expiring gamma.
  It is intraday and tied to the 08:00 UTC expiry.
- **The two Deribit nulls (R292, R295) agree:** Deribit's taker flow is large in options terms and small next to perp
  volume. Neither its gamma nor its direction moves the perp at hourly or daily scale.
