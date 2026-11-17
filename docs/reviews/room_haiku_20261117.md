# Salle de réflexion Haiku, 17-11-2026 : l'historique suffit-il, et comment organiser ?

Claude, 17-11-2026 au soir, à la demande du propriétaire : « Lance une room et réfléchis avec eux, que des Haiku ».
- **Coût de la session :** zéro essai et aucune ligne au registre.
- **Accès des voix :** lecture seule. Aucune n'a ouvert un journal de test sur papier ni un résultat en cours.
- **Où ce texte sert :** il révise le [plan du jour](plan_20261117.md) (section 9) et le [Statut](../STATUS.md).

**Pourquoi.** Le propriétaire a objecté au plan :
> « Non ta réflexion est mauvaise je pense et trop strict on peut tout a fait utiliser les données de 2026 ou autre année
> même si elles sont passé 2027 sera certe de nouvelles courbe et autre mais comme les années précédentes [...] tu veux
> me dire que sur 2petabyte possible de data il te faudrait un vrai live paper trading pour assurer tes dires ? »

Il a aussi dit ne pas comprendre les numéros R, et demandé que les dossiers soient enfin organisés.

**Qui.** Cinq agents Haiku, chacun avec un rôle, en deux tours. Au second tour, chacun a lu le résumé des quatre autres.

## Tour 1 : les positions
1. **Statisticien.**
   - Le propriétaire a raison en principe. L'historique peut prouver, à trois conditions :
     - il n'a pas servi à choisir la règle ;
     - les coûts sont réels ;
     - les essais multiples sont corrigés.
   - Ce qui compte, c'est le nombre de périodes indépendantes non lues, pas le volume de données.
   - Mais 2021-2026 a servi à choisir les livres : 7 retenus parmi 560.
   - Avec un Sharpe de 2,4, la statistique t attendue sur 90 jours est d'environ 1,2. À effet constant, un PASS au
     premier regard n'arriverait que dans 10 à 20 % des cas.
   - Références : Bailey et López de Prado sur le surajustement des backtests, Harvey, Liu et Zhu sur un seuil t ≥ 3,
     McLean et Pontiff sur la baisse des rendements après publication (environ 58 % selon la voix).
2. **Données et exécution.**
   - Le funding de plusieurs plateformes est déjà là. Bybit n'est pas ingéré ; OKX et Bitget n'ont que quelques mois.
   - Aucun carnet d'ordres n'est archivé avant octobre 2026.
   - Propositions :
     - rejouer le portage avec Bybit ;
     - rejouer l'exécution sur 3 mois de 2026 avec les fichiers publics de Binance (5 à 15 Go, donc accord du
       propriétaire) ;
     - demander l'échantillon gratuit de Tardis.
3. **Défenseur du test en direct.**
   - Le papier ne prouve pas le rendement : il manque de puissance.
   - Il révèle autre chose :
     - les pannes ;
     - les jours manqués ;
     - les conflits d'écriture entre deux programmes ;
     - les délais.
   - Exemples cités : l'arrêt de 3,1 jours, et le double écrivain de l'audit du 10-11.
   - Propositions : garder le papier comme test de mécanique, et faire un petit test réel de 2 à 4 semaines.
4. **Organisateur.**
   - Le dépôt contient 275 dossiers d'expériences, 500 scripts et 64 documents à la racine de `docs/`.
   - On s'y perd pour trois raisons :
     - il y a trois identifiants (R, M, C) en plus des noms de dossiers ;
     - les noms de dossiers sont techniques ;
     - plusieurs portes d'entrée se contredisent.
   - Proposition : une carte en français par familles, avec un verdict en un mot, sans déplacer de fichiers.
5. **Trader.**
   - Attendre coûte environ 80 $ par mois sur 10 000 $.
   - Proposition : un pilote réel borné.
     - 200 $ par livre, soit 2 % ;
     - arrêt à 25 % de perte ;
     - mise doublée après deux mois dans la tolérance du papier.
   - Le propriétaire fait seul le KYC, crée des clés sans droit de retrait et gère sa fiscalité.

## Tour 2 : les réactions
- **Statisticien.**
  - Il garde son lot vierge, avec un seuil t ≥ 3.
  - Un pilote réel avant tout PASS contredit la règle 6, que seul le propriétaire peut changer.
  - Point nouveau : personne n'a chiffré les coûts fixes. Un livre de 200 $ à 10 % par an rapporte environ 20 $ par an,
    alors que les transferts et les retraits entre plateformes ne sont pas tarifés.
- **Données et exécution.**
  - Le pilote n'est acceptable qu'après trois contrôles :
    - un test sans les sorties « blowout » ;
    - un gain net à 2x et 3x les coûts ;
    - une procédure en cas de délistage.
  - Ni la répétition historique ni le papier ne testent l'exécution. Le premier vrai test d'exécution serait donc le
    pilote réel, et il faut le dire comme tel.
- **Défenseur du test en direct.**
  - Il faut d'abord rejouer l'exécution, puis faire le pilote.
  - Il refuse que le papier déclenche une hausse de mise.
  - Le risque opérationnel est sous-estimé : un pilote tenu par une seule personne serait d'abord dominé par les
    pannes.
  - Il faut des alertes avant toute mise réelle.
- **Organisateur.**
  - La carte doit commencer par « où on en est » : l'argent engagé et la prochaine décision, renvoyés au Statut.
  - Il demande combien de temps il faudrait pour trancher, et s'il ne vaudrait pas mieux arrêter que d'attendre
    indéfiniment.
- **Trader.**
  - Il retire « valider » : son pilote teste la plomberie, pas le rendement.
  - Au moins une jambe doit être à la taille réelle (250 à 1 000 $), sinon on ne voit ni le glissement ni les minimums
    d'ordre.

## Faits vérifiés par Claude après la salle
1. **Le « lot vierge » proposé ne l'est plus pour le portage.**
   - R391 a lu les longues traînes KuCoin, dYdX et Lighter : +2,48 %/an, PASS.
   - R392 a lu la longue traîne Gate : +0,73 %/an, PASS mais sous le rendement du cash.
   - Il reste des lectures permises sur ces échantillons (2 sur 4 pour 2020 et Gate, 3 sur 4 pour KuCoin et dYdX).
     Mais relire le même échantillon avec la même règle n'apporte rien de neuf.
   - Ces répliques à l'aveugle gagnent bien moins que les livres choisis (+6 à +16 %/an). C'est l'effet de sélection
     que décrit le statisticien.
2. **Plateformes nouvelles :**

   | Plateforme | Réponse de son API publique (une requête par plateforme, sans réessai) |
   |---|---|
   | Bybit | refuse cette machine (blocage par pays) |
   | BitMEX | refuse cette machine (blocage par pays) |
   | Bitfinex | répond ; historique des dérivés depuis au moins août 2021 sur SOL |
   | OKX | répond, mais son API ne garde que 3 mois de funding |
   | Coinbase International | redirige ; la redirection n'a pas été suivie |

3. **Carnets d'ordres historiques.**
   - Le dépôt a `data/bookDepth_1h` : la profondeur Binance par tranches de 1 à 5 % autour du prix, chaque heure, sur
     30 grandes cryptos, de janvier 2023 à décembre 2025.
   - C'est trop grossier pour le coût d'une jambe de 250 à 1 000 $ sur une petite crypto. Il n'existe aucun carnet Gate
     historique.
   - Les enregistrements fins commencent en octobre 2026.
4. **Les « 2 Po ».** Ce sont surtout des carnets d'actions et du CME, payants (note du 16-11 sur la vidéo LSE). Ils ne
   couvrent pas les plateformes crypto du portage.

## Ce sur quoi la salle s'accorde
1. **Le propriétaire a raison sur le principe.** Des données passées peuvent prouver si elles n'ont pas servi à choisir
   la règle, si les coûts sont ceux qu'on paierait, et si les essais multiples sont comptés.
2. **Le papier de 90 jours est trop faible pour prouver un rendement.** Il sert à vérifier la mécanique.
3. **Ce que l'historique ne montre pas, c'est l'exécution :**
   - les ordres réellement remplis ;
   - le funding réellement crédité ;
   - les transferts ;
   - les délistages ;
   - les pannes.

   Pour les plateformes du portage, il n'existe presque pas d'historique de carnets avant octobre 2026.
4. **Le premier vrai test d'exécution est donc un petit test réel.** Il mesure la mécanique, pas le profit.
5. **Pour l'organisation :** une carte en français par familles, sans déplacer de fichiers.

## Désaccords
- **Faire un pilote réel avant les lectures de 2027 ?**
  - Pour : le trader et le défenseur du test en direct ; la voix des données aussi, après ses contrôles.
  - Contre : le statisticien et l'organisateur, au nom de la règle 6. Seul le propriétaire peut la changer.
- **Quelle taille ?** 200 $ par livre, ou au moins une jambe à taille réelle pour voir le glissement.
- **Les coûts fixes :** les transferts et retraits peuvent dépasser le gain d'un petit livre.

## Ce que Claude en retient
- **J'étais trop strict sur un point.** J'avais fait de 90 jours de papier la seule porte vers l'argent réel.
  - Le papier ne peut pas prouver le rendement en 90 jours.
  - L'historique l'a établi autant qu'il le peut, avec plusieurs plateformes et des lectures à l'aveugle.
  - La porte utile vers un *petit* test réel est la mesure de l'exécution.
- **Je garde deux réserves.**
  - Le gain à attendre est plutôt de quelques % par an que +10 % : les répliques à l'aveugle donnent +0,7 à +2,5 %/an.
  - L'exécution et les accidents ne se voient qu'en vrai.
- **Ce qui change :** la section 9 du [plan](plan_20261117.md) et la section 5 du [Statut](../STATUS.md).
- **La décision qui revient au propriétaire :** la règle 6 d'AGENTS.md est la sienne. Deux options, rédigées dans le
  Statut :
  - la garder telle quelle ;
  - y ajouter une exception pour un pilote de mesure borné.
- **Organisation :** la [carte en français](../guides/CARTE.fr.md) range les 277 expériences en 14 familles, avec un
  verdict en un mot. Elle est générée par `scripts/carte.py` à partir de `registry/lane_families.csv`, et aucun
  dossier n'est déplacé.
