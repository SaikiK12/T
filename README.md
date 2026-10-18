# T

A research lab for crypto perpetual futures (Binance USD-M archive, the full survivorship-free set of USDT perps,
hourly, 2021 to 2026). The goal is positive PnL; the rule is that nothing counts as an edge until it survives
pre-registration, a placebo, data it never saw and a forward paper test.

The working question is no longer "which rule wins?" but a map: which signals predict returns before fees, with what
confidence, in which context (hour and market opens, BTC regime, market-wide flushes, order flow), how far each is
from paying its costs, and which routes (stacking, context gating, limit-order entries, carry) close that gap.

- [`docs/MAP.md`](docs/MAP.md): what is known so far, lane by lane, and the routes still open.
- [`docs/FOUNDATION.md`](docs/FOUNDATION.md): conventions; [`docs/AUDIT.md`](docs/AUDIT.md): weak points;
  [`docs/CONCEPTS.md`](docs/CONCEPTS.md): ICT, prop-firm and order-flow concepts with their evidence.
- `registry/rounds.csv`: one row per round with its trial count (append-only).
- `experiments/<lane>/`: PREREG.md (frozen), FINDINGS.md, results.

## Use

```
python3 -m venv .venv && .venv/bin/pip install numpy pandas numba scipy pyarrow
.venv/bin/python -m unittest discover -s tests -t .
.venv/bin/python -m lab.data build klines 1h      # archive fetcher (also fundingRate, premiumIndexKlines)
.venv/bin/python -m lab.flow metrics              # order flow: open interest, long/short, taker ratio; bookDepth
.venv/bin/python scripts/build_views.py           # research universe + feature tensor
.venv/bin/python scripts/build_extra_views.py clock|ctx|flow
.venv/bin/python scripts/run_atlas.py discovery   # and the other scripts/run_*.py, one per lane
```

Rules for contributors: [`AGENTS.md`](AGENTS.md). New lane: copy `templates/lane/`.
