# Moteur de score (phase 2, F6)

Statut : moteur et tests écrits le 2026-11-20 sur la branche `arthur/scoring-engine` (Arthur Perret).
Règles, poids et seuils validés par Arthur le 2026-11-20 ; **à soumettre au groupe** (la liste
définitive des critères n'est pas encore validée par l'équipe). Branché sur la vraie base de Simon le
2026-11-25 (branche `arthur/connect-real-data`, voir « Branchement sur la vraie base »).

## À quoi il sert

Pour une opération (l'entreprise décrite par le banquier) et la liste des fonds de la base, le moteur
calcule pour chaque fonds un **score de compatibilité de 0 à 100**, le **détail critère par critère**
(points obtenus, points maximum, explication en français) et, le cas échéant, la **raison
d'exclusion**. Il renvoie les fonds classés du meilleur au moins bon.

- **100 % déterministe** : aucune IA, aucun hasard, aucune date du jour. Les mêmes entrées donnent
  toujours le même résultat, quel que soit l'ordre des fonds.
- **Module séparé** : `app/backend/app/logic/scoring/`. Il ne lit aucun fichier et n'appelle aucun
  réseau. La base de fonds (Simon, Alexandre), la saisie de l'opération (Constantin) et l'interface
  (Antoine) l'appellent par une seule fonction : `score_operation(operation, funds)`.
- Pas encore de route d'API : elle sera ajoutée par la partie API / interface.

| Fichier | Rôle |
|---|---|
| `app/backend/app/logic/scoring/config.py` | **le seul fichier à modifier** : critères, poids, seuils |
| `app/backend/app/logic/scoring/models.py` | formats d'entrée (fiche fonds, fiche opération) et du résultat |
| `app/backend/app/logic/scoring/engine.py` | les règles de calcul et le classement |
| `app/backend/app/logic/reference.py` | **source unique** des listes de valeurs (secteurs, types d'opération, positions) et des traductions depuis la base |
| `app/backend/app/logic/scoring/real_data.py` | branchement sur la vraie base : traduit chaque stratégie en fiche fonds, puis appelle le moteur (`score_operation_on_base`) |
| `app/backend/tests/test_scoring_*.py` | tests pytest (critères, classement, configuration, corrections après revue, vraie base) |
| `app/backend/tests/fixtures/synthetic_scoring_data.py` | 7 fonds et 3 opérations **fictifs** (tests uniquement) |

## Hypothèses (à connaître pour l'oral)

1. **Périmètre : private equity uniquement** (architecture.md). Les listes de valeurs (types
   d'opération, positions, secteurs) sont celles d'architecture.md. Pas de VC, dette, immobilier ou
   infrastructure.
2. **Le stade de l'entreprise est mesuré par sa valeur d'entreprise (VE).** La base n'a pas de
   colonne « stade » ; pour du LBO, la taille de l'entreprise (fourchette `ev_min_eur_m` –
   `ev_max_eur_m` publiée par le fonds) dit mieux le segment visé qu'un libellé « amorçage /
   croissance / mature ».
3. **La période d'investissement est approchée par l'année du dernier fonds levé**
   (`last_fund_year`). La base n'a pas la date de fin de période d'investissement ; un fonds investit
   en général pendant environ 5 ans après sa levée. Poids faible (10) car la donnée est indirecte.
4. **Pas de critère géographique** : toute la base et toutes les opérations sont en France. Limite
   connue : un fonds régional (qui n'investit que dans une région) n'est pas distingué d'un fonds
   national.
5. **Pas de critère « type de fonds »** : toute la base est du PE. Le critère existe dans la
   configuration (E5) mais il est désactivé et non programmé.
6. **Les seuils (25 %, 10 %, 20 %, 4 ans, 6 ans) sont des conventions de bon sens**, pas des chiffres
   tirés d'une source. Ils sont dans `config.py` pour être ajustés.

## Entrées

**Fiche fonds** : les colonnes de `strategies.csv` utiles au score, mêmes noms. Une cellule vide
devient `None` (« non publié »), jamais 0. Les cellules multi-valeurs « a; b » sont acceptées.

`strategy_id`, `management_company`, `strategy_name`, `ticket_min_eur_m`, `ticket_max_eur_m`,
`ev_min_eur_m`, `ev_max_eur_m`, `stake`, `deal_types`, `sectors`, `last_fund_size_eur_m`,
`last_fund_year`.

**Fiche opération** (format minimal à valider avec Constantin) : tous les champs sont obligatoires,
une fiche incomplète ou invalide est refusée avec un message.

| Champ | Contenu |
|---|---|
| `operation_id`, `company_name` | identifiant et nom |
| `deal_type` | un type d'opération de la liste (`primary_lbo`, `secondary_lbo`, `build_up`, `growth`, `carve_out`) |
| `equity_ticket_eur_m` | fonds propres recherchés auprès du fonds, en M€ |
| `enterprise_value_eur_m` | valeur d'entreprise estimée, en M€ |
| `sector` | un secteur de la liste (pas `generalist`) |
| `stake_sought` | `majority` ou `minority` |
| `analysis_date` | date de l'analyse (AAAA-MM-JJ) ; sert à l'âge du dernier fonds, pour que le calcul ne dépende jamais de la date du jour |

## Règles

### Critères éliminatoires (sans poids)

Un seul critère non rempli : le fonds est **exclu** (score 0, pas de rang). Toutes les raisons sont
listées, pas seulement la première.

| | Critère | Exclu si | Pourquoi |
|---|---|---|---|
| E1 | Type d'opération | le type de l'opération n'est pas dans `deal_types` | un fonds qui ne fait pas ce type d'opération ne regardera pas le dossier |
| E2 | Ticket minimum | ticket < `ticket_min_eur_m` (**égal = accepté**) | en dessous, le dossier est trop petit pour le fonds ; l'égalité respecte sa fourchette publiée |
| E3 | Ticket maximum | ticket > `ticket_max_eur_m` (**égal = accepté**) | au-dessus, le fonds ne peut pas suivre seul |
| E4 | Position | fonds `majority` et opération minoritaire, ou l'inverse ; `both` accepte tout | un fonds majoritaire ne prend pas de minorité, et inversement |

### Critères graduels (total 100)

Points = poids × part obtenue.

| | Critère | Poids | 100 % | 50 % | 0 | Pourquoi |
|---|---|---|---|---|---|---|
| G1 | Secteur | 35 | secteur dans `sectors` | fonds `generalist` | autre secteur | premier filtre d'un fonds ; un généraliste accepte sans l'avantage d'un spécialiste |
| G2 | Adéquation de taille (VE) | 35 | VE dans [`ev_min`, `ev_max`] (bornes incluses) | hors fourchette mais à moins de 25 % d'une borne (VE ≥ 0,75 × min ou ≤ 1,25 × max) | plus loin | mesure du stade (hypothèse 2) ; les fourchettes publiées sont indicatives |
| G3 | Taille du fonds | 20 | ticket ≤ 10 % du dernier fonds | ≤ 20 % | > 20 % | un fonds diversifie et évite de concentrer son capital sur une ligne |
| G4 | Période d'investissement | 10 | dernier fonds levé il y a ≤ 4 ans | 5 ou 6 ans | ≥ 7 ans | hypothèse 3 ; âge = année de `analysis_date` − `last_fund_year` |

Adéquation de taille au total : ticket (E2, E3, éliminatoire) + VE (G2, 35) + ticket / fonds
(G3, 20) = 55 points sur 100 ; secteur : 35.

**Une seule borne de VE publiée** (décision d'Arthur, 2026-11-20) : le calcul se fait sur la borne
connue (par exemple VE ≥ minimum pour 100 %), et la borne absente est **listée dans `missing_data`**
avec une alerte (« VE maximum non publiée, calcul sur le minimum ; à vérifier »). Le fonds compte
donc une donnée manquante au départage. Aucune borne publiée : règle « donnée manquante » ci-dessous,
et **les deux bornes absentes comptent pour une seule donnée manquante** (une seule entrée
`"ev_min_eur_m, ev_max_eur_m"` dans `missing_data`, décision d'Arthur, 2026-11-20) : c'est le
critère VE qui manque, pas deux critères. Conséquence au départage : un fonds sans aucune borne et un
fonds avec une seule borne comptent chacun une donnée manquante pour la VE.

Si le dernier fonds est daté après la date d'analyse, il est traité comme récent (100 %), avec
une alerte dans `warnings` (« année du dernier fonds postérieure à la date d'analyse ; à vérifier »),
car c'est probablement une faute de frappe ou une date d'analyse ancienne.
`last_fund_year` doit être entre 1980 et 2100 : une faute de frappe (3000) est refusée.

**Bornes exactes et nombres décimaux.** Un ordinateur calcule 0,75 × 80,4 = 60,300000000000004.
Pour qu'une valeur exactement sur un seuil reste du bon côté (bornes incluses), les comparaisons
se font avec une marge d'un milliardième (`_EPS` dans `engine.py`), sans effet sur un cas réel.

### Valeur manquante (règle explicite)

| Critère | Effet | Ce que le résultat affiche |
|---|---|---|
| éliminatoire | **pas d'exclusion** : une information non publiée ne prouve pas une incompatibilité | statut « Donnée manquante », explication « critère non vérifiable, fonds conservé ; à vérifier avant contact », et une alerte dans `warnings` |
| graduel | **50 % des points** (`missing_data_ratio`) : règle neutre, ni punition des fonds discrets ni récompense de l'absence d'information | statut « Donnée manquante », explication « la moitié des points (règle neutre) » |

Chaque champ manquant utilisé est listé dans `missing_data`.

### Score et classement

- Score = somme des points graduels, arrondie à 0,1 (points de chaque critère arrondis à 0,01),
  **au plus proche, la moitié vers le haut** (60,25 → 60,3), comme à la main. Le calcul se fait en
  décimal pour éviter les erreurs d'arrondi informatique. Le score est la somme des points **déjà
  arrondis** de chaque critère, volontairement, pour que les points affichés s'additionnent toujours
  exactement au score. Une différence avec l'arrondi du total exact n'est possible qu'avec un ratio à
  3 décimales ou plus (par exemple 0,2414) ; la configuration actuelle n'en a pas.
- Classement des fonds non exclus, dans cet ordre :
  1. score le plus haut ;
  2. en cas d'égalité, le moins de données manquantes (le score le mieux étayé passe devant) ;
  3. puis le plus de points sur le secteur (`tie_break_criterion`) ;
  4. puis `strategy_id` par ordre alphabétique (l'ordre est toujours le même).
- Fonds exclus : listés à part (`excluded`), par `strategy_id`.

## Résultat

```
operation_id, config_version
ranked:   [{rank, strategy_id, strategy_name, management_company, excluded: false, score,
            criteria: [{id, label, kind, status, status_label, points, max_points, explanation}],
            missing_data, warnings, exclusion_reasons: []}]
excluded: [{rank: null, ..., excluded: true, score: 0, exclusion_reasons: [...],
            criteria: [critères éliminatoires seulement]}]
```

`status` : `pass` / `fail` (éliminatoire), `full` / `partial` / `none` (graduel), `missing`
(donnée manquante). `status_label` en donne le libellé français. Pour un critère éliminatoire,
`points` et `max_points` valent `null`.

## Deux exemples calculés à la main (aussi dans acceptance.md, SC1 et SC2)

Opération A (fictive) : LBO primaire, ticket 15 M€, VE 60 M€, `software_it`, majoritaire,
analyse le 2026-11-20.

| | SC1 : fonds Bravo | SC2 : fonds Foxtrot |
|---|---|---|
| Fiche | primary_lbo + build_up, ticket 5–20, VE 20–100, both, generalist, 100 M€ en 2021 | primary_lbo, ticket 10–15, VE 70–150, both, industrials, 75 M€ en 2019 |
| Éliminatoires | 5 ≤ 15 ≤ 20, both : conservé | 10 ≤ 15 ≤ 15 (égal au maximum : accepté), both : conservé |
| G1 secteur (35) | généraliste : 35 × 0,5 = 17,5 | industrials : 0 |
| G2 VE (35) | 20 ≤ 60 ≤ 100 : 35 | 60 < 70 mais 0,75 × 70 = 52,5 ≤ 60 : 35 × 0,5 = 17,5 |
| G3 taille du fonds (20) | 15 / 100 = 15 % : 20 × 0,5 = 10 | 15 / 75 = 20 % exactement : 20 × 0,5 = 10 |
| G4 période (10) | 2026 − 2021 = 5 ans : 10 × 0,5 = 5 | 2026 − 2019 = 7 ans : 0 |
| **Total** | **17,5 + 35 + 10 + 5 = 67,5** | **0 + 17,5 + 10 + 0 = 27,5** |

## Modifier la configuration

Tout se fait dans `app/backend/app/logic/scoring/config.py`, sans toucher à `engine.py` :

- **changer un poids** : modifier `"weight"` ; les poids des critères graduels actifs doivent faire
  **100** ;
- **changer un seuil** : modifier la valeur dans `"params"` (par exemple `"full_max_share": 0.10`) ;
- **désactiver un critère** : `"enabled": False` (et redistribuer son poids s'il est graduel) ;
- **changer la règle des données manquantes** : `"missing_data_ratio"` (0,5 = moitié des points) ;
- **changer la version** : `"version"`, recopiée dans chaque résultat.

Contrôles automatiques au chargement (le moteur refuse de se charger et dit pourquoi) : poids = 100,
entre 5 et 15 critères actifs (`active_criteria_min` ≤ `active_criteria_max`), ratios entre 0 et 1,
seuil partiel pas plus strict que le seuil complet, paramètres attendus présents et aucun paramètre
inconnu, poids positifs sur les critères graduels, ni poids ni paramètres sur les critères
éliminatoires, pas d'identifiant en double, critère de départage actif. Une configuration passée à
`score_operation` est revérifiée de la même façon.

Ajouter un **nouveau** critère demande d'écrire sa règle dans `engine.py` (une fonction, puis
l'enregistrer dans `ELIMINATORY_RULES` ou `GRADED_RULES`) et ses tests.

Après toute modification : `npm run verify`, puis mettre à jour ce fichier et, si les exemples
changent, les cas SC1 et SC2 d'acceptance.md (recalculés à la main).

## Branchement sur la vraie base (2026-11-25)

**Source des données** : la base de Simon, `app/backend/data/` : **153 stratégies appartenant à
109 sociétés de gestion** (`funds.csv` en liste 112, dont 3 sans aucune stratégie ; une société peut
avoir jusqu'à 6 stratégies). Lue par son chargeur `app/data/investors.py` (`load_investors`).
Chaque stratégie a une `source_url` ; la trace des sources est dans `source_log.csv`. Aucune donnée
synthétique dans la base (les données fictives restent dans `tests/fixtures/`).

**Niveau de calcul** : le moteur note des **stratégies** (153). Pour afficher une ligne par
société de gestion, `best_strategy_per_management_company(data, result)` garde la stratégie la
mieux classée de chaque société (fonction `buyer_longlist` de Simon, regroupement par `fund_id`).

**Utilisation** : la base est chargée **une fois** (au démarrage de l'application,
`app.state.investor_data`, ou dans un test), puis passée au moteur :
`score_operation_on_base(operation, data)` traduit les 153 stratégies (`real_data.py`, avec les
tables de `reference.py`) et appelle le moteur ; `real_data.py` ne lit aucun fichier. Les fichiers
de Simon ne sont pas modifiés ; les tables `LEGACY_*` et `scoring_input` de son `investor_scoring.py`
ne sont plus utilisées par le moteur (à retirer ou faire pointer vers `reference.py` par Simon).

### Correspondance colonnes et critères

| Critère | Colonne(s) de la base | Format | Traduction |
|---|---|---|---|
| E1 Type d'opération | `strategies.deal_types` | ~55 libellés libres, séparés par « ; » | union de ce que couvrent les libellés (table ci-dessous) |
| E2 Ticket minimum | `equity_ticket_min_eur_m` | M€ | directe |
| E3 Ticket maximum | `equity_ticket_max_eur_m` | M€ | directe |
| E4 Position | `stake` | libellés séparés par « ; » | `majority` ; `minority`, `controlling_minority`, `significant_minority`, `lead_minority`, `co-investor`, `reference_shareholder` → minoritaire ; majoritaire + minoritaire → `both` ; `control_not_explicit` ignoré |
| G1 Secteur | `normalized_sector_codes` + `strategy_sector_summary.sector_scope` + `strategy_sectors.polarity` | 10 codes (`sectors.csv`) | voir ci-dessous |
| G2 VE | `target_ev_min_eur_m`, `target_ev_max_eur_m` | M€ | directe |
| G3 Taille du fonds | **aucune** | – | toujours donnée manquante |
| G4 Période d'investissement | **aucune** | – | toujours donnée manquante |

Toutes les colonnes de montants sont en **M€** (de 0,15 à 800 M€ dans la base : aucune valeur en €).

**Types d'opération (E1)** :
- `buyout`, `lbo`, `transmission` → LBO primaire **et** secondaire (« buyout » ne précise pas) ;
- `primary_lbo`, `mbo`, `mbi`, `obo`, `management_buyout`, `primary_buyout` → LBO primaire ;
- `growth`, `growth_capital`, `growth_equity` → growth ; `growth_buyout` → growth et LBO primaire ;
- `build_up`, `buy_and_build`, `add_on` → build-up ; `carve_out` → carve-out ;
- libellés **hors PE** (venture, mezzanine, dette senior, quasi-fonds propres, infrastructure,
  financement de projet, immobilier hôtelier, création d'entreprise...) : connus, ne couvrent rien ;
  un fonds qui n'a que ceux-là reçoit `non_pe` et est exclu de toute opération de PE ;
- libellés **vagues** (`impact`, `long_term`, `turnaround`, `family_succession`,
  `market_consolidation`, `public_to_private`...) : ignorés ; un fonds qui n'a que ceux-là a une
  liste « donnée manquante ».

Listes complètes (recopiées dans les tests, `test_scoring_real_data_guards.py`) :
- **hors PE (18)** : `venture`, `venture_growth`, `mezzanine`, `senior_debt`, `quasi_equity`,
  `hybrid_capital`, `convertible_financing`, `acquisition_financing`, `sponsorless_financing`,
  `infrastructure`, `infrastructure_equity`, `infrastructure_growth`, `growth_infrastructure`,
  `project_finance`, `greenfield`, `brownfield`, `hospitality_real_estate`, `company_creation` ;
- **vagues (20)** : `impact`, `long_term`, `evergreen`, `long_term_direct_investment`, `technology`,
  `transformation`, `special_situations`, `turnaround`, `restructuring`, `co_investment`,
  `minority_co_investment`, `flexible_capital`, `international_expansion`, `acquisition`,
  `change_of_ownership`, `family_succession`, `shareholder_reorganisation`, `public_to_private`,
  `market_consolidation`, `sponsorless`.
- `sector_scope` connus : `GENERALIST_OPEN`, `GENERALIST_PLUS_PREFERENCES`, `SECTOR_THEMES`,
  `UNKNOWN_SECTOR` (3 stratégies, secteur → donnée manquante) ; `polarity` : `INCLUDED`,
  `EXCLUDED_EXPLICIT`.

**Secteurs (G1)** : `TECH_SOFTWARE` → logiciel ; `HEALTHCARE` → santé ; `BUSINESS_SERVICES` →
services aux entreprises ; `INDUSTRIALS` → industrie ; `CONSUMER` → consommation et distribution ;
`FINANCIAL_SERVICES` → services financiers ; `ENERGY_ENV` → énergie et environnement ; `FOOD_AGRI` →
agroalimentaire **et** agriculture ; `INFRA_TRANSPORT` → transport et logistique ;
`REAL_ESTATE_HOSPITALITY` → construction et immobilier (**approximation** : l'hôtellerie n'a pas
d'équivalent dans le vocabulaire du moteur). `sector_scope` = `GENERALIST_OPEN` → fonds généraliste ;
`GENERALIST_PLUS_PREFERENCES` → secteurs préférés + généraliste. Un fonds qui **exclut** explicitement
un secteur (2 fonds) → donnée manquante, car le moteur ne sait pas exprimer une exclusion.

### Qualité des données, critère par critère (après traduction, 153 stratégies)

| Critère | Donnée manquante | Remarque |
|---|---|---|
| E1 Type d'opération | 5 | 14 fonds reconnus hors PE (`non_pe`) |
| E2 / E3 Ticket | 124 / 124 | |
| E4 Position | 57 | |
| G1 Secteur | 5 | |
| G2 VE | **131 sans aucune borne** (+ 3 avec une seule borne) | la VE manque pour 131 fonds sur 153 |
| G3 Taille du fonds | **153** | colonne absente de la base |
| G4 Période d'investissement | **153** | colonne absente de la base |

**Conséquences à connaître** :
- **G3 et G4 n'ont aucune donnée** : chaque fonds reçoit les mêmes **15 points neutres**
  (20 × 0,5 + 10 × 0,5). Ils ne départagent aucun fonds ; le classement repose sur le secteur (G1)
  et la VE (G2). Une proposition pour les remplacer est à soumettre au groupe.
- La VE manquant pour 131 fonds, la plupart reçoivent 17,5 points sur G2 : beaucoup d'ex æquo
  (par exemple 41 fonds à 67,5 pour un LBO small cap), départagés par le nombre de données
  manquantes, puis les points en secteur, puis **l'ordre alphabétique** de `strategy_id`.
- E1 est strict : un fonds qui publie `buyout` sans `build_up` est **exclu d'un build-up**. Pour
  le build-up mid cap d'exemple, **112 stratégies sont exclues au total, dont 107 au moins en
  partie par E1** (84 par E1 seul). Règle à rediscuter avec le groupe.
- Libellés « vagues » à rediscuter : `public_to_private`, `change_of_ownership`,
  `family_succession`, `shareholder_reorganisation` et `acquisition` décrivent des LBO et
  pourraient couvrir le LBO comme `transmission`. **Effet si on le faisait** : 3 stratégies
  (`str-aldebaran-transform`, `str-ext-caravelle-holding`, `str-ext-samfi-holding`), aujourd'hui
  exclues d'un LBO par E1 seul, deviendraient éligibles. À décider avec le groupe.

## Limites connues

- Les seuils sont des conventions, pas des données sourcées.
- Le stade et la période d'investissement reposent sur des approximations (hypothèses 2 et 3).
- Les fonds régionaux ne sont pas distingués (hypothèse 4).
- Sur la vraie base, G3 et G4 n'ont aucune donnée (voir ci-dessus) et la VE manque pour 131 fonds.
- La traduction des libellés de la base est un choix (validé par Arthur, 2026-11-25), pas une donnée
  sourcée ; une nouvelle valeur dans le CSV (type d'opération, position, code secteur,
  `sector_scope` ou `polarity`) fait échouer un test tant qu'elle n'est pas classée dans
  `reference.py`.
