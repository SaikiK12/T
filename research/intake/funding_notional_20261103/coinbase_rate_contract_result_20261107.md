# Coinbase CDE sampled funding-field qualification, 2026-11-07

Primary organization: Coinbase. Data publication date: undated API responses;
exact access timestamps and raw hashes are in each linked receipt.

R423's [frozen protocol](../../../experiments/cde_rate_contract_v1/PREREG.md)
and [one-run findings](../../../experiments/cde_rate_contract_v1/FINDINGS.md)
report8/8 exact same-time matches for BTC and8/8 for ETH between Advanced's
outer funding_rate and the MDA hourly-decimal field. No scale/time fitting.
Same-provider, ex-post sampled qualification only, not cleared cash or alpha.

Public source URLs (full JSON preserved, not full history):
- https://api.coinbase.com/api/v3/brokerage/market/products/BIP-20DEC30-CDE
- https://api.coinbase.com/api/v3/brokerage/market/products/ETP-20DEC30-CDE
- https://www.coinbase.com/api/mda/v1/instruments/CDE/BIPZ30/funding?result_limit=32
- https://www.coinbase.com/api/mda/v1/instruments/CDE/ETPZ30/funding?result_limit=32

Original source-body copies, URLs and receipt clocks are in the frozen lane
source manifest; MDA full-tail receipts are in `cde_rate_contract_20261107/`.
The prior `coinbase_unit_qualification_20261107.md` and its source receipt
are now frozen inputs and remain unchanged. This supplement records the new
result without rewriting that earlier source extraction.
