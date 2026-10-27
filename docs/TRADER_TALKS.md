# What proven traders let slip about how they make money (2026-10-21)

The original collection figures below are a dated historical report. Current
held-source coverage and actual reading are recorded in the appended
2026-10-26/27 corpus section; an old running-job statement does not describe a
process currently verified here.

The owner's ask: find the interviews, talks and podcasts of people who made money trading, Tarek Elmarhri first.
Look for the moments where they say more than they meant to about how the money is made. Then turn that into
things the lab can test, or into a way to find opportunities ourselves, not just copy someone else's strategy.

Nothing here is a result. A quote is a claim until a frozen lane tests it. The ideas that can be tested are
registered as M301-M304 in `registry/methods.csv`. M301 and M303 were tested as R289 (NULL, below); M302 and M304
are queued.

## How it was collected
- **Tool:** `scripts/dig_talks.py` holds a roster of about 70 traders and firms, each with a credibility tier, and
  works in three steps:
  - `match`: finds their episodes in the podcast index (17,971 episodes from 42 feeds; `scripts/dig_podcasts.py`).
  - `fetch`: takes each feed's own transcript when one is published. Otherwise it transcribes the audio locally with
    Whisper (base.en for English, small for French), within an hours budget.
  - `cues`: scores 140-word windows for mechanism words in English and French (counterparty, forced sellers,
    arbitrage, "our edge", "on gagne de l'argent", contrepartie…), numbers and first-person speech.
  - Outputs go to `data/videos/` (gitignored): `talks.csv`, `subs/`, `talk_cues.md`.
- **Held at the time of writing:**
  - 1,039 episodes matched for 54 people;
  - 170 transcripts for 35 people (116 from the feeds themselves, the rest from Whisper; the Whisper job is still
    running);
  - 200 scored windows for 33 people, all read.
  - A rebuild at 20:44 UTC, after three more Whisper transcripts (Unger, Jane Street, Jump), has 270 windows for 34
    people. The windows of those three people were read; they add the one-liners under "Others read".
- **Web sources** cover the people the podcast feeds miss: a regulator's order, court testimony, an IPO filing,
  and press profiles. Each is linked under Sources.
- **Not reached:**
  - YouTube refuses captions to this machine.
  - Instagram and TikTok audio was not used here.
  - Several tier-A names (Simons, Yass, Gerko, Druckenmiller) appear only as subjects of other people's episodes, so
    their cards rest on filings and press.
  - Whisper text has transcription errors; quotes below were checked against the audio transcript only, not the
    audio.

**Credibility tiers** (in the roster, used below):
- **A:** the record is checked by someone else, such as audited returns, a filing, a regulator's order, court
  testimony or an audited contest.
- **B:** a documented career, but the numbers are the person's own.
- **C:** results the person shows themselves, or income that comes mainly from courses, signals or prop-firm
  challenges.

A C-tier speaker can still describe a real mechanism. The tier says how much to trust their numbers, not their
description.

## The people, and what slipped

### Tarek Elmarhri, Krechendo Trading (tier C)
- **What he says he does** (Boursenews interview): his room trades index futures order flow with trades lasting 1 s
  to 5 min. It does not forecast direction: "identifier les zones d'intervention à l'achat et à la vente en
  travaillant uniquement sur les flux d'ordres exécutés par les gros intervenants. Nous n'essayons pas d'anticiper le
  sens du marché."
- **The slips** (So What podcast):
  1. **The US open, every day.** "À 15h30, à l'ouverture américaine, là, tout le monde est devant ses écrans… il y a
     des fenêtres de tir." Then, on the open itself: "c'est ce qu'on appelle du spoofing… c'est la banque qui vend
     agressivement pour faire chuter le marché. Tout le monde panique et se met à vendre. Et à ce moment-là, eux, ils
     achètent. Ça, l'ouverture américaine, à Krechendo, on le prend tout le temps."
     - **Mechanism:** a predictable flush at a fixed clock, then a reversal. Their money comes from being on the
       other side of the panic sellers, in a window where they know it happens.
  2. **Automation makes it easier.** "Plus les systèmes sont automatisés et plus on gagne de l'argent, parce qu'une IA
     ou un automate, il va toujours faire la même chose." They look for "les événements qui se répètent".
     - **Mechanism:** rule-bound flows (algorithms, fixings, rebalances) are predictable in time and side. Whoever
       knows the rule trades ahead of it or against its impact.
  3. **Who pays at the top.** "Ceux qui veulent les vendre, ils ont besoin d'une contrepartie. Et la contrepartie,
     c'est les particuliers… achetés tout en haut du cycle."
- **The business:**
  - Prop-firm challenges cost about $200. Firms are "valorisées en milliards", with "200 millions d'ebitda par an"
    for the large ones.
  - He tells aspiring traders that a challenge is the test: "si tu n'es pas capable de passer un challenge à 200
    dollars… c'est que tu sais pas trader."
  - He promotes a prop firm. The revenue of that industry is mostly challenge fees from people who fail, which is why
    he is tier C. `docs/PROP_FIRMS.md` has the lab's prop-firm numbers.
- **For the lab:** M301 (US-open flush and reverse) and M304 (fixed-hour automated flows). Both need sub-hour
  bars; 1-minute klines for BTC/ETH/SOL are downloading.

### Jane Street, per SEBI's interim order (tier A as a regulator's document; allegations, contested)
- **What the order says** (2025-07-03, Bank Nifty, 18 expiry days from 2023-01 to 2025-03), as summarized by the
  Oxford Business Law Blog and Moneylife:
  - **Patch I (morning):** Jane Street bought the index's bank stocks and their futures, often above the last price,
    which lifted the index, while building large short positions in index options.
  - **Patch II (afternoon):** it sold those stocks and futures, which pushed the index down into expiry, and the
    options book gained.
  - **Totals:** about ₹43,289 crore of profit from index options over the review period, against ₹7,687 crore of
    losses in stocks and futures. SEBI impounded ₹4,843.57 crore, which Jane Street deposited. It reserves the right
    to challenge the order.
- **Mechanism:** move the cheap, thin market that a settlement price is computed from; get paid in the large market
  that settles on it. The losing leg is the cost of the winning one.
- **For the lab:** this is illegal to do. It is useful to know when and where someone might be doing it, because
  the move and its unwinding are visible in prices.
  - Crypto's version is the settlement window. Deribit settles on a 30-minute TWAP of its index from 07:30 to
    08:00 UTC. Its docs say the TWAP and the multiple index constituents are there "to reduce the risk of price
    manipulation at settlement."
  - **M303** tests whether anything is left of the push or of the reversal after 08:00.

### Alameda Research and Sam Bankman-Fried (tier A for the court record, B for his own words)
- **His words:**
  - "I just saw arbitrage opportunities… billions of dollars a day of volume… and the spreads were just absolutely
    ludicrous given that. You saw 1% spreads all over the place."
  - On the model: "liquidity provider, an arbitrage firm… the average core trade is sort of just a delta-neutral
    hedged position."
  - "The less efficient things are, the more alpha there is and the more liquidity is needed."
  - The documented early trade was the Japan bitcoin premium. Korea's larger premium was out of reach because of
    capital controls.
- **The slip, at trial** (Gary Wang's testimony, 2023):
  - Alameda was exempted from FTX's liquidation rules ("allow negative").
  - It had a credit line reported at $65 billion, when no other customer's exceeded $1 billion.
- **Mechanism:**
  - **The legitimate part:** being paid to cross a barrier others cannot cross (capital controls, banking, KYC). The
    gap persists because of the barrier, not because nobody noticed it.
  - **The rest:** privileges inside the venue, which no outsider can have.
- **For the lab:** barrier gaps are the lab's venue-structure track (`docs/VENUE_STRUCTURE.md`): kimchi premium
  data (Upbit, Bithumb), the DEX-CEX gap recorder (M288) and Lighter's zero fees. A gap the owner can cross with
  public venues and small size is the only kind available.

### Virtu Financial and Doug Cifu (tier A for the filing)
- **The filing:** the 2014 S-1 reported one losing day in 1,238 trading days (2009-2013).
- **Cifu:**
  - "We are a passive market maker… We're willing to sell you something at ten, we're willing to buy it at nine…
    and we hope to collect that."
  - The slip: "More often than not, a lot of times we get run over and we lose money."
  - Hundreds of thousands of trades a day turn many small losses into almost no losing days.
- **Mechanism:**
  - The spread, paid by impatient traders.
  - Order flow bought from retail brokers (payment for order flow).
  - Inventory risk managed in real time.
- **For the lab:** not reachable as such. It needs exchange rebates, colocation and flow nobody sells to a $10k
  account. The reachable piece is the maker side at zero fee (Lighter; MEXC's 0-fee maker contracts). R193
  measured how much adverse selection eats a maker fill.

### Renaissance Technologies (tier A for the returns, as reported by Zuckerman's book)
- **The slip:** Robert Mercer is reported to have said their trades won about 50.75% of the time. That is enough
  with millions of trades and leverage.
- **Mechanism:** a tiny edge per trade times a huge count, with costs controlled to a fraction of a basis point.
- **For the lab:** the opposite of what a $10k API account can do. At 6-8 bp per side, a 50.75% hit rate with
  symmetric payoffs loses. The lesson is the arithmetic: the edge per trade has to clear the cost per trade, which
  is why every FINDINGS here reports 1x/2x/3x cost.

### Susquehanna (SIG) and Jeff Yass (tier A for the firm's scale; secondary sources for the method)
- **Background:** poker and game theory before trading. SIG began as options market makers on the Philadelphia
  exchange.
- **Business:** today it is one of the largest options traders in the US, and it buys retail order flow.
- **Mechanism:** pricing the probability better than the counterparty, and being paid the spread by flow that does
  not price it at all.
- **A 2026 detail:** SIG got a court to freeze accounts of options traders it alleges traded on inside
  information. A market maker watches who beats it, because informed flow is its cost.

### XTX Markets and Alex Gerko (tier A for the accounts)
- **Business:** machine-learning market making, mostly FX. Reported profit after tax was £1.71 billion on £3.93
  billion of revenue in 2025.
- **Mechanism:** forecast the next price a little better than others, quote around it, at enormous volume and thin
  margins.
- **For the lab:** out of reach. It confirms that the large money is in providing liquidity with a short-horizon
  forecast, not in directional calls.

### John Arnold (tier A: Enron's gas desk, then Centaurus)
- **The slips:**
  - "I was for a long time the largest market maker in the business, which I did both because I was profitable,
    as well as maybe more importantly, it allowed ability to put on and off positions with lower slippage and with
    fewer people knowing what my position was. And then also gave me insight into who was doing what in the
    market."
  - On why the market exists: commercial producers and users "are willing to pay something to have somebody else
    reduce their risk."
  - As a teenager in baseball cards: "information on pricing is not very uniform across the market… a lot of
    geographic price differences."
- **Mechanism:**
  - Market making as an information source and camouflage.
  - The hedger's premium.
  - Geographic price gaps.
- **For the lab:**
  - The hedger's premium in crypto is funding: leveraged longs pay to hold their position. That is the carry
    family (R191, R275, R277).
  - Geographic gaps are the cross-venue work.

### Takashi Kotegawa, "BNF" (tier A for the J-Com trade, which is on record; his method rests on press reports and his own interviews)
- **Reported method:** buy stocks that panic has pushed far below their 25-day moving average, and sell within
  days.
- **The documented trade:** in 2005 a Mizuho trader's error offered J-Com shares at ¥1 instead of one share at
  ¥610,000, and he bought into it. The press reported about ¥2 billion of profit.
- **Mechanism:** buy from forced or mistaken sellers.
- **For the lab:**
  - **M302** tests the extreme-tail deviation buy.
  - Most of its neighbourhood is already NULL here: R245 (1- and 7-day reversal), R243 (Bollinger fades), R263
    (5,472 chart rules) and R283 (VIX panic buy).

### Arthur Hayes, BitMEX co-founder (tier A: the court record of BitMEX)
- **The slips:**
  - "Why are perps good? Because retail investors love them. At the end of the day, Wall Street is about
    extracting value from dumb retail to smart institutional investors." The perpetual swap with socialized losses
    is "the product for them".
  - On running an exchange: the large trading firms "make up, you know, 70-80% of the flow on most exchanges",
    the venue bends its rules to them, and latency decides who wins.
- **Mechanism:** the product's design (high leverage, funding, liquidation) moves money from leveraged retail to
  liquidity providers, the venue and liquidators.
- **For the lab:** collect the design's transfers from the safe side:
  - funding carry;
  - liquidation flows. R206 found long cascades continue and short squeezes revert gross but not net of cost.

### Hasu (tier B; Flashbots, Lido)
- **The slip:** "Whether it's an oracle or whether it's a liquidity pool or a user making a DEX trade, if you're
  accepting a certain price, and somebody else can see that intent, then they will always push you to the worst
  possible price."
  - Liquidations triggered by oracle updates are auctioned to whoever is fastest.
- **Mechanism:** stale quotes are picked off. An AMM quotes an old price until someone trades against it.
- **For the lab:** that is exactly what the DEX pool recorder (M288) measures: how far and how long an AMM pool's
  price trails MEXC's.

### Cliff Asness, AQR (tier A)
- **The slips:**
  - "Markets are not arbitrage mechanisms… they're voting mechanisms." The second half of an arbitrage is riskier
    than the first, because you already hold the trade. So mispricings can persist.
  - "You need an economic story why it works. I don't believe in just data… and you need a lot of out of sample
    tests."
  - "On average, retail transfers money to Wall Street and to institutions."
- **For the lab:** this is the lab's rule set in his words: a mechanism first, then frozen out-of-sample tests.

### Peter Brandt (tier A: a registered CTA, profiled in Schwager's *Unknown Market Wizards*)
- **The slip:** "There is no edge in a head and shoulders… My edge comes from risk management and emotional
  management and process."
- **For the lab:** consistent with R243 and R263. 5,472 chart strategies gave nothing after costs and multiplicity.
  The chart is where he places a defined risk, not the source of the return.

### Others read, in one line each
- **Ed Thorp:** the first statistical arbitrage was warrants against their stocks, two related securities out of
  line.
- **Cobie and Su Zhu:** the GBTC premium trade and forced sellers. Contagion moved through lenders who did not know
  whom they were lending to. Crypto's large losses came from leverage on leverage, not from bad signals.
- **Rob Carver:** perps "are, in a sense, daily futures", so their funding is the daily settlement of the bet.
- **Kyle Samani:** AMM designs that slow arbitrage protect LPs. The arbitrageur's profit is the LP's loss.

Added from later Whisper transcripts (2026-10-21, evening):
- **Andrea Unger (tier A: four World Cup Trading Championship wins):** he does not trust crypto exchanges with much
  money, but holds BTC on a ledger and shorts the future against it, keeping only margin on the exchange: "Sometimes
  I was 20% a year". That is his own number. It is the carry trade the lab's carry lanes test (R191, R275).
- **An ex-Jane Street trader (Odds on Open):** edge is "something that you know that nobody else knows … or
  something that you can do that many other people can't do". Small shops used to live on "the bottom end of the
  Russell because big quant shop is kind of just not worth their time", and he says that room is shrinking as
  automation gets cheaper. This is the small-size edge in `docs/DIRECTION.md`.
- **Michael McGee, Jump Crypto (a former US equity market maker):** he describes payment for order flow: the broker
  sends a retail order to Citadel, which pays for it and then decides whether to fill it itself. Retail flow is worth
  paying for (source 6, venue privilege).

## Where the money comes from
Seven sources cover everything above. For each: who pays, whether a $10k API account can reach it, and what the
lab has already run.

| Source of money | Who pays, and why they accept it | Examples above | Reachable at $10k? | Lab so far |
|---|---|---|---|---|
| 1. Spread and liquidity provision | Impatient traders pay to trade now | Virtu, XTX, SIG, Arnold, Jane Street | Only the maker side at zero fee | R193 maker entries NULL; Lighter cost recorder live |
| 2. Risk-transfer premium | Hedgers and leveraged longs pay to hold risk | Arnold's hedgers; funding | Yes | R191 CONFIRMED (small); R275 and R277 PARTIAL; R278 and R279 forward |
| 3. Barrier gaps | Whoever cannot cross capital controls, KYC or banking | Alameda's Japan trade; kimchi; GBTC | Partly, on public venues | Cross-venue funding R275 and R277; DEX recorder (M288); R288 Lighter queued; Korean candles held, untested |
| 4. Forced or rule-bound flow | Sellers who must trade at a set time or price | Elmarhri's US open; BNF; SEBI's expiry days; liquidations; unlocks; delistings | Yes, if the clock or rule is public | R206, R223, R265 PARTIAL, R267, R269, R271 (mostly NULL); M301, M303, M304 queued |
| 5. Small edge at huge count | Everyone, by a sliver | Renaissance, XTX | No: costs are 6-8 bp per side | R287 (gross real, net killed by turnover) |
| 6. Venue privilege or design | Retail, through the product's rules | Alameda's exemptions, Hayes on perps, Hasu on liquidations | Only as the counterparty to the design (carry) | as row 2 |
| 7. Selling the dream | People who pay for courses and challenges | Prop-firm challenges | It is a business, not a trade | `docs/PROP_FIRMS.md` |

Rows 2-4 are where a small account has a chance. Each one has a payer with a reason to keep paying. The lab's best
result so far, carry (row 2), is the one with the clearest payer.

## Finding opportunities ourselves
The owner's point is that most people follow strategies and do not ask how an opportunity is made. Every
proven trader above answers the same few questions before they trade. As a checklist for any new idea:

1. **Who is on the other side, and why do they accept losing?**
   - They are forced: liquidation, settlement, an index or ETF rule, an unlock, a delisting.
   - They are impatient: they pay the spread.
   - They are constrained: capital controls, a mandate, no access to a venue.
   - They want something else more: leverage, a hedge, a lottery ticket.

   If there is no answer, the "edge" is probably noise.
2. **Is the flow on a clock or a rule?** Fixed times (opens, fixings, settlements, funding hours) and fixed rules
   (index weights, ETF creations, liquidation engines) repeat. Elmarhri's "les événements qui se répètent" is this.
3. **What barrier keeps others out, and can we cross it?** Small size, zero-fee venues, odd hours and thin coins
   can be advantages for $10k that a fund cannot use.
4. **Does it survive our cost at 2x?** The arithmetic of Renaissance and R287: the gross edge per trade has to
   clear 6-8 bp per side for MEXC API.
5. **Then register it.** Write a methods row, claim an id on #7, freeze a PREREG and read it against
   `registry.program_trials()`.

The four new rows come from questions 1 and 2:

| Id | Clock or rule | Who pays | Data |
|---|---|---|---|
| M301 | US cash open, 13:30/14:30 UTC | Panic sellers in the first minutes | 1-minute klines held; **R289 NULL** |
| M302 | 25-day MA deviation | Forced sellers in a coin-specific panic | held |
| M303 | Deribit settlement TWAP, 07:30-08:00 UTC | Whoever is short the move at expiry | 1-minute klines held; **R289 NULL** |
| M304 | ETF fixing hour (BRRNY), 15:00-16:00 New York | Creations and redemptions sized and timed by rule | hourly klines held; daily ETF flows need a fetch |

M290 (scheduled releases) and M206 (opening-range breakout) also wait on the same 1-minute data. Sessions and
holidays come from the lab's DST-aware session clocks (`lab/sessions.py`, with NYSE holidays), and any one of these rows becomes a lane only
through a frozen PREREG.

## What the first test found (R289, 2026-10-21)
`experiments/clockflow_v1/FINDINGS.md`: 40 frozen variants on Binance BTC, ETH and SOL 1-minute bars, 2021-04 to
2026-09, manual web costs of 3/6/9 bp per side. **NULL.**
- **The US-open flush (M301) does not transfer to crypto.** The best fade on discovery made +4.1 bp a day, almost
  all in 2022 and mostly on SOL. In 2024-26 it lost (t −0.48), at every cost.
- **The Deribit settlement window (M303) leaves a small reversal.** On Fridays, a move of at least one σ between 07:30
  and 08:00 UTC reverses by about +20 bp gross per trade over the next two hours, in both windows and all three
  coins. On the book that is +0.65 / +0.38 / +0.11 bp a day at 1x / 2x / 3x, t 1.37: too small and too rare to pass
  a 40-trial reality check (p 0.87).
- **Two placebo patterns, seen after the run and not decided on:**
  - the 09:30 New York fade works better on days the US market is shut;
  - moves in the hour after 10:30 New York continue.

  They are seeds for a new lane on reserved or forward data, not results.

Added from Whisper transcripts on 2026-10-22 (08:01 UTC rebuild: 358 windows for 44 people):
- **Linda Raschke (tier A: a CTA in Schwager's *The New Market Wizards*; Better System Trader 049 and 124):**
  - **Intraday relative strength:** at the open, long only the top three relative-strength leaders and short only
    the bottom three. "I'll get a win loss ratio of 80%… The duration of that edge might only last one day."
    Queued as **M318**.
  - **Against crowded trends:** "these markets tend to get very crowded very quickly. So the liquidation flushes can
    be quite severe", and a volatility breakout held about 24 hours trades against the trend. R243 and R263 tested
    breakouts without the crowding condition.
  - **On the first hour:** "in a strong trend, the first hour always offers the opportunity for the day". R293 found
    the first UTC hour reverses in crypto (M315, for unseen data only).
- **Kevin Davey (tier A: World Cup Trading Championship results):** end-of-day systems because he worked full time.
  Scale trading, adding to a loser on a scale down, is how he "got killed". That is the lab's prop never-do list
  (martingale).
- **Peter Brandt (2026 episode):** takes partial profits within a week or two "to give staying power" to the rest,
  and sizes every trade the same because he cannot tell which will be the best. A sizing rule, not a signal.

## Not checked
- No quote above was tested here. The numbers are the sources' own: SEBI's are allegations, Kotegawa's are press
  reports, Elmarhri's are his own.
- Whisper transcripts were not checked against the audio. The French quotes come from the podcast's published
  transcript.
- People the roster names but the feeds do not carry (Simons, Yass, Gerko, Druckenmiller, Larry Williams) have no
  transcript here. Williams's setups were looked up only in secondary code ports, so they are not carded. Raschke
  has two Better System Trader transcripts from 2026-10-22.

## Sources
- So What podcast, episode with Tarek Elmarhri (Ausha):
  https://podcast.ausha.co/sony-so-what-podcast/on-t-a-menti-sur-le-travail-et-sur-l-argent-tarek-elmarhri-fondateur-de-krechendo-trading
- Boursenews interview: https://boursenews.ma/article/decryptage/entretien-nos-transactions-durent-1-seconde-a-5-minutes
- Yabiladi profile: https://en.yabiladi.com/articles/details/76202/diaspo-tarek-elmarhri-trader-hunt.html
- SEBI order on Jane Street, summaries:
  https://blogs.law.ox.ac.uk/oblb/blog-post/2025/07/jane-street-and-expiry-day-trap-unpacking-sebis-crackdown-algorithmic
  and https://moneylife.in/article/explainer-what-are-sebis-findings-on-jane-street-groups-market-manipulation/77594.html
- Deribit settlement: https://support.deribit.com/hc/en-us/articles/29734325712413-Settlement
- CME CF reference rates: https://www.cmegroup.com/education/courses/micro-bitcoin-basics/cryptocurrency-reference-rates-and-real-time-indices-overview
- Gary Wang's testimony: https://www.bostonglobe.com/2023/10/06/business/mit-classmates-gary-wang-adam-yedidia-testify-against-sam-bankman-fried-crypto-fraud-trial
  and https://www.benzinga.com/markets/cryptocurrency/23/10/35130513/ftx-cto-gary-wang-reveals-fraudulent-practices-at-crypto-exchange-during-bankman-fried-tri
- Alameda: https://en.wikipedia.org/wiki/Alameda_Research and https://www.shortform.com/blog/sam-bankman-fried-alameda-research/
- Virtu's S-1 losing day: https://qz.com/186209/the-high-frequency-trading-firm-thats-about-to-go-public-only-had-one-day-of-trading-losses-in-four-years
- Renaissance hit rate: https://pwlcapital.com/renaissance-technologies-medallion-fund-an-exception-to-the-indexing-rule/
- Susquehanna: https://www.inquirer.com/politics/nation/jeff-yass-market-maker-trump-media-20240410.html and
  https://www.inquirer.com/business/jeff-yass-susquehanna-insider-trading-20260702.html
- XTX: https://cryptobriefing.com/xtx-markets-gerko-record-earnings-2025/ and
  https://www.bnnbloomberg.ca/math-whiz-trades-without-humans-to-build-a-700-million-fortune-1.1357870
- Kotegawa: https://behindtheinvestment.substack.com/p/bnf-and-his-trading-journey and
  https://www.ebc.com/forex/takashi-kotegawa-strategy-how-to-win-big-in-the-stock-market
- Podcast episodes (feed transcripts or Whisper): Invest Like the Best (John Arnold), Chat With Traders 329 (Peter
  Brandt), Odd Lots and Masters in Business (Cliff Asness), Bankless and Delphi (Arthur Hayes, Hasu, Cobie, Su Zhu,
  Kyle Samani, Sam Bankman-Fried), Virtu's Doug Cifu on payment for order flow, Top Traders Unplugged (Rob Carver),
  Ed Thorp's interview, Algorithmic Advantage 038 (Andrea Unger), Odds on Open (ex-Jane Street trader), Lightspeed
  (Jump's Michael McGee). The list with links is `data/videos/talks.csv`.

## 2026-10-26: deeper practitioner rules, including their losing executions

This pass reads **four complete publisher video transcripts and three method
articles**, instead of another roster introduction. The received versions,
57 strategy/variant/risk/process scopes, exact missing mechanics and aliases are
in the [source bundle](../research/intake/practitioner_methods_20261026.json),
imported into the existing intake. These are not 57 tested strategies.

| Primary material read | Concrete information acquired | Evidence boundary |
|---|---|---|
| [Qullamaggie's own setups](https://qullamaggie.com/my-3-timeless-setups-that-have-made-me-tens-of-millions/) | Momentum-base breakout, catalyst pivot, parabolic short and separately disclosed collapse-long; opening-range/daily entries and partial/MA exits | Own claims and selected examples; no complete audited costed account. Linked streams and charts unread. |
| [Unger Academy daily crypto/ATR transcript](https://ungeracademy.com/blog/volatility-position-sizing-adapting-your-strategies-to-market-volatility) | Next-day close-plus-true-range entry and day-end exit; fixed versus ATR-sized risk | Coach's optimized demonstration, not verified champion portfolio PnL. Entry true range differs from ATR sizing. |
| [Unger Academy robustness transcript](https://ungeracademy.com/blog/how-to-figure-out-if-a-strategy-will-work-before-investing-your-money-in-it) | AMZN prior-session DF filter, timed breakout, stop/target; neighborhood, walk-forward and resampling alternatives | Exact entry code missing; original/WFA windows differ. Stressing optimized trades does not supply an independent sample. |
| [Andrea Unger's public Daily Factor code](https://blog.ilgiornale.it/analisi-tecnica/2023/05/30/il-daily-factor-un-filtro-per-fare-trading-con-la-volatilita/) | Previous-session body/range filter, next-bar channel stops and monetary-stop alternatives | Source code read; original platform/order conventions and market outcomes not reproduced. |
| [January student-strategy article](https://ungeracademy.com/blog/strategy-of-the-month-january-2025-a-trend-following-strategy-for-gold-wins) | NQ rolling Donchian/asymmetric filters; GC Bollinger/prior-DF and delayed MA exit | Code behind membership; missing patterns/stop values remain missing. Student backtest contest differs from real-money championship. |
| [SMB GME review](https://www.smbtraining.com/blog/you-are-trading-better-than-you-think-2) | Multi-day extension context, failed VWAP reclaim, core/momentum lots, partial exits | Actual illustrated management is intraday; overnight holding is a proposed extension. No independently audited account. |
| [SMB NVAX losing-trade review](https://www.smbtraining.com/blog/one-bad-trade-a-new-trader-education-video-series) | Lower-high/tape confirmation, price-only versus price-and-time stops, wick exit/re-entry and failed momentum attempts | Correct direction still lost through execution. The losing path is retained. Speakers are Bellafiore with junior traders, not Lance. |

The official [organizer archive](https://www.worldcupchampionships.com/world-cup-trading-championship-historical-standings)
lists Unger wins in 2008/2009/2010 and **Q4 2012**. It does not establish four
annual results, which methods earned them, or their transfer to our capital,
risk and fees. Qullamaggie's biography is self-report. No speaker's aggregate
income is entered as our strategy's expected return.

### Useful source-code distinctions

The Daily Factor is `abs(O-C)/(H-L)` for the previous **session**, not a
true-range forecast. Four separate rational examples verify that a wide doji
can have DF zero and large true range, and a large overnight gap can leave DF
zero. The snippet keeps the previous DF on a zero-range session. Its strict
`DF < 1` condition excludes full-body candles, despite the prose describing
that setting as filter-off. These details must survive any faithful port.

The channel is 40 completed 30-minute bars, including the decision bar, for
next-bar stop entries. Twenty trading hours are not automatically twenty UTC
hours. The snippet does not settle OCO/dual hits, reversals, pyramiding, final
exit or the monetary stop's contract convention. Its staged DF/stop searches
do not establish a jointly executed 336-cell grid. No source strategy was run.

In the student NQ description, comparisons to a common current Donchian maximum
would be impossible for its own constituent highs. Comparing each bar against
its own earlier channel could be meaningful. The gated code is needed to resolve
this; the intake does not quietly choose the convenient interpretation.

### Reconciliation with our cost/account work

Ten new exact open scopes enter the **same queue**: M413–M417 and M419–M423.
The AMZN refinement maps to existing M200, so M418 is deliberately unallocated.
Prior generic chart/VWAP NULLs remain valid for their tested scopes. They do not
automatically test these source-specific conditions. Two weak equity reader
comments are attributed separately, not promoted to Qullamaggie's own methods.
M412/R333 and Claude's active files were left alone.

The [R334 interface](../experiments/opportunity_value_v1/FINDINGS.md) needs an
actual horizon/quantity-specific payoff forecast, calibrated error and
source-bound quotes/fees/session/lot contracts. These sources supply rules and
data questions, not those measured inputs. Re-entries and partial exits each
need their own costs; a stop at entry price is not net breakeven. Slower holds
may amortize entry costs, while funding and adverse exits still accumulate.

For a purely illustrative two-outcome trade with gain W, loss L, cost/reserve C
and error allowance E, positive expected net requires
`p > (L + C + E)/(W + L)`. This is an accounting identity, not a measured
probability or edge. Timeout, funding and variable costs need the full model.

Access closed with 12 combined search queries, eight direct static attempts
(six HTTP200/two HTTP403), and 1,695,922 accepted successful body bytes. Browser
wire costs are unmeasured; ordinary video opens were throttled. Publisher text
was read, not audiovisual frames, complete channels or paid code. One bounded
reader plus the main agent worked; no media/models/market history was downloaded.
Four toy arithmetic checks are not market observations. New strategy outcomes,
new prospective days and historical-budget consumption are all zero.

## 2026-10-26/27: a large source index feeding exact, cost-aware hypotheses

The owner requested thousands of leads rather than four isolated readings.
The existing podcast tools now have a bounded mode, committed at **adddfb6
before any dispatch**, using the existing acquisition-budget journal. This is
source acquisition and source interpretation, not an alpha test.

| State | Actual held scope |
|---|---:|
| Registered public feeds attempted | 42 |
| Complete feeds parsed | 25 |
| Episode metadata records | 6,240 |
| Episodes advertising a native transcript | 877 |
| Selected native-text attempts | 24 |
| Native texts parsed / HTTP404 failures | 22 / 2 |
| Complete received-text reviews / partial reviews | 3 / 1 |
| Parsed texts still semantically unread | 18 |
| New market trials / prospective days | 0 / 0 |

The [compressed episode identities](../research/intake/podcast_episode_index_20261026.csv.gz)
are 564 kB and contain titles, dates, links, feed/key identity and original
RSS body hashes. They contain no summaries or transcript bodies. Reposts under
new URLs/GUIDs can remain; these are not 6,240 distinct methods, verified guests
or profitable traders. The existing name matcher associates 342 episodes with
46 roster entries, including stories *about* people. These are retrieval hints.

The [source extraction bundle](../research/intake/podcast_methods_20261026.json)
records every received rule, weak alternative, incomplete claim, risk and
process in the reviewed scope: **65 records imported into the existing intake**.
This count is not 65 executable strategies or independent tests. All 465 earlier
source objects and their source versions remain intact; alias bytes append.
The canonical queue adds only **M424**. Other original instruments and long
holds remain received context outside the active short-hold-perps implementation.

| Text actually read | Read boundary | Useful mechanics and remaining limitations |
|---|---|---|
| [Grug / Flirting with Models](https://transcripts.captivate.fm/transcript/e532809b-fa1b-4853-b0ff-5bd4df7e4e49/index.html) | All 7,886 normalized words of the captured text, published 2023-07-24 | Atomic arbitrage/backrunning, liquidation financing, bid/gas costs, rare-event inactivity and development cost; NFT/airdrop/security examples retained as outside-scope context. Old protocol descriptions are not current implementation certification. |
| [David Sun / Resolve Riffs](https://transcripts.captivate.fm/transcript/e804454f-1293-44c2-9869-08e8917b547d/transcript.srt) | All 10,302 words, published 2024-02-09 | Intraday option-premium direction, fixed shared premium budget, staged exits, small trade capacity versus stressed exit capacity; conditional hedge and high-hit-rate claims are not our measured returns. |
| [Asif Noor / Flirting with Models](https://transcripts.captivate.fm/transcript/1a925ade-f348-4702-a669-d1352e848703/index.html) | All 8,359 words, published 2023-06-26 | One constrained portfolio needs comparable forecast units, model horizons/decay and size-specific execution capacity. Covariance groups, bounds and sticky allocations remain unspecified source methods, not an implemented institutional optimizer. |
| [Dean Curnutt / Flirting with Models](https://transcripts.captivate.fm/transcript/cc92f8b3-4d17-445e-9408-c6ac654f459e/index.html) | Words [0,4500) of 13,118, published 2023-09-11; all later words unread | Crowded dynamic insurance, conditional carry/roll-down, convergence gap risk and correlation-risk recycling. Historical narratives do not supply private rules or causal dealer positions. |

Only text was read: no audio, video frames, complete channel, private trading
ledger or linked book/code was checked. Source returns and institutional model
counts remain attributed claims. The delegated collector review completed;
a separate later transcript-reading task failed before producing a result, so
all semantic reviews above were completed by the main agent.

### What can reach our existing account

**M424 keeps two separate bearish definitions.** Sun describes contracting
call premiums and expanding put premiums, at an unspecified surface point and
rate, as differently timed downtrend indications. His original trade sells
index options. A short crypto-perp transfer is **our untested proposal**. The
source does not give a symmetric bullish rule, exact strike/expiry, rate window,
threshold or calibrated probability. Existing GEX and support-level results do
not test it.

Before such an experiment, option bid/ask and first-seen clocks must be matched
to the actual perp execution quote, costs, funding and session. The protocol
must distinguish premium movement from underlying momentum, implied volatility,
delta and time decay. Lagged underlying momentum and fixed surface/IV controls
are necessary comparators. Every actual variant and fixed 1x/2x/3x cost must be
registered before outcomes; no validation-winner transfer into R333/R336/R337.

**One portfolio does not mean one undifferentiated order.** Noor's example
keeps 500 fast and 500 slow lots on their respective researched schedules,
rather than using the fast signal to send all 1,000 immediately. Those are his
illustrative lots, not our capital or capacity. Each model needs target units,
first-seen origin, holding horizon, validity/decay, calibrated payoff uncertainty
and quantity-specific execution constraints. Reuse R334's common account/risk
and R319's model/receipt attribution. Durable allocation reservations and their
complete fill/lifecycle bridge remain unfinished; this source does not make
the single-batch R334 interface safe for repeated concurrent allocation.

**Confidence must clear a payoff hurdle.** For known fixed gross win `W`, gross
loss `L`, equal all-in cost `c` and success probability `p`, our cash identity is
`expected_net = p*W - (1-p)*L - c`. Break-even is `(L+c)/(W+L)`.
Sun's risk-two-to-win-one example needs 2/3 success only at zero cost; a cost of
0.2 in the same payoff units raises that to 11/15, about 73.3%. This is arithmetic
under explicit assumptions, not an observed win rate. Delta is not a calibrated
physical success probability, stops may lose more than planned, and many
same-day trades are dependent. Several signals agreeing can concentrate risk
rather than multiply confidence.

**A revert is not free execution.** An atomic asset-balance assertion does not
establish net profit after bids, gas and failed attempts. It also does not make
two venue API orders atomic. R319's partial fills, residual/orphan exposure and
costs still apply. These are constraints on executable economics, not a claim
that we acquired Grug's current private strategies.

### Acquisition and reproducibility

The closed batch used **66 HTTP attempts**, 73,180,449 accepted body bytes
including capped prefixes, and 34.835 seconds of summed request elapsed time.
Sixteen RSS bodies reached their cap and were not parsed as complete feeds;
one HTTP302 was not followed. Two selected transcripts returned HTTP404.
There were no retries or increases to the declared scope.

Conservative reservations remain **120 MiB / 1,650 seconds** against the declared
128 MiB / 1,800 seconds. The final six requests/eight MiB are unused. Wire bytes
are unmeasured. The accumulated market allowance remains 7,757 requests and
reported 229.85 MiB; this source budget does not reset or extend it.

The [actual source-budget journal](../data/videos/public_corpus_budget_20261026.jsonl)
is tracked to retain accumulated spend across checkouts. A sparse checkout can
omit its working file: recover that missing file from the committed snapshot
before invoking the collector. Raw RSS and transcript caches remain
private/ignored. After an actual environment
restart, replaying both phases with a network-forbidden opener preserved the
6,240 episodes, 22 parsed texts and 66 charged requests. With only a copied
journal and no raw cache, all 66 completed identities refuse new dispatch;
the journal stays byte-identical. Missing source bodies remain missing.

```sh
set -e
python - <<'PY'
import hashlib, json, subprocess
from pathlib import Path
from scripts.podcast_corpus import write_new

evidence = json.loads(Path('research/intake/podcast_methods_20261026.json').read_text())
target = Path(evidence['acquisition']['budget_journal_path'])
snapshot = subprocess.check_output(['git', 'show',
    '149bda38c3a58bbeba65473d69948591dae94db3:' + target.as_posix()])
if hashlib.sha256(snapshot).hexdigest() != evidence['acquisition']['budget_journal_sha256']:
    raise ValueError('source-budget snapshot mismatch; no collection')
if target.exists():
    if not target.read_bytes().startswith(snapshot):
        raise ValueError('existing ledger lost or changed prior charges; no collection')
else:
    write_new(target, snapshot)
# Existing journals are preserved; never overwrite or restore an advanced ledger.
PY
python scripts/dig_podcasts.py episodes --bounded --out data/videos/corpus_20261026
python scripts/dig_podcasts.py text --bounded --out data/videos/corpus_20261026
python scripts/check_method_intake.py --json
```

The bootstrap was checked using a missing target and the committed Git blob;
it restores the same 66 charged attempts, with no HTTP call. A missing Git blob
or digest mismatch must block recovery rather than initialize a new allowance.
These commands replay held receipts when available; they do not recover lost
raw text from hashes. Publisher URLs may change. The committed metadata index
and receipt/method counts can be independently recounted; independent speech
verification still needs the corresponding publisher text version.

Validation before collector commit: **1,449 tests pass, three explicit skips,
212.166 seconds**; 20 focused tests pass. An independent mocked review checked
eight failure/restart/provenance groups, followed by a root regression for
isolating custom-budget cache paths. No external reader completed the later
speech extraction. Neither corpus size, passed software checks nor source
confidence validates positive executable PnL or a new prospective observation.
