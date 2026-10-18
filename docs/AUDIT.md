# Audit: where the structure was wobbly

Read from the session transcript, not from the real repo. Each item says what was seen, why it matters, and the fix. **Evidence** is stated; anything beyond it is marked as inference. Ranked by how much it could mislead a decision about money.

## What is already solid (keep it)

Pre-registration with a hash; a survivorship-free point-in-time universe; a holdout never used for selection; a full-pipeline null instead of a per-cell p-value; a BETA-ONLY flag; a frozen forward spec checked against its hash before every score; the go-real gate; and honest nulls. R182 searched 139,377 trials, found nothing and said so (p=0.217).

## A. Decision risk

1. **No program-level multiplicity.** *Evidence:* 183 rounds; each lane tests against its own null. The owner also asked for a deep dive into the unlock finding once it looked promising, and that deep dive is R181. *Risk (inference):* across that many lanes, some will show t>4 by chance, and a follow-up chosen because a result looked good inherits that selection (R181: t=4.06). *Fix:* the `trials` column in `registry/rounds.csv`; read any lane against `registry.program_trials()`; treat only the forward ledger as confirmatory. R181 stays "in-sample" until it is scored.

2. **Forward gate counts correlated tickets.** *Evidence:* 364 tickets with shared entry dates (10-13, 10-16, 10-18...); R181 lists "BTC-down" as a HINT. *Risk:* 20 scored tickets can come from two or three market days, so the gate could pass on a handful of independent observations. *Fix:* `go_real(..., entry_days=...)` reports `n_clusters`. The rule is the owner's, so it is reported, not gated. Suggest the owner also require a minimum number of clusters.

3. **Flat cost, liquidity-blind.** *Evidence:* `COST = 0.002` for every symbol; the R181 edge sits in tokens whose unlock is large relative to daily volume. *Risk (inference):* those are likely the thinner markets, so a flat cost may flatter exactly the trades where slippage and funding are worst. *Fix:* a cost tied to a volume bucket, pre-registered, or at least a sensitivity row at 2x and 3x cost in every FINDINGS.

4. **Backtest venue differs from trade venue.** *Evidence:* ratios use Binance volume; forward tickets use MEXC prices and funding. *Fix:* the forward ledger already uses MEXC, which is right. Record in each PREREG which venue each number comes from.

5. **The tick prompt rewards finding a winner.** *Evidence:* "ask yourself what single next step most raises the chance of real positive PnL". *Risk (inference):* an agent optimizing that, with no cap on exploratory rounds, drifts toward p-hacking. *Fix:* item 1 plus a budget: exploratory lanes per week, declared in `AGENTS.md`.

## B. Reproducibility

6. **The hash covers the spec, not the code or data.** *Fix:* every `ledger.csv` row records `prereg_sha`, the code commit and a data-manifest hash.

7. **Universe drift.** *Evidence:* R182 used 900 symbols including TradFi; R164 used a filtered 806; R183 selects current survivors. *Fix:* a universe manifest (symbols, filter rule, hash) that each PREREG cites.

8. **Resolution of the family-wise p.** With 60 replicas the smallest nonzero p is 1/60. `familywise_p == 0` means "below 1/60", not zero. Quote it that way. More replicas on the GPU would fix it.

## C. Engineering

9. **Hand-edited CRLF files.** *Evidence:* ROADMAP and AGENTS edited by binary replace and `printf`; a `%%` bug in the R180 row. *Fix:* `registry/rounds.csv` is appended by code, LF only; ROADMAP.md becomes a rendering of it. `.gitattributes` stops git rewriting frozen specs.

10. **Id allocation by eye.** *Evidence:* "verified none of R182-R189 exist" before writing. With two AIs that is a race. *Fix:* `registry.append()` allocates under a lock.

11. **Single-writer by convention.** mtime checks work until two sessions check at the same moment. Fix: an `OWNERS` line per lane in its PREREG, and the lock above for shared files.

12. **Machine paths in rules.** The Python path and user directories sit inside AGENTS.md. Use one `PY` variable.

13. **Stray artifacts.** `results_run.log` duplicates `progress.log`; `cache/` is ~105 MB. Ignored here; document what rebuilds them.

14. **Two engines, one spec.** CPU and GPU searches duplicate the gating logic. The ~1e-9 parity test is the right contract. Keep it as a required test, and extract the gate into one function both call.

## Not audited

The real code and data, the first day of the session, and the lanes I only saw as one-line verdicts (funded, challengeoption, conscience, grandgrid, the listing listener). Anything said about them is from those one-liners.
