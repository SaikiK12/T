# R340 acquisition boundary

Owner Codex, 2026-10-27. Claim:
https://github.com/SaikiK12/T/issues/7#issuecomment-6434234152

One finite source/metadata phase, then at most one separately preregistered current
quote phase. Fixed source and API URL scopes are in the pinned collector. Four
official Binance API docs (COIN-M exchange information, depth, mark/index; spot
filters); two public exchange-information APIs. Current books only for BTC/ETH
spot USDT and their CURRENT_QUARTER/NEXT_QUARTER inverse USD contracts, exactly
four distinct pair/maturity identities. No alternative symbols, history, account,
order, authentication, redirect, retry, replacement, continuous loop or bypass.
Failed metadata/access prevents the quote phase; failures and body prefixes stay.

Accumulated NEW scope maximum16GET attempts,8MiB conservative reservation,128s
cumulative request time reserved,8s each request,180s wall deadline per phase.
Actual fixed request scopes use at most12 attempts; unused slots are not reassigned.
Every request first reserves512KiB and8s in ONE persistent BudgetJournal. Restart
does not clear reservations. All failures remain charged; completed phases refuse
re-execution. Child workers use an existing frozen no-redirect HTTP transport,
preserving injected proxy and TLS trust. Only owned children are terminated.

Historical7757requests/reported229.85MiB and prior closed66-request corpus batch
are separate existing spend, unchanged; neither allowance is renewed. No large
historical download or model weights. Static copyrighted HTML stays in ignored
private cache; public compact receipts retain URLs, hashes, access and exact
read/unread scopes. Small public API input bodies/budget are retained as evidence.

Freeze and commit this boundary and acquisition closure BEFORE dispatch. Reading
mechanics/metadata is not calculating a strategy outcome. No market-price economic
calculation occurs until its finite PREREG/code/inputs are frozen and committed.
Quote capture, if permitted by accessible metadata, is sealed and committed before
cost reporting. No prospective score, activation, order, money or secret access.

acquisition_inputs.json SHA256 796f6da917ad171e8eece52fa25b56a42b952aa0be288008e8e2b43561aac6da
