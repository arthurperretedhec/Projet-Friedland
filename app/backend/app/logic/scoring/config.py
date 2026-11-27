"""Configuration du moteur de score : LE fichier à modifier pour changer critères, poids et seuils.

Règles de modification (vérifiées au chargement du moteur, voir engine.load_config) :
- les poids des critères graduels ACTIFS doivent faire exactement 100 ;
- le nombre de critères actifs (éliminatoires + graduels) doit rester entre
  `active_criteria_min` et `active_criteria_max` ;
- un ratio (part des points) est entre 0 et 1 ; un seuil « partiel » ne peut pas être plus strict
  que le seuil « complet » ;
- pour désactiver un critère : `"enabled": False` (et redistribuer son poids s'il est graduel).
Si une règle n'est pas respectée, le moteur refuse de se charger et le message dit pourquoi.
Après une modification : lancer les tests (`npm run verify`) et mettre à jour app/docs/scoring.md.

Les seuils ci-dessous sont des CONVENTIONS DE BON SENS proposées au groupe, pas des chiffres
sourcés.

Deux configurations :
- SCORING_CONFIG (critères v2, PAR DÉFAUT) : proposition D, codée le 2026-11-25, à valider par le
  groupe. Secteur 40, type de fonds 25, capacité à mener 15, géographie 10, spécialité 10 ; VE,
  taille et âge du fonds désactivés (pas ou trop peu de données dans la base).
- SCORING_CONFIG_V1 (critères v1, validés par Arthur le 2026-11-20 : 35 / 35 / 20 / 10) : gardée
  telle quelle pour comparer et pour les tests des règles v1 (dont le code n'est pas supprimé).
"""

# --- Listes de valeurs autorisées ----------------------------------------------------------------
# Source unique : app/logic/reference.py (partagé avec le branchement sur la vraie base). Pour
# ajouter un secteur ou un type d'opération, le modifier là-bas, pas ici.
from app.logic.reference import (  # noqa: F401  (ré-exportés pour models.py et engine.py)
    BUCKETS,
    BUYER_ROLES,
    DEAL_TYPES,
    FUND_DEAL_TYPES,
    GENERALIST_SECTOR,
    NON_PE_DEAL_TYPE,
    SECTORS,
    SOURCE_QUALITY_ORDER,
    STAKES,
)

# --- Critères v1 (2026-11-20), gardés pour comparaison et tests ----------------------------------
SCORING_CONFIG_V1 = {
    # Change cette date à chaque modification : elle est recopiée dans chaque résultat.
    "version": "2026-11-20",
    # Part des points donnée à un critère graduel quand la donnée du fonds n'est pas publiée
    # (0,5 = la moitié : règle neutre, ni punition ni récompense). Le fonds n'est jamais exclu pour
    # une donnée manquante.
    "missing_data_ratio": 0.5,
    # Nombre de critères actifs autorisé (éliminatoires + graduels).
    "active_criteria_min": 5,
    "active_criteria_max": 15,
    # Critère dont les points départagent deux fonds à égalité de score et de données manquantes.
    "tie_break_criterion": "G1",
    # Critères ÉLIMINATOIRES : un seul non rempli => fonds exclu (score 0). Pas de poids.
    "eliminatory": [
        {
            "id": "E1",
            "rule": "deal_type",
            "label": "Deal type",
            "enabled": True,
            "description": "Exclu si le type de l'opération n'est pas dans deal_types du fonds.",
        },
        {
            "id": "E2",
            "rule": "ticket_min",
            "label": "Minimum ticket",
            "enabled": True,
            "description": "Exclu si ticket < ticket_min_eur_m ; égal au minimum = accepté.",
        },
        {
            "id": "E3",
            "rule": "ticket_max",
            "label": "Maximum ticket",
            "enabled": True,
            "description": "Exclu si ticket > ticket_max_eur_m ; égal au maximum = accepté.",
        },
        {
            "id": "E4",
            "rule": "stake",
            "label": "Stake sought",
            "enabled": True,
            "description": "majority <-> majoritaire, minority <-> minoritaire, both accepte tout.",
        },
        {
            "id": "E5",
            "rule": "fund_type",
            "label": "Fund type",
            # Désactivé : toute la base est du private equity (périmètre d'architecture.md) et
            # strategies.csv n'a pas de colonne « type de fonds ». Règle non programmée : l'activer
            # demande d'ajouter la colonne et la règle dans engine.py.
            "enabled": False,
            "description": "Non utilisé (base 100 % PE).",
        },
    ],
    # Critères GRADUELS : points = poids x part obtenue (1 = complet, 0 = rien).
    "graded": [
        {
            "id": "G1",
            "rule": "sector",
            "label": "Sector",
            "enabled": True,
            "weight": 35,
            "params": {
                # Part des points pour un fonds « generalist » (accepte tout, sans expertise).
                "generalist_ratio": 0.5,
            },
            "description": "100 % si le secteur est ciblé, 50 % si fonds généraliste, sinon 0.",
        },
        {
            "id": "G2",
            "rule": "enterprise_value",
            "label": "Size fit (EV)",
            "enabled": True,
            "weight": 35,
            "params": {
                # « Proche » = VE hors fourchette mais à moins de 25 % d'une borne
                # (VE >= 0,75 x min ou VE <= 1,25 x max).
                "near_tolerance": 0.25,
                "near_ratio": 0.5,
            },
            "description": (
                "Mesure du stade de l'entreprise (hypothèse). 100 % si la VE est dans "
                "[ev_min, ev_max], 50 % si à moins de 25 % d'une borne, sinon 0."
            ),
        },
        {
            "id": "G3",
            "rule": "fund_size",
            "label": "Taille du fonds",
            "enabled": True,
            "weight": 20,
            "params": {
                # Ticket / taille du dernier fonds.
                "full_max_share": 0.10,  # <= 10 % : 100 % des points
                "partial_max_share": 0.20,  # <= 20 % : partial_ratio ; au-delà : 0
                "partial_ratio": 0.5,
            },
            "description": "100 % si ticket <= 10 % du fonds, 50 % si <= 20 %, sinon 0.",
        },
        {
            "id": "G4",
            "rule": "investment_period",
            "label": "Investment period",
            "enabled": True,
            "weight": 10,
            "params": {
                # Âge = année de la date d'analyse - last_fund_year (approximation, hypothèse).
                "full_max_age": 4,  # <= 4 ans : 100 %
                "partial_max_age": 6,  # 5 ou 6 ans : partial_ratio ; 7 ans ou plus : 0
                "partial_ratio": 0.5,
            },
            "description": "100 % si dernier fonds levé il y a <= 4 ans, 50 % si 5-6 ans, sinon 0.",
        },
    ],
}


# --- Critères v2 (PAR DÉFAUT) : poids et seuils ---------------------------------------------
SCORING_CONFIG = {
    # Change cette date à chaque modification : elle est recopiée dans chaque résultat.
    "version": "2026-11-25-v2",
    # Donnée non publiée sur un critère noté : la moitié des points (règle neutre), jamais
    # d'exclusion.
    "missing_data_ratio": 0.5,
    "active_criteria_min": 5,
    "active_criteria_max": 15,
    # Départage des ex æquo : 1. score, 2. le moins de données manquantes, 3. la meilleure qualité
    # de source (classification_basis, ordre de reference.SOURCE_QUALITY_ORDER), 4. strategy_id.
    "tie_break_criterion": None,
    "tie_break_source_quality": True,
    # Indice de confiance : données manquantes sur les 9 critères actifs (E1 à E4, G1, G5 à G8 ;
    # un ticket min ou max non publié compte). Élevé : 0 ou 1 manquante ; moyen : 2 ou 3 ;
    # faible : 4 ou plus.
    "confidence_high_max_missing": 1,
    "confidence_medium_max_missing": 3,
    # Critères ÉLIMINATOIRES : inchangés par rapport à la v1.
    "eliminatory": [
        {
            "id": "E1",
            "rule": "deal_type",
            "label": "Deal type",
            "enabled": True,
            "description": "Exclu si le type de l'opération n'est pas dans deal_types du fonds.",
        },
        {
            "id": "E2",
            "rule": "ticket_min",
            "label": "Minimum ticket",
            "enabled": True,
            "description": "Exclu si ticket < ticket_min_eur_m ; égal au minimum = accepté.",
        },
        {
            "id": "E3",
            "rule": "ticket_max",
            "label": "Maximum ticket",
            "enabled": True,
            "description": "Exclu si ticket > ticket_max_eur_m ; égal au maximum = accepté.",
        },
        {
            "id": "E4",
            "rule": "stake",
            "label": "Stake sought",
            "enabled": True,
            "description": "majority <-> majoritaire, minority <-> minoritaire, both accepte tout.",
        },
        {
            "id": "E5",
            "rule": "fund_type",
            "label": "Fund type (eliminatory)",
            # Toujours désactivé : le type de fonds est noté en v2 (G5) au lieu d'exclure.
            "enabled": False,
            "description": "Non utilisé (voir G5).",
        },
    ],
    # Critères NOTÉS : points = poids x part obtenue. Total des poids actifs = 100.
    "graded": [
        {
            "id": "G1",
            "rule": "sector",
            "label": "Sector",
            "enabled": True,
            "weight": 40,
            "params": {"generalist_ratio": 0.5},
            "description": "100 % si le secteur est ciblé, 50 % si fonds généraliste, sinon 0.",
        },
        {
            "id": "G5",
            "rule": "fund_type",
            "label": "Fund type",
            "enabled": True,
            "weight": 25,
            "params": {
                # Part des points quand le bucket attendu n'est que secondaire.
                "secondary_ratio": 0.5,
            },
            "description": (
                "100 % si le bucket principal correspond à l'opération (LBO, build-up, carve-out "
                "-> BUYOUT ; growth -> GROWTH_EQUITY), 50 % si c'est un bucket secondaire, sinon 0."
            ),
        },
        {
            "id": "G6",
            "rule": "lead_capacity",
            "label": "Lead capacity",
            "enabled": True,
            "weight": 15,
            "params": {"partial_ratio": 0.5},
            "description": (
                "Majoritaire : CONTROL_POSSIBLE 100 %, CONTROL_NOT_VERIFIED 50 %, autres 0. "
                "Minoritaire : MINORITY_CAPITAL_PARTNER 100 %, CONTROL_POSSIBLE ou "
                "CONTROL_NOT_VERIFIED 50 %, autres 0."
            ),
        },
        {
            "id": "G7",
            "rule": "geography",
            "label": "Geography",
            "enabled": True,
            "weight": 10,
            "params": {"partial_ratio": 0.5},
            "description": (
                "France 100 % ; région française ou zone large incluant la France (Europe, "
                "mondial...) 50 % ; autres zones 0."
            ),
        },
        {
            "id": "G8",
            "rule": "transaction_speciality",
            "label": "Transaction speciality",
            "enabled": True,
            "weight": 10,
            "params": {
                # Part neutre quand aucune spécialité n'est définie pour le type d'opération
                # (growth).
                "no_speciality_ratio": 0.5,
            },
            "description": (
                "100 % si le fonds affiche la spécialité de l'opération (transmission pour un LBO, "
                "buy_and_build pour un build-up, carve_out pour un carve-out), sinon 0."
            ),
        },
        # Désactivés en v2 (code gardé) : la base ne publie la VE que pour 22 stratégies sur 153
        # et ne contient ni la taille ni l'année du dernier fonds.
        {
            "id": "G2",
            "rule": "enterprise_value",
            "label": "Size fit (EV)",
            "enabled": False,
            "weight": 35,
            "params": {"near_tolerance": 0.25, "near_ratio": 0.5},
            "description": "Désactivé en v2 : VE publiée pour 22 stratégies sur 153.",
        },
        {
            "id": "G3",
            "rule": "fund_size",
            "label": "Taille du fonds",
            "enabled": False,
            "weight": 20,
            "params": {"full_max_share": 0.10, "partial_max_share": 0.20, "partial_ratio": 0.5},
            "description": "Désactivé en v2 : taille du dernier fonds absente de la base.",
        },
        {
            "id": "G4",
            "rule": "investment_period",
            "label": "Investment period",
            "enabled": False,
            "weight": 10,
            "params": {"full_max_age": 4, "partial_max_age": 6, "partial_ratio": 0.5},
            "description": "Désactivé en v2 : année du dernier fonds absente de la base.",
        },
    ],
}
