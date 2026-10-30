# eventlag_fwd notes (not frozen; nothing here changes the PREREG's rule or verdict)

Registry id: R369. Written 2026-10-29 00:40 UTC, before the first release (14:30 UTC).

## Websocket drops, not covered by the PREREG's known limits
The public websockets reached through this container's proxy end every few minutes with `ConnectionClosedError: no close
frame received or sent` and reconnect 1-2 s later (`data/commodity_perps/sessions.csv`; Binance's book stream about every
10-20 minutes, Lighter's about every 30 minutes, `data/lighter_trades/sessions.csv`). Why it matters for the rule:

- A drop of a **leader** feed (Binance, Hyperliquid) across a release delays t*; the follower then has had longer to move, c
  grows, and the lag filter skips the trade. It can hide a lag; it cannot make one.
- A drop of the **follower** feed (Lighter, the decision follower) leaves its last quote on screen while the real book
  moves. The rule reads "the follower has not moved", keeps the trade at the stale touch, and books the catch-up as a
  gain. That is an artifact of the recording, not an opportunity.

Chance per release: about 75 s of window / 1,800 s between Lighter drops, roughly 4%. Small, but one artifact in 8 trades
would dominate a mean.

## What is done about it, without touching the frozen files
`scripts/eventlag_gaps.py` (a diagnostic, not a frozen input) marks, for each journaled release, which feed had a session
start or end inside [T - 10 s, T + 65 s] (+/- 2 s), writes `results/gaps.csv`, and prints the decision cell on the clean
releases next to the all-release cell. The verdict stays the frozen rule's, on all valid releases. If the two disagree, or
if a counted trade sits on a release whose Lighter feed was gapped, FINDINGS says so and the trade is treated as unproven.
A session that was cut by a SIGKILL leaves no end row, so a window inside a silent outage is caught only by the runner's
own validity test (a reference needs 25 of 51 marks and a quote in the 60 s after T).

## Disk
`scripts/record_commodity_perps.py` was restarted at 00:26 UTC on 2026-10-29 with MAX_MB 4,000 (was 800; measured about
4.3 MB stored over the first 1.5 h, which would have lasted days, not the 55 until 2026-12-23). Re-measure after the first
US session and set the cap again if the rate is far above 150 MB a day.

## What R370 says about reading this lane (2026-10-29)
`experiments/cmelead_v1` (R370) replayed 60 past EIA releases with CME trade ticks (Databento) against Binance aggregated
trades. It does not change this lane's frozen rule, calendar or runner. Three readings for the FINDINGS of R369:

- **Gas timing.** CME's first trade 20 bp from its pre-release median comes 1.04-1.08 s after the nominal 10:30:00 in at least
  75% of the releases. The market reacts about a second after the stamp, so this lane's gas t* should land near T + 1 s and its
  decision (L = 1 s) near T + 2 s. A t* far from that points to the noise, not the report.
- **Crude threshold.** 8 bp is crossed within a minute of 14:30 UTC on 24-27 of 29 ordinary days (placebo), against 30 of 30
  release days. The crude cell is therefore close to a generic lag test, not an event test. Read a crude hit with the
  placebo in mind. The gas threshold (20 bp) is specific to the release: it is crossed on 3-5 of 29 ordinary days.
- **Binance is not a laggard.** At CME's threshold trade Binance's CL and NG perps had already moved about 0.9 of CME's
  displacement. A lag found on Lighter here is Lighter's own, not a delay inherited from CME.
