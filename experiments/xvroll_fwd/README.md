# xvroll_fwd (R482)

Forward paper lane for M533. Short trade.xyz's NATGAS perp and long Lighter's at equal notional. Both are priced from
NYMEX Henry Hub futures, so the commodity and (mostly) the roll net out, and the pair keeps xyz's funding minus
Lighter's. R481's post hoc found xyz longs paying +0.77% of notional a cycle more, over six cycles chosen after the
fact; this lane tests it on new weeks from 2026-11-16. NATGAS decides; WTI and BRENTOIL are reported.

- `PREREG.md`: frozen book, reads, power and what the author had seen.
- `results/futility/` (after 2027-05-15) and `results/final/` (after 2027-11-13): written once each by
  `.github/workflows/claude-xvroll.yml`.
- Code: `scripts/run_xvroll.py`, `tests/test_xvroll.py`. Inputs are fetched at each read (xyz and Lighter public
  APIs, ^IRX), plus R480's recorded xyz 1-hour candles (`claude/futroll-data`, read only).

Paper only. No order, no money, no key. Both legs are France-reachable perp DEXes margined in USDC; no futures broker.
