# R343 bounded review

Scope: cached R329 source contract, new same-venue units/prefunding, shared cash/earmarks and terminal portfolio algebra. No network, market reporter, actual market outcome, tracked edits, new source acquisition, orders or broad audit. AGENTS.md and docs/ROOM.md read.

Findings fixed by root before freeze:
- lab/venue_carry.py:77: mismatched receipt/publication counts silently passed through zip (one receipt, no publication returned []). Equal cardinality and exact types now required; negative invented probe now raises ValueError.
- lab/venue_carry.py:36: route flags (1,1) compared equal to (True,True). Exact bool requirement now present; negative invented probe now raises ValueError.

Invariants checked:
- R329-S11/S39: spot quantities are BASE; min_trade_amount is minimum and increment; contract_size is not the increment. Fixed future quantities remain USD face and A=sum(face_i/price_i). Current metadata controls identity/route/grid; routed spot tape is unused.
- Common purchase q is rounded UP from worst 3x inverse A*(1+3*futurefee)/(1-3*spotfee). Reserve also covers the more expensive 3x quote-debit case. One invented one-level prepare plan passed all six standard-fee 1x/2x/3x by base/quote debit cases: D>=0 and spent<=reserved. This is an arithmetic control, not market evidence.
- scripts/run_same_venue.py:71/86/94/98: only one initial 10,000 USDC SpotCashAccount; inverse initial_coin equals the SAME net purchased inventory, virtual earmark rather than another deposit. Unused coin is exactly zero and cash+summed spot spends equals capital. Opening inverse fee is deducted in inverse coin once; spot holdings are not added again in terminal wealth.
- New model_open run on two invented coins at 3x/base debit passed cash, earmark, opening-coin-fee and cash restart checks. Journals are only .cache/r343-review-58_i1y2y/model/. No market report called.
- Independent toy kernel reconciliation: start 10,000; BTC 2@100 with .01 BTC fee, ETH 10@20 with 1 USDC fee, inverse entry fees .01 BTC/.02 ETH gave cash 9,599 and combined mark 9,996.6. The 3.4 loss equals all supplied fees exactly once; spot holdings must not also be added to inverse equity. Invented reference marks only.
- Terminal sum at scripts/run_same_venue.py:156-175 is cash_remaining + common_ratio * sum_i((Q_i*(1-delivery_fee_i)+D_i*X_i)*(1-spot_exit_fee_i)). Each leg uses zero idle cash locally (capital=its spend); the full-capital cash benchmark appears once at portfolio level. No second principal, initial coin or idle-cash credit found.

Limits: future delivery prices and sale/TWAP/FX ratio are supplied conditional worlds, not forecasts or executable prices. Current shown depth is not a future sale commitment. Actual account access, fee currency/rounding/tier, settled spendability, margin and liquidation remain unverified. Residual D is a coin exposure, so retaining X is necessary. Incomplete inputs and actual expected net remain unknown; review gives no strategy activation. No remaining issue found in this finite ownership/terminal-algebra scope.

Reviewed file identities:
- lab/venue_carry.py sha256 292af0e4950ab4ebeb58005e42a46e5cca155a9591eebc14da9f83b7973fccb5
- scripts/run_same_venue.py sha256 cd0cac20aac11c0035290b31bea089e2cac6d28422daedfadba4518b0664e1c6
