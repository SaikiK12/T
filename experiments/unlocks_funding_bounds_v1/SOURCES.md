# Primary mechanics checked before R259 outcomes

Inspected2026-10-20; formulas below are implemented as an explicit diagnostic
model, not asserted as complete historical account reconstruction.

- [Binance funding FAQ](https://www.binance.com/en/support/faq/detail/360033525031),
  page updated2026-03-06: cash depends on mark-valued position size; positive
  funding transfers from long to short. Intervals can change. Position timing
  near settlement has a15-second ambiguity. This supports signed cash and an
  enlarged boundary window; summing raw rates assumes an unchanged notional.
- [MEXC funding rules](https://www.mexc.com/support/article/mexc-futures-funding-rate-305432020820705280),
  page dated2026-06-01: stablecoin contracts use quantity times fair price, with
  pair-specific schedules and possible delayed processing. Binance settlements
  are not a substitute for MEXC history or its contract sizes.
- [MEXC liquidation FAQ](https://www.mexc.com/support/article/faq-on-liquidation-for-futures-trading-8123281969561):
  liquidation refers to fair price and maintenance requirements. A traded candle
  high alone cannot establish it. Daily mark highs allow a necessary equity
  diagnostic, without identifying fills, maintenance tiers or cross-margin paths.
- [Binance public archive](https://github.com/binance/binance-public-data):
  publisher checksums identify acquired versions; later revisions are possible.
  R259 uses the already-pinned #31 sources, without refreshing or filling gaps.

R259's use of a whole-day low/high for an unknown settlement mark, a symmetrical
15-second optional-charge envelope,60-second interval tolerance and generous
credit-before-peak allocation are OUR frozen modeling assumptions. None of these
sources proves that sampled mark OHLC encloses every internal settlement mark,
that missing observations are harmless, or that a paper order would fill.
