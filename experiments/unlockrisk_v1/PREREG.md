# PREREG: unlockrisk_v1 (R494). What sizing makes the unlock short survivable, and what does it cost?

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R494
- **Owner (single writer):** OpenHands agent, branch `openhands/session-persistence-factor-report`
- **Date registered (UTC):** 2026-11-15

Method M542. This is a **risk-model description of an existing lane, not a new signal**. The edge,
sample, direction and costs are R265's, already frozen (`4c630003`). Nothing here re-tests whether
the unlock short works, and nothing here selects a filter.

`experiments/unlocks_v1/FINDINGS.md` closes with: *"any forward or real version needs a per-event
size cap and a written plan for squeezes. That is decided in the next PREREG, not here."* This is
that PREREG. Motivation and the rejected alternatives: `research/VALUE_REVIEW_20261115.md`.

## Question
Under one pre-declared sizing rule, what are the portfolio-level drawdown, worst day and worst
cluster of the R265 unlock short, and how much return does the rule give up?

## Why a single rule and not a grid
A referee review (deepseek-v4-pro-0813, `research/value_review_20261115/workers/`) objected that
searching cap x gross-cap x cluster-limit on the same 422 events is selection: any cap chosen to
survive the known tail survives it by construction. **Accepted.** The primary rule below is fixed
by the owner's existing Gate-4 proposal, not by what looks best. Every other cell is reported as
sensitivity and decides nothing.

## Primary rule (frozen, one cell)
- **c = 2% of current equity per event**, the owner's Gate-4 proposal (`docs/GATES.md`, "at most 2%
  of the account's trading capital per book"). Not chosen from the results.
- **G = 10% total gross cap.** When n positions are open, each is sized `min(c, G/n)`. Verified
  before freezing that this is the only binding choice at c=2%: peak concurrency is 9, so peak
  gross is 18%; G=20% and G=30% never bind (0 days) and would be theatre. G=10% binds on 98 days.
- **No stop-loss.** The committed event file has no intrabar path, so a stop cannot be simulated,
  and R208 found stops harmful on the flow books. The book is made survivable by size alone.
- **No funding veto.** The file holds realised funding over the hold, not the trailing rate at
  entry; a veto on realised funding would leak the outcome.
- **No ADV filter.** The unlock/ADV >= 0.82 tail association was seen after R265 ran and is not
  significant (Fisher exact one-sided p = 0.101 on 6 events). It is not used in any form here: not
  as an exclusion, not as a covariate, not as a sizing input.

## Data
`experiments/unlocks_v1/results/events_priced.csv`, R265's committed per-event table, 422 events,
69 Binance perps, 2021-02..2026-09. Its sha256 is in the inputs block. **No download, no new market
data, no new events.** Columns used: `day`, `gross`, `funding`, `net1x`, `net2x`, `net3x`, `week`.
The hold is R265's D-7 close to D close, so a position entered on `day - 7` is open until `day`.

## Marking rule (the honest part)
The file has one return per event, not a daily path. Two markings are computed and **both** reported:
- **LUMP (primary, conservative):** the whole event return lands on its unlock day. This maximises
  the apparent daily loss and is the binding number for a daily-loss limit.
- **SPREAD (secondary):** the event return accrues in seven equal daily pieces over the hold. This
  is smoother and **understates intraday spikes**; it is reported only to show the assumption's size.
Neither is a claim about the intrabar path. Sizing uses the concurrency at each day, so concurrent
positions are marked **together** — the sequential one-at-a-time number in the value review is not
the portfolio path and is not used to decide anything here.

## Metrics (all reported, none searched)
Terminal equity multiple, max drawdown, worst single day, worst concurrent cluster, peak gross,
share of days the cap binds, and mean net per event after the cap's drag, at 1x/2x/3x costs.
Computed for the primary cell and, as labelled sensitivity only, c in {1%, 3%} and G in {20%, 30%}.

## Gates
This lane has **no significance gate**: it is a risk description, not a test of the edge. It reports
PASS/FAIL against two pre-declared survival conditions, chosen before computing anything:
- **S1:** primary-cell max drawdown (LUMP) better than **-10%**.
- **S2:** primary-cell worst single day (LUMP) better than **-5%**.
These are the typical prop-challenge max-drawdown and daily-loss limits, used as an external
yardstick, not as a fitted threshold. **SURVIVABLE** if both hold, **NOT SURVIVABLE** otherwise.
A FAIL is a result and is recorded as such.

## The owner decision this lane surfaces (not decided here)
`docs/GATES.md` Gate 4 also proposes a **hard stop at 25% of the stake**. At c=2% that is -0.50% of
equity, while the worst archived event is -3.55% of equity. The stop would therefore be breached by
the observed tail at every cap in {1%, 2%, 3%}. With no intrabar data it cannot be tested. The owner
must either accept a no-stop book sized small, or authorise hourly-bar collection so a stop can be
frozen and tested in its own lane. **This lane does not choose.**

## Multiplicity
**Trials: 1** (the primary cell). Sensitivity cells are descriptions of the same rule family and are
labelled as such; they are not extra chances at a verdict. Program trials before: **9,785,316**;
**9,785,317** with it. No holdout is read: R265's events are already seen, which is exactly why this
lane claims no confirmation and selects no parameter from them.

## Evidence lineage and admission
- Canonical method id M542. Parent: R265 (the edge and its committed events), R266 (the forward
  lane, untouched here), R224 (costs already inside net1x/2x/3x), R208 (stops harmful).
- `docs/GATES.md` SHA-256 at registration:
  `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`.
- Gate 0 description. Admits nothing to real money. No reserved read, no forward day, no new signal.
- Not a substitute for R266: only forward tickets can confirm the edge out of sample.

## Stop rules
One run of `scripts/run_unlockrisk.py`. No new caps, marks, filters or thresholds after seeing any
output. A crash fixed after the freeze is documented in FINDINGS with the changed sha.

```inputs
0aeb33d4cce29fd97a8077e6934180881411b5893f0a76346de5d59791ec2535 experiments/unlocks_v1/results/events_priced.csv
ea1840ba07d5cecdcbfee5f4da8b3a4569f05ece774f5abdadfd83b8c349cb99 scripts/run_unlockrisk.py
```
