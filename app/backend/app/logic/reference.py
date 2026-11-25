"""Listes de valeurs de référence et traductions depuis la base de fonds : SOURCE UNIQUE.

Utilisé par le moteur de score (scoring/config.py, scoring/models.py) et par le branchement sur la
vraie base (scoring/real_data.py). Ne pas recopier ces listes ailleurs : les importer d'ici.

1. Vocabulaire du moteur (listes d'app/docs/architecture.md, agréées le 2026-11-17).
2. Traductions depuis les valeurs de la base de Simon (app/backend/data/strategies.csv,
   strategy_sector_summary.csv), validées par Arthur le 2026-11-25. Détails : app/docs/scoring.md.
"""

from __future__ import annotations

# --- 1. Vocabulaire du moteur ----------------------------------------------------------------

DEAL_TYPES = ("primary_lbo", "secondary_lbo", "build_up", "growth", "carve_out")
# Valeur réservée aux fonds de la base : le fonds a publié ses types d'opération, mais aucun n'est
# du private equity (venture, dette, infrastructure...). Jamais utilisée comme type d'opération.
NON_PE_DEAL_TYPE = "non_pe"
FUND_DEAL_TYPES = (*DEAL_TYPES, NON_PE_DEAL_TYPE)

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
# Valeur de `sectors` d'un fonds qui accepte tous les secteurs (jamais le secteur d'une opération).
GENERALIST_SECTOR = "generalist"

# --- 2. Traductions depuis la base -----------------------------------------------------------

# Types d'opération : libellé de la base -> types du moteur couverts. Un fonds accepte l'union de
# ce que couvrent ses libellés.
DATA_DEAL_TYPE_COVERAGE: dict[str, tuple[str, ...]] = {
    # « buyout » ne dit pas si le LBO est primaire ou secondaire : il couvre les deux.
    "buyout": ("primary_lbo", "secondary_lbo"),
    "lbo": ("primary_lbo", "secondary_lbo"),
    "transmission": ("primary_lbo", "secondary_lbo"),
    "primary_lbo": ("primary_lbo",),
    "mbo": ("primary_lbo",),
    "mbi": ("primary_lbo",),
    "obo": ("primary_lbo",),
    "management_buyout": ("primary_lbo",),
    # Décision du 2026-11-25 (critères v2) : la succession familiale est une transmission.
    "family_succession": ("primary_lbo",),
    "primary_buyout": ("primary_lbo",),
    "growth": ("growth",),
    "growth_capital": ("growth",),
    "growth_equity": ("growth",),
    "growth_buyout": ("growth", "primary_lbo"),
    "build_up": ("build_up",),
    "buy_and_build": ("build_up",),
    "add_on": ("build_up",),
    "carve_out": ("carve_out",),
}
# Libellés hors private equity : connus, mais ne couvrent aucun type du moteur. Un fonds qui n'a
# que ceux-là est exclu d'une opération de PE (critère E1).
DATA_NON_PE_DEAL_TAGS = frozenset(
    {
        "venture",
        "venture_growth",
        "mezzanine",
        "senior_debt",
        "quasi_equity",
        "hybrid_capital",
        "convertible_financing",
        "acquisition_financing",
        "sponsorless_financing",
        "infrastructure",
        "infrastructure_equity",
        "infrastructure_growth",
        "growth_infrastructure",
        "project_finance",
        "greenfield",
        "brownfield",
        "hospitality_real_estate",
        "company_creation",
    }
)
# Libellés trop vagues pour dire quel type d'opération le fonds fait : ignorés. Un fonds qui n'a
# que ceux-là a une liste « donnée manquante » (critère non vérifiable, fonds conservé).
# `acquisition` reste ici volontairement (décision du 2026-11-25) : « acquisition » peut désigner un
# rachat par le fonds, mais aussi une acquisition par une société du portefeuille ou un financement
# d'acquisition ; il ne prouve pas que le fonds mène un LBO.
# `family_succession` couvre désormais le LBO primaire (voir DATA_DEAL_TYPE_COVERAGE) : effet,
# str-aldebaran-transform devient éligible aux LBO primaires. Restent à reposer au groupe :
# public_to_private, change_of_ownership et shareholder_reorganisation (sans effet sur un fonds
# aujourd'hui exclu) ; acquisition ferait entrer str-ext-caravelle-holding et str-ext-samfi-holding.
DATA_VAGUE_DEAL_TAGS = frozenset(
    {
        "impact",
        "long_term",
        "evergreen",
        "long_term_direct_investment",
        "technology",
        "transformation",
        "special_situations",
        "turnaround",
        "restructuring",
        "co_investment",
        "minority_co_investment",
        "flexible_capital",
        "international_expansion",
        "acquisition",
        "change_of_ownership",
        "shareholder_reorganisation",
        "public_to_private",
        "market_consolidation",
        "sponsorless",
    }
)

# Secteurs : code de la base (sectors.csv) -> secteurs du moteur.
DATA_SECTORS: dict[str, tuple[str, ...]] = {
    "TECH_SOFTWARE": ("software_it",),
    "HEALTHCARE": ("healthcare",),
    "BUSINESS_SERVICES": ("business_services",),
    "INDUSTRIALS": ("industrials",),
    "CONSUMER": ("consumer_retail",),
    "FINANCIAL_SERVICES": ("financial_services",),
    "ENERGY_ENV": ("energy_environment",),
    "FOOD_AGRI": ("food_beverage", "agriculture"),
    "INFRA_TRANSPORT": ("transport_logistics",),
    # APPROXIMATION : l'hôtellerie n'a pas d'équivalent dans le vocabulaire du moteur.
    "REAL_ESTATE_HOSPITALITY": ("construction_real_estate",),
}
# `sector_scope` (strategy_sector_summary.csv) qui fait d'un fonds un généraliste.
DATA_GENERALIST_OPEN = "GENERALIST_OPEN"
DATA_GENERALIST_PLUS_PREFERENCES = "GENERALIST_PLUS_PREFERENCES"
# Toutes les valeurs connues de `sector_scope` : une nouvelle valeur fait échouer un test.
DATA_KNOWN_SECTOR_SCOPES = frozenset(
    {DATA_GENERALIST_OPEN, DATA_GENERALIST_PLUS_PREFERENCES, "SECTOR_THEMES", "UNKNOWN_SECTOR"}
)
# `polarity` (strategy_sectors.csv) : secteur inclus ou explicitement exclu par le fonds.
DATA_EXCLUDED_POLARITY = "EXCLUDED_EXPLICIT"
DATA_KNOWN_POLARITIES = frozenset({"INCLUDED", DATA_EXCLUDED_POLARITY})

# Positions : libellé de la base -> position du moteur ; None = ignoré (trop vague).
DATA_STAKES: dict[str, str | None] = {
    "majority": "majority",
    "minority": "minority",
    "controlling_minority": "minority",
    "significant_minority": "minority",
    "lead_minority": "minority",
    "co-investor": "minority",
    "reference_shareholder": "minority",
    "control_not_explicit": None,
}

# --- 3. Critères v2 (proposition D, codée le 2026-11-25) ---------------------------------------

# Types de fonds (buckets.csv) et famille attendue selon le type d'opération (critère « Type de
# fonds »).
BUCKETS = (
    "BUYOUT",
    "GROWTH_EQUITY",
    "VENTURE_CAPITAL",
    "SPECIAL_SITUATIONS",
    "REAL_ASSETS",
    "DEBT_HYBRID",
    "CO_INVESTMENT",
    "PERMANENT_CAPITAL",
)
OPERATION_BUCKET: dict[str, str] = {
    "primary_lbo": "BUYOUT",
    "secondary_lbo": "BUYOUT",
    "build_up": "BUYOUT",
    "carve_out": "BUYOUT",
    "growth": "GROWTH_EQUITY",
}

# Rôles d'acquéreur (strategies.buyer_role) et capacité à mener l'opération, selon la position
# recherchée : "full" = 100 %, "partial" = part `partial_ratio` de config.py, absent = 0.
BUYER_ROLES = (
    "CONTROL_POSSIBLE",
    "CONTROL_NOT_VERIFIED",
    "MINORITY_CAPITAL_PARTNER",
    "SPECIALIST_REAL_ASSET_BUYER",
    "VENTURE_INVESTOR",
    "LENDER_OR_HYBRID_FINANCIER",
    "CO_INVESTOR_NOT_LEAD",
    "HISTORICAL_NOT_ACTIVE_CONFIRMED",
    "ADD_ON_OR_PLATFORM_ONLY",
)
LEAD_CAPACITY: dict[str, dict[str, str]] = {
    "majority": {"CONTROL_POSSIBLE": "full", "CONTROL_NOT_VERIFIED": "partial"},
    # Opération minoritaire : le partenaire minoritaire est le métier exact ; un fonds de contrôle
    # peut aussi prendre une minorité, mais ce n'est pas son métier principal.
    "minority": {
        "MINORITY_CAPITAL_PARTNER": "full",
        "CONTROL_POSSIBLE": "partial",
        "CONTROL_NOT_VERIFIED": "partial",
    },
}

# Géographie (strategies.geography_tags) : France = 100 % ; région française ou zone large qui
# inclut la France = part `partial_ratio` ; autres zones (pays étrangers seuls, autres
# continents) = 0.
GEO_FRANCE = "France"
GEO_FRENCH_REGIONS = frozenset(
    {
        "Bretagne",
        "France_Southeast",
        "Grand Est",
        "Grand Ouest",
        "Hauts_de_France",
        "Ile_de_France",
        "Normandie",
        "Nouvelle Aquitaine",
        "Nouvelle_Aquitaine",
        "Occitanie",
        "Pays_de_la_Loire",
        "Provence_Alpes_Cote_d_Azur",
    }
)
GEO_WIDE_INCLUDING_FRANCE = frozenset(
    {"Europe", "Continental_Europe", "Eurozone", "Global", "International", "OECD"}
)
GEO_OTHER = frozenset(
    {
        "Africa",
        "Asia",
        "Belgium",
        "Benelux",
        "DACH",
        "Germany",
        "Italy",
        "Latin_America",
        "Middle_East",
        "Neighboring_countries",
        "North America",
        "North_America",
        "North_Africa",
        "Spain",
        "Sub_Saharan_Africa",
        "Switzerland",
        "UK",
        "USA",
    }
)

# Spécialité de transaction (strategies.transaction_modifiers) attendue selon l'opération.
# Pas de spécialité définie pour le growth : part neutre `no_speciality_ratio`.
OPERATION_MODIFIER: dict[str, str] = {
    "primary_lbo": "transmission",
    "secondary_lbo": "transmission",
    "build_up": "buy_and_build",
    "carve_out": "carve_out",
}

# Qualité de la source (strategies.classification_basis), de la meilleure à la moins bonne :
# sert au départage des ex æquo. Valeur absente = après la dernière.
SOURCE_QUALITY_ORDER = (
    "SOURCE_DESCRIPTION",
    "INTERPRETED_DESCRIPTION",
    "BROAD_MAPPING",
    "HISTORICAL_DIRECTORY_LABEL",
)
