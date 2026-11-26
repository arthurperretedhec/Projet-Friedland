"""Route POST /api/score : classement des sociétés de gestion pour une opération.

Rôle de la route (architecture.md, partie « API ») : valider la requête, appeler la logique
(moteur de score), renvoyer une réponse typée. Aucune règle de score ici.
La base est chargée et traduite une seule fois au démarrage (`build_scoring_base`, appelé dans
app/main.py) ; chaque appel réutilise `app.state.scoring_base`.
Documentation pour l'interface : app/docs/scoring.md, « Route d'API POST /api/score ».
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.data.investors import InvestorData
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


def build_scoring_base(data: InvestorData) -> ScoringBase:
    return ScoringBase(data=data, funds=funds_from_base(data))


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
    strategy_name: str | None
    management_company: str | None
    exclusion_reasons: list[str]


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


class RankedCompany(CompanyResult):
    """Ligne du classement (CompanyResult du moteur) + fiche publiée de sa meilleure stratégie."""

    profile: FundProfile


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _number(value: object) -> float | None:
    return None if value is None else float(value)  # Decimal de la base -> nombre JSON


def fund_profile(data: InvestorData, strategy_id: str) -> FundProfile:
    row = data.strategies[strategy_id]
    return FundProfile(
        website=_text(row.get("website")),
        source_url=_text(row.get("source_url")),
        last_fund_name=_text(row.get("last_fund_name")),
        equity_ticket_min_eur_m=_number(row.get("equity_ticket_min_eur_m")),
        equity_ticket_max_eur_m=_number(row.get("equity_ticket_max_eur_m")),
        target_ev_min_eur_m=_number(row.get("target_ev_min_eur_m")),
        target_ev_max_eur_m=_number(row.get("target_ev_max_eur_m")),
    )


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
                **company.model_dump(), profile=fund_profile(base.data, company.best_strategy_id)
            )
            for company in companies
        ],
        excluded=[
            ExcludedStrategy(
                strategy_id=r.strategy_id,
                strategy_name=r.strategy_name,
                management_company=r.management_company,
                exclusion_reasons=r.exclusion_reasons,
            )
            for r in result.excluded
        ],
    )
