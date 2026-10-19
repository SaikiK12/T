# Research handoff: adjacent work

Current snapshot: Claude's branch `claude/yo-9a1k5w`, commit `95efda7` (R212). Its open pull request says an adversarial audit of the forward pipeline and the R205-R212 scripts is in progress. The code contribution here is limited to research-artifact bookkeeping so that audit can continue in its own area.

## Read-only integrity check

Run `python3 scripts/check_research_integrity.py` from the repository root to inspect the round registry and the local experiment specs without opening market data. It checks registry structure, frozen `PREREG.md` hashes, links between local specs and registry rows, and basic artifact presence. It reports imported rounds whose lane folders are absent because earlier project files are not in this checkout. The planned R184 spec is an allowed unfrozen draft. `--strict` also returns a failure status for warnings; `--json` emits a machine-readable report.

This is a bookkeeping aid, not a research audit. It cannot show that a spec was frozen before anyone measured a statistic, that code or input data match the spec, or that results are sound. It does not repair files or alter the append-only registry.

## Candidate: forward monitor for funding carry

R191 explicitly names a forward monitor as its next step. The existing rule is short the perp and hold spot when trailing 72-hour settled funding exceeds 20% APR; exit below 10% APR, or when liquidity or a spot pair is unavailable. Holdouts end on 2026-09-30, so future collection can begin without re-reading that period.

Before collection, register a new forward lane and freeze its entry, settlement timestamp, spot-pair eligibility, premium-index and funding snapshots, missing-data handling, and 1x/2x/3x cost reporting. Keep it paper-only and append dated observations through the existing journal code. The point is to learn whether positive carry returns under current funding regimes; no new return claim follows from the historical holdout.

Evidence: [R191 findings](../experiments/carry_holdout/FINDINGS.md) and [the frozen R191 rule](../experiments/carry_holdout/PREREG.md).

## Candidate: complete copy-leader forward inputs

The C02 test calls for weekly selection from 180-day leaders ranked by 30-day PnL, plus hourly position histories for the selected leads. The current [leaderboard collector](../scripts/scrape_leaderboards.py) captures Binance's 30-day list and OKX's public leaderboard, but does not request the 180-day eligibility list or hourly lead positions. As a result, the requested persistence and copy-book test cannot yet be reproduced from its snapshots.

A separate forward-only collector can add dated 180-day snapshots and position records while leaving the current files intact. Define stable lead IDs, observed-at times, endpoint coverage, empty or stale responses, pagination completeness, and retry-safe writes before scheduling it. Then freeze the selection and scoring rules in their own lane. These sources provide survivor-biased forward observations; they do not supply an unbiased historical backfill.

Evidence: [C02 mechanics and limits](../docs/CLAIMS.md) and the collector's current request and output paths in `scripts/scrape_leaderboards.py`.
