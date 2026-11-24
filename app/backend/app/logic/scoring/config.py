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
Validés par Arthur le 2026-11-20 (poids 35 / 35 / 20 / 10).
"""

# --- Listes de valeurs autorisées ----------------------------------------------------------------
# Copie des listes de référence d'app/docs/architecture.md (agréées le 2026-11-17). À remplacer
# par un import de app/logic/reference.py quand ce fichier existera (slice 2 du plan), pour
# n'avoir qu'une seule source.
DEAL_TYPES = ("primary_lbo", "secondary_lbo", "build_up", "growth", "carve_out")
STAKES = ("majority", "minority", "both")
SECTORS = (
    "software_it",
    "healthcare",
    "business_services",
    "industrials",
    "consumer_retail",
    "food_beverage",
    "financial_services",
    "education",
    "energy_environment",
    "construction_real_estate",
    "transport_logistics",
    "media_telecom",
    "agriculture",
    "generalist",
)
# Valeur de `sectors` d'un fonds qui accepte tous les secteurs (ne peut pas être le secteur d'une
# opération).
GENERALIST_SECTOR = "generalist"

# --- Critères, poids et seuils -------------------------------------------------------------------
SCORING_CONFIG = {
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
            "label": "Type d'opération",
            "enabled": True,
            "description": "Exclu si le type de l'opération n'est pas dans deal_types du fonds.",
        },
        {
            "id": "E2",
            "rule": "ticket_min",
            "label": "Ticket minimum",
            "enabled": True,
            "description": "Exclu si ticket < ticket_min_eur_m ; égal au minimum = accepté.",
        },
        {
            "id": "E3",
            "rule": "ticket_max",
            "label": "Ticket maximum",
            "enabled": True,
            "description": "Exclu si ticket > ticket_max_eur_m ; égal au maximum = accepté.",
        },
        {
            "id": "E4",
            "rule": "stake",
            "label": "Position recherchée",
            "enabled": True,
            "description": "majority <-> majoritaire, minority <-> minoritaire, both accepte tout.",
        },
        {
            "id": "E5",
            "rule": "fund_type",
            "label": "Type de fonds",
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
            "label": "Secteur",
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
            "label": "Adéquation de taille (VE)",
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
            "label": "Période d'investissement",
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
