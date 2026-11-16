# Newcomer review of /home/user/T (lens: simple)

## Summary (120 words)

T is a pre-registered lab that tests crypto-perpetual trading rules and tracks "forward" paper trades. Nothing has passed forward paper, yet the docs show 13 CONFIRMED verdicts and about 46 running lanes, so status is hard to read. The main traps: README says MEXC is the first venue, but its own audit says MEXC does not serve French residents. The README index is a 160-line changelog. PANEL.md is two days old and contradicts itself (17 vs 46 running lanes; "1 strict on-time day" vs "25 on-time days"). DIRECTION's "Now" is dated 2026-10-28. Two OPERATIONS files and two room numbers (#7, #71) add noise. I would keep five documents (README, a French glossary, AGENTS, a one-page DIRECTION, PANEL), merge or archive the rest with banners, and leave frozen experiment files untouched.

## 1. What I believe after 20 minutes

The project is an automated research lab. It writes down trading rules before testing them, runs them on historical data, then follows the survivors on new days as paper trades. The goal is positive return after fees, funding and slippage. No real money has moved.

What it has found is unclear to me. Most rounds read NULL and some PARTIAL. The docs say nothing counts as an edge until it passes several gates, yet the verdict list includes 13 CONFIRMED (e.g. `experiments/README.md:73`, R483). I could not tell whether CONFIRMED means "edge" or "test passed". The README says the project is in a state that depends on the 2026-11-07 Codex transfer, but I could not see what that transfer changed.

What is happening now is what I am least sure about:
- `README.md:23-24` says Codex is the single scheduled writer. `docs/PANEL.md:3` says it was rebuilt on 2026-11-14 "at the end of each tick", two days before today, so either the tick stopped or the panel is stale.
- `docs/DIRECTION.md:9` has a "Now" section dated 2026-10-28, with 2026-11-02 additions inside it.
- `docs/loop/PROMPT.md` is described as self-edited instructions run every 3 hours (`README.md:100-101`). I cannot tell from the docs whether it runs.
- The facts I know about the email flood, the paused loop and the venue-access shift came from the fact pack, not from the eight sources I was asked to read. A newcomer would not learn them from those sources. That is itself a finding.

## 2. The ten most confusing things

1. **MEXC contradiction.** `README.md:5` says "MEXC perps first", while `README.md:172-174` says Binance, Gate, MEXC and KuCoin do not serve French residents with perps.
2. **CONFIRMED with no meaning given.** `experiments/README.md:12` defines verdicts but not what CONFIRMED means for an edge (see section 1).
3. **Running-lane counts disagree.** `experiments/README.md:17` says 46 running or armed; `docs/PANEL.md:29` says 17 paper lanes; the fact pack says 67 RUNNING or REGISTERED.
4. **Paper-day counts disagree inside PANEL.** `PANEL.md:30` says "Strict on-time paper days so far: 1"; `PANEL.md:40` says R215 has "25 / 90 on-time days".
5. **Stale "current" dates.** PANEL is dated 11-14 (`PANEL.md:3`), today is 11-16; DIRECTION "Now" is 10-28 (`DIRECTION.md:9`).
6. **Two rooms.** `AGENTS.md:42` and `README.md:107` say issue #7; `README.md:29` says "room #71"; `PANEL.md:16` says "room #7".
7. **Two OPERATIONS guides.** `README.md:18` links `docs/guides/OPERATIONS.md`; `README.md:23` links `docs/OPERATIONS.md`. Operator setup also appears in HANDOVER.md and handover/SCHEDULED_CHECKS.md.
8. **Unexplained jargon.** M290, R400, C14, C17, "book A/B/X2", "gate 0-4", "NW t", "1x/2x/3x", "reserved sample", "futility", "S" (`AGENTS.md:3`). The French guide explains only M and R (`START_HERE.fr.md:23-25`).
9. **REFUSED appears in one place.** `START_HERE.fr.md:29-30` defines REFUSED, but it is absent from the verdict list in `experiments/README.md:12` and from the fact-pack verdict counts.
10. **Index is a changelog.** `README.md:118-278` is about 160 lines of R-number prose inside a `<details>` block, although the README says folder docs "do not maintain separate... changing result counts". Also `AGENTS.md:18-20` mixes dated owner instructions with rules.

Smaller items: `AGENTS.md:41` names a ROADMAP that is not in the `ls docs` output; the experiment folder names (`carry_*`, `xfund_*`, five `xfund` variants) are unexplained; `program trials 9,785,313` (`PANEL.md:28`) has no explanation.

## 3. Five documents for a newcomer

1. **README.md**: what T is in five sentences; the five gates; the three authorities (methods.csv, rounds.csv, each lane's PREREG/FINDINGS); one dated "now" line that links to PANEL; the venue question answered once; a link list of at most 20 entries.
2. **START_HERE.fr.md** (with an English mirror): the glossary. Every id, status word, verdict word, gate, cost tier and letter-book, each with one example and where its definition lives.
3. **AGENTS.md**: the 8 hard rules only, in plain words. The dated owner directives move out (see section 4).
4. **DIRECTION.md**: a one-page "Now" at the top: objective, cost wall, running lanes with their decision dates, what was ruled out, and the owner's latest instruction with its date.
5. **PANEL.md**: the generated status page. It needs a banner that says how stale it is versus today and which numbers it does not reconcile.

Everything else is reference, not reading.

## 4. What to delete, merge or archive

No frozen file changes. Check inbound links with grep before any move, because `README.md:281` says docs stay at their paths because frozen PREREGs link to them. "Archive" therefore means a banner plus removal from the index, not a move.

- **Merge** the operator docs (`docs/OPERATIONS.md`, `docs/guides/OPERATIONS.md`, `docs/HANDOVER.md`, `docs/handover/SCHEDULED_CHECKS.md`, `docs/loop/STATE.md`) into one page. Leave the old ones as short stubs.
- **Merge or banner** the seven proposal and coverage documents that AGENTS.md says must not be competing task lists: NEXT_SEARCH_SPACE, RESEARCH_FRONTIER, RESEARCH_HANDOFF, RESEARCH_COVERAGE_LEDGER, LEADS, IMPROVEMENTS_20261105, and `research/HYBRID_REVIEW_20261029.md`. Their open items should live in `registry/methods.csv`.
- **Archive** `docs/METHODS_QUEUE.md` (a historical snapshot) and `docs/EDGE_SCOREBOARD.md` (current only through R363) with banners.
- **Move** the R441 to R481 narrative out of `README.md:118-278` into a dated digest under `docs/reviews/`. Keep one line in the README.
- **Trim** DIRECTION.md to its top section and keep the 900 lines below as an archive with a banner.
- **Index** the experiment folders by family in one generated list. Do not rename folders.
- **Do not touch** `experiments/*` frozen folders (byte-identical), `docs/provenance/*.json`, `registry/rounds.csv`, `ledger.csv` or forward journals. Fix the reader, not the record.

## 5. If you only read one thing

1. T is an automated lab that tests crypto-perpetual trading rules against rules fixed in advance.
2. Its goal is a rule that still makes money after fees, funding and slippage, on days it never saw.
3. So far there are hundreds of tests. Most found nothing, some found partial signs, and none has passed forward paper.
4. Read status from `registry/rounds.csv` and `registry/methods.csv`, not from prose written weeks ago.
5. M is an idea in the queue, R is a tested round, C is a candidate inside a round, and "book A/B" is a variant.
6. A lane's real scope is its PREREG.md (frozen rules) and FINDINGS.md (result).
7. Costs are the wall: most gross effects are smaller than fees and funding. Report at 1x, 2x and 3x.
8. Never edit frozen files or hand-edit journals. No orders, no credentials, no deleted data. Read AGENTS.md first.
9. Check the timestamp on `docs/PANEL.md` before trusting any "now" statement; it is generated and may be stale.
10. The owner decides about real money. The lab only produces paper evidence.

## Limits of this review

I read only the requested slices. I did not run `python -m lab find`, `integrity` or `catalog.py --check`. I did not grep inbound references, check whether REFUSED exists in `registry/rounds.csv`, or confirm the 46 versus 67 counts. I did not read GATES.md, OPERATIONS.md or the PANEL past line 80. The claims about the email flood, the paused loop and the Codex end date come from the fact pack and are unverified here.
