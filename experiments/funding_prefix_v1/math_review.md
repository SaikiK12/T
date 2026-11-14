# R322 limited independent financial review — corrected blockers rechecked

Reviewed exact files:

- lab/funding_prefix.py SHA256 `156d3be79d46dcc25d8c3d6847fa8d8806d9f3b4ae31d96abd7e70409607f9be`.
- tests/test_funding_prefix.py SHA256 `c1d8e0190e4d710778034d7d9f694c83934c0625c75384e8e1cd45dc10026659`.

Scope: at most6local tool calls, no network/market statistics/new agents. Compared new model equation and transition ordering against the four received pinned Rust source scopes recorded in source_review.md. This is not full circuit/API/source-authenticity or runner sign-off.

Two blockers were found and corrected before any freeze:

1. Reusing the old checkpoint under a renamed provider event previously double-posted funding. Executed counterexample produced two accepted1e-7 credits for the same interval. Posting identity now hashes account,perpetual position slot,and start economic update time. Endpoint/provider label/size do not create a new start ID. Bound financial signature carries size,checkpoint,multiplier,mode,strategy,epoch,end-prefix and scope; reused-start changes conflict for reconciliation. The next properly advanced start gets a different identity. Colon-delimited identity ambiguity is removed.
2.32-bit strategy/ambiguous market identities admitted unsupported encoded domains. Strategy is now0..7; market is explicitly a perpetual position-slot index0..254,not a public48-bit market identifier.

The focused10hand tests pass on this exact reviewed revision (0.0815s measured including subprocess startup); output retained in math_review_tests.log. They include alias dedup,overlapping/revised endpoint/size/margin conflict,next-start separation,old-inventory increase/flip/close,unknown observations,epoch/clock rejection,domain overflow and partial rounding-component checks. Full suite is root's separate obligation. No production economic outcomes were computed here.

Limited conclusion: the two identified blockers are corrected; the reviewed source-level conditional equation and conservative failure paths are suitable to freeze as a **funding-component model only**. No API cash decoder,paid cash/profit,actual account entitlement,physical-base exposure,full trade PnL,margin liquidation,or activation claim is supported.

Remaining limits: source tree is not established as a deployed revision; imported signed bigint/overflow/Euclidean division helpers and complete matching/account persistence graph remain unread. Prefix observations and initialized position state are supplied model inputs,not authenticated API state. Arbitrary caller-declared start timestamps are not externally proven monotone account transitions. Model funding is segregated by margin/strategy but not reconciled with PaperAccount's physical base fills. The partial Python-floor component is not a verified wallet credit. Provider labels and receipt provenance must remain in external evidence records because stable financial identity deliberately excludes them. No review of root's new runner,source manifest,preregistration,full fixture family,or cost outcomes.
