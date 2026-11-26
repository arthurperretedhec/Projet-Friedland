"""Route POST /api/score : classement des sociétés de gestion pour une opération.

Rôle de la route (architecture.md, partie « API ») : valider la requête, appeler la logique
(moteur de score), renvoyer une réponse typée. Aucune règle de score ici.
La base est chargée et traduite une seule fois au démarrage (`build_scoring_base`, appelé dans
app/main.py) ; chaque appel réutilise `app.state.scoring_base`.
Documentation pour l'interface : app/docs/scoring.md, « Route d'API POST /api/score ».
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from types import MappingProxyType

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.data.investors import InvestorData
from app.data.portfolio_extended import Holding, latest_in_france, load_portfolio_extended
from app.logic.reference import DEAL_TYPES, GENERALIST_SECTOR, SECTORS
from app.logic.scoring import Fund, Operation, score_operation
from app.logic.scoring.real_data import CompanyResult, funds_from_base, rank_management_companies

router = APIRouter(prefix="/api")

OPERATION_SECTORS = tuple(s for s in SECTORS if s != GENERALIST_SECTOR)
STAKES_SOUGHT = ("majority", "minority")


@dataclass(frozen=True)
class ScoringBase:
    """La base de fonds et ses 153 fiches déjà traduites pour le moteur (chargées une fois)."""

    data: InvestorData
    funds: list[Fund]
    # Participations collectées sur les sites (portfolio_extended.csv), par fund_id ;
    # affichage seul, jamais utilisées par le moteur de score.
    holdings: Mapping[str, tuple[Holding, ...]] = field(
        default_factory=lambda: MappingProxyType({})
    )


def build_scoring_base(
    data: InvestorData, holdings: Mapping[str, tuple[Holding, ...]] | None = None
) -> ScoringBase:
    return ScoringBase(
        data=data,
        funds=funds_from_base(data),
        holdings=load_portfolio_extended() if holdings is None else holdings,
    )


def _allowed(value: str, allowed: tuple[str, ...], what: str) -> str:
    """`what` : début de phrase accordé, par exemple « position inconnue »."""
    if value not in allowed:
        raise ValueError(f"{what} « {value} » ; valeurs autorisées : {', '.join(allowed)}")
    return value


class ScoreRequest(BaseModel):
    """L'opération décrite par le banquier."""

    model_config = ConfigDict(extra="forbid")

    deal_type: str = Field(description="Type d'opération : " + ", ".join(DEAL_TYPES))
    sector: str = Field(description="Secteur de l'entreprise : " + ", ".join(OPERATION_SECTORS))
    equity_ticket_eur_m: float = Field(gt=0, description="Fonds propres recherchés, en M€")
    stake_sought: str = Field(description="Position recherchée : majority ou minority")
    enterprise_value_eur_m: float = Field(gt=0, description="Valeur d'entreprise estimée, en M€")
    company_name: str | None = Field(default=None, description="Nom de l'entreprise (facultatif)")
    operation_id: str | None = Field(default=None, description="Identifiant (facultatif)")
    analysis_date: date | None = Field(
        default=None, description="Date de l'analyse (facultatif ; par défaut aujourd'hui)"
    )

    @field_validator("deal_type")
    @classmethod
    def _deal_type(cls, value: str) -> str:
        return _allowed(value, DEAL_TYPES, "type d'opération inconnu")

    @field_validator("sector")
    @classmethod
    def _sector(cls, value: str) -> str:
        return _allowed(value, OPERATION_SECTORS, "secteur inconnu")

    @field_validator("stake_sought")
    @classmethod
    def _stake(cls, value: str) -> str:
        return _allowed(value, STAKES_SOUGHT, "position inconnue")


class ExcludedStrategy(BaseModel):
    strategy_id: str
    fund_id: str
    strategy_name: str | None
    management_company: str | None
    exclusion_reasons: list[str]


class Investment(BaseModel):
    """Une participation pour la colonne « Latest investments in France » du bandeau."""

    company_name: str
    entry_year: int | None
    country: str | None  # None = pays non publié par le fonds
    description_short: str | None  # résumé IA au format des slides
    description_short_by_ai: bool
    description: str | None  # texte publié par le fonds
    source_url: str


class FundProfile(BaseModel):
    """Fiche de la meilleure stratégie, telle que publiée dans la base (aucun calcul).

    Ajoutée pour l'écran de classement (Alexandre, 2026-11-26) : le banquier doit voir le ticket et
    la VE publiés, le site du fonds et la source sans quitter le classement. None = non publié.
    """

    website: str | None
    source_url: str | None
    last_fund_name: str | None
    equity_ticket_min_eur_m: float | None
    equity_ticket_max_eur_m: float | None
    target_ev_min_eur_m: float | None
    target_ev_max_eur_m: float | None
    # Collecte du 2026-11-26 (5 fonds) ; liste vide = pas encore collecté.
    latest_investments_france: list[Investment] = []
    holdings_collected: bool = False


class RankedCompany(CompanyResult):
    """Ligne du classement (CompanyResult du moteur) + fiche publiée de sa meilleure stratégie."""

    profile: FundProfile


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _number(value: object) -> float | None:
    return None if value is None else float(value)  # Decimal de la base -> nombre JSON


def _investment(h: Holding) -> Investment:
    return Investment(
        company_name=h.company_name,
        entry_year=h.entry_year,
        country=h.country,
        description_short=h.description_short,
        description_short_by_ai=h.description_short_by_ai,
        description=h.description,
        source_url=h.source_url,
    )


def fund_profile(
    data: InvestorData,
    strategy_id: str,
    holdings: Mapping[str, tuple[Holding, ...]] | None = None,
) -> FundProfile:
    row = data.strategies[strategy_id]
    held = (holdings or {}).get(str(row["fund_id"]), ())
    return FundProfile(
        latest_investments_france=[_investment(h) for h in latest_in_france(held)],
        holdings_collected=bool(held),
        website=_text(row.get("website")),
        source_url=_text(row.get("source_url")),
        last_fund_name=_text(row.get("last_fund_name")),
        equity_ticket_min_eur_m=_number(row.get("equity_ticket_min_eur_m")),
        equity_ticket_max_eur_m=_number(row.get("equity_ticket_max_eur_m")),
        target_ev_min_eur_m=_number(row.get("target_ev_min_eur_m")),
        target_ev_max_eur_m=_number(row.get("target_ev_max_eur_m")),
    )


class ExcludedCompany(BaseModel):
    """Société de gestion dont toutes les stratégies sont exclues : le banquier peut quand même
    l'ajouter à sa sélection (il sait qu'elle sera intéressée)."""

    fund_id: str
    management_company: str | None
    strategies: list[ExcludedStrategy]
    profile: FundProfile


class ScoreCounts(BaseModel):
    strategies_total: int
    strategies_ranked: int
    strategies_excluded: int
    companies_ranked: int


class ScoreResponse(BaseModel):
    operation_id: str
    company_name: str
    analysis_date: date
    config_version: str
    # Message à afficher quand aucun fonds n'est compatible ; None sinon.
    message: str | None
    counts: ScoreCounts
    companies: list[RankedCompany]
    excluded: list[ExcludedStrategy]
    excluded_companies: list[ExcludedCompany]


@router.post("/score", response_model=ScoreResponse)
def score(payload: ScoreRequest, request: Request) -> ScoreResponse:
    base: ScoringBase = request.app.state.scoring_base
    operation = Operation(
        operation_id=payload.operation_id or "operation",
        company_name=payload.company_name or "Opération sans nom",
        deal_type=payload.deal_type,
        equity_ticket_eur_m=payload.equity_ticket_eur_m,
        enterprise_value_eur_m=payload.enterprise_value_eur_m,
        sector=payload.sector,
        stake_sought=payload.stake_sought,
        analysis_date=payload.analysis_date or date.today(),
    )
    result = score_operation(operation, base.funds)
    companies = rank_management_companies(base.data, result)
    excluded = [
        ExcludedStrategy(
            strategy_id=r.strategy_id,
            fund_id=str(base.data.strategies[r.strategy_id]["fund_id"]),
            strategy_name=r.strategy_name,
            management_company=r.management_company,
            exclusion_reasons=r.exclusion_reasons,
        )
        for r in result.excluded
    ]
    return ScoreResponse(
        operation_id=operation.operation_id,
        company_name=operation.company_name,
        analysis_date=operation.analysis_date,
        config_version=result.config_version,
        message=None
        if companies
        else "Aucun fonds de la base n'est compatible avec cette opération.",
        counts=ScoreCounts(
            strategies_total=len(base.funds),
            strategies_ranked=len(result.ranked),
            strategies_excluded=len(result.excluded),
            companies_ranked=len(companies),
        ),
        companies=[
            RankedCompany(
                **company.model_dump(),
                profile=fund_profile(base.data, company.best_strategy_id, base.holdings),
            )
            for company in companies
        ],
        excluded=excluded,
        excluded_companies=_excluded_companies(base, excluded, {c.fund_id for c in companies}),
    )


def _excluded_companies(
    base: ScoringBase, excluded: list[ExcludedStrategy], ranked_funds: set[str]
) -> list[ExcludedCompany]:
    """Sociétés de gestion absentes du classement (toutes leurs stratégies exclues), par nom."""
    grouped: dict[str, list[ExcludedStrategy]] = {}
    for strategy in excluded:
        if strategy.fund_id not in ranked_funds:
            grouped.setdefault(strategy.fund_id, []).append(strategy)
    out = [
        ExcludedCompany(
            fund_id=fund_id,
            management_company=strategies[0].management_company,
            strategies=strategies,
            profile=fund_profile(base.data, strategies[0].strategy_id, base.holdings),
        )
        for fund_id, strategies in grouped.items()
    ]
    return sorted(out, key=lambda c: (c.management_company or c.fund_id).lower())
