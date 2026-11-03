# Bounded room actions, 2026-11-03

Scope: engineering and public schedule availability against `6aa579d`.
The owner requested a Codex/subagent room, then fewer agents and concrete
implementation. [Issue #71](https://github.com/SaikiK12/T/issues/71) records
the bounded triage; [#7](https://github.com/SaikiK12/T/issues/7) remains the
writer-claim and Claude handoff channel. The six read-only assignments
produced preliminary observations before usage limits stopped the wave.
The coordinator independently reproduced the two actionable defects/access
changes below and implemented them with the navigation improvement.
The remaining scopes are partial, not completed audits or new method results.

## Paper capital veto

An invented native ledger starts with 1,000 USDT, opens one unit at 100 with
zero fees, then withdraws 950. Cash and liquidation NAV are 50; reserved entry
notional is 100, leaving available simulated capital **−50**. The frozen
`PaperRisk` still returns `MODEL_WITHIN_LIMITS`: its flow-adjusted PnL and
initial-capital concentration checks do not incorporate this collateral
shortfall. This is a reproducible paper-entry admission gap, not a real-account
observation or a strategy result.

The new [PaperSolvencyGuard](../../lab/paper_solvency.py) wraps that frozen
engine. It checks the same copied account snapshot, account identities,
cash/NAV, the cash-minus-reservation identity, unresolved events and
reconciliation, without netting venues or settlement currencies. Missing
balances/marks stay unknown. Proposed reservations are explicit quote amounts
keyed by `(venue, asset)`; callers must supply them when checking a proposed
entry. Existing loss/drawdown stops survive journal reopening and deposits.
Capital failure vetoes new model entries without inventing an exit or changing
positions. Every result keeps actual-order and activation flags false.

New paper integrations use `PaperSolvencyGuard(existing_risk).observe(...)`
with the original risk arguments and `required_reserves={(venue, asset): amount}`.
The separate read-only command
`python scripts/check_paper_solvency.py /absolute/path/to/snapshot.json`
reports capacity only (exit 0 available, 1 blocked/unknown, 2 invalid input).
It always leaves model admission false because it does not run risk controls.
Neither interface authenticates supplied data or proves exchange margin.
Historical runners and their frozen account/control modules are unchanged;
they must not be described as retrofitted with this guard.

## BLS announced schedules

The former HTTP-403 access blocker is now resolved for the public
[BLS iCalendar](https://www.bls.gov/schedule/news_release/bls.ics) with the
project's existing `lab/1` client. A one-shot native recorder poll completed
at **local 2026-11-03 17:54:55Z**, with 23 baseline UIDs on/after November 3
in Eastern calendar dates. This scope includes already elapsed times on the
same date. It is a baseline observation, not proof the event was first
announced then. No recurring process was started or live daemon restarted.

The [static source and receipt](../../research/intake/bls_schedule_20261103/receipt.json)
archive a separate HTTP-200 response of 80,672 bytes, SHA256
`92a350111ace106deaab5584e4084366bd367b594a0d0bad116008d82d63e501`.
The receipt distinguishes this archive request from the earlier manual poll.
Read scope: the complete ICS structure, UID/start/title and optional revision
metadata; only current/upcoming Eastern dates enter the journal. No release
contents, consensus surprises, market outcomes or historical first-public
availability were read or reconstructed. [RFC 5545 sections 3.1 and 3.3.5](https://www.rfc-editor.org/rfc/rfc5545.html#section-3.1)
define content-line unfolding and floating/local/UTC date-time distinctions
used by the restricted parser; it is not a general recurrence engine.

The unfrozen [calendar recorder](../../scripts/record_tradfi_calendar.py)
now includes `bls_calendar` every six hours when a process runs the new code.
UID is the revision key. Eastern scheduled times convert using New York DST;
date-only, floating, ambiguous/nonexistent or unknown-zone times retain an
unknown UTC. Invalid/truncated/duplicate or recurring event lists fail the
whole poll and retain previous evidence. The existing shrink guard and
append-only journal semantics remain in force. Expired dates leave the
covered scope without generating false disappearance events.

`DTSTART` is a scheduled time. `DTSTAMP`, HTTP `Date`/`Last-Modified` and local
receipt clocks do not establish actual publication time or verified UTC.
This removes one calendar-access blocker for **M290**, whose canonical row
remains **UNTESTED**. Exact first-public clocks, publication lineage, reaction
design and executable costs still need their own frozen admission/test.
The change does not recover lost historical evidence or demonstrate alpha.

## Navigation and retained evidence

`python -m lab find R400` now labels the registry record as a snapshot and
prints the tracked native `FINDINGS.md` path when present. It does not parse
an outcome to silently rewrite append-only round status. In particular,
R400 remains terminal REFUSED; no extra look, threshold change or successor
experiment was started.

The old draft PRs #56, #32, #6 and #9 retain unique unmerged files or evidence.
They remain open for preservation/integration review. No branch, data or
historical document was deleted. Funding/dividend proposals and source-timing
diagnosis from the partial wave are not promoted to verified new leads here.

The canonical funding entries explain their remaining constraints: **M461**
uses previously inspected negative-funding histories, so its forced-hourly
comparison could only supply historical gate-0 evidence; it needs a frozen
design that addresses era/cap changes and separates manual switches.
**M449** requires at least 14 recorded days and still lacks Lighter funding
in its declared held data; elapsed calendar days alone do not prove complete
coverage. **M463** needs a venue-contract/dividend audit before testing a
settlement mismatch, with fees and owner access unresolved. Its cited source
already describes the simple leg as not an arbitrage net of fees. These are
existing queued hypotheses, not newly discovered edges; no return, funding
sample, cost tier or status was recomputed for them in this review.

The R400 source-timing diagnosis still depends on the already requested
timestamp-only JSON from the raw-data host. The local workspace has no rawtape
copy. A nominal 17:00 file cutoff alone does not explain the refusal: the
declared last decision is 16:59:30 with a target exit at 16:59:35.5. Next-quote
waits, encoded-offset changes and ID order remain possible explanations,
not established causes. The existing helper, frozen rules and terminal result
remain unchanged.

## Validation

The focused tests cover the native-ledger counterexample, required reserves,
unknown/malformed capital, venue separation, persistent stops, read-only CLI,
ICS clocks/folding/identity/error handling, and journal baseline/revision/
failed-poll/rollover behavior. They use invented fixtures and temporary
journals. Final full-suite, integrity and CI results are recorded in the
consolidated PR and room, with the exact published commit.
