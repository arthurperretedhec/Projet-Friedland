# Moteur de score (phase 2, F6)

Statut : moteur et tests écrits le 2026-11-20 sur la branche `arthur/scoring-engine` (Arthur Perret).
Règles, poids et seuils validés par Arthur le 2026-11-20 ; **à soumettre au groupe** (la liste
définitive des critères n'est pas encore validée par l'équipe). Branché sur la vraie base de Simon le
2026-11-25 (branche `arthur/connect-real-data`, voir « Branchement sur la vraie base »).

## Critères v2 : configuration par défaut depuis le 2026-11-25

Codés sur la branche `arthur/criteria-v2` (proposition D), **à valider par le groupe**. Les critères
v1 (35 / 35 / 20 / 10, décrits plus bas dans « Règles ») restent dans le code et dans
`SCORING_CONFIG_V1` (config.py), pour comparer et pour leurs tests.

**Pourquoi** : sur la vraie base, la VE n'est publiée que pour 22 stratégies sur 153, et la taille et
l'année du dernier fonds ne le sont jamais. G2, G3 et G4 donnaient donc presque le même nombre de points
à tout le monde (42 stratégies ex æquo à 67,5 pour le LBO d'exemple, 41 avant la traduction de
`family_succession`). La v2 n'utilise que des
colonnes remplies.

### Critères éliminatoires : inchangés (E1 à E4)

### Critères notés (total 100)

| | Critère | Colonne | Remplie | Poids | 100 % | 50 % | 0 |
|---|---|---|---|---|---|---|---|
| G1 | Secteur | codes + `sector_scope` | 148 / 153 | **40** | secteur ciblé | fonds généraliste | autre secteur |
| G5 | Type de fonds | `primary_bucket`, `secondary_buckets` | 153 / 153 | **25** | bucket principal attendu | bucket attendu en secondaire | sinon |
| G6 | Capacité à mener | `buyer_role` | 153 / 153 | **15** | voir ci-dessous | voir ci-dessous | autres rôles |
| G7 | Géographie | `geography_tags` | 151 / 153 | **10** | France citée | région française ; zone large incluant la France | autres zones |
| G8 | Spécialité de transaction | `transaction_modifiers` | 134 / 153 | **10** | spécialité de l'opération affichée | growth (aucune spécialité définie) | spécialité absente |

G2 (VE), G3 (taille du fonds) et G4 (période d'investissement) sont **désactivés** (`"enabled": False`),
leur code est gardé. Une donnée manquante sur un critère noté donne toujours 50 % des points, sans
exclusion.

- **Type de fonds (G5)** : bucket attendu = `BUYOUT` pour un LBO primaire ou secondaire, un build-up ou
  un carve-out ; `GROWTH_EQUITY` pour un growth. Il ne compte pas deux fois la même information
  que E1 : E1 (`deal_types`) est une porte sans points (« accepte-t-il ce type ? »), G5 donne des points
  pour le **métier principal** du fonds.
- **Capacité à mener (G6)** : opération **majoritaire** : `CONTROL_POSSIBLE` 100 %,
  `CONTROL_NOT_VERIFIED` 50 %, autres rôles 0. Opération **minoritaire** (règle proposée) :
  `MINORITY_CAPITAL_PARTNER` 100 % (c'est son métier) ; `CONTROL_POSSIBLE` et `CONTROL_NOT_VERIFIED` 50 %
  (peuvent prendre une minorité, mais ce n'est pas leur métier principal) ; autres rôles 0 (co-investisseur
  non chef de file, prêteur, venture, actifs réels...). E4 (`stake`) reste la porte, G6 donne les points.
- **Géographie (G7)** : régions françaises (50 %) : Bretagne, France_Southeast, Grand Est, Grand Ouest,
  Hauts_de_France, Ile_de_France, Normandie, Nouvelle Aquitaine (les deux orthographes de la base,
  avec espace ou `_`), Occitanie, Pays_de_la_Loire,
  Provence_Alpes_Cote_d_Azur (la région de l'entreprise n'est pas connue). Zones larges incluant la
  France (50 %) : Europe, Continental_Europe, Eurozone, Global, International, OECD. Autres zones (0) :
  pays étrangers cités seuls (Italy, Spain, Germany, Benelux, DACH, UK, Switzerland, Belgium...) et
  autres continents (`North America` et `North_America` : les deux orthographes sont reconnues). Cas
  discutable : `Neighboring_countries` est classé « autre zone ».
- **Spécialité (G8)** : `transmission` pour un LBO primaire ou secondaire, `buy_and_build` pour un
  build-up, `carve_out` pour un carve-out ; pour un growth, aucune spécialité définie : 50 % pour
  tous (part neutre, `no_speciality_ratio`), **sans regarder la donnée du fonds** : un fonds sans
  `transaction_modifiers` n'est donc pas compté en donnée manquante pour un growth (correction de la
  relecture du 2026-11-25). Limite : un fonds qui pratique la spécialité sans
  l'afficher a 0.

### Traduction des types d'opération (changement v2)

- `family_succession` couvre désormais le LBO primaire (comme `transmission`). Effet :
  `str-aldebaran-transform` devient éligible aux LBO primaires (77,5 pour le LBO d'exemple, SC8).
  Cette traduction vaut **pour les deux configurations** (elle est dans `reference.py`, partagé) :
  `SCORING_CONFIG_V1` signifie donc « poids et critères v1 avec les traductions actuelles » ; en
  v1, Aldebaran vaut désormais 67,5 au lieu d'être exclu.
- `acquisition` **reste un libellé vague, volontairement** : il peut désigner un rachat par le fonds,
  mais aussi une acquisition faite par une société du portefeuille ou un financement d'acquisition ; il
  ne prouve pas que le fonds mène un LBO. (Le traduire en LBO ferait entrer `str-ext-caravelle-holding`
  et `str-ext-samfi-holding`.)

### Départage des ex æquo (v2)

1. le score le plus haut ;
2. le moins de données manquantes (critères actifs, éliminatoires compris) ;
3. la meilleure **qualité de source** (`classification_basis`) : `SOURCE_DESCRIPTION` >
   `INTERPRETED_DESCRIPTION` > `BROAD_MAPPING` > `HISTORICAL_DIRECTORY_LABEL` > non renseigné ;
4. `strategy_id` par ordre alphabétique.

Les points en secteur ne départagent plus (règle v1 abandonnée).

### Indice de confiance (v2)

Pour chaque stratégie classée : `criteria_known / criteria_total` = critères actifs dont la donnée
est publiée, sur les **9 critères actifs**, éliminatoires compris (E1 à E4, G1, G5 à G8 ; un ticket
minimum ou maximum non publié compte) ; `level` ; `missing_data` = la même liste que
`FundResult.missing_data` (le niveau se calcule sur sa longueur ; en v1, une borne de VE absente y
compte aussi), recopiée volontairement pour que l'indice se lise seul dans l'interface.

| Niveau | Règle (config.py) | LBO d'exemple (95 stratégies) | Build-up d'exemple (41) |
|---|---|---|---|
| élevé | 0 ou 1 donnée manquante (`confidence_high_max_missing` = 1) | 13 | 10 |
| moyen | 2 ou 3 (`confidence_medium_max_missing` = 3) | 77 | 28 |
| faible | 4 ou plus | 5 | 3 |

Décision d'Arthur (2026-11-25) : compter aussi les critères éliminatoires. Effet : un fonds dont les
deux tickets ne sont pas publiés est au mieux « moyen » (par exemple Argos Mid-Market : 100 points,
7 / 9, moyen ; il était « élevé » quand seuls les critères notés comptaient). Le départage comptait
déjà ces données manquantes (`missing_data` inclut les critères éliminatoires).

### Classement par société de gestion (démo)

`rank_management_companies(data, result)` (dans `real_data.py`) renvoie une ligne par société de
gestion, dans l'ordre de sa meilleure stratégie (départage compris). Une société dont toutes les
stratégies sont exclues n'apparaît pas. Format d'une ligne, pour l'interface (Antoine) :

```json
{
  "rank": 7,
  "fund_id": "fund-001",
  "management_company": "Abenex Capital SAS",
  "best_strategy_id": "str-abenex-industries-90",
  "best_strategy_name": "Abenex Industries 9.0",
  "score": 90.0,
  "criteria": [
    {"id": "E1", "label": "Type d'opération", "kind": "eliminatory", "status": "pass",
     "status_label": "Critère rempli", "points": null, "max_points": null,
     "explanation": "Le fonds accepte les opérations primary_lbo."},
    {"id": "G1", "label": "Secteur", "kind": "graded", "status": "full",
     "status_label": "Correspondance complète", "points": 40.0, "max_points": 40.0,
     "explanation": "Secteur industrials ciblé par le fonds."}
  ],
  "confidence": {"criteria_known": 9, "criteria_total": 9, "level": "élevé", "missing_data": []},
  "missing_data": [],
  "warnings": [],
  "other_strategies": [
    {"strategy_id": "str-abenex-smallcap-ii", "strategy_name": "Abenex Small Cap II", "rank": 49,
     "score": 70.0, "excluded": false, "exclusion_reasons": []}
  ]
}
```

(Ligne réelle d'Abenex Capital pour le LBO d'exemple, abrégée : `criteria` contient tous les
critères actifs, E1 à E4 puis G1, G5 à G8.) `status` : `pass` / `fail` (éliminatoire), `full` /
`partial` / `none` (noté), `missing`. `other_strategies.rank` est `null` pour une stratégie exclue.
Le classement complet par stratégie reste disponible (`score_operation_on_base`).

## Route d'API POST /api/score (pour l'interface, Antoine)

Le moteur est appelé par **`POST /api/score`** (fichier `app/backend/app/api/score.py`). La base et
ses 153 fiches sont chargées et traduites **une seule fois au démarrage** du backend
(`app.state.scoring_base`), pas à chaque appel. Depuis le navigateur, appeler `/api/score` sur le
même site : Next.js transmet `/api/*` au backend.

### Requête (JSON)

| Champ | Obligatoire | Valeurs |
|---|---|---|
| `deal_type` | oui | `primary_lbo`, `secondary_lbo`, `build_up`, `growth`, `carve_out` |
| `sector` | oui | `software_it`, `healthcare`, `business_services`, `industrials`, `consumer_retail`, `food_beverage`, `financial_services`, `education`, `energy_environment`, `construction_real_estate`, `transport_logistics`, `media_telecom`, `agriculture` (pas `generalist`) |
| `equity_ticket_eur_m` | oui | nombre > 0 (fonds propres recherchés, M€) |
| `stake_sought` | oui | `majority` ou `minority` |
| `enterprise_value_eur_m` | oui | nombre > 0 (M€) ; demandé par le format, mais pas noté en v2 |
| `company_name` | non | texte ; par défaut « Opération sans nom » |
| `operation_id` | non | texte ; par défaut « operation » |
| `analysis_date` | non | AAAA-MM-JJ ; par défaut la date du jour (sans effet sur le score en v2) |

Tout autre champ est refusé.

```json
POST /api/score
{
  "deal_type": "primary_lbo",
  "sector": "industrials",
  "equity_ticket_eur_m": 15,
  "stake_sought": "majority",
  "enterprise_value_eur_m": 40,
  "company_name": "PME industrielle (exemple)",
  "analysis_date": "2026-11-25"
}
```

### Réponse (200)

- `companies` : le classement par société de gestion (format « Classement par société de
  gestion » ci-dessus : rang, société, meilleure stratégie, score, détail par critère, indice de
  confiance, données manquantes, alertes, autres stratégies) ;
- `excluded` : les **stratégies** exclues, chacune avec ses raisons ;
- `counts` : nombre de stratégies (total, classées, exclues) et de sociétés classées ;
- `message` : « Aucun fonds de la base n'est compatible avec cette opération. » quand
  `companies` est vide, sinon `null`.

Réponse réelle pour la requête ci-dessus, abrégée (1 société sur 82, 2 critères sur 9, 1 exclusion
sur 58) :

```json
{
  "operation_id": "operation",
  "company_name": "PME industrielle (exemple)",
  "analysis_date": "2026-11-25",
  "config_version": "2026-11-25-v2",
  "message": null,
  "counts": {"strategies_total": 153, "strategies_ranked": 95, "strategies_excluded": 58,
             "companies_ranked": 82},
  "companies": [
    {
      "rank": 1,
      "fund_id": "fund-075",
      "management_company": "MFGI",
      "best_strategy_id": "str-ext-mfgi-holding",
      "best_strategy_name": "MFGI - Owner-Led Industrial Buyouts",
      "score": 100.0,
      "criteria": [
        {"id": "E1", "label": "Type d'opération", "kind": "eliminatory", "status": "pass",
         "status_label": "Critère rempli", "points": null, "max_points": null,
         "explanation": "Le fonds accepte les opérations primary_lbo."},
        {"id": "G1", "label": "Secteur", "kind": "graded", "status": "full",
         "status_label": "Correspondance complète", "points": 40.0, "max_points": 40.0,
         "explanation": "Secteur industrials ciblé par le fonds."}
      ],
      "confidence": {"criteria_known": 7, "criteria_total": 9, "level": "moyen",
                     "missing_data": ["ticket_min_eur_m", "ticket_max_eur_m"]},
      "missing_data": ["ticket_min_eur_m", "ticket_max_eur_m"],
      "warnings": ["Ticket minimum : donnée manquante, à vérifier avant contact.",
                   "Ticket maximum : donnée manquante, à vérifier avant contact."],
      "other_strategies": []
    }
  ],
  "excluded": [
    {"strategy_id": "str-access-smallcap-coinvest",
     "strategy_name": "Small-cap Buy-out Co-investments",
     "management_company": "Access Capital Partners Group SA",
     "exclusion_reasons": ["Position recherchée : Le fonds ne prend que des participations minoritaires ; l'opération est majoritaire."]}
  ]
}
```

### Erreur (422)

Format commun d'architecture.md, messages en français, un détail par champ fautif :

```json
{
  "error": {
    "code": "invalid_request",
    "message": "Requête invalide : sector : secteur inconnu « aerospace » ; valeurs autorisées : software_it, ... ; equity_ticket_eur_m : doit être strictement supérieur à 0",
    "details": [
      {"field": "sector", "message": "secteur inconnu « aerospace » ; valeurs autorisées : software_it, ..."},
      {"field": "equity_ticket_eur_m", "message": "doit être strictement supérieur à 0"}
    ]
  }
}
```

Autres messages : « champ obligatoire manquant », « champ inconnu », « doit être un nombre »,
« date invalide (format attendu : AAAA-MM-JJ) », « JSON invalide ».

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
| `app/backend/app/logic/scoring/config.py` | **le seul fichier à modifier** : critères, poids, seuils (v2 par défaut, v1 gardée) |
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

## Règles (critères v1, `SCORING_CONFIG_V1`)

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
- `family_succession` → LBO primaire (depuis les critères v2, 2026-11-25) ;
- libellés **vagues** (`impact`, `long_term`, `turnaround`, `acquisition`,
  `market_consolidation`, `public_to_private`...) : ignorés ; un fonds qui n'a que ceux-là a une
  liste « donnée manquante ».

Listes complètes (recopiées dans les tests, `test_scoring_real_data_guards.py`) :
- **hors PE (18)** : `venture`, `venture_growth`, `mezzanine`, `senior_debt`, `quasi_equity`,
  `hybrid_capital`, `convertible_financing`, `acquisition_financing`, `sponsorless_financing`,
  `infrastructure`, `infrastructure_equity`, `infrastructure_growth`, `growth_infrastructure`,
  `project_finance`, `greenfield`, `brownfield`, `hospitality_real_estate`, `company_creation` ;
- **vagues (19)** : `impact`, `long_term`, `evergreen`, `long_term_direct_investment`, `technology`,
  `transformation`, `special_situations`, `turnaround`, `restructuring`, `co_investment`,
  `minority_co_investment`, `flexible_capital`, `international_expansion`, `acquisition`,
  `change_of_ownership`, `shareholder_reorganisation`, `public_to_private`,
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
  (par exemple 42 stratégies à 67,5 pour un LBO small cap, 41 avant la traduction de
  `family_succession`), départagés par le nombre de données
  manquantes, puis les points en secteur, puis **l'ordre alphabétique** de `strategy_id`.
- E1 est strict : un fonds qui publie `buyout` sans `build_up` est **exclu d'un build-up**. Pour
  le build-up mid cap d'exemple, **112 stratégies sont exclues au total, dont 107 au moins en
  partie par E1** (84 par E1 seul). Règle à rediscuter avec le groupe.
- Libellés « vagues » proches du LBO : `family_succession` couvre le LBO primaire depuis les critères
  v2 (Aldebaran Transform devient éligible). Restent à rediscuter : `acquisition` (ferait entrer
  `str-ext-caravelle-holding` et `str-ext-samfi-holding`), `public_to_private`,
  `change_of_ownership` et `shareholder_reorganisation` (sans effet sur un fonds aujourd'hui exclu).

## Limites connues

- Les seuils sont des conventions, pas des données sourcées.
- Le stade et la période d'investissement reposent sur des approximations (hypothèses 2 et 3).
- Les fonds régionaux ne sont pas distingués (hypothèse 4).
- Sur la vraie base, G3 et G4 n'ont aucune donnée (voir ci-dessus) et la VE manque pour 131 fonds.
- La traduction des libellés de la base est un choix (validé par Arthur, 2026-11-25), pas une donnée
  sourcée ; une nouvelle valeur dans le CSV (type d'opération, position, code secteur,
  `sector_scope` ou `polarity`) fait échouer un test tant qu'elle n'est pas classée dans
  `reference.py`.
