# PREREG: paperacct_fwd, a $10,000 paper account run like a real one over the lab's running lanes

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R415
- **Owner (single writer):** Claude (session claude/yo-9a1k5w)
- **Date registered (UTC):** 2026-11-06
- **Method:** the owner's instruction of 2026-11-06, no real stakes yet; stakes on paper "comme un vrai compte". It
  holds R285's three families (M281) at equal capital, the book R414 found best on risk.

## Question
From 2026-11-07, does a $10,000 paper account split equally across the lab's carry, flow and event lanes, never
rebalanced and unlevered, end above $10,000 at 1x and 2x cost, with a daily return that clears NW t ≥ 2.24 and a
drawdown no worse than −25%?

## Data
- **Only input:** `experiments/xbook_fwd/journal/book_days.csv`, written each tick by R285's frozen runner
  (`scripts/forward_xbook.py`). Its columns `carry`, `flow`, `events` and their `_2x` twins are each family's daily
  paper net on one unit of capital, at the lanes' own measured costs (1x) and their 2x costs. `final` marks a day at
  least 9 days old with carry and flow present.
- **The families, as R285 froze them:**

| Pot | Lanes (R285's sleeves) | Paper venue | France access (report of 2026-11-06, press-checked, not legal advice) |
|---|---|---|---|
| Carry | R278 A (Gate + Hyperliquid), R278 B (Binance + MEXC), R279 A (Gate + KuCoin), R279 B (Binance + KuCoin) | two venues per book | Binance futures, KuCoin global, Gate global and MEXC: not open to French residents on the records found; Hyperliquid unclear |
| Flow | R215 A/B, R218 X2 | MEXC | MEXC is withdrawing from France (press, 2026-10-30) |
| Events | R266 unlock short, R268 delisting short, R270 Monitoring Tag short, R272 FF long and PL short | MEXC | same |

So a GAIN here is a paper result. It does not make the account deployable from France as it stands.

## Rule (scripts/forward_paperacct.py)
- **Opening:** 2026-11-07, $10,000, one third in each pot. Book days before 2026-11-07 are never counted.
- **Each day d:** pot(d) = pot(d − 1) × (1 + the family's value on d). A day without a value leaves the pot as idle cash
  at 0%. The pots are never rebalanced, so no money moves between venues.
- **Stop:** a pot at or below half its opening amount is closed for good. Its cash stays in the account at 0%.
- **Costs:** 1x is the lanes' own net. 2x uses R285's `_2x` columns. 3x = 1x + 2 × (2x − 1x), applied day by day.
- **Official days:** every book day from the opening to the last `final` day, as they stand when read. Later days are
  provisional and shown apart.
- **Outputs each tick:** `journal/statement.csv`, `journal/status.json` and `journal/statement.md` (a French statement
  for the owner), all derived. `journal/decisions.csv` is append-only.

## Decision
**Looks:** at 180 and 365 official days (about 2027-05-15 and 2027-11-15). Each look is written once.

**GAIN** needs all four, on the first `look` official days:
1. the 1x balance > $10,000;
2. the 2x balance > $10,000;
3. the Newey-West t (lag 10, `lab.stats.newey_west_t`) of the account's daily return ≥ 2.24 (one-sided 1.25%, two
   looks);
4. the 1x maximum drawdown from the running peak (opening included) ≥ −25%.

**LOSS** if the 1x balance ≤ $10,000. **CONTINUE** otherwise at 180. At 365, a result that is neither is
**NOT_SHOWN**. The lane stops deciding after a GAIN or a LOSS; the statement keeps running.

**Trials:** 1. The read is reported against `registry.program_trials('registry/rounds.csv')`, but this is a prospective
lane: no day it scores was seen.

**Reported at every look and in every statement:** the balance at 1x, 2x and 3x; each pot; the worst drawdown; the best
and worst day in dollars; the share of up days; closed pots.

**What GAIN means and does not mean:** it says the equal-capital paper book made money net of the lanes' costs over
those days. It does not prove real fills, venue access from France, or capacity. Real money still goes only through
`lab.gate.go_real()`, in small stakes, placed by the owner, on a venue the owner can legally use.

## What was seen before this freeze
- **R285's journal, 2026-10-23..2026-11-05:** 14 book days, 6 final; equal-capital mean +0.09%/day, NW t 0.58,
  drawdown −1.9%. None of these days is in the account.
- **R414 (in-sample, gate 0):** the equal-capital book of the same 12 streams made +32.6%/yr, Sharpe 2.64 and −8.4%
  drawdown over 2023-08..2026-09. Those streams are inflated by their lanes' selection. The flow books' own holdout
  (R198) was not confirmed.
- **Power:** a GAIN at 180 days needs an annual Sharpe near 3.2; at 365 days, near 2.2. Unless the in-sample level
  holds forward, a GAIN at 180 is unlikely.

## Limits (stated now)
- **No real fills, margin calls or transfers.** The lanes' own paper accounting is all there is. Their known limits
  (R278's fill accounting, MEXC flow books one bar late, event tickets scored at modelled 2x) carry through.
- **Idle cash earns 0%,** not the T-bill.
- **Events over 10 slots:** R285 books each event ticket at 1/10 of the family on its exit day. More than 10 open
  tickets would overstate what the pot could hold.
- **France access:** in the table above, from a report and press. Not checked against the AMF or ESMA registers.

## Inputs frozen with this file
```inputs
84f325a036f3d51b2653d2480a6b48d621db07a3753813ebc8cd170940daa08b  scripts/forward_paperacct.py
12fe7da09777d4f98207c7e9f466c4864be3642e9602821981d314cc746128a2  tests/test_forward_paperacct.py
c399f44ad4ab0645f1dcc3657226e91f0125cd5203e61dd5c34b3162a8cfabc8  scripts/forward_xbook.py
3706d39c4422d1986307ce2d50cb0487b5528842fb13f2259e09eb3f24482563  experiments/xbook_fwd/PREREG.md
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
```
