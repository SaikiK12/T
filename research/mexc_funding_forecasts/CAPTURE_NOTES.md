# One bounded validation, then handoff

Frozen collector/protocol commit: `b31d124`, pushed before the first live call.
On 2026-10-20 at 12:23 UTC, one invocation completed all 12 public requests and
validated six major-contract observations. The complete raw bodies, request timing,
body hashes, normalized observations and COMPLETE manifest are in `data/`.
The capture is roughly 176 KiB on disk including filesystem allocation.

Validation: 14 offline unit tests pass; protocol hash verified before invocation;
no requests were retried, no historical data downloaded, and no schedule started.
This is a single API/schema/clock validation, not a funding-revision sample,
predictive edge, executed fill, prospective paper return or evidence for all alts.
No future settlement label or performance calculation was performed. M090 remains
blocked for statistical testing until a separately frozen collection/test design
provides enough prospectively timestamped observations.

Owner requested completion of existing work followed by stop. Nothing is running
in the background; a future operator must explicitly choose any collection cadence.
