# Sources and exact access scope

Access date for every entry: **2026-11-08 UTC**. Creator claims are primary
statements of what the creator presents, not independent evidence of profitability.
The [machine summary](retrieval_summary.json), page/body reservations and
append-only [media request receipts](media_requests.jsonl) carry timestamps,
hashes, byte bounds and response states.

| Source | Author / organization; publication date | Read scope |
|---|---|---|
| [DfVJWnfMysj](https://www.instagram.com/reel/DfVJWnfMysj/) | quant_models / Instagram; 2026-11-04 | Partial video: public metadata/data object, thumbnail and 20 fragment-start pictures at 0–95 seconds. All seven numbered slides observed. Audio unread. |
| [DfdWYmkv6Cy](https://www.instagram.com/reel/DfdWYmkv6Cy/) | thetawarriorpro / Instagram; 2026-11-07 | Partial video: same source scope, 11 fragment-start pictures at 0–50 seconds; 45-second picture recovered after a documented prefix decode failure. Audio unread. |
| [Dc7BZU2hqaC](https://www.instagram.com/reel/Dc7BZU2hqaC/) | adan_profits / Instagram; 2026-09-05 | Partial video: same source scope, five fragment-start pictures at 0–20 seconds. Audio unread. |
| [Futures forbidden practices](https://ftmo.com/en/futures/forbidden-trading-practices/) | FTMO; undated | Partial, full relevant cross-account/risk-management clauses. Exact relevant heading: “Hedge or offset risk across accounts”. Coverage includes other operators/platforms. Not a personalized legal opinion or a rule for every firm. |
| [CFD forbidden practices](https://ftmo.com/en/forbidden-trading-practices/) | FTMO; undated | Partial, relevant opposing-position/manipulative-purpose and consistency clauses; preserve the difference from the Futures policy. |
| [ETF options](https://www.theocc.com/clearance-and-settlement/clearing/etf-options) | Options Clearing Corporation; undated | Full relevant specifications. Exact sentence: “Each standard contract represents 100 shares of the underlying ETF.” Adjusted contracts are separately qualified. No QQQ trade tape was acquired. |
| [Protective collars](https://brokerage.ibkr.com/en/trading/protective-collar.php) | Interactive Brokers; undated | Partial, relevant strategy definition and portfolio-context explanation: long stock, long put, short call. No account or options permissions requested. |
| [Instagram extractor](https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/extractor/instagram.py) | yt-dlp contributors; undated retrieved revision | Partial functional review of anonymous logged-out query/data fields and MPD handling. Software not installed or executed. Its account-cookie, impersonation and retry paths were not used. The actual queries used ordinary urllib and a nonce from each already-held anonymous page. |
| [Project propfirm policy](../../../docs/PROP_FIRMS.md) | Lab; existing dated working document | Relevant never-do list and model limitations only. No frozen document changed. |
| [R202](../../../experiments/propfirm_v1/FINDINGS.md) | Lab; registered 2026-10-19 | Full FINDINGS; optimistic-path, payout and unconfirmed-input limitations retained. No rerun. |

Exact-ID and author/title public searches were attempted. They supplied no
independently matching transcript or verified record. Unrelated repositories
named `quant_models` and unrelated risk-reversal search results were not
attributed to these creators. Search snippets are not full source reads.

## Retrieval and limits

The owner supplied three exact reel links. Ordinary page GETs returned 200.
The complete page bodies were subsequently read with standard gzip negotiation
after successful bounded prefixes; this was not a response to an access denial.
The anonymous **read-only** content query returned matching public media data
for each requested code/id. Its `data` object is complete; the later response
envelope/extensions are incomplete. These states must not be conflated.

MPD-declared video byte indices, SIDX boundaries and content-range headers were
checked. First/second segment bounds and terminal byte closure agree; ffprobe
independently identifies each selected first packet as a keyframe with the
declared timestamp. No frame count is a count of trades or independent bets.
The SIDX starts-with-SAP bit was unset despite SAP type 1; the initial parser
rejected that field before any preview request. The revised reader preserves
both flags and verifies the actual packet, rather than claiming the bit was set.
Duplicate-request plumbing also initially rejected distinct byte ranges before
HTTP; no source request or financial read happened in those failed invocations.

Source bodies, decoded pages, fragment prefixes, images, OCR and contact sheets
remain local under `/tmp/owner_reels_20261108`, with a retained copy in this
worktree's ignored `data/source_media/reels_20261108/`; the
[local archive manifest](local_archive_manifest.json) records its hashes.
Videos/captions are not reposted.
The original page-metadata file is retained locally and excluded from Git.
These local files are not promised permanent availability; URLs may expire.
The code and hashes describe the retrieval, not permission to refresh its budget.
No supplied subtitle endpoint was found in the returned media schema; this is
not a claim that no subtitles exist elsewhere. No exact audio transcription,
complete-video watch, verified payout or independent trade-history read occurred.

The complete finite source reservation stays inside the **same** historical
allowance: conservative total **7,906 calls / 262,096,010 body bytes**, leaving
**94 calls / 47,990 bytes** of **8,000 / 262,144,000**. Whole reservations remain
charged. Bytes mean HTTP response bodies as read, including Content-Encoding;
decoded sizes are recorded separately, and TLS/network wire is unmeasured.
GitHub repository tooling and web-reference reads are separate from these
controlled historical/media download counters; no additional market-data grant
is claimed. No Lighter request, native tick/recorder, account, owner/account credential, order,
money movement, paid source, source-denial workaround or subagent was used.
