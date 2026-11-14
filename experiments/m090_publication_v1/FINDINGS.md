# R373: interrupted before publication or market capture

Native status: **ABANDONED / PARTIAL**. Zero strategy trials and zero market
observations, forecasts, labels, trades or PnL. Costs 1x/2x/3x: N/A.

On 2026-10-29, the local protocol was frozen with SHA256
`05ca7059257cdde36ac18049a60b642be6170bf99d8e620c10cd99f35779a685`.
Its code/trust manifest digest was
`c9fd370613cdf25d669d6d6ed927c1d2c349e3647cbfe4f2a50b3223d5bfad4a`.
The freeze/registry append were not committed or pushed before interruption.
The session trace records synthetic validation, but its temporary logs are
unavailable and are not current test evidence.

The environment restart removed `/tmp/t-m090-pipeline`: its code, public
material, inputs.json and test logs were uncommitted. The persistent Git branch
still points to ae76564. No live M090 source capture had been run. The exact
PREREG text was reconstructed from the session trace and its original digest
verified; the sidecar restores that original digest. The code/input manifest
cannot be restored byte-for-byte, so this lane must not be run or re-frozen.
No substitute inputs.json is fabricated.

[R374](../m090_content_v2/PREREG.md) registers a smaller successor in a
persistent workspace. It supplies signed-content capture only and does not
implement or claim R373's conditional clock/ticket admission rules. Earlier
invented-byte provider probes are feasibility context, not market evidence.
