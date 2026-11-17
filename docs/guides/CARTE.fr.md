# Carte du projet : toutes les expériences, rangées par famille

[Accueil](../../README.md) · [Statut](../STATUS.md) · [Guide de lecture](START_HERE.fr.md)

**Page générée** par `python scripts/carte.py` à partir de `registry/rounds.csv` et `registry/lane_families.csv`. Ne pas la modifier à la main. Aucun dossier n'a été déplacé : les règles figées des expériences pointent vers leurs chemins.

## Où on en est
- **Argent réel engagé : aucun.** Ce qui est vrai aujourd'hui, les dates et les décisions qui t'attendent sont dans le [Statut](../STATUS.md).
- **Le plan** : [plan du 17-11-2026](../reviews/plan_20261117.md), revu le même jour avec la [salle de réflexion](../reviews/room_haiku_20261117.md).
- **La famille qui compte** : le portage de financement crypto, en tête ci-dessous.

## Comment lire
- **R390**, par exemple, est le numéro d'une expérience. Son dossier est `experiments/<nom>/` : `PREREG.md` y fixe les règles avant le test, `FINDINGS.md` donne le résultat.
- **Verdicts** (tels qu'inscrits au registre ; le registre ne s'efface pas, il peut donc être en retard sur FINDINGS) :
  - *confirmé (historique)* : passé sur des données passées, pas encore en conditions réelles ;
  - *partiel* : un morceau tient, le reste non, ou c'est trop petit ;
  - *nul* : pas de gain après frais pour cette règle. C'est un résultat, pas un oubli ;
  - *en cours* : test sur papier ou mesure qui tourne ;
  - *autre* : enregistré, mesure faite, abandonné ou projet.

## Vue d'ensemble

| Famille | Expériences | confirmé (historique) | partiel | nul | en cours | autre |
|---|---|---|---|---|---|---|
| [Portage de financement crypto entre plateformes](#carry) | 40 | 8 | 5 | 5 | 11 | 11 |
| [Portage sur actions, obligations et matières premières](#carry-tradfi) | 13 | 0 | 4 | 4 | 4 | 1 |
| [Autour de l'heure de paiement du financement](#settle) | 10 | 0 | 3 | 5 | 2 | 0 |
| [Événements et annonces](#events) | 23 | 1 | 3 | 12 | 4 | 3 |
| [Flux d'ordres et positionnement des traders](#flow) | 26 | 1 | 0 | 14 | 8 | 3 |
| [Classements de cryptos et chasse aux signaux](#xsec) | 29 | 3 | 4 | 22 | 0 | 0 |
| [Graphiques, niveaux et tendances](#charts) | 24 | 0 | 2 | 21 | 0 | 1 |
| [Week-ends, sessions et calendrier](#calendar) | 20 | 0 | 4 | 9 | 5 | 2 |
| [Options, volatilité et signaux de marché](#options) | 16 | 0 | 0 | 14 | 0 | 2 |
| [Très court terme (secondes, minutes)](#micro) | 12 | 0 | 1 | 7 | 0 | 4 |
| [Coffres et pools des plateformes décentralisées](#vaults) | 11 | 0 | 1 | 4 | 6 | 0 |
| [Portefeuilles, comptes papier et règles de gestion](#portfolio) | 16 | 0 | 3 | 8 | 3 | 2 |
| [Lectures à l'aveugle d'échantillons mis de côté](#reserved) | 2 | 0 | 1 | 0 | 1 | 0 |
| [Mesures de coûts, de données et outils (sans pari)](#infra) | 39 | 0 | 16 | 1 | 3 | 19 |
| **Total** | **281** | **13** | **47** | **126** | **47** | **48** |

<a id="carry"></a>

## Portage de financement crypto entre plateformes

Tenir un achat sur la plateforme où le financement est bas et une vente là où il est haut, sans pari sur le prix, et encaisser l'écart. C'est la seule famille dont le gain tient sur plusieurs plateformes et sur des données lues à l'aveugle (2020, longues traînes). Sur 2021-2026, les meilleurs livres gagnent environ +6 à +16 % par an avant les doutes d'exécution. Les répliques à l'aveugle sur les longues traînes gagnent beaucoup moins (+0,7 à +2,5 % par an). Huit livres sont testés sur papier.

| R | Dossier | Ce qui a été testé (titre du registre, en anglais) | Verdict |
|---|---|---|---|
| R190 | [`carry_v1`](../../experiments/carry_v1) | hedged funding carry on liquid perps | confirmé (historique) |
| R191 | [`carry_holdout`](../../experiments/carry_holdout) | one-shot holdout of the funding carry | confirmé (historique) |
| R220 | [`carry_fwd`](../../experiments/carry_fwd) | R191 funding carry forward on paper, one bar late, Binance and MEXC (spot leg on each venue) | en cours |
| R275 | [`xfund_v1`](../../experiments/xfund_v1) | Cross-venue funding carry on Binance, Gate, Hyperliquid and MEXC | partiel |
| R278 | [`xfund_fwd`](../../experiments/xfund_fwd) | R275's cross-venue funding carry books forward on paper: A gate+hyperliquid L14 th5% K20, B binance+mexc L14… | en cours |
| R277 | [`xfund_kd_v1`](../../experiments/xfund_kd_v1) | R275's best carry book replicated, unchanged, on venues R275 never read: KuCoin and dYdX | partiel |
| R279 | [`xfund_kc_fwd`](../../experiments/xfund_kc_fwd) | R277's two replicating KuCoin carry books forward on paper: A gate+kucoin L14 th5% K20, B binance+kucoin L14… | en cours |
| R280 | [`levcarry_v1`](../../experiments/levcarry_v1) | Leverage and liquidation on the five forward carry books (R278 A/B/C, R279 A/B): L 1-10, isolated or cross ma… | mesure faite |
| R281 | [`sizecarry_v1`](../../experiments/sizecarry_v1) | Confidence-sized carry (M266): the six carry books (R278 A/B/C, R279 A/B, batch binance+gate) with each open… | nul |
| R288 | [`xfund_lt_v1`](../../experiments/xfund_lt_v1) | R275's best carry book (L14d th5% K20) replicated, unchanged, on six venue sets with Lighter (0/0 fees): bina… | confirmé (historique) |
| R294 | [`xfund_lt_fwd`](../../experiments/xfund_lt_fwd) | R288's mexc+lighter carry book forward on paper: A mexc+lighter L14 th5% K20 | en cours |
| R309 | [`capital_mix_v1`](../../experiments/capital_mix_v1) | Fixed initial-capital MEXC+Lighter carry and spot-trend allocation | nul |
| R327 | [`dated_carry_v1`](../../experiments/dated_carry_v1) | Inverse dated-carry source/account component; terminal driver ratio-format failure | partiel |
| R328 | [`dated_carry_v2`](../../experiments/dated_carry_v2) | Same-data exact-ratio dated carry: small conditional margin, actual net unknown | partiel |
| R335 | [`locked_carry_v1`](../../experiments/locked_carry_v1) | The guarantee engine: coin-margined cash-and-carry locked to expiry on Binance BTC/ETH quarterlies vs the 3-m… | mesure faite |
| R382 | [`fundvol_v1`](../../experiments/fundvol_v1) | M455 sizing half: trailing-volatility scaling or gating of R277 gate+kucoin carry book (saved daily net), cho… | nul |
| R384 | [`xfundint_v1`](../../experiments/xfundint_v1) | Settlement-interval audit of R277's KuCoin carry (gate+kucoin, binance+kucoin L14d th5% K20): replay of lab/x… | partiel |
| R390 | [`xfund_bg_fwd`](../../experiments/xfund_bg_fwd) | R286 C14's binance+gate cross-venue carry book (R275 L14d th10% K20) forward on paper from 2026-11-04 | en cours |
| R391 | [`reserved_batch2`](../../experiments/reserved_batch2) | Reserved batch 2: R275's carry book (L14d th5% K20) on the KuCoin, dYdX and Lighter long-tail samples with ME… | confirmé (historique) |
| R405 | [`lockcarry_fwd`](../../experiments/lockcarry_fwd) | R335's locked cash-and-carry forward on paper on Deribit BTC/ETH: executable locked yield vs the T-bill hourl… | abandonné |
| R406 | [`lockcarry_fwd2`](../../experiments/lockcarry_fwd2) | R335's locked cash-and-carry forward on paper on Deribit BTC/ETH (R405 with its FRED fetch fixed): executable… | en cours |
| R407 | [`locked_carry_mechanics_v1`](../../experiments/locked_carry_mechanics_v1) | Exact fee-aware inverse carry sizing and grid-exit cash mechanics on invented inputs | mesure faite |
| R412 | [`boroslock_v1`](../../experiments/boroslock_v1) | M480 item 97: does a Boros (Pendle) funding-rate lock at the best bid deliver its locked APR? Matured BTC/ETH… | mesure faite |
| R413 | [`boroslock_fwd`](../../experiments/boroslock_fwd) | M480 forward: Boros funding locks on paper at live order-book bids ($10k), BTC/ETH on Binance and Hyperliquid… | en cours |
| R418 | [`kraken_carry_v1`](../../experiments/kraken_carry_v1) | Kraken EEA fixed-quantity carry: funding gaps, funded capital and current costs | enregistré |
| R424 | [`cde_carry_screen_v1`](../../experiments/cde_carry_screen_v1) | Fixed CDE/Kraken opposing-perp net proxy economics with current fees, recorded-depth drag and segregated cash… | enregistré |
| R430 | [`okxcarry_v1`](../../experiments/okxcarry_v1) | M484 gate 0: static short OKX Europe X-Perp / long spot carry on BTC and ETH over every funding print the pub… | nul |
| R437 | [`carry_v2_audit_v1`](../../experiments/carry_v2_audit_v1) | Accounting audit: R275's 7 headline carry books (incl. forward R278 A/B/C, R390 A) re-run on the M468 engine… | confirmé (historique) |
| R438 | [`carry_v2_audit_kc_v1`](../../experiments/carry_v2_audit_kc_v1) | Accounting audit: R277's two KuCoin carry books (forward R279 A gate+kucoin, B binance+kucoin) re-run on the… | confirmé (historique) |
| R439 | [`carry5_v1`](../../experiments/carry5_v1) | R275's all-four carry rule (L14d th10% K20) as one book over five venues (Binance, Gate, Hyperliquid, MEXC, K… | confirmé (historique) |
| R440 | [`xfund5_fwd`](../../experiments/xfund5_fwd) | R439's five-venue carry book (binance+gate+hyperliquid+mexc+kucoin L14d th10% K20) forward on paper from 2026… | en cours |
| R441 | [`xperp_carry_v1`](../../experiments/xperp_carry_v1) | M490 OKX Europe alt X-Perp carry: short the crypto X-Perps with trailing 7-day realized funding >= 10%/yr (ex… | en cours |
| R443 | [`xperp_hl_v1`](../../experiments/xperp_hl_v1) | M502 cross-venue funding carry between OKX Europe crypto X-Perps and Hyperliquid perps (the two perp venues f… | en cours |
| R444 | [`hlspot_carry_v1`](../../experiments/hlspot_carry_v1) | M503 Hyperliquid spot-against-perp carry on one venue: long the USDC spot pair (HYPE or a Unit-bridged coin s… | nul |
| R445 | [`hlspot_pm_v1`](../../experiments/hlspot_pm_v1) | M504 R444's Hyperliquid spot-against-perp carry on HYPE and BTC only (the spot tokens with a listed portfolio… | en cours |
| R483 | [`carryhurdle_v1`](../../experiments/carryhurdle_v1) | M478/M481 gate 0: do the six forward cross-venue carry books (R278 A/B/C, R390 A, R279 A/B; R437/R438 engine… | confirmé (historique) |
| R499 | [`carrycost_hist_v1`](../../experiments/carrycost_hist_v1) | M547 measurement: R390's C14 book (binance+gate, R275 v1) with each real entry and exit 2021-07..2026-09 char… | enregistré |
| R500 | [`carrycost_hist_v2`](../../experiments/carrycost_hist_v2) | M547 measurement (supersedes R499 before any cost was read): R390's C14 book (binance+gate, R275 v1) with eac… | enregistré |
| R501 | [`cmecarry_v1`](../../experiments/cmecarry_v1) | M548 gate 1 on history: CME bitcoin futures (MBT costs) against the Binance perp, s = 7-day funding - basis t… | enregistré |
| R502 | [`cmecarry_v2`](../../experiments/cmecarry_v2) | M548 gate 1 on history (supersedes R501, which crashed at its first summary before any statistic): R501's rul… | enregistré |

<a id="carry-tradfi"></a>

## Portage sur actions, obligations et matières premières

Le même principe sur des perpétuels d'actions, d'obligations et de gaz ou de pétrole (trade.xyz, Lighter, OKX Europe), couverts par l'actif réel. Quelques résultats partiels sur des historiques courts ; plusieurs tests sur papier, lus en 2027.

| R | Dossier | Ce qui a été testé (titre du registre, en anglais) | Verdict |
|---|---|---|---|
| R389 | [`lighter_roll_fwd`](../../experiments/lighter_roll_fwd) | Lighter BRENTOIL index roll steps: does the book lag the documented step? (M462, forward paper) | abandonné |
| R436 | [`stock_carry_v1`](../../experiments/stock_carry_v1) | M493 gate 0: weekly short of the top trailing-funding MEXC US-stock/ETF perps, each hedged with the same noti… | nul |
| R442 | [`xperp_stock_v1`](../../experiments/xperp_stock_v1) | M501 OKX Europe stock X-Perp carry: short the X-Perps of 62 US-listed stocks with trailing 7-day realized fun… | nul |
| R470 | [`xvfund_v1`](../../experiments/xvfund_v1) | M527 gate 0: cross-venue funding carry on the same US stock perp, trade.xyz against Lighter (R465's 50 pairs)… | nul |
| R474 | [`tltcarry_fwd`](../../experiments/tltcarry_fwd) | M529 forward: hedged TLT carry, long the iShares $ Treasury Bond 20+yr UCITS ETF (DTLA, London) and short the… | en cours |
| R475 | [`hip3stock_v1`](../../experiments/hip3stock_v1) | M530 gate 0: weekly-selected funding carry on trade.xyz US-stock perps (short up to 5 perps with trailing 28-… | partiel |
| R476 | [`hip3other_v1`](../../experiments/hip3other_v1) | M530 replication: R475's frozen stock-perp funding carry (5 slots, enter >= 12%/yr trailing 28-day funding, e… | partiel |
| R477 | [`xyztwin_v1`](../../experiments/xyztwin_v1) | M531 gate 0: R475's frozen funding carry (5 slots, enter >= 12%/yr trailing funding, exit < 6%, M = 1/3) on 1… | partiel |
| R478 | [`rollcarry_v1`](../../experiments/rollcarry_v1) | M532 gate 0: short trade.xyz's futures-priced perps (NATGAS decides; CL, BRENTOIL reported) and hold the US f… | partiel |
| R479 | [`hip3carry_fwd`](../../experiments/hip3carry_fwd) | M530/M531 forward: R475's weekly funding-carry rule from 2026-11-16 on two books: S, every HIP-3 dex's US-sto… | en cours |
| R480 | [`futroll_fwd`](../../experiments/futroll_fwd) | M532 forward: short trade.xyz's NATGAS perp (decides; CL and BRENTOIL reported) hedged with the NYMEX contrac… | en cours |
| R481 | [`ltroll_v1`](../../experiments/ltroll_v1) | M532 on Lighter, gate 0: short Lighter's futures-priced perps (NATGAS decides; WTI, BRENTOIL, XCU reported) h… | nul |
| R482 | [`xvroll_fwd`](../../experiments/xvroll_fwd) | M533 forward: short trade.xyz's NATGAS perp and long Lighter's at equal notional (decides; WTI and BRENTOIL r… | en cours |

<a id="settle"></a>

## Autour de l'heure de paiement du financement

Encaisser le financement juste avant et après l'heure où il est payé. Quelques résultats partiels, mais petits ou rares une fois les frais et le délai comptés. Les tests sur papier se sont arrêtés avec le conteneur le 6 novembre 2026.

| R | Dossier | Ce qui a été testé (titre du registre, en anglais) | Verdict |
|---|---|---|---|
| R223 | [`settle_v1`](../../experiments/settle_v1) | funding-settlement capture: hold 1 h before to 1 h after a settlement when the last rate is beyond +/-0.20% (… | nul |
| R353 | [`settlehop_v1`](../../experiments/settlehop_v1) | Settlement-window hop (M267): collect a 4/8 h venue's funding lump (MEXC, Binance, Gate) hedged on an hourly… | nul |
| R354 | [`settlehop_pred_v1`](../../experiments/settlehop_pred_v1) | Settlement-window hop (M267) on a point-in-time predicted rate: Binance's premium formula rebuilt at T-1h (F… | partiel |
| R355 | [`settlehop_fwd`](../../experiments/settlehop_fwd) | R354's settlement hop forward on paper: MEXC's displayed rate at T-1h vs Lighter's hourly rate (e = F - 2h),… | en cours |
| R356 | [`settlehop_exit_v1`](../../experiments/settlehop_exit_v1) | R354's 87 settlement hops (Binance + Lighter, theta 0.5%) closed at the 1-minute close of T + 1/2/5/15/30 min… | partiel |
| R362 | [`settleticks_v1`](../../experiments/settleticks_v1) | Binance aggTrades around R354's 221 theta 0.3% settlement hops: a taker against the receiving side entering a… | nul |
| R363 | [`settlelit_v1`](../../experiments/settlelit_v1) | Lighter route of R354's settlement hops: position on Lighter against the side that received Binance's deep lu… | partiel |
| R364 | [`settlelit_fwd`](../../experiments/settlelit_fwd) | R363's Lighter settlement scalp forward on paper: Binance's live predicted rate at T-1h+20s vs Lighter's last… | en cours |
| R387 | [`settlelit_1h_v1`](../../experiments/settlelit_1h_v1) | M460: R363's Lighter settlement scalp (enter before T, cover T+1 min, against the side that received Binance'… | nul |
| R388 | [`forcedswitch_v1`](../../experiments/forcedswitch_v1) | Binance forced hourly switch as a natural experiment: post-rule switch prints vs pre-rule prints (M461) | nul |

<a id="events"></a>

## Événements et annonces

Parier sur ce qui suit une annonce : déblocage de jetons, délistage, nouveau contrat, publication économique. La vente avant un déblocage de jetons est partiellement confirmée ; la plupart des autres sont nuls. Plusieurs tests sur papier n'ont plus d'écrivain depuis le 6 novembre 2026.

| R | Dossier | Ce qui a été testé (titre du registre, en anglais) | Verdict |
|---|---|---|---|
| R180 | `unlocks_sf` | unlock-short paper forward | armé |
| R181 | `unlocks_deep` | what drives the unlock short | confirmé (historique) |
| R188 | [`listings_v1`](../../experiments/listings_v1) | returns after new perp listings | nul |
| R189 | [`listings_holdout`](../../experiments/listings_holdout) | one-shot holdout of the new-listing fade | nul |
| R265 | [`unlocks_v1`](../../experiments/unlocks_v1) | Unlock short replication (E01, old R179 rule): short close D-7 to close D on insider/privateSale cliffs >=1%… | partiel |
| R266 | [`unlocks_fwd`](../../experiments/unlocks_fwd) | R265 unlock short forward on MEXC paper: events from the recorded daily calendar snapshot (point-in-time), ti… | en cours |
| R267 | [`delist_v1`](../../experiments/delist_v1) | Delisting-notice short (old E03, spec S2): short the USD-M perp at the first hourly open after a Binance 'Wil… | nul |
| R268 | [`delist_fwd`](../../experiments/delist_fwd) | Spot delisting-notice short forward on MEXC paper (R267 logged variant 5): tickets from the notice recorder's… | en cours |
| R269 | [`montag_v1`](../../experiments/montag_v1) | Monitoring Tag short: short the USD-M perp at the first hourly open after Binance extends its Monitoring Tag… | nul |
| R270 | [`montag_fwd`](../../experiments/montag_fwd) | Monitoring Tag short forward on MEXC paper (R269 logged variant 2): tickets from the notice recorder's first_… | en cours |
| R271 | [`announce_v1`](../../experiments/announce_v1) | Every Binance announcement type as one family: long and short, four horizons, one reality check | nul |
| R273 | [`fundext_v1`](../../experiments/fundext_v1) | Onset of extreme funding on every Binance perp: long and short, four horizons, one reality check | nul |
| R272 | [`announce_fwd`](../../experiments/announce_fwd) | R271's funding-frequency long 1 h and pre-listing short 168 h forward on MEXC paper (notices first seen from… | en cours |
| R274 | [`squeeze_v1`](../../experiments/squeeze_v1) | Shorts after a negative-funding onset, with a protective cover, on Binance and MEXC | nul |
| R258 | [`unlocks_daily_v1`](../../experiments/unlocks_daily_v1) | Fixed R265-event independent daily-price and BTC-hedge check | partiel |
| R259 | [`unlocks_funding_bounds_v1`](../../experiments/unlocks_funding_bounds_v1) | Fixed unlock funding envelopes, notional fees and necessary isolated collateral | partiel |
| R368 | [`eventdrift_v1`](../../experiments/eventdrift_v1) | M444 on Binance TradFi perps, 1-minute bars: after each of 30 EIA crude (WPSR) and 30 natural-gas storage rel… | nul |
| R369 | [`eventlag_fwd`](../../experiments/eventlag_fwd) | M444/M443 forward paper lane on tick quotes: at each EIA gas-storage and crude release 2026-10-29..2026-12-31… | enregistré |
| R370 | [`cmelead_v1`](../../experiments/cmelead_v1) | M444/M443 on tick trades: at each of 60 EIA releases 2026-04..10, when CME's front-month crude or gas future… | fait, verdict à lire dans FINDINGS |
| R460 | [`usdtmint_v1`](../../experiments/usdtmint_v1) | M512 BTC after Tether USDT mints: 262 Issue events on Tron (TronGrid) and Ethereum (Blockscout) 2021-01-02..2… | nul |
| R461 | [`earnperp_v1`](../../experiments/earnperp_v1) | M513 earnings on 24/7 stock perps: 8-K Item 2.02 filings (EDGAR acceptance) after the close (amc) or before t… | nul |
| R485 | [`linstart_v1`](../../experiments/linstart_v1) | M538 gate 0: short a token's OKX USDT swap from the 1Dutc close of D-7 to the close of D+14 around an insider… | nul |
| R488 | [`usdeflow_v1`](../../experiments/usdeflow_v1) | M535 gate 0: does the weekly log change in USDe circulating supply (DefiLlama id 146, end-of-ISO-week stamp)… | nul |

<a id="flow"></a>

## Flux d'ordres et positionnement des traders

Suivre ou contrer les gros comptes et le flux acheteur ou vendeur. Un livre a passé l'historique (R197) mais pas la vérification à l'aveugle (R198) ; les autres sont nuls. Des tests sur papier tournent encore.

| R | Dossier | Ce qui a été testé (titre du registre, en anglais) | Verdict |
|---|---|---|---|
| R196 | [`flow72_v1`](../../experiments/flow72_v1) | short coins entering heavy-taker-selling / top-traders-short bins, 72 h, hedged | nul |
| R197 | [`flow72_v2`](../../experiments/flow72_v2) | three 72 h flow short cells as overlapping slices, universe-hedged | confirmé (historique) |
| R198 | [`flow72_holdout`](../../experiments/flow72_holdout) | one-shot holdout of the 72 h flow slice book | nul |
| R199 | [`flow72_fwd`](../../experiments/flow72_fwd) | forward paper test of the 72 h flow slice book (A) and top_vs_crowd alone (B) on live public data | enregistré |
| R200 | [`flow72_fwd2`](../../experiments/flow72_fwd2) | forward paper test of the 72 h flow slice book (A) and top_vs_crowd alone (B), live public data, TradFi perps… | enregistré |
| R205 | [`xvenue_v1`](../../experiments/xvenue_v1) | top traders vs the crowd measured on Gate, traded on Binance (CLAIMS C06) | nul |
| R206 | [`liq_v1`](../../experiments/liq_v1) | fade Gate liquidation spikes (CLAIMS C07) | nul |
| R211 | [`posfam_v1`](../../experiments/posfam_v1) | halves of top_vs_crowd and the top-account ratio as 72 h slice books | nul |
| R212 | [`posfam_v2`](../../experiments/posfam_v2) | top accounts headcount as a contrarian 72 h slice book | nul |
| R213 | [`delay_v1`](../../experiments/delay_v1) | flow books (R198 A, R200 B) with entry delayed 1-2 h after the signal bar (Codex timing finding) | nul |
| R214 | [`flow72_fwd3`](../../experiments/flow72_fwd3) | R200 forward books entered one bar after the signal bar (Codex timing finding) | en cours |
| R215 | [`mexc_fwd`](../../experiments/mexc_fwd) | R200 forward signals traded on MEXC prices and funding, one bar late (owner venue) | en cours |
| R216 | [`venue_gap_v1`](../../experiments/venue_gap_v1) | flow books split into crypto vs TradFi contracts (archive + forward replay) and Binance vs MEXC prices | mesure faite |
| R218 | [`mexc_fwd_sq`](../../experiments/mexc_fwd_sq) | agreement-squared flow book (R217 X2) on MEXC prices and funding, forward | en cours |
| R221 | [`mexc_seq`](../../experiments/mexc_seq) | sequential decision (futility 90 d, efficacy 182 d, final 365 d; Bonferroni over 3) for the MEXC flow books A… | en cours |
| R226 | [`tradesize_v1`](../../experiments/tradesize_v1) | trade count and mean print size (24 h vs 30 d) as 72 h spread books, tested beyond quote volume (Codex call,… | nul |
| R234 | [`posimpulse_v1`](../../experiments/posimpulse_v1) | 24 h / 72 h change in top-vs-crowd positioning as 72 h spread books, residual vs the level book | nul |
| R240 | [`posimpulse_v2`](../../experiments/posimpulse_v2) | Positioning impulse imp24/H and imp72/H tested on 2024-25 only (K fixed on 2023), follow-up of R234 | nul |
| R252 | [`oiwick_v1`](../../experiments/oiwick_v1) | Fade liquidation-cascade proxies on top-50 perps: hourly OI drop >= 3% plus a >= 3 ATR wick (lower wick: buy;… | nul |
| R255 | [`cascmkt_v1`](../../experiments/cascmkt_v1) | Cascade-count market timing: long the equal-weight top-50 market for 24 h after an hour with >= 3 R252 long-c… | nul |
| R298 | [`lotcap_v1`](../../experiments/lotcap_v1) | Lottery-cluster quintile short with a close-based squeeze cover (M276): score {age, cluster of age/size/vol_m… | nul |
| R303 | [`capit_v1`](../../experiments/capit_v1) | Capitulation buys on Binance perps: hedged deep-dip longs (25-day gap <= -20/30/40%, hold 1/5 d) and the top-… | nul |
| R448 | [`flow_hl_v1`](../../experiments/flow_hl_v1) | M126/M127 R200's flow books on crypto perps only, traded on Hyperliquid's hourly closes and funding (France-r… | en cours |
| R451 | [`flow_hlstock_v1`](../../experiments/flow_hlstock_v1) | M126/M127 R200's flow books on stock, index and commodity perps (R216's TradFi list) traded on Hyperliquid's… | en cours |
| R453 | [`flow_hlstock_mc_v1`](../../experiments/flow_hlstock_mc_v1) | R451's flow books (M126/M127 on xyz stock/commodity perps) re-priced at measured xyz costs: HIP-3 fee by grow… | en cours |
| R458 | [`flow_hl_mc_v1`](../../experiments/flow_hl_mc_v1) | M126/M127 R448's flow books on Hyperliquid's main-dex crypto perps re-priced at measured costs: Hyperliquid t… | en cours |

<a id="xsec"></a>

## Classements de cryptos et chasse aux signaux

Classer les cryptos entre elles (momentum, retour à la moyenne, apprentissage automatique) ou fouiller de grands tableaux de signaux. Des effets bruts existent ; aucun n'a encore tenu après frais sur des données neuves.

| R | Dossier | Ce qui a été testé (titre du registre, en anglais) | Verdict |
|---|---|---|---|
| R182 | `hypermine` | 38-feature search over 900 Binance USD-M perps 2021-2026 | nul |
| R193 | [`maker_v1`](../../experiments/maker_v1) | limit-order entries on the 413 replicated gross edges | nul |
| R194 | [`pack_v1`](../../experiments/pack_v1) | 252 maker cells in one book, BTC-hedged or not, 2021-2025H1 | nul |
| R185 | [`atlas_v1`](../../experiments/atlas_v1) | gross-edge atlas: 284 price + 6 clock + 37 flow views x bins x 5 horizons x groupings | confirmé (historique) |
| R186 | [`merge_v1`](../../experiments/merge_v1) | walk-forward composite of confident atlas cells, cost-threshold trading | nul |
| R187 | [`merge_v2`](../../experiments/merge_v2) | trade-consistent, session-aware merge, with and without flow | nul |
| R192 | [`atlas_ctx`](../../experiments/atlas_ctx) | context lifts: clock, crowding, market state and own order flow vs every signal | confirmé (historique) |
| R195 | [`atlas_mtf`](../../experiments/atlas_mtf) | multi-timeframe: 1 h signals under the coin own 4 h / 24 h state | confirmé (historique) |
| R201 | [`ctxslice_v1`](../../experiments/ctxslice_v1) | replicated excess context pairs (R192+R195) as one slice book | nul |
| R204 | [`ctxslice_v2`](../../experiments/ctxslice_v2) | 12-24 h replicated context pairs as a slice book, one-shot holdout | nul |
| R219 | [`seesaw_v1`](../../experiments/seesaw_v1) | big coins last hours predict alts: lead-lag regression and catch-up, quintile slice books (ALTCOIN_LEADS 1) | nul |
| R222 | [`xsalt_v1`](../../experiments/xsalt_v1) | slow altcoin cross-sections: low beta, residual momentum (+ plain momentum control), MAX both signs, premium… | nul |
| R236 | [`amihud_v1`](../../experiments/amihud_v1) | 30-day Amihud illiquidity as one-week xs8 spread books on top-50 perps | nul |
| R238 | [`xsbattery_v1`](../../experiments/xsbattery_v1) | Eight cross-sectional features (weekly mom/rev, MAX, IVOL, skew, 52w high, funding slope, Abdi-Ranaldo spread… | nul |
| R245 | [`xsrev_v1`](../../experiments/xsrev_v1) | 1-day and 7-day reversal books inside the most and least liquid terciles of the top-50 perps | nul |
| R250 | [`pairs_v1`](../../experiments/pairs_v1) | Pairs trading on top-20/top-50 perps: weekly 30-day formation by distance (Gatev) or Engle-Granger DF selecti… | nul |
| R261 | [`tradlead_v1`](../../experiments/tradlead_v1) | TradFi perps (CMD: XAU/XAG/CL/BZ; EQ: 8 US stocks/ETF) last-hour return leading crypto: market-timing and bet… | nul |
| R276 | [`xvfac_v1`](../../experiments/xvfac_v1) | Cross-venue factors: what Gate and Hyperliquid say about a Binance perp's next days | partiel |
| R282 | [`pitfac_v1`](../../experiments/pitfac_v1) | What the daily point-in-time panel's new sources say about a Binance perp's next days | partiel |
| R287 | [`pcares_v1`](../../experiments/pcares_v1) | PCA residual reversion (Avellaneda-Lee, M298) on the top-50 Binance perps, hourly: K 1/3/5 factors x OU windo… | nul |
| R299 | [`mlrank_v1`](../../experiments/mlrank_v1) | ML cross-sectional rankers (M042): ridge, IC-weighted and GBM on 27 point-in-time (+3 vintage) daily panel fe… | partiel |
| R300 | [`intrars_v1`](../../experiments/intrars_v1) | Intraday cross-sectional relative strength (M318): top-50 perps' move since 00:00 UTC at fixed hours, follow… | nul |
| R301 | [`qbasis_v1`](../../experiments/qbasis_v1) | Quarterly dated-futures basis cross-section on the perps (M170): level and change of the annualized COIN-M ba… | nul |
| R302 | [`fundxs_v1`](../../experiments/fundxs_v1) | Funding-level cross-section net of funding (M263): long the lowest fifth by 3- or 30-day funding, short the h… | nul |
| R304 | [`mlrank_v2`](../../experiments/mlrank_v2) | ML cross-sectional rankers (M042) again without the 3 survivor-leaking columns: ridge/IC/GBM x hold 1/7 d on… | partiel |
| R305 | [`mlaudit_v1`](../../experiments/mlaudit_v1) | Frozen audit of R304's pick: GBM h7 refits without age / risk-only / without risk, fixed low-risk, low-vol an… | nul |
| R308 | [`nagel_v1`](../../experiments/nagel_v1) | Liquidity provision after stress (M325, Nagel 2012): 1-day top-50/150 reversal only after market abs-return,… | nul |
| R332 | [`mlrank_v3`](../../experiments/mlrank_v3) | R304's ML rankers (ridge/IC/GBM x hold 1/7 d, 24 clean features, top 150 Binance perps, API costs) re-run on… | nul |
| R380 | [`hvrev_v1`](../../experiments/hvrev_v1) | M457: weekly 8/9/10-week reversal inside the high-volatility tercile of the top-150 Binance perps, raw and re… | nul |

<a id="charts"></a>

## Graphiques, niveaux et tendances

Règles de chartistes, niveaux, supports et résistances, tendances : plus de 5 000 variantes testées (R263). Nulles après frais, à part deux résultats partiels sur le modèle de niveaux.

| R | Dossier | Ce qui a été testé (titre du registre, en anglais) | Verdict |
|---|---|---|---|
| R203 | [`itsm_v1`](../../experiments/itsm_v1) | intraday time-series momentum: first hour predicts the last (CLAIMS C13) | nul |
| R229 | [`slow_trend_v1`](../../experiments/slow_trend_v1) | Fixed nine-horizon daily spot trend ensemble versus risk-matched passive on six coins | nul |
| R230 | [`weekly_rotation_v1`](../../experiments/weekly_rotation_v1) | Finite weekly spot rotation search | nul |
| R231 | [`partial_execution_v1`](../../experiments/partial_execution_v1) | Partial execution of unchanged slow spot trend targets | nul |
| R232 | [`rebalancing_v1`](../../experiments/rebalancing_v1) | Equal-weight rebalance cadence versus fixed-unit buyhold | nul |
| R237 | [`tsmom_v1`](../../experiments/tsmom_v1) | Cross-asset time-series momentum (12m sign and 1/3/12m blend) on 23 ETF/FX/metal/bond series | nul |
| R239 | [`fxindex_v1`](../../experiments/fxindex_v1) | FX/index battery: G10 spot momentum, dollar trend, VIX reversal SPY/QQQ, Halloween, pre-holiday, VRP measurem… | nul |
| R242 | [`tsbattery_v1`](../../experiments/tsbattery_v1) | Crypto time-series battery: week-open bias, pre-FOMC drift, ETH/BTC alt-season regime, vol-managed trend (top… | nul |
| R243 | [`chartist_v1`](../../experiments/chartist_v1) | Seven classic chart rules (Supertrend+RSI, MACD, Stochastic, CCI, Bollinger fades, Ichimoku, pivot breaks) on… | nul |
| R246 | [`ictlevels_v1`](../../experiments/ictlevels_v1) | ICT levels on hourly bars of the top-50 perps: round-number crosses and rejections, SMT divergence against BT… | nul |
| R247 | [`chartxm_v1`](../../experiments/chartxm_v1) | R243's seven chart rules (Supertrend+RSI, MACD, Stochastic/CCI/Bollinger fades, Ichimoku, pivot breaks) on da… | nul |
| R248 | [`pivotfade_v1`](../../experiments/pivotfade_v1) | Fade a close beyond the prior day floor pivot R1/S1 (mirror of PIVOT_BREAK) on unseen windows: world indices… | nul |
| R249 | [`rnfade_v1`](../../experiments/rnfade_v1) | Fade the first close through a round-number level per coin per UTC day (two- and one-significant-figure grids… | nul |
| R251 | [`lmw_v1`](../../experiments/lmw_v1) | Lo-Mamaysky-Wang kernel chart patterns (HS/IHS, broadening, triangle, rectangle tops and bottoms) on daily ba… | nul |
| R263 | [`brute5k_v1`](../../experiments/brute5k_v1) | 5,472 chart strategies (9 families x 4 timeframes x direction/filter/stop) on the top-20 perps, walk-forward… | nul |
| R284 | [`trendpull_v1`](../../experiments/trendpull_v1) | Trend pullback (Visser, M277): long after the 63-day rate of change resets near zero inside a rising 200-day… | nul |
| R290 | [`auction_v1`](../../experiments/auction_v1) | Auction-market levels on 1-minute bars (owner's term list, M305): value-area re-entry, IB60 and OR15 break, V… | nul |
| R293 | [`er_v1`](../../experiments/er_v1) | Efficiency-ratio forecast and chop-day gate (owner's reel DeF5_5yPtDb, M314): pooled ridge-logit on the reel'… | nul |
| R306 | [`msnr_v1`](../../experiments/msnr_v1) | Malaysian support and resistance (M323) on 4-hour candles: fade or follow the first touch of a fresh A/V leve… | nul |
| R330 | [`level_probability_v1`](../../experiments/level_probability_v1) | Causal close-level probability, payoff and shared-capital cost diagnostic | partiel |
| R333 | [`level_probability_v2`](../../experiments/level_probability_v2) | The owner's break-or-rebound model (M412) at scale: R330's levels/barriers on the point-in-time Binance top 1… | nul |
| R336 | [`levels_mexc0_v1`](../../experiments/levels_mexc0_v1) | R333's frozen level model (M412) re-priced on MEXC's zero-fee perps: 55 coins 0/0 on all five contract snapsh… | partiel |
| R337 | [`levels_lighter_v1`](../../experiments/levels_lighter_v1) | R333's level model (M412) on Lighter's own hourly prices and funding at its measured $1k book cost (fee 0): 9… | nul |
| R372 | [`orb_index_v1`](../../experiments/orb_index_v1) | M206 NAS100 common-parent OR30 with VWAP and volume: 4 fixed accounts x 1x/2x/3x conditional funded bar costs | enregistré |

<a id="calendar"></a>

## Week-ends, sessions et calendrier

Effets de week-end, d'ouverture de séance, de clôture asiatique, de fin de mois. Quelques résultats partiels, testés sur papier et lus en 2027.

| R | Dossier | Ce qui a été testé (titre du registre, en anglais) | Verdict |
|---|---|---|---|
| R235 | [`usindex_calendar_v1`](../../experiments/usindex_calendar_v1) | Turn-of-month and overnight drift on SPY/QQQ, alpha vs buy-and-hold (first non-crypto lane) | nul |
| R244 | [`weekendlink_v1`](../../experiments/weekendlink_v1) | BTC weekend move (Fri 16:00 to Mon 09:00 NY) sets long/short on QQQ and SPY for the first session of the week | nul |
| R256 | [`dow_v1`](../../experiments/dow_v1) | Day-of-week books on SPY, 10 world indices (EW), the USD G10 basket, BTC and top-50 crypto (EW): discovery se… | nul |
| R289 | [`clockflow_v1`](../../experiments/clockflow_v1) | Fixed-clock flows on 1-minute bars (trader talks): US cash-open flush fade/follow (M301, 24) and Deribit Frid… | nul |
| R371 | [`usopen_fwd`](../../experiments/usopen_fwd) | M318/C17 forward paper lane: at 10:00 New York on each NYSE day from 2026-10-29, long the 3 strongest and sho… | enregistré |
| R432 | [`weekend_reopen_v1`](../../experiments/weekend_reopen_v1) | M321+M188 gate 0: at the CME Globex reopen (Sun 18:00 ET), do Binance's 7 TradFi perps (QQQ, SPY, XAU, XAG, C… | nul |
| R435 | [`stock_tugofwar_v1`](../../experiments/stock_tugofwar_v1) | M492 gate 0: overnight-vs-intraday tug of war (Lou-Polk-Skouras) across MEXC US-stock perps; primary B1 long… | nul |
| R457 | [`usopen_dex_fwd`](../../experiments/usopen_dex_fwd) | M318/C17 R371's US-open picks traded where a French resident can: R371's frozen 50-name table filtered to nam… | en cours |
| R459 | [`oilwknd_fwd`](../../experiments/oilwknd_fwd) | M188/M321 R432's oil lead forward on fresh weekends from 2026-11-13 on Lighter WTI and BRENTOIL (France-reach… | en cours |
| R462 | [`xyzwknd_v1`](../../experiments/xyzwknd_v1) | M515 trade.xyz (Hyperliquid HIP-3) US-stock perps over the weekend: fade the perp-only move W (Fri 20:00 to S… | partiel |
| R463 | [`xyzwknd_fwd`](../../experiments/xyzwknd_fwd) | M515 forward: R462's frozen trade.xyz US-stock perp weekend fade (/W/ >= 50 bp, Fri 20:00 to Sun 19:00 ET; fa… | en cours |
| R464 | [`xyzns_wknd_v1`](../../experiments/xyzns_wknd_v1) | M520 R462's weekend fade on trade.xyz index, commodity and FX perps (SP500, XYZ100, GOLD, SILVER, PLATINUM, P… | nul |
| R465 | [`ltwknd_v1`](../../experiments/ltwknd_v1) | M515 R462's frozen weekend fade on Lighter's US-stock perps at zero fee: fade W (Fri 20:00 to Sun 19:00 ET, l… | partiel |
| R466 | [`xvwknd_v1`](../../experiments/xvwknd_v1) | M524 trade.xyz vs Lighter Sunday gap on the same US stock as a hedged pair: sell the dearer venue at Sun 19:0… | fait, verdict à lire dans FINDINGS |
| R467 | [`ltwknd_fwd`](../../experiments/ltwknd_fwd) | M515 forward on Lighter: R465's frozen rule (/W/ >= 50 bp, Fri 20:00 to Sun 19:00 ET on traded 1 h candles; f… | en cours |
| R468 | [`asiaclose_v1`](../../experiments/asiaclose_v1) | M526 Asian single-stock perps (xyz 9, Lighter 9; KRX, TSE, HKEX, SSE) across the daily closure of their home… | partiel |
| R469 | [`asiaclose_c`](../../experiments/asiaclose_c) | M526 confirmation on unseen openings: R468's frozen rule and universe (18 Asian single-stock perps, xyz and L… | en cours |
| R471 | [`cryptomon_v1`](../../experiments/cryptomon_v1) | M521 gate 0: Bitcoin's weekend return W (P 16:00 to S 09:00 New York) against the Monday session move D (open… | nul |
| R472 | [`rebalfront_v1`](../../experiments/rebalfront_v1) | M522 gate 0: front-running balanced-fund rebalancing (Harvey, Mazzoleni and Melone) on SPY/IEF closes: positi… | nul |
| R473 | [`tlteom_v1`](../../experiments/tlteom_v1) | M528 gate 0: end-of-month Treasury rally (Hartley and Schwarz 2019) as a long TLT position over the last 3 tr… | partiel |

<a id="options"></a>

## Options, volatilité et signaux de marché

Prime de volatilité, VIX, gamma des teneurs de marché, flux d'options. Aucun gain à ce jour.

| R | Dossier | Ce qui a été testé (titre du registre, en anglais) | Verdict |
|---|---|---|---|
| R207 | [`carrycrash_v1`](../../experiments/carrycrash_v1) | high market carry predicts BTC crashes (CLAIMS C08) | nul |
| R209 | [`vrp_v1`](../../experiments/vrp_v1) | Deribit DVOL minus realized vol as a BTC/ETH timing signal (CLAIMS C23) | nul |
| R210 | [`cbprem_v1`](../../experiments/cbprem_v1) | Coinbase premium z-score as a BTC/ETH perp signal (CLAIMS C18) | nul |
| R241 | [`volrisk_v1`](../../experiments/volrisk_v1) | SVXY in VIX contango, SVXY contango with calm VIX, and R239's VIXREV-QQQ on 2013-2026 | nul |
| R283 | [`vixpanic_v1`](../../experiments/vixpanic_v1) | VIX panic onsets (VIX>VIX3M, VVIX top 5%, both) -> long SPY/QQQ/BTC perp 5/10/20 d vs random dates (M278, own… | nul |
| R292 | [`dealerflow_v1`](../../experiments/dealerflow_v1) | Dealer gamma from Deribit taker flow (M308): GEX at the UTC close from net taker positions (makers = dealers)… | nul |
| R295 | [`optflow_v1`](../../experiments/optflow_v1) | Deribit option flow leading BTC/ETH perps (M311 block delta flow, M313 net drift): 5 signals x 1/4/24 h | nul |
| R296 | [`charm_expiry_v1`](../../experiments/charm_expiry_v1) | Friday 08:00 UTC Deribit expiry on BTC/ETH perps: settlement-fade slope on expiring near-money position (M303… | nul |
| R297 | [`fundgate_v1`](../../experiments/fundgate_v1) | Market funding response to up days as a market-timing gate (M295): trailing 30-day slope of top-50 funding on… | nul |
| R307 | [`rrskew_v1`](../../experiments/rrskew_v1) | Deribit 25-delta risk reversal (M174) as a weekly BTC/ETH perp timing signal: 30 d / 90 d RR built from every… | nul |
| R385 | [`dvolbeta_v1`](../../experiments/dvolbeta_v1) | M456 DVOL-beta sort (sort half only): trailing 90-day return beta to BTC/ETH DVOL changes, long low / short h… | nul |
| R408 | [`vrpsell_v1`](../../experiments/vrpsell_v1) | M477 crypto variance risk premium: delta-hedged short weekly ATM straddles on Deribit BTC/ETH from held hourl… | abandonné |
| R409 | [`vrpsell_v2`](../../experiments/vrpsell_v2) | M477 crypto variance risk premium (R408 with its stats call fixed): delta-hedged short weekly ATM straddles o… | nul |
| R411 | [`dvolvrp_v1`](../../experiments/dvolvrp_v1) | M477 item 41: Deribit DVOL at day start vs realized volatility of the next 30 days (Binance perp hourly), BTC… | mesure faite |
| R410 | [`vrpexec_v1`](../../experiments/vrpexec_v1) | M477 cost levers on R409 weekly short straddle: maker sale at the ask (trade-through replay on raw Deribit le… | nul |
| R416 | [`gexfilter_v1`](../../experiments/gexfilter_v1) | M486: S&P 500 dealer gamma (SqueezeMetrics' free daily GEX, rank over 252 days) as a predictor of BTC/ETH log… | nul |

<a id="micro"></a>

## Très court terme (secondes, minutes)

Aller plus vite que le carnet d'ordres. Presque tout est nul : le délai de cette machine et les frais mangent l'avantage.

| R | Dossier | Ce qui a été testé (titre du registre, en anglais) | Verdict |
|---|---|---|---|
| R291 | [`vpin_v1`](../../experiments/vpin_v1) | VPIN flow toxicity (owner's reel, M085): exact taker-side and BVC VPIN (50 buckets/day, n 50) added to a HAR… | nul |
| R347 | [`tapelag_lighter_v1`](../../experiments/tapelag_lighter_v1) | Zero-fee Lighter quote-lag scalps toward Binance (M425) on the unread 1-s tape: 6 trials, fill one full secon… | abandonné |
| R348 | [`tapelag_lighter_v2`](../../experiments/tapelag_lighter_v2) | R347's zero-fee Lighter quote-lag scalps (M425) rerun after R347's pre-statistic crash: same rule and 6 trial… | nul |
| R349 | [`minflow_v1`](../../experiments/minflow_v1) | Minute-scale extremes on BTC/ETH/SOL at Lighter's zero-fee book cost (M426) plus absorption/exhaustion (M306)… | partiel |
| R351 | [`minflow_alts_v1`](../../experiments/minflow_alts_v1) | R349's frozen pick (flow fade k5 h5, M426), unchanged, on nine more coins' unread 1-minute bars (BNB XRP TRX… | nul |
| R367 | [`hftlead_v1`](../../experiments/hftlead_v1) | M427 on Binance USDC perps (BTC, ETH) from this container's 100 ms recordings: a resting 0%-maker USDC quote… | fait, verdict à lire dans FINDINGS |
| R386 | [`atlas_tape_v1`](../../experiments/atlas_tape_v1) | Gate-0 screen of seconds-to-minutes conditional returns: 303,520 cells (22+26 features x gates x 5 thresholds… | nul |
| R400 | [`path_response_v1`](../../experiments/path_response_v1) | Arrival-order area and same-price replenishment: bounded equation search beyond the fixed OFI baseline | enregistré |
| R426 | [`maker_pilot_v1`](../../experiments/maker_pilot_v1) | Fixed Lighter commodity two-sided quote partial-fill inventory diagnostic on a short restored source fragment… | enregistré |
| R431 | [`rawlead_v1`](../../experiments/rawlead_v1) | M430+M431 gate 0: does a taker on Binance's USDC perp book, triggered when the USDT book moves >= 2 bp away,… | nul |
| R433 | [`lighter_flow_v1`](../../experiments/lighter_flow_v1) | M441 gate 1 on unread tape: do Lighter commodity-perp taker accounts' signed markouts persist from train days… | nul |
| R434 | [`wti_residual_v1`](../../experiments/wti_residual_v1) | M443 gate 0: cross-venue residual on 24/7 commodity perps (WTI/Brent/natgas/gold on Lighter, Hyperliquid xyz,… | nul |

<a id="vaults"></a>

## Coffres et pools des plateformes décentralisées

Déposer dans les coffres HLP, LLP ou JLP, ou suivre leurs positions. Tests sur papier en cours ; choisir un coffre d'après son passé n'a rien donné.

| R | Dossier | Ce qui a été testé (titre du registre, en anglais) | Verdict |
|---|---|---|---|
| R446 | [`dexvault_v1`](../../experiments/dexvault_v1) | M505 deposits in two public liquidity vaults on perp DEXes that do not exclude France, Hyperliquid's HLP and… | en cours |
| R447 | [`llpstake_v1`](../../experiments/llpstake_v1) | M506 Lighter's LLP pool as a depositor must hold it: per LIT staked (6%/yr), 10 USDC in LLP and a short of 1… | en cours |
| R449 | [`jlphedge_v1`](../../experiments/jlphedge_v1) | M509 two perp-DEX liquidity-pool tokens held against perp shorts on Hyperliquid: book J Jupiter's JLP hedged… | en cours |
| R452 | [`litpoolsel_v1`](../../experiments/litpoolsel_v1) | M507 on Lighter: the operator public pools picked by their past record (top 5 by mean/sd of 90-day daily shar… | nul |
| R450 | [`hlvaultsel_v1`](../../experiments/hlvaultsel_v1) | M507 Hyperliquid user vaults picked by their past record: monthly, top 10 vaults (>=180 days old, >=$500k) by… | nul |
| R454 | [`hlpinv_v1`](../../experiments/hlpinv_v1) | M510 HLP's inventory as a cross-sectional signal on Hyperliquid's main-dex perps: share = HLP child vaults' n… | en cours |
| R455 | [`llpinv_v1`](../../experiments/llpinv_v1) | M511 Lighter LLP's inventory as a cross-sectional signal on Lighter's perps: share = LLP's signed position va… | en cours |
| R456 | [`invcost_v1`](../../experiments/invcost_v1) | M510/M511 cost read: R454's (HLP) and R455's (LLP) inventory books recomputed unchanged and charged measured… | en cours |
| R484 | [`llphouse_v1`](../../experiments/llphouse_v1) | M536 gate 0: does Lighter LLP's day return (house side of the crowd's P&L) predict BTC's next UTC day on Hype… | nul |
| R486 | [`litbuyback_v1`](../../experiments/litbuyback_v1) | M537 gate 0: does Lighter's daily LIT buyback USDC as a share of LIT's perp plus spot quote volume rank-corre… | nul |
| R487 | [`adlstress_v1`](../../experiments/adlstress_v1) | M534 gate 0: worst-case ADL stress bound on 2025-10-10 for the nine audited carry books (six forward decide):… | partiel |

<a id="portfolio"></a>

## Portefeuilles, comptes papier et règles de gestion

Combiner les stratégies, les dimensionner, simuler les règles des challenges de prop firms, le compte papier de 10 000 $. Ces outils ne valent que ce que valent les stratégies combinées.

| R | Dossier | Ce qui a été testé (titre du registre, en anglais) | Verdict |
|---|---|---|---|
| R143 | `funded` | funded-account translation to crypto perps | partiel |
| R144 | `challengeoption` | challenge-option translation to crypto perps | partiel |
| R184 | [`battery_v1`](../../experiments/battery_v1) | adaptive selection: does recent performance pick next week winners out of a mined rule library? | projet |
| R202 | [`propfirm_v1`](../../experiments/propfirm_v1) | lab return streams under prop-firm rule sets (bootstrap pass probability, payouts, own capital) | partiel |
| R208 | [`daylimit_v1`](../../experiments/daylimit_v1) | daily loss/profit limits on the flow slice books (CLAIMS C17) | nul |
| R217 | [`sizing_v1`](../../experiments/sizing_v1) | confidence-scaled multipliers on the flow books vs constant size (time-series rules and cross-coin agreement… | nul |
| R225 | [`vt_fwd`](../../experiments/vt_fwd) | R217 volatility target (R1) applied forward to the MEXC flow books A, B (R215) and X2 (R218), warmed up on th… | en cours |
| R228 | [`allocation_v1`](../../experiments/allocation_v1) | Static convex allocation among archived flow books A/B/X2 | nul |
| R233 | [`regime_v1`](../../experiments/regime_v1) | Flow books A/B/X2 gated by trend x vol regime, and a regime-wise choice among them (MacroHFT) | nul |
| R253 | [`optimizer_v1`](../../experiments/optimizer_v1) | Static long-only min-variance, equal-risk and HRP allocations of A/B/X2 against R228 incumbent | nul |
| R260 | [`dispgate_v1`](../../experiments/dispgate_v1) | Flow books A/B/X2 at half size when 30 d cross-sectional dispersion is in its expanding top tercile and the a… | nul |
| R285 | [`xbook_fwd`](../../experiments/xbook_fwd) | Cross-family forward book (M281): carry (R278 A/B, R279 A/B), flow (R215 A/B, R218 X2) and events (R266, R268… | en cours |
| R257 | [`mixed_signals_v1`](../../experiments/mixed_signals_v1) | Finite regime-conditioned mixed targets versus discovery-selected standalone control | nul |
| R414 | [`famswitch_v1`](../../experiments/famswitch_v1) | Owner's blind-switch idea: exponential weights (HEDGE) and monthly follow-the-leader (FTL) across 12 lab stra… | nul |
| R415 | [`paperacct_fwd`](../../experiments/paperacct_fwd) | Owner's paper account: $10,000 from 2026-11-07, one third each in R285's carry, flow and event families, neve… | en cours |
| R331 | [`confidence_v1`](../../experiments/confidence_v1) | Frozen confidence family paused after training and calibration-fit; later stages unread | enregistré |

<a id="reserved"></a>

## Lectures à l'aveugle d'échantillons mis de côté

Des lots de candidats lus une seule fois sur des données gardées de côté (2020, longues traînes). La lecture de lot 2 (portage) est rangée avec le portage.

| R | Dossier | Ce qui a été testé (titre du registre, en anglais) | Verdict |
|---|---|---|---|
| R286 | [`reserved_batch1`](../../experiments/reserved_batch1) | Reserved batch 1: ten pre-committed candidates (C14 carry, C01 unlock short, C09/C10 notice shorts, C11a/b R2… | en cours |
| R392 | [`reserved_batch3`](../../experiments/reserved_batch3) | Reserved batch 3: C17 (R300 us10 n3 follow, M318) and M319 (08:00-clock k8 n3 follow) on reserved 2020, R275'… | partiel |

<a id="infra"></a>

## Mesures de coûts, de données et outils (sans pari)

Coûts réels des carnets d'ordres, frais, fidélité des données, outils du compte papier, audits. Ces lignes servent à décider ; elles ne gagnent ni ne perdent.

| R | Dossier | Ce qui a été testé (titre du registre, en anglais) | Verdict |
|---|---|---|---|
| R183 | `hypermine_expand` | Bybit perps cross-listed on MEXC: data coverage for 22 new labels | mesure faite |
| R224 | [`mexc_costs`](../../experiments/mexc_costs) | MEXC taker cost from the public order book (spread, impact at $1k/$10k/$50k, fee) for the forward books' coin… | en cours |
| R262 | [`impact_v1`](../../experiments/impact_v1) | Square-root market impact (Y sigma sqrt(Q/V), 30 d stats) on flow books A/B/X2 at capital $1k-$10M on top of… | mesure faite |
| R264 | [`accounting_v1`](../../experiments/accounting_v1) | Bridged gaps vs legacy zero-fill of missing next returns on flow books A/B/X2 (PR #25 audit item 4): measurem… | mesure faite |
| R310 | [`equations_v1`](../../experiments/equations_v1) | Twelve cost-aware funding/basis equations on the fixed R288 MEXC/Lighter universe | fait, verdict à lire dans FINDINGS |
| R311 | [`equations_v2`](../../experiments/equations_v2) | Source-seam corrected repeat of twelve funding/basis policies | fait, verdict à lire dans FINDINGS |
| R312 | [`pair_quotes_v1`](../../experiments/pair_quotes_v1) | First-seen MEXC/Lighter common-lot inputs and conditional crossing costs | partiel |
| R313 | [`stream_quotes_v1`](../../experiments/stream_quotes_v1) | Source-stamped paired quotes and fixed causal access-delay costs | partiel |
| R314 | [`depth_quotes_v1`](../../experiments/depth_quotes_v1) | Matched full-depth/top-level public quote costs with fixed0/300ms controls | partiel |
| R315 | [`funding_values_v1`](../../experiments/funding_values_v1) | Source-typed funding ledger and matched REST/WS reference publication inputs | partiel |
| R316 | [`warm_values_v1`](../../experiments/warm_values_v1) | Matched prestarted and cold fair requests with source-clock economic controls | partiel |
| R317 | [`fee_routes_v1`](../../experiments/fee_routes_v1) | Source-labelled conditional taker fee routes and crossing-floor decomposition | partiel |
| R318 | [`paper_account_v1`](../../experiments/paper_account_v1) | Integrated simulated account, source-aware cash and finite size/exit controls | partiel |
| R319 | [`paired_execution_v1`](../../experiments/paired_execution_v1) | Observed paper paired-fill lifecycle and fixed orphan/unwind economics | partiel |
| R320 | [`owner_acceptance_v1`](../../experiments/owner_acceptance_v1) | Common paper controls; four risk forecasts and exact owner100 acceptance | partiel |
| R321 | [`dependent_null_v1`](../../experiments/dependent_null_v1) | Null-only dependent inference: finite calibration,exact size and power controls | nul |
| R322 | [`funding_prefix_v1`](../../experiments/funding_prefix_v1) | Source-bound encoded funding application and common paper component | partiel |
| R323 | [`continuation_control_v1`](../../experiments/continuation_control_v1) | Finite-deadline carry continuation and fixed-policy paper replay | partiel |
| R324 | [`spot_perp_inputs_v1`](../../experiments/spot_perp_inputs_v1) | Physical spot/perpetual cash and finite public wire input compatibility | partiel |
| R325 | [`spot_perp_costs_v1`](../../experiments/spot_perp_costs_v1) | Source-aware spot/perpetual minimum and quote-cost input compatibility | partiel |
| R326 | [`spot_perp_costs_v2`](../../experiments/spot_perp_costs_v2) | Same-data Decimal and zero-minimum bridge for spot/perpetual quote costs | partiel |
| R373 | [`m090_publication_v1`](../../experiments/m090_publication_v1) | M090 publication engineering interrupted before commit/push/source capture | abandonné |
| R374 | [`m090_content_v2`](../../experiments/m090_content_v2) | M090 one bounded signed-content capture and head-pinned offline replay; UTC/forecast scoring disabled | enregistré |
| R401 | [`carry_cost_qualification_v1`](../../experiments/carry_cost_qualification_v1) | Current carry source qualification on the published R391 cohort; no strategy test | partiel |
| R402 | [`carry_targeted_costs_v1`](../../experiments/carry_targeted_costs_v1) | Targeted public carry contract and lot-matched depth qualification; no strategy test | partiel |
| R403 | [`metrics_archive_qualification_v1`](../../experiments/metrics_archive_qualification_v1) | Two official BTCUSDT metrics archive identities, schemas and raw time labels; no strategy test | mesure faite |
| R404 | [`book_costs_v1`](../../experiments/book_costs_v1) | Taker cost from public order books on every listed dYdX, KuCoin and MEXC perp, 3-hourly to 2026-11-18; cost i… | en cours |
| R417 | [`carry_execution_v1`](../../experiments/carry_execution_v1) | M485 bounded BTC displayed-depth sizes and segregated linear-perp one-leg stress accounting; zero predictive… | enregistré |
| R419 | [`eea_pair_capture_v1`](../../experiments/eea_pair_capture_v1) | M488 bounded inactive Coinbase CDE/Kraken raw capture with delayed book reobservations; zero predictive trials | enregistré |
| R420 | [`ops_takeover_v1`](../../experiments/ops_takeover_v1) | Owner-transferred durable paper operations: one serialized writer, canonical state and committed pre-HTTP res… | enregistré |
| R421 | [`eea_execution_v1`](../../experiments/eea_execution_v1) | M488 fixed CDE/Kraken first-packet displayed-depth execution costs; two explicit raw-unit hypotheses, no fund… | enregistré |
| R422 | [`paper_priority_v1`](../../experiments/paper_priority_v1) | Priority native papers with ordinary HTTP gzip, endpoint reservations and inherited R420 spend; same16MiB byt… | enregistré |
| R423 | [`cde_rate_contract_v1`](../../experiments/cde_rate_contract_v1) | M488 exact sampled Advanced outer funding-rate field versus MDA at declared time; no fitted scale or lag | enregistré |
| R425 | [`atomic_v2_routes_v1`](../../experiments/atomic_v2_routes_v1) | Disclosed prior metadata-only atomic-route RPC source qualification; no economic test | enregistré |
| R427 | [`lighter_trade_contract_v1`](../../experiments/lighter_trade_contract_v1) | Recorded Lighter trade role contract via exact signed base-position identities; two named source conventions | enregistré |
| R428 | [`participant_capture_v1`](../../experiments/participant_capture_v1) | Finite raw Lighter participant windows and selected runtime composition preserving inherited paper spend; no… | enregistré |
| R429 | [`paper_quote_scope_v1`](../../experiments/paper_quote_scope_v1) | Native DTB3 source scope and paper continuity | enregistré |
| R497 | [`gatemaker_v1`](../../experiments/gatemaker_v1) | M546 measurement: what a resting order at the touch earns or loses on Gate's USDT perps (5-second markout) ag… | mesure faite |
| R498 | [`gatefill_fwd`](../../experiments/gatefill_fwd) | M546 forward on paper: R390's C14 Gate leg as a resting order (inside the spread when there is room, else at… | en cours |
