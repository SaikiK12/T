# Microstructure / execution reading notes

Downloads: /tmp/claude-0/-home-user-T/a4c99094-0eba-54d5-9f6a-3abc85cabed2/scratchpad/books/micro/pdfs/
Text extracts: .../books/micro/raw/ (pdftotext, reading order)

Legal sources only: arXiv author PDFs (arxiv.org/pdf/ID), arXiv-hosted, author-hosted (Avellaneda, NYU).
Rejected: NYU Almgren-Chriss PDF (403 "read-protected" on math.nyu.edu / courant.nyu.edu);
a third-party smallake.kr copy was NOT used (not clearly legal). SSRN 1695596 (VPIN) 403.
Fed IFDP probes: wrong paper; not used.

## Sources and scope read

1. Gould, Porter, Williams et al., "Limit order books", arXiv:1012.0349 (v4, 2013). Read: pp.1-4 (intro, LOB definitions, depth, relative depth, orders); text-searched and read the impact section IV.F (instantaneous/permanent impact, Hasbrouck concavity) and the optimal-execution review paragraph (Bertsimas-Lo, Almgren-Chriss, Obizhaeva-Wang, Alfonsi et al.). Not read: priority/queue sec III.D-G in full, zero-intelligence and ABM sections, conclusion beyond headings.
2. Bouchaud, "Price Impact", arXiv:0903.2428 (review, 11pp). Read: all sections 1-4.3 (4.4 skimmed).
   - Three mechanisms of impact: forecasting, information, mechanical/statistical.
   - Kyle linear permanent impact; rho(T) correlation measure.
   - Concave impact R(dt,v) ~ v^psi, psi 0.1-0.3 for individual trades, -> 1 at thousands of trades; BARRA sqrt law R = A sigma sqrt(v/V).
   - Transient model: p_T = lambda sum G(N-n) eps_n v_n^psi; beta=(1-gamma)/2; Gatheral no-manipulation if beta+psi>=1.
3. Cont, Kukanov, Stoikov, "The price impact of order book events", arXiv:1011.6402. Read: abstract, sec 2 model, sec 3 estimation (TAQ, 50 stocks).
   - dP = OFI/(2D) + eps, OFI = (L_b - C_b - M_s) - (L_s - C_s - M_b) at best quotes, D = avg depth.
   - Fit R^2 ~65%; beta_i = c / AD^lambda, lambda ~ 1, c fitted (~ 1/2 in stylized model).
   - Square-root volume law follows from OFI ~ sqrt(VOL) scaling (inferred from Eq 13 argument).
4. Donier & Bonart, "A million metaorder analysis of market impact on the Bitcoin", arXiv:1412.4503. Read: abstract, intro, eq (1), sec on fees/stat-arb, Y-ratio results.
   - I(Q) ~ Y sigma (Q/V_D)^delta, delta ~ 1/2; holds on 4 decades; impact holds along the whole metaorder trajectory, not only at the final price; the authors attribute near-complete long-term decay of impact to the uninformed component of order flow.
   - Y ~ sigma/sqrt(V) ratio (Y-ratio collapses on sigma_D/V_D).
5. Bouchaud, Gefen, Potters, Wyart, "Fluctuations and response in financial markets", cond-mat/0307332 (2003/2004). Read: abstract, response function sections, propagator conclusions.
   - R(l)=<(p_{n+l}-p_n) eps_n>, nearly constant over l ~ 100-1000 then decays; bare propagator G0 power-law tuned so prices are diffusive.
   - Bid-ask bounce of D(1) ~ tick.
6. Toth et al., "Anomalous price impact and the critical nature of liquidity", arXiv:1105.1694. Read: abstract, intro, latent order book model, impact vs T/tau_life.
   - Latent order book V-shaped, vanishing at price; delta=1/2 unit execution, ~2/3 for zeta-execution; delta=1 when T>~tau_life.
7. Avellaneda & Stoikov, "High-frequency trading in a limit order book", Quant Finance 8(3) 2008; NYU PDF (math.nyu.edu/~avellane). Read: full (8pp). Equations partly garbled in text extraction; spread formula cross-checked against standard form.
   - Reservation price r(s,q,t) = s - q gamma sigma^2 (T-t).
   - Optimal total spread delta_a+delta_b = gamma sigma^2 (T-t) + (2/gamma) ln(1+gamma/k).
   - Fill intensity lambda(delta)=A exp(-k delta).
8. Guéant, Lehalle, Fernandez-Tapia, "Dealing with the inventory risk", arXiv:1105.3115. Read: abstract, sec 4 asymptotics (Thm 2) and spread limit formula.
   - HJB -> linear ODE system; asymptotic (large-T / inventory-bounded) spread involves (1/gamma)ln(1+gamma/k) plus ratio of ODE coefficients.
9. Guéant, "Optimal market making", arXiv:1605.01862. Read: abstract, intro (general framework and closed-form approximations, multi-asset extension).
10. Fodra & Labadie, "High-frequency market-making with inventory constraints and directional bets", arXiv:1206.4810. Read: abstract, intro remarks (closed-form controls for non-martingale midprice).
11. Guilbaud & Pham, "Optimal high frequency trading with limit and market orders", arXiv:1106.5040. Read: abstract, intro, model structure (Markov spread, Cox fill intensities, HJBQVI).
12. Guilbaud & Pham, "Optimal HFT in a pro-rata microstructure with predictive information", arXiv:1205.3051. Read: abstract only (partial fills via compound Poisson, overtrading risk).
13. Abergel, Huré, Pham, "Algorithmic trading in a microstructural limit order book model", arXiv:1705.01446. Read: abstract, intro, pointers to HJB/Hawkes extension (sec 5).
14. Lehalle & Mounjid, "Limit order strategic placement with adverse selection risk and the role of latency", arXiv:1610.00261 (v4 2018). Read: abstract, intro, sec 2 imbalance stylized fact (eq 1), latency-cost results.
    - Imb = (Q_bid - Q_ask)/(Q_bid+Q_ask); E[(P_{t+dt}-P_t) sign(Imb)|Imb]>0.
    - Latency cost rises with latency factor tau; higher with adverse-selection sensitivity alpha.
15. Gould & Bonart, "Queue imbalance as a one-tick-ahead price predictor", arXiv:1512.03492. Read: abstract, models, logistic-fit results (large-tick vs small-tick).
    - Logistic P(up|I); out-of-sample binary classification improvement 50-60% (large tick), 10-30% (small tick).
    - P(up | I near 1) ~ 0.8-0.9 large tick vs 0.6-0.7 small tick.
16. Huang, Lehalle, Rosenbaum, "Simulating and analyzing order book data: the queue-reactive model", arXiv:1312.0563. Read: abstract, model description sec 2.3, invariant distribution formula for independent queues.
    - Each queue: birth-death process; intensities lambda^L(n), lambda^C(n), lambda^M(n) depend only on queue size n.
    - Invariant pi(n)=pi(0) prod rho(k), rho(n)=lambda^L(n)/(lambda^C(n+1)+lambda^M(n+1)).
17. Bacry, Mastromatteo, Muzy, "Hawkes processes in finance", arXiv:1502.04592 (2015 review). Read: abstract, stationarity/branching (sec 1-3 partial), sec 5 optimal execution, sec 6 level-I order book (Large resiliency kernel).
    - Alfonsi-Blanc: no price manipulation with Hawkes iff self-excitation compensates resilience (martingale condition).
18. Said, Bel Hadj Ayed, Husson, Abergel, "Market impact: a systematic study of limit orders", arXiv:1802.08502 (v5, 2022). Read: abstract, sec on passive limit orders, square-root sec, fair pricing sec.
    - Power-law temporary impact fits, exact fits from the paper: aggressive all-metaorders y=0.54 x^0.45; Omega10 y=0.63 x^0.51; Omega30 y=0.80 x^0.53. Passive-execution metaorders (Omega10 y=0.37 x^0.61; Omega30 y=0.40 x^0.62): the paper reports smaller impact, insensitive to metaorder size (its main point).
    - Paper finds it beneficial to use passive limit orders (for impact control).
19. Zarinelli, Treccani, Farmer, Lillo, "Beyond the square root", arXiv:1412.2152. Read: abstract, intro, impact-surface discussion.
    - Log form fits better than power over 5 orders of magnitude of Q/V_D; impact surface in duration F and participation eta.
20. Benzaquen, Donier, Bouchaud, "Unravelling the trading invariance hypothesis", arXiv:1602.03011. Read: abstract only.
    - I = W/N^{3/2} not invariant across contracts; I/C (C = avg spread cost of a trade) more stable.
21. Bucci, Lillo, Bouchaud, Benzaquen, "Are trading invariants really invariant? Trading costs matter", arXiv:1902.03457. Read: abstract, intro, sec 4.1 summary.
    - R^2 > 0.8 between I and total trading cost (spread + impact) per bet; invariant ratio I/cost has much lower dispersion.
22. Bucci, Benzaquen, Lillo, Bouchaud, "Slow decay of impact in equity markets: insights from ANcerno", arXiv:1901.05332. Read: abstract, intro.
    - Relaxation after metaorder end: ~2/3 of peak at end of day, power-law decay, asymptote ~1/2 of end-day impact at ~50 days; need deconvolution for multi-day sign correlation.
23. Jaisson, "Market impact as anticipation of the order flow imbalance", arXiv:1402.1288. Read: abstract, intro.
    - Linear permanent impact + martingale price -> impact function exponent linked to long-memory exponent of order-sign correlation (Hawkes near-unstable flow).
24. Dall'Amico, Fosset, Bouchaud, Benzaquen, "How does latent liquidity get revealed in the limit order book?", arXiv:1808.09677. Read: abstract, intro.
    - Latent-order conversion mechanism; market instability threshold where conversion too slow; estimation of latent book from real data for >100 assets.
25. Sadighian, "Deep reinforcement learning in cryptocurrency market making", arXiv:1911.08647. Read: abstract, reward discussion (sec on reward functions). ML domain; noted for completeness.
26. Kelly & Yudovina, "A Markov model of a limit order book: thresholds, recurrence, and trading strategies", arXiv:1504.00579. Read: abstract only.

## Sources not legally readable from this session
- Almgren & Chriss (2000/2001) optliq.pdf at NYU: 403 read-protected.
- Kyle (1985), Glosten & Milgrom (1985): journal-only; no legal free copy checked.
- Easley, Lopez de Prado, O'Hara VPIN: SSRN 1695596 returned 403; not used.
- Stoikov "The micro-price": not located on arXiv; not checked further.
- Cartea-Jaimungal-Penalva book; Hasbrouck "Empirical Market Microstructure"; O'Hara; Lehalle-Laruelle; Abergel et al. book; Bouchaud et al. "Trades, Quotes and Prices": paywalled books; no free author copy located in this session (arXiv search for titles did not return them).
- arXiv API rate-limited (429), so search used arXiv HTML listing.

## Key formulas in the lab's terms (for the digest)
- OFI price model (CKS): dP = (OFI)/(2D) with OFI from best-quote queue changes.
- Square-root: I(Q) ~ Y sigma (Q/V_D)^{1/2}; better fit: logarithmic (Zarinelli et al.).
- Passive vs aggressive: Said et al. find lower, size-insensitive impact for passive execution.
- Queue-reactive invariant distribution (Huang-Lehalle-Rosenbaum).
- AS quotes: r = s - q gamma sigma^2 (T-t); spread gamma sigma^2 (T-t) + (2/gamma) ln(1+gamma/k).
