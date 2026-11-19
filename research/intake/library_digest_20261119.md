# Library digest: five readers, five domains (2026-11-19)

- **Asked by the owner (2026-11-19).** Read as many books as possible with Haiku readers, each reducing a book to a
  message, with the important parts understood. The ask was five readers of up to 100 books each.
- **What was done.** Five Haiku research agents, one per domain, did not overlap.
  - Legally free sources only: author-hosted, open-licence or publisher-free texts, arXiv, and regulator reports. No
    piracy sites, no paywall bypass.
  - Their full notes, with exact read scopes, are in `library_20261119/` (one file per domain). This page is the
    session's synthesis.
- **Scope, honestly.** About 100 sources were reached in total: 11 to 26 per reader, not 100. Most were read in
  targeted parts (contents, introduction and 1-3 relevant sections), not cover to cover. Partial reads are marked
  partial in the notes.
  - Several classics were not legally free or not reachable from the sandbox: Almgren-Chriss (403), ESL (TLS failure),
    the main text of Hasbrouck, Cartea et al. and Roncalli, Hansen's Econometrics, and SSRN papers (403).
- **Status of every idea below.** Each is a research reference, not demonstrated alpha.
- **One process note.** The statistics reader made one stray attempt to create a remote session, outside its task.
  The permission classifier denied it; it did not retry, and nothing else was affected.

## Coverage by domain
| Domain | Notes | Sources reached | Read beyond abstract | Main sources |
|---|---|---|---|---|
| Statistics and inference | `stats.md` | 21 | about 20 (targeted sections) | Ramdas & Wang (e-values book), Lattimore-Szepesvári (bandits), BDA3, Shalizi ADA, MacKay, Durrett, Vershynin, Davidson-MacKinnon (2021 draft), Hyndman FPP3, Gelman-Hill-Vehtari |
| Microstructure and execution | `micro.md` | 26 | about 9 (section-level) | Bouchaud impact review, Cont-Kukanov-Stoikov OFI, Donier-Bonart (Bitcoin square-root impact), Avellaneda-Stoikov, Guéant-Lehalle-Fernandez-Tapia, Huang-Lehalle-Rosenbaum, Gould-Bonart, Lehalle-Mounjid |
| Derivatives, funding, crypto | `deriv.md` | 15 | 11 | He-Manela-Ross-von Wachter and Ackerer-Hugonnier-Jermann (perpetual pricing), Christin et al. (crypto carry), Koijen et al. (carry), ESMA 2026 statement, venue funding specs |
| Risk, portfolio, sizing | `risk.md` | 11 | 11 | Palomar (portfolio optimisation), Busseti-Ryu-Boyd (risk-constrained Kelly), Boyd et al. (multi-period), Thorp, Moreira-Muir, Rockafellar-Uryasev, Ledoit-Wolf, Taleb |
| ML and strategy research | `ml.md` | 24 | about 22 (targeted) | Gu-Kelly-Xiu, Kelly-Xiu survey, Hou-Xue-Zhang, Harvey-Liu, Arnott-Harvey-Markowitz, Bailey et al. (PBO, DSR), Moskowitz-Ooi-Pedersen, ESL §7.10.2, Sutton-Barto |

## What the reading says about the lab's binding constraints
The lab's best edge is cross-venue funding carry on thin Kraken perps, now in forward paper (R509, R510, R512). Its
binding constraints are cost and capacity, sizing, and telling real from lucky. The ideas below are ranked by how
directly they act on those constraints.

1. **Cost: enter and exit passively on the thin legs** (micro: Said et al. passive impact; Huang-Lehalle-Rosenbaum
   queue-reactive fills; Gould-Bonart and Lehalle-Mounjid imbalance).
   - The carry book holds pairs for weeks, so it can wait for fills.
   - Kraken's quoted spread on the thin coins is 18-23 bp. Its maker fee is below its taker fee.
   - **To measure from public data:** fill probability and mark-out (adverse selection) of a resting order at the
     best price, from recorded trades and book updates. Then charge the carry book the measured passive cost instead
     of the taker walk.
   - This is the largest lever on R508-R512's 2-3x cost drag, and on capacity.
2. **Sizing: risk-constrained Kelly, bounded by liquidation on each leg** (risk: Busseti-Ryu-Boyd §4-5; Roncalli and
   Frazzini-Pedersen margin; Palomar §7.3).
   - Maximise E log growth subject to E[(1+r)^(−λ)] ≤ 1, with λ = ln β / ln α, so that
     P(wealth ever below α) < β.
   - Size on a shrunk Sharpe, not the in-sample one. The large-scale-inference reading shrank R511's figure from
     13.5%/yr to roughly 5-13%/yr.
   - Cap each leg's leverage by the worst observed one-period adverse move plus the maintenance margin. Liquidation
     binds before growth.
   - **To build:** a sizing function for the small-stake plan, run before `lab.gate.go_real()`.
3. **Inference across lanes: e-BH and null-calibrated bootstraps** (stats: Ramdas & Wang §9.1; Shalizi §23.5;
   Davidson-MacKinnon §7.5; ML: Bailey et al. PBO).
   - **e-BH.** Rejecting rank k when e_(k) ≥ K/(αk) controls FDR under any dependence. The lab's lanes share venues
     and coins.
   - **Stationary bootstraps.** They should resample under the null (Davidson-MacKinnon's golden rule).
   - **Use.** Calibrate R511's t with coin- and week-clustered resampling and placebo books, as the large-scale-inference
     note proposes.
4. **Mechanism: perpetual pricing with an interest term** (deriv: Ackerer-Hugonnier-Jermann Prop. 3;
   He-Manela-Ross-von Wachter Prop. 2).
   - **The formula.** For a linear perpetual with constant rates, f = (κ − ι)/(κ + r_b − r_a) · x. The interest term ι
     sets a discount, and the no-arbitrage band has width set by trading costs.
   - **Why it matters.** It gives a theory for why floored and unfloored venues price the same coin differently. It
     predicts which coins and regimes widen the spread.
   - **Test.** Regress the observed cross-venue basis on the predicted one.
5. **Regime filter: the calm band** (deriv: venue specs). On floored venues funding is pinned at 0.01%/8 h while the
   premium sits within the clamp. Measure the carry earned in the pinned regime against the free regime.
6. **Model checks on paper P&L** (stats: BDA3 §6.3 posterior predictive checks; Grinstead-Snell §12.3 arcsine law).
   Test whether drawdowns and losing streaks in forward lanes are unusual under the fitted model before calling them
   skill or failure.
7. **Discipline for any predictive lane** (ML: ESL §7.10.2 selection inside the folds; Arnott-Harvey-Markowitz
   checklist; Hou-Xue-Zhang replication rates).
   - Most published predictors fail replication. Strong predictive evidence comes from 60 years of US equities, which
     transfers poorly to a few years of crypto.
   - The one family with broad replicated evidence is time-series momentum with volatility scaling (Moskowitz-Ooi-
     Pedersen). The lab's registry should be checked for its earlier momentum nulls before any re-test.

## Not adopted, or weak
- Deep RL for trading: thin, unreplicated evidence, and the stability problems of off-policy learning (Sutton-Barto
  §11.3).
- Crypto ML accuracy claims: single studies, not replicated.
- Avellaneda-Stoikov market making as an edge in itself: the model is standard, but no source read shows net profit
  at this scale. Only a paper lane with mark-outs would say.
- Hawkes timing models: likely too few events on $5k-100k/day coins (the reader's inference).

## Checks by the session
- **Consistent with their standard published forms** (formulas read by the readers, not re-derived here):
  - the e-BH rule;
  - Ville's inequality, which is also in `anytime_valid_20261119.md`;
  - the Avellaneda-Stoikov reservation price and spread;
  - the risk-constrained Kelly constraint.
- **Not checked:** the Ackerer-Hugonnier-Jermann formula, which was read as a statement only. Treat it as a
  hypothesis to test.
