# cryptomon_v1 (R471)

Does a Bitcoin-linked US stock (MSTR, COIN, MARA, RIOT) keep moving after Monday's open in the direction of Bitcoin's
weekend move, or give the gap back? Gate 0 on public daily history from 2020-09.

- Rule and decision: [PREREG.md](PREREG.md) (frozen `88459528` before any stock price was fetched).
- Data: `scripts/fetch_cryptomon.py` (Binance's public archive for Bitcoin, Yahoo's chart endpoint for the stocks).
- Run: `python scripts/run_cryptomon.py` writes `results/`.
- Method M521; idea wave 8 ([intake](../../research/intake/idea_wave8_20261112.md)).
