# Le livre des stratégies (précis, vérifié ; mis à jour le 2026-11-26)

- **Pourquoi ce livre.** Le propriétaire, 2026-11-25 : « sois plus précise dans les stratégies, framework directement
  ou ML ». Chaque stratégie est une fiche : instrument, plateforme, règle d'entrée et de sortie, taille, coût, résultat
  net mesuré, capacité, statut, date de décision, maillon faible.
- **Sources.** Les PREREG et FINDINGS de chaque piste. Les chiffres principaux ont été revérifiés sur la page
  (brouillon de la salle : `docs/reviews/room_20261126/strategy_cards_draft.md`).
- **Les journaux scellés des pistes en papier ne sont jamais ouverts avant leur date** : « en cours » veut dire qu'aucun
  résultat n'est lu.

## 0. Le cadre : comment les stratégies se combinent
- **Trois moteurs indépendants :**
  - **A. le portage « design gap »** : une plateforme sans plancher de financement contre une plateforme à plancher ;
  - **B. le retour du week-end** sur les perps d'actions 24 h/24 ;
  - **C. une surcouche ML** sur A (R531).
- **Corrélations mesurées :**
  - entre les livres A de plateformes différentes : −0,04 (R508 contre R519, 343 jours) ;
  - en mois de crise, entre paires A : environ 0,35 en moyenne (Q26) ;
  - A et B n'ont aucun marché en commun.
- **Taille (Thorp) :** au plus la moitié du Kelly, calculée sur l'avantage rétréci (la moitié du niveau mesuré) et sur
  le saut possible, c'est-à-dire la faillite d'une plateforme (`scripts/stake_kelly.py`). Marge croisée par compte,
  jamais isolée par jambe (R280).
- **Filtres de risque à l'entrée (R526, adoptés) :**
  - **agree** : pas d'entrée si les deux jambes diffèrent de plus de 2 % en prix ;
  - **active** : chaque jambe a coté dans au moins 20 des 24 dernières heures.
  - Le stop horaire est rejeté : il double les pertes maximales sur des prix de dernière transaction.
- **Ce qui décide l'argent :** les lectures de décembre, et rien d'autre, fixées d'avance dans
  `docs/reviews/december_decision_20261125.md`.

## A. Portage « design gap »

### A1. Kraken + Hyperliquid (R508 historique ; R509 papier ; lectures rapides R510, R523, R527)
| Champ | Valeur |
|---|---|
| Instruments | perps linéaires Kraken PF_* (offerts aux clients EEA) et perps Hyperliquid ; 111 pièces |
| Signal | financement des 14 derniers jours sur chaque plateforme ; écart = (court − long) × 365/14 |
| Entrée | écart ≥ 5 %/an, du plus large au plus étroit, dans 20 cases ; garde : corrélation des rendements ≥ 0,9 sur 30 jours (20 observations au moins) |
| Position | long sur la plateforme qui paie le moins, court sur l'autre, 1x par jambe ; une case = 5 % du capital |
| Sortie | écart < 2,5 %/an, jambe sans cotation 3 jours, ou contrat retiré |
| Coûts | historique : 7/14/21 bp par jambe et par côté ; papier : coût mesuré du carnet à 1 000 $ + frais preneur (Kraken 5 bp, HL 4,5 bp) |
| Preuve (en échantillon, 2025-12..2026-11, 343 jours) | **+24,28 %/an à 1x, t 7,39** ; chaque mois positif (`experiments/xfund_eea_v1/FINDINGS.md:19-23`) |
| Coûts réels | 2 à 3 fois l'hypothèse 1x (carnets fins à 13,5-16,5 bp par côté) |
| Capacité | 97 % du rendement vient de pièces à moins de 100 k$ de volume par jour sur Kraken ; 20 cases ≈ 40-100 k$ de capital |
| Décision | R510 vers le 19-12 (30 jours) et le 03-01 ; R523 vers le 13-12 / 23-12 ; R527 vers le 15-12 / 25-12 ; R509 vers le 17-02 et le 18-05-2027 |
| Si réussite | mise 1 : 2 000 € (Kraken + Hyperliquid), levier ≤ 1,5, euros en collatéral sur Kraken |
| Maillon faible | un an de données Kraken ; formule de financement Kraken non vérifiée ; l'usure : environ −30 % du niveau par an (cycle 8) |

### A2. Deribit + Hyperliquid (R520 papier ; R521 rapide)
| Champ | Valeur |
|---|---|
| Règle | celle de A1 (14 jours, 5 %, sortie sous la moitié, 20 cases) ; 89 pièces |
| Coûts | carnets mesurés à 1 000 / 2 500 $ + Deribit 3,5 bp, HL 4,5 bp |
| Preuve (historique, 2023-06..2026-11) | **+4,52 %/an à 1x, t 7,02**. Le net de 2026 est d'environ 0 une fois les jambes de prix comptées |
| Décision | R521 vers le 22-12 et le 06-01 ; R520 à 90 et 180 jours notés ; coupe-circuit à −3 % |
| Si réussite | pas de mise sur R521 seul (décision de décembre) |

### A3. Bitfinex + Binance (R524 papier)
| Champ | Valeur |
|---|---|
| Règle | celle de A1 ; 69 pièces ; Binance 5 bp, Bitfinex 6,5 bp + carnets mesurés |
| Preuve (historique, 2 078 jours) | **+5,21 %/an à 1x, t 11,94** ; environ +3,1 %/an en 2025-26 |
| Décision | 90 et 180 jours notés, à partir du 25-11-2026 |
| Maillon faible | les données Bitfinex sont les moins fiables des trois plateformes sans plancher |

### A4. Les 12 paires en portefeuille (R525, historique)
| Champ | Valeur |
|---|---|
| Construction | Kraken, Bitfinex, Deribit × Binance, Gate, Hyperliquid, KuCoin ; chaque jour, moyenne à poids égal des paires vivantes |
| Preuve (en échantillon, 2021-01..2026-09) | **+7,77 %/an à 1x, Sharpe 5,5, t 11,96, perte max −0,73 %** (`experiments/gap_breadth_v1/FINDINGS.md:14-15`) |
| Par année (1x) | 2021 +13,7 · 2022 +4,1 · 2023 +9,4 · 2024 +8,6 · 2025 +2,2 · 2026 (à sept.) +9,5 |
| Risque | avec un jour de retard de décision, Bitfinex+Gate tombe à −11,4 %/an ; LUNA (mai 2022) : −85,9 % du capital du livre en un jour, sans les filtres R526 |
| Statut | historique uniquement ; seules les pistes papier A1-A3 confirmeront |

## B. Retour du week-end sur les perps d'actions 24 h/24

### B1. trade.xyz, directionnel (R463 papier) ; B2. Lighter (R467 papier)
| Champ | Valeur |
|---|---|
| Instruments | perps d'actions US : trade.xyz sur Hyperliquid (76 marchés) ; Lighter (50 marchés, 0 frais) |
| Signal | W = mouvement du vendredi 20:00 au dimanche 19:00 (heure de New York) |
| Entrée | \|W\| ≥ 50 bp : vente si W > 0, achat si W < 0, le dimanche 19:00 |
| Sortie | dimanche 22:00 (New York), après la réouverture |
| Coûts | frais preneur + coût enregistré du carnet à 1 000 $ (10 bp par défaut, compté) |
| Preuve (en échantillon) | trade.xyz **+42,4 bp par marché et par week-end** avant coûts (R462) ; Lighter +45,3 bp (A), mais **−1,3 bp** sur l'échantillon C jamais vu (fév.-avr. 2026) |
| Décision | arrêt pour futilité à 15 week-ends tradés ; réussite possible à 20 ou 30 week-ends |
| Maillon faible | prix de dernière transaction (rebond acheteur-vendeur) ; l'effet peut disparaître des mois entiers (C) |

### B3. trade.xyz, version équilibrée (R530 papier)
| Champ | Valeur |
|---|---|
| Signal | rel W = W − la médiane des W du week-end (au moins 5 marchés) |
| Entrée | acheter tout marché avec rel W ≤ −50 bp, vendre tout marché avec rel W ≥ +50 bp, montants égaux de chaque côté, dimanche 19:00 → 22:00 |
| Preuve (en échantillon) | **+52,0 bp par week-end, écart-type 27,7** (A) ; +22,2 bp (B) |
| Décision | à partir du week-end du 04-12 ; futilité à 15 ; réussite à 20 (fin avril 2027) ou 30 (juillet) |
| Prévision écrite | P(réussite) 0,36, revue à 0,23 après correction des coûts |
| Taille pour toi | marge isolée par position sur xyz : avec 10 000 €, environ 1 000 $ par trade |

## C. Surcouche ML (R531, historique)
| Champ | Valeur |
|---|---|
| Idée | méta-labeling (López de Prado) : la règle de A choisit les candidats, un second modèle apprend lesquels ne paieront pas |
| Modèle | régression logistique (L2) sur 7 variables calculées au jour d'entrée, sans futur : écart 14 j, sa variation sur 14 j, volatilité de l'écart de financement, base entre les deux jambes, part de jours cotés, plateforme sans plancher |
| Validation | walk-forward trimestriel purgé, embargo de 14 jours ; test 2024-01..2026-09 (12 trimestres, environ 4 700 entrées) |
| Filtre | un candidat sous p = 0,5 est sauté, sa case reste libre |
| Décision | réussite si le gain (ML − règle figée) à 2x a un t ≥ 2,5, est positif chaque année, et que le livre ML est positif à 2x |
| Prévision écrite | P(réussite) 0,07 : une surcouche sur une règle déjà sélective rapporte rarement |
| **Résultat (26-11, lu une fois)** | **ÉCHEC.** À 2x, le ML fait −0,35 %/an face à la règle figée (t −0,97). Il ne garde que 3,2 % des candidats et perd du portage : −1,17 %/an à 1x. Il ne gagne qu'à 3x (+0,48 %/an, t 1,27), en tradant moins. Seuls 44 % des trades de la règle paient : le livre vit d'une minorité de gros gains, imprévisibles à l'entrée. **On garde la règle.** Prochaine question ML possible : prédire la sortie, pas l'entrée. (`experiments/carry_meta_v1/FINDINGS.md`) |

## D. Candidates (pas encore des pistes ; les questions sont dans `docs/reviews/open_questions.md`)
| Id | Stratégie précise | État | Pourquoi pas encore |
|---|---|---|---|
| O7d | vendre le straddle BTC à 1 jour du dimanche 08:00 UTC (Deribit) quand son prix dépasse le mouvement attendu | 2026 : trop cher de 35 à 49 bp (constat après coup) | à confirmer en 2027 hors échantillon ; queues de distribution du dimanche soir |
| Q01 | écart entre l'indice gelé de Variational et xyz pendant le week-end | enregistrement depuis le 25-11 | première lecture le 29-11, règle écrite d'avance |
| K1 | vendre le perp mondial d'une pièce délistée par Upbit/Bithumb pendant les 30 jours de liquidation | idée, P ≈ 0,2 | historique des notices à constituer ; la même famille (R267) a donné un résultat nul |
