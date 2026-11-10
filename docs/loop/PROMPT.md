# Edge loop: the instructions each scheduled tick follows

Written by Claude on 2026-11-09 at the owner's request: "make the best prompt to steer us toward several ways to make
PnL on these markets; go anywhere (web search etc.) for an edge; make every deduction possible; a strategy does not work
all the time; launch Haiku subagents each time for new ideas; we want HFT or anything else where we are positive; think
about why firms like Jane Street succeed and we do not, and whether we would with their infrastructure; a
self-improvement loop on cron; change your own cron prompt as you advance; autonomy to find a flaw."

This file is the loop's working prompt. Claude edits it when a tick shows a step was wasteful or a better rule exists,
and logs every edit in the changelog at the bottom. `AGENTS.md` overrides anything here.

## Objective (owner, 2026-10-24 and 2026-11-09)
Find a reproducible positive net return at executable costs and comparable capital and risk, then genuinely new
prospective paper evidence. HFT is welcome where it is reachable; anything else that is net positive is equally
welcome. Public institutional practice is a reference, not access to anyone's strategy. A null is a result.

## Hard limits (never relaxed by this loop)
- **The AGENTS.md hard rules.**
  - Register and freeze before measuring.
  - Frozen files are never edited.
  - Journals are append-only.
  - One writer per file.
- **No real orders, money, credentials or deleted data.** Real money only through `lab.gate.go_real()`, placed by the
  owner after paper proves a net gain.
- **No large downloads without the owner's explicit yes,** and no paywall or login bypass.
- **No loosened gates, fees or source rules to manufacture a hit.**
- **Every result is read against `registry.program_trials()`,** with costs at 1x, 2x and 3x.
- **Subagent output is a claim to verify, not evidence.** Never paste it into a FINDINGS as fact.

## Our real constraints (update when measured, with the lane id)
| Constraint | Value | Source |
|---|---|---|
| Decision-to-arrival delay | ~250 ms RTT through the agent proxy; 274 ms median in R431 | R431 |
| Feed reliability | Python consumer queues 1-35 s in bursts; local clock drifts up to 30 ms a minute | R431 plumbing |
| Host | Chat container; sleeps between sessions; no always-on recorder | R367, OPERATIONS.md |
| Fees | Binance USDC perps 0 maker / ~4 bp taker (secondary source); MEXC API 6/8 bp; Lighter Standard 0/0 with 300 ms taker delay; Hyperliquid 1.5/4.5 bp | docs/VENUE_STRUCTURE.md |
| Capital, jurisdiction | ~$10k, owner in France (EEA routes; prediction markets not legal for the owner) | docs/LEADS.md |
| Benchmark | Binance internal catch-up: median 7 ms; USDC taker 1 s markout +0.55 bp vs 0.01-0.04 bp spread | R431 |
| Fee tiers | Binance LP rebates (−0.6 to −0.8 bp on USDC-M) need ≥ 0.2-1.5% of weekly maker volume and $100M of volume in 30 days to apply: unreachable | Binance announcement, verified 2026-11-09 |
| Access | Lighter's stream refuses the native runner's jurisdiction (HTTP 400, code 20558); no workaround | R428 |

Read `docs/INFRA_GAP.md` before choosing a test: it decomposes why fast firms win and which of their edges a slow,
small, public-data player can still reach.

## Each tick, in order
0. **Guard (5 min).**
   - `git pull` the branch `claude/yo-9a1k5w`.
   - Read fresh writer claims on issue #7, open PRs, and `docs/loop/STATE.md`.
   - Respect any fresh claim, and never start a second writer.
   - Handle anything due first: a PR event, a dated duty in `docs/OPERATIONS.md`, a check-in.
1. **Ideas: launch 2-3 Haiku subagents in parallel.**
   - Use `model: haiku`, in the background, and give each a different lens from the rotation below. Take the next
     lenses after the ones `STATE.md` lists as last used.
   - Give each one: the constraint table above; the read-only rule; web search allowed; no login, paywall, large
     download, order or credential; grep `registry/methods.csv` and cite the nearest Mxxx or say NEW; at most 900
     words; a URL per fact; UNVERIFIED where unsure.
   - Ask each for: the mechanism (who pays and why they accept it), frequency, the latency, fee and capital needed,
     public data, and a falsifiable kill test.
   - Give each the list of families already spent, so they do not rediscover them. In tick 1, about 25 ideas gave one
     new row. The spent families: latency leads and taker scalps (R348, R431); maker entries (R193, R194); USDC
     making; unlock shorts at D-7 and D-30 (M057 in forward test, M072); carry and crash gates (M136, R391); VRP (R409-R411); momentum and ML ranks
     (R263, R299, R304, R305, R332); settlement hops (R354, R363); listing fades (R188, R189). Ask for the gaps between them.
2. **Deduce.** While they run, and again on their output, reason it through. Write the conclusions down; do not
   just collect them.
   - **Who pays, and why have the fast firms not taken it?** Acceptable answers: capacity too small for them; outside
     their mandate or venue list; needs patience or a long hold; a speed bump or rule neutralises their speed; a
     barrier we can cross and they cannot. If none fits, the edge is probably noise or already gone.
   - **Does it survive our constraint table?** Compute the arithmetic before any data: gross needed vs fees ×2, our
     delay vs the decay time, and capacity at $10k.
   - **When does it work, and when does it fail?** A strategy does not work all the time. Name the regime variable
     **before** looking (volatility, funding level, open interest, an ETF-flow era, listing age, venue share). Make it
     computable at decision time. Count every regime split as trials. Never pick the regime after seeing the returns.
   - **What would the result change?** Prefer the test whose outcome most changes what we do next (value of
     information), not the most exciting one.
   - **Infra counterfactual.** Would Jane Street-class infrastructure flip it? If only infrastructure would, record it
     in `docs/INFRA_GAP.md`'s ledger and move on: we do not have it.
3. **Integrate.**
   - Verify the 1-3 claims that would create a queue row (official doc, paper or our own data).
   - Add NEW methods to `registry/methods.csv` and the source extraction to a dated `research/intake/` file, following
     `research/intake/README.md`. Run `python -m lab integrity`.
   - Duplicates get one line in the intake file pointing at the existing M-id, not a new row.
4. **Act: one real increment per tick.** In order of preference:
   1. **A registered test.** Claim an R-id on #7, write the PREREG with an `inputs` block, freeze it, register, commit
      and push. Then run once, write FINDINGS with 1x/2x/3x, close the registry row and update the methods row.
   2. **A measurement that unblocks a high-value test,** within existing budgets: a recorder, a public metadata
      fetch, a cost qualification.
   3. **If nothing is testable,** write down in `STATE.md` why, and change the lens rotation.

   A tick that only adds plans has failed: say so in `STATE.md`. Synthetic dry-run the runner before freezing. A crash
   after the freeze wastes the lane (R347).
5. **Learn.** Append one line to the tick log in `STATE.md`: date, lenses, ideas in/out, the test and its verdict, and
   the deduction that changes the next choice. Update the constraint table if something was measured. Keep `STATE.md`
   short: the queue lives in `registry/methods.csv`.
6. **Self-improve.**
   - If a step wasted time, produced nothing or repeated a passed check, edit this file. Add a changelog line with the
     reason.
   - If the scheduled prompt needs to change (cadence, focus, a new standing duty), call `update_trigger` on
     `trig_016TEUgXKYYAQzELorwi9buf` with a new prompt. Keep it short: point at this file and carry the current focus
     line.
   - Change cadence only with a reason. Slow down after 3 ticks without a new test; never schedule duplicate loops.
7. **Publish.**
   - Run `.venv/bin/python -m lab check --suite fast`; run the full suite before committing `lab/`. The system
     `python` lacks the lab's packages and reports dozens of false errors. On 2026-11-09, HEAD had 3 known errors:
     one in `test_input_contracts` (`dataclasses.replace` on an `init=False` field) and two in
     `test_level_probability` (read-only arrays). Any other error is new.
   - Commit, push, and keep PR #1 current.
   - Post on #7 in the room's short format: CLAIM before a test, FYI with the result.
   - Message the owner in French only when a test produced a result, something failed, or a decision is theirs.

## Lens rotation for the Haiku helpers
1. **Fast firms' playbooks:** Jane Street, Jump, Wintermute, XTX, Citadel Securities, Optiver, GSR. Which parts
   transfer to a slow, small, public-data player?
2. **Venue rules with a payer:** funding formulas and caps, mark and index or oracle timing, liquidation engines and
   ADL, vaults, listings and pre-market, rebate and zero-fee programs, RPI, speed bumps.
3. **Recent literature, 2023-2026:** strategies profitable after fees for slow, small traders, with 2024-2026 in
   sample.
4. **Regimes and decay:** when known edges work and fail, and ex-ante regime variables.
5. **Red team:** attack the lab's current leads (R391 carry, R300 forward, any PASS). How would they fail live?
6. **Forced and scheduled flow:** liquidations, unlocks, index and ETF rebalances, option expiries, settlement clocks,
   stablecoin mint and burn.
7. **Cross-market and barrier gaps reachable from France:** EEA venues, tokenized TradFi perps and their weekend
   pricing, DEX vs CEX, regional premiums.
8. **Market making for the slow:** speed-bump venues (Lighter's 300 ms taker delay), maker-protecting designs,
   inventory and toxicity models a slow maker can use.

## Changelog
- 2026-11-09: first version (Claude). Tick 1 run by hand right after writing it.
- 2026-11-09, after tick 1: two constraint rows added (LP-rebate thresholds, Lighter's jurisdiction refusal). The
  helpers now get the list of spent families, because about 25 ideas in tick 1 gave one new row. Step 7 now names
  the venv interpreter and the 3 known test errors. The scheduled task was moved to every 3 hours (the server
  anchored it at minute 30).
- 2026-11-09 ~22:45 UTC, owner: hunt mode. "Work continuously, not every 3 hours; the subscription ends soon; use
  100% of compute." Ticks give way to parallel forks, one lane each, with pre-assigned R-ids and a two-phase protocol:
  freeze and register, FROZEN, the orchestrator commits, GO, run once, FINDINGS, the orchestrator closes. Forks never
  run git or touch shared files. The scheduled task is now an hourly safety net. The owner also approved reading R392
  today.
- 2026-11-10, lessons from wave 1 (Claude):
  - **Dry runs pass the data path explicitly.** A default argument (`build(data=DATA)`) is bound at definition time,
    and R432's dry run read the real archive that way. Tests must refuse any read outside their temporary folder.
  - **The orchestrator writes FINDINGS.** The harness refuses subagent writes to FINDINGS.md, so a fork returns the
    text and the orchestrator saves it with a provenance line.
  - **Regenerate the catalogs after staging a lane** (`scripts/catalog.py`), or CI's offline check fails with STALE
    READMEs.
  - **Close registry rows inside `registry._lock(path)`,** because forks append rows at the same time.
  - **Pace the forks.** Six parallel Opus forks hit the 5-hour limit. Run two or three at a time, and give reading
    to Haiku.
  - **Run plumbing before claiming an R-id.** R437's oil check was stopped at plumbing: only 3 of 8 weekends had
    traded. No trials were spent.
  - **Never edit a file that any PREREG hashes.** `docs/GATES.md` is a frozen input of earlier lanes. Check
    with `grep -l "docs/GATES.md" experiments/*/PREREG.md` before editing any doc. Record owner decisions in STATE.md
    or in the lane's PREREG.
- 2026-11-10: never run `scripts/catalog.py` or add or edit files under `lab/` or `scripts/` while a forward
  orchestrator batch runs. It hashes those trees as code and marks a task FAILED if they change (R404 and R278 on
  11-10). Their ticks still completed. Wait for the batch, or regenerate catalogs only after it ends.
- 2026-11-10: R406 (lockcarry_fwd2), R413 (boroslock_fwd) and R419 are written by Codex's GitHub runtime (`.github/workflows/quant-paper-priority.yml`, canonical state on `codex/quant-runtime-state`, hourly since 11-07). Never run them through the local orchestrator: a local run on 11-10 08:14 made the branch journals diverge and failed the `paper` check every hour until the six files were restored to their pre-run versions. Before restarting any forward lane, check that runtime's manifest for the lane's journal paths.
