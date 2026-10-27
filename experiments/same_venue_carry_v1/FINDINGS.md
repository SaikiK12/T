# R343: preserved input-schema failure, not a carry return

**PARTIAL component / all economic inputs incomplete.** Freeze555add4 preceded
the single new current capture; all eight raw responses were sealed/committed
at4cb12cd before reporting. No executable expected net or prospective trading
day is established. No candidate activation.

Eight public GETs returned200;6609 accepted body bytes,524288 reserved bytes,
56 cumulative reserved seconds, no budget violation, redirect or retry.
Metadata receipts took590..843ms, concurrent book receipts1105..1319ms.
The one-time scope is CLOSED, including all unused allowance. Original history
spend7757/8000requests and reported229.85/250MiB is unchanged; no renewal.

All eight fixed coin/size/depth preparation attempts stopped at spot identity:
the new adapter incorrectly required contract_size=1. Both pinned spot metadata
responses give contract_size=0.00000001, independently of min_trade_amount, also
0.00000001 in this snapshot. R329-S39 says spot contract_size is base coin and
must not be used as the amount increment; it did NOT say it must equal1. The
error is ours. Raw units/base/quote/routing identities and timestamps remain.

| Face per coin | Depth | Input status | Economic result at1x/2x/3x |
|---|---|---|---|
|1000USD|full|BTC and ETH schema failure|unknown / unknown / unknown|
|1000USD|top only|BTC and ETH schema failure|unknown / unknown / unknown|
|5000USD|full|BTC and ETH schema failure|unknown / unknown / unknown|
|5000USD|top only|BTC and ETH schema failure|unknown / unknown / unknown|

Preserved all48 model cells,432 conditional worlds,48 cash-only journals and
eight explicit failures. They are not executed positions, profitable zeros,
432return observations or a completed current carry opportunity assessment.
Actual future sale/FX ratio and actual expected net remainNone in every row.
Source publication/effective time, account access, owner fee/debit/rounding,
settled-wallet collateral route, margin and future exit remain unproven.

Ten invented-input tests and the full1549test suite passed before freeze
(206.445s,3existing skips); those fixtures missed the real contract_size shape.
Independent stdlib raw/journal oracle passed4190 exact checks on the preserved
incomplete output; it is not a financial-path pass. Fresh-directory report,
journals and independent audit byte-reproduce offline. See audit.json,
reproduction.json, original results.json.gz/journals.json.gz and raw evidence.

Reproduce with Python3.12.14:

```
/workspace/T-consolidation/.venv/bin/python scripts/run_same_venue.py --out .cache/r343-fresh
/workspace/T-consolidation/.venv/bin/python scripts/check_same_venue.py --out .cache/r343-fresh
```

Frozen R343 code/spec/source/raw bytes are never edited. Separate R344 corrects
ONLY this exact metadata literal, freezing new adapter/runner/checker/test
identities before recalculating the SAME inputs. No new request, relaxed
tradability/depth/clock/cost rule, instrument or validation winner. Keep this
failure and all controls; both attempts share one batch, not new independent
evidence. R343 adds0predictive trials, program9479013 unchanged,0paper days.
