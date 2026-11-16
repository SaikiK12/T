# gatefill_fwd (R498): a resting order on Gate's leg of C14, hedged on Binance, forward on paper

Measurement, 0 trials, frozen 2026-11-16 ([PREREG](PREREG.md)). It was earned by R497 ([FINDINGS](../gatemaker_v1/FINDINGS.md)).
R497 showed that a resting order on Gate costs at most half of a taker if every trade at the touch fills it. This lane
checks that assumption on R390's own contracts.

- **What it does:** every 2 hours, on GitHub (`.github/workflows/claude-gatefill.yml`):
  - it places paper bids and asks of $1k and $5k on the Gate contract of each position R390 holds, at the touch and
    one tick inside the spread;
  - about 2 hours later it settles them from Gate's and Binance's public trade tapes.
- **The question:** is resting on Gate cheaper than crossing both legs at once? The resting route counts:
  - the queue ahead at placement;
  - fills only by trade-through or by volume beyond that queue;
  - the Binance hedge 5 s after each fill;
  - crossing the rest after 60 minutes.
- **Journal:** `journal/orders.csv`, `journal/settled.csv`, `journal/ticks.csv` and `journal/status.json`.
- **When it is read:** the first `status.json` with `"final": true`, after 2026-12-01 00:00 UTC. Interim figures decide
  nothing.
- **Paper only:** public endpoints, no key, no account, no order.
