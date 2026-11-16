# E. Critic (Sonnet): attack on the 2026-11-16 synthesis and STATUS.md

Read-only. I ran `scripts/lane_census.py` (69 open rows; codex 16, no-writer 13, no-writer-recent 2, workflow 38: matches). I checked the 2027 dates against the PREREGs (they are right). The problems are elsewhere.

1. **HIGH. The closing pass has no legal mechanism.** `stepback_20261116.md` s.6 item 1 says each no-writer row gets "a status that says so". `lab/registry.py` has only `append()`; ids are unique (`registry.py:73`) and no code path changes an existing row. AGENTS.md rule 3 forbids hand-editing a row. Reviewer B flagged this exact doubt (B_organisation s.3 end) and the synthesis dropped it. The closing pass would either hand-edit `rounds.csv` (a rule 3 breach) or do nothing. Also, `STATUS` s.2 says "A closing pass is the next maintenance item" without saying how. Fix: before any closing pass, ask the owner to rule on one mechanism (a new append-only `registry/lane_events.csv`, or an `append`-style status-event row), and state it in STATUS. Until then, closing notes go in FINDINGS only and `rounds.csv` is untouched.

2. **HIGH. "Ids claimed on a branch that does not merge within 7 days are free again" (s.5, STATUS s.4.7) can break frozen lanes.** A frozen PREREG, registry sha and workflow may already name that id. Re-issuing it collides with hashed inputs and with rule 2. Fix: delete the rule. Make the unmerged id permanently burned, or "unmerged ids are never reused".

3. **HIGH. The carry claim is overstated and the contrary evidence is left out.**
   - STATUS s.1 and s.1.2 of the synthesis: "one premium survives" and "forward lanes ... are the ones that answer it".
   - README:172-174 (venue note) records that the DEX-only book (Hyperliquid + Lighter) "earned below the T-bill on seen rows". That is the French-usable version of carry, and STATUS omits it.
   - The surviving numbers (C14 +2.86%/yr, R391 +2.48%, R392 +0.73% at 1x only) are not shown against the bill rate. "Premium" is undefined until they are.
   - Per the synthesis's own words, the survivor is untradable from France, and the French-usable version has seen-sample evidence below the bill. So: "no tradable premium has survived" is at least as supportable as "carry survives".
   - It is also not the only survivor. README:178-181 reports HLP/LLP vault yield (~+10.7%/yr) and R447 +10.04%/yr (t 3.94 on seen rows), and hedged JLP +43.9% in 2024. These are seen-sample and carry short-tail risk, so they are not "confirmed on reserved data". But "the only premium" is false as written. Fix: say "the only edge confirmed on reserved data; the French-usable form tests below the bill on seen rows", and list vault yield as unproven.

4. **MEDIUM. The carry decision date is misstated.** STATUS s.1: "reading from 2027-02 on". Per the PREREGs (`tltcarry_fwd:86-87`, `hip3carry_fwd:122-123`), 2027-02-13 is futility only; it can stop a lane but cannot pass it. Earliest PASS is 2027-05-15. Also R474/R479 are TLT and HIP-3 stock carry, not crypto perp carry. The lanes that answer the crypto question (R441/R443/R445, count-based) have no date in the table. Fix: state "earliest possible positive answer 2027-05-15, and for crypto carry see each PREREG".

5. **MEDIUM. The census list in STATUS is wrong in small ways.** STATUS s.2 names 12 ids for "13 rows": R419 (REGISTERED, last commit 2026-11-07, not Codex-owned) is missing. R369 is REGISTERED, not a "container daemon". R286's last commit is 2026-11-03, not 11-06. The census only tests "lane name appears in a workflow file and `git log` shows a commit under `experiments/<lane>` within 7 days". It does not confirm the workflow is enabled, succeeds or writes data. And `git log` depends on checkout depth. "38 live forward lanes" (the cap in principle 3) includes R404, which closes on 2026-11-18, and R200, which is merely REGISTERED. Fix: add the R419 id; define "live forward lane" as an explicit list; add a "workflow ran in 48 h" column or stop calling the class "live".

6. **MEDIUM. The charter is unenforceable as written.**
   - "Weekly" census, 48 h workflow check, French note and STATUS rewrite have no scheduler. The owner paused the hourly wake-up on 2026-11-13; the synthesis forbids agents from re-enabling any wake-up (s.5 "owner decides ... re-enabling any recurring wake-up"). Nobody runs the weekly check unless the owner opens a session.
   - "Bots never notify the owner" contradicts the "one note a week": that note is an agent action with no trigger.
   - "At most 3 new rows a week" is checked by nobody, and it collides with the owner's 2026-10-24 mandate (AGENTS.md "Owner working mode") to continue autonomously.
   - "Within 7 days draft PRs merged or closed" has no actor; PRs #97-#100 are already past it.
   - Fix: say plainly that every cadence item runs "at the next session, if any". Put any freshness check inside an existing workflow, for example a scheduled CI job that fails loudly if STATUS is older than 14 days. Offer the owner the choice of a single weekly scheduled task, and do not assume it.

7. **MEDIUM. Agents are not entitled to some things in the charter.**
   - "Keep any capital in bills" (s.3.1) is investment advice from an agent to a non-technical owner. AGENTS.md rule 6 only says real money waits for a paper pass and the owner places it. Say "no strategy has passed the gate; the default under the rules is no trade", not "keep capital in bills".
   - "Agents, without asking: ... new lanes within the limits" is fine. "Whether agents act in their name" and "stopping or budgeting compute" are listed as owner-only, yet agents closing PR #1 on their own initiative was exactly that kind of act. It is reversible and was disclosed, but the charter should not imply this was standard authority.
   - Also, `AGENTS.md` says "Do not loosen gates"; principle 3's caps are stricter, which is fine, but principle 6 ("new reels checked against the record") must not add a skipped-research rule; the owner earlier asked not to drop ideas without research.

8. **MEDIUM. The "philosophy" leans toward despair and presents arithmetic as honest.**
   - "tens to low hundreds of dollars a year" (s.3.3) assumes 2.5-3%/yr on $2-5k with no cost, which is the very thing s.1 says is the problem. After cost the figure may be negative. It is labelled "arithmetic", which is honest, but it anchors the owner on a small positive number the evidence does not support.
   - "128 NULLs protect against false despair" is rhetorical: 128 nulls are also a multiple-testing record, and counting them as comfort is the same mistake as counting 9.8M trials as rigor, which the synthesis itself rejects in s.1.
   - Counter-hope is also missing. The unproven candidates (vaults, hedged LP) are not mentioned as candidates.
   - Fix: state three outcomes: (a) no tradable edge found, (b) carry too small to matter, (c) unproven candidates still in forward test. Do not give a dollar range.

9. **LOW. STATUS says the PR #1 fix is complete; the synthesis says "no workflow changed".** The cause (default branch = bot push branch) remains. Any new PR from that head re-creates the e-mails; the rule is only a sentence in a doc. A branch-protection or repo-notification setting is the actual fix and is owner-only. Say so.

10. **LOW. Dangling and stale links.**
   - `stepback_20261116.md:207` links `stepback_20261116/E_critic_sonnet.md`, which does not exist until this file is copied there.
   - README:5 still says "MEXC perps first". The synthesis says the README was corrected, but I read it unchanged.
   - "24 claude-* workflows" matches; 30 total files. The workflow count of "27 scheduled" in B differs; harmless but unreconciled.

11. **What all five views missed.**
   - **Who verifies the verifier.** All views trust the forward journals the bots write to the default branch. No one checks that the data actually arrives (gaps, GitHub's auto-disable of scheduled workflows after 60 days without repo activity, quota). The "48 h workflow ran" check is the right idea but has no code.
   - **The owner's real question is asked and answered by no one in French.** `docs/guides/START_HERE.fr.md` is cited, but STATUS is in English only; the owner is French-speaking and non-technical. The one weekly note is the only French output. Fix: add a 10-line French summary at the top of STATUS.
   - **Rules 1 and 2 versus the new "decision first" rule.** Retro-fitting "monitoring" labels onto already-frozen lanes (s.5 principle 2 of philosophy) is itself an edit of frozen scope. Apply it to new lanes only.
   - **Compute and attention cost of the fix.** The review took five model runs to conclude "do less"; the proposed closing pass, integration batch and PANEL rebuild are 4 more work items. None has an end condition or budget.
