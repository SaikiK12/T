# Lighter trade-side documentation conflict

## Later registered check, R427

After a separately frozen/committed protocol, the existing convention
matched169/169WTI and50/50Brent signed account-position transitions; the
opposite convention matched none. [R427's findings](../lighter_trade_contract_v1/FINDINGS.md)
and native report retain both interpretations and all mismatches. This
supports the recorded convention, without certifying complete capture,
global semantics, production vintage or private order/fill acknowledgements.
No frozen R426 input or result was changed or rerun. The original source
conflict below remains part of the evidence history.

Read after R426's sole run on 2026-11-07, approximately18:27–18:35UTC. This
is source/code reading, not another market-data measurement. The original
report, frozen inputs and pre-registration remain unchanged.

The frozen model and existing `lab/tape.py:218` interpret
`is_maker_ask=true` as an ask-side maker and a buyer aggressor. A hypothetical
ask can therefore be filled by such a print above its price; a hypothetical
bid needs the opposite sign and a print below its price. The recorder copies
the boolean without converting its economic meaning.

## Read sources and contrary evidence

- **Primary, partial:** elliottech/Lighter agent kit,
  [schemas-read.md](https://github.com/elliottech/lighter-agent-kit/blob/main/references/schemas-read.md),
  publication date not stated, accessed2026-11-07. The trade example says
  exactly: `"is_maker_ask": false, // false = aggressive buy, true = aggressive sell`.
  This is the opposite convention. The document was read for its trade and
  funding sections, not as proof of the matching-engine implementation.
- **Primary, partial:** elliottech/Lighter Python SDK,
  [trade.py](https://github.com/elliottech/lighter-python/blob/main/lighter/models/trade.py),
  publication date not stated, accessed2026-11-07. It types
  `is_maker_ask: StrictBool` without defining the aggressor direction; it does
  not resolve the contradiction.
- **Secondary practitioner implementation, partial:** Nautech Systems,
  [Lighter websocket parse.rs](https://nautechsystems.github.io/nautilus_docs/rust-api-latest/src/nautilus_lighter/websocket/parse.rs.html),
  publication date not stated, accessed2026-11-07. The fill parser says
  "`is_maker_ask` says which book side rested as the maker" and assigns maker
  liquidity when `user_is_asker == trade.is_maker_ask`. Its four synthetic
  combinations agree with R426's convention. This independently supports the
  interpretation but is neither primary matching-engine code nor an actual
  order/fill witness from the captured sample.

Do not silently flip signs to improve results or edit a frozen parser.
Further qualification needs independently identified maker/taker order or
execution events with source identity, quantities and clocks, or an
unambiguous primary producer specification. Any empirical comparison of
signs, markouts or alternative strategy outcomes requires a new R-id,
committed freeze and one run. No such comparison was performed here.

This warning also matters to future Lighter flow studies using the same
field. It does not establish that a historical lane has a sign bug, and it
does not overturn or upgrade any prior outcome. R426 remains a negative
conditional calculation with unknown economic execution, not proven alpha.
