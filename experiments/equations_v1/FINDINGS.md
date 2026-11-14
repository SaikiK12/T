# R310 — INCONCLUSIVE: source pagination prevented a valid family comparison

Frozen and pushed in `1bb6f07` before outcomes. The frozen specification is
`ad89c67ec5eb7508cdbc46175d31235b94e8a6c854a1df18aa3eae0847dce663`.
Twelve trials are retained as DONE/PENDING; this is not evidence of a live edge.

## Observed historical proxy results

Calibration selected **F0_h7** before validation. Only F0_h7 and F0_h14 met the
60-scored/60-active-day calibration eligibility rule. Reference budget scale was
0.736631, F0_h14 0.818057 and F0_h7 1.0; no scale exceeded base size.

Validation was 273 calendar days, 2026-01-01 through 2026-09-30, with $10,000
initial total capital split equally between venues. These are **observed
close-price/funding-notional proxy totals**, including unscored intervals, not
complete cash payments or an eligible statistical sample:

| Policy | PnL 1x | PnL 2x | PnL 3x | Unscored days | Gross-breach days |
|---|---:|---:|---:|---:|---:|
| Matched reference | -$22.20 | -$186.86 | -$351.52 | 27 | 0 |
| Preselected F0_h7 | +$14.90 | -$38.04 | -$90.97 | 16 | 0 |
| F0_h14 | -$45.55 | -$228.26 | -$410.97 | 33 | 3 |
| Other ten policies, each | $0.00 | $0.00 | $0.00 | 0 | 0 |

The other ten policies never opened a validation position. Their zero PnL is
inactivity, not a successful strategy. No policy ended with an open leg or a
reported insolvency. F0_h7 had $74.33 funding proxy, -$6.50 price PnL and $105.87
cost at 2x. Only **238/273** days were common to all eligible return streams;
the frozen rule therefore did not run SPA or the selected paired inference.
No p-value, confidence interval or paper candidate is claimed.

## Diagnosed acquisition defect

Every one of the **1,318 missing interior Lighter funding hours** lies exactly
on a 700-hour query seam of our collector. BTC alone has 16 such holes.
Thirty-day complete funding means cannot survive this roughly 29-day gap pattern;
the gaps also interrupt the 14-day eligibility histories used for basis labels.
Thus the absence of F1/B trades does not establish that those methods are useless.

A bounded public query with BTC's missing 2025-05-26 04:00 UTC hour strictly
inside its request returned the actual source event (signed fraction 0.000012).
This corroborates a boundary-acquisition fault rather than a genuine zero
payment. The old dataset, frozen collector, specification and results remain
unchanged. **R311** repeats the same twelve policies after obtaining the missing
source events in a separate cache; it may not change any economic parameter or
rescue a validation winner. Both rounds count toward the same decision group and
the program's trial history. No interpolation or retrospective zero filling is allowed.

## Verification and limits

- All 11 result artifacts reproduced byte for byte in a separate output folder.
- Independent signed-ticket/source-settlement reconstruction checked **40,716**
  venue/day/cost-tier balances; maximum absolute difference **$3.55e-11**.
  This checks the proxy arithmetic, not the missing payments or index/fair prices.
- The old registry byte prefix is unchanged. Twelve trials bring the program
  total to **9,478,770**. The received-source intake remains one canonical bundle.
- Full suite before freeze: **1,054 tests, two skips**. On environment resumption,
  all **38 focused tests** passed again.

The parent acquisition used 6,428 requests and 229.6 MiB response bodies, within
the approved combined 8,000-request/250-MiB limit. R311 must keep its incremental
requests inside that same remaining budget. The historical universe/rules are
snapshot-conditioned, the dates are spent, MEXC funding needs fair price and
Lighter needs index price. Historical fills, margin and executable net gain are
unproven. **No prospective lane is activated from R310; prospective evidence is zero.**
