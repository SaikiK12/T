# value (qwen4-max-preview)

**Blunt verdict:** Only one candidate clears cost by an order of magnitude — unlock, 324bp/event vs 18.73bp round trip (2×9.3635). Everything else in the pack is a *cost* problem, not a signal problem. Hunting more directional perp indicators at API taker is theatre.

**#1 — Convert Atlas gross cells to passive/web-tier execution.**
*Mechanism / who pays:* you stop paying the spread; the impatient taker pays you. Atlas replication 47.6% vs placebo 9.1% is the only asset that is validated gross and fails **solely** on cost.
*Binding constraint removed:* 9.3635bp/side API taker against 1–15bp/day gross. Pack: web maker 0 on 1106/1200 contracts, web taker 2bp, API maker 6bp.
*Data:* MEXC depth snapshots — held. Zero new downloads.
*Cheapest decisive test:* replay frozen Atlas entries as resting limits inside held snapshots; measure fill rate and 1/5/30-min markout. Net = gross − spread paid − adverse selection − fee, at 1x/2x/3x.
*Falsifier:* fill-conditional markout ≥ gross (you only fill when wrong), or no fills at owner size. Then Atlas is permanently dead — write the null.
*Caveat:* no orders/credentials means fills are an **assumption**, not a result. Label it.

**#2 — Make R265 point-in-time and cost-complete.**
*Who pays:* unlock recipients distributing supply; you are paid to absorb it.
*Why it survives:* +3.24%/event, 422 events, sign p1.6e-8, week-bootstrap +1.21..+5.24%, trimmed +4.06% (not tail-driven); R494 4.22%/yr at 2% cap, maxDD −4.62%. Multi-day hold amortizes 18.73bp round trip to noise — this is the horizon change the other 50 nulls never made.
*Binding constraint removed:* Gate 0 calendar is not point-in-time; short-side funding drag and event-window depth are unmeasured.
*Data:* held fundingRate per coin + MEXC depth. PIT unlock-announcement timestamps are **not held** — the one download worth doing.
*Test:* re-run restricted to unlocks knowable T−k days, subtract accrued funding and depth-implied slippage; keep R266 logging on-time forward days (pack: no edge has one).
*Falsifier:* PIT-only CI spans zero or net ≤ 0; or R266 forward fails.

**#3 — Role/instrument change: passive spread capture, Deribit options (low probability).**
*Who pays:* option takers crossing spreads. This is not VRP, skew, RR timing or GEX — all closed.
*Data:* 41M taker-side trades 2016-11..2026-09, held; keyless API reachable.
*Test:* from the tape, realized half-spread vs markout at hedge horizon, minus perp hedging at 9.3635bp/side × hedge frequency.
*Falsifier:* markout + hedge cost ≥ half-spread. Execution also blocked without credentials — so this is measurement only.

**Theatre, explicitly rejected:** re-litigating GEX (R292, R416), pin/charm/settlement (R289, R296), 25-delta RR (R307), DVOL VRP (R209, R138), session splits (R493), more chart rules (5472 already brute-forced, 9,785,317 trials). Levering funding carry is theatre: 2x t1.14. "GEX to size with confidence" is closed twice over.

**Plainly:** if #2's PIT test fails, no edge is reachable at API taker under these constraints. Best realistic outcome is unlock at ~4.22%/yr, 2% cap — plus whatever #1 proves about maker cost. Fund those two; stop buying signals.
