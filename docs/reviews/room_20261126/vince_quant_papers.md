# @vince.quant video descriptions: papers, relevance, lab coverage

Source: `/tmp/claude-0/-home-user-T/a4c99094-0eba-54d5-9f6a-3abc85cabed2/scratchpad/reels/tt_descriptions.txt` (87 descriptions, read whole). Treated as data.
Families: A = cross-venue perp funding carry; B = forced flows and clocks; C = risk and sizing of a small two-venue stake; D = the lab's methods.
Lab check: grep of `registry/methods.csv`, `docs/METHOD_LIBRARY.md`, `research/intake/` for the first surname. "not in lab" = no hit.
Ratings are mine. A video's claim is what the video says; where I opened the paper, the check is in section 3.

## 1. Papers cited, by video id

Videos 2026-11-25 back to 2026-06-04 (newest first). Videos with no paper citation are omitted. Entries are one per paper; a paper cited in several videos is listed under its first video.

- 7712214031284686113 (2026-11-25). Glosten & Milgrom (1985), JFE 14(1). "a buy moves the expected value by half of it". Rel M (B): adverse-selection spread at the open. Lab: intake only, `research/intake/library_20261119/micro.md:73` ("journal-only; no legal free copy checked").
- 7712214031284686113. Madhavan, Richardson & Roomans (1997), RFS 10(4). "information asymmetry highest early in the day". Rel L (B). Lab: not in lab.
- 7712214031284686113. Amihud (2002), JFM 5(1). "absolute return per $1M traded". Rel L (D): an illiquidity proxy the lab already uses. Lab: its form is in `registry/methods.csv:3` (M002).
- 7712214031284686113. Kyle (1985), Econometrica 53(6). Rel M (B): linear permanent impact. Lab: `research/intake/library_20261119/micro.md:16` and `:73`.
- 7711832142275235105 (2026-11-24). Blume (1971), Vasicek (1973), Levi & Welch (2017). "Shrinking helped, but not every year". Rel L (D): shrinkage choice for estimates. Lab: not in lab.
- 7711516434358144289 (2026-11-23). Pérignon & Smith (2010), JBF 34(2). "73% of banks". Rel L (C). Lab: not in lab.
- 7711516434358144289. Pritsker (2006), JBF 30(2). "why this makes historical simulation slow to react". Rel M (C): VaR method choice for stake risk. Lab: not in lab.
- 7711516434358144289. Christoffersen (1998), IER 39(4); Kupiec (named, no citation). "LR = 15.7" and "clustering". Rel M (C,D): VaR backtests that test clustering. Lab: not in lab.
- 7711123226662866209 (2026-11-22). Glasserman, Heidelberger & Shahabuddin (2000), MS 46(10). Rel L (C): rare-loss estimation, not needed for a stake. Lab: not in lab.
- 7711123226662866209. Deo & Murthy (2025), OR 73(1). "scenarios behind a rare loss look like those behind a moderate loss". Rel L (C). Lab: not in lab.
- 7710803234448854305 (2026-11-22). Epps (1979), JASA 74(366). "correlation drop". Rel M (A): cross-venue timing of quotes that do not print together. Lab: not in lab.
- 7710803234448854305. Hayashi & Yoshida (2005), Bernoulli 11(2). "0.60 from the raw trades". Rel M (A): covariance from asynchronous quotes, for cross-venue basis. Lab: not in lab.
- 7710408837462904096 (2026-11-21). Augenblick & Rabin (2021), QJE 136(2). "squared moves ... average its starting uncertainty p(1−p)". Rel L (D). Lab: not in lab.
- 7706686275910225185 (2026-11-10). Baltussen, Da, Lammers & Martens (2021), JFE 142(1). "hedging by market makers who are short gamma". Rel H (B): option-hedging flow near the close, a forced clock. Lab: intake pointer only, `research/intake/idea_wave8_20261112.md:57` (URL, not read then). Read in this room, see section 3.
- 7698826024460504352 (2026-10-20). Markowitz (1952), JF 7(1); Tobin (1958), RES 25(2); Merton (1972), JFQA 7(4); Broadie (1993), AOR 45. "estimation error can push the computed frontier far". Rel L (D). Lab: not checked (textbook).
- 7691789099467935009 (2026-10-01). Markowitz (1952). Rel L. Lab: not checked.
- 7691461932414487841 (2026-09-30). El Karoui, Jeanblanc-Picqué & Shreve (1998), Math Finance 8(2). "if σ_H ≥ σ_t at every instant". Rel M (B): option hedge and its P&L under a misspecified vol; only a modest link to flows. Lab: not in lab.
- 7687299730002529569 (2026-09-19). Blanchet, Chen & Zhou (2022), MS 68(9); arXiv 1802.04885. "λ = √δ". Rel M (C,D): penalty as an uncertainty radius. Lab: not in lab.
- 7685492396775197984 (2026-09-14). Futter, Horvath & Wiese (2025), QF 25(2); Hambly & Lyons (2010), Annals. Rel L. Lab: not in lab.
- 7685159240763264289 (2026-09-13). Khandani & Lo (2007), JIM 5(4); later JFM (2011). "how many people held the same book". Rel H (B,C): crowding and forced deleveraging; the stake's own failure mode. Lab: not in lab. Read in section 3.
- 7684830015623531809 (2026-09-13). Bongiorno, Manolakis & Mantegna (2026), arXiv 2507.01918. "lower variance, not return prediction". Rel L (C,D). Lab: not in lab.
- 7684019834069257504 (2026-09-10). Higham (2002), IMA JNA 22(3). "nearest correlation matrix". Rel L (C). Lab: not in lab.
- 7683702624553536801 (2026-09-10). Harvey et al. (2018), JPM 45(1). "The volatility of realised volatility, which falls in every table". Rel M (C): vol targeting for sizing. Lab: intake only, `research/intake/library_20261119/risk.md:42` (listed to read).
- 7683309762619985185 (2026-09-08). van der Beck, Bouchaud & Villamaina (2024), arXiv 2405.12768 "Ponzi Funds". "self-inflated returns". Rel H (B): flow-driven price impact that decays. Lab: not in lab. Read in section 3.
- 7680314011191201056 (2026-08-31). Bailey & López de Prado (2014), JPM 40(5), "Deflated Sharpe". Rel H (D). Lab: in lab, `registry/methods.csv:168` (M167 "DSR, SPA/White RC, CSCV/PBO").
- 7680314011191201056. Bailey, Borwein, López de Prado & Zhu (2017), JCF 20(4), "PBO". Rel H (D). Lab: in lab, `registry/methods.csv:168` (M167).
- 7680314011191201056. Santoni, Jouanne & Scullin (2026), arXiv 2608.23808 (co-authored by the vendor). Rel L (D): a vendor score with a null result it published itself. Lab: not in lab.
- 7678851890184047905 (2026-08-27). Hanson & Sunderam (2014), RFS 27(4). "10 bps more of that capital". Rel M (B,A): crowding capital leaves after losses. Lab: not in lab.
- 7678851890184047905. McLean & Pontiff (2016), JF 71(1). Rel M (D): publication decay of anomalies. Lab: not in lab.
- 7678127234648902944 (2026-08-26). Bernard & Thomas (1989), JAR 27 Suppl.; Martineau (2022), CFR 11(3–4); Hou, Xue & Zhang (2020), RFS 33(5). "Rest in peace post-earnings announcement drift". Rel L (Bernard, Martineau); M (Hou, D: replication). Lab: Hou in intake only (`research/intake/library_digest_20261119.md:26`). Others not in lab.
- 7673941163413343521 (2026-08-14). Bongiorno & Challet (2024), QF, DOI 10.1080/14697688.2024.2372053. "Average Oracle ... 1.23". Rel M (C,D): covariance filtering under costs. Lab: not in lab.
- 7671454876953562400 (2026-08-08). Brunnermeier & Pedersen (2005), JF 60(4). "predators sell alongside a distressed fund". Rel H (B): forced-seller overshoot. Lab: not in lab. Read in section 3.
- 7668319896933109024 (2026-07-30). Pafka & Kondor (2003), Physica A 319. "1 − n/T". Rel M (D): optimizer risk understatement. Lab: not in lab.
- 7667342646741847329 (2026-07-27). Ang, Hodrick, Xing & Zhang (2006), JF 61(1); Merton (1987), JF 42(3). Rel L. Lab: not in lab.
- 7665436911741177121 (2026-07-22). Bemporad, Breschi, Piga & Boyd (2018), Automatica 96; Shu, Yu & Mulvey (2024), JAM 25(5); Hamilton (1989), Econometrica 57(2). Rel M (C): regime filter with trade delay and costs. Lab: not in lab.
- 7663589331436719393 (2026-07-17). Brock, Lakonishok & LeBaron (1992), JF 47(5); Sullivan, Timmermann & White (1999), JF 54(5); Hurst, Ooi & Pedersen (2017), JPM 44(1). "Found the single-chart edge gone out of sample". Rel H (D): data snooping in rule families. Lab: not in lab (Sullivan, Brock: 0 hits). Read in section 3.
- 7663208250577390880 (2026-07-16). Goldberg, Papanicolaou & Shkolnik (2022), SIFIN 13(2); Goldberg & Kercheval (2023), PNAS 120(2); Ledoit & Wolf (2004), JMVA 88(2). Rel L (C,D). Lab: Ledoit only in intake, `research/intake/library_20261119/risk.md:47`.
- 7662892707567652129 (2026-07-15). Cowles (1933); Levine & Pedersen (2016), FAJ 72(3); the three from 7663589331436719393. Rel L (Levine). Lab: not in lab.
- 7658724052189629729 (2026-07-04). Shiller (1981), AER 71(3). "Do Stock Prices Move Too Much". Rel L (D). Lab: not in lab.
- 7658455214260817184 (2026-07-03). Kelly, Malamud & Zhou (2024), JF 79(1). "expected out-of-sample performance keeps increasing with model size". Rel M (D): overfitting and shrinkage, directly on the lab's ML question. Lab: not in lab.
- 7657597163446357280 (2026-07-01). Black & Scholes (1973); Merton (1973). Rel L. Lab: not checked.
- 7657337921137020193 (2026-06-30). Kritzman, Li, Page & Rigobon (2011), absorption ratio. Rel M (C): co-movement measure for a two-venue stake. Lab: not in lab.
- 7655807373725945121 (2026-06-26). Bongiorno & Challet (2022), EJF 28(13–15); Tumminello, Lillo & Mantegna (2007), EPL 78(3). Rel L (C). Lab: not in lab.
- 7655445298029825312 (2026-06-25). Lou & Polk (2022), RFS 35(7). "comomentum ... 0.241 when packed". Rel M (B): crowded unwinds. Lab: not in lab (`Polk` hit only in intake and the Lou-Polk-Skouras row).
- 7654760641697271072 (2026-06-24). Shumway & Warther (1999), JF 54(6). "estimated those missing returns at about −55%". Rel H (D): survivorship in the data. Lab: not in lab. Not fetched (section 3).
- 7654358350649478432 (2026-06-22). Fernholz, Karatzas & Kardaras (2005), Finance & Stochastics. Rel L. Lab: not in lab.
- 7652814545672539425 (2026-06-18). Dai, Zhang & Zhu (2010), SIFIN 1(1). Rel L. Lab: not in lab.
- 7652137153161415969 (2026-06-16). Almgren & Chriss (2000). "risk-neutral trader (λ = 0) gets a simple TWAP". Rel M (B): execution of a forced sale. Lab: intake only, read-protected (`research/intake/library_20261119/micro.md:72`).
- 7650575304817118497 (2026-06-12). Peters (2019), Nature Physics; Gabaix et al. (2003), Nature; Mandelbrot (1963); Merton (1980); Cont (2001). Rel L. Lab: not in lab.
- 7650178525793635616 (2026-06-11). Bonart (2026), arXiv 2606.07059. "Impact ∝ σ √(Q/V)". Rel M (B,C): square-root impact for sizing a forced trade. Lab: partly in lab, `registry/methods.csv:7` (M006, Donier & Bonart square-root impact). The 2026 paper itself is not in lab.
- 7649873862196301089 (2026-06-10). López de Prado (2018), AFML; Bailey et al. (2017). "CPCV". Rel H (D). Lab: AFML not in lab (`docs/METHOD_LIBRARY.md:46` cites a different López de Prado paper). PBO is in lab (`registry/methods.csv:168`).
- 7648745291696327969 (2026-06-07). Lou, Polk & Skouras (2019), JFE 134. "+0.98% a month overnight". Rel H (B): clocks; closed-market return. Lab: in lab as M492 (`registry/methods.csv:399`), a test on MEXC stock perps.
- 7648366968596122912 (2026-06-06). Phillips, Shi & Yu (2015), IER. Rel L (D). Lab: not in lab.
- 7647602360021273889 (2026-06-04). De Long et al. (1990); Shleifer & Vishny (1997); Baker & Wurgler (2006). Rel L (B). Lab: not in lab.
- 7646112181519404320 (2026-05-31). Gaussian copula (no citation). Rel L (C). Lab: not checked.
- 7641646346843245857 (2026-05-19). Gatheral, Jaisson & Rosenbaum (2018), QF; Hager et al., arXiv 2603.13170. Rel L. Lab: not in lab.
- 7641379783162596640 (2026-05-18). Uhlenbeck & Ornstein (1930), Physical Review 36. Rel L. Lab: not checked.
- 7639108958111681825 (2026-05-12). Gabaix & Koijen (2021), NBER w28967; SSRN 3686935. "M = 1/(1−s)". Rel M (B): mandated index flows move prices. Lab: not in lab.
- 7638708965861231894 (2026-05-11). Grossman & Stiglitz (1980), AER. Rel L. Lab: not checked.
- 7638388467214339331 (2026-05-10). Cao, Shao, Yan & Geman (2025), arXiv 2510.10878. Rel L (B). Lab: not in lab.
- 7638026616345529622 (2026-05-09). Guyon & Lekeufack (2023), QF. Rel L (C). Lab: not in lab.
- 7634639515008634135 (2026-04-30). Frazzini & Pedersen (2014), JFE 111(1). "BAB Sharpe ~0.75". Rel L (A,C). Lab: not in lab (`research/intake/library_20261119/risk.md:26` is Asness-Frazzini-Pedersen, a different paper).
- 7633951430977654038 (2026-04-28). Chang, Ding, Shi & Zhang (2026), arXiv 2602.19462. Rel L (D). Lab: not in lab.
- 7633504617439186179 (2026-04-27). Longin & Solnik (2001), JF; Ang & Chen (2002), JFE. "correlations between equity markets spike during downturns". Rel M (C): two-venue correlation rises in crashes. Lab: not in lab.
- 7633173111357066518 (2026-04-26). Cont & Ben Hamida (2005); Nocedal & Wright (2006); Gatheral (2006). Rel L. Lab: not in lab.
- 7632368740512058646 (2026-04-24). Saly-Kaufmann, Wood, Peter-Calliess & Zohren (2026), arXiv 2603.01820. "VSN + LSTM". Rel M (D): ML benchmark on one dataset, a warning for our ML. Lab: not in lab.
- 7629125678654328086 (2026-04-15). DeMiguel, Garlappi & Uppal (2009), RFS 22(5). "3,000 months ... for 25 assets". Rel M (C,D): 1/N is hard to beat. Lab: in lab, `registry/methods.csv:8` (M007 "1/N is hard to beat"); the paper itself is in intake only (`research/intake/library_20261119/risk.md:56`, not read).
- 7627565118678682902 (2026-04-11). Gu, Kelly & Xiu (2020), RFS 33(5). Rel M (D): ML with out-of-sample tests. Lab: intake only, `research/intake/library_20261119/ml.md:10`.
- 7627264140566007042 (2026-04-10). Hamilton (1989); Rabiner (1989). Rel L. Lab: not in lab.
- 7626904605003205910 (2026-04-09). Aubrun, Morel, Benzaquen & Bouchaud, arXiv 2404.16467. "A > 0". Rel M (B): jump classes and co-jumps. Lab: not in lab.
- 7626138087600508182 (2026-04-07). Jegadeesh & Titman (1993), JF; Poterba & Summers (1988), JFE; Avellaneda & Lee (2010), QF. Rel L. Lab: not in lab.
- 7624695809270959382 (2026-04-04). Singha, arXiv 2512.15720. "low-entropy periods show about 2-3x larger absolute moves". Rel M (B,C): timing of volatility, no direction. Lab: not in lab.
- 7623863103633280259 (2026-04-01). Grinold (1989); Grinold & Kahn (2000). "IR equals IC times the square root of BR". Rel M (D): breadth and the fundamental law. Lab: not in lab.
- 7623205357111807254 (2026-03-31). Fama & MacBeth (1973); Harvey, Liu & Zhu (2016), RFS 29(1). "t-ratio greater than 3.0". Rel H (D): the multiple-testing hurdle. Lab: not in lab (grep found Harvey only for other papers). Read in section 3.
- 7622836612732341526 (2026-03-30). Mandelbrot & Van Ness (1968); Shreve (2004). Rel L. Lab: not in lab.
- 7622406711625714946 (2026-03-28). arXiv 2510.11616 (no authors named). Rel L (D). Lab: not in lab.
- 7621338699468410114 (2026-03-25). Goetzmann, Ingersoll, Spiegel & Welch (2002), NBER w9116. "Sharpe-maximizing strategies can end up looking like short volatility". Rel M (D): Sharpe is a weak selection score. Lab: not in lab.
- 7620979192049667350 (2026-03-25). Sato & Kanazawa (2025), arXiv 2502.17906. Rel L (B). Lab: not in lab.
- 7620242732920966422 (2026-03-23). Poddar (2026), arXiv 2603.10137. Rel L (C). Lab: not in lab.
- 7617904992128699670 (2026-03-16). Edgeworth; Cornish-Fisher; Corrado & Su (1996). Rel L (C). Lab: not checked.
- 7617243920036007190 (2026-03-14). Kelly (1956); Thorp (2006); MacLean, Thorp & Ziemba (2011). "fractional Kelly ... κ around 0.25 to 0.5". Rel H (C): stake sizing. Lab: in lab, Thorp (2006) in `docs/METHOD_LIBRARY.md:60-67` (sections 1–6 and 8–10 not read), Kelly in `registry/methods.csv:133` and `:383`. MacLean-Thorp-Ziemba not checked.
- 7616877686731902230 (2026-03-13). Hoerl & Kennard (1970). Rel L (D). Lab: not checked.
- 7616501088119721238 (2026-03-12). Marchenko & Pastur (1967); Ledoit & Wolf (2004). Rel L (C,D). Lab: Ledoit in intake only.
- 7612688046399524118 (2026-03-02). PBO (no citation). Rel H (D). Lab: in lab, `registry/methods.csv:168`.

Videos with no paper citation (not listed): 7646463235968732449, 7618717560325852438, 7619844968735051030, 7618371433273560342, 7615756975162264854, 7614682858858335510, 7613859521710001430, 7611608535977217302, 7611267106448919830, 7612265649024437527, 7625001528297934102, 7670268445836987681 (newsletter), 7684367271522995489 (Soros story, no paper), 7646112181519404320 (copula, no citation).

## 2. Count of relevance

- High (H), about a dozen entries: Baltussen et al.; Khandani & Lo; van der Beck et al.; Brunnermeier & Pedersen; Lou, Polk & Skouras; Bailey & López de Prado (DSR); PBO (Bailey et al. 2017, also the 2026-03-02 video); Sullivan, Timmermann & White; Harvey, Liu & Zhu; López de Prado (CPCV); Shumway & Warther; Kelly-Thorp-MacLean (sizing).
- Medium (M): about 30 papers, mostly B, C or D.
- Low (L): the rest.
- Family A (cross-venue funding carry) has no High paper. The closest are Epps and Hayashi-Yoshida (M, cross-venue timing) and Frazzini-Pedersen (L). The lab's family A has to come from its own funding data, not from these papers.

## 3. Top High papers not in the lab: legal copies and checked claims

Copies were fetched with curl from the authors' or public sites into the scratchpad (`.../scratchpad/papers/`) and read with `pdftotext`. Quotes below are copied from that text.

### 3.1 Brunnermeier & Pedersen (2005), Predatory Trading, JF 60(4)
- Legal copy: `https://www.princeton.edu/~markus/research/papers/predatory_trading_own_webversion.pdf` (author's web version, Oct 2004; the published text may differ).
- Claim, abstract: "if one trader needs to sell, others also sell and subsequently buy back the asset. This leads to price overshooting".
- Worked example, text near the figure: "Since 16 shares are sold and λ = 1, the price drops 16 points, falling to 100 ... the price recovers to 110. Hence, there is a price overshooting of 10 points." The video's 116 to 100 to 110 path matches this example.
- Data and sample: none. Theory with a stylized model (risk-neutral strategic traders, linear demand).
- Test on held data: on Binance or Hyperliquid perps (prices held), find days with a large one-day drop and a funding or open-interest spike; measure whether price rebounds by 1–3 days above the day's low. Name: "post-liquidation overshoot, perp prices". Caveat: the lab holds prices and funding but no liquidation feed, so the forced-seller day is a proxy, which I assume.

### 3.2 Khandani & Lo (2007/2011), What Happened to the Quants in August 2007?
- Legal copies: NBER w14465, `https://nber.org/system/files/working_papers/w14465/w14465.pdf` (text not extracted by pdftotext in the layout I used; only the 2008 text was checked for the 2007 week); New York Fed draft `https://www.newyorkfed.org/medialibrary/media/research/conference/2007/liquidity/Khandani_Lo.pdf`.
- Quote, NBER text: "Starting on Monday, August 6th and continuing through Thursday, August 9th, some of the most successful equity hedge funds in the history of the industry reported record losses."
- Quote on leverage: "If, for example, a portfolio manager had employed a leverage ratio of 8 : 1 for the Book-to-Market portfolio on the morning of August 1st, he would have experienced a cumulative loss of 24% by the close of August 7th".
- Sample: daily US equity returns, January 1995 to December 2007 (quote: "January 3, 1995 to December 31, 2007").
- Mismatch with the video: the video's daily losses (−4.64%, −11.33%, −11.43%) and "9:1 leverage" to recover 1998's return were not found in the text I read. The paper's 24% figure is for one book from 1 August, not the video's three-day sum. Treat the video's numbers as unverified.
- Test on held data: a crowding proxy from the lab's perps: pairs of perps sharing the same funding-rate sign and high open interest, then a joint drawdown. Name: "joint unwind day across crowded perps". Caveat: no holdings data for crowding.

### 3.3 van der Beck, Bouchaud & Villamaina (2024), Ponzi Funds, arXiv 2405.12768
- Legal copy: `https://arxiv.org/pdf/2405.12768` (v1, May 2024).
- Quote, abstract: "We find that flows chasing self-inflated returns predict bubbles in ETFs and their subsequent crashes, and lead to a daily wealth reallocation of $500 Million from ETFs alone." The video's $500 million matches.
- Quote on impact: "Because investors chase self-inflated fund returns at a high frequency, even short-lived impact meaningfully affects fund flows at longer time scales."
- Sample: daily holdings of US ETFs from ETF Global, 2019–2024 (paper section 3).
- Price-impact coefficient: "Across all specifications, we find a price impact of around 0.78" (fund level) and "θ̂ = 0.33" (stock level) (paper). Both match the video.
- Video claims not confirmed: "1,868 US equity ETFs" (no such number in the text I read). Flow share: the paper says "around 2% of all daily flows and 8-12% of flows in the top decile of illiquid funds"; the video says "2 to 3% elsewhere", which I could not find.
- Test on held data: the lab has no ETF holdings or flows. Only a proxy works: trade.xyz equity-perp hourly bars with funding or open-interest changes as flow, and whether the price move decays over 5–10 days. Name: "impact decay on equity perps". Caveat: flow is not observed, so this test is weak.

### 3.4 Sullivan, Timmermann & White (1999), JF 54(5)
- Legal copy: Kevin Sheppard course PDF, `https://bashtage.github.io/kevinsheppard.com/files/teaching/mfe/advanced-econometrics/Sullivan_Timmermann_White.pdf`.
- Quote, abstract: "we utilize White's Reality Check bootstrap methodology to evaluate simple technical trading rules while quantifying the data-snooping bias and fully adjusting for its effect".
- Sample: 100 years of daily DJIA data, 1897–1996; 26 rules (from Brock, Lakonishok & LeBaron, 1992).
- Video check: the video says the single-chart edge is "gone out of sample" after correction. The paper's abstract does not say this in the quoted lines, so I could not confirm the claim from this text.
- Test on held data: apply White's Reality Check (or stepdown) to the lab's own tested grid in `registry/methods.csv`, using the daily nets already on disk. Name: "Reality Check over the registry grid". This is the lab's own multiple-testing check (rule D).

### 3.5 Harvey, Liu & Zhu (2016), ...and the Cross-Section of Expected Returns, RFS 29(1)
- Legal copy: NBER w20592, `https://www.nber.org/papers/w20592.pdf`.
- Quote, abstract: "a newly discovered factor needs to clear a much higher hurdle, with a t-ratio greater than 3.0."
- Sample: 313 published factor papers, tests from 1967 onward.
- Test on held data: re-grade the registry's TESTED rows (`registry/methods.csv`) against a t > 3.0 bar, and project how many would pass at each hurdle. This needs no new data.

### 3.6 Baltussen, Da, Lammers & Martens (2021), Hedging demand and market intraday momentum, JFE 142(1)
- Legal copy: `https://academicweb.nd.edu/~zda/intramom.pdf` (author's page).
- Quote, abstract: "Hedging short gamma exposure requires trading in the direction of price movements".
- Sample: 17 developed-market equity index futures, plus bonds, commodities and currencies, December 1974 to May 2020.
- Sharpe: the abstract gives "annualized Sharpe ratios between 0.87 and 1.73 at the asset class level". The video's "1.73 on equity futures" is the top of that range; I did not isolate the equity number.
- Test on held data: ES hourly bars (held) with SqueezeMetrics GEX (held): regress the 15:00–16:00 return on the 09:30–15:00 return, split by the sign of GEX the day before. Caveat: the lab's ES bars are hourly, so the paper's last-half-hour window cannot be isolated; the test is coarser than the paper.

## 4. Checks of the video's numbers against the papers

- Brunnermeier-Pedersen: the 116 → 100 → 110 example matches the paper (section 3.1).
- Khandani-Lo: the day-by-day losses and the 9:1 claim do not match the text I read (section 3.2).
- van der Beck et al.: $500 million and 0.78 / 0.33 match. "1,868 ETFs" and "2 to 3%" do not (section 3.3).
- Baltussen et al.: the 1.73 Sharpe is the top of an asset-class range (section 3.6).
- Sullivan-Timmermann-White: the "gone out of sample" claim is not in the abstract I read (section 3.4).
- Shumway & Warther: not fetched. The JSTOR and Wiley copies are paywalled, and the BYU repository page (`https://scholarsarchive.byu.edu/facpub/9279`) gave no PDF link in my fetch. The video's "−55%" is unverified in this room.

## 5. Gaps

- Not fetched: Shumway & Warther (paywalled); Glosten-Milgrom and Kyle (journal-only, per the intake notes); Almgren-Chriss (403 in the intake notes); Bonart 2026 (not opened).
- Not verified: the video's "Proposition 5" and "predation fiercest when predators are few" (Brunnermeier-Pedersen); the Harvey-Liu-Zhu "projections" beyond the abstract.
- Family A (cross-venue funding carry) has no High paper here. The next lead for it is the Epps / Hayashi-Yoshida timing question applied to perp funding snapshots, which I have not tested.
