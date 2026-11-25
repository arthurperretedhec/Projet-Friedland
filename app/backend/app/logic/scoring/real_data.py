"""Branchement du moteur de score sur la vraie base de fonds (app/backend/data/, chargeur de Simon).

Traduit chaque stratégie de la base en fiche `Fund` avec les tables de app/logic/reference.py
(source unique), puis appelle le moteur. Fonctions pures : la base est chargée UNE fois ailleurs
(au démarrage de l'application, `app.state.investor_data`, ou dans un test) par le chargeur de
Simon `app.data.investors.load_investors`, puis passée ici. Ce module ne lit aucun fichier
(partie « Logic » d'architecture.md). Aucune règle de score ici : elles restent dans engine.py.

Règles de traduction (validées par Arthur le 2026-11-25, détail dans app/docs/scoring.md) :
- types d'opération : union de ce que couvrent les libellés ; libellés hors PE -> `non_pe` ;
  libellés vagues ignorés ; rien de connu -> donnée manquante ;
- secteurs : codes traduits ; généraliste selon `sector_scope` ; exclusion explicite -> donnée
  manquante (le moteur ne sait pas exprimer une exclusion) ;
- position : majoritaire + minoritaire -> `both` ; libellés vagues ignorés ;
- taille et année du dernier fonds : absentes de la base -> donnée manquante (G3, G4).
"""

from __future__ import annotations

from app.data.investors import InvestorData, tokens
from app.logic.investor_scoring import buyer_longlist
from app.logic.reference import (
    DATA_DEAL_TYPE_COVERAGE,
    DATA_EXCLUDED_POLARITY,
    DATA_GENERALIST_OPEN,
    DATA_GENERALIST_PLUS_PREFERENCES,
    DATA_KNOWN_POLARITIES,
    DATA_KNOWN_SECTOR_SCOPES,
    DATA_NON_PE_DEAL_TAGS,
    DATA_SECTORS,
    DATA_STAKES,
    DATA_VAGUE_DEAL_TAGS,
    DEAL_TYPES,
    GENERALIST_SECTOR,
    NON_PE_DEAL_TYPE,
)

from .engine import score_operation
from .models import Fund, FundResult, Operation, ScoringConfig, ScoringResult


def deal_types_from_tags(tags: tuple[str, ...]) -> list[str] | None:
    """Libellés de la base -> types du moteur (None = donnée manquante)."""
    covered = {t for tag in tags for t in DATA_DEAL_TYPE_COVERAGE.get(tag, ())}
    if covered:
        return [t for t in DEAL_TYPES if t in covered]  # ordre fixe : résultat déterministe
    if any(tag in DATA_NON_PE_DEAL_TAGS for tag in tags):
        return [NON_PE_DEAL_TYPE]
    return None  # aucun libellé, ou seulement des libellés vagues


def stake_from_tags(tags: tuple[str, ...]) -> str | None:
    stakes = {DATA_STAKES[tag] for tag in tags if DATA_STAKES.get(tag)}
    if stakes == {"majority", "minority"}:
        return "both"
    return next(iter(stakes), None)


def sectors_for(data: InvestorData, strategy_id: str) -> list[str] | None:
    if any(
        row["polarity"] == DATA_EXCLUDED_POLARITY
        for row in data.strategy_sectors.get(strategy_id, ())
    ):
        return None
    scope = data.sector_summary.get(strategy_id, {}).get("sector_scope")
    if scope == DATA_GENERALIST_OPEN:
        return [GENERALIST_SECTOR]
    codes = tokens(data.strategies[strategy_id]["normalized_sector_codes"])
    if not codes or any(code not in DATA_SECTORS for code in codes):
        return None
    sectors = list(dict.fromkeys(s for code in codes for s in DATA_SECTORS[code]))
    if scope == DATA_GENERALIST_PLUS_PREFERENCES:
        sectors.append(GENERALIST_SECTOR)
    return sectors


def fund_from_strategy(data: InvestorData, strategy_id: str) -> Fund:
    row = data.strategies[strategy_id]
    return Fund.model_validate(
        {
            "strategy_id": strategy_id,
            "management_company": row["management_company"],
            "strategy_name": row["strategy_name"],
            "ticket_min_eur_m": row["equity_ticket_min_eur_m"],
            "ticket_max_eur_m": row["equity_ticket_max_eur_m"],
            "ev_min_eur_m": row["target_ev_min_eur_m"],
            "ev_max_eur_m": row["target_ev_max_eur_m"],
            "stake": stake_from_tags(tokens(row["stake"])),
            "deal_types": deal_types_from_tags(tokens(row["deal_types"])),
            "sectors": sectors_for(data, strategy_id),
            # Absents de la base actuelle (153 / 153) : donnée manquante, 50 % des points.
            "last_fund_size_eur_m": None,
            "last_fund_year": None,
        }
    )


def funds_from_base(data: InvestorData) -> list[Fund]:
    return [fund_from_strategy(data, strategy_id) for strategy_id in data.strategies]


def unclassified_values(data: InvestorData) -> dict[str, set[str]]:
    """Valeurs de la base absentes des tables de reference.py (doit rester vide)."""
    known_deals = DATA_DEAL_TYPE_COVERAGE.keys() | DATA_NON_PE_DEAL_TAGS | DATA_VAGUE_DEAL_TAGS
    found: dict[str, set[str]] = {"deal_types": set(), "stake": set(), "sectors": set()}
    for row in data.strategies.values():
        found["deal_types"] |= set(tokens(row["deal_types"])) - known_deals
        found["stake"] |= set(tokens(row["stake"])) - DATA_STAKES.keys()
        found["sectors"] |= set(tokens(row["normalized_sector_codes"])) - DATA_SECTORS.keys()
    return found


def unclassified_sector_metadata(data: InvestorData) -> dict[str, set[str]]:
    """Valeurs de `sector_scope` et `polarity` inconnues de reference.py (doit rester vide)."""
    found: dict[str, set[str]] = {"sector_scope": set(), "polarity": set()}
    for summary in data.sector_summary.values():
        if summary["sector_scope"] not in DATA_KNOWN_SECTOR_SCOPES:
            found["sector_scope"].add(summary["sector_scope"])
    for rows in data.strategy_sectors.values():
        found["polarity"] |= {r["polarity"] for r in rows} - DATA_KNOWN_POLARITIES
    return found


def score_operation_on_base(
    operation: Operation,
    data: InvestorData,
    config: ScoringConfig | None = None,
) -> ScoringResult:
    """Score et classe toutes les stratégies d'une base déjà chargée pour une opération."""
    return score_operation(operation, funds_from_base(data), config)


def best_strategy_per_management_company(
    data: InvestorData, result: ScoringResult
) -> list[FundResult]:
    """Une ligne par société de gestion : sa stratégie la mieux classée (buyer_longlist de Simon).

    Le regroupement se fait par `fund_id` ; dans la base actuelle, un `fund_id` correspond à une
    seule société de gestion (et inversement).
    """
    return buyer_longlist(data, result.ranked)
