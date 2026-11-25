"""DONNÉES SYNTHÉTIQUES (FICTIVES) pour les tests du moteur de score uniquement.

Les colonnes des critères v2 (type de fonds, rôle, géographie, spécialité, qualité de source)
ont été ajoutées le 2026-11-25 ; elles ne changent aucun résultat des critères v1.

Aucun de ces fonds ni aucune de ces opérations n'existe : noms, montants et années sont inventés
pour tester les règles (cas limites, données manquantes, exclusions). Ne jamais les utiliser comme
données réelles ni les copier dans app/backend/data/.
"""

from __future__ import annotations

from typing import Any

from app.logic.scoring import Fund, Operation

SYNTHETIC_MARKER = "SYNTHETIC"

# --- Opérations fictives -------------------------------------------------------------------------

OPERATION_A = {  # LBO primaire, logiciel, majoritaire : sert aux deux cas calculés à la main
    "operation_id": "SYN-OP-A",
    "company_name": "Logiciel Fictif SAS (SYNTHETIC)",
    "deal_type": "primary_lbo",
    "equity_ticket_eur_m": 15,
    "enterprise_value_eur_m": 60,
    "sector": "software_it",
    "stake_sought": "majority",
    "analysis_date": "2026-11-20",
}
OPERATION_B = {  # build-up minoritaire, santé
    "operation_id": "SYN-OP-B",
    "company_name": "Santé Fictive SA (SYNTHETIC)",
    "deal_type": "build_up",
    "equity_ticket_eur_m": 40,
    "enterprise_value_eur_m": 250,
    "sector": "healthcare",
    "stake_sought": "minority",
    "analysis_date": "2026-11-20",
}
OPERATION_C = {  # capital-développement minoritaire, petit ticket : aucun fonds fictif compatible
    "operation_id": "SYN-OP-C",
    "company_name": "Commerce Fictif SARL (SYNTHETIC)",
    "deal_type": "growth",
    "equity_ticket_eur_m": 5,
    "enterprise_value_eur_m": 30,
    "sector": "consumer_retail",
    "stake_sought": "minority",
    "analysis_date": "2026-11-20",
}

# --- Fonds fictifs (mêmes noms de colonnes que strategies.csv) -----------------------------------

FUNDS: list[dict[str, Any]] = [
    {  # compatible en tout avec l'opération A : 100 / 100
        "strategy_id": "syn-alpha",
        "management_company": "Alpha Gestion Fictive (SYNTHETIC)",
        "strategy_name": "Fonds Fictif Alpha",
        "ticket_min_eur_m": 5,
        "ticket_max_eur_m": 20,
        "ev_min_eur_m": 20,
        "ev_max_eur_m": 100,
        "stake": "majority",
        "deal_types": ["primary_lbo", "secondary_lbo", "build_up"],
        "sectors": ["software_it", "business_services"],
        "last_fund_size_eur_m": 200,
        "last_fund_year": 2023,
        # Colonnes des critères v2 (2026-11-25), ignorées par les critères v1.
        "primary_bucket": "BUYOUT",
        "secondary_buckets": ["GROWTH_EQUITY"],
        "buyer_role": "CONTROL_POSSIBLE",
        "geography_tags": ["France"],
        "transaction_modifiers": ["transmission"],
        "classification_basis": "SOURCE_DESCRIPTION",
    },
    {  # cas calculé à la main n° 1 (opération A) : 67,5 / 100
        "strategy_id": "syn-bravo",
        "management_company": "Bravo Partners Fictif (SYNTHETIC)",
        "strategy_name": "Fonds Fictif Bravo",
        "ticket_min_eur_m": 5,
        "ticket_max_eur_m": 20,
        "ev_min_eur_m": 20,
        "ev_max_eur_m": 100,
        "stake": "both",
        "deal_types": ["primary_lbo", "build_up"],
        "sectors": ["generalist"],
        "last_fund_size_eur_m": 100,
        "last_fund_year": 2021,
        # Colonnes des critères v2 (2026-11-25), ignorées par les critères v1.
        "primary_bucket": "GROWTH_EQUITY",
        "secondary_buckets": ["BUYOUT"],
        "buyer_role": "CONTROL_NOT_VERIFIED",
        "geography_tags": ["Europe"],
        "transaction_modifiers": ["thematic_sector_focus"],
        "classification_basis": "INTERPRETED_DESCRIPTION",
    },
    {  # exclu de l'opération A pour trois raisons ; 100 / 100 pour l'opération B
        "strategy_id": "syn-charlie",
        "management_company": "Charlie Capital Fictif (SYNTHETIC)",
        "strategy_name": "Fonds Fictif Charlie",
        "ticket_min_eur_m": 20,
        "ticket_max_eur_m": 60,
        "ev_min_eur_m": 100,
        "ev_max_eur_m": 400,
        "stake": "minority",
        "deal_types": ["build_up", "growth"],
        "sectors": ["healthcare"],
        "last_fund_size_eur_m": 500,
        "last_fund_year": 2024,
        # Colonnes des critères v2 (2026-11-25), ignorées par les critères v1.
        "primary_bucket": "GROWTH_EQUITY",
        "secondary_buckets": None,
        "buyer_role": "MINORITY_CAPITAL_PARTNER",
        "geography_tags": ["France"],
        "transaction_modifiers": ["buy_and_build"],
        "classification_basis": "SOURCE_DESCRIPTION",
    },
    {  # données manquantes : ticket minimum, fourchette de VE et taille du fonds non publiés
        "strategy_id": "syn-delta",
        "management_company": "Delta Investissement Fictif (SYNTHETIC)",
        "strategy_name": "Fonds Fictif Delta",
        "ticket_min_eur_m": None,
        "ticket_max_eur_m": 30,
        "ev_min_eur_m": None,
        "ev_max_eur_m": None,
        "stake": "majority",
        "deal_types": ["primary_lbo"],
        "sectors": ["software_it"],
        "last_fund_size_eur_m": None,
        "last_fund_year": 2020,
        # Colonnes des critères v2 (2026-11-25), ignorées par les critères v1.
        "primary_bucket": "BUYOUT",
        "secondary_buckets": None,
        "buyer_role": "CONTROL_POSSIBLE",
        "geography_tags": None,
        "transaction_modifiers": None,
        "classification_basis": "BROAD_MAPPING",
    },
    {  # n'accepte que le LBO secondaire : exclu de l'opération A
        "strategy_id": "syn-echo",
        "management_company": "Echo Equity Fictif (SYNTHETIC)",
        "strategy_name": "Fonds Fictif Echo",
        "ticket_min_eur_m": 5,
        "ticket_max_eur_m": 20,
        "ev_min_eur_m": 20,
        "ev_max_eur_m": 100,
        "stake": "majority",
        "deal_types": ["secondary_lbo"],
        "sectors": ["software_it"],
        "last_fund_size_eur_m": 200,
        "last_fund_year": 2023,
        # Colonnes des critères v2 (2026-11-25), ignorées par les critères v1.
        "primary_bucket": "BUYOUT",
        "secondary_buckets": None,
        "buyer_role": "CONTROL_POSSIBLE",
        "geography_tags": ["France"],
        "transaction_modifiers": ["transmission"],
        "classification_basis": "SOURCE_DESCRIPTION",
    },
    {  # cas calculé à la main n° 2 (opération A) : 27,5 / 100 ; ticket = maximum, part = 20 %
        "strategy_id": "syn-foxtrot",
        "management_company": "Foxtrot Gestion Fictive (SYNTHETIC)",
        "strategy_name": "Fonds Fictif Foxtrot",
        "ticket_min_eur_m": 10,
        "ticket_max_eur_m": 15,
        "ev_min_eur_m": 70,
        "ev_max_eur_m": 150,
        "stake": "both",
        "deal_types": ["primary_lbo"],
        "sectors": ["industrials"],
        "last_fund_size_eur_m": 75,
        "last_fund_year": 2019,
        # Colonnes des critères v2 (2026-11-25), ignorées par les critères v1.
        "primary_bucket": "SPECIAL_SITUATIONS",
        "secondary_buckets": None,
        "buyer_role": "CONTROL_NOT_VERIFIED",
        "geography_tags": ["Nouvelle_Aquitaine"],
        "transaction_modifiers": ["carve_out"],
        "classification_basis": "INTERPRETED_DESCRIPTION",
    },
    {  # ticket = minimum, part = 10 %, fonds de 4 ans, VE trop loin : 65 / 100 pour l'opération A
        "strategy_id": "syn-golf",
        "management_company": "Golf Private Equity Fictif (SYNTHETIC)",
        "strategy_name": "Fonds Fictif Golf",
        "ticket_min_eur_m": 15,
        "ticket_max_eur_m": 50,
        "ev_min_eur_m": 10,
        "ev_max_eur_m": 40,
        "stake": "majority",
        "deal_types": ["primary_lbo"],
        "sectors": ["software_it"],
        "last_fund_size_eur_m": 150,
        "last_fund_year": 2022,
        # Colonnes des critères v2 (2026-11-25), ignorées par les critères v1.
        "primary_bucket": "BUYOUT",
        "secondary_buckets": None,
        "buyer_role": "CONTROL_POSSIBLE",
        "geography_tags": ["Sub_Saharan_Africa"],
        "transaction_modifiers": ["transmission", "buy_and_build"],
        "classification_basis": "HISTORICAL_DIRECTORY_LABEL",
    },
]


def funds() -> list[Fund]:
    return [Fund.model_validate(row) for row in FUNDS]


def fund(strategy_id: str) -> Fund:
    return next(f for f in funds() if f.strategy_id == strategy_id)


def operation(raw: dict[str, Any] = OPERATION_A, **changes: Any) -> Operation:
    return Operation.model_validate({**raw, **changes})


def compatible_fund(**changes: Any) -> Fund:
    """Le fonds Alpha (compatible en tout avec l'opération A), avec quelques champs modifiés."""
    return Fund.model_validate({**FUNDS[0], **changes})
