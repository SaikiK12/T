# Received-source extraction for the single methods queue

The operating panel is `docs/PANEL.md`; the live methods queue is `registry/methods.csv`. Files here are source-reading inputs, not another priority list or authority to run a study.

`source_catalog_20261020.csv` contains 30 provider or publisher entry points across market microstructure, options, on-chain lending/MEV, macro vintages, news, institutional data and practitioner media. Each row states the actual received scope, access boundary, existing queue relationship and unresolved verification. This is a source directory, not another methods queue: catalog discovery does not mean full-text extraction, possession of a dataset or a tested trading rule. No paid/private corpus was accessed, purchased or bypassed. Subscription prices, trial eligibility and MEXC-specific coverage are not assumed.

`source_catalog_tooling_20261020.csv` reviews 24 engineering tools from official capability/documentation excerpts.
Each records its role, overlap with qx/current code, a conditional disposition, material limitation and one open
validation question. Eighteen GitHub entries also retain a separately captured HEAD commit, README path and SHA-256;
six documentation-only entries remain explicitly unpinned. README hashes identify source versions, not a code audit
or proof that a mutable webpage excerpt was served from that exact commit. No tool was installed or benchmarked.
CCXT additionally has a narrowly scoped review of three named MEXC adapter functions, with a pinned code link/hash;
the remaining tool code was not audited.

The useful distinctions from this pass are:

- hftbacktest models queue/latency but its replay cannot simulate our own market impact; tick inputs remain required.
- cryptofeed's reviewed support list marks MEXC **spot**; neither that nor CCXT's exchange listing proves the needed
  perpetual channels, settlement clocks or fee path work.
- The pinned CCXT MEXC `fetch_funding_rate_history` function reads one requested page and filters `since` on the
  returned rows. Calling it once with an old `since` must not be treated as proof of a complete historical backfill.
  An explicit bounded page/interval-coverage check remains necessary; this is source inspection, not an API test.
- Polars/DuckDB/DataFusion share parts of the query role. Their speed is unmeasured here; choose one bounded
  comparison before adding multiple engines. Polars documents fallback to in-memory for some operations.
- Hypothesis/Proptest/Criterion can target accounting invariants, cross-language parity and performance regressions.
  Randomized tests do not replace explicit boundary fixtures; benchmarks do not establish a trading edge.
- MLflow/DVC/Prefect overlap tracking, versioning and orchestration already held in Git/manifests/the loop. They are
  optional mirrors or candidates, not replacements for the frozen registry or an authority to launch new studies.
- OpenTelemetry is instrumentation rather than storage; Prometheus is operational metrics rather than exact cash
  accounting. ECharts and Lightweight Charts are views; the latter has explicit attribution requirements.

Every row's `open_question` is unresolved research, not a task scheduled to run automatically. Still-unreviewed
families include durable orchestration alternatives, lake/versioned storage, Rust dependency/security tooling,
document/transcript extraction, desktop/table-grid alternatives and deterministic feed-recovery protocols. Future
passes should examine those gaps or specific library code/issues, rather than relabeling this catalog exhaustive.

`source_methods_20261020.json` preserves the original 164 atomic method/claim records from CLAIMS, ALTCOIN_LEADS, CONCEPTS, SOURCES, Quantpedia and coverage notes, then appends 37 records from the two earlier Instagram reels, the three owner-provided TikToks and 12 additional public video sources, followed by a second 34-record discovery batch. Every media record retains whether it came from captions, an official recap/transcript, a description or a secondary summary. Weak, incomplete and contextual methods remain visible. This is not full-book/full-paper reading or exhaustive internet coverage.

`owner_scope_20261020.json` preserves four owner messages verbatim with UTF-8 hashes and 21 distinct received concepts. The six optional-axis concepts retain shorter-horizon/scalping, MEXC/other-venue futures, order-book inputs, leverage and confidence sizing; the follow-up adds an implementation workflow request. Related aliases now include M264 (scalp), M265 (leverage) and M266 (confidence carry), while M267 (settlement-window carry) remains a separate Claude-selected operationalization. Exact queue mechanics are not attributed to the owner. Separate audit notes identify reusable sizing helpers and missing weighted-ledger/account mechanics; they establish no profitability or probability calibration. The first 14 extraction objects and earlier literal sources/hashes remain unchanged. Existing family aliases do not create executable rules or extra market trials. M027's static optimizer study is in `experiments/optimizer_v1/`.

The six original source hashes and extraction provenance remain unchanged. The original two-reel transcript version is preserved in Git history and identified by its prior SHA in the consolidated digest. The new video intake was reconciled against existing methods before originally adding M234-M251 (source-IV M234 is now M284 after an earlier R257 claim was verified); several source components map to existing rows and do not create new tests. R231/R232 evidence paths are verified on the current base; R233's gate-selection result is reconciled separately. The negative-sign ALT1 source rule remains distinct from R219's positive-sign test.

All 250 source records map through `registry/methods_aliases.csv` to the existing live queue or an explicit context entry. Feature code and creator examples are not completed portfolio tests. Missing mechanics require formalization; a weak prior does not exclude a method. Source/method counts are not measured-market trial counts. Freeze each new finite study before measuring, preserve NULLs and report 1x/2x/3x costs. This intake adds only methods-queue rows and aliases; it does not change experiment rounds, frozen studies or forward journals.

The owner-requested Aleks Rosme account follow-up adds eight AR26 records from seven enumerated page/link references, bringing the bundle to 243 records/aliases. The earlier three TikToks were already present. Vendor Net Drift applications are explicitly distinct from creator-attributed rules; brochures and tool capabilities stay contextual. Full account enumeration and new speech transcripts were unavailable. The compact assessment is in docs/REELS_TRANSCRIPT.md; no new queue ID or strategy outcome was added.

The bounded MEXC mechanics follow-up adds six XM26 records from seven official-page excerpts: MMR-versus-leverage events, tick-size treatment, trigger-reference comparison, rejected-cover state modeling, index-source health and venue-specific funding-frequency transport. This brings the current bundle to 249 records/aliases; earlier counts describe their earlier snapshots. These are our unregistered proposals, not exchange recommendations or outcomes. Three standalone scopes have BLOCKED canonical allocations; other parent aliases are explicitly related scope, and the IN publication/effectiveness conflict is preserved. Three BLOCKED canonical rows were added after a room claim (current IDs M400/M401/M282; historical source IDs M280/M281/M282 preserved in collision receipts); no frozen specification, journal or strategy result changed.

The three distinct MEXC scopes have canonical BLOCKED rows M400/M401/M282 after reconciliation; original source M280/M281 allocations are preserved, while the live lab retains its different M280/M281 methods. They are unregistered; six source records do not count as six measured strategies.

The library pass adds ten provider entrypoints (30 total, plus24 tools) and one pinned QC Dynamic Breakout II source, now M283. At the prior intake snapshot there were250 source records/aliases; the live queue has since gained Claude's M261/M262 and the intake rows M235–M251/M280–M284 (source-IV now M284; original M234 is reserved for R257). A bounded follow-up read one pinned third-party Dynamic Breakout II implementation in full and found it materially diverges from the official method; this is source-fidelity evidence, not a method result. Directory entries remain discovery inputs, not extracted strategy corpora. Public access, subscription boundaries and failed QuantStart fetches remain explicit. The existing hourly automation now prioritizes bounded source/code/data extraction; its enabled state does not guarantee every execution or delivery.

`registry/method_id_reassignment_source_iv_M234.json` preserves the source-IV row, original alias/provider targets and claim lineage. Historical source-intake ranges retain their original M234 allocation with an explicit reassignment notice; current targets use M284. Source versions remain retained, and a reviewed-history entry names each accepted current digest.

`coinmetrics_community_inputs_20261021` in the existing JSON supplement records four Community input definitions for M092/M093, pinned official source versions and two tiny BTC/definition metadata responses. It distinguishes interval labels, calculation completion and historical availability; revised current-vintage data does not become point-in-time through a fixed lag. Current and estimated market cap differ, and active addresses do not supply search attention or holder concentration. Original methods/statuses and all queue rows are retained; no strategy outcome or large dataset was acquired.

`mark_price_contracts_20261021` records the bounded Binance/Gate mark-price contracts and source versions for a future M265 extension. It separates ignored activity fields, UTC coverage, preceding mark anchors and unresolved Gate timestamp roles. Binance archive paths are declarations, not inspected data; M269/R282 already covers the related wick factor. Synthetic code checks establish no observed history, liquidation fill or new PnL.

`blueshift_expert_allocation_20261021` enumerates nine rules, controls and allocator variants from three pinned official QuantInsti files, bringing the source bundle to259 records/aliases while retaining all272 queue rows. The no-regret example supplies concrete M026 mechanics, but a seven-case synthetic audit finds that its advisor scores disagree with its own target weights and method0 emits NaN on flat history. Kelly and inverse-volatility siblings are enumerated, not independently validated. Two of the four signals retain prior positions when no new signal occurs; fifteen-minute evaluation is not a short holding-period guarantee. The focused reproducible audit is [draftPR42](https://github.com/SaikiK12/T/pull/42); no market result, new M/R-id or canonical verdict change.

`intake_collision_reconciliation_20261021` preserves the original pending source M280/M281 rows, aliases and source objects in two collision receipts and moves only their current allocations to M400/M401. Existing live-lab M280/M281 meanings remain intact; no historical claim precedence, method change or measured trial is inferred.
